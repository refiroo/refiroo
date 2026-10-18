from fastapi import APIRouter, Query, Request, status
from sqlalchemy import select

from ...common.pagination import (
    PageRequest,
    integer_key,
    paginate_sequence,
    paginate_statement,
    text_key,
)
from ...db import begin_snapshot_read
from ...engine.change_sets.access import effective_change_set_membership
from ...engine.change_sets.lifecycle import create_change_set, discard_change_set, update_change_set
from ...engine.change_sets.pinning import (
    pinned_model,
    selected_change_set_release,
    set_change_set_model_release,
)
from ...engine.change_sets.publish import publish_change_set, withdraw_publication
from ...engine.change_sets.validation import validate_change_set
from ...engine.model.change_set_migrations import submit_change_set_migration
from ...engine.model.registry import resolve_model_snapshot, resolve_pinned_release
from ...engine.model.workspace_models import load_assignment
from ...engine.operations.restructuring import (
    ChangeTypeOperation,
    ChangeTypeUnderOperation,
    InsertLevelOperation,
    MappingChoice,
    MoveOperation,
    Operation,
    RecordInputs,
    RemoveLevelOperation,
    Restructuring,
    TypeChoice,
    apply_restructuring,
    page_plan_records,
    preview_restructuring,
)
from ...engine.operations.type_changes import RelationInput
from ...engine.reads.change_lists import (
    ObjectChangeEntry,
    RelationChangeEntry,
    RelationEnd,
    list_object_changes,
    list_relation_changes,
)
from ...engine.reads.snapshot_reads import change_set_context
from ...engine.workspaces.catalogue import load_workspace
from ...engine.workspaces.workspace_audit import record_change_set_validated
from ...errors import ApiError, api_error
from ...models.database import ChangeSet, ModelRelease, Publication
from ..dependencies import DbSession
from ..paging import PageQuery
from ..presenters import job_responses, snapshot_attributes
from ..schemas.change_sets import (
    ChangeKind,
    ChangeSetCreate,
    ChangeSetMigrationRequest,
    ChangeSetModelReleaseUpdate,
    ChangeSetPage,
    ChangeSetPublishRequest,
    ChangeSetResponse,
    ChangeSetUpdate,
    ChangeSetValidation,
    ObjectChange,
    ObjectChangePage,
    ObjectChangeState,
    PublicationPage,
    PublicationResponse,
    RelationChange,
    RelationChangeEnd,
    RelationChangePage,
    RelationChangeState,
)
from ..schemas.jobs import JobResponse
from ..schemas.records import ObjectPathPart
from ..schemas.restructuring import (
    RestructuringApplyRequest,
    RestructuringPreview,
    RestructuringPreviewRequest,
    RestructuringRequest,
    RestructuringResult,
)

# The change-set workflow is an ordinary steward operation like a live edit (ADR-031): always
# registered, and refused in a retired workspace by the services it calls. Only workspace catalogue
# administration sits behind WORKSPACE_ADMIN_MUTATIONS_ENABLED.
router = APIRouter(prefix="/api/v1", tags=["change-sets"])
# A change set's move onto another release is a background job (0.11 V3, D93): registered where
# INTEGRATION_JOBS_ENABLED runs them.
migration_router = APIRouter(prefix="/api/v1", tags=["change-sets"])


def _change_set_response(session, item: ChangeSet) -> ChangeSetResponse:
    release = session.get(ModelRelease, item.model_release_id)
    source = (
        "currentLive"
        if item.base_id is not None
        else "publication"
        if item.derived_from_publication_id
        else "empty"
    )
    return ChangeSetResponse(
        id=item.id,
        workspaceKey=item.workspace_key,
        name=item.name,
        modelReleaseId=release.public_id if release else str(item.model_release_id),
        modelReleaseKey=release.release_key if release else "unavailable",
        modelReleaseVersion=release.release_version if release else "unavailable",
        source=source,
        derivedFromPublicationId=item.derived_from_publication_id,
        version=item.version,
        createdAt=item.created_at,
        updatedAt=item.updated_at,
    )


def _publication_response(session, item: Publication) -> PublicationResponse:
    release = session.get(ModelRelease, item.model_release_id)
    return PublicationResponse(
        id=item.id,
        workspaceKey=item.workspace_key,
        modelReleaseId=release.public_id if release else str(item.model_release_id),
        modelReleaseKey=release.release_key if release else "unavailable",
        modelReleaseVersion=release.release_version if release else "unavailable",
        publicationNumber=item.publication_number,
        status=item.status,
        derivedFromPublicationId=item.derived_from_publication_id,
        supersedesPublicationId=item.supersedes_publication_id,
        createdAt=item.created_at,
        publishedAt=item.published_at,
        withdrawnAt=item.withdrawn_at,
        feedPosition=item.feed_position,
    )


@router.get("/workspaces/{workspace_key}/change-sets", response_model=ChangeSetPage)
def list_change_sets(
    workspace_key: str,
    session: DbSession,
    paging: PageQuery,
    page_size: int = Query(default=100, ge=1, le=500, alias="pageSize"),
) -> ChangeSetPage:
    load_workspace(session, workspace_key)
    items = list(session.scalars(select(ChangeSet).where(ChangeSet.workspace_key == workspace_key)))
    page = paginate_sequence(
        items,
        lambda x: (x.created_at.isoformat(), x.id),
        scope="change-sets",
        filters={"workspaceKey": workspace_key},
        page=paging,
        page_size=page_size,
        sort=("createdAt", "id"),
        message="Change set cursor is invalid",
    )
    return ChangeSetPage(
        items=[_change_set_response(session, x) for x in page.items], **page.links()
    )


@router.post(
    "/workspaces/{workspace_key}/change-sets",
    response_model=ChangeSetResponse,
    status_code=status.HTTP_201_CREATED,
)
def post_change_set(
    workspace_key: str,
    payload: ChangeSetCreate,
    session: DbSession,
) -> ChangeSetResponse:
    selected = (
        selected_change_set_release(session, str(payload.modelReleaseId))
        if payload.modelReleaseId
        else None
    )
    active_release_id = load_assignment(session, workspace_key)[1].id
    if not selected:
        resolve_model_snapshot(session, workspace_key)
    return _change_set_response(
        session,
        create_change_set(
            session,
            workspace_key,
            selected.id if selected else active_release_id,
            name=payload.name,
            source_publication_id=str(payload.derivedFromPublicationId)
            if payload.derivedFromPublicationId
            else None,
            source=payload.source,
            expected_model_runtime_release_id=active_release_id,
            validate_selected_model=selected is not None,
        ),
    )


@router.get("/change-sets/{change_set_id}", response_model=ChangeSetResponse)
def get_change_set(change_set_id: str, session: DbSession) -> ChangeSetResponse:
    # ChangeSet's ORM primary key is the autoincrement sequence_id, so session.get by the
    # stable public id would always miss; resolve through the unique id column instead.
    item = session.scalar(select(ChangeSet).where(ChangeSet.id == change_set_id))
    if item is None:
        raise api_error(404, "CHANGE_SET_NOT_FOUND", "Change set not found")
    return _change_set_response(session, item)


@router.patch("/change-sets/{change_set_id}", response_model=ChangeSetResponse)
def patch_change_set(
    change_set_id: str, payload: ChangeSetUpdate, session: DbSession
) -> ChangeSetResponse:
    return _change_set_response(
        session, update_change_set(session, change_set_id, payload.expectedVersion, payload.name)
    )


@router.patch("/change-sets/{change_set_id}/model-release", response_model=ChangeSetResponse)
def patch_change_set_model_release(
    change_set_id: str, payload: ChangeSetModelReleaseUpdate, session: DbSession
) -> ChangeSetResponse:
    return _change_set_response(
        session,
        set_change_set_model_release(
            session,
            change_set_id,
            str(payload.modelReleaseId),
            payload.expectedChangeSetVersion,
        ),
    )


@migration_router.post(
    "/change-sets/{change_set_id}/model-migrations", response_model=JobResponse, status_code=202
)
def start_change_set_migration(
    change_set_id: str, payload: ChangeSetMigrationRequest, request: Request, session: DbSession
) -> JobResponse:
    """Preview a move of the change set onto the release its workspace runs (0.11 V3).

    For a change set left on a release its workspace no longer runs, whose content that release
    does not already accept (otherwise ``PATCH /change-sets/{id}/model-release`` moves it). Answers
    202 with a queued ``migration`` job naming the change set. Its preview converts the change
    set's own content to the workspace's release over live data as it is now and lists every
    conversion, type change, loss and refusal at ``GET /jobs/{jobId}/rows``, changing nothing; a
    record the change set changed that live data changed since its start is refused as
    ``CHANGE_SET_CONFLICT``. The job then waits for ``POST /jobs/{jobId}/confirm`` with its
    ``migration`` summary's ``expectedVersion`` and ``feedPosition`` (and ``acceptLoss`` when it
    removes anything from the change set); the change set's content, base and release then change
    in one transaction. Live data, the workspace's release and its feed are never changed. Refused
    before a job exists: ``404 CHANGE_SET_NOT_FOUND``, ``409 CHANGE_SET_VERSION_CONFLICT``, ``409
    WORKSPACE_RETIRED``, ``422 MIGRATION_TARGET_NOT_WORKSPACE_RELEASE``, ``422
    MIGRATION_TARGET_IS_CURRENT``, ``422 UNSUPPORTED_SCHEMA_VERSION``, ``422
    INVALID_MIGRATION_MAPPING`` (at ``details.pointer``)."""
    job = submit_change_set_migration(
        session,
        change_set_id,
        expected_change_set_version=payload.expectedChangeSetVersion,
        target_release_id=str(payload.targetReleaseId) if payload.targetReleaseId else None,
        type_mappings=[item.model_dump(by_alias=True) for item in payload.typeMappings],
        retention_days=request.app.state.batch_limits.retention_days,
    )
    session.commit()
    worker = getattr(request.app.state, "job_worker", None)
    if worker is not None:
        worker.wake()
    return job_responses(session, [job])[0]


@router.delete("/change-sets/{change_set_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_change_set(
    change_set_id: str,
    session: DbSession,
    expected_version: int = Query(alias="expectedVersion", ge=1),
) -> None:
    discard_change_set(session, change_set_id, expected_version)


_KIND = Query(
    default=None,
    description="Only these kinds (repeatable): added, changed or removed; every kind when omitted",
)
_OBJECT_TYPE_KEY = Query(
    default=None,
    alias="objectTypeKey",
    description=(
        "Only records of these types (repeatable), under the change set's model; a record whose"
        " type the change set changed matches either type"
    ),
)
_RELATION_TYPE_KEY = Query(
    default=None,
    alias="relationTypeKey",
    description="Only relations of these types (repeatable), under the change set's model",
)


def _pinned_model(session, context):
    """The change set's pinned model, from the change set row its context already read."""
    return resolve_pinned_release(
        session, context.change_set.model_release_id, require_ready=False
    ).model


def _object_change(model, entry: ObjectChangeEntry) -> ObjectChange:
    def state(side) -> ObjectChangeState | None:
        if side is None:
            return None
        return ObjectChangeState(
            objectTypeKey=side.object_type_key,
            name=side.name,
            parentObjectId=side.parent_object_id,
            attributes=snapshot_attributes(model, entry.object_id, side.attributes),
            version=side.version,
        )

    return ObjectChange(
        kind=entry.kind,
        objectId=entry.object_id,
        objectTypeKey=entry.object_type_key,
        applicationKey=entry.application_key,
        before=state(entry.before),
        after=state(entry.after),
        changedFields=entry.changed_fields,
        path=[ObjectPathPart(**part) for part in entry.path],
        beforePath=(
            None
            if entry.before_path is None
            else [ObjectPathPart(**part) for part in entry.before_path]
        ),
    )


def _relation_end(end: RelationEnd) -> RelationChangeEnd:
    return RelationChangeEnd(
        objectId=end.object_id, objectTypeKey=end.object_type_key, name=end.name
    )


def _relation_change(entry: RelationChangeEntry) -> RelationChange:
    def state(side) -> RelationChangeState | None:
        if side is None:
            return None
        return RelationChangeState(attributes=side.attributes, version=side.version)

    return RelationChange(
        kind=entry.kind,
        relationId=entry.relation_id,
        relationTypeKey=entry.relation_type_key,
        containment=entry.containment,
        fromObject=_relation_end(entry.from_end),
        toObject=_relation_end(entry.to_end),
        before=state(entry.before),
        after=state(entry.after),
        changedFields=entry.changed_fields,
    )


@router.get("/change-sets/{change_set_id}/object-changes", response_model=ObjectChangePage)
def get_object_changes(
    change_set_id: str,
    session: DbSession,
    paging: PageQuery,
    page_size: int = Query(default=100, ge=1, le=500, alias="pageSize"),
    kind: list[ChangeKind] | None = _KIND,
    object_type_key: list[str] | None = _OBJECT_TYPE_KEY,
) -> ObjectChangePage:
    """The records the change set adds, changes or removes against its source (Base 0.8 P2a)."""
    # The page, its paths and the pinned model read one snapshot: a write landing between them
    # would otherwise mix two states of the change set in one page.
    begin_snapshot_read(session)
    context = change_set_context(session, change_set_id)
    model = _pinned_model(session, context)
    page = list_object_changes(
        session,
        context,
        model,
        kinds=kind,
        object_type_keys=object_type_key,
        page=paging,
        page_size=page_size,
    )
    return ObjectChangePage(
        items=[_object_change(model, entry) for entry in page.items], **page.links()
    )


@router.get("/change-sets/{change_set_id}/relation-changes", response_model=RelationChangePage)
def get_relation_changes(
    change_set_id: str,
    session: DbSession,
    paging: PageQuery,
    page_size: int = Query(default=100, ge=1, le=500, alias="pageSize"),
    kind: list[ChangeKind] | None = _KIND,
    relation_type_key: list[str] | None = _RELATION_TYPE_KEY,
    containment: bool | None = Query(
        default=None,
        description=(
            "true lists only engine-maintained parent edges, false leaves them out; both when"
            " omitted"
        ),
    ),
) -> RelationChangePage:
    """The relations the change set adds, changes or removes against its source (Base 0.8 P2a)."""
    begin_snapshot_read(session)
    context = change_set_context(session, change_set_id)
    model = _pinned_model(session, context)
    page = list_relation_changes(
        session,
        context,
        model,
        kinds=kind,
        relation_type_keys=relation_type_key,
        containment=containment,
        page=paging,
        page_size=page_size,
    )
    return RelationChangePage(
        items=[_relation_change(entry) for entry in page.items], **page.links()
    )


def _operation(payload: RestructuringRequest) -> Operation:
    operation = payload.operation
    match operation.kind:
        case "move":
            return MoveOperation(
                str(operation.objectId),
                str(operation.parentObjectId) if operation.parentObjectId else None,
                operation.objectTypeKey,
            )
        case "changeType":
            return ChangeTypeOperation(str(operation.objectId), operation.objectTypeKey)
        case "insertLevel":
            return InsertLevelOperation(
                str(operation.parentObjectId) if operation.parentObjectId else None,
                tuple(str(item) for item in operation.childObjectIds),
                operation.objectTypeKey,
                operation.name,
            )
        case "removeLevel":
            return RemoveLevelOperation(str(operation.objectId))
        case _:
            return ChangeTypeUnderOperation(
                str(operation.objectId), operation.fromObjectTypeKey, operation.objectTypeKey
            )


def _restructuring(payload: RestructuringRequest) -> Restructuring:
    return Restructuring(
        operation=_operation(payload),
        type_choices=[
            TypeChoice(item.objectTypeKey, item.parentObjectTypeKey, item.newObjectTypeKey)
            for item in payload.choices.types
        ],
        mapping_choices=[
            MappingChoice(
                item.fromObjectTypeKey,
                item.toObjectTypeKey,
                {attribute.attributeTypeKey: attribute.from_ for attribute in item.attributes},
                item.restore,
            )
            for item in payload.choices.mappings
        ],
        inputs=[
            RecordInputs(
                item.objectId.lower(),
                {attribute.attributeTypeKey: attribute.value for attribute in item.attributes},
                tuple(
                    RelationInput(
                        relation.relationTypeKey,
                        relation.direction,
                        str(relation.objectId),
                        relation.attributes,
                    )
                    for relation in item.relations
                ),
            )
            for item in payload.inputs
        ],
    )


@router.post(
    "/change-sets/{change_set_id}/restructurings/preview", response_model=RestructuringPreview
)
def post_restructuring_preview(
    change_set_id: str, payload: RestructuringPreviewRequest, session: DbSession
) -> RestructuringPreview:
    """Plan a restructuring of a hierarchy in a change set and write nothing (Base 0.8 C3).

    The plan's records page by position in plan order; ``outcome`` filters them.
    """
    page = PageRequest(
        cursor=payload.cursor,
        position=payload.position,
        from_end=payload.from_ == "end",
        include_total=payload.includeTotal,
    )
    plan = preview_restructuring(
        session,
        change_set_id,
        _restructuring(payload),
        expected_change_set_version=payload.expectedChangeSetVersion,
    )
    found = page_plan_records(plan, payload.outcome, page, payload.pageSize)
    return RestructuringPreview.model_validate({**plan.payload(found.items), **found.links()})


@router.post("/change-sets/{change_set_id}/restructurings", response_model=RestructuringResult)
def post_restructuring(
    change_set_id: str, payload: RestructuringApplyRequest, session: DbSession
) -> RestructuringResult:
    """Apply a previewed restructuring: the plan is recomputed and written only when it is the
    one previewed and ready (Base 0.8 C3)."""
    result = apply_restructuring(
        session,
        change_set_id,
        _restructuring(payload),
        expected_change_set_version=payload.expectedChangeSetVersion,
        plan_digest=payload.planDigest,
    )
    return RestructuringResult(
        operationId=result.operation_id,
        changeSetId=result.change_set_id,
        changeSetVersion=result.change_set_version,
        summary=result.summary,
        createdObjectId=result.created_object_id,
    )


@router.post("/change-sets/{change_set_id}/validation", response_model=ChangeSetValidation)
def post_change_set_validation(change_set_id: str, session: DbSession) -> ChangeSetValidation:
    change_set, change_set_model = pinned_model(session, change_set_id)
    diagnostics = validate_change_set(session, change_set_id, change_set_model)
    # A validation never mutates the change set graph or bumps its version; the audit record is its only
    # side effect and is bounded to identity metadata plus counts (see D3a).  The conflict
    # short-circuit can leave a corrupt base unresolved, so fall back to zero counts instead of
    # failing a validation that already reported its diagnostic.
    try:
        membership = effective_change_set_membership(session, change_set_id)
        object_count, relation_count = len(membership.objects), len(membership.relations)
    except ApiError:
        object_count, relation_count = 0, 0
    record_change_set_validated(
        session,
        change_set=change_set,
        valid=not diagnostics,
        error_codes=[item["code"] for item in diagnostics],
        object_count=object_count,
        relation_count=relation_count,
        error_count=len(diagnostics),
    )
    session.commit()
    return ChangeSetValidation(valid=not diagnostics, diagnostics=diagnostics)


@router.post("/change-sets/{change_set_id}/publication", response_model=PublicationResponse)
def post_change_set_publication(
    change_set_id: str,
    payload: ChangeSetPublishRequest,
    session: DbSession,
) -> PublicationResponse:
    change_set, change_set_model = pinned_model(session, change_set_id)
    snapshot = resolve_model_snapshot(session, change_set.workspace_key)
    publication = publish_change_set(
        session,
        change_set_id,
        change_set_model,
        snapshot.release_db_id,
        payload.expectedChangeSetVersion,
        str(payload.expectedActivePublicationId) if payload.expectedActivePublicationId else None,
    )
    return _publication_response(session, publication)


@router.get("/workspaces/{workspace_key}/publications", response_model=PublicationPage)
def list_publications(
    workspace_key: str,
    session: DbSession,
    paging: PageQuery,
    page_size: int = Query(default=100, ge=1, le=500, alias="pageSize"),
) -> PublicationPage:
    load_workspace(session, workspace_key)
    page = paginate_statement(
        session,
        select(Publication).where(Publication.workspace_key == workspace_key),
        keys=(
            integer_key(
                "publicationNumber",
                Publication.publication_number,
                "publication_number",
                descending=True,
            ),
            text_key("id", Publication.id, "id", descending=True),
        ),
        scope="publications",
        filters={"workspaceKey": workspace_key},
        page=paging,
        page_size=page_size,
        message="Publication cursor is invalid",
    )
    return PublicationPage(
        items=[_publication_response(session, x) for x in page.items], **page.links()
    )


@router.get("/publications/{publication_id}", response_model=PublicationResponse)
def get_publication(publication_id: str, session: DbSession) -> PublicationResponse:
    item = session.scalar(select(Publication).where(Publication.id == publication_id))
    if item is None:
        raise api_error(404, "PUBLICATION_NOT_FOUND", "Publication not found")
    return _publication_response(session, item)


@router.post("/publications/{publication_id}/withdrawal", status_code=status.HTTP_204_NO_CONTENT)
def post_publication_withdrawal(publication_id: str, session: DbSession) -> None:
    withdraw_publication(session, publication_id)
