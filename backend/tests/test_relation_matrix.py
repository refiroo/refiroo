"""Base 0.8 A2: relation matrix reads over the starter model's three view shapes.

Every shape is read through the real HTTP route in live, change set and publication contexts: a
required, conditioned translation binding read outgoing; an optional system representation binding
read outgoing; and a many-to-many mapping binding read incoming.
"""

import json
from pathlib import Path
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from wp8_support import (
    create_change_set,
    inject_change_set_object,
    inject_change_set_relation,
    publish_change_set,
)

from app.config import reload_settings
from app.db import get_engine
from app.main import create_app
from app.services.model.registry import model_registry

BASE = "/api/v1/workspaces/default/relation-matrix"
TRANSLATIONS = {"applicationKey": "rdm-translations", "viewKey": "master-value-translations"}
CODELIST_SYSTEMS = {"applicationKey": "rdm-systems", "viewKey": "codelists-by-system"}
MASTER_SYSTEMS = {"applicationKey": "rdm-systems", "viewKey": "master-values-by-system"}


@pytest.fixture
def client(tmp_path, monkeypatch, migrated_database):
    model = json.loads((Path(__file__).resolve().parents[2] / "model/rdm-starter.json").read_text())
    model_path = tmp_path / "model.json"
    model_path.write_text(json.dumps(model))
    monkeypatch.setenv("DATABASE_URL", migrated_database("matrix.db"))
    monkeypatch.setenv("RDM_MODEL_PATH", str(model_path))
    model_registry.clear()
    with TestClient(create_app()) as value:
        yield value
    get_engine().dispose()
    monkeypatch.undo()
    reload_settings()
    model_registry.clear()


def attr(key, value):
    return {"attributeTypeKey": key, "value": value}


def create(client, application, object_type, name, attributes, *, parent=None, relations=None, **context):
    payload = {
        "applicationKey": application,
        "objectTypeKey": object_type,
        "name": name,
        "attributes": attributes,
        **(context or {"workspaceKey": "default"}),
    }
    if parent:
        payload["parentObjectId"] = parent["id"]
    if relations:
        payload["initialRelations"] = relations
    response = client.post("/api/v1/objects", json=payload)
    assert response.status_code == 201, response.text
    return response.json()


def relate(client, relation_type, source, target, **context):
    response = client.post(
        "/api/v1/relations",
        json={
            "relationTypeKey": relation_type,
            "fromObjectId": source["id"],
            "toObjectId": target["id"],
            **context,
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def matrix(client, view, expected=200, **params):
    """The page, or on a refusal the error body."""
    response = client.get(BASE, params={**view, **params})
    assert response.status_code == expected, response.text
    body = response.json()
    return body if expected == 200 else body["error"]


def cells(page, *, by="name"):
    """{row name: {column name: (state, record names)}} for readable assertions."""
    columns = {column["id"]: column[by] for column in page["columns"]}
    return {
        row["row"]["name"]: {
            columns[cell["columnId"]]: (cell["state"], [record["name"] for record in cell["records"]])
            for cell in row["cells"]
        }
        for row in page["items"]
    }


def names(page):
    return [row["row"]["name"] for row in page["items"]]


def delete(client, record, **params):
    """Delete a record with its relations, through the signed cascade preview."""
    path = f"/api/v1/objects/{record['objectTypeKey']}/{record['id']}"
    params = {"expectedVersion": record["version"], **params}
    preview = client.delete(path, params=params)
    assert preview.status_code == 409, preview.text
    token = preview.json()["error"]["details"]["deletionPreviewToken"]
    response = client.delete(path, params={**params, "cascade": True, "deletionPreviewToken": token})
    assert response.status_code == 204, response.text


def translation(client, name, group, master, *, active=True, **context):
    return create(
        client,
        "rdm-translations",
        "translation",
        name,
        [attr("translated-name", f"{name} text"), attr("active", active)],
        parent=group,
        relations=[
            {
                "relationTypeKey": "object-has-translation",
                "direction": "incoming",
                "otherObjectId": master["id"],
            }
        ],
        **context,
    )


@pytest.fixture
def translations(client):
    """Four master values and three languages, one with two container levels.

    Live: M1 has an active EN and an inactive CS translation; M2 an active and an inactive EN one;
    M3 had DE in publication 1, since deleted live; M4 has none. A change set from current live
    stages a second active EN translation for M2 and deletes M1's EN one.
    """
    domain = create(client, "rdm-master", "domain", "Domain", [attr("domain-code", "D")])
    codelist = create(
        client, "rdm-master", "codelist", "Codelist", [attr("codelist-code", "C")], parent=domain
    )
    masters = {
        name: create(
            client,
            "rdm-master",
            "master-value",
            name,
            [attr("master-id", name), attr("value-code", f"VC-{name}"), attr("value-name", f"Value {name}")],
            parent=codelist,
        )
        for name in ("M1", "M2", "M3", "M4")
    }
    languages, groups = {}, {}
    for code in ("en", "cs", "de"):
        languages[code] = create(
            client, "rdm-translations", "language", f"Language {code}", [attr("language-code", code)]
        )
        groups[code] = create(
            client,
            "rdm-translations",
            "translation-group",
            f"Group {code}",
            [attr("group-code", f"G-{code}")],
            parent=languages[code],
        )
    # EN translations sit two container levels below the language.
    nested = create(
        client,
        "rdm-translations",
        "translation-group",
        "Group en nested",
        [attr("group-code", "G-en-2")],
        parent=groups["en"],
    )
    m1_en = translation(client, "M1 en", nested, masters["M1"])
    translation(client, "M1 cs", groups["cs"], masters["M1"], active=False)
    translation(client, "M2 en", nested, masters["M2"])
    translation(client, "M2 en old", groups["en"], masters["M2"], active=False)

    staged = create_change_set(client, "default", name="history", source="currentLive").json()
    m3_de = translation(
        client,
        "M3 de",
        groups["de"],
        masters["M3"],
        changeSetId=staged["id"],
        expectedChangeSetVersion=staged["version"],
    )
    publication = publish_change_set(
        client, staged["id"], expected_change_set_version=m3_de["changeSetVersion"]
    ).json()
    delete(client, m3_de)

    change_set = create_change_set(client, "default", name="edits", source="currentLive").json()
    duplicate = str(uuid4())
    inject_change_set_object(
        change_set["id"],
        duplicate,
        "rdm-translations",
        "translation",
        "M2 en duplicate",
        parent_object_id=groups["en"]["id"],
        attributes={"translated-name": "duplicate", "active": True},
    )
    inject_change_set_relation(
        change_set["id"], str(uuid4()), "object-has-translation", masters["M2"]["id"], duplicate
    )
    delete(
        client,
        m1_en,
        changeSetId=change_set["id"],
        expectedChangeSetVersion=change_set["version"],
    )
    columns = [languages[code]["id"] for code in ("en", "cs", "de")]
    return {
        "masters": masters,
        "languages": languages,
        "codelist": codelist,
        "domain": domain,
        "columns": columns,
        "publication": publication,
        "change_set": change_set,
    }


def test_translation_cells_in_every_context(client, translations):
    columns = translations["columns"]
    live = matrix(client, TRANSLATIONS, columnIds=columns)
    assert [column["label"] for column in live["columns"]] == ["en", "cs", "de"]
    assert cells(live) == {
        "M1": {
            "Language en": ("one", ["M1 en"]),
            "Language cs": ("inactive", ["M1 cs"]),
            "Language de": ("none", []),
        },
        "M2": {
            "Language en": ("one", ["M2 en", "M2 en old"]),
            "Language cs": ("none", []),
            "Language de": ("none", []),
        },
        "M3": {
            "Language en": ("none", []),
            "Language cs": ("none", []),
            "Language de": ("historyOnly", ["M3 de"]),
        },
        "M4": {name: ("none", []) for name in ("Language en", "Language cs", "Language de")},
    }
    m2_en = live["items"][1]["cells"][0]
    assert (m2_en["recordCount"], m2_en["matchingCount"], m2_en["conflict"]) == (2, 1, False)
    assert [record["meetsCondition"] for record in m2_en["records"]] == [True, False]
    record = m2_en["records"][0]
    assert record["fields"] == {
        "translated-name": "M2 en text",
        "translated-value": None,
        "active": True,
    }
    assert record["version"] == 1 and record["relationId"]
    history = live["items"][2]["cells"][2]
    assert history["publication"] == {
        "id": translations["publication"]["id"],
        "number": translations["publication"]["publicationNumber"],
    }
    assert history["records"][0]["fields"]["active"] is True
    # Row fields are the view's rowColumns, the ancestor included.
    assert live["items"][0]["row"]["fields"] == {
        "name": "M1",
        "value-code": "VC-M1",
        "ancestor:codelist": "Codelist",
    }

    published = matrix(
        client, TRANSLATIONS, columnIds=columns, publicationId=translations["publication"]["id"]
    )
    # Publication 1 still holds M3's DE translation; nothing earlier holds anything.
    assert cells(published)["M3"]["Language de"] == ("one", ["M3 de"])
    assert cells(published)["M1"]["Language en"] == ("one", ["M1 en"])
    assert all(row["relationSetVersion"] == 0 for row in published["items"])

    staged = matrix(client, TRANSLATIONS, columnIds=columns, changeSetId=translations["change_set"]["id"])
    staged_cells = cells(staged)
    # Deleted in the change set, but publication 1 held it.
    assert staged_cells["M1"]["Language en"] == ("historyOnly", ["M1 en"])
    assert staged_cells["M2"]["Language en"] == ("several", ["M2 en", "M2 en duplicate", "M2 en old"])
    several = staged["items"][1]["cells"][0]
    assert (several["conflict"], several["recordCount"], several["matchingCount"]) == (True, 3, 2)
    assert staged_cells["M3"]["Language de"] == ("historyOnly", ["M3 de"])
    duplicate = several["records"][1]
    assert duplicate["fields"]["translated-name"] == "duplicate"


def test_state_filter_decides_over_every_row_with_totals(client, translations):
    columns = translations["columns"]

    def rows(state, **context):
        page = matrix(
            client, TRANSLATIONS, columnIds=columns, state=state, includeTotal=True, **context
        )
        assert page["totalCount"] == len(page["items"])
        return names(page)

    assert rows("one") == ["M1", "M2"]
    assert rows("inactive") == ["M1"]
    assert rows("several") == []
    # historyOnly never counts as one.
    assert rows("historyOnly") == ["M3"]
    assert rows("none") == ["M1", "M2", "M3", "M4"]
    change_set = {"changeSetId": translations["change_set"]["id"]}
    assert rows("several", **change_set) == ["M2"]
    assert rows("historyOnly", **change_set) == ["M1", "M3"]
    assert rows("one", **change_set) == []
    publication = {"publicationId": translations["publication"]["id"]}
    assert rows("historyOnly", **publication) == []
    assert rows("one", **publication) == ["M1", "M2", "M3"]

    # A single selected column narrows the filter to it.
    only_de = matrix(client, TRANSLATIONS, columnIds=[columns[2]], state="none")
    assert names(only_de) == ["M1", "M2", "M4"]
    assert [cell["columnId"] for cell in only_de["items"][0]["cells"]] == [columns[2]]


def test_filtered_rows_page_both_ways_by_cursor_and_position(client, translations):
    params = {"columnIds": translations["columns"], "state": "none", "pageSize": 1}
    seen, cursor = [], None
    while True:
        page = matrix(client, TRANSLATIONS, **params, **({"cursor": cursor} if cursor else {}))
        seen += names(page)
        cursor = page["nextCursor"]
        if cursor is None:
            break
    assert seen == ["M1", "M2", "M3", "M4"]
    back = matrix(client, TRANSLATIONS, **params, cursor=page["prevCursor"])
    assert names(back) == ["M3"]
    deep = matrix(client, TRANSLATIONS, **params, position=2, includeTotal=True)
    assert (names(deep), deep["startIndex"], deep["totalCount"]) == (["M3"], 2, 4)
    last = matrix(client, TRANSLATIONS, **params, **{"from": "end"})
    assert names(last) == ["M4"]
    # A cursor binds the state filter and the columns.
    error = matrix(client, TRANSLATIONS, 422, **{**params, "state": "one"}, cursor=page["prevCursor"])
    assert error["code"] == "invalid_cursor"
    error = matrix(
        client,
        TRANSLATIONS,
        422,
        **{**params, "columnIds": translations["columns"][:2]},
        cursor=page["prevCursor"],
    )
    assert error["code"] == "invalid_cursor"
    staged = {**params, "changeSetId": translations["change_set"]["id"], "state": "historyOnly"}
    deep = matrix(client, TRANSLATIONS, **staged, position=1, includeTotal=True)
    assert (names(deep), deep["totalCount"]) == (["M3"], 2)


def test_default_columns_page_by_name_with_their_own_cursor(client, translations):
    first = matrix(client, TRANSLATIONS, columnPageSize=2)
    assert [column["name"] for column in first["columns"]] == ["Language cs", "Language de"]
    assert first["columnsPrevCursor"] is None
    second = matrix(client, TRANSLATIONS, columnPageSize=2, columnCursor=first["columnsNextCursor"])
    assert [column["name"] for column in second["columns"]] == ["Language en"]
    assert second["columnsNextCursor"] is None
    assert cells(second)["M1"] == {"Language en": ("one", ["M1 en"])}
    back = matrix(client, TRANSLATIONS, columnPageSize=2, columnCursor=second["columnsPrevCursor"])
    assert [column["name"] for column in back["columns"]] == ["Language cs", "Language de"]
    # A column cursor belongs to its context.
    error = matrix(
        client,
        TRANSLATIONS,
        422,
        columnPageSize=2,
        columnCursor=first["columnsNextCursor"],
        changeSetId=translations["change_set"]["id"],
    )
    assert error["code"] == "invalid_cursor"


def test_rows_scope_search_sort_and_set_versions(client, translations):
    codelist, domain = translations["codelist"], translations["domain"]
    assert names(matrix(client, TRANSLATIONS, parentObjectId=codelist["id"])) == ["M1", "M2", "M3", "M4"]
    mismatch = matrix(client, TRANSLATIONS, 422, parentObjectId=domain["id"])
    assert mismatch["code"] == "relation_matrix_parent_scope_mismatch"
    missing = matrix(client, TRANSLATIONS, 404, parentObjectId=str(uuid4()))
    assert missing["code"] == "relation_matrix_parent_not_found"
    # searchFields: name, value-code and value-name; master-id is not among them.
    assert names(matrix(client, TRANSLATIONS, search="VC-M2")) == ["M2"]
    assert names(matrix(client, TRANSLATIONS, search="Value M3")) == ["M3"]
    assert names(matrix(client, TRANSLATIONS, search="M1")) == ["M1"]
    assert names(matrix(client, TRANSLATIONS, sort="-name")) == ["M4", "M3", "M2", "M1"]
    assert names(matrix(client, TRANSLATIONS, seek="M3")) == ["M3", "M4"]
    live = matrix(client, TRANSLATIONS, columnIds=translations["columns"])
    versions = {row["row"]["name"]: row["relationSetVersion"] for row in live["items"]}
    # The row's outgoing set version: one per translation created with it as an initial relation
    # (A3); M3's was staged, merged at publishing, then removed by a cascade.
    assert versions == {"M1": 2, "M2": 2, "M3": 2, "M4": 0}


def test_codelists_by_system_optional_binding_without_condition(client):
    domain = create(client, "rdm-master", "domain", "Domain", [attr("domain-code", "D")])
    codelists = [
        create(client, "rdm-master", "codelist", name, [attr("codelist-code", name)], parent=domain)
        for name in ("C1", "C2")
    ]
    systems = [
        create(client, "rdm-systems", "system", name, [attr("system-code", name.lower())])
        for name in ("S1", "S2")
    ]
    group = create(
        client, "rdm-systems", "system-group", "S1 group", [attr("group-code", "g")], parent=systems[0]
    )
    values = [
        create(
            client,
            "rdm-systems",
            "system-value",
            name,
            [attr("value-code", name), attr("value-name", name), attr("active", False)],
            parent=parent,
        )
        for name, parent in (("V1", group), ("V2", group), ("V3", systems[1]))
    ]
    for value in values:
        relate(client, "reference-has-system-representation", codelists[0], value)
    page = matrix(client, CODELIST_SYSTEMS, columnIds=[system["id"] for system in systems])
    assert [column["label"] for column in page["columns"]] == ["s1", "s2"]
    # Without a condition every record counts, however its own active flag reads.
    assert cells(page) == {
        "C1": {"S1": ("several", ["V1", "V2"]), "S2": ("one", ["V3"])},
        "C2": {"S1": ("none", []), "S2": ("none", [])},
    }
    several = page["items"][0]["cells"][0]
    assert (several["conflict"], several["recordCount"], several["matchingCount"]) == (False, 2, 2)
    assert several["records"][0]["fields"] == {"value-code": "V1", "value-name": "V1", "active": False}
    filtered = matrix(
        client, CODELIST_SYSTEMS, columnIds=[systems[1]["id"]], state="one", includeTotal=True
    )
    assert names(filtered) == ["C1"] and filtered["totalCount"] == 1


def test_master_values_by_system_many_to_many_incoming(client):
    domain = create(client, "rdm-master", "domain", "Domain", [attr("domain-code", "D")])
    codelist = create(
        client, "rdm-master", "codelist", "Codelist", [attr("codelist-code", "C")], parent=domain
    )
    masters = [
        create(
            client,
            "rdm-master",
            "master-value",
            name,
            [attr("master-id", name), attr("value-code", name), attr("value-name", name)],
            parent=codelist,
        )
        for name in ("M1", "M2", "M3")
    ]
    systems = [
        create(client, "rdm-systems", "system", name, [attr("system-code", name.lower())])
        for name in ("S1", "S2")
    ]
    values = [
        create(
            client,
            "rdm-systems",
            "system-value",
            name,
            [attr("value-code", name), attr("value-name", name)],
            parent=parent,
        )
        for name, parent in (("V1", systems[0]), ("V2", systems[0]), ("V3", systems[1]))
    ]
    # V1 maps to two master values: the same cell record sits in two rows.
    for value, master in ((values[0], masters[0]), (values[2], masters[0]), (values[0], masters[1]), (values[1], masters[1])):
        relate(client, "system-value-maps-to-master", value, master)
    columns = [system["id"] for system in systems]
    page = matrix(client, MASTER_SYSTEMS, columnIds=columns)
    assert cells(page) == {
        "M1": {"S1": ("one", ["V1"]), "S2": ("one", ["V3"])},
        "M2": {"S1": ("several", ["V1", "V2"]), "S2": ("none", [])},
        "M3": {"S1": ("none", []), "S2": ("none", [])},
    }
    # Read incoming, the binding's uniqueness never makes several a conflict.
    assert page["items"][1]["cells"][0]["conflict"] is False
    # The row's incoming set version: two relations each.
    assert [row["relationSetVersion"] for row in page["items"]] == [2, 2, 0]
    assert names(matrix(client, MASTER_SYSTEMS, columnIds=[columns[1]], state="one")) == ["M1"]
    assert names(matrix(client, MASTER_SYSTEMS, columnIds=columns, state="several")) == ["M2"]
    assert names(matrix(client, MASTER_SYSTEMS, columnIds=columns, state="none")) == ["M2", "M3"]

    change_set = create_change_set(client, "default", name="mapping", source="currentLive").json()
    relate(
        client,
        "system-value-maps-to-master",
        values[2],
        masters[2],
        changeSetId=change_set["id"],
        expectedChangeSetVersion=change_set["version"],
    )
    staged = matrix(client, MASTER_SYSTEMS, columnIds=columns, changeSetId=change_set["id"])
    assert cells(staged)["M3"] == {"S1": ("none", []), "S2": ("one", ["V3"])}
    assert names(matrix(client, MASTER_SYSTEMS, columnIds=[columns[1]], state="one", changeSetId=change_set["id"])) == ["M1", "M3"]


def test_refusals_are_machine_readable(client, translations):
    columns = translations["columns"]
    assert matrix(client, {**TRANSLATIONS, "viewKey": "missing"}, 404)["code"] == (
        "relation_matrix_view_not_found"
    )
    # A view of another type is not a matrix.
    assert matrix(client, {"applicationKey": "rdm-systems", "viewKey": "system-to-master-mapping"}, 404)[
        "code"
    ] == "relation_matrix_view_not_found"
    too_many = matrix(client, TRANSLATIONS, 422, columnIds=[str(uuid4()) for _ in range(21)])
    assert too_many["code"] == "too_many_columns" and too_many["details"]["limit"] == 20
    assert matrix(client, TRANSLATIONS, 422, columnIds=[columns[0], columns[0]])["code"] == (
        "duplicate_column_ids"
    )
    wrong_type = matrix(client, TRANSLATIONS, 404, columnIds=[columns[0], translations["codelist"]["id"]])
    assert wrong_type["code"] == "relation_matrix_column_not_found"
    assert wrong_type["details"]["columnIds"] == [translations["codelist"]["id"]]
    assert matrix(client, TRANSLATIONS, 422, state="one")["code"] == (
        "relation_matrix_state_requires_columns"
    )
    assert matrix(client, TRANSLATIONS, 422, columnIds=columns, columnCursor="x")["code"] == (
        "conflicting_column_parameters"
    )
    both = matrix(
        client,
        TRANSLATIONS,
        422,
        changeSetId=translations["change_set"]["id"],
        publicationId=translations["publication"]["id"],
    )
    assert both["code"] == "mutually_exclusive_context"
    assert matrix(client, TRANSLATIONS, 422, state="bogus", columnIds=columns)["code"] == (
        "request_validation_error"
    )
