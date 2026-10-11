"""Authoritative workspace catalogue and singleton default selection."""

from datetime import UTC, datetime
from typing import Literal

from sqlalchemy import Select, delete, event, func, or_, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ...errors import ApiError, api_error
from ...models.commands import WorkspaceCreate, WorkspaceUpdate
from ...models.database import (
    AuditEvent,
    ChangeSet,
    IdempotencyKey,
    Publication,
    RdmObject,
    RelationSetVersion,
    Workspace,
    WorkspaceRuntimeState,
)
from ..events.subscription_rules import has_subscriptions, suspend_for_retired_workspace
from ..indexes import matrix_states

DeleteBlocker = Literal["default", "published", "notEmpty", "subscribed"]


def load_workspace(session: Session, key: str, *, for_update: bool = False) -> Workspace:
    item = session.scalar(
        select(Workspace).where(Workspace.key == key).with_for_update()
        if for_update
        else select(Workspace).where(Workspace.key == key)
    )
    if item is None:
        raise api_error(404, "WORKSPACE_NOT_FOUND", f"Workspace '{key}' not found")
    return item


def load_workspace_runtime_state(
    session: Session, *, for_update: bool = False
) -> WorkspaceRuntimeState:
    statement = select(WorkspaceRuntimeState).where(WorkspaceRuntimeState.id == 1)
    item = session.scalar(statement.with_for_update() if for_update else statement)
    if item is None:  # The migration always creates this row.
        raise api_error(
            500, "WORKSPACE_RUNTIME_STATE_MISSING", "Workspace runtime state is missing"
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
            "WORKSPACE_RETIRED",
            f"Workspace '{item.key}' is retired and cannot be modified",
        )


@event.listens_for(Session, "before_commit")
def _require_resolved_workspaces(session: Session) -> None:
    """Refuse to commit a write into a workspace deleted or retired since it was resolved (0.8 W6).

    A write resolves its workspace before it writes, so a deletion or retirement could otherwise
    commit in between and leave rows under a retired key, or end in a foreign key failure on a
    deleted one. The reread runs after the flush, inside the write transaction.
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
                "WORKSPACE_NOT_FOUND",
                f"Workspace '{key}' was deleted while this request was processed; nothing was saved",
            )
        if current.status == "retired":
            raise api_error(
                409,
                "WORKSPACE_RETIRED",
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
            409, "WORKSPACE_ALREADY_EXISTS", f"Workspace '{key}' already exists"
        ) from None
    session.refresh(item)
    return item


def update_workspace(session: Session, key: str, payload: WorkspaceUpdate) -> Workspace:
    # Default switching and retirement lock the catalogue row, then the singleton: the lock order
    # of live writes, which recheck the runtime state as they commit (ARCHITECTURE). This
    # serializes the cross-row invariant that the selected default is always active. Label-only
    # updates and reactivation do not need to serialize unrelated workspace administration.
    load_workspace(session, key, for_update=True)
    state = (
        load_workspace_runtime_state(session, for_update=True)
        if payload.status == "retired"
        else None
    )
    if state is not None and state.default_workspace_key == key:
        raise api_error(
            409,
            "DEFAULT_WORKSPACE_CANNOT_BE_RETIRED",
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
            "VERSION_CONFLICT",
            "Workspace version has changed",
            {"currentVersion": current.version},
        )
    if payload.status == "retired":
        suspend_for_retired_workspace(session, key)
    session.commit()
    return load_workspace(session, key)


def set_default_workspace(
    session: Session, key: str, expected_version: int
) -> WorkspaceRuntimeState:
    workspace = load_workspace(session, key, for_update=True)
    load_workspace_runtime_state(session, for_update=True)
    if workspace.status != "active":
        raise api_error(409, "WORKSPACE_RETIRED", "The default workspace must be active")
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
            "VERSION_CONFLICT",
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
    # A workspace change never removes another owner's configuration (C11, C-D99).
    if has_subscriptions(session, key):
        return "subscribed", counts
    return None, counts


def delete_workspace(session: Session, key: str, expected_version: int) -> None:
    """Delete a workspace nothing refers to, so a mistyped key can be corrected (ADR-019, D27).

    The checks and the delete run in one transaction holding the workspace and runtime-state rows
    for update. A live write holds the workspace lock (``LiveWrites._begin``), so it either commits
    first, and the checks see its rows, or waits and is then refused as deleted. Any other row
    naming the workspace takes a key share lock on it through its foreign key, so a write adding
    one commits first or waits and then fails its foreign key. Relation-set versions cascade with the
    workspace; they are deleted here first, as are its matrix states, which have no foreign key.

    Its feed leaves with it (0.9 D208): the audit entries stay as history but lose their workspace
    and feed position, so a workspace created again under the key starts a clean feed at 1 and its
    readers never see the deleted one's changes; its consumer events and deriver checkpoint cascade
    with the row. Its idempotency keys go too, so a retried request under the new workspace never
    replays the deleted one's job.
    """
    try:
        _require_deletable(session, key, expected_version)
    except ApiError:
        session.rollback()  # Release the row locks; a refusal changes nothing.
        raise
    session.execute(delete(RelationSetVersion).where(RelationSetVersion.workspace_key == key))
    matrix_states.drop_workspace(session, key)
    session.execute(
        update(AuditEvent)
        .where(AuditEvent.workspace_key == key)
        .values(workspace_key=None, feed_position=None)
        .execution_options(synchronize_session=False)
    )
    session.execute(delete(IdempotencyKey).where(IdempotencyKey.workspace_key == key))
    session.execute(delete(Workspace).where(Workspace.key == key))
    session.commit()


def _require_deletable(session: Session, key: str, expected_version: int) -> None:
    workspace = load_workspace(session, key, for_update=True)
    state = load_workspace_runtime_state(session, for_update=True)
    blocker, counts = delete_blocker(session, key, state.default_workspace_key)
    if blocker == "default":
        raise api_error(
            409,
            "WORKSPACE_IS_DEFAULT",
            "The default workspace cannot be deleted. Make another workspace the default first",
        )
    if blocker == "published":
        raise api_error(
            409,
            "WORKSPACE_HAS_PUBLICATIONS",
            f"Workspace '{key}' has been published and cannot be deleted; retire it instead",
        )
    if blocker == "notEmpty":
        raise api_error(
            409,
            "WORKSPACE_NOT_EMPTY",
            f"Workspace '{key}' still has objects or change sets. Delete its objects and discard "
            "its change sets first, or retire it",
            counts,
        )
    if blocker == "subscribed":
        raise api_error(
            409,
            "WORKSPACE_HAS_SUBSCRIPTIONS",
            f"Workspace '{key}' has webhook subscriptions. Delete them first, or retire the workspace",
        )
    if workspace.version != expected_version:
        raise api_error(
            409,
            "VERSION_CONFLICT",
            "Workspace version has changed",
            {"currentVersion": workspace.version},
        )
