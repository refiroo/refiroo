from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from threading import Condition

from sqlalchemy import event, select
from sqlalchemy.orm import Session

from ...db import SessionLocal
from ...errors import api_error
from ...models.database import ChangeSet, ModelRelease, ModelRuntimeState, Publication
from ...models.schema import EngineModel
from .compiler import SUPPORTED_SCHEMA_VERSIONS, parse_model
from .diagnostics import ModelValidationError
from .metadata import clear_metadata_cache
from .runtime import require_runtime_state


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
                "The model pinned by this publication is unavailable",
                {"modelReleaseDbId": release_id},
            )
        if release.schema_version not in SUPPORTED_SCHEMA_VERSIONS:
            raise api_error(
                409,
                "unsupported_pinned_model_schema",
                "The model pinned by this context uses an unsupported schema",
                {
                    "modelReleaseId": release.public_id,
                    "schemaVersion": release.schema_version,
                    "supportedSchemaVersions": sorted(SUPPORTED_SCHEMA_VERSIONS),
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
        if release.schema_version not in SUPPORTED_SCHEMA_VERSIONS:
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
        with self._condition:
            self._models.clear()
            self._ready = True
        clear_metadata_cache()


model_registry = ModelRegistry()


_RESOLVED_ACTIVE_RELEASE = "resolved_active_model_release_db_id"


def resolve_model_snapshot(session: Session) -> ModelSnapshot:
    """Resolve the active model and bind this session's commits to it (see ``_require_resolved_release``)."""
    try:
        snapshot = model_registry.resolve_active(session)
    except ModelRegistryUnavailable as exc:
        raise api_error(
            503,
            "model_registry_unavailable",
            "The active model registry is unavailable",
        ) from exc
    session.info[_RESOLVED_ACTIVE_RELEASE] = snapshot.release_db_id
    return snapshot


@event.listens_for(Session, "before_commit")
def _require_resolved_release(session: Session) -> None:
    require_resolved_release(session)


def require_resolved_release(session: Session) -> None:
    """Refuse to commit a write validated under a release that is no longer active (0.8 W5).

    The registry's publication guard covers only the moment of resolution, so a write resolved
    under release A could otherwise commit after an incompatible release B activated, in this
    process or another one sharing the database. The check runs inside the write transaction after
    its rows are flushed, under a share lock on the runtime-state row, which conflicts with the
    lock activation holds from before its compatibility check until it commits. It runs as the
    session commits; a batch also runs it before it writes its matrix states (0.9.0-alpha.1 PG3b),
    so it holds the share lock before any state row: an activation that drops a matrix shape then
    never waits for a batch's state rows while the batch waits for the activation.
    """
    release_db_id = session.info.get(_RESOLVED_ACTIVE_RELEASE)
    if release_db_id is None:
        return
    session.flush()
    active = session.execute(
        select(ModelRelease.id, ModelRelease.public_id)
        .join(ModelRuntimeState, ModelRuntimeState.active_model_release_id == ModelRelease.id)
        .where(ModelRuntimeState.id == 1)
        .with_for_update(read=True, of=ModelRuntimeState)
    ).one_or_none()
    if active is None or active.id == release_db_id:
        return
    resolved = session.get(ModelRelease, release_db_id)
    raise api_error(
        409,
        "model_release_changed",
        "The active model release changed while this request was processed; nothing was saved. "
        "Reload and retry against the current model",
        {
            "resolvedReleaseId": resolved.public_id if resolved is not None else None,
            "activeReleaseId": active.public_id,
        },
    )


def resolve_request_model(
    session: Session,
    workspace_key: str | None,
    change_set_id: str | None,
    publication_id: str | None,
) -> ModelSnapshot:
    """Resolve the one model authority for a live, change-set or publication read request."""
    if change_set_id and publication_id:
        raise api_error(
            422,
            "mutually_exclusive_context",
            "changeSetId and publicationId cannot be combined",
        )
    if change_set_id:
        context = session.scalar(select(ChangeSet).where(ChangeSet.id == change_set_id))
        if context is None:
            raise api_error(404, "change_set_not_found", "Change set not found")
        if workspace_key is not None and workspace_key != context.workspace_key:
            raise api_error(
                422,
                "workspace_context_mismatch",
                "workspaceKey does not match the selected context",
                {"workspaceKey": workspace_key, "contextWorkspaceKey": context.workspace_key},
            )
        return resolve_pinned_release(session, context.model_release_id)
    if publication_id:
        context = session.scalar(
            select(Publication).where(Publication.id == publication_id)
        )
        if context is None:
            raise api_error(404, "publication_not_found", "Publication not found")
        if workspace_key is not None and workspace_key != context.workspace_key:
            raise api_error(
                422,
                "workspace_context_mismatch",
                "workspaceKey does not match the selected context",
                {"workspaceKey": workspace_key, "contextWorkspaceKey": context.workspace_key},
            )
        return resolve_pinned_release(session, context.model_release_id)
    return resolve_model_snapshot(session)


def resolve_change_set_snapshot(session: Session, change_set_id: str) -> ModelSnapshot:
    """Resolve the immutable model pinned by a change set write after its body-selected context."""
    change_set = session.scalar(select(ChangeSet).where(ChangeSet.id == change_set_id))
    if change_set is None:
        raise api_error(404, "change_set_not_found", "Change set not found")
    return resolve_pinned_release(session, change_set.model_release_id, require_ready=False)


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

