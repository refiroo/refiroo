"""0.8 W6 (D27): delete a workspace nothing refers to, so a mistyped key can be corrected.

A workspace may be deleted when it is not the default, was never published and has no objects and
no change sets. Every refusal leaves the catalogue and the workspace's rows unchanged.
"""

import threading
from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from wp8_support import (
    create_change_set,
    create_domain,
    create_workspace,
    publish_change_set,
    unique_key,
    withdraw_publication,
)

from app.config import reload_settings
from app.db import SessionLocal, get_engine
from app.engine.model.registry import model_registry
from app.engine.records import objects as object_writes
from app.main import create_app
from app.models.database import RdmObject, RelationSetVersion, Workspace

HOLD_TIMEOUT = 10


@pytest.fixture
def client(monkeypatch, migrated_database) -> Iterator[TestClient]:
    monkeypatch.setenv("DATABASE_URL", migrated_database("w6.db"))
    monkeypatch.setenv("WORKSPACE_ADMIN_MUTATIONS_ENABLED", "true")
    model_registry.clear()
    with TestClient(create_app()) as test_client:
        yield test_client
    get_engine().dispose()
    monkeypatch.undo()
    reload_settings()
    model_registry.clear()


def _detail(client: TestClient, key: str) -> dict:
    response = client.get(f"/api/v1/workspaces/{key}")
    assert response.status_code == 200, response.text
    return response.json()


def _delete(client: TestClient, key: str, version: int) -> httpx.Response:
    return client.delete(f"/api/v1/workspaces/{key}", params={"expectedVersion": version})


def _refused(client: TestClient, key: str, code: str, version: int | None = None) -> dict:
    before = _detail(client, key)
    response = _delete(client, key, version or before["version"])
    assert response.status_code == 409, response.text
    error = response.json()["error"]
    assert error["code"] == code
    assert _detail(client, key) == before
    return error


def _live_object(client: TestClient, workspace_key: str, object_type_key: str, name: str, *,
                 parent: str | None = None, **attributes) -> dict:
    response = client.post(
        "/api/v1/objects",
        json={
            "workspaceKey": workspace_key,
            "applicationKey": "rdm-systems" if object_type_key.startswith("system") else "rdm-master",
            "objectTypeKey": object_type_key,
            "name": name,
            "parentObjectId": parent,
            "attributes": [
                {"attributeTypeKey": key, "value": value} for key, value in attributes.items()
            ],
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def _delete_object(client: TestClient, item: dict) -> None:
    current = client.get(
        f"/api/v1/objects/{item['objectTypeKey']}/{item['id']}",
        params={"workspaceKey": item["workspaceKey"]},
    ).json()
    response = client.delete(
        f"/api/v1/objects/{item['objectTypeKey']}/{item['id']}",
        params={"expectedVersion": current["version"]},
    )
    assert response.status_code == 204, response.text


def test_empty_workspace_is_deleted_and_its_key_can_be_created_again(client):
    key = unique_key("w6-typo")
    created = create_workspace(client, key)
    assert created["deletable"] is True
    assert created["deleteBlockedBy"] is None
    assert _detail(client, key)["deletable"] is True
    # The paged list does not compute deletability.
    listed = client.get("/api/v1/workspaces", params={"search": key}).json()["items"]
    assert "deletable" not in listed[0]

    assert _delete(client, key, created["version"]).status_code == 204
    missing = client.get(f"/api/v1/workspaces/{key}")
    assert missing.status_code == 404
    assert missing.json()["error"]["code"] == "workspace_not_found"
    again = _delete(client, key, created["version"])
    assert again.status_code == 404
    assert again.json()["error"]["code"] == "workspace_not_found"

    recreated = create_workspace(client, key)
    assert recreated["version"] == 1


def test_retired_workspace_is_deleted_under_the_same_rule(client):
    key = unique_key("w6-retired")
    created = create_workspace(client, key)
    retired = client.patch(
        f"/api/v1/workspaces/{key}", json={"status": "retired", "expectedVersion": created["version"]}
    )
    assert retired.status_code == 200, retired.text
    assert retired.json()["deletable"] is True
    assert _delete(client, key, retired.json()["version"]).status_code == 204


def test_default_workspace_is_refused(client):
    state = client.get("/api/v1/workspace-runtime-state").json()
    default_key = state["defaultWorkspaceKey"]
    assert _detail(client, default_key)["deleteBlockedBy"] == "default"
    _refused(client, default_key, "workspace_is_default")
    assert client.get("/api/v1/workspace-runtime-state").json() == state


def test_published_workspace_is_refused_even_after_withdrawal_and_emptying(client):
    key = unique_key("w6-published")
    create_workspace(client, key)
    change_set = create_change_set(client, key).json()
    create_domain(client, change_set, unique_key("pub"))
    current = client.get(f"/api/v1/change-sets/{change_set['id']}").json()
    publication = publish_change_set(
        client, change_set["id"], expected_change_set_version=current["version"]
    ).json()
    withdraw_publication(client, publication["id"])
    # Remove the published objects from live: the publication still refers to the workspace.
    with SessionLocal() as session:
        live = session.scalars(select(RdmObject).where(RdmObject.workspace_key == key)).all()
        items = [
            {"objectTypeKey": row.object_type_key, "id": row.id, "workspaceKey": key} for row in live
        ]
    for item in items:
        _delete_object(client, item)

    detail = _detail(client, key)
    assert detail["deletable"] is False
    assert detail["deleteBlockedBy"] == "published"
    error = _refused(client, key, "workspace_has_publications")
    assert "retire" in error["message"]
    assert client.get(f"/api/v1/publications/{publication['id']}").status_code == 200


def test_objects_and_change_sets_are_refused_until_removed(client):
    key = unique_key("w6-content")
    create_workspace(client, key)
    system = _live_object(client, key, "system", "System", **{"system-code": unique_key("sys")})
    value = _live_object(
        client, key, "system-value", "Value", parent=system["id"],
        **{"value-code": unique_key("v"), "value-name": "Value"},
    )
    change_set = create_change_set(client, key).json()

    assert _detail(client, key)["deleteBlockedBy"] == "notEmpty"
    error = _refused(client, key, "workspace_not_empty")
    assert error["details"] == {"objectCount": 2, "changeSetCount": 1}
    assert client.get(f"/api/v1/change-sets/{change_set['id']}").status_code == 200

    _delete_object(client, value)
    _delete_object(client, system)
    error = _refused(client, key, "workspace_not_empty")
    assert error["details"] == {"objectCount": 0, "changeSetCount": 1}

    discarded = client.delete(
        f"/api/v1/change-sets/{change_set['id']}",
        params={"expectedVersion": change_set["version"]},
    )
    assert discarded.status_code == 204, discarded.text
    with SessionLocal() as session:
        # Live containment left relation-set versions behind, which the deletion removes.
        assert session.scalar(
            select(func.count()).where(RelationSetVersion.workspace_key == key)
        )
    detail = _detail(client, key)
    assert detail["deletable"] is True
    assert _delete(client, key, detail["version"]).status_code == 204
    with SessionLocal() as session:
        assert session.scalar(
            select(func.count()).where(RelationSetVersion.workspace_key == key)
        ) == 0


def test_stale_version_is_refused(client):
    key = unique_key("w6-stale")
    created = create_workspace(client, key)
    renamed = client.patch(
        f"/api/v1/workspaces/{key}", json={"label": "Renamed", "expectedVersion": created["version"]}
    ).json()
    error = _refused(client, key, "version_conflict", version=created["version"])
    assert error["details"] == {"currentVersion": renamed["version"]}


def test_deletion_is_absent_with_administration_off(monkeypatch, client):
    key = unique_key("w6-flag-off")
    created = create_workspace(client, key)
    monkeypatch.setenv("WORKSPACE_ADMIN_MUTATIONS_ENABLED", "false")
    disabled_app = create_app()
    assert set(disabled_app.openapi()["paths"]["/api/v1/workspaces/{workspace_key}"]) == {"get"}
    with TestClient(disabled_app) as disabled:
        assert _delete(disabled, key, created["version"]).status_code == 405
        assert _delete(disabled, unique_key("absent"), 1).status_code == 405
        assert _detail(disabled, key)["deletable"] is True


def test_live_write_resolved_before_deletion_saves_nothing(monkeypatch, client):
    """A create that resolved the workspace before it was deleted must not leave an orphan row."""
    key = unique_key("w6-race")
    created = create_workspace(client, key)
    resolved, deleted = threading.Event(), threading.Event()
    original = object_writes.resolve_workspace

    def resolve_then_hold(session, workspace_key, **kwargs):
        workspace = original(session, workspace_key, **kwargs)
        resolved.set()
        assert deleted.wait(HOLD_TIMEOUT)
        return workspace

    # Held where the create resolves the workspace, between that read and its write.
    monkeypatch.setattr(object_writes, "resolve_workspace", resolve_then_hold)
    name = f"Domain {unique_key('held')}"
    with ThreadPoolExecutor(max_workers=1) as pool:
        pending = pool.submit(
            _post_domain, client, key, name
        )
        assert resolved.wait(HOLD_TIMEOUT)
        deletion = _delete(client, key, created["version"])
        deleted.set()
        response = pending.result(timeout=HOLD_TIMEOUT)

    assert deletion.status_code == 204, deletion.text
    assert response.status_code == 404, response.text
    assert response.json()["error"]["code"] == "workspace_not_found"
    with SessionLocal() as session:
        assert session.scalar(select(func.count()).where(RdmObject.workspace_key == key)) == 0
        assert session.get(Workspace, key) is None


def _post_domain(client: TestClient, key: str, name: str) -> httpx.Response:
    return client.post(
        "/api/v1/objects",
        json={
            "workspaceKey": key,
            "applicationKey": "rdm-master",
            "objectTypeKey": "domain",
            "name": name,
            "attributes": [{"attributeTypeKey": "domain-code", "value": unique_key("d")}],
        },
    )
