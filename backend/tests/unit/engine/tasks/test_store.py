"""An assistant task follows the job it waits for (``engine/tasks/store.py``)."""

from types import SimpleNamespace

import pytest
from scenario import W1
from sqlalchemy import update

from app.db import SessionLocal
from app.engine.change_sets.lifecycle import create_change_set
from app.engine.jobs.store import start_job, stop_job
from app.engine.model.registry import resolve_model_snapshot
from app.engine.tasks import store
from app.errors import ApiError
from app.models.database import ChangeSet

CORRELATION = "3bf4d0425d41467493e19201315cdce9"


def test_a_task_whose_job_failed_shows_the_correlation_id_the_message_asks_for(seeded):
    """Given an assistant job that failed with an internal error before it had an item, then the
    task fails with a warning that gives the correlation ID it asks the person to report, and the
    job's result is not "every item applied" (0.13 DOC11 F6, F10)."""
    with SessionLocal() as session:
        job = start_job(
            session,
            kind="aiTask",
            workspace_key=W1,
            change_set_id=None,
            model_release_id=resolve_model_snapshot(session).release_db_id,
            parameters={"phase": "design", "taskId": "t", "taskVersion": 1},
            total=0,
            retention_days=7,
            queued=False,
        )
        stop_job(
            session,
            job,
            state="failed",
            reason="JOB_FAILED",
            error={
                "code": "JOB_FAILED",
                "message": "The job stopped because of an internal error. If it recurs, report "
                "the correlation ID",
                "details": {"correlationId": CORRELATION},
            },
            retention_days=7,
        )
        assert job.state == "failed" and job.result is None

        task = SimpleNamespace(state="reading", job_id=job.id, notes=[], version=1)
        store.sync(session, task, 7)
        assert task.state == "failed"
        assert task.notes[-1]["text"].endswith(f"report the correlation ID: {CORRELATION}")
        session.rollback()


def test_a_change_set_is_discarded_at_the_version_asked_for_and_a_missing_one_is_no_error(seeded):
    """Given a change set another session has since changed, then the one discard claims the
    version the session holds (a conflict) unless it is told to read it again, which is what a load
    whose batch rolled back needs; and a change set already gone is answered False, not refused."""
    with SessionLocal() as session, SessionLocal() as other:
        change_set = create_change_set(
            session, W1, resolve_model_snapshot(session).release_db_id, name="Load"
        )
        known = change_set.id
        other.execute(
            update(ChangeSet).where(ChangeSet.id == known).values(version=ChangeSet.version + 1)
        )
        other.commit()
        with pytest.raises(ApiError) as refused:
            store.discard_set(session, known)
        assert refused.value.code == "CHANGE_SET_VERSION_CONFLICT"
        session.rollback()
        assert store.discard_set(session, known, refresh=True) is True
        assert store.discard_set(session, known) is False
