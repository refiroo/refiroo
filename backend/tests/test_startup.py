"""Startup on PostgreSQL (0.9.0-alpha.1, PG1): the lifespan against real databases.

A clean database is checked, migrated to the baseline and bootstrapped, and starts again unchanged.
Every refusal (no or a non-PostgreSQL ``DATABASE_URL``, another collation, an unknown revision, a
missing ``pg_trgm`` or ``btree_gin``) leaves the service in maintenance mode (``/health`` 503) and logs one message
saying what failed and what to do, never a traceback. A migration that fails part-way rolls back
completely, and the next start after the cause is removed succeeds. PG2's revision (the trigram
search indexes) upgrades a database at the baseline, and its interrupted run rolls back to it.
"""

import threading
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

HEAD = "20261007_07"
IMPORT_PROFILES = "20261007_06"
JOB_NOTIFICATIONS = "20261007_05"
EXPORT_OUTPUT = "20261007_04"
DELIVERY_CHOICES = "20261007_03"
RESENDS = "20261007_02"
DELIVERY_LOG = "20261007_01"
DELIVERY_STATE = "20261006_03"
SUBSCRIPTIONS = "20261006_02"
CONSUMER_EVENTS = "20261006_01"
PUBLICATION_READS = "20261005_03"
TYPED_TRIGRAMS = "20261005_02"
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


PUBLICATION_READ_INDEXES = {
    "ix_publication_objects_lower_name",
    "ix_publication_objects_type_name_trigram",
    "ix_snapshot_attribute_values_publication_lower_text",
    *(f"ix_snapshot_attribute_values_publication_key_{name}" for name in ("integer", "decimal", "boolean", "date", "datetime")),
}


def _publication_read_indexes(url: URL) -> set[str]:
    engine = create_engine(url)
    try:
        return {
            index["name"]
            for table in ("publication_objects", "snapshot_attribute_values")
            for index in inspect(engine).get_indexes(table)
            if index["name"] in PUBLICATION_READ_INDEXES
        }
    finally:
        engine.dispose()


def test_an_interrupted_publication_index_revision_rolls_back_and_upgrades_on_the_next_start(
    monkeypatch, databases
):
    """Base 0.9 C6a's revision on a database at the previous one: interrupted after its first
    indexes, it leaves the database where it was; with the cause removed, it upgrades, and the
    service starts twice."""
    url = seeds.create_empty()
    databases.append(url)
    command.upgrade(migration_config(url), TYPED_TRIGRAMS)
    last = "ix_snapshot_attribute_values_publication_key_datetime"
    engine = create_engine(url)
    with engine.begin() as connection:
        connection.execute(text(f"CREATE INDEX {last} ON snapshot_attribute_values (owner_id)"))
    with serve(monkeypatch, _render(url)) as (client, errors):
        message = _assert_refused(
            client,
            errors,
            "Database migration failed",
            f"Current revision: {TYPED_TRIGRAMS}",
            f"target revision: {HEAD}",
            "still at its current revision",
        )
        assert last in message
    assert _scalar(url, "SELECT version_num FROM alembic_version") == TYPED_TRIGRAMS
    assert _publication_read_indexes(url) == {last}
    with engine.begin() as connection:
        connection.execute(text(f"DROP INDEX {last}"))
    engine.dispose()
    for _start in range(2):
        with serve(monkeypatch, _render(url)) as (client, errors):
            assert errors == []
            assert client.get("/health").json() == {"status": "ok"}
        assert _scalar(url, "SELECT version_num FROM alembic_version") == HEAD
        assert _publication_read_indexes(url) == PUBLICATION_READ_INDEXES


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


def _checkpoints(url: URL) -> dict[str, tuple[int, int]]:
    engine = create_engine(url)
    try:
        with engine.connect() as connection:
            rows = connection.execute(
                text("SELECT workspace_key, position, start_position FROM consumer_event_checkpoints")
            )
            return {row.workspace_key: (row.position, row.start_position) for row in rows}
    finally:
        engine.dispose()


def test_a_database_with_a_publication_upgrades_to_consumer_events(monkeypatch, databases):
    """Base 0.9 C10 on a database at the previous revision with a published workspace and one without
    a publication: the upgrade starts the first workspace's derivation at its publication's feed
    position and the second at 0 (C-D92); the service then derives and serves the events, and
    starts twice."""
    url = seeds.create_empty()
    databases.append(url)
    with serve(monkeypatch, _render(url)) as (client, errors):
        assert errors == []
        assert client.post("/api/v1/workspaces", json={"key": "second", "label": "Second"}).status_code == 201
        change_set = client.post(
            "/api/v1/workspaces/default/change-sets", json={"source": "currentLive"}
        ).json()
        published = client.post(
            f"/api/v1/change-sets/{change_set['id']}/publication",
            json={"expectedChangeSetVersion": change_set["version"], "expectedActivePublicationId": None},
        )
        assert published.status_code == 200, published.text
        position = published.json()["feedPosition"]
    command.downgrade(migration_config(url), PUBLICATION_READS)
    assert _scalar(url, "SELECT to_regclass('consumer_events')") is None
    for _start in range(2):
        with serve(monkeypatch, _render(url)) as (client, errors):
            assert errors == []
            assert client.get("/health").json() == {"status": "ok"}
        assert _scalar(url, "SELECT version_num FROM alembic_version") == HEAD
        starts = {key: start for key, (_position, start) in _checkpoints(url).items()}
        assert starts == {"default": position, "second": 0}


def test_an_interrupted_consumer_events_revision_rolls_back_and_the_next_start_recovers(
    monkeypatch, databases
):
    url = seeds.create_empty()
    databases.append(url)
    command.upgrade(migration_config(url), PUBLICATION_READS)
    # The second table's name already taken: the revision fails after creating the first.
    engine = create_engine(url)
    with engine.begin() as connection:
        connection.execute(text("CREATE TABLE consumer_event_checkpoints (taken integer)"))
    with serve(monkeypatch, _render(url)) as (client, errors):
        message = _assert_refused(
            client,
            errors,
            "Database migration failed",
            f"Current revision: {PUBLICATION_READS}",
            f"target revision: {HEAD}",
            "still at its current revision",
        )
        assert "consumer_event_checkpoints" in message
    assert _scalar(url, "SELECT version_num FROM alembic_version") == PUBLICATION_READS
    assert _scalar(url, "SELECT to_regclass('consumer_events')") is None
    with engine.begin() as connection:
        connection.execute(text("DROP TABLE consumer_event_checkpoints"))
    engine.dispose()
    with serve(monkeypatch, _render(url)) as (client, errors):
        assert errors == []
        assert client.get("/health").json() == {"status": "ok"}
    assert _scalar(url, "SELECT version_num FROM alembic_version") == HEAD
    assert _checkpoints(url)["default"][1] == 0


def test_a_database_with_consumer_events_upgrades_to_subscriptions(monkeypatch, databases):
    """Base 0.9 C11 on a database at the previous revision: the upgrade adds the subscriptions table,
    the service starts twice with the capability on, and a workspace with a subscription cannot be
    deleted (the reference restricts)."""
    url = seeds.create_empty()
    databases.append(url)
    command.upgrade(migration_config(url), CONSUMER_EVENTS)
    assert _scalar(url, "SELECT to_regclass('consumer_subscriptions')") is None
    monkeypatch.setenv("CONSUMER_SUBSCRIPTIONS_ENABLED", "true")
    monkeypatch.setenv("CONSUMER_WEBHOOK_KEY_ENCRYPTION_KEY", "a" * 43)
    for _start in range(2):
        with serve(monkeypatch, _render(url)) as (client, errors):
            assert errors == []
            assert client.get("/health").json() == {"status": "ok"}
            listed = client.get("/api/v1/consumer-subscriptions")
            assert listed.status_code == 200 and listed.json()["items"] == []
        assert _scalar(url, "SELECT version_num FROM alembic_version") == HEAD
    command.downgrade(migration_config(url), CONSUMER_EVENTS)
    assert _scalar(url, "SELECT to_regclass('consumer_subscriptions')") is None


def _dispatching() -> bool:
    return any(thread.name == "rdm-webhook-dispatcher" for thread in threading.enumerate())


def test_a_database_with_subscriptions_upgrades_to_delivery_state(monkeypatch, databases):
    """Base 0.9 C12 on a database at the previous revision holding a subscription: the upgrade adds
    the delivery state, the subscription has nothing pending and continues after its acknowledged
    position, and the service starts twice. The dispatcher runs only with the capability on."""
    url = seeds.create_empty()
    databases.append(url)
    with serve(monkeypatch, _render(url)) as (client, errors):
        assert errors == [] and client.app.state.consumer_dispatcher is None and not _dispatching()
    command.downgrade(migration_config(url), SUBSCRIPTIONS)
    engine = create_engine(url)
    with engine.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO consumer_subscriptions (public_id, consumer_api, contract_version, workspace_key, "
                "event_keys, filters, url, mode, payload, status, acknowledged_position, acknowledged_ordinal, "
                "signing_key, signing_key_created_at, version, created_at, updated_at) VALUES "
                "('00000000-0000-4000-8000-000000000001', 'rdm', 1, 'default', '[\"changed\"]', '{}', "
                "'https://hooks.example.test/x', 'perChange', 'full', 'active', 7, 2147483647, '\\x00', "
                "now(), 1, now(), now())"
            )
        )
    engine.dispose()
    monkeypatch.setenv("CONSUMER_SUBSCRIPTIONS_ENABLED", "true")
    monkeypatch.setenv("CONSUMER_WEBHOOK_KEY_ENCRYPTION_KEY", "a" * 43)
    for _start in range(2):
        with serve(monkeypatch, _render(url)) as (client, errors):
            assert errors == []
            assert client.get("/health").json() == {"status": "ok"}
            assert _dispatching()
            (item,) = client.get("/api/v1/consumer-subscriptions").json()["items"]
            assert item["acknowledgedThrough"] == 7
            assert item["delivery"] == {"lastDeliveredAt": None, "pending": None}
        assert _scalar(url, "SELECT version_num FROM alembic_version") == HEAD
        assert _scalar(url, "SELECT attempts FROM consumer_subscriptions") == 0
    command.downgrade(migration_config(url), SUBSCRIPTIONS)
    assert _scalar(url, "SELECT count(*) FROM consumer_subscriptions") == 1


def test_an_interrupted_delivery_state_revision_rolls_back_and_the_next_start_recovers(
    monkeypatch, databases
):
    url = seeds.create_empty()
    databases.append(url)
    command.upgrade(migration_config(url), SUBSCRIPTIONS)
    # The index's name already taken: the revision fails after adding the columns.
    engine = create_engine(url)
    with engine.begin() as connection:
        connection.execute(text("CREATE INDEX ix_consumer_subscriptions_due ON consumer_subscriptions (url)"))
    with serve(monkeypatch, _render(url)) as (client, errors):
        message = _assert_refused(
            client,
            errors,
            "Database migration failed",
            f"Current revision: {SUBSCRIPTIONS}",
            f"target revision: {HEAD}",
            "still at its current revision",
        )
        assert "ix_consumer_subscriptions_due" in message
    assert _scalar(url, "SELECT version_num FROM alembic_version") == SUBSCRIPTIONS
    assert "attempts" not in {c["name"] for c in inspect(engine).get_columns("consumer_subscriptions")}
    with engine.begin() as connection:
        connection.execute(text("DROP INDEX ix_consumer_subscriptions_due"))
    engine.dispose()
    with serve(monkeypatch, _render(url)) as (client, errors):
        assert errors == []
        assert client.get("/health").json() == {"status": "ok"}
    assert _scalar(url, "SELECT version_num FROM alembic_version") == HEAD


def test_a_database_with_subscriptions_upgrades_to_names_and_the_delivery_log(monkeypatch, databases):
    """Base 0.9 U5a on a database at the previous revision holding a subscription: the upgrade
    names it after its URL's host and path, adds the empty delivery log, and the service starts
    twice. A downgrade keeps the subscription."""
    url = seeds.create_empty()
    databases.append(url)
    command.upgrade(migration_config(url), DELIVERY_STATE)
    engine = create_engine(url)
    with engine.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO consumer_subscriptions (public_id, consumer_api, contract_version, workspace_key, "
                "event_keys, filters, url, mode, payload, status, acknowledged_position, acknowledged_ordinal, "
                "signing_key, signing_key_created_at, version, created_at, updated_at) VALUES "
                "('00000000-0000-4000-8000-000000000002', 'rdm', 1, 'default', '[\"changed\"]', '{}', "
                "'https://hooks.example.test/rdm/in/?token=x', 'perChange', 'full', 'active', 3, 2147483647, "
                "'\\x00', now(), 1, now(), now())"
            )
        )
    engine.dispose()
    monkeypatch.setenv("CONSUMER_SUBSCRIPTIONS_ENABLED", "true")
    monkeypatch.setenv("CONSUMER_WEBHOOK_KEY_ENCRYPTION_KEY", "a" * 43)
    for _start in range(2):
        with serve(monkeypatch, _render(url)) as (client, errors):
            assert errors == []
            (item,) = client.get("/api/v1/consumer-subscriptions").json()["items"]
            assert item["name"] == "hooks.example.test/rdm/in"
            deliveries = client.get(f"/api/v1/consumer-subscriptions/{item['id']}/deliveries")
            assert deliveries.status_code == 200 and deliveries.json()["items"] == []
        assert _scalar(url, "SELECT version_num FROM alembic_version") == HEAD
    command.downgrade(migration_config(url), DELIVERY_STATE)
    assert _scalar(url, "SELECT count(*) FROM consumer_subscriptions") == 1
    assert _scalar(url, "SELECT to_regclass('consumer_webhook_requests')") is None


def test_an_interrupted_delivery_log_revision_rolls_back_and_the_next_start_recovers(monkeypatch, databases):
    url = seeds.create_empty()
    databases.append(url)
    command.upgrade(migration_config(url), DELIVERY_STATE)
    # The attempts table's name already taken: the revision fails after naming the subscriptions.
    engine = create_engine(url)
    with engine.begin() as connection:
        connection.execute(text("CREATE TABLE consumer_webhook_attempts (x integer)"))
    with serve(monkeypatch, _render(url)) as (client, errors):
        message = _assert_refused(
            client,
            errors,
            "Database migration failed",
            f"Current revision: {DELIVERY_STATE}",
            f"target revision: {HEAD}",
            "still at its current revision",
        )
        assert "consumer_webhook_attempts" in message
    assert _scalar(url, "SELECT version_num FROM alembic_version") == DELIVERY_STATE
    assert "name" not in {c["name"] for c in inspect(engine).get_columns("consumer_subscriptions")}
    assert _scalar(url, "SELECT to_regclass('consumer_webhook_requests')") is None
    with engine.begin() as connection:
        connection.execute(text("DROP TABLE consumer_webhook_attempts"))
    engine.dispose()
    with serve(monkeypatch, _render(url)) as (client, errors):
        assert errors == []
        assert client.get("/health").json() == {"status": "ok"}
    assert _scalar(url, "SELECT version_num FROM alembic_version") == HEAD


def test_a_delivery_log_upgrades_to_resends_and_an_interrupted_run_recovers(monkeypatch, databases):
    """Base 0.9 U5a revision on a database at the previous revision: the upgrade adds
    ``resend_of`` and the service starts twice; with the column already there (by hand) the revision
    rolls back, the start refuses naming it, and once cleared the next start upgrades."""
    url = seeds.create_empty()
    databases.append(url)
    command.upgrade(migration_config(url), DELIVERY_LOG)
    engine = create_engine(url)
    with engine.begin() as connection:
        connection.execute(text("ALTER TABLE consumer_webhook_requests ADD COLUMN resend_of integer"))
    with serve(monkeypatch, _render(url)) as (client, errors):
        message = _assert_refused(
            client,
            errors,
            "Database migration failed",
            f"Current revision: {DELIVERY_LOG}",
            f"target revision: {HEAD}",
            "still at its current revision",
        )
        assert "resend_of" in message
    assert _scalar(url, "SELECT version_num FROM alembic_version") == DELIVERY_LOG
    with engine.begin() as connection:
        connection.execute(text("ALTER TABLE consumer_webhook_requests DROP COLUMN resend_of"))
    engine.dispose()
    monkeypatch.setenv("CONSUMER_SUBSCRIPTIONS_ENABLED", "true")
    monkeypatch.setenv("CONSUMER_WEBHOOK_KEY_ENCRYPTION_KEY", "a" * 43)
    for _start in range(2):
        with serve(monkeypatch, _render(url)) as (client, errors):
            assert errors == []
            assert client.get("/health").json() == {"status": "ok"}
        assert _scalar(url, "SELECT version_num FROM alembic_version") == HEAD
    assert "resend_of" in {c["name"] for c in inspect(create_engine(url)).get_columns("consumer_webhook_requests")}
    command.downgrade(migration_config(url), DELIVERY_LOG)
    assert _scalar(url, "SELECT version_num FROM alembic_version") == DELIVERY_LOG


def test_subscriptions_upgrade_to_the_delivery_choices_and_an_interrupted_run_recovers(monkeypatch, databases):
    """Base 0.9 C17 on a database at the previous revision holding a coalesced subscription, a
    logged notice and a logged events request: with ``format`` already there (by hand) the revision
    rolls back and the start refuses naming it; once cleared, the next start upgrades, the
    subscription reads back with the defaults (one event per request, RDM JSON, its payload kept),
    the notice is gone and the events request kept, and the service starts twice. A downgrade keeps
    the subscription."""
    url = seeds.create_empty()
    databases.append(url)
    command.upgrade(migration_config(url), RESENDS)
    engine = create_engine(url)
    with engine.begin() as connection:
        subscription = connection.scalar(
            text(
                "INSERT INTO consumer_subscriptions (public_id, name, consumer_api, contract_version, workspace_key, "
                "event_keys, filters, url, mode, debounce_seconds, payload, status, acknowledged_position, "
                "acknowledged_ordinal, signing_key, signing_key_created_at, version, created_at, updated_at) VALUES "
                "('00000000-0000-4000-8000-000000000003', 'Export', 'rdm', 1, 'default', '[\"changed\"]', '{}', "
                "'https://hooks.example.test/x', 'coalesced', 60, 'identity', 'active', 3, 2147483647, '\\x00', "
                "now(), 1, now(), now()) RETURNING sequence_id"
            )
        )
        for delivery_id, kind, event_id in (("n1", "notice", None), ("e1", "events", "ev1")):
            request = connection.scalar(
                text(
                    "INSERT INTO consumer_webhook_requests (subscription_sequence_id, delivery_id, batch_id, kind, "
                    "status, attempts, created_at) VALUES (:s, :d, :d, :k, 'succeeded', 1, now()) "
                    "RETURNING sequence_id"
                ),
                {"s": subscription, "d": delivery_id, "k": kind},
            )
            connection.execute(
                text(
                    "INSERT INTO consumer_webhook_request_events (request_sequence_id, ordinal, event_id, "
                    "event_key, change, object_type, object_id, position) VALUES (:r, 0, :e, 'changed', "
                    ":c, :t, :o, 3)"
                ),
                {
                    "r": request,
                    "e": event_id,
                    "c": event_id and "updated",
                    "t": event_id and "Ledger",
                    "o": event_id and "o1",
                },
            )
        connection.execute(text("ALTER TABLE consumer_subscriptions ADD COLUMN format integer"))
    with serve(monkeypatch, _render(url)) as (client, errors):
        message = _assert_refused(
            client,
            errors,
            "Database migration failed",
            f"Current revision: {RESENDS}",
            f"target revision: {HEAD}",
            "still at its current revision",
        )
        assert "format" in message
    assert _scalar(url, "SELECT version_num FROM alembic_version") == RESENDS
    assert "mode" in {c["name"] for c in inspect(engine).get_columns("consumer_subscriptions")}
    with engine.begin() as connection:
        connection.execute(text("ALTER TABLE consumer_subscriptions DROP COLUMN format"))
    engine.dispose()
    monkeypatch.setenv("CONSUMER_SUBSCRIPTIONS_ENABLED", "true")
    monkeypatch.setenv("CONSUMER_WEBHOOK_KEY_ENCRYPTION_KEY", "a" * 43)
    for _start in range(2):
        with serve(monkeypatch, _render(url)) as (client, errors):
            assert errors == []
            (item,) = client.get("/api/v1/consumer-subscriptions").json()["items"]
            assert (item["maxEventsPerBatch"], item["payload"], item["format"]) == (1, "identity", "rdm")
            assert "mode" not in item and "debounceSeconds" not in item
            rows = client.get(f"/api/v1/consumer-subscriptions/{item['id']}/deliveries").json()["items"]
            assert [(row["deliveryId"], row["eventId"]) for row in rows] == [("e1", "ev1")]
        assert _scalar(url, "SELECT version_num FROM alembic_version") == HEAD
    command.downgrade(migration_config(url), RESENDS)
    assert _scalar(url, "SELECT mode FROM consumer_subscriptions") == "perChange"
    assert _scalar(url, "SELECT kind FROM consumer_webhook_requests") == "events"


def test_jobs_upgrade_to_export_output_and_an_interrupted_run_recovers(monkeypatch, databases):
    """Base 0.9 J1 on a database at the previous revision: with ``jobs.output`` already there (by
    hand) the revision rolls back and the start refuses naming it; once cleared, the next start
    adds the column and the service starts twice. A downgrade removes it again."""
    url = seeds.create_empty()
    databases.append(url)
    command.upgrade(migration_config(url), DELIVERY_CHOICES)
    engine = create_engine(url)
    with engine.begin() as connection:
        connection.execute(text("ALTER TABLE jobs ADD COLUMN output integer"))
    with serve(monkeypatch, _render(url)) as (client, errors):
        message = _assert_refused(
            client,
            errors,
            "Database migration failed",
            f"Current revision: {DELIVERY_CHOICES}",
            f"target revision: {HEAD}",
            "still at its current revision",
        )
        assert "output" in message
    assert _scalar(url, "SELECT version_num FROM alembic_version") == DELIVERY_CHOICES
    with engine.begin() as connection:
        connection.execute(text("ALTER TABLE jobs DROP COLUMN output"))
    engine.dispose()
    for _start in range(2):
        with serve(monkeypatch, _render(url)) as (client, errors):
            assert errors == []
            assert client.get("/health").json() == {"status": "ok"}
        assert _scalar(url, "SELECT version_num FROM alembic_version") == HEAD
    assert "output" in _job_columns(url)
    command.downgrade(migration_config(url), DELIVERY_CHOICES)
    assert "output" not in _job_columns(url)


def _job_columns(url: URL) -> set[str]:
    engine = create_engine(url)
    try:
        return {column["name"] for column in inspect(engine).get_columns("jobs")}
    finally:
        engine.dispose()


def test_jobs_upgrade_to_notifications_and_an_interrupted_run_recovers(monkeypatch, databases):
    """Base 0.9 J1u on a database at the previous revision: with the trigger function already there
    (by hand) the revision rolls back and the start refuses naming it; once cleared, the next start
    adds the trigger and the service starts twice (J24.7's tests show a committed change reaching
    a stream). A downgrade removes the trigger."""
    url = seeds.create_empty()
    databases.append(url)
    command.upgrade(migration_config(url), EXPORT_OUTPUT)
    engine = create_engine(url)
    with engine.begin() as connection:
        connection.execute(text("CREATE FUNCTION rdm_notify_job() RETURNS integer LANGUAGE sql AS 'SELECT 1'"))
    with serve(monkeypatch, _render(url)) as (client, errors):
        message = _assert_refused(
            client,
            errors,
            "Database migration failed",
            f"Current revision: {EXPORT_OUTPUT}",
            f"target revision: {HEAD}",
            "still at its current revision",
        )
        assert "rdm_notify_job" in message
    assert _scalar(url, "SELECT version_num FROM alembic_version") == EXPORT_OUTPUT
    with engine.begin() as connection:
        connection.execute(text("DROP FUNCTION rdm_notify_job()"))
    for _start in range(2):
        with serve(monkeypatch, _render(url)) as (client, errors):
            assert errors == []
            assert client.get("/health").json() == {"status": "ok"}
        assert _scalar(url, "SELECT version_num FROM alembic_version") == HEAD
    assert _scalar(url, "SELECT count(*) FROM pg_trigger WHERE tgname = 'jobs_notify'") == 1
    command.downgrade(migration_config(url), EXPORT_OUTPUT)
    assert _scalar(url, "SELECT count(*) FROM pg_trigger WHERE tgname = 'jobs_notify'") == 0
    engine.dispose()


def test_jobs_upgrade_to_import_profiles_and_an_interrupted_run_recovers(monkeypatch, databases):
    """Base 0.9 J2 on a database at the previous revision: with an ``import_profiles`` table already
    there (by hand) the revision rolls back and the start refuses naming it; once dropped, the next
    start creates the table and the service starts twice. A downgrade removes it again."""
    url = seeds.create_empty()
    databases.append(url)
    command.upgrade(migration_config(url), JOB_NOTIFICATIONS)
    engine = create_engine(url)
    with engine.begin() as connection:
        connection.execute(text("CREATE TABLE import_profiles (stray integer)"))
    with serve(monkeypatch, _render(url)) as (client, errors):
        message = _assert_refused(
            client,
            errors,
            "Database migration failed",
            f"Current revision: {JOB_NOTIFICATIONS}",
            f"target revision: {HEAD}",
            "still at its current revision",
        )
        assert "import_profiles" in message
    assert _scalar(url, "SELECT version_num FROM alembic_version") == JOB_NOTIFICATIONS
    with engine.begin() as connection:
        connection.execute(text("DROP TABLE import_profiles"))
    for _start in range(2):
        with serve(monkeypatch, _render(url)) as (client, errors):
            assert errors == []
            assert client.get("/health").json() == {"status": "ok"}
        assert _scalar(url, "SELECT version_num FROM alembic_version") == HEAD
    assert _scalar(url, "SELECT count(*) FROM import_profiles") == 0
    command.downgrade(migration_config(url), JOB_NOTIFICATIONS)
    assert _scalar(url, "SELECT to_regclass('import_profiles') IS NULL") is True
    engine.dispose()


def test_upgrade_to_unique_values_fills_them_and_an_interrupted_run_recovers(
    monkeypatch, databases
):
    """Base 0.9 J2a on a database with records, taken back to the previous revision: with a
    ``unique_attribute_values`` table already there (by hand) the revision rolls back and the start
    refuses naming it; once dropped, the next start creates the table filled with the stored unique
    values and the service starts twice. A downgrade removes the table and its functions."""
    url = seeds.create_empty()
    databases.append(url)
    with serve(monkeypatch, _render(url)) as (client, errors):
        assert errors == []
        for code in ("UPGRADE-1", "UPGRADE-2", "UPGRADE-3"):
            body = {
                "applicationKey": "rdm-master",
                "objectTypeKey": "domain",
                "name": f"Domain {code}",
                "workspaceKey": "default",
                "attributes": [{"attributeTypeKey": "domain-code", "value": code}],
            }
            assert client.post("/api/v1/objects", json=body).status_code == 201
    held = _scalar(url, "SELECT count(*) FROM unique_attribute_values")
    assert held >= 3
    command.downgrade(migration_config(url), IMPORT_PROFILES)
    engine = create_engine(url)
    with engine.begin() as connection:
        connection.execute(text("CREATE TABLE unique_attribute_values (stray integer)"))
    with serve(monkeypatch, _render(url)) as (client, errors):
        message = _assert_refused(
            client,
            errors,
            "Database migration failed",
            f"Current revision: {IMPORT_PROFILES}",
            f"target revision: {HEAD}",
            "still at its current revision",
        )
        assert "unique_attribute_values" in message
    assert _scalar(url, "SELECT version_num FROM alembic_version") == IMPORT_PROFILES
    with engine.begin() as connection:
        connection.execute(text("DROP TABLE unique_attribute_values"))
    for _start in range(2):
        with serve(monkeypatch, _render(url)) as (client, errors):
            assert errors == []
            assert client.get("/health").json() == {"status": "ok"}
        assert _scalar(url, "SELECT version_num FROM alembic_version") == HEAD
    assert _scalar(url, "SELECT count(*) FROM unique_attribute_values") == held
    command.downgrade(migration_config(url), IMPORT_PROFILES)
    assert _scalar(url, "SELECT to_regclass('unique_attribute_values') IS NULL") is True
    assert _scalar(url, "SELECT count(*) FROM pg_proc WHERE proname LIKE 'rdm_unique_values%'") == 0
    engine.dispose()


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
        (None, "requires CONSUMER_WEBHOOK_KEY_ENCRYPTION_KEY"),
        ("too-short", "must be 32 bytes written in URL-safe base64"),
    ],
)
def test_subscriptions_without_a_usable_encryption_key_refuse_to_start(monkeypatch, key, message):
    """Base 0.9 C11 (C-D96): with the capability on, a missing or malformed key refuses the
    application's construction with the setting named and the command that generates one."""
    monkeypatch.setenv("CONSUMER_SUBSCRIPTIONS_ENABLED", "true")
    if key is None:
        monkeypatch.delenv("CONSUMER_WEBHOOK_KEY_ENCRYPTION_KEY", raising=False)
    else:
        monkeypatch.setenv("CONSUMER_WEBHOOK_KEY_ENCRYPTION_KEY", key)
    try:
        with pytest.raises(RuntimeError, match=message) as refused:
            create_app()
        assert "python -m app.cli.generate_key" in str(refused.value)
    finally:
        monkeypatch.undo()
        reload_settings()
