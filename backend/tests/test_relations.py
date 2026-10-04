from uuid import uuid4

import pytest
from fastapi.testclient import TestClient as HttpTestClient
from test_api import ChangeSetTestClient

from app.db import SessionLocal
from app.engine.model.loader import load_bootstrap_model
from app.engine.model.releases import install_model_release
from app.main import app

TestClient = ChangeSetTestClient


def _attr(key: str, value):
    return {"attributeTypeKey": key, "value": value}


def _suffix():
    return uuid4().hex[:8]


def _relation_path(relation_id: str) -> str:
    return f"/api/v1/relations/{relation_id}"


@pytest.fixture
def mapping_relation_attributes(monkeypatch):
    model = load_bootstrap_model()
    object_type_relations = tuple(
        item.model_copy(update={"attributeTypeKeys": ("sort-order",)})
        if item.relationTypeKey == "system-value-maps-to-master"
        else item
        for item in model.objectTypeRelations
    )
    model = model.model_copy(
        update={
            "objectTypeRelations": object_type_relations,
            "release": model.release.model_copy(update={"version": f"relation-attrs-{_suffix()}"}),
        }
    )
    # Install an immutable fixture release so active and pinned resolution share its real hash.
    with HttpTestClient(app), SessionLocal() as session:
        release, _created = install_model_release(session, model)
        session.commit()
        release_id = release.public_id
    monkeypatch.setattr(ChangeSetTestClient, "model_release_id", release_id)


def _create_domain(client, suffix):
    response = client.post(
        "/api/v1/objects",
        json={
            "applicationKey": "rdm-master",
            "objectTypeKey": "domain",
            "name": f"Domain {suffix}",
            "attributes": [_attr("domain-code", f"DOM_{suffix}")],
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def _create_codelist(client, suffix, parent_id):
    response = client.post(
        "/api/v1/objects",
        json={
            "applicationKey": "rdm-master",
            "objectTypeKey": "codelist",
            "parentObjectId": parent_id,
            "name": f"Codelist {suffix}",
            "attributes": [_attr("codelist-code", f"CL_{suffix}")],
        },
    )
    assert response.status_code == 201
    return response.json()


def _create_master_value(client, suffix, codelist_id):
    response = client.post(
        "/api/v1/objects",
        json={
            "applicationKey": "rdm-master",
            "objectTypeKey": "master-value",
            "parentObjectId": codelist_id,
            "name": f"Master {suffix}",
            "attributes": [
                _attr("master-id", f"MID_{suffix}"),
                _attr("value-code", f"VC_{suffix}"),
                _attr("value-name", f"Value {suffix}"),
            ],
        },
    )
    assert response.status_code == 201
    return response.json()


def _create_system_value(client, suffix):
    system_response = client.post(
        "/api/v1/objects",
        json={
            "applicationKey": "rdm-systems",
            "objectTypeKey": "system",
            "name": f"System {suffix}",
            "attributes": [_attr("system-code", f"SYS_{suffix}")],
        },
    )
    assert system_response.status_code == 201
    system = system_response.json()
    value_response = client.post(
        "/api/v1/objects",
        json={
            "applicationKey": "rdm-systems",
            "objectTypeKey": "system-value",
            "parentObjectId": system["id"],
            "name": f"System value {suffix}",
            "attributes": [
                _attr("value-code", f"SVC_{suffix}"),
                _attr("value-name", f"System value {suffix}"),
            ],
        },
    )
    assert value_response.status_code == 201
    return value_response.json()


def _mapping_endpoints(client, suffix):
    domain = _create_domain(client, suffix)
    codelist = _create_codelist(client, suffix, domain["id"])
    master = _create_master_value(client, suffix, codelist["id"])
    system_value = _create_system_value(client, suffix)
    return system_value, master


def _create_mapping(client, suffix) -> dict:
    """Build both hierarchies and link them with the mutable mapping relation."""
    system_value, master = _mapping_endpoints(client, suffix)
    response = client.post(
        "/api/v1/relations",
        json={
            "relationTypeKey": "system-value-maps-to-master",
            "fromObjectId": system_value["id"],
            "toObjectId": master["id"],
        },
    )
    assert response.status_code == 201
    return response.json()


def _parent_relation_id(client, codelist_id: str) -> str:
    """Return the id of the engine-maintained `domain-contains-codelist` relation."""
    response = client.get("/api/v1/relations", params={"objectId": codelist_id})
    assert response.status_code == 200
    relations = [
        item["relation"]
        for item in response.json()["items"]
        if item["relation"]["relationTypeKey"] == "domain-contains-codelist"
    ]
    assert len(relations) == 1
    return relations[0]["id"]


# --- GET single relation ---


def test_get_relation_by_id_returns_stored_relation():
    with TestClient(app) as client:
        mapping = _create_mapping(client, _suffix())
        response = client.get(_relation_path(mapping["id"]))
        assert response.status_code == 200
        body = response.json()
        assert body["id"] == mapping["id"]
        assert body["relationTypeKey"] == "system-value-maps-to-master"
        assert body["fromObjectId"] == mapping["fromObjectId"]
        assert body["toObjectId"] == mapping["toObjectId"]
        assert body["attributes"] == {}
        assert body["version"] == 1


def test_get_relation_by_id_returns_404_when_unknown():
    with TestClient(app) as client:
        response = client.get(_relation_path(str(uuid4())))
        assert response.status_code == 404
        assert response.json()["error"]["code"] == "RELATION_NOT_FOUND"


def test_get_engine_maintained_relation_is_readable():
    with TestClient(app) as client:
        domain = _create_domain(client, _suffix())
        codelist = _create_codelist(client, _suffix(), domain["id"])
        relation_id = _parent_relation_id(client, codelist["id"])
        response = client.get(_relation_path(relation_id))
        assert response.status_code == 200
    assert response.json()["relationTypeKey"] == "domain-contains-codelist"


def test_domain_and_codelist_share_exclusive_system_representation_relation():
    with TestClient(app) as client:
        suffix = _suffix()
        domain = _create_domain(client, suffix)
        codelist = _create_codelist(client, suffix, domain["id"])
        system_value = _create_system_value(client, suffix)

        created = client.post(
            "/api/v1/relations",
            json={
                "relationTypeKey": "reference-has-system-representation",
                "fromObjectId": domain["id"],
                "toObjectId": system_value["id"],
            },
        )
        assert created.status_code == 201

        incoming = client.get("/api/v1/relations", params={"objectId": system_value["id"]})
        assert incoming.status_code == 200
        assert any(
            item["relation"]["id"] == created.json()["id"]
            and item["direction"] == "incoming"
            for item in incoming.json()["items"]
        )

        conflicting = client.post(
            "/api/v1/relations",
            json={
                "relationTypeKey": "reference-has-system-representation",
                "fromObjectId": codelist["id"],
                "toObjectId": system_value["id"],
            },
        )
        assert conflicting.status_code == 409
        assert conflicting.json()["error"]["code"] == "CARDINALITY_VIOLATION"


# --- PATCH ---


def test_update_relation_attributes_and_bumps_version(mapping_relation_attributes):
    with TestClient(app) as client:
        mapping = _create_mapping(client, _suffix())
        response = client.patch(
            _relation_path(mapping["id"]),
            json={"attributes": {"sort-order": 9}, "expectedVersion": 1},
        )
        assert response.status_code == 200
        body = response.json()
        assert body["version"] == 2
        assert body["attributes"] == {"sort-order": 9}

        again = client.patch(
            _relation_path(mapping["id"]),
            json={"attributes": {}, "expectedVersion": 2},
        )
        assert again.status_code == 200
        assert again.json()["version"] == 3
        assert again.json()["attributes"] == {}


def test_relation_attributes_must_be_declared_by_the_allowed_pair():
    with TestClient(app) as client:
        mapping = _create_mapping(client, _suffix())
        response = client.patch(
            _relation_path(mapping["id"]),
            json={"attributes": {"confidence": 0.9}, "expectedVersion": 1},
        )
        assert response.status_code == 422
        assert response.json()["error"]["code"] == "UNKNOWN_RELATION_ATTRIBUTES"
        assert client.get(_relation_path(mapping["id"])).json()["version"] == 1


def test_create_relation_rejects_undeclared_attributes():
    with TestClient(app) as client:
        system_value, master = _mapping_endpoints(client, _suffix())
        response = client.post(
            "/api/v1/relations",
            json={
                "relationTypeKey": "system-value-maps-to-master",
                "fromObjectId": system_value["id"],
                "toObjectId": master["id"],
                "attributes": {"confidence": 0.9},
            },
        )
        assert response.status_code == 422
        assert response.json()["error"]["code"] == "UNKNOWN_RELATION_ATTRIBUTES"


def test_relation_attributes_use_the_declared_value_type(mapping_relation_attributes):
    with TestClient(app) as client:
        mapping = _create_mapping(client, _suffix())
        response = client.patch(
            _relation_path(mapping["id"]),
            json={"attributes": {"sort-order": "nine"}, "expectedVersion": 1},
        )
        assert response.status_code == 422
        assert response.json()["error"]["code"] == "INVALID_ATTRIBUTE_VALUE"
        assert client.get(_relation_path(mapping["id"])).json()["version"] == 1


def test_update_relation_rejects_stale_version():
    with TestClient(app) as client:
        mapping = _create_mapping(client, _suffix())
        response = client.patch(
            _relation_path(mapping["id"]),
            json={"attributes": {"confidence": 0.9}, "expectedVersion": 99},
        )
        assert response.status_code == 409
        assert response.json()["error"]["code"] == "VERSION_CONFLICT"


def test_update_relation_returns_404_when_unknown():
    with TestClient(app) as client:
        response = client.patch(
            _relation_path(str(uuid4())),
            json={"attributes": {}, "expectedVersion": 1},
        )
        assert response.status_code == 404
        assert response.json()["error"]["code"] == "RELATION_NOT_FOUND"


def test_update_relation_rejects_extra_fields():
    with TestClient(app) as client:
        mapping = _create_mapping(client, _suffix())
        response = client.patch(
            _relation_path(mapping["id"]),
            json={"attributes": {}, "expectedVersion": 1, "unexpected": "field"},
        )
        assert response.status_code == 422
        assert response.json()["error"]["code"] == "REQUEST_VALIDATION_ERROR"


def test_update_engine_maintained_relation_is_rejected():
    with TestClient(app) as client:
        domain = _create_domain(client, _suffix())
        codelist = _create_codelist(client, _suffix(), domain["id"])
        relation_id = _parent_relation_id(client, codelist["id"])
        response = client.patch(
            _relation_path(relation_id),
            json={"attributes": {}, "expectedVersion": 1},
        )
        assert response.status_code == 422
        assert response.json()["error"]["code"] == "IMMUTABLE_RELATION"


# --- DELETE ---


def test_delete_relation_removes_it():
    with TestClient(app) as client:
        mapping = _create_mapping(client, _suffix())
        response = client.delete(_relation_path(mapping["id"]), params={"expectedVersion": 1})
        assert response.status_code == 204

        get_response = client.get(_relation_path(mapping["id"]))
        assert get_response.status_code == 404
        assert get_response.json()["error"]["code"] == "RELATION_NOT_FOUND"


def test_delete_relation_rejects_stale_version():
    with TestClient(app) as client:
        mapping = _create_mapping(client, _suffix())
        response = client.delete(_relation_path(mapping["id"]), params={"expectedVersion": 99})
        assert response.status_code == 409
        assert response.json()["error"]["code"] == "VERSION_CONFLICT"


def test_delete_relation_returns_404_when_unknown():
    with TestClient(app) as client:
        response = client.delete(_relation_path(str(uuid4())), params={"expectedVersion": 1})
        assert response.status_code == 404
        assert response.json()["error"]["code"] == "RELATION_NOT_FOUND"


def test_delete_engine_maintained_relation_is_rejected():
    with TestClient(app) as client:
        domain = _create_domain(client, _suffix())
        codelist = _create_codelist(client, _suffix(), domain["id"])
        relation_id = _parent_relation_id(client, codelist["id"])
        response = client.delete(_relation_path(relation_id), params={"expectedVersion": 1})
        assert response.status_code == 422
        assert response.json()["error"]["code"] == "IMMUTABLE_RELATION"


# --- POST immutability guard ---


def test_create_engine_maintained_relation_is_rejected():
    with TestClient(app) as client:
        domain = _create_domain(client, _suffix())
        codelist = _create_codelist(client, _suffix(), domain["id"])
        response = client.post(
            "/api/v1/relations",
            json={
                "relationTypeKey": "domain-contains-codelist",
                "fromObjectId": domain["id"],
                "toObjectId": codelist["id"],
            },
        )
        assert response.status_code == 422
        assert response.json()["error"]["code"] == "IMMUTABLE_RELATION"
        # The atomic relation created on child add is still the only one present.
        assert len(_parent_relation_id(client, codelist["id"])) > 0


def test_duplicate_initial_relations_return_a_conflict_without_leaving_an_orphan():
    with TestClient(app) as client:
        suffix = _suffix()
        domain = _create_domain(client, suffix)
        codelist = _create_codelist(client, suffix, domain["id"])
        master = _create_master_value(client, suffix, codelist["id"])
        system_response = client.post(
            "/api/v1/objects",
            json={
                "applicationKey": "rdm-systems",
                "objectTypeKey": "system",
                "name": f"System {suffix}",
                "attributes": [_attr("system-code", f"SYS_INITIAL_{suffix}")],
            },
        )
        assert system_response.status_code == 201
        public_id = str(uuid4())
        initial_relation = {
            "relationTypeKey": "system-value-maps-to-master",
            "direction": "outgoing",
            "otherObjectId": master["id"],
        }

        response = client.post(
            "/api/v1/objects",
            json={
                "id": public_id,
                "applicationKey": "rdm-systems",
                "objectTypeKey": "system-value",
                "parentObjectId": system_response.json()["id"],
                "name": f"System value {suffix}",
                "attributes": [
                    _attr("value-code", f"SVC_INITIAL_{suffix}"),
                    _attr("value-name", f"System value {suffix}"),
                ],
                "initialRelations": [initial_relation, initial_relation],
            },
        )

        assert response.status_code == 422
        assert response.json()["error"]["code"] == "DUPLICATE_INITIAL_RELATION"
        assert client.get(f"/api/v1/objects/system-value/{public_id}").status_code == 404


# --- service-level concurrency guard ---


def test_relation_version_claim_rejects_a_relation_loaded_before_a_competing_write():
    with TestClient(app) as client:
        mapping = _create_mapping(client, _suffix())
        winner = client.patch(
            _relation_path(mapping["id"]),
            json={"attributes": {}, "expectedVersion": mapping["version"]},
        )
        assert winner.status_code == 200
        loser = client.patch(
            _relation_path(mapping["id"]),
            json={"attributes": {}, "expectedVersion": mapping["version"]},
        )
        assert loser.status_code == 409
        assert loser.json()["error"]["code"] == "VERSION_CONFLICT"
