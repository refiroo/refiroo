"""J12 — Run the service, and recover from an expected refusal (USER_JOURNEYS.md).

The operator's channel: the service started with settings on a database (``service.serve``), its log,
its commands run as processes, and ``/health``. A refusal is one concise message saying what failed,
the service state and the safe next step, never a traceback. J12.9 (carrying a SQLite database over)
was dropped with PG4 (2026-10-03).
"""

import json
import time
from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor

import pytest
import seeds
from alembic.script import ScriptDirectory
from harness_identity import TestClient
from scenario import W1, ok, scenario_seed
from service import command, execute, scalar, serve
from sqlalchemy.exc import TimeoutError as SQLAlchemyTimeout
from test_j24_background_job import _unreachable

from app.db import migration_config

HEAD = ScriptDirectory.from_config(migration_config()).get_current_head()
LIMITED_ROLE = "rdm_journey_limited"
SECRET = "s3cret-pass"


@pytest.fixture
def databases() -> Iterator[list]:
    """Databases a test creates, dropped when it ends."""
    created: list = []
    yield created
    for url in created:
        seeds.drop(url.database)


def _empty(databases, options=""):
    url = seeds.create_empty(options)
    databases.append(url)
    return url


def _clone(databases, seed="schema"):
    url = seeds.clone(seed)
    databases.append(url)
    return url


MAINTENANCE = ("maintenance mode", "/health will return HTTP 503")


def _refusal(service, *phrases, state=MAINTENANCE):
    """The one message a refused start logs, after checking it names ``phrases``, the service's
    ``state`` and no traceback, and that ``/health`` answers 503."""
    assert service.health() == 503
    [record] = service.errors()
    message = record.getMessage()
    for phrase in (*phrases, *state):
        assert phrase in message, message
    assert record.exc_info is None and "Traceback" not in message
    return message


def _serves(service):
    assert service.errors() == []
    assert service.client.get("/health").json() == {"status": "ok"}


@pytest.mark.journey("J12")
def test_start_on_a_fresh_database_and_serve(configuration, databases):
    """Given an empty database with the right collation. When the service starts on it, and again.
    Then it migrates to the latest revision, installs the configured model and serves; the second
    start migrates nothing and serves."""
    url = _empty(databases)
    with serve(configuration, url) as service:
        _serves(service)
        ok(service.world.api.get("/capabilities"))
        model = service.world.api.get("/model")
        assert ok(model)["release"] == configuration.model["release"]
        logged = [r.getMessage() for r in service.output.records]
    assert scalar(url, "SELECT version_num FROM alembic_version") == HEAD
    releases = scalar(url, "SELECT count(*) FROM model_releases")
    with serve(configuration, url) as service:
        _serves(service)
        again = [r.getMessage() for r in service.output.records]
    assert scalar(url, "SELECT version_num FROM alembic_version") == HEAD
    assert scalar(url, "SELECT count(*) FROM model_releases") == releases == 1
    assert len(again) <= len(logged)


@pytest.mark.journey("J12.1")
@pytest.mark.parametrize(
    ("configured", "phrases"),
    [
        (None, ("DATABASE_URL is not set",)),
        (
            f"sqlite:///./rdm-{SECRET}.db",
            ("DATABASE_URL names a sqlite database", "PostgreSQL only"),
        ),
        (f"postgresql+psycopg2://rdm:{SECRET}@localhost/rdm", ("DATABASE_URL uses the driver",)),
        (f"postgresql+psycopg://rdm:{SECRET}@localhost:1/rdm", ("cannot connect", "DATABASE_URL")),
    ],
    ids=["unset", "sqlite", "other-driver", "unreachable"],
)
def test_no_or_a_wrong_database_url_is_refused(configuration, databases, configured, phrases):
    """When the service starts without a database URL, with a SQLite URL, with another driver, or
    with an unreachable server. Then each refuses to serve with a message naming DATABASE_URL and
    what is wrong, never the password; with a correct URL the next start serves."""
    with serve(configuration, configured) as service:
        message = _refusal(service, *phrases)
        assert "s3cret-pass@" not in message and f":{SECRET}" not in message
    with serve(configuration, _clone(databases)) as service:
        _serves(service)


@pytest.mark.journey("J12.2")
def test_the_wrong_collation_is_refused(configuration, databases):
    """When the service starts on a database with another collation. Then it refuses, naming the ICU
    root collation and how to create such a database, and creates nothing; on a correct database
    it serves."""
    url = _empty(databases, "LOCALE_PROVIDER libc LOCALE 'C'")
    with serve(configuration, url) as service:
        _refusal(service, "ICU root collation 'und'", "CREATE DATABASE")
    assert scalar(url, "SELECT count(*) FROM pg_tables WHERE schemaname = 'public'") == 0
    with serve(configuration, _empty(databases)) as service:
        _serves(service)


@pytest.mark.journey("J12.3")
def test_an_unknown_revision_is_refused_and_left_untouched(configuration, databases):
    """When the service starts on a database stamped with a revision it does not know. Then it
    refuses, naming the database's revision, its own newest and the next step (the version that wrote
    it, or the backup), and the database is left as it was."""
    url = _clone(databases)
    execute(url, "UPDATE alembic_version SET version_num = '20991231_01'")
    with serve(configuration, url) as service:
        _refusal(
            service,
            "'20991231_01'",
            f"'{HEAD}'",
            "restore the backup",
            "Do not edit or stamp the schema manually",
        )
    assert scalar(url, "SELECT version_num FROM alembic_version") == "20991231_01"


@pytest.mark.journey("J12.4")
def test_missing_extensions_are_refused_until_they_are_installed(configuration, databases):
    """When the service starts where pg_trgm, btree_gin and pgcrypto (0.11 X2, D120) are missing and
    its role cannot create them. Then it refuses with the instruction to install them; once an
    administrator has installed them, the next start serves."""
    url = _empty(databases)
    with seeds.admin() as server:
        server.exec_driver_sql(
            f"DO $$ BEGIN CREATE ROLE {LIMITED_ROLE} LOGIN; "
            "EXCEPTION WHEN duplicate_object THEN NULL; END $$"
        )
    execute(url, f"GRANT CREATE ON SCHEMA public TO {LIMITED_ROLE}")
    limited = url.set(username=LIMITED_ROLE)
    try:
        with serve(configuration, limited) as service:
            _refusal(
                service,
                "lacks the pg_trgm, btree_gin and pgcrypto extensions",
                "CREATE EXTENSION pg_trgm; CREATE EXTENSION btree_gin; CREATE EXTENSION pgcrypto;",
            )
        execute(url, "CREATE EXTENSION pg_trgm")
        execute(url, "CREATE EXTENSION btree_gin")
        execute(url, "CREATE EXTENSION pgcrypto")
        with serve(configuration, limited) as service:
            _serves(service)
    finally:
        with seeds.admin() as server:
            server.exec_driver_sql(f'REVOKE ALL ON DATABASE "{url.database}" FROM {LIMITED_ROLE}')
        execute(url, f"REASSIGN OWNED BY {LIMITED_ROLE} TO CURRENT_USER")
        execute(url, f"DROP OWNED BY {LIMITED_ROLE}")


def _stale_bootstrap_release(configuration, url):
    """The configuration's model as an earlier engine stored it: the release the service installs
    keeps its key and version but is of schema 0.9, with other content."""
    release = configuration.model["release"]
    stale = {**configuration.model, "schemaVersion": "0.9"}
    execute(
        url,
        "UPDATE model_releases SET schema_version = '0.9', model_json = CAST(:model AS json), "
        "model_hash = 'stale-hash' WHERE release_key = :key AND release_version = :version",
        model=json.dumps(stale),
        key=release["key"],
        version=release["version"],
    )
    return release


@pytest.mark.journey("J12.6")
def test_a_stored_release_of_a_left_window_schema_is_raised_offline(configuration, databases):
    """Given a database whose bootstrap model's release is stored in schema 0.9 with other content,
    and workspaces running it. When the service starts; the raise command runs as a dry run and then
    for real; and the service restarts. Then the start serves, logs one error naming the command and
    no traceback, and the workspaces answer 503; the dry run changes nothing; the command rewrites the
    release to the window's schema; the restart logs no error and serves the workspaces."""
    url = _clone(databases, scenario_seed(configuration))
    release = _stale_bootstrap_release(configuration, url)
    schema = "SELECT schema_version FROM model_releases WHERE release_key = :key"
    with serve(configuration, url) as service:
        assert service.client.get("/health").status_code in (200, 503)
        [record] = service.errors()
        message = record.getMessage()
        assert "app.cli.model_release_raise" in message and "cd " in message, message
        assert record.exc_info is None and "Traceback" not in message
        assert service.client.get("/api/v1/model").status_code == 503

    dry = command("app.cli.model_release_raise", url, "--dry-run")
    assert dry.returncode == 0, dry.stderr
    assert "schema 0.9 -> 0.10" in dry.stdout and "Nothing changed" in dry.stdout
    assert scalar(url, schema, key=release["key"]) == "0.9"

    raised = command("app.cli.model_release_raise", url)
    assert raised.returncode == 0, raised.stderr
    assert scalar(url, schema, key=release["key"]) == "0.10"
    again = command("app.cli.model_release_raise", url)
    assert again.returncode == 0 and "nothing to do" in again.stdout
    with serve(configuration, url) as service:
        _serves(service)
        assert service.client.get("/api/v1/model").status_code == 200


@pytest.mark.journey("J12.6")
def test_a_changed_model_file_with_an_unchanged_release_version_is_named(configuration, databases):
    """Given a stored release of the bootstrap model's version with other content, in a schema in the
    window. When the service starts. Then it serves and logs one error naming the model file and
    asking for a new release version, with no command."""
    url = _clone(databases, scenario_seed(configuration))
    release = configuration.model["release"]
    execute(
        url,
        "UPDATE model_releases SET model_hash = 'other-hash' WHERE release_key = :key "
        "AND release_version = :version",
        key=release["key"],
        version=release["version"],
    )
    with serve(configuration, url) as service:
        [record] = service.errors()
        message = record.getMessage()
        assert "release.version" in message and "RDM_MODEL_PATH" in message, message
        assert "app.cli" not in message and record.exc_info is None
        assert service.health() == 200


@pytest.mark.journey("J12.7")
@pytest.mark.parametrize(
    ("settings", "group", "expected", "route"),
    [
        (
            {"MODEL_ADMIN_MUTATIONS_ENABLED": "true"},
            "modelAdmin",
            {"manageDrafts": True, "install": True, "activate": True},
            ("/api/v1/model-drafts", True),
        ),
        (
            {"MODEL_ADMIN_MUTATIONS_ENABLED": "false"},
            "modelAdmin",
            {"readReleases": True, "manageDrafts": False, "install": False, "activate": False},
            ("/api/v1/model-drafts", False),
        ),
        (
            {"WORKSPACE_ADMIN_MUTATIONS_ENABLED": "false"},
            "workspaceAdmin",
            {"manageWorkspaces": False},
            None,
        ),
        (
            {"INTEGRATION_JOBS_ENABLED": "false"},
            "integrationJobs",
            {"createJobs": False, "runModes": []},
            ("/api/v1/batches", False),
        ),
        (
            {
                "BATCH_MAX_ITEMS": "7",
                "BATCH_MAX_BYTES": "9000",
                "ATOMIC_JOB_MAX_ITEMS": "3",
                "BACKGROUND_JOB_MAX_ITEMS": "11",
                "BATCH_BACKGROUND_MAX_BYTES": "12000",
                "JOB_CHUNK_ITEMS": "4",
                "JOB_RETENTION_DAYS": "2",
                "IMPORT_MAX_BYTES": "13000",
                "JOB_PREVIEW_MAX_ITEMS": "14",
            },
            "integrationJobs",
            {"createJobs": True},
            ("/api/v1/batches", True),
        ),
    ],
    ids=["model-admin-on", "model-admin-off", "workspace-admin-off", "jobs-off", "small-limits"],
)
def test_settings_shape_what_the_service_offers(
    configuration, databases, settings, group, expected, route
):
    """When the service starts with model administration on or off, workspace administration off,
    integration jobs off, or small batch limits. Then the capabilities report each group's flags,
    limits and the setting that controls it, and a disabled group's mutating routes are absent."""
    with serve(configuration, _clone(databases), **settings) as service:
        _serves(service)
        capabilities = ok(service.world.api.get("/capabilities"))[group]
        assert {k: capabilities[k] for k in expected} == expected
        assert capabilities["setting"].endswith("_ENABLED")
        if "BATCH_MAX_ITEMS" in settings:
            # Every limit, as set (merged from test_batches in H4d).
            assert capabilities["limits"] == {
                "batchMaxItems": 7,
                "batchMaxBytes": 9000,
                "atomicJobMaxItems": 3,
                "backgroundJobMaxItems": 11,
                "backgroundBatchMaxBytes": 12000,
                "chunkItems": 4,
                "importMaxBytes": 13000,
                "previewMaxItems": 14,
                "retentionDays": 2,
            }
        paths = service.client.get("/openapi.json").json()["paths"]
        if route is not None:
            path, present = route
            assert ("post" in paths.get(path, {})) is present
        if settings.get("INTEGRATION_JOBS_ENABLED") == "false":
            # Cancellation goes with creation; job reads stay (OPERATIONS.md, merged in H4d).
            assert "/api/v1/jobs/{job_id}/cancel" not in paths
            ok(service.world.api.get("/jobs"))
        if group == "workspaceAdmin":
            assert "post" not in paths.get("/api/v1/workspaces", {})
            denied = service.world.api.post("/workspaces", {"key": "denied", "label": "Denied"})
            assert denied.status_code in {404, 405}


@pytest.mark.journey("J12.7")
@pytest.mark.parametrize("script", ["bundled", "cdn"])
def test_the_api_reference_loads_its_pinned_script(configuration, databases, script):
    """When the service starts with the API reference script bundled or from the CDN. Then the
    reference page loads the pinned script from the engine or from the CDN under its integrity
    hash."""
    with serve(configuration, _clone(databases), RDM_API_REFERENCE_SCRIPT=script) as service:
        page = service.client.get("/docs/api")
        assert page.status_code == 200
        if script == "bundled":
            assert "/docs/api/scalar/standalone.js" in page.text
            assert service.client.get("/docs/api/scalar/standalone.js").status_code == 200
        else:
            assert "cdn.jsdelivr.net" in page.text and 'integrity="sha' in page.text


@pytest.mark.journey("J12.7")
@pytest.mark.parametrize(
    ("settings", "named"),
    [
        ({"RDM_API_REFERENCE_SCRIPT": "elsewhere"}, ("RDM_API_REFERENCE_SCRIPT",)),
        ({"BATCH_MAX_ITEMS": "zero"}, ("BATCH_MAX_ITEMS",)),
        ({"DATABASE_POOL_SIZE": "0"}, ("DATABASE_POOL_SIZE",)),
        ({"DATABASE_POOL_MAX_OVERFLOW": "-1"}, ("DATABASE_POOL_MAX_OVERFLOW",)),
        ({"DATABASE_IDLE_TRANSACTION_TIMEOUT": "-1"}, ("DATABASE_IDLE_TRANSACTION_TIMEOUT",)),
        # Every stored secret is sealed with one key, required (0.12 I1, D253); the setting it
        # replaced is refused by name.
        ({"SECRETS_ENCRYPTION_KEY": ""}, ("SECRETS_ENCRYPTION_KEY", "generate_key")),
        (
            {"CONSUMER_WEBHOOK_KEY_ENCRYPTION_KEY": "a" * 43},
            ("CONSUMER_WEBHOOK_KEY_ENCRYPTION_KEY", "SECRETS_ENCRYPTION_KEY"),
        ),
        ({"PUBLIC_URL": "localhost:8000"}, ("PUBLIC_URL",)),
        ({"SOURCE_CODE_URL": "git.example.org/source"}, ("SOURCE_CODE_URL",)),
    ],
    ids=[
        "reference-script",
        "limit",
        "pool-size",
        "pool-overflow",
        "idle-transaction",
        "no-secrets-key",
        "retired-key-name",
        "public-url",
        "source-code-url",
    ],
)
def test_an_invalid_setting_refuses_to_start(configuration, databases, settings, named):
    """When the service starts with an invalid setting. Then it refuses to start with a message
    naming the setting."""
    with (
        pytest.raises(RuntimeError) as refusal,
        serve(configuration, _clone(databases), **settings),
    ):
        pass
    for name in named:
        assert name in str(refusal.value)


@pytest.mark.journey("J12.7", "J12.10")
def test_model_administration_with_several_workers(configuration, databases):
    """When the service starts with model administration on and ``WEB_CONCURRENCY=2``. Then it
    serves and offers installation and activation (refused before 0.11 N1; several real processes:
    ``test_j12_j36_several_processes.py``)."""
    settings = {"WEB_CONCURRENCY": "2", "MODEL_ADMIN_MUTATIONS_ENABLED": "true"}
    with serve(configuration, _clone(databases), **settings) as service:
        _serves(service)
        admin = service.client.get("/api/v1/capabilities").json()["modelAdmin"]
        assert admin["install"] is True and admin["activate"] is True


@pytest.mark.journey("J12.8")
@pytest.mark.structures("R", "R.u")
def test_the_database_goes_away_while_running(configuration, databases):
    """Given the service serving. When the database becomes unreachable, requests are sent, then the
    database returns. Then requests answer a concise error without a traceback and /health reports
    not ready; once the database returns, requests and /health answer 200 and the job worker runs a
    job, all without a restart (the worker's side mid-job: J24.6)."""
    url = _clone(databases, scenario_seed(configuration))
    with serve(configuration, url) as service:
        api, world = service.world.api, service.world
        ok(api.get("/objects", workspaceKey=W1, pageSize=5))
        with _unreachable(url.database):
            failing = api.get("/objects", workspaceKey=W1, pageSize=5)
            assert failing.status_code == 503 and failing.headers["Retry-After"]
            error = failing.json()["error"]
            assert error["code"] == "DATABASE_UNAVAILABLE", error
            assert error["details"]["reason"] == "unreachable"
            assert "Traceback" not in failing.text
            assert all(r.exc_info is None for r in service.errors())
            down = service.health()
        ok(api.get("/objects", workspaceKey=W1, pageSize=5))
        assert service.health() == 200
        items = [
            {
                "op": "create",
                "applicationKey": world.app("R"),
                "objectTypeKey": world.key("R"),
                "name": "After the outage",
                "attributes": [
                    {"attributeTypeKey": k, "value": v}
                    for k, v in {**world.required_values("R"), world.key("R.u"): "OUTAGE-1"}.items()
                ],
            }
        ]
        job = ok(
            api.post(
                "/batches",
                {"workspaceKey": W1, "policy": "independent", "run": "background", "items": items},
            ),
            202,
        )
        deadline = time.monotonic() + 20
        while ok(api.get(f"/jobs/{job['id']}"))["state"] != "completed":
            assert time.monotonic() < deadline
            time.sleep(0.05)
    assert down == 503


@pytest.mark.journey("J12.11", "J12.7")
def test_the_pool_runs_out(configuration, databases):
    """Given the service with a pool of one connection and a one-second wait, and that connection
    held, as a long request holds it. When a read is sent. Then it answers 503 DATABASE_UNAVAILABLE,
    reason poolExhausted, with Retry-After and a message naming DATABASE_POOL_SIZE; the log has a
    WARNING and no traceback. Once the connection is released, the same read answers 200, and
    GET /system/configuration reports the pool settings as set (0.11 Q1, D179, D180)."""
    from app.db import get_engine

    pool = {
        "DATABASE_POOL_SIZE": "1",
        "DATABASE_POOL_MAX_OVERFLOW": "0",
        "DATABASE_POOL_TIMEOUT": "1",
    }
    with serve(configuration, _clone(databases, scenario_seed(configuration)), **pool) as service:
        api = service.world.api
        ok(api.get("/objects", workspaceKey=W1, pageSize=5))
        # A client that raises what escapes the application: a server logs that as an unhandled
        # "Exception in ASGI application" traceback, which no log handler of the app's would see.
        strict = TestClient(service.client.app, raise_server_exceptions=True)
        held = _hold_the_pool(get_engine())
        try:
            failing = strict.get("/api/v1/objects", params={"workspaceKey": W1, "pageSize": 5})
        finally:
            held.close()
        assert failing.status_code == 503 and failing.headers["Retry-After"]
        error = failing.json()["error"]
        assert error["code"] == "DATABASE_UNAVAILABLE", error
        assert error["details"]["reason"] == "poolExhausted"
        assert "DATABASE_POOL_SIZE" in error["message"] and "Traceback" not in failing.text
        warnings = [r for r in service.output.records if r.levelname == "WARNING"]
        assert any("DATABASE_POOL_SIZE" in r.getMessage() for r in warnings)
        assert all(r.exc_info is None for r in service.output.records)
        ok(api.get("/objects", workspaceKey=W1, pageSize=5))
        reported = {s["name"]: s for s in ok(api.get("/system/configuration"))["settings"]}
        for name, value in pool.items():
            assert (
                reported[name]["value"] == int(value) and reported[name]["source"] == "environment"
            )


@pytest.mark.journey("J12.11")
def test_a_burst_of_requests_is_served_by_a_small_pool(configuration, databases):
    """Given the service with a pool of two connections and a three-second wait. When sixty signed-in
    reads arrive at once, as a page asking for a list per type sends them. Then every one answers
    200 within the wait: requests wait for their turn without holding a worker thread, so the ones
    holding connections always have a thread to finish on (found on a real instance, 2026-10-28:
    a sidebar of 101 types left every request waiting for DATABASE_POOL_TIMEOUT, then 503)."""
    pool = {
        "DATABASE_POOL_SIZE": "2",
        "DATABASE_POOL_MAX_OVERFLOW": "0",
        "DATABASE_POOL_TIMEOUT": "3",
    }
    with serve(configuration, _clone(databases, scenario_seed(configuration)), **pool) as service:
        api = service.world.api
        ok(api.get("/objects", workspaceKey=W1, pageSize=5))
        started = time.monotonic()
        with ThreadPoolExecutor(60) as threads:
            answers = list(
                threads.map(lambda _: api.get("/objects", workspaceKey=W1, pageSize=5), range(60))
            )
        took = time.monotonic() - started
        assert [a.status_code for a in answers] == [200] * 60, {a.status_code for a in answers}
        assert took < 3, took
        assert all(r.exc_info is None for r in service.output.records)


def _hold_the_pool(engine):
    """The pool's only connection, taken as soon as no background thread holds it."""
    deadline = time.monotonic() + 10
    while True:
        try:
            return engine.connect()
        except SQLAlchemyTimeout:
            assert time.monotonic() < deadline
            time.sleep(0.05)


@pytest.mark.journey("J12.11")
def test_more_processes_than_the_server_takes(configuration, databases):
    """When the service starts with WEB_CONCURRENCY so high that its processes' pools could need more
    connections than the PostgreSQL server allows. Then it starts and serves, and logs one WARNING
    naming both figures and the settings to change (0.11 Q1, D181)."""
    url = _clone(databases)
    limit = int(scalar(url, "SHOW max_connections"))
    with serve(configuration, url, WEB_CONCURRENCY=str(limit)) as service:
        _serves(service)
        [warning] = [
            r.getMessage()
            for r in service.output.records
            if r.levelname == "WARNING" and "max_connections" in r.getMessage()
        ]
    assert str(limit) in warning and str(limit * 16) in warning
    for name in ("WEB_CONCURRENCY", "DATABASE_POOL_SIZE", "DATABASE_POOL_MAX_OVERFLOW"):
        assert name in warning
