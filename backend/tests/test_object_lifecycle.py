from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import select, text

from app.db import SessionLocal
from app.main import app
from app.models.database import ModelRelease, ModelRuntimeState, ObjectDraft, RdmObject


def _attribute(key: str, value):
    return {"attributeTypeKey": key, "value": value}


def _legacy_active(client: TestClient, payload: dict) -> dict:
    response = client.post("/api/v1/objects", json=payload)
    assert response.status_code == 201, response.text
    return response.json()


def test_root_draft_history_branch_retirement_and_reactivation_are_explicit():
    token = uuid4().hex[:8]
    with TestClient(app) as client:
        created = client.post(
            "/api/v1/object-drafts",
            json={
                "applicationKey": "rdm-master",
                "objectTypeKey": "domain",
                "name": f"Draft domain {token}",
                "attributes": [_attribute("domain-code", f"LIFE_{token}")],
            },
        )
        assert created.status_code == 201, created.text
        draft = created.json()
        object_id = draft["objectId"]
        assert draft["derivedFromRevisionId"] is None
        assert client.get(f"/api/v1/objects/domain/{object_id}").status_code == 404

        saved = client.patch(
            f"/api/v1/object-drafts/{draft['id']}",
            json={
                "expectedVersion": 1,
                "name": f"Published domain {token}",
                "attributes": [
                    _attribute("domain-code", f"LIFE_{token}"),
                    _attribute("description", "First immutable snapshot"),
                    _attribute("active", True),
                ],
            },
        )
        assert saved.status_code == 200, saved.text
        draft = saved.json()
        explicit_null = client.patch(
            f"/api/v1/object-drafts/{draft['id']}",
            json={"expectedVersion": draft["version"], "name": None},
        )
        assert explicit_null.status_code == 422
        stale = client.patch(
            f"/api/v1/object-drafts/{draft['id']}",
            json={"expectedVersion": 1, "name": "Lost update"},
        )
        assert stale.status_code == 409
        assert stale.json()["error"] == {
            "code": "draft_version_conflict",
            "message": "Object draft version has changed",
            "details": {"currentVersion": 2},
        }

        activated = client.post(
            f"/api/v1/object-drafts/{draft['id']}/activation",
            json={"expectedDraftVersion": 2, "expectedActiveRevisionId": None},
        )
        assert activated.status_code == 200, activated.text
        revision_one = activated.json()
        assert revision_one["revisionNumber"] == 1
        assert revision_one["lifecycle"] == "active"
        assert revision_one["derivedFromRevisionId"] is None
        assert revision_one["supersedesRevisionId"] is None

        cloned = client.post(
            f"/api/v1/objects/domain/{object_id}/drafts",
            json={"derivedFromRevisionId": revision_one["id"]},
        )
        assert cloned.status_code == 201, cloned.text
        branch = cloned.json()
        changed = client.patch(
            f"/api/v1/object-drafts/{branch['id']}",
            json={"expectedVersion": 1, "name": f"Second domain {token}"},
        ).json()
        assert client.get(f"/api/v1/objects/domain/{object_id}").json()["name"] == (
            f"Published domain {token}"
        )

        active_conflict = client.post(
            f"/api/v1/object-drafts/{branch['id']}/activation",
            json={
                "expectedDraftVersion": changed["version"],
                "expectedActiveRevisionId": str(uuid4()),
            },
        )
        assert active_conflict.status_code == 409
        assert active_conflict.json()["error"]["code"] == "active_revision_conflict"
        assert client.get(f"/api/v1/object-drafts/{branch['id']}").status_code == 200

        activated = client.post(
            f"/api/v1/object-drafts/{branch['id']}/activation",
            json={
                "expectedDraftVersion": changed["version"],
                "expectedActiveRevisionId": revision_one["id"],
            },
        )
        assert activated.status_code == 200, activated.text
        revision_two = activated.json()
        assert revision_two["derivedFromRevisionId"] == revision_one["id"]
        assert revision_two["supersedesRevisionId"] == revision_one["id"]
        history = client.get(
            f"/api/v1/objects/domain/{object_id}/revisions", params={"pageSize": 1}
        )
        assert history.status_code == 200
        assert history.json()["items"][0]["id"] == revision_two["id"]
        assert history.json()["nextCursor"] is not None
        assert client.get(f"/api/v1/object-revisions/{revision_one['id']}").json()[
            "lifecycle"
        ] == "retired"

        retired = client.post(
            f"/api/v1/objects/domain/{object_id}/retirement",
            json={"expectedActiveRevisionId": revision_two["id"]},
        )
        assert retired.status_code == 200, retired.text
        assert retired.json()["retiredRevision"]["id"] == revision_two["id"]
        assert client.get(f"/api/v1/objects/domain/{object_id}").status_code == 404
        retired_page = client.get(
            "/api/v1/objects/domain",
            params={"lifecycle": "retired", "search": token},
        )
        assert [item["id"] for item in retired_page.json()["items"]] == [object_id]

        historical_branch = client.post(
            f"/api/v1/objects/domain/{object_id}/drafts",
            json={"derivedFromRevisionId": revision_one["id"]},
        ).json()
        reactivated = client.post(
            f"/api/v1/object-drafts/{historical_branch['id']}/activation",
            json={
                "expectedDraftVersion": historical_branch["version"],
                "expectedActiveRevisionId": None,
            },
        )
        assert reactivated.status_code == 200, reactivated.text
        revision_three = reactivated.json()
        assert revision_three["derivedFromRevisionId"] == revision_one["id"]
        assert revision_three["supersedesRevisionId"] is None
        assert client.get(f"/api/v1/objects/domain/{object_id}").status_code == 200


def test_discarding_the_last_never_activated_root_draft_removes_identity_shell():
    object_id = str(uuid4())
    with TestClient(app) as client:
        draft = client.post(
            "/api/v1/object-drafts",
            json={
                "objectId": object_id,
                "applicationKey": "rdm-master",
                "objectTypeKey": "domain",
                "name": "Temporary root draft",
                "attributes": [_attribute("domain-code", f"TMP_{uuid4().hex[:8]}")],
            },
        ).json()
        discarded = client.request(
            "DELETE",
            f"/api/v1/object-drafts/{draft['id']}",
            json={"expectedVersion": draft["version"]},
        )
        assert discarded.status_code == 204
        with SessionLocal() as session:
            assert session.scalar(
                select(RdmObject).where(RdmObject.id == object_id)
            ) is None


def test_activation_conditionally_claims_the_draft_version_at_publication():
    token = uuid4().hex[:8]
    trigger_name = f"draft_activation_race_{token}"
    with TestClient(app) as client:
        draft = client.post(
            "/api/v1/object-drafts",
            json={
                "applicationKey": "rdm-master",
                "objectTypeKey": "domain",
                "name": f"Activation race {token}",
                "attributes": [_attribute("domain-code", f"RACE_{token}")],
            },
        ).json()
        with SessionLocal() as session:
            session.execute(
                text(
                    f"CREATE TRIGGER {trigger_name} BEFORE INSERT ON object_revisions "
                    "BEGIN UPDATE object_drafts SET version = version + 1 "
                    "WHERE object_id = NEW.object_id; END"
                )
            )
            session.commit()
        try:
            activation = client.post(
                f"/api/v1/object-drafts/{draft['id']}/activation",
                json={"expectedDraftVersion": 1, "expectedActiveRevisionId": None},
            )
            assert activation.status_code == 409
            assert activation.json()["error"]["code"] == "draft_version_conflict"
            assert client.get(f"/api/v1/object-drafts/{draft['id']}").status_code == 200
            assert client.get(
                f"/api/v1/objects/domain/{draft['objectId']}"
            ).status_code == 404
        finally:
            with SessionLocal() as session:
                session.execute(text(f"DROP TRIGGER IF EXISTS {trigger_name}"))
                session.commit()


def test_retirement_refuses_a_corrupt_cross_workspace_containment_edge():
    token = uuid4().hex[:8]
    with TestClient(app) as client:
        workspace_key = f"scope-{token}"
        assert client.post(
            "/api/v1/workspaces", json={"key": workspace_key, "label": "Scope test"}
        ).status_code == 201
        root = _legacy_active(
            client,
            {
                "applicationKey": "rdm-master",
                "objectTypeKey": "domain",
                "name": f"Scope root {token}",
                "attributes": [_attribute("domain-code", f"SCOPE_ROOT_{token}")],
            },
        )
        local_parent = _legacy_active(
            client,
            {
                "applicationKey": "rdm-master",
                "objectTypeKey": "domain",
                "workspaceKey": workspace_key,
                "name": f"Local scope root {token}",
                "attributes": [_attribute("domain-code", f"SCOPE_LOCAL_{token}")],
            },
        )
        child = _legacy_active(
            client,
            {
                "applicationKey": "rdm-master",
                "objectTypeKey": "codelist",
                "workspaceKey": workspace_key,
                "parentObjectId": local_parent["id"],
                "name": f"Scope child {token}",
                "attributes": [_attribute("codelist-code", f"SCOPE_CHILD_{token}")],
            },
        )
        with SessionLocal() as session:
            stored_child = session.scalar(
                select(RdmObject).where(RdmObject.id == child["id"])
            )
            assert stored_child is not None
            stored_child.parent_object_id = root["id"]
            session.commit()
        try:
            impact = client.get(
                f"/api/v1/objects/domain/{root['id']}/retirement-impact",
                params={"expectedActiveRevisionId": root["activeRevisionId"]},
            )
            assert impact.status_code == 409
            assert impact.json()["error"]["code"] == "invalid_runtime_scope"
            assert client.get(f"/api/v1/objects/domain/{root['id']}").status_code == 200
            assert client.get(
                f"/api/v1/objects/codelist/{child['id']}"
            ).status_code == 200
        finally:
            with SessionLocal() as session:
                stored_child = session.scalar(
                    select(RdmObject).where(RdmObject.id == child["id"])
                )
                assert stored_child is not None
                stored_child.parent_object_id = None
                session.commit()


def test_compatibility_mutations_cannot_drift_the_lifecycle_projection():
    token = uuid4().hex[:8]
    with TestClient(app) as client:
        rejected_create = client.post(
            "/api/v1/objects",
            json={
                "applicationKey": "rdm-master",
                "objectTypeKey": "domain",
                "name": f"Invalid state {token}",
                "state": "retired",
                "attributes": [_attribute("domain-code", f"INVALID_{token}")],
            },
        )
        assert rejected_create.status_code == 422
        active = _legacy_active(
            client,
            {
                "applicationKey": "rdm-master",
                "objectTypeKey": "domain",
                "name": f"Stable lifecycle {token}",
                "attributes": [_attribute("domain-code", f"STABLE_{token}")],
            },
        )
        rejected_update = client.patch(
            f"/api/v1/objects/domain/{active['id']}",
            json={"expectedVersion": active["version"], "state": "retired"},
        )
        assert rejected_update.status_code == 422
        current = client.get(f"/api/v1/objects/domain/{active['id']}").json()
        assert current["activeRevisionId"] == active["activeRevisionId"]
        assert current["lifecycle"] == "active"
        assert "state" not in current


def test_activation_rejects_a_draft_pinned_to_another_model_without_losing_it():
    token = uuid4().hex[:8]
    with TestClient(app) as client:
        draft = client.post(
            "/api/v1/object-drafts",
            json={
                "applicationKey": "rdm-master",
                "objectTypeKey": "domain",
                "name": f"Pinned draft {token}",
                "attributes": [_attribute("domain-code", f"PIN_{token}")],
            },
        ).json()
        with SessionLocal() as session:
            selected_id = session.scalar(
                select(ModelRuntimeState.active_model_release_id).where(
                    ModelRuntimeState.id == 1
                )
            )
            selected = session.get(ModelRelease, selected_id)
            assert selected is not None
            other = ModelRelease(
                release_key=f"pinned-test-{token}",
                release_name="Pinned test release",
                release_version="1",
                schema_version=selected.schema_version,
                model_hash=uuid4().hex + uuid4().hex,
                model_json=selected.model_json,
                is_active=False,
            )
            session.add(other)
            session.flush()
            stored_draft = session.scalar(
                select(ObjectDraft).where(ObjectDraft.id == draft["id"])
            )
            assert stored_draft is not None
            stored_draft.model_release_id = other.id
            session.commit()
            other_public_id = other.public_id

        conflict = client.post(
            f"/api/v1/object-drafts/{draft['id']}/activation",
            json={"expectedDraftVersion": 1, "expectedActiveRevisionId": None},
        )
        assert conflict.status_code == 409
        assert conflict.json()["error"]["code"] == "draft_model_release_conflict"
        assert conflict.json()["error"]["details"]["draftModelReleaseId"] == other_public_id
        assert client.get(f"/api/v1/object-drafts/{draft['id']}").status_code == 200
        assert client.get(f"/api/v1/objects/domain/{draft['objectId']}").status_code == 404


def test_required_ownership_and_containment_publish_and_retire_atomically():
    token = uuid4().hex[:8]
    with TestClient(app) as client:
        language = _legacy_active(
            client,
            {
                "applicationKey": "rdm-translations",
                "objectTypeKey": "language",
                "name": f"Language {token}",
                "attributes": [_attribute("language-code", f"LG_{token}")],
            },
        )
        group = _legacy_active(
            client,
            {
                "applicationKey": "rdm-translations",
                "objectTypeKey": "translation-group",
                "parentObjectId": language["id"],
                "name": f"Group {token}",
                "attributes": [_attribute("group-code", f"GR_{token}")],
            },
        )
        target = _legacy_active(
            client,
            {
                "applicationKey": "rdm-master",
                "objectTypeKey": "domain",
                "name": f"Target {token}",
                "attributes": [_attribute("domain-code", f"TG_{token}")],
            },
        )
        draft = client.post(
            "/api/v1/object-drafts",
            json={
                "applicationKey": "rdm-translations",
                "objectTypeKey": "translation",
                "name": f"Translation {token}",
                "parentObjectId": group["id"],
                "attributes": [_attribute("translated-value", "Translated")],
                "requiredRelationships": [
                    {
                        "relationTypeKey": "object-has-translation",
                        "direction": "incoming",
                        "otherObjectId": target["id"],
                    }
                ],
            },
        ).json()
        activated = client.post(
            f"/api/v1/object-drafts/{draft['id']}/activation",
            json={"expectedDraftVersion": 1, "expectedActiveRevisionId": None},
        )
        assert activated.status_code == 200, activated.text
        translation = activated.json()
        relations = client.get(
            "/api/v1/relations", params={"objectId": translation["objectId"]}
        ).json()["items"]
        assert {item["relation"]["relationTypeKey"] for item in relations} == {
            "translation-group-contains-translation",
            "object-has-translation",
        }

        preview = client.post(
            f"/api/v1/objects/domain/{target['id']}/retirement",
            json={"expectedActiveRevisionId": target["id"]},
        )
        assert preview.status_code == 409
        assert preview.json()["error"]["code"] == "active_revision_conflict"
        target_history = client.get(
            f"/api/v1/objects/domain/{target['id']}/revisions"
        ).json()
        target_revision_id = target_history["items"][0]["id"]
        impact = client.get(
            f"/api/v1/objects/domain/{target['id']}/retirement-impact",
            params={"expectedActiveRevisionId": target_revision_id},
        )
        assert impact.status_code == 200
        assert impact.json()["cascadeRequired"] is True
        assert [item["id"] for item in impact.json()["dependants"]] == [
            translation["objectId"]
        ]
        malformed_impact = client.get(
            f"/api/v1/objects/domain/{target['id']}/retirement-impact",
            params={"expectedActiveRevisionId": "not-a-revision-id"},
        )
        assert malformed_impact.status_code == 422
        assert malformed_impact.json()["error"]["code"] == "request_validation_error"
        assert client.get(f"/api/v1/objects/domain/{target['id']}").status_code == 200
        blocked = client.post(
            f"/api/v1/objects/domain/{target['id']}/retirement",
            json={"expectedActiveRevisionId": target_revision_id},
        )
        assert blocked.status_code == 409
        assert blocked.json()["error"]["code"] == "object_has_dependants"
        retired = client.post(
            f"/api/v1/objects/domain/{target['id']}/retirement",
            json={"expectedActiveRevisionId": target_revision_id, "cascade": True},
        )
        assert retired.status_code == 200, retired.text
        assert [item["id"] for item in retired.json()["retiredDependants"]] == [
            translation["objectId"]
        ]
        assert client.get(
            f"/api/v1/objects/translation/{translation['objectId']}"
        ).status_code == 404
