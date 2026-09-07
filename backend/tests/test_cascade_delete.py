from uuid import uuid4

from test_api import DraftTestClient

from app.main import app

TestClient = DraftTestClient


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


def test_non_cascade_retirement_returns_recursive_child_impact_without_mutating():
    with TestClient(app) as client:
        domain, codelist, master, _system, _system_value, _relation = _create_graph(client)

        response = client.delete(
            f"/api/v1/objects/domain/{domain['id']}", params={"expectedVersion": 1}
        )

        assert response.status_code == 409
        error = response.json()["error"]
        assert error["code"] == "object_has_dependants"
        assert error["details"]["objectCount"] == 3
        assert error["details"]["retainedAssociationCount"] == 1
        assert {item["id"] for item in error["details"]["objectsToRetire"]} == {
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


def test_retirement_retains_optional_non_parent_relation_and_related_identity():
    with TestClient(app) as client:
        _domain, _codelist, master, _system, system_value, relation = _create_graph(client)

        retired = client.delete(
            f"/api/v1/objects/master-value/{master['id']}", params={"expectedVersion": 1}
        )
        assert retired.status_code == 204
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
        assert preview.json()["error"]["details"]["objectCount"] == 3

        deleted = client.delete(
            f"/api/v1/objects/domain/{domain['id']}",
            params={"expectedVersion": 1, "cascade": True},
        )
        assert deleted.status_code == 204
        assert client.get(f"/api/v1/objects/system-value/{system_value['id']}").status_code == 200
        assert client.get(f"/api/v1/relations/{representation['id']}").status_code == 404


def test_cascade_deletes_required_single_valued_fk_dependent():
    """The starter's Translation ownership binding is the real required one-to-many case."""
    with TestClient(app) as client:
        suffix = uuid4().hex[:8]
        language = client.post(
            "/api/v1/objects",
            json={
                "applicationKey": "rdm-translations",
                "objectTypeKey": "language",
                "name": f"Language {suffix}",
                "attributes": [_attr("language-code", f"L_{suffix}")],
            },
        ).json()
        group = client.post(
            "/api/v1/objects",
            json={
                "applicationKey": "rdm-translations",
                "objectTypeKey": "translation-group",
                "name": f"Group {suffix}",
                "parentObjectId": language["id"],
                "attributes": [_attr("group-code", f"G_{suffix}")],
            },
        ).json()
        domain = client.post(
            "/api/v1/objects",
            json={
                "applicationKey": "rdm-master",
                "objectTypeKey": "domain",
                "name": f"Domain {suffix}",
                "attributes": [_attr("domain-code", f"D_{suffix}")],
            },
        ).json()
        translation = client.post(
            "/api/v1/objects",
            json={
                "applicationKey": "rdm-translations",
                "objectTypeKey": "translation",
                "name": f"Translation {suffix}",
                "parentObjectId": group["id"],
                "attributes": [_attr("translated-name", "Translated")],
                "initialRelations": [{"relationTypeKey": "object-has-translation", "direction": "incoming", "otherObjectId": domain["id"]}],
            },
        ).json()
        preview = client.delete(f"/api/v1/objects/domain/{domain['id']}", params={"expectedVersion": 1})
        assert preview.status_code == 409
        dependent = next(item for item in preview.json()["error"]["details"]["objectsToRetire"] if item["id"] == translation["id"])
        assert dependent["reason"] == "required-ownership"
        deleted = client.delete(f"/api/v1/objects/domain/{domain['id']}", params={"expectedVersion": 1, "cascade": True})
        assert deleted.status_code == 204
        assert client.get(f"/api/v1/objects/translation/{translation['id']}").status_code == 404
