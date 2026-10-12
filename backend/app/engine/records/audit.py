from collections.abc import Iterable, Iterator, Sequence
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from ...common.encoding import to_jsonable
from ...common.pagination import Page, PageRequest, datetime_key, integer_key, paginate_statement
from ...models.database import AuditEvent, AuditEventSubject
from .feed import take_positions

_HISTORY_KEYS = (
    datetime_key("occurredAt", AuditEvent.occurred_at, "occurred_at", descending=True),
    integer_key("sequenceId", AuditEvent.sequence_id, "sequence_id", descending=True),
)
_CAUSE = "audit_cause"
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
    session: Session, entries: Sequence[AuditEntry], *, workspace_key: str | None = None
) -> list[AuditEvent]:
    """Record decided writes' events in order, per record as ever (PG-D16): the events in
    multi-row inserts whose sequence numbers come back for their subjects. With
    ``workspace_key`` they change its live data and take feed positions (``LiveWrites.record_all``).
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
            feed_subject=entry.subject if workspace_key is not None and entry.feed else None,
        )
        for entry in entries
    ]
    if workspace_key is not None:
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
) -> AuditEvent:
    """Record one event; with ``workspace_key`` it changes that workspace's live data and takes
    its next feed position (``LiveWrites.record``, publishing and withdrawal)."""
    cause_kind, cause_id = session.info.get(_CAUSE, (None, None))
    event = AuditEvent(
        aggregate_type=aggregate_type,
        aggregate_id=aggregate_id,
        action=action,
        version=version,
        changes=to_jsonable(changes),
        cause_kind=cause_kind,
        cause_id=cause_id,
        feed_subject=subject if workspace_key is not None else None,
    )
    if workspace_key is not None:
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
) -> Page[AuditEvent]:
    statement = (
        select(AuditEvent)
        .join(AuditEventSubject, AuditEventSubject.audit_event_id == AuditEvent.sequence_id)
        .where(AuditEventSubject.object_id == object_id)
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
        },
        page=page,
        page_size=page_size,
        message="Audit history cursor is invalid",
    )
