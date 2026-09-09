from uuid import uuid4

from fastapi.testclient import TestClient

from app.main import app


def test_canonical_draft_object_and_attribute_journey():
    with TestClient(app) as client:
        draft = client.post("/api/v1/workspaces/default/drafts", json={}).json()
        created = client.post(
            "/api/v1/objects",
            json={
                "applicationKey": "rdm-master",
                "objectTypeKey": "domain",
                "name": "WP7 domain",
                "attributes": [{"attributeTypeKey": "domain-code", "value": f"wp7-{uuid4().hex}"}],
                "workspaceDraftId": draft["id"],
                "expectedWorkspaceDraftVersion": 1,
            },
        )
        assert created.status_code == 201
        item = created.json()
        assert item["workspaceDraftVersion"] == 2
        assert (
            client.get(
                "/api/v1/objects/domain", params={"workspaceDraftId": draft["id"]}
            ).status_code
            == 200
        )
        updated = client.patch(
            f"/api/v1/objects/domain/{item['id']}",
            json={
                "name": "WP7 renamed",
                "expectedVersion": 1,
                "workspaceDraftId": draft["id"],
                "expectedWorkspaceDraftVersion": 2,
            },
        )
        assert updated.status_code == 200
        assert updated.json()["workspaceDraftVersion"] == 3
        attribute = client.patch(
            f"/api/v1/objects/domain/{item['id']}/attributes/domain-code",
            json={
                "value": f"wp7-updated-{uuid4().hex}",
                "expectedVersion": 2,
                "workspaceDraftId": draft["id"],
                "expectedWorkspaceDraftVersion": 3,
            },
        )
        assert attribute.status_code == 200
        assert attribute.json()["workspaceDraftVersion"] == 4


def test_empty_draft_relation_page_and_nested_routes_are_absent():
    with TestClient(app) as client:
        draft = client.post("/api/v1/workspaces/default/drafts", json={}).json()
        response = client.get(
            "/api/v1/relations",
            params={
                "objectId": "00000000-0000-0000-0000-000000000000",
                "workspaceDraftId": draft["id"],
            },
        )
        assert response.status_code == 200, response.text
        assert response.json() == {"items": [], "nextCursor": None}
        assert (
            "/api/v1/workspace-drafts/{draft_id}/objects"
            not in client.get("/openapi.json").json()["paths"]
        )


def test_draft_object_cursor_binds_query_context_and_honours_descending_name_sort():
    with TestClient(app) as client:
        draft = client.post("/api/v1/workspaces/default/drafts", json={}).json()
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
                    "workspaceDraftId": draft["id"],
                    "expectedWorkspaceDraftVersion": index,
                },
            )
            assert response.status_code == 201, response.text
        first = client.get(
            "/api/v1/objects/domain",
            params={
                "workspaceDraftId": draft["id"],
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
                "workspaceDraftId": draft["id"],
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
                "workspaceDraftId": draft["id"],
                "search": "different",
                "sort": "-name",
                "pageSize": 1,
                "cursor": cursor,
            },
        )
        assert mismatch.status_code == 422
        assert mismatch.json()["error"]["code"] == "invalid_cursor"


def test_draft_history_projects_canonical_mutation_events():
    with TestClient(app) as client:
        draft = client.post("/api/v1/workspaces/default/drafts", json={}).json()
        created = client.post(
            "/api/v1/objects",
            json={
                "applicationKey": "rdm-master",
                "objectTypeKey": "domain",
                "name": "History domain",
                "attributes": [
                    {"attributeTypeKey": "domain-code", "value": f"history-{uuid4().hex}"}
                ],
                "workspaceDraftId": draft["id"],
                "expectedWorkspaceDraftVersion": 1,
            },
        ).json()
        updated = client.patch(
            f"/api/v1/objects/domain/{created['id']}",
            json={
                "name": "History domain updated",
                "expectedVersion": created["version"],
                "workspaceDraftId": draft["id"],
                "expectedWorkspaceDraftVersion": 2,
            },
        )
        assert updated.status_code == 200
        history = client.get(
            f"/api/v1/objects/domain/{created['id']}/history",
            params={"workspaceDraftId": draft["id"]},
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
        draft = client.post(f"/api/v1/workspaces/{workspace_key}/drafts", json={}).json()
        created = client.post(
            "/api/v1/objects",
            json={
                "applicationKey": "rdm-translations",
                "objectTypeKey": "language",
                "name": "Historical WP7 language",
                "attributes": [
                    {"attributeTypeKey": "language-code", "value": f"history-{uuid4().hex}"}
                ],
                "workspaceDraftId": draft["id"],
                "expectedWorkspaceDraftVersion": 1,
            },
        )
        assert created.status_code == 201
        revision = client.post(
            f"/api/v1/workspace-drafts/{draft['id']}/activation",
            json={"expectedDraftVersion": 2, "expectedActiveRevisionId": None},
        )
        assert revision.status_code == 200, revision.text
        wrong_workspace = client.get(
            f"/api/v1/objects/language/{created.json()['id']}",
            params={"workspaceKey": "default"},
        )
        assert wrong_workspace.status_code == 404
        response = client.get(
            f"/api/v1/objects/language/{created.json()['id']}/attributes/language-code",
            params={"workspaceRevisionId": revision.json()["id"]},
        )
        assert response.status_code == 200, response.text
        assert response.json()["value"].startswith("history-")


def test_draft_delete_previews_and_cascades_containment_without_touching_published_data():
    with TestClient(app) as client:
        draft = client.post("/api/v1/workspaces/default/drafts", json={}).json()
        language = client.post(
            "/api/v1/objects",
            json={
                "applicationKey": "rdm-translations",
                "objectTypeKey": "language",
                "name": "Cascade language",
                "attributes": [
                    {"attributeTypeKey": "language-code", "value": f"cascade-{uuid4().hex}"}
                ],
                "workspaceDraftId": draft["id"],
                "expectedWorkspaceDraftVersion": 1,
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
                "workspaceDraftId": draft["id"],
                "expectedWorkspaceDraftVersion": 2,
            },
        ).json()
        preview = client.delete(
            f"/api/v1/objects/language/{language['id']}",
            params={
                "workspaceDraftId": draft["id"],
                "expectedWorkspaceDraftVersion": 3,
                "expectedVersion": language["version"],
            },
        )
        assert preview.status_code == 409
        assert preview.json()["error"]["code"] == "object_has_dependants"
        deleted = client.delete(
            f"/api/v1/objects/language/{language['id']}",
            params={
                "workspaceDraftId": draft["id"],
                "expectedWorkspaceDraftVersion": 3,
                "expectedVersion": language["version"],
                "cascade": "true",
                "deletionPreviewToken": preview.json()["error"]["details"]["deletionPreviewToken"],
            },
        )
        assert deleted.status_code == 204, deleted.text
        assert (
            client.get(
                f"/api/v1/objects/translation-group/{group['id']}",
                params={"workspaceDraftId": draft["id"]},
            ).status_code
            == 404
        )
