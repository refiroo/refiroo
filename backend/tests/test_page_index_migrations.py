"""Base 0.8 S3/S4 and S4R1 index migrations: relation endpoint indexes and live object page indexes.

``20260925_02`` adds (owner, endpoint, relation ID) indexes on revision, draft-base and draft
relations; ``20260925_03`` adds name-ordered page indexes on live objects; ``20260926_01`` rebuilds
the endpoint indexes to cover the relation type and the other end. The data is written
through the API at head, the database is taken back to the S2 head (``20260925_01``), which drops
both, and is upgraded again through the FastAPI lifespan. Relation and object pages in every context
must answer as before, and an interrupted run that left some indexes behind must complete.
"""

import json

import pytest
from alembic import command
from sqlalchemy import create_engine, inspect, text
from test_context_read_parity import ENTRY, FOLDER, _seed, _walk
from test_snapshot_value_migration import _app, _config, _version

PRECEDING, HEAD = "20260925_01", "20260926_01"
TABLES = {
    "workspace_revision_relations": "revision_id",
    "workspace_draft_base_relations": "base_id",
    "workspace_draft_relations": "draft_id",
}
ENDS = (("from", "to"), ("to", "from"))
EXPECTED = {
    (
        table,
        f"ix_{table}_{end}",
        (owner, f"{end}_object_id", "relation_type_key", "relation_id", f"{other}_object_id"),
    )
    for table, owner in TABLES.items()
    for end, other in ENDS
} | {
    ("objects", "ix_objects_type_name", ("workspace_key", "object_type_key", "name", "sequence_id")),
    (
        "objects",
        "ix_objects_parent_name",
        ("workspace_key", "parent_object_id", "object_type_key", "name", "sequence_id"),
    ),
}
OBJECT_QUERIES = ({}, {"sort": "name"}, {"sort": "-name", "includeTotal": True}, {"from": "end"})
QUERIES = ({}, {"sort": "-name"}, {"search": "e"}, {"direction": "incoming"})


def _endpoint_indexes(database) -> set[tuple[str, str, tuple[str, ...]]]:
    engine = create_engine(f"sqlite:///{database}")
    try:
        inspector = inspect(engine)
        return {
            (table, index["name"], tuple(index["column_names"]))
            for table in (*TABLES, "objects")
            for index in inspector.get_indexes(table)
            if index["name"].endswith(("_from", "_to", "_name"))
            and index["name"] != "ix_objects_name"
        }
    finally:
        engine.dispose()


def _reads(client, seeded) -> dict:
    """Relation pages around each seeded record and object pages by type and by parent."""
    objects = {
        (name, object_type, json.dumps({**scope, **query}, sort_keys=True)): [
            item["id"]
            for item in _walk(client, f"/api/v1/objects/{object_type}", {**context, **scope, **query})
        ]
        for name, context in seeded["contexts"].items()
        for object_type, scope in (
            (FOLDER, {"topLevel": True}),
            (ENTRY, {}),
            (ENTRY, {"parentObjectId": seeded["folders"][0]["id"]}),
        )
        for query in OBJECT_QUERIES
    }
    return objects | {
        (name, anchor["id"], json.dumps(query, sort_keys=True)): [
            (row["relation"]["id"], row["object"]["id"], row["direction"])
            for row in _walk(client, "/api/v1/relations", {**context, "objectId": anchor["id"], **query})
        ]
        for name, context in seeded["contexts"].items()
        for anchor in (*seeded["folders"], seeded["entries"][0])
        for query in QUERIES
    }


@pytest.fixture
def seeded_database(tmp_path, monkeypatch, _migrated_template):
    """Records and relations in every context, then the indexes dropped."""
    database = tmp_path / "s4.db"
    database.write_bytes(_migrated_template.read_bytes())
    # A clean bootstrap creates the indexes.
    assert _endpoint_indexes(database) == EXPECTED
    with _app(database, monkeypatch) as client:
        seeded = _seed(client)
        reads = _reads(client, seeded)
    assert any(rows for rows in reads.values())
    command.downgrade(_config(database), PRECEDING)
    assert _endpoint_indexes(database) == set()
    return database, seeded, reads


def test_upgrade_adds_the_indexes_and_pages_answer_as_before(seeded_database, monkeypatch):
    database, seeded, reads = seeded_database
    for _start in range(2):
        with _app(database, monkeypatch) as client:
            assert client.get("/health").json() == {"status": "ok"}
            assert _reads(client, seeded) == reads
        assert _version(database) == HEAD
        assert _endpoint_indexes(database) == EXPECTED


def test_upgrade_completes_after_an_interrupted_run(seeded_database, monkeypatch):
    database, seeded, reads = seeded_database
    engine = create_engine(f"sqlite:///{database}")
    try:
        # SQLite commits DDL as it runs: a stopped upgrade can leave some indexes behind without
        # recording the new version.
        with engine.begin() as connection:
            connection.execute(
                text(
                    "CREATE INDEX ix_workspace_revision_relations_from ON "
                    "workspace_revision_relations (revision_id, from_object_id, relation_id)"
                )
            )
            # An earlier shape of the same index is rebuilt, not kept.
            connection.execute(
                text(
                    "CREATE INDEX ix_workspace_draft_relations_to ON "
                    "workspace_draft_relations (draft_id, to_object_id)"
                )
            )
            connection.execute(
                text("CREATE INDEX ix_objects_type_name ON objects (workspace_key, object_type_key)")
            )
    finally:
        engine.dispose()
    assert _version(database) == PRECEDING
    with _app(database, monkeypatch) as client:
        assert client.get("/health").json() == {"status": "ok"}
        assert _reads(client, seeded) == reads
    assert _version(database) == HEAD
    assert _endpoint_indexes(database) == EXPECTED


def test_downgrade_restores_the_s4_endpoint_indexes(seeded_database, monkeypatch):
    database, seeded, reads = seeded_database
    with _app(database, monkeypatch) as client:
        assert _reads(client, seeded) == reads
    command.downgrade(_config(database), "20260925_03")
    s4 = {
        (table, f"ix_{table}_{end}", (owner, f"{end}_object_id", "relation_id"))
        for table, owner in TABLES.items()
        for end, _other in ENDS
    }
    assert _endpoint_indexes(database) == s4 | {item for item in EXPECTED if item[0] == "objects"}
