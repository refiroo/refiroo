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
One worker runs one chunk at a time, whichever thread asks (its loop, or ``run_until_idle``): its
claims accept its own leases, so two of its threads would otherwise run the same chunk (0.11 S1).
Lock order inside a chunk: the workspace (live) or the change set, then the write path's own
(records), then the job row at the checkpoint (ARCHITECTURE).

**Stopping.** Before each chunk the worker reads the job: a cancel request finishes it
``cancelled``; a release no longer the pinned one fails it with ``MODEL_RELEASE_CHANGED``; another
refusal of the context (a retired workspace, a lost change set claim) fails it with that error. An
``atomic`` job's chunk also checks for a cancel request between items and rolls back completely.
Any other error rolls the chunk back and fails the job with ``JOB_FAILED`` (D29). Items without an
outcome then become ``unprocessed`` with the stop's reason; chunks committed before stay applied.

**Retention.** The worker expires finished jobs past ``expiresAt`` every hour (D14, D30), and
removes the job files no completed job serves any more (``files.py``).

**Imports** (Base 0.9 J2, D73) run on the batch worker. An import's first step binds its file
(``imports/binding.py``): its rejected rows become its first outcomes and its items its inputs, in
one commit; a restart before that commit binds the file again. Its chunks then run as a background
batch's. Its file goes once the job finishes. A preview (0.9 J3) runs its items in one step that is
rolled back (``preview.py``), records what they would do and waits for confirmation without
a lease; a confirmed preview is queued again and binds its file anew (D81).

**Source files** (0.10 A3): a ``profile`` job stages a source file's cells and profiles them in one
step (``sources/profiling.py``). A ``dryRun`` binds a draft's source file from its staged cells and
previews every item against the draft's model, as an import's preview does, then completes with its
summary (``sources/dry_run.py``); it stops as ``cancelled`` once its draft has changed. An
``inference`` (0.10 A6) proposes from a draft's source file in one step (``sources/inference/``).
A file of an import profile is checked once profiled (0.10 A5c): a ``profileCheck`` compares its
columns, then binds its staged cells through the profile and previews every item in the profile's
workspace as a dry run does, and completes with its report (``sources/profile_check.py``).

**Exports** (Base 0.9 J1, D53) run on a worker of their own, which claims only ``export`` jobs while
the batch worker claims the rest, so neither kind waits behind the other. An export runs in one
step from one snapshot (``exports.py``); a cancel request, the lease and progress go through a short
session of the worker's own, between the export's rows. A failed, cancelled or lost export leaves no
file; a completed one's file is renamed into place before the commit that completes the job.
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
from sqlalchemy import case, func, or_, select, update
from sqlalchemy.orm import Session

from ...common.outage import OutageLog
from ...common.time import as_utc
from ...errors import ApiError
from ...models.commands import BatchItem
from ...models.database import ChangeSet, Job
from ..imports.binding import ImportLimits, bind_import
from ..model import change_set_migrations, migrations
from ..moves import move_job, move_load
from ..moves.mapping_inference import run_inference as run_mapping_inference
from ..sources.dry_run import (
    book_opener,
    dry_run_context,
    record_dry_run,
    superseded,
)
from ..sources.inference.run import run_inference
from ..sources.profile_check import (
    complete_unbound,
    prepare,
    queue_check,
    record_check,
    record_findings,
)
from ..sources.profiling import profile_source_file
from ..sources.store import expire_superseded, load_source_file
from .background import open_job_context
from .batches import BatchContext, JobCancelled, run_items
from .exports import ExportCancelled, ExportControl, run_export
from .files import JobFiles
from .preview import preview_items, record_preview
from .store import (
    FINISHED,
    PREVIEWED_KINDS,
    ROW_KINDS,
    LeaseLost,
    complete_job,
    expire_jobs,
    finish_export,
    load_inputs,
    previewing,
    record_binding,
    record_outcomes,
    stop_export,
    stop_job,
)

logger = logging.getLogger(__name__)

# A job queued or cancelled in this process wakes the worker at once. Otherwise it looks again when
# a lease held elsewhere expires, and at least this often (a job queued by another process).
IDLE_SECONDS = 60.0
RETRY_SECONDS = 2.0
SWEEP_SECONDS = 3600.0
# The worker threads' names, which a measurement of one request's statements leaves out.
THREAD_NAME = "rdm-job-worker"
EXPORT_THREAD_NAME = "rdm-export-worker"
BATCH_KINDS = (
    "batch",
    "import",
    "profile",
    "dryRun",
    "inference",
    "profileCheck",
    "migration",
    "mappingInference",
    "move",
)
EXPORT_KINDS = ("export",)
_ITEM = TypeAdapter(BatchItem)
# The jobs that bind a source file's staged cells rather than a job file (0.10 A3, A5c).
_STAGED_KINDS = ("dryRun", "profileCheck")


@dataclass(frozen=True)
class WorkerSettings:
    chunk_items: int
    lease_seconds: int
    retention_days: int
    # An import's items once its file is bound, under the batch limits (D13).
    atomic_max_items: int = 10_000
    background_max_items: int = 1_000_000
    # The items a preview runs (JOB_PREVIEW_MAX_ITEMS; 0.9 J3, D83; batches since 0.9 K2).
    preview_max_items: int = 10_000
    # The inference assistant (INFERENCE_ASSISTANT, INFERENCE_ASSISTANT_ROWS; 0.10 A6, D95).
    inference_assistant: str = ""
    inference_assistant_rows: int = 20


# Another worker holds the job now; this chunk must not commit.
_LeaseLost = LeaseLost


class JobWorker:
    """Runs jobs in this process: ``run_once`` runs one chunk; ``start`` runs them on a thread."""

    def __init__(
        self,
        session_factory: Callable[[], Session],
        settings: WorkerSettings,
        *,
        owner: str | None = None,
        kinds: tuple[str, ...] = BATCH_KINDS,
        files: JobFiles | None = None,
        sweeps: bool = True,
        thread_name: str = THREAD_NAME,
    ) -> None:
        self.session_factory = session_factory
        self.settings = settings
        self.owner = owner or f"{socket.gethostname()}:{os.getpid()}:{uuid4().hex[:8]}"
        self.kinds = kinds
        self.files = files
        self.sweeps = sweeps
        self.thread_name = thread_name
        self._wake = threading.Event()
        self._stopping = threading.Event()
        self._thread: threading.Thread | None = None
        self._one_chunk = threading.Lock()
        # The earliest expiry of a lease another worker holds, seen by the last claim.
        self._leased_elsewhere_until: datetime | None = None

    # --- one step ---------------------------------------------------------------------------------

    def run_once(self) -> bool:
        """Claim the oldest job this worker may run and run its next chunk; ``False`` when none
        is waiting."""
        with self._one_chunk:
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
        """Expire finished jobs past their retention, delete source files superseded longer ago
        (0.10 A3, D5) and remove the files no job or source file serves any more; the number of
        jobs expired."""
        now = now or datetime.now(UTC)
        with self.session_factory() as session:
            expired = expire_jobs(session, now)
            superseded_files = expire_superseded(session, now, self.settings.retention_days)
            session.commit()
            if self.files is not None:
                for source_file_id in superseded_files:
                    self.files.upload(source_file_id).unlink(missing_ok=True)
            if self.files is not None:
                self.files.reconcile(session)
        return expired

    def _claim(self) -> int | None:
        now = datetime.now(UTC)
        claimable = (
            Job.kind.in_(self.kinds),
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
                        Job.kind.in_(self.kinds),
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
                    stage=case(
                        ((Job.kind == "profile"), "profiling"),
                        ((Job.kind.in_(("inference", "mappingInference"))), "inferring"),
                        (Job.kind.in_(ROW_KINDS) & Job.total.is_(None), "binding"),
                        ((Job.kind == "move") & Job.total.is_(None), "binding"),
                        (
                            (Job.kind == "move")
                            & Job.confirmed_at.is_(None)
                            & (Job.parameters["stage"].as_string() == "preview"),
                            "previewing",
                        ),
                        (
                            Job.kind.in_(PREVIEWED_KINDS)
                            & Job.confirmed_at.is_(None)
                            & (Job.parameters["stage"].as_string() == "preview"),
                            "previewing",
                        ),
                        else_="applying",
                    ),
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
                self._stop(sequence_id, "cancelled", "JOB_CANCELLED", None)
                return
            if job.kind == "export":
                session.expunge(job)
                session.rollback()
                self._run_export(job)
                return
            try:
                if job.kind == "migration":
                    self._migrate(session, job)
                elif job.kind == "profile":
                    self._profile(session, job)
                elif job.kind == "inference":
                    self._infer(session, job)
                elif job.kind == "mappingInference":
                    self._infer_mapping(session, job)
                elif job.kind == "move":
                    self._move(session, job)
                elif job.kind in ROW_KINDS and job.total is None:
                    self._bind(session, job)
                elif previewing(job):
                    self._preview(session, job)
                else:
                    self._apply_chunk(session, job)
            except JobCancelled:
                session.rollback()
                self._stop(sequence_id, "cancelled", "JOB_CANCELLED", None)
            except _LeaseLost:
                session.rollback()
            except ApiError as error:
                session.rollback()
                reason = (
                    "MODEL_RELEASE_CHANGED"
                    if error.code == "MODEL_RELEASE_CHANGED"
                    else "JOB_FAILED"
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
                    "JOB_FAILED",
                    {
                        "code": "JOB_FAILED",
                        "message": "The job stopped because of an internal error. Items it "
                        "applied before stay applied; the rest are unprocessed and may be sent "
                        "again. If it recurs, report the correlation ID",
                        "details": {"correlationId": correlation_id},
                    },
                )

    def _apply_chunk(self, session: Session, job: Job) -> None:
        atomic = job.parameters.get("policy") == "atomic"
        context = open_job_context(session, job)
        inputs = load_inputs(session, job, job.total if atomic else self.settings.chunk_items)
        outcomes = run_items(
            session,
            context,
            [(index, _ITEM.validate_python(item)) for index, item in inputs],
            policy=job.parameters["policy"],
            on_existing=job.parameters.get("onExisting", "reject"),
            other_workspace_ids=job.parameters.get("otherWorkspaceIds", "refuse"),
            expected_change_set_version=job.change_set_version,
            job_id=job.id,
            should_stop=self._chunk_check(job.sequence_id) if atomic else None,
            file_rows=job.kind in ROW_KINDS,
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
        self._finished_import(job)

    # --- migrations (0.11 V1) ---------------------------------------------------------------------

    def _migrate(self, session: Session, job: Job) -> None:
        """A migration's preview, rolled back and left waiting, or its confirmed execution, in one
        step each (``model/migrations.py``)."""
        retention = self.settings.retention_days

        def hold() -> None:
            self._hold_lease(session, job.sequence_id)

        def renew() -> None:
            self._renew_lease(job.sequence_id)

        # A change set's move (0.11 V3) is the same job kind over the change set's rows.
        steps = change_set_migrations if migrations.moves_change_set(job) else migrations
        if previewing(job):
            steps.run_preview(session, job, retention_days=retention, hold=hold, renew=renew)
            session.commit()
            return
        steps.execute(session, job, retention_days=retention, hold=hold, renew=renew)

    def _renew_lease(self, sequence_id: int) -> None:
        """Extend a lease from a short session of its own, between a long step's statements (a
        migration's, 0.11 V1): the step's transaction does not hold the job row, so this never
        waits for it. Another worker holding the job ends the step (``LeaseLost``)."""
        with self.session_factory() as session:
            renewed = session.execute(
                update(Job)
                .where(Job.sequence_id == sequence_id, Job.lease_owner == self.owner)
                .values(
                    lease_expires_at=datetime.now(UTC)
                    + timedelta(seconds=self.settings.lease_seconds)
                )
                .execution_options(synchronize_session=False)
            )
            session.commit()
        if renewed.rowcount != 1:
            raise _LeaseLost

    # --- imports ----------------------------------------------------------------------------------

    def _bind(self, session: Session, job: Job) -> None:
        """Bind the import's file into its outcomes and inputs in one commit (0.9 J2). Under
        ``atomic`` a rejected row ends the job there: its items become ``unprocessed``."""
        context = self._context(session, job)
        if job.kind == "profileCheck":
            runnable = prepare(session, job, context.model)
            self._hold_lease(session, job.sequence_id)
            if not runnable:
                # The profile has problems, or no source fits the file: the report is complete.
                complete_unbound(session, job, retention_days=self.settings.retention_days)
                session.commit()
                return
            # The check's report and its profile commit before binding: binding renews the lease
            # from a session of its own, which would wait for this one's lock on the job row.
            session.commit()
            job = session.get(Job, job.sequence_id)
        files = self._files()
        bound = bind_import(
            session,
            job,
            files.source(job.id),
            context.model,
            lambda: self._binding_check(job),
            ImportLimits(
                atomic_max_items=self.settings.atomic_max_items,
                background_max_items=self.settings.background_max_items,
            ),
            book_opener(session, job, files) if job.kind in _STAGED_KINDS else None,
        )
        self._hold_lease(session, job.sequence_id)
        record_binding(
            session, job, rejected=bound.rejected, items=bound.items, report=bound.report
        )
        if job.kind == "profileCheck":
            record_findings(job, bound.findings)
        retention = self.settings.retention_days
        if previewing(job):
            # The preview runs next, every item whatever the policy (D80).
            job.stage = "previewing"
            job.lease_expires_at = datetime.now(UTC) + timedelta(
                seconds=self.settings.lease_seconds
            )
        elif job.parameters.get("policy") == "atomic" and bound.rejected:
            stop_job(
                session,
                job,
                state="completed",
                reason="BATCH_ROLLED_BACK",
                error=None,
                retention_days=retention,
            )
        elif job.processed >= job.total:
            complete_job(session, job, retention_days=retention)
        else:
            job.lease_expires_at = datetime.now(UTC) + timedelta(
                seconds=self.settings.lease_seconds
            )
        session.commit()
        self._finished_import(job)

    def _preview(self, session: Session, job: Job) -> None:
        """Run the preview's items and roll them back (D82); then, holding the lease, record what
        they would do and leave the job waiting for confirmation. A restart meanwhile runs the
        preview again from the stored inputs."""
        sequence_id = job.sequence_id
        context = self._context(session, job)
        dry_run = job.kind == "dryRun"
        outcomes = preview_items(
            session,
            job,
            context,
            # A dry run and a profile's check run the whole file (D67).
            limit=job.total if job.kind in _STAGED_KINDS else self.settings.preview_max_items,
            should_stop=self._stop_check(job),
        )
        session.rollback()
        self._hold_lease(session, sequence_id)
        job = session.get(Job, sequence_id)
        if dry_run:
            record_dry_run(
                session, job, outcomes, context.model, retention_days=self.settings.retention_days
            )
        elif job.kind == "profileCheck":
            record_check(
                session, job, outcomes, context.model, retention_days=self.settings.retention_days
            )
        else:
            record_preview(session, job, outcomes, retention_days=self.settings.retention_days)
        session.commit()

    def _context(self, session: Session, job: Job) -> BatchContext:
        """Where the job's items run: a dry run's, with its draft's model; any other's."""
        if job.kind == "dryRun":
            return dry_run_context(session, job)
        return open_job_context(session, job)

    def _stop_check(self, job: Job) -> Callable[[], bool]:
        """A preview's stop check; a dry run also stops once its draft has changed."""
        renewed = self._chunk_check(job.sequence_id)
        if job.kind != "dryRun":
            return renewed
        parameters = dict(job.parameters)

        def check() -> bool:
            if renewed():
                return True
            with self.session_factory() as session:
                return superseded(session, parameters)

        return check

    # --- source files -----------------------------------------------------------------------------

    def _profile(self, session: Session, job: Job) -> None:
        """Stage and profile the job's source file in one step and complete the job."""
        source_file_id = job.parameters["sourceFileId"]
        profile_source_file(
            session,
            source_file_id,
            self._files().upload(source_file_id),
            lambda: self._binding_check(job),
        )
        self._hold_lease(session, job.sequence_id)
        complete_job(session, job, retention_days=self.settings.retention_days)
        # A profile has no items, so no result.
        job.result = None
        source = load_source_file(session, source_file_id)
        if source.profile_key is not None:
            # A profile's next file is checked once profiled (0.10 A5c, D83).
            queue_check(session, source, retention_days=self.settings.retention_days)
        session.commit()

    def _infer(self, session: Session, job: Job) -> None:
        """Propose from the job's draft's source file in one step and complete the job (0.10 A6)."""
        run_inference(
            session,
            job,
            assistant_setting=self.settings.inference_assistant,
            assistant_rows=self.settings.inference_assistant_rows,
            check=lambda: self._binding_check(job),
        )
        self._hold_lease(session, job.sequence_id)
        complete_job(session, job, retention_days=self.settings.retention_days)
        # An inference has no items, so no result.
        job.result = None
        session.commit()

    def _infer_mapping(self, session: Session, job: Job) -> None:
        """Propose a model mapping in one step and complete the job (0.11 X1)."""
        run_mapping_inference(session, job, check=lambda: self._binding_check(job))
        self._hold_lease(session, job.sequence_id)
        complete_job(session, job, retention_days=self.settings.retention_days)
        # An inference has no items, so no result.
        job.result = None
        session.commit()

    # --- moves (0.11 X2, X3) ----------------------------------------------------------------------

    def _move(self, session: Session, job: Job) -> None:
        """A move: its binding committed with its rows and inputs; then, at the next chunk, the
        preview of every input, rolled back, the job left waiting with its summary
        (``moves/move_job.py``); once confirmed, or at once with ``stage: execute``, its load into
        a change set, one step per chunk (``moves/move_load.py``)."""
        sequence_id = job.sequence_id
        if job.total is not None and move_load.loading(job):
            move_load.load_step(
                session,
                job,
                chunk_items=self.settings.chunk_items,
                hold=lambda: self._hold_lease(session, sequence_id),
                retention_days=self.settings.retention_days,
            )
            if job.state == "running":
                job.lease_expires_at = datetime.now(UTC) + timedelta(
                    seconds=self.settings.lease_seconds
                )
            session.commit()
            return
        if job.total is None:
            move_job.bind(session, job)
            self._hold_lease(session, sequence_id)
            job.lease_expires_at = datetime.now(UTC) + timedelta(
                seconds=self.settings.lease_seconds
            )
            session.commit()
            return

        def hold(clean: Session) -> Job:
            self._hold_lease(clean, sequence_id)
            return clean.get(Job, sequence_id)

        move_job.preview(
            session,
            job,
            should_stop=self._chunk_check(sequence_id),
            hold=hold,
            retention_days=self.settings.retention_days,
        )
        session.commit()

    def _binding_check(self, job: Job) -> None:
        """While a file is bound or staged: renew the lease, and stop for a cancel request, a lost
        lease or, for a dry run, its draft changed."""
        if self._stop_check(job)():
            raise JobCancelled

    def _chunk_check(self, sequence_id: int) -> Callable[[], bool]:
        """An atomic chunk's or a preview's stop check (D28), asked every few hundred items: it
        also renews the lease in a short session of its own, so a long chunk keeps its job
        (0.9 R-F12); a lost lease stops it."""
        return lambda: self._renewed(sequence_id)

    def _renewed(self, sequence_id: int) -> bool:
        """Renew the job's lease in a short transaction; ``True`` when a cancel was requested.
        Raises ``_LeaseLost`` when another worker holds the job."""
        with self.session_factory() as session:
            row = session.execute(
                select(Job.lease_owner, Job.cancel_requested_at)
                .where(Job.sequence_id == sequence_id)
                .with_for_update()
            ).one()
            if row.lease_owner != self.owner:
                session.rollback()
                raise _LeaseLost
            session.execute(
                update(Job)
                .where(Job.sequence_id == sequence_id)
                .values(
                    lease_expires_at=datetime.now(UTC)
                    + timedelta(seconds=self.settings.lease_seconds)
                )
                .execution_options(synchronize_session=False)
            )
            session.commit()
        return row.cancel_requested_at is not None

    def _finished_import(self, job: Job) -> None:
        if job.kind == "import" and job.state in FINISHED and self.files is not None:
            self.files.remove(job.id)

    def _hold_lease(self, session: Session, sequence_id: int) -> None:
        owner = session.scalar(
            select(Job.lease_owner).where(Job.sequence_id == sequence_id).with_for_update()
        )
        if owner != self.owner:
            raise _LeaseLost

    # --- exports ----------------------------------------------------------------------------------

    def _run_export(self, job: Job) -> None:
        """Run the export from one snapshot in a session of its own; this worker's short sessions
        answer its checks (cancel, lease, progress) meanwhile."""
        files = self._files()
        partial = files.partial(job.id)
        lost: list[bool] = []
        control = ExportControl(
            check=lambda total, processed: self._export_check(
                job.sequence_id, total, processed, lost
            )
        )
        try:
            files.directory.mkdir(parents=True, exist_ok=True)
            with self.session_factory() as work:
                try:
                    outcome = run_export(work, job, partial, control)
                finally:
                    work.rollback()
        except ExportCancelled:
            files.remove(job.id)
            if not lost:
                self._stop(job.sequence_id, "cancelled", "JOB_CANCELLED", None)
            return
        except ApiError as error:
            files.remove(job.id)
            reason = (
                "MODEL_RELEASE_CHANGED" if error.code == "MODEL_RELEASE_CHANGED" else "JOB_FAILED"
            )
            self._stop(job.sequence_id, "failed", reason, _error_body(error))
            return
        except Exception:
            files.remove(job.id)
            correlation_id = uuid4().hex
            logger.exception(
                "Export %s failed (correlation ID %s); it left no file", job.id, correlation_id
            )
            self._stop(
                job.sequence_id,
                "failed",
                "JOB_FAILED",
                {
                    "code": "JOB_FAILED",
                    "message": "The export stopped because of an internal error and left no file. "
                    "Request it again; if it recurs, report the correlation ID",
                    "details": {"correlationId": correlation_id},
                },
            )
            return
        final = files.final(job.id, outcome.extension)
        partial.replace(final)
        with self.session_factory() as session:
            try:
                self._hold_lease(session, job.sequence_id)
            except _LeaseLost:
                session.rollback()
                final.unlink(missing_ok=True)
                return
            stored = session.get(Job, job.sequence_id)
            finish_export(
                session, stored, outcome.output, retention_days=self.settings.retention_days
            )
            session.commit()

    def _export_check(
        self, sequence_id: int, total: int | None, processed: int, lost: list[bool]
    ) -> bool:
        """Record progress and renew the lease; ``True`` when the export must stop: a cancel
        request, or the lease lost to another worker (``lost`` then says so)."""
        with self.session_factory() as session:
            row = session.execute(
                select(Job.lease_owner, Job.cancel_requested_at)
                .where(Job.sequence_id == sequence_id)
                .with_for_update()
            ).one()
            if row.lease_owner != self.owner:
                lost.append(True)
                session.rollback()
                return True
            session.execute(
                update(Job)
                .where(Job.sequence_id == sequence_id)
                .values(
                    total=total,
                    processed=processed,
                    stage="writing",
                    lease_expires_at=datetime.now(UTC)
                    + timedelta(seconds=self.settings.lease_seconds),
                )
                .execution_options(synchronize_session=False)
            )
            session.commit()
            return row.cancel_requested_at is not None

    def _files(self) -> JobFiles:
        if self.files is None:
            raise RuntimeError("This worker was started without JOB_FILE_DIR; it runs no exports")
        return self.files

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
            if job.kind == "export":
                stop_export(
                    session,
                    job,
                    state=state,
                    error=error,
                    retention_days=self.settings.retention_days,
                )
                session.commit()
                if self.files is not None:
                    self.files.remove(job.id)
                return
            stop_job(
                session,
                job,
                state=state,
                reason=reason,
                error=error,
                retention_days=self.settings.retention_days,
            )
            session.commit()
            self._finished_import(job)

    # --- the thread -------------------------------------------------------------------------------

    def start(self) -> None:
        self._stopping.clear()
        self._thread = threading.Thread(target=self._loop, name=self.thread_name, daemon=True)
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
        # Only the batch worker sweeps; the export worker's next sweep never comes.
        next_sweep = 0.0 if self.sweeps else float("inf")
        outage = OutageLog(logger, "The job worker", RETRY_SECONDS)
        while not self._stopping.is_set():
            worked, wait = False, IDLE_SECONDS
            try:
                if self.sweeps and time.monotonic() >= next_sweep:
                    self.sweep()
                    next_sweep = time.monotonic() + SWEEP_SECONDS
                worked = self.run_once()
                if not worked and self._leased_elsewhere_until is not None:
                    expires_in = as_utc(self._leased_elsewhere_until) - datetime.now(UTC)
                    wait = min(IDLE_SECONDS, max(0.1, expires_in.total_seconds()))
                outage.succeeded()
            except Exception as exc:  # noqa: BLE001 - every failure is logged by OutageLog
                outage.failed(exc)
                wait = RETRY_SECONDS
            if not worked:
                # A failed sweep leaves next_sweep in the past, so a retry waits its own time.
                if not outage.failing:
                    wait = min(wait, next_sweep - time.monotonic())
                self._wake.wait(max(0.0, wait))
                self._wake.clear()


def _error_body(error: ApiError) -> dict[str, Any]:
    body: dict[str, Any] = {"code": error.code, "message": error.message}
    if error.details is not None:
        body["details"] = error.details
    return body
