from datetime import datetime
from typing import Any, Literal

from pydantic import UUID4, BaseModel, ConfigDict, Field, field_validator, model_validator
from pydantic.json_schema import SkipJsonSchema


def _without_default(schema: dict[str, Any]) -> None:
    schema.pop("default", None)


def _omitted_when_none(value: object) -> bool:
    return value is None


def _requested_count() -> Any:
    """A count present only when asked for: omitted from the body rather than null, and documented
    as an optional integer."""
    return Field(default=None, exclude_if=_omitted_when_none, json_schema_extra=_without_default)


class CollectionPage[Item](BaseModel):
    """One page of a collection (ADR-030): ``items`` first, then the navigation fields.

    ``nextCursor`` and ``prevCursor`` continue after the last and before the first row and are
    null at the end and the start; ``anchor`` reopens this page. ``totalCount`` and ``startIndex``
    (the number of matching rows before the first row) are present only with ``includeTotal=true``
    and omitted otherwise.
    """

    items: list[Item]
    nextCursor: str | None
    prevCursor: str | None = None
    anchor: str | None = None
    totalCount: int | SkipJsonSchema[None] = _requested_count()
    startIndex: int | SkipJsonSchema[None] = _requested_count()


class ApiErrorBody(BaseModel):
    code: str
    message: str
    details: Any | None = None


class ApiErrorResponse(BaseModel):
    error: ApiErrorBody


class AttributeInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    attributeTypeKey: str
    value: Any


class AttributeOutput(BaseModel):
    id: str
    attributeTypeKey: str
    name: str
    valueType: str
    value: Any


class AttributeValueResponse(AttributeOutput):
    objectVersion: int
    changeSetVersion: int | None = None


class AttributeValueWrite(BaseModel):
    model_config = ConfigDict(extra="forbid")

    value: Any
    expectedVersion: int = Field(ge=1)
    changeSetId: UUID4 | None = None
    expectedChangeSetVersion: int | None = Field(default=None, ge=1)


class InitialRelationInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    relationTypeKey: str
    direction: Literal["outgoing", "incoming"]
    otherObjectId: UUID4
    attributes: dict[str, Any] = Field(default_factory=dict)


class ObjectCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID4 | None = None
    applicationKey: str
    objectTypeKey: str
    name: str = Field(min_length=1, max_length=500)
    workspaceKey: str | None = None
    parentObjectId: UUID4 | None = None
    attributes: list[AttributeInput] = Field(default_factory=list)
    initialRelations: list[InitialRelationInput] = Field(default_factory=list)
    changeSetId: UUID4 | None = None
    expectedChangeSetVersion: int | None = Field(default=None, ge=1)


class ObjectUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(default=None, min_length=1, max_length=500)
    parentObjectId: UUID4 | None = None
    attributes: list[AttributeInput] | None = None
    expectedVersion: int = Field(ge=1)
    changeSetId: UUID4 | None = None
    expectedChangeSetVersion: int | None = Field(default=None, ge=1)


class ObjectResponse(BaseModel):
    id: str
    workspaceKey: str
    applicationKey: str
    objectTypeKey: str
    parentObjectId: str | None
    name: str
    path: list[dict[str, str]]
    attributes: list[AttributeOutput]
    version: int
    # Null in change-set and publication contexts, which do not record timestamps.
    createdAt: datetime | None
    updatedAt: datetime | None
    changeSetVersion: int | None = None


class ObjectPage(CollectionPage[ObjectResponse]):
    pass


class ChangeSetCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str | None = Field(default=None, max_length=300)
    source: Literal["currentLive", "publication"] | None = None
    derivedFromPublicationId: UUID4 | None = None
    modelReleaseId: UUID4 | None = None

    @model_validator(mode="after")
    def validate_source(self) -> ChangeSetCreate:
        if self.source == "publication" and self.derivedFromPublicationId is None:
            raise ValueError("derivedFromPublicationId is required when source is publication")
        if self.source == "currentLive" and self.derivedFromPublicationId is not None:
            raise ValueError("derivedFromPublicationId cannot be combined with source currentLive")
        if self.derivedFromPublicationId is not None and self.modelReleaseId is not None:
            raise ValueError(
                "Historical creation retains its source model; change version afterward"
            )
        return self


class ChangeSetModelReleaseUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    modelReleaseId: UUID4
    expectedChangeSetVersion: int = Field(ge=1)


class ChangeSetUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str | None = Field(default=None, max_length=300)
    expectedVersion: int = Field(ge=1)


class ChangeSetResponse(BaseModel):
    id: str
    workspaceKey: str
    name: str | None
    modelReleaseId: str
    modelReleaseKey: str
    modelReleaseVersion: str
    source: Literal["currentLive", "publication", "empty"]
    derivedFromPublicationId: str | None
    version: int
    createdAt: datetime
    updatedAt: datetime


class ChangeSetPage(CollectionPage[ChangeSetResponse]):
    pass


class PublicationResponse(BaseModel):
    id: str
    workspaceKey: str
    modelReleaseId: str
    modelReleaseKey: str
    modelReleaseVersion: str
    publicationNumber: int
    status: Literal["active", "withdrawn"]
    derivedFromPublicationId: str | None
    supersedesPublicationId: str | None
    createdAt: datetime
    publishedAt: datetime
    withdrawnAt: datetime | None


class PublicationPage(CollectionPage[PublicationResponse]):
    pass


class ChangeSetObjectWrite(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: UUID4 | None = None
    applicationKey: str
    objectTypeKey: str
    name: str = Field(min_length=1, max_length=500)
    parentObjectId: UUID4 | None = None
    attributes: dict[str, Any] = Field(default_factory=dict)
    initialRelations: list[InitialRelationInput] = Field(default_factory=list)
    expectedChangeSetVersion: int = Field(ge=1)
    expectedRecordVersion: int | None = Field(default=None, ge=1)


class ChangeSetObjectUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str | None = Field(default=None, min_length=1, max_length=500)
    parentObjectId: UUID4 | None = None
    attributes: dict[str, Any] | None = None
    expectedChangeSetVersion: int = Field(ge=1)
    expectedRecordVersion: int = Field(ge=1)


class ChangeSetRelationWrite(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: UUID4 | None = None
    relationTypeKey: str
    fromObjectId: UUID4
    toObjectId: UUID4
    attributes: dict[str, Any] = Field(default_factory=dict)
    expectedChangeSetVersion: int = Field(ge=1)
    expectedRecordVersion: int | None = Field(default=None, ge=1)


class ChangeSetRelationUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    relationTypeKey: str | None = None
    fromObjectId: UUID4 | None = None
    toObjectId: UUID4 | None = None
    attributes: dict[str, Any] | None = None
    expectedChangeSetVersion: int = Field(ge=1)
    expectedRecordVersion: int = Field(ge=1)


class ChangeSetPublishRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    expectedChangeSetVersion: int = Field(ge=1)
    expectedActivePublicationId: UUID4 | None = None


class ChangeSetValidation(BaseModel):
    valid: bool
    diagnostics: list[dict[str, Any]]


class RelationCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    relationTypeKey: str
    fromObjectId: UUID4
    toObjectId: UUID4
    attributes: dict[str, Any] = Field(default_factory=dict)
    changeSetId: UUID4 | None = None
    expectedChangeSetVersion: int | None = Field(default=None, ge=1)


class RelationUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    attributes: dict[str, Any]
    expectedVersion: int = Field(ge=1)
    changeSetId: UUID4 | None = None
    expectedChangeSetVersion: int | None = Field(default=None, ge=1)


class RelationResponse(RelationCreate):
    id: str
    version: int
    # Null in change-set and publication contexts, which do not record timestamps.
    createdAt: datetime | None
    updatedAt: datetime | None
    changeSetVersion: int | None = None


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


class ModelReleaseDiffResponse(BaseModel):
    againstReleaseId: str
    releaseId: str
    changes: list[ModelChangeResponse]
    compatibility: ModelCompatibilityResponse


class ModelAdminCapabilities(BaseModel):
    readReleases: bool
    manageDrafts: bool
    install: bool
    activate: bool


class WorkspaceAdminCapabilities(BaseModel):
    manageWorkspaces: bool


class CapabilitiesResponse(BaseModel):
    modelAdmin: ModelAdminCapabilities
    workspaceAdmin: WorkspaceAdminCapabilities


class WorkspaceCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    key: str = Field(min_length=1, max_length=160, pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
    label: str = Field(min_length=1, max_length=300)

    @field_validator("key", "label", mode="before")
    @classmethod
    def trim_workspace_create_text(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value


class WorkspaceUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    expectedVersion: int = Field(ge=1)
    label: str | None = Field(default=None, min_length=1, max_length=300)
    status: Literal["active", "retired"] | None = None

    @field_validator("label", mode="before")
    @classmethod
    def trim_workspace_label(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value

    @model_validator(mode="after")
    def require_workspace_change(self) -> WorkspaceUpdate:
        if self.label is None and self.status is None:
            raise ValueError("At least one of 'label' or 'status' is required")
        return self


class WorkspaceResponse(BaseModel):
    key: str
    label: str
    status: Literal["active", "retired"]
    version: int
    createdAt: datetime
    updatedAt: datetime


class WorkspacePage(CollectionPage[WorkspaceResponse]):
    pass


class WorkspaceRuntimeStateUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    defaultWorkspaceKey: str = Field(min_length=1, max_length=160)
    expectedVersion: int = Field(ge=1)


class WorkspaceRuntimeStateResponse(BaseModel):
    defaultWorkspaceKey: str
    version: int
    updatedAt: datetime


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


class RelationExpansion(BaseModel):
    direction: Literal["outgoing", "incoming"]
    relation: RelationResponse
    object: ObjectResponse


class RelationPage(CollectionPage[RelationExpansion]):
    pass


class AuditEventResponse(BaseModel):
    id: str
    aggregateType: str
    aggregateId: str
    action: str
    version: int
    changedFields: list[str]
    attributeTypeKeys: list[str]
    occurredAt: datetime


class AuditEventPage(CollectionPage[AuditEventResponse]):
    pass


class MappingObjectSummary(BaseModel):
    id: str
    objectTypeKey: str
    name: str
    fields: dict[str, Any]


class MappingTargetSummary(BaseModel):
    relationId: str
    attributes: dict[str, Any]
    object: MappingObjectSummary


class MappingCoverageRow(BaseModel):
    source: MappingObjectSummary
    state: Literal["mapped", "unmapped", "ambiguous"]
    mappingVersion: int
    targetCount: int
    targets: list[MappingTargetSummary]
    targetsNextCursor: str | None


class MappingCoveragePage(CollectionPage[MappingCoverageRow]):
    pass


class MappingTargetPage(CollectionPage[MappingTargetSummary]):
    mappingVersion: int
    targetCount: int


class MappingCandidatePage(CollectionPage[MappingObjectSummary]):
    pass


class MappingListRow(BaseModel):
    relationId: str
    relationTypeKey: str
    direction: Literal["outgoing", "incoming"]
    source: MappingObjectSummary
    target: MappingObjectSummary
    attributes: dict[str, Any]
    mappingVersion: int


class MappingListPage(CollectionPage[MappingListRow]):
    pass


class MappingReplacementRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    relationTypeKey: str
    fromObjectTypeKey: str
    toObjectTypeKey: str
    direction: Literal["outgoing", "incoming"]
    sourceObjectId: UUID4
    targetObjectId: UUID4 | None = None
    expectedMappingVersion: int = Field(ge=0)
    attributes: dict[str, Any] | None = None
    changeSetId: UUID4 | None = None
    expectedChangeSetVersion: int | None = Field(default=None, ge=1)


class MappingReplacementResponse(BaseModel):
    sourceObjectId: str
    mappingVersion: int
    state: Literal["mapped", "unmapped"]
    relationId: str | None = None
    changeSetVersion: int | None = None
