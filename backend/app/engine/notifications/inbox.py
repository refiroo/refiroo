"""A person's or client's inbox (Product 0.12 A2, D233).

A notice is a row of ``notifications`` for one principal: a request waiting for their approval, a
decision on theirs (``announcements``), a job they started that finished (a trigger on ``jobs``).
Reading is paged newest or oldest first, searched and filtered (NT1, D462); a notice is read or
unread, marking is idempotent, and its owner may remove it (D461). The engine closes a notice whose
request is answered (``close``, D464), and the job worker's hourly sweep deletes notices older than
``RETENTION_DAYS`` (``expire``, D465). The stream (``GET /me/notifications/events``) wakes on
``rdm_notifications``, which each insert sends (``events.INBOX_CHANNEL``) and then reads the notices
after the one it last sent.
"""

from collections.abc import Collection, Iterable, Sequence
from datetime import UTC, datetime, timedelta
from typing import Any, Literal
from uuid import uuid4

from sqlalchemy import and_, delete, func, insert, or_, select, update
from sqlalchemy.orm import Session

from ...common.pagination import Page, PageRequest, integer_key, paginate_statement
from ...models.database import Notification
from ..identity.principals import Ref
from ..reads.object_query import escape_like
from .kinds import NOTICE_KINDS

Sort = Literal["newest", "oldest"]

_KEYS: dict[str, tuple[Any, ...]] = {
    "newest": (
        integer_key("sequenceId", Notification.sequence_id, "sequence_id", descending=True),
    ),
    "oldest": (integer_key("sequenceId", Notification.sequence_id, "sequence_id"),),
}

# How long a notice is kept, read or not (D465).
RETENTION_DAYS = 90


def principal_key(found: Ref) -> str:
    """What the inbox stream subscribes under: ``user:<row ID>`` or ``client:<row ID>``."""
    return f"{found[0]}:{found[1]}"


def _column(found: Ref) -> Any:
    return Notification.user_id if found[0] == "user" else Notification.client_id


def notify(
    session: Session,
    recipients: Iterable[Ref],
    *,
    kind: str,
    workspace_key: str,
    subject_kind: str,
    subject_id: str,
    details: dict[str, Any],
) -> int:
    """Put one notice in each recipient's inbox, in the caller's transaction; how many."""
    now = datetime.now(UTC)
    rows = [
        {
            "id": str(uuid4()),
            "user_id": row_id if principal == "user" else None,
            "client_id": row_id if principal == "client" else None,
            "kind": kind,
            "workspace_key": workspace_key,
            "subject_kind": subject_kind,
            "subject_id": subject_id,
            "details": details,
            "created_at": now,
        }
        for principal, row_id in dict.fromkeys(recipients)
    ]
    if rows:
        session.execute(insert(Notification), rows)
    return len(rows)


def close(session: Session, subject_kind: str, subject_id: str, kinds: Sequence[str]) -> None:
    """Mark everyone's unread notices of ``kinds`` about one subject read, in the caller's
    transaction: what they asked for is done (D464). A job's request for confirmation is closed the
    same way by the jobs trigger (revision ``20261116_01``)."""
    session.execute(
        update(Notification)
        .where(
            Notification.subject_kind == subject_kind,
            Notification.subject_id == subject_id,
            Notification.kind.in_(kinds),
            Notification.read_at.is_(None),
        )
        .values(read_at=datetime.now(UTC))
        .execution_options(synchronize_session=False)
    )


def close_requests(session: Session, change_set_id: str) -> None:
    """Close a change set's "waiting for your approval" notices: once it is decided or withdrawn
    they are no longer waiting."""
    close(session, "change-set", change_set_id, ["change-set.submitted"])


def _search(text: str) -> Any:
    """What a person sees of a notice contains ``text``: its kind's words, the change set's name,
    the comment, who acted, the job's kind (D462); other values in ``details`` are not read."""
    pattern = f"%{escape_like(text)}%"
    fields = (
        Notification.details["changeSetName"].as_string(),
        Notification.details["comment"].as_string(),
        Notification.details[("actor", "name")].as_string(),
        Notification.details["jobKind"].as_string(),
    )
    kinds = [kind for kind, label in NOTICE_KINDS if text.casefold() in label.casefold()]
    return or_(
        *(field.ilike(pattern, escape="\\") for field in fields),
        Notification.kind.in_(kinds),
    )


def notification_page(
    session: Session,
    found: Ref,
    *,
    unread: bool | None,
    page: PageRequest,
    page_size: int,
    search: str | None = None,
    kind: str | None = None,
    workspace_key: str | None = None,
    sort: Sort = "newest",
) -> Page[Notification]:
    """The principal's notices, newest or oldest first; ``unread`` keeps the unread (true) or the
    read (false); ``search``, ``kind`` and ``workspace_key`` narrow them."""
    search = search.strip() if search and search.strip() else None
    statement = select(Notification).where(_column(found) == found[1])
    if unread is not None:
        statement = statement.where(
            Notification.read_at.is_(None) if unread else Notification.read_at.is_not(None)
        )
    if search:
        statement = statement.where(_search(search))
    if kind:
        statement = statement.where(Notification.kind == kind)
    if workspace_key:
        statement = statement.where(Notification.workspace_key == workspace_key)
    return paginate_statement(
        session,
        statement,
        keys=_KEYS[sort],
        scope="notifications",
        filters={
            "principal": principal_key(found),
            "unread": unread,
            "q": search,
            "kind": kind,
            "workspace": workspace_key,
        },
        page=page,
        page_size=page_size,
        message="Notification list cursor is invalid",
    )


def find(session: Session, found: Ref, notification_id: str) -> Notification | None:
    """The principal's notice with this ID; None for another's or an unknown one (a digest links to
    its notices by ID, AO-D36)."""
    return session.scalar(
        select(Notification).where(_column(found) == found[1], Notification.id == notification_id)
    )


def unread_count(session: Session, found: Ref) -> int:
    return (
        session.scalar(
            select(func.count())
            .select_from(Notification)
            .where(_column(found) == found[1], Notification.read_at.is_(None))
        )
        or 0
    )


def mark_read(
    session: Session,
    found: Ref,
    ids: Sequence[str] | None,
    *,
    subject_id: str | None = None,
    read: bool = True,
) -> int:
    """Mark the principal's notices read (or unread with ``read`` false): those in ``ids``, those
    about ``subject_id``, or all of them when neither is given. Another principal's or an unknown
    ID is left alone. Commits; how many changed."""
    statement = update(Notification).where(
        _column(found) == found[1],
        Notification.read_at.is_(None) if read else Notification.read_at.is_not(None),
    )
    if ids is not None:
        statement = statement.where(Notification.id.in_(ids))
    if subject_id is not None:
        statement = statement.where(Notification.subject_id == subject_id)
    result = session.execute(
        statement.values(read_at=datetime.now(UTC) if read else None).execution_options(
            synchronize_session=False
        )
    )
    session.commit()
    return result.rowcount


def remove(session: Session, found: Ref, ids: Sequence[str] | None) -> int:
    """Delete the principal's notices in ``ids``, or every read one when ``ids`` is None (D461).
    Another principal's or an unknown ID is left alone. Commits; how many went."""
    statement = delete(Notification).where(_column(found) == found[1])
    statement = (
        statement.where(Notification.id.in_(ids))
        if ids is not None
        else statement.where(Notification.read_at.is_not(None))
    )
    result = session.execute(statement.execution_options(synchronize_session=False))
    session.commit()
    return result.rowcount


def expire(session: Session, now: datetime) -> int:
    """Delete every notice older than ``RETENTION_DAYS`` in one statement (the job worker's hourly
    sweep, D465); the caller commits. How many went."""
    result = session.execute(
        delete(Notification)
        .where(Notification.created_at < now - timedelta(days=RETENTION_DAYS))
        .execution_options(synchronize_session=False)
    )
    return result.rowcount


# One catch-up read of the stream holds at most this many notices; the stream reads again until
# a read comes back short (0.12 R), so a long absence is not one unbounded query.
CATCH_UP_LIMIT = 200


def after(
    session: Session,
    found: Ref,
    sequence_id: int,
    limit: int | None = None,
    *,
    recent_since: datetime | None = None,
    known: Collection[int] = (),
) -> list[Notification]:
    """The principal's notices made after ``sequence_id``, oldest first, at most ``limit``
    (``CATCH_UP_LIMIT``) of them (the stream's read). Sequence IDs are given when a notice is
    inserted and a notice shows at its commit, so one may appear after a later one was read; with
    ``recent_since`` the notices created since then are listed too, whatever their ID, except those
    in ``known`` (the ones the caller has sent)."""
    after_id = Notification.sequence_id > sequence_id
    late = (
        None
        if recent_since is None
        else and_(Notification.created_at >= recent_since, Notification.sequence_id.not_in(known))
    )
    return list(
        session.scalars(
            select(Notification)
            .where(_column(found) == found[1], after_id if late is None else or_(after_id, late))
            .order_by(Notification.sequence_id)
            .limit(limit or CATCH_UP_LIMIT)
        )
    )


def newest_id(session: Session, found: Ref) -> int:
    """The sequence ID of the principal's newest notice, 0 with none."""
    return (
        session.scalar(select(func.max(Notification.sequence_id)).where(_column(found) == found[1]))
        or 0
    )
