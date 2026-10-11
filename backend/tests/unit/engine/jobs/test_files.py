"""Job files in ``JOB_FILE_DIR`` (0.9 J1, J2; ``engine/jobs/files.py``): what a sweep removes."""

import os
import time
from uuid import uuid4

from app.engine.jobs.files import UNCOMMITTED_SECONDS, JobFiles


class _NoJobs:
    """A session that knows no job."""

    def execute(self, _statement):
        return self

    def all(self):
        return []


def test_a_file_of_no_job_stays_while_its_job_may_not_be_committed(tmp_path):
    """0.9 R-F10: an import writes its file just before the commit that stores its job; a sweep in
    between leaves the file, and a later sweep removes one that never got a job."""
    files = JobFiles(tmp_path)
    fresh, stale = files.source(str(uuid4())), files.source(str(uuid4()))
    fresh.write_bytes(b"x")
    stale.write_bytes(b"x")
    old = time.time() - UNCOMMITTED_SECONDS - 60
    os.utime(stale, (old, old))
    assert files.reconcile(_NoJobs()) == 1
    assert fresh.is_file() and not stale.exists()
