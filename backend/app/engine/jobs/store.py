"""Jobs, their item outcomes and idempotency keys (Base 0.9, ADR-036, INTEGRATION_API P).

An inline batch writes the job, its items' changes and their outcomes, and commits once, so a failed
request leaves no job behind. A background job is queued with its items as inputs (D27); the worker
commits each chunk's changes, outcomes and checkpoint (``processed``) together, so every item before
the checkpoint has its outcome and none after it has.

An import's inputs and outcomes carry the source and row of the file they came from (0.9 J3), so its
outcomes read by row. A previewed import waits in ``awaiting_confirmation`` (D87): confirming it
removes the preview's outcomes and queues it to be bound and run again; cancelling it ends it at once.
"""

import hashlib
import json
from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import JSON, delete, func, insert, literal, select, text, update
from sqlalchemy.orm import Session

from ...common.pagination import Page, PageRequest, integer_key, paginate_statement
from ...errors import api_error
from ...models.database import IdempotencyKey, Job, JobInput, JobItem, ModelRelease, RdmObject
from ..records.refusals import ELSEWHERE

ACTIONS = ("created", "updated", "unchanged", "deleted")
FINISHED = frozenset({"completed", "failed", "cancelled", "expired"})
AWAITING = "awaiting_confirmation"
# The states retention expires: the finished ones, and a preview nobody confirmed (D87).
EXPIRABLE = ("completed", "failed", "cancelled", AWAITING)

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
    total: int | None,
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
    if job.kind == "import" and outcomes:
        # The outcomes take their source and row from the inputs they ran (0.9 J3).
        session.execute(
            update(JobItem)
            .where(
                JobItem.job_id == job.sequence_id,
                JobItem.item_index.between(outcomes[0].index, outcomes[-1].index),
                JobInput.job_id == job.sequence_id,
                JobInput.item_index == JobItem.item_index,
            )
            .values(source_index=JobInput.source_index, row_number=JobInput.row_number)
            .execution_options(synchronize_session=False)
        )
    job.processed += len(outcomes)


def record_binding(
    session: Session,
    job: Job,
    *,
    rejected: int,
    items: int,
    report: list[dict[str, Any]] | None,
) -> None:
    """An import's file is bound (0.9 J2): its rejected rows are its first outcomes, already
    stored, and its items wait as inputs after them. The binding report goes on the job (D86)."""
    counts = _empty_counts() | dict(job.counts or {})
    counts["rejected"] += rejected
    job.counts = counts
    job.total = rejected + items
    job.processed = rejected
    job.stage = "applying"
    job.report = {
        **(job.report or {}),
        "bindingReport": report,
        "notices": _foreign_record_ids(session, job),
    }


def _foreign_record_ids(session: Session, job: Job) -> list[dict[str, Any]]:
    """Rows naming their records by IDs another workspace's records hold (0.9 J4a): an export
    sent to a second workspace of the instance. Record IDs are unique across the instance, so such
    rows cannot load here (D49); the job says so once, before its rows are read one by one. One
    statement over the job's inputs."""
    item_id = func.coalesce(JobInput.item["key"]["id"].as_string(), JobInput.item["id"].as_string())
    found = session.execute(
        select(RdmObject.workspace_key, func.count(func.distinct(JobInput.ref)))
        .join(RdmObject, RdmObject.id == item_id)
        .where(JobInput.job_id == job.sequence_id, RdmObject.workspace_key != job.workspace_key)
        .group_by(RdmObject.workspace_key)
        .order_by(RdmObject.workspace_key)
    ).all()
    counterparts = job.parameters.get("otherWorkspaceIds") == "counterparts"
    return [_foreign_notice(workspace_key, rows, counterparts) for workspace_key, rows in found]


def _foreign_notice(workspace_key: str, rows: int, counterparts: bool) -> dict[str, Any]:
    named = f"{rows} {'row names its record' if rows == 1 else 'rows name their records'}"
    if counterparts:
        # Asked for (0.9 J5, D96): the rows load as this workspace's own records.
        return {
            "code": "RECORD_IDS_AS_COUNTERPARTS",
            "message": f"{named} by IDs of workspace '{workspace_key}'; "
            f"{'it loads' if rows == 1 else 'they load'} as this workspace's own records, "
            "created on the first load and found again on the next.",
            "details": {"workspaceKey": workspace_key, "rows": rows},
        }
    return {
        "code": "RECORD_IDS_OF_ANOTHER_WORKSPACE",
        "message": f"{named} by IDs of workspace '{workspace_key}', so "
        f"{'it' if rows == 1 else 'they'} cannot load here. {ELSEWHERE}.",
        "details": {"workspaceKey": workspace_key, "rows": rows},
    }


PREVIEWED_KINDS = ("import", "batch")


def previewing(job: Job) -> bool:
    """Whether the job runs as a preview: an import or a batch (0.9 K2) sent with ``stage:
    preview`` and not confirmed."""
    return (
        job.kind in PREVIEWED_KINDS
        and job.parameters.get("stage") == "preview"
        and job.confirmed_at is None
    )


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
    ``reason``, written from its stored input in one statement. An import stopped before its file
    was bound has no items: its total becomes what it processed."""
    if job.total is None:
        job.total = job.processed
    remaining = job.total - job.processed
    if remaining:
        session.execute(
            insert(JobItem).from_select(
                ["job_id", "item_index", "ref", "source_index", "row_number", "status", "outcome"],
                select(
                    JobInput.job_id,
                    JobInput.item_index,
                    JobInput.ref,
                    JobInput.source_index,
                    JobInput.row_number,
                    literal("unprocessed"),
                    literal({"reason": reason}, JSON),
                ).where(JobInput.job_id == job.sequence_id, JobInput.item_index >= job.processed),
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
    keep_key_with(session, job)


def keep_key_with(session: Session, job: Job) -> None:
    """A key answers with its job for as long as the job is kept."""
    session.execute(
        update(IdempotencyKey)
        .where(IdempotencyKey.job_id == job.sequence_id)
        .values(expires_at=job.expires_at)
    )


def await_confirmation(
    session: Session, job: Job, report: dict[str, Any], *, retention_days: int
) -> None:
    """A preview's end (D87): the job waits for confirmation with the preview's summary, and is
    kept, unconfirmed, for the retention from now."""
    now = datetime.now(UTC)
    job.report = {**(job.report or {}), "preview": report}
    job.state = AWAITING
    job.stage = None
    job.expires_at = now + timedelta(days=retention_days)
    job.lease_owner = None
    job.lease_expires_at = None
    keep_key_with(session, job)


def confirm_job(session: Session, job: Job, check_context: Callable[[Job], None]) -> bool:
    """Confirm a waiting preview (D81, D87) under the job row's lock: its context is checked again
    by ``check_context``, which raises to refuse and leave it waiting; then the preview's outcomes
    go and the job is queued to run as an execution. An import's inputs go too, since it binds its
    file again; a batch keeps its stored items and runs them from the first (0.9 K2). ``False``
    when the job was confirmed before, which answers unchanged."""
    session.refresh(job, with_for_update=True)
    if job.confirmed_at is not None:
        return False
    imported = job.kind == "import"
    # Past its retention it is expired, whether or not the hourly sweep has marked it (0.9 R-F9).
    if job.state == "expired" or (job.state == AWAITING and job.expires_at <= datetime.now(UTC)):
        raise api_error(
            410,
            "JOB_EXPIRED",
            f"Job '{job.id}' passed its retention unconfirmed and its "
            f"{'file was' if imported else 'items were'} removed; send the "
            f"{'import' if imported else 'batch'} again",
        )
    if job.state != AWAITING:
        raise api_error(
            409,
            "JOB_NOT_AWAITING_CONFIRMATION",
            f"Job '{job.id}' is {job.state}; only a previewed import or batch waiting for "
            "confirmation is confirmed",
            {"jobId": job.id, "state": job.state},
        )
    check_context(job)
    if not imported:
        _carry_preview_claims(session, job)
    for table in (JobItem, JobInput) if imported else (JobItem,):
        session.execute(delete(table).where(table.job_id == job.sequence_id))
    job.confirmed_at = datetime.now(UTC)
    job.state = "queued"
    job.stage = None
    if imported:
        job.total = None
    job.processed = 0
    job.counts = _empty_counts()
    job.result = None
    return True


# The token a cascading delete item takes from its preview (0.9 K2b, D120); an item the preview did
# not delete itself (it went with another, or was refused) takes a token no impact matches, so a
# record standing on its own at execution is refused as changed rather than as never previewed.
_CARRY_TOKENS = text(
    """
    UPDATE job_inputs input
    SET item = (input.item::jsonb || jsonb_build_object('deletionPreviewToken',
        coalesce(outcome.outcome -> 'impact' ->> 'deletionPreviewToken', 'not-deleted-in-preview')
    ))::json
    FROM job_items outcome
    WHERE input.job_id = :job AND outcome.job_id = :job
        AND outcome.item_index = input.item_index
        AND input.item ->> 'op' = 'delete' AND (input.item ->> 'cascade')::boolean
        AND input.item ->> 'deletionPreviewToken' IS NULL
    """
)


# The set version a replacement takes from its preview (0.9 K3, D130): the version the preview found,
# from its outcome or its refusal, so execution refuses exactly the sets changed since.
_CARRY_SET_VERSIONS = text(
    """
    UPDATE job_inputs input
    SET item = (input.item::jsonb || jsonb_build_object('expectedRelationSetVersion',
        coalesce(
            outcome.outcome ->> 'previousRelationSetVersion',
            outcome.outcome -> 'error' -> 'details' ->> 'relationSetVersion'
        )::integer
    ))::json
    FROM job_items outcome
    WHERE input.job_id = :job AND outcome.job_id = :job
        AND outcome.item_index = input.item_index
        AND input.item ->> 'op' = 'replaceRelationSet'
        AND input.item ->> 'expectedRelationSetVersion' IS NULL
        AND coalesce(
            outcome.outcome ->> 'previousRelationSetVersion',
            outcome.outcome -> 'error' -> 'details' ->> 'relationSetVersion'
        ) IS NOT NULL
    """
)


def _carry_preview_claims(session: Session, job: Job) -> None:
    """What a batch's preview confirmed becomes each stored item's claim: a cascading delete's
    token (D120) and a set replacement's version (D130)."""
    session.execute(_CARRY_TOKENS, {"job": job.sequence_id})
    session.execute(_CARRY_SET_VERSIONS, {"job": job.sequence_id})


def applied_deletions(session: Session, job_id: str, object_ids: Iterable[str]) -> dict[str, int]:
    """The item of the job that deleted each of ``object_ids``, from its outcomes (0.9 K2b)."""
    wanted = sorted(set(object_ids))
    if not wanted:
        return {}
    object_id = JobItem.outcome["id"].as_string()
    return {
        found: index
        for found, index in session.execute(
            select(object_id, JobItem.item_index)
            .join(Job, Job.sequence_id == JobItem.job_id)
            .where(
                Job.id == job_id,
                JobItem.status == "applied",
                JobItem.outcome["action"].as_string() == "deleted",
                object_id.in_(wanted),
            )
        )
    }


def cancel_waiting(session: Session, job: Job, *, retention_days: int) -> None:
    """A waiting preview cancelled ends at once (D87, amending D28: the worker never claims a
    waiting job); its outcomes stay readable until retention."""
    session.execute(delete(JobInput).where(JobInput.job_id == job.sequence_id))
    job.cancel_requested_at = datetime.now(UTC)
    _close(job, "cancelled", retention_days=retention_days)
    keep_key_with(session, job)


def finish_export(
    session: Session, job: Job, output: dict[str, Any], *, retention_days: int
) -> None:
    """A completed export with its manifest (D52). ``result`` describes item outcomes, which an
    export has none of, so it stays empty."""
    job.output = output
    job.processed = job.total or 0
    _close(job, "completed", retention_days=retention_days)


def stop_export(
    session: Session,
    job: Job,
    *,
    state: str,
    error: dict[str, Any] | None,
    retention_days: int,
) -> None:
    """A cancelled or failed export: no output, its file removed by the worker."""
    job.error = error
    job.output = None
    _close(job, state, retention_days=retention_days)


def _close(job: Job, state: str, *, retention_days: int) -> None:
    now = datetime.now(UTC)
    job.state = state
    job.stage = None
    job.finished_at = now
    job.expires_at = now + timedelta(days=retention_days)
    job.lease_owner = None
    job.lease_expires_at = None


def expire_jobs(session: Session, now: datetime) -> int:
    """Retention (D14): a finished job, or a preview left unconfirmed (D87), past ``expiresAt``
    becomes ``expired``, keeping its summary (counts, result, error, report) while its outcomes,
    inputs and idempotency keys are removed. Keys past their own expiry go too. Returns the number
    of jobs expired."""
    # Locked, skipping a job a confirmation holds (0.9 R-F9): one that commits first is then
    # queued and no longer expirable, and one that waits finds it expired.
    expired = session.scalars(
        select(Job.sequence_id)
        .where(Job.state.in_(EXPIRABLE), Job.expires_at <= now)
        .with_for_update(skip_locked=True)
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
            "IDEMPOTENCY_KEY_REUSED",
            "This Idempotency-Key was used with a different request; nothing was run",
            {"jobId": job.id if job is not None else None},
        )
    # A preview waiting for confirmation is the request's answer too.
    if job is None or (job.state not in FINISHED and job.state != AWAITING):
        raise api_error(
            409,
            "IDEMPOTENCY_IN_PROGRESS",
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
        raise api_error(404, "JOB_NOT_FOUND", f"Job '{job_id}' not found")
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
    session: Session,
    job: Job,
    *,
    status: str | None,
    page: PageRequest,
    page_size: int,
    ref: str | None = None,
) -> Page[JobItem]:
    """A job's outcomes in item order; ``ref`` keeps those of one row (``{sheet}!{row}``)."""
    statement = select(JobItem).where(JobItem.job_id == job.sequence_id)
    if status is not None:
        statement = statement.where(JobItem.status == status)
    if ref is not None:
        statement = statement.where(JobItem.ref == ref)
    return paginate_statement(
        session,
        statement,
        keys=_ITEM_KEYS,
        scope="job-items",
        filters={"jobId": job.id, "status": status, "ref": ref},
        page=page,
        page_size=page_size,
        message="Job item cursor is invalid",
    )
