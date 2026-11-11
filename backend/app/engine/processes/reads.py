"""The instance as its processes reported it (Product 0.11 O1, D192–D194).

A process is ``live`` while its last heartbeat is within three of its intervals, ``silent`` after.
A workspace is ``served`` when it runs a release and no live process reported that release
unavailable; otherwise ``unavailable``, naming each process that cannot serve it and why.
"""

from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any, Literal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ...common.time import as_utc
from ...config import get_settings
from ...models.database import (
    ConsumerSubscription,
    EngineProcess,
    Job,
    ModelRelease,
    Workspace,
    WorkspaceModel,
)

MISSED_HEARTBEATS = 3
ACTIVE_JOB_STATES = ("queued", "running", "awaiting_confirmation")
ProcessState = Literal["live", "silent"]


def process_state(row: EngineProcess, now: datetime | None = None) -> ProcessState:
    now = now or datetime.now(UTC)
    window = timedelta(seconds=MISSED_HEARTBEATS * get_settings().process_heartbeat_seconds)
    return "live" if as_utc(row.heartbeat_at) >= now - window else "silent"


def live_processes(session: Session) -> list[EngineProcess]:
    now = datetime.now(UTC)
    rows = session.scalars(select(EngineProcess).order_by(EngineProcess.process_id))
    return [row for row in rows if process_state(row, now) == "live"]


@dataclass(frozen=True)
class ProcessUnavailable:
    process_id: str
    reason: str
    schema_version: str


@dataclass(frozen=True)
class WorkspaceReadiness:
    workspace_key: str
    release: ModelRelease | None
    unavailable_in: list[ProcessUnavailable]

    @property
    def served(self) -> bool:
        return self.release is not None and not self.unavailable_in


def workspace_readiness(
    session: Session, workspace_keys: Sequence[str], processes: Iterable[EngineProcess]
) -> list[WorkspaceReadiness]:
    """Each workspace of ``workspace_keys``, in that order, with its release and the live
    ``processes`` that reported it unavailable."""
    releases = {
        key: release
        for key, release in session.execute(
            select(WorkspaceModel.workspace_key, ModelRelease)
            .join(ModelRelease, ModelRelease.id == WorkspaceModel.model_release_id)
            .where(WorkspaceModel.workspace_key.in_(workspace_keys))
        )
    }
    unavailable: dict[str, list[ProcessUnavailable]] = {}
    for process in processes:
        for item in process.report.get("unavailableReleases", []):
            unavailable.setdefault(item["releaseId"], []).append(
                ProcessUnavailable(process.process_id, item["reason"], item["schemaVersion"])
            )
    return [
        WorkspaceReadiness(
            key,
            releases.get(key),
            unavailable.get(releases[key].public_id, []) if key in releases else [],
        )
        for key in workspace_keys
    ]


def unavailable_workspace_count(session: Session, processes: Iterable[EngineProcess]) -> int:
    """Workspaces some live process cannot serve, or that run no release."""
    release_ids = {
        item["releaseId"]
        for process in processes
        for item in process.report.get("unavailableReleases", [])
    }
    active = select(Workspace.key).where(Workspace.status == "active")
    without = session.scalar(
        select(func.count())
        .select_from(Workspace)
        .outerjoin(WorkspaceModel, WorkspaceModel.workspace_key == Workspace.key)
        .where(Workspace.status == "active", WorkspaceModel.workspace_key.is_(None))
    )
    on_unavailable = (
        session.scalar(
            select(func.count())
            .select_from(WorkspaceModel)
            .join(ModelRelease, ModelRelease.id == WorkspaceModel.model_release_id)
            .where(
                WorkspaceModel.workspace_key.in_(active),
                ModelRelease.public_id.in_(release_ids),
            )
        )
        if release_ids
        else 0
    )
    return (without or 0) + (on_unavailable or 0)


@dataclass(frozen=True)
class InstanceGauges:
    processes: dict[ProcessState, int]
    jobs: list[tuple[str, str, int]]
    subscriptions: dict[str, int]
    unavailable_workspaces: int


def instance_gauges(session: Session, processes: list[EngineProcess]) -> InstanceGauges:
    """What ``/metrics`` reads from the database when scraped (D194)."""
    now = datetime.now(UTC)
    counts: dict[ProcessState, int] = {"live": 0, "silent": 0}
    for row in session.scalars(select(EngineProcess)):
        counts[process_state(row, now)] += 1
    jobs = [
        (kind, state, count)
        for kind, state, count in session.execute(
            select(Job.kind, Job.state, func.count())
            .where(Job.state.in_(ACTIVE_JOB_STATES))
            .group_by(Job.kind, Job.state)
            .order_by(Job.kind, Job.state)
        )
    ]
    subscriptions: dict[str, Any] = {"active": 0, "failing": 0, "suspended": 0}
    for status, failing, count in session.execute(
        select(
            ConsumerSubscription.status,
            ConsumerSubscription.failing_since.is_not(None),
            func.count(),
        ).group_by(ConsumerSubscription.status, ConsumerSubscription.failing_since.is_not(None))
    ):
        state = "failing" if status == "active" and failing else status
        subscriptions[state] = subscriptions.get(state, 0) + count
    return InstanceGauges(
        counts, jobs, subscriptions, unavailable_workspace_count(session, processes)
    )
