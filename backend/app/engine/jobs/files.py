"""Job files in ``JOB_FILE_DIR`` (INTEGRATION_API P6, D12, D55; Base 0.9 J1).

A file is named after its job: ``{jobId}.{lease}.partial`` while a worker writes it, named after
that worker's lease so a worker that lost the export to another never writes or removes the other's
(0.11 N2, D174), and ``{jobId}.{extension}`` once its job completed. No path is stored on the job. Output is served only for a completed job, so a
file is kept only while its job is completed: a cancel, a failure, a restart or retention removes
it, and :meth:`JobFiles.reconcile` removes whatever a stopped process left behind.

An import's uploaded file (0.9 J2) is ``{jobId}.source``, kept while its job waits or runs: a
restart binds it again. It goes when the job finishes.

A source file (0.10 A3, D5) is ``{sourceFileId}.upload``, kept while its ``source_files`` row
exists: it lives as long as the draft or profile that owns it, not as long as a job.
"""

import logging
import time
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from ...models.database import Job, SourceFile

logger = logging.getLogger(__name__)

PARTIAL = "partial"
SOURCE = "source"
UPLOAD = "upload"
# The states in which an import still reads its file.
READS_SOURCE = frozenset({"queued", "running", "awaiting_confirmation"})
# A file of no job stays this long after it was last written (0.9 R-F10): an import writes its file
# just before the commit that stores its job, so a sweep in between would see no job yet.
UNCOMMITTED_SECONDS = 600


@dataclass(frozen=True)
class JobFiles:
    directory: Path

    def partial(self, job_id: str, lease: str) -> Path:
        return self.directory / f"{job_id}.{lease}.{PARTIAL}"

    def final(self, job_id: str, extension: str) -> Path:
        return self.directory / f"{job_id}.{extension}"

    def source(self, job_id: str) -> Path:
        return self.directory / f"{job_id}.{SOURCE}"

    def upload(self, source_file_id: str) -> Path:
        return self.directory / f"{source_file_id}.{UPLOAD}"

    def remove(self, job_id: str) -> None:
        """Every file of the job, written or partial."""
        for path in self.directory.glob(f"{job_id}.*"):
            path.unlink(missing_ok=True)

    def reconcile(self, session: Session) -> int:
        """Remove each file whose job neither runs nor is completed (expired, cancelled, failed,
        unknown), each partial file of a completed job, each import's file whose job no
        longer reads it, and each source file whose row is gone; the number removed. A file of no job written in the last
        :data:`UNCOMMITTED_SECONDS` is left for a later sweep: its job may not be committed yet."""
        if not self.directory.is_dir():
            return 0
        paths = [path for path in self.directory.iterdir() if path.is_file() and "." in path.name]
        if not paths:
            return 0
        ids = {path.name.split(".", 1)[0] for path in paths}
        states = dict(session.execute(select(Job.id, Job.state).where(Job.id.in_(ids))).all())
        named = {path.name.split(".", 1)[0] for path in paths if path.name.endswith(f".{UPLOAD}")}
        uploads = (
            set(
                session.scalars(select(SourceFile.public_id).where(SourceFile.public_id.in_(named)))
            )
            if named
            else set()
        )
        removed = 0
        recent = time.time() - UNCOMMITTED_SECONDS
        for path in paths:
            job_id, extension = path.name.split(".", 1)
            state = states.get(job_id)
            if extension == UPLOAD:
                # A source file is written just before the commit that stores its row.
                if job_id not in uploads and _modified(path) <= recent:
                    path.unlink(missing_ok=True)
                    removed += 1
                continue
            if state is None and _modified(path) > recent:
                continue
            # A running export's file is renamed into place just before the commit that completes
            # its job, so a running job keeps its file under either name.
            if extension == SOURCE:
                keep = state in READS_SOURCE
            else:
                partial = extension.endswith(PARTIAL)
                keep = state == "running" or (not partial and state == "completed")
            if not keep:
                path.unlink(missing_ok=True)
                removed += 1
        if removed:
            logger.info("Removed %d job file(s) whose job no longer serves them", removed)
        return removed


def _modified(path: Path) -> float:
    try:
        return path.stat().st_mtime
    except FileNotFoundError:
        return 0.0
