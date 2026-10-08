"""Submitting a batch: the request's limits and its idempotency key; and running it inline, in one
transaction.

An inline job, its items' changes, their outcomes and the idempotency key commit together, so a
request that fails (a refused context, a model release activated meanwhile) leaves no job, and its
key names a finished job. A background job is queued with its key (``background.py``), which answers
``IDEMPOTENCY_IN_PROGRESS`` until the job finishes.
"""

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ...errors import api_error
from ...models.commands import BatchRequest
from ...models.database import ChangeSet, Job
from .batches import BatchContext, check_batch_context, open_batch_context, run_batch
from .store import finish_job, remember_key, replayed_job, request_fingerprint, start_job

BATCHES_SCOPE = "POST /batches"


@dataclass(frozen=True)
class BatchLimits:
    """D13, D14 and D30, as configured (``GET /capabilities`` reports them)."""

    max_items: int
    max_bytes: int
    atomic_max_items: int
    retention_days: int
    background_max_items: int
    background_max_bytes: int
    chunk_items: int
    import_max_bytes: int
    preview_max_items: int = 10_000


def check_batch_request(request: BatchRequest, body_bytes: int, limits: BatchLimits) -> None:
    """Refuse a batch over its run's limits, before anything is read or written."""
    count = len(request.items)
    inline = request.run == "inline"
    items_setting, max_items = (
        ("BATCH_MAX_ITEMS", limits.max_items)
        if inline
        else ("BACKGROUND_JOB_MAX_ITEMS", limits.background_max_items)
    )
    bytes_setting, max_bytes = (
        ("BATCH_MAX_BYTES", limits.max_bytes)
        if inline
        else ("BATCH_BACKGROUND_MAX_BYTES", limits.background_max_bytes)
    )
    for setting, maximum, applies in (
        (items_setting, max_items, True),
        ("ATOMIC_JOB_MAX_ITEMS", limits.atomic_max_items, request.policy == "atomic"),
    ):
        if applies and count > maximum:
            raise api_error(
                413,
                "BATCH_TOO_LARGE",
                f"The batch has {count} items; at most {maximum} run in one {request.run} job",
                {"setting": setting, "maximum": maximum, "items": count},
            )
    if body_bytes > max_bytes:
        raise api_error(
            413,
            "BATCH_TOO_LARGE",
            f"The batch body has {body_bytes} bytes; at most {max_bytes} run in one "
            f"{request.run} job",
            {"setting": bytes_setting, "maximum": max_bytes, "bytes": body_bytes},
        )


def submit_inline_batch(
    session: Session,
    request: BatchRequest,
    *,
    idempotency_key: str | None,
    retention_days: int,
) -> tuple[Job, bool]:
    """Run the batch and commit; or, for a key seen before, the job it ran. ``True`` marks a
    replayed job."""
    fingerprint = request_fingerprint(request.model_dump(mode="json", exclude_unset=True))
    replayed = earlier_job(session, request, idempotency_key, fingerprint)
    if replayed is not None:
        return replayed, True
    context = open_batch_context(session, request)
    job = start_job(
        session,
        kind="batch",
        workspace_key=context.workspace_key,
        change_set_id=context.change_set.id if context.change_set else None,
        model_release_id=context.model_release_id,
        parameters=batch_parameters(request),
        total=len(request.items),
        retention_days=retention_days,
    )
    replayed = keep_key(session, context, idempotency_key, fingerprint, job)
    if replayed is not None:
        return replayed, True
    outcomes = run_batch(session, context, request, job.id)
    change_set_version = None
    if context.change_set is not None:
        change_set_version = session.scalar(
            select(ChangeSet.version).where(ChangeSet.id == context.change_set.id)
        )
    finish_job(
        session,
        job,
        outcomes,
        retention_days=retention_days,
        change_set_version=change_set_version,
    )
    session.commit()
    return job, False


def batch_parameters(request: BatchRequest) -> dict[str, str]:
    return {
        "policy": request.policy,
        "run": request.run,
        "stage": request.stage,
        "onExisting": request.onExisting,
        "otherWorkspaceIds": request.otherWorkspaceIds,
    }


def earlier_job(
    session: Session, request: BatchRequest, idempotency_key: str | None, fingerprint: str
) -> Job | None:
    """The finished job an earlier request with this key ran (P5), or ``None`` to run this one."""
    if idempotency_key is None:
        return None
    return replayed_job(
        session,
        scope=BATCHES_SCOPE,
        workspace_key=_workspace_key(session, request),
        key=idempotency_key,
        fingerprint=fingerprint,
    )


def keep_key(
    session: Session,
    context: BatchContext,
    idempotency_key: str | None,
    fingerprint: str,
    job: Job,
) -> Job | None:
    """Store the key with the new job; a concurrent request that stored it first answers instead
    (its job is returned, and this transaction is rolled back)."""
    if idempotency_key is None:
        return None
    try:
        remember_key(
            session,
            scope=BATCHES_SCOPE,
            workspace_key=context.workspace_key,
            key=idempotency_key,
            fingerprint=fingerprint,
            job=job,
        )
    except IntegrityError:
        # A concurrent request with the key committed first: answer as its retry.
        session.rollback()
        replayed = replayed_job(
            session,
            scope=BATCHES_SCOPE,
            workspace_key=context.workspace_key,
            key=idempotency_key,
            fingerprint=fingerprint,
        )
        if replayed is None:
            raise
        return replayed
    return None


def _workspace_key(session: Session, request: BatchRequest) -> str:
    """The workspace an idempotency key is scoped to, read without the write's checks, so a
    finished job is answered again even if its workspace has since been retired."""
    check_batch_context(request)
    if request.changeSetId is None:
        return request.workspaceKey
    workspace_key = session.scalar(
        select(ChangeSet.workspace_key).where(ChangeSet.id == str(request.changeSetId))
    )
    if workspace_key is None:
        raise api_error(
            404, "CHANGE_SET_NOT_FOUND", f"Change set '{request.changeSetId}' not found"
        )
    return workspace_key
