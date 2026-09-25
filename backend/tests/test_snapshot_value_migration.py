"""Base 0.8 S2 migration: typed value rows for revision, draft-base and draft objects.

The data is written through the API at head, where the flush hook indexes it; the database is then
taken back to the 0.7 head (``20260912_01``), which drops the index, and upgraded again through the
FastAPI lifespan. The backfill must rebuild exactly the rows the hook wrote, and every draft and
history read must answer as before.
"""

import json
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import patch as mock_patch

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, inspect, text
from test_context_read_parity import ENTRY, _seed, _walk, parity_model

import app.main as main_module
from app.config import reload_settings
from app.db import get_engine
from app.main import create_app
from app.models.database import SnapshotAttributeValue
from app.services.model.registry import model_registry

PRECEDING, HEAD = "20260912_01", "20260926_01"
QUERIES = (
    {"sort": "par-amount"},
    {"sort": "-par-seen", "filter.par-flag.isNull": "false"},
    {"filter.par-due.lte": "2026-01-10", "sort": "name"},
    {"search": "note", "sort": "par-code"},
)


@contextmanager
def _app(database: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    model_path = database.with_suffix(".model.json")
    model_path.write_text(json.dumps(parity_model()))
    with monkeypatch.context() as patch:
        patch.setenv("DATABASE_URL", f"sqlite:///{database}")
        patch.setenv("RDM_MODEL_PATH", str(model_path))
        reload_settings()
        model_registry.clear()
        try:
            with TestClient(create_app()) as client:
                yield client
        finally:
            get_engine().dispose()
    reload_settings()
    model_registry.clear()


def _config(database: Path) -> Config:
    config = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))
    config.set_main_option("sqlalchemy.url", f"sqlite:///{database}")
    return config


def _index(database: Path) -> set[tuple]:
    engine = create_engine(f"sqlite:///{database}")
    try:
        with engine.connect() as connection:
            return {
                tuple(row)
                for row in connection.execute(
                    text(
                        "SELECT owner_kind, owner_id, object_id, attribute_type_key, value_type, "
                        "text_value, integer_value, decimal_value, boolean_value, date_value, "
                        "datetime_value, json_value FROM snapshot_attribute_values"
                    )
                )
            }
    finally:
        engine.dispose()


def _reads(client: TestClient, contexts: dict) -> dict:
    return {
        (name, json.dumps(query, sort_keys=True)): [
            (item["id"], item["name"], json.dumps(item["attributes"], sort_keys=True))
            for item in _walk(client, f"/api/v1/objects/{ENTRY}", {**context, **query})
        ]
        for name, context in contexts.items()
        for query in QUERIES
    }


def _version(database: Path) -> str:
    engine = create_engine(f"sqlite:///{database}")
    try:
        with engine.connect() as connection:
            return connection.scalar(text("SELECT version_num FROM alembic_version"))
    finally:
        engine.dispose()


@pytest.fixture
def seeded_database(tmp_path, monkeypatch, _migrated_template):
    """A database holding live data, drafts on both base kinds and a revision, indexed at head."""
    database = tmp_path / "s2.db"
    database.write_bytes(_migrated_template.read_bytes())
    with _app(database, monkeypatch) as client:
        seeded = _seed(client)
        reads = _reads(client, seeded["contexts"])
    index = _index(database)
    assert {row[0] for row in index} == {"revision", "base", "draft"}
    command.downgrade(_config(database), PRECEDING)
    engine = create_engine(f"sqlite:///{database}")
    try:
        assert "snapshot_attribute_values" not in inspect(engine).get_table_names()
    finally:
        engine.dispose()
    return database, seeded, reads, index


def test_upgrade_backfills_the_index_and_reads_answer_as_before_across_restarts(
    seeded_database, monkeypatch
):
    database, seeded, reads, index = seeded_database
    for _start in range(2):
        with _app(database, monkeypatch) as client:
            assert client.get("/health").json() == {"status": "ok"}
            assert _reads(client, seeded["contexts"]) == reads
        assert _version(database) == HEAD
        assert _index(database) == index


def test_upgrade_rebuilds_an_index_left_by_an_interrupted_run(seeded_database, monkeypatch):
    database, seeded, reads, index = seeded_database
    engine = create_engine(f"sqlite:///{database}")
    try:
        # SQLite commits DDL as it runs: a stopped upgrade can leave the table, part of its rows
        # and some page indexes behind without recording the new version.
        SnapshotAttributeValue.__table__.create(engine)
        with engine.begin() as connection:
            connection.execute(
                text(
                    "INSERT INTO snapshot_attribute_values (owner_kind, owner_id, object_id, "
                    "attribute_type_key, value_type, text_value) VALUES "
                    "('draft', 'stale', 'stale', 'par-code', 'text', 'stale')"
                )
            )
            connection.execute(
                text(
                    "CREATE INDEX ix_workspace_revision_objects_type_name ON "
                    "workspace_revision_objects (revision_id, object_type_key, name, object_id)"
                )
            )
    finally:
        engine.dispose()
    with _app(database, monkeypatch) as client:
        assert client.get("/health").json() == {"status": "ok"}
        assert _reads(client, seeded["contexts"]) == reads
    assert _version(database) == HEAD
    assert _index(database) == index


def test_upgrade_refuses_an_unexpected_partial_table_without_a_traceback(
    seeded_database, monkeypatch
):
    database, _seeded, _reads, _index_rows = seeded_database
    engine = create_engine(f"sqlite:///{database}")
    try:
        with engine.begin() as connection:
            connection.execute(text("CREATE TABLE snapshot_attribute_values (sentinel TEXT)"))
            connection.execute(text("INSERT INTO snapshot_attribute_values VALUES ('preserve')"))
        with (
            mock_patch.object(main_module.logger, "error") as error,
            _app(database, monkeypatch) as client,
        ):
            assert client.get("/health").status_code == 503
        message = str(error.call_args.args[1])
        assert PRECEDING in message and HEAD in message
        assert "snapshot_attribute_values has an unexpected schema" in message
        assert "take a consistent backup" in message
        assert "python -m app.cli.database_upgrade" in message
        assert "Traceback" not in message
        with engine.connect() as connection:
            assert connection.scalar(text("SELECT sentinel FROM snapshot_attribute_values")) == (
                "preserve"
            )
        assert _version(database) == PRECEDING
    finally:
        engine.dispose()
