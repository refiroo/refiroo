"""Change set and history reads in SQL (Base 0.8 S2).

A publication's objects and relations are its own rows. A change set's are its base rows (a publication or a
private current-live base) that no change set row replaces, plus its non-deleted change set rows; any change set
row, including a tombstone, hides the base row with the same public ID. Every read here states that
rule as one statement, so a page or a record costs its own rows rather than the whole membership.

Validation and publishing still resolve the whole graph through
``change_sets.access.effective_change_set_membership``; they need all of it by definition. Change set writes
check only the records they touch, through ``engine/records/context.py`` (S2b).
"""

from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass, replace
from datetime import date
from typing import Any, Literal

from sqlalchemy import (
    Row,
    Select,
    String,
    and_,
    case,
    exists,
    literal,
    select,
    union_all,
)
from sqlalchemy.orm import Session, aliased
from sqlalchemy.sql.selectable import Subquery

from ...common.pagination import Keyed, Overlay, text_key
from ...errors import api_error
from ...models.database import (
    ChangeSet,
    ChangeSetBase,
    ChangeSetBaseObject,
    ChangeSetBaseRelation,
    ChangeSetObject,
    ChangeSetRelation,
    Publication,
    PublicationObject,
    PublicationRelation,
    SnapshotAttributeValue,
)
from ...models.schema import EngineModel, ObjectTypeDefinition
from ...models.search_index import MIN_INDEXED_LENGTH, SNAPSHOT_VALUES
from ..records.rules import get_object_type, object_type_changed, validate_application_object_type
from .object_query import (
    ObjectColumns,
    ObjectQuery,
    as_of_filter,
    bounded_match,
    escape_like,
    indexed_value_match,
    name_contains,
    query_error,
    refine_object_query,
    search_candidates,
    searchable_attribute_keys,
    top_level_filter,
)

# Change set and history rows record no timestamps; a query on them is refused, not matched as empty.
UNRECORDED_TIMESTAMPS = {"createdAt": "Created", "updatedAt": "Updated"}


# One part of a change set's union: every base row ("base"), the base rows its change set rows replace or
# delete ("replaced"), its non-deleted change set rows ("added"), or the effective rows: base less
# replaced, plus added.
ChangeSetPart = Literal["effective", "base", "replaced", "added"]


@dataclass(frozen=True)
class SnapshotBase:
    """The immutable rows a change set starts from: a publication or a private current-live base."""

    objects: Any
    relations: Any
    owner_column: str
    owner_id: str


@dataclass(frozen=True)
class SnapshotContext:
    """One change set or publication read context."""

    kind: Literal["change_set", "publication"]
    id: str
    workspace_key: str
    change_set: ChangeSet | None
    base: SnapshotBase | None


def change_set_context(session: Session, change_set_id: str) -> SnapshotContext:
    change_set = session.scalar(select(ChangeSet).where(ChangeSet.id == change_set_id))
    if change_set is None:
        raise api_error(404, "change_set_not_found", f"Change set '{change_set_id}' not found")
    base = None
    if change_set.derived_from_publication_id is not None:
        publication = session.scalar(
            select(Publication).where(Publication.id == change_set.derived_from_publication_id)
        )
        if publication is None or publication.workspace_key != change_set.workspace_key:
            raise api_error(
                409,
                "change_set_base_invalid",
                "Change set base publication is missing or belongs to another workspace",
            )
        base = SnapshotBase(
            PublicationObject, PublicationRelation, "publication_id", publication.id
        )
    if change_set.base_id is not None:
        current_live = session.get(ChangeSetBase, change_set.base_id)
        if current_live is None or current_live.workspace_key != change_set.workspace_key:
            raise api_error(
                409,
                "change_set_base_invalid",
                "Change set current-live base is missing or belongs to another workspace",
            )
        base = SnapshotBase(
            ChangeSetBaseObject, ChangeSetBaseRelation, "base_id", current_live.id
        )
    return SnapshotContext("change_set", change_set.id, change_set.workspace_key, change_set, base)


def publication_context(session: Session, publication_id: str) -> SnapshotContext:
    publication = session.scalar(select(Publication).where(Publication.id == publication_id))
    if publication is None:
        raise api_error(404, "publication_not_found", "Publication not found")
    return SnapshotContext(
        "publication",
        publication.id,
        publication.workspace_key,
        None,
        SnapshotBase(PublicationObject, PublicationRelation, "publication_id", publication.id),
    )


def object_projection(
    context: SnapshotContext,
    *,
    object_type_key: str | None = None,
    object_type_keys: Iterable[str] | None = None,
    application_key: str | None = None,
    parent_object_id: str | None = None,
    parent_object_ids: Iterable[str] | None = None,
    top_level: bool = False,
    object_ids: Iterable[str] | None = None,
    name_search: str | None = None,
    part: ChangeSetPart = "effective",
) -> Subquery:
    """The context's effective object rows, narrowed inside each arm so indexes apply.

    ``object_type_keys`` narrows to several types, as ``object_type_key`` does to one.
    ``name_search`` keeps rows whose name contains it.

    ``values_owner_id`` names the owner of each row's typed values in ``snapshot_attribute_values``;
    ``row_sequence_id`` is the row's key in its own table, which its type and parent indexes hold.
    ``part`` selects one part of a change set's union instead (see :data:`ChangeSetPart`).
    """
    ids = list(object_ids) if object_ids is not None else None
    parents = list(parent_object_ids) if parent_object_ids is not None else None
    types = sorted(object_type_keys) if object_type_keys is not None else None

    def arm(entity: Any, owner_id: str, *conditions: Any) -> Any:
        narrowing = []
        if object_type_key is not None:
            narrowing.append(entity.object_type_key == object_type_key)
        if types is not None:
            narrowing.append(entity.object_type_key.in_(types))
        if application_key:
            narrowing.append(entity.application_key == application_key)
        if parent_object_id:
            narrowing.append(entity.parent_object_id == parent_object_id)
        if parents is not None:
            narrowing.append(entity.parent_object_id.in_(parents))
        if top_level:
            narrowing.append(entity.parent_object_id.is_(None))
        first = [name_contains(entity.name, name_search)] if name_search else []
        where = [*first, *conditions, *narrowing]
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
            entity.sequence_id.label("row_sequence_id"),
        ).where(*where)

    return _effective(
        context,
        ChangeSetObject,
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
    endpoint_ids: Iterable[str] | None = None,
) -> Subquery:
    """The context's effective relation rows touching ``object_id`` in ``direction``.

    With ``object_id``, rows carry ``related_id``, the record at the other end. Each end is its own arm, so the (owner, from) and (owner, to) indexes serve it; one ``OR`` over
    both ends would read every relation of the owner. ``endpoint_ids`` does the same for a set of
    records, without ``related_id``.
    """
    ids = list(relation_ids) if relation_ids is not None else None
    endpoints = list(endpoint_ids) if endpoint_ids is not None else None

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
        elif endpoints is not None:
            ends = []
            if direction in {"outgoing", "both"}:
                ends.append(([entity.from_object_id.in_(endpoints)], []))
            if direction in {"incoming", "both"}:
                # A relation between two listed records is already in the outgoing arm.
                incoming = [entity.to_object_id.in_(endpoints)]
                if direction == "both":
                    incoming.append(~entity.from_object_id.in_(endpoints))
                ends.append((incoming, []))
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
        ChangeSetRelation,
        "relation_id",
        arm,
        lambda base: getattr(base.relations, base.owner_column) == base.owner_id,
        lambda base: base.relations,
        name="snapshot_relations",
    )


def _effective(
    context, overlay, identity, arm, base_filter, base_entity, *, name, part: ChangeSetPart = "effective"
) -> Subquery:
    """Union the context's arms; ``arm`` returns one select or a list of them per source."""

    def selects(result: Any) -> list[Any]:
        return result if isinstance(result, list) else [result]

    base = context.base
    arms = []
    if context.kind == "publication":
        arms.extend(selects(arm(base_entity(base), base.owner_id, base_filter(base))))
    else:
        if base is not None and part != "added":
            entity = base_entity(base)
            overridden = select(getattr(overlay, identity)).where(overlay.change_set_id == context.id)
            conditions = [base_filter(base)]
            if part == "effective":
                # NOT EXISTS, not NOT IN: an anti-join on the (change set, record) key, which NOT
                # IN's null semantics would rule out.
                conditions.append(
                    ~exists().where(
                        overlay.change_set_id == context.id,
                        getattr(overlay, identity) == getattr(entity, identity),
                    )
                )
            elif part == "replaced":
                # The rows the change set replaces, by its IDs. On base rows without statistics yet
                # (a base just captured) the planner may read every base row first; an ID array
                # avoids that but hides the set's size from the planner (POSTGRESQL_BUDGETS.md).
                conditions.append(getattr(entity, identity).in_(overridden))
            arms.extend(selects(arm(entity, base.owner_id, *conditions)))
        if part in {"effective", "added"}:
            arms.extend(
                selects(
                    arm(
                        overlay,
                        context.id,
                        overlay.change_set_id == context.id,
                        overlay.is_deleted.is_(False),
                    )
                )
            )
    return (union_all(*arms) if len(arms) > 1 else arms[0]).subquery(name)


@dataclass(frozen=True)
class EffectiveRecord:
    """The context's effective record for an ID expression, read through outer joins.

    Any change set row, a tombstone included, hides the base row, and a missing or deleted record reads
    as null. Use it where a statement lists records it names by ID, such as the other end of each
    relation; a whole object page reads ``object_projection`` instead, whose union arms a join
    would multiply.

    ``present`` keeps only rows whose record exists.
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
    """Outer joins to the one base row and the one change set row of ``object_id``, on unique keys."""
    base = context.base
    if context.kind == "publication":
        row = aliased(base.objects)
        return EffectiveRecord(
            ((row, and_(getattr(row, base.owner_column) == base.owner_id, row.object_id == object_id)),),
            lambda name: getattr(row, name),
            literal(base.owner_id, String),
            row.object_id.is_not(None),
        )
    change_set = aliased(ChangeSetObject)
    joins: list[tuple[Any, Any]] = [
        (change_set, and_(change_set.change_set_id == context.id, change_set.object_id == object_id))
    ]
    in_change_set = change_set.object_id.is_not(None)
    live_in_change_set = change_set.is_deleted.is_(False)

    def change_set_value(name: str) -> Any:
        return case((live_in_change_set, getattr(change_set, name)))

    if base is None:
        return EffectiveRecord(
            tuple(joins),
            change_set_value,
            literal(context.id, String),
            case((in_change_set, live_in_change_set), else_=False),
        )
    row = aliased(base.objects)
    joins.append(
        (
            row,
            and_(
                getattr(row, base.owner_column) == base.owner_id,
                row.object_id == object_id,
                change_set.object_id.is_(None),
            ),
        )
    )
    return EffectiveRecord(
        tuple(joins),
        lambda name: case((in_change_set, change_set_value(name)), else_=getattr(row, name)),
        case((in_change_set, literal(context.id, String)), else_=literal(base.owner_id, String)),
        case((in_change_set, live_in_change_set), else_=row.object_id.is_not(None)),
    )


def effective_object_value(context: SnapshotContext, object_id: Any, column: str) -> tuple[Any, Any]:
    """One column of the context's effective record ``object_id`` (an expression), and the owner of
    its typed values, as correlated scalar lookups on the unique (owner, object) keys.

    Any change set row, a tombstone included, hides the base row; a missing or deleted record reads as
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

    if context.kind == "publication":
        return base_lookup()
    overlay = ChangeSetObject
    in_change_set = (overlay.change_set_id == context.id, overlay.object_id == object_id)
    change_set_value = (
        select(getattr(overlay, column))
        .where(*in_change_set, overlay.is_deleted.is_(False))
        .correlate_except(overlay)
        .scalar_subquery()
    )
    change_set_owner = literal(context.id, String)
    if base is None:
        return change_set_value, change_set_owner
    base_value, base_owner = base_lookup()
    overridden = exists(select(overlay.sequence_id).where(*in_change_set).correlate_except(overlay))
    return (
        case((overridden, change_set_value), else_=base_value),
        case((overridden, change_set_owner), else_=base_owner),
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
    """The record in the context, or ``None``; found under another type than ``object_type_key``,
    ``409 object_type_changed`` (D42)."""
    row = find_objects(session, context, [object_id]).get(object_id)
    if row is None:
        return None
    if object_type_key is not None and row.object_type_key != object_type_key:
        raise object_type_changed(object_id, row.object_type_key, object_type_key)
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


def snapshot_object_columns(
    projection: Subquery, context: SnapshotContext, *, search_index: bool = True
) -> ObjectColumns:
    """Columns of an object projection; ``search_index`` narrows a search through the index."""
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
        search_values=_value_candidates(projection, context) if search_index else None,
        search_names=_name_candidates(projection, context) if search_index else None,
    )


def _owners(context: SnapshotContext) -> list[tuple[Any, str, str]]:
    """The object tables a context's rows come from, each with its owner column and owner."""
    owners: list[tuple[Any, str, str]] = []
    if context.base is not None:
        owners.append((context.base.objects, context.base.owner_column, context.base.owner_id))
    if context.kind == "change_set":
        owners.append((ChangeSetObject, "change_set_id", context.id))
    return owners


def _name_candidates(projection: Subquery, context: SnapshotContext) -> Callable[[str], Any]:
    """Object rows of the context's owners whose name the trigram index matches a pattern in.

    Compared by ``row_sequence_id``, as the value candidates are: a base row and a change set row
    that share a sequence number may name a row that does not match, and the search's ``LIKE`` on
    the effective row's name drops it.
    """
    owners = _owners(context)

    def search_names(pattern: str) -> Any:
        rows = []
        for entity, owner_column, owner_id in owners:
            row = aliased(entity)
            rows.append(
                select(row.sequence_id).where(
                    getattr(row, owner_column) == owner_id, row.name.ilike(pattern, escape="\\")
                )
            )
        matches = union_all(*rows) if len(rows) > 1 else rows[0]
        return bounded_match(select(matches.subquery().c.sequence_id), projection.c.row_sequence_id.in_(matches))

    return search_names


def _value_candidates(
    projection: Subquery, context: SnapshotContext
) -> Callable[[str, list[str]], Any]:
    """Records with a value of ``attributes`` that the trigram index matches a pattern in.

    Candidates are object rows of the context's owners, compared by ``row_sequence_id``, which
    the type and parent indexes a search walks already hold. A change set's candidates come from its
    base and its own rows alike: a replaced base value, or a base row and a change set row that share a
    sequence number, may name a row that does not match, and the search's ``LIKE`` on the
    effective row's values drops it (D25).
    """
    owners = _owners(context)

    def search_values(pattern: str, attributes: list[str]) -> Any:
        value = aliased(SnapshotAttributeValue)

        def candidates(matches: Select[Any]) -> Any:
            matched = select(value.object_id).where(
                value.sequence_id.in_(matches),
                value.owner_id.in_([owner_id for *_, owner_id in owners]),
                value.attribute_type_key.in_(attributes),
            )
            rows = []
            for entity, owner_column, owner_id in owners:
                row = aliased(entity)
                rows.append(
                    select(row.sequence_id).where(
                        getattr(row, owner_column) == owner_id, row.object_id.in_(matched)
                    )
                )
            return projection.c.row_sequence_id.in_(union_all(*rows) if len(rows) > 1 else rows[0])

        return indexed_value_match(SNAPSHOT_VALUES, pattern, candidates)

    return search_values


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
    search_fields: Sequence[str] | None = None,
    id_filter: Callable[[Any], Any] | None = None,
    as_of: date | None = None,
    session: Session | None = None,
) -> ObjectQuery:
    """The change set or publication object collection query, with the same contract as a live one.

    ``id_filter`` restricts each part of a change set's union alike, so position reads stay exact.
    With ``session``, a search first reads its candidates from the trigram indexes.
    """
    object_type = get_object_type(model, object_type_key)
    if application_key:
        validate_application_object_type(model, application_key, object_type_key)
    return snapshot_object_query(
        model,
        context,
        object_types=(object_type,),
        narrowing={
            "object_type_key": object_type_key,
            "application_key": application_key,
            "parent_object_id": parent_object_id,
            "top_level": top_level,
        },
        filters={
            "applicationKey": application_key,
            "objectTypeKey": object_type_key,
            "parentObjectId": parent_object_id,
            "search": search,
            **top_level_filter(top_level),
            **as_of_filter(as_of),
        },
        search=search,
        sort=sort,
        field_filters=field_filters,
        search_fields=search_fields,
        id_filter=id_filter,
        as_of=as_of,
        search_ids=(
            snapshot_search_candidates(
                session, model, context, object_type=object_type, search=search, search_fields=search_fields
            )
            if session is not None and search
            else None
        ),
    )


def snapshot_search_candidates(
    session: Session,
    model: EngineModel,
    context: SnapshotContext,
    *,
    object_type: ObjectTypeDefinition,
    search: str,
    search_fields: Sequence[str] | None,
) -> list[str] | None:
    """The records of ``object_type`` in the context's owners whose name or searchable value the
    trigram indexes match ``search`` in (:func:`search_candidates`).

    A change set's candidates come from its base and its own rows alike: a base row whose name the
    change set has replaced may be one that no longer matches, and the search's ``LIKE`` on the
    effective record drops it.
    """
    if len(search) < MIN_INDEXED_LENGTH:
        return None
    pattern = f"%{escape_like(search)}%"
    owners = _owners(context)
    parts = []
    if search_fields is None or "name" in search_fields:
        for entity, owner_column, owner_id in owners:
            parts.append(
                select(entity.object_id).where(
                    getattr(entity, owner_column) == owner_id,
                    entity.object_type_key == object_type.key,
                    entity.name.ilike(pattern, escape="\\"),
                )
            )
    attributes = searchable_attribute_keys(model, (object_type,), search_fields)
    if attributes:
        parts.append(
            select(SnapshotAttributeValue.object_id).where(
                SnapshotAttributeValue.sequence_id.in_(SNAPSHOT_VALUES.matches(pattern)),
                SnapshotAttributeValue.owner_id.in_([owner_id for *_, owner_id in owners]),
                SnapshotAttributeValue.attribute_type_key.in_(attributes),
            )
        )
    return search_candidates(session, parts)


def snapshot_object_query(
    model: EngineModel,
    context: SnapshotContext,
    *,
    object_types: Sequence[ObjectTypeDefinition],
    narrowing: dict[str, Any],
    filters: dict[str, Any],
    search: str | None,
    sort: str | None,
    field_filters: list[tuple[str, str, str]],
    search_fields: Sequence[str] | None = None,
    id_filter: Callable[[Any], Any] | None = None,
    builtin: Callable[[Subquery], dict[str, Any]] | None = None,
    parent_filter: Callable[[Any], Any] | None = None,
    as_of: date | None = None,
    search_ids: Sequence[str] | None = None,
) -> ObjectQuery:
    """A change set or publication object query over ``object_types``.

    ``narrowing`` is passed to :func:`object_projection`; ``filters`` are bound into cursors with
    the context and the normalized typed filters. ``builtin`` adds built-in fields read from the
    projection, for a list that filters by more of them than the per-type list does.
    ``parent_filter``, like ``id_filter``, restricts every part alike, by a predicate on the
    record's parent ID.
    """
    for field, operator, _raw in field_filters:
        if field in UNRECORDED_TIMESTAMPS:
            query_error(
                "invalid_filter",
                f"{UNRECORDED_TIMESTAMPS[field]} is not recorded in change sets or publications",
                f"filter.{field}.{operator}",
            )
    sort_field = (sort or "").removeprefix("-")
    if sort_field in UNRECORDED_TIMESTAMPS:
        query_error(
            "invalid_sort",
            f"{UNRECORDED_TIMESTAMPS[sort_field]} is not recorded in change sets or publications",
            "sort",
        )

    def refine(part: ChangeSetPart) -> tuple[Any, Any, Any, Any]:
        projection = object_projection(context, **narrowing, part=part)
        statement = select(projection)
        if id_filter is not None:
            statement = statement.where(id_filter(projection.c.object_id))
        if parent_filter is not None:
            statement = statement.where(parent_filter(projection.c.parent_object_id))
        # The replaced and added parts are as small as the change set: looking up their values
        # row by row costs less than reading the index (S8).
        columns = snapshot_object_columns(
            projection, context, search_index=part in {"effective", "base"}
        )
        if builtin is not None:
            columns = replace(columns, builtin={**columns.builtin, **builtin(projection)})
        return refine_object_query(
            model,
            columns,
            statement,
            object_types=object_types,
            search=search,
            sort=sort,
            field_filters=field_filters,
            search_fields=search_fields,
            as_of=as_of,
            search_ids=search_ids,
        )

    statement, keys, seek, normalized_filters = refine("effective")
    # A change set over a base resolves position reads in the base's index (Base 0.8 S4R6).
    overlay = None
    if context.kind == "change_set" and context.base is not None:
        parts = {part: Keyed(*refine(part)[:2]) for part in ("base", "replaced", "added")}
        overlay = Overlay(parts["base"], parts["replaced"], parts["added"])
    owner = "changeSetId" if context.kind == "change_set" else "publicationId"
    return ObjectQuery(
        statement=statement,
        keys=keys,
        filters={owner: context.id, **filters, "typedFilters": normalized_filters},
        seek=seek,
        overlay=overlay,
    )


def object_scope(context: SnapshotContext) -> str:
    return "objects-change-set" if context.kind == "change_set" else "objects-publication"
