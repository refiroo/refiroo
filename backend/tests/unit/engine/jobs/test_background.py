"""``engine/jobs/background.py``: queueing a background batch.

J24 queues jobs and J24.4 has a change set's version change under a running job. Here a job queued
with a stale change set version is refused at once and leaves no job.
"""

import pytest
from scenario import W1
from sqlalchemy import func, select

from app.db import SessionLocal
from app.engine.change_sets.lifecycle import create_change_set
from app.engine.jobs.background import submit_background_batch
from app.engine.model.registry import resolve_model_snapshot
from app.errors import ApiError
from app.models.commands import BatchRequest
from app.models.database import Job


def test_a_job_queued_with_a_stale_change_set_version_is_refused(seeded):
    world = seeded
    with SessionLocal() as session:
        release = resolve_model_snapshot(session).release_db_id
        staged = create_change_set(session, W1, release, source="currentLive")
        jobs = session.scalar(select(func.count()).select_from(Job))
        item = {
            "op": "create",
            "applicationKey": world.app("K"),
            "objectTypeKey": world.key("K"),
            "name": "Late",
            "attributes": [{"attributeTypeKey": world.key("K.code"), "value": "LATE"}],
        }
        request = BatchRequest.model_validate(
            {
                "policy": "independent",
                "run": "background",
                "items": [item],
                "changeSetId": staged.id,
                "expectedChangeSetVersion": staged.version + 1,
            }
        )
        with pytest.raises(ApiError) as refused:
            submit_background_batch(session, request, idempotency_key=None, retention_days=7)
        assert refused.value.code == "CHANGE_SET_VERSION_CONFLICT"
        session.rollback()
        assert session.scalar(select(func.count()).select_from(Job)) == jobs
