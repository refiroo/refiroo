"""Startup on PostgreSQL (0.9.0-alpha.1, PG1): the lifespan against real databases.

A clean database is checked, migrated to the baseline and bootstrapped, and starts again unchanged.
Every refusal (no or a non-PostgreSQL ``DATABASE_URL``, another collation, an unknown revision, a
missing ``pg_trgm``) leaves the service in maintenance mode (``/health`` 503) and logs one message
saying what failed and what to do, never a traceback. A migration that fails part-way rolls back
completely, and the next start after the cause is removed succeeds.
"""

from collections.abc import Iterator
from contextlib import contextmanager, suppress
from unittest.mock import patch as mock_patch

import pytest
import seeds
from fastapi.testclient import TestClient
from sqlalchemy import URL, create_engine, inspect, text

import app.main as main_module
from app.cli import database_upgrade
from app.config import reload_settings
from app.db import DatabaseStartupError, get_engine
from app.engine.model.registry import model_registry
from app.main import create_app

HEAD = "20261001_01"
LIMITED_ROLE = "rdm_startup_limited"


@pytest.fixture
def databases() -> Iterator[list[URL]]:
    """Databases a test creates, dropped when it ends."""
    created: list[URL] = []
    yield created
    for url in created:
        seeds.drop(url.database)


@contextmanager
def serve(monkeypatch: pytest.MonkeyPatch, url: str | None) -> Iterator[tuple[TestClient, list[str]]]:
    """Start the application on ``url`` and yield its client with the errors its startup logged."""
    with monkeypatch.context() as patch:
        if url is None:
            patch.delenv("DATABASE_URL", raising=False)
        else:
            patch.setenv("DATABASE_URL", url)
        reload_settings()
        model_registry.clear()
        try:
            with mock_patch.object(main_module.logger, "error") as log_error, TestClient(
                create_app()
            ) as client:
                yield client, [str(call.args[-1]) for call in log_error.call_args_list]
        finally:
            with suppress(DatabaseStartupError):  # no engine for a refused URL
                get_engine().dispose()
    model_registry.clear()
    reload_settings()


def _render(url: URL) -> str:
    return url.render_as_string(hide_password=False)


def _scalar(url: URL, statement: str):
    engine = create_engine(url)
    try:
        with engine.connect() as connection:
            return connection.scalar(text(statement))
    finally:
        engine.dispose()


def _assert_refused(client: TestClient, errors: list[str], *phrases: str) -> str:
    assert client.get("/health").status_code == 503
    assert len(errors) == 1, errors
    message = errors[0]
    for phrase in (*phrases, "maintenance mode", "/health will return HTTP 503"):
        assert phrase in message, message
    assert "Traceback" not in message
    return message


def test_a_clean_database_boots_and_restarts(monkeypatch, databases):
    url = seeds.create_empty()
    databases.append(url)
    for _start in range(2):
        with serve(monkeypatch, _render(url)) as (client, errors):
            assert errors == []
            assert client.get("/health").json() == {"status": "ok"}
            assert client.get("/api/v1/model").status_code == 200
            assert client.get("/api/v1/workspaces/default").status_code == 200
        assert _scalar(url, "SELECT version_num FROM alembic_version") == HEAD
        assert _scalar(url, "SELECT count(*) FROM pg_extension WHERE extname = 'pg_trgm'") == 1
        assert _scalar(url, "SELECT count(*) FROM model_releases") == 1


@pytest.mark.parametrize(
    ("configured", "phrases"),
    [
        (None, ("DATABASE_URL is not set", "scripts/postgres.sh start")),
        ("sqlite:///./rdm-engine.db", ("names a sqlite database", "PostgreSQL only", "PG-D10")),
        ("postgresql+psycopg2://rdm@localhost/rdm", ("driver 'postgresql+psycopg2'",)),
    ],
)
def test_a_missing_or_non_postgresql_url_is_refused(monkeypatch, configured, phrases):
    with serve(monkeypatch, configured) as (client, errors):
        _assert_refused(client, errors, *phrases)


def test_the_upgrade_command_prints_the_refusal_and_fails(monkeypatch, capsys):
    monkeypatch.setenv("DATABASE_URL", "sqlite:///./rdm-engine.db")
    reload_settings()
    try:
        assert database_upgrade.main() == 1
    finally:
        monkeypatch.undo()
        reload_settings()
    error = capsys.readouterr().err
    assert "PostgreSQL only" in error and "Traceback" not in error


def test_a_database_with_another_collation_is_refused(monkeypatch, databases):
    url = seeds.create_empty("LOCALE_PROVIDER libc LOCALE 'C'")
    databases.append(url)
    with serve(monkeypatch, _render(url)) as (client, errors):
        _assert_refused(
            client, errors, "default collation libc 'C'", "ICU root collation 'und'", "CREATE DATABASE"
        )
    assert _scalar(url, "SELECT count(*) FROM pg_tables WHERE schemaname = 'public'") == 0


def test_an_unknown_revision_is_refused_and_left_as_it_is(monkeypatch, databases):
    url = seeds.clone("schema")
    databases.append(url)
    engine = create_engine(url)
    with engine.begin() as connection:
        connection.execute(text("UPDATE alembic_version SET version_num = '20991231_01'"))
    engine.dispose()
    with serve(monkeypatch, _render(url)) as (client, errors):
        _assert_refused(
            client,
            errors,
            "schema revision '20991231_01'",
            f"its newest is '{HEAD}'",
            "Do not edit or stamp the schema manually",
        )
    assert _scalar(url, "SELECT version_num FROM alembic_version") == "20991231_01"


def test_a_missing_pg_trgm_the_role_cannot_create_is_refused(monkeypatch, databases):
    url = seeds.create_empty()
    databases.append(url)
    with seeds.admin() as server:
        if not server.scalar(text(f"SELECT 1 FROM pg_roles WHERE rolname = '{LIMITED_ROLE}'")):
            server.execute(text(f"CREATE ROLE {LIMITED_ROLE} LOGIN"))
    # The role may create tables, but not extensions (which needs CREATE on the database).
    engine = create_engine(url, isolation_level="AUTOCOMMIT")
    with engine.connect() as connection:
        connection.execute(text(f"GRANT CREATE ON SCHEMA public TO {LIMITED_ROLE}"))
    engine.dispose()
    limited = url.set(username=LIMITED_ROLE)
    with serve(monkeypatch, _render(limited)) as (client, errors):
        _assert_refused(
            client, errors, "lacks the pg_trgm extension", "CREATE EXTENSION pg_trgm;", "permission"
        )
    assert _scalar(url, "SELECT count(*) FROM pg_tables WHERE schemaname = 'public'") == 0
    with seeds.admin() as server:
        server.execute(text(f'REVOKE ALL ON DATABASE "{url.database}" FROM {LIMITED_ROLE}'))


def test_a_failed_migration_rolls_back_and_the_next_start_recovers(monkeypatch, databases):
    url = seeds.create_empty()
    databases.append(url)
    # The last table the baseline creates, there already: the baseline fails part-way through.
    engine = create_engine(url)
    with engine.begin() as connection:
        connection.execute(text("CREATE TABLE relation_set_versions (stray integer)"))
    with serve(monkeypatch, _render(url)) as (client, errors):
        message = _assert_refused(
            client,
            errors,
            "Database migration failed",
            "Current revision: unversioned",
            f"target revision: {HEAD}",
            "still at its current revision",
            "python -m app.cli.database_upgrade",
            "do not edit or stamp the schema manually",
        )
        assert "relation_set_versions" in message
    # Nothing the run created before the failure remains.
    assert set(inspect(engine).get_table_names()) == {"relation_set_versions"}
    with engine.begin() as connection:
        connection.execute(text("DROP TABLE relation_set_versions"))
    engine.dispose()
    with serve(monkeypatch, _render(url)) as (client, errors):
        assert errors == []
        assert client.get("/health").json() == {"status": "ok"}
    assert _scalar(url, "SELECT version_num FROM alembic_version") == HEAD
