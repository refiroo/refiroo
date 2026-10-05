"""Startup on PostgreSQL (0.9.0-alpha.1, PG1): the lifespan against real databases.

A clean database is checked, migrated to the baseline and bootstrapped, and starts again unchanged.
Every refusal (no or a non-PostgreSQL ``DATABASE_URL``, another collation, an unknown revision, a
missing ``pg_trgm`` or ``btree_gin``) leaves the service in maintenance mode (``/health`` 503) and logs one message
saying what failed and what to do, never a traceback. A migration that fails part-way rolls back
completely, and the next start after the cause is removed succeeds. PG2's revision (the trigram
search indexes) upgrades a database at the baseline, and its interrupted run rolls back to it.
"""

from collections.abc import Iterator
from contextlib import contextmanager, suppress
from unittest.mock import patch as mock_patch

import pytest
import seeds
from alembic import command
from fastapi.testclient import TestClient
from sqlalchemy import URL, create_engine, inspect, text

import app.main as main_module
from app.cli import database_upgrade
from app.config import reload_settings
from app.db import DatabaseStartupError, get_engine, migration_config
from app.engine.model.registry import model_registry
from app.main import create_app

HEAD = "20261005_02"
DECIMAL_ENCODING = "20261004_02"
FEED_POSITIONS = "20261003_02"
SEARCH_INDEXES = "20261003_01"
BASELINE = "20261001_01"
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
        assert _scalar(url, "SELECT count(*) FROM pg_extension WHERE extname IN ('pg_trgm', 'btree_gin')") == 2
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
            "lacks the pg_trgm and btree_gin extensions",
            "CREATE EXTENSION pg_trgm; CREATE EXTENSION btree_gin;",
            "permission",
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


def _search_indexes(url: URL) -> set[str]:
    engine = create_engine(url)
    try:
        return {
            index["name"]
            for table in ("attribute_values", "snapshot_attribute_values")
            for index in inspect(engine).get_indexes(table)
            if index["name"].endswith("_text_search")
        }
    finally:
        engine.dispose()


def test_a_baseline_database_upgrades_to_the_trigram_search_indexes(monkeypatch, databases):
    """PG2's revision on a database at the baseline: started once, upgraded, and started again."""
    url = seeds.create_empty()
    databases.append(url)
    command.upgrade(migration_config(url), BASELINE)
    assert _search_indexes(url) == set()
    for _start in range(2):
        with serve(monkeypatch, _render(url)) as (client, errors):
            assert errors == []
            assert client.get("/health").json() == {"status": "ok"}
        assert _scalar(url, "SELECT version_num FROM alembic_version") == HEAD
        assert _search_indexes(url) == {
            "ix_attribute_values_text_search",
            "ix_snapshot_attribute_values_text_search",
        }


def test_an_interrupted_search_index_revision_rolls_back_and_the_next_start_recovers(
    monkeypatch, databases
):
    url = seeds.create_empty()
    databases.append(url)
    command.upgrade(migration_config(url), BASELINE)
    # The second index's name already taken: the revision fails after creating the first.
    engine = create_engine(url)
    with engine.begin() as connection:
        connection.execute(
            text(
                "CREATE INDEX ix_snapshot_attribute_values_text_search "
                "ON snapshot_attribute_values (owner_id)"
            )
        )
    with serve(monkeypatch, _render(url)) as (client, errors):
        message = _assert_refused(
            client,
            errors,
            "Database migration failed",
            f"Current revision: {BASELINE}",
            f"target revision: {HEAD}",
            "still at its current revision",
        )
        assert "ix_snapshot_attribute_values_text_search" in message
    assert _scalar(url, "SELECT version_num FROM alembic_version") == BASELINE
    assert _search_indexes(url) == {"ix_snapshot_attribute_values_text_search"}
    with engine.begin() as connection:
        connection.execute(text("DROP INDEX ix_snapshot_attribute_values_text_search"))
    engine.dispose()
    with serve(monkeypatch, _render(url)) as (client, errors):
        assert errors == []
        assert client.get("/health").json() == {"status": "ok"}
    assert _scalar(url, "SELECT version_num FROM alembic_version") == HEAD


def test_a_database_with_audit_history_upgrades_to_feed_positions(monkeypatch, databases):
    """Base 0.9 F1 on a database at the previous revision with audit history (written here as an
    older release left it): the history keeps no position, the feed starts empty, and the next
    write takes position 1. Started twice."""
    url = seeds.create_empty()
    databases.append(url)
    command.upgrade(migration_config(url), SEARCH_INDEXES)
    engine = create_engine(url)
    with engine.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO audit_events (event_id, aggregate_type, aggregate_id, action, version, "
                "changes, occurred_at) VALUES (gen_random_uuid()::text, 'object', 'earlier', "
                "'created', 1, '{}', now())"
            )
        )
    engine.dispose()
    with serve(monkeypatch, _render(url)) as (client, errors):
        assert errors == []
        assert client.get("/health").json() == {"status": "ok"}
        empty = client.get("/api/v1/workspaces/default/feed").json()
        assert (empty["items"], empty["headPosition"]) == ([], 0)
        written = client.post(
            "/api/v1/objects",
            json={
                "workspaceKey": "default",
                "applicationKey": "rdm-master",
                "objectTypeKey": "domain",
                "name": "After the upgrade",
                "attributes": [{"attributeTypeKey": "domain-code", "value": "UPGRADED"}],
            },
        )
        assert written.status_code == 201, written.text
    with serve(monkeypatch, _render(url)) as (client, errors):
        assert errors == []
        entries = client.get("/api/v1/workspaces/default/feed").json()["items"]
        assert [(e["position"], e["id"]) for e in entries] == [(1, written.json()["id"])]
    assert _scalar(url, "SELECT version_num FROM alembic_version") == HEAD
    assert _scalar(url, "SELECT feed_position FROM audit_events WHERE aggregate_id = 'earlier'") is None


def test_an_interrupted_feed_position_revision_rolls_back_and_the_next_start_recovers(
    monkeypatch, databases
):
    url = seeds.create_empty()
    databases.append(url)
    command.upgrade(migration_config(url), SEARCH_INDEXES)
    # The revision's last column already there: it fails after adding the others.
    engine = create_engine(url)
    with engine.begin() as connection:
        connection.execute(text("ALTER TABLE publications ADD COLUMN feed_position integer"))
    with serve(monkeypatch, _render(url)) as (client, errors):
        message = _assert_refused(
            client,
            errors,
            "Database migration failed",
            f"Current revision: {SEARCH_INDEXES}",
            f"target revision: {HEAD}",
            "still at its current revision",
        )
        assert "feed_position" in message
    assert _scalar(url, "SELECT version_num FROM alembic_version") == SEARCH_INDEXES
    assert "feed_position" not in {c["name"] for c in inspect(engine).get_columns("workspaces")}
    with engine.begin() as connection:
        connection.execute(text("ALTER TABLE publications DROP COLUMN feed_position"))
    engine.dispose()
    with serve(monkeypatch, _render(url)) as (client, errors):
        assert errors == []
        assert client.get("/health").json() == {"status": "ok"}
    assert _scalar(url, "SELECT version_num FROM alembic_version") == HEAD


def _feed_time_index(url: URL) -> bool:
    return bool(
        _scalar(url, "SELECT count(*) FROM pg_indexes WHERE indexname = 'ix_audit_events_feed_time'")
    )


def test_a_database_with_a_feed_upgrades_to_feed_retention(monkeypatch, databases):
    """Base 0.9 F2 on a database at the previous revision whose feed has an entry: the upgrade adds
    the retention index, the entry is still answered with nothing expired, and the next write takes
    the next position. Started twice."""
    url = seeds.create_empty()
    databases.append(url)
    # A started service (its default workspace), then taken back to the previous revision.
    with serve(monkeypatch, _render(url)) as (client, errors):
        assert errors == []
    command.downgrade(migration_config(url), FEED_POSITIONS)
    assert not _feed_time_index(url)
    engine = create_engine(url)
    with engine.begin() as connection:
        connection.execute(text("UPDATE workspaces SET feed_position = 1 WHERE key = 'default'"))
        connection.execute(
            text(
                "INSERT INTO audit_events (event_id, aggregate_type, aggregate_id, action, version, "
                "changes, occurred_at, workspace_key, feed_position) VALUES "
                "(gen_random_uuid()::text, 'object', 'earlier', 'created', 1, '{}', "
                "now() - interval '400 days', 'default', 1)"
            )
        )
    engine.dispose()
    with serve(monkeypatch, _render(url)) as (client, errors):
        assert errors == []
        page = client.get("/api/v1/workspaces/default/feed").json()
        assert [e["position"] for e in page["items"]] == [1]
        assert (page["headPosition"], page["earliestPosition"]) == (1, 1)
    with serve(monkeypatch, _render(url)) as (client, errors):
        assert errors == []
        assert client.get("/health").json() == {"status": "ok"}
    assert _scalar(url, "SELECT version_num FROM alembic_version") == HEAD
    assert _feed_time_index(url)


def test_an_interrupted_feed_retention_revision_rolls_back_and_the_next_start_recovers(
    monkeypatch, databases
):
    url = seeds.create_empty()
    databases.append(url)
    command.upgrade(migration_config(url), FEED_POSITIONS)
    # The index's name already taken: the revision fails.
    engine = create_engine(url)
    with engine.begin() as connection:
        connection.execute(text("CREATE INDEX ix_audit_events_feed_time ON audit_events (action)"))
    with serve(monkeypatch, _render(url)) as (client, errors):
        message = _assert_refused(
            client,
            errors,
            "Database migration failed",
            f"Current revision: {FEED_POSITIONS}",
            f"target revision: {HEAD}",
            "still at its current revision",
        )
        assert "ix_audit_events_feed_time" in message
    assert _scalar(url, "SELECT version_num FROM alembic_version") == FEED_POSITIONS
    with engine.begin() as connection:
        connection.execute(text("DROP INDEX ix_audit_events_feed_time"))
    engine.dispose()
    with serve(monkeypatch, _render(url)) as (client, errors):
        assert errors == []
        assert client.get("/health").json() == {"status": "ok"}
    assert _scalar(url, "SELECT version_num FROM alembic_version") == HEAD
    assert _feed_time_index(url)


def test_stored_job_codes_follow_the_upper_case_revision_both_ways(monkeypatch, databases):
    """Base 0.9 T1b (D43): an atomic batch with a refused item stores a code and a reason. Taken back
    to the previous revision they read lower case, as that release wrote them; upgraded again, the
    job answers them upper case, as a new job does."""
    url = seeds.create_empty()
    databases.append(url)
    domain = {"op": "create", "applicationKey": "rdm-master", "objectTypeKey": "domain"}
    items = [
        {**domain, "name": "Kept", "attributes": [{"attributeTypeKey": "domain-code", "value": "K"}]},
        {**domain, "name": "Refused", "objectTypeKey": "no-such-type"},
    ]
    with serve(monkeypatch, _render(url)) as (client, errors):
        assert errors == []
        response = client.post(
            "/api/v1/batches",
            json={"policy": "atomic", "run": "inline", "workspaceKey": "default", "items": items},
        )
        assert response.status_code == 200, response.text
        job_id = response.json()["job"]["id"]

    def outcomes(client: TestClient) -> list[tuple[str, str]]:
        page = client.get(f"/api/v1/jobs/{job_id}/items").json()["items"]
        return [(item["status"], item.get("reason") or item["error"]["code"]) for item in page]

    command.downgrade(migration_config(url), DECIMAL_ENCODING)
    stored = _scalar(url, "SELECT string_agg(outcome::text, ' ') FROM job_items")
    assert "batch_rolled_back" in stored and "unknown_object_type" in stored
    with serve(monkeypatch, _render(url)) as (client, errors):
        assert errors == []
        assert outcomes(client) == [
            ("unprocessed", "BATCH_ROLLED_BACK"),
            ("rejected", "UNKNOWN_OBJECT_TYPE"),
        ]
    assert _scalar(url, "SELECT version_num FROM alembic_version") == HEAD
