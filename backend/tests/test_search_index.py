"""Base 0.8 S8: search reads the trigram index over text values, and the index follows every write.

A search of three or more characters narrows its value look-up to the records the trigram index
names (D25). The index only decides which records are looked up: the match stays the "contains"
``LIKE`` it was, in every context, so a search answers the same through the index, through the
per-record look-up it falls back to for common phrases, and in live, change-set and publication reads.

Triggers on the value tables keep the indexes equal to the values on every write; FTS5's
``integrity-check`` compares each index with its table. These are the SQLite forms, which PG2
replaces with ``pg_trgm`` (PG-D7); their SQLite migration tests went with the SQLite revisions.
"""

import test_context_read_parity
from sqlalchemy import event, select, text
from sqlalchemy.dialects import postgresql, sqlite
from test_context_read_parity import (
    ENTRY,
    WORKSPACE,
    _change_set_version,
    _create,
    _ok,
    _seed,
    _walk,
    load_change_set,
)

from app.db import get_engine
from app.engine.reads import object_query, snapshot_reads
from app.models.database import ChangeSetBaseObject, RdmObject
from app.models.search_index import SEARCH_INDEXES, match_phrase

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
    monkeypatch.setattr(object_query, "INDEXED_VALUE_LIMIT", -1)
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


def test_change_set_search_counts_a_change_set_match_and_not_a_hidden_base_match(client):
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
    change_set = load_change_set(client, source="currentLive")["id"]
    context = {"changeSetId": change_set}

    def patch(record: dict, body: dict) -> None:
        current = _ok(client.get(f"/api/v1/objects/{ENTRY}/{record['id']}", params=context))
        _ok(
            client.patch(
                f"/api/v1/objects/{ENTRY}/{record['id']}",
                json={
                    **body,
                    "expectedVersion": current["version"],
                    "changeSetId": change_set,
                    "expectedChangeSetVersion": _change_set_version(client, change_set),
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
                "changeSetId": change_set,
                "expectedVersion": current["version"],
                "expectedChangeSetVersion": _change_set_version(client, change_set),
            },
        ),
        204,
    )
    added = _create(
        client, ENTRY, "Needle five", folder["id"], {"par-code": "A-5"},
        changeSetId=change_set, expectedChangeSetVersion=_change_set_version(client, change_set),
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
    # Live creates, updates and deletes; change-set writes, tombstones and a change-set-only record;
    # publishing, which copies live data into a publication; change sets on both base kinds.
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
    # Discarding a change set deletes its rows and its base's in bulk.
    overlay = seeded["overlay"]
    _ok(
        client.delete(
            f"/api/v1/change-sets/{overlay}",
            params={"expectedVersion": _change_set_version(client, overlay)},
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


def _search_guards() -> list:
    """The index guard of a live search and of a change set search over its base's rows."""
    context = snapshot_reads.SnapshotContext(
        "change_set",
        "change-set-id",
        WORKSPACE,
        None,
        snapshot_reads.SnapshotBase(ChangeSetBaseObject, None, "base_id", "base-id"),
    )
    projection = snapshot_reads.object_projection(context, object_type_key=ENTRY)
    snapshot = snapshot_reads._value_candidates(projection, context)(match_phrase("note"), ["n"])
    return [
        select(RdmObject.id).where(object_query._live_value_candidates(match_phrase("note"), ["n"])),
        select(projection.c.object_id).where(snapshot),
    ]


def test_search_reads_the_index_on_sqlite_only():
    """PostgreSQL has no FTS5 index (its trigram form arrives with 0.11): a search there compiles
    without the guard and looks every record's values up, as before S8."""
    for statement in _search_guards():
        on_sqlite = str(statement.compile(dialect=sqlite.dialect()))
        on_postgresql = str(statement.compile(dialect=postgresql.dialect()))
        assert "_text_search" in on_sqlite and "MATCH" in on_sqlite
        # One parenthesized predicate, never a Boolean column compared with 1.
        assert "WHERE ((SELECT count(*)" in on_sqlite and ") = 1" not in on_sqlite
        assert "_text_search" not in on_postgresql and "MATCH" not in on_postgresql
        assert "WHERE true" in on_postgresql
