"""What one process reports about itself (Product 0.11 O1, D192, D194): what only it knows.

Whether it is ready, the state of each background thread, its connection pool, the releases some
workspace runs that it cannot serve and why, and its counters. Stored as JSON in its
``engine_processes`` row; the API and ``/metrics`` read it from there.
"""

import os
import socket
import uuid
from collections.abc import Collection
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Literal

from sqlalchemy.orm import Session

from ...common.outage import thread_states, unavailable_counts
from ...common.request_metrics import request_metrics
from ...common.time import as_utc
from ...config import get_settings
from ..events.dispatcher import THREAD_NAME as DISPATCHER_THREAD
from ..events.worker import THREAD_NAME as DERIVER_THREAD
from ..jobs.events import THREAD_NAME as LISTENER_THREAD
from ..jobs.worker import ASSISTANT_THREAD_NAME, EXPORT_THREAD_NAME
from ..jobs.worker import THREAD_NAME as JOB_WORKER_THREAD
from ..mail.sender import THREAD_NAME as MAIL_SENDER_THREAD
from ..model.registry import UnavailableWorkspaceModel, model_registry

HEARTBEAT_THREAD = "rdm-process-heartbeat"
# Each background thread by its thread name, and the name a report gives it, in report order.
THREADS: dict[str, str] = {
    JOB_WORKER_THREAD: "jobWorker",
    EXPORT_THREAD_NAME: "exportWorker",
    ASSISTANT_THREAD_NAME: "assistantWorker",
    LISTENER_THREAD: "jobListener",
    DERIVER_THREAD: "eventDeriver",
    DISPATCHER_THREAD: "webhookDispatcher",
    MAIL_SENDER_THREAD: "mailSender",
    HEARTBEAT_THREAD: "heartbeat",
}
UnavailableReason = Literal["unsupportedSchema", "invalid", "notLoaded"]


@dataclass(frozen=True)
class ProcessIdentity:
    """``host:pid:random``, as the job worker names its leases (0.11 N2): unique even when a host
    reuses a process ID."""

    process_id: str
    host: str
    pid: int
    started_at: datetime


_identity: ProcessIdentity | None = None


def this_process() -> ProcessIdentity:
    """This process's identity, made once per process (a forked worker makes its own)."""
    global _identity
    if _identity is None or _identity.pid != os.getpid():
        host, pid = socket.gethostname(), os.getpid()
        _identity = ProcessIdentity(
            f"{host}:{pid}:{uuid.uuid4().hex[:8]}"[:200], host[:255], pid, datetime.now(UTC)
        )
    return _identity


def unavailable_reason(item: UnavailableWorkspaceModel) -> UnavailableReason:
    """Why this process cannot serve a release: a schema outside the window, a model that does not
    validate, or a release withdrawn after it failed to load once activated (D29)."""
    if item.unsupported_schema:
        return "unsupportedSchema"
    return "invalid" if item.diagnostics else "notLoaded"


def build_report(session: Session, started_threads: Collection[str]) -> dict[str, Any]:
    states = thread_states()
    threads = []
    for name, key in THREADS.items():
        state = states.get(name)
        if name not in started_threads:
            threads.append({"name": key, "state": "off"})
        elif state is None or not state.failing:
            threads.append({"name": key, "state": "running"})
        else:
            threads.append(
                {
                    "name": key,
                    "state": "failing",
                    "reason": state.reason,
                    "since": as_utc(state.since).isoformat() if state.since else None,
                }
            )
    pool = session.get_bind().pool
    settings = get_settings()
    return {
        "ready": model_registry.ready,
        "threads": threads,
        "pool": {
            "size": settings.database_pool_size,
            "maxOverflow": settings.database_pool_max_overflow,
            "inUse": _checked_out(pool),
        },
        "unavailableReleases": [
            {
                "releaseId": item.release_id,
                "schemaVersion": item.schema_version,
                "reason": unavailable_reason(item),
            }
            for item in model_registry.unavailable_assigned(session)
        ],
        "counters": {
            **request_metrics.snapshot(),
            "databaseUnavailable": unavailable_counts(),
        },
    }


def _checked_out(pool: Any) -> int:
    checked_out = getattr(pool, "checkedout", None)
    return checked_out() if callable(checked_out) else 0
