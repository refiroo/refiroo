"""J31 — Check what a deployment runs and how it is configured (USER_JOURNEYS.md).

The operator reads ``GET /api/v1/system``: the engine and management API version, the schema
languages, the active model release, the database revision and every setting with its value, its
default and where the value came from. Secrets and the database password are never returned.
"""

import base64
from collections.abc import Iterator

import pytest
import seeds
from alembic.script import ScriptDirectory
from scenario import ok, scenario_seed
from service import serve

from app.db import migration_config
from app.engine.model.compiler import SUPPORTED_SCHEMA_VERSIONS

HEAD = ScriptDirectory.from_config(migration_config()).get_current_head()
GROUPS = {"runtime", "capabilities", "limits", "webhooks"}
SECRETS = ("RDM_CURSOR_SIGNING_KEY", "CONSUMER_WEBHOOK_KEY_ENCRYPTION_KEY")
SIGNING_KEY = "journey-signing-key-not-to-be-shown"
ENCRYPTION_KEY = base64.urlsafe_b64encode(b"k" * 32).decode()
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
    document = ok(world.api.get("/openapi.json"))
    assert system["engine"] == {"version": document["info"]["version"], "managementApi": "v1"}
    assert system["schemaLanguages"] == sorted(SUPPORTED_SCHEMA_VERSIONS)
    state = ok(world.api.get("/model-runtime-state"))
    release = ok(world.api.get(f"/model-releases/{state['activeReleaseId']}"))
    assert system["activeModelRelease"] == {
        "id": release["id"],
        "key": release["key"],
        "name": release["name"],
        "version": release["version"],
        "schemaVersion": release["schemaVersion"],
        "activatedAt": state["updatedAt"],
    }
    assert system["database"] == {"revision": HEAD}
    names = [setting["name"] for setting in system["settings"]]
    assert len(names) == len(set(names)) and "DATABASE_URL" in names
    for setting in system["settings"]:
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
    settings = _settings(ok(world.api.get("/system")))
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


@pytest.mark.journey("J31.2")
@pytest.mark.settings(
    RDM_CURSOR_SIGNING_KEY=SIGNING_KEY, CONSUMER_WEBHOOK_KEY_ENCRYPTION_KEY=ENCRYPTION_KEY
)
def test_secrets_are_set_and_never_shown(world):
    """Given both secrets set. When the operator reads the system. Then each reads no value and no
    default, only `environment`, and neither appears anywhere in the response."""
    response = world.api.get("/system")
    settings = _settings(ok(response))
    for name in SECRETS:
        assert (settings[name]["value"], settings[name]["default"]) == (None, None)
        assert settings[name]["source"] == "environment"
    assert SIGNING_KEY not in response.text and ENCRYPTION_KEY not in response.text


@pytest.mark.journey("J31.2")
@pytest.mark.settings(RDM_CURSOR_SIGNING_KEY="", CONSUMER_WEBHOOK_KEY_ENCRYPTION_KEY="")
def test_secrets_left_unset(world):
    """Given neither secret set. Then each reads no value, no default and `default`."""
    settings = _settings(ok(world.api.get("/system")))
    for name in SECRETS:
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
        response = service.world.api.get("/system")
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
    state = ok(world.api.get("/model-runtime-state"))
    active = ok(world.api.get("/system"))["activeModelRelease"]
    assert (active["id"], active["key"], active["version"]) == (
        release["id"],
        release["key"],
        release["version"],
    )
    assert active["activatedAt"] == state["updatedAt"] != before["activatedAt"]
