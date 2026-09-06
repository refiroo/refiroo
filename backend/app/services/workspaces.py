"""Authoritative workspace catalogue and singleton default selection."""

from datetime import UTC, datetime

from sqlalchemy import Select, or_, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..common.time import as_utc
from ..errors import api_error
from ..models.api import (
    WorkspaceCreate,
    WorkspaceResponse,
    WorkspaceRuntimeStateResponse,
    WorkspaceUpdate,
)
from ..models.database import Workspace, WorkspaceRuntimeState


def workspace_response(item: Workspace) -> WorkspaceResponse:
    return WorkspaceResponse(
        key=item.key,
        label=item.label,
        status=item.status,
        version=item.version,
        createdAt=as_utc(item.created_at),
        updatedAt=as_utc(item.updated_at),
    )


def runtime_state_response(item: WorkspaceRuntimeState) -> WorkspaceRuntimeStateResponse:
    return WorkspaceRuntimeStateResponse(
        defaultWorkspaceKey=item.default_workspace_key,
        version=item.version,
        updatedAt=as_utc(item.updated_at),
    )


def load_workspace(session: Session, key: str, *, for_update: bool = False) -> Workspace:
    item = session.scalar(
        select(Workspace).where(Workspace.key == key).with_for_update()
        if for_update
        else select(Workspace).where(Workspace.key == key)
    )
    if item is None:
        raise api_error(404, "workspace_not_found", f"Workspace '{key}' not found")
    return item


def load_workspace_runtime_state(
    session: Session, *, for_update: bool = False
) -> WorkspaceRuntimeState:
    statement = select(WorkspaceRuntimeState).where(WorkspaceRuntimeState.id == 1)
    item = session.scalar(statement.with_for_update() if for_update else statement)
    if item is None:  # The migration always creates this row.
        raise api_error(
            500, "workspace_runtime_state_missing", "Workspace runtime state is missing"
        )
    return item


def resolve_workspace(
    session: Session, key: str | None, *, require_active: bool = False
) -> Workspace:
    effective_key = (
        key if key is not None else load_workspace_runtime_state(session).default_workspace_key
    )
    item = load_workspace(session, effective_key)
    if require_active and item.status == "retired":
        raise api_error(
            409,
            "workspace_retired",
            f"Workspace '{item.key}' is retired and cannot be modified",
        )
    return item


def build_workspace_query(
    search: str | None, status: str
) -> tuple[Select[tuple[Workspace]], dict[str, str | None]]:
    normalized_search = search.strip() if search and search.strip() else None
    statement = select(Workspace)
    if status != "all":
        statement = statement.where(Workspace.status == status)
    if normalized_search:
        escaped = normalized_search.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        pattern = f"%{escaped}%"
        statement = statement.where(
            or_(
                Workspace.key.ilike(pattern, escape="\\"),
                Workspace.label.ilike(pattern, escape="\\"),
            )
        )
    return statement, {"search": normalized_search, "status": status}


def create_workspace(session: Session, payload: WorkspaceCreate) -> Workspace:
    key = payload.key.strip()
    label = payload.label.strip()
    item = Workspace(key=key, label=label, status="active")
    session.add(item)
    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        raise api_error(
            409, "workspace_already_exists", f"Workspace '{key}' already exists"
        ) from None
    session.refresh(item)
    return item


def update_workspace(session: Session, key: str, payload: WorkspaceUpdate) -> Workspace:
    # Default switching and retirement lock the singleton first, then the catalogue row. This
    # serializes the cross-row invariant that the selected default is always active. Label-only
    # updates and reactivation do not need to serialize unrelated workspace administration.
    state = (
        load_workspace_runtime_state(session, for_update=True)
        if payload.status == "retired"
        else None
    )
    load_workspace(session, key, for_update=True)
    if state is not None and state.default_workspace_key == key:
        raise api_error(
            409,
            "default_workspace_cannot_be_retired",
            "The default workspace cannot be retired",
        )
    values: dict[str, object] = {
        "version": Workspace.version + 1,
        "updated_at": datetime.now(UTC),
    }
    if payload.label is not None:
        values["label"] = payload.label.strip()
    if payload.status is not None:
        values["status"] = payload.status
    result = session.execute(
        update(Workspace)
        .where(Workspace.key == key, Workspace.version == payload.expectedVersion)
        .values(**values)
    )
    if result.rowcount != 1:
        session.rollback()
        current = load_workspace(session, key)
        raise api_error(
            409,
            "version_conflict",
            "Workspace version has changed",
            {"currentVersion": current.version},
        )
    session.commit()
    return load_workspace(session, key)


def set_default_workspace(
    session: Session, key: str, expected_version: int
) -> WorkspaceRuntimeState:
    load_workspace_runtime_state(session, for_update=True)
    workspace = load_workspace(session, key, for_update=True)
    if workspace.status != "active":
        raise api_error(409, "workspace_retired", "The default workspace must be active")
    result = session.execute(
        update(WorkspaceRuntimeState)
        .where(WorkspaceRuntimeState.id == 1, WorkspaceRuntimeState.version == expected_version)
        .values(
            default_workspace_key=key,
            version=WorkspaceRuntimeState.version + 1,
            updated_at=datetime.now(UTC),
        )
    )
    if result.rowcount != 1:
        session.rollback()
        current = load_workspace_runtime_state(session)
        raise api_error(
            409,
            "version_conflict",
            "Workspace runtime-state version has changed",
            {
                "currentVersion": current.version,
                "defaultWorkspaceKey": current.default_workspace_key,
            },
        )
    session.commit()
    return load_workspace_runtime_state(session)
