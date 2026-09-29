import json
import os
import subprocess
from pathlib import Path
from unittest.mock import Mock

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from model_support import MODEL_PATH, starter_at_schema
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.cli.model_schema_upgrade import transition
from app.config import get_settings, reload_settings
from app.db import SessionLocal
from app.engine.model.compatibility import CompatibilityResult
from app.engine.model.diagnostics import ModelDiagnostic
from app.engine.model.registry import ModelRegistry, UnsupportedSelectedModelSchema, model_registry
from app.main import app, create_app, schema_upgrade_command
from app.models.database import ModelRelease, ModelRuntimeState


def _candidate_model_path(tmp_path: Path, schema_version: str) -> Path:
    """The starter as a transition candidate at ``schema_version``."""
    if schema_version == "0.7":
        return MODEL_PATH
    path = tmp_path / f"rdm-starter-{schema_version}.json"
    path.write_text(json.dumps(starter_at_schema(schema_version)))
    return path


def _legacy_database(database_path: Path) -> str:
    config = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))
    config.set_main_option("sqlalchemy.url", f"sqlite:///{database_path}")
    command.upgrade(config, "head")
    source = starter_at_schema("0.5")
    source["schemaVersion"] = "0.4"
    source["release"]["version"] = "0.5.0"
    engine = create_engine(f"sqlite:///{database_path}")
    with Session(engine) as session:
        release = ModelRelease(
            release_key="rdm-starter",
            release_name="RDM Starter Model",
            release_version="0.5.0",
            schema_version="0.4",
            model_hash="a" * 64,
            model_json=source,
            is_active=True,
        )
        session.add(release)
        session.flush()
        session.add(ModelRuntimeState(id=1, active_model_release_id=release.id, version=1))
        session.commit()
        return release.public_id


def test_offline_schema_upgrade_installs_checks_and_atomically_selects_candidate(tmp_path, monkeypatch):
    database_path = tmp_path / "upgrade.db"
    old_release_id = _legacy_database(database_path)
    model_05 = _candidate_model_path(tmp_path, "0.5")
    engine = create_engine(f"sqlite:///{database_path}")
    with Session(engine) as session, pytest.raises(
        UnsupportedSelectedModelSchema
    ) as error:
        ModelRegistry().resolve_active(session)
    assert error.value.schema_version == "0.4"
    with monkeypatch.context() as patch:
        patch.setenv("DATABASE_URL", f"sqlite:///{database_path}")
        reload_settings()
        selected_id = transition(model_05)
    reload_settings()

    with Session(engine) as session:
        state = session.get(ModelRuntimeState, 1)
        selected = session.get(ModelRelease, state.active_model_release_id)
        assert selected.public_id == selected_id
        assert selected.schema_version == "0.5"
        assert state.version == 2
        assert session.scalar(select(ModelRelease).where(ModelRelease.public_id == old_release_id))


def test_offline_schema_upgrade_rolls_back_installation_when_compatibility_fails(tmp_path, monkeypatch):
    database_path = tmp_path / "blocked.db"
    old_release_id = _legacy_database(database_path)
    model_05 = _candidate_model_path(tmp_path, "0.5")
    diagnostic = ModelDiagnostic(
        severity="error",
        code="migration_needed",
        path="/objectTypes/domain",
        message="Stored data needs migration",
        count=1,
    )
    with monkeypatch.context() as patch:
        patch.setenv("DATABASE_URL", f"sqlite:///{database_path}")
        patch.setattr(
            "app.cli.model_schema_upgrade.analyze_compatibility",
            lambda *_args: CompatibilityResult(old_release_id, [diagnostic]),
        )
        reload_settings()
        with pytest.raises(RuntimeError, match="requires runtime-data migration"):
            transition(model_05)
    reload_settings()

    engine = create_engine(f"sqlite:///{database_path}")
    with Session(engine) as session:
        state = session.get(ModelRuntimeState, 1)
        releases = list(session.scalars(select(ModelRelease)))
        assert state.version == 1
        assert len(releases) == 1
        assert releases[0].public_id == old_release_id


def test_offline_schema_upgrade_rejects_a_selected_schema_05_release(tmp_path, monkeypatch):
    database_path = tmp_path / "already-upgraded.db"
    _legacy_database(database_path)
    model_05 = _candidate_model_path(tmp_path, "0.5")
    with monkeypatch.context() as patch:
        patch.setenv("DATABASE_URL", f"sqlite:///{database_path}")
        reload_settings()
        selected_id = transition(model_05)
        with pytest.raises(
            RuntimeError,
            match="requires a selected schema 0.4 release; found schema 0.5",
        ):
            transition(model_05)
    reload_settings()

    engine = create_engine(f"sqlite:///{database_path}")
    with Session(engine) as session:
        state = session.get(ModelRuntimeState, 1)
        releases = list(session.scalars(select(ModelRelease)))
        assert state.version == 2
        assert session.get(ModelRelease, state.active_model_release_id).public_id == selected_id
        assert len(releases) == 2


def test_startup_reports_the_exact_schema_upgrade_command_without_a_traceback(
    monkeypatch, caplog
):
    def reject_selected_schema(_session):
        raise UnsupportedSelectedModelSchema("0.4")

    model_registry.clear()
    monkeypatch.setattr(model_registry, "resolve_active", reject_selected_schema)
    try:
        with caplog.at_level("ERROR", logger="app.main"), TestClient(
            create_app()
        ) as client:
            assert client.get("/health").status_code == 503

        assert "RDM Engine cannot serve model-backed requests" in caplog.text
        assert schema_upgrade_command(get_settings()) in caplog.text
        assert "<path>" not in caplog.text
        assert "Traceback" not in caplog.text
        assert all(record.exc_info is None for record in caplog.records)
    finally:
        model_registry.clear()


def test_schema_04_release_remains_listable_and_exportable_as_history():
    with TestClient(app) as client:
        with SessionLocal() as session:
            historical = ModelRelease(
                release_key="historical-schema",
                release_name="Historical schema",
                release_version="0.4.9",
                schema_version="0.4",
                model_hash="b" * 64,
                model_json={"schemaVersion": "0.4", "historical": True},
                is_active=False,
            )
            session.add(historical)
            session.commit()
            release_id = historical.public_id

        page = client.get("/api/v1/model-releases", params={"pageSize": 100})
        assert page.status_code == 200
        assert release_id in {item["id"] for item in page.json()["items"]}
        detail = client.get(
            f"/api/v1/model-releases/{release_id}", params={"includeModel": "true"}
        )
        assert detail.status_code == 200
        assert detail.json()["schemaVersion"] == "0.4"
        assert detail.json()["model"] == {"schemaVersion": "0.4", "historical": True}


@pytest.mark.parametrize("candidate_schema", ["0.5", "0.6", "0.7"])
def test_actual_startup_recovery_command_selects_supported_candidate_and_restarts(
    tmp_path, monkeypatch, candidate_schema
):
    database_path = tmp_path / "recovery.db"
    old_release_id = _legacy_database(database_path)
    candidate_path = _candidate_model_path(tmp_path, candidate_schema)
    with monkeypatch.context() as patch:
        patch.setenv("DATABASE_URL", f"sqlite:///{database_path}")
        patch.setenv("RDM_MODEL_PATH", str(candidate_path))
        reload_settings()
        model_registry.clear()
        try:
            error_log = Mock()
            patch.setattr("app.main.logger.error", error_log)
            with TestClient(create_app()) as client:
                assert client.get("/health").status_code == 503
            command_text = schema_upgrade_command(get_settings())
            assert error_log.call_args.args[2] == command_text
            # Interrupt after candidate installation and runtime updates, before commit.
            with monkeypatch.context() as interruption:
                interruption.setattr("app.cli.model_schema_upgrade.AuditEvent", Mock(side_effect=RuntimeError("interrupted transition")))
                with pytest.raises(RuntimeError, match="interrupted transition"):
                    transition(candidate_path)
            engine = create_engine(f"sqlite:///{database_path}")
            with Session(engine) as session:
                state = session.get(ModelRuntimeState, 1)
                assert state.version == 1
                assert session.get(ModelRelease, state.active_model_release_id).public_id == old_release_id
            result = subprocess.run(command_text, shell=True, capture_output=True, text=True, env=os.environ.copy(), check=False)
            assert result.returncode == 0, result.stderr
            assert "Selected supported model release" in result.stdout
            model_registry.clear()  # A process restart resets registry readiness.
            with TestClient(create_app()) as client:
                assert client.get("/health").status_code == 200
                assert client.get("/api/v1/model").json()["schemaVersion"] == candidate_schema
            with TestClient(create_app()) as client:
                assert client.get("/health").status_code == 200
            # Retrying an already completed transition refuses safely and preserves the release.
            refused = subprocess.run(command_text, shell=True, capture_output=True, text=True, env=os.environ.copy(), check=False)
            assert refused.returncode == 1
            assert "Schema transition refused" in refused.stderr
            assert "selected release is unchanged" in refused.stderr
            assert "Traceback" not in refused.stderr
            with TestClient(create_app()) as client:
                assert client.get("/health").status_code == 200
        finally:
            model_registry.clear()
    reload_settings()
