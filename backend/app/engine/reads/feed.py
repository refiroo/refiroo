"""The feed of a workspace's live data, read by position (Base 0.9 F1, INTEGRATION_API §F4).

Positions are gapless and committed in order (``records/feed.py``), so the position a reader last
processed is its resume token: a page is the entries after it, up to the head the workspace's
counter shows. A filtered page scans at most ten pages' worth of positions and says where it
stopped, so a sparse filter never costs an unbounded scan.

Entries older than the retention period expire (F2, §F5, D8): a position below the earliest one
still answered is refused, naming the workspace's active publication as the baseline to re-read.
The earliest position never passes that publication's, so a reader can always follow on from it,
and with no publication to re-read nothing expires (D40). The audit log itself is never pruned.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from ...errors import api_error
from ...models.database import AuditEvent, Publication, Workspace

# What a filtered page scans at most, in pages (§F4).
SCAN_PAGES = 10
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


@dataclass(frozen=True)
class RetentionFloor:
    """The workspace's feed head, the earliest position still answered, and the active publication
    to re-read below it (its ID, number and position; ``None`` without one)."""

    head_position: int
    earliest_position: int
    publication_id: str | None
    publication_number: int | None
    publication_position: int | None


def retention_floor(session: Session, workspace_key: str, retention_days: int) -> RetentionFloor:
    """The earliest position the feed answers (F2, D40): the first entry within the period, never
    past the active publication's position + 1; 1 with no publication that has a position. Consumer
    events expire with it (C-D92). ``404 WORKSPACE_NOT_FOUND`` for an unknown workspace."""
    row = session.execute(
        select(
            Workspace.feed_position,
            Publication.id,
            Publication.publication_number,
            Publication.feed_position,
        )
        .outerjoin(Publication, Publication.id == Workspace.active_publication_id)
        .where(Workspace.key == workspace_key)
    ).one_or_none()
    if row is None:
        raise api_error(404, "WORKSPACE_NOT_FOUND", "Workspace not found")
    head, publication_id, publication_number, baseline = row
    earliest = 1
    if baseline is not None:
        cutoff = datetime.now(UTC) - timedelta(days=retention_days)
        earliest = min(baseline + 1, _time_floor(session, workspace_key, cutoff, head))
    return RetentionFloor(head, earliest, publication_id, publication_number, baseline)


def read_feed(
    session: Session,
    workspace_key: str,
    *,
    after: int,
    page_size: int,
    retention_days: int,
    kinds: Sequence[str] = (),
    object_type_keys: Sequence[str] = (),
) -> FeedPage:
    """The entries after ``after``: a page of them, or of those matching the filters within a
    bounded scan. ``kinds`` and ``object_type_keys`` each match any of their values; an object type
    matches a record's type or, for a reclassification, its previous one."""
    floor = retention_floor(session, workspace_key, retention_days)
    head, earliest = floor.head_position, floor.earliest_position
    if after > head:
        raise api_error(
            409,
            "FEED_POSITION_AHEAD",
            f"Position {after} is past the feed's head, {head}: it was not read from this "
            "workspace's feed, or the database was restored to an earlier state. Read again from a "
            "baseline",
            {"headPosition": head},
        )
    if after < earliest - 1:
        raise api_error(
            410,
            "FEED_POSITION_EXPIRED",
            f"Position {after} has expired: the feed answers from position {earliest} on. Read "
            "the publication named in the details, then follow the feed from its position",
            {
                "earliestPosition": earliest,
                "headPosition": head,
                "publication": {
                    "id": floor.publication_id,
                    "publicationNumber": floor.publication_number,
                    "feedPosition": floor.publication_position,
                },
            },
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
    return FeedPage(entries, next_after, head, earliest)


def _time_floor(session: Session, workspace_key: str, cutoff: datetime, head: int) -> int:
    """The position of the first entry within the retention period, or the one after the head when
    every entry is older. Positions and times rise together, both taken under the workspace lock,
    so the first entry in time is the first in position; one probe of
    ``ix_audit_events_feed_time`` finds it however long the feed is."""
    first = session.scalar(
        select(AuditEvent.feed_position)
        .where(
            AuditEvent.workspace_key == workspace_key,
            AuditEvent.feed_position.is_not(None),
            AuditEvent.occurred_at >= cutoff,
        )
        .order_by(AuditEvent.occurred_at, AuditEvent.feed_position)
        .limit(1)
    )
    return head + 1 if first is None else first
