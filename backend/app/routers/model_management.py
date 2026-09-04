from datetime import datetime

from fastapi import APIRouter, Query, Response, status
from sqlalchemy import and_, or_, select

from ..db import SessionLocal
from ..errors import api_error
from ..models.api import (
    ModelCompatibilityResponse,
    ModelCompilationResponse,
    ModelDiagnosticResponse,
    ModelDraftCreate,
    ModelDraftPage,
    ModelDraftResponse,
    ModelDraftUpdate,
    ModelDraftVersionRequest,
    ModelReleaseResponse,
)
from ..models.database import AuditEvent, ModelDraft
from ..services.model_compatibility import analyze_compatibility
from ..services.model_compiler import ModelDiagnostic, compile_model
from ..services.model_drafts import (
    base_release_public_id,
    create_draft,
    delete_draft,
    load_draft,
    load_draft_for_update,
    require_draft_version,
    update_draft,
)
from ..services.model_registry import ActiveModelSnapshot
from ..services.model_releases import (
    ReleaseIdentityConflict,
    install_model_release,
    model_installation_lock,
)
from .model import _as_utc, _decode_cursor, _encode_cursor

router = APIRouter(prefix="/api/v1", tags=["model administration"])


@router.get("/model-drafts", response_model=ModelDraftPage)
def list_model_drafts(
    cursor: str | None = None,
    page_size: int = Query(default=100, ge=1, le=500, alias="pageSize"),
) -> ModelDraftPage:
    cursor_sort = ("updatedAt", "publicId")
    with SessionLocal() as session:
        statement = select(ModelDraft)
        if cursor is not None:
            identity = _decode_cursor(
                cursor, scope="model-drafts", sort=cursor_sort, filters={}
            )
            if len(identity) != 2:
                raise api_error(422, "invalid_cursor", "Metadata cursor is invalid")
            try:
                updated_at = datetime.fromisoformat(identity[0])
            except ValueError:
                raise api_error(422, "invalid_cursor", "Metadata cursor is invalid") from None
            statement = statement.where(
                or_(
                    ModelDraft.updated_at < updated_at,
                    and_(
                        ModelDraft.updated_at == updated_at,
                        ModelDraft.public_id > identity[1],
                    ),
                )
            )
        rows = list(
            session.scalars(
                statement.order_by(ModelDraft.updated_at.desc(), ModelDraft.public_id).limit(
                    page_size + 1
                )
            )
        )
        visible = rows[:page_size]
        items = [_draft_response(session, draft) for draft in visible]

    next_cursor = (
        _encode_cursor(
            (_as_utc(visible[-1].updated_at).isoformat(), visible[-1].public_id),
            scope="model-drafts",
            sort=cursor_sort,
            filters={},
        )
        if len(rows) > page_size
        else None
    )
    return ModelDraftPage(items=items, nextCursor=next_cursor)


@router.get("/model-drafts/{draft_id}", response_model=ModelDraftResponse)
def get_model_draft(draft_id: str) -> ModelDraftResponse:
    with SessionLocal() as session:
        return _draft_response(session, load_draft(session, draft_id))


@router.post(
    "/model-drafts",
    response_model=ModelDraftResponse,
    status_code=status.HTTP_201_CREATED,
)
def save_model_draft(payload: ModelDraftCreate) -> ModelDraftResponse:
    with SessionLocal() as session:
        draft = create_draft(
            session,
            name=payload.name,
            model=payload.model,
            base_release_id=str(payload.baseReleaseId) if payload.baseReleaseId else None,
        )
        session.commit()
        return _draft_response(session, draft)


@router.patch("/model-drafts/{draft_id}", response_model=ModelDraftResponse)
def patch_model_draft(draft_id: str, payload: ModelDraftUpdate) -> ModelDraftResponse:
    with SessionLocal() as session:
        draft = update_draft(
            session,
            draft_id,
            payload.expectedVersion,
            name=payload.name,
            model=payload.model,
        )
        session.commit()
        return _draft_response(session, draft)


@router.delete("/model-drafts/{draft_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_model_draft(
    draft_id: str,
    expected_version: int = Query(ge=1, alias="expectedVersion"),
) -> Response:
    with SessionLocal() as session:
        delete_draft(session, draft_id, expected_version)
        session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/model-drafts/{draft_id}/compile",
    response_model=ModelCompilationResponse,
    response_model_exclude_none=True,
)
def compile_model_draft(
    draft_id: str,
    payload: ModelDraftVersionRequest,
    snapshot: ActiveModelSnapshot,
) -> ModelCompilationResponse:
    with SessionLocal() as session:
        draft = load_draft(session, draft_id)
        require_draft_version(draft, payload.expectedVersion)
        compiled = compile_model(draft.model_json)
        if not compiled.valid or compiled.model is None:
            return ModelCompilationResponse(
                valid=False,
                diagnostics=[_diagnostic_response(item) for item in compiled.diagnostics],
                compatibility=ModelCompatibilityResponse(
                    classification="invalid",
                    activeReleaseId=snapshot.release_id,
                    diagnostics=[],
                ),
            )
        compatibility = analyze_compatibility(
            session, snapshot.model, compiled.model, snapshot.release_id
        )

    return ModelCompilationResponse(
        valid=True,
        model=compiled.canonical_model,
        modelHash=compiled.model_hash,
        diagnostics=[_diagnostic_response(item) for item in compiled.diagnostics],
        compatibility=ModelCompatibilityResponse(
            classification=compatibility.classification,
            activeReleaseId=compatibility.active_release_id,
            diagnostics=[
                _diagnostic_response(item) for item in compatibility.diagnostics
            ],
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
    snapshot: ActiveModelSnapshot,
    response: Response,
) -> ModelReleaseResponse:
    with model_installation_lock, SessionLocal() as session:
        draft = load_draft_for_update(session, draft_id)
        require_draft_version(draft, payload.expectedVersion)
        compiled = compile_model(draft.model_json)
        if not compiled.valid or compiled.model is None:
            raise api_error(
                422,
                "invalid_model",
                "Model draft is invalid and cannot be installed",
                [_diagnostic_response(item).model_dump(exclude_none=True) for item in compiled.diagnostics],
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
            installedAt=_as_utc(release.installed_at),
            active=release.public_id == snapshot.release_id,
        )


def _draft_response(session, draft: ModelDraft) -> ModelDraftResponse:
    return ModelDraftResponse(
        id=draft.public_id,
        name=draft.name,
        baseReleaseId=base_release_public_id(session, draft),
        model=draft.model_json,
        version=draft.version,
        createdAt=_as_utc(draft.created_at),
        updatedAt=_as_utc(draft.updated_at),
    )


def _diagnostic_response(item: ModelDiagnostic) -> ModelDiagnosticResponse:
    values = {
        "severity": item.severity,
        "code": item.code,
        "path": item.path,
        "message": item.message,
    }
    if item.count is not None:
        values["count"] = item.count
    return ModelDiagnosticResponse(**values)
