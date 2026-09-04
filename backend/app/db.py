from pathlib import Path

from alembic.config import Config
from sqlalchemy import create_engine, select, update
from sqlalchemy.orm import Session, sessionmaker

from alembic import command

from .config import database_url
from .models.database import ModelRelease, ModelRuntimeState
from .models.schema import EngineModel
from .services.model_releases import ReleaseIdentityConflict, install_model_release

engine = create_engine(database_url())
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)


def create_database() -> None:
    config = Config()
    config.set_main_option("script_location", str(Path(__file__).resolve().parent / "migrations"))
    config.set_main_option("sqlalchemy.url", database_url().replace("%", "%%"))
    command.upgrade(config, "head")


def bootstrap_model(model: EngineModel) -> ModelRelease:
    with SessionLocal() as session:
        release = ensure_bootstrap_release(session, model)
        session.commit()
        return release


def ensure_bootstrap_release(session: Session, model: EngineModel) -> ModelRelease:
    try:
        release, _created = install_model_release(session, model)
    except ReleaseIdentityConflict as exc:
        raise RuntimeError(
            "Bootstrap model release identity conflict: "
            f"{model.release.key}@{model.release.version} has different installed content"
        ) from exc

    state = session.get(ModelRuntimeState, 1)
    if state is None:
        legacy_active = list(
            session.scalars(select(ModelRelease).where(ModelRelease.is_active.is_(True)))
        )
        if len(legacy_active) > 1:
            raise RuntimeError(
                "Cannot initialize model runtime state: multiple legacy active releases exist"
            )
        selected_release = legacy_active[0] if legacy_active else release
        state = ModelRuntimeState(id=1, active_model_release_id=selected_release.id, version=1)
        session.add(state)
        session.flush()

    _sync_legacy_active_flag(session, state.active_model_release_id)
    return release


def _sync_legacy_active_flag(session: Session, active_release_id: int) -> None:
    session.execute(update(ModelRelease).values(is_active=False))
    session.execute(
        update(ModelRelease)
        .where(ModelRelease.id == active_release_id)
        .values(is_active=True)
    )
