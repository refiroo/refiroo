from uuid import uuid4

from fastapi.testclient import TestClient

from app.main import app


def test_canonical_change_set_object_and_attribute_journey():
    with TestClient(app) as client:
        change_set = client.post("/api/v1/workspaces/default/change-sets", json={}).json()
        created = client.post(
            "/api/v1/objects",
            json={
                "applicationKey": "rdm-master",
                "objectTypeKey": "domain",
                "name": "WP7 domain",
                "attributes": [{"attributeTypeKey": "domain-code", "value": f"wp7-{uuid4().hex}"}],
                "changeSetId": change_set["id"],
                "expectedChangeSetVersion": 1,
            },
        )
        assert created.status_code == 201
        item = created.json()
        assert item["changeSetVersion"] == 2
        assert (
            client.get(
                "/api/v1/objects/domain", params={"changeSetId": change_set["id"]}
            ).status_code
            == 200
        )
        updated = client.patch(
            f"/api/v1/objects/domain/{item['id']}",
            json={
                "name": "WP7 renamed",
                "expectedVersion": 1,
                "changeSetId": change_set["id"],
                "expectedChangeSetVersion": 2,
            },
        )
        assert updated.status_code == 200
        assert updated.json()["changeSetVersion"] == 3
        attribute = client.patch(
            f"/api/v1/objects/domain/{item['id']}/attributes/domain-code",
            json={
                "value": f"wp7-updated-{uuid4().hex}",
                "expectedVersion": 2,
                "changeSetId": change_set["id"],
                "expectedChangeSetVersion": 3,
            },
        )
        assert attribute.status_code == 200
        assert attribute.json()["changeSetVersion"] == 4


def test_change_set_relation_page_of_an_unknown_record_and_nested_routes_are_absent():
    with TestClient(app) as client:
        change_set = client.post("/api/v1/workspaces/default/change-sets", json={}).json()
        response = client.get(
            "/api/v1/relations",
            params={
                "objectId": "00000000-0000-0000-0000-000000000000",
                "changeSetId": change_set["id"],
            },
        )
        # As live: the anchor record decides the related types, so an unknown one is not found.
        assert response.status_code == 404, response.text
        assert response.json()["error"]["code"] == "object_not_found"
        assert (
            "/api/v1/change-sets/{change_set_id}/objects"
            not in client.get("/openapi.json").json()["paths"]
        )


def test_change_set_object_cursor_binds_query_context_and_honours_descending_name_sort():
    with TestClient(app) as client:
        change_set = client.post("/api/v1/workspaces/default/change-sets", json={}).json()
        for index, name in enumerate(("Alpha query", "Zulu query"), start=1):
            response = client.post(
                "/api/v1/objects",
                json={
                    "applicationKey": "rdm-master",
                    "objectTypeKey": "domain",
                    "name": name,
                    "attributes": [
                        {"attributeTypeKey": "domain-code", "value": f"wp7-query-{uuid4().hex}"}
                    ],
                    "changeSetId": change_set["id"],
                    "expectedChangeSetVersion": index,
                },
            )
            assert response.status_code == 201, response.text
        first = client.get(
            "/api/v1/objects/domain",
            params={
                "changeSetId": change_set["id"],
                "search": "query",
                "sort": "-name",
                "pageSize": 1,
            },
        )
        assert first.status_code == 200, first.text
        assert first.json()["items"][0]["name"] == "Zulu query"
        cursor = first.json()["nextCursor"]
        assert cursor
        second = client.get(
            "/api/v1/objects/domain",
            params={
                "changeSetId": change_set["id"],
                "search": "query",
                "sort": "-name",
                "pageSize": 1,
                "cursor": cursor,
            },
        )
        assert second.status_code == 200, second.text
        assert second.json()["items"][0]["name"] == "Alpha query"
        mismatch = client.get(
            "/api/v1/objects/domain",
            params={
                "changeSetId": change_set["id"],
                "search": "different",
                "sort": "-name",
                "pageSize": 1,
                "cursor": cursor,
            },
        )
        assert mismatch.status_code == 422
        assert mismatch.json()["error"]["code"] == "invalid_cursor"


def test_change_set_history_projects_canonical_mutation_events():
    with TestClient(app) as client:
        change_set = client.post("/api/v1/workspaces/default/change-sets", json={}).json()
        created = client.post(
            "/api/v1/objects",
            json={
                "applicationKey": "rdm-master",
                "objectTypeKey": "domain",
                "name": "History domain",
                "attributes": [
                    {"attributeTypeKey": "domain-code", "value": f"history-{uuid4().hex}"}
                ],
                "changeSetId": change_set["id"],
                "expectedChangeSetVersion": 1,
            },
        ).json()
        updated = client.patch(
            f"/api/v1/objects/domain/{created['id']}",
            json={
                "name": "History domain updated",
                "expectedVersion": created["version"],
                "changeSetId": change_set["id"],
                "expectedChangeSetVersion": 2,
            },
        )
        assert updated.status_code == 200
        history = client.get(
            f"/api/v1/objects/domain/{created['id']}/history",
            params={"changeSetId": change_set["id"]},
        )
        assert history.status_code == 200, history.text
        assert [event["action"] for event in history.json()["items"]] == ["updated", "created"]


def test_historical_attribute_read_uses_the_canonical_subresource():
    with TestClient(app) as client:
        workspace_key = f"wp7-history-{uuid4().hex[:12]}"
        workspace = client.post(
            "/api/v1/workspaces",
            json={"key": workspace_key, "label": "WP7 history"},
        )
        assert workspace.status_code == 201
        change_set = client.post(f"/api/v1/workspaces/{workspace_key}/change-sets", json={}).json()
        created = client.post(
            "/api/v1/objects",
            json={
                "applicationKey": "rdm-translations",
                "objectTypeKey": "language",
                "name": "Historical WP7 language",
                "attributes": [
                    {"attributeTypeKey": "language-code", "value": f"history-{uuid4().hex}"}
                ],
                "changeSetId": change_set["id"],
                "expectedChangeSetVersion": 1,
            },
        )
        assert created.status_code == 201
        publication = client.post(
            f"/api/v1/change-sets/{change_set['id']}/publication",
            json={"expectedChangeSetVersion": 2, "expectedActivePublicationId": None},
        )
        assert publication.status_code == 200, publication.text
        wrong_workspace = client.get(
            f"/api/v1/objects/language/{created.json()['id']}",
            params={"workspaceKey": "default"},
        )
        assert wrong_workspace.status_code == 404
        response = client.get(
            f"/api/v1/objects/language/{created.json()['id']}/attributes/language-code",
            params={"publicationId": publication.json()["id"]},
        )
        assert response.status_code == 200, response.text
        assert response.json()["value"].startswith("history-")


def test_change_set_delete_previews_and_cascades_containment_without_touching_published_data():
    with TestClient(app) as client:
        change_set = client.post("/api/v1/workspaces/default/change-sets", json={}).json()
        language = client.post(
            "/api/v1/objects",
            json={
                "applicationKey": "rdm-translations",
                "objectTypeKey": "language",
                "name": "Cascade language",
                "attributes": [
                    {"attributeTypeKey": "language-code", "value": f"cascade-{uuid4().hex}"}
                ],
                "changeSetId": change_set["id"],
                "expectedChangeSetVersion": 1,
            },
        ).json()
        group = client.post(
            "/api/v1/objects",
            json={
                "applicationKey": "rdm-translations",
                "objectTypeKey": "translation-group",
                "name": "Cascade group",
                "parentObjectId": language["id"],
                "attributes": [
                    {"attributeTypeKey": "group-code", "value": f"cascade-{uuid4().hex}"}
                ],
                "changeSetId": change_set["id"],
                "expectedChangeSetVersion": 2,
            },
        ).json()
        preview = client.delete(
            f"/api/v1/objects/language/{language['id']}",
            params={
                "changeSetId": change_set["id"],
                "expectedChangeSetVersion": 3,
                "expectedVersion": language["version"],
            },
        )
        assert preview.status_code == 409
        assert preview.json()["error"]["code"] == "object_has_dependants"
        deleted = client.delete(
            f"/api/v1/objects/language/{language['id']}",
            params={
                "changeSetId": change_set["id"],
                "expectedChangeSetVersion": 3,
                "expectedVersion": language["version"],
                "cascade": "true",
                "deletionPreviewToken": preview.json()["error"]["details"]["deletionPreviewToken"],
            },
        )
        assert deleted.status_code == 204, deleted.text
        assert (
            client.get(
                f"/api/v1/objects/translation-group/{group['id']}",
                params={"changeSetId": change_set["id"]},
            ).status_code
            == 404
        )
