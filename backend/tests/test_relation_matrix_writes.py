"""Base 0.8 A3: writes from a relation matrix cell.

A cell writes through the generic object and relation APIs; the matrix adds the container and link
candidate reads a cell needs. Every write is exercised at the real HTTP boundary over the
translation shape (a required, conditioned binding read outgoing) and the mapping shapes (an
optional one-to-many binding read outgoing, a many-to-many binding read incoming), live and in a
change set, and each refusal is checked to leave nothing partial.
"""

import json
from pathlib import Path
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from test_relation_matrix import (
    CODELIST_SYSTEMS,
    MASTER_SYSTEMS,
    TRANSLATIONS,
    attr,
    cells,
    create,
    matrix,
    relate,
)
from wp8_support import create_change_set, publish_change_set, validate_change_set

from app.config import reload_settings
from app.db import SessionLocal, get_engine
from app.engine.indexes import matrix_states
from app.engine.model.registry import model_registry
from app.main import create_app

BASE = "/api/v1/workspaces/default/relation-matrix"
TRANSLATION_LINK = "object-has-translation"
STARTER = Path(__file__).resolve().parents[2] / "model/rdm-starter.json"


def serve(model, tmp_path, monkeypatch, database_url):
    """A client over ``model`` and a fresh migrated database."""
    model_path = tmp_path / "model.json"
    model_path.write_text(json.dumps(model))
    monkeypatch.setenv("DATABASE_URL", database_url)
    monkeypatch.setenv("RDM_MODEL_PATH", str(model_path))
    model_registry.clear()
    with TestClient(create_app()) as value:
        yield value
        # A3b: after every test's writes, stored cell states equal states rebuilt from records.
        with SessionLocal() as session:
            assert matrix_states.verify(session) == []
    get_engine().dispose()
    monkeypatch.undo()
    reload_settings()
    model_registry.clear()


@pytest.fixture
def client(tmp_path, monkeypatch, migrated_database):
    yield from serve(json.loads(STARTER.read_text()), tmp_path, monkeypatch, migrated_database("matrix-writes.db"))


def helper(client, path, view, expected=200, **params):
    """A container or candidate page, or on a refusal the error body."""
    response = client.get(f"{BASE}/{path}", params={**view, **params})
    assert response.status_code == expected, response.text
    body = response.json()
    return body if expected == 200 else body["error"]


def patch(client, record, expected=200, **fields):
    response = client.patch(
        f"/api/v1/objects/{record['objectTypeKey']}/{record['id']}",
        json={"expectedVersion": record["version"], **fields},
    )
    assert response.status_code == expected, response.text
    return response.json() if expected == 200 else response.json()["error"]


def link(client, relation_type, source, target, expected=201, **fields):
    response = client.post(
        "/api/v1/relations",
        json={
            "relationTypeKey": relation_type,
            "fromObjectId": source["id"],
            "toObjectId": target["id"],
            **fields,
        },
    )
    assert response.status_code == expected, response.text
    return response.json() if expected == 201 else response.json()["error"]


def unlink(client, record, expected=204, **params):
    response = client.delete(
        f"/api/v1/relations/{record['relationId']}",
        params={"expectedVersion": record["relationVersion"], **params},
    )
    assert response.status_code == expected, response.text
    return None if expected == 204 else response.json()["error"]


def row(page, name):
    return next(item for item in page["items"] if item["row"]["name"] == name)


def cell(page, row_name, column_id):
    return next(item for item in row(page, row_name)["cells"] if item["columnId"] == column_id)


def translation_payload(name, group, master, *, active=True, **context):
    return {
        "applicationKey": "rdm-translations",
        "objectTypeKey": "translation",
        "name": name,
        "parentObjectId": group["id"],
        "attributes": [attr("translated-name", f"{name} text"), attr("active", active)],
        "initialRelations": [
            {"relationTypeKey": TRANSLATION_LINK, "direction": "incoming", "otherObjectId": master["id"]}
        ],
        **(context or {"workspaceKey": "default"}),
    }


@pytest.fixture
def languages(client):
    """Master values M1 and M2 and languages EN (two container levels), CS (one group) and DE
    (none). M1 has an active EN translation in the nested group, M2 an active and an inactive
    one."""
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
            [attr("master-id", name), attr("value-code", name), attr("value-name", name)],
            parent=codelist,
        )
        for name in ("M1", "M2")
    }
    language = {
        code: create(
            client, "rdm-translations", "language", f"Language {code}", [attr("language-code", code)]
        )
        for code in ("en", "cs", "de")
    }

    def group(name, parent):
        return create(
            client, "rdm-translations", "translation-group", name, [attr("group-code", name)], parent=parent
        )

    groups = {"en": group("Group en", language["en"]), "cs": group("Group cs", language["cs"])}
    groups["nested"] = group("Nested", groups["en"])

    def translate(name, container, master, active=True):
        response = client.post(
            "/api/v1/objects", json=translation_payload(name, container, master, active=active)
        )
        assert response.status_code == 201, response.text
        return response.json()

    records = {
        "M1 en": translate("M1 en", groups["nested"], masters["M1"]),
        "M2 en": translate("M2 en", groups["en"], masters["M2"]),
        "M2 en old": translate("M2 en old", groups["en"], masters["M2"], active=False),
    }
    return {
        "masters": masters,
        "language": language,
        "groups": groups,
        "records": records,
        "columns": [language[code]["id"] for code in ("en", "cs", "de")],
    }


@pytest.fixture
def systems(client):
    """Codelists C1 and C2, master values SM1 and SM2, system S1 with a group and S2 without.
    V1, V2 and inactive V4 sit in S1's group, V3 directly under S2; C1 represents V1."""
    domain = create(client, "rdm-master", "domain", "Systems domain", [attr("domain-code", "SD")])
    codelists = {
        name: create(client, "rdm-master", "codelist", name, [attr("codelist-code", name)], parent=domain)
        for name in ("C1", "C2")
    }
    masters = {
        name: create(
            client,
            "rdm-master",
            "master-value",
            name,
            [attr("master-id", name), attr("value-code", name), attr("value-name", name)],
            parent=codelists["C1"],
        )
        for name in ("SM1", "SM2")
    }
    system = {
        name: create(client, "rdm-systems", "system", name, [attr("system-code", name.lower())])
        for name in ("S1", "S2")
    }
    group = create(
        client, "rdm-systems", "system-group", "S1 group", [attr("group-code", "g")], parent=system["S1"]
    )
    values = {
        name: create(
            client,
            "rdm-systems",
            "system-value",
            name,
            [attr("value-code", name), attr("value-name", name), attr("active", active)],
            parent=parent,
        )
        for name, parent, active in (
            ("V1", group, True),
            ("V2", group, True),
            ("V3", system["S2"], True),
            ("V4", group, False),
        )
    }
    relate(client, "reference-has-system-representation", codelists["C1"], values["V1"])
    return {
        "codelists": codelists,
        "masters": masters,
        "system": system,
        "group": group,
        "values": values,
        "columns": [system["S1"]["id"], system["S2"]["id"]],
    }


def container_names(page):
    return [(item["name"], [part["name"] for part in item["path"]]) for item in page["items"]]


def test_containers_list_what_can_hold_a_new_cell_record(client, languages, systems):
    en, cs, de = languages["columns"]
    page = helper(client, "containers", TRANSLATIONS, columnId=en, includeTotal=True)
    # A language cannot hold a translation directly; its groups at every depth can, in path order.
    assert container_names(page) == [
        ("Group en", ["Group en"]),
        ("Nested", ["Group en", "Nested"]),
    ]
    assert page["defaultContainerId"] is None and page["totalCount"] == 2
    only = helper(client, "containers", TRANSLATIONS, columnId=cs)
    assert only["defaultContainerId"] == languages["groups"]["cs"]["id"]
    # The default is the column's, whatever the search narrows the page to.
    searched = helper(client, "containers", TRANSLATIONS, columnId=en, search="NEST")
    assert container_names(searched) == [("Nested", ["Group en", "Nested"])]
    assert searched["defaultContainerId"] is None
    empty = helper(client, "containers", TRANSLATIONS, columnId=de)
    assert empty["items"] == [] and empty["defaultContainerId"] is None

    # A system holds values directly, so the column record itself is a container.
    s1, s2 = systems["columns"]
    page = helper(client, "containers", CODELIST_SYSTEMS, columnId=s1)
    assert container_names(page) == [("S1", []), ("S1 group", ["S1 group"])]
    assert helper(client, "containers", CODELIST_SYSTEMS, columnId=s2)["defaultContainerId"] == s2

    # Pages by cursor both ways.
    first = helper(client, "containers", TRANSLATIONS, columnId=en, pageSize=1)
    second = helper(client, "containers", TRANSLATIONS, columnId=en, pageSize=1, cursor=first["nextCursor"])
    assert container_names(second) == [("Nested", ["Group en", "Nested"])] and second["nextCursor"] is None
    back = helper(client, "containers", TRANSLATIONS, columnId=en, pageSize=1, cursor=second["prevCursor"])
    assert container_names(back) == [("Group en", ["Group en"])]
    # A cursor binds the column.
    error = helper(client, "containers", TRANSLATIONS, 422, columnId=cs, pageSize=1, cursor=first["nextCursor"])
    assert error["code"] == "INVALID_CURSOR"

    # In a change set: a group added under CS and the nested group moved there.
    change_set = create_change_set(client, "default", name="containers", source="currentLive").json()
    added = create(
        client,
        "rdm-translations",
        "translation-group",
        "Group cs 2",
        [attr("group-code", "cs2")],
        parent=languages["groups"]["cs"],
        changeSetId=change_set["id"],
        expectedChangeSetVersion=change_set["version"],
    )
    moved = patch(
        client,
        languages["groups"]["nested"],
        parentObjectId=languages["groups"]["cs"]["id"],
        changeSetId=change_set["id"],
        expectedChangeSetVersion=added["changeSetVersion"],
    )
    assert moved["parentObjectId"] == languages["groups"]["cs"]["id"]
    staged = helper(client, "containers", TRANSLATIONS, columnId=cs, changeSetId=change_set["id"])
    assert container_names(staged) == [
        ("Group cs", ["Group cs"]),
        ("Group cs 2", ["Group cs", "Group cs 2"]),
        ("Nested", ["Group cs", "Nested"]),
    ]
    assert staged["defaultContainerId"] is None
    assert container_names(helper(client, "containers", TRANSLATIONS, columnId=en, changeSetId=change_set["id"])) == [
        ("Group en", ["Group en"])
    ]
    # Live is unchanged.
    assert helper(client, "containers", TRANSLATIONS, columnId=cs)["defaultContainerId"] == languages["groups"]["cs"]["id"]


def test_container_and_candidate_refusals(client, languages, systems):
    # The mapping matrix offers no create; the translation matrices no link.
    error = helper(client, "containers", MASTER_SYSTEMS, 422, columnId=systems["columns"][0])
    assert error["code"] == "RELATION_MATRIX_ACTION_NOT_ALLOWED"
    assert error["details"] == {"viewKey": "master-values-by-system", "action": "create"}
    error = helper(
        client,
        "link-candidates",
        TRANSLATIONS,
        422,
        rowId=languages["masters"]["M1"]["id"],
        columnId=languages["columns"][0],
    )
    assert error["code"] == "RELATION_MATRIX_ACTION_NOT_ALLOWED"
    # A column or row of the wrong type.
    error = helper(client, "containers", TRANSLATIONS, 404, columnId=languages["groups"]["en"]["id"])
    assert error["code"] == "RELATION_MATRIX_COLUMN_NOT_FOUND"
    error = helper(
        client,
        "link-candidates",
        CODELIST_SYSTEMS,
        404,
        rowId=systems["masters"]["SM1"]["id"],
        columnId=systems["columns"][0],
    )
    assert error["code"] == "RELATION_MATRIX_ROW_NOT_FOUND"
    error = helper(
        client,
        "link-candidates",
        CODELIST_SYSTEMS,
        404,
        rowId=str(uuid4()),
        columnId=systems["columns"][0],
    )
    assert error["code"] == "RELATION_MATRIX_ROW_NOT_FOUND"


def candidates(page):
    return {item["name"]: item["reason"] for item in page["items"]}


def test_link_candidates_are_listed_with_reasons(client, systems):
    s1, s2 = systems["columns"]
    c1, c2 = systems["codelists"]["C1"], systems["codelists"]["C2"]
    page = helper(
        client, "link-candidates", CODELIST_SYSTEMS, rowId=c1["id"], columnId=s1, includeTotal=True
    )
    # Every value under S1, at any depth, is listed; ineligible ones say why.
    assert candidates(page) == {"V1": "alreadyLinked", "V2": None, "V4": None}
    assert page["totalCount"] == 3
    v1 = page["items"][0]
    assert v1["eligible"] is False and v1["path"][0]["name"] == "S1 group"
    assert v1["fields"] == {"value-code": "V1", "value-name": "V1", "active": True}
    assert v1["version"] == 1
    # A system value belongs to one codelist (one-to-many): V1 is taken for C2.
    assert candidates(helper(client, "link-candidates", CODELIST_SYSTEMS, rowId=c2["id"], columnId=s1)) == {
        "V1": "candidateCardinality",
        "V2": None,
        "V4": None,
    }
    assert candidates(helper(client, "link-candidates", CODELIST_SYSTEMS, rowId=c2["id"], columnId=s2)) == {
        "V3": None
    }
    searched = helper(client, "link-candidates", CODELIST_SYSTEMS, rowId=c2["id"], columnId=s1, search="v2")
    assert candidates(searched) == {"V2": None}
    # The row's set version, which a link claims.
    assert page["relationSetVersion"] == matrix(client, CODELIST_SYSTEMS, columnIds=[s1])["items"][0][
        "relationSetVersion"
    ]

    # Many-to-many, read incoming: only what the row already relates to is ineligible.
    m1 = systems["masters"]["SM1"]
    relate(client, "system-value-maps-to-master", systems["values"]["V2"], m1)
    assert candidates(helper(client, "link-candidates", MASTER_SYSTEMS, rowId=m1["id"], columnId=s1)) == {
        "V1": None,
        "V2": "alreadyLinked",
        "V4": None,
    }


def test_live_translation_cell_create_and_edit(client, languages):
    en = languages["columns"][0]
    masters, groups, records = languages["masters"], languages["groups"], languages["records"]
    before = matrix(client, TRANSLATIONS, columnIds=languages["columns"])
    # Creating a record with initial relations advances the row's set like any relation write.
    assert row(before, "M1")["relationSetVersion"] == 1
    assert row(before, "M2")["relationSetVersion"] == 2

    # create: the chosen container, the row through initialRelations, cellFields as attributes.
    created = client.post("/api/v1/objects", json=translation_payload("M1 / cs", groups["cs"], masters["M1"]))
    assert created.status_code == 201, created.text
    after = matrix(client, TRANSLATIONS, columnIds=languages["columns"])
    assert cells(after)["M1"]["Language cs"] == ("one", ["M1 / cs"])
    assert row(after, "M1")["relationSetVersion"] == 2

    # A second active EN translation for M1 is refused whole and names the one already there.
    duplicate = client.post("/api/v1/objects", json=translation_payload("M1 en again", groups["en"], masters["M1"]))
    assert duplicate.status_code == 409, duplicate.text
    error = duplicate.json()["error"]
    assert error["code"] == "DUPLICATE_RELATION_SCOPE"
    assert error["details"]["conflictingObjectId"] == records["M1 en"]["id"]
    assert error["details"]["conflictingRelationId"] == cell(after, "M1", en)["records"][0]["relationId"]
    assert error["details"]["ancestorObjectId"] == en
    unchanged = matrix(client, TRANSLATIONS, columnIds=languages["columns"])
    assert cells(unchanged) == cells(after)
    assert unchanged["items"] == after["items"]

    # edit: cellFields under the record's version.
    record = cell(after, "M1", en)["records"][0]
    edited = patch(
        client,
        {"objectTypeKey": "translation", "id": record["id"], "version": record["version"]},
        attributes=[attr("translated-name", "Corrected")],
    )
    assert edited["version"] == record["version"] + 1
    refreshed = cell(matrix(client, TRANSLATIONS, columnIds=[en]), "M1", en)["records"][0]
    assert refreshed["fields"]["translated-name"] == "Corrected"
    # A stale version is refused and the value stays.
    stale = patch(
        client,
        {"objectTypeKey": "translation", "id": record["id"], "version": record["version"]},
        409,
        attributes=[attr("translated-name", "Lost")],
    )
    assert stale["code"] == "VERSION_CONFLICT"
    # Activating M2's old EN translation would make two: refused, naming the active one.
    old = records["M2 en old"]
    breach = patch(client, old, 409, attributes=[attr("active", True)])
    assert breach["code"] == "DUPLICATE_RELATION_SCOPE"
    assert breach["details"]["conflictingObjectId"] == records["M2 en"]["id"]
    m2 = cell(matrix(client, TRANSLATIONS, columnIds=[en]), "M2", en)
    assert (m2["state"], m2["matchingCount"]) == ("one", 1)
    assert m2["records"][1]["version"] == old["version"]


def test_live_link_and_unlink_claim_the_row_set(client, systems):
    s1, _ = systems["columns"]
    values = systems["values"]
    page = matrix(client, CODELIST_SYSTEMS, columnIds=[s1])
    c1 = row(page, "C1")
    version = c1["relationSetVersion"]
    claim = {"expectedRelationSetVersion": version, "relationSetDirection": "outgoing"}
    linked = link(
        client, "reference-has-system-representation", systems["codelists"]["C1"], values["V2"], **claim
    )
    assert linked["relationSetVersion"] == version + 1
    # A second write from the same stale read is refused and creates nothing.
    stale = link(
        client, "reference-has-system-representation", systems["codelists"]["C1"], values["V4"], 409, **claim
    )
    assert stale["code"] == "RELATION_SET_VERSION_CONFLICT"
    assert stale["details"] == {
        "anchorObjectId": systems["codelists"]["C1"]["id"],
        "direction": "outgoing",
        "relationSetVersion": version + 1,
    }
    after = matrix(client, CODELIST_SYSTEMS, columnIds=[s1])
    assert cells(after)["C1"]["S1"] == ("several", ["V1", "V2"])
    assert row(after, "C1")["relationSetVersion"] == version + 1
    # Half a claim is refused.
    half = link(
        client,
        "reference-has-system-representation",
        systems["codelists"]["C2"],
        values["V4"],
        422,
        expectedRelationSetVersion=0,
    )
    assert half["code"] == "RELATION_SET_CLAIM_INCOMPLETE"

    # unlink with the relation's version and the row's set version.
    v1 = cell(after, "C1", s1)["records"][0]
    stale = unlink(client, v1, 409, expectedRelationSetVersion=version, relationSetDirection="outgoing")
    assert stale["code"] == "RELATION_SET_VERSION_CONFLICT"
    assert cells(matrix(client, CODELIST_SYSTEMS, columnIds=[s1]))["C1"]["S1"] == ("several", ["V1", "V2"])
    unlink(client, v1, expectedRelationSetVersion=version + 1, relationSetDirection="outgoing")
    final = matrix(client, CODELIST_SYSTEMS, columnIds=[s1])
    assert cells(final)["C1"]["S1"] == ("one", ["V2"])
    assert row(final, "C1")["relationSetVersion"] == version + 2

    # Incoming, many-to-many: the row is the relation's to end.
    m1 = systems["masters"]["SM1"]
    mapped = matrix(client, MASTER_SYSTEMS, columnIds=[s1])
    claim = {"expectedRelationSetVersion": row(mapped, "SM1")["relationSetVersion"], "relationSetDirection": "incoming"}
    link(client, "system-value-maps-to-master", values["V1"], m1, **claim)
    link(client, "system-value-maps-to-master", values["V2"], m1, 409, **claim)
    mapped = matrix(client, MASTER_SYSTEMS, columnIds=[s1])
    assert cells(mapped)["SM1"]["S1"] == ("one", ["V1"])
    unlink(
        client,
        cell(mapped, "SM1", s1)["records"][0],
        expectedRelationSetVersion=row(mapped, "SM1")["relationSetVersion"],
        relationSetDirection="incoming",
    )
    assert cells(matrix(client, MASTER_SYSTEMS, columnIds=[s1]))["SM1"]["S1"] == ("none", [])


def test_change_set_cell_writes_publish(client, languages, systems):
    de = languages["columns"][2]
    change_set = create_change_set(client, "default", name="cells", source="currentLive").json()
    context = {"changeSetId": change_set["id"]}
    de_group = create(
        client,
        "rdm-translations",
        "translation-group",
        "Group de",
        [attr("group-code", "de")],
        parent=languages["language"]["de"],
        changeSetId=change_set["id"],
        expectedChangeSetVersion=change_set["version"],
    )
    assert helper(client, "containers", TRANSLATIONS, columnId=de, **context)["defaultContainerId"] == de_group["id"]
    staged = client.post(
        "/api/v1/objects",
        json=translation_payload(
            "M2 de",
            de_group,
            languages["masters"]["M2"],
            changeSetId=change_set["id"],
            expectedChangeSetVersion=de_group["changeSetVersion"],
        ),
    )
    assert staged.status_code == 201, staged.text
    version = staged.json()["changeSetVersion"]
    in_change_set = matrix(client, TRANSLATIONS, columnIds=[de], **context)
    assert cells(in_change_set)["M2"]["Language de"] == ("one", ["M2 de"])
    # The change set's own set version advanced; live saw nothing.
    assert row(in_change_set, "M2")["relationSetVersion"] == 1
    assert cells(matrix(client, TRANSLATIONS, columnIds=[de]))["M2"]["Language de"] == ("none", [])

    # A staged duplicate is held by the change set (H4c): the matrix shows both, and it is removed
    # again before publishing, which would refuse it.
    duplicate = client.post(
        "/api/v1/objects",
        json=translation_payload(
            "M2 de again",
            de_group,
            languages["masters"]["M2"],
            changeSetId=change_set["id"],
            expectedChangeSetVersion=version,
        ),
    )
    assert duplicate.status_code == 201, duplicate.text
    held = cells(matrix(client, TRANSLATIONS, columnIds=[de], **context))["M2"]["Language de"]
    assert held[0] == "several", held
    removal = {
        "changeSetId": change_set["id"],
        "expectedVersion": duplicate.json()["version"],
        "expectedChangeSetVersion": duplicate.json()["changeSetVersion"],
    }
    path = f"/api/v1/objects/translation/{duplicate.json()['id']}"
    preview = client.delete(path, params=removal).json()["error"]["details"]
    removed = client.delete(
        path,
        params={**removal, "cascade": "true", "deletionPreviewToken": preview["deletionPreviewToken"]},
    )
    assert removed.status_code == 204, removed.text
    version = client.get(f"/api/v1/change-sets/{change_set['id']}").json()["version"]

    # A link in the change set claims the change set's set version.
    s1 = systems["columns"][0]
    c2 = systems["codelists"]["C2"]
    set_version = row(matrix(client, CODELIST_SYSTEMS, columnIds=[s1], **context), "C2")["relationSetVersion"]
    claim = {
        "expectedRelationSetVersion": set_version,
        "relationSetDirection": "outgoing",
        "changeSetId": change_set["id"],
    }
    linked = link(
        client,
        "reference-has-system-representation",
        c2,
        systems["values"]["V2"],
        expectedChangeSetVersion=version,
        **claim,
    )
    assert linked["relationSetVersion"] == set_version + 1
    stale = link(
        client,
        "reference-has-system-representation",
        c2,
        systems["values"]["V4"],
        409,
        expectedChangeSetVersion=linked["changeSetVersion"],
        **claim,
    )
    assert stale["code"] == "RELATION_SET_VERSION_CONFLICT"
    staged_link = cell(matrix(client, CODELIST_SYSTEMS, columnIds=[s1], **context), "C2", s1)
    assert staged_link["state"] == "one"
    unlink(
        client,
        staged_link["records"][0],
        changeSetId=change_set["id"],
        expectedChangeSetVersion=linked["changeSetVersion"],
        expectedRelationSetVersion=set_version + 1,
        relationSetDirection="outgoing",
    )
    relinked = link(
        client,
        "reference-has-system-representation",
        c2,
        systems["values"]["V2"],
        expectedChangeSetVersion=linked["changeSetVersion"] + 1,
        **{**claim, "expectedRelationSetVersion": set_version + 2},
    )

    assert validate_change_set(client, change_set["id"])["valid"] is True
    publish_change_set(client, change_set["id"], expected_change_set_version=relinked["changeSetVersion"])
    assert cells(matrix(client, TRANSLATIONS, columnIds=[de]))["M2"]["Language de"] == ("one", ["M2 de"])
    assert cells(matrix(client, CODELIST_SYSTEMS, columnIds=[s1]))["C2"]["S1"] == ("one", ["V2"])


def change_set_exists(client, change_set_id):
    return client.get(f"/api/v1/change-sets/{change_set_id}").status_code == 200


def test_staged_translation_then_filled_live_is_refused_at_publish(client, languages):
    cs = languages["columns"][1]
    group, m2 = languages["groups"]["cs"], languages["masters"]["M2"]
    change_set = create_change_set(client, "default", name="staged", source="currentLive").json()
    staged = client.post(
        "/api/v1/objects",
        json=translation_payload(
            "M2 cs staged", group, m2, changeSetId=change_set["id"], expectedChangeSetVersion=change_set["version"]
        ),
    )
    assert staged.status_code == 201, staged.text
    live = client.post("/api/v1/objects", json=translation_payload("M2 cs live", group, m2))
    assert live.status_code == 201, live.text

    refused = publish_change_set(
        client,
        change_set["id"],
        expected_change_set_version=staged.json()["changeSetVersion"],
        expected_status=422,
    ).json()["error"]
    assert refused["code"] == "WORKSPACE_GRAPH_INVALID"
    (diagnostic,) = refused["details"]
    assert diagnostic["code"] == "DUPLICATE_RELATION_SCOPE"
    assert diagnostic["details"]["conflictingObjectId"] in {live.json()["id"], staged.json()["id"]}
    # Nothing was published; the change set and its staged record are kept.
    assert cells(matrix(client, TRANSLATIONS, columnIds=[cs]))["M2"]["Language cs"] == ("one", ["M2 cs live"])
    assert change_set_exists(client, change_set["id"])
    kept = matrix(client, TRANSLATIONS, columnIds=[cs], changeSetId=change_set["id"])
    assert cells(kept)["M2"]["Language cs"] == ("one", ["M2 cs staged"])


def test_moving_a_container_to_another_column_is_rechecked(client, languages):
    en, cs, _ = languages["columns"]
    groups, records = languages["groups"], languages["records"]
    # M1 gets an active CS translation; its EN one sits in the nested group.
    cs_record = client.post(
        "/api/v1/objects", json=translation_payload("M1 cs", groups["cs"], languages["masters"]["M1"])
    )
    assert cs_record.status_code == 201, cs_record.text
    # Live: moving the nested group under CS would put two active translations there.
    breach = patch(client, groups["nested"], 409, parentObjectId=groups["cs"]["id"])
    assert breach["code"] == "DUPLICATE_RELATION_SCOPE"
    assert breach["details"]["conflictingObjectId"] in {records["M1 en"]["id"], cs_record.json()["id"]}
    assert cells(matrix(client, TRANSLATIONS, columnIds=[en]))["M1"]["Language en"] == ("one", ["M1 en"])

    # In a change set the move is staged, shows as a conflict, and publishing refuses it.
    change_set = create_change_set(client, "default", name="move", source="currentLive").json()
    moved = patch(
        client,
        groups["nested"],
        parentObjectId=groups["cs"]["id"],
        changeSetId=change_set["id"],
        expectedChangeSetVersion=change_set["version"],
    )
    staged = matrix(client, TRANSLATIONS, columnIds=[en, cs], changeSetId=change_set["id"])
    assert cells(staged)["M1"] == {
        "Language en": ("none", []),
        "Language cs": ("several", ["M1 cs", "M1 en"]),
    }
    assert cell(staged, "M1", cs)["conflict"] is True
    diagnostics = validate_change_set(client, change_set["id"])
    assert diagnostics["valid"] is False
    diagnostic = next(item for item in diagnostics["diagnostics"] if item["code"] == "DUPLICATE_RELATION_SCOPE")
    assert diagnostic["details"]["ancestorObjectId"] == cs
    assert diagnostic["details"]["conflictingObjectId"] in {records["M1 en"]["id"], cs_record.json()["id"]}
    publish_change_set(
        client, change_set["id"], expected_change_set_version=moved["changeSetVersion"], expected_status=422
    )
    assert change_set_exists(client, change_set["id"])
    assert cells(matrix(client, TRANSLATIONS, columnIds=[en]))["M1"]["Language en"] == ("one", ["M1 en"])


@pytest.fixture
def scoped_client(tmp_path, monkeypatch, migrated_database):
    """The starter model with a system value unique per system for a codelist while active, so a
    link can meet the binding's uniqueness scope."""
    model = json.loads(STARTER.read_text())
    for binding in model["objectTypeRelations"]:
        if (binding["relationTypeKey"], binding["fromObjectTypeKey"]) == (
            "reference-has-system-representation",
            "codelist",
        ):
            binding["features"] = {
                "uniqueToAncestorTypeKey": "system",
                "uniqueWhenToAttributeEquals": {"attributeTypeKey": "active", "value": True},
            }
    yield from serve(model, tmp_path, monkeypatch, migrated_database("matrix-scoped.db"))


def test_a_scope_held_by_the_row_is_a_candidate_reason(scoped_client):
    client = scoped_client
    domain = create(client, "rdm-master", "domain", "Domain", [attr("domain-code", "D")])
    codelist = create(client, "rdm-master", "codelist", "C1", [attr("codelist-code", "C1")], parent=domain)
    system = create(client, "rdm-systems", "system", "S1", [attr("system-code", "s1")])
    values = {
        name: create(
            client,
            "rdm-systems",
            "system-value",
            name,
            [attr("value-code", name), attr("value-name", name), attr("active", active)],
            parent=system,
        )
        for name, active in (("V1", True), ("V2", True), ("V3", False))
    }
    relate(client, "reference-has-system-representation", codelist, values["V1"])
    page = helper(client, "link-candidates", CODELIST_SYSTEMS, rowId=codelist["id"], columnId=system["id"])
    # V2 is active like V1, which already fills the scope; inactive V3 is outside it.
    assert candidates(page) == {"V1": "alreadyLinked", "V2": "scopeTaken", "V3": None}
    refused = link(client, "reference-has-system-representation", codelist, values["V2"], 409)
    assert refused["code"] == "DUPLICATE_RELATION_SCOPE"
    assert refused["details"]["conflictingObjectId"] == values["V1"]["id"]
    link(client, "reference-has-system-representation", codelist, values["V3"])
