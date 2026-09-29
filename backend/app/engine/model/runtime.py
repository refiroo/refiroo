"""Access to the singleton model runtime-state row and the release it selects."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from ...errors import api_error
from ...models.database import ModelRelease, ModelRuntimeState

RuntimeSelection = tuple[ModelRuntimeState, ModelRelease]


def find_runtime_state(session: Session) -> RuntimeSelection | None:
    """Return the runtime state joined to its active release, or None when uninitialized."""
    row = session.execute(
        select(ModelRuntimeState, ModelRelease).join(
            ModelRelease,
            ModelRelease.id == ModelRuntimeState.active_model_release_id,
        )
    ).one_or_none()
    if row is None:
        return None
    runtime_state, release = row
    return runtime_state, release


def load_runtime_state(session: Session) -> RuntimeSelection:
    """Read the runtime selection for an API request, reporting 503 when it is missing."""
    selection = find_runtime_state(session)
    if selection is None:
        raise api_error(
            503, "model_runtime_state_unavailable", "Model runtime state is unavailable"
        )
    return selection


def require_runtime_state(session: Session) -> RuntimeSelection:
    """Read the runtime selection where its absence is a broken installation, not a request error."""
    selection = find_runtime_state(session)
    if selection is None:
        raise RuntimeError("Model runtime state has no active installed release")
    return selection
