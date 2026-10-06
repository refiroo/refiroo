from typing import Any

from fastapi import APIRouter, Query, Request, Response

from ...common.cursors import METADATA_CURSOR_MESSAGE
from ...common.pagination import paginate_sequence
from ...common.time import as_utc
from ...engine.events import delivery
from ...engine.model.compiler import compile_model
from ...engine.model.placements import model_placements
from ...engine.model.runtime import load_runtime_state
from ...engine.records.rules import get_application, get_object_type
from ...errors import api_error
from ..dependencies import DbSession, RequestModelSnapshot
from ..paging import PageQuery
from ..presenters import diagnostic_response
from ..projections.model_metadata import (
    build_application_responses,
    build_attribute_type_responses,
    build_object_type_relation_responses,
    build_object_type_responses,
    build_relation_type_responses,
)
from ..schemas.model import (
    ApplicationResponse,
    AttributeTypeResponse,
    CapabilitiesResponse,
    ChangeFeedCapabilities,
    ConsumerApiCapabilities,
    ConsumerSubscriptionCapabilities,
    IntegrationJobCapabilities,
    JobLimits,
    MetadataPage,
    ModelAdminCapabilities,
    ModelDocumentRequest,
    ModelPlacements,
    ModelRuntimeStateResponse,
    ModelValidationResponse,
    ObjectTypeRelationResponse,
    ObjectTypeResponse,
    RelationTypeResponse,
    WebhookDeliveryLimits,
    WorkspaceAdminCapabilities,
)

router = APIRouter(prefix="/api/v1", tags=["model"])


@router.get("/capabilities", response_model=CapabilitiesResponse)
def get_capabilities(request: Request) -> CapabilitiesResponse:
    mutations_enabled = bool(request.app.state.model_admin_mutations_enabled)
    jobs_enabled = bool(request.app.state.integration_jobs_enabled)
    limits = request.app.state.batch_limits
    return CapabilitiesResponse(
        modelAdmin=ModelAdminCapabilities(
            readReleases=True,
            manageDrafts=mutations_enabled,
            install=mutations_enabled,
            activate=mutations_enabled,
            setting="MODEL_ADMIN_MUTATIONS_ENABLED",
        ),
        workspaceAdmin=WorkspaceAdminCapabilities(
            manageWorkspaces=bool(request.app.state.workspace_admin_mutations_enabled),
            setting="WORKSPACE_ADMIN_MUTATIONS_ENABLED",
        ),
        integrationJobs=IntegrationJobCapabilities(
            createJobs=jobs_enabled,
            runModes=["inline", "background"] if jobs_enabled else [],
            limits=JobLimits(
                batchMaxItems=limits.max_items,
                batchMaxBytes=limits.max_bytes,
                atomicJobMaxItems=limits.atomic_max_items,
                backgroundJobMaxItems=limits.background_max_items,
                backgroundBatchMaxBytes=limits.background_max_bytes,
                chunkItems=limits.chunk_items,
                retentionDays=limits.retention_days,
            ),
            setting="INTEGRATION_JOBS_ENABLED",
        ),
        changeFeed=ChangeFeedCapabilities(retentionDays=request.app.state.feed_retention_days),
        consumerApi=ConsumerApiCapabilities(
            resolveMaxItems=request.app.state.consumer_resolve_max_items,
            setting="CONSUMER_RESOLVE_MAX_ITEMS",
        ),
        consumerSubscriptions=ConsumerSubscriptionCapabilities(
            manageSubscriptions=bool(request.app.state.consumer_subscriptions_enabled),
            allowedHosts=list(request.app.state.webhook_allowed_hosts),
            delivery=WebhookDeliveryLimits(
                maxEvents=delivery.MAX_EVENTS,
                maxBytes=delivery.MAX_BYTES,
                timeoutSeconds=delivery.TIMEOUT_SECONDS,
                retryWaitsSeconds=list(delivery.RETRY_WAITS),
                laterWaitSeconds=delivery.LATER_WAIT,
                retryHours=delivery.RETRY_HOURS,
            ),
            setting="CONSUMER_SUBSCRIPTIONS_ENABLED",
        ),
    )


@router.get(
    "/model",
    responses={
        200: {
            "headers": {
                "ETag": {
                    "description": "Quoted SHA-256 entity tag of the active immutable model",
                    "schema": {"type": "string"},
                },
                "X-Model-Release-Id": {
                    "description": "Public UUID of the active installed release",
                    "schema": {"type": "string", "format": "uuid"},
                },
            }
        }
    },
)
def get_model(response: Response, snapshot: RequestModelSnapshot) -> dict[str, Any]:
    response.headers["ETag"] = f'"{snapshot.model_hash}"'
    response.headers["X-Model-Release-Id"] = snapshot.release_id
    return snapshot.model.model_dump(mode="json")


@router.get("/model/placements", response_model=ModelPlacements)
def get_model_placements(response: Response, snapshot: RequestModelSnapshot) -> ModelPlacements:
    """Where the context's model lets records stand, per application (Base 0.8 C4): the types at the
    top level and, per type as a parent, the types it contains and the types a record can become
    under it. Derived from the same model as ``GET /model`` in the same context, with its ETag."""
    response.headers["ETag"] = f'"{snapshot.model_hash}"'
    return ModelPlacements.model_validate(model_placements(snapshot.model))


@router.get("/model-runtime-state", response_model=ModelRuntimeStateResponse)
def get_model_runtime_state(session: DbSession) -> ModelRuntimeStateResponse:
    runtime_state, active_release = load_runtime_state(session)
    return ModelRuntimeStateResponse(
        activeReleaseId=active_release.public_id,
        activeModelHash=active_release.model_hash,
        version=runtime_state.version,
        updatedAt=as_utc(runtime_state.updated_at),
    )


@router.post(
    "/model-validations",
    response_model=ModelValidationResponse,
    response_model_exclude_none=True,
)
def validate_model(payload: ModelDocumentRequest) -> ModelValidationResponse:
    compiled = compile_model(payload.model)
    return ModelValidationResponse(
        valid=compiled.valid,
        diagnostics=[diagnostic_response(item) for item in compiled.diagnostics],
    )


@router.get("/applications", response_model=MetadataPage[ApplicationResponse])
def get_applications(
    session: DbSession,
    snapshot: RequestModelSnapshot,
    paging: PageQuery,
    page_size: int = Query(default=100, ge=1, le=500, alias="pageSize"),
) -> MetadataPage[ApplicationResponse]:
    page = paginate_sequence(
        snapshot.model.applications,
        lambda item: (item.key,),
        scope="applications",
        filters={"modelReleaseId": snapshot.release_id},
        page=paging,
        page_size=page_size,
        message=METADATA_CURSOR_MESSAGE,
    )
    return MetadataPage(
        items=build_application_responses(session, snapshot, page.items), **page.links()
    )


@router.get("/applications/{application_key}", response_model=ApplicationResponse)
def get_application_detail(
    application_key: str, session: DbSession, snapshot: RequestModelSnapshot
) -> ApplicationResponse:
    application = get_application(snapshot.model, application_key)
    return build_application_responses(session, snapshot, [application])[0]


@router.get("/attribute-types", response_model=MetadataPage[AttributeTypeResponse])
def list_attribute_types(
    session: DbSession,
    snapshot: RequestModelSnapshot,
    paging: PageQuery,
    page_size: int = Query(default=100, ge=1, le=500, alias="pageSize"),
) -> MetadataPage[AttributeTypeResponse]:
    page = paginate_sequence(
        snapshot.model.attributeTypes,
        lambda item: (item.key,),
        scope="attribute-types",
        filters={"modelReleaseId": snapshot.release_id},
        page=paging,
        page_size=page_size,
        message=METADATA_CURSOR_MESSAGE,
    )
    return MetadataPage(
        items=build_attribute_type_responses(session, snapshot, page.items), **page.links()
    )


@router.get("/attribute-types/{attribute_type_key}", response_model=AttributeTypeResponse)
def get_attribute_type(
    attribute_type_key: str, session: DbSession, snapshot: RequestModelSnapshot
) -> AttributeTypeResponse:
    definition = snapshot.model.attribute_type(attribute_type_key)
    if not definition:
        raise api_error(
            404, "UNKNOWN_ATTRIBUTE_TYPE", f"Attribute type '{attribute_type_key}' not found"
        )
    return build_attribute_type_responses(session, snapshot, [definition])[0]


@router.get("/object-types", response_model=MetadataPage[ObjectTypeResponse])
def list_object_types(
    session: DbSession,
    snapshot: RequestModelSnapshot,
    paging: PageQuery,
    page_size: int = Query(default=100, ge=1, le=500, alias="pageSize"),
) -> MetadataPage[ObjectTypeResponse]:
    page = paginate_sequence(
        snapshot.model.objectTypes,
        lambda item: (item.key,),
        scope="object-types",
        filters={"modelReleaseId": snapshot.release_id},
        page=paging,
        page_size=page_size,
        message=METADATA_CURSOR_MESSAGE,
    )
    return MetadataPage(
        items=build_object_type_responses(session, snapshot, page.items), **page.links()
    )


@router.get("/object-types/{object_type_key}", response_model=ObjectTypeResponse)
def get_object_type_detail(
    object_type_key: str, session: DbSession, snapshot: RequestModelSnapshot
) -> ObjectTypeResponse:
    object_type = get_object_type(snapshot.model, object_type_key)
    return build_object_type_responses(session, snapshot, [object_type])[0]


@router.get("/relation-types", response_model=MetadataPage[RelationTypeResponse])
def list_relation_types(
    session: DbSession,
    snapshot: RequestModelSnapshot,
    paging: PageQuery,
    page_size: int = Query(default=100, ge=1, le=500, alias="pageSize"),
) -> MetadataPage[RelationTypeResponse]:
    page = paginate_sequence(
        snapshot.model.relationTypes,
        lambda item: (item.key,),
        scope="relation-types",
        filters={"modelReleaseId": snapshot.release_id},
        page=paging,
        page_size=page_size,
        message=METADATA_CURSOR_MESSAGE,
    )
    return MetadataPage(
        items=build_relation_type_responses(session, snapshot, page.items), **page.links()
    )


@router.get("/relation-types/{relation_type_key}", response_model=RelationTypeResponse)
def get_relation_type(
    relation_type_key: str, session: DbSession, snapshot: RequestModelSnapshot
) -> RelationTypeResponse:
    definition = snapshot.model.relation_type(relation_type_key)
    if not definition:
        raise api_error(
            404, "UNKNOWN_RELATION_TYPE", f"Relation type '{relation_type_key}' not found"
        )
    return build_relation_type_responses(session, snapshot, [definition])[0]


@router.get("/object-type-relations", response_model=MetadataPage[ObjectTypeRelationResponse])
def get_object_type_relations(
    session: DbSession,
    snapshot: RequestModelSnapshot,
    paging: PageQuery,
    from_object_type: str | None = Query(default=None, alias="fromObjectType"),
    to_object_type: str | None = Query(default=None, alias="toObjectType"),
    page_size: int = Query(default=100, ge=1, le=500, alias="pageSize"),
) -> MetadataPage[ObjectTypeRelationResponse]:
    relations = snapshot.model.objectTypeRelations
    if from_object_type:
        relations = [item for item in relations if item.fromObjectTypeKey == from_object_type]
    if to_object_type:
        relations = [item for item in relations if item.toObjectTypeKey == to_object_type]
    page = paginate_sequence(
        relations,
        lambda item: (
            item.relationTypeKey,
            item.fromObjectTypeKey,
            item.toObjectTypeKey,
        ),
        scope="object-type-relations",
        sort=("relationTypeKey", "fromObjectTypeKey", "toObjectTypeKey"),
        filters={
            "modelReleaseId": snapshot.release_id,
            "fromObjectType": from_object_type,
            "toObjectType": to_object_type,
        },
        page=paging,
        page_size=page_size,
        message=METADATA_CURSOR_MESSAGE,
    )
    return MetadataPage(
        items=build_object_type_relation_responses(session, snapshot, page.items),
        **page.links(),
    )
