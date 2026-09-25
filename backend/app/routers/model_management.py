from fastapi import APIRouter, Query, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..common.time import as_utc
from ..db import DbSession
from ..errors import api_error
from ..models.api import (
    ModelActivationRequest,
    ModelCompatibilityResponse,
    ModelCompilationResponse,
    ModelDraftCreate,
    ModelDraftPage,
    ModelDraftResponse,
    ModelDraftUpdate,
    ModelDraftVersionRequest,
    ModelReleaseResponse,
    ModelRuntimeStateResponse,
)
from ..models.database import AuditEvent, ModelDraft, ModelRelease
from ..services.cursors import METADATA_CURSOR_MESSAGE
from ..services.model.compatibility import analyze_compatibility
from ..services.model.compiler import SUPPORTED_SCHEMA_VERSIONS, compile_model
from ..services.model.diff import semantic_diff
from ..services.model.drafts import (
    base_release_public_id,
    create_draft,
    delete_draft,
    load_draft,
    load_draft_for_update,
    require_draft_version,
    update_draft,
)
from ..services.model.registry import ActiveModelSnapshot, model_registry
from ..services.model.releases import (
    ActivationConflict,
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
from ..services.pagination import datetime_key, paginate_statement, text_key
from .paging import PageQuery
from .presenters import change_response, diagnostic_details, diagnostic_response

router = APIRouter(prefix="/api/v1", tags=["model administration"])

# Newest first, with an ascending public-id tie-breaker. The directions differ per key on
# purpose; the paginator derives each key's comparison from its own direction, so the pair still
# orders lexicographically.
_DRAFT_KEYS = (
    datetime_key("updatedAt", ModelDraft.updated_at, "updated_at", descending=True),
    text_key("publicId", ModelDraft.public_id, "public_id"),
)


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
                "model_release_not_found",
                f"Model release '{release_id}' not found",
            ) from exc
        except ActivationConflict as exc:
            raise api_error(
                409,
                "activation_conflict",
                "The active model selection changed before activation",
                {
                    "activeReleaseId": exc.active_release_id,
                    "runtimeVersion": exc.runtime_version,
                },
            ) from exc
        except UnsupportedModelSchema as exc:
            raise api_error(
                422,
                "unsupported_schema_version",
                f"Schema version '{exc.schema_version}' cannot be activated",
                {
                    "releaseId": exc.release_id,
                    "schemaVersion": exc.schema_version,
                    "supportedSchemaVersions": sorted(SUPPORTED_SCHEMA_VERSIONS),
                    "operation": "activation",
                },
            ) from exc
        except ModelMigrationRequired as exc:
            raise api_error(
                409,
                "model_migration_required",
                "Stored runtime data is incompatible with the candidate model",
                diagnostic_details(exc.compatibility.diagnostics),
            ) from exc
        except InvalidInstalledModel as exc:
            raise api_error(
                500,
                "invalid_installed_model",
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
                    "model_registry_refresh_failed",
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
    draft = update_draft(
        session,
        draft_id,
        payload.expectedVersion,
        name=payload.name,
        model=payload.model,
    )
    session.commit()
    return draft_response(session, draft)


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
    compiled = compile_model(draft.model_json)
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
            503, "model_runtime_state_unavailable", "Model runtime state is unavailable"
        )
    baseline = compile_model(baseline_release.model_json)
    if not baseline.valid or baseline.canonical_model is None:
        if baseline.unsupported_schema_version is not None:
            raise api_error(
                422,
                "unsupported_schema_version",
                f"Baseline release '{baseline_release.public_id}' uses schema version"
                f" '{baseline.unsupported_schema_version}' which this deployment cannot interpret",
                {
                    "releaseId": baseline_release.public_id,
                    "schemaVersion": baseline.unsupported_schema_version,
                    "supportedSchemaVersions": sorted(SUPPORTED_SCHEMA_VERSIONS),
                    "operation": "compile",
                },
            )
        raise api_error(
            500, "invalid_installed_model", "An installed model release failed validation"
        )
    if compiled.canonical_model is None:
        raise api_error(500, "internal_error", "Compiled model result is incomplete")
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
        compiled = compile_model(draft.model_json)
        if not compiled.valid or compiled.model is None:
            raise api_error(
                422,
                "invalid_model",
                "Model draft is invalid and cannot be installed",
                diagnostic_details(compiled.diagnostics),
            )
        analyze_compatibility(session, snapshot.model, compiled.model, snapshot.release_id)
        try:
            release, created = install_model_release(session, compiled.model)
        except ReleaseIdentityConflict as exc:
            raise api_error(
                409,
                "release_identity_conflict",
                f"Release '{exc.release_key}@{exc.release_version}' is already installed with different content",
            ) from exc
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
