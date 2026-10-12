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

    def scalars(self, _statement):
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


class _Uploads(_NoJobs):
    """A session that knows no job and the source files named."""

    def __init__(self, *names: str) -> None:
        self.names = names

    def scalars(self, _statement):
        return list(self.names)


def test_a_source_file_stays_while_its_row_exists_and_goes_once_it_is_gone(tmp_path):
    """0.10 A3 (D5): a source file outlives every job; the sweep removes it once its row is gone
    and the file is older than a row's commit could be."""
    files = JobFiles(tmp_path)
    kept, gone, new = (str(uuid4()) for _ in range(3))
    old = time.time() - UNCOMMITTED_SECONDS - 60
    for name in (kept, gone, new):
        files.upload(name).write_bytes(b"x")
    for name in (kept, gone):
        os.utime(files.upload(name), (old, old))
    assert files.reconcile(_Uploads(kept)) == 1
    assert files.upload(kept).is_file() and files.upload(new).is_file()
    assert not files.upload(gone).exists()
