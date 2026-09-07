from fastapi import APIRouter, Query, Request

from ..db import DbSession
from ..errors import api_error
from ..models.api import (
    AuditEventPage,
    ObjectPage,
    ObjectResponse,
)
from ..services.audit import list_object_history
from ..services.model.registry import ActiveModelSnapshot
from ..services.objects import (
    build_object_query,
    build_object_responses,
    get_object_type,
    load_active_projection,
    load_object,
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


@router.get("/objects/{object_type_key}/{object_id}", response_model=ObjectResponse)
def get_object(
    object_type_key: str,
    object_id: str,
    session: DbSession,
    snapshot: ActiveModelSnapshot,
) -> ObjectResponse:
    model = snapshot.model
    get_object_type(model, object_type_key)
    item = load_active_projection(session, object_id, object_type_key)
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
