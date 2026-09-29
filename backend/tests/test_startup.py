from pathlib import Path
from unittest.mock import patch as mock_patch

from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text

import app.main as main_module
from app.config import reload_settings
from app.engine.model.registry import model_registry
from app.main import create_app


def _upgrade_to_previous_revision(database_path: Path) -> None:
    config = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))
    config.set_main_option("sqlalchemy.url", f"sqlite:///{database_path}")
    command.upgrade(config, "20260905_02")


def test_application_lifespan_boots_and_restarts_against_a_real_clean_database(
    tmp_path, monkeypatch
):
    database_path = tmp_path / "startup-smoke.db"
    try:
        with monkeypatch.context() as patch:
            patch.setenv("DATABASE_URL", f"sqlite:///{database_path}")
            reload_settings()
            model_registry.clear()
            with TestClient(create_app()) as client:
                assert client.get("/health").json() == {"status": "ok"}
                assert client.get("/api/v1/model").status_code == 200

            model_registry.clear()
            with TestClient(create_app()) as restarted_client:
                assert restarted_client.get("/health").json() == {"status": "ok"}
                assert restarted_client.get("/api/v1/model").status_code == 200
    finally:
        model_registry.clear()
        reload_settings()


def test_startup_handles_unsafe_partial_migration_without_a_traceback(
    tmp_path, monkeypatch
):
    database_path = tmp_path / "unsafe-partial.db"
    _upgrade_to_previous_revision(database_path)
    engine = create_engine(f"sqlite:///{database_path}")
    with engine.begin() as connection:
        connection.execute(text("CREATE TABLE object_revisions (id VARCHAR(36))"))
    engine.dispose()

    try:
        with monkeypatch.context() as patch:
            patch.setenv("DATABASE_URL", f"sqlite:///{database_path}")
            reload_settings()
            model_registry.clear()
            with mock_patch.object(main_module.logger, "error") as log_error, TestClient(
                create_app()
            ) as client:
                response = client.get("/health")
                assert response.status_code == 503
                assert response.json() == {"status": "unhealthy"}

        log_error.assert_called_once()
        assert log_error.call_args.args[0] == "%s"
        message = str(log_error.call_args.args[1])
        assert "Database migration failed" in message
        assert "incomplete object-lifecycle migration" in message
        assert "take a consistent backup" in message
        assert "python -m app.cli.database_upgrade" in message
        assert "do not edit or stamp the schema manually" in message
        assert "Traceback" not in message
        assert "exc_info" not in log_error.call_args.kwargs
    finally:
        model_registry.clear()
        reload_settings()
