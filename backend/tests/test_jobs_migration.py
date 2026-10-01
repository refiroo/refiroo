"""Base 0.9 B1 and B2 at startup: migrations ``20260930_01`` (jobs, job items, idempotency keys and
the audit cause) and ``20261001_01`` (job inputs, the worker's lease, cancellation), and the
settings a batch runs under.

An existing database upgrades from the preceding revision with its audit history intact (no
cause), serves batches after the upgrade and after a restart, and an interrupted run, which SQLite
leaves with some tables or columns behind, completes on the next start; a table of another shape is
refused with a recovery instruction, leaving the revision where it was.

The limits and the SQLite lock wait are settings refused at startup when invalid. A batch holds
SQLite's writer lock for seconds (D13), so another write waits for it up to the lock wait instead of
failing at the driver's 5 s default.
"""

import json
import sqlite3
import threading
import time
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

import pytest
from alembic import command
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import OperationalError
from test_batches import FOLDER, batch_model, create_item
from test_snapshot_value_migration import _config, _version

from app.config import Settings, reload_settings
from app.db import get_engine
from app.engine.model.registry import model_registry
from app.main import create_app

PRECEDING, HEAD = "20260928_01", "20261001_01"
B1 = "20260930_01"
TABLES = {"jobs", "job_items", "idempotency_keys"}


def k(key: str) -> str:
    return key


@contextmanager
def _serve(database: Path, monkeypatch: pytest.MonkeyPatch, **env: str) -> Iterator[TestClient]:
    model_path = database.with_suffix(".model.json")
    model_path.write_text(json.dumps(batch_model()))
    with monkeypatch.context() as patch:
        patch.setenv("DATABASE_URL", f"sqlite:///{database}")
        patch.setenv("RDM_MODEL_PATH", str(model_path))
        for name, value in env.items():
            patch.setenv(name, value)
        reload_settings()
        model_registry.clear()
        try:
            with TestClient(create_app()) as client:
                yield client
        finally:
            get_engine().dispose()
    reload_settings()
    model_registry.clear()


def _tables(database: Path) -> set[str]:
    engine = create_engine(f"sqlite:///{database}")
    try:
        return set(inspect(engine).get_table_names())
    finally:
        engine.dispose()


def _batch(client: TestClient, code: str) -> dict:
    response = client.post(
        "/api/v1/batches",
        json={
            "workspaceKey": "default",
            "policy": "atomic",
            "run": "inline",
            "items": [create_item(k, FOLDER, code, code)],
        },
        headers={"Idempotency-Key": code},
    )
    assert response.status_code == 200, response.text
    assert response.json()["job"]["result"] == "applied"
    return response.json()


def test_upgrade_from_the_preceding_revision_keeps_history_and_serves_batches(
    tmp_path, monkeypatch, _migrated_template
):
    database = tmp_path / "b1-upgrade.db"
    database.write_bytes(_migrated_template.read_bytes())
    command.downgrade(_config(database), PRECEDING)
    assert TABLES.isdisjoint(_tables(database))
    with _serve(database, monkeypatch) as client:
        # The application refuses nothing at the preceding revision: it migrates on start.
        assert client.get("/health").json() == {"status": "ok"}
    assert _version(database) == HEAD

    # History written before the upgrade (at the preceding revision) keeps no cause.
    command.downgrade(_config(database), PRECEDING)
    engine = create_engine(f"sqlite:///{database}")
    with engine.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO audit_events (event_id, aggregate_type, aggregate_id, action, version, "
                "changes, occurred_at) VALUES ('e-1', 'object', 'o-1', 'created', 1, '{}', "
                "'2026-09-30 10:00:00')"
            )
        )
    engine.dispose()
    for start in range(2):
        with _serve(database, monkeypatch) as client:
            assert client.get("/health").json() == {"status": "ok"}
            first = _batch(client, f"CODE-{start}")
            replay = client.post(
                "/api/v1/batches",
                json={
                    "workspaceKey": "default",
                    "policy": "atomic",
                    "run": "inline",
                    "items": [create_item(k, FOLDER, "CODE-0", "CODE-0")],
                },
                headers={"Idempotency-Key": "CODE-0"},
            )
            # After a restart the key still answers with the first job.
            assert replay.headers["Idempotent-Replayed"] == "true"
            assert client.get(f"/api/v1/jobs/{first['job']['id']}").status_code == 200
        assert _version(database) == HEAD
    engine = create_engine(f"sqlite:///{database}")
    with engine.connect() as connection:
        assert connection.execute(
            text("SELECT cause_kind, cause_id FROM audit_events WHERE event_id = 'e-1'")
        ).one() == (None, None)
    engine.dispose()


def test_an_interrupted_upgrade_completes_and_an_unknown_table_is_refused(
    tmp_path, monkeypatch, _migrated_template
):
    database = tmp_path / "b1-interrupted.db"
    database.write_bytes(_migrated_template.read_bytes())
    command.downgrade(_config(database), PRECEDING)
    # A stopped run added one cause column and created the jobs table, without the version bump.
    engine = create_engine(f"sqlite:///{database}")
    with engine.begin() as connection:
        connection.execute(text("ALTER TABLE audit_events ADD COLUMN cause_kind VARCHAR(20)"))
        connection.execute(
            text(
                "CREATE TABLE jobs (sequence_id INTEGER PRIMARY KEY, id VARCHAR, kind VARCHAR, "
                "workspace_key VARCHAR, change_set_id VARCHAR, model_release_id INTEGER, "
                "parameters JSON, state VARCHAR, stage VARCHAR, total INTEGER, processed INTEGER, "
                "counts JSON, result VARCHAR, error JSON, change_set_version INTEGER, "
                "created_at DATETIME, started_at DATETIME, finished_at DATETIME, expires_at DATETIME)"
            )
        )
    engine.dispose()
    with _serve(database, monkeypatch) as client:
        assert client.get("/health").json() == {"status": "ok"}
        _batch(client, "AFTER")
    assert _version(database) == HEAD
    assert TABLES <= _tables(database)

    # A table of another shape is refused with a recovery instruction.
    command.downgrade(_config(database), PRECEDING)
    engine = create_engine(f"sqlite:///{database}")
    with engine.begin() as connection:
        connection.execute(text("CREATE TABLE job_items (id INTEGER PRIMARY KEY, note VARCHAR)"))
    engine.dispose()
    with pytest.raises(Exception, match="unexpected schema"):
        command.upgrade(_config(database), "head")
    assert _version(database) == PRECEDING
    # Through the application the same refusal is the operator message, and /health is 503.
    with _serve(database, monkeypatch) as client:
        assert client.get("/health").status_code == 503
    assert _version(database) == PRECEDING


def test_batch_settings_have_defaults_and_refuse_invalid_values():
    defaults = Settings.from_env({})
    assert (
        defaults.integration_jobs_enabled,
        defaults.batch_max_items,
        defaults.batch_max_bytes,
        defaults.atomic_job_max_items,
        defaults.job_retention_days,
        defaults.sqlite_lock_wait_seconds,
        defaults.background_job_max_items,
        defaults.batch_background_max_bytes,
        defaults.job_chunk_items,
        defaults.job_lease_seconds,
    ) == (True, 1000, 5 * 1024 * 1024, 10_000, 7, 60, 1_000_000, 50 * 1024 * 1024, 500, 120)
    assert not Settings.from_env({"INTEGRATION_JOBS_ENABLED": "false"}).integration_jobs_enabled
    for name in (
        "BATCH_MAX_ITEMS",
        "BATCH_MAX_BYTES",
        "ATOMIC_JOB_MAX_ITEMS",
        "JOB_RETENTION_DAYS",
        "SQLITE_LOCK_WAIT_SECONDS",
        "BACKGROUND_JOB_MAX_ITEMS",
        "BATCH_BACKGROUND_MAX_BYTES",
        "JOB_CHUNK_ITEMS",
        "JOB_LEASE_SECONDS",
    ):
        for value in ("0", "-1", "many"):
            with pytest.raises(RuntimeError, match=f"{name} must be a positive integer"):
                Settings.from_env({name: value})


def _hold_writer_lock(database: Path, seconds: float) -> threading.Thread:
    """Another transaction holding SQLite's writer lock for ``seconds``, as a batch does."""
    held = threading.Event()

    def hold() -> None:
        connection = sqlite3.connect(database, isolation_level=None)
        connection.execute("BEGIN IMMEDIATE")
        held.set()
        time.sleep(seconds)
        connection.execute("COMMIT")
        connection.close()

    thread = threading.Thread(target=hold)
    thread.start()
    held.wait()
    return thread


def _create(client: TestClient, code: str):
    return client.post(
        "/api/v1/objects",
        json={
            "workspaceKey": "default",
            "applicationKey": "par-app",
            "objectTypeKey": FOLDER,
            "name": code,
            "attributes": [{"attributeTypeKey": "par-code", "value": code}],
        },
    )


def test_a_write_waits_for_the_writer_lock_up_to_the_lock_wait(tmp_path, monkeypatch, _migrated_template):
    database = tmp_path / "lock-wait.db"
    database.write_bytes(_migrated_template.read_bytes())
    with _serve(database, monkeypatch, SQLITE_LOCK_WAIT_SECONDS="10") as client:
        holder = _hold_writer_lock(database, 1.5)
        started = time.perf_counter()
        response = _create(client, "WAITED")
        holder.join()
        assert response.status_code == 201, response.text
        assert time.perf_counter() - started >= 1.4
    # With a shorter wait than the holder takes, the write gives up.
    with _serve(database, monkeypatch, SQLITE_LOCK_WAIT_SECONDS="1") as client:
        holder = _hold_writer_lock(database, 2.5)
        try:
            with pytest.raises(OperationalError, match="database is locked"):
                _create(client, "GAVE UP")
        finally:
            holder.join()


# --- B2: 20261001_01 ---------------------------------------------------------------------------


def _background(client: TestClient, code: str) -> dict:
    response = client.post(
        "/api/v1/batches",
        json={
            "workspaceKey": "default",
            "policy": "independent",
            "run": "background",
            "items": [create_item(k, FOLDER, f"{code}-{n}", f"{code}-{n}") for n in range(3)],
        },
    )
    assert response.status_code == 202, response.text
    job_id = response.json()["id"]
    deadline = time.monotonic() + 15
    while (job := client.get(f"/api/v1/jobs/{job_id}").json())["state"] != "completed":
        assert time.monotonic() < deadline, job
        time.sleep(0.05)
    assert job["result"] == "applied"
    return job


def test_upgrade_from_b1_keeps_its_jobs_and_runs_background_jobs(tmp_path, monkeypatch, _migrated_template):
    database = tmp_path / "b2-upgrade.db"
    database.write_bytes(_migrated_template.read_bytes())
    # An inline job, kept when the database goes back to B1's revision.
    with _serve(database, monkeypatch) as client:
        before = _batch(client, "BEFORE")["job"]["id"]
    command.downgrade(_config(database), B1)
    assert "job_inputs" not in _tables(database)
    for start in range(2):
        with _serve(database, monkeypatch) as client:
            assert client.get("/health").json() == {"status": "ok"}
            kept = client.get(f"/api/v1/jobs/{before}").json()
            assert (kept["state"], kept["leaseOwner"], kept["cancelRequestedAt"]) == ("completed", None, None)
            _background(client, f"AFTER-{start}")
        assert _version(database) == HEAD
    assert "job_inputs" in _tables(database)


def test_an_interrupted_b2_upgrade_completes_and_an_unknown_inputs_table_is_refused(
    tmp_path, monkeypatch, _migrated_template
):
    database = tmp_path / "b2-interrupted.db"
    database.write_bytes(_migrated_template.read_bytes())
    command.downgrade(_config(database), B1)
    # A stopped run added one lease column and created job_inputs, without the version bump.
    engine = create_engine(f"sqlite:///{database}")
    with engine.begin() as connection:
        connection.execute(text("ALTER TABLE jobs ADD COLUMN lease_owner VARCHAR(120)"))
        connection.execute(
            text(
                "CREATE TABLE job_inputs (sequence_id INTEGER PRIMARY KEY, job_id INTEGER, "
                "item_index INTEGER, ref VARCHAR, item JSON)"
            )
        )
    engine.dispose()
    with _serve(database, monkeypatch) as client:
        assert client.get("/health").json() == {"status": "ok"}
        _background(client, "RESUMED")
    assert _version(database) == HEAD

    command.downgrade(_config(database), B1)
    engine = create_engine(f"sqlite:///{database}")
    with engine.begin() as connection:
        connection.execute(text("CREATE TABLE job_inputs (id INTEGER PRIMARY KEY, payload BLOB)"))
    engine.dispose()
    with pytest.raises(Exception, match="unexpected schema"):
        command.upgrade(_config(database), "head")
    assert _version(database) == B1
    with _serve(database, monkeypatch) as client:
        assert client.get("/health").status_code == 503
    assert _version(database) == B1


def test_a_live_unique_value_check_seeks_to_the_value(tmp_path, _migrated_template):
    """B2 budget finding: the live unique-value lookup read every value of the attribute, so each
    write with a unique attribute cost in proportion to the records holding it. It now seeks."""
    database = tmp_path / "b2-value-index.db"
    database.write_bytes(_migrated_template.read_bytes())
    engine = create_engine(f"sqlite:///{database}")
    try:
        with engine.connect() as connection:
            plan = " ".join(
                str(row[-1])
                for row in connection.execute(
                    text(
                        "EXPLAIN QUERY PLAN SELECT objects.id FROM objects JOIN attribute_values "
                        "ON attribute_values.object_id = objects.id "
                        "WHERE attribute_values.attribute_type_key = 'code' "
                        "AND attribute_values.text_value = 'A-1' AND objects.workspace_key = 'default' "
                        "LIMIT 1"
                    )
                )
            )
    finally:
        engine.dispose()
    assert "ix_attribute_values_key_text" in plan, plan
    # Downgrading to B1 removes the index with the rest of B2.
    command.downgrade(_config(database), B1)
    engine = create_engine(f"sqlite:///{database}")
    try:
        assert "ix_attribute_values_key_text" not in {
            index["name"] for index in inspect(engine).get_indexes("attribute_values")
        }
    finally:
        engine.dispose()
