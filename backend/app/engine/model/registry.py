import logging
from collections.abc import Callable
from dataclasses import dataclass, replace
from threading import Lock

from sqlalchemy import event, select
from sqlalchemy.orm import Session

from ...db import SessionLocal
from ...errors import api_error
from ...models.database import (
    ChangeSet,
    ModelRelease,
    ObjectRelation,
    Publication,
    RdmObject,
    Workspace,
    WorkspaceModel,
    WorkspaceRuntimeState,
)
from ...models.schema import EngineModel
from .compiler import SCHEMA_VERSIONS, SUPPORTED_SCHEMA_VERSIONS, parse_model
from .diagnostics import ModelValidationError
from .metadata import clear_metadata_cache

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ModelSnapshot:
    release_db_id: int
    release_id: str
    model_hash: str
    model: EngineModel
    # The workspace whose model this is; None for a release read by its ID alone.
    workspace_key: str | None = None


class ModelRegistryUnavailable(RuntimeError):
    pass


@dataclass(frozen=True)
class UnavailableWorkspaceModel:
    """A release some workspace runs that this process cannot serve (0.11 D29, D34)."""

    release_db_id: int
    release_id: str
    schema_version: str
    diagnostics: tuple[dict, ...] = ()

    @property
    def unsupported_schema(self) -> bool:
        return self.schema_version not in SUPPORTED_SCHEMA_VERSIONS


class WorkspaceModelUnavailable(RuntimeError):
    def __init__(self, workspace_key: str, unavailable: UnavailableWorkspaceModel) -> None:
        super().__init__(workspace_key)
        self.workspace_key = workspace_key
        self.unavailable = unavailable


class ModelRegistry:
    """Parsed releases, one per release, for every workspace and pinned context of this process.

    A workspace resolves its own release (ADR-042); a release this process cannot serve makes only
    the workspaces running it unavailable (D29). ``ready`` is false when the database could not be
    prepared at startup, or when no assigned release can be served.
    """

    def __init__(self) -> None:
        self._models: dict[tuple[str, str], EngineModel] = {}
        self._unavailable: dict[tuple[str, str], UnavailableWorkspaceModel] = {}
        self._lock = Lock()
        self._ready = True
        self._servable = True
        # Run once when the process becomes servable after being not (0.12 R, R-F9).
        self._on_servable: list[Callable[[], None]] = []

    def resolve_workspace(self, session: Session, workspace_key: str | None) -> ModelSnapshot:
        """The model of ``workspace_key`` (the default workspace when ``None``)."""
        self._require_ready()
        return self._load_workspace(session, workspace_key)

    def resolve_release(
        self, session: Session, release_id: int, *, require_ready: bool = True
    ) -> ModelSnapshot:
        """Resolve an explicitly pinned release, whichever workspace runs it."""
        if require_ready:
            self._require_ready()
        return self._resolve_release(session, release_id)

    def _resolve_release(self, session: Session, release_id: int) -> ModelSnapshot:
        release = session.get(ModelRelease, release_id)
        if release is None:
            raise api_error(
                409,
                "PINNED_MODEL_UNAVAILABLE",
                "The model pinned by this publication is unavailable",
                {"modelReleaseDbId": release_id},
            )
        if release.schema_version not in SUPPORTED_SCHEMA_VERSIONS:
            raise api_error(
                409,
                "UNSUPPORTED_PINNED_MODEL_SCHEMA",
                "The model pinned by this context uses an unsupported schema",
                {
                    "modelReleaseId": release.public_id,
                    "schemaVersion": release.schema_version,
                    "supportedSchemaVersions": list(SCHEMA_VERSIONS),
                },
            )
        try:
            model = self._parsed(release)
        except ModelValidationError as exc:
            raise api_error(
                409,
                "PINNED_MODEL_INVALID",
                "The model pinned by this context is invalid",
                {
                    "modelReleaseId": release.public_id,
                    "diagnostics": [item.__dict__ for item in exc.diagnostics],
                },
            ) from exc
        return _snapshot(release, model)

    def _parsed(self, release: ModelRelease) -> EngineModel:
        cache_key = (release.public_id, release.model_hash)
        with self._lock:
            model = self._models.get(cache_key)
            if model is None:
                model = parse_model(release.model_json)
                self._models[cache_key] = model
        return model

    def _load_workspace(self, session: Session, workspace_key: str | None) -> ModelSnapshot:
        key = workspace_key
        if key is None:
            key = session.scalar(
                select(WorkspaceRuntimeState.default_workspace_key).where(
                    WorkspaceRuntimeState.id == 1
                )
            )
        row = session.execute(
            select(Workspace.key, ModelRelease)
            .outerjoin(WorkspaceModel, WorkspaceModel.workspace_key == Workspace.key)
            .outerjoin(ModelRelease, ModelRelease.id == WorkspaceModel.model_release_id)
            .where(Workspace.key == key)
        ).one_or_none()
        if row is None:
            raise api_error(404, "WORKSPACE_NOT_FOUND", f"Workspace '{key}' not found")
        _key, release = row
        if release is None:
            raise ModelRegistryUnavailable(f"Workspace '{key}' runs no installed release")
        unavailable = self._unavailable_release(release)
        if unavailable is not None:
            raise WorkspaceModelUnavailable(key, unavailable)
        return replace(_snapshot(release, self._parsed(release)), workspace_key=key)

    def _unavailable_release(self, release: ModelRelease) -> UnavailableWorkspaceModel | None:
        """Why this process cannot serve ``release``, or None; a failed parse is remembered."""
        if release.schema_version not in SUPPORTED_SCHEMA_VERSIONS:
            return UnavailableWorkspaceModel(release.id, release.public_id, release.schema_version)
        cache_key = (release.public_id, release.model_hash)
        with self._lock:
            known = self._unavailable.get(cache_key)
        if known is not None:
            return known
        try:
            self._parsed(release)
        except ModelValidationError as exc:
            known = UnavailableWorkspaceModel(
                release.id,
                release.public_id,
                release.schema_version,
                tuple(item.__dict__ for item in exc.diagnostics),
            )
            with self._lock:
                self._unavailable[cache_key] = known
            return known
        return None

    def unavailability(self, release: ModelRelease) -> UnavailableWorkspaceModel | None:
        """Why this process cannot serve ``release`` (None when it can), as a workspace's request
        would find it; nothing is raised (0.12 UW1)."""
        return self._unavailable_release(release)

    def _assigned_unavailable(
        self, session: Session
    ) -> tuple[int, list[UnavailableWorkspaceModel]]:
        """How many releases some workspace runs, and the ones this process cannot serve."""
        releases = list(
            session.scalars(
                select(ModelRelease)
                .where(ModelRelease.id.in_(select(WorkspaceModel.model_release_id)))
                .order_by(ModelRelease.id)
            )
        )
        found = [item for item in map(self._unavailable_release, releases) if item is not None]
        return len(releases), found

    def start(self, session: Session) -> list[UnavailableWorkspaceModel]:
        """Load every release a workspace runs, at startup; the ones this process cannot serve.

        The instance is not ``ready`` when there are releases to serve and none of them can be.
        """
        assigned, found = self._assigned_unavailable(session)
        with self._lock:
            self._servable = not assigned or len(found) < assigned
        return found

    def refresh_servable(self, session: Session) -> bool:
        """Read the assignments again: whether this process can serve some workspace now. A raising
        in this process or another (R-F9), or a release assigned since, changes it; when the process
        becomes servable, the callbacks of ``when_servable`` run, once (0.12 R)."""
        assigned, found = self._assigned_unavailable(session)
        servable = not assigned or len(found) < assigned
        with self._lock:
            became = servable and not self._servable
            self._servable = servable
            callbacks = list(self._on_servable) if became else []
            if became:
                self._on_servable.clear()
        for callback in callbacks:
            try:
                callback()
            except Exception:
                logger.exception("Starting the background threads of a servable process failed")
        return servable

    def when_servable(self, callback: Callable[[], None]) -> None:
        """Call ``callback`` once, when a refresh finds this process able to serve a workspace it
        could not before: the background threads that need a servable model start then."""
        with self._lock:
            self._on_servable.append(callback)

    def forget_servable_callbacks(self) -> None:
        with self._lock:
            self._on_servable.clear()

    def unavailable_assigned(self, session: Session) -> list[UnavailableWorkspaceModel]:
        """The releases some workspace runs that this process cannot serve, as its heartbeat
        reports them (0.11 O1, D192). A release not parsed yet is parsed now, as its workspace's
        next request would."""
        releases = session.scalars(
            select(ModelRelease)
            .where(ModelRelease.id.in_(select(WorkspaceModel.model_release_id)))
            .order_by(ModelRelease.id)
        )
        return [item for item in map(self._unavailable_release, releases) if item is not None]

    def warm(self, release_db_id: int) -> None:
        """Parse a newly assigned release into this process registry (after an activation). Other
        processes parse it on their first request in the workspace, which reads its assignment
        (0.11 N1, D165)."""
        with SessionLocal() as session:
            release = session.get(ModelRelease, release_db_id)
            if release is None:
                raise ModelRegistryUnavailable(f"Model release {release_db_id} is not installed")
            unavailable = self._unavailable_release(release)
            if unavailable is not None:
                raise ModelRegistryUnavailable(
                    f"Model release {release.public_id} cannot be served"
                )

    def withdraw(self, release: ModelRelease) -> None:
        """Serve no workspace on ``release`` until this process restarts: it could not be loaded
        after an activation committed it (0.11 D29)."""
        with self._lock:
            self._unavailable[(release.public_id, release.model_hash)] = UnavailableWorkspaceModel(
                release.id, release.public_id, release.schema_version
            )

    def _require_ready(self) -> None:
        with self._lock:
            if not self._ready:
                raise ModelRegistryUnavailable("The model registry is unhealthy")

    def mark_unhealthy(self) -> None:
        with self._lock:
            self._ready = False

    @property
    def waiting_for_a_servable_model(self) -> bool:
        """Healthy, but no workspace's release can be served yet: a raising, here or in another
        process, can change that, so a probe or a heartbeat asks again."""
        with self._lock:
            return self._ready and not self._servable

    @property
    def ready(self) -> bool:
        with self._lock:
            return self._ready and self._servable

    def clear(self) -> None:
        with self._lock:
            self._models.clear()
            self._unavailable.clear()
            self._ready = True
            self._servable = True
            self._on_servable.clear()
        clear_metadata_cache()


def _snapshot(release: ModelRelease, model: EngineModel) -> ModelSnapshot:
    return ModelSnapshot(
        release_db_id=release.id,
        release_id=release.public_id,
        model_hash=release.model_hash,
        model=model,
    )


model_registry = ModelRegistry()


# Each workspace a session resolved, with the release its writes were validated under.
_RESOLVED_RELEASES = "resolved_workspace_model_releases"
# Each change set a session read in, with the release it pinned then (the read guard, 0.11 N1).
_PINNED_CHANGE_SETS = "read_change_set_model_releases"
# Set once a session committed: what it answers then follows from a write the commit guard checked.
_COMMITTED = "committed"


def resolve_model_snapshot(session: Session, workspace_key: str | None = None) -> ModelSnapshot:
    """Resolve the model of ``workspace_key`` (the default workspace when ``None``, D6) and bind
    this session's commits to it (see ``require_resolved_release``)."""
    try:
        snapshot = model_registry.resolve_workspace(session, workspace_key)
    except WorkspaceModelUnavailable as exc:
        details = {"workspaceKey": exc.workspace_key, "releaseId": exc.unavailable.release_id}
        if exc.unavailable.unsupported_schema:
            details["schemaVersion"] = exc.unavailable.schema_version
            details["supportedSchemaVersions"] = list(SCHEMA_VERSIONS)
        raise api_error(
            503,
            "MODEL_REGISTRY_UNAVAILABLE",
            f"The model of workspace '{exc.workspace_key}' cannot be served by this version",
            details,
        ) from exc
    except ModelRegistryUnavailable as exc:
        raise api_error(
            503,
            "MODEL_REGISTRY_UNAVAILABLE",
            "The model registry is unavailable",
        ) from exc
    session.info.setdefault(_RESOLVED_RELEASES, {})[snapshot.workspace_key] = snapshot.release_db_id
    return snapshot


def resolve_record_snapshot(session: Session, object_id: str) -> ModelSnapshot:
    """The model of the workspace holding a live record, for a write naming the record alone; the
    default workspace's when no such record exists, so the write answers its own not-found."""
    workspace_key = session.scalar(select(RdmObject.workspace_key).where(RdmObject.id == object_id))
    return resolve_model_snapshot(session, workspace_key)


def resolve_relation_snapshot(session: Session, relation_id: str) -> ModelSnapshot:
    """The model of the workspace holding a live relationship (that of its ``from`` record)."""
    workspace_key = session.scalar(
        select(RdmObject.workspace_key)
        .join(ObjectRelation, ObjectRelation.from_object_id == RdmObject.id)
        .where(ObjectRelation.id == relation_id)
    )
    return resolve_model_snapshot(session, workspace_key)


@event.listens_for(Session, "before_commit")
def _require_resolved_release(session: Session) -> None:
    require_resolved_release(session)


def require_resolved_release(session: Session) -> None:
    """Refuse to commit a write validated under a release its workspace no longer runs (0.8 W5,
    0.11 M1).

    The registry's publication guard covers only the moment of resolution, so a write resolved
    under release A could otherwise commit after B was activated into its workspace, in this
    process or another one sharing the database. The check runs inside the write transaction after
    its rows are flushed, under a share lock on each resolved workspace's ``workspace_models`` row,
    which conflicts with the lock activation holds from before its compatibility check until it
    commits; a write in another workspace takes another row and is never held up. It runs as the
    session commits; a batch also runs it before it writes its matrix states (0.9.0-alpha.1 PG3b),
    so it holds the share lock before any state row: an activation that drops a matrix shape then
    never waits for a batch's state rows while the batch waits for the activation.
    """
    resolved = session.info.get(_RESOLVED_RELEASES)
    if not resolved:
        return
    session.flush()
    for workspace_key in sorted(resolved):
        release_db_id = resolved[workspace_key]
        # The row alone: a share lock that waited for an activation rechecks only the row's own
        # condition; joined to its release, the switched row would drop out and pass (0.11 N1).
        current_id = session.scalar(
            select(WorkspaceModel.model_release_id)
            .where(WorkspaceModel.workspace_key == workspace_key)
            .with_for_update(read=True)
        )
        if current_id is None or current_id == release_db_id:
            continue
        current = session.get(ModelRelease, current_id)
        was = session.get(ModelRelease, release_db_id)
        raise api_error(
            409,
            "MODEL_RELEASE_CHANGED",
            f"Workspace '{workspace_key}' was moved to another model release while this request "
            "was processed; nothing was saved. Reload and retry against its current model",
            {
                "workspaceKey": workspace_key,
                "resolvedReleaseId": was.public_id if was is not None else None,
                "currentReleaseId": current.public_id,
            },
        )


@event.listens_for(Session, "after_commit")
def _note_commit(session: Session) -> None:
    session.info[_COMMITTED] = True


def require_unchanged_releases(session: Session) -> None:
    """Refuse to answer a read whose model changed while it ran (the read guard, 0.11 N1, D166).

    A request resolves its workspace's release, then reads its data. A migration (V1) or a change
    set moved to another release (V2, V3) switches data and release in one transaction, in this
    process or any other on the database, so a read that resolved the old release may have read the
    new data. Checked as the request ends, before it answers: when every workspace it resolved still
    runs that release and every change set it read in still pins it, each of its statements ran
    before the switch committed and it read the old data only. A request that committed is not
    checked: the commit guard checked its write, and refusing would hide a saved write.
    """
    if session.info.get(_COMMITTED):
        return
    resolved = session.info.get(_RESOLVED_RELEASES) or {}
    pinned = session.info.get(_PINNED_CHANGE_SETS) or {}
    if not resolved and not pinned:
        return
    current: dict[str, int | None] = {}
    if resolved:
        current |= dict(
            session.execute(
                select(WorkspaceModel.workspace_key, WorkspaceModel.model_release_id).where(
                    WorkspaceModel.workspace_key.in_(list(resolved))
                )
            ).all()
        )
    for workspace_key in sorted(resolved):
        was, now = resolved[workspace_key], current.get(workspace_key)
        if now is not None and now != was:
            _release_changed(
                session,
                {"workspaceKey": workspace_key},
                was,
                now,
                f"Workspace '{workspace_key}' was moved to another model release",
            )
    if pinned:
        changed = session.execute(
            select(ChangeSet.id, ChangeSet.workspace_key, ChangeSet.model_release_id).where(
                ChangeSet.id.in_(list(pinned))
            )
        ).all()
        for change_set_id, workspace_key, now in sorted(changed):
            was = pinned[change_set_id]
            if now != was:
                _release_changed(
                    session,
                    {"workspaceKey": workspace_key, "changeSetId": change_set_id},
                    was,
                    now,
                    f"Change set '{change_set_id}' was moved to another model release",
                )


def _release_changed(session: Session, details: dict, was_id: int, now_id: int, what: str) -> None:
    public = dict(
        session.execute(
            select(ModelRelease.id, ModelRelease.public_id).where(
                ModelRelease.id.in_([was_id, now_id])
            )
        ).all()
    )
    raise api_error(
        409,
        "MODEL_RELEASE_CHANGED",
        f"{what} while this request was read; its answer could mix two models, so none is "
        "given. Read again against its current model",
        {
            **details,
            "resolvedReleaseId": public.get(was_id),
            "currentReleaseId": public.get(now_id),
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
            "MUTUALLY_EXCLUSIVE_CONTEXT",
            "changeSetId and publicationId cannot be combined",
        )
    if change_set_id:
        context = session.scalar(select(ChangeSet).where(ChangeSet.id == change_set_id))
        if context is None:
            raise api_error(404, "CHANGE_SET_NOT_FOUND", "Change set not found")
        if workspace_key is not None and workspace_key != context.workspace_key:
            raise api_error(
                422,
                "WORKSPACE_CONTEXT_MISMATCH",
                "workspaceKey does not match the selected context",
                {"workspaceKey": workspace_key, "contextWorkspaceKey": context.workspace_key},
            )
        session.info.setdefault(_PINNED_CHANGE_SETS, {})[context.id] = context.model_release_id
        return replace(
            resolve_pinned_release(session, context.model_release_id),
            workspace_key=context.workspace_key,
        )
    if publication_id:
        context = session.scalar(select(Publication).where(Publication.id == publication_id))
        if context is None:
            raise api_error(404, "PUBLICATION_NOT_FOUND", "Publication not found")
        if workspace_key is not None and workspace_key != context.workspace_key:
            raise api_error(
                422,
                "WORKSPACE_CONTEXT_MISMATCH",
                "workspaceKey does not match the selected context",
                {"workspaceKey": workspace_key, "contextWorkspaceKey": context.workspace_key},
            )
        return replace(
            resolve_pinned_release(session, context.model_release_id),
            workspace_key=context.workspace_key,
        )
    return resolve_model_snapshot(session, workspace_key)


def resolve_change_set_snapshot(session: Session, change_set_id: str) -> ModelSnapshot:
    """Resolve the immutable model pinned by a change set write after its body-selected context."""
    change_set = session.scalar(select(ChangeSet).where(ChangeSet.id == change_set_id))
    if change_set is None:
        raise api_error(404, "CHANGE_SET_NOT_FOUND", "Change set not found")
    return resolve_pinned_release(session, change_set.model_release_id, require_ready=False)


def resolve_pinned_release(
    session: Session, release_id: int, *, require_ready: bool = True
) -> ModelSnapshot:
    """Expose pinned resolution through the same structured readiness boundary as active reads."""
    try:
        return model_registry.resolve_release(session, release_id, require_ready=require_ready)
    except ModelRegistryUnavailable as exc:
        raise api_error(
            503,
            "MODEL_REGISTRY_UNAVAILABLE",
            "The model registry is unavailable",
        ) from exc
