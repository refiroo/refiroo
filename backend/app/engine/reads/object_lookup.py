"""Cross-type object lookup (Base 0.9 Q1, INTEGRATION_API §Q1).

``GET /objects`` lists records of every type, or of the types a repeatable ``objectTypeKey`` names,
in live, change set and publication contexts. It answers through the per-type list's builders, so
paging, cursors and context parity are the same; it only narrows what may be asked. Search matches
the name, and filters and sorts cover built-in fields: a model-declared field has a type only on
one object type's list, so asking for one here is refused with the route that answers it.

Naming several workspaces reads their live records together (0.11 M4, D41): each workspace's model
is its own, so a type or application some of them lack is refused naming those workspaces (D42).
"""

from collections.abc import Callable, Mapping, Sequence
from dataclasses import replace
from typing import Any

from sqlalchemy import case, select

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
QUERY_ROUTE = "POST /api/v1/workspaces/{workspaceKey}/queries/objects"
FILTER_FIELDS = ("id", "name", "objectTypeKey", "parentObjectId", "createdAt", "updatedAt")
SORT_FIELDS = ("name", "id", "objectType", "createdAt", "updatedAt")
# Search is on the name only: searchable attributes belong to their object types.
SEARCH_FIELDS = ("name",)


def lookup_scope(context: SnapshotContext | None) -> str:
    """The cursor scope, distinct from the per-type list's so neither accepts the other's cursors."""
    if context is None:
        return "object-lookup"
    return (
        "object-lookup-change-set" if context.kind == "change_set" else "object-lookup-publication"
    )


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


def build_spanning_lookup_query(
    models: Mapping[str, EngineModel],
    *,
    object_type_keys: Sequence[str],
    application_key: str | None,
    parent_object_id: str | None,
    top_level: bool,
    search: str | None,
    sort: str | None,
    field_filters: list[tuple[str, str, str]],
) -> ObjectQuery:
    """The live records of several workspaces (``models``: each workspace's model) in one list
    (D41). A named type or application must be in every workspace's model (D42); ``objectType``
    sorts by each record's type name in its own workspace's model."""
    workspaces = sorted(models)
    if application_key:
        _in_every_model(models, "application", application_key, _holds_application)
    for key in sorted(set(object_type_keys)):
        _in_every_model(models, "objectType", key, _holds_type)
    _check_built_in(field_filters, sort)
    listed = {
        workspace: _listed_types(models[workspace], object_type_keys, application_key)
        for workspace in workspaces
    }
    types = next(iter(listed.values()))[0]
    narrowing = sorted(
        {
            key
            for found, definitions in listed.values()
            for key in _narrowing_types(found, definitions)
        }
    )
    statement = select(RdmObject).where(
        RdmObject.workspace_key.in_(workspaces), RdmObject.object_type_key.in_(narrowing)
    )
    if application_key:
        statement = statement.where(RdmObject.application_key == application_key)
    if parent_object_id:
        statement = statement.where(RdmObject.parent_object_id == parent_object_id)
    if top_level:
        statement = statement.where(RdmObject.parent_object_id.is_(None))
    names = {
        (workspace, item.key): item.name
        for workspace in workspaces
        for item in models[workspace].objectTypes
    }
    label = case(
        *(
            ((RdmObject.workspace_key == workspace) & (RdmObject.object_type_key == key), name)
            for (workspace, key), name in names.items()
        ),
        else_=RdmObject.object_type_key,
    )
    columns = replace(
        LIVE_OBJECT_COLUMNS,
        builtin={
            **LIVE_OBJECT_COLUMNS.builtin,
            "objectTypeKey": RdmObject.object_type_key,
            "parentObjectId": RdmObject.parent_object_id,
        },
        object_type_label=(
            label,
            lambda row: names.get((row.workspace_key, row.object_type_key), row.object_type_key),
        ),
    )
    # The lookup filters, searches and sorts built-in fields only, which read no model; the
    # builder is given one workspace's model and types, and the type label covers the others.
    first = workspaces[0]
    statement, keys, seek, normalized_filters = refine_object_query(
        models[first],
        columns,
        statement,
        object_types=listed[first][1],
        search=search,
        sort=sort,
        field_filters=field_filters,
        search_fields=SEARCH_FIELDS,
    )
    return ObjectQuery(
        statement=statement,
        keys=keys,
        filters={
            "workspaceKeys": workspaces,
            **_bound_filters(types, application_key, parent_object_id, top_level, search),
            "typedFilters": normalized_filters,
        },
        seek=seek,
    )


def _holds_application(model: EngineModel, key: str) -> bool:
    return any(item.key == key for item in model.applications)


def _holds_type(model: EngineModel, key: str) -> bool:
    return any(item.key == key for item in model.objectTypes)


def _in_every_model(
    models: Mapping[str, EngineModel],
    kind: str,
    key: str,
    holds: Callable[[EngineModel, str], bool],
) -> None:
    """Refuse an element some of the read workspaces' models lack, naming them (D42); none holding
    it is the element's own not-found, as on a read of one workspace."""
    lacking = sorted(workspace for workspace, model in models.items() if not holds(model, key))
    if not lacking:
        return
    if len(lacking) == len(models):
        model = models[lacking[0]]
        if kind == "application":
            get_application(model, key)
        get_object_type(model, key)
    raise api_error(
        422,
        "MODEL_ELEMENT_NOT_IN_EVERY_MODEL",
        f"{'Application' if kind == 'application' else 'Object type'} '{key}' is not in the model "
        f"of every workspace read: {', '.join(lacking)} lack it. Name only the workspaces whose "
        "models hold it",
        {"element": {"kind": kind, "key": key}, "workspaces": lacking},
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


def refuse_as_of(as_of: str | None) -> None:
    """``asOf`` filters by a period one type declares, so it belongs on the routes that list one
    type (D21). Refused rather than ignored, so a lookup never answers undated as if dated."""
    if as_of is None:
        return
    raise api_error(
        422,
        "AS_OF_NOT_SUPPORTED",
        f"asOf applies to one object type's records; ask {PER_TYPE_ROUTE} or {QUERY_ROUTE}",
        {"path": "/query/asOf", "route": PER_TYPE_ROUTE},
    )


def _check_built_in(field_filters: list[tuple[str, str, str]], sort: str | None) -> None:
    """Refuse a filter or sort on a field this list does not hold, naming the list that does."""
    for field, operator, _raw in field_filters:
        if field not in FILTER_FIELDS:
            raise api_error(
                422,
                "INVALID_FILTER",
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
            "INVALID_SORT",
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
