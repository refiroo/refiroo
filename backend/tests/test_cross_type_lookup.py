"""Base 0.9 Q1: ``GET /objects`` lists records of any type in live, change set and publication contexts.

The lookup answers through the per-type list's builders, so the same query gives the same records
in the same order in every context (the S2 parity rule), and an item has the per-type list's shape.
It filters and sorts by built-in fields only and refuses a model-declared field with the route that
answers it. Every test runs on the generated parity model and on a copy with every key renamed, so
no behaviour can depend on a key.
"""

import json
from collections.abc import Callable, Iterator
from typing import Any

import pytest
from harness_identity import TestClient
from model_support import renamed_model
from postgres_server import collated
from test_context_read_parity import APP, CITES, ENTRY, FOLDER, parity_model

from app.config import reload_settings
from app.db import get_engine
from app.engine.model.registry import model_registry
from app.main import create_app

LOOKUP = "/api/v1/objects"
WORKSPACE = "default"
OTHER_APP = "par-other-app"


@pytest.fixture(params=["generated", "renamed"])
def lookup(request, tmp_path, monkeypatch, migrated_database) -> Iterator[tuple[TestClient, Callable[[str], str]]]:
    source = parity_model()
    # A second application holding only folders, so a type outside an application can be named.
    other = {**source["applications"][0], "key": OTHER_APP, "name": "Other", "objectTypeKeys": [FOLDER]}
    other["views"] = [view for view in other["views"] if view["objectTypeKey"] == FOLDER]
    other["defaultView"] = other["views"][0]["key"]
    source["applications"].append(other)
    names: dict[str, str] = {}
    if request.param == "renamed":
        source, names = renamed_model(source)
    model_path = tmp_path / "lookup-model.json"
    model_path.write_text(json.dumps(source))
    monkeypatch.setenv("DATABASE_URL", migrated_database("lookup.db"))
    monkeypatch.setenv("RDM_MODEL_PATH", str(model_path))
    reload_settings()
    model_registry.clear()
    with TestClient(create_app()) as client:
        yield client, lambda key: names.get(key, key)
    get_engine().dispose()
    monkeypatch.undo()
    reload_settings()
    model_registry.clear()


def _ok(response, status: int = 200) -> dict[str, Any]:
    assert response.status_code == status, response.text
    return response.json() if response.content else {}


def _refused(response, status: int, code: str) -> dict[str, Any]:
    assert response.status_code == status, response.text
    error = response.json()["error"]
    assert error["code"] == code, error
    return error


def _walk(client, path: str, params: dict[str, Any]) -> list[dict[str, Any]]:
    """Every item of a collection, read in pages of two through its cursors."""
    items, cursor = [], None
    while True:
        page = _ok(client.get(path, params={**params, "pageSize": 2, **({"cursor": cursor} if cursor else {})}))
        items.extend(page["items"])
        cursor = page["nextCursor"]
        if cursor is None:
            return items


def _change_set_version(client, change_set_id: str) -> int:
    return _ok(client.get(f"/api/v1/change-sets/{change_set_id}"))["version"]


def _seed(client, k: Callable[[str], str]) -> dict[str, Any]:
    """Live data; a change set reaching the same data through overlay rows and a tombstone; a
    publication of it and a change set derived from that publication."""

    def create(object_type: str, name: str, parent: str | None, code: str, **context) -> dict[str, Any]:
        return _ok(
            client.post(
                "/api/v1/objects",
                json={
                    "applicationKey": k(APP),
                    "objectTypeKey": k(object_type),
                    "name": name,
                    "parentObjectId": parent,
                    "attributes": [{"attributeTypeKey": k("par-code"), "value": code}],
                    **context,
                },
            ),
            201,
        )

    live = {"workspaceKey": WORKSPACE}
    folders = [create(FOLDER, name, None, code, **live) for name, code in (("Folder one", "F-1"), ("folder two", "F-2"))]
    entries = [
        create(ENTRY, name, folders[folder]["id"], code, **live)
        for name, folder, code in (
            ("Alpha", 0, "A-1"),
            ("bravo", 0, "B-2"),
            ("Charlie", 1, "C-3"),
            ("delta 50%", 1, "D_4"),
            ("Echo", 0, "E-5"),
            ("Folder three", 1, "X-6"),
        )
    ]
    doomed = create(ENTRY, "Doomed", folders[0]["id"], "Z-9", **live)
    _ok(
        client.post(
            "/api/v1/relations",
            json={"relationTypeKey": k(CITES), "fromObjectId": entries[0]["id"], "toObjectId": folders[1]["id"]},
        ),
        201,
    )

    def change_set(**body) -> dict[str, Any]:
        return _ok(client.post(f"/api/v1/workspaces/{WORKSPACE}/change-sets", json=body), 201)

    overlay = change_set(source="currentLive")["id"]
    for record in (*entries[::2], folders[1]):
        current = _ok(client.get(f"/api/v1/objects/{record['objectTypeKey']}/{record['id']}", params={"changeSetId": overlay}))
        _ok(
            client.patch(
                f"/api/v1/objects/{record['objectTypeKey']}/{record['id']}/attributes/{k('par-code')}",
                json={
                    "value": current["attributes"][0]["value"],
                    "expectedVersion": current["version"],
                    "changeSetId": overlay,
                    "expectedChangeSetVersion": _change_set_version(client, overlay),
                },
            )
        )
    temporary = create(
        FOLDER, "Temporary", None, "T-0",
        changeSetId=overlay, expectedChangeSetVersion=_change_set_version(client, overlay),
    )
    for record in (temporary, doomed):
        current = _ok(client.get(f"/api/v1/objects/{record['objectTypeKey']}/{record['id']}", params={"changeSetId": overlay}))
        _ok(
            client.delete(
                f"/api/v1/objects/{record['objectTypeKey']}/{record['id']}",
                params={
                    "changeSetId": overlay,
                    "expectedVersion": current["version"],
                    "expectedChangeSetVersion": _change_set_version(client, overlay),
                },
            ),
            204,
        )
    _ok(client.delete(f"/api/v1/objects/{k(ENTRY)}/{doomed['id']}", params={"expectedVersion": doomed["version"]}), 204)

    publish = change_set(source="currentLive")
    publication = _ok(
        client.post(
            f"/api/v1/change-sets/{publish['id']}/publication",
            json={"expectedChangeSetVersion": publish["version"]},
        )
    )
    derived = change_set(source="publication", derivedFromPublicationId=publication["id"])["id"]
    return {
        "folders": folders,
        "entries": entries,
        "contexts": {
            "live": live,
            "overlay change set": {"changeSetId": overlay},
            "publication change set": {"changeSetId": derived},
            "publication": {"publicationId": publication["id"]},
        },
    }


def _identity(item: dict[str, Any]) -> tuple[Any, ...]:
    """What every context must agree on; versions, timestamps and value IDs are the context's own."""
    return (
        item["id"],
        item["name"],
        item["objectTypeKey"],
        item["applicationKey"],
        item["parentObjectId"],
        json.dumps({value["attributeTypeKey"]: value["value"] for value in item["attributes"]}, sort_keys=True),
        json.dumps(item["path"], sort_keys=True),
    )


def test_the_same_query_lists_the_same_records_in_every_context(lookup):
    client, k = lookup
    seeded = _seed(client, k)
    folder_one = seeded["folders"][0]["id"]
    alpha = seeded["entries"][0]["id"]
    queries: list[dict[str, Any]] = [
        {},
        {"sort": "-name"},
        {"sort": "id"},
        {"sort": "-id"},
        {"sort": "objectType"},
        {"sort": "-objectType"},
        {"search": "o"},
        {"search": "FOLDER"},
        {"search": "50%"},
        {"objectTypeKey": k(FOLDER)},
        {"objectTypeKey": [k(ENTRY), k(FOLDER)], "sort": "-name"},
        {"applicationKey": k(APP), "sort": "objectType"},
        {"topLevel": True},
        {"parentObjectId": folder_one},
        {"filter.objectTypeKey.eq": k(ENTRY)},
        {"filter.objectTypeKey.startsWith": k(FOLDER)[:-3]},
        {"filter.parentObjectId.isNull": "true"},
        {"filter.parentObjectId.eq": folder_one, "sort": "-id"},
        {"filter.name.startsWith": "f"},
        {"filter.name.contains": "O", "filter.objectTypeKey.eq": k(FOLDER)},
        {"filter.id.eq": [alpha, folder_one]},
    ]
    for query in queries:
        results = {name: _walk(client, LOOKUP, {**context, **query}) for name, context in seeded["contexts"].items()}
        expected = [_identity(item) for item in results["live"]]
        assert expected, query
        for name, items in results.items():
            assert [_identity(item) for item in items] == expected, f"{name} {query}"

    everything = _walk(client, LOOKUP, seeded["contexts"]["live"])
    assert {item["objectTypeKey"] for item in everything} == {k(FOLDER), k(ENTRY)}
    assert "Doomed" not in {item["name"] for item in everything}
    assert [item["name"] for item in everything] == collated(item["name"] for item in everything)
    # Type names order objectType; the name orders records of one type.
    type_names = {item["key"]: item["name"] for item in _ok(client.get("/api/v1/model"))["objectTypes"]}
    by_type = _walk(client, LOOKUP, {**seeded["contexts"]["live"], "sort": "objectType"})
    order = [(type_names[item["objectTypeKey"]], item["name"]) for item in by_type]
    assert order == collated(order) and len(order) == len(everything)
    # A search matches both types; "FOLDER" finds the folders and an entry named "Folder three".
    found = _walk(client, LOOKUP, {**seeded["contexts"]["live"], "search": "FOLDER"})
    assert {item["objectTypeKey"] for item in found} == {k(FOLDER), k(ENTRY)}


def test_an_item_has_the_per_type_list_shape(lookup):
    client, k = lookup
    seeded = _seed(client, k)
    for name, context in seeded["contexts"].items():
        for object_type in (FOLDER, ENTRY):
            listed = _walk(client, f"{LOOKUP}/{k(object_type)}", {**context, "sort": "name"})
            looked_up = _walk(client, LOOKUP, {**context, "objectTypeKey": k(object_type)})
            # Plus the release each item was read under (0.11 M4, D43).
            assert all(item.pop("modelReleaseId") for item in looked_up), f"{name} {object_type}"
            assert looked_up == listed, f"{name} {object_type}"


def test_search_matches_the_name_only(lookup):
    client, k = lookup
    seeded = _seed(client, k)
    for name, context in seeded["contexts"].items():
        # A-1 is Alpha's searchable code: the per-type list finds it, the lookup does not.
        assert [item["name"] for item in _walk(client, f"{LOOKUP}/{k(ENTRY)}", {**context, "search": "A-1"})] == ["Alpha"], name
        assert _walk(client, LOOKUP, {**context, "search": "A-1"}) == [], name
        assert [item["name"] for item in _walk(client, LOOKUP, {**context, "search": "alp"})] == ["Alpha"], name


def test_timestamps_filter_and_sort_live_and_are_refused_where_unrecorded(lookup):
    client, k = lookup
    seeded = _seed(client, k)
    live = seeded["contexts"]["live"]
    created = _walk(client, LOOKUP, {**live, "sort": "createdAt"})
    stamps = [item["createdAt"] for item in created]
    assert stamps == sorted(stamps) and len(created) == 8
    assert [item["id"] for item in _walk(client, LOOKUP, {**live, "sort": "-updatedAt"})] != []
    since = _walk(client, LOOKUP, {**live, "filter.createdAt.gte": stamps[2], "sort": "createdAt"})
    assert [item["id"] for item in since] == [item["id"] for item in created if item["createdAt"] >= stamps[2]]
    # A day for a date-time field is that whole day in UTC (0.9 R-F6): the records were made today.
    today = stamps[0][:10]
    on_the_day = _walk(client, LOOKUP, {**live, "filter.createdAt.eq": today, "sort": "createdAt"})
    assert [item["id"] for item in on_the_day] == [item["id"] for item in created]
    assert _walk(client, LOOKUP, {**live, "filter.createdAt.lt": today}) == []
    assert len(_walk(client, LOOKUP, {**live, "filter.createdAt.lte": today})) == 8
    assert _walk(client, LOOKUP, {**live, "filter.createdAt.gt": today}) == []
    for name, context in seeded["contexts"].items():
        if name == "live":
            continue
        _refused(client.get(LOOKUP, params={**context, "sort": "createdAt"}), 422, "INVALID_SORT")
        _refused(client.get(LOOKUP, params={**context, "filter.updatedAt.lt": stamps[0]}), 422, "INVALID_FILTER")


def test_model_declared_fields_and_bad_scopes_are_refused(lookup):
    client, k = lookup
    seeded = _seed(client, k)
    for name, context in seeded["contexts"].items():
        error = _refused(client.get(LOOKUP, params={**context, f"filter.{k('par-code')}.eq": "A-1"}), 422, "INVALID_FILTER")
        assert error["details"]["route"] == "GET /api/v1/objects/{objectTypeKey}", name
        assert error["details"]["path"] == f"/query/filter.{k('par-code')}.eq"
        assert "GET /api/v1/objects/{objectTypeKey}" in error["message"]
        for sort in (k("par-count"), f"ancestor:{k(FOLDER)}", "objectTypeKey", "parentObjectId", "sequenceId", "-relationship"):
            error = _refused(client.get(LOOKUP, params={**context, "sort": sort}), 422, "INVALID_SORT")
            assert error["details"]["route"] == "GET /api/v1/objects/{objectTypeKey}", (name, sort)
        _refused(client.get(LOOKUP, params={**context, "filter.sequenceId.eq": "1"}), 422, "INVALID_FILTER")
        _refused(client.get(LOOKUP, params={**context, "filter.name.lt": "b"}), 422, "INVALID_FILTER")
        _refused(client.get(LOOKUP, params={**context, "objectTypeKey": "no-such-type"}), 404, "UNKNOWN_OBJECT_TYPE")
        _refused(client.get(LOOKUP, params={**context, "applicationKey": "no-such-app"}), 404, "UNKNOWN_APPLICATION")
        _refused(
            client.get(LOOKUP, params={**context, "topLevel": True, "parentObjectId": seeded["folders"][0]["id"]}),
            422,
            "MUTUALLY_EXCLUSIVE_SCOPE",
        )
    contexts = seeded["contexts"]
    _refused(
        client.get(LOOKUP, params={**contexts["overlay change set"], **contexts["publication"]}),
        422,
        "MUTUALLY_EXCLUSIVE_CONTEXT",
    )


def test_application_narrows_to_its_records_and_types(lookup):
    client, k = lookup
    seeded = _seed(client, k)
    other = _ok(
        client.post(
            "/api/v1/objects",
            json={"workspaceKey": WORKSPACE, "applicationKey": k(OTHER_APP), "objectTypeKey": k(FOLDER), "name": "Other folder"},
        ),
        201,
    )
    live = seeded["contexts"]["live"]
    assert [item["id"] for item in _walk(client, LOOKUP, {**live, "applicationKey": k(OTHER_APP)})] == [other["id"]]
    assert len(_walk(client, LOOKUP, {**live, "applicationKey": k(APP), "objectTypeKey": [k(FOLDER), k(ENTRY)]})) == 8
    error = _refused(
        client.get(LOOKUP, params={**live, "applicationKey": k(OTHER_APP), "objectTypeKey": [k(FOLDER), k(ENTRY)]}),
        422,
        "INVALID_OBJECT_TYPE_FOR_APPLICATION",
    )
    assert k(ENTRY) in error["message"]


def test_cursors_are_bound_to_the_lookup_its_context_and_its_query(lookup):
    client, k = lookup
    seeded = _seed(client, k)
    contexts = seeded["contexts"]
    for name, context in contexts.items():
        base = {"objectTypeKey": [k(FOLDER), k(ENTRY)], "pageSize": 2}
        query = {**context, **base}
        first = _ok(client.get(LOOKUP, params=query))
        cursor = first["nextCursor"]
        # The type set is bound, not the order it was named in.
        again = _ok(client.get(LOOKUP, params={**query, "objectTypeKey": [k(ENTRY), k(FOLDER), k(ENTRY)], "cursor": cursor}))
        assert again["items"] == _ok(client.get(LOOKUP, params={**query, "cursor": cursor}))["items"], name
        for changed in (
            {"objectTypeKey": k(ENTRY)},
            {"objectTypeKey": []},
            {"sort": "-name"},
            {"search": "a"},
            {"filter.name.startsWith": "a"},
        ):
            _refused(client.get(LOOKUP, params={**query, **changed, "cursor": cursor}), 422, "INVALID_CURSOR")
        # Neither list accepts the other's cursor.
        per_type = _ok(client.get(f"{LOOKUP}/{k(ENTRY)}", params={**context, "pageSize": 2}))["nextCursor"]
        _refused(client.get(LOOKUP, params={**context, "objectTypeKey": k(ENTRY), "pageSize": 2, "cursor": per_type}), 422, "INVALID_CURSOR")
        mine = _ok(client.get(LOOKUP, params={**context, "objectTypeKey": k(ENTRY), "pageSize": 2}))["nextCursor"]
        _refused(client.get(f"{LOOKUP}/{k(ENTRY)}", params={**context, "pageSize": 2, "cursor": mine}), 422, "INVALID_CURSOR")
        for other_name, other in contexts.items():
            if other_name != name:
                _refused(client.get(LOOKUP, params={**other, **base, "cursor": cursor}), 422, "INVALID_CURSOR")


def test_positions_seek_end_and_totals_agree_in_every_context(lookup):
    client, k = lookup
    seeded = _seed(client, k)
    for name, context in seeded["contexts"].items():
        for query in ({}, {"sort": "-objectType"}, {"objectTypeKey": k(ENTRY), "sort": "-id"}):
            params = {**context, **query}
            whole = _walk(client, LOOKUP, params)
            total = _ok(client.get(LOOKUP, params={**params, "pageSize": 2, "includeTotal": True}))
            assert total["totalCount"] == len(whole) and total["startIndex"] == 0, (name, query)
            for position in (1, 3, len(whole) - 1):
                page = _ok(client.get(LOOKUP, params={**params, "pageSize": 2, "position": position, "includeTotal": True}))
                assert [item["id"] for item in page["items"]] == [item["id"] for item in whole[position : position + 2]], (name, query, position)
                assert page["startIndex"] == position
            end = _ok(client.get(LOOKUP, params={**params, "pageSize": 3, "from": "end"}))
            assert [item["id"] for item in end["items"]] == [item["id"] for item in whole[-3:]], (name, query)
            backward = _ok(client.get(LOOKUP, params={**params, "pageSize": 3, "cursor": end["prevCursor"]}))
            assert [item["id"] for item in backward["items"]] == [item["id"] for item in whole[-6:-3]], (name, query)
        sought = _ok(client.get(LOOKUP, params={**context, "seek": "Echo", "pageSize": 2}))
        assert [item["name"] for item in sought["items"]] == ["Echo", "Folder one"], name
