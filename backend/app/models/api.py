from datetime import datetime
from typing import Any, Literal

from pydantic import UUID4, BaseModel, ConfigDict, Field


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


class AttributeValueWrite(BaseModel):
    model_config = ConfigDict(extra="forbid")

    value: Any
    expectedVersion: int = Field(ge=1)


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
    workspaceKey: str = "default"
    parentObjectId: UUID4 | None = None
    state: str = "active"
    attributes: list[AttributeInput] = Field(default_factory=list)
    initialRelations: list[InitialRelationInput] = Field(default_factory=list)


class ObjectUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(default=None, min_length=1, max_length=500)
    state: str | None = None
    parentObjectId: UUID4 | None = None
    attributes: list[AttributeInput] | None = None
    expectedVersion: int = Field(ge=1)


class ObjectResponse(BaseModel):
    id: str
    workspaceKey: str
    applicationKey: str
    objectTypeKey: str
    parentObjectId: str | None
    state: str
    name: str
    path: list[dict[str, str]]
    attributes: list[AttributeOutput]
    version: int
    createdAt: datetime
    updatedAt: datetime


class ObjectPage(BaseModel):
    items: list[ObjectResponse]
    nextCursor: str | None


class RelationCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    relationTypeKey: str
    fromObjectId: UUID4
    toObjectId: UUID4
    attributes: dict[str, Any] = Field(default_factory=dict)


class RelationUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    attributes: dict[str, Any]
    expectedVersion: int = Field(ge=1)


class RelationResponse(RelationCreate):
    id: str
    version: int
    createdAt: datetime
    updatedAt: datetime


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


class RelationExpansion(BaseModel):
    direction: Literal["outgoing", "incoming"]
    relation: RelationResponse
    object: ObjectResponse
