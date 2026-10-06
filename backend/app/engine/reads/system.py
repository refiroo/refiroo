"""What the deployment runs (``GET /api/v1/system``, 0.9 U3): the database's migration revision and
the active model release with the time it was selected, read on one session."""

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import text
from sqlalchemy.orm import Session

from ...models.database import ModelRelease
from ..model.runtime import load_runtime_state


@dataclass(frozen=True)
class SystemState:
    revision: str | None
    active_release: ModelRelease
    activated_at: datetime


def read_system_state(session: Session) -> SystemState:
    revision = session.execute(text("SELECT version_num FROM alembic_version")).scalar_one_or_none()
    runtime_state, active_release = load_runtime_state(session)
    # The runtime state changes only when a release is activated or its schema is upgraded.
    return SystemState(revision, active_release, runtime_state.updated_at)
