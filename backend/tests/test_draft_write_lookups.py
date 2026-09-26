"""Base 0.8 S2b: draft writes check what they touch, not the whole membership.

A unique attribute is checked draft-wide through the typed value index. A base record holds its
value only while no draft row replaces it, and a draft record only while it is not deleted; these
cases are what the effective lookup of the matching records decides.
"""

from uuid import uuid4

from fastapi.testclient import TestClient
from wp8_support import (
    activate_draft,
    attribute,
    create_draft,
    create_object,
    create_workspace,
    unique_key,
)

from app.main import app

DOMAIN = "domain"
CODE = "domain-code"


def _draft_version(client, draft: dict) -> None:
    response = client.get(f"/api/v1/workspace-drafts/{draft['id']}")
    assert response.status_code == 200, response.text
    draft["version"] = response.json()["version"]


def _set_code(client, draft: dict, object_id: str, code: str, expected_status: int = 200):
    record = client.get(
        f"/api/v1/objects/{DOMAIN}/{object_id}", params={"workspaceDraftId": draft["id"]}
    ).json()
    response = client.patch(
        f"/api/v1/objects/{DOMAIN}/{object_id}/attributes/{CODE}",
        json={
            "value": code,
            "expectedVersion": record["version"],
            "workspaceDraftId": draft["id"],
            "expectedWorkspaceDraftVersion": draft["version"],
        },
    )
    assert response.status_code == expected_status, response.text
    _draft_version(client, draft)
    return response


def _domain(client, draft: dict, name: str, code: str, expected_status: int = 201):
    return create_object(
        client,
        draft,
        "rdm-master",
        DOMAIN,
        name,
        attributes=[attribute(CODE, code)],
        expected_status=expected_status,
    )


def _delete(client, draft: dict, object_id: str) -> None:
    record = client.get(
        f"/api/v1/objects/{DOMAIN}/{object_id}", params={"workspaceDraftId": draft["id"]}
    ).json()
    response = client.delete(
        f"/api/v1/objects/{DOMAIN}/{object_id}",
        params={
            "workspaceDraftId": draft["id"],
            "expectedVersion": record["version"],
            "expectedWorkspaceDraftVersion": draft["version"],
        },
    )
    assert response.status_code == 204, response.text
    _draft_version(client, draft)


def _conflict(response) -> str:
    body = response.json()
    error = body.get("error", body)
    assert error["code"] == "duplicate_attribute_value", body
    return error["details"]["conflictingObjectId"]


def test_unique_values_follow_the_draft_over_its_base():
    with TestClient(app) as client:
        workspace_key = unique_key("s2b")
        create_workspace(client, workspace_key)
        suffix = uuid4().hex[:8]
        a, b, c, d = (f"s2b-{letter}-{suffix}" for letter in "abcd")

        first = create_draft(client, workspace_key).json()
        alpha = _domain(client, first, "Alpha", a).json()
        bravo = _domain(client, first, "Bravo", b).json()
        activated = activate_draft(client, first["id"], expected_draft_version=first["version"])
        revision_id = activated.json()["id"]

        draft = create_draft(client, workspace_key, derived_from_revision_id=revision_id).json()
        # A base record holds its value.
        assert _conflict(_set_code(client, draft, bravo["id"], a, 409)) == alpha["id"]
        assert _conflict(_domain(client, draft, "Copy", b, 409)) == bravo["id"]

        # A draft row that changes the base value frees it and holds the new one.
        _set_code(client, draft, alpha["id"], c)
        _set_code(client, draft, bravo["id"], a)
        assert _conflict(_domain(client, draft, "Copy", c, 409)) == alpha["id"]

        # A record's own value is not a conflict.
        _set_code(client, draft, bravo["id"], a)

        # A draft-only record holds its value until it is deleted.
        charlie = _domain(client, draft, "Charlie", d).json()
        assert _conflict(_domain(client, draft, "Copy", d, 409)) == charlie["id"]
        _delete(client, draft, charlie["id"])
        _domain(client, draft, "Delta", d)

        # A deleted base record frees its value too.
        _delete(client, draft, alpha["id"])
        _domain(client, draft, "Echo", c)
