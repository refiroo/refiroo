"""Moves between workspaces whose models differ (Product 0.11 X2, D114–D123, API.md § Moves).

``POST /moves`` queues a move's dry run: a job of kind ``move`` whose rows say what each selected
record and relationship becomes in the target, read at ``GET /jobs/{jobId}/rows``, and whose
summary is the job's ``move``. Registered with both gates (D14, D111): ``INTEGRATION_JOBS_ENABLED``
and ``MODEL_ADMIN_MUTATIONS_ENABLED``.
"""

from fastapi import APIRouter, Request

from ...engine.moves.move_job import submit_move
from ...models.moves import MoveRequest
from ..access import (
    MOVE,
    AuthorizedRoute,
    requires,
)
from ..dependencies import DbSession
from ..presenters import job_responses
from ..schemas.jobs import JobResponse

router = APIRouter(route_class=AuthorizedRoute, prefix="/api/v1", tags=["moves"])


@router.post("/moves", response_model=JobResponse, status_code=202)
@requires("moves.create", at=MOVE)
def start_move(payload: MoveRequest, request: Request, session: DbSession) -> JobResponse:
    """Starts a move: what each record the ``selection`` names (the whole workspace when empty;
    types with criteria, a subtree, records by ID, combined) becomes in the target workspace through
    the mapping at ``mapping.expectedVersion``, read from the source's live data or a publication
    (``sourceAt``). ``mode`` is ``copy`` (the source is untouched) or ``move`` (the copy, plus a
    change set of the source deleting what was loaded). ``stage`` is ``preview`` (the default: a dry
    run that writes nothing, completing with one row per record and relationship, which waits for
    ``POST /jobs/{jobId}/confirm``) or ``execute`` (it loads at once). Either way it loads into a
    new change set of the target. Answers 202 with a queued ``move`` job. Refused before a job
    exists: ``422 MOVE_SAME_WORKSPACE``, ``404 WORKSPACE_NOT_FOUND``, ``409 WORKSPACE_RETIRED``,
    ``404 MODEL_MAPPING_NOT_FOUND``, ``409 MOVE_MAPPING_CHANGED`` (with ``currentVersion``), ``422
    MODEL_MAPPING_MODEL_MISMATCH``, ``422 MOVE_MAPPING_HAS_PROBLEMS`` (the mapping's problems
    against the releases the two workspaces run), ``404 PUBLICATION_NOT_FOUND``, ``422
    INVALID_QUERY`` and ``404 OBJECT_NOT_FOUND`` (at ``details.path`` in the selection)."""
    job = submit_move(
        session, payload, retention_days=request.app.state.batch_limits.retention_days
    )
    worker = getattr(request.app.state, "job_worker", None)
    if worker is not None:
        worker.wake()
    return job_responses(session, [job])[0]
