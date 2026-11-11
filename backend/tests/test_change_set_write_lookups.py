"""Base 0.8 S2b: change set writes check what they touch, not the whole membership.

A unique attribute is checked change set-wide through the typed value index. A base record holds its
value only while no change set row replaces it, and a change set record only while it is not deleted; these
cases are what the effective lookup of the matching records decides.
"""

from uuid import uuid4

from harness_identity import TestClient
from wp8_support import (
    attribute,
    create_change_set,
    create_object,
    create_workspace,
    publish_change_set,
    unique_key,
)

from app.main import app

DOMAIN = "domain"
CODE = "domain-code"


def _change_set_version(client, change_set: dict) -> None:
    response = client.get(f"/api/v1/change-sets/{change_set['id']}")
    assert response.status_code == 200, response.text
    change_set["version"] = response.json()["version"]


def _set_code(client, change_set: dict, object_id: str, code: str, expected_status: int = 200):
    record = client.get(
        f"/api/v1/objects/{DOMAIN}/{object_id}", params={"changeSetId": change_set["id"]}
    ).json()
    response = client.patch(
        f"/api/v1/objects/{DOMAIN}/{object_id}/attributes/{CODE}",
        json={
            "value": code,
            "expectedVersion": record["version"],
            "changeSetId": change_set["id"],
            "expectedChangeSetVersion": change_set["version"],
        },
    )
    assert response.status_code == expected_status, response.text
    _change_set_version(client, change_set)
    return response


def _domain(client, change_set: dict, name: str, code: str, expected_status: int = 201):
    return create_object(
        client,
        change_set,
        "rdm-master",
        DOMAIN,
        name,
        attributes=[attribute(CODE, code)],
        expected_status=expected_status,
    )


def _delete(client, change_set: dict, object_id: str) -> None:
    record = client.get(
        f"/api/v1/objects/{DOMAIN}/{object_id}", params={"changeSetId": change_set["id"]}
    ).json()
    response = client.delete(
        f"/api/v1/objects/{DOMAIN}/{object_id}",
        params={
            "changeSetId": change_set["id"],
            "expectedVersion": record["version"],
            "expectedChangeSetVersion": change_set["version"],
        },
    )
    assert response.status_code == 204, response.text
    _change_set_version(client, change_set)


def _conflict(response) -> str:
    body = response.json()
    error = body.get("error", body)
    assert error["code"] == "DUPLICATE_ATTRIBUTE_VALUE", body
    return error["details"]["conflictingObjectId"]


def test_unique_values_follow_the_change_set_over_its_base():
    with TestClient(app) as client:
        workspace_key = unique_key("s2b")
        create_workspace(client, workspace_key)
        suffix = uuid4().hex[:8]
        a, b, c, d = (f"s2b-{letter}-{suffix}" for letter in "abcd")

        first = create_change_set(client, workspace_key).json()
        alpha = _domain(client, first, "Alpha", a).json()
        bravo = _domain(client, first, "Bravo", b).json()
        activated = publish_change_set(
            client, first["id"], expected_change_set_version=first["version"]
        )
        publication_id = activated.json()["id"]

        change_set = create_change_set(
            client, workspace_key, derived_from_publication_id=publication_id
        ).json()
        # A base record holds its value.
        assert _conflict(_set_code(client, change_set, bravo["id"], a, 409)) == alpha["id"]
        assert _conflict(_domain(client, change_set, "Copy", b, 409)) == bravo["id"]

        # A change set row that changes the base value frees it and holds the new one.
        _set_code(client, change_set, alpha["id"], c)
        _set_code(client, change_set, bravo["id"], a)
        assert _conflict(_domain(client, change_set, "Copy", c, 409)) == alpha["id"]

        # A record's own value is not a conflict.
        _set_code(client, change_set, bravo["id"], a)

        # A change set-only record holds its value until it is deleted.
        charlie = _domain(client, change_set, "Charlie", d).json()
        assert _conflict(_domain(client, change_set, "Copy", d, 409)) == charlie["id"]
        _delete(client, change_set, charlie["id"])
        _domain(client, change_set, "Delta", d)

        # A deleted base record frees its value too.
        _delete(client, change_set, alpha["id"])
        _domain(client, change_set, "Echo", c)
