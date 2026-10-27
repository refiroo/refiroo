from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from ...db import SessionLocal
from ...models.database import ModelRelease, Workspace, WorkspaceModel
from ...models.schema import EngineModel
from .releases import ReleaseIdentityConflict, install_model_release


class BootstrapReleaseConflict(RuntimeError):
    """The bootstrap model's release key and version are installed with other content, which the
    engine does not overwrite: the file changed without a new version, or the stored release is of a
    schema that left the window."""

    def __init__(self, release_key: str, release_version: str, stored_schema_version: str) -> None:
        self.release_key = release_key
        self.release_version = release_version
        self.stored_schema_version = stored_schema_version
        super().__init__(
            "Bootstrap model release identity conflict: "
            f"{release_key}@{release_version} has different installed content"
        )


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
        stored = session.scalar(
            select(ModelRelease.schema_version).where(
                ModelRelease.release_key == exc.release_key,
                ModelRelease.release_version == exc.release_version,
            )
        )
        raise BootstrapReleaseConflict(exc.release_key, exc.release_version, stored or "") from exc

    unassigned = session.scalars(
        select(Workspace.key)
        .where(~Workspace.key.in_(select(WorkspaceModel.workspace_key)))
        .order_by(Workspace.key)
    ).all()
    now = datetime.now(UTC)
    for key in unassigned:
        session.add(
            WorkspaceModel(
                workspace_key=key, model_release_id=release.id, version=1, updated_at=now
            )
        )
    session.flush()
    return release
