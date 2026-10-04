"""Base 0.8 B2: move targets and path context.

``GET /objects/{type}/{id}/parent-candidates`` lists every record the model allows as the record's
parent, live or in a change set, with the candidates a move would refuse marked by reason (D14).
Moves themselves go through ``PATCH /objects/{type}/{id}``; these tests check that the query and
the write agree, that paths follow a move in each context, and that a cycle is refused at the query,
the write and publication. Two hierarchies of the starter model are used: systems, whose groups
nest and whose values sit under a system or a group (moves across types), and domains, codelists
and master values, whose values nest.
"""

import json
from pathlib import Path
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from wp8_support import create_change_set, create_workspace, publish_change_set

from app.config import reload_settings
from app.db import SessionLocal, get_engine
from app.engine.indexes import matrix_states
from app.engine.model.registry import model_registry
from app.main import create_app

STARTER = Path(__file__).resolve().parents[2] / "model/rdm-starter.json"
LIVE = {"workspaceKey": "default"}


@pytest.fixture
def client(tmp_path, monkeypatch, migrated_database):
    model_path = tmp_path / "model.json"
    model_path.write_text(STARTER.read_text())
    monkeypatch.setenv("DATABASE_URL", migrated_database("parent-candidates.db"))
    monkeypatch.setenv("RDM_MODEL_PATH", str(model_path))
    model_registry.clear()
    with TestClient(create_app()) as value:
        yield value
        # Moves change containers: stored matrix cell states must still equal rebuilt ones.
        with SessionLocal() as session:
            assert matrix_states.verify(session) == []
    get_engine().dispose()
    monkeypatch.undo()
    reload_settings()
    model_registry.clear()


def attr(key, value):
    return {"attributeTypeKey": key, "value": value}


CODES = {
    "system": "system-code",
    "system-group": "group-code",
    "domain": "domain-code",
    "codelist": "codelist-code",
    "language": "language-code",
    "translation-group": "group-code",
}


def create(client, application, object_type, name, parent=None, attributes=None, **context):
    if attributes is None:
        attributes = [attr(CODES[object_type], f"{name}-{uuid4().hex[:6]}")]
    payload = {
        "applicationKey": application,
        "objectTypeKey": object_type,
        "name": name,
        "attributes": attributes,
        **(context or LIVE),
    }
    if parent:
        payload["parentObjectId"] = parent["id"]
    response = client.post("/api/v1/objects", json=payload)
    assert response.status_code == 201, response.text
    return response.json()


def system_value(client, name, parent, **context):
    return create(
        client,
        "rdm-systems",
        "system-value",
        name,
        parent,
        [attr("value-code", f"{name}-{uuid4().hex[:6]}"), attr("value-name", name)],
        **context,
    )


def master_value(client, name, parent, **context):
    code = f"{name}-{uuid4().hex[:6]}"
    return create(
        client,
        "rdm-master",
        "master-value",
        name,
        parent,
        [attr("master-id", code), attr("value-code", code), attr("value-name", name)],
        **context,
    )


def candidates(client, record, expected=200, **params):
    response = client.get(
        f"/api/v1/objects/{record['objectTypeKey']}/{record['id']}/parent-candidates",
        params={**LIVE, **params} if "changeSetId" not in params else params,
    )
    assert response.status_code == expected, response.text
    body = response.json()
    return body if expected == 200 else body["error"]


def listed(page):
    """{name: reason or None} for readable assertions."""
    return {item["name"]: item["reason"] for item in page["items"]}


def read(client, record, **params):
    response = client.get(
        f"/api/v1/objects/{record['objectTypeKey']}/{record['id']}", params=params or LIVE
    )
    assert response.status_code == 200, response.text
    return response.json()


def names(path):
    return [part["name"] for part in path]


def move(client, record, parent, expected=200, **context):
    response = client.patch(
        f"/api/v1/objects/{record['objectTypeKey']}/{record['id']}",
        json={"parentObjectId": parent["id"], "expectedVersion": record["version"], **context},
    )
    assert response.status_code == expected, response.text
    return response.json() if expected == 200 else response.json()["error"]


def change_set_version(client, change_set_id):
    return client.get(f"/api/v1/change-sets/{change_set_id}").json()["version"]


def in_change_set(client, change_set_id):
    return {"changeSetId": change_set_id, "expectedChangeSetVersion": change_set_version(client, change_set_id)}


@pytest.fixture
def systems(client):
    """S1 > G1 > G2 > G3 with value V under G2, S2 > H1, and a group of another workspace."""
    records = {}
    records["S1"] = create(client, "rdm-systems", "system", "S1")
    records["S2"] = create(client, "rdm-systems", "system", "S2")
    records["G1"] = create(client, "rdm-systems", "system-group", "G1", records["S1"])
    records["G2"] = create(client, "rdm-systems", "system-group", "G2", records["G1"])
    records["G3"] = create(client, "rdm-systems", "system-group", "G3", records["G2"])
    records["H1"] = create(client, "rdm-systems", "system-group", "H1", records["S2"])
    records["V"] = system_value(client, "V", records["G2"])
    create_workspace(client, "elsewhere")
    elsewhere = {"workspaceKey": "elsewhere"}
    other = create(client, "rdm-systems", "system", "Other S", **elsewhere)
    create(client, "rdm-systems", "system-group", "Other G", other, **elsewhere)
    return records


def test_candidates_mark_self_descendant_and_current_parent(client, systems):
    page = candidates(client, systems["G2"], includeTotal=True)
    # Every system and group of the workspace, in name order; none from the other workspace.
    assert listed(page) == {
        "G1": "currentParent",
        "G2": "self",
        "G3": "descendant",
        "H1": None,
        "S1": None,
        "S2": None,
    }
    assert page["totalCount"] == 6 and page["startIndex"] == 0
    by_name = {item["name"]: item for item in page["items"]}
    assert names(by_name["G3"]["path"]) == ["S1", "G1", "G2", "G3"]
    assert [part["objectTypeKey"] for part in by_name["H1"]["path"]] == ["system", "system-group"]
    assert all(item["eligible"] is (item["reason"] is None) for item in page["items"])

    # One type at a time, and a search over names and searchable fields.
    assert listed(candidates(client, systems["G2"], parentObjectTypeKey="system")) == {"S1": None, "S2": None}
    assert listed(candidates(client, systems["G2"], search="h1")) == {"H1": None}
    code = next(item["value"] for item in systems["H1"]["attributes"] if item["attributeTypeKey"] == "group-code")
    assert listed(candidates(client, systems["G2"], search=code[-6:])) == {"H1": None}

    # Ineligible candidates keep their place across pages, so the pages add up to the total.
    first = candidates(client, systems["G2"], pageSize=4, includeTotal=True)
    second = candidates(client, systems["G2"], pageSize=4, cursor=first["nextCursor"])
    assert [item["name"] for item in first["items"] + second["items"]] == list(listed(page))
    assert second["nextCursor"] is None
    jumped = candidates(client, systems["G2"], pageSize=2, position=2, includeTotal=True)
    assert [item["name"] for item in jumped["items"]] == ["G3", "H1"] and jumped["startIndex"] == 2


def test_the_write_agrees_with_each_reason(client, systems):
    g1, g2, g3 = systems["G1"], systems["G2"], systems["G3"]
    # self and descendant are refused as cycles; the query said so first.
    assert move(client, g2, g2, 422)["code"] == "PARENT_CYCLE"
    assert move(client, g1, g3, 422)["code"] == "PARENT_CYCLE"
    assert read(client, g1)["version"] == g1["version"]
    # An eligible candidate moves the record, its edge and the paths below it together.
    moved = move(client, g2, systems["H1"])
    assert names(moved["path"]) == ["S2", "H1", "G2"]
    assert names(read(client, g3)["path"]) == ["S2", "H1", "G2", "G3"]
    edges = client.get(
        "/api/v1/relations",
        params={**LIVE, "objectId": g2["id"], "direction": "incoming", "relationTypeKey": "system-group-has-child"},
    ).json()["items"]
    assert [edge["object"]["id"] for edge in edges] == [systems["H1"]["id"]]
    # G1 no longer holds G2: G2 and G3 are now eligible for it, and H1 is G2's current parent.
    assert listed(candidates(client, g1, parentObjectTypeKey="system-group")) == {
        "G1": "self",
        "G2": None,
        "G3": None,
        "H1": None,
    }
    assert listed(candidates(client, moved, parentObjectTypeKey="system-group"))["H1"] == "currentParent"


def test_move_across_types_in_a_mixed_hierarchy(client, systems):
    value = systems["V"]
    # A value can sit under a system or a group: both types are candidates, mixed in name order.
    page = candidates(client, value, includeTotal=True)
    assert listed(page) == {"G1": None, "G2": "currentParent", "G3": None, "H1": None, "S1": None, "S2": None}
    assert page["totalCount"] == 6
    moved = move(client, value, systems["S2"])
    assert moved["parentObjectId"] == systems["S2"]["id"]
    assert names(moved["path"]) == ["S2", "V"]
    edges = client.get(
        "/api/v1/relations", params={**LIVE, "objectId": value["id"], "direction": "incoming"}
    ).json()["items"]
    assert [(edge["relation"]["relationTypeKey"], edge["object"]["name"]) for edge in edges] == [
        ("system-contains-value", "S2")
    ]
    assert listed(candidates(client, moved))["S2"] == "currentParent"


def test_value_hierarchy_of_another_application(client):
    domain = create(client, "rdm-master", "domain", "D")
    c1 = create(client, "rdm-master", "codelist", "C1", domain)
    c2 = create(client, "rdm-master", "codelist", "C2", domain)
    m1 = master_value(client, "M1", c1)
    master_value(client, "M2", m1)
    master_value(client, "M3", c2)
    assert listed(candidates(client, m1)) == {
        "C1": "currentParent",
        "C2": None,
        "M1": "self",
        "M2": "descendant",
        "M3": None,
    }
    # A codelist's only parent type is the domain; a domain has none.
    assert listed(candidates(client, c1)) == {"D": "currentParent"}
    empty = candidates(client, domain, includeTotal=True)
    assert empty["items"] == [] and empty["totalCount"] == 0


def test_refusals(client, systems):
    error = candidates(client, systems["G2"], 422, parentObjectTypeKey="system-value")
    assert error["code"] == "INVALID_PARENT_TYPE"
    assert error["details"]["permitted"] == ["system", "system-group"]
    missing = {"objectTypeKey": "system-group", "id": str(uuid4())}
    assert candidates(client, missing, 404)["code"] == "OBJECT_NOT_FOUND"
    # A record of the default workspace is not found through another one.
    assert candidates(client, systems["G2"], 404, workspaceKey="elsewhere")["code"] == "OBJECT_NOT_FOUND"
    # Named under a type it does not have: where the record is (D42, ADR-034).
    wrong_type = candidates(client, {**systems["G2"], "objectTypeKey": "system"}, 409)
    assert wrong_type["code"] == "OBJECT_TYPE_CHANGED"
    assert wrong_type["details"]["objectTypeKey"] == "system-group"
    assert candidates(client, {**systems["G2"], "objectTypeKey": "nothing"}, 404)["code"] == "UNKNOWN_OBJECT_TYPE"
    stale = candidates(client, systems["G2"], pageSize=2)
    refused = candidates(client, systems["G2"], 422, pageSize=2, cursor=stale["nextCursor"], search="S")
    assert refused["code"] == "INVALID_CURSOR"


def test_change_set_moves_paths_and_candidates(client, systems):
    change_set = create_change_set(client, "default", source="currentLive").json()
    context = {"changeSetId": change_set["id"]}
    g2, g3 = systems["G2"], systems["G3"]
    moved = move(client, g2, systems["H1"], **in_change_set(client, change_set["id"]))
    assert names(moved["path"]) == ["S2", "H1", "G2"]

    # The moved record and its untouched child read the change set's parent; live reads do not.
    assert names(read(client, g2, **context)["path"]) == ["S2", "H1", "G2"]
    assert names(read(client, g3, **context)["path"]) == ["S2", "H1", "G2", "G3"]
    page = client.get(
        "/api/v1/objects/system-group", params={**context, "parentObjectId": g2["id"]}
    ).json()
    assert [names(item["path"]) for item in page["items"]] == [["S2", "H1", "G2", "G3"]]
    assert names(read(client, g3)["path"]) == ["S1", "G1", "G2", "G3"]

    # Candidates follow the change set: G2 is no longer under G1.
    assert listed(candidates(client, systems["G1"], **context)) == {
        "G1": "self",
        "G2": None,
        "G3": None,
        "H1": None,
        "S1": "currentParent",
        "S2": None,
    }
    assert listed(candidates(client, systems["G1"]))["G2"] == "descendant"
    assert listed(candidates(client, g2, **context))["H1"] == "currentParent"
    # A cycle is refused in the change set too, and the change set keeps its move.
    refused = move(client, read(client, systems["H1"], **context), g3, 422, **in_change_set(client, change_set["id"]))
    assert refused["code"] == "PARENT_CYCLE"

    # Published, the new publication and live both carry the new paths.
    published = publish_change_set(
        client, change_set["id"], expected_change_set_version=change_set_version(client, change_set["id"])
    ).json()
    publication = {"publicationId": published["id"]}
    assert names(read(client, g3, **publication)["path"]) == ["S2", "H1", "G2", "G3"]
    assert names(read(client, g3)["path"]) == ["S2", "H1", "G2", "G3"]


def test_a_move_live_made_cyclic_is_refused_at_publication(client, systems):
    a = create(client, "rdm-systems", "system-group", "A", systems["S1"])
    b = create(client, "rdm-systems", "system-group", "B", systems["S1"])
    change_set = create_change_set(client, "default", source="currentLive").json()
    context = {"changeSetId": change_set["id"]}
    # The change set puts A under B: valid in its graph.
    assert listed(candidates(client, a, **context))["B"] is None
    move(client, a, b, **in_change_set(client, change_set["id"]))
    # Live, B goes under A: valid in live, where A is still under S1.
    assert listed(candidates(client, b))["A"] is None
    move(client, b, a)

    refused = client.post(
        f"/api/v1/change-sets/{change_set['id']}/publication",
        json={"expectedChangeSetVersion": change_set_version(client, change_set["id"])},
    )
    assert refused.status_code == 422, refused.text
    error = refused.json()["error"]
    assert error["code"] == "WORKSPACE_GRAPH_INVALID"
    assert "CONTAINMENT_CYCLE" in {item["code"] for item in error["details"]}
    # Nothing changed: live keeps B under A, and the change set keeps A under B.
    assert names(read(client, b)["path"]) == ["S1", "A", "B"]
    assert read(client, a, **context)["parentObjectId"] == b["id"]
    kept = client.get(f"/api/v1/change-sets/{change_set['id']}")
    assert kept.status_code == 200
    assert client.get("/api/v1/workspaces/default/publications").json()["items"] == []


def test_moving_a_container_keeps_ancestor_scoped_uniqueness(client):
    """A move re-checks a scoped binding for the records under the moved one: translations are
    unique per language, and a translation group can take its translations to another language."""
    english = create(client, "rdm-translations", "language", "English")
    czech = create(client, "rdm-translations", "language", "Czech")
    en_group = create(client, "rdm-translations", "translation-group", "EN group", english)
    cs_group = create(client, "rdm-translations", "translation-group", "CS group", czech)
    cs_nested = create(client, "rdm-translations", "translation-group", "CS nested", cs_group)
    domain = create(client, "rdm-master", "domain", "Colours")

    def translation(name, group):
        return client.post(
            "/api/v1/objects",
            json={
                **LIVE,
                "applicationKey": "rdm-translations",
                "objectTypeKey": "translation",
                "name": name,
                "parentObjectId": group["id"],
                "attributes": [attr("translated-name", name), attr("active", True)],
                "initialRelations": [
                    {"relationTypeKey": "object-has-translation", "direction": "incoming", "otherObjectId": domain["id"]}
                ],
            },
        )

    assert translation("Colours en", en_group).status_code == 201
    assert translation("Barvy", cs_nested).status_code == 201
    # The nested Czech group moving under the English group would give the domain two English
    # translations: refused, and nothing moves.
    refused = move(client, cs_nested, en_group, 409)
    assert refused["code"] == "DUPLICATE_RELATION_SCOPE"
    assert read(client, cs_nested)["parentObjectId"] == cs_group["id"]
    # Within Czech, the move changes no scope and is accepted.
    other_cs = create(client, "rdm-translations", "translation-group", "CS other", czech)
    assert move(client, cs_nested, other_cs)["parentObjectId"] == other_cs["id"]


def test_openapi_documents_the_route(client):
    document = client.get("/openapi.json").json()
    operation = document["paths"]["/api/v1/objects/{object_type_key}/{object_id}/parent-candidates"]["get"]
    parameters = {item["name"] for item in operation["parameters"]}
    assert {"workspaceKey", "changeSetId", "parentObjectTypeKey", "search", "cursor", "position", "includeTotal"} <= parameters
    schema = document["components"]["schemas"]["ParentCandidate"]
    assert set(json.dumps(schema["properties"]["reason"]).split('"')) >= {"self", "descendant", "currentParent"}
