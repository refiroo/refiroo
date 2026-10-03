"""The feed of a workspace's live data, read by position (Base 0.9 F1, INTEGRATION_API §F4).

Positions are gapless and committed in order (``records/feed.py``), so the position a reader last
processed is its resume token: a page is the entries after it, up to the head the workspace's
counter shows. A filtered page scans at most ten pages' worth of positions and says where it
stopped, so a sparse filter never costs an unbounded scan.
"""

from collections.abc import Sequence
from dataclasses import dataclass

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from ...errors import api_error
from ...models.database import AuditEvent, Workspace

# What a filtered page scans at most, in pages (§F4).
SCAN_PAGES = 10
# Until retention (F2) no entry expires: every feed starts at its first position.
EARLIEST_POSITION = 1
# The audit aggregates of each kind of entry; a withdrawal is aggregated on the workspace.
KIND_AGGREGATES = {
    "object": ("object",),
    "relation": ("relation",),
    "publication": ("publication", "workspace"),
}


@dataclass(frozen=True)
class FeedPage:
    entries: list[AuditEvent]
    next_after: int
    head_position: int
    earliest_position: int


def read_feed(
    session: Session,
    workspace_key: str,
    *,
    after: int,
    page_size: int,
    kinds: Sequence[str] = (),
    object_type_keys: Sequence[str] = (),
) -> FeedPage:
    """The entries after ``after``: a page of them, or of those matching the filters within a
    bounded scan. ``kinds`` and ``object_type_keys`` each match any of their values; an object type
    matches a record's type or, for a reclassification, its previous one."""
    head = session.scalar(select(Workspace.feed_position).where(Workspace.key == workspace_key))
    if head is None:
        raise api_error(404, "workspace_not_found", "Workspace not found")
    if after > head:
        raise api_error(
            409,
            "feed_position_ahead",
            f"Position {after} is past the feed's head, {head}: it was not read from this "
            "workspace's feed, or the database was restored to an earlier state. Read again from a "
            "baseline",
            {"headPosition": head},
        )
    filtered = bool(kinds or object_type_keys)
    end = min(head, after + page_size * (SCAN_PAGES if filtered else 1))
    statement = select(AuditEvent).where(
        AuditEvent.workspace_key == workspace_key,
        AuditEvent.feed_position > after,
        AuditEvent.feed_position <= end,
    )
    if kinds:
        statement = statement.where(
            AuditEvent.aggregate_type.in_(
                [aggregate for kind in kinds for aggregate in KIND_AGGREGATES[kind]]
            )
        )
    if object_type_keys:
        subject = AuditEvent.feed_subject
        statement = statement.where(
            AuditEvent.aggregate_type == "object",
            or_(
                subject["objectTypeKey"].as_string().in_(object_type_keys),
                subject["previousObjectTypeKey"].as_string().in_(object_type_keys),
            ),
        )
    entries = list(
        session.scalars(statement.order_by(AuditEvent.feed_position).limit(page_size))
    )
    next_after = entries[-1].feed_position if len(entries) == page_size else end
    return FeedPage(entries, next_after, head, EARLIEST_POSITION)
