from datetime import datetime
from typing import Any, Literal

from pydantic import UUID4, BaseModel, ConfigDict, Field, field_validator, model_validator


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
    workspaceDraftVersion: int | None = None


class AttributeValueWrite(BaseModel):
    model_config = ConfigDict(extra="forbid")

    value: Any
    expectedVersion: int = Field(ge=1)
    workspaceDraftId: UUID4 | None = None
    expectedWorkspaceDraftVersion: int | None = Field(default=None, ge=1)


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
    workspaceDraftId: UUID4 | None = None
    expectedWorkspaceDraftVersion: int | None = Field(default=None, ge=1)


class ObjectUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(default=None, min_length=1, max_length=500)
    parentObjectId: UUID4 | None = None
    attributes: list[AttributeInput] | None = None
    expectedVersion: int = Field(ge=1)
    workspaceDraftId: UUID4 | None = None
    expectedWorkspaceDraftVersion: int | None = Field(default=None, ge=1)


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
    createdAt: datetime
    updatedAt: datetime
    workspaceDraftVersion: int | None = None


class ObjectPage(BaseModel):
    items: list[ObjectResponse]
    nextCursor: str | None


class WorkspaceDraftCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str | None = Field(default=None, max_length=300)
    source: Literal["currentLive", "revision"] | None = None
    derivedFromRevisionId: UUID4 | None = None
    modelReleaseId: UUID4 | None = None

    @model_validator(mode="after")
    def validate_source(self) -> WorkspaceDraftCreate:
        if self.source == "revision" and self.derivedFromRevisionId is None:
            raise ValueError("derivedFromRevisionId is required when source is revision")
        if self.source == "currentLive" and self.derivedFromRevisionId is not None:
            raise ValueError("derivedFromRevisionId cannot be combined with source currentLive")
        if self.derivedFromRevisionId is not None and self.modelReleaseId is not None:
            raise ValueError(
                "Historical creation retains its source model; change version afterward"
            )
        return self


class WorkspaceDraftModelReleaseUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    modelReleaseId: UUID4
    expectedDraftVersion: int = Field(ge=1)


class WorkspaceDraftUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str | None = Field(default=None, max_length=300)
    expectedVersion: int = Field(ge=1)


class WorkspaceDraftResponse(BaseModel):
    id: str
    workspaceKey: str
    name: str | None
    modelReleaseId: str
    modelReleaseKey: str
    modelReleaseVersion: str
    source: Literal["currentLive", "revision", "empty"]
    derivedFromRevisionId: str | None
    version: int
    createdAt: datetime
    updatedAt: datetime


class WorkspaceDraftPage(BaseModel):
    items: list[WorkspaceDraftResponse]
    nextCursor: str | None


class WorkspaceRevisionResponse(BaseModel):
    id: str
    workspaceKey: str
    modelReleaseId: str
    revisionNumber: int
    status: Literal["active", "retired"]
    derivedFromRevisionId: str | None
    supersedesRevisionId: str | None
    createdAt: datetime
    activatedAt: datetime
    retiredAt: datetime | None


class WorkspaceRevisionPage(BaseModel):
    items: list[WorkspaceRevisionResponse]
    nextCursor: str | None


class WorkspaceDraftObjectWrite(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: UUID4 | None = None
    applicationKey: str
    objectTypeKey: str
    name: str = Field(min_length=1, max_length=500)
    parentObjectId: UUID4 | None = None
    attributes: dict[str, Any] = Field(default_factory=dict)
    initialRelations: list[InitialRelationInput] = Field(default_factory=list)
    expectedDraftVersion: int = Field(ge=1)
    expectedRecordVersion: int | None = Field(default=None, ge=1)


class WorkspaceDraftObjectUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str | None = Field(default=None, min_length=1, max_length=500)
    parentObjectId: UUID4 | None = None
    attributes: dict[str, Any] | None = None
    expectedDraftVersion: int = Field(ge=1)
    expectedRecordVersion: int = Field(ge=1)


class WorkspaceDraftRelationWrite(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: UUID4 | None = None
    relationTypeKey: str
    fromObjectId: UUID4
    toObjectId: UUID4
    attributes: dict[str, Any] = Field(default_factory=dict)
    expectedDraftVersion: int = Field(ge=1)
    expectedRecordVersion: int | None = Field(default=None, ge=1)


class WorkspaceDraftRelationUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    relationTypeKey: str | None = None
    fromObjectId: UUID4 | None = None
    toObjectId: UUID4 | None = None
    attributes: dict[str, Any] | None = None
    expectedDraftVersion: int = Field(ge=1)
    expectedRecordVersion: int = Field(ge=1)


class WorkspaceDraftActivation(BaseModel):
    model_config = ConfigDict(extra="forbid")
    expectedDraftVersion: int = Field(ge=1)
    expectedActiveRevisionId: UUID4 | None = None


class WorkspaceRetirement(BaseModel):
    model_config = ConfigDict(extra="forbid")
    expectedActiveRevisionId: UUID4


class WorkspaceDraftValidation(BaseModel):
    valid: bool
    diagnostics: list[dict[str, Any]]


class RelationCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    relationTypeKey: str
    fromObjectId: UUID4
    toObjectId: UUID4
    attributes: dict[str, Any] = Field(default_factory=dict)
    workspaceDraftId: UUID4 | None = None
    expectedWorkspaceDraftVersion: int | None = Field(default=None, ge=1)


class RelationUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    attributes: dict[str, Any]
    expectedVersion: int = Field(ge=1)
    workspaceDraftId: UUID4 | None = None
    expectedWorkspaceDraftVersion: int | None = Field(default=None, ge=1)


class RelationResponse(RelationCreate):
    id: str
    version: int
    createdAt: datetime
    updatedAt: datetime
    workspaceDraftVersion: int | None = None


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


class MetadataPage[ResponseItem](BaseModel):
    items: list[ResponseItem]
    nextCursor: str | None


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


class ModelReleasePage(BaseModel):
    items: list[ModelReleaseSummary]
    nextCursor: str | None


class ModelReleaseActivationResponse(BaseModel):
    """One recorded selection of a release as the active model, read from the audit trail."""

    eventId: str
    kind: Literal["activated", "schemaUpgraded"]
    previousReleaseId: str
    runtimeVersion: int
    occurredAt: datetime


class ModelReleaseActivationPage(BaseModel):
    items: list[ModelReleaseActivationResponse]
    nextCursor: str | None


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


class WorkspacePage(BaseModel):
    items: list[WorkspaceResponse]
    nextCursor: str | None


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


class ModelDraftPage(BaseModel):
    items: list[ModelDraftResponse]
    nextCursor: str | None


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


class RelationPage(BaseModel):
    items: list[RelationExpansion]
    nextCursor: str | None


class AuditEventResponse(BaseModel):
    id: str
    aggregateType: str
    aggregateId: str
    action: str
    version: int
    changedFields: list[str]
    attributeTypeKeys: list[str]
    occurredAt: datetime


class AuditEventPage(BaseModel):
    items: list[AuditEventResponse]
    nextCursor: str | None


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


class MappingCoveragePage(BaseModel):
    items: list[MappingCoverageRow]
    nextCursor: str | None


class MappingTargetPage(BaseModel):
    mappingVersion: int
    targetCount: int
    items: list[MappingTargetSummary]
    nextCursor: str | None


class MappingCandidatePage(BaseModel):
    items: list[MappingObjectSummary]
    nextCursor: str | None


class MappingListRow(BaseModel):
    relationId: str
    relationTypeKey: str
    direction: Literal["outgoing", "incoming"]
    source: MappingObjectSummary
    target: MappingObjectSummary
    attributes: dict[str, Any]
    mappingVersion: int


class MappingListPage(BaseModel):
    items: list[MappingListRow]
    nextCursor: str | None


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
    workspaceDraftId: UUID4 | None = None
    expectedWorkspaceDraftVersion: int | None = Field(default=None, ge=1)


class MappingReplacementResponse(BaseModel):
    sourceObjectId: str
    mappingVersion: int
    state: Literal["mapped", "unmapped"]
    relationId: str | None = None
    workspaceDraftVersion: int | None = None
