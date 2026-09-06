import json
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.cli.model_schema_upgrade import transition
from app.config import reload_settings
from app.db import SessionLocal
from app.main import app
from app.models.database import ModelRelease, ModelRuntimeState
from app.services.model.compatibility import CompatibilityResult
from app.services.model.diagnostics import ModelDiagnostic
from app.services.model.registry import ModelRegistry

MODEL_PATH = Path(__file__).resolve().parents[2] / "model" / "rdm-starter.json"


def _legacy_database(database_path: Path) -> str:
    config = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))
    config.set_main_option("sqlalchemy.url", f"sqlite:///{database_path}")
    command.upgrade(config, "head")
    source = json.loads(MODEL_PATH.read_text())
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
    engine = create_engine(f"sqlite:///{database_path}")
    with Session(engine) as session, pytest.raises(
        RuntimeError, match="unsupported schema version '0.4'"
    ):
        ModelRegistry().resolve_active(session)
    with monkeypatch.context() as patch:
        patch.setenv("DATABASE_URL", f"sqlite:///{database_path}")
        reload_settings()
        selected_id = transition(MODEL_PATH)
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
            transition(MODEL_PATH)
    reload_settings()

    engine = create_engine(f"sqlite:///{database_path}")
    with Session(engine) as session:
        state = session.get(ModelRuntimeState, 1)
        releases = list(session.scalars(select(ModelRelease)))
        assert state.version == 1
        assert len(releases) == 1
        assert releases[0].public_id == old_release_id


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
