from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from uuid import uuid4

import pytest
import seeds
from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlalchemy import func, select
from workspace_model_support import DEFAULT_ACTIVATION, default_model

from app.db import SessionLocal
from app.engine.model.bootstrap import ensure_bootstrap_release
from app.engine.model.diagnostics import ModelValidationError
from app.engine.model.loader import load_bootstrap_model
from app.engine.model.registry import ModelRegistry, model_registry
from app.engine.model.releases import install_model_release
from app.engine.model.workspace_models import workspaces_running
from app.main import app, create_app
from app.models.database import (
    ApplicationMeta,
    AuditEvent,
    Base,
    ModelDraft,
    ModelRelease,
    Publication,
    PublicationObject,
    RdmObject,
    Workspace,
)
from app.models.schema import EngineModel


def _model(version: str, *, product_name: str | None = None) -> EngineModel:
    source = load_bootstrap_model().model_dump(mode="json")
    source["release"]["version"] = version
    if product_name is not None:
        source["product"]["name"] = product_name
    return EngineModel.model_validate(source)


def _session():
    return seeds.schema_session()


def test_release_installation_rejects_a_shape_only_model_with_invalid_references():
    source = load_bootstrap_model().model_dump(mode="json")
    source["objectTypes"][0]["attributes"][0]["attributeTypeKey"] = "missing-attribute"
    shape_only_model = EngineModel.model_validate(source)

    with _session() as session, pytest.raises(ModelValidationError):
        install_model_release(session, shape_only_model)


def test_first_bootstrap_initializes_runtime_state_and_restart_is_idempotent():
    with _session() as session:
        first = ensure_bootstrap_release(session, _model("0.4.0"))
        session.commit()
        first_public_id = first.public_id

        restarted = ensure_bootstrap_release(session, _model("0.4.0"))
        session.commit()

        state = default_model(session)
        assert state is not None
        assert restarted.public_id == first_public_id
        assert state.model_release_id == first.id
        assert session.scalar(select(func.count()).select_from(ModelRelease)) == 1


def test_different_bootstrap_release_installs_inactive_and_preserves_runtime_selection():
    with _session() as session:
        first = ensure_bootstrap_release(session, _model("0.4.0"))
        session.commit()
        second = ensure_bootstrap_release(session, _model("0.5.0"))
        session.commit()

        state = default_model(session)
        assert state is not None
        assert state.model_release_id == first.id
        assert workspaces_running(session, second.id) == []
        assert session.scalar(select(func.count()).select_from(ModelRelease)) == 2


def test_bootstrap_rejects_same_release_identity_with_different_content():
    with _session() as session:
        ensure_bootstrap_release(session, _model("0.4.0"))
        session.commit()

        try:
            ensure_bootstrap_release(
                session,
                _model("0.4.0", product_name="Conflicting product content"),
            )
        except RuntimeError as exc:
            assert "Bootstrap model release identity conflict" in str(exc)
        else:
            raise AssertionError("Conflicting release identity must be rejected")


def test_resolved_request_snapshots_keep_model_and_metadata_from_one_release():
    registry = ModelRegistry()
    with _session() as session:
        first = ensure_bootstrap_release(session, _model("0.4.0"))
        second = ensure_bootstrap_release(session, _model("0.5.0", product_name="Second model"))
        session.commit()

        first_snapshot = registry.resolve_workspace(session, None)
        assert registry.resolve_workspace(session, None).model is first_snapshot.model
        state = default_model(session)
        assert state is not None
        state.model_release_id = second.id
        session.commit()
        second_snapshot = registry.resolve_workspace(session, None)

        assert first_snapshot.release_db_id == first.id
        assert first_snapshot.model.release.version == "0.4.0"
        assert second_snapshot.release_db_id == second.id
        assert second_snapshot.model.release.version == "0.5.0"
        for snapshot in (first_snapshot, second_snapshot):
            metadata_names = dict(
                session.execute(
                    select(ApplicationMeta.key, ApplicationMeta.name).where(
                        ApplicationMeta.model_release_id == snapshot.release_db_id
                    )
                ).all()
            )
            assert metadata_names == {
                application.key: application.name for application in snapshot.model.applications
            }


def test_resolved_model_snapshot_graph_is_immutable():
    registry = ModelRegistry()
    with _session() as session:
        ensure_bootstrap_release(session, _model("0.4.0"))
        session.commit()
        snapshot = registry.resolve_workspace(session, None)

        with pytest.raises(ValidationError):
            snapshot.model.product.name = "Mutated product"
        with pytest.raises(TypeError, match="Model definitions are immutable"):
            snapshot.model.objectTypes[0].features["mutated"] = True
        with pytest.raises(AttributeError):
            snapshot.model.applications.append(snapshot.model.applications[0])
        with pytest.raises(TypeError, match="Model definitions are immutable"):
            snapshot.model._object_types_by_key.clear()

        resolved_again = registry.resolve_workspace(session, None)
        assert resolved_again.model is snapshot.model
        assert resolved_again.model.product.name == "RDM Engine"


def test_active_model_headers_and_release_read_apis_are_coherent():
    with TestClient(app) as client:
        model_response = client.get("/api/v1/model")
        assert model_response.status_code == 200
        release_id = model_response.headers["X-Model-Release-Id"]
        etag = model_response.headers["ETag"]
        assert etag.startswith('"') and etag.endswith('"')
        model_hash = etag[1:-1]

        active_page = client.get("/api/v1/model-releases", params={"assigned": True})
        assert active_page.status_code == 200
        assert active_page.json()["nextCursor"] is None
        assert len(active_page.json()["items"]) == 1
        summary = active_page.json()["items"][0]
        assert summary["id"] == release_id
        assert summary["modelHash"] == model_hash
        assert summary["assigned"] is True
        assert "model" not in summary
        installed_at = datetime.fromisoformat(summary["installedAt"])
        assert installed_at.utcoffset() == UTC.utcoffset(installed_at)

        detail = client.get(f"/api/v1/model-releases/{release_id}")
        assert detail.status_code == 200
        assert "model" not in detail.json()

        detail_with_model = client.get(
            f"/api/v1/model-releases/{release_id}", params={"includeModel": True}
        )
        assert detail_with_model.status_code == 200
        assert detail_with_model.json()["model"] == model_response.json()

        by_key = client.get("/api/v1/model-releases", params={"releaseKey": summary["key"]})
        assert by_key.status_code == 200
        assert any(item["id"] == release_id for item in by_key.json()["items"])


def test_release_cursor_rejects_tampering_and_filter_reuse():
    with SessionLocal() as session:
        ensure_bootstrap_release(session, _model("0.5.1-test-cursor"))
        session.commit()

    with TestClient(app) as client:
        first_page = client.get("/api/v1/model-releases", params={"pageSize": 1})
        assert first_page.status_code == 200
        cursor = first_page.json()["nextCursor"]
        assert cursor is not None

        filtered = client.get(
            "/api/v1/model-releases",
            params={"assigned": True, "cursor": cursor, "pageSize": 1},
        )
        assert filtered.status_code == 422
        assert filtered.json()["error"]["code"] == "INVALID_CURSOR"

        replacement = "A" if cursor[-1] != "A" else "B"
        tampered = client.get(
            "/api/v1/model-releases",
            params={"cursor": cursor[:-1] + replacement, "pageSize": 1},
        )
        assert tampered.status_code == 422
        assert tampered.json()["error"]["code"] == "INVALID_CURSOR"


def test_unknown_model_release_is_explicit():
    with TestClient(app) as client:
        response = client.get("/api/v1/model-releases/00000000-0000-4000-8000-000000000000")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "MODEL_RELEASE_NOT_FOUND"


def test_inline_validation_is_side_effect_free_and_returns_stable_diagnostics():
    with TestClient(app) as client:
        with SessionLocal() as session:
            before_counts = {
                table.name: session.scalar(select(func.count()).select_from(table))
                for table in Base.metadata.sorted_tables
            }

        valid_model = client.get("/api/v1/model").json()
        valid = client.post("/api/v1/model-validations", json={"model": valid_model})
        assert valid.status_code == 200
        assert valid.json() == {"valid": True, "diagnostics": []}

        valid_model["applications"][0]["objectTypeKeys"].append("missing")
        invalid = client.post("/api/v1/model-validations", json={"model": valid_model})
        assert invalid.status_code == 200
        assert invalid.json()["valid"] is False
        assert invalid.json()["diagnostics"][0]["code"] == "UNKNOWN_OBJECT_TYPE"
        assert invalid.json()["diagnostics"][0]["path"].startswith("/applications/")

        with SessionLocal() as session:
            after_counts = {
                table.name: session.scalar(select(func.count()).select_from(table))
                for table in Base.metadata.sorted_tables
            }
        assert after_counts == before_counts


def test_installed_release_diff_is_key_based_and_assesses_active_runtime_data():
    candidate_source = load_bootstrap_model().model_dump(mode="json")
    candidate_source["release"]["version"] = "0.4.0-wp2-diff"
    candidate_source["applications"][0]["views"][0]["name"] = "Renamed domains"
    candidate_source["attributeTypes"].reverse()
    candidate = EngineModel.model_validate(candidate_source)
    with SessionLocal() as session:
        candidate_release = ensure_bootstrap_release(session, candidate)
        session.commit()

    with TestClient(app) as client:
        active_release_id = client.get("/api/v1/model").headers["X-Model-Release-Id"]
        response = client.get(
            f"/api/v1/model-releases/{candidate_release.public_id}/diff",
            params={"againstReleaseId": active_release_id},
        )

    assert response.status_code == 200
    body = response.json()
    assert body["releaseId"] == candidate_release.public_id
    assert body["againstReleaseId"] == active_release_id
    workspaces = body["compatibility"].pop("workspaces")
    assert body["compatibility"] == {
        "classification": "compatible",
        "activeReleaseId": active_release_id,
        "diagnostics": [],
    }
    # 0.11 M3 (D25): each workspace running the model, every one compatible.
    assert workspaces and all(
        (item["classification"], item["diagnostics"]) == ("compatible", []) for item in workspaces
    )
    paths = {item["path"] for item in body["changes"]}
    assert "/applications/rdm-master/views/domains/name" in paths
    assert "/release/version" in paths
    assert not any(path.startswith("/attributeTypes/") for path in paths)


def test_release_diff_preserves_json_null_before_and_after_values():
    candidate_source = load_bootstrap_model().model_dump(mode="json")
    candidate_source["release"]["version"] = "0.4.0-wp2-null-diff"
    candidate_source["product"]["description"] = None
    candidate = EngineModel.model_validate(candidate_source)
    with SessionLocal() as session:
        candidate_release = ensure_bootstrap_release(session, candidate)
        session.commit()

    with TestClient(app) as client:
        active_release_id = client.get("/api/v1/model").headers["X-Model-Release-Id"]
        response = client.get(
            f"/api/v1/model-releases/{candidate_release.public_id}/diff",
            params={"againstReleaseId": active_release_id},
        )

    assert response.status_code == 200
    description_change = next(
        item for item in response.json()["changes"] if item["path"] == "/product/description"
    )
    assert description_change["kind"] == "changed"
    assert description_change["after"] is None
    assert "before" in description_change


def test_release_diff_reports_unknown_baseline_release():
    with TestClient(app) as client:
        release_id = client.get("/api/v1/model").headers["X-Model-Release-Id"]
        response = client.get(
            f"/api/v1/model-releases/{release_id}/diff",
            params={"againstReleaseId": "00000000-0000-4000-8000-000000000000"},
        )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "MODEL_RELEASE_NOT_FOUND"


def test_model_admin_capabilities_and_routes_are_disabled_by_default():
    with TestClient(app) as client:
        capabilities = client.get("/api/v1/capabilities")
        drafts = client.get("/api/v1/model-drafts")

    # The administration capabilities; integrationJobs (0.9 B1) is J12.7's subject.
    body = capabilities.json()
    assert {key: body[key] for key in ("modelAdmin", "workspaceAdmin")} == {
        "modelAdmin": {
            "readReleases": True,
            "manageDrafts": False,
            "install": False,
            "activate": False,
            "setting": "MODEL_ADMIN_MUTATIONS_ENABLED",
        },
        "workspaceAdmin": {
            "manageWorkspaces": True,
            "setting": "WORKSPACE_ADMIN_MUTATIONS_ENABLED",
        },
    }
    assert drafts.status_code == 404
    assert "/api/v1/model-drafts" not in app.openapi()["paths"]


def test_draft_crud_compile_and_installation_lifecycle(monkeypatch):
    monkeypatch.setenv("MODEL_ADMIN_MUTATIONS_ENABLED", "true")
    enabled_app = create_app()

    with TestClient(enabled_app) as client:
        capabilities = client.get("/api/v1/capabilities").json()["modelAdmin"]
        assert capabilities == {
            "readReleases": True,
            "manageDrafts": True,
            "install": True,
            "activate": True,
            "setting": "MODEL_ADMIN_MUTATIONS_ENABLED",
        }
        active = client.get("/api/v1/model")
        active_release_id = active.headers["X-Model-Release-Id"]
        runtime_state = client.get("/api/v1/workspaces/default/model")
        assert runtime_state.status_code == 200
        assert runtime_state.json()["releaseId"] == active_release_id
        assert runtime_state.json()["version"] >= 1
        candidate = active.json()
        candidate["release"]["version"] = "0.4.0-wp3-install"
        candidate["product"]["name"] = "Installed from a persisted draft"
        candidate["product"]["description"] = None

        created = client.post(
            "/api/v1/model-drafts",
            json={
                "name": "WP3 candidate",
                "baseReleaseId": active_release_id,
                "model": candidate,
            },
        )
        assert created.status_code == 201
        draft = created.json()
        assert draft["version"] == 1
        assert draft["baseReleaseId"] == active_release_id
        assert draft["model"] == candidate

        listed = client.get("/api/v1/model-drafts", params={"pageSize": 1})
        assert listed.status_code == 200
        assert listed.json()["items"][0]["id"] == draft["id"]
        detail = client.get(f"/api/v1/model-drafts/{draft['id']}")
        assert detail.json() == draft

        updated = client.patch(
            f"/api/v1/model-drafts/{draft['id']}",
            json={"expectedVersion": 1, "name": "Ready to install"},
        )
        assert updated.status_code == 200
        assert updated.json()["version"] == 2
        stale = client.patch(
            f"/api/v1/model-drafts/{draft['id']}",
            json={"expectedVersion": 1, "name": "Stale overwrite"},
        )
        assert stale.status_code == 409
        assert stale.json()["error"]["code"] == "VERSION_CONFLICT"

        with SessionLocal() as session:
            counts_before_compile = {
                table.name: session.scalar(select(func.count()).select_from(table))
                for table in Base.metadata.sorted_tables
            }
        compiled = client.post(
            f"/api/v1/model-drafts/{draft['id']}/compile",
            json={"expectedVersion": 2},
        )
        assert compiled.status_code == 200
        assert compiled.json()["valid"] is True
        assert compiled.json()["model"] == candidate
        assert compiled.json()["againstReleaseId"] == active_release_id
        assert any(change["path"] == "/product/name" for change in compiled.json()["changes"])
        null_change = next(
            change
            for change in compiled.json()["changes"]
            if change["path"] == "/product/description"
        )
        assert "after" in null_change
        assert null_change["after"] is None
        assert compiled.json()["compatibility"]["classification"] == "compatible"
        with SessionLocal() as session:
            counts_after_compile = {
                table.name: session.scalar(select(func.count()).select_from(table))
                for table in Base.metadata.sorted_tables
            }
        assert counts_after_compile == counts_before_compile

        installed = client.post(
            f"/api/v1/model-drafts/{draft['id']}/installation",
            json={"expectedVersion": 2},
        )
        assert installed.status_code == 201
        release = installed.json()
        assert release["assigned"] is False
        assert "model" not in release
        assert client.get("/api/v1/model").headers["X-Model-Release-Id"] == active_release_id

        installed_again = client.post(
            f"/api/v1/model-drafts/{draft['id']}/installation",
            json={"expectedVersion": 2},
        )
        assert installed_again.status_code == 200
        assert installed_again.json()["id"] == release["id"]

        stale_delete = client.delete(
            f"/api/v1/model-drafts/{draft['id']}",
            params={"expectedVersion": 1},
        )
        assert stale_delete.status_code == 409
        assert stale_delete.json()["error"]["code"] == "VERSION_CONFLICT"
        deleted = client.delete(
            f"/api/v1/model-drafts/{draft['id']}",
            params={"expectedVersion": 2},
        )
        assert deleted.status_code == 204
        assert client.get(f"/api/v1/model-drafts/{draft['id']}").status_code == 404

    with SessionLocal() as session:
        assert (
            session.scalar(
                select(func.count())
                .select_from(ModelRelease)
                .where(ModelRelease.public_id == release["id"])
            )
            == 1
        )
        assert session.scalar(select(func.count()).select_from(ModelDraft)) == 0
        audit_events = list(
            session.scalars(
                select(AuditEvent)
                .where(AuditEvent.aggregate_id.in_([draft["id"], release["id"]]))
                .order_by(AuditEvent.sequence_id)
            )
        )
        assert [event.action for event in audit_events] == [
            "created",
            "updated",
            "installed",
            "deleted",
        ]
        assert all("model" not in event.changes for event in audit_events)


def test_draft_installation_recompiles_and_rejects_invalid_or_conflicting_content(
    monkeypatch,
):
    monkeypatch.setenv("MODEL_ADMIN_MUTATIONS_ENABLED", "true")
    enabled_app = create_app()
    with TestClient(enabled_app) as client:
        active_model = client.get("/api/v1/model").json()
        invalid = dict(active_model)
        invalid.pop("applications")
        invalid_draft = client.post(
            "/api/v1/model-drafts", json={"name": "Invalid", "model": invalid}
        ).json()
        invalid_compile = client.post(
            f"/api/v1/model-drafts/{invalid_draft['id']}/compile",
            json={"expectedVersion": 1},
        )
        assert invalid_compile.status_code == 200
        assert invalid_compile.json()["valid"] is False
        assert invalid_compile.json()["compatibility"]["classification"] == "invalid"
        assert "model" not in invalid_compile.json()
        assert "modelHash" not in invalid_compile.json()
        invalid_install = client.post(
            f"/api/v1/model-drafts/{invalid_draft['id']}/installation",
            json={"expectedVersion": 1},
        )
        assert invalid_install.status_code == 422
        assert invalid_install.json()["error"]["code"] == "INVALID_MODEL"

        conflicting = client.get("/api/v1/model").json()
        conflicting["product"]["name"] = "Same identity, different content"
        conflict_draft = client.post(
            "/api/v1/model-drafts",
            json={"name": "Conflict", "model": conflicting},
        ).json()
        conflict = client.post(
            f"/api/v1/model-drafts/{conflict_draft['id']}/installation",
            json={"expectedVersion": 1},
        )
        assert conflict.status_code == 409
        assert conflict.json()["error"]["code"] == "RELEASE_IDENTITY_CONFLICT"


def test_concurrent_identical_draft_installations_are_idempotent(monkeypatch):
    monkeypatch.setenv("MODEL_ADMIN_MUTATIONS_ENABLED", "true")
    enabled_app = create_app()
    with TestClient(enabled_app) as client:
        candidate = client.get("/api/v1/model").json()
        candidate["release"]["version"] = "0.4.0-wp3-concurrent-install"
        draft_ids = [
            client.post(
                "/api/v1/model-drafts",
                json={"name": f"Concurrent {index}", "model": candidate},
            ).json()["id"]
            for index in range(2)
        ]

        def install(draft_id: str):
            return client.post(
                f"/api/v1/model-drafts/{draft_id}/installation",
                json={"expectedVersion": 1},
            )

        with ThreadPoolExecutor(max_workers=2) as executor:
            responses = list(executor.map(install, draft_ids))

    assert sorted(response.status_code for response in responses) == [200, 201]
    assert len({response.json()["id"] for response in responses}) == 1


def test_guarded_activation_updates_runtime_state_registry_and_audit(monkeypatch):
    monkeypatch.setenv("MODEL_ADMIN_MUTATIONS_ENABLED", "true")
    enabled_app = create_app()
    with TestClient(enabled_app) as client:
        active = client.get("/api/v1/model")
        old_release_id = active.headers["X-Model-Release-Id"]
        candidate_model = active.json()
        candidate_model["release"]["version"] = "0.4.0-wp4-activation"
        candidate_model["product"]["name"] = "Activated model"
        with SessionLocal() as session:
            candidate = ensure_bootstrap_release(
                session, EngineModel.model_validate(candidate_model)
            )
            session.commit()
            state = default_model(session)
            assert state is not None
            expected_version = state.version

        response = client.post(
            DEFAULT_ACTIVATION,
            json={
                "releaseId": candidate.public_id,
                "expectedVersion": expected_version,
                "expectedReleaseId": old_release_id,
            },
        )

        assert response.status_code == 200
        body = response.json()
        assert body["releaseId"] == candidate.public_id
        assert body["modelHash"] == candidate.model_hash
        assert body["version"] == expected_version + 1
        assert datetime.fromisoformat(body["updatedAt"]).utcoffset() == UTC.utcoffset(
            datetime.fromisoformat(body["updatedAt"])
        )
        published = client.get("/api/v1/model")
        assert published.status_code == 200
        assert published.headers["X-Model-Release-Id"] == candidate.public_id
        assert published.json()["product"]["name"] == "Activated model"

    with SessionLocal() as session:
        event = session.scalar(
            select(AuditEvent)
            .where(
                AuditEvent.aggregate_type == "workspace_model",
                AuditEvent.action == "activated",
                AuditEvent.version == expected_version + 1,
            )
            .order_by(AuditEvent.sequence_id.desc())
        )
        assert event is not None
        assert event.changes == {
            "workspaceKey": "default",
            "changeSetsLeftBehind": [],
            "oldReleaseId": old_release_id,
            "oldModelHash": active.headers["ETag"].strip('"'),
            "newReleaseId": candidate.public_id,
            "newModelHash": candidate.model_hash,
        }


def test_activation_blocks_incompatible_runtime_data_without_changing_selection(monkeypatch):
    monkeypatch.setenv("MODEL_ADMIN_MUTATIONS_ENABLED", "true")
    enabled_app = create_app()
    with TestClient(enabled_app) as client:
        active = client.get("/api/v1/model")
        active_release_id = active.headers["X-Model-Release-Id"]
        used_application = active.json()["applications"][0]["key"]
        used_object_type = active.json()["applications"][0]["objectTypeKeys"][0]
        candidate_model = active.json()
        candidate_model["release"]["version"] = "0.4.0-wp4-incompatible"
        candidate_model["applications"] = [
            item for item in candidate_model["applications"] if item["key"] != used_application
        ]
        with SessionLocal() as session:
            state = default_model(session)
            assert state is not None
            publication = Publication(
                workspace_key="default",
                model_release_id=state.model_release_id,
                publication_number=1,
                status="active",
            )
            session.add(publication)
            session.flush()
            item = RdmObject(
                id=str(uuid4()),
                workspace_key="default",
                application_key=used_application,
                object_type_key=used_object_type,
                name="Compatibility guard evidence",
            )
            session.add(item)
            session.flush()
            session.add(
                PublicationObject(
                    publication_id=publication.id,
                    object_id=item.id,
                    application_key=item.application_key,
                    object_type_key=item.object_type_key,
                    name=item.name,
                    parent_object_id=None,
                    attributes={},
                    version=item.version,
                )
            )
            workspace = session.get(Workspace, "default")
            assert workspace is not None
            workspace.active_publication_id = publication.id
            candidate = ensure_bootstrap_release(
                session, EngineModel.model_validate(candidate_model)
            )
            session.commit()
            expected_version = state.version

        response = client.post(
            DEFAULT_ACTIVATION,
            json={
                "releaseId": candidate.public_id,
                "expectedVersion": expected_version,
                "expectedReleaseId": active_release_id,
            },
        )

        assert response.status_code == 409
        assert response.json()["error"]["code"] == "MODEL_MIGRATION_REQUIRED"
        diagnostic = next(
            item
            for item in response.json()["error"]["details"]
            if item["code"] == "APPLICATION_IN_USE"
        )
        assert diagnostic["path"].startswith("/applications/")
        assert diagnostic["count"] >= 1
        assert client.get("/api/v1/model").headers["X-Model-Release-Id"] == active_release_id
        with SessionLocal() as session:
            state = default_model(session)
            assert state is not None
            assert state.version == expected_version


def test_activation_rejects_stale_runtime_tokens(monkeypatch):
    monkeypatch.setenv("MODEL_ADMIN_MUTATIONS_ENABLED", "true")
    enabled_app = create_app()
    with TestClient(enabled_app) as client:
        active = client.get("/api/v1/model")
        active_release_id = active.headers["X-Model-Release-Id"]
        with SessionLocal() as session:
            state = default_model(session)
            assert state is not None
            current_version = state.version

        response = client.post(
            DEFAULT_ACTIVATION,
            json={
                "releaseId": active_release_id,
                "expectedVersion": current_version + 1,
                "expectedReleaseId": active_release_id,
            },
        )
        wrong_release_response = client.post(
            DEFAULT_ACTIVATION,
            json={
                "releaseId": active_release_id,
                "expectedVersion": current_version,
                "expectedReleaseId": str(uuid4()),
            },
        )

    assert response.status_code == 409
    assert response.json()["error"] == {
        "code": "ACTIVATION_CONFLICT",
        "message": "The model of workspace 'default' changed before activation",
        "details": {
            "workspaceKey": "default",
            "currentReleaseId": active_release_id,
            "currentVersion": current_version,
        },
    }
    assert wrong_release_response.status_code == 409
    assert wrong_release_response.json()["error"]["code"] == "ACTIVATION_CONFLICT"


def test_concurrent_activation_allows_only_one_runtime_state_claim(monkeypatch):
    monkeypatch.setenv("MODEL_ADMIN_MUTATIONS_ENABLED", "true")
    enabled_app = create_app()
    with TestClient(enabled_app) as client:
        active = client.get("/api/v1/model")
        active_release_id = active.headers["X-Model-Release-Id"]
        candidates = []
        with SessionLocal() as session:
            for suffix in ("a", "b"):
                candidate_model = active.json()
                candidate_model["release"]["version"] = f"0.4.0-wp4-concurrent-{suffix}"
                candidates.append(
                    ensure_bootstrap_release(session, EngineModel.model_validate(candidate_model))
                )
            session.commit()
            state = default_model(session)
            assert state is not None
            expected_version = state.version

        def activate(candidate: ModelRelease):
            return client.post(
                DEFAULT_ACTIVATION,
                json={
                    "releaseId": candidate.public_id,
                    "expectedVersion": expected_version,
                    "expectedReleaseId": active_release_id,
                },
            )

        with ThreadPoolExecutor(max_workers=2) as executor:
            responses = list(executor.map(activate, candidates))

        assert sorted(response.status_code for response in responses) == [200, 409]
        conflict = next(response for response in responses if response.status_code == 409)
        assert conflict.json()["error"]["code"] == "ACTIVATION_CONFLICT"
        winner = next(response for response in responses if response.status_code == 200).json()
        assert (
            client.get("/api/v1/model").headers["X-Model-Release-Id"] == winner["releaseId"]
        )


def test_registry_refresh_failure_leaves_committed_activation_unready(monkeypatch):
    monkeypatch.setenv("MODEL_ADMIN_MUTATIONS_ENABLED", "true")
    enabled_app = create_app()
    with TestClient(enabled_app, raise_server_exceptions=False) as client:
        active = client.get("/api/v1/model")
        active_release_id = active.headers["X-Model-Release-Id"]
        candidate_model = active.json()
        candidate_model["release"]["version"] = "0.4.0-wp4-refresh-failure"
        with SessionLocal() as session:
            candidate = ensure_bootstrap_release(
                session, EngineModel.model_validate(candidate_model)
            )
            session.commit()
            state = default_model(session)
            assert state is not None
            expected_version = state.version

        def fail_refresh(_release_db_id):
            raise RuntimeError("publish failed")

        monkeypatch.setattr(
            "app.management.routers.model_management.model_registry.warm", fail_refresh
        )
        response = client.post(
            DEFAULT_ACTIVATION,
            json={
                "releaseId": candidate.public_id,
                "expectedVersion": expected_version,
                "expectedReleaseId": active_release_id,
            },
        )

        assert response.status_code == 503
        assert response.json()["error"]["code"] == "MODEL_REGISTRY_REFRESH_FAILED"
        # Only the workspace on that release is unavailable (0.11 D29); health counts every one.
        unavailable = client.get("/api/v1/model")
        assert unavailable.status_code == 503
        assert unavailable.json()["error"]["code"] == "MODEL_REGISTRY_UNAVAILABLE"
        assert unavailable.json()["error"]["details"]["workspaceKey"] == "default"
        with SessionLocal() as session:
            state = default_model(session)
            assert state is not None
            assert state.model_release_id == candidate.id
            assert state.version == expected_version + 1

    model_registry.clear()


def test_activation_rejects_corrupted_installed_model_without_mutation(monkeypatch):
    monkeypatch.setenv("MODEL_ADMIN_MUTATIONS_ENABLED", "true")
    enabled_app = create_app()
    with TestClient(enabled_app) as client:
        active = client.get("/api/v1/model")
        active_release_id = active.headers["X-Model-Release-Id"]
        candidate_model = active.json()
        candidate_model["release"]["version"] = "0.4.0-wp4-corrupted"
        with SessionLocal() as session:
            candidate = ensure_bootstrap_release(
                session, EngineModel.model_validate(candidate_model)
            )
            session.commit()
            state = default_model(session)
            assert state is not None
            expected_version = state.version
            candidate.model_json = {}
            session.commit()

        response = client.post(
            DEFAULT_ACTIVATION,
            json={
                "releaseId": candidate.public_id,
                "expectedVersion": expected_version,
                "expectedReleaseId": active_release_id,
            },
        )

        assert response.status_code == 500
        assert response.json()["error"]["code"] == "INVALID_INSTALLED_MODEL"
        assert response.json()["error"]["details"]
        assert client.get("/api/v1/model").headers["X-Model-Release-Id"] == active_release_id
        with SessionLocal() as session:
            state = default_model(session)
            assert state is not None
            assert state.version == expected_version


def test_activation_rejects_a_historical_schema_release_without_mutation(monkeypatch):
    monkeypatch.setenv("MODEL_ADMIN_MUTATIONS_ENABLED", "true")
    enabled_app = create_app()
    with TestClient(enabled_app) as client:
        active = client.get("/api/v1/model")
        active_release_id = active.headers["X-Model-Release-Id"]
        with SessionLocal() as session:
            identity = uuid4().hex
            historical = ModelRelease(
                release_key=f"historical-schema-{identity}",
                release_name="Historical schema",
                release_version=f"0.4.9-{identity}",
                schema_version="0.4",
                model_hash=identity * 2,
                model_json={"schemaVersion": "0.4", "historical": True},
            )
            session.add(historical)
            session.commit()
            historical_id = historical.public_id
            state = default_model(session)
            assert state is not None
            expected_version = state.version

        response = client.post(
            DEFAULT_ACTIVATION,
            json={
                "releaseId": historical_id,
                "expectedVersion": expected_version,
                "expectedReleaseId": active_release_id,
            },
        )

        assert response.status_code == 422
        assert response.json()["error"] == {
            "code": "UNSUPPORTED_SCHEMA_VERSION",
            "message": "Schema version '0.4' cannot be activated",
            "details": {
                "releaseId": historical_id,
                "schemaVersion": "0.4",
                "supportedSchemaVersions": ["0.5", "0.6", "0.7", "0.8", "0.9", "0.10"],
                "operation": "activation",
            },
        }
        assert client.get("/api/v1/model").headers["X-Model-Release-Id"] == active_release_id
        with SessionLocal() as session:
            state = default_model(session)
            assert state is not None
            assert state.version == expected_version


def test_model_admin_mutations_reject_multi_worker_configuration(monkeypatch):
    monkeypatch.setenv("MODEL_ADMIN_MUTATIONS_ENABLED", "true")
    monkeypatch.setenv("WEB_CONCURRENCY", "2")

    with pytest.raises(RuntimeError, match="requires WEB_CONCURRENCY=1"):
        create_app()


def test_release_activation_history_reads_recorded_predecessors_oldest_first(monkeypatch):
    monkeypatch.setenv("MODEL_ADMIN_MUTATIONS_ENABLED", "true")
    enabled_app = create_app()
    with TestClient(enabled_app) as client:
        active = client.get("/api/v1/model")
        original_id = active.headers["X-Model-Release-Id"]
        candidates = []
        for suffix in ("a", "b"):
            source = active.json()
            source["release"]["version"] = f"0.7.0-wp12-history-{suffix}"
            with SessionLocal() as session:
                release = ensure_bootstrap_release(session, EngineModel.model_validate(source))
                session.commit()
                candidates.append(release.public_id)
        first_id, second_id = candidates

        untouched = client.get(f"/api/v1/model-releases/{first_id}/activations")
        assert untouched.status_code == 200
        assert untouched.json() == {
            "items": [],
            "nextCursor": None,
            "prevCursor": None,
            "anchor": None,
        }

        # original -> first -> second -> first (rollback) -> original (restores the shared database)
        current_id = original_id
        for target_id in (first_id, second_id, first_id, original_id):
            state = client.get("/api/v1/workspaces/default/model").json()
            response = client.post(
                DEFAULT_ACTIVATION,
                json={
                    "releaseId": target_id,
                    "expectedVersion": state["version"],
                    "expectedReleaseId": current_id,
                },
            )
            assert response.status_code == 200, response.json()
            current_id = target_id

        first_page = client.get(
            f"/api/v1/model-releases/{first_id}/activations", params={"pageSize": 1}
        )
        assert first_page.status_code == 200
        introduced = first_page.json()["items"]
        assert [item["previousReleaseId"] for item in introduced] == [original_id]
        assert introduced[0]["kind"] == "activated"
        assert datetime.fromisoformat(introduced[0]["occurredAt"]).utcoffset() is not None
        cursor = first_page.json()["nextCursor"]
        assert cursor is not None

        second_page = client.get(
            f"/api/v1/model-releases/{first_id}/activations",
            params={"pageSize": 1, "cursor": cursor},
        )
        assert [item["previousReleaseId"] for item in second_page.json()["items"]] == [second_id]
        assert second_page.json()["items"][0]["runtimeVersion"] > introduced[0]["runtimeVersion"]
        assert second_page.json()["nextCursor"] is None

        second = client.get(f"/api/v1/model-releases/{second_id}/activations").json()
        assert [item["previousReleaseId"] for item in second["items"]] == [first_id]

        reused = client.get(
            f"/api/v1/model-releases/{second_id}/activations",
            params={"pageSize": 1, "cursor": cursor},
        )
        assert reused.status_code == 422
        assert reused.json()["error"]["code"] == "INVALID_CURSOR"

        unknown = client.get(
            "/api/v1/model-releases/00000000-0000-4000-8000-000000000000/activations"
        )
        assert unknown.status_code == 404
        assert unknown.json()["error"]["code"] == "MODEL_RELEASE_NOT_FOUND"


def test_release_activation_history_includes_offline_schema_upgrades():
    with SessionLocal() as session:
        upgraded = ensure_bootstrap_release(session, _model("0.7.0-wp12-schema-upgrade"))
        session.add(
            AuditEvent(
                aggregate_type="model_runtime_state",
                aggregate_id=upgraded.public_id,
                action="schema_upgraded",
                version=99,
                changes={
                    "oldReleaseId": "legacy-release",
                    "newReleaseId": upgraded.public_id,
                    "oldSchemaVersion": "0.5",
                    "newSchemaVersion": "0.6",
                },
            )
        )
        session.commit()
        upgraded_id = upgraded.public_id

    with TestClient(app) as client:
        response = client.get(f"/api/v1/model-releases/{upgraded_id}/activations")

    assert response.status_code == 200
    [item] = response.json()["items"]
    assert item["kind"] == "schemaUpgraded"
    assert item["previousReleaseId"] == "legacy-release"
    assert item["runtimeVersion"] == 99
