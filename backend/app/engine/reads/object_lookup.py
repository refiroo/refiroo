"""Cross-type object lookup (Base 0.9 Q1, INTEGRATION_API §Q1).

``GET /objects`` lists records of every type, or of the types a repeatable ``objectTypeKey`` names,
in live, change set and publication contexts. It answers through the per-type list's builders, so
paging, cursors and context parity are the same; it only narrows what may be asked. Search matches
the name, and filters and sorts cover built-in fields: a model-declared field has a type only on
one object type's list, so asking for one here is refused with the route that answers it.
"""

from collections.abc import Sequence
from dataclasses import replace
from typing import Any

from sqlalchemy import select

from ...errors import api_error
from ...models.database import RdmObject
from ...models.schema import EngineModel, ObjectTypeDefinition
from ..records.rules import get_application, get_object_type, validate_application_object_type
from .object_query import (
    DEFAULT_SORT,
    LIVE_OBJECT_COLUMNS,
    ObjectQuery,
    refine_object_query,
    top_level_filter,
)
from .snapshot_reads import SnapshotContext, snapshot_object_query

PER_TYPE_ROUTE = "GET /api/v1/objects/{objectTypeKey}"
FILTER_FIELDS = ("id", "name", "objectTypeKey", "parentObjectId", "createdAt", "updatedAt")
SORT_FIELDS = ("name", "id", "objectType", "createdAt", "updatedAt")
# Search is on the name only: searchable attributes belong to their object types.
SEARCH_FIELDS = ("name",)


def lookup_scope(context: SnapshotContext | None) -> str:
    """The cursor scope, distinct from the per-type list's so neither accepts the other's cursors."""
    if context is None:
        return "object-lookup"
    return "object-lookup-change-set" if context.kind == "change_set" else "object-lookup-publication"


def build_live_lookup_query(
    model: EngineModel,
    *,
    workspace_key: str,
    object_type_keys: Sequence[str],
    application_key: str | None,
    parent_object_id: str | None,
    top_level: bool,
    search: str | None,
    sort: str | None,
    field_filters: list[tuple[str, str, str]],
) -> ObjectQuery:
    types, object_types = _listed_types(model, object_type_keys, application_key)
    _check_built_in(field_filters, sort)
    statement = select(RdmObject).where(
        RdmObject.workspace_key == workspace_key,
        RdmObject.object_type_key.in_(_narrowing_types(types, object_types)),
    )
    if application_key:
        statement = statement.where(RdmObject.application_key == application_key)
    if parent_object_id:
        statement = statement.where(RdmObject.parent_object_id == parent_object_id)
    if top_level:
        statement = statement.where(RdmObject.parent_object_id.is_(None))
    columns = replace(
        LIVE_OBJECT_COLUMNS,
        builtin={
            **LIVE_OBJECT_COLUMNS.builtin,
            "objectTypeKey": RdmObject.object_type_key,
            "parentObjectId": RdmObject.parent_object_id,
        },
    )
    statement, keys, seek, normalized_filters = refine_object_query(
        model,
        columns,
        statement,
        object_types=object_types,
        search=search,
        sort=sort,
        field_filters=field_filters,
        search_fields=SEARCH_FIELDS,
    )
    return ObjectQuery(
        statement=statement,
        keys=keys,
        filters={
            "workspaceKey": workspace_key,
            **_bound_filters(types, application_key, parent_object_id, top_level, search),
            "typedFilters": normalized_filters,
        },
        seek=seek,
    )


def build_snapshot_lookup_query(
    model: EngineModel,
    context: SnapshotContext,
    *,
    object_type_keys: Sequence[str],
    application_key: str | None,
    parent_object_id: str | None,
    top_level: bool,
    search: str | None,
    sort: str | None,
    field_filters: list[tuple[str, str, str]],
) -> ObjectQuery:
    types, object_types = _listed_types(model, object_type_keys, application_key)
    _check_built_in(field_filters, sort)
    return snapshot_object_query(
        model,
        context,
        object_types=object_types,
        narrowing={
            "object_type_keys": _narrowing_types(types, object_types),
            "application_key": application_key,
            "parent_object_id": parent_object_id,
            "top_level": top_level,
            # The name match is the whole search here, so the projection applies it (see there).
            "name_search": search,
        },
        filters=_bound_filters(types, application_key, parent_object_id, top_level, search),
        search=None,
        sort=sort,
        field_filters=field_filters,
        builtin=lambda projection: {
            "objectTypeKey": projection.c.object_type_key,
            "parentObjectId": projection.c.parent_object_id,
        },
    )


def _listed_types(
    model: EngineModel, object_type_keys: Sequence[str], application_key: str | None
) -> tuple[list[str] | None, tuple[ObjectTypeDefinition, ...]]:
    """The named types, sorted and without repeats (``None`` for every type), and their definitions.

    Every named type must exist and, with ``applicationKey``, belong to that application.
    """
    types = sorted(set(object_type_keys)) or None
    if types is None:
        if application_key:
            keys = get_application(model, application_key).objectTypeKeys
            return None, tuple(get_object_type(model, key) for key in keys)
        return None, tuple(model.objectTypes)
    definitions = tuple(get_object_type(model, key) for key in types)
    if application_key:
        for key in types:
            validate_application_object_type(model, application_key, key)
    return types, definitions


def _narrowing_types(
    types: list[str] | None, object_types: Sequence[ObjectTypeDefinition]
) -> list[str]:
    """The types a statement narrows to: the named ones, or every type the list can hold.

    Every record in a context has a type its model declares (activation refuses to remove a type
    in use, and a change set is checked whole against the release it pins), so naming them all
    changes no result. It lets the planner read the (owner, type, name) page indexes instead of
    every row of the owner: a first page over every type in a change set drops from about 120 ms
    to a few milliseconds over 110,000 records.
    """
    return types if types is not None else sorted(item.key for item in object_types)


def _check_built_in(field_filters: list[tuple[str, str, str]], sort: str | None) -> None:
    """Refuse a filter or sort on a field this list does not hold, naming the list that does."""
    for field, operator, _raw in field_filters:
        if field not in FILTER_FIELDS:
            raise api_error(
                422,
                "invalid_filter",
                f"Field '{field}' is not a built-in field; filter by it on {PER_TYPE_ROUTE}",
                {
                    "path": f"/query/filter.{field}.{operator}",
                    "builtInFields": list(FILTER_FIELDS),
                    "route": PER_TYPE_ROUTE,
                },
            )
    field = (sort or DEFAULT_SORT).removeprefix("-")
    if field not in SORT_FIELDS:
        raise api_error(
            422,
            "invalid_sort",
            f"Field '{field}' is not a built-in sort; sort by it on {PER_TYPE_ROUTE}",
            {"path": "/query/sort", "builtInSorts": list(SORT_FIELDS), "route": PER_TYPE_ROUTE},
        )


def _bound_filters(
    types: list[str] | None,
    application_key: str | None,
    parent_object_id: str | None,
    top_level: bool,
    search: str | None,
) -> dict[str, Any]:
    return {
        "objectTypeKeys": types,
        "applicationKey": application_key,
        "parentObjectId": parent_object_id,
        "search": search,
        **top_level_filter(top_level),
    }
