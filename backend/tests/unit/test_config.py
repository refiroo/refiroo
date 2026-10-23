"""``config.py``: the settings the service starts with.

J12.7 starts the service with one invalid limit and with small limits. Here every integration-job
setting, the change feed's retention and the consumer batch resolve maximum have its default and refuses a value that is not a positive
integer. The settings catalogue (J31) names every setting once, in the OPERATIONS table of its group,
and the database URL it reports has no password.
"""

import re
import tomllib
from pathlib import Path

import pytest

from app.config import (
    ENGINE_VERSION,
    SETTINGS_CATALOGUE,
    Settings,
    describe_settings,
    without_password,
)

ROOT = Path(__file__).resolve().parents[3]
# The OPERATIONS heading whose table lists each group's settings.
GROUP_SECTIONS = {
    "runtime": "### Runtime",
    "capabilities": "### Capability groups",
    "limits": "### Batch and job limits",
    "webhooks": "## Webhook subscriptions",
}

JOB_LIMITS = {
    "BATCH_MAX_ITEMS": ("batch_max_items", 1000),
    "BATCH_MAX_BYTES": ("batch_max_bytes", 5 * 1024 * 1024),
    "ATOMIC_JOB_MAX_ITEMS": ("atomic_job_max_items", 10_000),
    "JOB_RETENTION_DAYS": ("job_retention_days", 7),
    "BACKGROUND_JOB_MAX_ITEMS": ("background_job_max_items", 1_000_000),
    "BATCH_BACKGROUND_MAX_BYTES": ("batch_background_max_bytes", 50 * 1024 * 1024),
    "JOB_CHUNK_ITEMS": ("job_chunk_items", 500),
    "JOB_LEASE_SECONDS": ("job_lease_seconds", 120),
    "FEED_RETENTION_DAYS": ("feed_retention_days", 30),
    "CONSUMER_RESOLVE_MAX_ITEMS": ("consumer_resolve_max_items", 1000),
}


def test_integration_jobs_are_on_by_default_and_can_be_turned_off():
    assert Settings.from_env({}).integration_jobs_enabled
    assert not Settings.from_env({"INTEGRATION_JOBS_ENABLED": "false"}).integration_jobs_enabled


@pytest.mark.parametrize("name", JOB_LIMITS)
def test_a_job_limit_has_its_default_and_takes_only_a_positive_integer(name):
    attribute, default = JOB_LIMITS[name]
    assert getattr(Settings.from_env({}), attribute) == default
    assert getattr(Settings.from_env({name: "3"}), attribute) == 3
    for value in ("0", "-1", "many"):
        with pytest.raises(RuntimeError, match=f"{name} must be a positive integer"):
            Settings.from_env({name: value})


def test_the_catalogue_names_every_setting_once():
    fields = [entry.field for entry in SETTINGS_CATALOGUE]
    names = [entry.name for entry in SETTINGS_CATALOGUE]
    assert sorted(fields) == sorted(Settings.model_fields)
    assert len(set(names)) == len(names)
    assert {entry.name for entry in SETTINGS_CATALOGUE if entry.secret} == {
        "RDM_CURSOR_SIGNING_KEY",
        "SECRETS_ENCRYPTION_KEY",
    }


def _section(text: str, heading: str) -> str:
    start = text.index(f"\n{heading}\n")
    level = heading.split(" ")[0]
    following = re.search(rf"\n#{{2,{len(level)}}} ", text[start + len(heading) + 2 :])
    return text[start : start + len(heading) + 2 + following.start()] if following else text[start:]


@pytest.mark.parametrize("entry", SETTINGS_CATALOGUE, ids=lambda entry: entry.name)
def test_each_setting_is_in_the_operations_table_of_its_group(entry):
    operations = (ROOT / "docs" / "OPERATIONS.md").read_text()
    assert f"| `{entry.name}` |" in _section(operations, GROUP_SECTIONS[entry.group])


def test_a_reported_setting_keeps_its_type_and_says_where_it_came_from():
    environ = {
        "FEED_RETENTION_DAYS": "14",
        "CORS_ORIGINS": "https://a.example",
        "RDM_CURSOR_SIGNING_KEY": "",
    }
    reported = {s.name: s for s in describe_settings(Settings.from_env(environ), environ)}
    assert (reported["FEED_RETENTION_DAYS"].value, reported["FEED_RETENTION_DAYS"].default) == (
        14,
        30,
    )
    assert reported["FEED_RETENTION_DAYS"].source == "environment"
    assert reported["CORS_ORIGINS"].value == ["https://a.example"]
    assert (reported["JOB_CHUNK_ITEMS"].value, reported["JOB_CHUNK_ITEMS"].source) == (
        500,
        "default",
    )
    assert reported["RDM_CURSOR_SIGNING_KEY"].source == "default"
    assert reported["MODEL_ADMIN_MUTATIONS_ENABLED"].value is False


def test_a_secret_reports_only_whether_it_is_set():
    environ = {"RDM_CURSOR_SIGNING_KEY": "not-shown"}
    reported = {s.name: s for s in describe_settings(Settings.from_env(environ), environ)}
    key = reported["RDM_CURSOR_SIGNING_KEY"]
    assert (key.value, key.default, key.source) == (None, None, "environment")
    unset = reported["SECRETS_ENCRYPTION_KEY"]
    assert (unset.value, unset.default, unset.source) == (None, None, "default")


@pytest.mark.parametrize(
    ("url", "shown"),
    [
        (
            "postgresql+psycopg://rdm:pw@db.example:5432/rdm",
            "postgresql+psycopg://rdm@db.example:5432/rdm",
        ),
        ("postgresql+psycopg://rdm@db.example/rdm", "postgresql+psycopg://rdm@db.example/rdm"),
        ("postgresql+psycopg://rdm:pw@/rdm?host=/tmp", "postgresql+psycopg://rdm@/rdm?host=%2Ftmp"),
        (
            "postgresql+psycopg://db.example/rdm?password=pw&sslmode=require",
            "postgresql+psycopg://db.example/rdm?sslmode=require",
        ),
        ("not a url :pw@", None),
    ],
    ids=["password", "user-only", "socket", "password-parameter", "unreadable"],
)
def test_the_database_url_is_shown_without_its_password(url, shown):
    assert without_password(url) == shown


def test_the_engine_version_is_the_package_version():
    pyproject = tomllib.loads((ROOT / "backend" / "pyproject.toml").read_text())
    assert ENGINE_VERSION == pyproject["project"]["version"]
