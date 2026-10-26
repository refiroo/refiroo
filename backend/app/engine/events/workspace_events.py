"""A workspace's change-set events (Product 0.12 A2, D233).

``change-set.submitted``, ``change-set.approved`` and ``change-set.sent-back`` are not record
events, so they have no place in a consumer API's feed. Each is a row of ``workspace_events`` written
in the transaction of the step it reports, numbered without gaps per workspace (``position``): the
number is taken last in the transaction, by one upsert on the workspace's head row, so two steps
never wait on each other's other locks. A webhook subscription with this source (``SOURCE`` in its
``consumer_api``) delivers them with the same signing, retry, log and resend as record events; its
acknowledged position is a position of these events.

An event reads as a consumer event does to the delivery code (``eventId``, ``event``, ``change``,
``objectType``, ``id``, ``position``, ``occurredAt``), with ``scope: "workspace"`` so a CloudEvent's
type is the event key alone, and names the people (``submitter``, ``decider``: kind, id, name; no
e-mail, D239 as amended by A2) and the change set as it was.
"""

from collections.abc import Sequence
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import uuid4

from sqlalchemy import delete, func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from ...models.database import WorkspaceEvent, WorkspaceEventHead

# What ``consumer_subscriptions.consumer_api`` holds for the workspace source: no model key can.
SOURCE = "$workspace"
SUBMITTED, APPROVED, SENT_BACK = (
    "change-set.submitted",
    "change-set.approved",
    "change-set.sent-back",
)
EVENT_KEYS = (SUBMITTED, APPROVED, SENT_BACK)
_CHANGES = {SUBMITTED: "submitted", APPROVED: "approved", SENT_BACK: "sentBack"}


def record(
    session: Session,
    workspace_key: str,
    event_key: str,
    change_set_id: str,
    body: dict[str, Any],
) -> WorkspaceEvent:
    """Write an event in the caller's transaction; call it last, before the commit."""
    position = session.scalar(
        insert(WorkspaceEventHead)
        .values(workspace_key=workspace_key, position=1)
        .on_conflict_do_update(
            index_elements=[WorkspaceEventHead.workspace_key],
            set_={"position": WorkspaceEventHead.position + 1},
        )
        .returning(WorkspaceEventHead.position)
    )
    now = datetime.now(UTC)
    event_id = str(uuid4())
    row = WorkspaceEvent(
        event_id=event_id,
        workspace_key=workspace_key,
        position=position,
        event_key=event_key,
        change_set_id=change_set_id,
        payload={
            "eventId": event_id,
            "scope": "workspace",
            "event": event_key,
            "change": _CHANGES[event_key],
            "objectType": "change-set",
            "id": change_set_id,
            "position": position,
            "occurredAt": now.isoformat(),
            "workspaceKey": workspace_key,
            **body,
        },
        occurred_at=now,
    )
    session.add(row)
    session.flush()
    return row


def head(session: Session, workspace_key: str) -> int:
    """The position of the workspace's newest event, 0 with none."""
    return (
        session.scalar(
            select(WorkspaceEventHead.position).where(
                WorkspaceEventHead.workspace_key == workspace_key
            )
        )
        or 0
    )


def earliest(session: Session, workspace_key: str) -> int:
    """The first position still kept; ``head + 1`` when none is."""
    found = session.scalar(
        select(func.min(WorkspaceEvent.position)).where(
            WorkspaceEvent.workspace_key == workspace_key
        )
    )
    return found if found is not None else head(session, workspace_key) + 1


def events_after(
    session: Session,
    workspace_key: str,
    after: int,
    *,
    keys: Sequence[str],
    limit: int,
    through: int | None = None,
) -> list[WorkspaceEvent]:
    """The events after position ``after`` (to ``through``), oldest first, of the event ``keys``
    only; at most ``limit``."""
    statement = select(WorkspaceEvent).where(
        WorkspaceEvent.workspace_key == workspace_key,
        WorkspaceEvent.position > after,
        WorkspaceEvent.event_key.in_(keys),
    )
    if through is not None:
        statement = statement.where(WorkspaceEvent.position <= through)
    return list(session.scalars(statement.order_by(WorkspaceEvent.position).limit(limit)))


def prune(session: Session, now: datetime, retention_days: int) -> int:
    """Delete events older than the retention (as record events expire); how many."""
    return session.execute(
        delete(WorkspaceEvent).where(
            WorkspaceEvent.occurred_at < now - timedelta(days=retention_days)
        )
    ).rowcount
