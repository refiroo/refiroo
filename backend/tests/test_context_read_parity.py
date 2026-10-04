"""Base 0.8 S2: live, change set and history reads answer the same query with the same rows.

Change set and history reads run in SQL over base-plus-overlay projections with a typed value index,
through the same query builder as live reads. When the three contexts hold the same data, every
search, typed filter and sort must return the same records in the same order, page by page.

The generated model uses its own keys and one field of every queryable value type. The change set holds
the same data as live through a mix of base rows, identical overlay rows and tombstones, so each arm
of the change set projection is exercised.
"""

import base64
import hmac
import json
from collections.abc import Iterator
from typing import Any

import pytest
from fastapi.testclient import TestClient
from postgres_server import collated
from sqlalchemy import select

from app.config import cursor_signing_key, reload_settings
from app.db import get_engine
from app.engine.indexes.snapshot_values import value_rows
from app.engine.model.registry import model_registry
from app.main import create_app
from app.models.database import (
    ChangeSetBaseObject,
    ChangeSetObject,
    PublicationObject,
    SnapshotAttributeValue,
)

APP, FOLDER, ENTRY = "par-app", "par-folder", "par-entry"
HOLDS, CITES = "par-folder-holds-entry", "par-entry-cites-folder"
WORKSPACE = "default"
QUERYABLE = {"filterable": True, "sortable": True}
FIELDS = {
    "par-code": ("text", {**QUERYABLE, "searchable": True}),
    "par-note": ("longText", {**QUERYABLE, "searchable": True}),
    "par-count": ("integer", QUERYABLE),
    "par-amount": ("decimal", QUERYABLE),
    "par-flag": ("boolean", QUERYABLE),
    "par-due": ("date", QUERYABLE),
    "par-seen": ("dateTime", QUERYABLE),
}

# name, folder index, values (a missing key is unset; None is an explicit null)
ENTRIES: list[tuple[str, int, dict[str, Any]]] = [
    ("Alpha", 0, {"par-code": "A-1", "par-note": "first Note", "par-count": 5, "par-amount": "2.50",
                  "par-flag": True, "par-due": "2026-01-10", "par-seen": "2026-03-01T10:00:00+02:00"}),
    ("bravo", 0, {"par-code": "b-2", "par-note": None, "par-count": -3, "par-amount": "10",
                  "par-flag": False, "par-due": "2025-12-31", "par-seen": "2026-03-01T08:30:00Z"}),
    ("Charlie", 1, {"par-code": "C-3", "par-count": 40, "par-amount": "-1.5", "par-flag": True,
                    "par-due": "2026-07-01"}),
    ("delta 50%", 1, {"par-code": "D_4", "par-note": "percent_sign", "par-count": 0,
                      "par-amount": "0.000", "par-seen": "2027-01-01T00:00:00+00:00"}),
    ("Echo", 0, {"par-code": "E-5", "par-note": "echo note", "par-count": 12, "par-amount": "2.5001",
                 "par-flag": None, "par-due": None, "par-seen": "2026-03-01T09:00:00+01:00"}),
    ("foxtrot", 1, {"par-code": "F-6", "par-note": "Second NOTE", "par-count": 7,
                    "par-amount": "100", "par-flag": False, "par-due": "2026-01-11"}),
    ("Golf", 0, {"par-code": "g-7", "par-count": None, "par-amount": None, "par-flag": True,
                 "par-due": "2024-02-29", "par-seen": "2025-06-15T12:00:00-04:00"}),
    ("hotel", 1, {"par-code": "H-8", "par-note": "last", "par-count": 99, "par-amount": "3",
                  "par-due": "2026-01-09", "par-seen": None}),
    ('Ünal "quoted"', 0, {"par-code": "Ü-10", "par-note": "Straße naïve"}),
]
QUERIES: list[dict[str, str]] = [
    {"sort": "name"},
    {"sort": "-name"},
    *({"sort": direction + key} for key in FIELDS for direction in ("", "-")),
    {"search": "note"},
    {"search": "a"},
    {"search": "%"},
    {"search": "_", "sort": "name"},
    # Three or more characters read the trigram index (S8); the match is unchanged: literal % and
    # _, a quote, non-ASCII text, and ASCII case folding on names and values.
    {"search": "50%"},
    {"search": "d_4"},
    {"search": "t_s"},
    {"search": '"quoted"'},
    {"search": "Ünal"},
    {"search": "STRAßE"},
    {"search": "naïve"},
    {"search": "-5"},
    {"filter.par-count.gte": "5", "sort": "par-count"},
    {"filter.par-count.lt": "0"},
    {"filter.par-amount.gt": "2.5", "sort": "-par-amount"},
    {"filter.par-amount.eq": "2.5"},
    {"filter.par-flag.eq": "true", "sort": "name"},
    {"filter.par-flag.isNull": "true"},
    {"filter.par-flag.isUnset": "true"},
    {"filter.par-note.isNull": "false", "sort": "par-note"},
    {"filter.par-note.isUnset": "true"},
    {"filter.par-note.contains": "NOTE", "sort": "-par-note"},
    {"filter.par-code.startsWith": "c"},
    {"filter.par-due.lte": "2026-01-10", "sort": "par-due"},
    {"filter.par-seen.gt": "2026-03-01T07:00:00+00:00", "sort": "par-seen"},
    {"filter.par-seen.lt": "2026-03-01T08:30:00"},
    {"filter.name.startsWith": "d"},
    {"filter.id.isNull": "false", "sort": "-par-count"},
]


def parity_model() -> dict[str, Any]:
    def object_type(key: str, parents: list[str]) -> dict[str, Any]:
        item: dict[str, Any] = {
            "key": key,
            "name": key,
            "pluralName": f"{key}s",
            "attributes": [
                {"attributeTypeKey": field, "order": index}
                for index, field in enumerate(FIELDS)
            ],
            "features": {"rootCreatable": not parents},
        }
        if parents:
            item["behavior"] = {"parentRelationTypeKeys": parents}
        return item

    def table(key: str, object_type_key: str) -> dict[str, Any]:
        return {
            "key": key,
            "name": key,
            "type": "table",
            "objectTypeKey": object_type_key,
            "config": {
                "columns": ["name", *FIELDS],
                "filterFields": list(FIELDS),
                "sortFields": ["name", *FIELDS],
                "defaultSort": "name",
                "pageSize": 20,
            },
        }

    return {
        "schemaVersion": "0.6",
        "release": {"key": "par-model", "name": "Parity model", "version": "0.8.0-s2"},
        "product": {"name": "Parity fixture", "description": "Generated S2 parity model"},
        "attributeTypes": [
            {"key": key, "name": key, "valueType": value_type, "features": features}
            for key, (value_type, features) in FIELDS.items()
        ],
        "objectTypes": [object_type(FOLDER, []), object_type(ENTRY, [HOLDS])],
        "relationTypes": [
            {"key": HOLDS, "reverseKey": f"{HOLDS}-r", "name": HOLDS, "reverseName": HOLDS,
             "features": {"parentOf": True}},
            {"key": CITES, "reverseKey": f"{CITES}-r", "name": CITES, "reverseName": CITES,
             "features": {}},
        ],
        "objectTypeRelations": [
            {"relationTypeKey": HOLDS, "fromObjectTypeKey": FOLDER, "toObjectTypeKey": ENTRY,
             "cardinality": "one-to-many"},
            {"relationTypeKey": CITES, "fromObjectTypeKey": ENTRY, "toObjectTypeKey": FOLDER,
             "cardinality": "many-to-many"},
        ],
        "applications": [
            {
                "key": APP,
                "name": "Parity",
                "objectTypeKeys": [FOLDER, ENTRY],
                "defaultView": "folders",
                "views": [table("folders", FOLDER), table("entries", ENTRY)],
            }
        ],
    }


@pytest.fixture
def client(tmp_path, monkeypatch, migrated_database) -> Iterator[TestClient]:
    model_path = tmp_path / "parity-model.json"
    model_path.write_text(json.dumps(parity_model()))
    monkeypatch.setenv("DATABASE_URL", migrated_database("parity.db"))
    monkeypatch.setenv("RDM_MODEL_PATH", str(model_path))
    reload_settings()
    model_registry.clear()
    with TestClient(create_app()) as test_client:
        yield test_client
    get_engine().dispose()
    monkeypatch.undo()
    reload_settings()
    model_registry.clear()


def _ok(response, status: int = 200) -> dict[str, Any]:
    assert response.status_code == status, response.text
    return response.json() if response.content else {}


def _create(client, object_type: str, name: str, parent: str | None, values, **context):
    return _ok(
        client.post(
            "/api/v1/objects",
            json={
                "applicationKey": APP,
                "objectTypeKey": object_type,
                "name": name,
                "parentObjectId": parent,
                "attributes": [
                    {"attributeTypeKey": key, "value": value} for key, value in values.items()
                ],
                **context,
            },
        ),
        201,
    )


def load_change_set(client, **body) -> dict[str, Any]:
    return _ok(client.post(f"/api/v1/workspaces/{WORKSPACE}/change-sets", json=body), 201)


def _change_set_version(client, change_set_id: str) -> int:
    return _ok(client.get(f"/api/v1/change-sets/{change_set_id}"))["version"]


def _walk(client, path: str, params: dict[str, Any]) -> list[dict[str, Any]]:
    """Every item of a collection, read in pages of three through its cursors."""
    items, cursor = [], None
    while True:
        page = _ok(client.get(path, params={**params, "pageSize": 3, **({"cursor": cursor} if cursor else {})}))
        items.extend(page["items"])
        cursor = page["nextCursor"]
        if cursor is None:
            return items


def _values(item: dict[str, Any]) -> dict[str, Any]:
    return {entry["attributeTypeKey"]: entry["value"] for entry in item["attributes"]}


def _seed(client) -> dict[str, Any]:
    """Live data; a change set that reaches the same data through overlays; a publication of it."""
    live = {"workspaceKey": WORKSPACE}
    folders = [
        _create(client, FOLDER, name, None, {"par-code": code}, **live)
        for name, code in (("Folder one", "F-1"), ("folder two", "F-2"))
    ]
    entries = [
        _create(client, ENTRY, name, folders[folder]["id"], values, **live)
        for name, folder, values in ENTRIES
    ]
    doomed = _create(client, ENTRY, "Doomed", folders[0]["id"], {"par-code": "Z-9"}, **live)
    for entry in entries[:5]:
        _ok(
            client.post(
                "/api/v1/relations",
                json={"relationTypeKey": CITES, "fromObjectId": entry["id"],
                      "toObjectId": folders[1]["id"]},
            ),
            201,
        )

    # The overlay change set starts from current live data and ends equal to it: identical rewrites of
    # base rows, a change set-only record that is created and then deleted, and a tombstone for the record
    # that live deletes too.
    overlay = load_change_set(client, source="currentLive")["id"]
    for entry in entries[::2]:
        record = _ok(client.get(f"/api/v1/objects/{ENTRY}/{entry['id']}", params={"changeSetId": overlay}))
        for key, value in _values(record).items():
            record = _ok(
                client.patch(
                    f"/api/v1/objects/{ENTRY}/{entry['id']}/attributes/{key}",
                    json={"value": value, "expectedVersion": record["version"],
                          "changeSetId": overlay,
                          "expectedChangeSetVersion": _change_set_version(client, overlay)},
                )
            )
    temporary = _create(
        client, ENTRY, "Temporary", folders[1]["id"], {"par-code": "T-0"},
        changeSetId=overlay, expectedChangeSetVersion=_change_set_version(client, overlay),
    )
    for record in (temporary, doomed):
        current = _ok(client.get(f"/api/v1/objects/{ENTRY}/{record['id']}", params={"changeSetId": overlay}))
        _ok(
            client.delete(
                f"/api/v1/objects/{ENTRY}/{record['id']}",
                params={"changeSetId": overlay, "expectedVersion": current["version"],
                        "expectedChangeSetVersion": _change_set_version(client, overlay)},
            ),
            204,
        )
    _ok(
        client.delete(
            f"/api/v1/objects/{ENTRY}/{doomed['id']}",
            params={"expectedVersion": doomed["version"]},
        ),
        204,
    )

    # A publication of current live data, and a change set derived from it without edits.
    publish = load_change_set(client, source="currentLive")
    publication = _ok(
        client.post(
            f"/api/v1/change-sets/{publish['id']}/publication",
            json={"expectedChangeSetVersion": publish["version"]},
        )
    )
    derived = load_change_set(client, source="publication", derivedFromPublicationId=publication["id"])["id"]
    return {
        "folders": folders,
        "entries": entries,
        "contexts": {
            "live": live,
            "overlay change set": {"changeSetId": overlay},
            "publication change set": {"changeSetId": derived},
            "history": {"publicationId": publication["id"]},
        },
        "overlay": overlay,
    }


def _order_key(item: dict[str, Any], sort: str | None) -> Any:
    """What a sort orders by; records that tie on it may come in any order.

    Without a sort, every context lists by name (S4R4).
    """
    field = (sort or "name").removeprefix("-")
    if field == "name":
        return item["name"]
    return _values(item).get(field)


def test_live_change_set_and_history_return_the_same_rows_in_the_same_order(client):
    seeded = _seed(client)
    contexts = seeded["contexts"]
    # The overlay change set really does read through overlay rows and a base-row tombstone.
    with get_engine().connect() as connection:
        overlay_rows = connection.execute(
            select(ChangeSetObject.object_id, ChangeSetObject.is_deleted).where(
                ChangeSetObject.change_set_id == seeded["overlay"]
            )
        ).all()
    assert sum(not deleted for _id, deleted in overlay_rows) >= 4
    assert sum(deleted for _id, deleted in overlay_rows) == 2

    for query in QUERIES:
        results = {
            name: _walk(client, f"/api/v1/objects/{ENTRY}", {**context, **query})
            for name, context in contexts.items()
        }
        expected = results["live"]
        assert expected, query
        for name, items in results.items():
            label = f"{name} {query}"
            assert {item["id"] for item in items} == {item["id"] for item in expected}, label
            assert [_order_key(item, query.get("sort")) for item in items] == [
                _order_key(item, query.get("sort")) for item in expected
            ], label
            by_id = {item["id"]: item for item in items}
            for item in expected:
                assert _values(by_id[item["id"]]) == _values(item), label
                assert by_id[item["id"]]["name"] == item["name"], label
                assert by_id[item["id"]]["parentObjectId"] == item["parentObjectId"], label

    scoped = {
        name: _walk(
            client,
            f"/api/v1/objects/{ENTRY}",
            {**context, "parentObjectId": seeded["folders"][0]["id"], "sort": "-par-seen"},
        )
        for name, context in contexts.items()
    }
    for name, items in scoped.items():
        # Alpha and Echo were seen at the same instant in different offsets: a tie.
        assert {item["id"] for item in items} == {item["id"] for item in scoped["live"]}, name
        assert [_order_key(item, "-par-seen") for item in items] == [
            _order_key(item, "-par-seen") for item in scoped["live"]
        ], name
    assert "Doomed" not in {item["name"] for item in scoped["live"]}

    cited = seeded["folders"][1]["id"]
    relations = {
        name: _walk(client, "/api/v1/relations", {**context, "objectId": cited})
        for name, context in contexts.items()
    }
    expected_relations = {
        (item["relation"]["id"], item["direction"], item["object"]["id"], json.dumps(_values(item["object"]), sort_keys=True))
        for item in relations["live"]
    }
    assert len(expected_relations) == 5 + 4  # five citations, four contained entries
    for name, items in relations.items():
        assert {
            (item["relation"]["id"], item["direction"], item["object"]["id"], json.dumps(_values(item["object"]), sort_keys=True))
            for item in items
        } == expected_relations, name

    entry = seeded["entries"][0]
    live_path = _ok(client.get(f"/api/v1/objects/{ENTRY}/{entry['id']}", params=contexts["live"]))["path"]
    assert [step["id"] for step in live_path][-1] == entry["id"] and len(live_path) >= 2
    for name, context in contexts.items():
        record = _ok(client.get(f"/api/v1/objects/{ENTRY}/{entry['id']}", params=context))
        assert _values(record) == _values(entry), name
        # A single-record read carries its ancestor path in every context, as its pages do (S7).
        assert record["path"] == live_path, name
        value = _ok(client.get(f"/api/v1/objects/{ENTRY}/{entry['id']}/attributes/par-amount", params=context))
        assert value["value"] == "2.5", name


def reissue_cursor(cursor: str, **changes: Any) -> str:
    """The cursor re-signed with ``changes``, such as the ``sort`` of a former default order."""
    encoded = cursor.split(".")[0]
    body = json.loads(base64.urlsafe_b64decode(encoded + "=" * (-len(encoded) % 4)))
    payload = json.dumps({**body, **changes}, sort_keys=True, separators=(",", ":")).encode()
    signature = hmac.digest(cursor_signing_key(), payload, "sha256")
    return ".".join(
        base64.urlsafe_b64encode(part).rstrip(b"=").decode() for part in (payload, signature)
    )


def test_default_order_is_name_in_every_context(client):
    """S4R4 (D22): without a sort, live, change set and history list by name, which seek finds."""
    seeded = _seed(client)
    path = f"/api/v1/objects/{ENTRY}"
    created = [name for name, _folder, _values in ENTRIES]
    for name, context in seeded["contexts"].items():
        items = _walk(client, path, context)
        names = [item["name"] for item in items]
        # In the database's order the entries were created in name order (ICU root, PG-D11); the
        # default matches the explicit name sort below, and the former default's cursor is refused.
        assert names == collated(created), name
        by_name = _walk(client, path, {**context, "sort": "name"})
        assert [item["id"] for item in items] == [item["id"] for item in by_name], name
        sought = _ok(client.get(path, params={**context, "seek": "Echo", "pageSize": 2}))
        assert [item["name"] for item in sought["items"]] == ["Echo", "foxtrot"], name

    # A cursor issued for the former default (live creation sequence, change set and history record ID)
    # is bound to that order and refused rather than read against the new one.
    for name, context, former in (
        ("live", seeded["contexts"]["live"], "sequenceId"),
        ("change_set", seeded["contexts"]["overlay change set"], "id"),
        ("history", seeded["contexts"]["history"], "id"),
    ):
        first = _ok(client.get(path, params={**context, "pageSize": 2}))
        # Control: re-signing alone keeps a cursor valid.
        _ok(client.get(path, params={**context, "pageSize": 2, "cursor": reissue_cursor(first["nextCursor"])}))
        stale = reissue_cursor(first["nextCursor"], sort=[former], position=["1"])
        refused = client.get(path, params={**context, "pageSize": 2, "cursor": stale})
        assert refused.status_code == 422, name
        assert refused.json()["error"]["code"] == "INVALID_CURSOR", name


def test_snapshot_cursor_is_bound_to_its_context_and_query(client):
    seeded = _seed(client)
    change_set = seeded["contexts"]["overlay change set"]
    first = _ok(client.get(f"/api/v1/objects/{ENTRY}", params={**change_set, "sort": "name", "pageSize": 2}))
    assert first["nextCursor"]
    for params in (
        {**change_set, "sort": "-name"},
        {**change_set, "sort": "name", "search": "a"},
        {**seeded["contexts"]["history"], "sort": "name"},
        {**seeded["contexts"]["publication change set"], "sort": "name"},
    ):
        refused = client.get(
            f"/api/v1/objects/{ENTRY}", params={**params, "cursor": first["nextCursor"]}
        )
        assert refused.status_code == 422, params
        assert refused.json()["error"]["code"] == "INVALID_CURSOR"


def test_every_change_set_write_keeps_the_typed_value_index_equal_to_the_json(client):
    """The index is derived from each row's JSON; no write path may leave it behind."""
    seeded = _seed(client)
    overlay = seeded["overlay"]
    entry = seeded["entries"][1]
    record = _ok(client.get(f"/api/v1/objects/{ENTRY}/{entry['id']}", params={"changeSetId": overlay}))
    record = _ok(
        client.patch(
            f"/api/v1/objects/{ENTRY}/{entry['id']}",
            json={"name": "Bravo renamed", "parentObjectId": seeded["folders"][1]["id"],
                  "attributes": [{"attributeTypeKey": "par-count", "value": 8}],
                  "expectedVersion": record["version"], "changeSetId": overlay,
                  "expectedChangeSetVersion": _change_set_version(client, overlay)},
        )
    )
    _ok(
        client.delete(
            f"/api/v1/objects/{ENTRY}/{entry['id']}/attributes/par-seen",
            params={"changeSetId": overlay, "expectedVersion": record["version"],
                    "expectedChangeSetVersion": _change_set_version(client, overlay)},
        ),
        204,
    )
    listed = _walk(
        client, f"/api/v1/objects/{ENTRY}",
        {"changeSetId": overlay, "filter.par-count.eq": "8"},
    )
    assert [item["name"] for item in listed] == ["Bravo renamed"]

    value_types = {key: value_type for key, (value_type, _features) in FIELDS.items()}
    with get_engine().connect() as connection:
        indexed = {
            (row.owner_id, row.object_id, row.attribute_type_key): row
            for row in connection.execute(select(SnapshotAttributeValue))
        }
        expected: dict[tuple[str, str, str], dict[str, Any]] = {}
        for entity, kind, owner in (
            (PublicationObject, "publication", "publication_id"),
            (ChangeSetBaseObject, "base", "base_id"),
            (ChangeSetObject, "change_set", "change_set_id"),
        ):
            for row in connection.execute(select(entity)):
                if getattr(row, "is_deleted", False):
                    continue
                owner_id = getattr(row, owner)
                for value in value_rows(kind, owner_id, row.object_id, row.attributes, value_types):
                    expected[(owner_id, row.object_id, value["attribute_type_key"])] = value
    assert set(indexed) == set(expected)
    for key, value in expected.items():
        row = indexed[key]
        assert row.value_type == value["value_type"], key
        column = {
            "text": "text_value", "longText": "text_value", "integer": "integer_value",
            "decimal": "decimal_value", "boolean": "boolean_value", "date": "date_value",
            "dateTime": "datetime_value",
        }[value["value_type"]]
        assert (getattr(row, column) is None) == (value[column] is None), key
