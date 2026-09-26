from typing import Literal

from fastapi import APIRouter, Query, status

from ..db import DbSession
from ..models.api import (
    WorkspaceCreate,
    WorkspaceDetailResponse,
    WorkspacePage,
    WorkspaceRuntimeStateResponse,
    WorkspaceRuntimeStateUpdate,
    WorkspaceUpdate,
)
from ..models.database import Workspace
from ..services.pagination import paginate_statement, text_key
from ..services.workspaces import (
    build_workspace_query,
    create_workspace,
    delete_workspace,
    load_workspace,
    load_workspace_runtime_state,
    runtime_state_response,
    set_default_workspace,
    update_workspace,
    workspace_detail_response,
    workspace_response,
)
from .paging import PageQuery

read_router = APIRouter(prefix="/api/v1", tags=["workspaces"])
# Workspace catalogue administration, registered only with WORKSPACE_ADMIN_MUTATIONS_ENABLED.
admin_router = APIRouter(prefix="/api/v1", tags=["workspaces"])


@read_router.get("/workspaces", response_model=WorkspacePage)
def list_workspaces(
    session: DbSession,
    paging: PageQuery,
    search: str | None = None,
    workspace_status: Literal["active", "retired", "all"] = Query(default="active", alias="status"),
    page_size: int = Query(default=100, ge=1, le=500, alias="pageSize"),
) -> WorkspacePage:
    statement, filters = build_workspace_query(search, workspace_status)
    page = paginate_statement(
        session,
        statement,
        keys=(text_key("key", Workspace.key, "key"),),
        scope="workspaces",
        filters=filters,
        page=paging,
        page_size=page_size,
        message="Workspace cursor is invalid",
    )
    return WorkspacePage(
        items=[workspace_response(item) for item in page.items], **page.links()
    )


@read_router.get("/workspaces/{workspace_key}", response_model=WorkspaceDetailResponse)
def get_workspace(workspace_key: str, session: DbSession) -> WorkspaceDetailResponse:
    return workspace_detail_response(session, load_workspace(session, workspace_key))


@read_router.get("/workspace-runtime-state", response_model=WorkspaceRuntimeStateResponse)
def get_workspace_runtime_state(session: DbSession) -> WorkspaceRuntimeStateResponse:
    return runtime_state_response(load_workspace_runtime_state(session))


@admin_router.post(
    "/workspaces", response_model=WorkspaceDetailResponse, status_code=status.HTTP_201_CREATED
)
def post_workspace(payload: WorkspaceCreate, session: DbSession) -> WorkspaceDetailResponse:
    return workspace_detail_response(session, create_workspace(session, payload))


@admin_router.patch("/workspaces/{workspace_key}", response_model=WorkspaceDetailResponse)
def patch_workspace(
    workspace_key: str, payload: WorkspaceUpdate, session: DbSession
) -> WorkspaceDetailResponse:
    return workspace_detail_response(session, update_workspace(session, workspace_key, payload))


@admin_router.delete("/workspaces/{workspace_key}", status_code=status.HTTP_204_NO_CONTENT)
def delete_workspace_route(
    workspace_key: str,
    session: DbSession,
    expected_version: int = Query(alias="expectedVersion", ge=1),
) -> None:
    delete_workspace(session, workspace_key, expected_version)


@admin_router.patch("/workspace-runtime-state", response_model=WorkspaceRuntimeStateResponse)
def patch_workspace_runtime_state(
    payload: WorkspaceRuntimeStateUpdate, session: DbSession
) -> WorkspaceRuntimeStateResponse:
    return runtime_state_response(
        set_default_workspace(session, payload.defaultWorkspaceKey, payload.expectedVersion)
    )
