"""J24 — Run a large background job and recover (USER_JOURNEYS.md).

The journey application runs no worker thread; a test runs the engine's own job worker, chunk by
chunk (``run_once``) or on its thread, with five items a chunk. A "restarted process" is a worker with
another owner, which takes the job over once the first one's lease has expired.
"""

import time
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta

import pytest
import seeds
from scenario import W1, W2, ok, refused
from sqlalchemy import text

from app.common import outage as outage_module
from app.db import SessionLocal
from app.engine.jobs import worker as worker_module
from app.engine.jobs.worker import JobWorker, WorkerSettings

CHUNK = 5


def _worker(owner, lease=120):
    return JobWorker(SessionLocal, WorkerSettings(CHUNK, lease, 7), owner=owner)


def _items(world, count, prefix="J"):
    return [
        {
            "op": "create",
            "applicationKey": world.app("R"),
            "objectTypeKey": world.key("R"),
            "name": f"{prefix} {n:03d}",
            "attributes": [
                {"attributeTypeKey": k, "value": v}
                for k, v in {
                    **world.required_values("R"),
                    world.key("R.u"): f"{prefix}-{n:03d}",
                }.items()
            ],
        }
        for n in range(count)
    ]


def _submit(world, items, *, workspace=W1, policy="independent", **body):
    context = {"workspaceKey": workspace} if "changeSetId" not in body else {}
    request = {**context, "policy": policy, "run": "background", "items": items, **body}
    return ok(world.api.post("/batches", request), 202)


def _job(world, job_id):
    return ok(world.api.get(f"/jobs/{job_id}"))


def _outcomes(world, job_id, **params):
    items, cursor = [], None
    while True:
        page = ok(world.api.get(f"/jobs/{job_id}/items", pageSize=100, cursor=cursor, **params))
        items += page["items"]
        cursor = page.get("nextCursor")
        if not cursor:
            return [(i["status"], i.get("action") or i.get("reason")) for i in items]


def _named(world, prefix):
    page = ok(world.api.get(f"/objects/{world.key('R')}", search=f"{prefix} ", pageSize=500))
    return sorted(world.names(page))


@pytest.mark.journey("J24")
@pytest.mark.structures("R", "R.u")
def test_submit_follow_page_outcomes_and_survive_a_restart(world):
    """When 30 items are submitted to run in the background, five a chunk; the job is followed and
    its applied outcomes paged while it runs; the process stops after two chunks and another takes
    over. Then the job is queued at once; progress grows by chunks and outcomes page in as they
    commit; after the restart the job resumes at its first item without an outcome and completes;
    every item is applied exactly once, and the finished job is listed among completed batches."""
    job = _submit(world, _items(world, 30))
    assert job["state"] == "queued" and job["progress"] == {"total": 30, "processed": 0}

    first = _worker("process-1", lease=1)
    seen = []
    for _chunk in range(2):
        assert first.run_once()
        running = _job(world, job["id"])
        seen.append(running["progress"]["processed"])
        assert running["state"] == "running"
        assert (
            len(_outcomes(world, job["id"], status="applied")) == running["progress"]["processed"]
        )
    assert seen == [5, 10]

    # The first process is gone without releasing its lease; the next waits for it to expire.
    second = _worker("process-2")
    assert not second.run_once()
    time.sleep(1.1)
    assert second.run_until_idle() == 4
    done = _job(world, job["id"])
    assert (done["state"], done["result"], done["progress"]) == (
        "completed",
        "applied",
        {"total": 30, "processed": 30},
    )
    assert _outcomes(world, job["id"]) == [("applied", "created")] * 30
    assert _named(world, "J") == [f"J {n:03d}" for n in range(30)]
    listed = ok(world.api.get("/jobs", kind="batch", state="completed"))["items"]
    assert job["id"] in {item["id"] for item in listed}


@pytest.mark.journey("J24.1")
@pytest.mark.structures("R", "R.u")
def test_an_import_beside_stewards(world):
    """Given a background job running in W1. When a steward corrects a record there meanwhile, again
    and again. Then every write succeeds within a chunk's wait, nothing deadlocks, and both the
    steward's last value and every one of the job's items are saved."""
    record = world.made("R", "Steward's record")
    job = _submit(world, _items(world, 40))
    worker = _worker("importer")
    worker.start()
    try:
        version = record["version"]
        for n in range(8):
            started = time.monotonic()
            version = ok(world.update("R", record["id"], version, name=f"Corrected {n}"))["version"]
            assert time.monotonic() - started < 5
        deadline = time.monotonic() + 20
        while _job(world, job["id"])["state"] != "completed":
            assert time.monotonic() < deadline
            time.sleep(0.05)
    finally:
        worker.stop(timeout=10)
    assert world.record("R", record["id"])["name"] == "Corrected 7"
    assert _outcomes(world, job["id"]) == [("applied", "created")] * 40


@pytest.mark.journey("J24.2")
@pytest.mark.structures("R", "R.u")
def test_cancel_a_queued_a_running_and_an_atomic_job(world):
    """When a queued job is cancelled; a running independent job between chunks; an atomic job while
    it runs; a job twice; a finished job; and an unknown one. Then the cancel is accepted at once;
    the queued job applies nothing; the independent one keeps its committed chunk and the rest are
    unprocessed; the atomic one applies nothing; a second cancel changes nothing; the finished and
    unknown jobs are refused."""
    worker = _worker("canceller")
    queued = _submit(world, _items(world, 10, "Q"))
    accepted = ok(world.api.post(f"/jobs/{queued['id']}/cancel"), 202)
    assert accepted["cancelRequestedAt"] is not None
    again = ok(world.api.post(f"/jobs/{queued['id']}/cancel"), 202)
    assert again["cancelRequestedAt"] == accepted["cancelRequestedAt"]
    worker.run_until_idle()
    assert _job(world, queued["id"])["state"] == "cancelled"
    assert _outcomes(world, queued["id"]) == [("unprocessed", "JOB_CANCELLED")] * 10

    running = _submit(world, _items(world, 15, "I"))
    assert worker.run_once()
    ok(world.api.post(f"/jobs/{running['id']}/cancel"), 202)
    worker.run_until_idle()
    assert _outcomes(world, running["id"]) == (
        [("applied", "created")] * 5 + [("unprocessed", "JOB_CANCELLED")] * 10
    )
    assert _named(world, "I") == [f"I {n:03d}" for n in range(5)]

    atomic = _submit(world, _items(world, 10, "T"), policy="atomic")
    with world.holding(W1) as held:
        chunk = held.start(worker.run_once)
        held.waiting(1)
        ok(world.api.post(f"/jobs/{atomic['id']}/cancel"), 202)
    chunk.result(timeout=20)
    worker.run_until_idle()
    assert _job(world, atomic["id"])["state"] == "cancelled"
    assert _named(world, "T") == []

    finished = refused(world.api.post(f"/jobs/{queued['id']}/cancel"), 409, "JOB_FINISHED")
    assert finished["details"]["state"] == "cancelled"
    refused(
        world.api.post("/jobs/7d1c6f0e-2a4b-4c8d-9e1f-3a5b7c9d1e2f/cancel"), 404, "JOB_NOT_FOUND"
    )


@pytest.mark.journey("J24.4")
@pytest.mark.structures("R", "R.u")
def test_the_model_the_change_set_or_the_workspace_changes_mid_job(world):
    """When, between a job's chunks, another release is activated; someone else writes to the job's
    change set; the job's workspace is retired. Then each job fails with that reason, its first
    chunk stays applied and the rest are unprocessed, and its result says it applied in part."""
    worker = _worker("stopped")

    def after_one_chunk(job, change):
        assert worker.run_once()
        change()
        worker.run_until_idle()
        failed = _job(world, job["id"])
        assert (failed["state"], failed["result"]) == ("failed", "partial")
        outcomes = _outcomes(world, job["id"])
        assert outcomes[:CHUNK] == [("applied", "created")] * CHUNK
        assert {status for status, _reason in outcomes[CHUNK:]} == {"unprocessed"}
        return failed["error"]["code"]

    live = _submit(world, _items(world, 10, "L"))
    model, _key = world.candidate("compatible")
    release = world.install(model)["id"]
    assert after_one_chunk(live, lambda: ok(world.activate(release))) == "MODEL_RELEASE_CHANGED"

    cs = world.change_set()
    staged = _submit(
        world, _items(world, 10, "C"), changeSetId=cs["id"], expectedChangeSetVersion=cs["version"]
    )
    other_write = lambda: world.made("R", "Someone else", change_set=world.current(cs))
    assert after_one_chunk(staged, other_write) == "CHANGE_SET_VERSION_CONFLICT"

    elsewhere = _submit(world, _items(world, 10, "W"), workspace=W2)
    workspace = ok(world.api.get(f"/workspaces/{W2}"))

    def retire():
        ok(
            world.api.patch(
                f"/workspaces/{W2}", {"expectedVersion": workspace["version"], "status": "retired"}
            )
        )

    assert after_one_chunk(elsewhere, retire) == "WORKSPACE_RETIRED"


@pytest.mark.journey("J24.5")
@pytest.mark.structures("R", "R.u")
def test_finished_jobs_expire_and_keep_their_summary(world):
    """Given a finished job past its retention. When the job, its outcomes and a batch with its old
    key are requested. Then the job reads as expired with its counts, result, progress and times;
    its outcomes are an empty page; the key counts as new and the batch runs."""
    items = _items(world, 3)
    headers = {"Idempotency-Key": "weekly-load"}
    body = {"workspaceKey": W1, "policy": "independent", "run": "background", "items": items}
    job = world.api.client.post("/api/v1/batches", json=body, headers=headers).json()
    worker = _worker("retention")
    worker.run_until_idle()
    finished = _job(world, job["id"])
    assert worker.sweep(datetime.now(UTC) + timedelta(days=8)) >= 1
    expired = _job(world, job["id"])
    assert expired["state"] == "expired"
    kept = ("counts", "result", "progress", "createdAt", "startedAt", "finishedAt")
    assert {k: expired[k] for k in kept} == {k: finished[k] for k in kept}
    assert ok(world.api.get(f"/jobs/{job['id']}/items"))["items"] == []
    again = world.api.client.post("/api/v1/batches", json=body, headers=headers)
    assert again.status_code == 202 and again.json()["id"] != job["id"]


@contextmanager
def _unreachable(database):
    """The test's database refuses connections, and those open are ended, until the block ends."""
    with seeds.admin() as server:
        server.execute(text(f'ALTER DATABASE "{database}" ALLOW_CONNECTIONS false'))
        server.execute(
            text("SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = :name"),
            {"name": database},
        )
    try:
        yield
    finally:
        with seeds.admin() as server:
            server.execute(text(f'ALTER DATABASE "{database}" ALLOW_CONNECTIONS true'))


@pytest.mark.journey("J24.6")
@pytest.mark.structures("R", "R.u")
def test_the_worker_waits_while_the_database_is_unreachable(world, monkeypatch, caplog):
    """Given a running job. When the database becomes unreachable, then returns. Then the worker
    retries, logging the cause once in a plain line without a traceback (C12) and no more than a
    line a reminder interval;
    it logs the recovery, and the job resumes and completes with every item applied once."""
    monkeypatch.setattr(worker_module, "RETRY_SECONDS", 0.05)
    # The sweep's failure is part of the outage until the sweep works again (R172-F27), so its retry
    # is short here, as the retry of the job loop is.
    monkeypatch.setattr(worker_module, "SWEEP_RETRY_SECONDS", 0.2)
    monkeypatch.setattr(outage_module, "REMINDER_SECONDS", 0.3)
    job = _submit(world, _items(world, 20))
    worker = _worker("survivor")
    assert worker.run_once()
    with caplog.at_level("INFO", logger=worker_module.logger.name):
        with _unreachable(world.database.database):
            worker.start()
            time.sleep(1.0)
        try:
            deadline = time.monotonic() + 20
            while _job(world, job["id"])["state"] != "completed":
                assert time.monotonic() < deadline
                time.sleep(0.05)
        finally:
            worker.stop(timeout=10)
    lines = [r for r in caplog.records if r.name == worker_module.logger.name]
    outage = [r for r in lines if "reach the database" in r.getMessage()]
    assert sum(r.exc_info is not None for r in outage) == 0
    assert 2 <= len(outage) <= 6
    assert any("reaches the database again" in r.getMessage() for r in lines)
    assert _outcomes(world, job["id"]) == [("applied", "created")] * 20
    assert _named(world, "J") == [f"J {n:03d}" for n in range(20)]
