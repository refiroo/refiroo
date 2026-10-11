"""WP-11: Historical release refusals, actionable API errors and draft UI consistency.

Backend regression tests for unsupported-schema diff/compile refusals, the improved
unexpected-error boundary and corrupt-model distinction.
"""

import hashlib
import json
from unittest.mock import patch
from uuid import uuid4

from fastapi.testclient import TestClient

from app.db import SessionLocal
from app.main import app, create_app
from app.models.database import ModelDraft, ModelRelease, ModelRuntimeState


def _install_historical(*, schema_version="0.4", stored_schema_version=None, corrupt=False):
    identity = uuid4().hex
    model_json = (
        {"schemaVersion": schema_version, "historical": True, "_id": identity}
        if not corrupt
        else {"_id": identity}
    )
    with SessionLocal() as session:
        release = ModelRelease(
            release_key=f"historical-{identity}",
            release_name="Historical schema",
            release_version=f"0.0.1-{identity}",
            schema_version=stored_schema_version or schema_version,
            model_hash=hashlib.sha256(json.dumps(model_json, sort_keys=True).encode()).hexdigest(),
            model_json=model_json,
            is_active=False,
        )
        session.add(release)
        session.commit()
        return release.public_id


def test_diff_unsupported_candidate_returns_422():
    with TestClient(app) as client:
        active_id = client.get("/api/v1/model").headers["X-Model-Release-Id"]
        historical_id = _install_historical(schema_version="0.4")

        response = client.get(
            f"/api/v1/model-releases/{historical_id}/diff",
            params={"againstReleaseId": active_id},
        )

    assert response.status_code == 422
    body = response.json()["error"]
    assert body["code"] == "UNSUPPORTED_SCHEMA_VERSION"
    assert body["details"]["releaseId"] == historical_id
    assert body["details"]["schemaVersion"] == "0.4"
    assert body["details"]["supportedSchemaVersions"] == ["0.5", "0.6", "0.7", "0.8", "0.9", "0.10"]
    assert body["details"]["operation"] == "diff"


def test_diff_unsupported_baseline_returns_422():
    with TestClient(app) as client:
        active_id = client.get("/api/v1/model").headers["X-Model-Release-Id"]
        historical_id = _install_historical(schema_version="0.3")

        response = client.get(
            f"/api/v1/model-releases/{active_id}/diff",
            params={"againstReleaseId": historical_id},
        )

    assert response.status_code == 422
    body = response.json()["error"]
    assert body["code"] == "UNSUPPORTED_SCHEMA_VERSION"
    assert body["details"]["releaseId"] == historical_id
    assert body["details"]["schemaVersion"] == "0.3"
    assert body["details"]["operation"] == "diff"


def test_diff_reports_schema_from_json_when_release_metadata_disagrees():
    with TestClient(app) as client:
        active_id = client.get("/api/v1/model").headers["X-Model-Release-Id"]
        historical_id = _install_historical(
            schema_version="0.4", stored_schema_version="0.6"
        )

        response = client.get(
            f"/api/v1/model-releases/{historical_id}/diff",
            params={"againstReleaseId": active_id},
        )

    assert response.status_code == 422
    assert response.json()["error"]["details"]["schemaVersion"] == "0.4"


def test_diff_corrupt_supported_schema_remains_500():
    with TestClient(app) as client:
        active_id = client.get("/api/v1/model").headers["X-Model-Release-Id"]
        corrupt_id = _install_historical(schema_version="0.6", corrupt=True)

        response = client.get(
            f"/api/v1/model-releases/{corrupt_id}/diff",
            params={"againstReleaseId": active_id},
        )

    assert response.status_code == 500
    assert response.json()["error"]["code"] == "INVALID_INSTALLED_MODEL"


def test_diff_supported_releases_succeeds():
    with TestClient(app) as client:
        active_id = client.get("/api/v1/model").headers["X-Model-Release-Id"]

        response = client.get(
            f"/api/v1/model-releases/{active_id}/diff",
            params={"againstReleaseId": active_id},
        )

    assert response.status_code == 200


def test_diff_missing_release_retains_404():
    with TestClient(app) as client:
        active_id = client.get("/api/v1/model").headers["X-Model-Release-Id"]
        response = client.get(
            f"/api/v1/model-releases/{active_id}/diff",
            params={"againstReleaseId": "00000000-0000-4000-8000-000000000000"},
        )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "MODEL_RELEASE_NOT_FOUND"


def test_activation_unsupported_schema_retains_422(monkeypatch):
    """Existing activation refusal for unsupported schema must still work."""
    monkeypatch.setenv("MODEL_ADMIN_MUTATIONS_ENABLED", "true")
    with TestClient(create_app()) as client:
        active_id = client.get("/api/v1/model").headers["X-Model-Release-Id"]
        historical_id = _install_historical(schema_version="0.4")
        with SessionLocal() as session:
            state = session.get(ModelRuntimeState, 1)
            version = state.version

        response = client.post(
            f"/api/v1/model-releases/{historical_id}/activation",
            json={"expectedRuntimeVersion": version, "expectedActiveReleaseId": active_id},
        )

    assert response.status_code == 422
    error = response.json()["error"]
    assert error["code"] == "UNSUPPORTED_SCHEMA_VERSION"
    assert error["details"] == {
        "releaseId": historical_id,
        "schemaVersion": "0.4",
        "supportedSchemaVersions": ["0.5", "0.6", "0.7", "0.8", "0.9", "0.10"],
        "operation": "activation",
    }


def test_activation_reports_unsupported_schema_from_json_without_mutation(monkeypatch):
    monkeypatch.setenv("MODEL_ADMIN_MUTATIONS_ENABLED", "true")
    with TestClient(create_app()) as client:
        active_id = client.get("/api/v1/model").headers["X-Model-Release-Id"]
        historical_id = _install_historical(
            schema_version="0.4", stored_schema_version="0.6"
        )
        with SessionLocal() as session:
            state = session.get(ModelRuntimeState, 1)
            version = state.version

        response = client.post(
            f"/api/v1/model-releases/{historical_id}/activation",
            json={"expectedRuntimeVersion": version, "expectedActiveReleaseId": active_id},
        )

    assert response.status_code == 422
    assert response.json()["error"]["details"]["schemaVersion"] == "0.4"
    with SessionLocal() as session:
        state = session.get(ModelRuntimeState, 1)
        assert state.version == version
        assert session.get(ModelRelease, state.active_model_release_id).public_id == active_id


def test_unexpected_error_includes_correlation_id():
    with (
        TestClient(app, raise_server_exceptions=False) as client,
        patch(
            "app.management.routers.model_releases.paginate_statement",
            side_effect=RuntimeError("simulated failure"),
        ),
    ):
        response = client.get("/api/v1/model-releases")

    assert response.status_code == 500
    body = response.json()["error"]
    assert body["code"] == "INTERNAL_ERROR"
    assert "reference" in body["message"]
    assert body["details"]["correlationId"]
    assert len(body["details"]["correlationId"]) == 12


def test_compile_model_draft_unsupported_baseline(monkeypatch):
    monkeypatch.setenv("MODEL_ADMIN_MUTATIONS_ENABLED", "true")
    with TestClient(create_app()) as client:
        model = client.get("/api/v1/model").json()
        draft_response = client.post(
            "/api/v1/model-drafts",
            json={"name": "wp11-test", "model": model},
        )
        assert draft_response.status_code == 201
        draft = draft_response.json()

        historical_id = _install_historical(schema_version="0.4")
        with SessionLocal() as session:
            db_draft = session.query(ModelDraft).filter_by(public_id=draft["id"]).first()
            db_draft.base_model_release_id = session.query(ModelRelease.id).filter_by(
                public_id=historical_id
            ).scalar()
            session.commit()

        response = client.post(
            f"/api/v1/model-drafts/{draft['id']}/compile",
            json={"expectedVersion": draft["version"]},
        )

        client.delete(
            f"/api/v1/model-drafts/{draft['id']}",
            params={"expectedVersion": draft["version"]},
        )

    assert response.status_code == 422
    body = response.json()["error"]
    assert body["code"] == "UNSUPPORTED_SCHEMA_VERSION"
    assert body["details"]["releaseId"] == historical_id
    assert body["details"]["schemaVersion"] == "0.4"
    assert body["details"]["operation"] == "compile"
