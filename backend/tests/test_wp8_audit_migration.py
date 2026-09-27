"""WP8 audit-width migration at upgrade, restart and interrupted-startup boundaries."""

from pathlib import Path
from unittest.mock import patch as mock_patch

from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, inspect, text

import app.main as main_module
from app.config import reload_settings
from app.main import create_app
from app.services.model.registry import model_registry


def _preceding_database(path):
    config = Config(str(Path(__file__).parents[1] / "alembic.ini"))
    config.set_main_option("sqlalchemy.url", f"sqlite:///{path}")
    command.upgrade(config, "20260907_03")
    engine = create_engine(f"sqlite:///{path}")
    with engine.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO audit_events (sequence_id, event_id, aggregate_type, aggregate_id, "
                "action, version, changes, occurred_at) VALUES (123, 'event-to-preserve', 'object', "
                "'object-to-preserve', 'created', 1, '{}', '2026-09-08T12:00:00')"
            )
        )
        connection.execute(
            text(
                "INSERT INTO audit_event_subjects (audit_event_id, object_id) "
                "VALUES (123, 'object-to-preserve')"
            )
        )
    return engine


def _assert_history_preserved(engine):
    with engine.connect() as connection:
        assert connection.execute(
            text(
                "SELECT e.event_id, s.object_id FROM audit_events e JOIN audit_event_subjects s "
                "ON s.audit_event_id = e.sequence_id WHERE e.sequence_id = 123"
            )
        ).all() == [("event-to-preserve", "object-to-preserve")]
        assert connection.execute(text("PRAGMA foreign_key_check")).all() == []


def test_wp8_upgrade_preserves_audit_subjects_and_restarts(tmp_path, monkeypatch):
    path = tmp_path / "audit-upgrade.db"
    engine = _preceding_database(path)
    try:
        with monkeypatch.context() as patch:
            patch.setenv("DATABASE_URL", f"sqlite:///{path}")
            for _attempt in range(2):
                model_registry.clear()
                with TestClient(create_app()) as client:
                    assert client.get("/health").json() == {"status": "ok"}
                    assert client.get("/api/v1/model").status_code == 200
                _assert_history_preserved(engine)
            columns = {row["name"]: row for row in inspect(engine).get_columns("audit_events")}
            assert columns["aggregate_id"]["type"].length == 200
            with engine.connect() as connection:
                assert (
                    connection.scalar(text("SELECT version_num FROM alembic_version"))
                    == "20260927_01"
                )
    finally:
        engine.dispose()
        model_registry.clear()
        reload_settings()


def test_wp8_interrupted_batch_refuses_safely_and_preserves_history(tmp_path, monkeypatch):
    path = tmp_path / "audit-interrupted.db"
    engine = _preceding_database(path)
    # A process stopped during Alembic's copy phase can leave this table behind.
    with engine.begin() as connection:
        connection.execute(text("CREATE TABLE _alembic_tmp_audit_events (sentinel TEXT)"))
        connection.execute(text("INSERT INTO _alembic_tmp_audit_events VALUES ('preserve')"))
    try:
        with monkeypatch.context() as patch:
            patch.setenv("DATABASE_URL", f"sqlite:///{path}")
            model_registry.clear()
            with (
                mock_patch.object(main_module.logger, "error") as error,
                TestClient(create_app()) as client,
            ):
                assert client.get("/health").status_code == 503
            message = str(error.call_args.args[1])
            assert "20260907_03" in message and "20260927_01" in message
            assert "_alembic_tmp_audit_events" in message
            assert "take a consistent backup" in message
            assert "python -m app.cli.database_upgrade" in message
            assert "do not edit or stamp the schema manually" in message
            assert "Traceback" not in message
            assert "exc_info" not in error.call_args.kwargs
        _assert_history_preserved(engine)
        with engine.connect() as connection:
            assert (
                connection.scalar(text("SELECT sentinel FROM _alembic_tmp_audit_events"))
                == "preserve"
            )
            assert (
                connection.scalar(text("SELECT version_num FROM alembic_version")) == "20260907_03"
            )
    finally:
        engine.dispose()
        model_registry.clear()
        reload_settings()


def test_current_live_base_interrupted_migration_refuses_startup_and_preserves_partial_table(
    tmp_path, monkeypatch
):
    path = tmp_path / "current-live-base-interrupted.db"
    config = Config(str(Path(__file__).parents[1] / "alembic.ini"))
    config.set_main_option("sqlalchemy.url", f"sqlite:///{path}")
    command.upgrade(config, "20260908_01")
    engine = create_engine(f"sqlite:///{path}")
    with engine.begin() as connection:
        connection.execute(text("CREATE TABLE workspace_draft_bases (sentinel TEXT)"))
        connection.execute(text("INSERT INTO workspace_draft_bases VALUES ('preserve')"))
    try:
        with monkeypatch.context() as patch:
            patch.setenv("DATABASE_URL", f"sqlite:///{path}")
            model_registry.clear()
            with (
                mock_patch.object(main_module.logger, "error") as error,
                TestClient(create_app()) as client,
            ):
                assert client.get("/health").status_code == 503
            message = str(error.call_args.args[1])
            assert "20260908_01" in message and "20260927_01" in message
            assert "workspace_draft_bases" in message
            assert "take a consistent backup" in message
            assert "python -m app.cli.database_upgrade" in message
            assert "Traceback" not in message
        with engine.connect() as connection:
            assert (
                connection.scalar(text("SELECT sentinel FROM workspace_draft_bases")) == "preserve"
            )
            assert (
                connection.scalar(text("SELECT version_num FROM alembic_version")) == "20260908_01"
            )
    finally:
        engine.dispose()
        model_registry.clear()
        reload_settings()
