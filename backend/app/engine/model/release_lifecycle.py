"""Retiring and deleting installed model releases (Product 0.12 MR1, D457–D459).

A release's snapshot never changes; its status does. A retired release is not chosen again (a new
workspace, a change set, an activation or a migration target), while every workspace and change
set already on it keeps working. A release nothing refers to may be deleted: what refers to it is
found from the database's own foreign keys, so a table added later is counted without a change
here.
"""

from collections.abc import Iterable
from datetime import UTC, datetime
from typing import Literal

from sqlalchemy import Table, delete, literal, select, union_all
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ...errors import api_error
from ...models.database import (
    AuditEvent,
    Base,
    ModelRelease,
    WorkspaceModel,
    WorkspaceRuntimeState,
)

ReleaseStatus = Literal["active", "retired"]
DeleteBlocker = Literal["running", "history", "importProfile", "mapping"]

# The order a refusal names them in: the first that applies.
_BLOCKER_ORDER: tuple[DeleteBlocker, ...] = ("running", "history", "importProfile", "mapping")
# What a table that keeps a release refers to it for; any other table is its history.
_BLOCKER_OF_TABLE: dict[str, DeleteBlocker] = {
    "workspace_models": "running",
    "import_profiles": "importProfile",
    "model_mappings": "mapping",
}


def _restricting_columns() -> list[tuple[DeleteBlocker, Table, str]]:
    """Every column whose foreign key keeps a release from being deleted. The model's structure
    rows go with it (``CASCADE``) and a draft forgets where it started (``SET NULL``)."""
    found: list[tuple[DeleteBlocker, Table, str]] = []
    for table in Base.metadata.sorted_tables:
        for key in table.foreign_keys:
            if key.column.table.name != ModelRelease.__tablename__:
                continue
            if (key.ondelete or "").upper() in ("CASCADE", "SET NULL"):
                continue
            blocker = _BLOCKER_OF_TABLE.get(table.name, "history")
            found.append((blocker, table, key.parent.name))
    return found


def delete_blockers(session: Session, release_ids: Iterable[int]) -> dict[int, DeleteBlocker]:
    """For each release (by database id) that cannot be deleted, the first reason; one statement
    for the whole set."""
    ids = list(set(release_ids))
    if not ids:
        return {}
    parts = [
        select(table.c[column].label("release_id"), literal(blocker).label("blocker"))
        .where(table.c[column].in_(ids))
        .distinct()
        for blocker, table, column in _restricting_columns()
    ]
    found: dict[int, set[str]] = {}
    for release_id, blocker in session.execute(union_all(*parts)):
        found.setdefault(release_id, set()).add(blocker)
    return {
        release_id: next(item for item in _BLOCKER_ORDER if item in blockers)
        for release_id, blockers in found.items()
    }


def require_choosable(session: Session, release: ModelRelease, *, operation: str) -> None:
    """Refuse a retired release where a caller chooses it (``409 MODEL_RELEASE_RETIRED``). The
    status is read under a share lock, so a retirement committing meanwhile is waited for."""
    status = session.scalar(
        select(ModelRelease.status).where(ModelRelease.id == release.id).with_for_update(read=True)
    )
    if status == "retired":
        raise api_error(
            409,
            "MODEL_RELEASE_RETIRED",
            f"Model release '{release.public_id}' is retired and cannot be chosen",
            {"releaseId": release.public_id, "operation": operation},
        )


def _load_for_update(session: Session, release_id: str) -> ModelRelease:
    release = session.scalar(
        select(ModelRelease)
        .where(ModelRelease.public_id == release_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if release is None:
        raise api_error(404, "MODEL_RELEASE_NOT_FOUND", f"Model release '{release_id}' not found")
    return release


def _require_status_version(release: ModelRelease, expected: int) -> None:
    if release.status_version != expected:
        raise api_error(
            409,
            "MODEL_RELEASE_VERSION_CONFLICT",
            f"Model release '{release.public_id}' changed status since version {expected}",
            {
                "releaseId": release.public_id,
                "status": release.status,
                "currentStatusVersion": release.status_version,
            },
        )


def _default_release_id(session: Session) -> int | None:
    """The release the default workspace runs, its choice held until this transaction ends."""
    default_key = session.scalar(
        select(WorkspaceRuntimeState.default_workspace_key)
        .where(WorkspaceRuntimeState.id == 1)
        .with_for_update(read=True)
    )
    return session.scalar(
        select(WorkspaceModel.model_release_id).where(WorkspaceModel.workspace_key == default_key)
    )


def set_release_status(
    session: Session, release_id: str, status: ReleaseStatus, expected_status_version: int
) -> ModelRelease:
    """Retire or restore a release. The default workspace's release is not retired (``409
    MODEL_RELEASE_IS_DEFAULT``): a new workspace starts on it unless another is named. Asking for
    the status it has changes nothing."""
    release = _load_for_update(session, release_id)
    _require_status_version(release, expected_status_version)
    if release.status == status:
        return release
    if status == "retired" and _default_release_id(session) == release.id:
        raise api_error(
            409,
            "MODEL_RELEASE_IS_DEFAULT",
            f"Model release '{release.public_id}' is run by the default workspace and cannot be"
            " retired; make another workspace the default or move it to another release first",
            {"releaseId": release.public_id},
        )
    release.status = status
    release.status_version += 1
    release.retired_at = datetime.now(UTC) if status == "retired" else None
    session.add(
        AuditEvent(
            aggregate_type="model_release",
            aggregate_id=release.public_id,
            action="retired" if status == "retired" else "restored",
            version=release.status_version,
            changes={
                "releaseKey": release.release_key,
                "releaseVersion": release.release_version,
                "status": status,
            },
        )
    )
    session.flush()
    return release


def _release_in_use(release: ModelRelease, blocker: DeleteBlocker) -> Exception:
    return api_error(
        409,
        "MODEL_RELEASE_IN_USE",
        f"Model release '{release.public_id}' cannot be deleted: {_BLOCKER_TEXT[blocker]}."
        " Retire it instead",
        {"releaseId": release.public_id, "blockedBy": blocker},
    )


_BLOCKER_TEXT: dict[DeleteBlocker, str] = {
    "running": "a workspace runs it",
    "history": "records, change sets, publications or jobs refer to it",
    "importProfile": "an import profile was checked against it",
    "mapping": "a model mapping is between it and another release",
}


def delete_release(session: Session, release_id: str, expected_status_version: int) -> None:
    """Delete a release nothing refers to, with its structure rows (``409 MODEL_RELEASE_IN_USE``
    names the first reason it cannot be). A reference written meanwhile is refused by the foreign
    key and answered the same way."""
    release = _load_for_update(session, release_id)
    _require_status_version(release, expected_status_version)
    blocker = delete_blockers(session, [release.id]).get(release.id)
    if blocker is not None:
        raise _release_in_use(release, blocker)
    session.add(
        AuditEvent(
            aggregate_type="model_release",
            aggregate_id=release.public_id,
            action="deleted",
            version=release.status_version,
            changes={
                "releaseKey": release.release_key,
                "releaseVersion": release.release_version,
                "modelHash": release.model_hash,
            },
        )
    )
    try:
        with session.begin_nested():
            session.execute(delete(ModelRelease).where(ModelRelease.id == release.id))
    except IntegrityError as exc:
        found = delete_blockers(session, [release.id]).get(release.id, "history")
        raise _release_in_use(release, found) from exc


def deletable_releases(session: Session, *, retired_only: bool) -> list[ModelRelease]:
    """The releases nothing refers to, oldest first; ``retired_only`` keeps the retired ones."""
    statement = select(ModelRelease).order_by(ModelRelease.installed_at, ModelRelease.id)
    if retired_only:
        statement = statement.where(ModelRelease.status == "retired")
    for _, table, column in _restricting_columns():
        statement = statement.where(
            ModelRelease.id.not_in(select(table.c[column]).where(table.c[column].is_not(None)))
        )
    return list(session.scalars(statement))


def delete_unreferenced(session: Session, releases: list[ModelRelease]) -> int:
    """Delete the given releases, which ``deletable_releases`` found, in one statement; the
    foreign keys refuse the whole statement if one was referred to meanwhile."""
    if not releases:
        return 0
    session.add_all(
        AuditEvent(
            aggregate_type="model_release",
            aggregate_id=release.public_id,
            action="deleted",
            version=release.status_version,
            changes={
                "releaseKey": release.release_key,
                "releaseVersion": release.release_version,
                "modelHash": release.model_hash,
            },
        )
        for release in releases
    )
    result = session.execute(
        delete(ModelRelease).where(ModelRelease.id.in_([release.id for release in releases]))
    )
    return result.rowcount
