"""A person's or client's inbox (Product 0.12 A2, D233).

A notice is a row of ``notifications`` for one principal: a request waiting for their approval, a
decision on theirs (``announcements``), a job they started that finished (a trigger on ``jobs``).
Reading is paged newest first; a notice is read or unread, and marking is idempotent. The stream
(``GET /me/notifications/events``) wakes on ``rdm_notifications``, which each insert sends
(``events.INBOX_CHANNEL``) and then reads the notices after the one it last sent.
"""

from collections.abc import Iterable, Sequence
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from sqlalchemy import func, insert, select, update
from sqlalchemy.orm import Session

from ...common.pagination import Page, PageRequest, integer_key, paginate_statement
from ...models.database import Notification
from ..identity.principals import Ref

_KEYS = (integer_key("sequenceId", Notification.sequence_id, "sequence_id", descending=True),)


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


def close_requests(session: Session, change_set_id: str) -> None:
    """Mark the unread "waiting for your approval" notices of a change set read: once it is
    decided or withdrawn they are no longer waiting."""
    session.execute(
        update(Notification)
        .where(
            Notification.subject_kind == "change-set",
            Notification.subject_id == change_set_id,
            Notification.kind == "change-set.submitted",
            Notification.read_at.is_(None),
        )
        .values(read_at=datetime.now(UTC))
        .execution_options(synchronize_session=False)
    )


def notification_page(
    session: Session,
    found: Ref,
    *,
    unread: bool | None,
    page: PageRequest,
    page_size: int,
) -> Page[Notification]:
    """The principal's notices, newest first; ``unread`` keeps the unread (true) or the read
    (false)."""
    statement = select(Notification).where(_column(found) == found[1])
    if unread is not None:
        statement = statement.where(
            Notification.read_at.is_(None) if unread else Notification.read_at.is_not(None)
        )
    return paginate_statement(
        session,
        statement,
        keys=_KEYS,
        scope="notifications",
        filters={"principal": principal_key(found), "unread": unread},
        page=page,
        page_size=page_size,
        message="Notification list cursor is invalid",
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


def mark_read(session: Session, found: Ref, ids: Sequence[str] | None) -> int:
    """Mark the principal's notices read: those in ``ids``, or all of them when ``ids`` is None.
    Another principal's or an unknown ID is left alone. Commits; how many were unread."""
    statement = update(Notification).where(
        _column(found) == found[1], Notification.read_at.is_(None)
    )
    if ids is not None:
        statement = statement.where(Notification.id.in_(ids))
    result = session.execute(
        statement.values(read_at=datetime.now(UTC)).execution_options(synchronize_session=False)
    )
    session.commit()
    return result.rowcount


def after(session: Session, found: Ref, sequence_id: int) -> list[Notification]:
    """The principal's notices made after ``sequence_id``, oldest first (the stream's read)."""
    return list(
        session.scalars(
            select(Notification)
            .where(_column(found) == found[1], Notification.sequence_id > sequence_id)
            .order_by(Notification.sequence_id)
        )
    )


def newest_id(session: Session, found: Ref) -> int:
    """The sequence ID of the principal's newest notice, 0 with none."""
    return (
        session.scalar(select(func.max(Notification.sequence_id)).where(_column(found) == found[1]))
        or 0
    )
