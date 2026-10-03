"""``engine/jobs/store.py``: jobs, their stored inputs and outcomes, and idempotency keys.

J11.5 and J24.5 walk a key reused, a key whose job still runs and a job past its retention through
the API, and J24 lists jobs and pages a job's applied outcomes. Here are the store's own cases: what
a key answers for each state of its job and in another workspace, a background job's inputs read
back as they were sent, which jobs retention expires, and the job and outcome reads' order and
filters.
"""

from datetime import UTC, datetime, timedelta

import pytest
from scenario import W1, W2
from sqlalchemy import func, select

from app.common.pagination import PageRequest
from app.db import SessionLocal
from app.engine.jobs.store import (
    ItemOutcome,
    complete_job,
    expire_jobs,
    job_item_page,
    job_page,
    load_inputs,
    load_job,
    record_outcomes,
    remember_key,
    replayed_job,
    start_job,
    store_inputs,
)
from app.engine.model.registry import resolve_model_snapshot
from app.errors import ApiError
from app.models.database import IdempotencyKey, Job

SCOPE = "POST /batches"


def new_job(session, *, workspace: str = W1, queued: bool = False) -> Job:
    return start_job(
        session,
        kind="batch",
        workspace_key=workspace,
        change_set_id=None,
        model_release_id=resolve_model_snapshot(session).release_db_id,
        parameters={"policy": "independent", "run": "background"},
        total=0,
        retention_days=7,
        queued=queued,
    )


def answer(session, key: str, fingerprint: str, workspace: str = W1):
    return replayed_job(
        session, scope=SCOPE, workspace_key=workspace, key=key, fingerprint=fingerprint
    )


def test_a_key_answers_with_its_finished_job_and_refuses_anything_else(seeded):
    with SessionLocal() as session:
        job = new_job(session, queued=True)
        remember_key(session, scope=SCOPE, workspace_key=W1, key="k", fingerprint="f1", job=job)

        with pytest.raises(ApiError) as running:
            answer(session, "k", "f1")
        assert (running.value.code, running.value.details, running.value.headers) == (
            "idempotency_in_progress",
            {"jobId": job.id},
            {"Retry-After": "1"},
        )
        with pytest.raises(ApiError) as reused:
            answer(session, "k", "f2")
        assert (reused.value.code, reused.value.details) == (
            "idempotency_key_reused",
            {"jobId": job.id},
        )

        complete_job(session, job, retention_days=7)
        assert answer(session, "k", "f1") is job
        # A key lives as long as its finished job, and belongs to its workspace.
        stored = session.scalar(select(IdempotencyKey).where(IdempotencyKey.key == "k"))
        assert stored.expires_at == job.expires_at
        assert answer(session, "k", "f1", workspace=W2) is None

        stored.expires_at = datetime.now(UTC) - timedelta(seconds=1)
        session.flush()
        assert answer(session, "k", "f1") is None
        assert session.scalar(select(func.count()).select_from(IdempotencyKey)) == 0


def test_inputs_are_read_back_as_they_were_sent(seeded):
    """A field the request left out stays out (an update without ``parent`` keeps the record's
    parent), ``null`` stays ``null``, and values keep their types."""
    sent = [
        {"op": "update", "target": {"id": "a"}, "expectedVersion": 1, "name": "Kept"},
        {"op": "update", "target": {"id": "b"}, "expectedVersion": 2, "parent": None},
        {
            "op": "create",
            "objectTypeKey": "t",
            "applicationKey": "a",
            "name": "Typed",
            "ref": "row-3",
            "attributes": [
                {"attributeTypeKey": "n", "value": 3},
                {"attributeTypeKey": "f", "value": False},
            ],
        },
    ]
    with SessionLocal() as session:
        job = new_job(session, queued=True)
        job.total = len(sent)
        store_inputs(session, job, sent)
        assert load_inputs(session, job, 2) == [(0, sent[0]), (1, sent[1])]
        job.processed = 2
        assert load_inputs(session, job, 2) == [(2, sent[2])]


def test_retention_expires_finished_jobs_only(seeded):
    with SessionLocal() as session:
        finished = new_job(session)
        remember_key(
            session, scope=SCOPE, workspace_key=W1, key="kept", fingerprint="f", job=finished
        )
        complete_job(session, finished, retention_days=7)
        waiting = new_job(session, queued=True)
        session.commit()
        assert expire_jobs(session, datetime.now(UTC)) == 0
        # The seed's own batch is finished too.
        assert expire_jobs(session, datetime.now(UTC) + timedelta(days=30)) >= 1
        session.commit()
        session.expire_all()
        assert (
            session.get(Job, finished.sequence_id).state,
            session.get(Job, waiting.sequence_id).state,
        ) == ("expired", "queued")
        assert session.scalar(select(func.count()).select_from(IdempotencyKey)) == 0


def test_jobs_list_newest_first_and_outcomes_in_item_order(seeded):
    with SessionLocal() as session:
        older, newer = new_job(session), new_job(session, queued=True)
        older.total = 5
        statuses = ["applied", "rejected", "applied", "rejected", "applied"]
        record_outcomes(
            session,
            older,
            [
                ItemOutcome(
                    i, None, status, {"action": "created"} if status == "applied" else {"error": {}}
                )
                for i, status in enumerate(statuses)
            ],
        )
        complete_job(session, older, retention_days=7)

        def jobs(**filters) -> list[str]:
            page = job_page(
                session,
                workspace_key=W1,
                kind=filters.get("kind"),
                state=filters.get("state"),
                page=PageRequest(),
                page_size=50,
            )
            return [job.id for job in page.items if job.id in {older.id, newer.id}]

        assert jobs() == [newer.id, older.id]
        assert (jobs(state="completed"), jobs(kind="export")) == ([older.id], [])

        def outcomes(status=None, **request) -> tuple[list[int], int | None]:
            page = job_item_page(
                session, older, status=status, page=PageRequest(**request), page_size=2
            )
            return [item.item_index for item in page.items], page.total_count

        assert outcomes("rejected") == ([1, 3], None)
        assert outcomes(position=3, include_total=True) == ([3, 4], 5)
        assert load_job(session, older.id) is older
        with pytest.raises(ApiError) as unknown:
            load_job(session, "00000000-0000-4000-8000-000000000000")
        assert unknown.value.code == "job_not_found"
