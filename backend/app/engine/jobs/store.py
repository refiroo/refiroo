"""Jobs, their item outcomes and idempotency keys (Base 0.9, ADR-036, INTEGRATION_API P).

An inline batch writes the job, its items' changes and their outcomes, and commits once, so a failed
request leaves no job behind. A background job is queued with its items as inputs (D27); the worker
commits each chunk's changes, outcomes and checkpoint (``processed``) together, so every item before
the checkpoint has its outcome and none after it has.
"""

import hashlib
import json
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import JSON, delete, insert, literal, select, update
from sqlalchemy.orm import Session

from ...common.pagination import Page, PageRequest, integer_key, paginate_statement
from ...errors import api_error
from ...models.database import IdempotencyKey, Job, JobInput, JobItem, ModelRelease

ACTIONS = ("created", "updated", "unchanged", "deleted")
FINISHED = frozenset({"completed", "failed", "cancelled", "expired"})

_JOB_KEYS = (integer_key("sequenceId", Job.sequence_id, "sequence_id", descending=True),)
_ITEM_KEYS = (integer_key("index", JobItem.item_index, "item_index"),)
# Input rows per insert statement, well under every driver's bound-parameter limit.
_INSERT_ROWS = 1000


@dataclass(frozen=True)
class ItemOutcome:
    """One item's outcome (P2): ``applied`` with an action, ``rejected`` with an error, or
    ``unprocessed`` with a reason; ``fields`` holds the rest of it."""

    index: int
    ref: str | None
    status: str
    fields: dict[str, Any] = field(default_factory=dict)


def start_job(
    session: Session,
    *,
    kind: str,
    workspace_key: str,
    change_set_id: str | None,
    model_release_id: int,
    parameters: dict[str, Any],
    total: int,
    retention_days: int,
    queued: bool = False,
    change_set_version: int | None = None,
) -> Job:
    """A job, flushed so its ID can be the cause of the changes it makes: running for an inline
    batch, queued for the worker otherwise."""
    now = datetime.now(UTC)
    job = Job(
        kind=kind,
        workspace_key=workspace_key,
        change_set_id=change_set_id,
        model_release_id=model_release_id,
        parameters=parameters,
        state="queued" if queued else "running",
        stage=None if queued else "applying",
        total=total,
        processed=0,
        counts=_empty_counts(),
        change_set_version=change_set_version,
        created_at=now,
        started_at=None if queued else now,
        expires_at=now + timedelta(days=retention_days),
    )
    session.add(job)
    session.flush()
    return job


def store_inputs(session: Session, job: Job, items: Sequence[dict[str, Any]]) -> None:
    """A background job's items, in order, for the worker to read chunk by chunk (D27)."""
    for start in range(0, len(items), _INSERT_ROWS):
        session.execute(
            insert(JobInput),
            [
                {
                    "job_id": job.sequence_id,
                    "item_index": index,
                    "ref": item.get("ref"),
                    "item": item,
                }
                for index, item in enumerate(items[start : start + _INSERT_ROWS], start)
            ],
        )


def load_inputs(session: Session, job: Job, count: int) -> list[tuple[int, dict[str, Any]]]:
    """The next ``count`` items after the job's checkpoint."""
    return list(
        session.execute(
            select(JobInput.item_index, JobInput.item)
            .where(
                JobInput.job_id == job.sequence_id,
                JobInput.item_index >= job.processed,
                JobInput.item_index < job.processed + count,
            )
            .order_by(JobInput.item_index)
        )
        .tuples()
        .all()
    )


def record_outcomes(session: Session, job: Job, outcomes: Sequence[ItemOutcome]) -> None:
    """Add outcomes in item order and move the job's checkpoint past them."""
    if outcomes:
        session.execute(
            insert(JobItem),
            [
                {
                    "job_id": job.sequence_id,
                    "item_index": outcome.index,
                    "ref": outcome.ref,
                    "status": outcome.status,
                    "outcome": outcome.fields,
                }
                for outcome in outcomes
            ],
        )
    counts = _empty_counts() | dict(job.counts or {})
    for outcome in outcomes:
        counts[outcome.status] += 1
        if outcome.status == "applied":
            counts[outcome.fields["action"]] += 1
    job.counts = counts
    job.processed += len(outcomes)


def complete_job(session: Session, job: Job, *, retention_days: int) -> None:
    """Every item has its outcome: the job is completed with its result."""
    _finish(session, job, "completed", retention_days=retention_days)


def stop_job(
    session: Session,
    job: Job,
    *,
    state: str,
    reason: str,
    error: dict[str, Any] | None,
    retention_days: int,
) -> None:
    """End the job before its last item (P6): every item without an outcome is ``unprocessed`` with
    ``reason``, written from its stored input in one statement."""
    remaining = job.total - job.processed
    if remaining:
        session.execute(
            insert(JobItem).from_select(
                ["job_id", "item_index", "ref", "status", "outcome"],
                select(
                    JobInput.job_id,
                    JobInput.item_index,
                    JobInput.ref,
                    literal("unprocessed"),
                    literal({"reason": reason}, JSON),
                ).where(
                    JobInput.job_id == job.sequence_id, JobInput.item_index >= job.processed
                ),
            )
        )
        counts = _empty_counts() | dict(job.counts or {})
        counts["unprocessed"] += remaining
        job.counts = counts
        job.processed = job.total
    job.error = error
    _finish(session, job, state, retention_days=retention_days)


def finish_job(
    session: Session,
    job: Job,
    outcomes: Sequence[ItemOutcome],
    *,
    retention_days: int,
    change_set_version: int | None = None,
) -> None:
    """Record an inline job's outcomes and complete it."""
    record_outcomes(session, job, outcomes)
    job.change_set_version = change_set_version
    complete_job(session, job, retention_days=retention_days)


def _finish(session: Session, job: Job, state: str, *, retention_days: int) -> None:
    counts = job.counts
    now = datetime.now(UTC)
    job.result = (
        "applied"
        if counts["applied"] == job.total
        else "rejected"
        if counts["applied"] == 0
        else "partial"
    )
    job.state = state
    job.stage = None
    job.finished_at = now
    job.expires_at = now + timedelta(days=retention_days)
    job.lease_owner = None
    job.lease_expires_at = None
    session.execute(delete(JobInput).where(JobInput.job_id == job.sequence_id))
    # A key answers with its job for as long as the job is kept.
    session.execute(
        update(IdempotencyKey)
        .where(IdempotencyKey.job_id == job.sequence_id)
        .values(expires_at=job.expires_at)
    )


def expire_jobs(session: Session, now: datetime) -> int:
    """Retention (D14): a finished job past ``expiresAt`` becomes ``expired``, keeping its summary
    (counts, result, error) while its outcomes, inputs and idempotency keys are removed. Keys past
    their own expiry go too. Returns the number of jobs expired."""
    expired = session.scalars(
        select(Job.sequence_id).where(
            Job.state.in_(("completed", "failed", "cancelled")), Job.expires_at <= now
        )
    ).all()
    for start in range(0, len(expired), _INSERT_ROWS):
        ids = expired[start : start + _INSERT_ROWS]
        for table in (JobItem, JobInput, IdempotencyKey):
            session.execute(delete(table).where(table.job_id.in_(ids)))
        session.execute(
            update(Job)
            .where(Job.sequence_id.in_(ids))
            .values(state="expired")
            .execution_options(synchronize_session=False)
        )
    session.execute(delete(IdempotencyKey).where(IdempotencyKey.expires_at <= now))
    return len(expired)


def _empty_counts() -> dict[str, int]:
    return {status: 0 for status in ("applied", "rejected", "unprocessed")} | {
        action: 0 for action in ACTIONS
    }


# --- idempotency (P5) ----------------------------------------------------------------------------


def request_fingerprint(body: Any) -> str:
    """SHA-256 of the request's canonical JSON."""
    canonical = json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(canonical.encode()).hexdigest()


def replayed_job(
    session: Session, *, scope: str, workspace_key: str, key: str, fingerprint: str
) -> Job | None:
    """The finished job an earlier request with this key created, to answer again.

    ``None`` when the key is new or past retention (an expired key is removed and counts as new).
    The same key with another request is ``422 idempotency_key_reused``; one whose job is still
    running is ``409 idempotency_in_progress``.
    """
    stored = session.scalar(
        select(IdempotencyKey).where(
            IdempotencyKey.scope == scope,
            IdempotencyKey.workspace_key == workspace_key,
            IdempotencyKey.key == key,
        )
    )
    if stored is None:
        return None
    if stored.expires_at <= datetime.now(UTC):
        session.execute(
            delete(IdempotencyKey).where(IdempotencyKey.sequence_id == stored.sequence_id)
        )
        session.flush()
        return None
    job = session.get(Job, stored.job_id)
    if stored.fingerprint != fingerprint:
        raise api_error(
            422,
            "idempotency_key_reused",
            "This Idempotency-Key was used with a different request; nothing was run",
            {"jobId": job.id if job is not None else None},
        )
    if job is None or job.state not in FINISHED:
        raise api_error(
            409,
            "idempotency_in_progress",
            "The request with this Idempotency-Key is still running; retry later",
            {"jobId": job.id if job is not None else None},
            headers={"Retry-After": "1"},
        )
    return job


def remember_key(
    session: Session, *, scope: str, workspace_key: str, key: str, fingerprint: str, job: Job
) -> None:
    session.add(
        IdempotencyKey(
            scope=scope,
            workspace_key=workspace_key,
            key=key,
            fingerprint=fingerprint,
            job_id=job.sequence_id,
            expires_at=job.expires_at,
        )
    )
    session.flush()


# --- reads (P6) ----------------------------------------------------------------------------------


def load_job(session: Session, job_id: str) -> Job:
    job = session.scalar(select(Job).where(Job.id == job_id))
    if job is None:
        raise api_error(404, "job_not_found", f"Job '{job_id}' not found")
    return job


def release_public_ids(session: Session, jobs: Iterable[Job]) -> dict[int, str]:
    """The public ID of each job's pinned model release."""
    ids = {job.model_release_id for job in jobs}
    if not ids:
        return {}
    return dict(
        session.execute(
            select(ModelRelease.id, ModelRelease.public_id).where(ModelRelease.id.in_(ids))
        )
        .tuples()
        .all()
    )


def job_page(
    session: Session,
    *,
    workspace_key: str | None,
    kind: str | None,
    state: str | None,
    page: PageRequest,
    page_size: int,
) -> Page[Job]:
    """Jobs, newest first."""
    statement = select(Job)
    if workspace_key is not None:
        statement = statement.where(Job.workspace_key == workspace_key)
    if kind is not None:
        statement = statement.where(Job.kind == kind)
    if state is not None:
        statement = statement.where(Job.state == state)
    return paginate_statement(
        session,
        statement,
        keys=_JOB_KEYS,
        scope="jobs",
        filters={"workspaceKey": workspace_key, "kind": kind, "state": state},
        page=page,
        page_size=page_size,
        message="Job list cursor is invalid",
    )


def job_item_page(
    session: Session, job: Job, *, status: str | None, page: PageRequest, page_size: int
) -> Page[JobItem]:
    """A job's outcomes in item order."""
    statement = select(JobItem).where(JobItem.job_id == job.sequence_id)
    if status is not None:
        statement = statement.where(JobItem.status == status)
    return paginate_statement(
        session,
        statement,
        keys=_ITEM_KEYS,
        scope="job-items",
        filters={"jobId": job.id, "status": status},
        page=page,
        page_size=page_size,
        message="Job item cursor is invalid",
    )
