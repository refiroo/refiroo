from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from ...db import SessionLocal
from ...models.database import ModelRelease, Workspace, WorkspaceModel
from ...models.schema import EngineModel
from .releases import ReleaseIdentityConflict, install_model_release


def bootstrap_model(model: EngineModel) -> ModelRelease:
    with SessionLocal() as session:
        release = ensure_bootstrap_release(session, model)
        session.commit()
        return release


def ensure_bootstrap_release(session: Session, model: EngineModel) -> ModelRelease:
    """Install the bootstrap model and give it to every workspace that runs no release yet: on a
    new database, the default workspace the baseline migration created (0.11 M1)."""
    try:
        release, _created = install_model_release(session, model)
    except ReleaseIdentityConflict as exc:
        raise RuntimeError(
            "Bootstrap model release identity conflict: "
            f"{model.release.key}@{model.release.version} has different installed content"
        ) from exc

    unassigned = session.scalars(
        select(Workspace.key)
        .where(~Workspace.key.in_(select(WorkspaceModel.workspace_key)))
        .order_by(Workspace.key)
    ).all()
    now = datetime.now(UTC)
    for key in unassigned:
        session.add(
            WorkspaceModel(workspace_key=key, model_release_id=release.id, version=1, updated_at=now)
        )
    session.flush()
    return release
