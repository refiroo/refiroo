from datetime import datetime
from typing import Annotated, Any, Literal

from pydantic import (
    UUID4,
    BaseModel,
    ConfigDict,
    Field,
    GetJsonSchemaHandler,
    SkipValidation,
    field_validator,
    model_validator,
)
from pydantic.json_schema import JsonSchemaValue
from pydantic_core import CoreSchema

from app.models.schema import EngineModel

from .common import ActorResponse, CollectionPage, PrincipalResponse
from .model_operations import DraftOperation


class _ModelLanguage:
    """The OpenAPI document names ``EngineModel`` and its definitions for a model document
    (0.16 AP11). Only the document: at runtime the field stays an open object, so a wrong model gets
    the compiler's diagnostics with their JSON pointers, not a generic 422."""

    @classmethod
    def __get_pydantic_json_schema__(
        cls, _core: CoreSchema, handler: GetJsonSchemaHandler
    ) -> JsonSchemaValue:
        return handler(EngineModel.__pydantic_core_schema__)


ModelDocument = Annotated[dict[str, Any], _ModelLanguage]


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
    # Run by at least one workspace, and the keys of the workspaces running it (0.11 D24).
    assigned: bool
    workspaces: list[str]
    status: Literal["active", "retired"] = Field(
        description="A retired release is never chosen again; what runs on it keeps running"
    )
    statusVersion: int = Field(
        description="Changes with the status; sent back to change or delete it"
    )
    retiredAt: datetime | None = None
    deletable: bool = Field(description="Nothing refers to the release, so it may be deleted")
    deleteBlockedBy: Literal["running", "history", "importProfile", "mapping"] | None = Field(
        default=None, description="Why it may not be deleted, the first reason that applies"
    )


class ModelReleaseResponse(ModelReleaseSummary):
    model: ModelDocument | None = None


class InstalledImportProfile(BaseModel):
    """The instance import profile an installation saved from the draft's (0.10 A5, D80)."""

    key: str
    version: int


class ModelInstallationResponse(ModelReleaseResponse):
    importProfile: InstalledImportProfile | None = None


class ModelReleasePage(CollectionPage[ModelReleaseSummary]):
    pass


class ModelReleaseActivationResponse(BaseModel):
    """One recorded selection of a release as a workspace's model, read from the audit trail;
    ``workspaceKey`` is absent for one made for the whole instance before 0.11, and
    ``runtimeVersion`` is the assignment's version it gave the workspace."""

    eventId: str
    kind: Literal["activated", "schemaUpgraded"]
    previousReleaseId: str
    workspaceKey: str | None = None
    runtimeVersion: int
    occurredAt: datetime
    # Who made it (0.12 Z4, D313); the engine for an offline schema upgrade, null before Z4.
    actor: ActorResponse | None


class ModelReleaseActivationPage(CollectionPage[ModelReleaseActivationResponse]):
    pass


class ModelDocumentRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    model: ModelDocument


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


class WorkspaceCompatibilityResponse(BaseModel):
    """Activating the candidate into one workspace running its model: that workspace's data
    against its own release (0.11 D25)."""

    workspaceKey: str
    releaseId: str
    classification: Literal["compatible", "migration_required"]
    diagnostics: list[ModelDiagnosticResponse]


class CandidateCompatibilityResponse(ModelCompatibilityResponse):
    """What activating the candidate into the default workspace would do (``activeReleaseId`` is
    the default workspace's release), and ``workspaces``: the same for each workspace running a
    release of the candidate's model, in workspace key order (0.11 D25, D37). A new model's list
    is empty."""

    workspaces: list[WorkspaceCompatibilityResponse]


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
    compatibility: CandidateCompatibilityResponse
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
    background job commits ``chunkItems`` items at a time (``JOB_CHUNK_ITEMS``); a preview, an
    import's or a batch's, runs at most ``previewMaxItems`` items (``JOB_PREVIEW_MAX_ITEMS``) and
    is a sample beyond them."""

    batchMaxItems: int
    batchMaxBytes: int
    atomicJobMaxItems: int
    backgroundJobMaxItems: int
    backgroundBatchMaxBytes: int
    chunkItems: int
    importMaxBytes: int
    previewMaxItems: int
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
    model: ModelDocument


class ModelDraftUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    expectedVersion: int = Field(ge=1)
    name: str | None = Field(default=None, min_length=1, max_length=300)
    model: ModelDocument | None = None

    @model_validator(mode="after")
    def require_change(self) -> ModelDraftUpdate:
        if self.name is None and self.model is None:
            raise ValueError("At least one of 'name' or 'model' is required")
        return self


class ModelDraftVersionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    expectedVersion: int = Field(ge=1)


class ModelDraftResponse(BaseModel):
    id: str
    name: str
    baseReleaseId: str | None
    # The workspace it was opened from, which it applies to (0.16 WM1).
    workspaceKey: str | None = None
    model: ModelDocument
    version: int
    createdAt: datetime
    updatedAt: datetime


class ModelDraftPage(CollectionPage[ModelDraftResponse]):
    pass


class ModelDraftOperationsRequest(BaseModel):
    """One step of a draft's history: operations applied in order, all or none (0.10 A2)."""

    model_config = ConfigDict(extra="forbid")

    expectedVersion: int = Field(ge=1)
    # Described by the kinds registry (0.13 AQ); validated by the engine, which names what it
    # refuses, so the items stay open objects at runtime.
    operations: SkipValidation[list[DraftOperation]] = Field(min_length=1)

    @field_validator("operations", mode="before")
    @classmethod
    def _are_objects(cls, value: Any) -> Any:
        if (
            not isinstance(value, list)
            or not value
            or not all(isinstance(item, dict) for item in value)
        ):
            raise ValueError("operations is a list of one or more objects")
        return value


class ModelDraftUndoRequest(BaseModel):
    """Undo the latest step not yet undone, or ``step``, or the ``steps`` together (D8)."""

    model_config = ConfigDict(extra="forbid")

    expectedVersion: int = Field(ge=1)
    step: int | None = Field(default=None, ge=1)
    steps: list[int] | None = Field(default=None, min_length=1)


class ModelDraftOperationMigration(BaseModel):
    """An element of the base release an operation changes that needs a migration when the draft is
    installed (MG): the element by its keys, whether its key changed, and what holds it."""

    element: dict[str, str]
    keyChange: bool
    impact: dict[str, int | str] = Field(
        description="The records, values and relationships holding the element, as they were when "
        'the operation was applied (a count is exact up to 10,000, then a text such as "10000+")'
    )


class ModelDraftOperationEntry(BaseModel):
    """One operation in a draft's history (D4, ADR-041)."""

    sequence: int
    step: int
    kind: str
    parameters: dict[str, Any]
    inverse: dict[str, Any]
    draftVersion: int
    # Who applied it (0.12 Z4, D315); null for an operation from before Z4.
    author: PrincipalResponse | None
    at: datetime
    undone: bool
    origin: dict[str, Any]
    removed: list[dict[str, str]] = Field(
        default_factory=list,
        description="Views and panels the operation took away because they could stand in no "
        "application after it, each with its kind, applicationKey, view or detail and panel, and "
        "name (a move between applications says what it could not carry)",
    )
    migration: list[ModelDraftOperationMigration] = Field(
        default_factory=list,
        description="The elements of the base release the operation changed that need a migration "
        "when the draft is installed: a change to what stored data holds, or a key change. The "
        "operation is applied all the same; none for an operation that changes nothing of the kind",
    )


class ModelDraftOperationPage(CollectionPage[ModelDraftOperationEntry]):
    pass


class DraftMigrationStep(BaseModel):
    """A step of the draft's history that needs a migration."""

    step: int
    sequence: int
    kind: str
    migration: list[ModelDraftOperationMigration]


class DraftMigrationRow(BaseModel):
    """One type the migration changes: what its records become, where they go and under what."""

    fromObjectTypeKey: str
    toObjectTypeKey: str
    fromName: str
    toName: str
    fromApplicationKeys: list[str]
    toApplicationKeys: list[str]
    toApplicationKey: str | None
    parent: Literal["unchanged", "topLevel", "changed"] = Field(
        description="`topLevel`: the type stands at the top now, so its records leave their parents; "
        "`changed`: it is under other types now, so records the new parents do not hold are "
        "refused in the preview"
    )
    attributes: list[dict[str, str]]
    records: dict[str, int | str]


class DraftMigrationKeyChange(BaseModel):
    """A released element whose key changed, with the consumer APIs of the base release naming the
    old key: integrations naming it must change with it."""

    element: dict[str, str]
    from_: str = Field(alias="from")
    to: str
    consumerApis: list[dict[str, str]]

    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)


class DraftMigrationLanding(BaseModel):
    """The preview's own check of the migration against one workspace's live records."""

    workspaceKey: str
    moved: int
    createdRecords: int
    createdRelationships: int
    losses: list[dict[str, Any]]
    refused: list[dict[str, Any]]


class ModelDraftMigrationResponse(BaseModel):
    """The migration a draft states against its base release (MG), derived from the steps of its
    history that stand now and its model. ``typeMappings``, ``relationTypeMappings``, ``splits`` and
    ``listConversions`` are a workspace migration's request fields; ``rows`` describe them for
    reading. ``landing`` is read with ``workspaceKey``."""

    baseReleaseId: str | None
    draftVersion: int
    required: bool
    steps: list[DraftMigrationStep]
    typeMappings: list[dict[str, Any]]
    relationTypeMappings: list[dict[str, str]]
    splits: list[dict[str, Any]]
    listConversions: list[dict[str, str]]
    rows: list[DraftMigrationRow]
    keyChanges: list[DraftMigrationKeyChange]
    notes: list[dict[str, str]]
    landing: DraftMigrationLanding | None = None


class StepDryRun(BaseModel):
    """The dry run a step queued (0.10 A5, D79); ``GET …/dry-run`` reads it."""

    state: Literal["checking"]
    jobId: str


class ModelDraftStepResponse(BaseModel):
    """The draft after a step: its version, the step's entries, the compiler's diagnostics and the
    draft profile's warnings (0.10 A5), and the dry run the step queued, or ``null``."""

    version: int
    entries: list[ModelDraftOperationEntry]
    valid: bool
    diagnostics: list[ModelDiagnosticResponse]
    dryRun: StepDryRun | None = None


class DraftProfileSourceFile(BaseModel):
    id: str
    name: str
    profile: str


class ModelDraftProfileResponse(BaseModel):
    """``GET /model-drafts/{id}/profile`` (0.10 A5, D75)."""

    version: int
    profile: dict[str, Any] | None
    definition: dict[str, Any] | None
    valid: bool
    diagnostics: list[ModelDiagnosticResponse]
    # A key no stored profile holds, when another model's profile holds the draft profile's key
    # (IMPORT_PROFILE_MODEL_MISMATCH at /profile/key): what `setProfile` should set (0.16).
    freeKey: str | None = None
    sourceFile: DraftProfileSourceFile | None


OutlineMark = Literal["new", "changed", "released"]


class OutlineReleaseIdentity(BaseModel):
    key: str | None = None
    name: str | None = None
    version: str | None = None
    schemaVersion: str | None = None


class OutlineTypeNode(BaseModel):
    objectType: str
    children: list[OutlineTypeNode]


class OutlineNavigationEntry(BaseModel):
    """An entry of a navigation group: a collection (by its type) or a relation matrix (by its view)."""

    collection: str | None = None
    view: str | None = None


class OutlineNavigationGroup(BaseModel):
    key: str
    label: str
    collapsed: bool
    collections: list[str]
    entries: list[OutlineNavigationEntry]
    mark: OutlineMark


class OutlineNavigation(BaseModel):
    groups: list[OutlineNavigationGroup]
    ungrouped: list[str]
    # Collection key to the view its sidebar entry opens on.
    opens: dict[str, str]


class OutlineView(BaseModel):
    key: str
    name: str
    type: str | None = None
    # The collection the view belongs to: its source type.
    collection: str | None = None
    shows: list[str]
    # A relation matrix's configuration, as the model declares it; absent on other kinds.
    matrix: dict[str, Any] | None = None
    # A tree's, a mapping grid's or a relationships table's configuration, as the model declares it (0.13 ED); absent on other kinds.
    config: dict[str, Any] | None = None
    mark: OutlineMark


class OutlineApplication(BaseModel):
    key: str
    name: str
    icon: str | None = None
    color: str | None = None
    defaultView: str | None = None
    objectTypeKeys: list[str]
    tree: list[OutlineTypeNode]
    navigation: OutlineNavigation
    views: list[OutlineView]
    # The types it could stop listing: unused here, listed elsewhere, not in the base release here.
    unlistable: list[str]
    mark: OutlineMark


class OutlineAttribute(BaseModel):
    attributeType: str
    name: str
    valueType: str | None = None
    required: bool
    readOnly: bool
    unique: bool
    sharedWith: list[str]
    # The display hints this type gives the attribute (0.13 ED).
    hidden: bool = False
    helpText: str | None = None
    mark: OutlineMark


class OutlineObjectType(BaseModel):
    key: str
    name: str
    pluralName: str
    icon: str | None = None
    description: str | None = None
    rootCreatable: bool
    parents: list[str]
    # What the editor's Settings show (0.13 ED): the attribute that names a record, its effective
    # period (start and end date attributes), the attributes of which one must be filled and the
    # relation types that place it under a parent.
    displayAttribute: str | None = None
    effectivePeriod: dict[str, str] | None = None
    atLeastOneOf: list[str] = []
    parentRelationTypeKeys: list[str] = []
    attributes: list[OutlineAttribute]
    mark: OutlineMark


class OutlineAttributeType(BaseModel):
    key: str
    name: str
    valueType: str | None = None
    features: dict[str, Any]
    # Bounds of a number type and display hints (0.13 ED).
    minimum: float | int | None = None
    maximum: float | int | None = None
    hidden: bool = False
    helpText: str | None = None
    boundBy: list[str]
    mark: OutlineMark


class OutlineRelationType(BaseModel):
    key: str
    reverseKey: str | None = None
    name: str
    reverseName: str | None = None
    containment: bool
    isOriented: bool = True
    mark: OutlineMark


class OutlineRelation(BaseModel):
    relationType: str
    from_: str = Field(alias="from")
    to: str
    cardinality: str | None = None
    required: bool
    # The attributes a relationship carries (0.13 ED).
    attributeTypeKeys: list[str] = []
    containment: bool
    # The ancestor type under which a source may hold only one target; absent without the rule.
    uniquePer: str | None = None
    # Which records may be chosen at each end (0.9 K7), as the model declares it; absent without.
    candidates: dict[str, Any] | None = None
    mark: OutlineMark

    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)


class OutlineDiagnostic(ModelDiagnosticResponse):
    """A diagnostic with the element its pointer falls in, named as operations name it, or ``null``."""

    element: dict[str, str] | None


class OutlineConsumerExposedType(BaseModel):
    objectType: str
    publicName: str


class OutlineConsumerCounts(BaseModel):
    fields: int
    related: int
    lists: int
    filters: int
    events: int


class OutlineConsumerContract(BaseModel):
    """A definition checked against what the active release's consumers read (C-D17)."""

    classification: Literal["compatible", "version_required"]
    diagnostics: list[OutlineDiagnostic]


class OutlineConsumerApi(BaseModel):
    """A consumer API definition of the draft (0.10 A4c, D55); ``contract`` is ``null`` while the
    draft does not compile."""

    key: str
    name: str
    description: str | None = None
    contractVersion: int | None = None
    exposes: list[OutlineConsumerExposedType]
    counts: OutlineConsumerCounts
    mark: OutlineMark
    contract: OutlineConsumerContract | None


class ModelDraftConsumerApiResponse(BaseModel):
    """A draft's consumer API definition as written and, when the draft compiles, with every default
    written out and its contract against the active release (0.10 A4c, D56)."""

    version: int
    valid: bool
    definition: dict[str, Any]
    expanded: dict[str, Any] | None = None
    contract: OutlineConsumerContract | None = None


class ModelDraftOutlineResponse(BaseModel):
    """A draft's structure as the editor shows it, each element marked against the base release
    (0.10 A4a, D36)."""

    version: int
    baseReleaseId: str | None
    workspaceKey: str | None = None
    release: OutlineReleaseIdentity
    baseRelease: OutlineReleaseIdentity | None
    applications: list[OutlineApplication]
    objectTypes: list[OutlineObjectType]
    attributeTypes: list[OutlineAttributeType]
    relationTypes: list[OutlineRelationType]
    relations: list[OutlineRelation]
    consumerApis: list[OutlineConsumerApi]
    valid: bool
    diagnostics: list[OutlineDiagnostic]


class ModelDraftModelResponse(BaseModel):
    """A draft compiled as ``GET /model`` serves the active model, with its placements (0.10 A4b,
    D43); ``model`` and ``placements`` are absent when the draft does not compile."""

    version: int
    valid: bool
    diagnostics: list[OutlineDiagnostic]
    model: ModelDocument | None = None
    placements: ModelPlacements | None = None


class ModelCompilationResponse(BaseModel):
    valid: bool
    model: ModelDocument | None = None
    modelHash: str | None = None
    diagnostics: list[ModelDiagnosticResponse]
    compatibility: CandidateCompatibilityResponse
    againstReleaseId: str | None = None
    changes: list[ModelChangeResponse] = Field(default_factory=list)
    # Present when the draft is valid.
    consumerContracts: ModelConsumerContractsResponse | None = None


class ModelReleaseStatusRequest(BaseModel):
    """Retire a release or bring it back (0.12 MR1, D457)."""

    model_config = ConfigDict(extra="forbid")

    status: Literal["active", "retired"]
    expectedStatusVersion: int = Field(ge=1)


class ModelReleaseRaisingRequest(BaseModel):
    """Preview (`confirm: false`) or apply (`confirm: true`, with the hash the preview named)
    raising a release to the schema this version reads (0.12 UW1)."""

    model_config = ConfigDict(extra="forbid")

    confirm: bool
    expectedModelHash: str | None = Field(
        default=None,
        min_length=1,
        description="The `modelHash` the preview answered; required with `confirm: true`",
    )

    @model_validator(mode="after")
    def _confirmation_names_the_preview(self) -> ModelReleaseRaisingRequest:
        if self.confirm and self.expectedModelHash is None:
            raise ValueError("expectedModelHash is required with confirm: true")
        return self


class ModelReleaseRaisingWorkspace(BaseModel):
    key: str
    label: str


class ModelReleaseRaisingResponse(BaseModel):
    applied: bool = Field(description="False for a preview, which changes nothing")
    releaseId: str
    releaseKey: str
    releaseVersion: str
    schemaFrom: str
    schemaTo: str
    consumerApisRewritten: int = Field(
        description="Consumer API definitions rewritten from the old internal shape"
    )
    modelHash: str = Field(
        description="The release's hash now: before the raising on a preview, the new one after "
        "applying"
    )
    workspaces: list[ModelReleaseRaisingWorkspace] = Field(
        description="The workspaces running the release, which are served again after applying"
    )
