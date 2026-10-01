"""The job worker: runs queued and running jobs chunk by chunk under a lease (INTEGRATION_API P6).

A chunk's data writes, its outcomes and the job's checkpoint (``processed``) commit in one
transaction, so a job resumed after a crash starts at the first item without an outcome and never
repeats or skips one. An ``independent`` job's chunk is ``JOB_CHUNK_ITEMS`` items; an ``atomic``
job is one chunk.

**Lease.** A worker claims a job by setting ``leaseOwner`` and ``leaseExpiresAt`` in a short
transaction and renews the lease with each chunk's commit. A chunk does not keep the job row locked
while it applies items, so a cancel request never waits for it (D28); before it commits, it locks
the row and checks it still holds the lease, and rolls back when another worker took the job over.
A process that stops mid-chunk loses that chunk's work only; the job resumes once its lease expires.
Lock order inside a chunk: the change set (in a change set), then the write path's own (records).

**Stopping.** Before each chunk the worker reads the job: a cancel request finishes it
``cancelled``; a release no longer the pinned one fails it with ``model_release_changed``; another
refusal of the context (a retired workspace, a lost change set claim) fails it with that error. An
``atomic`` job's chunk also checks for a cancel request between items and rolls back completely.
Any other error rolls the chunk back and fails the job with ``job_failed`` (D29). Items without an
outcome then become ``unprocessed`` with the stop's reason; chunks committed before stay applied.

**Retention.** The worker expires finished jobs past ``expiresAt`` every hour (D14, D30).
"""

import logging
import os
import socket
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import uuid4

from pydantic import TypeAdapter
from sqlalchemy import func, or_, select, update
from sqlalchemy.orm import Session

from ...common.time import as_utc
from ...db import begin_transaction
from ...errors import ApiError
from ...models.commands import BatchItem
from ...models.database import ChangeSet, Job
from .background import open_job_context
from .batches import JobCancelled, run_items
from .store import complete_job, expire_jobs, load_inputs, record_outcomes, stop_job

logger = logging.getLogger(__name__)

# A job queued or cancelled in this process wakes the worker at once. Otherwise it looks again when
# a lease held elsewhere expires, and at least this often (a job queued by another process).
IDLE_SECONDS = 60.0
RETRY_SECONDS = 2.0
SWEEP_SECONDS = 3600.0
_ITEM = TypeAdapter(BatchItem)


@dataclass(frozen=True)
class WorkerSettings:
    chunk_items: int
    lease_seconds: int
    retention_days: int


class _LeaseLost(Exception):
    """Another worker holds the job now; this chunk must not commit."""


class JobWorker:
    """Runs jobs in this process: ``run_once`` runs one chunk; ``start`` runs them on a thread."""

    def __init__(
        self,
        session_factory: Callable[[], Session],
        settings: WorkerSettings,
        *,
        owner: str | None = None,
    ) -> None:
        self.session_factory = session_factory
        self.settings = settings
        self.owner = owner or f"{socket.gethostname()}:{os.getpid()}:{uuid4().hex[:8]}"
        self._wake = threading.Event()
        self._stopping = threading.Event()
        self._thread: threading.Thread | None = None
        # The earliest expiry of a lease another worker holds, seen by the last claim.
        self._leased_elsewhere_until: datetime | None = None

    # --- one step ---------------------------------------------------------------------------------

    def run_once(self) -> bool:
        """Claim the oldest job this worker may run and run its next chunk; ``False`` when none
        is waiting."""
        sequence_id = self._claim()
        if sequence_id is None:
            return False
        self._run_chunk(sequence_id)
        return True

    def run_until_idle(self) -> int:
        """Run chunks until no job is waiting; the number of chunks run."""
        chunks = 0
        while self.run_once():
            chunks += 1
        return chunks

    def sweep(self, now: datetime | None = None) -> int:
        """Expire finished jobs past their retention; the number expired."""
        with self.session_factory() as session:
            expired = expire_jobs(session, now or datetime.now(UTC))
            session.commit()
        return expired

    def _claim(self) -> int | None:
        now = datetime.now(UTC)
        claimable = (
            Job.state.in_(("queued", "running")),
            or_(
                Job.lease_owner.is_(None),
                Job.lease_owner == self.owner,
                Job.lease_expires_at <= now,
            ),
        )
        with self.session_factory() as session:
            sequence_id = session.scalar(
                select(Job.sequence_id).where(*claimable).order_by(Job.sequence_id).limit(1)
            )
            if sequence_id is None:
                self._leased_elsewhere_until = session.scalar(
                    select(func.min(Job.lease_expires_at)).where(
                        Job.state.in_(("queued", "running")),
                        Job.lease_owner.is_not(None),
                        Job.lease_owner != self.owner,
                    )
                )
                return None
            claimed = session.execute(
                update(Job)
                .where(Job.sequence_id == sequence_id, *claimable)
                .values(
                    state="running",
                    stage="applying",
                    started_at=func.coalesce(Job.started_at, now),
                    lease_owner=self.owner,
                    lease_expires_at=now + timedelta(seconds=self.settings.lease_seconds),
                )
                .execution_options(synchronize_session=False)
            )
            if claimed.rowcount != 1:
                # Another worker claimed it first.
                session.rollback()
                return None
            session.commit()
        return sequence_id

    def _run_chunk(self, sequence_id: int) -> None:
        with self.session_factory() as session:
            job = session.get(Job, sequence_id)
            if job is None or job.state != "running" or job.lease_owner != self.owner:
                return
            job_id = job.id
            if job.cancel_requested_at is not None:
                session.rollback()
                self._stop(sequence_id, "cancelled", "job_cancelled", None)
                return
            try:
                self._apply_chunk(session, job)
            except JobCancelled:
                session.rollback()
                self._stop(sequence_id, "cancelled", "job_cancelled", None)
            except _LeaseLost:
                session.rollback()
            except ApiError as error:
                session.rollback()
                reason = (
                    "model_release_changed"
                    if error.code == "model_release_changed"
                    else "job_failed"
                )
                self._stop(sequence_id, "failed", reason, _error_body(error))
            except Exception:
                session.rollback()
                correlation_id = uuid4().hex
                logger.exception(
                    "Job %s failed in a chunk (correlation ID %s); its applied chunks stay",
                    job_id,
                    correlation_id,
                )
                self._stop(
                    sequence_id,
                    "failed",
                    "job_failed",
                    {
                        "code": "job_failed",
                        "message": "The job stopped because of an internal error. Items it "
                        "applied before stay applied; the rest are unprocessed and may be sent "
                        "again. If it recurs, report the correlation ID",
                        "details": {"correlationId": correlation_id},
                    },
                )

    def _apply_chunk(self, session: Session, job: Job) -> None:
        atomic = job.parameters.get("policy") == "atomic"
        begin_transaction(session)
        context = open_job_context(session, job)
        inputs = load_inputs(
            session, job, job.total if atomic else self.settings.chunk_items
        )
        outcomes = run_items(
            session,
            context,
            [(index, _ITEM.validate_python(item)) for index, item in inputs],
            policy=job.parameters["policy"],
            on_existing=job.parameters.get("onExisting", "reject"),
            expected_change_set_version=job.change_set_version,
            job_id=job.id,
            should_stop=_cancel_requested(session, job.sequence_id) if atomic else None,
        )
        self._hold_lease(session, job.sequence_id)
        record_outcomes(session, job, outcomes)
        if context.change_set is not None:
            job.change_set_version = session.scalar(
                select(ChangeSet.version).where(ChangeSet.id == context.change_set.id)
            )
        if job.processed >= job.total:
            complete_job(session, job, retention_days=self.settings.retention_days)
        else:
            job.lease_expires_at = datetime.now(UTC) + timedelta(
                seconds=self.settings.lease_seconds
            )
        session.commit()

    def _hold_lease(self, session: Session, sequence_id: int) -> None:
        owner = session.scalar(
            select(Job.lease_owner).where(Job.sequence_id == sequence_id).with_for_update()
        )
        if owner != self.owner:
            raise _LeaseLost

    def _stop(
        self, sequence_id: int, state: str, reason: str, error: dict[str, Any] | None
    ) -> None:
        # A new session: the chunk's may be bound to a release no longer active.
        with self.session_factory() as session:
            try:
                self._hold_lease(session, sequence_id)
            except _LeaseLost:
                return
            job = session.get(Job, sequence_id)
            stop_job(
                session,
                job,
                state=state,
                reason=reason,
                error=error,
                retention_days=self.settings.retention_days,
            )
            session.commit()

    # --- the thread -------------------------------------------------------------------------------

    def start(self) -> None:
        self._stopping.clear()
        self._thread = threading.Thread(target=self._loop, name="rdm-job-worker", daemon=True)
        self._thread.start()

    def stop(self, timeout: float = 30.0) -> None:
        """Stop after the running chunk and release this worker's leases, so another process
        resumes its jobs at once."""
        self._stopping.set()
        self._wake.set()
        if self._thread is not None:
            self._thread.join(timeout)
            self._thread = None
        try:
            with self.session_factory() as session:
                session.execute(
                    update(Job)
                    .where(Job.lease_owner == self.owner, Job.state == "running")
                    .values(lease_owner=None, lease_expires_at=None)
                    .execution_options(synchronize_session=False)
                )
                session.commit()
        except Exception:
            logger.exception("The job worker could not release its leases; they expire instead")

    def wake(self) -> None:
        """A job was queued or cancelled: look now rather than at the next poll."""
        self._wake.set()

    def _loop(self) -> None:
        next_sweep = 0.0
        while not self._stopping.is_set():
            worked, wait = False, IDLE_SECONDS
            try:
                if time.monotonic() >= next_sweep:
                    self.sweep()
                    next_sweep = time.monotonic() + SWEEP_SECONDS
                worked = self.run_once()
                if not worked and self._leased_elsewhere_until is not None:
                    expires_in = as_utc(self._leased_elsewhere_until) - datetime.now(UTC)
                    wait = min(IDLE_SECONDS, max(0.1, expires_in.total_seconds()))
            except Exception:
                logger.exception(
                    "The job worker could not reach the database; it retries in %s s",
                    RETRY_SECONDS,
                )
                wait = RETRY_SECONDS
            if not worked:
                self._wake.wait(min(wait, next_sweep - time.monotonic()))
                self._wake.clear()


def _cancel_requested(session: Session, sequence_id: int) -> Callable[[], bool]:
    def requested() -> bool:
        return (
            session.scalar(select(Job.cancel_requested_at).where(Job.sequence_id == sequence_id))
            is not None
        )

    return requested


def _error_body(error: ApiError) -> dict[str, Any]:
    body: dict[str, Any] = {"code": error.code, "message": error.message}
    if error.details is not None:
        body["details"] = error.details
    return body
