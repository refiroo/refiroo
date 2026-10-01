"""Base 0.9 B1 and B2: the settings a batch runs under, and the value index a live write seeks.

The limits are settings refused at startup when invalid. The B1 and B2 migrations and their
interrupted-run recovery were SQLite revisions, replaced by the PostgreSQL baseline (0.9.0-alpha.1,
PG-D3); the baseline is checked against the ORM in ``test_schema_drift``.
"""

import pytest
from sqlalchemy import create_engine, text

from app.config import Settings


def test_batch_settings_have_defaults_and_refuse_invalid_values():
    defaults = Settings.from_env({})
    assert (
        defaults.integration_jobs_enabled,
        defaults.batch_max_items,
        defaults.batch_max_bytes,
        defaults.atomic_job_max_items,
        defaults.job_retention_days,
        defaults.sqlite_lock_wait_seconds,
        defaults.background_job_max_items,
        defaults.batch_background_max_bytes,
        defaults.job_chunk_items,
        defaults.job_lease_seconds,
    ) == (True, 1000, 5 * 1024 * 1024, 10_000, 7, 60, 1_000_000, 50 * 1024 * 1024, 500, 120)
    assert not Settings.from_env({"INTEGRATION_JOBS_ENABLED": "false"}).integration_jobs_enabled
    for name in (
        "BATCH_MAX_ITEMS",
        "BATCH_MAX_BYTES",
        "ATOMIC_JOB_MAX_ITEMS",
        "JOB_RETENTION_DAYS",
        "SQLITE_LOCK_WAIT_SECONDS",
        "BACKGROUND_JOB_MAX_ITEMS",
        "BATCH_BACKGROUND_MAX_BYTES",
        "JOB_CHUNK_ITEMS",
        "JOB_LEASE_SECONDS",
    ):
        for value in ("0", "-1", "many"):
            with pytest.raises(RuntimeError, match=f"{name} must be a positive integer"):
                Settings.from_env({name: value})


def test_a_live_unique_value_check_seeks_to_the_value(migrated_database):
    """B2 budget finding: the live unique-value lookup read every value of the attribute, so each
    write with a unique attribute cost in proportion to the records holding it. It now seeks."""
    engine = create_engine(migrated_database())
    try:
        with engine.connect() as connection:
            # An empty table plans a sequential scan; forbidding it shows the index answers.
            connection.execute(text("SET enable_seqscan = off"))
            plan = " ".join(
                row[0]
                for row in connection.execute(
                    text(
                        "EXPLAIN SELECT objects.id FROM objects JOIN attribute_values "
                        "ON attribute_values.object_id = objects.id "
                        "WHERE attribute_values.attribute_type_key = 'code' "
                        "AND attribute_values.text_value = 'A-1' AND objects.workspace_key = 'default' "
                        "LIMIT 1"
                    )
                )
            )
    finally:
        engine.dispose()
    assert "ix_attribute_values_key_text" in plan, plan
