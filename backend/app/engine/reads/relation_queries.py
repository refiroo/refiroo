"""Relation collection queries for one record (Base 0.8 S4, revised in S4R1).

A relation page lists the relations touching an anchor record together with the record at the other
end. Search, sort and seek apply to that related record through the object query builder
(:func:`objects.refine_object_query`), so they mean what they mean on an object list: ``search``
matches its name and searchable fields, and ``sort`` takes its name, a scalar attribute, an
``ancestor:<type>`` name, ``objectType`` (its type's name) or, live, its timestamps, and
``relationship`` orders by the relationship label the row shows. The default order is by name in
every context, closed by the relation's unique key. An attribute sort puts records whose type lacks
the attribute last; an ancestor sort needs the related records to have one type, which the relation
types, direction and anchor type decide.

Live, change set and history reads share this contract; each builder returns the statement, keyset,
cursor filters and seek for ``pagination.paginate_statement``.
"""

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Any

from sqlalchemy import (
    ARRAY,
    JSON,
    Select,
    String,
    case,
    func,
    literal,
    null,
    or_,
    select,
    true,
    type_coerce,
)
from sqlalchemy.dialects.postgresql import distinct_on
from sqlalchemy.orm import Session, aliased

from ...common.cursors import encode_cursor
from ...common.pagination import SortKey, text_key
from ...errors import api_error
from ...models.database import AttributeValue, ObjectRelation, RdmObject, SnapshotAttributeValue
from ...models.schema import EngineModel
from ..model.traversal import related_object_types
from ..records.values import value_json
from .object_query import ObjectColumns, query_error, refine_object_query
from .snapshot_reads import (
    UNRECORDED_TIMESTAMPS,
    SnapshotContext,
    effective_object_value,
    effective_record,
    object_projection,
    relation_projection,
)

# Containment is acyclic, but a walk up it stops here whatever the data holds.
_MAX_ANCESTOR_DEPTH = 64
# Not recorded for change set and publication rows (WP-10K).
_TIMESTAMPS = ("created_at", "updated_at")


@dataclass(frozen=True)
class RelationQuery:
    """A relation page statement returning result rows, with the keyset it must be paged by.

    Each row carries the relation and ``related_id``, plus a ``sort_<n>`` column per sort key
    before the tiebreak.
    """

    statement: Select[Any]
    keys: tuple[SortKey, ...]
    filters: dict[str, Any]
    seek: Callable[[str], Any]


def build_relation_query(
    model: EngineModel,
    *,
    object_id: str,
    anchor_type_key: str,
    direction: str,
    relation_type_keys: Sequence[str] | None,
    workspace_key: str,
    search: str | None,
    sort: str | None,
) -> RelationQuery:
    """The live relations touching ``object_id``; the related record must be in ``workspace_key``."""
    related = aliased(RdmObject, name="related")
    outgoing = ObjectRelation.from_object_id == object_id
    related_id = case((outgoing, ObjectRelation.to_object_id), else_=ObjectRelation.from_object_id)
    ends = []
    if direction in {"outgoing", "both"}:
        ends.append(ObjectRelation.from_object_id == object_id)
    if direction in {"incoming", "both"}:
        ends.append(ObjectRelation.to_object_id == object_id)
    statement = (
        select(ObjectRelation, related_id.label("related_id"))
        .join(related, related.id == related_id)
        .where(or_(*ends), related.workspace_key == workspace_key)
    )
    if relation_type_keys:
        statement = statement.where(ObjectRelation.relation_type_key.in_(relation_type_keys))

    columns = ObjectColumns(
        source=related,
        id=related.id,
        name=related.name,
        values=AttributeValue,
        value_match=lambda values: (values.object_id == related.id,),
        builtin={
            "id": related.id,
            "name": related.name,
            "createdAt": related.created_at,
            "updatedAt": related.updated_at,
        },
        tiebreak=lambda descending: SortKey(
            name="relation",
            column=ObjectRelation.sequence_id,
            attribute="",
            descending=descending,
            parse=int,
            extract=lambda _session, row: row.ObjectRelation.sequence_id,
        ),
        select_sort_values=True,
        ancestor=_ancestor_join(_live_lookup, related.parent_object_id),
        object_type=related.object_type_key,
        # The listed record is the relation's source when the anchor is its target.
        relationship=(ObjectRelation.relation_type_key, ObjectRelation.from_object_id != object_id),
    )
    statement, keys, seek, _filters = refine_object_query(
        model,
        columns,
        statement,
        object_types=related_object_types(model, anchor_type_key, direction, relation_type_keys),
        search=search,
        sort=sort,
        field_filters=[],
    )
    return RelationQuery(
        statement=statement,
        keys=keys,
        filters=relation_filters(
            None,
            object_id=object_id,
            direction=direction,
            relation_type_keys=relation_type_keys,
            workspace_key=workspace_key,
            search=search,
        ),
        seek=seek,
    )


def build_snapshot_relation_query(
    model: EngineModel,
    context: SnapshotContext,
    *,
    object_id: str,
    anchor_type_key: str,
    direction: str,
    relation_type_keys: Sequence[str] | None,
    search: str | None,
    sort: str | None,
) -> RelationQuery:
    """The change set or publication relations touching ``object_id``, with the live contract.

    The related record is read by outer joins on its unique keys
    (:func:`snapshot_reads.effective_record`) rather than a join to the object projection, whose
    union arms the planner would multiply by the relation arms.
    """
    field = (sort or "").removeprefix("-")
    if field in UNRECORDED_TIMESTAMPS:
        query_error(
            "INVALID_SORT",
            f"{UNRECORDED_TIMESTAMPS[field]} is not recorded in change sets or publications",
            "sort",
        )
    relations = relation_projection(
        context, object_id=object_id, direction=direction, relation_type_keys=relation_type_keys
    )
    related_id = relations.c.related_id
    related = effective_record(context, related_id)
    related_name = related.column("name")
    # A relation whose other end is missing is not listed (a valid change set holds none).
    statement = related.join(select(relations)).where(related.present)
    values = SnapshotAttributeValue
    columns = ObjectColumns(
        source=relations,
        id=related_id,
        name=related_name,
        values=values,
        value_match=lambda values: (
            values.owner_id == related.values_owner,
            values.object_id == related_id,
        ),
        builtin={"id": related_id, "name": related_name},
        tiebreak=lambda descending: text_key(
            "relation", relations.c.relation_id, "relation_id", descending=descending
        ),
        select_sort_values=True,
        ancestor=_ancestor_join(
            lambda record_id, column: effective_object_value(context, record_id, column)[0],
            related.column("parent_object_id"),
        ),
        object_type=related.column("object_type_key"),
        relationship=(relations.c.relation_type_key, relations.c.from_object_id != object_id),
    )
    statement, keys, seek, _filters = refine_object_query(
        model,
        columns,
        statement,
        object_types=related_object_types(model, anchor_type_key, direction, relation_type_keys),
        search=search,
        sort=sort,
        field_filters=[],
    )
    return RelationQuery(
        statement=statement,
        keys=keys,
        filters=relation_filters(
            context,
            object_id=object_id,
            direction=direction,
            relation_type_keys=relation_type_keys,
            workspace_key=None,
            search=search,
        ),
        seek=seek,
    )


def _live_lookup(object_id: Any, column: str) -> Any:
    return (
        select(getattr(RdmObject, column))
        .where(RdmObject.id == object_id)
        .correlate_except(RdmObject)
        .scalar_subquery()
    )


def _ancestor_join(
    lookup: Callable[[Any, str], Any], parent_id: Any
) -> Callable[[Select[Any], str], tuple[Select[Any], Any]]:
    """Join each related record's ``ancestor:<type>`` name into a relation statement.

    The walk up the containment chain starts once from each distinct parent of the listed records,
    not from every record: a heavy parent's thousands of children share one walk. Being small, the
    walk reads records with keyed lookups (``lookup`` reads one column of a record by ID in the
    list's context), which the planner cannot turn into a scan of every record of a type. Like a
    record's ``path``, a type met twice on the way up resolves to the one nearest the root.
    """

    def join(statement: Select[Any], ancestor_type_key: str) -> tuple[Select[Any], Any]:
        walk = _ancestor_walk(
            lookup,
            statement.with_only_columns(
                parent_id.label("start"), maintain_column_froms=True
            ).distinct(),
        )
        ancestors = _nearest_ancestor(walk, lookup, ancestor_type_key, "ancestors")
        return statement.outerjoin(ancestors, ancestors.c.start == parent_id), ancestors.c.name

    return join


def relation_scope(context: SnapshotContext | None) -> str:
    """The relation list's cursor scope in a context (live when ``None``)."""
    return "relations" if context is None else f"relations-{context.kind}"


def relation_filters(
    context: SnapshotContext | None,
    *,
    object_id: str,
    direction: str,
    relation_type_keys: Sequence[str] | None,
    workspace_key: str | None,
    search: str | None,
) -> dict[str, Any]:
    """What a relation list's cursor binds: its anchor, direction, types, search and context."""
    owner = (
        {"workspaceKey": workspace_key}
        if context is None
        else {"changeSetId" if context.kind == "change_set" else "publicationId": context.id}
    )
    return {
        "objectId": object_id,
        "direction": direction,
        **_relation_types_filter(relation_type_keys),
        **owner,
        **_search_filter(search),
    }


# The cursor tokens of the relation list's default order: the related record's name, then the
# relation's unique key.
_NAME_ORDER = ("name", "relation")


@dataclass(frozen=True)
class ExpansionRow:
    """One relation of an anchor, in the relation list's default order, with the anchor's total.

    ``tiebreak`` is the relation's unique key in that order: its sequence number live, its public
    ID in a change set or publication.
    """

    anchor_id: str
    relation_id: str
    related_id: str
    related_name: str
    tiebreak: Any
    total: int
    # What a narrowed expansion read of the related record (0.11 X6, D155); None when not narrowed.
    fields: RelatedFields | None = None


@dataclass(frozen=True)
class NarrowFields:
    """What a narrowed expansion reads of each related record beside its ID, type, version and
    name (0.11 X6, D155): attribute values, and of its ancestor of a type nearest the root, the
    ancestor's ID and name and attribute values."""

    attributes: tuple[str, ...] = ()
    ancestors: tuple[str, ...] = ()
    ancestor_attributes: tuple[tuple[str, str], ...] = ()


@dataclass(frozen=True)
class RelatedFields:
    """A related record as a narrowed expansion read it. Values are in their stored JSON form;
    ``created_at`` and ``updated_at`` are null in a change set or publication, as their rows
    record none. ``ancestors`` maps a type to the ancestor's ``(id, name)``, or ``None``."""

    object_type_key: str
    version: int
    application_key: str
    parent_object_id: str | None
    created_at: Any
    updated_at: Any
    attributes: dict[str, Any]
    ancestors: dict[str, tuple[str, str] | None]
    ancestor_attributes: dict[tuple[str, str], Any]


def expansion_rows(
    session: Session,
    context: SnapshotContext | None,
    *,
    workspace_key: str,
    anchor_ids: Sequence[str],
    direction: str,
    relation_type_key: str,
    limit: int,
    narrow: NarrowFields | None = None,
) -> list[ExpansionRow]:
    """The first ``limit`` relations of each anchor in one direction, in one statement (0.9 Q3).

    With ``narrow``, the same statement reads what it names of each related record, its ancestors'
    values by a walk up the parent chain inside it (0.11 X6, D155): no record is built and dropped.

    Each anchor's rows are those ``GET /relations`` lists first for it, with that direction and
    relation type, in name order: the related record's name, then the relation's unique key. The
    anchors are a list the statement unnests; each reads its own rows and its total through two
    ``LATERAL`` subqueries, so an anchor keeps a ``limit``-row sort however many relations it has
    (numbering them all in a window sorted every one: 20,000 children, 111 ms against 30), and a
    page of anchors is one statement planned once (0.9 K5: a ``UNION ALL`` arm per anchor took
    600 ms for a page of 100 with two expansions).
    """
    if not anchor_ids:
        return []
    ids = list(dict.fromkeys(anchor_ids))
    anchors = select(func.unnest(literal(ids, ARRAY(String))).label("anchor_id")).subquery(
        "anchors"
    )
    anchor = anchors.c.anchor_id
    # In a context, the page's relations are read once, for every anchor, and each anchor's
    # subqueries filter them: the projection's union arms sit too deep to correlate to the anchor.
    relations = (
        None
        if context is None
        else relation_projection(
            context, endpoint_ids=ids, direction=direction, relation_type_keys=[relation_type_key]
        ).element.cte("expansion_relations")
    )
    page = (
        _expansion_page(
            context, relations, workspace_key, anchor, direction, relation_type_key, narrow
        )
        .limit(limit)
        .lateral("expansion_page")
    )
    total = _expansion_total(relations, anchor, direction, relation_type_key).lateral(
        "expansion_total"
    )
    read = (
        select(anchor.label("anchor_id"), *page.c, total.c.total)
        # The total before the page: it depends on the anchor alone, and joined after the page a
        # publication's plan counted it again for every row of the page (0.9 R, R-F28).
        .select_from(anchors)
        .join(total, true())
        .join(page, true())
    )
    order: Any = (anchor, page.c.related_name, page.c.tiebreak)
    ancestors: dict[str, tuple[int, list[str]]] = {}
    if narrow is not None and (narrow.ancestors or narrow.ancestor_attributes):
        expanded = read.cte("expanded")
        lookup, value = _context_lookups(context)
        starts = select(expanded.c.parent_object_id.label("start")).distinct()
        walk = _ancestor_walk(lookup, starts)
        statement = select(*expanded.c)
        types = dict.fromkeys([*narrow.ancestors, *(key for key, _ in narrow.ancestor_attributes)])
        for index, type_key in enumerate(types):
            keys = [name for owner, name in narrow.ancestor_attributes if owner == type_key]
            found = _nearest_ancestor(walk, lookup, type_key, f"ancestor_{index}", value, keys)
            statement = statement.outerjoin(
                found, found.c.start == expanded.c.parent_object_id
            ).add_columns(*(column.label(f"a{index}_{column.key}") for column in found.c))
            ancestors[type_key] = (index, keys)
        order = (expanded.c.anchor_id, expanded.c.related_name, expanded.c.tiebreak)
        read = statement
    # Ordered by the database, so names follow its collation as the list's own order does.
    ordered = session.execute(read.order_by(*order))
    return [
        ExpansionRow(
            anchor_id=row.anchor_id,
            relation_id=row.relation_id,
            related_id=row.related_id,
            related_name=row.related_name,
            tiebreak=row.tiebreak,
            total=row.total,
            fields=None if narrow is None else _related_fields(row, narrow, ancestors),
        )
        for row in ordered
    ]


def _related_fields(
    row: Any, narrow: NarrowFields, ancestors: dict[str, tuple[int, list[str]]]
) -> RelatedFields:
    found: dict[str, tuple[str, str] | None] = {}
    values: dict[tuple[str, str], Any] = {}
    for type_key, (index, keys) in ancestors.items():
        ancestor_id = getattr(row, f"a{index}_id")
        found[type_key] = (
            None if ancestor_id is None else (ancestor_id, getattr(row, f"a{index}_name"))
        )
        for position, key in enumerate(keys):
            values[(type_key, key)] = getattr(row, f"a{index}_value_{position}")
    return RelatedFields(
        object_type_key=row.related_type,
        version=row.related_version,
        application_key=row.related_application,
        parent_object_id=row.parent_object_id,
        created_at=row.related_created_at,
        updated_at=row.related_updated_at,
        attributes={
            key: getattr(row, f"value_{index}") for index, key in enumerate(narrow.attributes)
        },
        ancestors=found,
        ancestor_attributes=values,
    )


def _live_value(object_id: Any, key: str) -> Any:
    """A live record's value of one attribute in its stored JSON form, as a keyed lookup."""
    values = aliased(AttributeValue)
    return (
        select(value_json(values, type_=JSON))
        .where(values.object_id == object_id, values.attribute_type_key == key)
        .correlate_except(values)
        .scalar_subquery()
    )


def _json_value(attributes: Any, key: str) -> Any:
    """One key of a row's JSON ``attributes``: SQL null when the record has no value."""
    return type_coerce(attributes, JSON)[key]


def _context_lookups(
    context: SnapshotContext | None,
) -> tuple[Callable[[Any, str], Any], Callable[[Any, str], Any]]:
    """Keyed lookups of a record's column and of one attribute value by ID, in the context."""
    if context is None:
        return _live_lookup, _live_value

    def lookup(record_id: Any, column: str) -> Any:
        return effective_object_value(context, record_id, column)[0]

    return lookup, lambda record_id, key: _json_value(lookup(record_id, "attributes"), key)


def _ancestor_walk(lookup: Callable[[Any, str], Any], starts: Select[Any]) -> Any:
    """Every record up the containment chain from each start (a parent ID), with its depth: the
    start is depth 1. Few rows, read with keyed lookups (see :func:`_ancestor_join`)."""
    begin = starts.subquery("ancestor_starts")
    walk = select(begin.c.start, begin.c.start.label("current"), literal(1).label("depth")).cte(
        "ancestor_walk", recursive=True
    )
    return walk.union_all(
        select(walk.c.start, lookup(walk.c.current, "parent_object_id"), walk.c.depth + 1).where(
            walk.c.current.is_not(None), walk.c.depth < _MAX_ANCESTOR_DEPTH
        )
    )


def _nearest_ancestor(
    walk: Any,
    lookup: Callable[[Any, str], Any],
    type_key: str,
    name: str,
    value: Callable[[Any, str], Any] | None = None,
    keys: Sequence[str] = (),
) -> Any:
    """One row per start: its ancestor of ``type_key`` nearest the root (as a record's ``path``
    names it; the match with the greatest depth), with the ancestor's ID, name and, read with
    ``value``, the values of ``keys``."""
    values = [] if value is None else [value(walk.c.current, key) for key in keys]
    return (
        select(
            walk.c.start,
            walk.c.current.label("id"),
            lookup(walk.c.current, "name").label("name"),
            *(item.label(f"value_{index}") for index, item in enumerate(values)),
        )
        .where(lookup(walk.c.current, "object_type_key") == literal(type_key, String))
        .ext(distinct_on(walk.c.start))
        .order_by(walk.c.start, walk.c.depth.desc())
        .cte(name)
    )


def _expansion_page(
    context: SnapshotContext | None,
    relations: Any,
    workspace_key: str,
    anchor: Any,
    direction: str,
    relation_type_key: str,
    narrow: NarrowFields | None = None,
) -> Select[Any]:
    """One anchor's relations with their records, in name order (limited by the caller), and with
    ``narrow`` the related record's columns and values it names.

    Live, the anchor's relations are read first, behind an ``OFFSET 0`` fence, and their records
    looked up by ID: PostgreSQL would otherwise walk the name index over every record of the
    workspace until enough of them belong to the anchor, which reads most of them when the anchor's
    records sort late (0.9.0-alpha.1 PG5: 20,000 children, 400 ms against 65 ms). In a change set or
    publication, the related record is read as the relation list reads it, from ``relations``, the
    context's relations of every anchor.
    """
    if context is None:
        relation, related = aliased(ObjectRelation), aliased(RdmObject, name="expanded")
        own, other = _relation_ends(relation.from_object_id, relation.to_object_id, direction)
        edges = (
            select(relation.id, relation.sequence_id, other.label("other_id"))
            .where(own == anchor, relation.relation_type_key == relation_type_key)
            # The anchor is two levels up; automatic correlation reaches one.
            .correlate_except(relation)
            .offset(0)
            .lateral("expansion_edges")
        )
        return (
            select(
                edges.c.id.label("relation_id"),
                edges.c.other_id.label("related_id"),
                related.name.label("related_name"),
                edges.c.sequence_id.label("tiebreak"),
                *_narrow_columns(
                    narrow,
                    lambda column: getattr(related, column),
                    lambda key: _live_value(related.id, key),
                ),
            )
            .select_from(edges)
            .join(related, related.id == edges.c.other_id)
            .where(related.workspace_key == workspace_key)
            .order_by(related.name, edges.c.sequence_id)
        )
    own, other = _relation_ends(relations.c.from_object_id, relations.c.to_object_id, direction)
    related = effective_record(context, other)
    name = related.column("name")
    return (
        related.join(select(relations).where(own == anchor))
        .where(related.present)
        .with_only_columns(
            relations.c.relation_id.label("relation_id"),
            other.label("related_id"),
            name.label("related_name"),
            relations.c.relation_id.label("tiebreak"),
            *_narrow_columns(
                narrow,
                lambda column: null() if column in _TIMESTAMPS else related.column(column),
                lambda key: _json_value(related.column("attributes"), key),
            ),
            maintain_column_froms=True,
        )
        .order_by(name, relations.c.relation_id)
    )


def _narrow_columns(
    narrow: NarrowFields | None, column: Callable[[str], Any], value: Callable[[str], Any]
) -> list[Any]:
    """The related record's columns a narrowed expansion reads (none without ``narrow``)."""
    if narrow is None:
        return []
    return [
        column("object_type_key").label("related_type"),
        column("version").label("related_version"),
        column("application_key").label("related_application"),
        column("parent_object_id").label("parent_object_id"),
        column("created_at").label("related_created_at"),
        column("updated_at").label("related_updated_at"),
        *(value(key).label(f"value_{index}") for index, key in enumerate(narrow.attributes)),
    ]


def _expansion_total(
    relations: Any, anchor: Any, direction: str, relation_type_key: str
) -> Select[Any]:
    """How many relations of the type the anchor has in the direction.

    Live, the anchor's relations alone: a relation joins records of one workspace, so the anchor's
    workspace bounds them without reading the other ends. In a context, relations alone too: the
    list leaves out one whose other end is missing, and a valid change set or a publication holds
    none, so reading every other end again would count the same.
    """
    if relations is None:
        counted = aliased(ObjectRelation)
        own, _ = _relation_ends(counted.from_object_id, counted.to_object_id, direction)
        return (
            select(func.count().label("total"))
            .select_from(counted)
            .where(own == anchor, counted.relation_type_key == relation_type_key)
        )
    own, _ = _relation_ends(relations.c.from_object_id, relations.c.to_object_id, direction)
    return select(func.count().label("total")).select_from(relations).where(own == anchor)


def _relation_ends(from_column: Any, to_column: Any, direction: str) -> tuple[Any, Any]:
    """The anchor's end of a relation and the other end, for ``direction`` from the anchor."""
    return (from_column, to_column) if direction == "outgoing" else (to_column, from_column)


def expansion_cursor(
    context: SnapshotContext | None,
    *,
    workspace_key: str,
    direction: str,
    relation_type_key: str,
    after: ExpansionRow,
) -> str:
    """The ``GET /relations`` cursor that continues an anchor's expansion after ``after``.

    It is the cursor that list issues for that row in its default order, with the anchor, the
    direction, the one relation type and the context the expansion read.
    """
    return encode_cursor(
        (str(after.related_name), str(after.tiebreak)),
        scope=relation_scope(context),
        sort=_NAME_ORDER,
        filters=relation_filters(
            context,
            object_id=after.anchor_id,
            direction=direction,
            relation_type_keys=[relation_type_key],
            workspace_key=workspace_key if context is None else None,
            search=None,
        ),
    )


def _relation_types_filter(relation_type_keys: Sequence[str] | None) -> dict[str, Any]:
    return {"relationTypeKeys": sorted(set(relation_type_keys))} if relation_type_keys else {}


def _search_filter(search: str | None) -> dict[str, Any]:
    """Bind ``search`` into a cursor only when set, so cursors issued before it stay valid."""
    return {"search": search} if search else {}


# How many records one read of what a set holds may name (0.9 K6a, D165).
HELD_MAX_RECORDS = 500


@dataclass(frozen=True)
class HeldQuery:
    """What a set of records holds through one relationship: the statement and its keyset."""

    statement: Select[Any]
    keys: tuple[SortKey, ...]
    filters: dict[str, Any]


def held_records_query(
    model: EngineModel,
    context: SnapshotContext | None,
    *,
    workspace_key: str,
    object_type_key: str,
    relation_type_key: str,
    direction: str,
    object_ids: Sequence[str],
) -> HeldQuery:
    """The records at the other end of ``relation_type_key`` from ``object_ids`` (records of
    ``object_type_key``, read ``direction`` from them), each with how many of them hold it, in the
    far record's name order (0.9 K6a, D165). One grouped set statement, live or in a context.
    """
    if model.relation_type(relation_type_key) is None:
        raise api_error(
            422,
            "UNKNOWN_RELATION_TYPE",
            f"Relation type '{relation_type_key}' not found",
            {"parameter": "relationTypeKey"},
        )
    targets = related_object_types(model, object_type_key, direction, [relation_type_key])
    if not targets:
        raise api_error(
            422,
            "INVALID_RELATION_PAIR",
            f"Object type '{object_type_key}' has no {direction} binding of relation type"
            f" '{relation_type_key}'",
            {"parameter": "relationTypeKey"},
        )
    ids = sorted(set(object_ids))
    if len(ids) > HELD_MAX_RECORDS:
        raise api_error(
            422,
            "TOO_MANY_RECORDS",
            f"Name at most {HELD_MAX_RECORDS} records in one read; {len(ids)} were named",
            {"parameter": "objectId", "limit": HELD_MAX_RECORDS},
        )
    target_keys = [item.key for item in targets]
    if context is None:
        relation = aliased(ObjectRelation)
        own, far = _relation_ends(relation.from_object_id, relation.to_object_id, direction)
        held = (
            select(far.label("far_id"), func.count().label("held"))
            .where(own.in_(ids), relation.relation_type_key == relation_type_key)
            .group_by(far)
            .subquery("held")
        )
        other = aliased(RdmObject, name="held_record")
        statement = (
            select(
                other.id.label("id"),
                other.name.label("name"),
                other.object_type_key.label("object_type_key"),
                held.c.held,
            )
            .join(held, held.c.far_id == other.id)
            .where(other.workspace_key == workspace_key, other.object_type_key.in_(target_keys))
        )
        name, identity = other.name, other.id
    else:
        relations = relation_projection(
            context, endpoint_ids=ids, direction=direction, relation_type_keys=[relation_type_key]
        )
        own, far = _relation_ends(relations.c.from_object_id, relations.c.to_object_id, direction)
        held = (
            select(far.label("far_id"), func.count().label("held"))
            .select_from(relations)
            .where(own.in_(ids))
            .group_by(far)
            .subquery("held")
        )
        others = object_projection(context, object_type_keys=target_keys).alias("held_records")
        statement = select(
            others.c.object_id.label("id"),
            others.c.name.label("name"),
            others.c.object_type_key.label("object_type_key"),
            held.c.held,
        ).join(held, held.c.far_id == others.c.object_id)
        name, identity = others.c.name, others.c.object_id
    return HeldQuery(
        statement=statement,
        keys=(text_key("name", name, "name"), text_key("id", identity, "id")),
        filters={
            "objectTypeKey": object_type_key,
            "relationTypeKey": relation_type_key,
            "direction": direction,
            "objectIds": ids,
            **({"workspaceKey": workspace_key} if context is None else {"context": context.id}),
        },
    )
