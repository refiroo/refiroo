from typing import Any

from fastapi import APIRouter, Query, Request, Response, status
from sqlalchemy.orm import Session

from ...common.pagination import paginate_statement
from ...engine.change_sets.records import (
    delete_change_set_object,
    put_change_set_object,
    update_change_set_object,
)
from ...engine.model.registry import resolve_change_set_snapshot, resolve_model_snapshot
from ...engine.reads.model_query import (
    Expansion,
    list_expansions,
    list_relation_filters,
    split_relation_filters,
)
from ...engine.reads.object_lookup import (
    build_live_lookup_query,
    build_snapshot_lookup_query,
    lookup_scope,
    refuse_as_of,
)
from ...engine.reads.object_query import build_object_query
from ...engine.reads.snapshot_reads import (
    SnapshotContext,
    build_snapshot_object_query,
    change_set_context,
    find_object,
    object_path,
    object_paths,
    object_scope,
    publication_context,
)
from ...engine.records.audit import object_history
from ...engine.records.context import load_active_projection, load_object
from ...engine.records.deletion import delete_object_record
from ...engine.records.objects import create_object_record, update_object_record
from ...engine.records.rules import get_object_type
from ...engine.workspaces.catalogue import resolve_workspace
from ...errors import api_error
from ...models.commands import (
    ChangeSetObjectUpdate,
    ChangeSetObjectWrite,
    ObjectCreate,
    ObjectUpdate,
)
from ...models.schema import EngineModel
from ..dependencies import DbSession, RequestModelSnapshot
from ..paging import PageQuery, SeekablePageQuery
from ..presenters import (
    audit_event_page,
    build_object_responses,
    change_set_object_response,
)
from ..projections.model_query import expand_records
from ..projections.parent_candidates import parent_candidates
from ..query_parameters import accepts_field_filters
from ..schemas.common import CalendarDate
from ..schemas.queries import QueryObject, TypedObjectPage
from ..schemas.records import AuditEventPage, ObjectPage, ObjectResponse, ParentCandidatePage

router = APIRouter(prefix="/api/v1", tags=["objects"])


def _change_set_write_response(session, change_set_id: str, row) -> ObjectResponse:
    """A change set write's response: the written row with its path, read by direct lookups."""
    context = change_set_context(session, change_set_id)
    return change_set_object_response(
        row,
        change_set_id,
        resolve_change_set_snapshot(session, change_set_id).model,
        path=object_path(session, context, row),
    ).model_copy(
        update={
            "workspaceKey": context.workspace_key,
            "changeSetVersion": context.change_set.version,
        }
    )


def _require_change_set_context(change_set_id: str, expected: int | None) -> int:
    """Guard a write that explicitly targets a change set but omits its optimistic-concurrency version."""
    if expected is None:
        raise api_error(
            409,
            "CHANGE_SET_REQUIRED",
            "expectedChangeSetVersion is required when targeting a change set",
        )
    return expected


@router.post("/objects", response_model=ObjectResponse, status_code=status.HTTP_201_CREATED)
def create_object(
    payload: ObjectCreate, session: DbSession
) -> ObjectResponse:
    attribute_keys = [item.attributeTypeKey for item in payload.attributes]
    if len(attribute_keys) != len(set(attribute_keys)):
        raise api_error(422, "DUPLICATE_ATTRIBUTE", "Object attributes must not repeat a key")
    if payload.changeSetId:
        change_set_id = str(payload.changeSetId)
        expected = _require_change_set_context(change_set_id, payload.expectedChangeSetVersion)
        context = change_set_context(session, change_set_id)
        if payload.workspaceKey is not None and payload.workspaceKey != context.workspace_key:
            raise api_error(
                422,
                "WORKSPACE_CONTEXT_MISMATCH",
                "workspaceKey does not match changeSetId",
                {
                    "workspaceKey": payload.workspaceKey,
                    "contextWorkspaceKey": context.workspace_key,
                },
            )
        row = put_change_set_object(
            session,
            change_set_id,
            ChangeSetObjectWrite(
                id=payload.id,
                applicationKey=payload.applicationKey,
                objectTypeKey=payload.objectTypeKey,
                name=payload.name,
                parentObjectId=payload.parentObjectId,
                attributes={item.attributeTypeKey: item.value for item in payload.attributes},
                initialRelations=payload.initialRelations,
                expectedChangeSetVersion=expected,
                expectedRecordVersion=None,
            ),
        )
        return _change_set_write_response(session, change_set_id, row)
    if payload.workspaceKey is None:
        raise api_error(
            422,
            "WORKSPACE_KEY_REQUIRED",
            "workspaceKey is required for a live (active workspace) write; omit changeSetId "
            "and provide workspaceKey, or target a change set",
        )
    snapshot = resolve_model_snapshot(session)
    item = create_object_record(session, snapshot.model, payload)
    return build_object_responses(session, snapshot.model, [item])[0]


@router.patch("/objects/{object_type_key}/{object_id}", response_model=ObjectResponse)
def update_object(
    object_type_key: str,
    object_id: str,
    payload: ObjectUpdate,
    session: DbSession,
) -> ObjectResponse:
    fields = payload.model_dump(
        exclude={"expectedVersion", "changeSetId", "expectedChangeSetVersion"},
        exclude_unset=True,
    )
    if "attributes" in fields:
        fields["attributes"] = {
            item["attributeTypeKey"]: item["value"] for item in fields["attributes"]
        }
    if payload.changeSetId:
        change_set_id = str(payload.changeSetId)
        expected = _require_change_set_context(change_set_id, payload.expectedChangeSetVersion)
        change_set_payload = ChangeSetObjectUpdate(
            expectedChangeSetVersion=expected, expectedRecordVersion=payload.expectedVersion, **fields
        )
        row = update_change_set_object(
            session, change_set_id, object_id, change_set_payload, object_type_key=object_type_key
        )
        return _change_set_write_response(session, change_set_id, row)
    snapshot = resolve_model_snapshot(session)
    item = update_object_record(session, snapshot.model, object_type_key, object_id, payload)
    return build_object_responses(session, snapshot.model, [item])[0]


@router.delete("/objects/{object_type_key}/{object_id}", status_code=204)
def delete_object(
    object_type_key: str,
    object_id: str,
    session: DbSession,
    change_set_id: str | None = Query(default=None, alias="changeSetId"),
    expected_change_set_version: int | None = Query(
        default=None, alias="expectedChangeSetVersion", ge=1
    ),
    expected_version: int = Query(ge=1, alias="expectedVersion"),
    cascade: bool = False,
    deletion_preview_token: str | None = Query(default=None, alias="deletionPreviewToken"),
) -> Response:
    if change_set_id:
        _require_change_set_context(change_set_id, expected_change_set_version)
        delete_change_set_object(
            session,
            change_set_id,
            object_type_key,
            object_id,
            expected_change_set_version,
            expected_version,
            cascade=cascade,
            deletion_preview=deletion_preview_token,
        )
    else:
        snapshot = resolve_model_snapshot(session)
        delete_object_record(
            session,
            snapshot.model,
            object_type_key,
            object_id,
            expected_version,
            cascade=cascade,
            deletion_preview=deletion_preview_token,
            model_identity=snapshot.model_hash,
        )
    return Response(status_code=204)


_AS_OF = Query(
    default=None,
    alias="asOf",
    description=(
        "A date (YYYY-MM-DD): only records effective on it, by the type's declared effective"
        " period; as_of_not_supported on a type without one"
    ),
)


_EXPAND = Query(
    default=None,
    description=(
        "Repeatable, at most 5: a relation type's key (its outgoing relationships) or reverse key"
        " (its incoming ones) that the type has a binding of, optionally followed by '.' and a"
        " field of the related records (name, an attribute, or ancestor:<type>.<field>). Each item"
        " then carries `expanded`, one entry per key in this order: the first `expandLimit` related"
        " records in name order (each with its name, and the field's value under `field`) and how"
        " many there are; INVALID_EXPAND otherwise"
    ),
)


@router.get(
    "/objects/{object_type_key}",
    response_model=TypedObjectPage,
    openapi_extra={
        "parameters": [
            {
                "name": "filter.<field>.<operator>",
                "in": "query",
                "required": False,
                "description": (
                    "Repeatable schema 0.5 typed filter. Operators and lexical values depend on "
                    "the model-declared field type and filterable capability. A relationship "
                    "(0.9 K6): filter.related:<key>.eq=<record ID>, repeatable, keeps records "
                    "related to any of them; filter.related:<key>.isNull=true those related to "
                    "none, =false those related to any."
                ),
                "schema": {"type": "string"},
            }
        ]
    },
)
@accepts_field_filters
def list_objects(
    object_type_key: str,
    request: Request,
    session: DbSession,
    snapshot: RequestModelSnapshot,
    paging: SeekablePageQuery,
    page_size: int = Query(default=100, ge=1, le=500, alias="pageSize"),
    application_key: str | None = Query(default=None, alias="applicationKey"),
    workspace_key: str | None = Query(default=None, alias="workspaceKey"),
    change_set_id: str | None = Query(default=None, alias="changeSetId"),
    publication_id: str | None = Query(default=None, alias="publicationId"),
    parent_object_id: str | None = Query(default=None, alias="parentObjectId"),
    top_level: bool = Query(
        default=False,
        alias="topLevel",
        description="Only records without a parent; cannot be combined with parentObjectId",
    ),
    search: str | None = None,
    sort: str | None = Query(
        default=None,
        description=(
            "One field: name, id, objectType, (live only) createdAt or updatedAt, a scalar"
            " attribute of the type, ancestor:<type>, or related:<key> where a record holds at most"
            " one such relationship; prefix '-' for descending; name when omitted"
        ),
    ),
    as_of: CalendarDate | None = _AS_OF,
    expand: list[str] | None = _EXPAND,
    expand_limit: int = Query(
        default=3,
        ge=1,
        le=20,
        alias="expandLimit",
        description="How many related records each `expand` entry shows per item",
    ),
) -> TypedObjectPage:
    model = snapshot.model
    expansions = list_expansions(model, object_type_key, expand or [], expand_limit)
    related_filters, field_filters = split_relation_filters(_field_filters(request))
    if change_set_id and publication_id:
        raise api_error(
            422,
            "MUTUALLY_EXCLUSIVE_CONTEXT",
            "changeSetId and publicationId cannot be combined",
        )
    if top_level and parent_object_id:
        raise api_error(
            422,
            "MUTUALLY_EXCLUSIVE_SCOPE",
            "topLevel and parentObjectId cannot be combined",
            {"parameters": ["topLevel", "parentObjectId"]},
        )
    if change_set_id or publication_id:
        context = (
            change_set_context(session, change_set_id)
            if change_set_id
            else publication_context(session, publication_id)
        )
        relations = list_relation_filters(
            model,
            object_type_key,
            related_filters,
            workspace_key=context.workspace_key,
            context=context,
        )
        query = build_snapshot_object_query(
            model,
            context,
            object_type_key=object_type_key,
            application_key=application_key or None,
            parent_object_id=parent_object_id or None,
            search=search or None,
            sort=sort,
            field_filters=field_filters,
            top_level=top_level,
            id_filter=relations.id_filter,
            as_of=as_of,
            session=session,
        )
        page = paginate_statement(
            session,
            query.statement,
            keys=query.keys,
            scope=object_scope(context),
            filters=_bound(query.filters, relations.normalized),
            page=paging,
            page_size=page_size,
            message="Object cursor is invalid",
            rows=True,
            seek=query.seek,
            overlay=query.overlay,
            parts=query.parts,
        )
        paths = object_paths(session, context, page.items)
        records = [
            change_set_object_response(
                row, context.id, model, path=paths[row.object_id]
            ).model_copy(update={"workspaceKey": context.workspace_key})
            for row in page.items
        ]
        return _typed_page(
            session, model, context, context.workspace_key, records, expansions, page.links()
        )
    workspace = resolve_workspace(session, workspace_key)
    workspace_key = workspace.key
    relations = list_relation_filters(
        model, object_type_key, related_filters, workspace_key=workspace_key, context=None
    )
    query = build_object_query(
        model,
        object_type_key=object_type_key,
        application_key=application_key or None,
        workspace_key=workspace_key,
        parent_object_id=parent_object_id or None,
        search=search or None,
        sort=sort,
        field_filters=field_filters,
        top_level=top_level,
        id_filter=relations.id_filter,
        as_of=as_of,
        session=session,
    )
    page = paginate_statement(
        session,
        query.statement,
        keys=query.keys,
        scope="objects",
        filters=_bound(query.filters, relations.normalized),
        page=paging,
        page_size=page_size,
        message="Object cursor is invalid",
        seek=query.seek,
        parts=query.parts,
    )
    records = build_object_responses(session, model, page.items)
    return _typed_page(session, model, None, workspace_key, records, expansions, page.links())


def _bound(filters: dict[str, Any], relations: tuple[tuple[str, str, str], ...]) -> dict[str, Any]:
    """What a cursor binds: the list's filters and, when any, its relationship filters (0.9 K6)."""
    return {**filters, "relationFilters": [list(item) for item in relations]} if relations else filters


def _typed_page(
    session: Session,
    model: EngineModel,
    context: SnapshotContext | None,
    workspace_key: str,
    records: list[ObjectResponse],
    expansions: tuple[Expansion, ...],
    links: dict[str, Any],
) -> TypedObjectPage:
    """The per-type list's page, each record with its relation columns when ``expand`` named any."""
    expanded = expand_records(
        session,
        model,
        context,
        workspace_key=workspace_key,
        anchor_ids=[record.id for record in records],
        expansions=expansions,
    )
    return TypedObjectPage(
        items=[
            QueryObject(**record.model_dump(), expanded=expanded.get(record.id))
            for record in records
        ],
        **links,
    )


_LOOKUP_OBJECT_TYPE_KEYS = Query(
    default=None,
    alias="objectTypeKey",
    description="Repeatable; only records of these object types. Every type when omitted",
)


@router.get(
    "/objects",
    response_model=ObjectPage,
    openapi_extra={
        "parameters": [
            {
                "name": "filter.<field>.<operator>",
                "in": "query",
                "required": False,
                "description": (
                    "Repeatable filter on a built-in field: id, name, objectTypeKey, parentObjectId"
                    " and (live only) createdAt or updatedAt. A model-declared field is refused as"
                    " invalid_filter; filter by it on GET /api/v1/objects/{objectTypeKey}"
                ),
                "schema": {"type": "string"},
            }
        ]
    },
)
@accepts_field_filters
def lookup_objects(
    request: Request,
    session: DbSession,
    snapshot: RequestModelSnapshot,
    paging: SeekablePageQuery,
    page_size: int = Query(default=100, ge=1, le=500, alias="pageSize"),
    object_type_keys: list[str] | None = _LOOKUP_OBJECT_TYPE_KEYS,
    application_key: str | None = Query(default=None, alias="applicationKey"),
    workspace_key: str | None = Query(default=None, alias="workspaceKey"),
    change_set_id: str | None = Query(default=None, alias="changeSetId"),
    publication_id: str | None = Query(default=None, alias="publicationId"),
    parent_object_id: str | None = Query(default=None, alias="parentObjectId"),
    top_level: bool = Query(
        default=False,
        alias="topLevel",
        description="Only records without a parent; cannot be combined with parentObjectId",
    ),
    search: str | None = Query(default=None, description="Case-insensitive match in the name"),
    sort: str | None = Query(
        default=None,
        description=(
            "One built-in field: name, id, objectType, or (live only) createdAt or updatedAt;"
            " prefix '-' for descending; name when omitted"
        ),
    ),
    as_of: str | None = Query(
        default=None,
        alias="asOf",
        description=(
            "Not supported on this list: refused as as_of_not_supported, naming the per-type"
            " route. asOf applies to one object type's records"
        ),
    ),
) -> ObjectPage:
    """Records of any object type in one list: a lookup by name, ID, type, parent or timestamps."""
    model = snapshot.model
    refuse_as_of(as_of)
    if change_set_id and publication_id:
        raise api_error(
            422,
            "MUTUALLY_EXCLUSIVE_CONTEXT",
            "changeSetId and publicationId cannot be combined",
        )
    if top_level and parent_object_id:
        raise api_error(
            422,
            "MUTUALLY_EXCLUSIVE_SCOPE",
            "topLevel and parentObjectId cannot be combined",
            {"parameters": ["topLevel", "parentObjectId"]},
        )
    options = {
        "object_type_keys": object_type_keys or [],
        "application_key": application_key or None,
        "parent_object_id": parent_object_id or None,
        "top_level": top_level,
        "search": search or None,
        "sort": sort,
        "field_filters": _field_filters(request),
    }
    if change_set_id or publication_id:
        context = (
            change_set_context(session, change_set_id)
            if change_set_id
            else publication_context(session, publication_id)
        )
        query = build_snapshot_lookup_query(model, context, **options)
        page = paginate_statement(
            session,
            query.statement,
            keys=query.keys,
            scope=lookup_scope(context),
            filters=query.filters,
            page=paging,
            page_size=page_size,
            message="Object cursor is invalid",
            rows=True,
            seek=query.seek,
            overlay=query.overlay,
            parts=query.parts,
        )
        paths = object_paths(session, context, page.items)
        return ObjectPage(
            items=[
                change_set_object_response(
                    row, context.id, model, path=paths[row.object_id]
                ).model_copy(update={"workspaceKey": context.workspace_key})
                for row in page.items
            ],
            **page.links(),
        )
    workspace = resolve_workspace(session, workspace_key)
    query = build_live_lookup_query(model, workspace_key=workspace.key, **options)
    page = paginate_statement(
        session,
        query.statement,
        keys=query.keys,
        scope=lookup_scope(None),
        filters=query.filters,
        page=paging,
        page_size=page_size,
        message="Object cursor is invalid",
        seek=query.seek,
    )
    return ObjectPage(items=build_object_responses(session, model, page.items), **page.links())


def _field_filters(request: Request) -> list[tuple[str, str, str]]:
    result: list[tuple[str, str, str]] = []
    for key, value in request.query_params.multi_items():
        if not key.startswith("filter."):
            continue
        field_operator = key.removeprefix("filter.")
        if "." not in field_operator:
            raise api_error(
                422,
                "INVALID_FILTER",
                f"Invalid filter parameter '{key}'",
                {"path": f"/query/{key}"},
            )
        field, operator = field_operator.rsplit(".", 1)
        if not field or not operator:
            raise api_error(
                422,
                "INVALID_FILTER",
                f"Invalid filter parameter '{key}'",
                {"path": f"/query/{key}"},
            )
        result.append((field, operator, value))
    return result


@router.get("/objects/{object_type_key}/{object_id}", response_model=ObjectResponse)
def get_object(
    object_type_key: str,
    object_id: str,
    session: DbSession,
    snapshot: RequestModelSnapshot,
    workspace_key: str | None = Query(default=None, alias="workspaceKey"),
    change_set_id: str | None = Query(default=None, alias="changeSetId"),
    publication_id: str | None = Query(default=None, alias="publicationId"),
) -> ObjectResponse:
    model = snapshot.model
    get_object_type(model, object_type_key)
    if change_set_id and publication_id:
        raise api_error(
            422,
            "MUTUALLY_EXCLUSIVE_CONTEXT",
            "changeSetId and publicationId cannot be combined",
        )
    if change_set_id or publication_id:
        context = (
            change_set_context(session, change_set_id)
            if change_set_id
            else publication_context(session, publication_id)
        )
        item = find_object(session, context, object_id, object_type_key)
        if item is None:
            raise api_error(404, "OBJECT_NOT_FOUND", f"Object '{object_id}' not found")
        return change_set_object_response(
            item, context.id, model, path=object_path(session, context, item)
        ).model_copy(update={"workspaceKey": context.workspace_key})
    selected_workspace_key = resolve_workspace(session, workspace_key).key
    item = load_active_projection(session, object_id, object_type_key)
    if item.workspace_key != selected_workspace_key:
        raise api_error(404, "OBJECT_NOT_FOUND", f"Object '{object_id}' not found")
    return build_object_responses(session, model, [item])[0]


_WITHIN_OBJECT_TYPE_KEY = Query(
    default=None,
    alias="withinObjectTypeKey",
    description=(
        "Keep to these types (repeatable): only candidates of these types and, with"
        " includeTypeChanges, only these as the types the record would become; a candidate left"
        " with none is not listed (Base 0.8 C4)"
    ),
)


@router.get(
    "/objects/{object_type_key}/{object_id}/parent-candidates", response_model=ParentCandidatePage
)
def get_parent_candidates(
    object_type_key: str,
    object_id: str,
    session: DbSession,
    snapshot: RequestModelSnapshot,
    paging: PageQuery,
    page_size: int = Query(default=50, ge=1, le=100, alias="pageSize"),
    workspace_key: str | None = Query(default=None, alias="workspaceKey"),
    change_set_id: str | None = Query(default=None, alias="changeSetId"),
    parent_object_type_key: str | None = Query(
        default=None,
        alias="parentObjectTypeKey",
        description="Only candidates of this type, one of those that can contain the record",
    ),
    search: str | None = Query(
        default=None, max_length=500, description="Matches the name or a searchable field"
    ),
    include_type_changes: bool = Query(
        default=False,
        alias="includeTypeChanges",
        description=(
            "In a change set, also list records of types that can contain another type of the"
            " record's application, each with objectTypeKeys, the types the record would become"
            " there (Base 0.8 C3)"
        ),
    ),
    within_object_type_keys: list[str] | None = _WITHIN_OBJECT_TYPE_KEY,
) -> ParentCandidatePage:
    """Records the record could move under, live or in a change set, in name order (Base 0.8 B2).

    Every record of a type the model allows as the record's parent is listed, in its application
    and workspace; one the move would refuse is marked ineligible with its reason (D14). With
    ``includeTypeChanges`` in a change set, records a move with a type change could go under are
    listed as well (C3).
    """
    return parent_candidates(
        session,
        snapshot.model,
        object_type_key=object_type_key,
        object_id=object_id,
        workspace_key=workspace_key,
        change_set_id=change_set_id or None,
        parent_object_type_key=parent_object_type_key or None,
        search=search or None,
        page=paging,
        page_size=page_size,
        include_type_changes=include_type_changes,
        within_object_type_keys=within_object_type_keys,
    )


@router.get("/objects/{object_type_key}/{object_id}/history", response_model=AuditEventPage)
def get_object_history(
    object_type_key: str,
    object_id: str,
    session: DbSession,
    paging: PageQuery,
    page_size: int = Query(default=100, ge=1, le=500, alias="pageSize"),
    change_set_id: str | None = Query(default=None, alias="changeSetId"),
) -> AuditEventPage:
    if change_set_id:
        snapshot = resolve_change_set_snapshot(session, change_set_id)
        get_object_type(snapshot.model, object_type_key)
        context = change_set_context(session, change_set_id)
        item = find_object(session, context, object_id, object_type_key)
        if item is None:
            raise api_error(404, "OBJECT_NOT_FOUND", f"Object '{object_id}' not found")
        return audit_event_page(
            object_history(
                session,
                object_id=item.object_id,
                object_type_key=item.object_type_key,
                workspace_key=context.workspace_key,
                page=paging,
                page_size=page_size,
            )
        )
    snapshot = resolve_model_snapshot(session)
    get_object_type(snapshot.model, object_type_key)
    item = load_object(session, object_id, object_type_key)
    return audit_event_page(
        object_history(
            session,
            object_id=item.id,
            object_type_key=item.object_type_key,
            workspace_key=item.workspace_key,
            page=paging,
            page_size=page_size,
        )
    )
