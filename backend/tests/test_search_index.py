"""Base 0.8 S8: search reads the trigram index over text values, and the index follows every write.

A search of three or more characters narrows its value look-up to the records the trigram index
names (D25). The index only decides which records are looked up: the match stays the "contains"
``LIKE`` it was, in every context, so a search answers the same through the index, through the
per-record look-up it falls back to for common phrases, and in live, change-set and publication reads.

The indexes are ``pg_trgm`` GIN indexes (0.9.0-alpha.1 PG2, PG-D7), which PostgreSQL keeps equal
to the values on every write; after each write path a search through the index answers what the
per-record look-up answers. ``EXPLAIN`` shows the index answering the guard's pattern.
"""

import pytest
import test_context_read_parity
from sqlalchemy import select, text
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
from app.models import search_index
from app.models.database import ChangeSetBaseObject, RdmObject, SnapshotAttributeValue
from app.models.search_index import SEARCH_INDEXES

# The parity model's app over a migrated database.
client = test_context_read_parity.client
SEARCHES = ("note", "50%", "d_4", "t_s", '"quoted"', "Ünal", "STRAßE", "naïve", "F-", "-10", "zzz")


def _ids(client, context: dict, search: str) -> list[str]:
    return [
        item["id"]
        for item in _walk(client, f"/api/v1/objects/{ENTRY}", {**context, "search": search})
    ]


def _assert_index_answers_as_values(client, contexts: dict, monkeypatch) -> None:
    """Through the index and through every record's values, each search finds the same records."""
    indexed = {
        (name, search): _ids(client, context, search)
        for name, context in contexts.items()
        for search in SEARCHES
    }
    with monkeypatch.context() as patch:
        patch.setattr(object_query, "INDEXED_VALUE_LIMIT", -1)
        for (name, search), ids in indexed.items():
            assert _ids(client, contexts[name], search) == ids, (name, search)


@pytest.fixture
def index_reads(monkeypatch) -> list[str]:
    """The source table of every index guard a statement is built with."""
    reads: list[str] = []
    matches = search_index.SearchIndex.matches

    def recorded(index, pattern):
        reads.append(index.source)
        return matches(index, pattern)

    monkeypatch.setattr(search_index.SearchIndex, "matches", recorded)
    return reads


def test_search_answers_the_same_through_the_index_in_every_context(
    client, monkeypatch, index_reads
):
    seeded = _seed(client)
    indexed = {
        (name, search): _ids(client, context, search)
        for name, context in seeded["contexts"].items()
        for search in SEARCHES
    }
    # Every context looked values up through the index; one- and two-character searches do not.
    for name, context in seeded["contexts"].items():
        index_reads.clear()
        _ids(client, context, "note")
        assert index_reads, name
        index_reads.clear()
        _ids(client, context, "te")
        assert not index_reads, name

    # Past the limit, every record's values are looked up: the same records in the same order.
    monkeypatch.setattr(object_query, "INDEXED_VALUE_LIMIT", -1)
    for (name, search), ids in indexed.items():
        assert _ids(client, seeded["contexts"][name], search) == ids, (name, search)
    for search in SEARCHES:
        expected = indexed[("live", search)]
        assert all(indexed[(name, search)] == expected for name in seeded["contexts"]), search
    assert indexed[("live", "zzz")] == []
    assert len(indexed[("live", "F-")]) == 1  # a value match: foxtrot's code
    # Case folds beyond ASCII under the ICU root collation (PG-D11), through the index as well.
    for name, context in seeded["contexts"].items():
        assert _ids(client, context, "ünal") == indexed[(name, "Ünal")] != [], name


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


def test_every_write_path_keeps_the_indexes_equal_to_the_values(client, monkeypatch):
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
    _assert_index_answers_as_values(client, seeded["contexts"], monkeypatch)
    # Discarding a change set deletes its rows and its base's in bulk.
    overlay = seeded["overlay"]
    _ok(
        client.delete(
            f"/api/v1/change-sets/{overlay}",
            params={"expectedVersion": _change_set_version(client, overlay)},
        ),
        204,
    )
    contexts = {name: context for name, context in seeded["contexts"].items() if name != "overlay change set"}
    _assert_index_answers_as_values(client, contexts, monkeypatch)
    with get_engine().connect() as connection:
        stale = connection.scalar(
            select(SnapshotAttributeValue.sequence_id).where(
                SnapshotAttributeValue.owner_id == overlay
            )
        )
    assert stale is None


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
    snapshot = snapshot_reads._value_candidates(projection, context)("%note%", ["n"])
    return [
        select(RdmObject.id).where(object_query._live_value_candidates("%note%", ["n"])),
        select(projection.c.object_id).where(snapshot),
    ]


# Rows enough for the planner to weigh the trigram index against the value btrees, added in a
# transaction that is rolled back.
_FILL = {
    "attribute_values": (
        "INSERT INTO attribute_values (id, object_id, attribute_type_key, value_type, text_value, "
        "value_source, version) SELECT gen_random_uuid()::text, :record, 'fill-' || n, 'text', "
        "md5(n::text), 'own', 1 FROM generate_series(1, 20000) AS n"
    ),
    "snapshot_attribute_values": (
        "INSERT INTO snapshot_attribute_values (owner_kind, owner_id, object_id, "
        "attribute_type_key, value_type, text_value) SELECT 'base', 'fill', 'fill-' || n, 'n', "
        "'text', md5(n::text) FROM generate_series(1, 20000) AS n"
    ),
}


def test_the_trigram_index_answers_the_search_guard(client):
    """Each guard's pattern is read from its table's GIN trigram index, not a full scan of the
    table or of its value btree (sequential scans off: the planner may scan 20,000 rows)."""
    seeded = _seed(client)
    with get_engine().connect() as connection:
        connection.execute(text("SET LOCAL enable_seqscan = off"))
        for index in SEARCH_INDEXES:
            connection.execute(text(_FILL[index.source]), {"record": seeded["entries"][0]["id"]})
            connection.execute(text(f"ANALYZE {index.source}"))
        for statement, index in zip(_search_guards(), SEARCH_INDEXES, strict=True):
            compiled = statement.compile(connection, compile_kwargs={"render_postcompile": True})
            plan = " ".join(
                row[0]
                for row in connection.exec_driver_sql("EXPLAIN " + str(compiled), compiled.params)
            )
            assert f"Bitmap Index Scan on {index.name}" in plan, plan
        connection.rollback()
