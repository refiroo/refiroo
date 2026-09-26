"""Draft and history reads in SQL (Base 0.8 S2).

A revision's objects and relations are its own rows. A draft's are its base rows (a revision or a
private current-live base) that no draft row replaces, plus its non-deleted draft rows; any draft
row, including a tombstone, hides the base row with the same public ID. Every read here states that
rule as one statement, so a page or a record costs its own rows rather than the whole membership.

Validation, activation and draft writes still resolve the whole graph through
``workspace_revisions.effective_draft_membership``; they need all of it by definition.
"""

from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass
from typing import Any, Literal

from sqlalchemy import Row, Select, String, and_, case, exists, literal, select, union_all
from sqlalchemy.orm import Session, aliased
from sqlalchemy.sql.selectable import Subquery

from ..errors import api_error
from ..models.database import (
    SnapshotAttributeValue,
    WorkspaceDraft,
    WorkspaceDraftBase,
    WorkspaceDraftBaseObject,
    WorkspaceDraftBaseRelation,
    WorkspaceDraftObject,
    WorkspaceDraftRelation,
    WorkspaceRevision,
    WorkspaceRevisionObject,
    WorkspaceRevisionRelation,
)
from ..models.schema import EngineModel
from .objects import (
    ObjectColumns,
    ObjectQuery,
    _query_error,
    get_object_type,
    refine_object_query,
    top_level_filter,
    validate_application_object_type,
)
from .pagination import Keyed, Overlay, text_key

# Draft and history rows record no timestamps; a query on them is refused, not matched as empty.
UNRECORDED_TIMESTAMPS = {"createdAt": "Created", "updatedAt": "Updated"}


# One part of a draft's union: every base row ("base"), the base rows its draft rows replace or
# delete ("replaced"), its non-deleted draft rows ("added"), or the effective rows: base less
# replaced, plus added.
DraftPart = Literal["effective", "base", "replaced", "added"]


@dataclass(frozen=True)
class SnapshotBase:
    """The immutable rows a draft starts from: a revision or a private current-live base."""

    objects: Any
    relations: Any
    owner_column: str
    owner_id: str


@dataclass(frozen=True)
class SnapshotContext:
    """One draft or revision read context."""

    kind: Literal["draft", "revision"]
    id: str
    workspace_key: str
    draft: WorkspaceDraft | None
    base: SnapshotBase | None


def draft_context(session: Session, draft_id: str) -> SnapshotContext:
    draft = session.scalar(select(WorkspaceDraft).where(WorkspaceDraft.id == draft_id))
    if draft is None:
        raise api_error(404, "workspace_draft_not_found", f"Workspace draft '{draft_id}' not found")
    base = None
    if draft.derived_from_revision_id is not None:
        revision = session.scalar(
            select(WorkspaceRevision).where(WorkspaceRevision.id == draft.derived_from_revision_id)
        )
        if revision is None or revision.workspace_key != draft.workspace_key:
            raise api_error(
                409,
                "workspace_draft_base_invalid",
                "Workspace draft base revision is missing or belongs to another workspace",
            )
        base = SnapshotBase(
            WorkspaceRevisionObject, WorkspaceRevisionRelation, "revision_id", revision.id
        )
    if draft.base_id is not None:
        current_live = session.get(WorkspaceDraftBase, draft.base_id)
        if current_live is None or current_live.workspace_key != draft.workspace_key:
            raise api_error(
                409,
                "workspace_draft_base_invalid",
                "Workspace draft current-live base is missing or belongs to another workspace",
            )
        base = SnapshotBase(
            WorkspaceDraftBaseObject, WorkspaceDraftBaseRelation, "base_id", current_live.id
        )
    return SnapshotContext("draft", draft.id, draft.workspace_key, draft, base)


def revision_context(session: Session, revision_id: str) -> SnapshotContext:
    revision = session.scalar(select(WorkspaceRevision).where(WorkspaceRevision.id == revision_id))
    if revision is None:
        raise api_error(404, "workspace_revision_not_found", "Workspace revision not found")
    return SnapshotContext(
        "revision",
        revision.id,
        revision.workspace_key,
        None,
        SnapshotBase(WorkspaceRevisionObject, WorkspaceRevisionRelation, "revision_id", revision.id),
    )


def object_projection(
    context: SnapshotContext,
    *,
    object_type_key: str | None = None,
    application_key: str | None = None,
    parent_object_id: str | None = None,
    top_level: bool = False,
    object_ids: Iterable[str] | None = None,
    part: DraftPart = "effective",
) -> Subquery:
    """The context's effective object rows, narrowed inside each arm so indexes apply.

    ``values_owner_id`` names the owner of each row's typed values in ``snapshot_attribute_values``.
    ``part`` selects one part of a draft's union instead (see :data:`DraftPart`).
    """
    ids = list(object_ids) if object_ids is not None else None

    def arm(entity: Any, owner_id: str, *conditions: Any) -> Any:
        narrowing = []
        if object_type_key is not None:
            narrowing.append(entity.object_type_key == object_type_key)
        if application_key:
            narrowing.append(entity.application_key == application_key)
        if parent_object_id:
            narrowing.append(entity.parent_object_id == parent_object_id)
        if top_level:
            narrowing.append(entity.parent_object_id.is_(None))
        if part == "replaced":
            narrowing = [_unindexed(condition) for condition in narrowing]
        where = [*conditions, *narrowing]
        if ids is not None:
            where.append(entity.object_id.in_(ids))
        return select(
            entity.object_id,
            entity.application_key,
            entity.object_type_key,
            entity.name,
            entity.parent_object_id,
            entity.attributes,
            entity.version,
            literal(owner_id, String).label("values_owner_id"),
        ).where(*where)

    return _effective(
        context,
        WorkspaceDraftObject,
        "object_id",
        arm,
        lambda base: getattr(base.objects, base.owner_column) == base.owner_id,
        lambda base: base.objects,
        name="snapshot_objects",
        part=part,
    )


def relation_projection(
    context: SnapshotContext,
    *,
    object_id: str | None = None,
    direction: str = "both",
    relation_type_keys: Sequence[str] | None = None,
    relation_ids: Iterable[str] | None = None,
) -> Subquery:
    """The context's effective relation rows touching ``object_id`` in ``direction``.

    With ``object_id``, rows carry ``related_id``, the record at the other end. Each end is its own arm, so the (owner, from) and (owner, to) indexes serve it; one ``OR`` over
    both ends would read every relation of the owner.
    """
    ids = list(relation_ids) if relation_ids is not None else None

    def arm(entity: Any, _owner_id: str, *conditions: Any) -> list[Any]:
        where = list(conditions)
        if relation_type_keys:
            where.append(entity.relation_type_key.in_(relation_type_keys))
        if ids is not None:
            where.append(entity.relation_id.in_(ids))
        # Each end's arm also names the record at the other end, as a plain column to join on.
        ends: list[tuple[list[Any], list[Any]]] = [([], [])]
        if object_id is not None:
            ends = []
            if direction in {"outgoing", "both"}:
                ends.append(
                    ([entity.from_object_id == object_id], [entity.to_object_id.label("related_id")])
                )
            if direction in {"incoming", "both"}:
                # A relation from the record to itself is already in the outgoing arm.
                incoming = [entity.to_object_id == object_id]
                if direction == "both":
                    incoming.append(entity.from_object_id != object_id)
                ends.append((incoming, [entity.from_object_id.label("related_id")]))
        return [
            select(
                entity.relation_id,
                entity.relation_type_key,
                entity.from_object_id,
                entity.to_object_id,
                entity.attributes,
                entity.version,
                *related,
            ).where(*where, *end)
            for end, related in ends
        ]

    return _effective(
        context,
        WorkspaceDraftRelation,
        "relation_id",
        arm,
        lambda base: getattr(base.relations, base.owner_column) == base.owner_id,
        lambda base: base.relations,
        name="snapshot_relations",
    )


def _unindexed(condition: Any) -> Any:
    """``condition`` as a term no index serves, so the planner looks rows up by another one."""
    return case((condition, 1), else_=0) == 1


def _effective(
    context, overlay, identity, arm, base_filter, base_entity, *, name, part: DraftPart = "effective"
) -> Subquery:
    """Union the context's arms; ``arm`` returns one select or a list of them per source."""

    def selects(result: Any) -> list[Any]:
        return result if isinstance(result, list) else [result]

    base = context.base
    arms = []
    if context.kind == "revision":
        arms.extend(selects(arm(base_entity(base), base.owner_id, base_filter(base))))
    else:
        if base is not None and part != "added":
            entity = base_entity(base)
            overridden = select(getattr(overlay, identity)).where(overlay.draft_id == context.id)
            conditions = [base_filter(base)]
            if part == "effective":
                conditions.append(~getattr(entity, identity).in_(overridden))
            elif part == "replaced":
                # Driven by the draft's IDs: the arm's other terms would otherwise let the
                # planner walk the base's type or parent index across every base row.
                conditions = [
                    _unindexed(conditions[0]),
                    getattr(entity, identity).in_(overridden),
                ]
            arms.extend(selects(arm(entity, base.owner_id, *conditions)))
        if part in {"effective", "added"}:
            arms.extend(
                selects(
                    arm(
                        overlay,
                        context.id,
                        overlay.draft_id == context.id,
                        overlay.is_deleted.is_(False),
                    )
                )
            )
    return (union_all(*arms) if len(arms) > 1 else arms[0]).subquery(name)


@dataclass(frozen=True)
class EffectiveRecord:
    """The context's effective record for an ID expression, read through outer joins.

    Any draft row, a tombstone included, hides the base row, and a missing or deleted record reads
    as null. Use it where a statement lists records it names by ID, such as the other end of each
    relation; a whole object page reads ``object_projection`` instead, whose union arms a join
    would multiply.

    ``present`` keeps only rows whose record exists. It is a ``CASE`` on purpose: SQLite turns an
    outer join whose row a ``WHERE`` term requires (``name IS NOT NULL``) into an inner join it may
    reorder, and then scans every record of the owner to probe the listed rows. A ``CASE`` keeps
    the outer join, so the listed rows stay the outer loop.
    """

    joins: tuple[tuple[Any, Any], ...]
    read: Callable[[str], Any]
    values_owner: Any
    present: Any

    def join(self, statement: Select[Any]) -> Select[Any]:
        for target, onclause in self.joins:
            statement = statement.outerjoin(target, onclause)
        return statement

    def column(self, name: str) -> Any:
        return self.read(name)


def effective_record(context: SnapshotContext, object_id: Any) -> EffectiveRecord:
    """Outer joins to the one base row and the one draft row of ``object_id``, on unique keys."""
    base = context.base
    if context.kind == "revision":
        row = aliased(base.objects)
        return EffectiveRecord(
            ((row, and_(getattr(row, base.owner_column) == base.owner_id, row.object_id == object_id)),),
            lambda name: getattr(row, name),
            literal(base.owner_id, String),
            case((row.object_id.is_(None), False), else_=True),
        )
    draft = aliased(WorkspaceDraftObject)
    joins: list[tuple[Any, Any]] = [
        (draft, and_(draft.draft_id == context.id, draft.object_id == object_id))
    ]
    in_draft = draft.object_id.is_not(None)
    live_in_draft = draft.is_deleted.is_(False)

    def draft_value(name: str) -> Any:
        return case((live_in_draft, getattr(draft, name)))

    if base is None:
        return EffectiveRecord(
            tuple(joins),
            draft_value,
            literal(context.id, String),
            case((in_draft, live_in_draft), else_=False),
        )
    row = aliased(base.objects)
    joins.append(
        (
            row,
            and_(
                getattr(row, base.owner_column) == base.owner_id,
                row.object_id == object_id,
                draft.object_id.is_(None),
            ),
        )
    )
    return EffectiveRecord(
        tuple(joins),
        lambda name: case((in_draft, draft_value(name)), else_=getattr(row, name)),
        case((in_draft, literal(context.id, String)), else_=literal(base.owner_id, String)),
        case((in_draft, live_in_draft), else_=row.object_id.is_not(None)),
    )


def effective_object_value(context: SnapshotContext, object_id: Any, column: str) -> tuple[Any, Any]:
    """One column of the context's effective record ``object_id`` (an expression), and the owner of
    its typed values, as correlated scalar lookups on the unique (owner, object) keys.

    Any draft row, a tombstone included, hides the base row; a missing or deleted record reads as
    null. A lookup runs once per row of the statement it sits in, whatever the planner prefers: use
    it for few rows, such as an ancestor walk, and :func:`effective_record` for a list.
    """
    base = context.base
    # Explicit correlation: the lookups may sit several subqueries below the statement that names
    # ``object_id``, where automatic correlation would cross-join that statement instead.

    def base_lookup() -> tuple[Any, Any]:
        entity = base.objects
        value = (
            select(getattr(entity, column))
            .where(getattr(entity, base.owner_column) == base.owner_id, entity.object_id == object_id)
            .correlate_except(entity)
            .scalar_subquery()
        )
        return value, literal(base.owner_id, String)

    if context.kind == "revision":
        return base_lookup()
    overlay = WorkspaceDraftObject
    in_draft = (overlay.draft_id == context.id, overlay.object_id == object_id)
    draft_value = (
        select(getattr(overlay, column))
        .where(*in_draft, overlay.is_deleted.is_(False))
        .correlate_except(overlay)
        .scalar_subquery()
    )
    draft_owner = literal(context.id, String)
    if base is None:
        return draft_value, draft_owner
    base_value, base_owner = base_lookup()
    overridden = exists(select(overlay.sequence_id).where(*in_draft).correlate_except(overlay))
    return (
        case((overridden, draft_value), else_=base_value),
        case((overridden, draft_owner), else_=base_owner),
    )


def find_objects(session: Session, context: SnapshotContext, object_ids: Iterable[str]) -> dict[str, Row]:
    ids = list(dict.fromkeys(object_ids))
    if not ids:
        return {}
    projection = object_projection(context, object_ids=ids)
    return {row.object_id: row for row in session.execute(select(projection))}


def find_object(
    session: Session, context: SnapshotContext, object_id: str, object_type_key: str | None = None
) -> Row | None:
    row = find_objects(session, context, [object_id]).get(object_id)
    if row is None or (object_type_key is not None and row.object_type_key != object_type_key):
        return None
    return row


def find_relation(session: Session, context: SnapshotContext, relation_id: str) -> Row | None:
    projection = relation_projection(context, relation_ids=[relation_id])
    return session.execute(select(projection)).first()


def object_path(session: Session, context: SnapshotContext, item: Any) -> list[dict[str, Any]]:
    """The record's ancestor path, one lookup per level: its cost is the hierarchy depth."""
    path, seen, current = [], set(), item
    while current is not None and current.object_id not in seen:
        seen.add(current.object_id)
        path.append(
            {"id": current.object_id, "name": current.name, "objectTypeKey": current.object_type_key}
        )
        parent_id = current.parent_object_id
        current = find_object(session, context, parent_id) if parent_id else None
    path.reverse()
    return path


def object_paths(
    session: Session, context: SnapshotContext, items: Iterable[Any]
) -> dict[str, list[dict[str, Any]]]:
    """Root-first ancestor paths for a page of records, as live pages return them.

    Parents resolve level by level for the whole batch, so a page costs one lookup per hierarchy
    level rather than one per record and level.
    """
    items = list(items)
    paths = {
        item.object_id: [
            {"id": item.object_id, "name": item.name, "objectTypeKey": item.object_type_key}
        ]
        for item in items
    }
    visited = {item.object_id: {item.object_id} for item in items}
    frontier = {item.object_id: item.parent_object_id for item in items if item.parent_object_id}
    while frontier:
        parents = find_objects(session, context, set(frontier.values()))
        next_frontier: dict[str, str] = {}
        for object_id, parent_id in frontier.items():
            parent = parents.get(parent_id)
            if parent is None or parent.object_id in visited[object_id]:
                continue
            visited[object_id].add(parent.object_id)
            paths[object_id].append(
                {"id": parent.object_id, "name": parent.name, "objectTypeKey": parent.object_type_key}
            )
            if parent.parent_object_id:
                next_frontier[object_id] = parent.parent_object_id
        frontier = next_frontier
    return {object_id: list(reversed(path)) for object_id, path in paths.items()}


def snapshot_object_columns(projection: Subquery) -> ObjectColumns:
    values = SnapshotAttributeValue
    return ObjectColumns(
        source=projection,
        id=projection.c.object_id,
        name=projection.c.name,
        values=values,
        value_match=lambda values: (
            values.owner_id == projection.c.values_owner_id,
            values.object_id == projection.c.object_id,
        ),
        builtin={"id": projection.c.object_id, "name": projection.c.name},
        object_type=projection.c.object_type_key,
        tiebreak=lambda descending: text_key(
            "id", projection.c.object_id, "object_id", descending=descending
        ),
    )


def build_snapshot_object_query(
    model: EngineModel,
    context: SnapshotContext,
    *,
    object_type_key: str,
    application_key: str | None,
    parent_object_id: str | None,
    search: str | None,
    sort: str | None,
    field_filters: list[tuple[str, str, str]],
    top_level: bool = False,
) -> ObjectQuery:
    """The draft or revision object collection query, with the same contract as a live one."""
    object_type = get_object_type(model, object_type_key)
    if application_key:
        validate_application_object_type(model, application_key, object_type_key)
    for field, operator, _raw in field_filters:
        if field in UNRECORDED_TIMESTAMPS:
            _query_error(
                "invalid_filter",
                f"{UNRECORDED_TIMESTAMPS[field]} is not recorded in drafts or history",
                f"filter.{field}.{operator}",
            )
    sort_field = (sort or "").removeprefix("-")
    if sort_field in UNRECORDED_TIMESTAMPS:
        _query_error(
            "invalid_sort",
            f"{UNRECORDED_TIMESTAMPS[sort_field]} is not recorded in drafts or history",
            "sort",
        )

    def refine(part: DraftPart) -> tuple[Any, Any, Any, Any]:
        projection = object_projection(
            context,
            object_type_key=object_type_key,
            application_key=application_key,
            parent_object_id=parent_object_id,
            top_level=top_level,
            part=part,
        )
        return refine_object_query(
            model,
            snapshot_object_columns(projection),
            select(projection),
            object_types=(object_type,),
            search=search,
            sort=sort,
            field_filters=field_filters,
        )

    statement, keys, seek, normalized_filters = refine("effective")
    # A draft over a base resolves position reads in the base's index (Base 0.8 S4R6).
    overlay = None
    if context.kind == "draft" and context.base is not None:
        parts = {part: Keyed(*refine(part)[:2]) for part in ("base", "replaced", "added")}
        overlay = Overlay(parts["base"], parts["replaced"], parts["added"])
    owner = "draftId" if context.kind == "draft" else "revisionId"
    return ObjectQuery(
        statement=statement,
        keys=keys,
        filters={
            owner: context.id,
            "applicationKey": application_key,
            "objectTypeKey": object_type_key,
            "parentObjectId": parent_object_id,
            "search": search,
            "typedFilters": normalized_filters,
            **top_level_filter(top_level),
        },
        seek=seek,
        overlay=overlay,
    )


def object_scope(context: SnapshotContext) -> str:
    return "objects-draft" if context.kind == "draft" else "objects-revision"
