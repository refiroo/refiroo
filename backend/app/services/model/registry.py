from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from threading import Condition
from typing import Annotated

from fastapi import Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from ...db import DbSession, SessionLocal
from ...errors import api_error
from ...models.database import ModelRelease, WorkspaceDraft, WorkspaceRevision
from ...models.schema import EngineModel
from .compiler import parse_model
from .diagnostics import ModelValidationError
from .runtime import require_runtime_state

_SUPPORTED_SCHEMA_VERSIONS = {"0.5", "0.6"}


@dataclass(frozen=True)
class ModelSnapshot:
    release_db_id: int
    release_id: str
    model_hash: str
    model: EngineModel


class ModelRegistryUnavailable(RuntimeError):
    pass


class UnsupportedSelectedModelSchema(RuntimeError):
    def __init__(self, schema_version: str) -> None:
        super().__init__(schema_version)
        self.schema_version = schema_version


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

    def resolve_release(
        self, session: Session, release_id: int, *, require_ready: bool = True
    ) -> ModelSnapshot:
        """Resolve an explicitly pinned release without falling back to active authority."""
        if require_ready:
            with self._resolution_guard():
                return self._resolve_release(session, release_id)
        return self._resolve_release(session, release_id)

    def _resolve_release(self, session: Session, release_id: int) -> ModelSnapshot:
        release = session.get(ModelRelease, release_id)
        if release is None:
            raise api_error(
                409,
                "pinned_model_unavailable",
                "The model pinned by this historical context is unavailable",
                {"modelReleaseDbId": release_id},
            )
        if release.schema_version not in _SUPPORTED_SCHEMA_VERSIONS:
            raise api_error(
                409,
                "unsupported_pinned_model_schema",
                "The model pinned by this context uses an unsupported schema",
                {
                    "modelReleaseId": release.public_id,
                    "schemaVersion": release.schema_version,
                    "supportedSchemaVersions": sorted(_SUPPORTED_SCHEMA_VERSIONS),
                },
            )
        cache_key = (release.public_id, release.model_hash)
        with self._condition:
            model = self._models.get(cache_key)
            if model is None:
                try:
                    model = parse_model(release.model_json)
                except ModelValidationError as exc:
                    raise api_error(
                        409,
                        "pinned_model_invalid",
                        "The model pinned by this context is invalid",
                        {
                            "modelReleaseId": release.public_id,
                            "diagnostics": [item.__dict__ for item in exc.diagnostics],
                        },
                    ) from exc
                self._models[cache_key] = model
        return ModelSnapshot(
            release_db_id=release.id,
            release_id=release.public_id,
            model_hash=release.model_hash,
            model=model,
        )

    def _load_active(self, session: Session) -> ModelSnapshot:
        _runtime_state, release = require_runtime_state(session)
        if release.schema_version not in _SUPPORTED_SCHEMA_VERSIONS:
            raise UnsupportedSelectedModelSchema(release.schema_version)
        cache_key = (release.public_id, release.model_hash)
        with self._condition:
            model = self._models.get(cache_key)
            if model is None:
                model = parse_model(release.model_json)
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
        from .metadata import clear_metadata_cache

        with self._condition:
            self._models.clear()
            self._ready = True
        clear_metadata_cache()


model_registry = ModelRegistry()


def resolve_model_snapshot(session: DbSession) -> ModelSnapshot:
    try:
        return model_registry.resolve_active(session)
    except ModelRegistryUnavailable as exc:
        raise api_error(
            503,
            "model_registry_unavailable",
            "The active model registry is unavailable",
        ) from exc


ActiveModelSnapshot = Annotated[ModelSnapshot, Depends(resolve_model_snapshot)]


def resolve_request_model(
    session: DbSession,
    workspace_key: str | None = Query(default=None, alias="workspaceKey"),
    workspace_draft_id: str | None = Query(default=None, alias="workspaceDraftId"),
    workspace_revision_id: str | None = Query(default=None, alias="workspaceRevisionId"),
) -> ModelSnapshot:
    """Resolve the one model authority for a live, draft, or historical read request."""
    if workspace_draft_id and workspace_revision_id:
        raise api_error(
            422,
            "mutually_exclusive_context",
            "workspaceDraftId and workspaceRevisionId cannot be combined",
        )
    if workspace_draft_id:
        context = session.scalar(select(WorkspaceDraft).where(WorkspaceDraft.id == workspace_draft_id))
        if context is None:
            raise api_error(404, "workspace_draft_not_found", "Workspace draft not found")
        if workspace_key is not None and workspace_key != context.workspace_key:
            raise api_error(
                422,
                "workspace_context_mismatch",
                "workspaceKey does not match the selected context",
                {"workspaceKey": workspace_key, "contextWorkspaceKey": context.workspace_key},
            )
        return resolve_pinned_release(session, context.model_release_id)
    if workspace_revision_id:
        context = session.scalar(
            select(WorkspaceRevision).where(WorkspaceRevision.id == workspace_revision_id)
        )
        if context is None:
            raise api_error(404, "workspace_revision_not_found", "Workspace revision not found")
        if workspace_key is not None and workspace_key != context.workspace_key:
            raise api_error(
                422,
                "workspace_context_mismatch",
                "workspaceKey does not match the selected context",
                {"workspaceKey": workspace_key, "contextWorkspaceKey": context.workspace_key},
            )
        return resolve_pinned_release(session, context.model_release_id)
    return resolve_model_snapshot(session)


def resolve_draft_snapshot(session: Session, draft_id: str) -> ModelSnapshot:
    """Resolve the immutable model pinned by a draft write after its body-selected context."""
    draft = session.scalar(select(WorkspaceDraft).where(WorkspaceDraft.id == draft_id))
    if draft is None:
        raise api_error(404, "workspace_draft_not_found", "Workspace draft not found")
    return resolve_pinned_release(session, draft.model_release_id, require_ready=False)


def resolve_pinned_release(
    session: Session, release_id: int, *, require_ready: bool = True
) -> ModelSnapshot:
    """Expose pinned resolution through the same structured readiness boundary as active reads."""
    try:
        return model_registry.resolve_release(
            session, release_id, require_ready=require_ready
        )
    except ModelRegistryUnavailable as exc:
        raise api_error(
            503,
            "model_registry_unavailable",
            "The model registry is unavailable",
        ) from exc


RequestModelSnapshot = Annotated[ModelSnapshot, Depends(resolve_request_model)]
