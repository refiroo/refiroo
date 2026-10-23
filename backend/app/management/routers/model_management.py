from typing import Any

from fastapi import APIRouter, Query, Request, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ...common.cursors import METADATA_CURSOR_MESSAGE
from ...common.pagination import datetime_key, integer_key, paginate_statement, text_key
from ...common.time import as_utc
from ...engine.model.authoring import history
from ...engine.model.authoring.consumer_documents import (
    draft_consumer_api,
    draft_example,
    draft_openapi,
    draft_schema,
)
from ...engine.model.authoring.outline import draft_model, draft_outline
from ...engine.model.authoring.released import base_model, base_release
from ...engine.model.compiler import (
    SCHEMA_VERSIONS,
    compile_authored_model,
    compile_model,
)
from ...engine.model.diff import semantic_diff
from ...engine.model.draft_compatibility import assess
from ...engine.model.drafts import (
    base_release_public_id,
    create_draft,
    delete_draft,
    load_draft,
    load_draft_for_update,
    require_draft_version,
    update_draft,
)
from ...engine.model.migrations import submit_migration
from ...engine.model.registry import model_registry
from ...engine.model.releases import (
    ActivationConflict,
    ConsumerContractVersionRequired,
    InvalidInstalledModel,
    ModelMigrationRequired,
    ModelReleaseNotFound,
    ReleaseIdentityConflict,
    UnsupportedModelSchema,
    WorkspaceNotFound,
    WorkspaceRetired,
    activate_model_release,
    install_model_release,
)
from ...engine.model.workspace_models import workspaces_running
from ...engine.sources import draft_profile
from ...engine.sources.inference import run as inference
from ...errors import api_error
from ...models.database import AuditEvent, ModelDraft, ModelDraftOperation
from ..access import (
    INSTANCE,
    WORKSPACE_PATH,
    AuthorizedRoute,
    requires,
)
from ..dependencies import DbSession, DefaultModelSnapshot
from ..paging import PageQuery
from ..presenters import (
    candidate_compatibility_response,
    change_response,
    consumer_contracts_response,
    diagnostic_details,
    diagnostic_response,
    job_responses,
)
from ..schemas.jobs import JobResponse
from ..schemas.model import (
    CandidateCompatibilityResponse,
    ModelCompilationResponse,
    ModelDraftConsumerApiResponse,
    ModelDraftCreate,
    ModelDraftModelResponse,
    ModelDraftOperationEntry,
    ModelDraftOperationPage,
    ModelDraftOperationsRequest,
    ModelDraftOutlineResponse,
    ModelDraftPage,
    ModelDraftProfileResponse,
    ModelDraftResponse,
    ModelDraftStepResponse,
    ModelDraftUndoRequest,
    ModelDraftUpdate,
    ModelDraftVersionRequest,
    ModelInstallationResponse,
)
from ..schemas.workspaces import (
    ChangeSetLeftBehind,
    WorkspaceMigrationRequest,
    WorkspaceModelActivation,
    WorkspaceModelActivationResponse,
)
from ..steps import step_response

router = APIRouter(route_class=AuthorizedRoute, prefix="/api/v1", tags=["model administration"])
# Migrations are model administration and background jobs both (D14): registered with
# MODEL_ADMIN_MUTATIONS_ENABLED and INTEGRATION_JOBS_ENABLED.
migration_router = APIRouter(
    route_class=AuthorizedRoute, prefix="/api/v1", tags=["model administration"]
)

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
    "/workspaces/{workspace_key}/model/activation",
    response_model=WorkspaceModelActivationResponse,
)
@requires("model.activate", at=WORKSPACE_PATH)
def activate_workspace_model(
    workspace_key: str, payload: WorkspaceModelActivation, session: DbSession
) -> WorkspaceModelActivationResponse:
    """Activate an installed release into one workspace (0.11 M1, ADR-042): its compatibility check
    counts that workspace's data alone, and the other workspaces keep their releases."""
    try:
        activated = activate_model_release(
            session,
            workspace_key,
            str(payload.releaseId),
            expected_version=payload.expectedVersion,
            expected_release_id=str(payload.expectedReleaseId),
        )
    except WorkspaceNotFound as exc:
        raise api_error(
            404, "WORKSPACE_NOT_FOUND", f"Workspace '{exc.workspace_key}' not found"
        ) from exc
    except ModelReleaseNotFound as exc:
        raise api_error(
            404,
            "MODEL_RELEASE_NOT_FOUND",
            f"Model release '{exc.release_id}' not found",
        ) from exc
    except ActivationConflict as exc:
        raise api_error(
            409,
            "ACTIVATION_CONFLICT",
            f"The model of workspace '{exc.workspace_key}' changed before activation",
            {
                "workspaceKey": exc.workspace_key,
                "currentReleaseId": exc.current_release_id,
                "currentVersion": exc.current_version,
            },
        ) from exc
    except WorkspaceRetired as exc:
        raise api_error(
            409,
            "WORKSPACE_RETIRED",
            f"Workspace '{exc.workspace_key}' is retired; its model is not changed",
            {"workspaceKey": exc.workspace_key},
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
            f"Data of workspace '{workspace_key}' is incompatible with the candidate model",
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

    response = WorkspaceModelActivationResponse(
        workspaceKey=workspace_key,
        releaseId=activated.release.public_id,
        releaseKey=activated.release.release_key,
        releaseName=activated.release.release_name,
        releaseVersion=activated.release.release_version,
        schemaVersion=activated.release.schema_version,
        modelHash=activated.release.model_hash,
        version=activated.version,
        updatedAt=activated.updated_at,
        changeSetsLeftBehind=[
            ChangeSetLeftBehind(id=item.id, name=item.name, version=item.version)
            for item in activated.change_sets_left_behind
        ],
    )
    session.commit()
    try:
        model_registry.warm(activated.release.id)
    except Exception as exc:
        model_registry.withdraw(activated.release)
        raise api_error(
            503,
            "MODEL_REGISTRY_REFRESH_FAILED",
            "The model was activated, but this process could not load the new release",
            {
                "workspaceKey": workspace_key,
                "releaseId": response.releaseId,
                "version": response.version,
            },
        ) from exc
    return response


@migration_router.post(
    "/workspaces/{workspace_key}/model/migrations", response_model=JobResponse, status_code=202
)
@requires("model.activate", at=WORKSPACE_PATH)
def start_workspace_migration(
    workspace_key: str, payload: WorkspaceMigrationRequest, request: Request, session: DbSession
) -> JobResponse:
    """Preview a migration of the workspace's data to an installed release (0.11 V1).

    Answers 202 with a queued ``migration`` job. Its preview lists every conversion, type change,
    loss and refusal of this workspace's data under the target release at ``GET
    /jobs/{jobId}/rows`` and changes nothing; the job then waits for ``POST /jobs/{jobId}/confirm``
    with its ``migration`` summary's ``expectedVersion`` and ``feedPosition`` (and ``acceptLoss``
    when it removes anything), after which the data and the workspace's release switch in one
    transaction. ``typeMappings`` names what a type of the workspace's model became in the target,
    so its records keep their IDs. Refused before a job exists: ``404 WORKSPACE_NOT_FOUND``, ``404
    MODEL_RELEASE_NOT_FOUND``, ``409 WORKSPACE_RETIRED``, ``409 ACTIVATION_CONFLICT`` (the
    assignment changed since ``expectedVersion``), ``422 UNSUPPORTED_SCHEMA_VERSION``, ``422
    MIGRATION_TARGET_IS_CURRENT``, ``422 INVALID_MIGRATION_MAPPING`` (at ``details.pointer``),
    ``409 CONSUMER_CONTRACT_VERSION_REQUIRED`` (as on activation).

    Naming ``changeSetId`` with ``expectedChangeSetVersion`` (0.11 V2) migrates the workspace to
    that change set's release (``targetReleaseId`` may be left out) and publishes the change set in
    the same transaction; the preview also lists what would stop the publication as refused items.
    Refused before a job exists: ``404 CHANGE_SET_NOT_FOUND`` (not a change set of this
    workspace), ``409 CHANGE_SET_VERSION_CONFLICT``, ``422 MIGRATION_TARGET_NOT_CHANGE_SET_RELEASE``,
    and ``422 MIGRATION_TARGET_IS_CURRENT`` for a change set on the workspace's own release."""
    try:
        job = submit_migration(
            session,
            workspace_key,
            target_release_id=str(payload.targetReleaseId) if payload.targetReleaseId else None,
            expected_version=payload.expectedVersion,
            type_mappings=[item.model_dump(by_alias=True) for item in payload.typeMappings],
            retention_days=request.app.state.batch_limits.retention_days,
            change_set_id=payload.changeSetId,
            expected_change_set_version=payload.expectedChangeSetVersion,
        )
    except ConsumerContractVersionRequired as exc:
        raise api_error(
            409,
            "CONSUMER_CONTRACT_VERSION_REQUIRED",
            "A consumer API definition changes what this workspace's consumers read; raise its"
            " contractVersion in a new release",
            diagnostic_details(exc.diagnostics),
        ) from exc
    session.commit()
    worker = getattr(request.app.state, "job_worker", None)
    if worker is not None:
        worker.wake()
    return job_responses(session, [job])[0]


@router.get("/model-drafts", response_model=ModelDraftPage)
@requires("model.author", at=INSTANCE)
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
@requires("model.author", at=INSTANCE)
def get_model_draft(draft_id: str, session: DbSession) -> ModelDraftResponse:
    return draft_response(session, load_draft(session, draft_id))


@router.post(
    "/model-drafts",
    response_model=ModelDraftResponse,
    status_code=status.HTTP_201_CREATED,
)
@requires("model.author", at=INSTANCE)
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
@requires("model.author", at=INSTANCE)
def patch_model_draft(
    draft_id: str, payload: ModelDraftUpdate, session: DbSession
) -> ModelDraftResponse:
    previous = (
        load_draft_for_update(session, draft_id).model_json if payload.model is not None else None
    )
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


@router.post(
    "/model-drafts/{draft_id}/operations",
    response_model=ModelDraftStepResponse,
    response_model_exclude_unset=True,
)
@requires("model.author", at=INSTANCE)
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
    return step_response(session, result, request)


@router.get("/model-drafts/{draft_id}/operations", response_model=ModelDraftOperationPage)
@requires("model.author", at=INSTANCE)
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
    return ModelDraftOperationPage(items=[_entry(row) for row in page.items], **page.links())


@router.get(
    "/model-drafts/{draft_id}/outline",
    response_model=ModelDraftOutlineResponse,
    response_model_by_alias=True,
    response_model_exclude_unset=True,
)
@requires("model.author", at=INSTANCE)
def get_model_draft_outline(draft_id: str, session: DbSession) -> ModelDraftOutlineResponse:
    """The draft's structure as the editor shows it (0.10 A4a, D36), with each consumer API's
    contract against the release the draft is compared with (0.10 A4c, D55; 0.11 D37)."""
    draft = load_draft(session, draft_id)
    outline = draft_outline(session, draft, base_model(session, draft))
    return ModelDraftOutlineResponse.model_validate(outline)


@router.get(
    "/model-drafts/{draft_id}/model",
    response_model=ModelDraftModelResponse,
    response_model_exclude_unset=True,
)
@requires("model.author", at=INSTANCE)
def get_model_draft_model(draft_id: str, session: DbSession) -> ModelDraftModelResponse:
    """The draft compiled as ``GET /model`` serves the active model, with its placements, for a
    preview before installing (0.10 A4b, D43). It reads and writes nothing."""
    return ModelDraftModelResponse.model_validate(draft_model(load_draft(session, draft_id)))


@router.get(
    "/model-drafts/{draft_id}/consumer-apis/{consumer_api}",
    response_model=ModelDraftConsumerApiResponse,
    response_model_exclude_unset=True,
)
@requires("model.author", at=INSTANCE)
def get_model_draft_consumer_api(
    draft_id: str, consumer_api: str, session: DbSession
) -> ModelDraftConsumerApiResponse:
    """A consumer API definition of the draft as written and, when the draft compiles, with every
    default and its contract against the release the draft is compared with (0.10 A4c, D56; 0.11
    D37), compatible for a new model. It reads and writes nothing."""
    draft = load_draft(session, draft_id)
    answer = draft_consumer_api(draft, consumer_api, base_model(session, draft))
    return ModelDraftConsumerApiResponse.model_validate(answer)


@router.get(
    "/model-drafts/{draft_id}/consumer-apis/{consumer_api}/schema.json",
    response_model=dict[str, Any],
)
@requires("model.author", at=INSTANCE)
def get_model_draft_consumer_api_schema(
    draft_id: str, consumer_api: str, request: Request, session: DbSession
) -> dict[str, Any]:
    """The JSON Schema of the object message the definition serves, from the draft (D56)."""
    return draft_schema(
        load_draft(session, draft_id),
        consumer_api,
        resolve_max_items=request.app.state.consumer_resolve_max_items,
    )


@router.get(
    "/model-drafts/{draft_id}/consumer-apis/{consumer_api}/example.json",
    response_model=dict[str, Any],
)
@requires("model.author", at=INSTANCE)
def get_model_draft_consumer_api_example(
    draft_id: str, consumer_api: str, request: Request, session: DbSession
) -> dict[str, Any]:
    """One object message valid against the definition's schema, written from it; no record is read (D56)."""
    return draft_example(
        load_draft(session, draft_id),
        consumer_api,
        resolve_max_items=request.app.state.consumer_resolve_max_items,
    )


@router.get(
    "/model-drafts/{draft_id}/consumer-apis/{consumer_api}/openapi.json",
    response_model=dict[str, Any],
)
@requires("model.author", at=INSTANCE)
def get_model_draft_consumer_api_openapi(
    draft_id: str, consumer_api: str, request: Request, session: DbSession
) -> dict[str, Any]:
    """The definition's OpenAPI document as the consumer tier will serve it from this draft (D56)."""
    return draft_openapi(
        load_draft(session, draft_id),
        consumer_api,
        root_path=request.scope.get("root_path", ""),
        resolve_max_items=request.app.state.consumer_resolve_max_items,
        token_url=f"{request.app.state.identity_settings.issuer}/oauth/token",
    )


@router.post(
    "/model-drafts/{draft_id}/undo",
    response_model=ModelDraftStepResponse,
    response_model_exclude_unset=True,
)
@requires("model.author", at=INSTANCE)
def undo_model_draft_step(
    draft_id: str, payload: ModelDraftUndoRequest, session: DbSession, request: Request
) -> ModelDraftStepResponse:
    result = history.undo(session, draft_id, payload.expectedVersion, payload.step, payload.steps)
    return step_response(session, result, request)


@router.post(
    "/model-drafts/{draft_id}/redo",
    response_model=ModelDraftStepResponse,
    response_model_exclude_unset=True,
)
@requires("model.author", at=INSTANCE)
def redo_model_draft_step(
    draft_id: str, payload: ModelDraftVersionRequest, session: DbSession, request: Request
) -> ModelDraftStepResponse:
    result = history.redo(session, draft_id, payload.expectedVersion)
    return step_response(session, result, request)


@router.get("/model-drafts/{draft_id}/profile", response_model=ModelDraftProfileResponse)
@requires("model.author", at=INSTANCE)
def get_model_draft_profile(draft_id: str, session: DbSession) -> ModelDraftProfileResponse:
    """The draft's import profile (0.10 A5, D75): as the draft holds it, the import profile it
    stands for, its warnings against the draft's model, and the source file it binds. It reads
    and writes nothing."""
    draft = load_draft(session, draft_id)
    answer = draft_profile.read(session, draft)
    # What the latest inference found otherwise (0.10 A6, D92): reminders, never a blocker.
    found = [*answer["diagnostics"], *inference.disagreement_diagnostics(session, draft)]
    answer["diagnostics"] = [diagnostic_response(item) for item in found]
    return ModelDraftProfileResponse.model_validate(answer)


def _entry(row: ModelDraftOperation) -> ModelDraftOperationEntry:
    return ModelDraftOperationEntry(**history.entry_response(row))


@router.delete("/model-drafts/{draft_id}", status_code=status.HTTP_204_NO_CONTENT)
@requires("model.author", at=INSTANCE)
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
@requires("model.author", at=INSTANCE)
def compile_model_draft(
    draft_id: str,
    payload: ModelDraftVersionRequest,
    session: DbSession,
    snapshot: DefaultModelSnapshot,
) -> ModelCompilationResponse:
    draft = load_draft(session, draft_id)
    require_draft_version(draft, payload.expectedVersion)
    compiled = compile_authored_model(draft.model_json)
    if not compiled.valid or compiled.model is None:
        # `changes` is sent empty, not left out: an answer's lists are always present (a client read
        # its length and blanked the page, reported 2026-10-14).
        return ModelCompilationResponse(
            valid=False,
            diagnostics=[diagnostic_response(item) for item in compiled.diagnostics],
            changes=[],
            compatibility=CandidateCompatibilityResponse(
                classification="invalid",
                activeReleaseId=snapshot.release_id,
                diagnostics=[],
                workspaces=[],
            ),
        )
    if compiled.canonical_model is None:
        raise api_error(500, "INTERNAL_ERROR", "Compiled model result is incomplete")
    # D37: compared with its base, or the newest release of its model; a new model with nothing.
    baseline_release = base_release(session, draft)
    baseline = None
    if baseline_release is not None:
        baseline = compile_model(baseline_release.model_json)
        if not baseline.valid or baseline.canonical_model is None or baseline.model is None:
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
    changes = semantic_diff(baseline.canonical_model if baseline else {}, compiled.canonical_model)

    return ModelCompilationResponse(
        valid=True,
        model=compiled.canonical_model,
        modelHash=compiled.model_hash,
        diagnostics=[diagnostic_response(item) for item in compiled.diagnostics],
        againstReleaseId=baseline_release.public_id if baseline_release else None,
        changes=[change_response(item) for item in changes],
        compatibility=candidate_compatibility_response(assess(session, snapshot, compiled.model)),
        consumerContracts=consumer_contracts_response(
            baseline.model, compiled.model, baseline_release.public_id
        )
        if baseline is not None and baseline_release is not None
        else None,
    )


@router.post(
    "/model-drafts/{draft_id}/installation",
    response_model=ModelInstallationResponse,
    response_model_exclude_none=True,
    status_code=status.HTTP_201_CREATED,
)
@requires("model.install", at=INSTANCE)
def install_model_draft(
    draft_id: str,
    payload: ModelDraftVersionRequest,
    session: DbSession,
    response: Response,
) -> ModelInstallationResponse:
    draft = load_draft_for_update(session, draft_id)
    require_draft_version(draft, payload.expectedVersion)
    compiled = compile_authored_model(draft.model_json)
    if compiled.unsupported_schema_version is not None:
        # A version outside the window is refused as activation refuses one (0.11 V4, D98).
        raise api_error(
            422,
            "UNSUPPORTED_SCHEMA_VERSION",
            f"Model draft uses schema version '{compiled.unsupported_schema_version}', which this"
            f" deployment does not support; supported versions: {', '.join(SCHEMA_VERSIONS)}",
            {
                "draftId": draft.public_id,
                "schemaVersion": compiled.unsupported_schema_version,
                "supportedSchemaVersions": list(SCHEMA_VERSIONS),
                "operation": "install",
            },
        )
    if not compiled.valid or compiled.model is None:
        raise api_error(
            422,
            "INVALID_MODEL",
            "Model draft is invalid and cannot be installed",
            diagnostic_details(compiled.diagnostics),
        )
    # Installing is instance-wide and checks no workspace's data; activation does (ADR-042).
    draft_profile.require_installable(session, draft, compiled.model)
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
    # D80: the draft's import profile becomes the instance profile of its key.
    saved = draft_profile.save_at_installation(session, draft, release, compiled.model)
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
    return ModelInstallationResponse(
        id=release.public_id,
        key=release.release_key,
        name=release.release_name,
        version=release.release_version,
        schemaVersion=release.schema_version,
        modelHash=release.model_hash,
        installedAt=as_utc(release.installed_at),
        assigned=bool(running := workspaces_running(session, release.id)),
        workspaces=running,
        importProfile={"key": saved.key, "version": saved.version} if saved is not None else None,
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
