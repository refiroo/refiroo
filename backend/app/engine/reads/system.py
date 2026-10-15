"""What the deployment runs (``GET /api/v1/system``, 0.9 U3): the database's migration revision and
the default workspace's model release with the time it was selected, read on one session (each
workspace's is ``GET /workspaces/{key}/model``, 0.11 M1)."""

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import text
from sqlalchemy.orm import Session

from ...models.database import ModelRelease
from ..model.workspace_models import default_assignment


@dataclass(frozen=True)
class SystemState:
    revision: str | None
    active_release: ModelRelease
    activated_at: datetime


def read_system_state(session: Session) -> SystemState:
    revision = session.execute(text("SELECT version_num FROM alembic_version")).scalar_one_or_none()
    assignment, release = default_assignment(session)
    # The assignment changes only when a release is activated or its schema is upgraded.
    return SystemState(revision, release, assignment.updated_at)
