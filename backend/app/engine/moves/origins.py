"""Where a moved record came from, as its history names it (Product 0.11 X3, D23, D136)."""

from collections.abc import Sequence
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from ...models.database import AuditEvent, Job, RecordOrigin


@dataclass(frozen=True)
class HistoryOrigin:
    """The record ``object_id`` was copied from, and the moves among a page's causes."""

    workspace_key: str
    object_id: str
    moves: frozenset[str]


def history_origin(
    session: Session, object_id: str, events: Sequence[AuditEvent]
) -> HistoryOrigin | None:
    """The origin of a record a move created, with the jobs among ``events``' causes that are
    moves (its first, and any later move updating it); none for a record no move created."""
    origin = session.get(RecordOrigin, object_id)
    if origin is None:
        return None
    causes = {event.cause_id for event in events if event.cause_kind == "job" and event.cause_id}
    moves = (
        set(session.scalars(select(Job.id).where(Job.id.in_(causes), Job.kind == "move")))
        if causes
        else set()
    )
    return HistoryOrigin(
        origin.origin_workspace_key,
        origin.origin_object_id,
        frozenset((moves | {origin.job_id}) & causes),
    )
