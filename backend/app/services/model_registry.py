from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db import SessionLocal
from ..models.database import ModelRelease, ModelRuntimeState
from ..models.schema import EngineModel


@dataclass(frozen=True)
class ModelSnapshot:
    release_db_id: int
    release_id: str
    model_hash: str
    model: EngineModel


class ModelRegistry:
    def __init__(self) -> None:
        self._models: dict[tuple[str, str], EngineModel] = {}

    def resolve_active(self, session: Session) -> ModelSnapshot:
        row = session.execute(
            select(ModelRuntimeState, ModelRelease).join(
                ModelRelease,
                ModelRelease.id == ModelRuntimeState.active_model_release_id,
            )
        ).one_or_none()
        if row is None:
            raise RuntimeError("Model runtime state has no active installed release")
        _runtime_state, release = row
        cache_key = (release.public_id, release.model_hash)
        model = self._models.get(cache_key)
        if model is None:
            model = EngineModel.model_validate(release.model_json)
            self._models[cache_key] = model
        return ModelSnapshot(
            release_db_id=release.id,
            release_id=release.public_id,
            model_hash=release.model_hash,
            model=model,
        )

    def clear(self) -> None:
        self._models.clear()


model_registry = ModelRegistry()


def resolve_model_snapshot() -> ModelSnapshot:
    with SessionLocal() as session:
        return model_registry.resolve_active(session)


ActiveModelSnapshot = Annotated[ModelSnapshot, Depends(resolve_model_snapshot)]
