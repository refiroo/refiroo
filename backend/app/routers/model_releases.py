from fastapi import APIRouter, Query
from sqlalchemy import select

from ..common.time import as_utc
from ..db import DbSession
from ..errors import api_error
from ..models.api import (
    ModelCompatibilityResponse,
    ModelReleaseDiffResponse,
    ModelReleasePage,
    ModelReleaseResponse,
)
from ..models.database import ModelRelease
from ..services.cursors import METADATA_CURSOR_MESSAGE
from ..services.model.compatibility import analyze_compatibility
from ..services.model.compiler import SUPPORTED_SCHEMA_VERSIONS, compile_model
from ..services.model.diff import semantic_diff
from ..services.model.registry import ActiveModelSnapshot
from ..services.pagination import datetime_key, paginate_statement, text_key
from .presenters import change_response, diagnostic_details, diagnostic_response

router = APIRouter(prefix="/api/v1", tags=["model"])

_RELEASE_KEYS = (
    datetime_key("installedAt", ModelRelease.installed_at, "installed_at"),
    text_key("publicId", ModelRelease.public_id, "public_id"),
)


@router.get("/model-releases", response_model=ModelReleasePage)
def list_model_releases(
    session: DbSession,
    snapshot: ActiveModelSnapshot,
    release_key: str | None = Query(default=None, alias="releaseKey"),
    active: bool | None = None,
    cursor: str | None = None,
    page_size: int = Query(default=100, ge=1, le=500, alias="pageSize"),
) -> ModelReleasePage:
    statement = select(ModelRelease)
    if release_key is not None:
        statement = statement.where(ModelRelease.release_key == release_key)
    if active is True:
        statement = statement.where(ModelRelease.public_id == snapshot.release_id)
    elif active is False:
        statement = statement.where(ModelRelease.public_id != snapshot.release_id)

    releases, next_cursor = paginate_statement(
        session,
        statement,
        keys=_RELEASE_KEYS,
        scope="model-releases",
        filters={
            "releaseKey": release_key,
            "active": active,
            "activeReleaseId": snapshot.release_id,
        },
        cursor=cursor,
        page_size=page_size,
        message=METADATA_CURSOR_MESSAGE,
    )
    return ModelReleasePage(
        items=[build_release_response(item, snapshot.release_id) for item in releases],
        nextCursor=next_cursor,
    )


@router.get(
    "/model-releases/{release_id}",
    response_model=ModelReleaseResponse,
    response_model_exclude_none=True,
)
def get_model_release(
    release_id: str,
    session: DbSession,
    snapshot: ActiveModelSnapshot,
    include_model: bool = Query(default=False, alias="includeModel"),
) -> ModelReleaseResponse:
    release = load_release(session, release_id)
    return build_release_response(release, snapshot.release_id, include_model=include_model)


@router.get(
    "/model-releases/{release_id}/diff",
    response_model=ModelReleaseDiffResponse,
    response_model_exclude_unset=True,
)
def diff_model_release(
    release_id: str,
    session: DbSession,
    snapshot: ActiveModelSnapshot,
    against_release_id: str = Query(alias="againstReleaseId"),
) -> ModelReleaseDiffResponse:
    releases = {
        release.public_id: release
        for release in session.scalars(
            select(ModelRelease).where(
                ModelRelease.public_id.in_([release_id, against_release_id])
            )
        )
    }
    candidate_release = releases.get(release_id)
    if candidate_release is None:
        raise _release_not_found(release_id)
    baseline_release = releases.get(against_release_id)
    if baseline_release is None:
        raise _release_not_found(against_release_id)

    candidate = compile_model(candidate_release.model_json)
    baseline = compile_model(baseline_release.model_json)
    for compilation, release in (
        (candidate, candidate_release),
        (baseline, baseline_release),
    ):
        if not compilation.valid:
            if compilation.unsupported_schema_version is not None:
                raise api_error(
                    422,
                    "unsupported_schema_version",
                    f"Release '{release.public_id}' uses schema version"
                    f" '{compilation.unsupported_schema_version}'"
                    " which this deployment cannot interpret for comparison",
                    {
                        "releaseId": release.public_id,
                        "schemaVersion": compilation.unsupported_schema_version,
                        "supportedSchemaVersions": sorted(SUPPORTED_SCHEMA_VERSIONS),
                        "operation": "diff",
                    },
                )
            raise api_error(
                500,
                "invalid_installed_model",
                "An installed model release failed validation",
                diagnostic_details(compilation.diagnostics),
            )
    if (
        candidate.model is None
        or candidate.canonical_model is None
        or baseline.canonical_model is None
    ):
        raise api_error(500, "internal_error", "Compiled model result is incomplete")

    compatibility = analyze_compatibility(
        session,
        snapshot.model,
        candidate.model,
        snapshot.release_id,
    )
    changes = semantic_diff(baseline.canonical_model, candidate.canonical_model)

    return ModelReleaseDiffResponse(
        againstReleaseId=against_release_id,
        releaseId=release_id,
        changes=[change_response(item) for item in changes],
        compatibility=ModelCompatibilityResponse(
            classification=compatibility.classification,
            activeReleaseId=compatibility.active_release_id,
            diagnostics=[diagnostic_response(item) for item in compatibility.diagnostics],
        ),
    )


def load_release(session: DbSession, release_id: str) -> ModelRelease:
    release = session.scalar(select(ModelRelease).where(ModelRelease.public_id == release_id))
    if release is None:
        raise _release_not_found(release_id)
    return release


def build_release_response(
    release: ModelRelease,
    active_release_id: str,
    *,
    include_model: bool = False,
) -> ModelReleaseResponse:
    return ModelReleaseResponse(
        id=release.public_id,
        key=release.release_key,
        name=release.release_name,
        version=release.release_version,
        schemaVersion=release.schema_version,
        modelHash=release.model_hash,
        installedAt=as_utc(release.installed_at),
        active=release.public_id == active_release_id,
        model=release.model_json if include_model else None,
    )


def _release_not_found(release_id: str):
    return api_error(
        404, "model_release_not_found", f"Model release '{release_id}' not found"
    )
