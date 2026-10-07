"""Background batches: queued with their items (D27), cancelled on request (D28), and the context
each chunk writes in (INTEGRATION_API P6).

A background batch answers once it is queued: the job, its items as inputs and its idempotency key
commit together, and the worker (``worker.py``) runs it chunk by chunk. A request refused before
that (a context, a stale change set claim, a release activated meanwhile) leaves no job.
"""

from datetime import UTC, datetime

from sqlalchemy import func, update
from sqlalchemy.orm import Session

from ...errors import ApiError, api_error
from ...models.commands import BatchRequest
from ...models.database import Job
from ..change_sets.access import change_set_model, load_change_set
from ..model.registry import resolve_model_snapshot
from ..workspaces.catalogue import resolve_workspace
from .batches import BatchContext, open_batch_context
from .files import JobFiles
from .inline import batch_parameters, earlier_job, keep_key
from .store import (
    AWAITING,
    cancel_waiting,
    confirm_job,
    load_job,
    request_fingerprint,
    start_job,
    store_inputs,
)

CANCELLABLE = ("queued", "running")


def submit_background_batch(
    session: Session,
    request: BatchRequest,
    *,
    idempotency_key: str | None,
    retention_days: int,
) -> tuple[Job, bool]:
    """Queue the batch and commit; or, for a key seen before, the job it queued. ``True`` marks a
    replayed job."""
    fingerprint = request_fingerprint(request.model_dump(mode="json", exclude_unset=True))
    replayed = earlier_job(session, request, idempotency_key, fingerprint)
    if replayed is not None:
        return replayed, True
    context = open_batch_context(session, request)
    if (
        context.change_set is not None
        and context.change_set.version != request.expectedChangeSetVersion
    ):
        raise api_error(409, "CHANGE_SET_VERSION_CONFLICT", "Change set version has changed")
    job = start_job(
        session,
        kind="batch",
        workspace_key=context.workspace_key,
        change_set_id=context.change_set.id if context.change_set else None,
        model_release_id=context.model_release_id,
        parameters=batch_parameters(request),
        total=len(request.items),
        retention_days=retention_days,
        queued=True,
        # The version the job claims when its first chunk runs.
        change_set_version=request.expectedChangeSetVersion,
    )
    store_inputs(
        session,
        job,
        [item.model_dump(mode="json", exclude_unset=True) for item in request.items],
    )
    replayed = keep_key(session, context, idempotency_key, fingerprint, job)
    if replayed is not None:
        return replayed, True
    session.commit()
    return job, False


def request_cancel(session: Session, job_id: str, *, files: JobFiles, retention_days: int) -> Job:
    """Ask the worker to cancel the job (D28). One short write: the worker finishes the job, so
    the request never waits for a chunk. A preview waiting for confirmation, which no worker
    claims, is cancelled at once and its file removed (D87)."""
    job = load_job(session, job_id)
    if job.state == AWAITING:
        session.refresh(job, with_for_update=True)
        if job.state == AWAITING:
            cancel_waiting(session, job, retention_days=retention_days)
            session.commit()
            files.remove(job.id)
            session.refresh(job)
            return job
    result = session.execute(
        update(Job)
        .where(Job.sequence_id == job.sequence_id, Job.state.in_(CANCELLABLE))
        .values(cancel_requested_at=func.coalesce(Job.cancel_requested_at, datetime.now(UTC)))
        .execution_options(synchronize_session=False)
    )
    if result.rowcount != 1:
        session.rollback()
        session.refresh(job)
        raise api_error(
            409,
            "JOB_FINISHED",
            f"Job '{job.id}' is {job.state}; only a queued, running or waiting job can be "
            "cancelled",
            {"jobId": job.id, "state": job.state},
        )
    session.commit()
    session.refresh(job)
    return job


def confirm_preview(session: Session, job_id: str) -> Job:
    """Confirm a previewed import (D87) and commit: it is queued to bind its file again and run as
    ``stage: execute`` would (D81). A job confirmed before answers unchanged. Its context is
    checked again as at submission, and a refusal leaves it waiting: a release activated since,
    a retired workspace, a missing change set, or a change set changed since the request's
    ``expectedChangeSetVersion``."""
    job = load_job(session, job_id)

    def check(job: Job) -> None:
        try:
            context = open_job_context(session, job)
        except ApiError as error:
            if error.code != "MODEL_RELEASE_CHANGED":
                raise
            raise api_error(
                409,
                "MODEL_RELEASE_CHANGED",
                "The model release this preview ran under is no longer the one its context uses; "
                "send the import again",
            ) from None
        if context.change_set is not None and context.change_set.version != job.change_set_version:
            raise api_error(
                409,
                "CHANGE_SET_VERSION_CONFLICT",
                "The change set changed since the import was sent; send it again with the "
                "change set's current version",
                {"currentVersion": context.change_set.version},
            )

    if confirm_job(session, job, check):
        session.commit()
    else:
        session.rollback()
    session.refresh(job)
    return job


def open_job_context(session: Session, job: Job) -> BatchContext:
    """Where the job's next chunk writes, under the release the job pinned.

    A release activated since (live), or a change set moved to another release, is ``409
    model_release_changed``; a workspace retired since is its single write's refusal.
    """
    if job.change_set_id is None:
        workspace = resolve_workspace(session, job.workspace_key, require_active=True)
        snapshot = resolve_model_snapshot(session)
        if snapshot.release_db_id != job.model_release_id:
            raise _release_changed()
        return BatchContext(
            workspace.key, None, snapshot.model, snapshot.release_db_id, snapshot.model_hash
        )
    change_set = load_change_set(session, job.change_set_id, for_update=True)
    if change_set.model_release_id != job.model_release_id:
        raise _release_changed()
    return BatchContext(
        change_set.workspace_key,
        change_set,
        change_set_model(session, change_set),
        change_set.model_release_id,
        None,
    )


def _release_changed():
    return api_error(
        409,
        "MODEL_RELEASE_CHANGED",
        "The model release this job was created under is no longer the one its context uses; "
        "the job stopped, and the items it applied before stay applied",
    )
