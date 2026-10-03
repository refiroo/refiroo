"""Batches and jobs (Base 0.9, ADR-036, INTEGRATION_API P and B).

``write_router`` creates and cancels jobs and is registered only with ``INTEGRATION_JOBS_ENABLED``
(D10); ``router`` reads them and is always registered.
"""

from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Header, Query, Request, Response
from fastapi.responses import JSONResponse

from ...common.pagination import FIRST_PAGE
from ...engine.jobs.background import request_cancel, submit_background_batch
from ...engine.jobs.inline import BatchLimits, check_batch_request, submit_inline_batch
from ...engine.jobs.store import job_item_page, job_page, load_job
from ...models.commands import BatchRequest
from ..dependencies import DbSession
from ..paging import PageQuery
from ..presenters import batch_response, job_responses
from ..presenters import job_item_page as present_job_items
from ..presenters import job_page as present_jobs
from ..schemas.jobs import BatchResponse, JobItemPage, JobPage, JobResponse

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
    ``GET /jobs/{jobId}/items``. Retrying a create without an ``id`` and without an
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
    with ``job_cancelled``, chunks committed before stay applied, and an ``atomic`` job rolls back
    completely. A finished job answers ``409 job_finished``.
    """
    job = request_cancel(session, job_id)
    _wake_worker(request)
    return job_responses(session, [job])[0]


def _wake_worker(request: Request) -> None:
    worker = getattr(request.app.state, "job_worker", None)
    if worker is not None:
        worker.wake()


@router.get("/jobs", response_model=JobPage)
def list_jobs(
    session: DbSession,
    paging: PageQuery,
    workspace_key: str | None = Query(default=None, alias="workspaceKey"),
    kind: Literal["batch", "import", "export"] | None = None,
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
    page_size: int = Query(default=1000, ge=1, le=1000, alias="pageSize"),
) -> JobItemPage:
    """A job's outcomes in item order."""
    job = load_job(session, job_id)
    return present_job_items(
        job_item_page(session, job, status=status, page=paging, page_size=page_size)
    )
