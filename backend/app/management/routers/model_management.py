from fastapi import APIRouter, Query, Request, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ...common.cursors import METADATA_CURSOR_MESSAGE
from ...common.pagination import datetime_key, integer_key, paginate_statement, text_key
from ...common.time import as_utc
from ...engine.model.authoring import history
from ...engine.model.compatibility import analyze_compatibility
from ...engine.model.compiler import (
    SCHEMA_VERSIONS,
    compile_authored_model,
    compile_model,
)
from ...engine.model.diff import semantic_diff
from ...engine.model.drafts import (
    base_release_public_id,
    create_draft,
    delete_draft,
    load_draft,
    load_draft_for_update,
    require_draft_version,
    update_draft,
)
from ...engine.model.registry import model_registry
from ...engine.model.releases import (
    ActivationConflict,
    ConsumerContractVersionRequired,
    InvalidInstalledModel,
    ModelMigrationRequired,
    ModelReleaseNotFound,
    ReleaseIdentityConflict,
    UnsupportedModelSchema,
    activate_model_release,
    install_model_release,
    model_activation_lock,
    model_installation_lock,
)
from ...errors import api_error
from ...models.database import AuditEvent, ModelDraft, ModelDraftOperation, ModelRelease
from ..dependencies import ActiveModelSnapshot, DbSession
from ..paging import PageQuery
from ..presenters import (
    change_response,
    consumer_contracts_response,
    diagnostic_details,
    diagnostic_response,
)
from ..schemas.model import (
    ModelActivationRequest,
    ModelCompatibilityResponse,
    ModelCompilationResponse,
    ModelDraftCreate,
    ModelDraftOperationEntry,
    ModelDraftOperationPage,
    ModelDraftOperationsRequest,
    ModelDraftPage,
    ModelDraftResponse,
    ModelDraftStepResponse,
    ModelDraftUndoRequest,
    ModelDraftUpdate,
    ModelDraftVersionRequest,
    ModelReleaseResponse,
    ModelRuntimeStateResponse,
)

router = APIRouter(prefix="/api/v1", tags=["model administration"])

# Newest first, with an ascending public-id tie-breaker. The directions differ per key on
# purpose; the paginator derives each key's comparison from its own direction, so the pair still
# orders lexicographically.
_DRAFT_KEYS = (
    datetime_key("updatedAt", ModelDraft.updated_at, "updated_at", descending=True),
    text_key("publicId", ModelDraft.public_id, "public_id"),
)
# A draft's history in the order it was written (0.10 A2).
_OPERATION_KEYS = (integer_key("sequence", ModelDraftOperation.sequence, "sequence"),)


@router.post(
    "/model-releases/{release_id}/activation",
    response_model=ModelRuntimeStateResponse,
)
def activate_release(
    release_id: str, payload: ModelActivationRequest, session: DbSession
) -> ModelRuntimeStateResponse:
    with model_activation_lock:
        try:
            activated = activate_model_release(
                session,
                release_id,
                expected_runtime_version=payload.expectedRuntimeVersion,
                expected_active_release_id=str(payload.expectedActiveReleaseId),
            )
        except ModelReleaseNotFound as exc:
            raise api_error(
                404,
                "MODEL_RELEASE_NOT_FOUND",
                f"Model release '{release_id}' not found",
            ) from exc
        except ActivationConflict as exc:
            raise api_error(
                409,
                "ACTIVATION_CONFLICT",
                "The active model selection changed before activation",
                {
                    "activeReleaseId": exc.active_release_id,
                    "runtimeVersion": exc.runtime_version,
                },
            ) from exc
        except UnsupportedModelSchema as exc:
            raise api_error(
                422,
                "UNSUPPORTED_SCHEMA_VERSION",
                f"Schema version '{exc.schema_version}' cannot be activated",
                {
                    "releaseId": exc.release_id,
                    "schemaVersion": exc.schema_version,
                    "supportedSchemaVersions": list(SCHEMA_VERSIONS),
                    "operation": "activation",
                },
            ) from exc
        except ModelMigrationRequired as exc:
            raise api_error(
                409,
                "MODEL_MIGRATION_REQUIRED",
                "Stored runtime data is incompatible with the candidate model",
                diagnostic_details(exc.compatibility.diagnostics),
            ) from exc
        except ConsumerContractVersionRequired as exc:
            raise api_error(
                409,
                "CONSUMER_CONTRACT_VERSION_REQUIRED",
                "A consumer API definition changes what its consumers read; raise its"
                " contractVersion in a new release",
                diagnostic_details(exc.diagnostics),
            ) from exc
        except InvalidInstalledModel as exc:
            raise api_error(
                500,
                "INVALID_INSTALLED_MODEL",
                "An installed model release failed validation",
                diagnostic_details(exc.diagnostics),
            ) from exc

        with model_registry.publication_guard():
            session.commit()

            try:
                model_registry.refresh_active()
            except Exception as exc:
                model_registry.mark_unhealthy()
                raise api_error(
                    503,
                    "MODEL_REGISTRY_REFRESH_FAILED",
                    "The model was activated, but this process could not publish the committed selection",
                    {
                        "activeReleaseId": activated.active_release_id,
                        "runtimeVersion": activated.version,
                    },
                ) from exc

    return ModelRuntimeStateResponse(
        activeReleaseId=activated.active_release_id,
        activeModelHash=activated.active_model_hash,
        version=activated.version,
        updatedAt=activated.updated_at,
    )


@router.get("/model-drafts", response_model=ModelDraftPage)
def list_model_drafts(
    session: DbSession,
    paging: PageQuery,
    page_size: int = Query(default=100, ge=1, le=500, alias="pageSize"),
) -> ModelDraftPage:
    page = paginate_statement(
        session,
        select(ModelDraft),
        keys=_DRAFT_KEYS,
        scope="model-drafts",
        filters={},
        page=paging,
        page_size=page_size,
        cursor_sort_tokens=("updatedAt", "publicId"),
        message=METADATA_CURSOR_MESSAGE,
    )
    return ModelDraftPage(
        items=[draft_response(session, draft) for draft in page.items], **page.links()
    )


@router.get("/model-drafts/{draft_id}", response_model=ModelDraftResponse)
def get_model_draft(draft_id: str, session: DbSession) -> ModelDraftResponse:
    return draft_response(session, load_draft(session, draft_id))


@router.post(
    "/model-drafts",
    response_model=ModelDraftResponse,
    status_code=status.HTTP_201_CREATED,
)
def save_model_draft(payload: ModelDraftCreate, session: DbSession) -> ModelDraftResponse:
    draft = create_draft(
        session,
        name=payload.name,
        model=payload.model,
        base_release_id=str(payload.baseReleaseId) if payload.baseReleaseId else None,
    )
    session.commit()
    return draft_response(session, draft)


@router.patch("/model-drafts/{draft_id}", response_model=ModelDraftResponse)
def patch_model_draft(
    draft_id: str, payload: ModelDraftUpdate, session: DbSession
) -> ModelDraftResponse:
    previous = load_draft_for_update(session, draft_id).model_json if payload.model is not None else None
    draft = update_draft(
        session,
        draft_id,
        payload.expectedVersion,
        name=payload.name,
        model=payload.model,
    )
    if previous is not None:
        history.record_patch(session, draft, previous)
    session.commit()
    return draft_response(session, draft)


@router.post("/model-drafts/{draft_id}/operations", response_model=ModelDraftStepResponse, response_model_exclude_unset=True)
def apply_model_draft_operations(
    draft_id: str, payload: ModelDraftOperationsRequest, session: DbSession, request: Request
) -> ModelDraftStepResponse:
    result = history.apply_request(
        session,
        draft_id,
        payload.expectedVersion,
        payload.operations,
        request.app.state.model_operation_max_items,
    )
    return _step_response(session, result)


@router.get("/model-drafts/{draft_id}/operations", response_model=ModelDraftOperationPage)
def list_model_draft_operations(
    draft_id: str,
    session: DbSession,
    paging: PageQuery,
    page_size: int = Query(default=100, ge=1, le=500, alias="pageSize"),
) -> ModelDraftOperationPage:
    draft = load_draft(session, draft_id)
    page = paginate_statement(
        session,
        select(ModelDraftOperation).where(ModelDraftOperation.draft_id == draft.id),
        keys=_OPERATION_KEYS,
        scope=f"model-draft-operations:{draft.public_id}",
        filters={},
        page=paging,
        page_size=page_size,
        cursor_sort_tokens=("sequence",),
        message=METADATA_CURSOR_MESSAGE,
    )
    return ModelDraftOperationPage(
        items=[_entry(row) for row in page.items], **page.links()
    )


@router.post("/model-drafts/{draft_id}/undo", response_model=ModelDraftStepResponse, response_model_exclude_unset=True)
def undo_model_draft_step(
    draft_id: str, payload: ModelDraftUndoRequest, session: DbSession
) -> ModelDraftStepResponse:
    result = history.undo(session, draft_id, payload.expectedVersion, payload.step, payload.steps)
    return _step_response(session, result)


@router.post("/model-drafts/{draft_id}/redo", response_model=ModelDraftStepResponse, response_model_exclude_unset=True)
def redo_model_draft_step(
    draft_id: str, payload: ModelDraftVersionRequest, session: DbSession
) -> ModelDraftStepResponse:
    result = history.redo(session, draft_id, payload.expectedVersion)
    return _step_response(session, result)


def _step_response(session: Session, result: history.StepResult) -> ModelDraftStepResponse:
    response = ModelDraftStepResponse(
        version=result.draft.version,
        entries=[_entry(row) for row in result.entries],
        valid=result.valid,
        diagnostics=[diagnostic_response(item) for item in result.diagnostics],
    )
    session.commit()
    return response


def _entry(row: ModelDraftOperation) -> ModelDraftOperationEntry:
    return ModelDraftOperationEntry(**history.entry_response(row))


@router.delete("/model-drafts/{draft_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_model_draft(
    draft_id: str,
    session: DbSession,
    expected_version: int = Query(ge=1, alias="expectedVersion"),
) -> Response:
    delete_draft(session, draft_id, expected_version)
    session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/model-drafts/{draft_id}/compile",
    response_model=ModelCompilationResponse,
    response_model_exclude_unset=True,
)
def compile_model_draft(
    draft_id: str,
    payload: ModelDraftVersionRequest,
    session: DbSession,
    snapshot: ActiveModelSnapshot,
) -> ModelCompilationResponse:
    draft = load_draft(session, draft_id)
    require_draft_version(draft, payload.expectedVersion)
    compiled = compile_authored_model(draft.model_json)
    if not compiled.valid or compiled.model is None:
        return ModelCompilationResponse(
            valid=False,
            diagnostics=[diagnostic_response(item) for item in compiled.diagnostics],
            compatibility=ModelCompatibilityResponse(
                classification="invalid",
                activeReleaseId=snapshot.release_id,
                diagnostics=[],
            ),
        )
    compatibility = analyze_compatibility(
        session, snapshot.model, compiled.model, snapshot.release_id
    )
    baseline_release = None
    if draft.base_model_release_id is not None:
        baseline_release = session.get(ModelRelease, draft.base_model_release_id)
    if baseline_release is None:
        baseline_release = session.scalar(
            select(ModelRelease).where(ModelRelease.public_id == snapshot.release_id)
        )
    if baseline_release is None:
        raise api_error(
            503, "MODEL_RUNTIME_STATE_UNAVAILABLE", "Model runtime state is unavailable"
        )
    baseline = compile_model(baseline_release.model_json)
    if not baseline.valid or baseline.canonical_model is None:
        if baseline.unsupported_schema_version is not None:
            raise api_error(
                422,
                "UNSUPPORTED_SCHEMA_VERSION",
                f"Baseline release '{baseline_release.public_id}' uses schema version"
                f" '{baseline.unsupported_schema_version}' which this deployment cannot interpret",
                {
                    "releaseId": baseline_release.public_id,
                    "schemaVersion": baseline.unsupported_schema_version,
                    "supportedSchemaVersions": list(SCHEMA_VERSIONS),
                    "operation": "compile",
                },
            )
        raise api_error(
            500, "INVALID_INSTALLED_MODEL", "An installed model release failed validation"
        )
    if compiled.canonical_model is None:
        raise api_error(500, "INTERNAL_ERROR", "Compiled model result is incomplete")
    changes = semantic_diff(baseline.canonical_model, compiled.canonical_model)

    return ModelCompilationResponse(
        valid=True,
        model=compiled.canonical_model,
        modelHash=compiled.model_hash,
        diagnostics=[diagnostic_response(item) for item in compiled.diagnostics],
        againstReleaseId=baseline_release.public_id,
        changes=[change_response(item) for item in changes],
        compatibility=ModelCompatibilityResponse(
            classification=compatibility.classification,
            activeReleaseId=compatibility.active_release_id,
            diagnostics=[diagnostic_response(item) for item in compatibility.diagnostics],
        ),
        consumerContracts=consumer_contracts_response(
            snapshot.model, compiled.model, snapshot.release_id
        ),
    )


@router.post(
    "/model-drafts/{draft_id}/installation",
    response_model=ModelReleaseResponse,
    response_model_exclude_none=True,
    status_code=status.HTTP_201_CREATED,
)
def install_model_draft(
    draft_id: str,
    payload: ModelDraftVersionRequest,
    session: DbSession,
    snapshot: ActiveModelSnapshot,
    response: Response,
) -> ModelReleaseResponse:
    with model_installation_lock:
        draft = load_draft_for_update(session, draft_id)
        require_draft_version(draft, payload.expectedVersion)
        compiled = compile_authored_model(draft.model_json)
        if not compiled.valid or compiled.model is None:
            raise api_error(
                422,
                "INVALID_MODEL",
                "Model draft is invalid and cannot be installed",
                diagnostic_details(compiled.diagnostics),
            )
        analyze_compatibility(session, snapshot.model, compiled.model, snapshot.release_id)
        try:
            release, created = install_model_release(session, compiled.model)
        except ReleaseIdentityConflict as exc:
            raise api_error(
                409,
                "RELEASE_IDENTITY_CONFLICT",
                f"Release '{exc.release_key}@{exc.release_version}' is already installed with different content",
            ) from exc
        # D17: what the draft held is now released; its version is unchanged (D34).
        draft.base_model_release_id = release.id
        if created:
            session.add(
                AuditEvent(
                    aggregate_type="model_release",
                    aggregate_id=release.public_id,
                    action="installed",
                    version=1,
                    changes={
                        "draftId": draft.public_id,
                        "releaseKey": release.release_key,
                        "releaseVersion": release.release_version,
                        "modelHash": release.model_hash,
                    },
                )
            )
        session.commit()
        if not created:
            response.status_code = status.HTTP_200_OK
        return ModelReleaseResponse(
            id=release.public_id,
            key=release.release_key,
            name=release.release_name,
            version=release.release_version,
            schemaVersion=release.schema_version,
            modelHash=release.model_hash,
            installedAt=as_utc(release.installed_at),
            active=release.public_id == snapshot.release_id,
        )


def draft_response(session: Session, draft: ModelDraft) -> ModelDraftResponse:
    return ModelDraftResponse(
        id=draft.public_id,
        name=draft.name,
        baseReleaseId=base_release_public_id(session, draft),
        model=draft.model_json,
        version=draft.version,
        createdAt=as_utc(draft.created_at),
        updatedAt=as_utc(draft.updated_at),
    )
