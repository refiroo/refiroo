"""A model draft's inference (Product 0.10 A6, D86–D98): propose a model and its mapping from the
draft's source file, read the proposals, and apply them as steps of the draft's history.

Registered with ``dry_run_router``'s conditions: model administration (a draft) and integration
jobs (the inference is a job) both enabled.
"""

from fastapi import APIRouter, Query, Request
from fastapi.responses import JSONResponse

from ...engine.model.drafts import load_draft
from ...engine.sources.inference.one_list import propose_list
from ...engine.sources.inference.run import (
    InvalidDraft,
    apply_inference,
    proposal_page,
    read_inference,
    submit_inference,
)
from ...errors import api_error
from ...models.sources import InferenceApplicationRequest, InferenceRequest, ListProposalRequest
from ..access import (
    INSTANCE,
    AuthorizedRoute,
    requires,
)
from ..dependencies import DbSession
from ..paging import PageQuery
from ..presenters import diagnostic_details
from ..schemas.model import ModelDraftStepResponse
from ..schemas.sources import (
    InferenceResponse,
    ListProposalResponse,
    ProposalPage,
    ProposalResponse,
)
from ..steps import step_response

router = APIRouter(route_class=AuthorizedRoute, prefix="/api/v1", tags=["model administration"])


@router.post("/model-drafts/{draft_id}/inference", response_model=InferenceResponse, status_code=202)
@requires("model.author", at=INSTANCE)
def run_inference(draft_id: str, payload: InferenceRequest, request: Request, session: DbSession) -> JSONResponse:
    """Propose a model and its mapping from the draft's current source file (D87, D90, D91).

    Answers 202 with the inference ``checking``; ``GET /model-drafts/{id}/inference`` reads it and
    ``…/inference/proposals`` lists its proposals once completed. Nothing is applied: ``POST
    …/inference/application`` applies them. An inference still running for the draft is cancelled.
    Refused: ``404 SOURCE_FILE_NOT_FOUND`` for a draft without a file, ``409
    SOURCE_FILE_PROFILE_NOT_READY`` before the file is profiled, ``422 INVALID_MODEL`` for a draft
    that does not compile, ``422 INVALID_INFERENCE_REQUEST`` for an application key that does not
    fit the mode.
    """
    try:
        submit_inference(session, draft_id, payload, retention_days=request.app.state.batch_limits.retention_days)
    except InvalidDraft as invalid:
        raise api_error(
            422,
            "INVALID_MODEL",
            "Model draft is invalid; an inference needs a draft that compiles",
            diagnostic_details(invalid.diagnostics),
        ) from None
    worker = getattr(request.app.state, "job_worker", None)
    if worker is not None:
        worker.wake()
    answer = read_inference(session, load_draft(session, draft_id))
    return JSONResponse(InferenceResponse.model_validate(answer).model_dump(mode="json"), status_code=202)


@router.get("/model-drafts/{draft_id}/inference", response_model=InferenceResponse)
@requires("model.author", at=INSTANCE)
def get_inference(draft_id: str, session: DbSession) -> InferenceResponse:
    """The draft's latest inference: its state, its proposals' counts by status, what the workbook
    disagrees with, its warnings and the elements still as proposed (``404 INFERENCE_NOT_FOUND``
    before the first)."""
    return InferenceResponse.model_validate(read_inference(session, load_draft(session, draft_id)))


@router.get("/model-drafts/{draft_id}/inference/proposals", response_model=ProposalPage)
@requires("model.author", at=INSTANCE)
def list_proposals(
    draft_id: str,
    session: DbSession,
    paging: PageQuery,
    sheet: str | None = Query(default=None, description="The proposals of one sheet"),
    column: str | None = Query(default=None, description="The proposals naming one column's header"),
    page_size: int = Query(default=100, ge=1, le=500, alias="pageSize"),
) -> ProposalPage:
    """The latest inference's proposals in the order they apply (``409 INFERENCE_NOT_READY`` while
    it runs)."""
    draft = load_draft(session, draft_id)
    page, status = proposal_page(session, draft, paging, page_size, sheet=sheet, column=column)
    items = []
    for row in page.items:
        body = row.body
        items.append(
            ProposalResponse(
                id=row.public_id,
                position=row.position,
                pattern=row.pattern,
                sheet=body.get("sheet"),
                columns=body.get("columns") or [],
                summary=body.get("summary") or "",
                evidence=body.get("evidence") or {},
                operations=body.get("operations") or [],
                alternatives=body.get("alternatives") or [],
                requires=body.get("requires") or [],
                status=status.get(row.public_id, "open"),
            )
        )
    return ProposalPage(items=items, **page.links())


@router.post(
    "/model-drafts/{draft_id}/inference/application",
    response_model=ModelDraftStepResponse,
    response_model_exclude_unset=True,
)
@requires("model.author", at=INSTANCE)
def apply_proposals(
    draft_id: str, payload: InferenceApplicationRequest, request: Request, session: DbSession
) -> ModelDraftStepResponse:
    """Apply the latest inference's proposals (every open one by default), each one step of origin
    ``proposal``, in their order, all or none (D89); the dry run follows the last.

    Refused: ``404 PROPOSAL_NOT_FOUND``, ``409 PROPOSAL_ALREADY_APPLIED``, ``422
    PROPOSAL_REQUIREMENT_MISSING`` for a proposal whose requirement is neither applied nor sent,
    ``409 INFERENCE_STALE`` when the draft changed after the inference, ``409 NOTHING_TO_APPLY``,
    ``409 VERSION_CONFLICT``, and ``422 INVALID_OPERATION`` with the step it came from.
    """
    result = apply_inference(session, draft_id, payload, max_items=request.app.state.model_operation_max_items)
    return step_response(session, result, request)


@router.post("/model-drafts/{draft_id}/inference/list", response_model=ListProposalResponse)
@requires("model.author", at=INSTANCE)
def propose_one_list(draft_id: str, payload: ListProposalRequest, session: DbSession) -> ListProposalResponse:
    """Read a rectangle of the draft's file as a list (0.10 A8b, D128): the ``listBlock`` proposal
    A8a's rules make of it against the draft as it is now, answered and not stored. Its
    ``operations`` sent to ``POST …/operations`` load the list as the administrator's. A free field
    note is read as a note, since the list was asked for.

    Refused: ``404 SOURCE_FILE_NOT_FOUND`` (no file), ``409 SOURCE_FILE_PROFILE_NOT_READY``, ``404
    SOURCE_SHEET_NOT_FOUND``, ``422 INVALID_RANGE`` for a rectangle outside the sheet or with no
    value under its header, ``422 INVALID_INFERENCE_REQUEST`` for an application the draft lacks.
    """
    return ListProposalResponse.model_validate(propose_list(session, draft_id, payload))
