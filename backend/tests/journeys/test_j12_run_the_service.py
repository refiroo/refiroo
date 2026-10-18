"""J12 — Run the service, and recover from an expected refusal (USER_JOURNEYS.md).

The operator's channel: the service started with settings on a database (``service.serve``), its log,
its commands run as processes, and ``/health``. A refusal is one concise message saying what failed,
the service state and the safe next step, never a traceback. J12.9 (carrying a SQLite database over)
was dropped with PG4 (2026-10-03).
"""

import hashlib
import json
import time
from collections.abc import Iterator
from pathlib import Path

import pytest
import seeds
from alembic import command as alembic
from alembic.script import ScriptDirectory
from model_support import starter_at_schema
from scenario import W1, W2, W3, model_path, ok, scenario_seed
from service import command, execute, scalar, serve
from test_j24_background_job import _unreachable

from app.db import migration_config
from app.engine.model.compiler import SUPPORTED_SCHEMA_VERSIONS

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


@pytest.mark.journey("J12.5")
def test_an_interrupted_migration_leaves_the_database_as_it_was(configuration, databases):
    """Given a database whose migration fails part-way. When the upgrade command runs, then the
    service starts in the same condition, then starts once the cause is removed. Then the command
    names the database, the current and target revisions, the reason, and the backup and retry
    steps, without credentials or a traceback; nothing it created remains; the service is in
    maintenance; once fixed, the next start migrates and serves."""
    url = _empty(databases)
    # The last table the baseline creates is there already: the migration fails at its end.
    execute(url, "CREATE TABLE relation_set_versions (stray integer)")
    upgrade = command("app.cli.database_upgrade", url)
    assert upgrade.returncode == 1
    for phrase in (
        f"'{url.database}'",
        "Current revision: unversioned",
        f"target revision: {HEAD}",
        "relation_set_versions",
        "pg_dump",
        "python -m app.cli.database_upgrade",
    ):
        assert phrase in upgrade.stderr, upgrade.stderr
    assert "Traceback" not in upgrade.stderr + upgrade.stdout
    assert scalar(url, "SELECT count(*) FROM pg_tables WHERE schemaname = 'public'") == 1
    with serve(configuration, url) as service:
        _refusal(service, "Database migration failed", "still at its current revision")
    execute(url, "DROP TABLE relation_set_versions")
    with serve(configuration, url) as service:
        _serves(service)
    assert scalar(url, "SELECT version_num FROM alembic_version") == HEAD


# The revision before the name search indexes (0.9.0-alpha.1 PG5), as the previous version left it.
BEFORE_NAME_INDEXES = "20261001_02"


def _name_indexes(url) -> int:
    return scalar(url, "SELECT count(*) FROM pg_indexes WHERE indexname LIKE '%\\_name\\_search'")


@pytest.mark.journey("J12.5")
@pytest.mark.structures("R")
def test_an_interrupted_name_index_revision_is_refused_then_recovers(configuration, databases):
    """Given a database at the revision before the name search indexes, one of whose names is taken.
    When the service starts, then starts once the name is free, then starts again. Then the first
    start refuses, naming the current and target revisions and the index, and leaves the database
    at its revision with none of the revision's indexes; the second migrates and serves, and a
    search finds a record by part of its name; the third serves without migrating."""
    url = _empty(databases)
    alembic.upgrade(migration_config(url), BEFORE_NAME_INDEXES)
    execute(url, "CREATE INDEX ix_change_set_objects_name_search ON change_set_objects (change_set_id)")
    with serve(configuration, url) as service:
        message = _refusal(
            service,
            "Database migration failed",
            f"Current revision: {BEFORE_NAME_INDEXES}",
            f"target revision: {HEAD}",
            "still at its current revision",
        )
        assert "ix_change_set_objects_name_search" in message
    assert scalar(url, "SELECT version_num FROM alembic_version") == BEFORE_NAME_INDEXES
    assert _name_indexes(url) == 1
    execute(url, "DROP INDEX ix_change_set_objects_name_search")
    with serve(configuration, url) as service:
        _serves(service)
        world = service.world
        made = world.made("R", "Quarterly harbour ledger")
        page = ok(world.api.get(f"/objects/{world.key('R')}", workspaceKey=W1, search="harbour"))
        assert [item["id"] for item in page["items"]] == [made["id"]]
    assert scalar(url, "SELECT version_num FROM alembic_version") == HEAD
    assert _name_indexes(url) == 4
    with serve(configuration, url) as service:
        _serves(service)


def _select_a_schema_04_release(configuration, url):
    """The selected release as an engine before schema 0.5 stored it: the configuration's model
    without the later features, at schema 0.4 and another version."""
    legacy = starter_at_schema("0.5", configuration.model)
    legacy["schemaVersion"] = "0.4"
    legacy["release"]["version"] = "0.4.0-legacy"
    execute(
        url,
        "UPDATE model_releases SET schema_version = '0.4', release_version = :version, "
        "model_json = CAST(:model AS json), model_hash = :hash WHERE id = (SELECT model_release_id "
        "FROM workspace_models WHERE workspace_key = 'default')",
        version="0.4.0-legacy",
        model=json.dumps(legacy),
        hash=hashlib.sha256(json.dumps(legacy).encode()).hexdigest(),
    )


@pytest.mark.journey("J12.6")
@pytest.mark.structures("R")
def test_an_unsupported_model_schema_is_upgraded_offline(configuration, databases, tmp_path):
    """Given a database with records whose selected release has a schema this version does not read.
    When the service starts; the upgrade command runs with a file that is not a model, then with the
    model; and the service restarts. Then the start refuses, naming the selected and supported schemas
    and the upgrade command; the failing command leaves the selection unchanged; the upgrade selects
    a supported release in one step, recorded as a schema upgrade; the restart serves the records."""
    url = _clone(databases, scenario_seed(configuration))
    _select_a_schema_04_release(configuration, url)
    selected = "SELECT model_release_id FROM workspace_models WHERE workspace_key = 'default'"
    before = scalar(url, selected)
    with serve(configuration, url) as service:
        message = _refusal(
            service,
            "schema 0.4",
            "app.cli.model_schema_upgrade --model",
            state=("/health returns HTTP 503",),
        )
        for version in SUPPORTED_SCHEMA_VERSIONS:
            assert version in message, message

    broken = tmp_path / "not-a-model.json"
    broken.write_text("{}")
    failed = command("app.cli.model_schema_upgrade", url, "--model", str(broken))
    assert failed.returncode == 1 and "The selected release is unchanged" in failed.stderr
    assert "Traceback" not in failed.stderr and scalar(url, selected) == before

    upgraded = command(
        "app.cli.model_schema_upgrade", url, "--model", str(model_path(configuration))
    )
    assert upgraded.returncode == 0, upgraded.stderr
    release_id = upgraded.stdout.split()[-1]
    with serve(configuration, url) as service:
        _serves(service)
        api = service.world.api
        assert api.get("/model").headers["X-Model-Release-Id"] == release_id
        # One entry per workspace the upgrade moved (0.11 M1): each runs its own release.
        items = ok(api.get(f"/model-releases/{release_id}/activations"))["items"]
        assert [a["kind"] for a in items] == ["schemaUpgraded"] * 3
        assert sorted(a["workspaceKey"] for a in items) == sorted([W1, W2, W3])
        page = ok(api.get(f"/objects/{configuration.key('R')}", workspaceKey="closed-site"))
        assert page["items"]


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
        page = service.client.get("/docs")
        assert page.status_code == 200
        if script == "bundled":
            assert "/docs/scalar/standalone.js" in page.text
            assert service.client.get("/docs/scalar/standalone.js").status_code == 200
        else:
            assert "cdn.jsdelivr.net" in page.text and 'integrity="sha' in page.text


@pytest.mark.journey("J12.7")
@pytest.mark.parametrize(
    ("settings", "named"),
    [
        ({"RDM_API_REFERENCE_SCRIPT": "elsewhere"}, ("RDM_API_REFERENCE_SCRIPT",)),
        ({"BATCH_MAX_ITEMS": "zero"}, ("BATCH_MAX_ITEMS",)),
        (
            {"WEB_CONCURRENCY": "2", "MODEL_ADMIN_MUTATIONS_ENABLED": "true"},
            ("MODEL_ADMIN_MUTATIONS_ENABLED", "WEB_CONCURRENCY"),
        ),
    ],
    ids=["reference-script", "limit", "concurrency"],
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
            assert failing.status_code >= 500
            error = failing.json()["error"]
            assert error["code"] and "Traceback" not in failing.text
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


@pytest.mark.journey("J12.7")
def test_a_model_file_with_schema_0_8_consumer_apis_refuses_to_start(configuration, databases, tmp_path):
    """When the service starts with RDM_MODEL_PATH naming a schema 0.8 model that declares
    consumerApis. Then it refuses to start with a message naming the setting, the file and schema
    0.9 (C18, C-D134). The same file without them starts."""
    legacy = json.loads((Path(__file__).parents[1] / "fixtures" / "consumer_08" / "rdm-starter-0.9.2.json").read_text())
    path = tmp_path / "legacy.json"
    path.write_text(json.dumps(legacy))
    with (
        pytest.raises(RuntimeError) as refusal,
        serve(configuration, _clone(databases), RDM_MODEL_PATH=str(path)),
    ):
        pass
    assert "RDM_MODEL_PATH" in str(refusal.value) and str(path) in str(refusal.value)
    assert "schema 0.9" in str(refusal.value)
    del legacy["consumerApis"]
    path.write_text(json.dumps(legacy))
    with serve(configuration, _clone(databases), RDM_MODEL_PATH=str(path)) as service:
        assert service.health() == 200
