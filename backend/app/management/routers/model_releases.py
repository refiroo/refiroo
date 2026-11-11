from typing import Literal

from fastapi import APIRouter, Query, status
from sqlalchemy import select

from ...common.cursors import METADATA_CURSOR_MESSAGE
from ...common.pagination import datetime_key, integer_key, paginate_statement, text_key
from ...common.time import as_utc
from ...engine.identity.principals import actors
from ...engine.model.compiler import SCHEMA_VERSIONS, compile_model
from ...engine.model.diff import semantic_diff
from ...engine.model.draft_compatibility import assess
from ...engine.model.raising import raise_release
from ...engine.model.registry import model_registry, resolve_model_snapshot
from ...engine.model.release_lifecycle import delete_release, set_release_status
from ...errors import api_error
from ...models.database import AuditEvent, ModelRelease, Workspace, WorkspaceModel
from ..access import (
    ANYWHERE,
    INSTANCE,
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
    model_release_responses,
)
from ..schemas.model import (
    ModelReleaseActivationPage,
    ModelReleaseActivationResponse,
    ModelReleaseDiffResponse,
    ModelReleasePage,
    ModelReleaseRaisingRequest,
    ModelReleaseRaisingResponse,
    ModelReleaseRaisingWorkspace,
    ModelReleaseResponse,
    ModelReleaseStatusRequest,
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
    release_status: Literal["active", "retired", "all"] = Query(default="all", alias="status"),
    usable: bool = False,
    page_size: int = Query(default=100, ge=1, le=500, alias="pageSize"),
) -> ModelReleasePage:
    """Installed releases, oldest first; ``assigned`` keeps those some workspace runs (``true``) or
    none does (``false``). Each names the workspaces running it (D24). ``status`` keeps the active
    or the retired ones; ``usable=true`` keeps those a caller may choose, active and of a schema
    this version reads (0.12 MR1, D458)."""
    statement = select(ModelRelease)
    if release_key is not None:
        statement = statement.where(ModelRelease.release_key == release_key)
    if release_status != "all":
        statement = statement.where(ModelRelease.status == release_status)
    if usable:
        statement = statement.where(
            ModelRelease.status == "active", ModelRelease.schema_version.in_(SCHEMA_VERSIONS)
        )
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
            "status": release_status,
            "usable": usable,
        },
        page=paging,
        page_size=page_size,
        message=METADATA_CURSOR_MESSAGE,
    )
    return ModelReleasePage(
        items=model_release_responses(session, page.items),
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
    return model_release_responses(session, [release], include_model=include_model)[0]


@router.patch(
    "/model-releases/{release_id}",
    response_model=ModelReleaseResponse,
    response_model_exclude_none=True,
)
@requires("model.install", at=INSTANCE)
def patch_model_release(
    release_id: str, payload: ModelReleaseStatusRequest, session: DbSession
) -> ModelReleaseResponse:
    """Retire a release (`status: retired`) or bring it back (`active`); its model never changes
    (0.12 MR1, D457). A retired release is refused where a release is chosen (`409
    MODEL_RELEASE_RETIRED`: a new workspace, a change set, an activation, a migration), and every
    workspace and change set on it keeps working. `404 MODEL_RELEASE_NOT_FOUND`, `409
    MODEL_RELEASE_VERSION_CONFLICT`, `409 MODEL_RELEASE_IS_DEFAULT` (the default workspace runs
    it)."""
    release = set_release_status(session, release_id, payload.status, payload.expectedStatusVersion)
    session.commit()
    return model_release_responses(session, [release])[0]


@router.delete("/model-releases/{release_id}", status_code=status.HTTP_204_NO_CONTENT)
@requires("model.install", at=INSTANCE)
def delete_model_release(
    release_id: str,
    session: DbSession,
    expected_status_version: int = Query(ge=1, alias="expectedStatusVersion"),
) -> None:
    """Delete a release nothing refers to: no workspace runs it, and no record, change set,
    publication, job, import profile or model mapping was made under it (0.12 MR1, D457). Its
    drafts stay, without their link to it. `404 MODEL_RELEASE_NOT_FOUND`, `409
    MODEL_RELEASE_VERSION_CONFLICT`, `409 MODEL_RELEASE_IN_USE` (with `blockedBy`)."""
    delete_release(session, release_id, expected_status_version)
    session.commit()


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
            select(ModelRelease).where(ModelRelease.public_id.in_([release_id, against_release_id]))
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


@router.post(
    "/model-releases/{release_id}/raising",
    response_model=ModelReleaseRaisingResponse,
)
@requires("model.install", at=INSTANCE)
def raise_model_release(
    release_id: str, payload: ModelReleaseRaisingRequest, session: DbSession
) -> ModelReleaseRaisingResponse:
    """Bring a release of a schema that left the window up to the schema this version reads, in
    place (0.12 UW1): `{confirm: false}` previews and changes nothing; `{confirm: true,
    expectedModelHash}` rewrites the release, and every process serves the workspaces running it
    from its next request. Its id, key and version are unchanged, so records, change sets and
    publications follow. A maintenance step of the releases before 1.0. `404
    MODEL_RELEASE_NOT_FOUND`, `422 RELEASE_NOT_RAISABLE`, `422 RELEASE_RAISE_REFUSED`, `409
    MODEL_HASH_CHANGED`."""
    result = raise_release(
        session,
        release_id,
        confirm=payload.confirm,
        expected_model_hash=payload.expectedModelHash,
    )
    labels = dict(
        session.execute(
            select(Workspace.key, Workspace.label).where(Workspace.key.in_(result.workspaces))
        ).all()
    )
    if result.applied:
        session.commit()
        # A process that started with nothing it could serve is ready now (0.12 R, R-F9).
        model_registry.refresh_servable(session)
    return ModelReleaseRaisingResponse(
        applied=result.applied,
        releaseId=result.release.public_id,
        releaseKey=result.release.release_key,
        releaseVersion=result.release.release_version,
        schemaFrom=result.schema_from,
        schemaTo=result.schema_to,
        consumerApisRewritten=result.rewritten,
        modelHash=result.model_hash,
        workspaces=[
            ModelReleaseRaisingWorkspace(key=key, label=labels[key]) for key in result.workspaces
        ],
    )


def load_release(session: DbSession, release_id: str) -> ModelRelease:
    release = session.scalar(select(ModelRelease).where(ModelRelease.public_id == release_id))
    if release is None:
        raise _release_not_found(release_id)
    return release


def _release_not_found(release_id: str):
    return api_error(404, "MODEL_RELEASE_NOT_FOUND", f"Model release '{release_id}' not found")
