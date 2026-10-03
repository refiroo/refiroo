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

from sqlalchemy import Select, String, case, func, literal, or_, select, union_all
from sqlalchemy.orm import Session, aliased

from ...common.cursors import encode_cursor
from ...common.pagination import SortKey, text_key
from ...models.database import AttributeValue, ObjectRelation, RdmObject, SnapshotAttributeValue
from ...models.schema import EngineModel
from ..model.traversal import related_object_types
from .object_query import ObjectColumns, query_error, refine_object_query
from .snapshot_reads import (
    UNRECORDED_TIMESTAMPS,
    SnapshotContext,
    effective_object_value,
    effective_record,
    relation_projection,
)

# Containment is acyclic, but a walk up it stops here whatever the data holds.
_MAX_ANCESTOR_DEPTH = 64


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
            "invalid_sort",
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
        parents = (
            statement.with_only_columns(parent_id.label("start"), maintain_column_froms=True)
            .distinct()
            .subquery("ancestor_starts")
        )
        walk = select(
            parents.c.start, parents.c.start.label("current"), literal(1).label("depth")
        ).cte("ancestor_walk", recursive=True)
        walk = walk.union_all(
            select(walk.c.start, lookup(walk.c.current, "parent_object_id"), walk.c.depth + 1).where(
                walk.c.current.is_not(None), walk.c.depth < _MAX_ANCESTOR_DEPTH
            )
        )
        # One row per start: the match with the greatest depth, the one nearest the root.
        ancestors = (
            select(walk.c.start, lookup(walk.c.current, "name").label("name"))
            .where(lookup(walk.c.current, "object_type_key") == literal(ancestor_type_key, String))
            .distinct(walk.c.start)
            .order_by(walk.c.start, walk.c.depth.desc())
            .cte("ancestors")
        )
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


def expansion_rows(
    session: Session,
    context: SnapshotContext | None,
    *,
    workspace_key: str,
    anchor_ids: Sequence[str],
    direction: str,
    relation_type_key: str,
    limit: int,
) -> list[ExpansionRow]:
    """The first ``limit`` relations of each anchor in one direction, in one statement (0.9 Q3).

    Each anchor's rows are those ``GET /relations`` lists first for it, with that direction and
    relation type, in name order: the related record's name, then the relation's unique key. Each
    anchor is one arm of a ``UNION ALL`` that orders its own rows and keeps ``limit``, as that list
    does, so an arm keeps a ``limit``-row sort however many relations the anchor has; numbering
    them all in a window sorted every one (20,000 children: 111 ms against 30). An arm also counts
    the anchor's relations. A page of anchors costs one statement whatever its size.
    """
    if not anchor_ids:
        return []
    arms = [
        _expansion_arm(context, workspace_key, anchor_id, direction, relation_type_key, limit, index)
        for index, anchor_id in enumerate(dict.fromkeys(anchor_ids))
    ]
    # Ordered by the database, so names follow its collation as the list's own order does.
    rows = (union_all(*arms) if len(arms) > 1 else arms[0]).subquery("expansion_rows")
    ordered = session.execute(
        select(rows).order_by(rows.c.anchor_id, rows.c.related_name, rows.c.tiebreak)
    )
    return [
        ExpansionRow(
            anchor_id=row.anchor_id,
            relation_id=row.relation_id,
            related_id=row.related_id,
            related_name=row.related_name,
            tiebreak=row.tiebreak,
            total=row.total,
        )
        for row in ordered
    ]


def _expansion_arm(
    context: SnapshotContext | None,
    workspace_key: str,
    anchor_id: str,
    direction: str,
    relation_type_key: str,
    limit: int,
    index: int,
) -> Select[Any]:
    """One anchor's first ``limit`` relations in name order, each with the anchor's total.

    Live, the total counts the anchor's relations alone: a relation joins records of one
    workspace, so the anchor's workspace bounds them without reading the other ends. The
    anchor's relations are read first, as a materialized set, and their records looked up by ID:
    PostgreSQL would otherwise walk the name index over every record of the workspace until
    ``limit`` of them belong to the anchor, which reads most of them when the anchor's records
    sort late (0.9.0-alpha.1 PG5: 20,000 children, 400 ms against 65 ms).
    """
    anchor = literal(anchor_id, String).label("anchor_id")
    if context is None:
        relation, related = aliased(ObjectRelation), aliased(RdmObject, name="expanded")
        own, other = _relation_ends(relation.from_object_id, relation.to_object_id, direction)
        edges = (
            select(relation.id, relation.sequence_id, other.label("other_id"))
            .where(own == anchor_id, relation.relation_type_key == relation_type_key)
            .cte(f"expansion_edges_{index}")
            .prefix_with("MATERIALIZED")
        )
        counted = aliased(ObjectRelation)
        counted_own, _ = _relation_ends(counted.from_object_id, counted.to_object_id, direction)
        total = (
            select(func.count())
            .select_from(counted)
            .where(counted_own == anchor_id, counted.relation_type_key == relation_type_key)
            .scalar_subquery()
        )
        page = (
            select(
                anchor,
                edges.c.id.label("relation_id"),
                edges.c.other_id.label("related_id"),
                related.name.label("related_name"),
                edges.c.sequence_id.label("tiebreak"),
                total.label("total"),
            )
            .select_from(edges)
            .join(related, related.id == edges.c.other_id)
            .where(related.workspace_key == workspace_key)
            .order_by(related.name, edges.c.sequence_id)
        )
    else:
        def anchored() -> Any:
            return relation_projection(
                context, object_id=anchor_id, direction=direction, relation_type_keys=[relation_type_key]
            )

        # The related record is read as the relation list reads it. The total counts relations
        # alone: the list leaves out one whose other end is missing, and a valid change set or a
        # publication holds none, so reading every other end again would count the same.
        relations = anchored()
        related = effective_record(context, relations.c.related_id)
        statement = related.join(select(relations)).where(related.present)
        total = select(func.count()).select_from(anchored()).scalar_subquery()
        name = related.column("name")
        page = statement.with_only_columns(
            anchor,
            relations.c.relation_id.label("relation_id"),
            relations.c.related_id.label("related_id"),
            name.label("related_name"),
            relations.c.relation_id.label("tiebreak"),
            total.label("total"),
            maintain_column_froms=True,
        ).order_by(name, relations.c.relation_id)
    # A compound's arm keeps its own ORDER BY and LIMIT inside a subquery.
    limited = page.limit(limit).subquery()
    return select(limited)


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
