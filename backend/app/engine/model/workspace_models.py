"""The release each workspace runs (Product 0.11 M1, ADR-042, D4, D30).

Every workspace names its release in ``workspace_models``; nothing follows a default. A workspace is
created on a named release or on the default workspace's; activation (``releases``) moves one
workspace to another release.
"""

from collections.abc import Iterable
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from ...errors import api_error
from ...models.database import ModelRelease, Workspace, WorkspaceModel, WorkspaceRuntimeState
from .compiler import SCHEMA_VERSIONS, SUPPORTED_SCHEMA_VERSIONS

Assignment = tuple[WorkspaceModel, ModelRelease]


def load_assignment(session: Session, workspace_key: str, *, for_update: bool = False) -> Assignment:
    """The workspace's assignment and release; ``for_update`` holds the assignment row, which the
    commit guard of every write in the workspace shares."""
    if for_update:
        # The row is locked alone, then its release read: a lock that waited for another
        # transaction's switch rechecks only the row's own condition, where a join's condition
        # would be checked against the release read before the wait and drop the row (0.11 N1).
        assignment = session.scalar(
            select(WorkspaceModel)
            .where(WorkspaceModel.workspace_key == workspace_key)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        row = (
            None
            if assignment is None
            else (assignment, session.get(ModelRelease, assignment.model_release_id))
        )
    else:
        row = session.execute(
            select(WorkspaceModel, ModelRelease)
            .join(ModelRelease, ModelRelease.id == WorkspaceModel.model_release_id)
            .where(WorkspaceModel.workspace_key == workspace_key)
        ).one_or_none()
    if row is None:
        if session.get(Workspace, workspace_key) is None:
            raise api_error(404, "WORKSPACE_NOT_FOUND", f"Workspace '{workspace_key}' not found")
        raise api_error(
            503,
            "MODEL_REGISTRY_UNAVAILABLE",
            f"Workspace '{workspace_key}' runs no installed release",
            {"workspaceKey": workspace_key},
        )
    assignment, release = row
    return assignment, release


def default_workspace_key(session: Session) -> str:
    return session.scalar(
        select(WorkspaceRuntimeState.default_workspace_key).where(WorkspaceRuntimeState.id == 1)
    )


def default_assignment(session: Session) -> Assignment:
    return load_assignment(session, default_workspace_key(session))


def assign_new_workspace(
    session: Session, workspace_key: str, release_public_id: str | None
) -> WorkspaceModel:
    """The new workspace's assignment: the named release, or the default workspace's (D4, D31)."""
    if release_public_id is None:
        release = default_assignment(session)[1]
    else:
        release = session.scalar(
            select(ModelRelease).where(ModelRelease.public_id == release_public_id)
        )
        if release is None:
            raise api_error(
                404,
                "MODEL_RELEASE_NOT_FOUND",
                f"Model release '{release_public_id}' not found",
            )
        if release.schema_version not in SUPPORTED_SCHEMA_VERSIONS:
            raise api_error(
                422,
                "UNSUPPORTED_SCHEMA_VERSION",
                f"Schema version '{release.schema_version}' cannot be run by a workspace",
                {
                    "releaseId": release.public_id,
                    "schemaVersion": release.schema_version,
                    "supportedSchemaVersions": list(SCHEMA_VERSIONS),
                    "operation": "workspaceCreation",
                },
            )
    assignment = WorkspaceModel(
        workspace_key=workspace_key,
        model_release_id=release.id,
        version=1,
        updated_at=datetime.now(UTC),
    )
    session.add(assignment)
    return assignment


def workspaces_running(session: Session, release_db_id: int) -> list[str]:
    """The keys of the workspaces running a release, in key order."""
    return list(
        session.scalars(
            select(WorkspaceModel.workspace_key)
            .where(WorkspaceModel.model_release_id == release_db_id)
            .order_by(WorkspaceModel.workspace_key)
        )
    )


def assigned_workspaces(session: Session, release_db_ids: Iterable[int]) -> dict[int, list[str]]:
    """For each release, the keys of the workspaces running it, in key order."""
    found: dict[int, list[str]] = {}
    for release_id, workspace_key in session.execute(
        select(WorkspaceModel.model_release_id, WorkspaceModel.workspace_key)
        .where(WorkspaceModel.model_release_id.in_(set(release_db_ids)))
        .order_by(WorkspaceModel.workspace_key)
    ):
        found.setdefault(release_id, []).append(workspace_key)
    return found


def assignments_of(session: Session, workspace_keys: Iterable[str]) -> dict[str, Assignment]:
    """Each workspace's assignment and release, read once for a page of workspaces."""
    return {
        assignment.workspace_key: (assignment, release)
        for assignment, release in session.execute(
            select(WorkspaceModel, ModelRelease)
            .join(ModelRelease, ModelRelease.id == WorkspaceModel.model_release_id)
            .where(WorkspaceModel.workspace_key.in_(set(workspace_keys)))
        ).tuples()
    }
