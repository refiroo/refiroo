"""Batches and jobs (Base 0.9, ADR-036, INTEGRATION_API P and B).

``write_router`` creates and cancels jobs and is registered only with ``INTEGRATION_JOBS_ENABLED``
(D10); ``router`` reads them and is always registered.
"""

import asyncio
import base64
import json
import logging
from collections.abc import AsyncIterator
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Header, Query, Request, Response
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse

from ...common.pagination import FIRST_PAGE
from ...engine.jobs.background import confirm_preview, request_cancel, submit_background_batch
from ...engine.jobs.events import JobListener
from ...engine.jobs.exports import FORMATS, submit_export
from ...engine.jobs.files import JobFiles
from ...engine.jobs.inline import BatchLimits, check_batch_request, submit_inline_batch
from ...engine.jobs.store import job_item_page, job_page, load_job
from ...engine.model.migrations import confirm_migration
from ...errors import api_error
from ...models.commands import BatchRequest
from ...models.exports import ExportRequest
from ..dependencies import DbSession
from ..paging import PageQuery
from ..presenters import batch_response, job_responses
from ..presenters import job_item_page as present_job_items
from ..presenters import job_page as present_jobs
from ..projections.job_rows import job_row_page, migration_row_page
from ..schemas.jobs import (
    BatchResponse,
    JobConfirmation,
    JobItemPage,
    JobPage,
    JobResponse,
    JobRowPage,
    MigrationRowPage,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["jobs"])
write_router = APIRouter(prefix="/api/v1", tags=["jobs"])

# Every inline batch's outcomes fit the first page at the default limit (§B5).
INLINE_PAGE_SIZE = 1000


async def _body_bytes(request: Request) -> int:
    return len(await request.body())


@write_router.post(
    "/batches",
    response_model=BatchResponse,
    responses={
        200: {
            "headers": {
                "Idempotent-Replayed": {
                    "description": "true when the response is an earlier request's job, answered "
                    "again for the same Idempotency-Key",
                    "schema": {"type": "string"},
                }
            }
        },
        202: {
            "model": JobResponse,
            "description": "A background batch, queued: follow it at GET /jobs/{jobId}",
            "headers": {
                "Idempotent-Replayed": {
                    "description": "true when the job is an earlier request's, answered again "
                    "for the same Idempotency-Key",
                    "schema": {"type": "string"},
                }
            },
        },
    },
)
def create_batch(
    payload: BatchRequest,
    request: Request,
    response: Response,
    session: DbSession,
    body_bytes: Annotated[int, Depends(_body_bytes)],
    idempotency_key: str | None = Header(
        default=None,
        alias="Idempotency-Key",
        min_length=1,
        max_length=200,
        pattern=r"^[\x20-\x7e]+$",
        description="Answer a retry with the first request's job instead of running it again",
    ),
) -> BatchResponse | JSONResponse:
    """Run a batch of object and relationship writes as a job.

    ``run: inline`` answers 200 with the finished job and its outcomes, whatever its
    ``job.result``: read ``result`` to learn whether every item applied. ``run: background``
    answers 202 with the queued job; the worker applies it in chunks, and its outcomes page at
    ``GET /jobs/{jobId}/items``. A background batch sent with ``stage: preview`` runs its items
    without writing anything and waits in ``awaiting_confirmation`` with ``preview``; ``POST
    /jobs/{jobId}/confirm`` applies it (0.9 K2). Retrying a create without an ``id`` and without an
    ``Idempotency-Key`` can create the record twice.
    """
    limits: BatchLimits = request.app.state.batch_limits
    check_batch_request(payload, body_bytes, limits)
    if payload.run == "background":
        job, replayed = submit_background_batch(
            session,
            payload,
            idempotency_key=idempotency_key,
            retention_days=limits.retention_days,
        )
        _wake_worker(request)
        return JSONResponse(
            job_responses(session, [job])[0].model_dump(mode="json"),
            status_code=202,
            headers={"Idempotent-Replayed": "true"} if replayed else None,
        )
    job, replayed = submit_inline_batch(
        session,
        payload,
        idempotency_key=idempotency_key,
        retention_days=limits.retention_days,
    )
    if replayed:
        response.headers["Idempotent-Replayed"] = "true"
    items = job_item_page(session, job, status=None, page=FIRST_PAGE, page_size=INLINE_PAGE_SIZE)
    return batch_response(session, job, items)


@write_router.post("/jobs/{job_id}/cancel", response_model=JobResponse, status_code=202)
def cancel_job(job_id: str, request: Request, session: DbSession) -> JobResponse:
    """Ask for the job to be cancelled; ``cancelRequestedAt`` is set at once.

    The worker carries it out at the job's next chunk: items not reached become ``unprocessed``
    with ``JOB_CANCELLED``, chunks committed before stay applied, and an ``atomic`` job rolls back
    completely. An import preview awaiting confirmation is cancelled at once, its file removed and
    its preview's outcomes kept to read. A finished job answers ``409 JOB_FINISHED``.
    """
    limits: BatchLimits = request.app.state.batch_limits
    job = request_cancel(
        session, job_id, files=request.app.state.job_files, retention_days=limits.retention_days
    )
    _wake_worker(request)
    return job_responses(session, [job])[0]


@write_router.post("/jobs/{job_id}/confirm", response_model=JobResponse, status_code=202)
def confirm_job(
    job_id: str,
    request: Request,
    session: DbSession,
    payload: JobConfirmation | None = None,
) -> JobResponse:
    """Confirm an import (0.9 J3) or a background batch (0.9 K2) previewed with ``stage: preview``,
    or a migration (0.11 V1).

    The job is queued again and runs as ``stage: execute`` would: an import's stored file is bound
    anew, a batch's stored items run from the first. Data changed since the preview counts, and
    execution's outcomes, which replace the preview's, are authoritative. Confirming a job already confirmed answers with it unchanged. Refused, leaving
    the job waiting: ``409 MODEL_RELEASE_CHANGED``, ``404 WORKSPACE_NOT_FOUND``, ``404
    CHANGE_SET_NOT_FOUND``, ``409 CHANGE_SET_VERSION_CONFLICT`` (the change set changed since the
    request's ``expectedChangeSetVersion``). A job not waiting is ``409
    JOB_NOT_AWAITING_CONFIRMATION`` naming its state; a preview past its retention ``410
    JOB_EXPIRED``.

    A migration names its preview's ``expectedVersion`` and ``feedPosition``
    (``expectedFeedPosition``) and, when it removes anything, ``acceptLoss: true``; the worker then
    applies it and switches the workspace's release in one transaction. Refused, leaving it
    waiting: ``409 MIGRATION_REVIEW_STALE`` (the workspace was written or its model changed since
    the preview), ``409 MIGRATION_HAS_REFUSALS``, ``422 MIGRATION_LOSS_NOT_ACCEPTED``.
    """
    job = load_job(session, job_id)
    if job.kind == "migration":
        confirmation = payload or JobConfirmation()
        job = confirm_migration(
            session,
            job_id,
            expected_version=confirmation.expectedVersion,
            expected_feed_position=confirmation.expectedFeedPosition,
            accept_loss=confirmation.acceptLoss,
        )
    else:
        job = confirm_preview(session, job_id)
    _wake_worker(request)
    return job_responses(session, [job])[0]


@write_router.post("/exports", response_model=JobResponse, status_code=202, tags=["exports"])
def create_export(payload: ExportRequest, request: Request, session: DbSession) -> JobResponse:
    """Export a stated scope of one workspace as a background job (0.9 J1).

    Answers 202 with the queued job. Everything in the file is read at one instant: a live
    export's ``output.feedPosition`` is the feed head it equals, so a reader follows the feed from
    there. When the job is ``completed``, ``output`` describes the file and
    ``GET /jobs/{jobId}/output`` serves it; a cancelled or failed export has no file. JSON Lines
    holds batch items (``upsert`` by ID with ``expectedVersion``, then ``ensureRelation``), so the
    file sent back to ``POST /batches`` changes nothing; CSV and XLSX hold the same rows in one
    table layout. A criterion the model cannot answer is ``422 INVALID_QUERY`` at its JSON pointer.
    """
    limits: BatchLimits = request.app.state.batch_limits
    job = submit_export(session, payload, retention_days=limits.retention_days)
    worker = getattr(request.app.state, "export_worker", None)
    if worker is not None:
        worker.wake()
    return job_responses(session, [job])[0]


def _wake_worker(request: Request) -> None:
    for name in ("job_worker", "export_worker"):
        worker = getattr(request.app.state, name, None)
        if worker is not None:
            worker.wake()


@router.get("/jobs", response_model=JobPage)
def list_jobs(
    session: DbSession,
    paging: PageQuery,
    workspace_key: str | None = Query(default=None, alias="workspaceKey"),
    kind: Literal[
        "batch", "import", "export", "profile", "dryRun", "inference", "profileCheck", "migration"
    ]
    | None = None,
    state: Literal[
        "queued", "running", "awaiting_confirmation", "completed", "failed", "cancelled", "expired"
    ]
    | None = None,
    page_size: int = Query(default=50, ge=1, le=500, alias="pageSize"),
) -> JobPage:
    """Jobs, newest first."""
    return present_jobs(
        session,
        job_page(
            session,
            workspace_key=workspace_key,
            kind=kind,
            state=state,
            page=paging,
            page_size=page_size,
        ),
    )


@router.get("/jobs/{job_id}", response_model=JobResponse)
def get_job(job_id: str, session: DbSession) -> JobResponse:
    return job_responses(session, [load_job(session, job_id)])[0]


@router.get("/jobs/{job_id}/items", response_model=JobItemPage)
def list_job_items(
    job_id: str,
    session: DbSession,
    paging: PageQuery,
    status: Literal["applied", "rejected", "unprocessed"] | None = None,
    ref: str | None = Query(
        default=None, description="One row's outcomes, as ``{sheet}!{row}`` (an import's items)"
    ),
    page_size: int = Query(default=1000, ge=1, le=1000, alias="pageSize"),
) -> JobItemPage:
    """A job's outcomes in item order."""
    job = load_job(session, job_id)
    return present_job_items(
        job_item_page(session, job, status=status, ref=ref, page=paging, page_size=page_size)
    )


@router.get("/jobs/{job_id}/rows", response_model=JobRowPage | MigrationRowPage)
def list_job_rows(
    job_id: str,
    session: DbSession,
    paging: PageQuery,
    status: Literal[
        "applied", "rejected", "unprocessed", "conversion", "reclassified", "loss", "refused"
    ]
    | None = Query(
        default=None,
        description="An import's rows whose worst item has this status, or a migration's items "
        "of this outcome",
    ),
    page_size: int = Query(default=500, ge=1, le=1000, alias="pageSize"),
) -> JobRowPage | MigrationRowPage:
    """An import's outcomes by row of its file, in source then row order (0.9 J3): each row's
    worst status, its applied items by action and its rejected and unprocessed outcomes. A
    migration's items in item order (0.11 V1): every conversion, type change, loss and refusal.
    A status of the other kind is ``422 INVALID_PAGE_PARAMETER``. A batch or an export has none
    (``404 JOB_HAS_NO_ROWS``)."""
    job = load_job(session, job_id)
    if job.kind == "migration":
        return migration_row_page(session, job, outcome=status, page=paging, page_size=page_size)
    return job_row_page(session, job, status=status, page=paging, page_size=page_size)


@router.get(
    "/jobs/{job_id}/output",
    response_class=FileResponse,
    responses={
        200: {
            "description": "The completed export's file, with its SHA-256 in ETag and Repr-Digest",
            "content": {content_type.split(";")[0]: {} for content_type, _ in FORMATS.values()},
        }
    },
)
def get_job_output(job_id: str, request: Request, session: DbSession) -> FileResponse:
    """A completed export's file (0.9 J1). A job that is not completed has none (``409
    JOB_NOT_COMPLETED`` naming its state), so a partial file cannot be taken for a complete one; a
    batch has none (``404 JOB_HAS_NO_OUTPUT``); retention removes it (``410 JOB_EXPIRED``)."""
    job = load_job(session, job_id)
    if job.kind != "export":
        raise api_error(
            404, "JOB_HAS_NO_OUTPUT", f"Job '{job.id}' is a {job.kind}; only an export has a file"
        )
    if job.state == "expired":
        raise api_error(
            410,
            "JOB_EXPIRED",
            f"Export '{job.id}' passed its retention and its file was removed; request it again",
        )
    if job.state != "completed" or job.output is None:
        raise api_error(
            409,
            "JOB_NOT_COMPLETED",
            f"Export '{job.id}' is {job.state}; its file is served once it is completed",
            {"state": job.state},
        )
    output = job.output
    files: JobFiles = request.app.state.job_files
    path = files.final(job.id, FORMATS[output["format"]][1])
    if not path.is_file():
        logger.warning("The file of export %s is missing from %s", job.id, files.directory)
        raise api_error(
            410,
            "JOB_OUTPUT_MISSING",
            f"The file of export '{job.id}' is no longer in the job file directory; request the "
            "export again. Operators: check JOB_FILE_DIR and what removes files from it",
        )
    digest = bytes.fromhex(output["sha256"])
    return FileResponse(
        path,
        media_type=output["contentType"],
        filename=f"export-{job.id}.{FORMATS[output['format']][1]}",
        headers={
            "ETag": f'"{output["sha256"]}"',
            "Repr-Digest": f"sha-256=:{base64.b64encode(digest).decode()}:",
        },
    )


# A stream sends a comment this often while its job does not change, so proxies keep it open.
KEEP_ALIVE_SECONDS = 15.0
FINAL_STATES = frozenset({"completed", "failed", "cancelled", "expired"})


@router.get(
    "/jobs/{job_id}/events",
    response_class=StreamingResponse,
    responses={
        200: {
            "description": "Server-sent events: `event: job` with the job as `GET /jobs/{jobId}` "
            "answers it, at once and after each committed change; the stream ends after a final state",
            "content": {"text/event-stream": {}},
        }
    },
)
async def job_events(job_id: str, request: Request) -> StreamingResponse:
    """Follow a job as it changes (0.9 J1u): the job at once, then again after each committed change
    of its state, progress, cancel request or output; the stream ends once the job is completed,
    failed, cancelled or expired. Nothing is polled: the database tells the engine of each change
    (D58). A comment line every 15 s keeps an idle stream open through proxies."""
    listener: JobListener = request.app.state.job_listener
    subscription = listener.subscribe(job_id)
    try:
        first = await run_in_threadpool(_job_body, request, job_id)
    except BaseException:
        listener.unsubscribe(subscription)
        raise

    async def stream() -> AsyncIterator[str]:
        try:
            body = first
            yield _event(body)
            while body["state"] not in FINAL_STATES:
                try:
                    await asyncio.wait_for(subscription.woken.wait(), KEEP_ALIVE_SECONDS)
                except TimeoutError:
                    yield ": keep-alive\n\n"
                    continue
                subscription.woken.clear()
                current = await run_in_threadpool(_job_body, request, job_id)
                if current != body:
                    body = current
                    yield _event(body)
        finally:
            listener.unsubscribe(subscription)

    return StreamingResponse(
        stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


def _job_body(request: Request, job_id: str) -> dict:
    """The job as ``GET /jobs/{id}`` answers it. A stream outlives any one request session, so each
    read opens a short session of its own instead of holding a connection while the job runs."""
    with request.app.state.session_factory() as session:
        return job_responses(session, [load_job(session, job_id)])[0].model_dump(mode="json")


def _event(body: dict) -> str:
    return f"event: job\ndata: {json.dumps(body, separators=(',', ':'))}\n\n"
