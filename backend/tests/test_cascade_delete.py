from uuid import uuid4

from fastapi.testclient import TestClient

from app.main import app
from app.services.model.loader import load_bootstrap_model
from app.services.model.registry import ModelSnapshot, resolve_model_snapshot


def _attr(key: str, value):
    return {"attributeTypeKey": key, "value": value}


def _create_graph(client: TestClient):
    suffix = uuid4().hex[:8]
    domain = client.post(
        "/api/v1/objects",
        json={
            "applicationKey": "rdm-master",
            "objectTypeKey": "domain",
            "name": f"Domain {suffix}",
            "attributes": [_attr("domain-code", f"DOM_{suffix}")],
        },
    ).json()
    codelist = client.post(
        "/api/v1/objects",
        json={
            "applicationKey": "rdm-master",
            "objectTypeKey": "codelist",
            "parentObjectId": domain["id"],
            "name": f"Codelist {suffix}",
            "attributes": [_attr("codelist-code", f"CL_{suffix}")],
        },
    ).json()
    master = client.post(
        "/api/v1/objects",
        json={
            "applicationKey": "rdm-master",
            "objectTypeKey": "master-value",
            "parentObjectId": codelist["id"],
            "name": f"Master {suffix}",
            "attributes": [
                _attr("master-id", f"MID_{suffix}"),
                _attr("value-code", f"MVC_{suffix}"),
                _attr("value-name", f"Master {suffix}"),
            ],
        },
    ).json()
    system = client.post(
        "/api/v1/objects",
        json={
            "applicationKey": "rdm-systems",
            "objectTypeKey": "system",
            "name": f"System {suffix}",
            "attributes": [_attr("system-code", f"SYS_{suffix}")],
        },
    ).json()
    system_value = client.post(
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
    ).json()
    relation = client.post(
        "/api/v1/relations",
        json={
            "relationTypeKey": "system-value-maps-to-master",
            "fromObjectId": system_value["id"],
            "toObjectId": master["id"],
        },
    ).json()
    return domain, codelist, master, system, system_value, relation


def test_non_cascade_delete_returns_recursive_child_impact_without_mutating():
    with TestClient(app) as client:
        domain, codelist, master, _system, _system_value, _relation = _create_graph(client)

        response = client.delete(
            f"/api/v1/objects/domain/{domain['id']}", params={"expectedVersion": 1}
        )

        assert response.status_code == 409
        error = response.json()["error"]
        assert error["code"] == "object_has_dependents"
        assert error["details"]["objectCount"] == 3
        assert {item["id"] for item in error["details"]["objectsToDelete"]} == {
            codelist["id"],
            master["id"],
        }
        assert client.get(f"/api/v1/objects/domain/{domain['id']}").status_code == 200

        deleted = client.delete(
            f"/api/v1/objects/domain/{domain['id']}",
            params={"expectedVersion": 1, "cascade": True},
        )
        assert deleted.status_code == 204
        assert client.get(f"/api/v1/objects/domain/{domain['id']}").status_code == 404
        assert client.get(f"/api/v1/objects/codelist/{codelist['id']}").status_code == 404
        assert client.get(f"/api/v1/objects/master-value/{master['id']}").status_code == 404


def test_cascade_unlinks_optional_non_parent_relation_but_preserves_related_object():
    with TestClient(app) as client:
        _domain, _codelist, master, _system, system_value, relation = _create_graph(client)

        preview = client.delete(
            f"/api/v1/objects/master-value/{master['id']}", params={"expectedVersion": 1}
        )
        assert preview.status_code == 409
        relationship = preview.json()["error"]["details"]["relationshipsToRemove"][0]
        assert relationship["id"] == relation["id"]
        assert relationship["fkPk"] is False
        assert relationship["relatedObjectWillBeDeleted"] is False

        deleted = client.delete(
            f"/api/v1/objects/master-value/{master['id']}",
            params={"expectedVersion": 1, "cascade": True},
        )
        assert deleted.status_code == 204
        assert client.get(f"/api/v1/objects/system-value/{system_value['id']}").status_code == 200
        assert client.get(f"/api/v1/relations/{relation['id']}").status_code == 404


def test_cascade_deleting_reference_structure_preserves_system_representation():
    with TestClient(app) as client:
        domain, _codelist, _master, _system, system_value, _mapping = _create_graph(client)
        representation = client.post(
            "/api/v1/relations",
            json={
                "relationTypeKey": "reference-has-system-representation",
                "fromObjectId": domain["id"],
                "toObjectId": system_value["id"],
            },
        ).json()

        preview = client.delete(
            f"/api/v1/objects/domain/{domain['id']}", params={"expectedVersion": 1}
        )
        assert preview.status_code == 409
        relationship = next(
            item
            for item in preview.json()["error"]["details"]["relationshipsToRemove"]
            if item["id"] == representation["id"]
        )
        assert relationship["fkPk"] is False
        assert relationship["relatedObjectWillBeDeleted"] is False

        deleted = client.delete(
            f"/api/v1/objects/domain/{domain['id']}",
            params={"expectedVersion": 1, "cascade": True},
        )
        assert deleted.status_code == 204
        assert client.get(f"/api/v1/objects/system-value/{system_value['id']}").status_code == 200
        assert client.get(f"/api/v1/relations/{representation['id']}").status_code == 404


def test_cascade_deletes_required_single_valued_fk_dependent():
    model = load_bootstrap_model()
    dependent_relations = tuple(
        item.model_copy(update={"required": True, "cardinality": "one-to-many"})
        if item.relationTypeKey == "system-value-maps-to-master"
        else item
        for item in model.objectTypeRelations
    )
    dependent_model = model.model_copy(update={"objectTypeRelations": dependent_relations})
    active_model = model
    try:
        app.dependency_overrides[resolve_model_snapshot] = lambda: ModelSnapshot(
            release_db_id=-1,
            release_id="test-release",
            model_hash="test-hash",
            model=active_model,
        )
        with TestClient(app) as client:
            _domain, codelist, master, system, system_value, _relation = _create_graph(client)
            active_model = dependent_model
            preview = client.delete(
                f"/api/v1/objects/system-value/{system_value['id']}",
                params={"expectedVersion": 1},
            )
            assert preview.status_code == 409
            details = preview.json()["error"]["details"]
            dependent = next(
                item for item in details["objectsToDelete"] if item["id"] == master["id"]
            )
            assert dependent["reason"] == "fkDependent"

            deleted = client.delete(
                f"/api/v1/objects/system-value/{system_value['id']}",
                params={"expectedVersion": 1, "cascade": True},
            )
            assert deleted.status_code == 204
            assert client.get(f"/api/v1/objects/master-value/{master['id']}").status_code == 404
            assert client.get(f"/api/v1/objects/codelist/{codelist['id']}").status_code == 200
            assert client.get(f"/api/v1/objects/system/{system['id']}").status_code == 200
    finally:
        app.dependency_overrides.pop(resolve_model_snapshot, None)
