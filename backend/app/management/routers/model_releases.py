from fastapi import APIRouter, Query
from sqlalchemy import select

from ...common.cursors import METADATA_CURSOR_MESSAGE
from ...common.pagination import datetime_key, integer_key, paginate_statement, text_key
from ...common.time import as_utc
from ...engine.identity.principals import actors
from ...engine.model.compiler import SCHEMA_VERSIONS, compile_model
from ...engine.model.diff import semantic_diff
from ...engine.model.draft_compatibility import assess
from ...engine.model.registry import resolve_model_snapshot
from ...engine.model.workspace_models import assigned_workspaces
from ...errors import api_error
from ...models.database import AuditEvent, ModelRelease, WorkspaceModel
from ..access import (
    ANYWHERE,
    AuthorizedRoute,
    requires,
)
from ..dependencies import DbSession
from ..paging import PageQuery
from ..presenters import (
    candidate_compatibility_response,
    change_response,
    consumer_contracts_response,
    diagnostic_details,
)
from ..schemas.model import (
    ModelReleaseActivationPage,
    ModelReleaseActivationResponse,
    ModelReleaseDiffResponse,
    ModelReleasePage,
    ModelReleaseResponse,
)

router = APIRouter(route_class=AuthorizedRoute, prefix="/api/v1", tags=["model"])

_RELEASE_KEYS = (
    datetime_key("installedAt", ModelRelease.installed_at, "installed_at"),
    text_key("publicId", ModelRelease.public_id, "public_id"),
)

# Oldest first, so the first item is the activation that introduced the release.
_ACTIVATION_KEYS = (
    datetime_key("occurredAt", AuditEvent.occurred_at, "occurred_at"),
    integer_key("sequenceId", AuditEvent.sequence_id, "sequence_id"),
)
_ACTIVATION_KINDS = {"activated": "activated", "schema_upgraded": "schemaUpgraded"}


@router.get("/model-releases", response_model=ModelReleasePage)
@requires("model-releases.read", at=ANYWHERE)
def list_model_releases(
    session: DbSession,
    paging: PageQuery,
    release_key: str | None = Query(default=None, alias="releaseKey"),
    assigned: bool | None = None,
    page_size: int = Query(default=100, ge=1, le=500, alias="pageSize"),
) -> ModelReleasePage:
    """Installed releases, oldest first; ``assigned`` keeps those some workspace runs (``true``) or
    none does (``false``). Each names the workspaces running it (D24)."""
    statement = select(ModelRelease)
    if release_key is not None:
        statement = statement.where(ModelRelease.release_key == release_key)
    running = select(WorkspaceModel.model_release_id)
    if assigned is True:
        statement = statement.where(ModelRelease.id.in_(running))
    elif assigned is False:
        statement = statement.where(ModelRelease.id.not_in(running))

    page = paginate_statement(
        session,
        statement,
        keys=_RELEASE_KEYS,
        scope="model-releases",
        filters={
            "releaseKey": release_key,
            "assigned": assigned,
        },
        page=paging,
        page_size=page_size,
        message=METADATA_CURSOR_MESSAGE,
    )
    return ModelReleasePage(
        items=release_responses(session, page.items),
        **page.links(),
    )


@router.get(
    "/model-releases/{release_id}",
    response_model=ModelReleaseResponse,
    response_model_exclude_none=True,
)
@requires("model-releases.read", at=ANYWHERE)
def get_model_release(
    release_id: str,
    session: DbSession,
    include_model: bool = Query(default=False, alias="includeModel"),
) -> ModelReleaseResponse:
    release = load_release(session, release_id)
    return release_responses(session, [release], include_model=include_model)[0]


@router.get(
    "/model-releases/{release_id}/activations",
    response_model=ModelReleaseActivationPage,
)
@requires("model-releases.read", at=ANYWHERE)
def list_model_release_activations(
    release_id: str,
    session: DbSession,
    paging: PageQuery,
    page_size: int = Query(default=100, ge=1, le=500, alias="pageSize"),
) -> ModelReleaseActivationPage:
    """Recorded selections of this release as a workspace's model, with the release they replaced
    and the workspace (none for a selection made for the whole instance before 0.11).

    The initial bootstrap selection is not an audited activation, so a release first selected by
    bootstrap has no item for that selection.
    """
    load_release(session, release_id)
    statement = select(AuditEvent).where(
        AuditEvent.aggregate_type.in_(("workspace_model", "model_runtime_state")),
        AuditEvent.aggregate_id == release_id,
        AuditEvent.action.in_(tuple(_ACTIVATION_KINDS)),
    )
    page = paginate_statement(
        session,
        statement,
        keys=_ACTIVATION_KEYS,
        scope="model-release-activations",
        filters={"releaseId": release_id},
        page=paging,
        page_size=page_size,
        message=METADATA_CURSOR_MESSAGE,
    )
    named_actors = actors(session, page.items)
    return ModelReleaseActivationPage(
        items=[
            ModelReleaseActivationResponse(
                eventId=event.event_id,
                kind=_ACTIVATION_KINDS[event.action],
                previousReleaseId=event.changes["oldReleaseId"],
                workspaceKey=event.changes.get("workspaceKey"),
                runtimeVersion=event.version,
                occurredAt=as_utc(event.occurred_at),
                actor=named_actors[event.sequence_id],
            )
            for event in page.items
        ],
        **page.links(),
    )


@router.get(
    "/model-releases/{release_id}/diff",
    response_model=ModelReleaseDiffResponse,
    response_model_exclude_unset=True,
)
@requires("model-releases.read", at=ANYWHERE)
def diff_model_release(
    release_id: str,
    session: DbSession,
    against_release_id: str = Query(alias="againstReleaseId"),
    workspace_key: str | None = Query(
        default=None,
        alias="workspaceKey",
        description="The workspace whose activation `compatibility` and `consumerContracts`"
        " describe, against its own release and data; the default workspace without it (0.11 D52)",
    ),
) -> ModelReleaseDiffResponse:
    snapshot = resolve_model_snapshot(session, workspace_key)
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
                    "UNSUPPORTED_SCHEMA_VERSION",
                    f"Release '{release.public_id}' uses schema version"
                    f" '{compilation.unsupported_schema_version}'"
                    " which this deployment cannot interpret for comparison",
                    {
                        "releaseId": release.public_id,
                        "schemaVersion": compilation.unsupported_schema_version,
                        "supportedSchemaVersions": list(SCHEMA_VERSIONS),
                        "operation": "diff",
                    },
                )
            raise api_error(
                500,
                "INVALID_INSTALLED_MODEL",
                "An installed model release failed validation",
                diagnostic_details(compilation.diagnostics),
            )
    if (
        candidate.model is None
        or candidate.canonical_model is None
        or baseline.canonical_model is None
    ):
        raise api_error(500, "INTERNAL_ERROR", "Compiled model result is incomplete")

    # Into the named (or default) workspace, and into each workspace running the candidate's
    # model (D25, D52).
    compatibility = assess(session, snapshot, candidate.model)
    changes = semantic_diff(baseline.canonical_model, candidate.canonical_model)

    return ModelReleaseDiffResponse(
        againstReleaseId=against_release_id,
        releaseId=release_id,
        changes=[change_response(item) for item in changes],
        compatibility=candidate_compatibility_response(compatibility),
        consumerContracts=consumer_contracts_response(
            snapshot.model, candidate.model, snapshot.release_id
        ),
    )


def load_release(session: DbSession, release_id: str) -> ModelRelease:
    release = session.scalar(select(ModelRelease).where(ModelRelease.public_id == release_id))
    if release is None:
        raise _release_not_found(release_id)
    return release


def release_responses(
    session: DbSession, releases: list[ModelRelease], *, include_model: bool = False
) -> list[ModelReleaseResponse]:
    """The releases with the workspaces running each, read once for the page."""
    running = assigned_workspaces(session, (release.id for release in releases))
    return [
        build_release_response(release, running.get(release.id, []), include_model=include_model)
        for release in releases
    ]


def build_release_response(
    release: ModelRelease,
    workspaces: list[str],
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
        assigned=bool(workspaces),
        workspaces=workspaces,
        model=release.model_json if include_model else None,
    )


def _release_not_found(release_id: str):
    return api_error(
        404, "MODEL_RELEASE_NOT_FOUND", f"Model release '{release_id}' not found"
    )
