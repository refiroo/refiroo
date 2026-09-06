from typing import Literal

from fastapi import APIRouter, Query, Request, Response, status

from ..db import DbSession
from ..errors import api_error
from ..models.api import (
    AuditEventPage,
    ObjectCreate,
    ObjectDraftActivationRequest,
    ObjectDraftCreate,
    ObjectDraftUpdate,
    ObjectPage,
    ObjectResponse,
    ObjectUpdate,
)
from ..services.audit import list_object_history
from ..services.model.registry import ActiveModelSnapshot
from ..services.object_lifecycle import (
    activate_draft,
    clone_revision_to_draft,
    create_root_draft,
    effective_model_release_id,
    load_active_object,
    load_identity,
    retire_active_revision,
    update_draft,
)
from ..services.objects import (
    build_object_query,
    build_object_responses,
    get_object_type,
)
from ..services.pagination import paginate_statement
from ..services.workspaces import resolve_workspace

router = APIRouter(prefix="/api/v1", tags=["objects"])

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
    snapshot: ActiveModelSnapshot,
    cursor: str | None = None,
    page_size: int = Query(default=100, ge=1, le=500, alias="pageSize"),
    application_key: str | None = Query(default=None, alias="applicationKey"),
    workspace_key: str | None = Query(default=None, alias="workspaceKey"),
    parent_object_id: str | None = Query(default=None, alias="parentObjectId"),
    search: str | None = None,
    sort: str | None = Query(
        default=None,
        description="One built-in or model-declared sortable field; prefix '-' for descending",
    ),
    lifecycle: Literal["active", "retired"] = "active",
) -> ObjectPage:
    model = snapshot.model
    workspace_key = resolve_workspace(session, workspace_key).key
    query = build_object_query(
        model,
        object_type_key=object_type_key,
        application_key=application_key or None,
        workspace_key=workspace_key,
        parent_object_id=parent_object_id or None,
        search=search or None,
        sort=sort,
        field_filters=_field_filters(request),
        lifecycle=lifecycle,
    )
    objects, next_cursor = paginate_statement(
        session,
        query.statement,
        keys=query.keys,
        scope="objects",
        filters=query.filters,
        cursor=cursor,
        page_size=page_size,
        message="Object cursor is invalid",
    )
    return ObjectPage(items=build_object_responses(session, model, objects), nextCursor=next_cursor)


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


@router.post(
    "/objects",
    response_model=ObjectResponse,
    status_code=status.HTTP_201_CREATED,
    include_in_schema=False,
)
def create_object(
    payload: ObjectCreate, session: DbSession, snapshot: ActiveModelSnapshot
) -> ObjectResponse:
    model = snapshot.model
    model_release_id = effective_model_release_id(session, snapshot.release_db_id)
    draft = create_root_draft(
        session,
        model,
        model_release_db_id=model_release_id,
        payload=ObjectDraftCreate(
            objectId=payload.id,
            applicationKey=payload.applicationKey,
            objectTypeKey=payload.objectTypeKey,
            name=payload.name,
            workspaceKey=payload.workspaceKey,
            parentObjectId=payload.parentObjectId,
            attributes=payload.attributes,
            requiredRelationships=payload.initialRelations,
        ),
        commit=False,
    )
    activate_draft(
        session,
        model,
        current_model_release_db_id=model_release_id,
        draft_id=draft.id,
        payload=ObjectDraftActivationRequest(
            expectedDraftVersion=draft.version,
            expectedActiveRevisionId=None,
        ),
    )
    item = load_active_object(session, draft.object_id)
    session.refresh(item)
    return build_object_responses(session, model, [item])[0]


@router.get("/objects/{object_type_key}/{object_id}", response_model=ObjectResponse)
def get_object(
    object_type_key: str,
    object_id: str,
    session: DbSession,
    snapshot: ActiveModelSnapshot,
) -> ObjectResponse:
    model = snapshot.model
    get_object_type(model, object_type_key)
    item = load_active_object(session, object_id, object_type_key)
    return build_object_responses(session, model, [item])[0]


@router.patch(
    "/objects/{object_type_key}/{object_id}",
    response_model=ObjectResponse,
    include_in_schema=False,
)
def update_object(
    object_type_key: str,
    object_id: str,
    payload: ObjectUpdate,
    session: DbSession,
    snapshot: ActiveModelSnapshot,
) -> ObjectResponse:
    model = snapshot.model
    model_release_id = effective_model_release_id(session, snapshot.release_db_id)
    item = load_active_object(session, object_id, object_type_key)
    if item.version != payload.expectedVersion:
        raise api_error(409, "version_conflict", "Object version has changed")
    draft = clone_revision_to_draft(
        session,
        model,
        model_release_db_id=model_release_id,
        object_type_key=object_type_key,
        object_id=object_id,
        derived_from_revision_id=item.active_revision_id or "",
        commit=False,
    )
    update_fields: dict = {"expectedVersion": draft.version}
    if payload.name is not None:
        update_fields["name"] = payload.name
    if "parentObjectId" in payload.model_fields_set:
        update_fields["parentObjectId"] = payload.parentObjectId
    if payload.attributes is not None:
        merged = dict(draft.attributes)
        merged.update({value.attributeTypeKey: value.value for value in payload.attributes})
        update_fields["attributes"] = [
            {"attributeTypeKey": key, "value": value} for key, value in merged.items()
        ]
    if len(update_fields) > 1:
        draft = update_draft(
            session,
            model,
            draft.id,
            ObjectDraftUpdate.model_validate(update_fields),
            commit=False,
        )
    activate_draft(
        session,
        model,
        current_model_release_db_id=model_release_id,
        draft_id=draft.id,
        payload=ObjectDraftActivationRequest(
            expectedDraftVersion=draft.version,
            expectedActiveRevisionId=item.active_revision_id,
        ),
    )
    item = load_active_object(session, object_id, object_type_key)
    session.refresh(item)
    return build_object_responses(session, model, [item])[0]


@router.get("/objects/{object_type_key}/{object_id}/history", response_model=AuditEventPage)
def get_object_history(
    object_type_key: str,
    object_id: str,
    session: DbSession,
    snapshot: ActiveModelSnapshot,
    cursor: str | None = None,
    page_size: int = Query(default=100, ge=1, le=500, alias="pageSize"),
) -> AuditEventPage:
    get_object_type(snapshot.model, object_type_key)
    item = load_identity(session, object_id, object_type_key)
    return list_object_history(
        session,
        object_id=item.id,
        object_type_key=item.object_type_key,
        workspace_key=item.workspace_key,
        cursor=cursor,
        page_size=page_size,
    )


@router.delete(
    "/objects/{object_type_key}/{object_id}", status_code=204, include_in_schema=False
)
def delete_object(
    object_type_key: str,
    object_id: str,
    session: DbSession,
    snapshot: ActiveModelSnapshot,
    expected_version: int = Query(ge=1, alias="expectedVersion"),
    cascade: bool = False,
) -> Response:
    model = snapshot.model
    get_object_type(model, object_type_key)
    item = load_active_object(session, object_id, object_type_key)
    resolve_workspace(session, item.workspace_key, require_active=True)
    if item.version != expected_version:
        raise api_error(409, "version_conflict", "Object version has changed")
    retire_active_revision(
        session,
        model,
        object_type_key=object_type_key,
        object_id=object_id,
        expected_active_revision_id=item.active_revision_id or "",
        cascade=cascade,
    )
    return Response(status_code=204)
