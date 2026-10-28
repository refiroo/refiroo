"""Startup on PostgreSQL (0.9.0-alpha.1, PG1): the lifespan against real databases.

A clean database is checked, migrated to the baseline and bootstrapped, and starts again unchanged.
Every refusal (no or a non-PostgreSQL ``DATABASE_URL``, another collation, an unknown revision, a
missing ``pg_trgm``, ``btree_gin`` or ``pgcrypto``) leaves the service in maintenance mode (``/health`` 503) and logs one message
saying what failed and what to do, never a traceback. Upgrades from older revisions, downgrades and
interrupted migrations are not tested before 1.0: no instance runs an older version (the user,
2026-10-23).
"""

from collections.abc import Iterator
from contextlib import contextmanager, suppress
from unittest.mock import patch as mock_patch

import pytest
import seeds
from harness_identity import TestClient
from sqlalchemy import URL, create_engine, text

import app.main as main_module
from app.cli import database_upgrade
from app.config import reload_settings
from app.db import DatabaseStartupError, get_engine
from app.engine.model.registry import model_registry
from app.main import create_app

HEAD = "20261117_01"
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
    # In maintenance mode a token is not looked up, nor one issued: both answer 503 as every route
    # did before tokens, never an internal error (0.12 I1; the identity tables may not exist yet).
    for response in (
        client.get("/api/v1/workspaces", headers={"Authorization": "Bearer any"}),
        client.post("/oauth/token", data={"grant_type": "client_credentials", "client_id": "a", "client_secret": "b"}),
        # The application's JSON sign-in routes (I5) are guarded the same way (0.12 R).
        client.get("/oauth/sign-in/options"),
        client.post("/oauth/sign-in/password", json={"username": "a", "password": "b"}),
        client.post("/oauth/sign-in/reset-request", json={"username": "a"}),
    ):
        assert response.status_code == 503, response.text
        assert response.json()["error"]["code"] == "MODEL_REGISTRY_UNAVAILABLE"
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
        assert _scalar(url, "SELECT count(*) FROM pg_extension WHERE extname IN ('pg_trgm', 'btree_gin', 'pgcrypto')") == 3
        assert _scalar(url, "SELECT count(*) FROM model_releases") == 1


@pytest.mark.parametrize(
    ("configured", "phrases"),
    [
        (None, ("DATABASE_URL is not set", "scripts/postgres.sh start")),
        ("sqlite:///./rdm-engine.db", ("names a sqlite database", "PostgreSQL only")),
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


def test_missing_extensions_the_role_cannot_create_are_refused(monkeypatch, databases):
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
            client,
            errors,
            "lacks the pg_trgm, btree_gin and pgcrypto extensions",
            "CREATE EXTENSION pg_trgm; CREATE EXTENSION btree_gin; CREATE EXTENSION pgcrypto;",
            "permission",
        )
    assert _scalar(url, "SELECT count(*) FROM pg_tables WHERE schemaname = 'public'") == 0
    with seeds.admin() as server:
        server.execute(text(f'REVOKE ALL ON DATABASE "{url.database}" FROM {LIMITED_ROLE}'))


def test_a_job_file_directory_that_cannot_be_written_refuses_to_start(monkeypatch, tmp_path):
    """Base 0.9 J1 (D55): with job creation on, a ``JOB_FILE_DIR`` that cannot be written refuses
    the application's construction, naming the path and the setting; with job creation off the
    directory is not needed."""
    blocked = tmp_path / "not-a-directory"
    blocked.write_text("a file where the directory should be")
    monkeypatch.setenv("JOB_FILE_DIR", str(blocked / "job-files"))
    try:
        with pytest.raises(RuntimeError, match="JOB_FILE_DIR") as refused:
            create_app()
        assert str(blocked / "job-files") in str(refused.value)
        monkeypatch.setenv("INTEGRATION_JOBS_ENABLED", "false")
        create_app()
    finally:
        monkeypatch.undo()
        reload_settings()


@pytest.mark.parametrize(
    ("key", "message"),
    [
        (None, "SECRETS_ENCRYPTION_KEY is required"),
        ("too-short", "must be 32 bytes written in URL-safe base64"),
    ],
)
def test_without_a_usable_secrets_key_the_application_refuses_to_start(monkeypatch, key, message):
    """0.12 I1 (D253, after Base 0.9 C11's C-D96): a missing or malformed key refuses the
    application's construction with the setting named and the command that generates one."""
    if key is None:
        monkeypatch.delenv("SECRETS_ENCRYPTION_KEY", raising=False)
    else:
        monkeypatch.setenv("SECRETS_ENCRYPTION_KEY", key)
    try:
        with pytest.raises(RuntimeError, match=message) as refused:
            create_app()
        assert "python -m app.cli.generate_key" in str(refused.value)
    finally:
        monkeypatch.undo()
        reload_settings()
