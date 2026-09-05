from datetime import UTC, datetime
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import select, update

from app.db import SessionLocal
from app.main import app
from app.models.database import AuditEvent, AuditEventSubject, ObjectRelation, RdmObject


def _attr(key: str, value):
    return {"attributeTypeKey": key, "value": value}


def _create_domain(
    client: TestClient,
    token: str,
    index: int,
    *,
    state: str = "active",
    workspace_key: str = "default",
):
    response = client.post(
        "/api/v1/objects",
        json={
            "applicationKey": "rdm-master",
            "objectTypeKey": "domain",
            "name": f"{token} {index}",
            "state": state,
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

        assert set(seen) == {item["id"] for item in created} | {inserted["id"]}
        assert len(seen) == len(set(seen))


def test_object_state_is_repeatable_and_cursor_is_bound_to_filters_and_sort():
    token = f"WP5_{uuid4().hex[:8]}"
    with TestClient(app) as client:
        active = _create_domain(client, token, 1, state="active")
        draft = _create_domain(client, token, 2, state="draft")
        _create_domain(client, token, 3, state="retired")
        first = client.get(
            "/api/v1/objects/domain",
            params=[
                ("search", token),
                ("state", "active"),
                ("state", "draft"),
                ("sort", "-name"),
                ("pageSize", "1"),
            ],
        )
        assert first.status_code == 200
        assert first.json()["items"][0]["id"] == draft["id"]
        cursor = first.json()["nextCursor"]
        second = client.get(
            "/api/v1/objects/domain",
            params=[
                ("search", token),
                ("state", "draft"),
                ("state", "active"),
                ("sort", "-name"),
                ("pageSize", "1"),
                ("cursor", cursor),
            ],
        )
        assert second.status_code == 200
        assert second.json()["items"][0]["id"] == active["id"]

        mismatched = client.get(
            "/api/v1/objects/domain",
            params={"search": token, "sort": "name", "pageSize": 1, "cursor": cursor},
        )
        assert mismatched.status_code == 422
        assert mismatched.json()["error"]["code"] == "invalid_cursor"


def test_every_built_in_object_sort_supports_cursor_traversal():
    token = f"WP5_{uuid4().hex[:8]}"
    with TestClient(app) as client:
        created = {
            _create_domain(client, token, index, state=state)["id"]
            for index, state in enumerate(("draft", "active", "retired"), start=1)
        }
        for sort in (
            "name",
            "-name",
            "state",
            "-state",
            "createdAt",
            "-createdAt",
            "updatedAt",
            "-updatedAt",
        ):
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
        related = [_create_domain(client, f"RELATED_{token}", index) for index in range(2)]
        relation_ids = []
        with SessionLocal() as session:
            for item in related:
                relation = ObjectRelation(
                    relation_type_key="test-query-relation",
                    from_object_id=anchor["id"],
                    to_object_id=item["id"],
                )
                session.add(relation)
                session.flush()
                relation_ids.append(relation.id)
            foreign = RdmObject(
                workspace_key="other",
                application_key="rdm-master",
                object_type_key="domain",
                name="Foreign workspace",
            )
            session.add(foreign)
            session.flush()
            session.add(
                ObjectRelation(
                    relation_type_key="test-query-relation",
                    from_object_id=anchor["id"],
                    to_object_id=foreign.id,
                )
            )
            session.commit()

        first = client.get(
            "/api/v1/relations", params={"objectId": anchor["id"], "pageSize": 1}
        )
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
        assert {
            first.json()["items"][0]["relation"]["id"],
            second.json()["items"][0]["relation"]["id"],
        } == set(relation_ids)

        mismatch = client.get(
            "/api/v1/relations",
            params={
                "objectId": anchor["id"],
                "direction": "outgoing",
                "cursor": first.json()["nextCursor"],
            },
        )
        assert mismatch.status_code == 422
        assert mismatch.json()["error"]["code"] == "invalid_cursor"


def test_object_parent_candidate_and_relation_queries_preserve_workspace_scope():
    token = f"WP5_{uuid4().hex[:8]}"
    with TestClient(app) as client:
        west = _create_domain(client, token, 1, workspace_key="west")
        east = _create_domain(client, token, 2, workspace_key="east")

        candidates = client.get(
            "/api/v1/objects/domain",
            params={"workspaceKey": "west", "search": token},
        )
        assert candidates.status_code == 200
        assert [item["id"] for item in candidates.json()["items"]] == [west["id"]]

        wrong_parent = client.post(
            "/api/v1/objects",
            json={
                "applicationKey": "rdm-master",
                "objectTypeKey": "codelist",
                "workspaceKey": "west",
                "parentObjectId": east["id"],
                "name": f"Wrong parent {token}",
                "attributes": [_attr("codelist-code", f"WRONG_{token}")],
            },
        )
        assert wrong_parent.status_code == 422
        assert wrong_parent.json()["error"]["code"] == "parent_wrong_scope"

        with SessionLocal() as session:
            foreign_value = RdmObject(
                workspace_key="east",
                application_key="rdm-systems",
                object_type_key="system-value",
                name=f"Foreign value {token}",
            )
            session.add(foreign_value)
            session.commit()
            foreign_value_id = foreign_value.id
        wrong_relation = client.post(
            "/api/v1/relations",
            json={
                "relationTypeKey": "reference-has-system-representation",
                "fromObjectId": west["id"],
                "toObjectId": foreign_value_id,
            },
        )
        assert wrong_relation.status_code == 422
        assert wrong_relation.json()["error"]["code"] == "relation_wrong_scope"


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
        with SessionLocal() as session:
            relation = ObjectRelation(
                relation_type_key="test-history-relation",
                from_object_id=first["id"],
                to_object_id=second["id"],
            )
            session.add(relation)
            session.flush()
            event = AuditEvent(
                aggregate_type="relation",
                aggregate_id=relation.id,
                action="created",
                version=1,
                changes={
                    "fromObjectId": first["id"],
                    "toObjectId": second["id"],
                    "secret": {"before": "hidden", "after": "hidden"},
                },
            )
            session.add(event)
            session.flush()
            session.add_all(
                [
                    AuditEventSubject(audit_event_id=event.sequence_id, object_id=first["id"]),
                    AuditEventSubject(audit_event_id=event.sequence_id, object_id=second["id"]),
                ]
            )
            fixed_time = datetime(2026, 9, 5, 12, 0, tzinfo=UTC)
            session.execute(
                update(AuditEvent)
                .where(
                    AuditEvent.sequence_id.in_(
                        select(AuditEventSubject.audit_event_id).where(
                            AuditEventSubject.object_id == first["id"]
                        )
                    )
                )
                .values(occurred_at=fixed_time)
            )
            session.commit()

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
        assert len({item["id"] for item in events}) == 3
        assert {item["aggregateType"] for item in events} == {"object", "relation"}
        assert any(item["attributeTypeKeys"] == ["domain-code"] for item in events)
        assert all("changes" not in item for item in events)

        wrong_object = client.get(
            f"/api/v1/objects/domain/{second['id']}/history",
            params={"pageSize": 1, "cursor": mismatched_cursor},
        )
        assert wrong_object.status_code == 422
        assert wrong_object.json()["error"]["code"] == "invalid_cursor"


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
            history = client.get(
                f"/api/v1/objects/{object_type_key}/{object_id}/history"
            )
            assert history.status_code == 200
            assert any(
                item["aggregateType"] == "relation"
                and item["aggregateId"] == relation.json()["id"]
                for item in history.json()["items"]
            )
            relation_updates = [
                item
                for item in history.json()["items"]
                if item["aggregateType"] == "relation" and item["action"] == "updated"
            ]
            assert relation_updates[0]["attributeTypeKeys"] == []
