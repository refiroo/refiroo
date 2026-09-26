"""WP8.1-A request-context and pinned-model integration regressions."""

from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import select
from wp8_support import create_change_set, create_workspace, unique_key

from app.db import SessionLocal
from app.main import app, create_app
from app.models.database import (
    ChangeSet,
    ModelRelease,
    ModelRuntimeState,
    ObjectRelation,
    Publication,
    PublicationObject,
    PublicationRelation,
    RdmObject,
    Workspace,
)
from app.models.schema import EngineModel
from app.services.model.bootstrap import ensure_bootstrap_release
from app.services.model.registry import model_registry


def _candidate_without_language_attribute(client, version: str) -> tuple[EngineModel, str]:
    source = client.get("/api/v1/model").json()
    language = next(item for item in source["objectTypes"] if item["key"] == "language")
    binding = language["attributes"][0]["attributeTypeKey"]
    source["attributeTypes"] = [
        item for item in source["attributeTypes"] if item["key"] != binding
    ]
    language["attributes"] = [
        item for item in language["attributes"] if item["attributeTypeKey"] != binding
    ]

    def scrub(value):
        if isinstance(value, list):
            return [scrub(item) for item in value if item != binding]
        if isinstance(value, dict):
            result = {key: scrub(item) for key, item in value.items()}
            if result.get("displayAttributeTypeKey") == binding:
                result["displayAttributeTypeKey"] = "locale-code"
            return result
        return value

    source = scrub(source)
    source["release"]["version"] = version
    return EngineModel.model_validate(source), binding


def _install_candidate(candidate: EngineModel) -> ModelRelease:
    with SessionLocal() as session:
        release = ensure_bootstrap_release(session, candidate)
        session.commit()
        return release


def _activate_candidate(monkeypatch, candidate: EngineModel):
    release = _install_candidate(candidate)
    monkeypatch.setenv("MODEL_ADMIN_MUTATIONS_ENABLED", "true")
    with TestClient(create_app()) as client:
        with SessionLocal() as session:
            state = session.get(ModelRuntimeState, 1)
            assert state is not None
            active = session.get(ModelRelease, state.active_model_release_id)
            assert active is not None
            expected_version = state.version
            active_id = active.public_id
        response = client.post(
            f"/api/v1/model-releases/{release.public_id}/activation",
            json={
                "expectedRuntimeVersion": expected_version,
                "expectedActiveReleaseId": active_id,
            },
        )
    return response, release, active_id, expected_version


def _restore_active(monkeypatch, release_id: str) -> None:
    monkeypatch.setenv("MODEL_ADMIN_MUTATIONS_ENABLED", "true")
    with TestClient(create_app()) as client:
        with SessionLocal() as session:
            state = session.get(ModelRuntimeState, 1)
            assert state is not None
            current = session.get(ModelRelease, state.active_model_release_id)
            assert current is not None
            if current.public_id == release_id:
                return
            expected_version = state.version
            current_id = current.public_id
        response = client.post(
            f"/api/v1/model-releases/{release_id}/activation",
            json={
                "expectedRuntimeVersion": expected_version,
                "expectedActiveReleaseId": current_id,
            },
        )
        assert response.status_code == 200, response.text


def _language_value(value_type: str):
    return {
        "text": "legacy-language",
        "longText": "legacy-language",
        "integer": 1,
        "decimal": 1,
        "boolean": True,
        "date": "2026-01-01",
        "dateTime": "2026-01-01T00:00:00Z",
    }.get(value_type, "legacy-language")


def test_1_live_only_incompatible_data_blocks_activation_without_publication(monkeypatch):
    with TestClient(app) as client:
        workspace_key = unique_key("live-only")
        create_workspace(client, workspace_key)
        model = client.get("/api/v1/model").json()
        definition = next(
            item for item in model["attributeTypes"] if item["key"] == "language-code"
        )
        created = client.post(
            "/api/v1/objects",
            json={
                "applicationKey": "rdm-translations",
                "objectTypeKey": "language",
                "workspaceKey": workspace_key,
                "name": "Live only",
                "attributes": [
                    {"attributeTypeKey": "language-code", "value": _language_value(definition["valueType"])}
                ],
            },
        )
        assert created.status_code == 201, created.text
        candidate, _binding = _candidate_without_language_attribute(client, f"0.6.0-live-{uuid4().hex}")
    response, _release, active_id, expected_version = _activate_candidate(monkeypatch, candidate)
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "model_migration_required"
    with SessionLocal() as session:
        state = session.get(ModelRuntimeState, 1)
        assert state is not None
        assert state.version == expected_version
        live = session.scalar(select(RdmObject).where(RdmObject.id == created.json()["id"]))
        assert live is not None
        session.delete(live)
        session.commit()
        active = session.get(ModelRelease, state.active_model_release_id)
        assert active is not None and active.public_id == active_id


def test_2_catalogue_retired_live_data_still_blocks_incompatible_activation(monkeypatch):
    with TestClient(app) as client:
        workspace_key = unique_key("retired-live")
        create_workspace(client, workspace_key)
        created = client.post(
            "/api/v1/objects",
            json={
                "applicationKey": "rdm-translations",
                "objectTypeKey": "language",
                "workspaceKey": workspace_key,
                "name": "Retired live",
                "attributes": [{"attributeTypeKey": "language-code", "value": "retired"}],
            },
        )
        assert created.status_code == 201, created.text
        with SessionLocal() as session:
            workspace = session.scalar(select(Workspace).where(Workspace.key == workspace_key))
            assert workspace is not None
            workspace.status = "retired"
            session.commit()
        candidate, _binding = _candidate_without_language_attribute(client, f"0.6.0-retired-{uuid4().hex}")
    response, _release, _active_id, expected_version = _activate_candidate(monkeypatch, candidate)
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "model_migration_required"
    with SessionLocal() as session:
        state = session.get(ModelRuntimeState, 1)
        assert state is not None and state.version == expected_version
        live = session.scalar(select(RdmObject).where(RdmObject.id == created.json()["id"]))
        assert live is not None
        session.delete(live)
        session.commit()


def test_3_compatible_candidate_activation_succeeds(monkeypatch):
    with TestClient(app) as client:
        source = client.get("/api/v1/model").json()
        source["release"]["version"] = f"0.6.0-compatible-{uuid4().hex}"
        candidate = EngineModel.model_validate(source)
    response, release, active_id, expected_version = _activate_candidate(monkeypatch, candidate)
    try:
        assert response.status_code == 200, response.text
        assert response.json()["activeReleaseId"] == release.public_id
        with SessionLocal() as session:
            state = session.get(ModelRuntimeState, 1)
            assert state is not None and state.version == expected_version + 1
    finally:
        _restore_active(monkeypatch, active_id)


def test_4_pinned_history_survives_active_model_switch_with_old_field_and_relation(monkeypatch):
    with TestClient(app) as client:
        workspace_key = unique_key("pinned-history")
        create_workspace(client, workspace_key)
        source = client.get("/api/v1/model").json()
        active_release_id = client.get("/api/v1/model").headers["X-Model-Release-Id"]
        historical_attribute_key = "history-only-label"
        historical_relation_key = "history-only-relation"
        source["release"]["version"] = f"0.6.0-history-old-{uuid4().hex}"
        source["attributeTypes"].append(
            {
                "key": historical_attribute_key,
                "name": "Historical only label",
                "valueType": "text",
                "features": {"filterable": True},
            }
        )
        language = next(item for item in source["objectTypes"] if item["key"] == "language")
        language["attributes"].append({"attributeTypeKey": historical_attribute_key, "order": 99})
        source["relationTypes"].append(
            {
                "key": historical_relation_key,
                "reverseKey": "history-only-relation-reverse",
                "name": "Historical only relation",
                "reverseName": "Historical only relation reverse",
            }
        )
        source["objectTypeRelations"].append(
            {
                "relationTypeKey": historical_relation_key,
                "fromObjectTypeKey": "language",
                "toObjectTypeKey": "translation-group",
                "cardinality": "many-to-many",
            }
        )
        old_model = EngineModel.model_validate(source)
        old_attr = {"name": "Historical only label", "valueType": "text"}
    old_response, old_release, original_active_id, _version = _activate_candidate(monkeypatch, old_model)
    assert old_response.status_code == 200, old_response.text
    assert old_release.public_id != active_release_id
    with TestClient(app) as client:
        active_model = client.get("/api/v1/model").json()
        old_release_id = client.get("/api/v1/model").headers["X-Model-Release-Id"]
        with SessionLocal() as session:
            release = session.scalar(select(ModelRelease).where(ModelRelease.public_id == old_release_id))
            assert release is not None
            publication = Publication(
                workspace_key=workspace_key,
                model_release_id=release.id,
                publication_number=1,
                status="withdrawn",
            )
            session.add(publication)
            session.flush()
            language_id, group_id = str(uuid4()), str(uuid4())
            session.add_all(
                [
                    PublicationObject(
                        publication_id=publication.id,
                        object_id=language_id,
                        application_key="rdm-translations",
                        object_type_key="language",
                        name="Pinned language",
                        attributes={historical_attribute_key: "legacy"},
                    ),
                    PublicationObject(
                        publication_id=publication.id,
                        object_id=group_id,
                        application_key="rdm-translations",
                        object_type_key="translation-group",
                        name="Pinned group",
                        attributes={},
                        parent_object_id=language_id,
                    ),
                    PublicationRelation(
                        publication_id=publication.id,
                        relation_id=str(uuid4()),
                        relation_type_key=historical_relation_key,
                        from_object_id=language_id,
                        to_object_id=group_id,
                        attributes={},
                    ),
                ]
            )
            session.commit()
            publication_id = publication.id
        candidate_source = active_model
        candidate_source["release"]["version"] = f"0.6.0-history-new-{uuid4().hex}"
        candidate_source["attributeTypes"] = [
            item for item in candidate_source["attributeTypes"] if item["key"] != historical_attribute_key
        ]
        language = next(item for item in candidate_source["objectTypes"] if item["key"] == "language")
        language["attributes"] = [
            item for item in language["attributes"]
            if item["attributeTypeKey"] != historical_attribute_key
        ]
        candidate_source["relationTypes"] = [
            item for item in candidate_source["relationTypes"] if item["key"] != historical_relation_key
        ]
        candidate_source["objectTypeRelations"] = [
            item for item in candidate_source["objectTypeRelations"]
            if item["relationTypeKey"] != historical_relation_key
        ]
        candidate = EngineModel.model_validate(candidate_source)
    try:
        response, _release, _active_id, _expected_version = _activate_candidate(monkeypatch, candidate)
        assert response.status_code == 200, response.text
        with TestClient(app) as client:
            assert historical_attribute_key not in {item["key"] for item in client.get("/api/v1/model").json()["attributeTypes"]}
            assert historical_relation_key not in {item["key"] for item in client.get("/api/v1/model").json()["relationTypes"]}
        with TestClient(app) as client:
            objects = client.get(
            "/api/v1/objects/language",
            params={
                "publicationId": publication_id,
                f"filter.{historical_attribute_key}.eq": "legacy",
            },
            )
            assert objects.status_code == 200, objects.text
            assert objects.json()["items"][0]["id"] == language_id
            value = client.get(
            f"/api/v1/objects/language/{language_id}/attributes/{historical_attribute_key}",
            params={"publicationId": publication_id},
            )
            assert value.status_code == 200, value.text
            assert value.json()["value"] == "legacy"
            assert value.json()["name"] == old_attr["name"]
            assert value.json()["valueType"] == old_attr["valueType"]
            relations = client.get(
            "/api/v1/relations",
            params={
                "objectId": language_id,
                "publicationId": publication_id,
                "relationTypeKey": historical_relation_key,
            },
            )
            assert relations.status_code == 200, relations.text
            assert relations.json()["items"][0]["object"]["id"] == group_id
    finally:
        _restore_active(monkeypatch, original_active_id)


def test_0_explicit_workspace_key_mismatch_is_rejected_for_all_pinned_read_paths():
    with TestClient(app) as client:
        workspace_key = unique_key("pinned-context")
        other_workspace = unique_key("other-context")
        create_workspace(client, workspace_key)
        create_workspace(client, other_workspace)
        change_set = create_change_set(client, workspace_key, name="context").json()

        object_id = str(uuid4())
        attribute_url = f"/api/v1/objects/language/{object_id}/attributes/language-code"
        for url, params in (
            (
                f"/api/v1/objects/language/{object_id}",
                {"changeSetId": change_set["id"], "workspaceKey": other_workspace},
            ),
            (attribute_url, {"changeSetId": change_set["id"], "workspaceKey": other_workspace}),
            (
                "/api/v1/relations",
                {
                    "objectId": object_id,
                    "changeSetId": change_set["id"],
                    "workspaceKey": other_workspace,
                },
            ),
        ):
            response = client.get(url, params=params)
            assert response.status_code == 422, response.text
            assert response.json()["error"]["code"] == "workspace_context_mismatch"

        with SessionLocal() as session:
            relation_id = "missing"
            active_release_id = client.get("/api/v1/model").headers["X-Model-Release-Id"]
            release = session.scalar(
                select(ModelRelease).where(ModelRelease.public_id == active_release_id)
            )
            assert release is not None
            publication = Publication(
                workspace_key=workspace_key,
                model_release_id=release.id,
                publication_number=1,
                status="withdrawn",
            )
            session.add(publication)
            session.flush()
            publication_id = publication.id
            session.commit()
        change_set_version = change_set["version"]
        response = client.post(
            "/api/v1/objects",
            json={
                "applicationKey": "rdm-translations",
                "objectTypeKey": "language",
                "name": "wrong workspace",
                "workspaceKey": other_workspace,
                "changeSetId": change_set["id"],
                "expectedChangeSetVersion": change_set_version,
            },
        )
        assert response.status_code == 422
        assert response.json()["error"]["code"] == "workspace_context_mismatch"
        for url, params in (
            (
                "/api/v1/objects/language",
                {"publicationId": publication_id, "workspaceKey": other_workspace},
            ),
            (
                "/api/v1/objects/language/missing",
                {"publicationId": publication_id, "workspaceKey": other_workspace},
            ),
            (
                "/api/v1/objects/language/missing/attributes/language-code",
                {"publicationId": publication_id, "workspaceKey": other_workspace},
            ),
            (
                "/api/v1/relations",
                {
                    "objectId": "missing",
                    "publicationId": publication_id,
                    "workspaceKey": other_workspace,
                },
            ),
            (
                "/api/v1/relations/missing",
                {"publicationId": publication_id, "workspaceKey": other_workspace},
            ),
        ):
            mismatch = client.get(url, params=params)
            assert mismatch.status_code == 422, mismatch.text
            assert mismatch.json()["error"]["code"] == "workspace_context_mismatch"
        with SessionLocal() as session:
            current = session.scalar(
                select(ChangeSet).where(ChangeSet.id == change_set["id"])
            )
            assert current is not None and current.version == change_set_version
        # Relation detail uses the same context resolver even when the relation is not found.
        response = client.get(
            f"/api/v1/relations/{relation_id}",
            params={"changeSetId": change_set["id"], "workspaceKey": other_workspace},
        )
        assert response.status_code == 422
        assert response.json()["error"]["code"] == "workspace_context_mismatch"


def test_0_unsupported_pinned_change_set_model_is_explicit_and_never_uses_active_model():
    with TestClient(app) as client:
        workspace_key = unique_key("unsupported-pin")
        create_workspace(client, workspace_key)
        change_set = create_change_set(client, workspace_key, name="unsupported").json()

        with SessionLocal() as session:
            item = session.scalar(select(ChangeSet).where(ChangeSet.id == change_set["id"]))
            assert item is not None
            release = session.get(ModelRelease, item.model_release_id)
            assert release is not None
            unsupported = ModelRelease(
                release_key=f"unsupported-{uuid4().hex}",
                release_name=release.release_name,
                release_version="0.4",
                schema_version="0.4",
                model_hash=uuid4().hex + uuid4().hex,
                model_json=release.model_json,
                is_active=False,
            )
            session.add(unsupported)
            session.flush()
            item.model_release_id = unsupported.id
            publication = Publication(
                workspace_key=item.workspace_key,
                model_release_id=unsupported.id,
                publication_number=1,
                status="withdrawn",
            )
            session.add(publication)
            session.flush()
            publication_id = publication.id
            session.commit()

        response = client.get(
            "/api/v1/objects/language",
            params={"changeSetId": change_set["id"]},
        )
        assert response.status_code == 409
        body = response.json()
        assert body["error"] == {
            "code": "unsupported_pinned_model_schema",
            "message": "The model pinned by this context uses an unsupported schema",
            "details": {
                "modelReleaseId": body["error"]["details"]["modelReleaseId"],
                "schemaVersion": "0.4",
                "supportedSchemaVersions": ["0.5", "0.6", "0.7"],
            },
        }
        historical = client.get(
            "/api/v1/objects/language",
            params={"publicationId": publication_id},
        )
        assert historical.status_code == 409
        assert historical.json()["error"]["code"] == "unsupported_pinned_model_schema"


def test_pinned_model_unavailable_and_invalid_are_structured_without_fallback():
    with TestClient(app) as client:
        workspace_key = unique_key("bad-pin")
        create_workspace(client, workspace_key)
        active_id = client.get("/api/v1/model").headers["X-Model-Release-Id"]
        with SessionLocal() as session:
            active = session.scalar(select(ModelRelease).where(ModelRelease.public_id == active_id))
            assert active is not None
            unavailable = Publication(
                workspace_key=workspace_key,
                model_release_id=active.id,
                publication_number=1,
                status="withdrawn",
            )
            session.add(unavailable)
            session.flush()
            unavailable.model_release_id = 999999999
            invalid_release = ModelRelease(
                release_key=f"invalid-pin-{uuid4().hex}",
                release_name="Invalid pinned model",
                release_version="1",
                schema_version="0.5",
                model_hash=uuid4().hex + uuid4().hex,
                model_json={"schemaVersion": "0.5", "invalid": True},
                is_active=False,
            )
            session.add(invalid_release)
            session.flush()
            invalid = Publication(
                workspace_key=workspace_key,
                model_release_id=invalid_release.id,
                publication_number=2,
                status="withdrawn",
            )
            session.add(invalid)
            session.flush()
            session.commit()
            unavailable_id, invalid_id = unavailable.id, invalid.id
        missing = client.get("/api/v1/objects/language", params={"publicationId": unavailable_id})
        assert missing.status_code == 409
        assert missing.json()["error"]["code"] == "pinned_model_unavailable"
        corrupt = client.get("/api/v1/objects/language", params={"publicationId": invalid_id})
        assert corrupt.status_code == 409
        assert corrupt.json()["error"]["code"] == "pinned_model_invalid"
        assert client.get("/api/v1/model").headers["X-Model-Release-Id"] == active_id


def test_pinned_resolution_reports_registry_unavailable_as_structured_http_error():
    with TestClient(app) as client:
        workspace_key = unique_key("unhealthy-pin")
        create_workspace(client, workspace_key)
        active_id = client.get("/api/v1/model").headers["X-Model-Release-Id"]
        with SessionLocal() as session:
            active = session.scalar(select(ModelRelease).where(ModelRelease.public_id == active_id))
            assert active is not None
            publication = Publication(
                workspace_key=workspace_key,
                model_release_id=active.id,
                publication_number=1,
                status="withdrawn",
            )
            session.add(publication)
            session.flush()
            publication_id = publication.id
            session.commit()
        model_registry.mark_unhealthy()
        try:
            response = client.get(
                "/api/v1/objects/language", params={"publicationId": publication_id}
            )
            assert response.status_code == 503
            assert response.json()["error"]["code"] == "model_registry_unavailable"
        finally:
            model_registry.clear()


def test_change_set_write_uses_pinned_model_when_active_registry_is_unhealthy():
    with TestClient(app) as client:
        workspace_key = unique_key("change-set-unhealthy")
        create_workspace(client, workspace_key)
        change_set = create_change_set(client, workspace_key, name="change-set-unhealthy").json()
        model_registry.mark_unhealthy()
        try:
            response = client.post(
                "/api/v1/objects",
                json={
                    "applicationKey": "rdm-translations",
                    "objectTypeKey": "language",
                    "name": "Pinned change set write",
                    "attributes": [{"attributeTypeKey": "language-code", "value": "change_set"}],
                    "changeSetId": change_set["id"],
                    "expectedChangeSetVersion": change_set["version"],
                },
            )
            assert response.status_code == 201, response.text
            assert response.json()["changeSetVersion"] == change_set["version"] + 1
        finally:
            model_registry.clear()


def test_live_relation_detail_honors_explicit_workspace_key():
    with TestClient(app) as client:
        workspace_key = unique_key("relation-scope")
        other_workspace = unique_key("relation-other")
        create_workspace(client, workspace_key)
        create_workspace(client, other_workspace)
        with SessionLocal() as session:
            first_id, second_id = str(uuid4()), str(uuid4())
            session.add_all(
                [
                    RdmObject(
                        id=first_id,
                        workspace_key=workspace_key,
                        application_key="rdm-master",
                        object_type_key="domain",
                        name="Relation source",
                    ),
                    RdmObject(
                        id=second_id,
                        workspace_key=workspace_key,
                        application_key="rdm-master",
                        object_type_key="codelist",
                        name="Relation target",
                    ),
                ]
            )
            relation = ObjectRelation(
                relation_type_key="domain-contains-codelist",
                from_object_id=first_id,
                to_object_id=second_id,
            )
            self_id = str(uuid4())
            session.add(
                RdmObject(
                    id=self_id,
                    workspace_key=workspace_key,
                    application_key="rdm-master",
                    object_type_key="master-value",
                    name="Self relation target",
                )
            )
            self_relation = ObjectRelation(
                relation_type_key="master-value-has-child",
                from_object_id=self_id,
                to_object_id=self_id,
            )
            session.add_all([relation, self_relation])
            session.commit()
            relation_id, self_relation_id = relation.id, self_relation.id
        wrong = client.get(
            f"/api/v1/relations/{relation_id}",
            params={"workspaceKey": other_workspace},
        )
        assert wrong.status_code == 404
        assert wrong.json()["error"]["code"] == "relation_not_found"
        correct = client.get(
            f"/api/v1/relations/{relation_id}",
            params={"workspaceKey": workspace_key},
        )
        assert correct.status_code == 200, correct.text
        self_response = client.get(
            f"/api/v1/relations/{self_relation_id}",
            params={"workspaceKey": workspace_key},
        )
        assert self_response.status_code == 200, self_response.text
