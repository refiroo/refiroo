from uuid import uuid4

from fastapi.testclient import TestClient

from app.main import app, create_app


def _key(prefix: str) -> str:
    return f"{prefix}-{uuid4().hex[:8]}"


def test_workspace_catalogue_pages_searches_and_rejects_unknown_scope():
    first_key = _key("central")
    second_key = _key("central")
    with TestClient(app) as client:
        for key, label in ((first_key, "Central Europe"), (second_key, "Central Archive")):
            created = client.post("/api/v1/workspaces", json={"key": key, "label": label})
            assert created.status_code == 201

        first = client.get(
            "/api/v1/workspaces",
            params={"search": "central", "status": "all", "pageSize": 1},
        )
        assert first.status_code == 200
        assert first.json()["nextCursor"] is not None
        second = client.get(
            "/api/v1/workspaces",
            params={
                "search": "central",
                "status": "all",
                "pageSize": 1,
                "cursor": first.json()["nextCursor"],
            },
        )
        assert second.status_code == 200
        assert {first.json()["items"][0]["key"], second.json()["items"][0]["key"]} == {
            first_key,
            second_key,
        }
        mismatched_cursor = client.get(
            "/api/v1/workspaces",
            params={
                "search": first_key,
                "status": "all",
                "pageSize": 1,
                "cursor": first.json()["nextCursor"],
            },
        )
        assert mismatched_cursor.status_code == 422
        assert mismatched_cursor.json()["error"]["code"] == "invalid_cursor"

        unknown = client.get("/api/v1/objects/domain", params={"workspaceKey": _key("missing")})
        assert unknown.status_code == 404
        assert unknown.json()["error"]["code"] == "workspace_not_found"


def test_default_switch_is_atomic_and_omitted_scope_uses_the_catalogue_default():
    workspace_key = _key("default-target")
    with TestClient(app) as client:
        assert (
            client.post(
                "/api/v1/workspaces", json={"key": workspace_key, "label": "Default target"}
            ).status_code
            == 201
        )
        state = client.get("/api/v1/workspace-runtime-state").json()
        changed = client.patch(
            "/api/v1/workspace-runtime-state",
            json={
                "defaultWorkspaceKey": workspace_key,
                "expectedVersion": state["version"],
            },
        )
        assert changed.status_code == 200
        assert changed.json()["defaultWorkspaceKey"] == workspace_key

        stale = client.patch(
            "/api/v1/workspace-runtime-state",
            json={"defaultWorkspaceKey": "default", "expectedVersion": state["version"]},
        )
        assert stale.status_code == 409
        assert stale.json()["error"]["code"] == "version_conflict"

        change_set = client.post(f"/api/v1/workspaces/{workspace_key}/change-sets", json={}).json()
        created = client.post(
            "/api/v1/objects",
            json={
                "applicationKey": "rdm-translations",
                "objectTypeKey": "language",
                "name": "Catalogue default object",
                "attributes": [
                    {"attributeTypeKey": "language-code", "value": _key("catalogue-default")}
                ],
                "changeSetId": change_set["id"],
                "expectedChangeSetVersion": change_set["version"],
            },
        )
        assert created.status_code == 201
        assert created.json()["workspaceKey"] == workspace_key

        current = changed.json()
        restored = client.patch(
            "/api/v1/workspace-runtime-state",
            json={
                "defaultWorkspaceKey": "default",
                "expectedVersion": current["version"],
            },
        )
        assert restored.status_code == 200


def test_retired_workspace_remains_readable_but_blocks_all_runtime_mutations():
    workspace_key = _key("archive")
    with TestClient(app) as client:
        created_workspace = client.post(
            "/api/v1/workspaces", json={"key": workspace_key, "label": "Archive"}
        ).json()
        change_set = client.post(f"/api/v1/workspaces/{workspace_key}/change-sets", json={}).json()
        created_object = client.post(
            "/api/v1/objects",
            json={
                "applicationKey": "rdm-translations",
                "objectTypeKey": "language",
                "workspaceKey": workspace_key,
                "name": "Archived domain",
                "attributes": [
                    {"attributeTypeKey": "language-code", "value": _key("archive-domain")}
                ],
                "changeSetId": change_set["id"],
                "expectedChangeSetVersion": change_set["version"],
            },
        ).json()
        activation = client.post(
            f"/api/v1/change-sets/{change_set['id']}/publication",
            json={"expectedChangeSetVersion": 2, "expectedActivePublicationId": None},
        )
        assert activation.status_code == 200
        blocked_change_set = client.post(f"/api/v1/workspaces/{workspace_key}/change-sets", json={}).json()
        retired = client.patch(
            f"/api/v1/workspaces/{workspace_key}",
            json={"status": "retired", "expectedVersion": created_workspace["version"]},
        )
        assert retired.status_code == 200

        active_search = client.get("/api/v1/workspaces", params={"search": workspace_key})
        assert active_search.status_code == 200
        assert active_search.json()["items"] == []
        retired_search = client.get(
            "/api/v1/workspaces", params={"search": workspace_key, "status": "retired"}
        )
        assert retired_search.status_code == 200
        assert [item["key"] for item in retired_search.json()["items"]] == [workspace_key]

        state = client.get("/api/v1/workspace-runtime-state").json()
        default_to_retired = client.patch(
            "/api/v1/workspace-runtime-state",
            json={
                "defaultWorkspaceKey": workspace_key,
                "expectedVersion": state["version"],
            },
        )
        assert default_to_retired.status_code == 409
        assert default_to_retired.json()["error"]["code"] == "workspace_retired"

        assert client.get(f"/api/v1/workspaces/{workspace_key}").status_code == 200
        assert (
            client.get("/api/v1/objects/language", params={"workspaceKey": workspace_key}).status_code
            == 200
        )
        assert client.get(f"/api/v1/objects/language/{created_object['id']}", params={"workspaceKey": workspace_key}).status_code == 200

        update = client.patch(
            f"/api/v1/objects/language/{created_object['id']}",
                json={"name": "Blocked", "expectedVersion": created_object["version"], "changeSetId": blocked_change_set["id"], "expectedChangeSetVersion": 1},
        )
        assert update.status_code == 409
        assert update.json()["error"]["code"] == "workspace_retired"
        create = client.post(
            "/api/v1/objects",
            json={
                "applicationKey": "rdm-translations",
                "objectTypeKey": "language",
                "workspaceKey": workspace_key,
                "name": "Blocked",
                "attributes": [{"attributeTypeKey": "language-code", "value": _key("blocked")}],
                "changeSetId": blocked_change_set["id"],
                "expectedChangeSetVersion": 1,
            },
        )
        assert create.status_code == 409
        assert create.json()["error"]["code"] == "workspace_retired"

        attribute = client.patch(
            f"/api/v1/objects/language/{created_object['id']}/attributes/language-code",
            json={"value": _key("blocked-attribute"), "expectedVersion": created_object["version"], "changeSetId": blocked_change_set["id"], "expectedChangeSetVersion": 1},
        )
        assert attribute.status_code == 409
        assert attribute.json()["error"]["code"] == "workspace_retired"
        relation = client.post(
            "/api/v1/relations",
            json={
                "relationTypeKey": "not-reached",
                "fromObjectId": created_object["id"],
                "toObjectId": created_object["id"],
                "attributes": {},
                "changeSetId": blocked_change_set["id"],
                "expectedChangeSetVersion": 1,
            },
        )
        assert relation.status_code == 409
        assert relation.json()["error"]["code"] == "workspace_retired"
        delete = client.delete(
            f"/api/v1/objects/language/{created_object['id']}",
            params={"expectedVersion": created_object["version"], "changeSetId": blocked_change_set["id"], "expectedChangeSetVersion": 1},
        )
        assert delete.status_code == 409
        assert delete.json()["error"]["code"] == "workspace_retired"


def test_default_workspace_cannot_be_retired_and_workspace_version_is_claimed():
    workspace_key = _key("concurrent")
    with TestClient(app) as client:
        default = client.get("/api/v1/workspaces/default").json()
        blocked = client.patch(
            "/api/v1/workspaces/default",
            json={"status": "retired", "expectedVersion": default["version"]},
        )
        assert blocked.status_code == 409
        assert blocked.json()["error"]["code"] == "default_workspace_cannot_be_retired"

        created = client.post(
            "/api/v1/workspaces", json={"key": workspace_key, "label": "Original"}
        ).json()
        updated = client.patch(
            f"/api/v1/workspaces/{workspace_key}",
            json={"label": "Updated", "expectedVersion": created["version"]},
        )
        assert updated.status_code == 200
        stale = client.patch(
            f"/api/v1/workspaces/{workspace_key}",
            json={"label": "Lost", "expectedVersion": created["version"]},
        )
        assert stale.status_code == 409
        assert stale.json()["error"]["details"]["currentVersion"] == updated.json()["version"]


def test_workspace_mutations_can_be_removed_while_discovery_remains(monkeypatch):
    monkeypatch.setenv("WORKSPACE_ADMIN_MUTATIONS_ENABLED", "false")
    disabled_app = create_app()
    schema = disabled_app.openapi()
    assert schema["paths"]["/api/v1/workspaces"] == {
        "get": schema["paths"]["/api/v1/workspaces"]["get"]
    }
    with TestClient(disabled_app) as client:
        assert client.get("/api/v1/workspaces").status_code == 200
        assert (
            client.post(
                "/api/v1/workspaces", json={"key": _key("disabled"), "label": "Disabled"}
            ).status_code
            == 405
        )
        assert client.get("/api/v1/capabilities").json()["workspaceAdmin"] == {
            "manageWorkspaces": False
        }
