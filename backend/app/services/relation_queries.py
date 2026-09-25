"""Relation collection queries for one record (Base 0.8 S4).

A relation page lists the relations touching an anchor record together with the record at the other
end. ``search`` matches that related record's name and its ``searchable`` attribute values; ``sort``
orders by the related record's name or, live, by relation creation. Live, draft and history reads
share this contract; each builder returns the statement, keyset, cursor filters and seek for
``pagination.paginate_statement``.
"""

from collections.abc import Callable
from dataclasses import dataclass, replace
from datetime import datetime
from typing import Any

from sqlalchemy import Select, case, exists, or_, select
from sqlalchemy.orm import aliased

from ..models.database import AttributeValue, ObjectRelation, RdmObject, SnapshotAttributeValue
from ..models.schema import EngineModel
from .objects import _escape_like, _query_error
from .pagination import SortKey, datetime_key, seek_error, seek_predicate, text_key
from .snapshot_reads import (
    UNRECORDED_TIMESTAMPS,
    SnapshotContext,
    effective_object_value,
    relation_projection,
)

RELATION_SORT_FIELDS = ("name", "createdAt")


@dataclass(frozen=True)
class RelationQuery:
    """A relation page statement returning result rows, with the keyset it must be paged by.

    Each row carries the relation, ``related_id`` and, when the query needs it, ``related_name``.
    """

    statement: Select[Any]
    keys: tuple[SortKey, ...]
    filters: dict[str, Any]
    seek: Callable[[str], Any]


def build_relation_query(
    model: EngineModel,
    *,
    object_id: str,
    direction: str,
    relation_type_key: str | None,
    workspace_key: str,
    search: str | None,
    sort: str | None,
) -> RelationQuery:
    """The live relations touching ``object_id``; both ends must be in ``workspace_key``."""
    field, descending = _relation_sort(sort)
    from_object, to_object = aliased(RdmObject), aliased(RdmObject)
    outgoing = ObjectRelation.from_object_id == object_id
    related_id = case((outgoing, ObjectRelation.to_object_id), else_=ObjectRelation.from_object_id)
    related_name = case((outgoing, to_object.name), else_=from_object.name)
    ends = []
    if direction in {"outgoing", "both"}:
        ends.append(ObjectRelation.from_object_id == object_id)
    if direction in {"incoming", "both"}:
        ends.append(ObjectRelation.to_object_id == object_id)
    statement = (
        select(ObjectRelation, related_id.label("related_id"), related_name.label("related_name"))
        .join(from_object, from_object.id == ObjectRelation.from_object_id)
        .join(to_object, to_object.id == ObjectRelation.to_object_id)
        .where(
            or_(*ends),
            from_object.workspace_key == workspace_key,
            to_object.workspace_key == workspace_key,
        )
    )
    if relation_type_key:
        statement = statement.where(ObjectRelation.relation_type_key == relation_type_key)
    if search:
        pattern = f"%{_escape_like(search)}%"
        statement = statement.where(
            or_(
                related_name.ilike(pattern, escape="\\"),
                exists(
                    select(AttributeValue.sequence_id).where(
                        AttributeValue.object_id == related_id,
                        AttributeValue.attribute_type_key.in_(searchable_attribute_keys(model)),
                        AttributeValue.text_value.ilike(pattern, escape="\\"),
                    )
                ),
            )
        )

    def relation_value(attribute: str) -> Callable[[Any, Any], Any]:
        return lambda _session, row: getattr(row.ObjectRelation, attribute)

    tiebreak = SortKey(
        name="sequenceId",
        column=ObjectRelation.sequence_id,
        attribute="",
        descending=descending,
        parse=int,
        extract=relation_value("sequence_id"),
    )
    if field == "name":
        keys = (text_key("name", related_name, "related_name", descending=descending), tiebreak)
    elif field == "createdAt":
        created = datetime_key("createdAt", ObjectRelation.created_at, "", descending=descending)
        keys = (replace(created, extract=relation_value("created_at")), tiebreak)
    else:
        keys = (tiebreak,)
    return RelationQuery(
        statement=statement,
        keys=keys,
        filters={
            "objectId": object_id,
            "direction": direction,
            "relationTypeKey": relation_type_key,
            "workspaceKey": workspace_key,
            **_search_filter(search),
        },
        seek=_relation_seek(field, keys),
    )


def build_snapshot_relation_query(
    model: EngineModel,
    context: SnapshotContext,
    *,
    object_id: str,
    direction: str,
    relation_type_key: str | None,
    search: str | None,
    sort: str | None,
) -> RelationQuery:
    """The draft or revision relations touching ``object_id``, with the live contract.

    Search and name sort read the related record through keyed lookups per listed relation
    (:func:`snapshot_reads.effective_object_value`) rather than a join to the object projection,
    whose union arms the planner would multiply by the relation arms.
    """
    field, descending = _relation_sort(sort)
    if field in UNRECORDED_TIMESTAMPS:
        _query_error(
            "invalid_sort",
            f"{UNRECORDED_TIMESTAMPS[field]} is not recorded in drafts or history",
            "sort",
        )
    relations = relation_projection(
        context, object_id=object_id, direction=direction, relation_type_key=relation_type_key
    )
    related_id = case(
        (relations.c.from_object_id == object_id, relations.c.to_object_id),
        else_=relations.c.from_object_id,
    )
    statement = select(relations, related_id.label("related_id"))
    related_name = None
    if search or field == "name":
        related_name, values_owner = effective_object_value(context, related_id, "name")
        # A relation whose other end is missing is not listed (a valid draft holds none).
        statement = statement.add_columns(related_name.label("related_name")).where(
            related_name.is_not(None)
        )
        if search:
            pattern = f"%{_escape_like(search)}%"
            values = SnapshotAttributeValue
            statement = statement.where(
                or_(
                    related_name.ilike(pattern, escape="\\"),
                    exists(
                        select(values.sequence_id).where(
                            values.owner_id == values_owner,
                            values.object_id == related_id,
                            values.attribute_type_key.in_(searchable_attribute_keys(model)),
                            values.text_value.ilike(pattern, escape="\\"),
                        )
                    ),
                )
            )
    tiebreak = text_key("id", relations.c.relation_id, "relation_id", descending=descending)
    if field == "name":
        keys = (text_key("name", related_name, "related_name", descending=descending), tiebreak)
    else:
        keys = (tiebreak,)
    owner = "draftId" if context.kind == "draft" else "revisionId"
    return RelationQuery(
        statement=statement,
        keys=keys,
        filters={
            owner: context.id,
            "objectId": object_id,
            "direction": direction,
            "relationTypeKey": relation_type_key,
            **_search_filter(search),
        },
        seek=_relation_seek(field, keys),
    )


def searchable_attribute_keys(model: EngineModel) -> list[str]:
    """Attribute types with the ``searchable`` feature; a related record may be of any type."""
    return [item.key for item in model.attributeTypes if item.features.get("searchable")]


def _relation_sort(sort: str | None) -> tuple[str | None, bool]:
    if sort is None:
        return None, False
    field = sort.removeprefix("-")
    if field not in RELATION_SORT_FIELDS:
        _query_error(
            "invalid_sort",
            f"Unknown relation sort field '{field}'; use one of {', '.join(RELATION_SORT_FIELDS)}",
            "sort",
        )
    return field, sort.startswith("-")


def _relation_seek(field: str | None, keys: tuple[SortKey, ...]) -> Callable[[str], Any]:
    def seek(raw: str) -> Any:
        if field is None:
            raise seek_error("Seek requires a sort; the default order has no value to seek by")
        try:
            value = datetime.fromisoformat(raw) if field == "createdAt" else raw
        except ValueError:
            raise seek_error(f"Invalid seek value for sort '{field}'") from None
        return seek_predicate(keys, [value])

    return seek


def _search_filter(search: str | None) -> dict[str, Any]:
    """Bind ``search`` into a cursor only when set, so cursors issued before it stay valid."""
    return {"search": search} if search else {}
