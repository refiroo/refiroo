"""The processes, the readiness per workspace and ``/metrics`` as the API shows them (Product 0.11
O1, D192–D194), from the processes' ``engine_processes`` rows and a few counts read when asked."""

from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from ...common.prometheus import Family, render
from ...common.request_metrics import DURATION_BOUNDS
from ...engine.processes.reads import (
    WorkspaceReadiness,
    instance_gauges,
    live_processes,
    process_state,
)
from ...models.database import EngineProcess
from ..schemas.system import (
    ProcessCounters,
    ProcessPool,
    ProcessResponse,
    ProcessThread,
    ReadinessProcess,
    ReadinessRelease,
    UnavailableRelease,
    WorkspaceReadinessResponse,
)


def process_response(row: EngineProcess, now: datetime) -> ProcessResponse:
    report = row.report
    counters = report.get("counters", {})
    requests = counters.get("requests", [])
    return ProcessResponse(
        id=row.process_id,
        host=row.host,
        pid=row.pid,
        engineVersion=row.engine_version,
        startedAt=row.started_at,
        heartbeatAt=row.heartbeat_at,
        state=process_state(row, now),
        ready=report.get("ready", False),
        threads=[ProcessThread(**thread) for thread in report.get("threads", [])],
        pool=ProcessPool(**report["pool"]),
        unavailableReleases=[
            UnavailableRelease(**item) for item in report.get("unavailableReleases", [])
        ],
        counters=ProcessCounters(
            requests=sum(item["count"] for item in requests),
            serverErrors=sum(item["count"] for item in requests if item["status"] >= 500),
            databaseUnavailable=counters.get("databaseUnavailable", {}),
        ),
    )


def readiness_response(item: WorkspaceReadiness) -> WorkspaceReadinessResponse:
    release = item.release
    return WorkspaceReadinessResponse(
        workspaceKey=item.workspace_key,
        release=(
            ReadinessRelease(
                id=release.public_id,
                key=release.release_key,
                version=release.release_version,
                schemaVersion=release.schema_version,
            )
            if release is not None
            else None
        ),
        state="served" if item.served else "unavailable",
        unavailableIn=[
            ReadinessProcess(
                processId=process.process_id,
                reason=process.reason,
                schemaVersion=process.schema_version,
            )
            for process in item.unavailable_in
        ],
    )


def metrics_text(session: Session) -> str:
    """Every live process's figures, labelled ``process``, and the instance's gauges (D193)."""
    processes = live_processes(session)
    ready = Family("rdm_process_ready", "gauge", "1 when the process serves requests")
    started = Family("rdm_process_start_time_seconds", "gauge", "When the process started")
    requests = Family(
        "rdm_http_requests_total", "counter", "Requests answered, by method, route and status"
    )
    durations = Family(
        "rdm_http_request_duration_seconds", "histogram", "Time to answer a request, by route"
    )
    unavailable = Family(
        "rdm_database_unavailable_total",
        "counter",
        "Requests and background threads that got no database connection, by reason",
    )
    pool_size = Family("rdm_database_pool_size", "gauge", "DATABASE_POOL_SIZE")
    pool_overflow = Family("rdm_database_pool_max_overflow", "gauge", "DATABASE_POOL_MAX_OVERFLOW")
    pool_in_use = Family(
        "rdm_database_pool_connections_in_use", "gauge", "Database connections checked out"
    )
    threads = Family(
        "rdm_background_thread_failing", "gauge", "1 while a background thread's rounds fail"
    )
    releases = Family(
        "rdm_releases_unavailable",
        "gauge",
        "Releases some workspace runs that the process cannot serve",
    )
    for row in processes:
        report: dict[str, Any] = row.report
        process = {"process": row.process_id}
        ready.add({**process, "version": row.engine_version}, 1 if report.get("ready") else 0)
        started.add(process, row.started_at.timestamp())
        counters = report.get("counters", {})
        for item in counters.get("requests", []):
            requests.add(
                {
                    **process,
                    "method": item["method"],
                    "route": item["route"],
                    "status": str(item["status"]),
                },
                item["count"],
            )
        for item in counters.get("durations", []):
            durations.histogram(
                {**process, "route": item["route"]}, DURATION_BOUNDS, item["counts"], item["sum"]
            )
        for reason, count in sorted(counters.get("databaseUnavailable", {}).items()):
            unavailable.add({**process, "reason": reason}, count)
        pool = report.get("pool", {})
        pool_size.add(process, pool.get("size", 0))
        pool_overflow.add(process, pool.get("maxOverflow", 0))
        pool_in_use.add(process, pool.get("inUse", 0))
        for thread in report.get("threads", []):
            if thread["state"] != "off":
                threads.add(
                    {**process, "thread": thread["name"]}, 1 if thread["state"] == "failing" else 0
                )
        releases.add(process, len(report.get("unavailableReleases", [])))
    gauges = instance_gauges(session, processes)
    process_count = Family("rdm_processes", "gauge", "Engine processes, live or silent")
    for state, count in gauges.processes.items():
        process_count.add({"state": state}, count)
    jobs = Family("rdm_jobs", "gauge", "Jobs queued, running or awaiting confirmation, by kind")
    for kind, state, count in gauges.jobs:
        jobs.add({"kind": kind, "state": state}, count)
    subscriptions = Family(
        "rdm_webhook_subscriptions",
        "gauge",
        "Webhook subscriptions: active, failing (a batch being retried) or suspended",
    )
    for state, count in gauges.subscriptions.items():
        subscriptions.add({"state": state}, count)
    workspaces = Family(
        "rdm_workspaces_unavailable",
        "gauge",
        "Active workspaces some live process cannot serve, or that run no release",
    )
    workspaces.add({}, gauges.unavailable_workspaces)
    return render(
        (
            ready,
            started,
            requests,
            durations,
            unavailable,
            pool_size,
            pool_overflow,
            pool_in_use,
            threads,
            releases,
            process_count,
            jobs,
            subscriptions,
            workspaces,
        )
    )
