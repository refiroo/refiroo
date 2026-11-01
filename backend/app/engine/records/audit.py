from collections.abc import Iterable, Iterator, Sequence
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any

from sqlalchemy import event as orm_event
from sqlalchemy import select
from sqlalchemy.orm import Session

from ...common.encoding import to_jsonable
from ...common.pagination import Page, PageRequest, datetime_key, integer_key, paginate_statement
from ...models.database import AuditEvent, AuditEventSubject, ChangeSet
from ..authorization.writes import requester_of
from ..identity.principals import columns, named_by
from .feed import take_positions
from .history_details import kind_condition

_HISTORY_KEYS = (
    datetime_key("occurredAt", AuditEvent.occurred_at, "occurred_at", descending=True),
    integer_key("sequenceId", AuditEvent.sequence_id, "sequence_id", descending=True),
)
_CAUSE = "audit_cause"
_CHANNEL = "audit_channel"
_TRIAL = "audit_trial_run"


@contextmanager
def audit_cause(session: Session, kind: str, cause_id: str) -> Iterator[None]:
    """Name what made the changes audited in this session meanwhile, such as a job.

    A job's item goes through the single-write service, which audits as it always does; the
    entries it writes carry the job as their cause (INTEGRATION_API P6).
    """
    session.info[_CAUSE] = (kind, cause_id)
    try:
        yield
    finally:
        session.info.pop(_CAUSE, None)


@contextmanager
def trial_run(session: Session) -> Iterator[None]:
    """A trial run (a preview or a dry run, rolled back whole) meanwhile: decided writes record no
    audit entry and take no feed position (0.10 A3a, D72). Nothing within a run reads them, and
    the run commits nothing."""
    session.info[_TRIAL] = True
    try:
        yield
    finally:
        session.info.pop(_TRIAL, None)


def audit_cause_of(session: Session) -> tuple[str | None, str | None]:
    """What ``audit_cause`` names for this session now: the kind and ID, or neither."""
    return session.info.get(_CAUSE, (None, None))


def set_channel(session: Session, channel: str) -> None:
    """What the session's audit entries name as their channel from now on (0.16 AG-D30)."""
    session.info[_CHANNEL] = channel


def audit_actor_of(session: Session) -> dict[str, Any]:
    """Who the session's audit entries name as their actor (0.12 Z4, D313), as the three
    columns: the caller whose writes the session makes (a request's, or a job step's requester),
    else the engine. The same writer Z2's record-type check trusts."""
    principal = requester_of(session)
    return {
        "actor_kind": principal[0] if principal is not None else "engine",
        **columns(principal, "actor"),
    }


@orm_event.listens_for(Session, "before_flush")
def _name_actors(session: Session, _context: Any, _instances: Any) -> None:
    """Every audit entry the ORM inserts names its actor, however it was built, unless it was built
    naming one (a failed sign-in names nobody); the raw inserts take ``audit_actor_of``."""
    added = [
        item
        for item in session.new
        if isinstance(item, AuditEvent) and "actor_kind" not in item.__dict__
    ]
    if not added:
        return
    actor = audit_actor_of(session)
    channel = session.info.get(_CHANNEL)
    for item in added:
        item.channel = channel
        for column, value in actor.items():
            setattr(item, column, value)


def change_set_of(aggregate_type: str, aggregate_id: str, changes: Any) -> str | None:
    """The change set an entry was made in: its own aggregate, or the one its changes name."""
    if aggregate_type == "change-set":
        return aggregate_id
    named = changes.get("changeSetId") if isinstance(changes, dict) else None
    return named if isinstance(named, str) else None


@orm_event.listens_for(Session, "before_flush")
def _place_entries(session: Session, _context: Any, _instances: Any) -> None:
    """Every entry the ORM inserts that belongs to a workspace names it (0.12 Z6, D341): one made
    in a change set its change set's, a workspace's model activation the one its changes name. One
    statement per flush for the change sets; the raw inserts name it themselves."""
    unplaced = [
        item for item in session.new if isinstance(item, AuditEvent) and item.workspace_key is None
    ]
    if not unplaced:
        return
    wanted = {
        item: change_set_of(item.aggregate_type, item.aggregate_id, item.changes)
        for item in unplaced
    }
    found = {item.id: item.workspace_key for item in session.new if isinstance(item, ChangeSet)}
    ids = {change_set for change_set in wanted.values() if change_set is not None} - set(found)
    if ids:
        found.update(
            session.execute(
                select(ChangeSet.id, ChangeSet.workspace_key).where(ChangeSet.id.in_(ids))
            )
            .tuples()
            .all()
        )
    for item, change_set in wanted.items():
        named = item.changes.get("workspaceKey") if isinstance(item.changes, dict) else None
        if change_set is not None:
            item.workspace_key = found.get(change_set) or named
        elif item.aggregate_type == "workspace_model":
            item.workspace_key = named


@dataclass(frozen=True)
class AuditEntry:
    """One audit event a decided write records, with its subjects (0.9.0-alpha.1 PG3b) and, for a
    change to live data, what its feed entry names (``feed.object_subject``, Base 0.9 F1)."""

    aggregate_type: str
    aggregate_id: str
    action: str
    version: int
    changes: dict[str, Any]
    object_ids: tuple[str, ...]
    subject: dict[str, Any] | None = None
    # A relation set's ``transition`` (0.9 B3) summarises entries that are in the feed; it is not.
    feed: bool = True


def _place_in_feed(session: Session, workspace_key: str, events: Sequence[AuditEvent]) -> None:
    """Give events that change the workspace's live data the next positions of its feed, in
    order (Base 0.9 F1); the caller holds the workspace row lock."""
    if not events:
        return
    first, release_id = take_positions(session, workspace_key, len(events))
    for offset, event in enumerate(events):
        event.workspace_key = workspace_key
        event.feed_position = first + offset
        event.model_release_id = release_id


def record_audit_events(
    session: Session,
    entries: Sequence[AuditEntry],
    *,
    workspace_key: str | None = None,
    feed: bool = True,
) -> list[AuditEvent]:
    """Record decided writes' events in order, per record as ever (PG-D16): the events in
    multi-row inserts whose sequence numbers come back for their subjects. With
    ``workspace_key`` they belong to that workspace (0.12 Z6, D341) and, unless ``feed`` is off
    (a change set's edits), change its live data and take feed positions
    (``LiveWrites.record_all``).
    """
    if not entries or session.info.get(_TRIAL):
        return []
    cause_kind, cause_id = session.info.get(_CAUSE, (None, None))
    events = [
        AuditEvent(
            aggregate_type=entry.aggregate_type,
            aggregate_id=entry.aggregate_id,
            action=entry.action,
            version=entry.version,
            changes=to_jsonable(entry.changes),
            cause_kind=cause_kind,
            cause_id=cause_id,
            workspace_key=workspace_key,
            subject=entry.subject,
        )
        for entry in entries
    ]
    if workspace_key is not None and feed:
        _place_in_feed(
            session,
            workspace_key,
            [event for event, entry in zip(events, entries, strict=True) if entry.feed],
        )
    session.add_all(events)
    session.flush()
    session.add_all(
        AuditEventSubject(audit_event_id=event.sequence_id, object_id=object_id)
        for event, entry in zip(events, entries, strict=True)
        for object_id in dict.fromkeys(entry.object_ids)
    )
    return events


def record_audit_event(
    session: Session,
    *,
    aggregate_type: str,
    aggregate_id: str,
    action: str,
    version: int,
    changes: dict[str, Any],
    object_ids: Iterable[str],
    workspace_key: str | None = None,
    subject: dict[str, Any] | None = None,
    feed: bool = True,
) -> AuditEvent:
    """Record one event; with ``workspace_key`` it belongs to that workspace and, unless ``feed``
    is off, changes its live data and takes its next feed position (``LiveWrites.record``,
    publishing and withdrawal). ``subject`` names the record or relationship it changed. An entry
    given no workspace is placed from its change set when it names one (``_place_entries``)."""
    cause_kind, cause_id = session.info.get(_CAUSE, (None, None))
    event = AuditEvent(
        aggregate_type=aggregate_type,
        aggregate_id=aggregate_id,
        action=action,
        version=version,
        changes=to_jsonable(changes),
        cause_kind=cause_kind,
        cause_id=cause_id,
        workspace_key=workspace_key,
        subject=subject,
    )
    if workspace_key is not None and feed:
        _place_in_feed(session, workspace_key, [event])
    session.add(event)
    session.flush()
    for object_id in dict.fromkeys(object_ids):
        session.add(AuditEventSubject(audit_event_id=event.sequence_id, object_id=object_id))
    return event


def object_history(
    session: Session,
    *,
    object_id: str,
    object_type_key: str,
    workspace_key: str,
    page: PageRequest,
    page_size: int,
    kind: str | None = None,
    actor_id: str | None = None,
) -> Page[AuditEvent]:
    """A record's history, newest first; ``kind`` and ``actor_id`` (a person's or client's ID, or
    ``engine``) narrow it in the database (0.12 RH1, D391)."""
    statement = (
        select(AuditEvent)
        .join(AuditEventSubject, AuditEventSubject.audit_event_id == AuditEvent.sequence_id)
        .where(AuditEventSubject.object_id == object_id)
    )
    if kind is not None:
        statement = statement.where(kind_condition(kind))
    if actor_id == "engine":
        statement = statement.where(AuditEvent.actor_kind == "engine")
    elif actor_id is not None:
        statement = statement.where(
            named_by(AuditEvent.actor_user_id, AuditEvent.actor_client_id, actor_id)
        )
    return paginate_statement(
        session,
        statement,
        keys=_HISTORY_KEYS,
        scope="object-history",
        filters={
            "objectId": object_id,
            "objectTypeKey": object_type_key,
            "workspaceKey": workspace_key,
            "kind": kind,
            "actorId": actor_id,
        },
        page=page,
        page_size=page_size,
        message="Audit history cursor is invalid",
    )
