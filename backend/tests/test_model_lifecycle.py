from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

from app.db import SessionLocal, ensure_bootstrap_release
from app.main import app
from app.models.database import ApplicationMeta, Base, ModelRelease, ModelRuntimeState
from app.models.schema import EngineModel
from app.services.model_loader import load_bootstrap_model
from app.services.model_registry import ModelRegistry


def _model(version: str, *, product_name: str | None = None) -> EngineModel:
    source = load_bootstrap_model().model_dump(mode="json")
    source["release"]["version"] = version
    if product_name is not None:
        source["product"]["name"] = product_name
    return EngineModel.model_validate(source)


def _session() -> Session:
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    return Session(engine)


def test_first_bootstrap_initializes_runtime_state_and_restart_is_idempotent():
    with _session() as session:
        first = ensure_bootstrap_release(session, _model("0.4.0"))
        session.commit()
        first_public_id = first.public_id

        restarted = ensure_bootstrap_release(session, _model("0.4.0"))
        session.commit()

        state = session.get(ModelRuntimeState, 1)
        assert state is not None
        assert restarted.public_id == first_public_id
        assert state.active_model_release_id == first.id
        assert session.scalar(select(func.count()).select_from(ModelRelease)) == 1


def test_different_bootstrap_release_installs_inactive_and_preserves_runtime_selection():
    with _session() as session:
        first = ensure_bootstrap_release(session, _model("0.4.0"))
        session.commit()
        second = ensure_bootstrap_release(session, _model("0.5.0"))
        session.commit()

        state = session.get(ModelRuntimeState, 1)
        assert state is not None
        assert state.active_model_release_id == first.id
        assert first.is_active is True
        assert second.is_active is False
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

        first_snapshot = registry.resolve_active(session)
        assert registry.resolve_active(session).model is first_snapshot.model
        state = session.get(ModelRuntimeState, 1)
        assert state is not None
        state.active_model_release_id = second.id
        session.commit()
        second_snapshot = registry.resolve_active(session)

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
        snapshot = registry.resolve_active(session)

        with pytest.raises(ValidationError):
            snapshot.model.product.name = "Mutated product"
        with pytest.raises(TypeError, match="Model definitions are immutable"):
            snapshot.model.objectTypes[0].features["mutated"] = True
        with pytest.raises(AttributeError):
            snapshot.model.applications.append(snapshot.model.applications[0])
        with pytest.raises(TypeError, match="Model definitions are immutable"):
            snapshot.model._object_types_by_key.clear()

        resolved_again = registry.resolve_active(session)
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

        active_page = client.get("/api/v1/model-releases", params={"active": True})
        assert active_page.status_code == 200
        assert active_page.json()["nextCursor"] is None
        assert len(active_page.json()["items"]) == 1
        summary = active_page.json()["items"][0]
        assert summary["id"] == release_id
        assert summary["modelHash"] == model_hash
        assert summary["active"] is True
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

        by_key = client.get(
            "/api/v1/model-releases", params={"releaseKey": summary["key"]}
        )
        assert by_key.status_code == 200
        assert any(item["id"] == release_id for item in by_key.json()["items"])


def test_release_cursor_rejects_tampering_and_filter_reuse():
    with SessionLocal() as session:
        ensure_bootstrap_release(session, _model("0.5.0"))
        session.commit()

    with TestClient(app) as client:
        first_page = client.get("/api/v1/model-releases", params={"pageSize": 1})
        assert first_page.status_code == 200
        cursor = first_page.json()["nextCursor"]
        assert cursor is not None

        filtered = client.get(
            "/api/v1/model-releases",
            params={"active": True, "cursor": cursor, "pageSize": 1},
        )
        assert filtered.status_code == 422
        assert filtered.json()["error"]["code"] == "invalid_cursor"

        replacement = "A" if cursor[-1] != "A" else "B"
        tampered = client.get(
            "/api/v1/model-releases",
            params={"cursor": cursor[:-1] + replacement, "pageSize": 1},
        )
        assert tampered.status_code == 422
        assert tampered.json()["error"]["code"] == "invalid_cursor"


def test_unknown_model_release_is_explicit():
    with TestClient(app) as client:
        response = client.get(
            "/api/v1/model-releases/00000000-0000-4000-8000-000000000000"
        )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "model_release_not_found"


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
        assert invalid.json()["diagnostics"][0]["code"] == "unknown_object_type"
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
    assert body["compatibility"] == {
        "classification": "compatible",
        "activeReleaseId": active_release_id,
        "diagnostics": [],
    }
    paths = {item["path"] for item in body["changes"]}
    assert "/applications/rdm-master/views/domains/name" in paths
    assert "/release/version" in paths
    assert not any(path.startswith("/attributeTypes/") for path in paths)


def test_release_diff_reports_unknown_baseline_release():
    with TestClient(app) as client:
        release_id = client.get("/api/v1/model").headers["X-Model-Release-Id"]
        response = client.get(
            f"/api/v1/model-releases/{release_id}/diff",
            params={"againstReleaseId": "00000000-0000-4000-8000-000000000000"},
        )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "model_release_not_found"
