from typing import Literal

from fastapi import APIRouter, Query, status
from sqlalchemy import select

from ..db import DbSession
from ..errors import ApiError, api_error
from ..models.api import (
    WorkspaceCreate,
    WorkspaceDraftActivation,
    WorkspaceDraftCreate,
    WorkspaceDraftModelReleaseUpdate,
    WorkspaceDraftPage,
    WorkspaceDraftResponse,
    WorkspaceDraftUpdate,
    WorkspaceDraftValidation,
    WorkspacePage,
    WorkspaceResponse,
    WorkspaceRetirement,
    WorkspaceRevisionPage,
    WorkspaceRevisionResponse,
    WorkspaceRuntimeStateResponse,
    WorkspaceRuntimeStateUpdate,
    WorkspaceUpdate,
)
from ..models.database import ModelRelease, Workspace, WorkspaceDraft, WorkspaceRevision
from ..services.model.registry import ActiveModelSnapshot, resolve_model_snapshot
from ..services.model.runtime import load_runtime_state
from ..services.pagination import integer_key, paginate_sequence, paginate_statement, text_key
from ..services.workspace_audit import record_draft_validated
from ..services.workspace_revisions import (
    activate_draft,
    change_draft_model_release,
    create_draft,
    discard_draft,
    effective_draft_membership,
    pinned_model,
    retire_publication,
    selected_draft_release,
    update_draft,
    validate_draft,
)
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
from .paging import PageQuery

read_router = APIRouter(prefix="/api/v1", tags=["workspaces"])
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


def _draft_response(session, item: WorkspaceDraft) -> WorkspaceDraftResponse:
    release = session.get(ModelRelease, item.model_release_id)
    source = (
        "currentLive"
        if item.base_id is not None
        else "revision"
        if item.derived_from_revision_id
        else "empty"
    )
    return WorkspaceDraftResponse(
        id=item.id,
        workspaceKey=item.workspace_key,
        name=item.name,
        modelReleaseId=release.public_id if release else str(item.model_release_id),
        modelReleaseKey=release.release_key if release else "unavailable",
        modelReleaseVersion=release.release_version if release else "unavailable",
        source=source,
        derivedFromRevisionId=item.derived_from_revision_id,
        version=item.version,
        createdAt=item.created_at,
        updatedAt=item.updated_at,
    )


def _revision_response(session, item: WorkspaceRevision) -> WorkspaceRevisionResponse:
    release = session.get(ModelRelease, item.model_release_id)
    return WorkspaceRevisionResponse(
        id=item.id,
        workspaceKey=item.workspace_key,
        modelReleaseId=release.public_id if release else str(item.model_release_id),
        revisionNumber=item.revision_number,
        status=item.status,
        derivedFromRevisionId=item.derived_from_revision_id,
        supersedesRevisionId=item.supersedes_revision_id,
        createdAt=item.created_at,
        activatedAt=item.activated_at,
        retiredAt=item.retired_at,
    )


@read_router.get("/workspaces/{workspace_key}/drafts", response_model=WorkspaceDraftPage)
def list_workspace_drafts(
    workspace_key: str,
    session: DbSession,
    paging: PageQuery,
    page_size: int = Query(default=100, ge=1, le=500, alias="pageSize"),
) -> WorkspaceDraftPage:
    load_workspace(session, workspace_key)
    items = list(
        session.scalars(select(WorkspaceDraft).where(WorkspaceDraft.workspace_key == workspace_key))
    )
    page = paginate_sequence(
        items,
        lambda x: (x.created_at.isoformat(), x.id),
        scope="workspace-drafts",
        filters={"workspaceKey": workspace_key},
        page=paging,
        page_size=page_size,
        sort=("createdAt", "id"),
        message="Workspace draft cursor is invalid",
    )
    return WorkspaceDraftPage(
        items=[_draft_response(session, x) for x in page.items], **page.links()
    )


@admin_router.post(
    "/workspaces/{workspace_key}/drafts",
    response_model=WorkspaceDraftResponse,
    status_code=status.HTTP_201_CREATED,
)
def post_workspace_draft(
    workspace_key: str,
    payload: WorkspaceDraftCreate,
    session: DbSession,
) -> WorkspaceDraftResponse:
    selected = (
        selected_draft_release(session, str(payload.modelReleaseId))
        if payload.modelReleaseId
        else None
    )
    active_release_id = (
        load_runtime_state(session)[1].id
        if selected
        else resolve_model_snapshot(session).release_db_id
    )
    return _draft_response(
        session,
        create_draft(
            session,
            workspace_key,
            selected.id if selected else active_release_id,
            name=payload.name,
            source_revision_id=str(payload.derivedFromRevisionId)
            if payload.derivedFromRevisionId
            else None,
            source=payload.source,
            expected_model_runtime_release_id=active_release_id,
            validate_selected_model=selected is not None,
        ),
    )


@read_router.get("/workspace-drafts/{draft_id}", response_model=WorkspaceDraftResponse)
def get_workspace_draft(draft_id: str, session: DbSession) -> WorkspaceDraftResponse:
    # WorkspaceDraft's ORM primary key is the autoincrement sequence_id, so session.get by the
    # stable public id would always miss; resolve through the unique id column instead.
    item = session.scalar(select(WorkspaceDraft).where(WorkspaceDraft.id == draft_id))
    if item is None:
        raise api_error(404, "workspace_draft_not_found", "Workspace draft not found")
    return _draft_response(session, item)


@admin_router.patch("/workspace-drafts/{draft_id}", response_model=WorkspaceDraftResponse)
def patch_workspace_draft(
    draft_id: str, payload: WorkspaceDraftUpdate, session: DbSession
) -> WorkspaceDraftResponse:
    return _draft_response(
        session, update_draft(session, draft_id, payload.expectedVersion, payload.name)
    )


@admin_router.patch(
    "/workspaces/{workspace_key}/drafts/{draft_id}/model-release",
    response_model=WorkspaceDraftResponse,
)
def patch_workspace_draft_model_release(
    workspace_key: str, draft_id: str, payload: WorkspaceDraftModelReleaseUpdate, session: DbSession
) -> WorkspaceDraftResponse:
    return _draft_response(
        session,
        change_draft_model_release(
            session,
            workspace_key,
            draft_id,
            str(payload.modelReleaseId),
            payload.expectedDraftVersion,
        ),
    )


@admin_router.delete("/workspace-drafts/{draft_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_workspace_draft(
    draft_id: str, session: DbSession, expected_version: int = Query(alias="expectedVersion", ge=1)
) -> None:
    discard_draft(session, draft_id, expected_version)


@admin_router.post(
    "/workspace-drafts/{draft_id}/validation", response_model=WorkspaceDraftValidation
)
def validate_workspace_draft(draft_id: str, session: DbSession) -> WorkspaceDraftValidation:
    draft, draft_model = pinned_model(session, draft_id)
    diagnostics = validate_draft(session, draft_id, draft_model)
    # A validation never mutates the draft graph or bumps its version; the audit record is its only
    # side effect and is bounded to identity metadata plus counts (see D3a).  The conflict
    # short-circuit can leave a corrupt base unresolved, so fall back to zero counts instead of
    # failing a validation that already reported its diagnostic.
    try:
        membership = effective_draft_membership(session, draft_id)
        object_count, relation_count = len(membership.objects), len(membership.relations)
    except ApiError:
        object_count, relation_count = 0, 0
    record_draft_validated(
        session,
        draft=draft,
        valid=not diagnostics,
        error_codes=[item["code"] for item in diagnostics],
        object_count=object_count,
        relation_count=relation_count,
        error_count=len(diagnostics),
    )
    session.commit()
    return WorkspaceDraftValidation(valid=not diagnostics, diagnostics=diagnostics)


@admin_router.post(
    "/workspace-drafts/{draft_id}/activation", response_model=WorkspaceRevisionResponse
)
def activate_workspace_draft(
    draft_id: str,
    payload: WorkspaceDraftActivation,
    session: DbSession,
    snapshot: ActiveModelSnapshot,
) -> WorkspaceRevisionResponse:
    _draft, draft_model = pinned_model(session, draft_id)
    revision = activate_draft(
        session,
        draft_id,
        draft_model,
        snapshot.release_db_id,
        payload.expectedDraftVersion,
        str(payload.expectedActiveRevisionId) if payload.expectedActiveRevisionId else None,
    )
    return _revision_response(session, revision)


@read_router.get("/workspaces/{workspace_key}/revisions", response_model=WorkspaceRevisionPage)
def list_workspace_revisions(
    workspace_key: str,
    session: DbSession,
    paging: PageQuery,
    page_size: int = Query(default=100, ge=1, le=500, alias="pageSize"),
) -> WorkspaceRevisionPage:
    load_workspace(session, workspace_key)
    page = paginate_statement(
        session,
        select(WorkspaceRevision).where(WorkspaceRevision.workspace_key == workspace_key),
        keys=(
            integer_key(
                "revisionNumber",
                WorkspaceRevision.revision_number,
                "revision_number",
                descending=True,
            ),
            text_key("id", WorkspaceRevision.id, "id", descending=True),
        ),
        scope="workspace-revisions",
        filters={"workspaceKey": workspace_key},
        page=paging,
        page_size=page_size,
        message="Workspace revision cursor is invalid",
    )
    return WorkspaceRevisionPage(
        items=[_revision_response(session, x) for x in page.items], **page.links()
    )


@read_router.get("/workspace-revisions/{revision_id}", response_model=WorkspaceRevisionResponse)
def get_workspace_revision(revision_id: str, session: DbSession) -> WorkspaceRevisionResponse:
    item = session.scalar(select(WorkspaceRevision).where(WorkspaceRevision.id == revision_id))
    if item is None:
        raise api_error(404, "workspace_revision_not_found", "Workspace revision not found")
    return _revision_response(session, item)


@admin_router.post("/workspaces/{workspace_key}/retirement", status_code=status.HTTP_204_NO_CONTENT)
def retire_workspace_publication(
    workspace_key: str, payload: WorkspaceRetirement, session: DbSession
) -> None:
    retire_publication(session, workspace_key, str(payload.expectedActiveRevisionId))
