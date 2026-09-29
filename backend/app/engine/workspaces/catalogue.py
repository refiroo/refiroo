"""Authoritative workspace catalogue and singleton default selection."""

from datetime import UTC, datetime
from typing import Literal

from sqlalchemy import Select, delete, event, func, or_, select, update
from sqlalchemy.exc import IntegrityError, OperationalError
from sqlalchemy.orm import Session

from ...errors import ApiError, api_error
from ...models.commands import WorkspaceCreate, WorkspaceUpdate
from ...models.database import (
    ChangeSet,
    Publication,
    RdmObject,
    RelationSetVersion,
    Workspace,
    WorkspaceRuntimeState,
)
from ..indexes import matrix_states

DeleteBlocker = Literal["default", "published", "notEmpty"]


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
    if require_active:
        _require_active(item)
        session.info.setdefault(_RESOLVED_ACTIVE_WORKSPACES, set()).add(item.key)
    return item


_RESOLVED_ACTIVE_WORKSPACES = "resolved_active_workspace_keys"


def _require_active(item: Workspace) -> None:
    if item.status == "retired":
        raise api_error(
            409,
            "workspace_retired",
            f"Workspace '{item.key}' is retired and cannot be modified",
        )


@event.listens_for(Session, "before_commit")
def _require_resolved_workspaces(session: Session) -> None:
    """Refuse to commit a write into a workspace deleted or retired since it was resolved (0.8 W6).

    A write resolves its workspace before it writes, so a deletion or retirement could otherwise
    commit in between and leave rows under a missing or retired key; SQLite foreign keys are not
    enforced at runtime. The reread runs after the flush, inside the write transaction, so on SQLite
    it holds the writer lock that deletion also takes before its checks.
    """
    keys = session.info.get(_RESOLVED_ACTIVE_WORKSPACES)
    if not keys:
        return
    session.flush()
    for key in sorted(keys):
        current = session.execute(
            select(Workspace.key, Workspace.status).where(Workspace.key == key)
        ).one_or_none()
        if current is None:
            raise api_error(
                404,
                "workspace_not_found",
                f"Workspace '{key}' was deleted while this request was processed; nothing was saved",
            )
        if current.status == "retired":
            raise api_error(
                409,
                "workspace_retired",
                f"Workspace '{key}' was retired while this request was processed; nothing was saved",
            )


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
        session.flush()
        matrix_states.sync_workspace(session, key)
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


def delete_blocker(
    session: Session, key: str, default_key: str
) -> tuple[DeleteBlocker | None, dict[str, int]]:
    """Return why ``key`` may not be deleted, in the order the refusals are reported (D27)."""
    if key == default_key:
        return "default", {}
    # Publications are withdrawn, never removed, so any row means the workspace was published.
    if session.scalar(select(Publication.id).where(Publication.workspace_key == key).limit(1)):
        return "published", {}
    counts = {
        "objectCount": session.scalar(
            select(func.count()).select_from(RdmObject).where(RdmObject.workspace_key == key)
        )
        or 0,
        "changeSetCount": session.scalar(
            select(func.count()).select_from(ChangeSet).where(ChangeSet.workspace_key == key)
        )
        or 0,
    }
    if counts["objectCount"] or counts["changeSetCount"]:
        return "notEmpty", counts
    return None, counts


def delete_workspace(session: Session, key: str, expected_version: int) -> None:
    """Delete a workspace nothing refers to, so a mistyped key can be corrected (ADR-019, D27).

    The checks and the delete run in one transaction under SQLite's database-wide writer
    reservation (row locks elsewhere), so no object, change set or publication can be added between
    them; a live write that resolved the workspace earlier rechecks it before it commits
    (``_require_resolved_workspaces``). Foreign keys are not enforced on SQLite, so the cascading
    relation-set versions are removed explicitly.
    """
    if session.bind is not None and session.bind.dialect.name == "sqlite":
        session.rollback()
        try:
            session.connection().exec_driver_sql("BEGIN IMMEDIATE")
        except OperationalError as exc:
            session.rollback()
            raise api_error(
                409,
                "workspace_delete_retry",
                "Other changes are being saved; retry deleting the workspace after they finish",
            ) from exc
    try:
        _require_deletable(session, key, expected_version)
    except ApiError:
        session.rollback()  # Release the writer reservation; a refusal changes nothing.
        raise
    session.execute(delete(RelationSetVersion).where(RelationSetVersion.workspace_key == key))
    matrix_states.drop_workspace(session, key)
    session.execute(delete(Workspace).where(Workspace.key == key))
    session.commit()


def _require_deletable(session: Session, key: str, expected_version: int) -> None:
    state = load_workspace_runtime_state(session, for_update=True)
    workspace = load_workspace(session, key, for_update=True)
    blocker, counts = delete_blocker(session, key, state.default_workspace_key)
    if blocker == "default":
        raise api_error(
            409,
            "workspace_is_default",
            "The default workspace cannot be deleted. Make another workspace the default first",
        )
    if blocker == "published":
        raise api_error(
            409,
            "workspace_has_publications",
            f"Workspace '{key}' has been published and cannot be deleted; retire it instead",
        )
    if blocker == "notEmpty":
        raise api_error(
            409,
            "workspace_not_empty",
            f"Workspace '{key}' still has objects or change sets. Delete its objects and discard "
            "its change sets first, or retire it",
            counts,
        )
    if workspace.version != expected_version:
        raise api_error(
            409,
            "version_conflict",
            "Workspace version has changed",
            {"currentVersion": workspace.version},
        )
