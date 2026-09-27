"""Base 0.8 S2b migration: the value lookup index on ``snapshot_attribute_values``.

``20260926_02`` adds (owner, attribute, text value, object), which a draft write's unique-value
check seeks. The data is written through the API at head, the database is taken back to
``20260926_01``, which drops the index, and is upgraded again through the FastAPI lifespan. Draft
and history reads must answer as before, and an interrupted run that left an index of another shape
must complete.
"""

import pytest
from alembic import command
from sqlalchemy import create_engine, inspect, text
from test_context_read_parity import _seed
from test_page_index_migrations import _reads
from test_snapshot_value_migration import _app, _config, _version

PRECEDING, HEAD = "20260926_01", "20260927_01"
TABLE = "snapshot_attribute_values"
NAME = "ix_snapshot_attribute_values_owner_key_text"
COLUMNS = ("owner_id", "attribute_type_key", "text_value", "object_id")


def _lookup_index(database) -> tuple[str, ...] | None:
    engine = create_engine(f"sqlite:///{database}")
    try:
        indexes = {
            index["name"]: tuple(index["column_names"])
            for index in inspect(engine).get_indexes(TABLE)
        }
        return indexes.get(NAME)
    finally:
        engine.dispose()


@pytest.fixture
def seeded_database(tmp_path, monkeypatch, _migrated_template):
    database = tmp_path / "s2b.db"
    database.write_bytes(_migrated_template.read_bytes())
    # A clean bootstrap creates the index.
    assert _lookup_index(database) == COLUMNS
    with _app(database, monkeypatch) as client:
        seeded = _seed(client)
        reads = _reads(client, seeded)
    command.downgrade(_config(database), PRECEDING)
    assert _lookup_index(database) is None
    return database, seeded, reads


def test_upgrade_adds_the_index_and_reads_answer_as_before(seeded_database, monkeypatch):
    database, seeded, reads = seeded_database
    for _start in range(2):
        with _app(database, monkeypatch) as client:
            assert client.get("/health").json() == {"status": "ok"}
            assert _reads(client, seeded) == reads
        assert _version(database) == HEAD
        assert _lookup_index(database) == COLUMNS


def test_upgrade_completes_after_an_interrupted_run(seeded_database, monkeypatch):
    database, seeded, reads = seeded_database
    engine = create_engine(f"sqlite:///{database}")
    try:
        # SQLite commits DDL as it runs: a stopped upgrade can leave an index without recording
        # the version. One of another shape is rebuilt, not kept.
        with engine.begin() as connection:
            connection.execute(text(f"CREATE INDEX {NAME} ON {TABLE} (owner_id, text_value)"))
    finally:
        engine.dispose()
    assert _version(database) == PRECEDING
    with _app(database, monkeypatch) as client:
        assert client.get("/health").json() == {"status": "ok"}
        assert _reads(client, seeded) == reads
    assert _version(database) == HEAD
    assert _lookup_index(database) == COLUMNS
