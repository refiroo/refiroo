"""A candidate model checked against every workspace running its model (0.11 D25, D37).

A draft's compilation and a release comparison report, besides what activating into the default
workspace would do, one entry per workspace running a release of the candidate's model: that
workspace's key and release, and the compatibility analysis of the candidate against that release
over that workspace's data alone. A retired workspace (no activation reaches it) and one whose
release cannot be loaded (D29) are left out.
"""

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from ...errors import ApiError
from ...models.database import ModelRelease, Workspace, WorkspaceModel
from ...models.schema import EngineModel
from .compatibility import CompatibilityResult, analyze_compatibility
from .registry import ModelSnapshot, model_registry


@dataclass(frozen=True)
class WorkspaceCompatibility:
    workspace_key: str
    release_id: str
    result: CompatibilityResult


@dataclass(frozen=True)
class CandidateCompatibility:
    default: CompatibilityResult
    workspaces: list[WorkspaceCompatibility]


def assess(session: Session, default: ModelSnapshot, candidate: EngineModel) -> CandidateCompatibility:
    """The candidate activated into the default workspace (``default`` is its model), and into each
    workspace running the candidate's model."""
    return CandidateCompatibility(
        analyze_compatibility(
            session, default.model, candidate, default.release_id, [default.workspace_key]
        ),
        by_workspace(session, candidate),
    )


def by_workspace(session: Session, candidate: EngineModel) -> list[WorkspaceCompatibility]:
    """The candidate against each workspace running a release of its model, in workspace key
    order."""
    rows = session.execute(
        select(WorkspaceModel.workspace_key, ModelRelease.id, ModelRelease.public_id)
        .join(ModelRelease, ModelRelease.id == WorkspaceModel.model_release_id)
        .join(Workspace, Workspace.key == WorkspaceModel.workspace_key)
        .where(ModelRelease.release_key == candidate.release.key, Workspace.status != "retired")
        .order_by(WorkspaceModel.workspace_key)
    ).all()
    found = []
    for workspace_key, release_db_id, release_id in rows:
        try:
            current = model_registry.resolve_release(session, release_db_id, require_ready=False).model
        except ApiError:
            continue
        result = analyze_compatibility(session, current, candidate, release_id, [workspace_key])
        found.append(WorkspaceCompatibility(workspace_key, release_id, result))
    return found
