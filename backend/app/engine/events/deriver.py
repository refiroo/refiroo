"""Consumer events derived from a workspace's feed (Base 0.9 C10, CONSUMER_API "How events are
produced", INTEGRATION_API F6).

The deriver reads a workspace's feed entries after its checkpoint, a page at a time, in one
REPEATABLE READ transaction that holds the checkpoint row (``FOR UPDATE SKIP LOCKED``), so two
processes never derive one range and a write never waits for it: it takes no workspace lock (C-D8).
Each entry is derived under the release it was written under (C-D88); owners are read from live data
as the deriver finds it (C-D89). The events and the checkpoint commit together, so a crash repeats
and skips nothing.

Python reads the page's entries (at most a page) and turns them into the plan's rows (``plan.py``);
one ``INSERT … SELECT`` per definition then finds the objects each change reaches (children,
descendants through a recursive query, relation owners), merges what one position does to one object,
keeps what each event takes and writes the events. A fan-out of thousands of objects never passes
through Python (set work in the database). An event's ID is a digest of its entry, definition, event
and object, so deriving the same state again gives the same IDs.
"""

from collections.abc import Callable, Iterable, Sequence
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import (
    ARRAY,
    Integer,
    String,
    and_,
    case,
    cast,
    column,
    distinct,
    func,
    insert,
    literal,
    literal_column,
    null,
    select,
    union_all,
)
from sqlalchemy.dialects.postgresql import UUID, aggregate_order_by
from sqlalchemy.orm import Session, aliased

from ...models.database import (
    AuditEvent,
    ConsumerEvent,
    ConsumerEventCheckpoint,
    ObjectRelation,
    RdmObject,
    Workspace,
)
from .plan import (
    CHILDREN,
    DESCENDANTS,
    SELF,
    SELF_AND_DESCENDANTS,
    EventPlan,
    FeedChange,
    Own,
    Reach,
)

# Entries derived in one transaction.
PAGE_ENTRIES = 500

PlansFor = Callable[[Session, int], Sequence[EventPlan]]


def derive_page(session: Session, workspace_key: str, plans_for: PlansFor, page_entries: int = PAGE_ENTRIES) -> bool:
    """Derive the workspace's next page of entries and commit; ``False`` when it is derived to its
    head or another deriver holds it. ``session`` must not have run a statement yet."""
    session.connection(execution_options={"isolation_level": "REPEATABLE READ"})
    checkpoint = session.execute(
        select(ConsumerEventCheckpoint)
        .where(ConsumerEventCheckpoint.workspace_key == workspace_key)
        .with_for_update(skip_locked=True)
    ).scalar_one_or_none()
    head = session.scalar(select(Workspace.feed_position).where(Workspace.key == workspace_key))
    if checkpoint is None or head is None or checkpoint.position >= head:
        session.rollback()
        return False
    end = min(head, checkpoint.position + page_entries)
    entries = session.scalars(
        select(AuditEvent)
        .where(
            AuditEvent.workspace_key == workspace_key,
            AuditEvent.feed_position > checkpoint.position,
            AuditEvent.feed_position <= end,
        )
        .order_by(AuditEvent.feed_position)
    ).all()
    by_release: dict[int, list[FeedChange]] = {}
    for entry in entries:
        change = FeedChange.of(entry)
        if change is not None and entry.model_release_id is not None:
            by_release.setdefault(entry.model_release_id, []).append(change)
    for release_id, changes in by_release.items():
        for plan in plans_for(session, release_id):
            owns, reaches = plan.seeds(changes)
            if owns or reaches:
                _insert_events(session, workspace_key, release_id, plan, owns, reaches)
    checkpoint.position = end
    checkpoint.updated_at = datetime.now(UTC)
    session.commit()
    return True


def _rows(name: str, columns: Sequence[tuple[str, Any, list[Any]]]) -> Any:
    """Parallel arrays as a CTE: one parameter per column, whatever the rows."""
    arrays = [literal(values, ARRAY(type_)) for _label, type_, values in columns]
    rows = func.unnest(*arrays).table_valued(*(column(label, type_) for label, type_, _ in columns))
    derived = rows.render_derived(name=f"{name}_rows")
    return select(*(derived.c[label] for label, _, _ in columns)).cte(name)


def _insert_events(
    session: Session,
    workspace_key: str,
    release_id: int,
    plan: EventPlan,
    owns: Sequence[Own],
    reaches: Sequence[Reach],
) -> None:
    flat = _event_rows(workspace_key, owns, reaches)
    decided = union_all(*(_decided(flat, event) for event in plan.events)).subquery("decided")
    entry = AuditEvent
    definition = plan.definition
    digest = func.md5(
        func.concat(entry.event_id, ":", plan.store_key, ":", decided.c.event_key, ":", decided.c.object_id)
    )
    rows = select(
        cast(cast(digest, UUID), String(36)),
        literal(workspace_key, String),
        literal(plan.store_key, String),
        literal(definition.contractVersion, Integer),
        decided.c.event_key,
        decided.c.position,
        func.row_number().over(
            partition_by=decided.c.position, order_by=(decided.c.event_key, decided.c.object_id)
        ),
        decided.c.change,
        decided.c.object_id,
        decided.c.object_type_key,
        case(plan.public_names, value=decided.c.object_type_key, else_=decided.c.object_type_key),
        func.to_json(decided.c.changed),
        entry.cause_kind,
        entry.cause_id,
        entry.occurred_at,
        literal(release_id, Integer),
    ).join(entry, and_(entry.workspace_key == workspace_key, entry.feed_position == decided.c.position))
    session.execute(
        insert(ConsumerEvent).from_select(
            [
                "event_id",
                "workspace_key",
                "consumer_api",
                "contract_version",
                "event_key",
                "position",
                "ordinal",
                "change",
                "object_id",
                "object_type_key",
                "object_type",
                "changed",
                "cause_kind",
                "cause_id",
                "occurred_at",
                "model_release_id",
            ],
            rows,
        )
    )


def _event_rows(workspace_key: str, owns: Sequence[Own], reaches: Sequence[Reach]) -> Any:
    """One row per object, change and output (an output-less row for an own change without one):
    the own rows as given, the reached objects found from each reach's start."""
    own = _rows(
        "own",
        [
            ("position", Integer, [row.position for row in owns for _ in _outputs(row.outputs)]),
            ("object_id", String, [row.object_id for row in owns for _ in _outputs(row.outputs)]),
            ("change", String, [row.change for row in owns for _ in _outputs(row.outputs)]),
            ("type_key", String, [row.type_key for row in owns for _ in _outputs(row.outputs)]),
            ("previous_type_key", String, [row.previous_type_key for row in owns for _ in _outputs(row.outputs)]),
            ("output", String, [output for row in owns for output in _outputs(row.outputs)]),
        ],
    )
    seeds = _rows(
        "reach",
        [
            ("idx", Integer, list(range(len(reaches)))),
            ("position", Integer, [row.position for row in reaches]),
            ("record_id", String, [row.record_id for row in reaches]),
            ("base", String, [row.base for row in reaches]),
            ("relation", String, [row.relation for row in reaches]),
            ("direction", String, [row.direction for row in reaches]),
        ],
    )
    outputs = _rows(
        "reach_output",
        [
            ("idx", Integer, [index for index, row in enumerate(reaches) for _ in row.outputs]),
            ("output", String, [output for row in reaches for output in row.outputs]),
        ],
    )
    child, start, step = aliased(RdmObject), aliased(RdmObject), aliased(RdmObject)
    below = (
        select(seeds.c.idx, start.id.label("item"))
        .join(start, start.parent_object_id == seeds.c.record_id)
        .where(seeds.c.base.in_([DESCENDANTS, SELF_AND_DESCENDANTS]))
        .cte("reach_below", recursive=True)
    )
    below = below.union_all(select(below.c.idx, step.id).join(step, step.parent_object_id == below.c.item))
    items = union_all(
        select(seeds.c.idx, seeds.c.record_id.label("item")).where(seeds.c.base.in_([SELF, SELF_AND_DESCENDANTS])),
        select(seeds.c.idx, child.id).join(child, child.parent_object_id == seeds.c.record_id).where(
            seeds.c.base == CHILDREN
        ),
        select(below.c.idx, below.c.item),
    ).cte("reach_items")
    related = aliased(ObjectRelation)
    owners = union_all(
        select(items.c.idx, items.c.item.label("owner"))
        .join(seeds, seeds.c.idx == items.c.idx)
        .where(seeds.c.relation.is_(None)),
        select(items.c.idx, related.from_object_id)
        .join(seeds, seeds.c.idx == items.c.idx)
        .join(
            related,
            and_(related.relation_type_key == seeds.c.relation, related.to_object_id == items.c.item),
        )
        .where(seeds.c.direction == "outgoing"),
        select(items.c.idx, related.to_object_id)
        .join(seeds, seeds.c.idx == items.c.idx)
        .join(
            related,
            and_(related.relation_type_key == seeds.c.relation, related.from_object_id == items.c.item),
        )
        .where(seeds.c.direction == "incoming"),
    ).cte("reach_owners")
    reached = aliased(RdmObject)
    return union_all(
        select(own.c.position, own.c.object_id, own.c.change, own.c.type_key, own.c.previous_type_key, own.c.output),
        select(
            seeds.c.position,
            reached.id,
            literal("updated", String),
            reached.object_type_key,
            null().cast(String),
            outputs.c.output,
        )
        .select_from(owners)
        .join(seeds, seeds.c.idx == owners.c.idx)
        .join(outputs, outputs.c.idx == owners.c.idx)
        .join(reached, and_(reached.id == owners.c.owner, reached.workspace_key == workspace_key)),
    ).cte("event_rows")


def _outputs(outputs: Sequence[str]) -> Iterable[str | None]:
    return outputs or (None,)


def _decided(flat: Any, event: Any) -> Any:
    """The events of one declared event: each object's merged change at a position, told as the
    kind the event takes (C-D83 for a type change) with the watched outputs it changed."""
    types = list(event.objectTypes)
    changes = set(event.changes)
    watch = None if event.watch is None else [*event.watch.fields, *event.watch.projections]
    kept = flat.c.output.is_not(None) if watch is None else flat.c.output.in_(watch)
    own = flat.c.change != "updated"
    merged = (
        select(
            flat.c.position,
            flat.c.object_id,
            func.coalesce(func.max(flat.c.change).filter(own), "updated").label("change"),
            func.coalesce(func.max(flat.c.type_key).filter(own), func.max(flat.c.type_key)).label("type_key"),
            func.max(flat.c.previous_type_key).label("previous_type_key"),
            func.coalesce(
                func.array_agg(aggregate_order_by(distinct(flat.c.output), flat.c.output)).filter(kept),
                literal_column("'{}'::varchar[]"),
            ).label("seen"),
        )
        .group_by(flat.c.position, flat.c.object_id)
        .subquery()
    )
    exposed, was_exposed = merged.c.type_key.in_(types), merged.c.previous_type_key.in_(types)
    seen = func.cardinality(merged.c.seen) > 0
    retyped = merged.c.change == "reclassified"
    whens = []
    if "created" in changes:
        whens += [((merged.c.change == "created") & exposed, "created"), (retyped & exposed & ~was_exposed, "created")]
    if "deleted" in changes:
        whens += [((merged.c.change == "deleted") & exposed, "deleted"), (retyped & was_exposed & ~exposed, "deleted")]
    if "updated" in changes:
        whens += [((merged.c.change == "updated") & exposed & seen, "updated"), (retyped & exposed & was_exposed & seen, "updated")]
    kind = case(*whens, else_=null())
    return select(
        merged.c.position,
        merged.c.object_id,
        literal(event.key, String).label("event_key"),
        kind.label("change"),
        case((retyped & ~exposed, merged.c.previous_type_key), else_=merged.c.type_key).label("object_type_key"),
        case((kind == "updated", merged.c.seen), else_=literal_column("'{}'::varchar[]")).label("changed"),
    ).where(kind.is_not(None))
