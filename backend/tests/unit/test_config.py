"""``config.py``: the settings the service starts with.

J12.7 starts the service with one invalid limit and with small limits. Here every integration-job
setting, the change feed's retention and the consumer batch resolve maximum have its default and refuses a value that is not a positive
integer.
"""

import pytest

from app.config import Settings

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
