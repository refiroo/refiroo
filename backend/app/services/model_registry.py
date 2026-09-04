from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from threading import Condition
from typing import Annotated

from fastapi import Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db import SessionLocal
from ..errors import api_error
from ..models.database import ModelRelease, ModelRuntimeState
from ..models.schema import EngineModel


@dataclass(frozen=True)
class ModelSnapshot:
    release_db_id: int
    release_id: str
    model_hash: str
    model: EngineModel


class ModelRegistryUnavailable(RuntimeError):
    pass


class ModelRegistry:
    def __init__(self) -> None:
        self._models: dict[tuple[str, str], EngineModel] = {}
        self._condition = Condition()
        self._active_readers = 0
        self._publishing = False
        self._ready = True

    def resolve_active(self, session: Session) -> ModelSnapshot:
        with self._resolution_guard():
            return self._load_active(session)

    def _load_active(self, session: Session) -> ModelSnapshot:
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
        with self._condition:
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

    @contextmanager
    def _resolution_guard(self) -> Iterator[None]:
        with self._condition:
            while self._publishing:
                self._condition.wait()
            if not self._ready:
                raise ModelRegistryUnavailable("The active model registry is unhealthy")
            self._active_readers += 1
        try:
            yield
        finally:
            with self._condition:
                self._active_readers -= 1
                if self._active_readers == 0:
                    self._condition.notify_all()

    @contextmanager
    def publication_guard(self) -> Iterator[None]:
        """Keep request resolution outside the commit-to-publication window."""
        with self._condition:
            self._publishing = True
            while self._active_readers:
                self._condition.wait()
        try:
            yield
        finally:
            with self._condition:
                self._publishing = False
                self._condition.notify_all()

    def refresh_active(self) -> ModelSnapshot:
        """Publish the committed database selection into this process registry."""
        with SessionLocal() as session:
            snapshot = self._load_active(session)
        return snapshot

    def mark_unhealthy(self) -> None:
        with self._condition:
            self._ready = False

    @property
    def ready(self) -> bool:
        with self._condition:
            return self._ready

    def clear(self) -> None:
        with self._condition:
            self._models.clear()
            self._ready = True


model_registry = ModelRegistry()


def resolve_model_snapshot() -> ModelSnapshot:
    try:
        with SessionLocal() as session:
            return model_registry.resolve_active(session)
    except ModelRegistryUnavailable as exc:
        raise api_error(
            503,
            "model_registry_unavailable",
            "The active model registry is unavailable",
        ) from exc


ActiveModelSnapshot = Annotated[ModelSnapshot, Depends(resolve_model_snapshot)]
