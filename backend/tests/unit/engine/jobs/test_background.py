"""``engine/jobs/background.py``: queueing a background batch.

J24 queues jobs and J24.4 has a change set's version change under a running job. Here a job queued
with a stale change set version is refused at once and leaves no job.
"""

import pytest
from scenario import W1
from sqlalchemy import func, select

from app.db import SessionLocal
from app.engine.change_sets.lifecycle import create_change_set
from app.engine.jobs.background import (
    replace_earlier_job,
    request_stop,
    submit_background_batch,
)
from app.engine.jobs.store import start_job
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


def test_a_stop_pressed_twice_keeps_the_time_of_the_first(seeded):
    world = seeded
    item = {
        "op": "create",
        "applicationKey": world.app("K"),
        "objectTypeKey": world.key("K"),
        "name": "Twice",
        "attributes": [{"attributeTypeKey": world.key("K.code"), "value": "TWICE"}],
    }
    request = BatchRequest.model_validate(
        {"policy": "independent", "run": "background", "items": [item], "workspaceKey": W1}
    )
    with SessionLocal() as session:
        job, _ = submit_background_batch(session, request, idempotency_key=None, retention_days=7)
        where = Job.sequence_id == job.sequence_id
        assert request_stop(session, where) == 1
        session.commit()
        session.refresh(job)
        first = job.cancel_requested_at
        assert first is not None
        assert request_stop(session, where) == 1
        session.commit()
        session.refresh(job)
        assert job.cancel_requested_at == first
        # A finished job has nothing to stop.
        job.state = "completed"
        session.commit()
        assert request_stop(session, where) == 0


def test_a_new_job_for_a_subject_stops_only_that_subjects_earlier_job(seeded):
    def queue(session, draft):
        release = resolve_model_snapshot(session).release_db_id
        return start_job(
            session,
            kind="dryRun",
            workspace_key=W1,
            change_set_id=None,
            model_release_id=release,
            parameters={"draftId": draft},
            total=None,
            retention_days=7,
            queued=True,
        )

    with SessionLocal() as session:
        earlier, other = queue(session, "draft-a"), queue(session, "draft-b")
        session.commit()
        refused = ApiError(409, "AI_TASK_STATE", "held")

        def refuse():
            raise refused

        with pytest.raises(ApiError):
            replace_earlier_job(
                session,
                "dryRun",
                "draftId",
                "draft-a",
                lambda: queue(session, "draft-a"),
                guard=refuse,
            )
        session.rollback()
        session.refresh(earlier)
        assert earlier.cancel_requested_at is None
        newer = replace_earlier_job(
            session, "dryRun", "draftId", "draft-a", lambda: queue(session, "draft-a")
        )
        session.commit()
        for job in (earlier, other, newer):
            session.refresh(job)
        assert earlier.cancel_requested_at is not None
        assert other.cancel_requested_at is None
        assert newer.cancel_requested_at is None
