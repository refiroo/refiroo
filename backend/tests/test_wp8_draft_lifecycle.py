"""WP8 package-1 tests: workspace draft lifecycle orchestration.

These cover root draft creation, derivation from active and retired history, cursor-paged listing,
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


def _create_draft(
    client,
    workspace_key: str,
    *,
    name: str | None = None,
    derived_from_revision_id: str | None = None,
    expected_status: int = 201,
):
    payload = {}
    if name is not None:
        payload["name"] = name
    if derived_from_revision_id is not None:
        payload["derivedFromRevisionId"] = derived_from_revision_id
    response = client.post(f"/api/v1/workspaces/{workspace_key}/drafts", json=payload)
    assert response.status_code == expected_status, response.text
    return response


def _add_language(client, workspace_key: str, draft: dict, suffix: str) -> dict:
    response = client.post(
        "/api/v1/objects",
        json={
            "applicationKey": "rdm-translations",
            "objectTypeKey": "language",
            "name": f"Language {suffix}",
            "attributes": [
                {"attributeTypeKey": "language-code", "value": f"lang-{suffix}-{uuid4().hex[:8]}"}
            ],
            "workspaceDraftId": draft["id"],
            "expectedWorkspaceDraftVersion": draft["version"],
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def _activate_draft(
    client,
    draft_id: str,
    *,
    expected_draft_version: int,
    expected_active_revision_id: str | None = None,
) -> dict:
    payload = {"expectedDraftVersion": expected_draft_version}
    if expected_active_revision_id is not None:
        payload["expectedActiveRevisionId"] = expected_active_revision_id
    response = client.post(f"/api/v1/workspace-drafts/{draft_id}/activation", json=payload)
    assert response.status_code == 200, response.text
    return response.json()


def _publish_revision(
    client,
    workspace_key: str,
    suffix: str,
    *,
    expected_active_revision_id: str | None = None,
    name: str = "seed",
) -> dict:
    """Create one draft, add a language record, and activate it into a revision."""
    draft = _create_draft(client, workspace_key, name=f"{name} {suffix}").json()
    _add_language(client, workspace_key, draft, suffix)
    return _activate_draft(
        client,
        draft["id"],
        expected_draft_version=draft["version"] + 1,
        expected_active_revision_id=expected_active_revision_id,
    )


def _draft_events(draft_id: str) -> list[AuditEvent]:
    with SessionLocal() as session:
        return list(
            session.scalars(
                select(AuditEvent)
                .where(
                    AuditEvent.aggregate_type == "workspace-draft",
                    AuditEvent.aggregate_id == draft_id,
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


def test_empty_root_draft_creation_records_created_audit_event():
    workspace_key = _key("root")
    with TestClient(app) as client:
        _create_workspace(client, workspace_key)
        draft = _create_draft(client, workspace_key, name="Root draft").json()
        assert draft["derivedFromRevisionId"] is None
        assert draft["version"] == 1
        assert draft["name"] == "Root draft"
        assert draft["modelReleaseId"]
        detail = client.get(f"/api/v1/workspace-drafts/{draft['id']}")
        assert detail.status_code == 200
        assert detail.json()["name"] == "Root draft"
        assert detail.json()["version"] == 1

    events = _draft_events(draft["id"])
    assert [(event.action, event.version) for event in events] == [("created", 1)]
    created = events[0]
    assert created.aggregate_type == "workspace-draft"
    assert created.changes == {
        "workspaceKey": workspace_key,
        "modelReleaseId": draft["modelReleaseId"],
        "name": "Root draft",
    }
    assert _subject_count([created.sequence_id]) == 0


def test_draft_derivation_from_active_revision():
    workspace_key = _key("derive-active")
    with TestClient(app) as client:
        _create_workspace(client, workspace_key)
        active = _publish_revision(client, workspace_key, "active", name="seed")
        assert client.get(f"/api/v1/workspace-revisions/{active['id']}").json()["status"] == "active"
        derived = _create_draft(
            client,
            workspace_key,
            name="Derived from active",
            derived_from_revision_id=active["id"],
        ).json()
        assert derived["derivedFromRevisionId"] == active["id"]
        assert derived["modelReleaseId"] == active["modelReleaseId"]
        assert derived["version"] == 1

    events = _draft_events(derived["id"])
    assert [(event.action, event.version) for event in events] == [("derived", 1)]
    assert events[0].changes == {
        "workspaceKey": workspace_key,
        "modelReleaseId": derived["modelReleaseId"],
        "name": "Derived from active",
        "derivedFromRevisionId": active["id"],
    }
    assert _subject_count([events[0].sequence_id]) == 0


def test_draft_derivation_from_an_older_retired_revision():
    workspace_key = _key("derive-retired")
    with TestClient(app) as client:
        _create_workspace(client, workspace_key)
        first = _publish_revision(client, workspace_key, "first", name="first")
        second = _publish_revision(
            client,
            workspace_key,
            "second",
            name="second",
            expected_active_revision_id=first["id"],
        )
        assert client.get(f"/api/v1/workspace-revisions/{first['id']}").json()["status"] == "retired"
        assert client.get(f"/api/v1/workspace-revisions/{second['id']}").json()["status"] == "active"

        derived = _create_draft(
            client, workspace_key, name="Derived from retired", derived_from_revision_id=first["id"]
        ).json()
        assert derived["derivedFromRevisionId"] == first["id"]
        assert derived["modelReleaseId"] == first["modelReleaseId"]

    events = _draft_events(derived["id"])
    assert [(event.action, event.version) for event in events] == [("derived", 1)]
    assert events[0].changes["derivedFromRevisionId"] == first["id"]
    assert events[0].changes["workspaceKey"] == workspace_key


def test_draft_list_cursor_detail_rename_and_discard():
    workspace_key = _key("lifecycle")
    with TestClient(app) as client:
        _create_workspace(client, workspace_key)
        first = _create_draft(client, workspace_key, name="First").json()
        second = _create_draft(client, workspace_key, name="Second").json()

        first_page = client.get(f"/api/v1/workspaces/{workspace_key}/drafts", params={"pageSize": 1})
        assert first_page.status_code == 200
        assert len(first_page.json()["items"]) == 1
        cursor = first_page.json()["nextCursor"]
        assert cursor is not None
        second_page = client.get(
            f"/api/v1/workspaces/{workspace_key}/drafts",
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

        # List is bound to the workspace: another workspace's drafts never leak in, and a cursor
        # minted for one workspace is rejected by a different workspace's list.
        other_key = _key("other")
        _create_workspace(client, other_key)
        _create_draft(client, other_key, name="Other")
        other_page = client.get(f"/api/v1/workspaces/{other_key}/drafts", params={"pageSize": 5})
        assert other_page.status_code == 200
        assert [item["name"] for item in other_page.json()["items"]] == ["Other"]
        mismatched = client.get(
            f"/api/v1/workspaces/{other_key}/drafts",
            params={"pageSize": 1, "cursor": cursor},
        )
        assert mismatched.status_code == 422
        assert mismatched.json()["error"]["code"] == "invalid_cursor"

        detail = client.get(f"/api/v1/workspace-drafts/{second['id']}")
        assert detail.status_code == 200
        assert detail.json()["name"] == "Second"

        renamed = client.patch(
            f"/api/v1/workspace-drafts/{second['id']}",
            json={"name": "Renamed", "expectedVersion": 1},
        )
        assert renamed.status_code == 200
        assert renamed.json()["name"] == "Renamed"
        assert renamed.json()["version"] == 2

        discarded = client.delete(
            f"/api/v1/workspace-drafts/{second['id']}", params={"expectedVersion": 2}
        )
        assert discarded.status_code == 204
        missing = client.get(f"/api/v1/workspace-drafts/{second['id']}")
        assert missing.status_code == 404
        assert missing.json()["error"]["code"] == "workspace_draft_not_found"

        # Discard removes only the mutable draft; workspace identity and the sibling draft remain.
        assert client.get(f"/api/v1/workspaces/{workspace_key}").status_code == 200
        assert client.get(f"/api/v1/workspace-drafts/{first['id']}").status_code == 200

    events = _draft_events(second["id"])
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


def test_draft_rename_and_discard_enforce_optimistic_concurrency():
    workspace_key = _key("conflict")
    with TestClient(app) as client:
        _create_workspace(client, workspace_key)
        draft = _create_draft(client, workspace_key, name="Original").json()

        renamed = client.patch(
            f"/api/v1/workspace-drafts/{draft['id']}",
            json={"name": "Renamed", "expectedVersion": 1},
        )
        assert renamed.status_code == 200

        stale_rename = client.patch(
            f"/api/v1/workspace-drafts/{draft['id']}",
            json={"name": "Stale", "expectedVersion": 1},
        )
        assert stale_rename.status_code == 409
        assert stale_rename.json()["error"]["code"] == "workspace_draft_version_conflict"

        stale_discard = client.delete(
            f"/api/v1/workspace-drafts/{draft['id']}", params={"expectedVersion": 1}
        )
        assert stale_discard.status_code == 409
        assert stale_discard.json()["error"]["code"] == "workspace_draft_version_conflict"

        # The draft is untouched by the rejected claims.
        assert client.get(f"/api/v1/workspace-drafts/{draft['id']}").json()["version"] == 2


def test_missing_draft_returns_workspace_draft_not_found():
    missing_id = str(uuid4())
    with TestClient(app) as client:
        for request in (
            lambda: client.get(f"/api/v1/workspace-drafts/{missing_id}"),
            lambda: client.patch(
                f"/api/v1/workspace-drafts/{missing_id}",
                json={"name": "Missing", "expectedVersion": 1},
            ),
            lambda: client.delete(
                f"/api/v1/workspace-drafts/{missing_id}", params={"expectedVersion": 1}
            ),
        ):
            response = request()
            assert response.status_code == 404
            assert response.json()["error"]["code"] == "workspace_draft_not_found"


def test_catalogue_retirement_blocks_draft_derive_rename_and_discard():
    workspace_key = _key("retired-mutations")
    with TestClient(app) as client:
        workspace = _create_workspace(client, workspace_key)
        published = _publish_revision(client, workspace_key, "seed", name="seed")
        draft = _create_draft(client, workspace_key, name="Existing").json()
        retired = client.patch(
            f"/api/v1/workspaces/{workspace_key}",
            json={"status": "retired", "expectedVersion": workspace["version"]},
        )
        assert retired.status_code == 200
        assert retired.json()["status"] == "retired"

        derive = _create_draft(
            client,
            workspace_key,
            name="Blocked derive",
            derived_from_revision_id=published["id"],
            expected_status=409,
        )
        assert derive.json()["error"]["code"] == "workspace_retired"
        create = _create_draft(client, workspace_key, name="Blocked create", expected_status=409)
        assert create.json()["error"]["code"] == "workspace_retired"

        rename = client.patch(
            f"/api/v1/workspace-drafts/{draft['id']}",
            json={"name": "Blocked rename", "expectedVersion": draft["version"]},
        )
        assert rename.status_code == 409
        assert rename.json()["error"]["code"] == "workspace_retired"

        discard = client.delete(
            f"/api/v1/workspace-drafts/{draft['id']}",
            params={"expectedVersion": draft["version"]},
        )
        assert discard.status_code == 409
        assert discard.json()["error"]["code"] == "workspace_retired"

        # The workspace catalogue record stays readable and the draft row survives each rejection.
        assert client.get(f"/api/v1/workspaces/{workspace_key}").status_code == 200
        assert client.get(f"/api/v1/workspace-drafts/{draft['id']}").json()["name"] == "Existing"


def test_discard_removes_only_the_mutable_draft_not_history_identity_or_audit():
    workspace_key = _key("discard-immutable")
    with TestClient(app) as client:
        _create_workspace(client, workspace_key)
        revision = _publish_revision(client, workspace_key, "seed", name="seed")
        draft = _create_draft(client, workspace_key, name="Transient").json()

        discarded = client.delete(
            f"/api/v1/workspace-drafts/{draft['id']}", params={"expectedVersion": 1}
        )
        assert discarded.status_code == 204
        assert client.get(f"/api/v1/workspace-drafts/{draft['id']}").status_code == 404
        # The published revision and the workspace catalogue record survive the discard.
        revision_detail = client.get(f"/api/v1/workspace-revisions/{revision['id']}")
        assert revision_detail.status_code == 200
        assert revision_detail.json()["status"] == "active"
        assert client.get(f"/api/v1/workspaces/{workspace_key}").status_code == 200

    events = _draft_events(draft["id"])
    assert [(event.action, event.version) for event in events] == [("created", 1), ("discarded", 2)]
    assert events[1].changes == {"workspaceKey": workspace_key}
    assert _subject_count([event.sequence_id for event in events]) == 0


def test_record_level_crud_audit_stays_separate_from_workspace_lifecycle_audit():
    workspace_key = _key("audit-separation")
    with TestClient(app) as client:
        _create_workspace(client, workspace_key)
        draft = _create_draft(client, workspace_key, name="Separate").json()
        language = _add_language(client, workspace_key, draft, "separate")
        client.patch(
            f"/api/v1/workspace-drafts/{draft['id']}",
            json={"name": "Renamed separate", "expectedVersion": 2},
        )
        client.delete(
            f"/api/v1/workspace-drafts/{draft['id']}", params={"expectedVersion": 3}
        )

    with SessionLocal() as session:
        lifecycle = list(
            session.scalars(
                select(AuditEvent)
                .where(
                    AuditEvent.aggregate_type == "workspace-draft",
                    AuditEvent.aggregate_id == draft["id"],
                )
                .order_by(AuditEvent.sequence_id)
            )
        )
        record_level = list(
            session.scalars(
                select(AuditEvent)
                .where(
                    AuditEvent.aggregate_type == "object-draft",
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
