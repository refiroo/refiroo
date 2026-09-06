from typing import Literal

from fastapi import APIRouter, Query, status

from ..db import DbSession
from ..models.api import (
    WorkspaceCreate,
    WorkspacePage,
    WorkspaceResponse,
    WorkspaceRuntimeStateResponse,
    WorkspaceRuntimeStateUpdate,
    WorkspaceUpdate,
)
from ..models.database import Workspace
from ..services.pagination import paginate_statement, text_key
from ..services.workspaces import (
    build_workspace_query,
    create_workspace,
    load_workspace,
    load_workspace_runtime_state,
    runtime_state_response,
    set_default_workspace,
    update_workspace,
    workspace_response,
)

read_router = APIRouter(prefix="/api/v1", tags=["workspaces"])
admin_router = APIRouter(prefix="/api/v1", tags=["workspaces"])


@read_router.get("/workspaces", response_model=WorkspacePage)
def list_workspaces(
    session: DbSession,
    search: str | None = None,
    workspace_status: Literal["active", "retired", "all"] = Query(default="active", alias="status"),
    cursor: str | None = None,
    page_size: int = Query(default=100, ge=1, le=500, alias="pageSize"),
) -> WorkspacePage:
    statement, filters = build_workspace_query(search, workspace_status)
    items, next_cursor = paginate_statement(
        session,
        statement,
        keys=(text_key("key", Workspace.key, "key"),),
        scope="workspaces",
        filters=filters,
        cursor=cursor,
        page_size=page_size,
        message="Workspace cursor is invalid",
    )
    return WorkspacePage(items=[workspace_response(item) for item in items], nextCursor=next_cursor)


@read_router.get("/workspaces/{workspace_key}", response_model=WorkspaceResponse)
def get_workspace(workspace_key: str, session: DbSession) -> WorkspaceResponse:
    return workspace_response(load_workspace(session, workspace_key))


@read_router.get("/workspace-runtime-state", response_model=WorkspaceRuntimeStateResponse)
def get_workspace_runtime_state(session: DbSession) -> WorkspaceRuntimeStateResponse:
    return runtime_state_response(load_workspace_runtime_state(session))


@admin_router.post(
    "/workspaces", response_model=WorkspaceResponse, status_code=status.HTTP_201_CREATED
)
def post_workspace(payload: WorkspaceCreate, session: DbSession) -> WorkspaceResponse:
    return workspace_response(create_workspace(session, payload))


@admin_router.patch("/workspaces/{workspace_key}", response_model=WorkspaceResponse)
def patch_workspace(
    workspace_key: str, payload: WorkspaceUpdate, session: DbSession
) -> WorkspaceResponse:
    return workspace_response(update_workspace(session, workspace_key, payload))


@admin_router.patch("/workspace-runtime-state", response_model=WorkspaceRuntimeStateResponse)
def patch_workspace_runtime_state(
    payload: WorkspaceRuntimeStateUpdate, session: DbSession
) -> WorkspaceRuntimeStateResponse:
    return runtime_state_response(
        set_default_workspace(session, payload.defaultWorkspaceKey, payload.expectedVersion)
    )
