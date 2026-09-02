from uuid import uuid4

from fastapi.testclient import TestClient

from app.main import app


def test_model_object_hierarchy_and_relation_vertical_slice():
    with TestClient(app) as client:
        model_response = client.get("/api/v1/model")
        assert model_response.status_code == 200
        assert model_response.json()["schemaVersion"] == "0.3"
        assert model_response.json()["applications"][0]["details"][0]["panels"][0]["type"] == (
            "children"
        )

        suffix = uuid4().hex[:8]
        domain_response = client.post(
            "/api/v1/objects/domain",
            json={
                "applicationKey": "rdm-master",
                "name": f"Connections {suffix}",
                "attributes": {"domain-code": f"CONNECTIONS_{suffix}"},
            },
        )
        assert domain_response.status_code == 201
        domain = domain_response.json()
        assert domain["attributes"]["active"] is True

        codelist_response = client.post(
            "/api/v1/objects/codelist",
            json={
                "applicationKey": "rdm-master",
                "parentObjectId": domain["id"],
                "name": f"Timetable type {suffix}",
                "attributes": {"codelist-code": f"MOT_{suffix}"},
            },
        )
        assert codelist_response.status_code == 201
        codelist = codelist_response.json()
        assert codelist["parentObjectId"] == domain["id"]
        assert [part["name"] for part in codelist["path"]] == [
            domain["name"],
            codelist["name"],
        ]

        list_response = client.get(
            "/api/v1/objects/domain",
            params={"pageSize": 1, "applicationKey": "rdm-master"},
        )
        assert list_response.status_code == 200
        assert len(list_response.json()["items"]) == 1

        second_domain_response = client.post(
            "/api/v1/objects/domain",
            json={
                "applicationKey": "rdm-master",
                "name": f"Connections second {suffix}",
                "attributes": {"domain-code": f"CONNECTIONS_SECOND_{suffix}"},
            },
        )
        assert second_domain_response.status_code == 201
        search_page = client.get(
            "/api/v1/objects/domain",
            params={
                "pageSize": 1,
                "applicationKey": "rdm-master",
                "search": suffix,
            },
        ).json()
        assert len(search_page["items"]) == 1
        assert search_page["nextCursor"] is not None
        next_search_page = client.get(
            "/api/v1/objects/domain",
            params={
                "pageSize": 1,
                "applicationKey": "rdm-master",
                "search": suffix,
                "cursor": search_page["nextCursor"],
            },
        ).json()
        assert len(next_search_page["items"]) == 1
        assert next_search_page["items"][0]["id"] != search_page["items"][0]["id"]

        relation_response = client.get("/api/v1/relations", params={"objectId": domain["id"]})
        assert relation_response.status_code == 200
        assert relation_response.json()[0]["relation"]["relationTypeKey"] == (
            "domain-contains-codelist"
        )

        update_response = client.patch(
            f"/api/v1/objects/domain/{domain['id']}",
            json={"attributes": {"description": "Updated"}, "expectedVersion": 1},
        )
        assert update_response.status_code == 200
        assert update_response.json()["version"] == 2

        stale_response = client.patch(
            f"/api/v1/objects/domain/{domain['id']}",
            json={"name": "Stale write", "expectedVersion": 1},
        )
        assert stale_response.status_code == 409

        system_response = client.post(
            "/api/v1/objects/system",
            json={
                "applicationKey": "rdm-systems",
                "name": f"System {suffix}",
                "attributes": {"system-code": f"SYS_{suffix}"},
            },
        )
        assert system_response.status_code == 201
        system = system_response.json()
        delete_response = client.delete(
            f"/api/v1/objects/system/{system['id']}", params={"expectedVersion": 1}
        )
        assert delete_response.status_code == 204
