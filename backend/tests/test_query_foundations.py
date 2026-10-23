from uuid import uuid4

import pytest
from harness_identity import TestClient as LiveTestClient
from test_api import ChangeSetTestClient as TestClient

from app.main import app


def _attr(key: str, value):
    return {"attributeTypeKey": key, "value": value}


def _create_domain(
    client: TestClient,
    token: str,
    index: int,
    *,
        workspace_key: str = "default",
):
    response = client.post(
        "/api/v1/objects",
        json={
            "applicationKey": "rdm-master",
            "objectTypeKey": "domain",
            "name": f"{token} {index}",
                "workspaceKey": workspace_key,
            "attributes": [_attr("domain-code", f"{token}_{index}")],
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_object_cursor_handles_duplicate_names_and_insert_between_pages():
    token = f"WP5_{uuid4().hex[:8]}"
    with TestClient(app) as client:
        created = [_create_domain(client, token, index) for index in range(3)]
        for item in created:
            response = client.patch(
                f"/api/v1/objects/domain/{item['id']}",
                json={"name": token, "expectedVersion": item["version"]},
            )
            assert response.status_code == 200

        first = client.get(
            "/api/v1/objects/domain",
            params={"search": token, "sort": "name", "pageSize": 1},
        ).json()
        assert first["nextCursor"] is not None
        inserted = _create_domain(client, token, 99)
        inserted = client.patch(
            f"/api/v1/objects/domain/{inserted['id']}",
            json={"name": token, "expectedVersion": inserted["version"]},
        ).json()

        seen = [first["items"][0]["id"]]
        cursor = first["nextCursor"]
        while cursor:
            page = client.get(
                "/api/v1/objects/domain",
                params={
                    "search": token,
                    "sort": "name",
                    "pageSize": 1,
                    "cursor": cursor,
                },
            ).json()
            seen.extend(item["id"] for item in page["items"])
            cursor = page["nextCursor"]

        # A newly inserted equal-sort-key record can sort before the cursor's immutable tie-breaker;
        # traversal must retain every record that was already visible and never duplicate one.
        assert {item["id"] for item in created}.issubset(seen)
        assert len(seen) == len(set(seen))


def test_object_lifecycle_is_bound_to_cursor_filters_and_sort():
    token = f"WP5_{uuid4().hex[:8]}"
    with TestClient(app) as client:
        first_object = _create_domain(client, token, 1)
        second_object = _create_domain(client, token, 2)
        first = client.get(
            "/api/v1/objects/domain",
            params=[
                ("search", token),
                ("sort", "-name"),
                ("pageSize", "1"),
            ],
        )
        assert first.status_code == 200
        assert first.json()["items"][0]["id"] == second_object["id"]
        cursor = first.json()["nextCursor"]
        second = client.get(
            "/api/v1/objects/domain",
            params=[
                ("search", token),
                ("sort", "-name"),
                ("pageSize", "1"),
                ("cursor", cursor),
            ],
        )
        assert second.status_code == 200
        assert second.json()["items"][0]["id"] == first_object["id"]

        mismatched = client.get(
            "/api/v1/objects/domain",
            params={
                "search": f"{token}-different",
                "sort": "-name",
                "pageSize": 1,
                "cursor": cursor,
            },
        )
        assert mismatched.status_code == 422
        assert mismatched.json()["error"]["code"] == "INVALID_CURSOR"


@pytest.mark.parametrize("context", ["live", "change_set"])
def test_every_built_in_object_sort_supports_cursor_traversal(context):
    token = f"WP5_{uuid4().hex[:8]}"
    client_type = LiveTestClient if context == "live" else TestClient
    with client_type(app) as client:
        created = {
            _create_domain(client, token, index)["id"] for index in range(1, 4)
        }
        if context == "change_set":
            # Change sets record no timestamps (WP-10K): a timestamp sort is refused explicitly.
            for sort in ("createdAt", "-updatedAt"):
                refused = client.get(
                    "/api/v1/objects/domain", params={"search": token, "sort": sort}
                )
                assert refused.status_code == 422, refused.text
                assert refused.json()["error"]["code"] == "INVALID_SORT"
        timestamp_sorts = ("createdAt", "-createdAt", "updatedAt", "-updatedAt")
        for sort in ("name", "-name", *(timestamp_sorts if context == "live" else ())):
            seen: list[str] = []
            cursor = None
            while True:
                params = {"search": token, "sort": sort, "pageSize": 1}
                if cursor is not None:
                    params["cursor"] = cursor
                response = client.get("/api/v1/objects/domain", params=params)
                assert response.status_code == 200, response.text
                page = response.json()
                seen.extend(item["id"] for item in page["items"])
                cursor = page["nextCursor"]
                if cursor is None:
                    break
            assert set(seen) == created
            assert len(seen) == len(created)


def test_relation_expansion_is_paged_cursor_bound_and_workspace_filtered():
    token = uuid4().hex[:8]
    with TestClient(app) as client:
        anchor = _create_domain(client, f"ANCHOR_{token}", 1)
        for index in range(2):
            response = client.post(
                "/api/v1/objects",
                json={
                    "applicationKey": "rdm-master",
                    "objectTypeKey": "codelist",
                    "parentObjectId": anchor["id"],
                    "name": f"RELATED_{token} {index}",
                    "attributes": [_attr("codelist-code", f"RELATED_{token}_{index}")],
                },
            )
            assert response.status_code == 201, response.text

        first = client.get("/api/v1/relations", params={"objectId": anchor["id"], "pageSize": 1})
        assert first.status_code == 200
        assert first.json()["nextCursor"] is not None
        second = client.get(
            "/api/v1/relations",
            params={
                "objectId": anchor["id"],
                "pageSize": 1,
                "cursor": first.json()["nextCursor"],
            },
        )
        assert second.status_code == 200
        assert second.json()["nextCursor"] is None
        assert len({
            first.json()["items"][0]["relation"]["id"],
            second.json()["items"][0]["relation"]["id"],
        }) == 2

        mismatch = client.get(
            "/api/v1/relations",
            params={
                "objectId": anchor["id"],
                "direction": "outgoing",
                "cursor": first.json()["nextCursor"],
            },
        )
        assert mismatch.status_code == 422
        assert mismatch.json()["error"]["code"] == "INVALID_CURSOR"


def test_object_parent_candidate_and_relation_queries_preserve_workspace_scope():
    token = f"WP5_{uuid4().hex[:8]}"
    with TestClient(app) as client:
        for key in ("west", "east"):
            response = client.post("/api/v1/workspaces", json={"key": key, "label": key.title()})
            assert response.status_code in {201, 409}
        west_change_set = client.post("/api/v1/workspaces/west/change-sets", json={}).json()
        east_change_set = client.post("/api/v1/workspaces/east/change-sets", json={}).json()
        west_response = client.post("/api/v1/objects", json={
            "applicationKey": "rdm-master", "objectTypeKey": "domain", "name": f"{token} west",
            "attributes": [_attr("domain-code", f"{token}_west")],
            "changeSetId": west_change_set["id"], "expectedChangeSetVersion": 1,
        })
        east_response = client.post("/api/v1/objects", json={
            "applicationKey": "rdm-master", "objectTypeKey": "domain", "name": f"{token} east",
            "attributes": [_attr("domain-code", f"{token}_east")],
            "changeSetId": east_change_set["id"], "expectedChangeSetVersion": 1,
        })
        assert west_response.status_code == east_response.status_code == 201
        west, east = west_response.json(), east_response.json()

        candidates = client.get(
            "/api/v1/objects/domain",
            params={"changeSetId": west_change_set["id"], "search": token},
        )
        assert candidates.status_code == 200
        assert [item["id"] for item in candidates.json()["items"]] == [west["id"]]

        wrong_parent = client.post(
            "/api/v1/objects",
            json={
                "applicationKey": "rdm-master",
                "objectTypeKey": "codelist",
                "parentObjectId": east["id"],
                "name": f"Wrong parent {token}",
                "attributes": [_attr("codelist-code", f"WRONG_{token}")],
                "changeSetId": west_change_set["id"],
                "expectedChangeSetVersion": 2,
            },
        )
        assert wrong_parent.status_code == 422
        assert wrong_parent.json()["error"]["code"] == "PARENT_WRONG_SCOPE"

        wrong_relation = client.post(
            "/api/v1/relations",
            json={
                "relationTypeKey": "reference-has-system-representation",
                "fromObjectId": west["id"],
                "toObjectId": east["id"],
                "changeSetId": west_change_set["id"],
                "expectedChangeSetVersion": 2,
            },
        )
        assert wrong_relation.status_code == 422
        assert wrong_relation.json()["error"]["code"] == "RELATION_ENDPOINT_MISSING"


def test_object_history_includes_safe_object_and_connected_relation_events():
    token = f"WP5_{uuid4().hex[:8]}"
    with TestClient(app) as client:
        first = _create_domain(client, token, 1)
        second = _create_domain(client, token, 2)
        attribute_update = client.patch(
            f"/api/v1/objects/domain/{first['id']}/attributes/domain-code",
            json={"value": f"{token}_updated", "expectedVersion": first["version"]},
        )
        assert attribute_update.status_code == 200

        first_page = client.get(
            f"/api/v1/objects/domain/{first['id']}/history", params={"pageSize": 1}
        )
        assert first_page.status_code == 200
        cursor = first_page.json()["nextCursor"]
        assert cursor is not None
        mismatched_cursor = cursor
        events = list(first_page.json()["items"])
        while cursor:
            page = client.get(
                f"/api/v1/objects/domain/{first['id']}/history",
                params={"pageSize": 1, "cursor": cursor},
            )
            assert page.status_code == 200
            events.extend(page.json()["items"])
            cursor = page.json()["nextCursor"]
        assert len({item["id"] for item in events}) == 2
        assert {item["aggregateType"] for item in events} == {"change-set-object"}
        assert all("changes" not in item for item in events)

        wrong_object = client.get(
            f"/api/v1/objects/domain/{second['id']}/history",
            params={"pageSize": 1, "cursor": mismatched_cursor},
        )
        assert wrong_object.status_code == 422
        assert wrong_object.json()["error"]["code"] == "INVALID_CURSOR"


def test_relation_writes_project_both_endpoint_subjects():
    token = uuid4().hex[:8]
    with TestClient(app) as client:
        domain = _create_domain(client, f"SUBJECT_{token}", 1)
        system = client.post(
            "/api/v1/objects",
            json={
                "applicationKey": "rdm-systems",
                "objectTypeKey": "system",
                "name": f"System {token}",
                "attributes": [_attr("system-code", f"SYSTEM_{token}")],
            },
        ).json()
        system_value = client.post(
            "/api/v1/objects",
            json={
                "applicationKey": "rdm-systems",
                "objectTypeKey": "system-value",
                "parentObjectId": system["id"],
                "name": f"System value {token}",
                "attributes": [
                    _attr("value-code", f"VALUE_{token}"),
                    _attr("value-name", f"Value {token}"),
                ],
            },
        ).json()
        relation = client.post(
            "/api/v1/relations",
            json={
                "relationTypeKey": "reference-has-system-representation",
                "fromObjectId": domain["id"],
                "toObjectId": system_value["id"],
            },
        )
        assert relation.status_code == 201, relation.text
        updated = client.patch(
            f"/api/v1/relations/{relation.json()['id']}",
            json={"attributes": {}, "expectedVersion": relation.json()["version"]},
        )
        assert updated.status_code == 200, updated.text

        for object_type_key, object_id in (
            ("domain", domain["id"]),
            ("system-value", system_value["id"]),
        ):
            history = client.get(f"/api/v1/objects/{object_type_key}/{object_id}/history")
            assert history.status_code == 200
            assert any(
                item["aggregateType"] == "relation" and item["aggregateId"] == relation.json()["id"]
                for item in history.json()["items"]
            )
            relation_updates = [
                item
                for item in history.json()["items"]
                if item["aggregateType"] == "relation" and item["action"] == "updated"
            ]
            assert relation_updates[0]["attributeTypeKeys"] == []
