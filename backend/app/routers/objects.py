from fastapi import APIRouter, Query, Request, Response, status

from ..db import DbSession
from ..errors import api_error
from ..models.api import (
    AuditEventPage,
    ChangeSetObjectUpdate,
    ChangeSetObjectWrite,
    ObjectCreate,
    ObjectPage,
    ObjectResponse,
    ObjectUpdate,
    ParentCandidatePage,
)
from ..services.audit import list_object_history
from ..services.change_sets import (
    delete_change_set_object,
    put_change_set_object,
    update_change_set_object,
)
from ..services.deletion import delete_object_record
from ..services.model.registry import (
    RequestModelSnapshot,
    resolve_change_set_snapshot,
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
from ..services.parent_candidates import parent_candidates
from ..services.snapshot_reads import (
    build_snapshot_object_query,
    change_set_context,
    find_object,
    object_path,
    object_paths,
    object_scope,
    publication_context,
)
from ..services.workspaces import resolve_workspace
from .paging import PageQuery, SeekablePageQuery

router = APIRouter(prefix="/api/v1", tags=["objects"])


def _change_set_object_response(item, change_set_id: str, model, *, path=None) -> ObjectResponse:
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
        # Not recorded for change set and history rows (WP-10K); never substitute the current time.
        createdAt=None,
        updatedAt=None,
    )


def _change_set_write_response(session, change_set_id: str, row) -> ObjectResponse:
    """A change set write's response: the written row with its path, read by direct lookups."""
    context = change_set_context(session, change_set_id)
    return _change_set_object_response(
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
            "change_set_required",
            "expectedChangeSetVersion is required when targeting a change set",
        )
    return expected


@router.post("/objects", response_model=ObjectResponse, status_code=status.HTTP_201_CREATED)
def create_object(
    payload: ObjectCreate, session: DbSession
) -> ObjectResponse:
    attribute_keys = [item.attributeTypeKey for item in payload.attributes]
    if len(attribute_keys) != len(set(attribute_keys)):
        raise api_error(422, "duplicate_attribute", "Object attributes must not repeat a key")
    if payload.changeSetId:
        change_set_id = str(payload.changeSetId)
        expected = _require_change_set_context(change_set_id, payload.expectedChangeSetVersion)
        context = change_set_context(session, change_set_id)
        if payload.workspaceKey is not None and payload.workspaceKey != context.workspace_key:
            raise api_error(
                422,
                "workspace_context_mismatch",
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
            "workspace_key_required",
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
        row = update_change_set_object(session, change_set_id, object_id, change_set_payload)
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
            " attribute of the type, or ancestor:<type>; prefix '-' for descending; name when"
            " omitted"
        ),
    ),
) -> ObjectPage:
    model = snapshot.model
    if change_set_id and publication_id:
        raise api_error(
            422,
            "mutually_exclusive_context",
            "changeSetId and publicationId cannot be combined",
        )
    if top_level and parent_object_id:
        raise api_error(
            422,
            "mutually_exclusive_scope",
            "topLevel and parentObjectId cannot be combined",
            {"parameters": ["topLevel", "parentObjectId"]},
        )
    if change_set_id or publication_id:
        context = (
            change_set_context(session, change_set_id)
            if change_set_id
            else publication_context(session, publication_id)
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
            overlay=query.overlay,
        )
        paths = object_paths(session, context, page.items)
        return ObjectPage(
            items=[
                _change_set_object_response(
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
    change_set_id: str | None = Query(default=None, alias="changeSetId"),
    publication_id: str | None = Query(default=None, alias="publicationId"),
) -> ObjectResponse:
    model = snapshot.model
    get_object_type(model, object_type_key)
    if change_set_id and publication_id:
        raise api_error(
            422,
            "mutually_exclusive_context",
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
            raise api_error(404, "object_not_found", f"Object '{object_id}' not found")
        return _change_set_object_response(
            item, context.id, model, path=object_path(session, context, item)
        ).model_copy(update={"workspaceKey": context.workspace_key})
    selected_workspace_key = resolve_workspace(session, workspace_key).key
    item = load_active_projection(session, object_id, object_type_key)
    if item.workspace_key != selected_workspace_key:
        raise api_error(404, "object_not_found", f"Object '{object_id}' not found")
    return build_object_responses(session, model, [item])[0]


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
) -> ParentCandidatePage:
    """Records the record could move under, live or in a change set, in name order (Base 0.8 B2).

    Every record of a type the model allows as the record's parent is listed, in its application
    and workspace; one the move would refuse is marked ineligible with its reason (D14).
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
