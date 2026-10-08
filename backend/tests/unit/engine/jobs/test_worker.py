"""``engine/jobs/worker.py``: the job worker runs a background job chunk by chunk.

J24 walks a background job through the API (progress, outcomes, a restart, cancellation, two
workers, a change mid-job, retention, a database outage). Here are the worker's own cases: the
change set version a job follows from chunk to chunk, an atomic job as one chunk, a stopping
worker's leases, an unexpected error, what a finished job leaves behind, and the wait between
retries while the database cannot be reached.
"""

import time
from typing import Any

import pytest
from scenario import W1
from sqlalchemy import func, select
from sqlalchemy.exc import OperationalError

from app.common import outage as outage_module
from app.db import SessionLocal
from app.engine.change_sets.lifecycle import create_change_set
from app.engine.jobs import worker as worker_module
from app.engine.jobs.background import submit_background_batch
from app.engine.jobs.worker import JobWorker, WorkerSettings
from app.engine.model.registry import resolve_model_snapshot
from app.models.commands import BatchRequest
from app.models.database import ChangeSet, Job, JobInput, JobItem, RdmObject

CHUNK = 2


def worker(owner: str = "worker-a") -> JobWorker:
    return JobWorker(SessionLocal, WorkerSettings(CHUNK, 120, 7), owner=owner)


def items(world, count: int, prefix: str = "J", clash: int | None = None) -> list[dict[str, Any]]:
    """Creates of ``R`` with unique values ``prefix-n``; item ``clash`` repeats the first value."""

    def values(n: int) -> list[dict[str, Any]]:
        filled = world.required_values("R")
        filled[world.key("R.u")] = f"{prefix}-{0 if n == clash else n}"
        return [{"attributeTypeKey": k, "value": v} for k, v in filled.items()]

    return [
        {
            "op": "create",
            "applicationKey": world.app("R"),
            "objectTypeKey": world.key("R"),
            "name": f"{prefix} {n}",
            "attributes": values(n),
        }
        for n in range(count)
    ]


def queue(world, batch: list[dict], *, policy="independent", change_set: str | None = None) -> str:
    with SessionLocal() as session:
        context: dict[str, Any] = {"workspaceKey": W1}
        if change_set:
            version = session.scalar(select(ChangeSet.version).where(ChangeSet.id == change_set))
            context = {"changeSetId": change_set, "expectedChangeSetVersion": version}
        request = BatchRequest.model_validate(
            {"policy": policy, "run": "background", "items": batch, **context}
        )
        job, _replayed = submit_background_batch(
            session, request, idempotency_key=None, retention_days=7
        )
        return job.id


def job(job_id: str) -> Job:
    with SessionLocal() as session:
        return session.scalar(select(Job).where(Job.id == job_id))


def outcomes(job_id: str) -> list[tuple[str, str]]:
    with SessionLocal() as session:
        rows = session.execute(
            select(JobItem.status, JobItem.outcome)
            .join(Job, Job.sequence_id == JobItem.job_id)
            .where(Job.id == job_id)
            .order_by(JobItem.item_index)
        ).all()
    return [(s, o.get("action") or o.get("reason") or o["error"]["code"]) for s, o in rows]


def live(world, prefix: str) -> int:
    with SessionLocal() as session:
        return session.scalar(
            select(func.count())
            .select_from(RdmObject)
            .where(
                RdmObject.workspace_key == W1,
                RdmObject.object_type_key == world.key("R"),
                RdmObject.name.like(f"{prefix} %"),
            )
        )


def test_a_job_in_a_change_set_follows_the_version_each_chunk_leaves(seeded):
    world = seeded
    with SessionLocal() as session:
        release = resolve_model_snapshot(session).release_db_id
        staged = create_change_set(session, W1, release, source="currentLive")
        change_set, before = staged.id, staged.version
    job_id = queue(world, items(world, 5), change_set=change_set)
    runner = worker()
    runner.run_once()
    assert job(job_id).change_set_version == before + 1
    runner.run_until_idle()
    finished = job(job_id)
    assert (finished.state, finished.result, finished.change_set_version) == (
        "completed",
        "applied",
        before + 3,
    )
    assert finished.counts == {
        "applied": 5,
        "rejected": 0,
        "unprocessed": 0,
        "created": 5,
        "updated": 0,
        "unchanged": 0,
        "deleted": 0,
    }
    assert finished.parameters == {
        "policy": "independent",
        "run": "background",
        "onExisting": "reject",
        "otherWorkspaceIds": "refuse",
    }
    with SessionLocal() as session:
        assert (
            session.scalar(select(ChangeSet.version).where(ChangeSet.id == change_set))
            == before + 3
        )
    assert live(world, "J") == 0


def test_an_atomic_job_runs_as_one_chunk_and_a_rejection_rolls_it_back(seeded):
    world = seeded
    applied = queue(world, items(world, 5, "A"), policy="atomic")
    assert worker().run_until_idle() == 1
    assert job(applied).result == "applied" and live(world, "A") == 5
    rejected = queue(world, items(world, 5, "B", clash=4), policy="atomic")
    worker().run_until_idle()
    assert job(rejected).result == "rejected"
    assert outcomes(rejected) == [("unprocessed", "BATCH_ROLLED_BACK")] * 4 + [
        ("rejected", "DUPLICATE_ATTRIBUTE_VALUE")
    ]
    assert live(world, "B") == 0


def test_a_stopping_worker_releases_its_leases_and_a_finished_job_leaves_no_inputs(seeded):
    world = seeded
    job_id = queue(world, items(world, 4))
    first = worker("worker-a")
    first.run_once()
    first.stop()
    assert job(job_id).lease_owner is None
    # Another process resumes at once, without waiting for the lease to expire.
    assert worker("worker-b").run_until_idle() == 1
    finished = job(job_id)
    assert (finished.state, finished.lease_owner, finished.lease_expires_at) == (
        "completed",
        None,
        None,
    )
    with SessionLocal() as session:
        assert (
            session.scalar(
                select(func.count())
                .select_from(JobInput)
                .where(JobInput.job_id == finished.sequence_id)
            )
            == 0
        )


def test_an_unexpected_error_fails_the_job_with_a_correlation_id(seeded, monkeypatch, caplog):
    """A defect in a chunk (made here by the batch's code raising) fails the job: its committed
    chunks stay, the rest are unprocessed, and the error names a correlation ID the log holds with
    the cause, never the cause itself."""
    world = seeded
    job_id = queue(world, [{**item, "ref": f"row-{n}"} for n, item in enumerate(items(world, 4))])
    original, calls = worker_module.run_items, []

    def broken(*args, **kwargs):
        calls.append(1)
        if len(calls) == 2:
            raise RuntimeError("simulated defect")
        return original(*args, **kwargs)

    monkeypatch.setattr(worker_module, "run_items", broken)
    worker().run_until_idle()
    failed = job(job_id)
    assert (failed.state, failed.result, failed.error["code"]) == (
        "failed",
        "partial",
        "JOB_FAILED",
    )
    correlation = failed.error["details"]["correlationId"]
    assert "simulated" not in failed.error["message"]
    assert correlation in caplog.text and "simulated defect" in caplog.text
    assert outcomes(job_id) == [("applied", "created")] * 2 + [("unprocessed", "JOB_FAILED")] * 2
    with SessionLocal() as session:
        refs = session.scalars(
            select(JobItem.ref)
            .join(Job, Job.sequence_id == JobItem.job_id)
            .where(Job.id == job_id)
            .order_by(JobItem.item_index)
        ).all()
    assert refs == ["row-0", "row-1", "row-2", "row-3"]
    assert live(world, "J") == 2


@pytest.mark.serial
def test_without_its_database_the_worker_waits_between_retries_and_logs_no_traceback(
    monkeypatch, caplog
):
    """A database down for hours once made the worker spin (a failed sweep left its next sweep in
    the past, so the wait was negative) and log a traceback per pass: 28 GB of log overnight. An
    unreachable database is an expected failure: one plain line, then a reminder an interval, no
    traceback (C12)."""
    attempts = 0

    def unreachable() -> Any:
        nonlocal attempts
        attempts += 1
        raise OperationalError("SELECT 1", {}, OSError("connection refused"))

    monkeypatch.setattr(worker_module, "RETRY_SECONDS", 0.05)
    monkeypatch.setattr(outage_module, "REMINDER_SECONDS", 0.2)
    down = JobWorker(unreachable, WorkerSettings(CHUNK, 120, 7), owner="worker-down")
    with caplog.at_level("INFO", logger=worker_module.logger.name):
        down.start()
        time.sleep(0.5)
        down.stop(timeout=1)
    retries = [r for r in caplog.records if "reach the database" in r.getMessage()]
    assert 5 <= attempts <= 15
    assert sum(r.exc_info is not None for r in retries) == 0
    assert [r.levelname for r in retries][:1] == ["ERROR"]
    assert 1 <= len(retries) <= 4
