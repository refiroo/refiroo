from fastapi import APIRouter, Query, Request, Response, status

from ..db import DbSession
from ..errors import api_error
from ..models.api import (
    AuditEventPage,
    ObjectCreate,
    ObjectPage,
    ObjectResponse,
    ObjectUpdate,
    WorkspaceDraftObjectUpdate,
    WorkspaceDraftObjectWrite,
)
from ..services.audit import list_object_history
from ..services.deletion import delete_object_record
from ..services.model.registry import (
    RequestModelSnapshot,
    resolve_draft_snapshot,
    resolve_model_snapshot,
)
from ..services.objects import (
    build_object_query,
    build_object_responses,
    create_object_record,
    get_object_type,
    load_active_projection,
    load_object,
    update_object_record,
)
from ..services.pagination import paginate_statement
from ..services.snapshot_reads import (
    build_snapshot_object_query,
    draft_context,
    find_object,
    object_path,
    object_paths,
    object_scope,
    revision_context,
)
from ..services.workspace_revisions import (
    delete_draft_object,
    put_draft_object,
    update_draft_object,
)
from ..services.workspaces import resolve_workspace
from .paging import PageQuery, SeekablePageQuery

router = APIRouter(prefix="/api/v1", tags=["objects"])


def _draft_object_response(item, draft_id: str, model, *, path=None) -> ObjectResponse:
    attrs = []
    for key, value in (item.attributes or {}).items():
        definition = model.attribute_type(key)
        attrs.append(
            {
                "id": f"{item.object_id}:{key}",
                "attributeTypeKey": key,
                "name": definition.name if definition else key,
                "valueType": definition.valueType if definition else "text",
                "value": value,
            }
        )
    return ObjectResponse(
        id=item.object_id,
        workspaceKey=(getattr(item, "workspace_key", None) or ""),
        applicationKey=item.application_key,
        objectTypeKey=item.object_type_key,
        parentObjectId=item.parent_object_id,
        name=item.name,
        path=path or [],
        attributes=attrs,
        version=item.version,
        # Not recorded for draft and history rows (WP-10K); never substitute the current time.
        createdAt=None,
        updatedAt=None,
    )


def _draft_write_response(session, draft_id: str, row) -> ObjectResponse:
    """A draft write's response: the written row with its path, read by direct lookups."""
    context = draft_context(session, draft_id)
    return _draft_object_response(
        row,
        draft_id,
        resolve_draft_snapshot(session, draft_id).model,
        path=object_path(session, context, row),
    ).model_copy(
        update={
            "workspaceKey": context.workspace_key,
            "workspaceDraftVersion": context.draft.version,
        }
    )


def _require_draft_context(draft_id: str, expected: int | None) -> int:
    """Guard a write that explicitly targets a draft but omits its optimistic-concurrency version."""
    if expected is None:
        raise api_error(
            409,
            "workspace_draft_required",
            "expectedWorkspaceDraftVersion is required when targeting a workspace draft",
        )
    return expected


@router.post("/objects", response_model=ObjectResponse, status_code=status.HTTP_201_CREATED)
def create_object(
    payload: ObjectCreate, session: DbSession
) -> ObjectResponse:
    attribute_keys = [item.attributeTypeKey for item in payload.attributes]
    if len(attribute_keys) != len(set(attribute_keys)):
        raise api_error(422, "duplicate_attribute", "Object attributes must not repeat a key")
    if payload.workspaceDraftId:
        draft_id = str(payload.workspaceDraftId)
        expected = _require_draft_context(draft_id, payload.expectedWorkspaceDraftVersion)
        context = draft_context(session, draft_id)
        if payload.workspaceKey is not None and payload.workspaceKey != context.workspace_key:
            raise api_error(
                422,
                "workspace_context_mismatch",
                "workspaceKey does not match workspaceDraftId",
                {
                    "workspaceKey": payload.workspaceKey,
                    "contextWorkspaceKey": context.workspace_key,
                },
            )
        row = put_draft_object(
            session,
            draft_id,
            WorkspaceDraftObjectWrite(
                id=payload.id,
                applicationKey=payload.applicationKey,
                objectTypeKey=payload.objectTypeKey,
                name=payload.name,
                parentObjectId=payload.parentObjectId,
                attributes={item.attributeTypeKey: item.value for item in payload.attributes},
                initialRelations=payload.initialRelations,
                expectedDraftVersion=expected,
                expectedRecordVersion=None,
            ),
        )
        return _draft_write_response(session, draft_id, row)
    if payload.workspaceKey is None:
        raise api_error(
            422,
            "workspace_key_required",
            "workspaceKey is required for a live (active workspace) write; omit workspaceDraftId "
            "and provide workspaceKey, or target a workspace draft",
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
        exclude={"expectedVersion", "workspaceDraftId", "expectedWorkspaceDraftVersion"},
        exclude_unset=True,
    )
    if "attributes" in fields:
        fields["attributes"] = {
            item["attributeTypeKey"]: item["value"] for item in fields["attributes"]
        }
    if payload.workspaceDraftId:
        draft_id = str(payload.workspaceDraftId)
        expected = _require_draft_context(draft_id, payload.expectedWorkspaceDraftVersion)
        draft_payload = WorkspaceDraftObjectUpdate(
            expectedDraftVersion=expected, expectedRecordVersion=payload.expectedVersion, **fields
        )
        row = update_draft_object(session, draft_id, object_id, draft_payload)
        return _draft_write_response(session, draft_id, row)
    snapshot = resolve_model_snapshot(session)
    item = update_object_record(session, snapshot.model, object_type_key, object_id, payload)
    return build_object_responses(session, snapshot.model, [item])[0]


@router.delete("/objects/{object_type_key}/{object_id}", status_code=204)
def delete_object(
    object_type_key: str,
    object_id: str,
    session: DbSession,
    workspace_draft_id: str | None = Query(default=None, alias="workspaceDraftId"),
    expected_workspace_draft_version: int | None = Query(
        default=None, alias="expectedWorkspaceDraftVersion", ge=1
    ),
    expected_version: int = Query(ge=1, alias="expectedVersion"),
    cascade: bool = False,
    deletion_preview_token: str | None = Query(default=None, alias="deletionPreviewToken"),
) -> Response:
    if workspace_draft_id:
        _require_draft_context(workspace_draft_id, expected_workspace_draft_version)
        delete_draft_object(
            session,
            workspace_draft_id,
            object_type_key,
            object_id,
            expected_workspace_draft_version,
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


@router.get(
    "/objects/{object_type_key}",
    response_model=ObjectPage,
    openapi_extra={
        "parameters": [
            {
                "name": "filter.<field>.<operator>",
                "in": "query",
                "required": False,
                "description": (
                    "Repeatable schema 0.5 typed filter. Operators and lexical values depend on "
                    "the model-declared field type and filterable capability."
                ),
                "schema": {"type": "string"},
            }
        ]
    },
)
def list_objects(
    object_type_key: str,
    request: Request,
    session: DbSession,
    snapshot: RequestModelSnapshot,
    paging: SeekablePageQuery,
    page_size: int = Query(default=100, ge=1, le=500, alias="pageSize"),
    application_key: str | None = Query(default=None, alias="applicationKey"),
    workspace_key: str | None = Query(default=None, alias="workspaceKey"),
    workspace_draft_id: str | None = Query(default=None, alias="workspaceDraftId"),
    workspace_revision_id: str | None = Query(default=None, alias="workspaceRevisionId"),
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
            " attribute of the type, or ancestor:<type>; prefix '-' for descending; name when"
            " omitted"
        ),
    ),
) -> ObjectPage:
    model = snapshot.model
    if workspace_draft_id and workspace_revision_id:
        raise api_error(
            422,
            "mutually_exclusive_context",
            "workspaceDraftId and workspaceRevisionId cannot be combined",
        )
    if top_level and parent_object_id:
        raise api_error(
            422,
            "mutually_exclusive_scope",
            "topLevel and parentObjectId cannot be combined",
            {"parameters": ["topLevel", "parentObjectId"]},
        )
    if workspace_draft_id or workspace_revision_id:
        context = (
            draft_context(session, workspace_draft_id)
            if workspace_draft_id
            else revision_context(session, workspace_revision_id)
        )
        query = build_snapshot_object_query(
            model,
            context,
            object_type_key=object_type_key,
            application_key=application_key or None,
            parent_object_id=parent_object_id or None,
            search=search or None,
            sort=sort,
            field_filters=_field_filters(request),
            top_level=top_level,
        )
        page = paginate_statement(
            session,
            query.statement,
            keys=query.keys,
            scope=object_scope(context),
            filters=query.filters,
            page=paging,
            page_size=page_size,
            message="Object cursor is invalid",
            rows=True,
            seek=query.seek,
        )
        paths = object_paths(session, context, page.items)
        return ObjectPage(
            items=[
                _draft_object_response(
                    row, context.id, model, path=paths[row.object_id]
                ).model_copy(update={"workspaceKey": context.workspace_key})
                for row in page.items
            ],
            **page.links(),
        )
    workspace = resolve_workspace(session, workspace_key)
    workspace_key = workspace.key
    query = build_object_query(
        model,
        object_type_key=object_type_key,
        application_key=application_key or None,
        workspace_key=workspace_key,
        parent_object_id=parent_object_id or None,
        search=search or None,
        sort=sort,
        field_filters=_field_filters(request),
        top_level=top_level,
    )
    page = paginate_statement(
        session,
        query.statement,
        keys=query.keys,
        scope="objects",
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
                "invalid_filter",
                f"Invalid filter parameter '{key}'",
                {"path": f"/query/{key}"},
            )
        field, operator = field_operator.rsplit(".", 1)
        if not field or not operator:
            raise api_error(
                422,
                "invalid_filter",
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
    workspace_draft_id: str | None = Query(default=None, alias="workspaceDraftId"),
    workspace_revision_id: str | None = Query(default=None, alias="workspaceRevisionId"),
) -> ObjectResponse:
    model = snapshot.model
    get_object_type(model, object_type_key)
    if workspace_draft_id and workspace_revision_id:
        raise api_error(
            422,
            "mutually_exclusive_context",
            "workspaceDraftId and workspaceRevisionId cannot be combined",
        )
    if workspace_draft_id or workspace_revision_id:
        context = (
            draft_context(session, workspace_draft_id)
            if workspace_draft_id
            else revision_context(session, workspace_revision_id)
        )
        item = find_object(session, context, object_id, object_type_key)
        if item is None:
            raise api_error(404, "object_not_found", f"Object '{object_id}' not found")
        return _draft_object_response(item, context.id, model).model_copy(
            update={"workspaceKey": context.workspace_key}
        )
    selected_workspace_key = resolve_workspace(session, workspace_key).key
    item = load_active_projection(session, object_id, object_type_key)
    if item.workspace_key != selected_workspace_key:
        raise api_error(404, "object_not_found", f"Object '{object_id}' not found")
    return build_object_responses(session, model, [item])[0]


@router.get("/objects/{object_type_key}/{object_id}/history", response_model=AuditEventPage)
def get_object_history(
    object_type_key: str,
    object_id: str,
    session: DbSession,
    paging: PageQuery,
    page_size: int = Query(default=100, ge=1, le=500, alias="pageSize"),
    workspace_draft_id: str | None = Query(default=None, alias="workspaceDraftId"),
) -> AuditEventPage:
    if workspace_draft_id:
        snapshot = resolve_draft_snapshot(session, workspace_draft_id)
        get_object_type(snapshot.model, object_type_key)
        context = draft_context(session, workspace_draft_id)
        item = find_object(session, context, object_id, object_type_key)
        if item is None:
            raise api_error(404, "object_not_found", f"Object '{object_id}' not found")
        return list_object_history(
            session,
            object_id=item.object_id,
            object_type_key=item.object_type_key,
            workspace_key=context.workspace_key,
            page=paging,
            page_size=page_size,
        )
    snapshot = resolve_model_snapshot(session)
    get_object_type(snapshot.model, object_type_key)
    item = load_object(session, object_id, object_type_key)
    return list_object_history(
        session,
        object_id=item.id,
        object_type_key=item.object_type_key,
        workspace_key=item.workspace_key,
        page=paging,
        page_size=page_size,
    )
