"""Job files in ``JOB_FILE_DIR`` (INTEGRATION_API P6, D12, D55; Base 0.9 J1).

A file is named after its job: ``{jobId}.partial`` while it is written, ``{jobId}.{extension}`` once
its job completed. No path is stored on the job. Output is served only for a completed job, so a
file is kept only while its job is completed: a cancel, a failure, a restart or retention removes
it, and :meth:`JobFiles.reconcile` removes whatever a stopped process left behind.

An import's uploaded file (0.9 J2) is ``{jobId}.source``, kept while its job waits or runs: a
restart binds it again. It goes when the job finishes.
"""

import logging
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from ...models.database import Job

logger = logging.getLogger(__name__)

PARTIAL = "partial"
SOURCE = "source"
# The states in which an import still reads its file.
READS_SOURCE = frozenset({"queued", "running", "awaiting_confirmation"})


@dataclass(frozen=True)
class JobFiles:
    directory: Path

    def partial(self, job_id: str) -> Path:
        return self.directory / f"{job_id}.{PARTIAL}"

    def final(self, job_id: str, extension: str) -> Path:
        return self.directory / f"{job_id}.{extension}"

    def source(self, job_id: str) -> Path:
        return self.directory / f"{job_id}.{SOURCE}"

    def remove(self, job_id: str) -> None:
        """Every file of the job, written or partial."""
        for path in self.directory.glob(f"{job_id}.*"):
            path.unlink(missing_ok=True)

    def reconcile(self, session: Session) -> int:
        """Remove each file whose job neither runs nor is completed (expired, cancelled, failed,
        unknown), each partial file of a completed job, and each import's file whose job no
        longer reads it; the number removed."""
        if not self.directory.is_dir():
            return 0
        paths = [path for path in self.directory.iterdir() if path.is_file() and "." in path.name]
        if not paths:
            return 0
        ids = {path.name.split(".", 1)[0] for path in paths}
        states = dict(session.execute(select(Job.id, Job.state).where(Job.id.in_(ids))).all())
        removed = 0
        for path in paths:
            job_id, extension = path.name.split(".", 1)
            state = states.get(job_id)
            # A running export's file is renamed into place just before the commit that completes
            # its job, so a running job keeps its file under either name.
            if extension == SOURCE:
                keep = state in READS_SOURCE
            else:
                keep = state == "running" or (extension != PARTIAL and state == "completed")
            if not keep:
                path.unlink(missing_ok=True)
                removed += 1
        if removed:
            logger.info("Removed %d job file(s) whose job no longer serves them", removed)
        return removed
