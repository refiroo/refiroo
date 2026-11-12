from dataclasses import replace
from typing import Literal

from fastapi import APIRouter, Query, Request, status
from fastapi.responses import JSONResponse
from sqlalchemy import Integer, select
from sqlalchemy.orm import Session

from ...common.pagination import PageRequest, integer_key, paginate_statement, text_key
from ...engine.authorization.administration import known_groups
from ...engine.authorization.permissions import Permissions
from ...engine.authorization.visibility import in_workspaces
from ...engine.model.workspace_models import assignments_of, load_assignment
from ...engine.reads.feed import read_feed
from ...engine.sources.dry_run import InvalidDraft
from ...engine.workspaces.catalogue import (
    build_workspace_query,
    create_workspace,
    delete_workspace,
    load_workspace,
    load_workspace_runtime_state,
    set_default_workspace,
    update_workspace,
)
from ...engine.workspaces.from_workbook import UnsupportedDraftSchema, create_from_workbook
from ...errors import api_error
from ...models.commands import WorkspaceCreate, WorkspaceFromWorkbook, WorkspaceUpdate
from ...models.database import ModelRelease, Workspace, WorkspaceModel
from ..access import (
    INSTANCE,
    SIGNED_IN,
    WORKSPACE_PATH,
    AuthorizedRoute,
    CurrentPermissions,
    forbidden,
    requires,
)
from ..dependencies import CurrentPrincipal, DbSession
from ..paging import PageQuery
from ..presenters import (
    diagnostic_details,
    feed_page,
    job_responses,
    runtime_state_response,
    workspace_assignment_response,
    workspace_detail_response,
    workspace_page_items,
)
from ..projections.home import own_workspace_items
from ..schemas.records import FeedPage
from ..schemas.workspaces import (
    OwnWorkspacePage,
    WorkspaceAssignmentPage,
    WorkspaceAssignmentResponse,
    WorkspaceDetailResponse,
    WorkspaceFromWorkbookResponse,
    WorkspacePage,
    WorkspaceRuntimeStateResponse,
    WorkspaceRuntimeStateUpdate,
)

read_router = APIRouter(route_class=AuthorizedRoute, prefix="/api/v1", tags=["workspaces"])
# Workspace catalogue administration, registered only with WORKSPACE_ADMIN_MUTATIONS_ENABLED.
admin_router = APIRouter(route_class=AuthorizedRoute, prefix="/api/v1", tags=["workspaces"])
# A workspace made from a workbook's draft also installs a model and starts an import: registered
# only when workspace administration, model administration and integration jobs are all enabled.
from_workbook_router = APIRouter(route_class=AuthorizedRoute, prefix="/api/v1", tags=["workspaces"])


def workspace_page(
    session: Session,
    permissions: Permissions,
    paging: PageRequest,
    *,
    search: str | None,
    workspace_status: Literal["active", "retired", "all"],
    holding: str | None,
    page_size: int,
) -> WorkspacePage:
    """A page of the workspaces the caller may see; the route's and the agent tool's one query."""
    statement, filters = build_workspace_query(search, workspace_status)
    groups = frozenset(known_groups([holding])) if holding is not None else None
    if holding is not None:
        filters["holding"] = holding
    visible = in_workspaces(Workspace.key, permissions, groups)
    if visible is not None:
        statement = statement.where(visible)
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
    return WorkspacePage(items=workspace_page_items(session, page.items), **page.links())


@read_router.get("/workspaces", response_model=WorkspacePage)
@requires("workspaces.list", at=SIGNED_IN)
def list_workspaces(
    session: DbSession,
    permissions: CurrentPermissions,
    paging: PageQuery,
    search: str | None = None,
    workspace_status: Literal["active", "retired", "all"] = Query(default="active", alias="status"),
    holding: str | None = Query(
        default=None,
        description="Only the workspaces where the caller holds this action group (D327)",
    ),
    page_size: int = Query(default=100, ge=1, le=500, alias="pageSize"),
) -> WorkspacePage:
    return workspace_page(
        session,
        permissions,
        paging,
        search=search,
        workspace_status=workspace_status,
        holding=holding,
        page_size=page_size,
    )


@read_router.get("/me/workspaces", response_model=OwnWorkspacePage)
@requires("signed-in", at=SIGNED_IN)
def list_own_workspaces(
    session: DbSession,
    principal: CurrentPrincipal,
    permissions: CurrentPermissions,
    paging: PageQuery,
    page_size: int = Query(default=50, ge=1, le=500, alias="pageSize"),
) -> OwnWorkspacePage:
    """The active workspaces where the caller holds Browse, the default first and then by label,
    each with its applications and the open change sets waiting there (0.12 HM1, D332)."""
    default_key = load_workspace_runtime_state(session).default_workspace_key
    statement = select(Workspace).where(Workspace.status == "active")
    visible = in_workspaces(Workspace.key, permissions, frozenset({"browse"}))
    if visible is not None:
        statement = statement.where(visible)
    first = replace(
        integer_key("default", (Workspace.key != default_key).cast(Integer), "key"),
        extract=lambda _session, row: int(row.key != default_key),
    )
    page = paginate_statement(
        session,
        statement,
        keys=(
            first,
            text_key("label", Workspace.label, "label"),
            text_key("key", Workspace.key, "key"),
        ),
        scope="own-workspaces",
        filters={"defaultWorkspaceKey": default_key},
        page=paging,
        page_size=page_size,
        message="Workspace cursor is invalid",
    )
    return OwnWorkspacePage(
        items=own_workspace_items(session, principal, permissions, page.items, default_key),
        **page.links(),
    )


@read_router.get("/workspaces/{workspace_key}", response_model=WorkspaceDetailResponse)
@requires("workspace.read", at=WORKSPACE_PATH)
def get_workspace(workspace_key: str, session: DbSession) -> WorkspaceDetailResponse:
    return workspace_detail_response(session, load_workspace(session, workspace_key))


@read_router.get("/workspaces/{workspace_key}/model", response_model=WorkspaceAssignmentResponse)
@requires("model.read", at=WORKSPACE_PATH)
def get_workspace_model(workspace_key: str, session: DbSession) -> WorkspaceAssignmentResponse:
    """The release the workspace runs and its assignment's version (0.11 M1, ADR-042)."""
    return workspace_assignment_response(load_assignment(session, workspace_key))


@read_router.get("/workspace-models", response_model=WorkspaceAssignmentPage)
@requires("workspaces.list", at=SIGNED_IN)
def list_workspace_models(
    session: DbSession,
    permissions: CurrentPermissions,
    paging: PageQuery,
    release_key: str | None = Query(default=None, alias="releaseKey"),
    release_id: str | None = Query(default=None, alias="releaseId"),
    page_size: int = Query(default=100, ge=1, le=500, alias="pageSize"),
) -> WorkspaceAssignmentPage:
    """Every workspace's assignment in workspace key order, of one model (``releaseKey``) or one
    release (``releaseId``) when named (0.11 M1)."""
    statement = select(WorkspaceModel).join(
        ModelRelease, ModelRelease.id == WorkspaceModel.model_release_id
    )
    if release_key is not None:
        statement = statement.where(ModelRelease.release_key == release_key)
    if release_id is not None:
        statement = statement.where(ModelRelease.public_id == release_id)
    visible = in_workspaces(WorkspaceModel.workspace_key, permissions, None)
    if visible is not None:
        statement = statement.where(visible)
    page = paginate_statement(
        session,
        statement,
        keys=(text_key("workspaceKey", WorkspaceModel.workspace_key, "workspace_key"),),
        scope="workspace-models",
        filters={"releaseKey": release_key, "releaseId": release_id},
        page=paging,
        page_size=page_size,
        message="Workspace model cursor is invalid",
    )
    assignments = assignments_of(session, (item.workspace_key for item in page.items))
    return WorkspaceAssignmentPage(
        items=[
            workspace_assignment_response(assignments[item.workspace_key]) for item in page.items
        ],
        **page.links(),
    )


FeedKind = Literal["object", "relation", "publication"]
_FEED_KIND = Query(default=None, description="Entries of these kinds only (repeatable)")
_FEED_OBJECT_TYPE_KEY = Query(
    default=None,
    alias="objectTypeKey",
    description="Object entries of these types only, a reclassified record's previous type "
    "included (repeatable)",
)


@read_router.get("/workspaces/{workspace_key}/feed", response_model=FeedPage)
@requires("feed.read", at=WORKSPACE_PATH)
def get_feed(
    workspace_key: str,
    session: DbSession,
    request: Request,
    after: int = Query(default=0, ge=0, description="The last position the reader processed"),
    page_size: int = Query(default=500, ge=1, le=1000, alias="pageSize"),
    kind: list[FeedKind] | None = _FEED_KIND,
    object_type_key: list[str] | None = _FEED_OBJECT_TYPE_KEY,
) -> FeedPage:
    """Every change to the workspace's live data in commit order, after a stored position
    (INTEGRATION_API F4). A filtered page scans at most ten pages' worth of positions. A position
    older than ``FEED_RETENTION_DAYS`` is ``410 FEED_POSITION_EXPIRED``, naming the active
    publication to re-read (F5)."""
    return feed_page(
        session,
        read_feed(
            session,
            workspace_key,
            after=after,
            page_size=page_size,
            retention_days=request.app.state.feed_retention_days,
            kinds=kind or (),
            object_type_keys=object_type_key or (),
        ),
    )


@read_router.get("/workspace-runtime-state", response_model=WorkspaceRuntimeStateResponse)
@requires("signed-in", at=SIGNED_IN)
def get_workspace_runtime_state(session: DbSession) -> WorkspaceRuntimeStateResponse:
    return runtime_state_response(load_workspace_runtime_state(session))


@admin_router.post(
    "/workspaces", response_model=WorkspaceDetailResponse, status_code=status.HTTP_201_CREATED
)
@requires("workspaces.manage", at=INSTANCE)
def post_workspace(payload: WorkspaceCreate, session: DbSession) -> WorkspaceDetailResponse:
    return workspace_detail_response(session, create_workspace(session, payload))


@from_workbook_router.post(
    "/workspaces/from-workbook", response_model=WorkspaceFromWorkbookResponse, status_code=202
)
@requires("workspaces.create-from-workbook", at=INSTANCE)
def post_workspace_from_workbook(
    payload: WorkspaceFromWorkbook,
    request: Request,
    session: DbSession,
    permissions: CurrentPermissions,
) -> JSONResponse:
    """Create a workspace from the model draft a workbook made, and load the workbook.

    One step for what the separate routes do in turn: the draft is installed as a release (its
    release version raised when the key and version are another model's; its import profile's key
    made free), the workspace is created on that release, and the draft's workbook is queued as an
    import into the workspace's live data (policy `independent`: a refused row is reported and the
    rest load). Answers 202 with the workspace, the release and the import job; follow the job at
    `GET /jobs/{jobId}`. Everything before the job is one transaction. Needs the groups of the
    separate steps together: Workspace administration, an instance-wide Install a model or Model
    release, and an instance-wide Bulk and import (the new workspace has no grants of its own yet).
    Refused: `409 VERSION_CONFLICT` (the draft changed), `422 INVALID_MODEL` with the draft's
    diagnostics, `422 INVALID_IMPORT_PROFILE` with the profile's problems, `422
    DRAFT_HAS_NO_WORKBOOK`, `409 SOURCE_FILE_PROFILE_NOT_READY`, `409 WORKSPACE_ALREADY_EXISTS`,
    `404 MODEL_DRAFT_NOT_FOUND`, `422 UNSUPPORTED_SCHEMA_VERSION`.
    """
    if not (permissions.allows("model-install", None) or permissions.allows("model-release", None)):
        raise forbidden("model.install", ("model-release", "model-install"), None)
    if not permissions.allows("bulk", None):
        raise forbidden("bulk.write", ("bulk",), None)
    limits = request.app.state.batch_limits
    try:
        created = create_from_workbook(
            session,
            draft_id=payload.draftId,
            expected_version=payload.expectedVersion,
            name=payload.name,
            key=payload.key,
            files=request.app.state.job_files,
            max_bytes=limits.import_max_bytes,
            retention_days=limits.retention_days,
        )
    except InvalidDraft as invalid:
        raise api_error(
            422,
            "INVALID_MODEL",
            "Model draft is invalid and cannot be installed",
            diagnostic_details(invalid.diagnostics),
        ) from None
    except UnsupportedDraftSchema as unsupported:
        raise api_error(
            422,
            "UNSUPPORTED_SCHEMA_VERSION",
            f"Model draft uses schema version '{unsupported.schema_version}', which this"
            " deployment does not support",
            {
                "draftId": unsupported.draft_id,
                "schemaVersion": unsupported.schema_version,
                "operation": "install",
            },
        ) from None
    worker = getattr(request.app.state, "job_worker", None)
    if worker is not None:
        worker.wake()
    answer = WorkspaceFromWorkbookResponse(
        workspace=workspace_detail_response(session, created.workspace),
        releaseId=created.release.public_id,
        releaseKey=created.release.release_key,
        releaseVersion=created.release.release_version,
        job=job_responses(session, [created.job])[0],
    )
    return JSONResponse(answer.model_dump(mode="json"), status_code=202)


@admin_router.patch("/workspaces/{workspace_key}", response_model=WorkspaceDetailResponse)
@requires("workspaces.manage", at=INSTANCE)
def patch_workspace(
    workspace_key: str, payload: WorkspaceUpdate, session: DbSession
) -> WorkspaceDetailResponse:
    return workspace_detail_response(session, update_workspace(session, workspace_key, payload))


@admin_router.delete("/workspaces/{workspace_key}", status_code=status.HTTP_204_NO_CONTENT)
@requires("workspaces.manage", at=INSTANCE)
def delete_workspace_route(
    workspace_key: str,
    session: DbSession,
    expected_version: int = Query(alias="expectedVersion", ge=1),
) -> None:
    delete_workspace(session, workspace_key, expected_version)


@admin_router.patch("/workspace-runtime-state", response_model=WorkspaceRuntimeStateResponse)
@requires("workspaces.manage", at=INSTANCE)
def patch_workspace_runtime_state(
    payload: WorkspaceRuntimeStateUpdate, session: DbSession
) -> WorkspaceRuntimeStateResponse:
    return runtime_state_response(
        set_default_workspace(session, payload.defaultWorkspaceKey, payload.expectedVersion)
    )
