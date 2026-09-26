"""Request-boundary regressions found while reviewing the uncommitted WP8 diff."""

import json
from pathlib import Path
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import event, func, select
from wp8_support import create_change_set, create_workspace, publish_change_set, unique_key

from app.config import reload_settings
from app.db import SessionLocal, get_engine
from app.main import create_app
from app.models.database import (
    AttributeValue,
    AuditEvent,
    ChangeSet,
    ChangeSetObject,
    ObjectRelation,
    PublicationObject,
    RdmObject,
)
from app.services.model.registry import model_registry


@pytest.fixture
def review_client(tmp_path, monkeypatch, migrated_database, request):
    model = json.loads((Path(__file__).parents[2] / "model/rdm-starter.json").read_text())
    oriented, required = getattr(request, "param", (True, False))
    model["relationTypes"].append(
        {
            "key": "review-link",
            "reverseKey": "review-backlink",
            "name": "Review link",
            "reverseName": "Review backlink",
            "isOriented": oriented,
        }
    )
    model["objectTypeRelations"].append(
        {
            "relationTypeKey": "review-link",
            "fromObjectTypeKey": "domain",
            "toObjectTypeKey": "language",
            "cardinality": "one-to-many",
            "required": required,
        }
    )
    model["attributeTypes"].append(
        {
            "key": "locked-note",
            "name": "Locked note",
            "valueType": "text",
            "default": "locked",
        }
    )
    next(x for x in model["objectTypes"] if x["key"] == "domain")["attributes"].append(
        {
            "attributeTypeKey": "locked-note",
            "readOnly": True,
        }
    )
    path = tmp_path / "model.json"
    path.write_text(json.dumps(model))
    try:
        with monkeypatch.context() as patch:
            patch.setenv("DATABASE_URL", migrated_database("review.db"))
            patch.setenv("RDM_MODEL_PATH", str(path))
            model_registry.clear()
            with TestClient(create_app()) as client:
                engine = get_engine()

                def foreign_keys(connection, _record, _proxy):
                    connection.execute("PRAGMA foreign_keys=ON")

                event.listen(engine, "checkout", foreign_keys)
                try:
                    yield client
                finally:
                    event.remove(engine, "checkout", foreign_keys)
                    engine.dispose()
    finally:
        model_registry.clear()
        reload_settings()


def _create(client, workspace, kind="domain", *, change_set=None, parent=None, owner=None):
    app = "rdm-translations" if kind == "language" else "rdm-master"
    code = {"domain": "domain-code", "language": "language-code", "codelist": "codelist-code"}[kind]
    payload = {
        "workspaceKey": workspace,
        "applicationKey": app,
        "objectTypeKey": kind,
        "name": unique_key(kind),
        "attributes": [{"attributeTypeKey": code, "value": uuid4().hex}],
    }
    if change_set:
        payload.update(changeSetId=change_set["id"], expectedChangeSetVersion=change_set["version"])
    if parent:
        payload["parentObjectId"] = parent
    if owner:
        payload["initialRelations"] = [
            {
                "relationTypeKey": "review-link",
                "direction": "incoming",
                "otherObjectId": owner,
            }
        ]
    response = client.post("/api/v1/objects", json=payload)
    assert response.status_code == 201, response.text
    if change_set:
        change_set["version"] = response.json()["changeSetVersion"]
    return response.json()


def _audit_count():
    with SessionLocal() as session:
        return session.scalar(select(func.count()).select_from(AuditEvent))


@pytest.mark.parametrize("mode", ["live", "change_set"])
@pytest.mark.parametrize("review_client", [(True, False), (False, True)], indirect=True)
def test_association_delete_requires_confirmation_and_retains_other_endpoint(review_client, mode):
    client = review_client
    workspace = unique_key("review")
    create_workspace(client, workspace)
    change_set = create_change_set(client, workspace).json() if mode == "change_set" else None
    source = _create(client, workspace, change_set=change_set)
    target = _create(client, workspace, "language", change_set=change_set, owner=source["id"])
    context = {"changeSetId": change_set["id"]} if change_set else {"workspaceKey": workspace}
    claim = {"expectedVersion": source["version"]}
    if change_set:
        claim.update(changeSetId=change_set["id"], expectedChangeSetVersion=change_set["version"])
    path = f"/api/v1/objects/domain/{source['id']}"
    events = _audit_count()
    preview = client.delete(path, params=claim)
    assert preview.status_code == 409, preview.text
    error = preview.json()["error"]
    assert error["code"] == "object_has_dependants"
    assert "cascade=true" in error["message"]
    assert error["details"]["objectsToDelete"] == []
    assert error["details"]["relationshipCount"] == 1
    assert client.get(path, params=context).json()["version"] == source["version"]
    assert _audit_count() == events
    if change_set:
        assert (
            client.get(f"/api/v1/change-sets/{change_set['id']}").json()["version"]
            == change_set["version"]
        )
    deleted = client.delete(
        path,
        params={
            **claim,
            "cascade": True,
            "deletionPreviewToken": error["details"]["deletionPreviewToken"],
        },
    )
    assert deleted.status_code == 204, deleted.text
    assert client.get(f"/api/v1/objects/language/{target['id']}", params=context).status_code == 200
    assert (
        client.get("/api/v1/relations", params={**context, "objectId": target["id"]}).json()[
            "items"
        ]
        == []
    )


def test_live_relation_is_addressed_only_by_public_uuid(review_client):
    client = review_client
    source = _create(client, "default")
    target = _create(client, "default", "language", owner=source["id"])
    relation = client.get("/api/v1/relations", params={"objectId": target["id"]}).json()["items"][
        0
    ]["relation"]
    assert client.get(f"/api/v1/relations/{relation['id']}").json() == relation
    assert client.get(f"/api/v1/relations/{uuid4()}").status_code == 404
    with SessionLocal() as session:
        sequence_id = session.scalar(
            select(ObjectRelation.sequence_id).where(ObjectRelation.id == relation["id"])
        )
    assert client.get(f"/api/v1/relations/{sequence_id}").status_code == 404


@pytest.mark.parametrize("cascade", [False, True])
def test_live_containment_delete_respects_foreign_keys(review_client, cascade):
    client = review_client
    parent = _create(client, "default")
    child = _create(client, "default", "codelist", parent=parent["id"])
    victim = parent if cascade else child
    kind = "domain" if cascade else "codelist"
    params = {"expectedVersion": 1, "cascade": cascade}
    if cascade:
        preview = client.delete(
            f"/api/v1/objects/{kind}/{victim['id']}", params={"expectedVersion": 1}
        )
        params["deletionPreviewToken"] = preview.json()["error"]["details"]["deletionPreviewToken"]
    deleted = client.delete(f"/api/v1/objects/{kind}/{victim['id']}", params=params)
    assert deleted.status_code == 204, deleted.text
    with SessionLocal() as session:
        assert (
            session.scalar(
                select(func.count())
                .select_from(AttributeValue)
                .where(AttributeValue.object_id == victim["id"])
            )
            == 0
        )


def test_activation_reparents_survivor_before_deleting_old_parent(review_client):
    client = review_client
    change_set = create_change_set(client, "default").json()
    old_parent = _create(client, "default", change_set=change_set)
    child = _create(client, "default", "codelist", change_set=change_set, parent=old_parent["id"])
    first = publish_change_set(client, change_set["id"], expected_change_set_version=change_set["version"]).json()
    change_set = create_change_set(client, "default", derived_from_publication_id=first["id"]).json()
    new_parent = _create(client, "default", change_set=change_set)
    moved = client.patch(
        f"/api/v1/objects/codelist/{child['id']}",
        json={
            "parentObjectId": new_parent["id"],
            "expectedVersion": child["version"],
            "changeSetId": change_set["id"],
            "expectedChangeSetVersion": change_set["version"],
        },
    )
    assert moved.status_code == 200, moved.text
    change_set["version"] = moved.json()["changeSetVersion"]
    deleted = client.delete(
        f"/api/v1/objects/domain/{old_parent['id']}",
        params={
            "expectedVersion": old_parent["version"],
            "changeSetId": change_set["id"],
            "expectedChangeSetVersion": change_set["version"],
        },
    )
    assert deleted.status_code == 204, deleted.text
    publish_change_set(
        client,
        change_set["id"],
        expected_change_set_version=change_set["version"] + 1,
        expected_active_publication_id=first["id"],
    )
    assert (
        client.get(f"/api/v1/objects/codelist/{child['id']}").json()["parentObjectId"]
        == new_parent["id"]
    )
    with SessionLocal() as session:
        history = session.scalar(
            select(PublicationObject).where(
                PublicationObject.publication_id == first["id"],
                PublicationObject.object_id == child["id"],
            )
        )
        assert history.parent_object_id == old_parent["id"]
        assert (
            session.scalar(
                select(func.count())
                .select_from(AttributeValue)
                .where(AttributeValue.object_id == old_parent["id"])
            )
            == 0
        )


def test_retired_catalogue_rejects_publication_withdrawal(review_client):
    client = review_client
    workspace = unique_key("retired")
    create_workspace(client, workspace)
    change_set = create_change_set(client, workspace).json()
    _create(client, workspace, change_set=change_set)
    publication = publish_change_set(client, change_set["id"], expected_change_set_version=change_set["version"]).json()
    retired = client.patch(
        f"/api/v1/workspaces/{workspace}", json={"status": "retired", "expectedVersion": 1}
    )
    assert retired.status_code == 200, retired.text
    events = _audit_count()
    response = client.post(f"/api/v1/publications/{publication['id']}/withdrawal")
    assert response.status_code == 409, response.text
    assert response.json()["error"]["code"] == "workspace_retired"
    assert client.get(f"/api/v1/publications/{publication['id']}").json()["status"] == "active"
    assert _audit_count() == events


def test_change_set_read_only_attribute_delete_preserves_value_and_versions(review_client):
    client = review_client
    change_set = create_change_set(client, "default").json()
    item = _create(client, "default", change_set=change_set)
    path = f"/api/v1/objects/domain/{item['id']}/attributes/locked-note"
    events = _audit_count()
    response = client.delete(
        path,
        params={
            "changeSetId": change_set["id"],
            "expectedChangeSetVersion": change_set["version"],
            "expectedVersion": 1,
        },
    )
    assert response.status_code == 422, response.text
    assert response.json()["error"]["code"] == "read_only_attributes"
    assert "locked-note" in response.json()["error"]["message"]
    value = client.get(path, params={"changeSetId": change_set["id"]}).json()
    assert value["value"] == "locked" and value["objectVersion"] == 1
    assert (
        client.get(f"/api/v1/change-sets/{change_set['id']}").json()["version"] == change_set["version"]
    )
    assert _audit_count() == events


def test_stale_loaded_change_set_cannot_overwrite_a_committed_rename(review_client):
    from app.errors import ApiError
    from app.services.change_sets import update_change_set

    change_set = create_change_set(review_client, "default").json()
    with SessionLocal() as first, SessionLocal() as second:
        # Keep both ORM instances alive to reproduce concurrent request reads on SQLite.
        loaded_first = first.scalar(select(ChangeSet).where(ChangeSet.id == change_set["id"]))
        loaded_second = second.scalar(
            select(ChangeSet).where(ChangeSet.id == change_set["id"])
        )
        assert loaded_first.version == loaded_second.version == 1
        update_change_set(first, change_set["id"], 1, "winner")
        with pytest.raises(ApiError) as error:
            update_change_set(second, change_set["id"], 1, "lost update")
        assert error.value.code == "change_set_version_conflict"
    current = review_client.get(f"/api/v1/change-sets/{change_set['id']}").json()
    assert current["name"] == "winner" and current["version"] == 2


def test_change_set_requires_parent_on_create_update_and_activation(review_client):
    client = review_client
    change_set = create_change_set(client, "default").json()
    root_payload = {
        "applicationKey": "rdm-master",
        "objectTypeKey": "codelist",
        "name": "Invalid root",
        "attributes": [{"attributeTypeKey": "codelist-code", "value": uuid4().hex}],
        "changeSetId": change_set["id"],
        "expectedChangeSetVersion": change_set["version"],
    }
    invalid = client.post("/api/v1/objects", json=root_payload)
    assert invalid.status_code == 422 and invalid.json()["error"]["code"] == "parent_required"
    parent = _create(client, "default", change_set=change_set)
    child = _create(client, "default", "codelist", change_set=change_set, parent=parent["id"])
    events = _audit_count()
    invalid = client.patch(
        f"/api/v1/objects/codelist/{child['id']}",
        json={
            "parentObjectId": None,
            "expectedVersion": child["version"],
            "changeSetId": change_set["id"],
            "expectedChangeSetVersion": change_set["version"],
        },
    )
    assert invalid.status_code == 422 and invalid.json()["error"]["code"] == "parent_required"
    assert _audit_count() == events
    # An old/imported invalid candidate must also be refused at the publication boundary.
    with SessionLocal() as session:
        row = session.scalar(
            select(ChangeSetObject).where(
                ChangeSetObject.change_set_id == change_set["id"],
                ChangeSetObject.object_id == child["id"],
            )
        )
        row.parent_object_id = None
        session.commit()
    invalid = publish_change_set(
        client, change_set["id"], expected_change_set_version=change_set["version"], expected_status=422
    )
    assert "parent_required" in {item["code"] for item in invalid.json()["error"]["details"]}
    assert (
        client.get(f"/api/v1/change-sets/{change_set['id']}").json()["version"] == change_set["version"]
    )
    assert client.get("/api/v1/workspaces/default/publications").json()["items"] == []


def test_activation_reports_id_collision_in_another_workspace(review_client):
    client = review_client
    change_set = create_change_set(client, "default").json()
    item = _create(client, "default", change_set=change_set)
    workspace = unique_key("other")
    create_workspace(client, workspace)
    live_payload = {
        "id": item["id"],
        "workspaceKey": workspace,
        "applicationKey": "rdm-master",
        "objectTypeKey": "domain",
        "name": "Concurrent live owner",
        "attributes": [{"attributeTypeKey": "domain-code", "value": uuid4().hex}],
    }
    live = client.post("/api/v1/objects", json=live_payload)
    assert live.status_code == 201, live.text
    events = _audit_count()
    conflict = publish_change_set(
        client, change_set["id"], expected_change_set_version=change_set["version"], expected_status=409
    )
    assert conflict.json()["error"]["code"] == "version_conflict"
    assert any(
        entry["id"] == item["id"] and entry["code"] == "id_collision"
        for entry in conflict.json()["error"]["details"]["conflicts"]
    )
    assert _audit_count() == events
    assert (
        client.get(f"/api/v1/change-sets/{change_set['id']}").json()["version"] == change_set["version"]
    )
    fresh = create_change_set(client, "default").json()
    duplicate = client.post(
        "/api/v1/objects",
        json={
            **live_payload,
            "workspaceKey": "default",
            "changeSetId": fresh["id"],
            "expectedChangeSetVersion": fresh["version"],
        },
    )
    assert (
        duplicate.status_code == 409
        and duplicate.json()["error"]["code"] == "object_already_exists"
    )


@pytest.mark.parametrize("mode", ["live", "change_set"])
def test_cascade_confirmation_rejects_hierarchy_changed_after_preview(review_client, mode):
    client = review_client
    workspace = unique_key("preview-lock")
    create_workspace(client, workspace)
    change_set = create_change_set(client, workspace).json() if mode == "change_set" else None
    parent = _create(client, workspace, change_set=change_set)
    first_child = _create(client, workspace, "codelist", change_set=change_set, parent=parent["id"])
    params = {"expectedVersion": parent["version"]}
    if change_set:
        params.update(changeSetId=change_set["id"], expectedChangeSetVersion=change_set["version"])
    path = f"/api/v1/objects/domain/{parent['id']}"
    preview = client.delete(path, params=params)
    assert preview.status_code == 409, preview.text
    token = preview.json()["error"]["details"]["deletionPreviewToken"]
    preview_change_set_version = change_set["version"] if change_set else None

    # Another session adds a descendant without changing the parent's record version.
    second_child = _create(client, workspace, "codelist", change_set=change_set, parent=parent["id"])
    events = _audit_count()
    confirmation = {
        "expectedVersion": parent["version"],
        "cascade": True,
        "deletionPreviewToken": token,
    }
    if change_set:
        confirmation.update(
            changeSetId=change_set["id"],
            expectedChangeSetVersion=preview_change_set_version,
        )
    rejected = client.delete(path, params=confirmation)
    assert rejected.status_code == 409, rejected.text
    assert rejected.json()["error"] == {
        "code": "deletion_preview_changed",
        "message": "The object was modified by another session. Please retry.",
    }
    assert _audit_count() == events
    context = {"changeSetId": change_set["id"]} if change_set else {"workspaceKey": workspace}
    for object_type, item in (
        ("domain", parent),
        ("codelist", first_child),
        ("codelist", second_child),
    ):
        response = client.get(f"/api/v1/objects/{object_type}/{item['id']}", params=context)
        assert response.status_code == 200


def test_cascade_rejects_missing_or_tampered_preview_token(review_client):
    client = review_client
    parent = _create(client, "default")
    _create(client, "default", "codelist", parent=parent["id"])
    path = f"/api/v1/objects/domain/{parent['id']}"
    missing = client.delete(path, params={"expectedVersion": 1, "cascade": True})
    assert missing.status_code == 409
    assert missing.json()["error"]["code"] == "deletion_preview_required"
    tampered = client.delete(
        path,
        params={"expectedVersion": 1, "cascade": True, "deletionPreviewToken": "tampered"},
    )
    assert tampered.status_code == 409
    assert tampered.json()["error"]["code"] == "deletion_preview_changed"
    assert client.get(path).status_code == 200


def test_missing_preview_token_precedes_stale_root_version(review_client):
    client = review_client
    parent = _create(client, "default")
    _create(client, "default", "codelist", parent=parent["id"])
    path = f"/api/v1/objects/domain/{parent['id']}"
    changed = client.patch(path, json={"name": "Changed", "expectedVersion": 1})
    assert changed.status_code == 200

    rejected = client.delete(path, params={"expectedVersion": 1, "cascade": True})

    assert rejected.status_code == 409
    assert rejected.json()["error"]["code"] == "deletion_preview_required"


def test_change_set_delete_honours_object_type_in_route(review_client):
    client = review_client
    workspace = unique_key("change-set-type")
    create_workspace(client, workspace)
    change_set = create_change_set(client, workspace).json()
    item = _create(client, workspace, change_set=change_set)

    rejected = client.delete(
        f"/api/v1/objects/codelist/{item['id']}",
        params={
            "changeSetId": change_set["id"],
            "expectedChangeSetVersion": change_set["version"],
            "expectedVersion": item["version"],
        },
    )

    assert rejected.status_code == 404
    assert rejected.json()["error"]["code"] == "object_not_found"
    assert (
        client.get(
            f"/api/v1/objects/domain/{item['id']}",
            params={"changeSetId": change_set["id"]},
        ).status_code
        == 200
    )


def test_live_delete_refuses_corrupt_cross_workspace_containment(review_client):
    client = review_client
    first_workspace = unique_key("isolated-a")
    second_workspace = unique_key("isolated-b")
    create_workspace(client, first_workspace)
    create_workspace(client, second_workspace)
    parent = _create(client, first_workspace)
    second_parent = _create(client, second_workspace)
    child = _create(client, second_workspace, "codelist", parent=second_parent["id"])
    with SessionLocal() as session:
        stored_child = session.scalar(select(RdmObject).where(RdmObject.id == child["id"]))
        assert stored_child is not None
        stored_child.parent_object_id = parent["id"]
        session.commit()

    events = _audit_count()
    rejected = client.delete(
        f"/api/v1/objects/domain/{parent['id']}", params={"expectedVersion": 1}
    )

    assert rejected.status_code == 409
    assert rejected.json()["error"]["code"] == "workspace_graph_invalid"
    assert _audit_count() == events
    assert (
        client.get(
            f"/api/v1/objects/domain/{parent['id']}",
            params={"workspaceKey": first_workspace},
        ).status_code
        == 200
    )
    assert (
        client.get(
            f"/api/v1/objects/codelist/{child['id']}",
            params={"workspaceKey": second_workspace},
        ).status_code
        == 200
    )


def test_live_delete_refuses_corrupt_cross_workspace_relationship(review_client):
    client = review_client
    first_workspace = unique_key("relation-a")
    second_workspace = unique_key("relation-b")
    create_workspace(client, first_workspace)
    create_workspace(client, second_workspace)
    source = _create(client, first_workspace)
    target = _create(client, second_workspace, "language")
    with SessionLocal() as session:
        session.add(
            ObjectRelation(
                relation_type_key="review-link",
                from_object_id=source["id"],
                to_object_id=target["id"],
                attributes={},
            )
        )
        session.commit()

    events = _audit_count()
    rejected = client.delete(
        f"/api/v1/objects/domain/{source['id']}", params={"expectedVersion": 1}
    )

    assert rejected.status_code == 409
    assert rejected.json()["error"]["code"] == "workspace_graph_invalid"
    assert _audit_count() == events
    assert (
        client.get(
            f"/api/v1/objects/domain/{source['id']}",
            params={"workspaceKey": first_workspace},
        ).status_code
        == 200
    )
    assert (
        client.get(
            f"/api/v1/objects/language/{target['id']}",
            params={"workspaceKey": second_workspace},
        ).status_code
        == 200
    )


def test_cascade_rejects_child_record_change_after_preview(review_client):
    client = review_client
    parent = _create(client, "default")
    child = _create(client, "default", "codelist", parent=parent["id"])
    path = f"/api/v1/objects/domain/{parent['id']}"
    preview = client.delete(path, params={"expectedVersion": 1})
    assert preview.status_code == 409
    token = preview.json()["error"]["details"]["deletionPreviewToken"]
    changed = client.patch(
        f"/api/v1/objects/codelist/{child['id']}",
        json={"name": "Changed child", "expectedVersion": child["version"]},
    )
    assert changed.status_code == 200
    events = _audit_count()

    rejected = client.delete(
        path,
        params={
            "expectedVersion": 1,
            "cascade": True,
            "deletionPreviewToken": token,
        },
    )

    assert rejected.status_code == 409
    assert rejected.json()["error"] == {
        "code": "deletion_preview_changed",
        "message": "The object was modified by another session. Please retry.",
    }
    assert _audit_count() == events
    assert client.get(path).status_code == 200
    assert client.get(f"/api/v1/objects/codelist/{child['id']}").status_code == 200


def test_cascade_maps_root_change_after_preview_to_retry_conflict(review_client):
    client = review_client
    parent = _create(client, "default")
    child = _create(client, "default", "codelist", parent=parent["id"])
    path = f"/api/v1/objects/domain/{parent['id']}"
    preview = client.delete(path, params={"expectedVersion": 1})
    token = preview.json()["error"]["details"]["deletionPreviewToken"]
    changed = client.patch(path, json={"name": "Changed elsewhere", "expectedVersion": 1})
    assert changed.status_code == 200
    events = _audit_count()
    rejected = client.delete(
        path,
        params={
            "expectedVersion": 1,
            "cascade": True,
            "deletionPreviewToken": token,
        },
    )
    assert rejected.status_code == 409
    assert rejected.json()["error"] == {
        "code": "deletion_preview_changed",
        "message": "The object was modified by another session. Please retry.",
    }
    assert _audit_count() == events
    assert client.get(path).status_code == 200
    assert client.get(f"/api/v1/objects/codelist/{child['id']}").status_code == 200
