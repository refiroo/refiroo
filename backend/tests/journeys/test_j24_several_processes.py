"""J24.3 and J24.8 across processes — the job worker of two server processes on one database
(USER_JOURNEYS.md, Base 0.11 N2).

Each process is a server started as an operator starts it (``processes.run``), the two sharing
``JOB_FILE_DIR`` as OPERATIONS asks of several nodes. A process is frozen with ``SIGSTOP`` and
resumed with ``SIGCONT``, as a node that stops answering and comes back; a lock held from the
test's own connection holds a job's step until the test lets it go. A worker keeps its lease with a
heartbeat while its process runs (D170), and every process's workers are woken by the job
notifications any process sends (D173); a partial export file belongs to one lease (D174).
"""

import hashlib
import json
import os
import shutil
import signal
import tempfile
import time
from collections.abc import Iterator
from contextlib import ExitStack, contextmanager
from pathlib import Path

import pytest
import seeds
from processes import run
from scenario import W1, W2, ok, scenario_seed
from service import scalar
from sqlalchemy import create_engine, text
from sqlalchemy.pool import NullPool
from test_j24_background_job import _items, _submit
from test_j27_export import _export

# The lease of these processes' workers (seconds): short, so a frozen process loses its job soon.
LEASE = "2"
FINAL = {"completed", "failed", "cancelled", "expired"}


@contextmanager
def _nodes(configuration, **settings: str) -> Iterator[tuple]:
    """Processes A and B on one clone of the configuration's seed, sharing ``JOB_FILE_DIR``; each
    resumed at the end if the test left it frozen."""
    name = scenario_seed(configuration)
    ids = seeds.ensure(name)["ids"]
    url = seeds.clone(name)
    files = Path(tempfile.mkdtemp(prefix="rdm-n2-"))
    shared = {"JOB_FILE_DIR": str(files), "JOB_LEASE_SECONDS": LEASE, **settings}
    try:
        with ExitStack() as stack:
            a = stack.enter_context(run(configuration, url, ids, **shared))
            b = stack.enter_context(run(configuration, url, ids, **shared))
            try:
                yield a, b, url
            finally:
                for each in (a, b):
                    _resume(each)
    finally:
        seeds.drop(url.database)
        shutil.rmtree(files, ignore_errors=True)


def _freeze(process, url=None) -> None:
    """Freeze the process; with ``url``, first wait until no session of the database is inside a
    transaction, so the frozen process holds no lock the test does not mean it to (its worker's
    sweep at start, a claim)."""
    if url is not None:
        deadline = time.monotonic() + 30
        while scalar(
            url,
            "SELECT count(*) FROM pg_stat_activity WHERE datname = current_database() "
            "AND pid <> pg_backend_pid() AND state IN ('active', 'idle in transaction')",
        ):
            assert time.monotonic() < deadline, "the processes never became idle"
            time.sleep(0.05)
    os.kill(process.pid, signal.SIGSTOP)


def _resume(process) -> None:
    try:
        os.kill(process.pid, signal.SIGCONT)
    except ProcessLookupError:
        pass


@contextmanager
def _holding(url, statement: str, **params) -> Iterator[None]:
    """``statement`` (a lock) held from the test's own connection while the block runs."""
    engine = create_engine(url, poolclass=NullPool)
    holder = engine.connect()
    try:
        holder.execute(text(statement), params)
        yield
    finally:
        holder.rollback()
        holder.close()
        engine.dispose()


def _waiting(url, count: int) -> None:
    """Returns once PostgreSQL shows ``count`` statements waiting for a lock."""
    deadline = time.monotonic() + 30
    while time.monotonic() < deadline:
        waiting = scalar(
            url,
            "SELECT count(*) FROM pg_stat_activity WHERE datname = current_database() "
            "AND wait_event_type = 'Lock'",
        )
        if waiting >= count:
            return
        time.sleep(0.05)
    raise AssertionError(f"{count} statements never waited for the held lock")


def _held_by(url, job_id: str, process, seconds: float = 30) -> None:
    """Returns once the job's lease is held by ``process``'s worker (its owner names the PID)."""
    deadline, owner = time.monotonic() + seconds, None
    while time.monotonic() < deadline:
        owner = scalar(url, "SELECT lease_owner FROM jobs WHERE id = :id", id=job_id)
        if owner is not None and f":{process.pid}:" in owner:
            return
        time.sleep(0.05)
    raise AssertionError(f"job {job_id} was never claimed by process {process.pid}: {owner}")


def _job(world, job_id, states, seconds: float = 60):
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        job = ok(world.api.get(f"/jobs/{job_id}"))
        if job["state"] in states:
            return job
        time.sleep(0.1)
    raise AssertionError(f"job {job_id} stayed {job['state']} for {seconds} s")


@pytest.mark.journey("J24.3")
@pytest.mark.structures("R", "R.u")
def test_a_frozen_node_loses_its_job_and_commits_nothing(configuration):
    """Given processes A and B. When A's worker applies a chunk of a background batch and A is
    frozen. Then once A's lease expires B takes the job over and completes it; A, resumed and
    reaching its commit, commits nothing; every item is applied once."""
    with _nodes(configuration, JOB_CHUNK_ITEMS="10") as (a, b, url):
        _freeze(b, url)
        with _holding(url, "SELECT 1 FROM workspaces WHERE key = :k FOR UPDATE", k=W1):
            job = _submit(a.world, _items(a.world, 40, "F"))
            _held_by(url, job["id"], a)
            _waiting(url, 1)
            _freeze(a)
            _resume(b)
            _held_by(url, job["id"], b)
        # A's statement was waiting for the lock and holds it now, in A's open transaction: B
        # goes on only once A, resumed, reaches its commit and rolls back.
        _resume(a)
        done = _job(b.world, job["id"], FINAL)
        assert (done["state"], done["counts"]["applied"]) == ("completed", 40), done
        page = ok(b.world.api.get(f"/objects/{b.world.key('R')}", search="F ", pageSize=100))
        assert sorted(b.world.names(page)) == [f"F {n:03d}" for n in range(40)]


@pytest.mark.journey("J24.8")
@pytest.mark.structures("R", "R.u")
def test_a_job_queued_on_a_busy_node_starts_on_an_idle_one(configuration):
    """Given processes A and B, A's worker held in a long chunk. When a job of another workspace is
    sent to A. Then it starts on B within 5 s."""
    with _nodes(configuration) as (a, b, url):
        _freeze(b, url)
        with _holding(url, "SELECT 1 FROM workspaces WHERE key = :k FOR UPDATE", k=W1):
            busy = _submit(a.world, _items(a.world, 5, "Busy"))
            _held_by(url, busy["id"], a)
            _waiting(url, 1)
            _resume(b)
            time.sleep(1)
            sent = time.monotonic()
            other = _submit(a.world, _items(a.world, 5, "Idle"), workspace=W2)
            _held_by(url, other["id"], b, seconds=5)
            assert time.monotonic() - sent < 5
            _job(a.world, other["id"], {"completed"}, seconds=30)
        assert _job(a.world, busy["id"], {"completed"})["counts"]["applied"] == 5


@pytest.mark.journey("J24.8", "J27.1")
@pytest.mark.structures("R", "R.u")
def test_an_export_taken_over_by_another_node_serves_a_whole_file(configuration):
    """Given processes A and B. When A's worker runs an export and A is frozen until B has taken
    the export over and completed it, then resumed. Then the export is completed and its file is
    served whole: every record of its manifest, each line JSON."""
    with _nodes(configuration) as (a, b, url):
        loaded = _submit(a.world, _items(a.world, 30, "Export"))
        assert _job(a.world, loaded["id"], FINAL)["state"] == "completed"
        _freeze(b, url)
        with _holding(url, "LOCK TABLE objects IN ACCESS EXCLUSIVE MODE"):
            job = ok(_export(a.world, W1, [{"objectTypeKey": a.world.key("R")}]), 202)
            _held_by(url, job["id"], a)
            _waiting(url, 1)
            _freeze(a)
            _resume(b)
            _held_by(url, job["id"], b)
        done = _job(b.world, job["id"], FINAL)
        assert done["state"] == "completed", done
        _resume(a)
        time.sleep(2)
        response = b.world.api.get(f"/jobs/{job['id']}/output")
        assert response.status_code == 200, response.text
        output = ok(b.world.api.get(f"/jobs/{job['id']}"))["output"]
        assert len(response.content) == output["bytes"]
        assert hashlib.sha256(response.content).hexdigest() == output["sha256"]
        lines = [json.loads(line) for line in response.content.decode().splitlines()]
        counts = output["counts"]
        assert len(lines) == sum(counts["records"].values()) + sum(counts["relations"].values())
