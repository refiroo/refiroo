"""Base 0.8 W2 migration: change sets and publications (ADR-031).

``20260926_04`` rebuilds the draft and revision tables under their ADR-031 names, renames their
columns, indexes and constraints, the workspace publication pointer, the relation-set change-set
column and the snapshot owner kinds, and rewrites stored audit names. The data is written through
the API at head, the database is taken back to ``20260926_03`` and upgraded again through the
FastAPI lifespan. Every context must answer as before, the schema must equal a clean bootstrap's,
and an interrupted run must complete.
"""

import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch as mock_patch

import pytest
from alembic import command
from sqlalchemy import create_engine, inspect, text
from test_context_read_parity import WORKSPACE, _seed
from test_page_index_migrations import _reads
from test_snapshot_value_migration import _app, _config, _index, _version

import app.main as main_module

PRECEDING, HEAD = "20260926_03", "20260927_01"
MIGRATION = (
    Path(__file__).resolve().parents[1]
    / "app/migrations/versions/20260926_04_change_sets_and_publications.py"
)


def _revision():
    spec = importlib.util.spec_from_file_location("change_sets_and_publications", MIGRATION)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


REVISION = _revision()
OLD_TABLES = {table.name for table in REVISION._TABLES}
NEW_TABLES = {table.new_name for table in REVISION._TABLES}


def _schema(database: Path) -> dict[str, tuple]:
    """Columns, indexes, unique and check constraints of every renamed or rebuilt table."""
    engine = create_engine(f"sqlite:///{database}")
    try:
        inspector = inspect(engine)
        return {
            table: (
                tuple(column["name"] for column in inspector.get_columns(table)),
                frozenset(
                    (index["name"], tuple(index["column_names"]), bool(index["unique"]))
                    for index in inspector.get_indexes(table)
                ),
                frozenset(
                    (item["name"], tuple(item["column_names"]))
                    for item in inspector.get_unique_constraints(table)
                ),
                frozenset(
                    (item["name"], " ".join(item["sqltext"].split()))
                    for item in inspector.get_check_constraints(table)
                ),
            )
            for table in sorted(set(inspector.get_table_names()) & (OLD_TABLES | NEW_TABLES))
        }
    finally:
        engine.dispose()


def _audit(database: Path) -> list[tuple]:
    engine = create_engine(f"sqlite:///{database}")
    try:
        with engine.connect() as connection:
            return [
                (row.aggregate_type, row.action, json.loads(row.changes))
                for row in connection.execute(
                    text(
                        "SELECT aggregate_type, action, changes FROM audit_events "
                        "WHERE aggregate_type NOT LIKE 'model%' ORDER BY sequence_id"
                    )
                )
            ]
    finally:
        engine.dispose()


def _state(client, seeded) -> tuple:
    """Record pages in every context plus the workspace's change sets and publications."""
    lists = tuple(
        client.get(f"/api/v1/workspaces/{WORKSPACE}/{kind}", params={"pageSize": 500}).json()
        for kind in ("change-sets", "publications")
    )
    return _reads(client, seeded), lists


def _scalar(database: Path, sql: str):
    engine = create_engine(f"sqlite:///{database}")
    try:
        with engine.connect() as connection:
            return connection.execute(text(sql)).all()
    finally:
        engine.dispose()


@pytest.fixture
def seeded_database(tmp_path, monkeypatch, _migrated_template):
    """Every context and a withdrawn publication written at head, then taken back to 20260926_03."""
    database = tmp_path / "w2.db"
    database.write_bytes(_migrated_template.read_bytes())
    with _app(database, monkeypatch) as client:
        seeded = _seed(client)
        publication = client.get(f"/api/v1/workspaces/{WORKSPACE}/publications").json()["items"][0]
        response = client.post(f"/api/v1/publications/{publication['id']}/withdrawal")
        assert response.status_code == 204, response.text
        state = _state(client, seeded)
    head = {
        "schema": _schema(database),
        "index": _index(database),
        "audit": _audit(database),
    }
    assert set(head["schema"]) == NEW_TABLES
    assert {row[0] for row in head["index"]} == {"publication", "base", "change_set"}
    assert ("publication", "published") in {row[:2] for row in head["audit"]}
    assert ("workspace", "publication-withdrawn") in {row[:2] for row in head["audit"]}

    command.downgrade(_config(database), PRECEDING)

    # The downgrade restores the preceding schema exactly and the earlier stored names.
    fresh = tmp_path / "preceding.db"
    command.upgrade(_config(fresh), PRECEDING)
    assert _schema(database) == _schema(fresh)
    assert set(_schema(database)) == OLD_TABLES
    assert _scalar(database, "SELECT status FROM workspace_revisions") == [("retired",)]
    assert {row[0] for row in _index(database)} == {"revision", "base", "draft"}
    audit = _audit(database)
    names = {row[:2] for row in audit}
    assert {("workspace-revision", "activated"), ("workspace", "publication-retired")} <= names
    assert not names & {("publication", "published"), ("change-set", "created")}
    assert any("draftId" in changes for aggregate, _action, changes in audit if aggregate == "workspace-revision")
    assert any("workspaceDraftId" in changes for _aggregate, _action, changes in audit)
    return database, seeded, state, head


def _assert_upgraded(database: Path, monkeypatch, seeded, state, head) -> None:
    with _app(database, monkeypatch) as client:
        assert client.get("/health").json() == {"status": "ok"}
        assert _state(client, seeded) == state
    assert _version(database) == HEAD
    assert _schema(database) == head["schema"]
    assert _index(database) == head["index"]
    assert _audit(database) == head["audit"]
    leftovers = _scalar(database, "SELECT name FROM sqlite_master WHERE name LIKE '\\_w2\\_%' ESCAPE '\\'")
    assert leftovers == []


def test_upgrade_renames_storage_and_contexts_answer_as_before_across_restarts(
    seeded_database, monkeypatch
):
    database, seeded, state, head = seeded_database
    for _start in range(2):
        _assert_upgraded(database, monkeypatch, seeded, state, head)
    # The publication keeps its number and reads back withdrawn.
    publications = state[1][1]["items"]
    assert [(item["publicationNumber"], item["status"]) for item in publications] == [
        (1, "withdrawn")
    ]
    # The rebuilt snapshot table keeps its trigram index current.
    engine = create_engine(f"sqlite:///{database}")
    try:
        with engine.connect() as connection:
            triggers = connection.scalars(
                text(
                    "SELECT name FROM sqlite_master WHERE type = 'trigger' "
                    "AND tbl_name = 'snapshot_attribute_values'"
                )
            ).all()
            assert len(triggers) == 3
            assert connection.execute(
                text(
                    "INSERT INTO snapshot_attribute_values_text_search"
                    "(snapshot_attribute_values_text_search) VALUES ('integrity-check')"
                )
            )
    finally:
        engine.dispose()


def test_upgrade_completes_after_an_interrupted_run(seeded_database, monkeypatch):
    database, seeded, state, head = seeded_database
    tables = {table.name: table for table in REVISION._TABLES}
    engine = create_engine(f"sqlite:///{database}")

    def staging(table) -> str:
        prefix = f"CREATE TABLE {table.new_name} ("
        return f'CREATE TABLE "_w2_{table.new_name}" (' + table.new_ddl[len(prefix) :]

    def copy(connection, table) -> None:
        targets = ", ".join(new for _old, new in table.columns())
        sources = ", ".join(old for old, _new in table.columns())
        connection.execute(
            text(f"INSERT INTO _w2_{table.new_name} ({targets}) SELECT {sources} FROM {table.name}")
        )

    try:
        # SQLite commits DDL as it runs. A stopped upgrade can leave a partial copy beside its
        # source, a finished copy whose source is gone, or a swapped table without its indexes.
        with engine.begin() as connection:
            partial = tables["workspace_revisions"]
            connection.execute(text(staging(partial)))
            connection.execute(
                text(
                    "INSERT INTO _w2_publications (sequence_id, id, workspace_key, model_release_id, "
                    "publication_number, status, created_at, published_at) VALUES "
                    "(999, 'stale', 'default', 1, 99, 'active', '2026-01-01', '2026-01-01')"
                )
            )
            copied = tables["workspace_revision_objects"]
            connection.execute(text(staging(copied)))
            copy(connection, copied)
            connection.execute(text(f"DROP TABLE {copied.name}"))
            swapped = tables["workspace_draft_bases"]
            connection.execute(text(staging(swapped)))
            copy(connection, swapped)
            connection.execute(text(f"DROP TABLE {swapped.name}"))
            connection.execute(text(f"ALTER TABLE _w2_{swapped.new_name} RENAME TO {swapped.new_name}"))
    finally:
        engine.dispose()
    assert _version(database) == PRECEDING
    _assert_upgraded(database, monkeypatch, seeded, state, head)


def test_upgrade_refuses_a_source_table_of_another_shape_without_a_traceback(
    seeded_database, monkeypatch
):
    database, _seeded, _state_rows, _head = seeded_database
    engine = create_engine(f"sqlite:///{database}")
    try:
        with engine.begin() as connection:
            connection.execute(text("ALTER TABLE workspace_draft_objects RENAME COLUMN draft_id TO owner"))
        with (
            mock_patch.object(main_module.logger, "error") as error,
            _app(database, monkeypatch) as client,
        ):
            assert client.get("/health").status_code == 503
        message = str(error.call_args.args[1])
        assert PRECEDING in message and HEAD in message
        assert "workspace_draft_objects lacks columns ['draft_id']" in message
        assert "restore the pre-upgrade backup" in message
        assert "Traceback" not in message
        assert _version(database) == PRECEDING
        with engine.connect() as connection:
            assert connection.scalar(text("SELECT count(*) FROM workspace_draft_objects")) > 0
    finally:
        engine.dispose()


def test_upgrade_refuses_another_dialect_with_a_recovery_instruction(monkeypatch):
    revision = _revision()
    executed: list = []
    bind = SimpleNamespace(dialect=SimpleNamespace(name="postgresql"), execute=executed.append)
    monkeypatch.setattr(revision.op, "get_bind", lambda: bind, raising=False)
    monkeypatch.setattr(revision, "_needs_upgrade", lambda _bind: True)
    with pytest.raises(RuntimeError, match="supported automatically only for SQLite"):
        revision.upgrade()
    monkeypatch.setattr(revision, "_needs_upgrade", lambda _bind: False)
    revision.upgrade()
    revision.downgrade()
    assert executed == []
