"""Base 0.9 Q3: ``POST /workspaces/{key}/queries/objects``, the model-aware query.

A criterion the object list can express selects the same records in the same order through the
query and through the list, in live, change set and publication contexts. The query adds
``ancestor:<type>`` by ID and one relation hop, ``select`` and ``expand`` (D17), and refuses a name
the model does not give the queried type as ``INVALID_QUERY`` at its JSON pointer (D19). Every test
runs on a generated model and on a copy with every key renamed, so no behaviour depends on a key.
"""

import json
from collections.abc import Callable, Iterator
from typing import Any

import pytest
from harness_identity import TestClient
from model_support import renamed_model
from test_context_read_parity import CITES, ENTRIES, ENTRY, FIELDS, FOLDER, QUERIES, parity_model

from app.config import reload_settings
from app.db import get_engine
from app.engine.model.registry import model_registry
from app.main import create_app

WORKSPACE = "default"
QUERY = f"/api/v1/workspaces/{WORKSPACE}/queries/objects"
NESTS = "par-folder-nests-folder"
TAG = "par-tag"
TAGGED = "par-entry-tagged-tag"
COLOUR = "par-colour"
APP = "par-app"

Keys = Callable[[str], str]


def query_model() -> dict[str, Any]:
    """The parity model with folders that nest and a tag type binding none of the entry's fields."""
    source = parity_model()
    folder = next(item for item in source["objectTypes"] if item["key"] == FOLDER)
    folder["behavior"] = {"parentRelationTypeKeys": [NESTS]}
    source["attributeTypes"].append(
        {"key": COLOUR, "name": COLOUR, "valueType": "text", "features": {"filterable": True}}
    )
    source["objectTypes"].append(
        {
            "key": TAG,
            "name": TAG,
            "pluralName": f"{TAG}s",
            "attributes": [{"attributeTypeKey": COLOUR, "order": 0}],
            "features": {"rootCreatable": True},
        }
    )
    source["relationTypes"] += [
        {
            "key": NESTS,
            "reverseKey": f"{NESTS}-r",
            "name": NESTS,
            "reverseName": NESTS,
            "features": {"parentOf": True, "hierarchical": True},
        },
        {
            "key": TAGGED,
            "reverseKey": f"{TAGGED}-r",
            "name": TAGGED,
            "reverseName": TAGGED,
            "features": {},
        },
    ]
    source["objectTypeRelations"] += [
        {
            "relationTypeKey": NESTS,
            "fromObjectTypeKey": FOLDER,
            "toObjectTypeKey": FOLDER,
            "cardinality": "one-to-many",
        },
        {
            "relationTypeKey": TAGGED,
            "fromObjectTypeKey": ENTRY,
            "toObjectTypeKey": TAG,
            "cardinality": "many-to-many",
        },
    ]
    application = source["applications"][0]
    application["objectTypeKeys"].append(TAG)
    application["views"].append(
        {
            "key": "tags",
            "name": "tags",
            "type": "table",
            "objectTypeKey": TAG,
            "config": {
                "columns": ["name", COLOUR],
                "filterFields": [COLOUR],
                "sortFields": ["name"],
                "defaultSort": "name",
                "pageSize": 20,
            },
        }
    )
    return source


@pytest.fixture(params=["generated", "renamed"])
def query(request, tmp_path, monkeypatch, migrated_database) -> Iterator[tuple[TestClient, Keys]]:
    source = query_model()
    names: dict[str, str] = {}
    if request.param == "renamed":
        source, names = renamed_model(source)
    model_path = tmp_path / "query-model.json"
    model_path.write_text(json.dumps(source))
    monkeypatch.setenv("DATABASE_URL", migrated_database("query.db"))
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


def _refused(response, code: str, path: str | None = None, status: int = 422) -> dict[str, Any]:
    assert response.status_code == status, response.text
    error = response.json()["error"]
    assert error["code"] == code, error
    if path is not None:
        assert error["details"]["path"] == path, error
    return error


def _walk_list(client, path: str, params: dict[str, Any]) -> list[dict[str, Any]]:
    items, cursor = [], None
    while True:
        page = _ok(
            client.get(
                path, params={**params, "pageSize": 3, **({"cursor": cursor} if cursor else {})}
            )
        )
        items.extend(page["items"])
        cursor = page["nextCursor"]
        if cursor is None:
            return items


def _walk(client, body: dict[str, Any]) -> list[dict[str, Any]]:
    """Every item of the query, read in pages of three through its cursors."""
    items, cursor = [], None
    while True:
        page = _ok(
            client.post(
                QUERY, json={**body, "pageSize": 3, **({"cursor": cursor} if cursor else {})}
            )
        )
        items.extend(page["items"])
        cursor = page["nextCursor"]
        if cursor is None:
            return items


def _ids(items: list[dict[str, Any]]) -> list[str]:
    return [item["id"] for item in items]


def _version(client, change_set_id: str) -> int:
    return _ok(client.get(f"/api/v1/change-sets/{change_set_id}"))["version"]


def _seed(client, k: Keys) -> dict[str, Any]:
    """Live data under nested folders with citations and tags; a change set that edits it; and a
    publication of live data taken before the change set's edits."""

    def create(object_type: str, name: str, parent: str | None, values: dict[str, Any], **context):
        return _ok(
            client.post(
                "/api/v1/objects",
                json={
                    "applicationKey": k(APP),
                    "objectTypeKey": k(object_type),
                    "name": name,
                    "parentObjectId": parent,
                    "attributes": [
                        {"attributeTypeKey": k(key), "value": value}
                        for key, value in values.items()
                    ],
                    **context,
                },
            ),
            201,
        )

    def relate(relation: str, source: str, target: str, **context) -> dict[str, Any]:
        return _ok(
            client.post(
                "/api/v1/relations",
                json={
                    "relationTypeKey": k(relation),
                    "fromObjectId": source,
                    "toObjectId": target,
                    **context,
                },
            ),
            201,
        )

    live = {"workspaceKey": WORKSPACE}
    top = create(FOLDER, "Top", None, {"par-code": "F-1"}, **live)
    sub = create(FOLDER, "Sub", top["id"], {"par-code": "F-2"}, **live)
    other = create(FOLDER, "Other", None, {"par-code": "F-3"}, **live)
    # Entries of folder 0 sit in Sub, two levels under Top; entries of folder 1 in Other.
    entries = [
        create(ENTRY, name, (sub, other)[folder]["id"], values, **live)
        for name, folder, values in ENTRIES
    ]
    direct = create(ENTRY, "Direct", top["id"], {"par-code": "Q-1"}, **live)
    red = create(TAG, "Red", None, {COLOUR: "red"}, **live)
    blue = create(TAG, "Blue", None, {COLOUR: "blue"}, **live)
    for entry in entries[:5]:
        relate(CITES, entry["id"], other["id"])
    relate(CITES, entries[5]["id"], top["id"])
    relate(TAGGED, entries[0]["id"], red["id"])
    relate(TAGGED, entries[2]["id"], red["id"])
    relate(TAGGED, entries[1]["id"], blue["id"])

    publish = _ok(
        client.post(f"/api/v1/workspaces/{WORKSPACE}/change-sets", json={"source": "currentLive"}),
        201,
    )
    publication = _ok(
        client.post(
            f"/api/v1/change-sets/{publish['id']}/publication",
            json={"expectedChangeSetVersion": publish["version"]},
        )
    )

    # The change set tags Echo red, removes Alpha's tag and deletes Charlie.
    change_set = _ok(
        client.post(f"/api/v1/workspaces/{WORKSPACE}/change-sets", json={"source": "currentLive"}),
        201,
    )["id"]
    relate(
        TAGGED,
        entries[4]["id"],
        red["id"],
        changeSetId=change_set,
        expectedChangeSetVersion=_version(client, change_set),
    )
    alpha_tags = _ok(
        client.get(
            "/api/v1/relations",
            params={
                "objectId": entries[0]["id"],
                "changeSetId": change_set,
                "relationTypeKey": k(TAGGED),
            },
        )
    )["items"]
    _ok(
        client.delete(
            f"/api/v1/relations/{alpha_tags[0]['relation']['id']}",
            params={
                "changeSetId": change_set,
                "expectedVersion": alpha_tags[0]["relation"]["version"],
                "expectedChangeSetVersion": _version(client, change_set),
            },
        ),
        204,
    )
    charlie = _ok(
        client.get(
            f"/api/v1/objects/{k(ENTRY)}/{entries[2]['id']}", params={"changeSetId": change_set}
        )
    )
    deletion = {
        "changeSetId": change_set,
        "expectedVersion": charlie["version"],
        "expectedChangeSetVersion": _version(client, change_set),
    }
    path = f"/api/v1/objects/{k(ENTRY)}/{entries[2]['id']}"
    preview = client.delete(path, params=deletion)
    assert preview.status_code == 409, preview.text
    token = preview.json()["error"]["details"]["deletionPreviewToken"]
    _ok(
        client.delete(path, params={**deletion, "cascade": True, "deletionPreviewToken": token}),
        204,
    )
    return {
        "top": top,
        "sub": sub,
        "other": other,
        "entries": entries,
        "direct": direct,
        "red": red,
        "blue": blue,
        "contexts": {
            "live": ({"workspaceKey": WORKSPACE}, {}),
            "change set": ({"changeSetId": change_set}, {"changeSetId": change_set}),
            "publication": (
                {"publicationId": publication["id"]},
                {"publicationId": publication["id"]},
            ),
        },
    }


def _typed(field: str, operator: str, lexical: str) -> Any:
    """A list filter's lexical value as the query's JSON value."""
    if operator in {"isNull", "isUnset"}:
        return lexical == "true"
    value_type = FIELDS[field][0] if field in FIELDS else "text"
    if value_type == "integer":
        return int(lexical)
    if value_type == "decimal":
        return float(lexical)
    if value_type == "boolean":
        return lexical == "true"
    return lexical


def _as_query(
    k: Keys, params: dict[str, str]
) -> tuple[list[dict[str, Any]], str | None, dict[str, str]]:
    """A parity list query as query criteria and sort, and as the list's parameters with renamed keys."""
    where, list_params, sort = [], {}, params.get("sort")
    for key, lexical in params.items():
        if not key.startswith("filter."):
            continue
        field, operator = key.removeprefix("filter.").rsplit(".", 1)
        where.append({"field": k(field), "op": operator, "value": _typed(field, operator, lexical)})
        list_params[f"filter.{k(field)}.{operator}"] = lexical
    if sort is not None:
        descending = sort.startswith("-")
        sort = ("-" if descending else "") + k(sort.removeprefix("-"))
        list_params["sort"] = sort
    return where, sort, list_params


def test_every_list_criterion_selects_the_list_records_in_every_context(query):
    client, k = query
    seeded = _seed(client, k)
    list_path = f"/api/v1/objects/{k(ENTRY)}"
    checked = 0
    for params in QUERIES:
        if "search" in params:
            continue  # search is the list's; the query has criteria
        where, sort, list_params = _as_query(k, params)
        for name, (list_context, query_context) in seeded["contexts"].items():
            expected = _walk_list(client, list_path, {**list_context, **list_params})
            body = {"objectTypeKey": k(ENTRY), "context": query_context, "where": where}
            if sort is not None:
                body["sort"] = sort
            items = _walk(client, body)
            assert _ids(items) == _ids(expected), f"{name} {params}"
            assert items == expected, f"{name} {params}"
            checked += 1
    assert checked == 3 * len([params for params in QUERIES if "search" not in params]) > 90
    # A decimal may also be given as a string, and a built-in timestamp filters live.
    decimal = _walk(
        client,
        {
            "objectTypeKey": k(ENTRY),
            "where": [{"field": k("par-amount"), "op": "eq", "value": "2.50"}],
        },
    )
    assert [item["name"] for item in decimal] == ["Alpha"]
    everything = _walk(
        client,
        {
            "objectTypeKey": k(ENTRY),
            "where": [{"field": "createdAt", "op": "gte", "value": "2000-01-01T00:00:00Z"}],
        },
    )
    assert len(everything) == len(ENTRIES) + 1


def test_ancestor_criterion_reads_the_containment_path(query):
    client, k = query
    seeded = _seed(client, k)
    in_sub = {
        entry["id"]
        for entry, (_name, folder, _v) in zip(seeded["entries"], ENTRIES, strict=True)
        if folder == 0
    }
    in_other = {
        entry["id"]
        for entry, (_name, folder, _v) in zip(seeded["entries"], ENTRIES, strict=True)
        if folder == 1
    }

    def under(
        ancestor: dict[str, Any], context: dict[str, Any], object_type: str = ENTRY
    ) -> set[str]:
        criterion = {"field": f"ancestor:{k(FOLDER)}", "op": "eq", "value": ancestor["id"]}
        return set(
            _ids(
                _walk(
                    client,
                    {"objectTypeKey": k(object_type), "context": context, "where": [criterion]},
                )
            )
        )

    charlie = seeded["entries"][2]["id"]
    for name, (_list_context, context) in seeded["contexts"].items():
        deleted = {charlie} if name == "change set" else set()
        # Any ancestor of the type counts: Top holds Sub's entries two levels down and one directly.
        assert under(seeded["top"], context) == (in_sub | {seeded["direct"]["id"]}) - deleted, name
        assert under(seeded["sub"], context) == in_sub - deleted, name
        assert under(seeded["other"], context) == in_other - deleted, name
        # A folder is not its own ancestor; one of another type or an unknown ID matches nothing.
        assert under(seeded["top"], context, FOLDER) == {seeded["sub"]["id"]}, name
        assert under(seeded["entries"][0], context) == set(), name
        assert under({"id": "00000000-0000-4000-8000-000000000000"}, context) == set(), name
    # Combined with a field criterion and a sort, as the list combines its own.
    items = _walk(
        client,
        {
            "objectTypeKey": k(ENTRY),
            "where": [
                {"field": f"ancestor:{k(FOLDER)}", "op": "eq", "value": seeded["top"]["id"]},
                {"field": k("par-flag"), "op": "eq", "value": True},
            ],
            "sort": f"-{k('par-due')}",
        },
    )
    assert [item["name"] for item in items] == ["Alpha", "Golf"]

    base = {"objectTypeKey": k(ENTRY)}
    ancestor = f"ancestor:{k(FOLDER)}"
    for criterion, path in (
        ({"field": f"ancestor:{k(ENTRY)}", "op": "eq", "value": "x"}, "/where/0/field"),
        ({"field": f"ancestor:{k(TAG)}", "op": "eq", "value": "x"}, "/where/0/field"),
        ({"field": ancestor, "op": "contains", "value": "x"}, "/where/0/op"),
        ({"field": ancestor, "op": "eq", "value": 5}, "/where/0/value"),
        ({"field": ancestor, "op": "eq", "value": "x", "not": True}, "/where/0/not"),
    ):
        _refused(client.post(QUERY, json={**base, "where": [criterion]}), "INVALID_QUERY", path)


def test_one_relation_hop_in_both_directions_and_inverted(query):
    client, k = query
    seeded = _seed(client, k)
    names = [name for name, _folder, _values in ENTRIES]
    citing_other = set(names[:5])

    def names_of(body: dict[str, Any]) -> set[str]:
        return {item["name"] for item in _walk(client, body)}

    def cites(where: list[dict[str, Any]], **extra) -> dict[str, Any]:
        return {
            "related": {"relationTypeKey": k(CITES), "direction": "outgoing", "where": where},
            **extra,
        }

    def tagged(where: list[dict[str, Any]], **extra) -> dict[str, Any]:
        return {
            "related": {"relationTypeKey": k(TAGGED), "direction": "outgoing", "where": where},
            **extra,
        }

    all_entries = set(names) | {"Direct"}
    for name, (_list_context, context) in seeded["contexts"].items():
        body = {"objectTypeKey": k(ENTRY), "context": context}
        deleted = {"Charlie"} if name == "change set" else set()
        # Outgoing, on the other end's built-in field and on its attribute.
        assert (
            names_of(
                {**body, "where": [cites([{"field": "name", "op": "startsWith", "value": "Oth"}])]}
            )
            == citing_other - deleted
        ), name
        assert names_of(
            {**body, "where": [cites([{"field": k("par-code"), "op": "eq", "value": "F-1"}])]}
        ) == {names[5]}, name
        # Without criteria: any citation; inverted: none.
        assert names_of({**body, "where": [cites([])]}) == (citing_other | {names[5]}) - deleted, (
            name
        )
        assert (
            names_of({**body, "where": [cites([], **{"not": True})]})
            == all_entries - citing_other - {names[5]} - deleted
        ), name
        # Into a third type on its own attribute; the change set tags Echo and untags Alpha.
        red = {"Alpha", "Charlie"} if name != "change set" else {"Echo"}
        assert (
            names_of(
                {**body, "where": [tagged([{"field": k(COLOUR), "op": "eq", "value": "red"}])]}
            )
            == red
        ), name
        assert (
            names_of(
                {
                    **body,
                    "where": [
                        tagged([{"field": k(COLOUR), "op": "eq", "value": "red"}], **{"not": True})
                    ],
                }
            )
            == all_entries - red - deleted
        ), name
        # Incoming: folders cited by an entry whose flag is set, combined with a folder criterion.
        folders = {"objectTypeKey": k(FOLDER), "context": context}
        incoming = {
            "related": {
                "relationTypeKey": k(CITES),
                "direction": "incoming",
                "where": [{"field": k("par-flag"), "op": "eq", "value": True}],
            }
        }
        assert names_of({**folders, "where": [incoming]}) == {"Other"}, name
        assert (
            names_of(
                {**folders, "where": [incoming, {"field": "name", "op": "eq", "value": "Top"}]}
            )
            == set()
        ), name
        # A hop and an ancestor criterion together.
        assert (
            names_of(
                {
                    **body,
                    "where": [
                        cites([]),
                        {
                            "field": f"ancestor:{k(FOLDER)}",
                            "op": "eq",
                            "value": seeded["other"]["id"],
                        },
                    ],
                }
            )
            == {n for n, f, _v in ENTRIES[:6] if f == 1} - deleted
        ), name

    base = {"objectTypeKey": k(ENTRY)}
    for criterion, path in (
        # The tag type binds none of the entry's fields.
        (
            tagged([{"field": k("par-code"), "op": "eq", "value": "A-1"}]),
            "/where/0/related/where/0/field",
        ),
        (tagged([{"field": k(COLOUR), "op": "gt", "value": "a"}]), "/where/0/related/where/0/op"),
        (tagged([{"field": k(COLOUR), "op": "eq", "value": 1}]), "/where/0/related/where/0/value"),
        (tagged([cites([])]), "/where/0/related/where/0/related"),
        (
            tagged([{"field": f"ancestor:{k(FOLDER)}", "op": "eq", "value": "x"}]),
            "/where/0/related/where/0/field",
        ),
        (
            {"related": {"relationTypeKey": "missing", "direction": "outgoing"}},
            "/where/0/related/relationTypeKey",
        ),
        # Entries are the source of citations, never the target.
        (
            {"related": {"relationTypeKey": k(CITES), "direction": "incoming"}},
            "/where/0/related/direction",
        ),
        (
            {"related": {"relationTypeKey": k(CITES), "direction": "outgoing"}, "field": "name"},
            "/where/0/related",
        ),
    ):
        _refused(client.post(QUERY, json={**base, "where": [criterion]}), "INVALID_QUERY", path)


def test_select_and_expand_shapes_in_every_context(query):
    client, k = query
    seeded = _seed(client, k)
    for name, (list_context, context) in seeded["contexts"].items():
        # Without select, an item is the list's item, and nothing is expanded unless asked.
        listed = _ok(
            client.get(f"/api/v1/objects/{k(ENTRY)}", params={**list_context, "pageSize": 2})
        )
        page = _ok(
            client.post(QUERY, json={"objectTypeKey": k(ENTRY), "context": context, "pageSize": 2})
        )
        assert page["items"] == listed["items"], name
        assert "totalCount" not in page, name

        selected = _ok(
            client.post(
                QUERY,
                json={
                    "objectTypeKey": k(ENTRY),
                    "context": context,
                    "where": [{"field": "name", "op": "eq", "value": "Golf"}],
                    "select": [
                        "name",
                        k("par-code"),
                        k("par-note"),
                        f"ancestor:{k(FOLDER)}",
                        "path",
                        "id",
                    ],
                },
            )
        )["items"]
        golf = next(entry for entry in seeded["entries"] if entry["name"] == "Golf")
        assert selected == [
            {
                "id": golf["id"],
                "objectTypeKey": k(ENTRY),
                "version": selected[0]["version"],
                "fields": {
                    "name": "Golf",
                    k("par-code"): "g-7",
                    # Unset on Golf: null, as an attribute the record does not hold.
                    k("par-note"): None,
                    # Top, not Sub: the ancestor of the type nearest the root.
                    f"ancestor:{k(FOLDER)}": {"id": seeded["top"]["id"], "name": "Top"},
                    "path": golf["path"],
                },
            }
        ], name

        # Expansion: at most ``limit`` in name order, the count, and a cursor that continues on
        # GET /relations exactly where the expansion stopped.
        body = {
            "objectTypeKey": k(FOLDER),
            "context": context,
            "sort": "name",
            "select": ["name"],
            "expand": [
                {
                    "relationTypeKey": k(CITES),
                    "direction": "incoming",
                    "select": ["name", k("par-code")],
                    "limit": 2,
                },
                {"relationTypeKey": k(NESTS), "direction": "outgoing"},
            ],
        }
        folders = {
            item["fields"]["name"]: item for item in _ok(client.post(QUERY, json=body))["items"]
        }
        assert list(folders) == ["Other", "Sub", "Top"], name
        other = folders["Other"]["expanded"]
        assert [(item["relationTypeKey"], item["direction"]) for item in other] == [
            (k(CITES), "incoming"),
            (k(NESTS), "outgoing"),
        ], name
        citations, nested = other
        relations = {
            "objectId": seeded["other"]["id"],
            "direction": "incoming",
            "relationTypeKey": k(CITES),
            **list_context,
        }
        every = _walk_list(client, "/api/v1/relations", relations)
        deleted = 1 if name == "change set" else 0
        assert citations["count"] == len(every) == 5 - deleted, name
        assert [item["relationId"] for item in citations["items"]] == [
            item["relation"]["id"] for item in every[:2]
        ], name
        assert [item["object"] for item in citations["items"]] == [
            {
                "id": item["object"]["id"],
                "objectTypeKey": k(ENTRY),
                "version": item["object"]["version"],
                "fields": {"name": item["object"]["name"], k("par-code"): _code(item["object"], k)},
            }
            for item in every[:2]
        ], name
        rest = _walk_list(
            client, "/api/v1/relations", {**relations, "cursor": citations["nextCursor"]}
        )
        assert [item["relation"]["id"] for item in rest] == [
            item["relation"]["id"] for item in every[2:]
        ], name
        assert nested == {
            "relationTypeKey": k(NESTS),
            "direction": "outgoing",
            "count": 0,
            "items": [],
            "nextCursor": None,
        }, name
        # Top holds Sub: an expansion without select carries the list's item; all shown, no cursor.
        top_nested = folders["Top"]["expanded"][1]
        sub = _ok(
            client.get(f"/api/v1/objects/{k(FOLDER)}/{seeded['sub']['id']}", params=list_context)
        )
        assert top_nested["count"] == 1 and top_nested["nextCursor"] is None, name
        assert top_nested["items"][0]["object"] == sub, name

    base = {"objectTypeKey": k(ENTRY)}
    for body, path in (
        ({**base, "select": ["name", k(COLOUR)]}, "/select/1"),
        ({**base, "select": [f"ancestor:{k(TAG)}"]}, "/select/0"),
        (
            {**base, "expand": [{"relationTypeKey": k(CITES), "direction": "incoming"}]},
            "/expand/0/direction",
        ),
        (
            {**base, "expand": [{"relationTypeKey": "missing", "direction": "outgoing"}]},
            "/expand/0/relationTypeKey",
        ),
        (
            {
                **base,
                "expand": [
                    {
                        "relationTypeKey": k(TAGGED),
                        "direction": "outgoing",
                        "select": [k("par-code")],
                    }
                ],
            },
            "/expand/0/select/0",
        ),
        (
            {**base, "expand": [{"relationTypeKey": k(TAGGED), "direction": "outgoing"}] * 2},
            "/expand/1",
        ),
    ):
        _refused(client.post(QUERY, json=body), "INVALID_QUERY", path)
    # The expansion's limit is part of the body's shape.
    _refused(
        client.post(
            QUERY,
            json={
                **base,
                "expand": [{"relationTypeKey": k(TAGGED), "direction": "outgoing", "limit": 21}],
            },
        ),
        "REQUEST_VALIDATION_ERROR",
    )


def _code(item: dict[str, Any], k: Keys) -> Any:
    return next(
        (
            value["value"]
            for value in item["attributes"]
            if value["attributeTypeKey"] == k("par-code")
        ),
        None,
    )


def test_pages_and_cursors_are_bound_to_the_body_and_context(query):
    client, k = query
    seeded = _seed(client, k)
    body = {
        "objectTypeKey": k(ENTRY),
        "where": [{"field": k("par-count"), "op": "gte", "value": 0}],
        "sort": k("par-count"),
    }
    first = _ok(client.post(QUERY, json={**body, "pageSize": 2, "includeTotal": True}))
    assert first["totalCount"] == 6 and first["startIndex"] == 0
    expected = _walk(client, body)
    assert [item["name"] for item in expected] == [
        "delta 50%",
        "Alpha",
        "foxtrot",
        "Echo",
        "Charlie",
        "hotel",
    ]
    # The same body continues. A cursor binds the whole body but its page selection, so another
    # body (even one that only selects differently), another context or another route refuses it.
    second = _ok(client.post(QUERY, json={**body, "pageSize": 2, "cursor": first["nextCursor"]}))
    assert _ids(second["items"]) == _ids(expected[2:4])
    for other in (
        {**body, "sort": f"-{k('par-count')}"},
        {**body, "where": []},
        {**body, "select": ["name"]},
        {**body, "context": seeded["contexts"]["publication"][1]},
    ):
        _refused(
            client.post(QUERY, json={**other, "cursor": first["nextCursor"]}), "INVALID_CURSOR"
        )
    _refused(
        client.get(
            f"/api/v1/objects/{k(ENTRY)}",
            params={"workspaceKey": WORKSPACE, "cursor": first["nextCursor"]},
        ),
        "INVALID_CURSOR",
    )
    # Positions, the last page and the way back, with totals.
    for name, (_list_context, context) in seeded["contexts"].items():
        scoped = {**body, "context": context}
        every = _walk(client, scoped)
        at = _ok(
            client.post(QUERY, json={**scoped, "pageSize": 2, "position": 3, "includeTotal": True})
        )
        assert _ids(at["items"]) == _ids(every[3:5]) and at["startIndex"] == 3, name
        assert at["totalCount"] == len(every), name
        back = _ok(client.post(QUERY, json={**scoped, "pageSize": 2, "cursor": at["prevCursor"]}))
        assert _ids(back["items"]) == _ids(every[1:3]), name
        end = _ok(
            client.post(QUERY, json={**scoped, "pageSize": 2, "from": "end", "includeTotal": True})
        )
        assert _ids(end["items"]) == _ids(every[-2:]) and end["nextCursor"] is None, name
    _refused(
        client.post(QUERY, json={**body, "cursor": first["nextCursor"], "position": 2}),
        "CONFLICTING_PAGE_PARAMETERS",
    )


def test_refusals_name_the_body_part(query):
    client, k = query
    seeded = _seed(client, k)
    change_set = seeded["contexts"]["change set"][1]
    publication = seeded["contexts"]["publication"][1]
    base = {"objectTypeKey": k(ENTRY)}
    for body, path in (
        ({"objectTypeKey": "missing"}, "/objectTypeKey"),
        ({**base, "where": [{"field": "missing", "op": "eq", "value": "x"}]}, "/where/0/field"),
        ({**base, "where": [{"field": k(COLOUR), "op": "eq", "value": "x"}]}, "/where/0/field"),
        ({**base, "where": [{"field": "sequenceId", "op": "eq", "value": "1"}]}, "/where/0/field"),
        ({**base, "where": [{"field": "name", "op": "like", "value": "x"}]}, "/where/0/op"),
        ({**base, "where": [{"field": "name"}]}, "/where/0/op"),
        ({**base, "where": [{"op": "eq", "value": "x"}]}, "/where/0/field"),
        (
            {**base, "where": [{"field": k("par-count"), "op": "gt", "value": "5"}]},
            "/where/0/value",
        ),
        (
            {**base, "where": [{"field": k("par-count"), "op": "gt", "value": True}]},
            "/where/0/value",
        ),
        (
            {**base, "where": [{"field": k("par-due"), "op": "gt", "value": "2026-13-01"}]},
            "/where/0/value",
        ),
        (
            {**base, "where": [{"field": k("par-flag"), "op": "isNull", "value": "true"}]},
            "/where/0/value",
        ),
        (
            {**base, "where": [{"field": "name", "op": "eq", "value": "x", "not": True}]},
            "/where/0/not",
        ),
        (
            {
                **base,
                "context": change_set,
                "where": [{"field": "createdAt", "op": "gt", "value": "2026-01-01T00:00:00Z"}],
            },
            "/where/0/field",
        ),
        ({**base, "sort": "missing"}, "/sort"),
        ({**base, "sort": "parentObjectId"}, "/sort"),
        ({**base, "sort": f"ancestor:{k(FOLDER)}"}, "/sort"),
        ({**base, "context": publication, "sort": "-updatedAt"}, "/sort"),
        ({**base, "asOf": "tomorrow"}, "/asOf"),
    ):
        _refused(client.post(QUERY, json=body), "INVALID_QUERY", path)
    _refused(
        client.post(QUERY, json={**base, "asOf": "2026-10-01"}), "AS_OF_NOT_SUPPORTED", "/asOf"
    )
    _refused(
        client.post(QUERY, json={**base, "context": {**change_set, **publication}}),
        "MUTUALLY_EXCLUSIVE_CONTEXT",
    )
    _refused(
        client.post(
            QUERY, json={**base, "context": {"changeSetId": "00000000-0000-4000-8000-000000000000"}}
        ),
        "CHANGE_SET_NOT_FOUND",
        status=404,
    )
    _refused(
        client.post("/api/v1/workspaces/missing/queries/objects", json=base),
        "WORKSPACE_NOT_FOUND",
        status=404,
    )
    # The body's shape: unknown properties and wrong JSON types are request validation errors (D19).
    _refused(client.post(QUERY, json={**base, "filter": {}}), "REQUEST_VALIDATION_ERROR")
    _refused(
        client.post(
            QUERY,
            json={**base, "where": [{"related": {"relationTypeKey": k(CITES), "direction": "up"}}]},
        ),
        "REQUEST_VALIDATION_ERROR",
    )
    _refused(client.post(QUERY, json={**base, "pageSize": 501}), "REQUEST_VALIDATION_ERROR")
