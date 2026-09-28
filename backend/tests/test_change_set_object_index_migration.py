"""Base 0.8 A6 migration: owner-leading page indexes on change set objects (D28).

``20260928_01`` adds (change set, type, name, object) and (change set, parent, type, name, object)
on ``change_set_objects`` and drops the ten single-column indexes the ORM no longer declares where
a ``create_all`` database has them. The data is written through the API at head, the database is
taken back to ``20260927_01`` and upgraded again through the FastAPI lifespan. Object and relation
pages in every context must answer as before, an interrupted run must complete, and each starting
point must end with the schema the ORM declares.
"""

import pytest
from alembic import command
from sqlalchemy import create_engine, inspect, text
from test_context_read_parity import _seed
from test_page_index_migrations import _reads
from test_schema_drift import _schema_differences
from test_snapshot_value_migration import _app, _config, _version

PRECEDING, HEAD = "20260927_01", "20260928_01"
TABLE = "change_set_objects"
EXPECTED = {
    "ix_change_set_objects_type_name": ("change_set_id", "object_type_key", "name", "object_id"),
    "ix_change_set_objects_parent_name": (
        "change_set_id",
        "parent_object_id",
        "object_type_key",
        "name",
        "object_id",
    ),
}
REMOVED = {
    "publication_objects": ("parent_object_id", "object_type_key"),
    "change_set_objects": ("parent_object_id", "object_type_key"),
    "publication_relations": ("from_object_id", "to_object_id", "relation_type_key"),
    "change_set_relations": ("from_object_id", "to_object_id", "relation_type_key"),
}


def _indexes(database) -> dict[str, tuple[str, ...]]:
    engine = create_engine(f"sqlite:///{database}")
    try:
        return {
            index["name"]: tuple(index["column_names"])
            for index in inspect(engine).get_indexes(TABLE)
            if index["name"] in EXPECTED
        }
    finally:
        engine.dispose()


def _execute(database, *statements: str) -> None:
    engine = create_engine(f"sqlite:///{database}")
    try:
        with engine.begin() as connection:
            for statement in statements:
                connection.execute(text(statement))
    finally:
        engine.dispose()


@pytest.fixture
def seeded_database(tmp_path, monkeypatch, _migrated_template):
    """Records and relations in every context written at head, then the indexes dropped."""
    database = tmp_path / "a6.db"
    database.write_bytes(_migrated_template.read_bytes())
    # A clean bootstrap creates the indexes and matches the ORM.
    assert _indexes(database) == EXPECTED
    assert _schema_differences(f"sqlite:///{database}") == []
    with _app(database, monkeypatch) as client:
        seeded = _seed(client)
        reads = _reads(client, seeded)
    assert any(rows for rows in reads.values())
    command.downgrade(_config(database), PRECEDING)
    assert _indexes(database) == {}
    return database, seeded, reads


def _upgraded_and_answering(database, monkeypatch, seeded, reads) -> None:
    with _app(database, monkeypatch) as client:
        assert client.get("/health").json() == {"status": "ok"}
        assert _reads(client, seeded) == reads
    assert _version(database) == HEAD
    assert _indexes(database) == EXPECTED
    assert _schema_differences(f"sqlite:///{database}") == []


def test_upgrade_adds_the_indexes_and_pages_answer_as_before(seeded_database, monkeypatch):
    database, seeded, reads = seeded_database
    for _start in range(2):
        _upgraded_and_answering(database, monkeypatch, seeded, reads)


def test_upgrade_completes_after_an_interrupted_run(seeded_database, monkeypatch):
    database, seeded, reads = seeded_database
    # SQLite commits DDL as it runs: a stopped upgrade can leave one index created and another of
    # the same name but an earlier shape without recording the version. The first is kept, the
    # second rebuilt.
    _execute(
        database,
        "CREATE INDEX ix_change_set_objects_type_name ON change_set_objects "
        "(change_set_id, object_type_key, name, object_id)",
        "CREATE INDEX ix_change_set_objects_parent_name ON change_set_objects "
        "(change_set_id, parent_object_id)",
    )
    assert _version(database) == PRECEDING
    _upgraded_and_answering(database, monkeypatch, seeded, reads)


def test_upgrade_drops_the_indexes_the_orm_no_longer_declares(seeded_database, monkeypatch):
    """A database built with ``create_all`` before A6 holds the ten single-column indexes."""
    database, seeded, reads = seeded_database
    _execute(
        database,
        *(
            f"CREATE INDEX ix_{table}_{column} ON {table} ({column})"
            for table, columns in REMOVED.items()
            for column in columns
        ),
    )
    assert len(_schema_differences(f"sqlite:///{database}")) == 12
    _upgraded_and_answering(database, monkeypatch, seeded, reads)


def test_downgrade_removes_the_indexes(seeded_database, monkeypatch):
    database, seeded, reads = seeded_database
    _upgraded_and_answering(database, monkeypatch, seeded, reads)
    command.downgrade(_config(database), PRECEDING)
    assert _version(database) == PRECEDING
    assert _indexes(database) == {}
