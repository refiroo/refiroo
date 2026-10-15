"""Reads of a workspace's model assignment for the older test modules (0.11 M1, ADR-042)."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.database import WorkspaceModel, WorkspaceRuntimeState

DEFAULT_ACTIVATION = "/api/v1/workspaces/default/model/activation"


def default_model(session: Session) -> WorkspaceModel | None:
    """The default workspace's assignment row: its release and version."""
    return session.scalar(
        select(WorkspaceModel).join(
            WorkspaceRuntimeState,
            WorkspaceRuntimeState.default_workspace_key == WorkspaceModel.workspace_key,
        )
    )
