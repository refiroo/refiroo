"""J31 — Check what a deployment runs and how it is configured (USER_JOURNEYS.md).

Anyone signed in reads ``GET /api/v1/system``: the engine and management API version, the schema
languages and the active model release. The operator reads ``GET /api/v1/system/configuration``
(0.12 D246): the database revision and every setting with its value, its default and where the value
came from. Secrets and the database password are never returned.
"""

from collections.abc import Iterator

import pytest
import seeds
from alembic.script import ScriptDirectory
from harness_identity import SECRETS_ENCRYPTION_KEY
from scenario import ok, scenario_seed
from service import serve

from app.db import migration_config
from app.engine.model.compiler import SCHEMA_VERSIONS

HEAD = ScriptDirectory.from_config(migration_config()).get_current_head()
GROUPS = {"runtime", "capabilities", "limits", "webhooks", "ai"}
SECRETS = ("RDM_CURSOR_SIGNING_KEY", "SECRETS_ENCRYPTION_KEY")
SIGNING_KEY = "journey-signing-key-not-to-be-shown"
# The harness's key: every test database's secrets are sealed with it (0.12 I1).
ENCRYPTION_KEY = SECRETS_ENCRYPTION_KEY
PASSWORD = "s3cret-pass"


def _settings(system):
    return {setting["name"]: setting for setting in system["settings"]}


@pytest.fixture
def databases() -> Iterator[list]:
    created: list = []
    yield created
    for url in created:
        seeds.drop(url.database)


@pytest.mark.journey("J31")
def test_read_what_the_deployment_runs(world):
    """Given a running service. When the operator reads the system. Then it names the engine version
    the API document carries, the management API `v1`, the schema languages it reads, the active
    release as the runtime state and the release read name it, the database at the newest revision,
    and every setting once, in one of the four groups, each with what it controls."""
    system = ok(world.api.get("/system"))
    configuration = ok(world.api.get("/system/configuration"))
    document = ok(world.api.get("/openapi.json"))
    assert system["engine"] == {
        "version": document["info"]["version"],
        "managementApi": "v1",
        "license": "AGPL-3.0-or-later",
        "sourceCode": f"https://github.com/refiroo/refiroo/tree/v{document['info']['version']}",
    }
    # The licence is in the API document too (0.12 L1, D219).
    assert document["info"]["license"]["identifier"] == "AGPL-3.0-or-later"
    # Oldest first, by number: 0.10 after 0.9 (0.10 N1).
    assert system["schemaLanguages"] == list(SCHEMA_VERSIONS)
    assert system["schemaLanguages"] == ["0.10"]
    state = world.workspace_model()
    release = ok(world.api.get(f"/model-releases/{state['releaseId']}"))
    assert system["activeModelRelease"] == {
        "id": release["id"],
        "key": release["key"],
        "name": release["name"],
        "version": release["version"],
        "schemaVersion": release["schemaVersion"],
        "activatedAt": state["updatedAt"],
    }
    # What the deployment runs is for anyone signed in; how it is configured is not in it (D246).
    # The instance's product, which a person with no workspace reads too (0.12 HM1, D338).
    assert set(system) == {"engine", "schemaLanguages", "activeModelRelease", "product", "ai"}
    # Whether an AI provider is set, for a client to offer an AI action only then (0.16 AP1).
    assert system["ai"] == {"configured": False, "provider": None, "sendLevel": "values"}
    assert configuration["database"] == {"revision": HEAD}
    names = [setting["name"] for setting in configuration["settings"]]
    assert len(names) == len(set(names)) and "DATABASE_URL" in names
    for setting in configuration["settings"]:
        assert setting["group"] in GROUPS and setting["description"]
        assert setting["source"] in {"environment", "default"}


@pytest.mark.journey("J31.1")
@pytest.mark.settings(
    FEED_RETENTION_DAYS="14",
    CORS_ORIGINS="https://one.example, https://two.example",
    INTEGRATION_JOBS_ENABLED="false",
)
def test_a_setting_from_the_environment_against_one_at_its_default(world):
    """Given the service started with three settings in the environment. When the operator reads the
    system. Then each reads its value with its type (an integer, a list, a boolean), its default and
    `environment`; a setting left alone reads its default as its value and `default`."""
    settings = _settings(ok(world.api.get("/system/configuration")))
    assert settings["FEED_RETENTION_DAYS"] | {"description": ""} == {
        "name": "FEED_RETENTION_DAYS",
        "group": "limits",
        "description": "",
        "value": 14,
        "default": 30,
        "source": "environment",
    }
    assert settings["CORS_ORIGINS"]["value"] == ["https://one.example", "https://two.example"]
    assert settings["CORS_ORIGINS"]["default"] == ["http://localhost:5173"]
    assert settings["CORS_ORIGINS"]["source"] == "environment"
    jobs = settings["INTEGRATION_JOBS_ENABLED"]
    assert (jobs["group"], jobs["value"], jobs["default"], jobs["source"]) == (
        "capabilities",
        False,
        True,
        "environment",
    )
    chunk = settings["JOB_CHUNK_ITEMS"]
    assert (chunk["value"], chunk["default"], chunk["source"]) == (500, 500, "default")


@pytest.mark.journey("J31.4")
@pytest.mark.settings(SOURCE_CODE_URL="https://git.example.org/ops/refiroo-modified")
def test_an_operator_names_the_source_of_a_modified_version(world):
    """Given the service started by an operator with a `SOURCE_CODE_URL`. When the system is read.
    Then the engine offers that address as its source, the setting reads back from the environment
    with the project's tag as its default, and the licence is still the AGPL's."""
    system = ok(world.api.get("/system"))
    configuration = ok(world.api.get("/system/configuration"))
    assert system["engine"]["sourceCode"] == "https://git.example.org/ops/refiroo-modified"
    assert system["engine"]["license"] == "AGPL-3.0-or-later"
    setting = _settings(configuration)["SOURCE_CODE_URL"]
    assert setting["value"] == "https://git.example.org/ops/refiroo-modified"
    assert setting["default"].startswith("https://github.com/refiroo/refiroo/tree/v")
    assert setting["source"] == "environment"


@pytest.mark.journey("J31.2")
@pytest.mark.settings(RDM_CURSOR_SIGNING_KEY=SIGNING_KEY, SECRETS_ENCRYPTION_KEY=ENCRYPTION_KEY)
def test_secrets_are_set_and_never_shown(world):
    """Given both secrets set. When the operator reads the configuration. Then each reads no value
    and no default, only `environment`, and neither appears anywhere in the response."""
    response = world.api.get("/system/configuration")
    settings = _settings(ok(response))
    for name in SECRETS:
        assert (settings[name]["value"], settings[name]["default"]) == (None, None)
        assert settings[name]["source"] == "environment"
    assert SIGNING_KEY not in response.text and ENCRYPTION_KEY not in response.text


@pytest.mark.journey("J31.2")
@pytest.mark.settings(RDM_CURSOR_SIGNING_KEY="")
def test_a_secret_left_unset(world):
    """Given the cursor signing key not set (the secrets key is required, D253). Then it reads no
    value, no default and `default`."""
    settings = _settings(ok(world.api.get("/system/configuration")))
    for name in SECRETS[:1]:
        assert settings[name] | {"description": ""} == {
            "name": name,
            "group": settings[name]["group"],
            "description": "",
            "value": None,
            "default": None,
            "source": "default",
        }


@pytest.mark.journey("J31.2")
def test_the_database_password_is_never_returned(configuration, databases):
    """Given the service started with a database URL carrying a password. When the operator reads
    the system. Then `DATABASE_URL` reads the same URL without the password, and the password
    appears nowhere in the response."""
    url = seeds.clone(scenario_seed(configuration))
    databases.append(url)
    with serve(configuration, url.set(password=PASSWORD)) as service:
        response = service.world.api.get("/system/configuration")
        database_url = _settings(ok(response))["DATABASE_URL"]
    assert PASSWORD not in response.text
    assert database_url["value"] == url.render_as_string(hide_password=False)
    assert (database_url["default"], database_url["source"]) == (None, "environment")


@pytest.mark.journey("J31.3")
@pytest.mark.structures("R")
def test_the_active_release_after_an_activation(world):
    """Given a compatible release installed and activated. When the operator reads the system. Then
    it names the new release, and `activatedAt` is the runtime state's time of the activation."""
    model, _ = world.candidate("compatible")
    release = world.install(model)
    before = ok(world.api.get("/system"))["activeModelRelease"]
    assert before["id"] != release["id"]
    ok(world.activate(release["id"]))
    state = world.workspace_model()
    active = ok(world.api.get("/system"))["activeModelRelease"]
    assert (active["id"], active["key"], active["version"]) == (
        release["id"],
        release["key"],
        release["version"],
    )
    assert active["activatedAt"] == state["updatedAt"] != before["activatedAt"]
