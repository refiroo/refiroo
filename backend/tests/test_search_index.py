"""Base 0.8 S8: search reads the trigram index over text values, and the index follows every write.

A search of three or more characters narrows its value look-up to the records the trigram index
names (D25). The index only decides which records are looked up: the match stays the "contains"
``LIKE`` it was, in every context, so a search answers the same through the index, through the
per-record look-up it falls back to for common phrases, and in live, draft and history reads.

``20260926_03`` builds the indexes. Triggers on the value tables keep them equal to the values on
every write; FTS5's ``integrity-check`` compares each index with its table.
"""

from pathlib import Path

import pytest
import test_context_read_parity
from alembic import command
from sqlalchemy import create_engine, event, text
from test_context_read_parity import (
    ENTRY,
    WORKSPACE,
    _create,
    _draft,
    _draft_version,
    _ok,
    _seed,
    _walk,
)
from test_snapshot_value_migration import _app, _config, _version

from app.db import get_engine
from app.models.database import Base
from app.models.search_index import SEARCH_INDEXES
from app.services import objects

PRECEDING, HEAD = "20260926_02", "20260926_03"
# The parity model's app over a migrated database.
client = test_context_read_parity.client
SEARCHES = ("note", "50%", "d_4", "t_s", '"quoted"', "Ünal", "STRAßE", "naïve", "F-", "-10", "zzz")


def _ids(client, context: dict, search: str) -> list[str]:
    return [
        item["id"]
        for item in _walk(client, f"/api/v1/objects/{ENTRY}", {**context, "search": search})
    ]


def _check_indexes(connection) -> None:
    """FTS5 compares each external-content index with its table; a difference is an error."""
    for index in SEARCH_INDEXES:
        connection.execute(
            text(f"INSERT INTO {index.name}({index.name}, rank) VALUES ('integrity-check', 1)")
        )


def _search_objects(connection) -> set[tuple[str, str]]:
    """The index tables and triggers in a database, by type and name."""
    return {
        tuple(row)
        for row in connection.execute(
            text(
                "SELECT type, name FROM sqlite_master "
                "WHERE name LIKE '%\\_text\\_search%' ESCAPE '\\'"
            )
        )
    }


def test_search_answers_the_same_through_the_index_in_every_context(client, monkeypatch):
    seeded = _seed(client)
    statements: list[str] = []
    event.listen(
        get_engine(), "before_cursor_execute", lambda *args: statements.append(args[2])
    )
    indexed = {
        (name, search): _ids(client, context, search)
        for name, context in seeded["contexts"].items()
        for search in SEARCHES
    }
    # Every context looked values up through the index; one- and two-character searches do not.
    for name, context in seeded["contexts"].items():
        statements.clear()
        _ids(client, context, "note")
        assert any("_text_search" in item and "MATCH" in item for item in statements), name
        statements.clear()
        _ids(client, context, "te")
        assert not any("_text_search" in statement for statement in statements), name

    # Past the limit, every record's values are looked up: the same records in the same order.
    monkeypatch.setattr(objects, "INDEXED_VALUE_LIMIT", -1)
    for (name, search), ids in indexed.items():
        assert _ids(client, seeded["contexts"][name], search) == ids, (name, search)
    for search in SEARCHES:
        expected = indexed[("live", search)]
        assert all(indexed[(name, search)] == expected for name in seeded["contexts"]), search
    assert indexed[("live", "zzz")] == []
    assert len(indexed[("live", "F-")]) == 1  # a value match: foxtrot's code
    # SQLite folds ASCII case only, through the index as before it.
    for name, context in seeded["contexts"].items():
        assert _ids(client, context, "ünal") == [], name


def test_draft_search_counts_a_draft_match_and_not_a_hidden_base_match(client):
    live = {"workspaceKey": WORKSPACE}
    folder = _create(client, "par-folder", "Holder", None, {"par-code": "H-0"}, **live)
    renamed, recoded, gained, deleted = (
        _create(client, ENTRY, name, folder["id"], {"par-code": code}, **live)
        for name, code in (
            ("Needle one", "N-1"),
            ("Plain two", "needle-2"),
            ("Plain three", "P-3"),
            ("Needle four", "N-4"),
        )
    )
    draft = _draft(client, source="currentLive")["id"]
    context = {"workspaceDraftId": draft}

    def patch(record: dict, body: dict) -> None:
        current = _ok(client.get(f"/api/v1/objects/{ENTRY}/{record['id']}", params=context))
        _ok(
            client.patch(
                f"/api/v1/objects/{ENTRY}/{record['id']}",
                json={
                    **body,
                    "expectedVersion": current["version"],
                    "workspaceDraftId": draft,
                    "expectedWorkspaceDraftVersion": _draft_version(client, draft),
                },
            )
        )

    patch(renamed, {"name": "Renamed one"})
    patch(recoded, {"attributes": [{"attributeTypeKey": "par-code", "value": "P-2"}]})
    patch(gained, {"attributes": [{"attributeTypeKey": "par-code", "value": "NEEDLE-3"}]})
    current = _ok(client.get(f"/api/v1/objects/{ENTRY}/{deleted['id']}", params=context))
    _ok(
        client.delete(
            f"/api/v1/objects/{ENTRY}/{deleted['id']}",
            params={
                "workspaceDraftId": draft,
                "expectedVersion": current["version"],
                "expectedWorkspaceDraftVersion": _draft_version(client, draft),
            },
        ),
        204,
    )
    added = _create(
        client, ENTRY, "Needle five", folder["id"], {"par-code": "A-5"},
        workspaceDraftId=draft, expectedWorkspaceDraftVersion=_draft_version(client, draft),
    )

    assert set(_ids(client, live, "needle")) == {
        renamed["id"], recoded["id"], deleted["id"]
    }
    assert set(_ids(client, context, "needle")) == {gained["id"], added["id"]}
    page = _ok(
        client.get(
            f"/api/v1/objects/{ENTRY}",
            params={**context, "search": "needle", "includeTotal": "true", "pageSize": 1},
        )
    )
    assert page["totalCount"] == 2
    assert _ok(
        client.get(
            f"/api/v1/objects/{ENTRY}",
            params={**context, "search": "needle", "includeTotal": "true"},
        )
    )["totalCount"] == 2


def test_every_write_path_keeps_the_indexes_equal_to_the_values(client):
    # Live creates, updates and deletes; draft writes, tombstones and a draft-only record; a
    # publication copying live data into a revision; drafts on both base kinds.
    seeded = _seed(client)
    # A live value changed in place, and one removed.
    live = seeded["contexts"]["live"]
    entry = _ok(client.get(f"/api/v1/objects/{ENTRY}/{seeded['entries'][1]['id']}", params=live))
    entry = _ok(
        client.patch(
            f"/api/v1/objects/{ENTRY}/{entry['id']}",
            json={
                "attributes": [{"attributeTypeKey": "par-code", "value": "Changed-2"}],
                "expectedVersion": entry["version"],
            },
        )
    )
    _ok(
        client.patch(
            f"/api/v1/objects/{ENTRY}/{entry['id']}",
            json={
                "attributes": [{"attributeTypeKey": "par-note", "value": None}],
                "expectedVersion": entry["version"],
            },
        )
    )
    assert _ids(client, live, "changed-2") == [entry["id"]]
    assert _ids(client, live, "b-2") == []
    with get_engine().connect() as connection:
        _check_indexes(connection)
    # Discarding a draft deletes its rows and its base's in bulk.
    overlay = seeded["overlay"]
    _ok(
        client.delete(
            f"/api/v1/workspace-drafts/{overlay}",
            params={"expectedVersion": _draft_version(client, overlay)},
        ),
        204,
    )
    with get_engine().connect() as connection:
        _check_indexes(connection)
        stale = connection.scalar(
            text(
                "SELECT count(*) FROM snapshot_attribute_values_text_search "
                "JOIN snapshot_attribute_values v ON v.sequence_id = "
                "snapshot_attribute_values_text_search.rowid WHERE v.owner_id = :owner"
            ),
            {"owner": overlay},
        )
    assert stale == 0


def test_a_clean_bootstrap_and_create_all_build_the_same_indexes(_migrated_template, tmp_path):
    migrated = create_engine(f"sqlite:///{_migrated_template}")
    created = create_engine(f"sqlite:///{tmp_path / 'created.db'}")
    try:
        Base.metadata.create_all(created)
        with migrated.connect() as left, created.connect() as right:
            expected = {
                ("table", index.name) for index in SEARCH_INDEXES
            } | {
                ("trigger", f"{index.name}_{name}")
                for index in SEARCH_INDEXES
                for name in ("insert", "delete", "update")
            }
            assert expected <= _search_objects(left) == _search_objects(right)
    finally:
        migrated.dispose()
        created.dispose()


def _reads(client, seeded) -> dict:
    return {
        (name, search): _ids(client, context, search)
        for name, context in seeded["contexts"].items()
        for search in SEARCHES
    }


@pytest.fixture
def downgraded_database(tmp_path, monkeypatch, _migrated_template):
    """Data in every context written at head, then taken back to the preceding revision."""
    database = tmp_path / "s8.db"
    database.write_bytes(_migrated_template.read_bytes())
    with _app(database, monkeypatch) as client:
        seeded = _seed(client)
        reads = _reads(client, seeded)
    command.downgrade(_config(database), PRECEDING)
    engine = create_engine(f"sqlite:///{database}")
    try:
        with engine.connect() as connection:
            assert _search_objects(connection) == set()
    finally:
        engine.dispose()
    return database, seeded, reads


def _assert_upgraded(database: Path, monkeypatch, seeded, reads) -> None:
    with _app(database, monkeypatch) as client:
        assert client.get("/health").json() == {"status": "ok"}
        assert _reads(client, seeded) == reads
    assert _version(database) == HEAD
    engine = create_engine(f"sqlite:///{database}")
    try:
        with engine.connect() as connection:
            _check_indexes(connection)
    finally:
        engine.dispose()


def test_upgrade_builds_the_indexes_from_existing_values(downgraded_database, monkeypatch):
    database, seeded, reads = downgraded_database
    # Upgrade through the FastAPI lifespan, then start again on the upgraded database.
    for _start in range(2):
        _assert_upgraded(database, monkeypatch, seeded, reads)


def test_upgrade_completes_after_an_interrupted_run(downgraded_database, monkeypatch):
    database, seeded, reads = downgraded_database
    engine = create_engine(f"sqlite:///{database}")
    try:
        # SQLite commits DDL as it runs: a stopped upgrade can leave an index without its
        # triggers, or one that another shape and no content fill.
        with engine.begin() as connection:
            connection.execute(
                text("CREATE VIRTUAL TABLE attribute_values_text_search USING fts5(text_value)")
            )
            connection.execute(
                text(
                    "CREATE VIRTUAL TABLE snapshot_attribute_values_text_search USING fts5("
                    "text_value, content='snapshot_attribute_values', "
                    "content_rowid='sequence_id', tokenize='trigram')"
                )
            )
    finally:
        engine.dispose()
    assert _version(database) == PRECEDING
    _assert_upgraded(database, monkeypatch, seeded, reads)
