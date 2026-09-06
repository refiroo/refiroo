from typing import Annotated

from fastapi import APIRouter, Query, Request, Response, status

from ..db import DbSession
from ..errors import api_error
from ..models.api import (
    AuditEventPage,
    ObjectCreate,
    ObjectPage,
    ObjectResponse,
    ObjectUpdate,
)
from ..services.audit import list_object_history
from ..services.deletion import build_delete_plan, delete_plan_details, execute_delete_plan
from ..services.model.registry import ActiveModelSnapshot
from ..services.objects import (
    build_object_query,
    build_object_responses,
    claim_object_version,
    create_object_record,
    get_object_type,
    load_object,
    update_object_record,
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
    state_filter: Annotated[list[str] | None, Query(alias="state")] = None,
    search: str | None = None,
    sort: str | None = Query(
        default=None,
        description="One built-in or model-declared sortable field; prefix '-' for descending",
    ),
) -> ObjectPage:
    model = snapshot.model
    workspace_key = resolve_workspace(session, workspace_key).key
    query = build_object_query(
        model,
        object_type_key=object_type_key,
        application_key=application_key or None,
        workspace_key=workspace_key,
        parent_object_id=parent_object_id or None,
        states=state_filter,
        search=search or None,
        sort=sort,
        field_filters=_field_filters(request),
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
)
def create_object(
    payload: ObjectCreate, session: DbSession, snapshot: ActiveModelSnapshot
) -> ObjectResponse:
    model = snapshot.model
    item = create_object_record(session, model, payload)
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
    item = load_object(session, object_id, object_type_key)
    return build_object_responses(session, model, [item])[0]


@router.patch("/objects/{object_type_key}/{object_id}", response_model=ObjectResponse)
def update_object(
    object_type_key: str,
    object_id: str,
    payload: ObjectUpdate,
    session: DbSession,
    snapshot: ActiveModelSnapshot,
) -> ObjectResponse:
    model = snapshot.model
    item = update_object_record(session, model, object_type_key, object_id, payload)
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
    item = load_object(session, object_id, object_type_key)
    return list_object_history(
        session,
        object_id=item.id,
        object_type_key=item.object_type_key,
        workspace_key=item.workspace_key,
        cursor=cursor,
        page_size=page_size,
    )


@router.delete("/objects/{object_type_key}/{object_id}", status_code=204)
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
    item = load_object(session, object_id, object_type_key)
    resolve_workspace(session, item.workspace_key, require_active=True)
    claim_object_version(session, item, expected_version)
    plan = build_delete_plan(session, model, item, cascade=True)
    if plan.has_dependents and not cascade:
        raise api_error(
            409,
            "object_has_dependents",
            "Deleting this object requires cascade confirmation",
            delete_plan_details(session, model, plan),
        )
    execute_delete_plan(session, plan)
    session.commit()
    return Response(status_code=204)
