"""Check a restored copy of the instance's database and record the result (Product 0.11 O2).

The operator restores a backup into a separate database (D198); :func:`rehearse` then meets what a
recovery from that backup would meet (D199): the copy is prepared as startup prepares a database
(collation, extensions, migrations to this engine's revision, so the copy is changed), the process
rows that came with the backup are cleared (D203), every active workspace's release is loaded in a
registry of its own and each workspace is counted in PostgreSQL, beside the instance's records. The
rehearsal passes when the copy was prepared and every active workspace in it is served. It is
recorded in the instance, passed or failed (D200); the copy gets nothing.
"""

import socket
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from sqlalchemy import URL, Connection, create_engine, func, insert, select, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from sqlalchemy.pool import NullPool

from ...config import ENGINE_VERSION
from ...db import DatabaseStartupError, prepare_database
from ...models.database import (
    AuditEvent,
    BackupRehearsal,
    ChangeSet,
    EngineProcess,
    ModelRelease,
    ObjectRelation,
    Publication,
    RdmObject,
    Workspace,
)
from ..model.registry import ModelRegistry, ModelRegistryUnavailable, WorkspaceModelUnavailable
from ..processes.report import unavailable_reason

NOT_SERVED = "WORKSPACES_NOT_SERVED"


class SameDatabase(RuntimeError):
    """The copy named is the instance's own database: nothing is changed or recorded."""


@dataclass
class WorkspaceCheck:
    workspace_key: str
    release: dict[str, str] | None
    state: str = "served"
    # unsupportedSchema, invalid, or noRelease for a workspace that runs none.
    reason: str | None = None
    records: int = 0
    relations: int = 0
    open_change_sets: int = 0
    publications: int = 0
    live_records: int = 0

    def as_json(self) -> dict[str, Any]:
        return {
            "workspaceKey": self.workspace_key,
            "release": self.release,
            "state": self.state,
            "reason": self.reason,
            "records": self.records,
            "relations": self.relations,
            "openChangeSets": self.open_change_sets,
            "publications": self.publications,
            "liveRecords": self.live_records,
        }


@dataclass
class Rehearsal:
    backup: str | None
    checked_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    data_as_of: datetime | None = None
    revision_before: str | None = None
    revision_after: str | None = None
    failure_code: str | None = None
    failure_message: str | None = None
    workspaces: list[WorkspaceCheck] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return self.failure_code is None


@contextmanager
def _connected(url: URL) -> Iterator[Connection]:
    engine = create_engine(url.render_as_string(hide_password=False), poolclass=NullPool)
    try:
        with engine.connect() as connection:
            yield connection
    finally:
        engine.dispose()


def rehearse(instance_url: URL, restored_url: URL, backup: str | None) -> Rehearsal:
    """Check the copy at ``restored_url`` and record the result in the instance at
    ``instance_url``. Raises :class:`SameDatabase` before anything is changed when both name one
    database, and :class:`DatabaseStartupError` when the instance cannot be reached."""
    rehearsal = Rehearsal(backup)
    with _connected(instance_url) as instance:
        try:
            _refuse_same_database(instance, restored_url)
            rehearsal.revision_before, rehearsal.revision_after = prepare_database(
                restored_url, warn=False
            )
        except DatabaseStartupError as exc:
            rehearsal.failure_code = exc.code
            rehearsal.failure_message = f"A recovery from this backup would not start: {exc}"
        else:
            _check_copy(restored_url, rehearsal)
            _count_live(instance, rehearsal.workspaces)
        _record(instance, rehearsal)
    return rehearsal


def _refuse_same_database(instance: Connection, restored_url: URL) -> None:
    """Refuse a copy that is the instance's database: its server shows this check's own instance
    session in that database, however the two URLs spell the host."""
    pid = instance.scalar(text("SELECT pg_backend_pid()"))
    instance.commit()
    try:
        with _connected(restored_url) as copy:
            same = copy.scalar(
                text(
                    "SELECT count(*) FROM pg_stat_activity "
                    "WHERE pid = :pid AND datname = current_database()"
                ),
                {"pid": pid},
            )
    except SQLAlchemyError:
        # Unreachable or refused: preparing the copy reports it with what to do.
        return
    if same:
        raise SameDatabase(
            "The restored copy named by --restored is the instance's own database "
            f"('{restored_url.database}'). Nothing was changed or recorded. Restore the backup into "
            "a new, separate database and name that one; the check upgrades and changes the copy."
        )


def _check_copy(url: URL, rehearsal: Rehearsal) -> None:
    engine = create_engine(url.render_as_string(hide_password=False), poolclass=NullPool)
    try:
        with engine.begin() as connection:
            connection.execute(EngineProcess.__table__.delete())
        with Session(engine) as session:
            rehearsal.data_as_of = session.scalar(select(func.max(AuditEvent.occurred_at)))
            rehearsal.workspaces = _serve_each(session)
            _count_copy(session, rehearsal.workspaces)
    finally:
        engine.dispose()
    not_served = [item for item in rehearsal.workspaces if item.state != "served"]
    if not_served:
        rehearsal.failure_code = NOT_SERVED
        rehearsal.failure_message = (
            "A recovery from this backup would leave "
            + "; ".join(_why(item) for item in not_served)
            + " answering 503 MODEL_REGISTRY_UNAVAILABLE, while the other workspaces serve. Before "
            "relying on this backup, activate a release this engine reads in each of them, or keep "
            "the engine version that reads their releases with the backup."
        )


def _why(item: WorkspaceCheck) -> str:
    if item.release is None:
        return f"workspace '{item.workspace_key}' (it runs no release)"
    release = item.release
    reason = {
        "unsupportedSchema": f"schema language {release['schemaVersion']} is outside what engine "
        f"{ENGINE_VERSION} reads",
        "invalid": "the model does not validate in this engine",
    }[item.reason or "invalid"]
    return (
        f"workspace '{item.workspace_key}' (release {release['key']} {release['version']}: "
        f"{reason})"
    )


def _serve_each(session: Session) -> list[WorkspaceCheck]:
    """Each active workspace of the copy resolved in a registry of its own, as the first process
    started on the copy would resolve it."""
    registry = ModelRegistry()
    checks = []
    keys = session.scalars(
        select(Workspace.key).where(Workspace.status == "active").order_by(Workspace.key)
    )
    for key in keys:
        check = WorkspaceCheck(key, None)
        try:
            snapshot = registry.resolve_workspace(session, key)
            release = session.get(ModelRelease, snapshot.release_db_id)
        except WorkspaceModelUnavailable as exc:
            release = session.get(ModelRelease, exc.unavailable.release_db_id)
            check.state, check.reason = "unavailable", unavailable_reason(exc.unavailable)
        except ModelRegistryUnavailable:
            release = None
            check.state, check.reason = "unavailable", "noRelease"
        if release is not None:
            check.release = {
                "id": release.public_id,
                "key": release.release_key,
                "version": release.release_version,
                "schemaVersion": release.schema_version,
            }
        checks.append(check)
    return checks


def _count_copy(session: Session, checks: list[WorkspaceCheck]) -> None:
    """Every row counted in PostgreSQL, one grouped statement per kind."""
    by_key = {item.workspace_key: item for item in checks}
    relation_owner = select(RdmObject.workspace_key, func.count()).join(
        ObjectRelation, ObjectRelation.from_object_id == RdmObject.id
    )
    for attribute, statement in (
        ("records", select(RdmObject.workspace_key, func.count())),
        ("relations", relation_owner),
        ("open_change_sets", select(ChangeSet.workspace_key, func.count())),
        ("publications", select(Publication.workspace_key, func.count())),
    ):
        column = statement.selected_columns[0]
        rows = session.execute(statement.where(column.in_(list(by_key))).group_by(column)).tuples()
        for key, count in rows:
            setattr(by_key[key], attribute, count)


def _count_live(instance: Connection, checks: list[WorkspaceCheck]) -> None:
    counts: dict[str, int] = dict(
        instance.execute(
            select(RdmObject.workspace_key, func.count())
            .where(RdmObject.workspace_key.in_([item.workspace_key for item in checks]))
            .group_by(RdmObject.workspace_key)
        ).all()
    )
    for item in checks:
        item.live_records = counts.get(item.workspace_key, 0)
    instance.commit()


def _record(instance: Connection, rehearsal: Rehearsal) -> None:
    instance.execute(
        insert(BackupRehearsal).values(
            public_id=str(uuid4()),
            checked_at=rehearsal.checked_at,
            backup=rehearsal.backup,
            data_as_of=rehearsal.data_as_of,
            revision_before=rehearsal.revision_before,
            revision_after=rehearsal.revision_after,
            engine_version=ENGINE_VERSION,
            host=socket.gethostname()[:255],
            result="passed" if rehearsal.passed else "failed",
            failure_code=rehearsal.failure_code,
            failure_message=rehearsal.failure_message,
            workspaces=[item.as_json() for item in rehearsal.workspaces],
        )
    )
    instance.commit()
