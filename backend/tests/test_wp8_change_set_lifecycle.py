"""WP8 package-1 tests: change set lifecycle orchestration.

These cover root change set creation, derivation from active and retired history, cursor-paged listing,
detail read, rename, discard, optimistic-concurrency conflicts, and the catalogue-retirement guard.
Lifecycle audit is verified directly against :class:`AuditEvent` because workspace-scoped events
carry no ``AuditEventSubject`` rows and therefore never surface on object-history endpoints.
"""

from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import func, select

from app.db import SessionLocal
from app.main import app
from app.models.database import AuditEvent, AuditEventSubject


def _key(prefix: str) -> str:
    return f"{prefix}-{uuid4().hex[:10]}"


def _create_workspace(client, key: str) -> dict:
    response = client.post("/api/v1/workspaces", json={"key": key, "label": key})
    assert response.status_code == 201, response.text
    return response.json()


def _create_change_set(
    client,
    workspace_key: str,
    *,
    name: str | None = None,
    derived_from_publication_id: str | None = None,
    expected_status: int = 201,
):
    payload = {}
    if name is not None:
        payload["name"] = name
    if derived_from_publication_id is not None:
        payload["derivedFromPublicationId"] = derived_from_publication_id
    response = client.post(f"/api/v1/workspaces/{workspace_key}/change-sets", json=payload)
    assert response.status_code == expected_status, response.text
    return response


def _add_language(client, workspace_key: str, change_set: dict, suffix: str) -> dict:
    response = client.post(
        "/api/v1/objects",
        json={
            "applicationKey": "rdm-translations",
            "objectTypeKey": "language",
            "name": f"Language {suffix}",
            "attributes": [
                {"attributeTypeKey": "language-code", "value": f"lang-{suffix}-{uuid4().hex[:8]}"}
            ],
            "changeSetId": change_set["id"],
            "expectedChangeSetVersion": change_set["version"],
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def _activate_change_set(
    client,
    change_set_id: str,
    *,
    expected_change_set_version: int,
    expected_active_publication_id: str | None = None,
) -> dict:
    payload = {"expectedChangeSetVersion": expected_change_set_version}
    if expected_active_publication_id is not None:
        payload["expectedActivePublicationId"] = expected_active_publication_id
    response = client.post(f"/api/v1/change-sets/{change_set_id}/publication", json=payload)
    assert response.status_code == 200, response.text
    return response.json()


def _publish_publication(
    client,
    workspace_key: str,
    suffix: str,
    *,
    expected_active_publication_id: str | None = None,
    name: str = "seed",
) -> dict:
    """Create one change set, add a language record, and activate it into a publication."""
    change_set = _create_change_set(client, workspace_key, name=f"{name} {suffix}").json()
    _add_language(client, workspace_key, change_set, suffix)
    return _activate_change_set(
        client,
        change_set["id"],
        expected_change_set_version=change_set["version"] + 1,
        expected_active_publication_id=expected_active_publication_id,
    )


def _change_set_events(change_set_id: str) -> list[AuditEvent]:
    with SessionLocal() as session:
        return list(
            session.scalars(
                select(AuditEvent)
                .where(
                    AuditEvent.aggregate_type == "change-set",
                    AuditEvent.aggregate_id == change_set_id,
                )
                .order_by(AuditEvent.sequence_id)
            )
        )


def _subject_count(event_ids: list[int]) -> int:
    with SessionLocal() as session:
        return session.scalar(
            select(func.count())
            .select_from(AuditEventSubject)
            .where(AuditEventSubject.audit_event_id.in_(event_ids))
        )


def test_empty_root_change_set_creation_records_created_audit_event():
    workspace_key = _key("root")
    with TestClient(app) as client:
        _create_workspace(client, workspace_key)
        change_set = _create_change_set(client, workspace_key, name="Root change set").json()
        assert change_set["derivedFromPublicationId"] is None
        assert change_set["version"] == 1
        assert change_set["name"] == "Root change set"
        assert change_set["modelReleaseId"]
        detail = client.get(f"/api/v1/change-sets/{change_set['id']}")
        assert detail.status_code == 200
        assert detail.json()["name"] == "Root change set"
        assert detail.json()["version"] == 1

    events = _change_set_events(change_set["id"])
    assert [(event.action, event.version) for event in events] == [("created", 1)]
    created = events[0]
    assert created.aggregate_type == "change-set"
    assert created.changes == {
        "workspaceKey": workspace_key,
        "modelReleaseId": change_set["modelReleaseId"],
        "name": "Root change set",
    }
    assert _subject_count([created.sequence_id]) == 0


def test_change_set_derivation_from_active_publication():
    workspace_key = _key("derive-active")
    with TestClient(app) as client:
        _create_workspace(client, workspace_key)
        active = _publish_publication(client, workspace_key, "active", name="seed")
        assert client.get(f"/api/v1/publications/{active['id']}").json()["status"] == "active"
        derived = _create_change_set(
            client,
            workspace_key,
            name="Derived from active",
            derived_from_publication_id=active["id"],
        ).json()
        assert derived["derivedFromPublicationId"] == active["id"]
        assert derived["modelReleaseId"] == active["modelReleaseId"]
        assert derived["version"] == 1

    events = _change_set_events(derived["id"])
    assert [(event.action, event.version) for event in events] == [("derived", 1)]
    assert events[0].changes == {
        "workspaceKey": workspace_key,
        "modelReleaseId": derived["modelReleaseId"],
        "name": "Derived from active",
        "derivedFromPublicationId": active["id"],
    }
    assert _subject_count([events[0].sequence_id]) == 0


def test_change_set_derivation_from_an_older_retired_publication():
    workspace_key = _key("derive-retired")
    with TestClient(app) as client:
        _create_workspace(client, workspace_key)
        first = _publish_publication(client, workspace_key, "first", name="first")
        second = _publish_publication(
            client,
            workspace_key,
            "second",
            name="second",
            expected_active_publication_id=first["id"],
        )
        assert client.get(f"/api/v1/publications/{first['id']}").json()["status"] == "withdrawn"
        assert client.get(f"/api/v1/publications/{second['id']}").json()["status"] == "active"

        derived = _create_change_set(
            client, workspace_key, name="Derived from retired", derived_from_publication_id=first["id"]
        ).json()
        assert derived["derivedFromPublicationId"] == first["id"]
        assert derived["modelReleaseId"] == first["modelReleaseId"]

    events = _change_set_events(derived["id"])
    assert [(event.action, event.version) for event in events] == [("derived", 1)]
    assert events[0].changes["derivedFromPublicationId"] == first["id"]
    assert events[0].changes["workspaceKey"] == workspace_key


def test_change_set_list_cursor_detail_rename_and_discard():
    workspace_key = _key("lifecycle")
    with TestClient(app) as client:
        _create_workspace(client, workspace_key)
        first = _create_change_set(client, workspace_key, name="First").json()
        second = _create_change_set(client, workspace_key, name="Second").json()

        first_page = client.get(f"/api/v1/workspaces/{workspace_key}/change-sets", params={"pageSize": 1})
        assert first_page.status_code == 200
        assert len(first_page.json()["items"]) == 1
        cursor = first_page.json()["nextCursor"]
        assert cursor is not None
        second_page = client.get(
            f"/api/v1/workspaces/{workspace_key}/change-sets",
            params={"pageSize": 1, "cursor": cursor},
        )
        assert second_page.status_code == 200
        assert len(second_page.json()["items"]) == 1
        assert second_page.json()["nextCursor"] is None
        names = {
            first_page.json()["items"][0]["name"],
            second_page.json()["items"][0]["name"],
        }
        assert names == {"First", "Second"}

        # List is bound to the workspace: another workspace's change sets never leak in, and a cursor
        # minted for one workspace is rejected by a different workspace's list.
        other_key = _key("other")
        _create_workspace(client, other_key)
        _create_change_set(client, other_key, name="Other")
        other_page = client.get(f"/api/v1/workspaces/{other_key}/change-sets", params={"pageSize": 5})
        assert other_page.status_code == 200
        assert [item["name"] for item in other_page.json()["items"]] == ["Other"]
        mismatched = client.get(
            f"/api/v1/workspaces/{other_key}/change-sets",
            params={"pageSize": 1, "cursor": cursor},
        )
        assert mismatched.status_code == 422
        assert mismatched.json()["error"]["code"] == "invalid_cursor"

        detail = client.get(f"/api/v1/change-sets/{second['id']}")
        assert detail.status_code == 200
        assert detail.json()["name"] == "Second"

        renamed = client.patch(
            f"/api/v1/change-sets/{second['id']}",
            json={"name": "Renamed", "expectedVersion": 1},
        )
        assert renamed.status_code == 200
        assert renamed.json()["name"] == "Renamed"
        assert renamed.json()["version"] == 2

        discarded = client.delete(
            f"/api/v1/change-sets/{second['id']}", params={"expectedVersion": 2}
        )
        assert discarded.status_code == 204
        missing = client.get(f"/api/v1/change-sets/{second['id']}")
        assert missing.status_code == 404
        assert missing.json()["error"]["code"] == "change_set_not_found"

        # Discard removes only the mutable change set; workspace identity and the sibling change set remain.
        assert client.get(f"/api/v1/workspaces/{workspace_key}").status_code == 200
        assert client.get(f"/api/v1/change-sets/{first['id']}").status_code == 200

    events = _change_set_events(second["id"])
    assert [(event.action, event.version) for event in events] == [
        ("created", 1),
        ("renamed", 2),
        ("discarded", 3),
    ]
    renamed_event = events[1]
    assert renamed_event.changes == {"name": {"from": "Second", "to": "Renamed"}}
    discarded_event = events[2]
    assert discarded_event.changes == {"workspaceKey": workspace_key}
    assert _subject_count([event.sequence_id for event in events]) == 0


def test_change_set_rename_and_discard_enforce_optimistic_concurrency():
    workspace_key = _key("conflict")
    with TestClient(app) as client:
        _create_workspace(client, workspace_key)
        change_set = _create_change_set(client, workspace_key, name="Original").json()

        renamed = client.patch(
            f"/api/v1/change-sets/{change_set['id']}",
            json={"name": "Renamed", "expectedVersion": 1},
        )
        assert renamed.status_code == 200

        stale_rename = client.patch(
            f"/api/v1/change-sets/{change_set['id']}",
            json={"name": "Stale", "expectedVersion": 1},
        )
        assert stale_rename.status_code == 409
        assert stale_rename.json()["error"]["code"] == "change_set_version_conflict"

        stale_discard = client.delete(
            f"/api/v1/change-sets/{change_set['id']}", params={"expectedVersion": 1}
        )
        assert stale_discard.status_code == 409
        assert stale_discard.json()["error"]["code"] == "change_set_version_conflict"

        # The change set is untouched by the rejected claims.
        assert client.get(f"/api/v1/change-sets/{change_set['id']}").json()["version"] == 2


def test_missing_change_set_returns_change_set_not_found():
    missing_id = str(uuid4())
    with TestClient(app) as client:
        for request in (
            lambda: client.get(f"/api/v1/change-sets/{missing_id}"),
            lambda: client.patch(
                f"/api/v1/change-sets/{missing_id}",
                json={"name": "Missing", "expectedVersion": 1},
            ),
            lambda: client.delete(
                f"/api/v1/change-sets/{missing_id}", params={"expectedVersion": 1}
            ),
        ):
            response = request()
            assert response.status_code == 404
            assert response.json()["error"]["code"] == "change_set_not_found"


def test_catalogue_retirement_blocks_change_set_derive_rename_and_discard():
    workspace_key = _key("retired-mutations")
    with TestClient(app) as client:
        workspace = _create_workspace(client, workspace_key)
        published = _publish_publication(client, workspace_key, "seed", name="seed")
        change_set = _create_change_set(client, workspace_key, name="Existing").json()
        retired = client.patch(
            f"/api/v1/workspaces/{workspace_key}",
            json={"status": "retired", "expectedVersion": workspace["version"]},
        )
        assert retired.status_code == 200
        assert retired.json()["status"] == "retired"

        derive = _create_change_set(
            client,
            workspace_key,
            name="Blocked derive",
            derived_from_publication_id=published["id"],
            expected_status=409,
        )
        assert derive.json()["error"]["code"] == "workspace_retired"
        create = _create_change_set(client, workspace_key, name="Blocked create", expected_status=409)
        assert create.json()["error"]["code"] == "workspace_retired"

        rename = client.patch(
            f"/api/v1/change-sets/{change_set['id']}",
            json={"name": "Blocked rename", "expectedVersion": change_set["version"]},
        )
        assert rename.status_code == 409
        assert rename.json()["error"]["code"] == "workspace_retired"

        discard = client.delete(
            f"/api/v1/change-sets/{change_set['id']}",
            params={"expectedVersion": change_set["version"]},
        )
        assert discard.status_code == 409
        assert discard.json()["error"]["code"] == "workspace_retired"

        # The workspace catalogue record stays readable and the change set row survives each rejection.
        assert client.get(f"/api/v1/workspaces/{workspace_key}").status_code == 200
        assert client.get(f"/api/v1/change-sets/{change_set['id']}").json()["name"] == "Existing"


def test_discard_removes_only_the_mutable_change_set_not_history_identity_or_audit():
    workspace_key = _key("discard-immutable")
    with TestClient(app) as client:
        _create_workspace(client, workspace_key)
        publication = _publish_publication(client, workspace_key, "seed", name="seed")
        change_set = _create_change_set(client, workspace_key, name="Transient").json()

        discarded = client.delete(
            f"/api/v1/change-sets/{change_set['id']}", params={"expectedVersion": 1}
        )
        assert discarded.status_code == 204
        assert client.get(f"/api/v1/change-sets/{change_set['id']}").status_code == 404
        # The published publication and the workspace catalogue record survive the discard.
        publication_detail = client.get(f"/api/v1/publications/{publication['id']}")
        assert publication_detail.status_code == 200
        assert publication_detail.json()["status"] == "active"
        assert client.get(f"/api/v1/workspaces/{workspace_key}").status_code == 200

    events = _change_set_events(change_set["id"])
    assert [(event.action, event.version) for event in events] == [("created", 1), ("discarded", 2)]
    assert events[1].changes == {"workspaceKey": workspace_key}
    assert _subject_count([event.sequence_id for event in events]) == 0


def test_record_level_crud_audit_stays_separate_from_workspace_lifecycle_audit():
    workspace_key = _key("audit-separation")
    with TestClient(app) as client:
        _create_workspace(client, workspace_key)
        change_set = _create_change_set(client, workspace_key, name="Separate").json()
        language = _add_language(client, workspace_key, change_set, "separate")
        client.patch(
            f"/api/v1/change-sets/{change_set['id']}",
            json={"name": "Renamed separate", "expectedVersion": 2},
        )
        client.delete(
            f"/api/v1/change-sets/{change_set['id']}", params={"expectedVersion": 3}
        )

    with SessionLocal() as session:
        lifecycle = list(
            session.scalars(
                select(AuditEvent)
                .where(
                    AuditEvent.aggregate_type == "change-set",
                    AuditEvent.aggregate_id == change_set["id"],
                )
                .order_by(AuditEvent.sequence_id)
            )
        )
        record_level = list(
            session.scalars(
                select(AuditEvent)
                .where(
                    AuditEvent.aggregate_type == "change-set-object",
                    AuditEvent.aggregate_id == language["id"],
                )
                .order_by(AuditEvent.sequence_id)
            )
        )
        assert [event.action for event in lifecycle] == ["created", "renamed", "discarded"]
        assert [event.action for event in record_level] == ["created"]
        # Lifecycle events never carry per-object AuditEventSubject rows.
        subject_total = session.scalar(
            select(func.count())
            .select_from(AuditEventSubject)
            .where(AuditEventSubject.audit_event_id.in_([event.sequence_id for event in lifecycle]))
        )
        assert subject_total == 0
