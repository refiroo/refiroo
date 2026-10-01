"""Base 0.9 B2: background batches run by the job worker (INTEGRATION_API P6, D27–D30).

A background batch is queued with its items as inputs and answers 202; the worker applies it in
chunks, each committing its data, outcomes and checkpoint together. The tests drive the worker one
chunk at a time (the application's own worker thread is off, except in the lifespan test) and stop
it where a crash, a cancel request, a release activation, a lost change set claim or another worker
would meet it: no item is repeated or skipped, and the items it did not reach are ``unprocessed``
with the stop's reason. Everything runs on a generated model and on a copy with every key renamed.

Cancellation is designed for PostgreSQL (D28): on the SQLite test database a cancel request cannot
commit while a chunk holds the writer lock, so the atomic job's cancel between items is exercised
from within the chunk. The concurrent case waits for the PostgreSQL migration (TODO).
"""

import json
import time
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from fastapi.testclient import TestClient
from model_support import renamed_model
from sqlalchemy import func, select, update
from test_batches import (
    CODE,
    ENTRY,
    FOLDER,
    WORKSPACE,
    Keys,
    _ok,
    _refused,
    attrs,
    batch_model,
    by_code,
    change_set,
    change_set_version,
    create_item,
    history,
    outcomes,
    single_create,
    upsert_item,
)

from app.config import reload_settings
from app.db import SessionLocal, get_engine
from app.engine.indexes import matrix_states
from app.engine.jobs import batches as batch_engine
from app.engine.jobs.worker import JobWorker, WorkerSettings
from app.engine.model.bootstrap import ensure_bootstrap_release
from app.engine.model.registry import model_registry
from app.main import create_app
from app.models.database import (
    AuditEvent,
    ChangeSet,
    IdempotencyKey,
    Job,
    JobInput,
    JobItem,
    ModelRelease,
    ModelRuntimeState,
    RdmObject,
    Workspace,
)
from app.models.schema import EngineModel

CHUNK = 2
LEASE = 120


def _app(source: dict, tmp_path, monkeypatch, migrated_database, *, run_worker=False, **env: str):
    model_path = tmp_path / "background-model.json"
    model_path.write_text(json.dumps(source))
    monkeypatch.setenv("DATABASE_URL", migrated_database("background.db"))
    monkeypatch.setenv("RDM_MODEL_PATH", str(model_path))
    monkeypatch.setenv("JOB_CHUNK_ITEMS", str(CHUNK))
    monkeypatch.setenv("MODEL_ADMIN_MUTATIONS_ENABLED", "true")
    for name, value in env.items():
        monkeypatch.setenv(name, value)
    reload_settings()
    model_registry.clear()
    application = create_app()
    application.state.run_job_worker = run_worker
    return application


def _cleanup(monkeypatch) -> None:
    get_engine().dispose()
    monkeypatch.undo()
    reload_settings()
    model_registry.clear()


@pytest.fixture(params=["generated", "renamed"])
def background(request, tmp_path, monkeypatch, migrated_database) -> Iterator[tuple[TestClient, Keys]]:
    source = batch_model()
    names: dict[str, str] = {}
    if request.param == "renamed":
        source, names = renamed_model(source)
    with TestClient(_app(source, tmp_path, monkeypatch, migrated_database)) as client:
        yield client, lambda key: names.get(key, key)
        with SessionLocal() as session:
            assert matrix_states.verify(session) == []
    _cleanup(monkeypatch)


@pytest.fixture
def configured(tmp_path, monkeypatch, migrated_database):
    """An application factory with environment settings, on the generated model."""

    def serve(**env: str):
        return _app(batch_model(), tmp_path, monkeypatch, migrated_database, **env)

    yield serve
    _cleanup(monkeypatch)


def worker(owner: str = "worker-a") -> JobWorker:
    return JobWorker(SessionLocal, WorkerSettings(CHUNK, LEASE, 7), owner=owner)


def queue(client, items: list[dict], *, policy="independent", headers=None, **context) -> Any:
    return client.post(
        "/api/v1/batches",
        json={"policy": policy, "run": "background", "items": items, **(context or {"workspaceKey": WORKSPACE})},
        headers=headers or {},
    )


def queued(client, items: list[dict], **options) -> dict[str, Any]:
    return _ok(queue(client, items, **options), 202)


def job(client, job_id: str) -> dict[str, Any]:
    return _ok(client.get(f"/api/v1/jobs/{job_id}"))


def job_outcomes(client, job_id: str) -> dict[str, Any]:
    return _ok(client.get(f"/api/v1/jobs/{job_id}/items"))


def folders(k: Keys, count: int, prefix: str = "F") -> list[dict]:
    return [create_item(k, FOLDER, f"{prefix}{n}", f"{prefix}{n}") for n in range(count)]


def codes(client, k: Keys, count: int, prefix: str = "F", **context) -> list[int]:
    """How many records hold each code ``prefix0`` … in the context."""
    result = []
    for n in range(count):
        response = client.get(
            f"/api/v1/objects/{k(FOLDER)}",
            params={"workspaceKey": WORKSPACE, f"filter.{k(CODE)}.eq": f"{prefix}{n}", **context},
        )
        result.append(len(_ok(response)["items"]))
    return result


def expire_lease(job_id: str) -> None:
    with SessionLocal() as session:
        session.execute(
            update(Job).where(Job.id == job_id).values(lease_expires_at=datetime.now(UTC) - timedelta(seconds=1))
        )
        session.commit()


def created_audits(job_id: str) -> int:
    with SessionLocal() as session:
        return session.scalar(
            select(func.count()).select_from(AuditEvent).where(AuditEvent.cause_id == job_id, AuditEvent.action == "created")
        )


def inputs_left(job_id: str) -> int:
    with SessionLocal() as session:
        return session.scalar(
            select(func.count()).select_from(JobInput).join(Job, Job.sequence_id == JobInput.job_id).where(Job.id == job_id)
        )


def _crash_at(monkeypatch, index: int) -> None:
    """The process stops while item ``index`` is applied: nothing after it runs or commits."""
    original = batch_engine._Batch.apply

    def apply(self, item_index, item):
        if item_index == index:
            raise _Crash
        return original(self, item_index, item)

    monkeypatch.setattr(batch_engine._Batch, "apply", apply)


class _Crash(BaseException):
    pass


# --- running in chunks ---------------------------------------------------------------------------


def test_a_background_batch_is_queued_and_applied_in_chunks(background):
    client, k = background
    items = folders(k, 5)
    items[3] = create_item(k, FOLDER, "Dup", "F0")  # rejected: F0 is taken by item 0
    items[1]["ref"] = "row-1"
    accepted = queued(client, items)
    assert (accepted["state"], accepted["progress"], accepted["startedAt"]) == ("queued", {"total": 5, "processed": 0}, None)
    assert accepted["parameters"] == {"run": "background", "onExisting": "reject"}
    assert (accepted["leaseOwner"], accepted["cancelRequestedAt"]) == (None, None)
    job_id = accepted["id"]
    assert inputs_left(job_id) == 5

    runner = worker()
    assert runner.run_once()
    first = job(client, job_id)
    assert (first["state"], first["progress"]["processed"], first["leaseOwner"]) == ("running", 2, "worker-a")
    assert first["leaseExpiresAt"] is not None and first["startedAt"] is not None
    assert [item["index"] for item in job_outcomes(client, job_id)["items"]] == [0, 1]
    assert runner.run_until_idle() == 2
    assert not runner.run_once()

    finished = job(client, job_id)
    assert (finished["state"], finished["result"], finished["stage"]) == ("completed", "partial", None)
    assert finished["counts"] == {"applied": 4, "rejected": 1, "unprocessed": 0, "created": 4, "updated": 0, "unchanged": 0, "deleted": 0}
    assert (finished["leaseOwner"], finished["leaseExpiresAt"]) == (None, None)
    page = job_outcomes(client, job_id)
    assert outcomes(page) == [("applied", "created")] * 3 + [("rejected", "duplicate_attribute_value"), ("applied", "created")]
    assert page["items"][1]["ref"] == "row-1"
    assert page["items"][3]["error"]["details"]["pointer"] == "/items/3/attributes"
    assert inputs_left(job_id) == 0
    assert created_audits(job_id) == 4
    record = page["items"][0]
    assert history(client, k, FOLDER, record["id"])[0]["cause"] == {"kind": "job", "id": job_id}


def test_items_in_a_later_chunk_see_earlier_chunks_and_keep_their_semantics(background):
    """Item fields the request left out stay left out: an upsert without a parent keeps the
    record where it is, and one moved to no parent is moved."""
    client, k = background
    folder = _ok(single_create(client, k, FOLDER, "Top", "TOP"), 201)
    items = [
        create_item(k, FOLDER, "Parent", "P1"),
        create_item(k, FOLDER, "Other", "P2"),
        create_item(k, ENTRY, "Child", "C1", by_code(k, FOLDER, "P1")),
        upsert_item(k, FOLDER, "Top renamed", "TOP"),
    ]
    items[3]["expectedVersion"] = folder["version"]
    job_id = queued(client, items)["id"]
    worker().run_until_idle()
    assert outcomes(job_outcomes(client, job_id)) == [("applied", "created")] * 3 + [("applied", "updated")]
    top = _ok(client.get(f"/api/v1/objects/{k(FOLDER)}/{folder['id']}"))
    assert (top["name"], top["parentObjectId"]) == ("Top renamed", None)


def test_a_background_batch_in_a_change_set_holds_its_claim_between_chunks(background):
    client, k = background
    staged = change_set(client)
    context = {"changeSetId": staged["id"], "expectedChangeSetVersion": staged["version"]}
    _refused(
        queue(client, folders(k, 1), changeSetId=staged["id"], expectedChangeSetVersion=staged["version"] + 1),
        "change_set_version_conflict",
        409,
    )
    accepted = queued(client, folders(k, 5), **context)
    assert (accepted["changeSetId"], accepted["changeSetVersion"]) == (staged["id"], staged["version"])
    runner = worker()
    runner.run_once()
    # One version per chunk that changed something; the job holds the version it left.
    assert job(client, accepted["id"])["changeSetVersion"] == staged["version"] + 1
    runner.run_until_idle()
    finished = job(client, accepted["id"])
    assert (finished["state"], finished["result"], finished["changeSetVersion"]) == ("completed", "applied", staged["version"] + 3)
    assert change_set_version(client, staged["id"]) == staged["version"] + 3
    assert codes(client, k, 5, changeSetId=staged["id"]) == [1] * 5
    assert codes(client, k, 5) == [0] * 5


def test_an_atomic_background_job_is_one_chunk(background):
    client, k = background
    items = folders(k, 5)
    job_id = queued(client, items, policy="atomic")["id"]
    assert worker().run_until_idle() == 1
    assert job(client, job_id)["result"] == "applied"
    # A rejection rolls the whole job back.
    items = folders(k, 5, "G")
    items[4] = create_item(k, FOLDER, "Dup", "G0")
    job_id = queued(client, items, policy="atomic")["id"]
    worker().run_until_idle()
    assert outcomes(job_outcomes(client, job_id)) == [("unprocessed", "batch_rolled_back")] * 4 + [("rejected", "duplicate_attribute_value")]
    assert codes(client, k, 4, "G") == [0] * 4
    assert job(client, job_id)["result"] == "rejected"


# --- crash and resumption ------------------------------------------------------------------------


@pytest.mark.parametrize("where", ["between chunks", "inside a chunk"])
def test_a_job_resumes_after_a_crash_without_repeating_or_skipping_an_item(background, monkeypatch, where):
    client, k = background
    job_id = queued(client, folders(k, 7))["id"]
    first = worker("worker-a")
    first.run_once()  # items 0 and 1 committed
    if where == "inside a chunk":
        with monkeypatch.context() as patch:
            _crash_at(patch, 3)
            with pytest.raises(_Crash):
                first.run_once()  # items 2 and 3: item 2 applied in the open transaction, then lost
    assert job(client, job_id)["progress"]["processed"] == 2
    # A restarted process has another owner: it waits for the lease to expire.
    second = worker("worker-b")
    assert not second.run_once()
    expire_lease(job_id)
    second.run_until_idle()
    finished = job(client, job_id)
    assert (finished["state"], finished["result"], finished["counts"]["created"]) == ("completed", "applied", 7)
    assert [item["index"] for item in job_outcomes(client, job_id)["items"]] == list(range(7))
    assert codes(client, k, 7) == [1] * 7
    assert created_audits(job_id) == 7


def test_a_worker_that_lost_its_lease_commits_nothing(background, monkeypatch):
    """Another worker took the job over while this one applied a chunk: the chunk rolls back."""
    client, k = background
    job_id = queued(client, folders(k, 4))["id"]
    original = batch_engine._Batch.apply

    def taken_over(self, index, item):
        result = original(self, index, item)
        if index == 1:
            # As if the lease had expired and worker-b had claimed the job meanwhile.
            self.session.execute(update(Job).where(Job.id == job_id).values(lease_owner="worker-b"))
        return result

    with monkeypatch.context() as patch:
        patch.setattr(batch_engine._Batch, "apply", taken_over)
        worker("worker-a").run_once()
    assert job(client, job_id)["progress"]["processed"] == 0
    assert codes(client, k, 2) == [0, 0]
    assert job(client, job_id)["leaseOwner"] == "worker-a"
    expire_lease(job_id)
    worker("worker-b").run_until_idle()
    assert job(client, job_id)["result"] == "applied"
    assert codes(client, k, 4) == [1] * 4


def test_a_stopping_worker_releases_its_leases(background):
    client, k = background
    job_id = queued(client, folders(k, 4))["id"]
    first = worker("worker-a")
    first.run_once()
    first.stop()
    assert job(client, job_id)["leaseOwner"] is None
    assert worker("worker-b").run_until_idle() == 1
    assert job(client, job_id)["result"] == "applied"


# --- cancellation (D28) --------------------------------------------------------------------------


def test_cancelling_a_queued_job_runs_none_of_its_items(background):
    client, k = background
    job_id = queued(client, folders(k, 3))["id"]
    requested = _ok(client.post(f"/api/v1/jobs/{job_id}/cancel"), 202)
    assert requested["state"] == "queued" and requested["cancelRequestedAt"] is not None
    # Asking again changes nothing.
    again = _ok(client.post(f"/api/v1/jobs/{job_id}/cancel"), 202)
    assert again["cancelRequestedAt"] == requested["cancelRequestedAt"]
    worker().run_until_idle()
    cancelled = job(client, job_id)
    assert (cancelled["state"], cancelled["result"], cancelled["error"]) == ("cancelled", "rejected", None)
    assert cancelled["counts"]["unprocessed"] == 3 and cancelled["progress"]["processed"] == 3
    assert outcomes(job_outcomes(client, job_id)) == [("unprocessed", "job_cancelled")] * 3
    assert codes(client, k, 3) == [0] * 3
    assert inputs_left(job_id) == 0


def test_cancelling_between_chunks_keeps_the_applied_chunks(background):
    client, k = background
    items = folders(k, 5)
    items[3]["ref"] = "row-3"
    job_id = queued(client, items)["id"]
    runner = worker()
    runner.run_once()
    _ok(client.post(f"/api/v1/jobs/{job_id}/cancel"), 202)
    runner.run_until_idle()
    cancelled = job(client, job_id)
    assert (cancelled["state"], cancelled["result"]) == ("cancelled", "partial")
    page = job_outcomes(client, job_id)
    assert outcomes(page) == [("applied", "created")] * 2 + [("unprocessed", "job_cancelled")] * 3
    assert page["items"][3]["ref"] == "row-3"
    assert codes(client, k, 5) == [1, 1, 0, 0, 0]
    # A finished job cannot be cancelled.
    error = _refused(client.post(f"/api/v1/jobs/{job_id}/cancel"), "job_finished", 409)
    assert error["details"] == {"jobId": job_id, "state": "cancelled"}
    finished = queued(client, folders(k, 1, "X"))["id"]
    runner.run_until_idle()
    _refused(client.post(f"/api/v1/jobs/{finished}/cancel"), "job_finished", 409)
    _refused(client.post("/api/v1/jobs/00000000-0000-4000-8000-000000000000/cancel"), "job_not_found", 404)


def test_cancelling_an_atomic_job_rolls_it_back_completely(background, monkeypatch):
    client, k = background
    job_id = queued(client, folders(k, 5), policy="atomic")["id"]
    original = batch_engine._Batch.apply

    def cancelled_meanwhile(self, index, item):
        result = original(self, index, item)
        if index == 2:
            # The cancel request, as the chunk's next read sees it on PostgreSQL (D28).
            self.session.execute(update(Job).where(Job.id == job_id).values(cancel_requested_at=datetime.now(UTC)))
        return result

    monkeypatch.setattr(batch_engine._Batch, "apply", cancelled_meanwhile)
    worker().run_until_idle()
    cancelled = job(client, job_id)
    assert (cancelled["state"], cancelled["result"]) == ("cancelled", "rejected")
    assert outcomes(job_outcomes(client, job_id)) == [("unprocessed", "job_cancelled")] * 5
    assert codes(client, k, 5) == [0] * 5
    assert created_audits(job_id) == 0


# --- stops: release, claim, failure --------------------------------------------------------------


def _activate_another_release(client) -> ModelRelease:
    source = client.get("/api/v1/model").json()
    source["release"]["version"] = "9.9.9-b2"
    with SessionLocal() as session:
        release = ensure_bootstrap_release(session, EngineModel.model_validate(source))
        session.commit()
        state = session.get(ModelRuntimeState, 1)
        active = session.get(ModelRelease, state.active_model_release_id)
        expected = {"expectedRuntimeVersion": state.version, "expectedActiveReleaseId": active.public_id}
    _ok(client.post(f"/api/v1/model-releases/{release.public_id}/activation", json=expected))
    return release


def test_a_release_activated_mid_job_fails_it_at_the_next_chunk(background):
    client, k = background
    job_id = queued(client, folders(k, 5))["id"]
    runner = worker()
    runner.run_once()
    _activate_another_release(client)
    runner.run_until_idle()
    failed = job(client, job_id)
    assert (failed["state"], failed["result"], failed["error"]["code"]) == ("failed", "partial", "model_release_changed")
    assert outcomes(job_outcomes(client, job_id)) == [("applied", "created")] * 2 + [("unprocessed", "model_release_changed")] * 3
    assert codes(client, k, 5) == [1, 1, 0, 0, 0]


def test_a_release_activated_during_a_chunk_refuses_that_chunk(background, monkeypatch):
    client, k = background
    job_id = queued(client, folders(k, 3))["id"]
    original = batch_engine._Batch.apply

    def activated_meanwhile(self, index, item):
        # As if another release were active when the chunk commits (0.8 W5's check).
        self.session.info["resolved_active_model_release_db_id"] = -1
        return original(self, index, item)

    monkeypatch.setattr(batch_engine._Batch, "apply", activated_meanwhile)
    worker().run_until_idle()
    failed = job(client, job_id)
    assert (failed["state"], failed["error"]["code"]) == ("failed", "model_release_changed")
    assert outcomes(job_outcomes(client, job_id)) == [("unprocessed", "model_release_changed")] * 3
    assert codes(client, k, 3) == [0] * 3


def test_a_change_set_moved_to_another_release_fails_the_job(background):
    client, k = background
    staged = change_set(client)
    job_id = queued(client, folders(k, 3), changeSetId=staged["id"], expectedChangeSetVersion=staged["version"])["id"]
    runner = worker()
    runner.run_once()
    release = _activate_another_release(client)
    with SessionLocal() as session:
        session.execute(update(ChangeSet).where(ChangeSet.id == staged["id"]).values(model_release_id=release.id))
        session.commit()
    runner.run_until_idle()
    failed = job(client, job_id)
    assert (failed["state"], failed["error"]["code"]) == ("failed", "model_release_changed")
    assert outcomes(job_outcomes(client, job_id))[2:] == [("unprocessed", "model_release_changed")]


def test_a_lost_change_set_claim_fails_the_job(background):
    client, k = background
    staged = change_set(client)
    job_id = queued(client, folders(k, 5), changeSetId=staged["id"], expectedChangeSetVersion=staged["version"])["id"]
    runner = worker()
    runner.run_once()
    # Another writer changes the change set between chunks.
    _ok(
        single_create(
            client, k, FOLDER, "Elsewhere", "ELSEWHERE",
            changeSetId=staged["id"], expectedChangeSetVersion=change_set_version(client, staged["id"]),
        ),
        201,
    )
    runner.run_until_idle()
    failed = job(client, job_id)
    assert (failed["state"], failed["result"], failed["error"]["code"]) == ("failed", "partial", "change_set_version_conflict")
    assert outcomes(job_outcomes(client, job_id)) == [("applied", "created")] * 2 + [("unprocessed", "job_failed")] * 3
    assert failed["changeSetVersion"] == staged["version"] + 1


def test_an_unexpected_error_fails_the_job_with_a_correlation_id(background, monkeypatch, caplog):
    client, k = background
    job_id = queued(client, folders(k, 4))["id"]
    original = batch_engine._Batch.apply

    def broken(self, index, item):
        if index == 3:
            raise RuntimeError("simulated defect")
        return original(self, index, item)

    monkeypatch.setattr(batch_engine._Batch, "apply", broken)
    worker().run_until_idle()
    failed = job(client, job_id)
    assert (failed["state"], failed["result"], failed["error"]["code"]) == ("failed", "partial", "job_failed")
    correlation_id = failed["error"]["details"]["correlationId"]
    assert "Traceback" not in failed["error"]["message"] and "simulated" not in failed["error"]["message"]
    assert correlation_id in caplog.text and "simulated defect" in caplog.text
    assert outcomes(job_outcomes(client, job_id)) == [("applied", "created")] * 2 + [("unprocessed", "job_failed")] * 2
    assert codes(client, k, 4) == [1, 1, 0, 0]


def test_a_workspace_retired_mid_job_fails_it(background):
    client, k = background
    _ok(client.post("/api/v1/workspaces", json={"key": "brief", "label": "Brief"}), 201)
    job_id = queued(client, folders(k, 3), workspaceKey="brief")["id"]
    runner = worker()
    runner.run_once()
    with SessionLocal() as session:
        session.execute(update(Workspace).where(Workspace.key == "brief").values(status="retired"))
        session.commit()
    runner.run_until_idle()
    failed = job(client, job_id)
    assert (failed["state"], failed["error"]["code"]) == ("failed", "workspace_retired")
    assert outcomes(job_outcomes(client, job_id))[2:] == [("unprocessed", "job_failed")]


# --- idempotency, retention, capability ------------------------------------------------------------


def test_an_idempotency_key_answers_with_the_background_job(background):
    client, k = background
    items = folders(k, 3)
    key = {"Idempotency-Key": "nightly-load"}
    first = queue(client, items, headers=key)
    assert first.status_code == 202 and "Idempotent-Replayed" not in first.headers
    job_id = first.json()["id"]
    # While the job is queued or running, a retry is told to wait.
    running = queue(client, items, headers=key)
    assert _refused(running, "idempotency_in_progress", 409)["details"]["jobId"] == job_id
    _refused(queue(client, folders(k, 2), headers=key), "idempotency_key_reused", 422)
    worker().run_until_idle()
    replay = queue(client, items, headers=key)
    assert replay.status_code == 202 and replay.headers["Idempotent-Replayed"] == "true"
    assert replay.json()["id"] == job_id and replay.json()["state"] == "completed"
    # The key lives as long as the finished job.
    with SessionLocal() as session:
        stored = session.scalar(select(IdempotencyKey))
        finished = session.scalar(select(Job).where(Job.id == job_id))
        assert stored.expires_at == finished.expires_at


def test_retention_expires_finished_jobs_and_keeps_their_summary(background):
    client, k = background
    done = queued(client, folders(k, 3), headers={"Idempotency-Key": "kept-a-week"})["id"]
    runner = worker()
    runner.run_until_idle()
    waiting = queued(client, folders(k, 1, "W"))["id"]
    assert runner.sweep() == 0
    summary = job(client, done)
    assert runner.sweep(datetime.now(UTC) + timedelta(days=8)) == 1
    expired = job(client, done)
    assert expired["state"] == "expired"
    assert {key: expired[key] for key in ("counts", "result", "progress", "finishedAt")} == {
        key: summary[key] for key in ("counts", "result", "progress", "finishedAt")
    }
    assert job_outcomes(client, done)["items"] == []
    with SessionLocal() as session:
        assert session.scalar(select(func.count()).select_from(IdempotencyKey)) == 0
        assert session.scalar(select(func.count()).select_from(JobItem).join(Job).where(Job.id == done)) == 0
    # A job not yet finished never expires.
    assert job(client, waiting)["state"] == "queued"
    # The key now counts as new.
    again = queued(client, folders(k, 3), headers={"Idempotency-Key": "kept-a-week"})
    assert again["id"] != done


def test_with_jobs_disabled_there_is_no_worker_and_no_cancel_route(configured):
    application = configured(INTEGRATION_JOBS_ENABLED="false")
    assert application.state.job_worker is None
    with TestClient(application) as client:
        paths = client.get("/openapi.json").json()["paths"]
        assert "/api/v1/jobs/{job_id}/cancel" not in paths and "/api/v1/batches" not in paths
        assert client.post("/api/v1/jobs/x/cancel").status_code in {404, 405}
        assert _ok(client.get("/api/v1/jobs"))["items"] == []


def test_the_application_runs_background_jobs_on_its_worker_thread(tmp_path, monkeypatch, migrated_database):
    """Through the lifespan: a queued job wakes the worker, which completes it."""
    application = _app(batch_model(), tmp_path, monkeypatch, migrated_database, run_worker=True)
    try:
        with TestClient(application) as client:
            k: Keys = lambda key: key
            job_id = queued(client, folders(k, 5))["id"]
            deadline = time.monotonic() + 15
            while job(client, job_id)["state"] != "completed":
                assert time.monotonic() < deadline, job(client, job_id)
                time.sleep(0.05)
            assert codes(client, k, 5) == [1] * 5
            assert job(client, job_id)["result"] == "applied"
        # A restarted application finds nothing left to do.
        with SessionLocal() as session:
            assert session.scalar(select(func.count()).select_from(JobInput)) == 0
            assert session.scalar(select(func.count()).select_from(RdmObject)) >= 5
    finally:
        _cleanup(monkeypatch)


def test_background_attributes_keep_their_declared_types(background):
    client, k = background
    item = create_item(k, FOLDER, "Typed", "TYPED")
    item["attributes"] += attrs(k, par_count=3)
    job_id = queued(client, [item])["id"]
    worker().run_until_idle()
    [outcome] = job_outcomes(client, job_id)["items"]
    record = _ok(client.get(f"/api/v1/objects/{k(FOLDER)}/{outcome['id']}"))
    values = {attribute["attributeTypeKey"]: attribute["value"] for attribute in record["attributes"]}
    assert values[k("par-count")] == 3

