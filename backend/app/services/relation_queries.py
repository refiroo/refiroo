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

Live, draft and history reads share this contract; each builder returns the statement, keyset,
cursor filters and seek for ``pagination.paginate_statement``.
"""

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Any

from sqlalchemy import Select, String, case, func, literal, or_, select
from sqlalchemy.orm import aliased

from ..models.database import AttributeValue, ObjectRelation, RdmObject, SnapshotAttributeValue
from ..models.schema import EngineModel
from .model.traversal import related_object_types
from .objects import ObjectColumns, _query_error, refine_object_query
from .pagination import SortKey, text_key
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
        filters={
            "objectId": object_id,
            "direction": direction,
            **_relation_types_filter(relation_type_keys),
            "workspaceKey": workspace_key,
            **_search_filter(search),
        },
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
    """The draft or revision relations touching ``object_id``, with the live contract.

    The related record is read by outer joins on its unique keys
    (:func:`snapshot_reads.effective_record`) rather than a join to the object projection, whose
    union arms the planner would multiply by the relation arms.
    """
    field = (sort or "").removeprefix("-")
    if field in UNRECORDED_TIMESTAMPS:
        _query_error(
            "invalid_sort",
            f"{UNRECORDED_TIMESTAMPS[field]} is not recorded in drafts or history",
            "sort",
        )
    relations = relation_projection(
        context, object_id=object_id, direction=direction, relation_type_keys=relation_type_keys
    )
    related_id = relations.c.related_id
    related = effective_record(context, related_id)
    related_name = related.column("name")
    # A relation whose other end is missing is not listed (a valid draft holds none).
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
    owner = "draftId" if context.kind == "draft" else "revisionId"
    return RelationQuery(
        statement=statement,
        keys=keys,
        filters={
            owner: context.id,
            "objectId": object_id,
            "direction": direction,
            **_relation_types_filter(relation_type_keys),
            **_search_filter(search),
        },
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
        # SQLite reads the bare ``name`` from the row holding ``max(depth)``: the one nearest the root.
        ancestors = (
            select(walk.c.start, lookup(walk.c.current, "name").label("name"), func.max(walk.c.depth))
            .where(lookup(walk.c.current, "object_type_key") == literal(ancestor_type_key, String))
            .group_by(walk.c.start)
            .cte("ancestors")
        )
        return statement.outerjoin(ancestors, ancestors.c.start == parent_id), ancestors.c.name

    return join


def _relation_types_filter(relation_type_keys: Sequence[str] | None) -> dict[str, Any]:
    return {"relationTypeKeys": sorted(set(relation_type_keys))} if relation_type_keys else {}


def _search_filter(search: str | None) -> dict[str, Any]:
    """Bind ``search`` into a cursor only when set, so cursors issued before it stay valid."""
    return {"search": search} if search else {}
