"""Model mappings (Product 0.11 X1, D104–D113): what each element of a source model becomes in a
target model, created between two workspaces, changed by operations with history, undo and redo,
and proposed by an inference.

``router`` reads and is always registered; ``write_router`` creates, changes, deletes and infers,
and is registered with ``INTEGRATION_JOBS_ENABLED``, as import profiles are (D111).
"""

from fastapi import APIRouter, Query, Request, Response, status
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from ...common.pagination import integer_key, paginate_statement
from ...engine.model.authoring import history
from ...engine.moves import mapping_inference, mappings
from ...models.database import ModelMapping, ModelMappingOperation
from ...models.mappings import (
    MappingInferenceApplication,
    MappingInferenceRequest,
    ModelMappingCreate,
    ModelMappingOperationsRequest,
    ModelMappingUndoRequest,
    ModelMappingVersionRequest,
)
from ..dependencies import DbSession
from ..paging import PageQuery
from ..schemas.mappings import (
    MappingInferenceResponse,
    MappingProposalPage,
    MappingProposalResponse,
    ModelMappingOperationEntry,
    ModelMappingOperationPage,
    ModelMappingPage,
    ModelMappingResponse,
    ModelMappingStepResponse,
    ModelMappingSummary,
)

router = APIRouter(prefix="/api/v1", tags=["model mappings"])
write_router = APIRouter(prefix="/api/v1", tags=["model mappings"])

_OPERATION_KEYS = (integer_key("sequence", ModelMappingOperation.sequence, "sequence"),)


def _summary(mapping: ModelMapping) -> dict:
    return {
        "key": mapping.key,
        "name": mapping.name,
        "sourceModelKey": mapping.source_model_key,
        "targetModelKey": mapping.target_model_key,
        "sourceReleaseId": mapping.definition["sourceReleaseId"],
        "targetReleaseId": mapping.definition["targetReleaseId"],
        "version": mapping.version,
        "updatedAt": mapping.updated_at,
    }


def _response(read: mappings.ReadMapping) -> ModelMappingResponse:
    mapping = read.mapping
    return ModelMappingResponse(
        **_summary(mapping),
        types=mapping.definition.get("types") or [],
        valueMaps=mapping.definition.get("valueMaps") or {},
        problems=read.problems,
        coverage=read.coverage,
        createdAt=mapping.created_at,
    )


def _step(session: Session, result: history.StepResult) -> ModelMappingStepResponse:
    """The step's answer with the mapping's problems against its releases; commits."""
    read = mappings.read_mapping(session, result.subject)
    response = ModelMappingStepResponse(
        version=result.subject.version,
        entries=[_entry(row) for row in result.entries],
        problems=read.problems,
    )
    session.commit()
    return response


def _entry(row: ModelMappingOperation) -> ModelMappingOperationEntry:
    return ModelMappingOperationEntry(**history.entry_response(row, mappings.MAPPINGS))


# --- reads -----------------------------------------------------------------------------------------


@router.get("/model-mappings", response_model=ModelMappingPage)
def list_model_mappings(
    session: DbSession,
    paging: PageQuery,
    source_model_key: str | None = Query(default=None, alias="sourceModelKey"),
    target_model_key: str | None = Query(default=None, alias="targetModelKey"),
    page_size: int = Query(default=100, ge=1, le=500, alias="pageSize"),
) -> ModelMappingPage:
    """Model mappings in key order, of one source and one target model when given (D18)."""
    page = mappings.mapping_page(
        session,
        paging,
        page_size,
        source_model_key=source_model_key,
        target_model_key=target_model_key,
    )
    return ModelMappingPage(
        items=[ModelMappingSummary(**_summary(m)) for m in page.items], **page.links()
    )


@router.get("/model-mappings/{key}", response_model=ModelMappingResponse)
def get_model_mapping(
    key: str,
    session: DbSession,
    source_workspace_key: str | None = Query(default=None, alias="sourceWorkspaceKey"),
    target_workspace_key: str | None = Query(default=None, alias="targetWorkspaceKey"),
) -> ModelMappingResponse:
    """The mapping with its problems and coverage against its releases; a side whose workspace is
    named is read against the release that workspace runs (D110). ``404 MODEL_MAPPING_NOT_FOUND``;
    ``422 MODEL_MAPPING_MODEL_MISMATCH`` for a workspace running another model."""
    read = mappings.read_mapping(
        session,
        mappings.load_mapping(session, key),
        source_workspace_key=source_workspace_key,
        target_workspace_key=target_workspace_key,
    )
    return _response(read)


@router.get("/model-mappings/{key}/operations", response_model=ModelMappingOperationPage)
def list_model_mapping_operations(
    key: str,
    session: DbSession,
    paging: PageQuery,
    page_size: int = Query(default=100, ge=1, le=500, alias="pageSize"),
) -> ModelMappingOperationPage:
    """The mapping's history in sequence order (D105)."""
    mapping = mappings.load_mapping(session, key)
    page = paginate_statement(
        session,
        select(ModelMappingOperation).where(ModelMappingOperation.mapping_id == mapping.id),
        keys=_OPERATION_KEYS,
        scope=f"model-mapping-operations:{mapping.key}",
        filters={},
        page=paging,
        page_size=page_size,
        message="Model mapping history cursor is invalid",
    )
    return ModelMappingOperationPage(items=[_entry(row) for row in page.items], **page.links())


@router.get("/model-mappings/{key}/inference", response_model=MappingInferenceResponse)
def get_mapping_inference(key: str, session: DbSession) -> MappingInferenceResponse:
    """The mapping's latest inference: its state, its proposals' counts by status and its warnings
    (``404 INFERENCE_NOT_FOUND`` before the first)."""
    mapping = mappings.load_mapping(session, key)
    return MappingInferenceResponse.model_validate(
        mapping_inference.read_inference(session, mapping)
    )


@router.get("/model-mappings/{key}/inference/proposals", response_model=MappingProposalPage)
def list_mapping_proposals(
    key: str,
    session: DbSession,
    paging: PageQuery,
    source_type: str | None = Query(
        default=None, alias="sourceType", description="The proposals of one source type"
    ),
    page_size: int = Query(default=100, ge=1, le=500, alias="pageSize"),
) -> MappingProposalPage:
    """The latest inference's proposals in the order they apply: types, then relationships
    (``409 INFERENCE_NOT_READY`` while it runs)."""
    mapping = mappings.load_mapping(session, key)
    page, statuses = mapping_inference.proposal_page(
        session, mapping, paging, page_size, source_type=source_type
    )
    items = [
        MappingProposalResponse(
            id=row.public_id,
            position=row.position,
            kind=row.kind,
            sourceType=row.body["sourceType"],
            relation=row.body.get("relation"),
            target=row.body["target"],
            score=row.body["score"],
            summary=row.body["summary"],
            evidence=row.body["evidence"],
            operations=row.body["operations"],
            alternatives=row.body["alternatives"],
            requires=row.body["requires"],
            status=statuses.get(row.public_id, "open"),
        )
        for row in page.items
    ]
    return MappingProposalPage(items=items, **page.links())


# --- writes ----------------------------------------------------------------------------------------


@write_router.post("/model-mappings", response_model=ModelMappingResponse, status_code=201)
def create_model_mapping(payload: ModelMappingCreate, session: DbSession) -> ModelMappingResponse:
    """A mapping between the releases two workspaces run, or two releases (D104), with no type
    mapped. Refused: ``409 MODEL_MAPPING_EXISTS``, ``404 WORKSPACE_NOT_FOUND``, ``409
    WORKSPACE_RETIRED``, ``404 MODEL_RELEASE_NOT_FOUND``, ``422 INVALID_MODEL_MAPPING`` for a side
    named twice or not at all."""
    read = mappings.create_mapping(
        session,
        key=payload.key,
        name=payload.name,
        source_workspace_key=payload.sourceWorkspaceKey,
        target_workspace_key=payload.targetWorkspaceKey,
        source_release_id=payload.sourceReleaseId,
        target_release_id=payload.targetReleaseId,
    )
    return _response(read)


@write_router.delete("/model-mappings/{key}", status_code=status.HTTP_204_NO_CONTENT)
def delete_model_mapping(
    key: str, session: DbSession, expected_version: int = Query(ge=1, alias="expectedVersion")
) -> Response:
    """The mapping, its history and its proposals (D112); ``409 VERSION_CONFLICT`` at a stale version."""
    mappings.delete_mapping(session, key, expected_version)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@write_router.post("/model-mappings/{key}/operations", response_model=ModelMappingStepResponse)
def apply_model_mapping_operations(
    key: str, payload: ModelMappingOperationsRequest, session: DbSession, request: Request
) -> ModelMappingStepResponse:
    """Apply operations in order, all or none, as one step of the mapping's history (D107):
    ``mapType``, ``unmapType``, ``mapAttribute``, ``unmapAttribute``, ``mapRelation``,
    ``unmapRelation``, ``setParent``, ``setMatch``, ``setValueMap``, ``setMissing``, ``setDefault``,
    ``setReleases``. Refused: ``422 INVALID_OPERATION`` at the parameter at fault with its
    ``reason``, ``409 VERSION_CONFLICT`` with the newer entries, ``413 OPERATION_BATCH_TOO_LARGE``."""
    result = mappings.apply_request(
        session,
        key,
        payload.expectedVersion,
        payload.operations,
        request.app.state.model_operation_max_items,
    )
    return _step(session, result)


@write_router.post("/model-mappings/{key}/undo", response_model=ModelMappingStepResponse)
def undo_model_mapping_step(
    key: str, payload: ModelMappingUndoRequest, session: DbSession
) -> ModelMappingStepResponse:
    """Undo the latest step, or ``step``, or ``steps`` together. Refused: ``409 NOTHING_TO_UNDO``,
    ``409 OPERATION_HAS_DEPENDANTS`` naming the later steps that rely on it."""
    return _step(
        session, mappings.undo(session, key, payload.expectedVersion, payload.step, payload.steps)
    )


@write_router.post("/model-mappings/{key}/redo", response_model=ModelMappingStepResponse)
def redo_model_mapping_step(
    key: str, payload: ModelMappingVersionRequest, session: DbSession
) -> ModelMappingStepResponse:
    """Redo the latest undone step (``409 NOTHING_TO_REDO``)."""
    return _step(session, mappings.redo(session, key, payload.expectedVersion))


@write_router.post(
    "/model-mappings/{key}/inference", response_model=MappingInferenceResponse, status_code=202
)
def run_mapping_inference(
    key: str, payload: MappingInferenceRequest, request: Request, session: DbSession
) -> JSONResponse:
    """Propose the mapping from its two releases and the two workspaces' records (D108). Answers 202
    with the inference ``checking``; an inference still running for the mapping is cancelled.
    Refused: ``422 MODEL_MAPPING_MODEL_MISMATCH`` for a workspace running another model."""
    mapping_inference.submit_inference(
        session,
        key,
        payload.sourceWorkspaceKey,
        payload.targetWorkspaceKey,
        retention_days=request.app.state.batch_limits.retention_days,
    )
    worker = getattr(request.app.state, "job_worker", None)
    if worker is not None:
        worker.wake()
    answer = mapping_inference.read_inference(session, mappings.load_mapping(session, key))
    return JSONResponse(
        MappingInferenceResponse.model_validate(answer).model_dump(mode="json"), status_code=202
    )


@write_router.post(
    "/model-mappings/{key}/inference/application", response_model=ModelMappingStepResponse
)
def apply_mapping_proposals(
    key: str, payload: MappingInferenceApplication, request: Request, session: DbSession
) -> ModelMappingStepResponse:
    """Apply the latest inference's proposals (every open one by default), each one step of origin
    ``proposal``, in their order, all or none. Refused: ``404 PROPOSAL_NOT_FOUND``, ``409
    PROPOSAL_ALREADY_APPLIED``, ``422 PROPOSAL_REQUIREMENT_MISSING``, ``409 INFERENCE_STALE`` when the
    mapping was re-pointed since, ``409 NOTHING_TO_APPLY``, ``409 VERSION_CONFLICT`` and ``422
    INVALID_OPERATION`` with the step it came from."""
    result = mapping_inference.apply_inference(
        session,
        key,
        payload.expectedVersion,
        payload.proposals,
        max_items=request.app.state.model_operation_max_items,
    )
    return _step(session, result)
