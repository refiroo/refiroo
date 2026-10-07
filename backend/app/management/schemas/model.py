from datetime import datetime
from typing import Any, Literal

from pydantic import UUID4, BaseModel, ConfigDict, Field, model_validator

from .common import CollectionPage


class ModelPlacementParent(BaseModel):
    """A type of the application as a parent: the types it contains, and the types a record can
    become under it (a restructuring's possible types, ADR-034)."""

    objectTypeKey: str
    childObjectTypeKeys: list[str]
    possibleObjectTypeKeys: list[str]


class ModelApplicationPlacements(BaseModel):
    applicationKey: str
    topLevelObjectTypeKeys: list[str]
    parents: list[ModelPlacementParent]


class ModelPlacements(BaseModel):
    """Where the model lets records stand, per application (Base 0.8 C4): the engine's one rule,
    served so clients read it instead of re-deriving it."""

    applications: list[ModelApplicationPlacements]


class ApplicationResponse(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: str
    key: str
    name: str
    description: str | None = None
    icon: str | None = None
    color: str | None = None
    state: str = "active"
    objectTypeKeys: list[str] = Field(default_factory=list)
    defaultView: str
    views: list[Any] = Field(default_factory=list)
    details: list[Any] = Field(default_factory=list)
    settings: dict[str, Any] = Field(default_factory=dict)


class AttributeTypeResponse(BaseModel):
    id: str
    key: str
    name: str
    description: str | None
    valueType: str
    default: Any | None
    features: dict[str, Any]
    validation: dict[str, Any]
    ui: dict[str, Any]


class AttributeBindingResponse(BaseModel):
    id: str
    attributeTypeKey: str
    name: str
    valueType: str
    required: bool
    readOnly: bool
    order: int


class ObjectTypeResponse(BaseModel):
    id: str
    key: str
    name: str
    pluralName: str
    description: str | None
    icon: str | None
    displayAttributeTypeKey: str | None
    attributes: list[AttributeBindingResponse]
    features: dict[str, Any]
    behavior: dict[str, Any]
    validation: dict[str, Any]


class AllowedObjectTypePair(BaseModel):
    id: str
    fromObjectTypeKey: str
    toObjectTypeKey: str
    cardinality: str
    required: bool
    attributeTypeKeys: list[str]
    features: dict[str, Any]


class ObjectTypeRelationResponse(AllowedObjectTypePair):
    relationTypeKey: str


class RelationTypeResponse(BaseModel):
    id: str
    key: str
    name: str
    reverseKey: str
    reverseName: str
    isOriented: bool
    features: dict[str, Any]
    allowedPairs: list[AllowedObjectTypePair]


class MetadataPage[ResponseItem](CollectionPage[ResponseItem]):
    pass


class ModelReleaseSummary(BaseModel):
    id: str
    key: str
    name: str
    version: str
    schemaVersion: str
    modelHash: str
    installedAt: datetime
    active: bool


class ModelReleaseResponse(ModelReleaseSummary):
    model: dict[str, Any] | None = None


class ModelReleasePage(CollectionPage[ModelReleaseSummary]):
    pass


class ModelReleaseActivationResponse(BaseModel):
    """One recorded selection of a release as the active model, read from the audit trail."""

    eventId: str
    kind: Literal["activated", "schemaUpgraded"]
    previousReleaseId: str
    runtimeVersion: int
    occurredAt: datetime


class ModelReleaseActivationPage(CollectionPage[ModelReleaseActivationResponse]):
    pass


class ModelDocumentRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    model: dict[str, Any]


class ModelDiagnosticResponse(BaseModel):
    severity: Literal["error", "warning"]
    code: str
    path: str
    message: str
    count: int | None = None


class ModelValidationResponse(BaseModel):
    valid: bool
    diagnostics: list[ModelDiagnosticResponse]


class ModelChangeResponse(BaseModel):
    kind: Literal["added", "changed", "removed"]
    path: str
    before: Any | None = None
    after: Any | None = None


class ModelCompatibilityResponse(BaseModel):
    classification: Literal["compatible", "migration_required", "invalid"]
    activeReleaseId: str
    diagnostics: list[ModelDiagnosticResponse]


class ModelConsumerContractsResponse(BaseModel):
    """The candidate's consumer API definitions against the active release's (Base 0.9 C1, C-D17).

    ``version_required`` when a definition changes what its consumers read without a higher
    ``contractVersion``: its diagnostics are errors, and activation is refused until it is raised.
    A removed definition is a warning and does not change the classification.
    """

    classification: Literal["compatible", "version_required"]
    activeReleaseId: str
    diagnostics: list[ModelDiagnosticResponse]


class ModelReleaseDiffResponse(BaseModel):
    againstReleaseId: str
    releaseId: str
    changes: list[ModelChangeResponse]
    compatibility: ModelCompatibilityResponse
    consumerContracts: ModelConsumerContractsResponse | None = None


class ModelAdminCapabilities(BaseModel):
    readReleases: bool
    manageDrafts: bool
    install: bool
    activate: bool
    # The deployment setting that enables this group's mutations, so a client can name it.
    setting: Literal["MODEL_ADMIN_MUTATIONS_ENABLED"]


class WorkspaceAdminCapabilities(BaseModel):
    manageWorkspaces: bool
    setting: Literal["WORKSPACE_ADMIN_MUTATIONS_ENABLED"]


class JobLimits(BaseModel):
    """Batch and job limits (D13) and retention (D14). A refusal names the setting it enforces:
    ``BATCH_MAX_ITEMS``, ``BATCH_MAX_BYTES``, ``ATOMIC_JOB_MAX_ITEMS``,
    ``BACKGROUND_JOB_MAX_ITEMS``, ``BATCH_BACKGROUND_MAX_BYTES``, ``IMPORT_MAX_BYTES``. A
    background job commits ``chunkItems`` items at a time (``JOB_CHUNK_ITEMS``)."""

    batchMaxItems: int
    batchMaxBytes: int
    atomicJobMaxItems: int
    backgroundJobMaxItems: int
    backgroundBatchMaxBytes: int
    chunkItems: int
    importMaxBytes: int
    retentionDays: int


class IntegrationJobCapabilities(BaseModel):
    """Bulk writes, imports and exports as jobs (ADR-036). Job reads are always available."""

    createJobs: bool
    runModes: list[Literal["inline", "background"]]
    limits: JobLimits
    setting: Literal["INTEGRATION_JOBS_ENABLED"]


class ChangeFeedCapabilities(BaseModel):
    """The change feed (INTEGRATION_API F). A position older than ``retentionDays``
    (``FEED_RETENTION_DAYS``) is refused as expired, naming a baseline to re-read."""

    retentionDays: int


class ConsumerApiCapabilities(BaseModel):
    """The consumer tier (CONSUMER_API). A batch resolve holds at most ``resolveMaxItems`` items
    (``CONSUMER_RESOLVE_MAX_ITEMS``); more are refused as ``BATCH_TOO_LARGE``."""

    resolveMaxItems: int
    setting: Literal["CONSUMER_RESOLVE_MAX_ITEMS"]


class WebhookDeliveryLimits(BaseModel):
    """How webhooks are delivered (CONSUMER_API "Delivery", C-D103, C-D104, C17): a subscription
    may batch up to ``maxEventsPerBatch`` events in a request, and a request holds at most
    ``maxBytes`` of body (an event alone over it is sent alone); a receiver answers within ``timeoutSeconds``; a failing batch is retried with backoff
    (``retryWaitsSeconds``, then every ``laterWaitSeconds``, each ±20 %) for ``retryHours`` after
    its first failure, then the subscription is suspended ``DELIVERY_FAILED``. Constants, not
    settings."""

    maxEventsPerBatch: int
    maxBytes: int
    timeoutSeconds: float
    retryWaitsSeconds: list[int]
    laterWaitSeconds: int
    retryHours: int


class ConsumerSubscriptionCapabilities(BaseModel):
    """Webhook subscriptions (CONSUMER_API "Subscriptions"): managed through
    ``/consumer-subscriptions`` and delivered when ``manageSubscriptions``
    (``CONSUMER_SUBSCRIPTIONS_ENABLED``)."""

    manageSubscriptions: bool
    # Days the delivery log keeps a request (``CONSUMER_WEBHOOK_LOG_RETENTION_DAYS``, U5a).
    logRetentionDays: int
    delivery: WebhookDeliveryLimits
    setting: Literal["CONSUMER_SUBSCRIPTIONS_ENABLED"]


class CapabilitiesResponse(BaseModel):
    modelAdmin: ModelAdminCapabilities
    workspaceAdmin: WorkspaceAdminCapabilities
    integrationJobs: IntegrationJobCapabilities
    changeFeed: ChangeFeedCapabilities
    consumerApi: ConsumerApiCapabilities
    consumerSubscriptions: ConsumerSubscriptionCapabilities


class ModelDraftCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=300)
    baseReleaseId: UUID4 | None = None
    model: dict[str, Any]


class ModelDraftUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    expectedVersion: int = Field(ge=1)
    name: str | None = Field(default=None, min_length=1, max_length=300)
    model: dict[str, Any] | None = None

    @model_validator(mode="after")
    def require_change(self) -> ModelDraftUpdate:
        if self.name is None and self.model is None:
            raise ValueError("At least one of 'name' or 'model' is required")
        return self


class ModelDraftVersionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    expectedVersion: int = Field(ge=1)


class ModelActivationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    expectedRuntimeVersion: int = Field(ge=1)
    expectedActiveReleaseId: UUID4


class ModelRuntimeStateResponse(BaseModel):
    activeReleaseId: str
    activeModelHash: str
    version: int
    updatedAt: datetime


class ModelDraftResponse(BaseModel):
    id: str
    name: str
    baseReleaseId: str | None
    model: dict[str, Any]
    version: int
    createdAt: datetime
    updatedAt: datetime


class ModelDraftPage(CollectionPage[ModelDraftResponse]):
    pass


class ModelCompilationResponse(BaseModel):
    valid: bool
    model: dict[str, Any] | None = None
    modelHash: str | None = None
    diagnostics: list[ModelDiagnosticResponse]
    compatibility: ModelCompatibilityResponse
    againstReleaseId: str | None = None
    changes: list[ModelChangeResponse] = Field(default_factory=list)
    # Present when the draft is valid.
    consumerContracts: ModelConsumerContractsResponse | None = None
