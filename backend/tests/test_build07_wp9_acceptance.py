"""Base 0.7 WP-9 composed SC-15 acceptance at the HTTP boundary.

The browser runner ``frontend/e2e/sc15-model-version-acceptance.mjs`` drives the same journey
through the UI. This module adds what a browser cannot set up: corrupt and unsupported installed
releases. Each refusal must leave live data, history, the runtime selection, the other draft and
another workspace untouched. The journey activates a release, so it owns a private database.
"""

import json
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from test_build07_wp6 import add_field_and_view, install_model
from wp8_support import create_object, create_workspace, unique_key

from app.config import reload_settings
from app.db import get_engine
from app.main import create_app
from app.services.model.registry import model_registry


@pytest.fixture
def client(monkeypatch, migrated_database):
    monkeypatch.setenv("DATABASE_URL", migrated_database("sc15.db"))
    monkeypatch.setenv("MODEL_ADMIN_MUTATIONS_ENABLED", "true")
    monkeypatch.setenv("WEB_CONCURRENCY", "1")
    model_registry.clear()
    with TestClient(create_app()) as test_client:
        yield test_client
    get_engine().dispose()
    monkeypatch.undo()
    reload_settings()
    model_registry.clear()


def _language(client, draft, name, *attributes):
    return create_object(
        client,
        draft,
        "rdm-translations",
        "language",
        name,
        attributes=[
            {"attributeTypeKey": "language-code", "value": unique_key("lang")},
            *attributes,
        ],
    ).json()


def _snapshot(client, retail, warehouse, language_id):
    """Everything a refused or unrelated draft operation must leave exactly as it was."""

    def get(path, **params):
        return client.get(f"/api/v1{path}", params=params).json()

    return json.dumps(
        {
            "runtime": get("/model-runtime-state")["activeReleaseId"],
            "model": get("/model"),
            "live": get(f"/objects/language/{language_id}", workspaceKey=retail),
            "revisions": get(f"/workspaces/{retail}/revisions"),
            "warehouse": get("/objects/language", workspaceKey=warehouse),
            "warehouseDrafts": get(f"/workspaces/{warehouse}/drafts"),
        },
        sort_keys=True,
    )


def test_sc15_two_drafts_on_two_releases_through_activation_and_refusals(client):
    retail, warehouse = unique_key("retail"), unique_key("warehouse")
    create_workspace(client, retail)
    create_workspace(client, warehouse)

    def live_language(workspace, name, code):
        response = client.post(
            "/api/v1/objects",
            json={
                "workspaceKey": workspace,
                "applicationKey": "rdm-translations",
                "objectTypeKey": "language",
                "name": name,
                "attributes": [{"attributeTypeKey": "language-code", "value": code}],
            },
        )
        assert response.status_code == 201, response.text
        return response.json()

    live = live_language(retail, "Czech", "cs")
    live_language(warehouse, "German", "de")
    candidate, _, _ = install_model(client, add_field_and_view)
    unsupported, _, _ = install_model(client, schema="9.9")
    corrupt, _, _ = install_model(client, corrupt=True)

    def draft(model_release_id=None):
        body = {
            "source": "currentLive",
            **({"modelReleaseId": model_release_id} if model_release_id else {}),
        }
        return client.post(f"/api/v1/workspaces/{retail}/drafts", json=body)

    draft1 = draft().json()
    draft2 = draft(candidate).json()
    _language(client, draft1, "Current rules")
    prepared = _language(
        client, draft2, "Next rules", {"attributeTypeKey": "wp6-number", "value": 7}
    )
    draft1 = client.get(f"/api/v1/workspace-drafts/{draft1['id']}").json()
    draft2 = client.get(f"/api/v1/workspace-drafts/{draft2['id']}").json()

    # Unavailable, unsupported and corrupt releases are refused for creation and version change.
    before = _snapshot(client, retail, warehouse, live["id"])
    for release, code in (
        (str(uuid4()), "pinned_model_unavailable"),
        (unsupported, "unsupported_pinned_model_schema"),
        (corrupt, "pinned_model_invalid"),
    ):
        created = draft(release)
        changed = client.patch(
            f"/api/v1/workspaces/{retail}/drafts/{draft1['id']}/model-release",
            json={"modelReleaseId": release, "expectedDraftVersion": draft1["version"]},
        )
        for response in (created, changed):
            assert response.status_code == 409, response.text
            assert response.json()["error"]["code"] == code
    assert _snapshot(client, retail, warehouse, live["id"]) == before
    assert client.get(f"/api/v1/workspace-drafts/{draft1['id']}").json() == draft1
    assert client.get(f"/api/v1/workspace-drafts/{draft2['id']}").json() == draft2
    assert len(client.get(f"/api/v1/workspaces/{retail}/drafts").json()["items"]) == 2

    # draft2 cannot publish before its release is active; draft1 can.
    refused = client.post(
        f"/api/v1/workspace-drafts/{draft2['id']}/activation",
        json={"expectedDraftVersion": draft2["version"]},
    )
    assert refused.json()["error"]["code"] == "workspace_draft_model_release_conflict"
    assert _snapshot(client, retail, warehouse, live["id"]) == before

    # The administrator activates the candidate; live data is unchanged by that selection.
    runtime = client.get("/api/v1/model-runtime-state").json()
    activated = client.post(
        f"/api/v1/model-releases/{candidate}/activation",
        json={
            "expectedRuntimeVersion": runtime["version"],
            "expectedActiveReleaseId": runtime["activeReleaseId"],
        },
    )
    assert activated.status_code == 200, activated.text
    assert (
        client.get(f"/api/v1/objects/language/{live['id']}", params={"workspaceKey": retail}).json()
        == (json.loads(before)["live"])
    )

    # draft2 publishes through the ordinary path; its typed value reaches live.
    published = client.post(
        f"/api/v1/workspace-drafts/{draft2['id']}/activation",
        json={"expectedDraftVersion": draft2["version"]},
    )
    assert published.status_code == 200, published.text
    live_prepared = client.get(
        f"/api/v1/objects/language/{prepared['id']}", params={"workspaceKey": retail}
    ).json()
    assert {"attributeTypeKey": "wp6-number", "value": 7} in [
        {"attributeTypeKey": item["attributeTypeKey"], "value": item["value"]}
        for item in live_prepared["attributes"]
    ]

    # draft1 is now on a non-active release: refused, then discarded with no data change.
    after_publication = _snapshot(client, retail, warehouse, live["id"])
    refused = client.post(
        f"/api/v1/workspace-drafts/{draft1['id']}/activation",
        json={"expectedDraftVersion": draft1["version"]},
    )
    assert refused.json()["error"]["code"] == "workspace_draft_model_release_conflict"
    discarded = client.delete(
        f"/api/v1/workspace-drafts/{draft1['id']}", params={"expectedVersion": draft1["version"]}
    )
    assert discarded.status_code == 204, discarded.text
    assert _snapshot(client, retail, warehouse, live["id"]) == after_publication
    names = [
        item["name"]
        for item in client.get("/api/v1/objects/language", params={"workspaceKey": retail}).json()[
            "items"
        ]
    ]
    assert "Current rules" not in names and "Next rules" in names
