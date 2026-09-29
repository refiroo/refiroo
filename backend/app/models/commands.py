"""Write inputs the engine accepts for records, relations, mappings and workspaces.

The management API takes them as request bodies unchanged, and batch items reuse them, so a batch
item and its single-write route validate one shape.
"""

from typing import Any, Literal

from pydantic import UUID4, BaseModel, ConfigDict, Field, field_validator, model_validator


class AttributeInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    attributeTypeKey: str
    value: Any


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


class RelationCreate(BaseModel):
    """A relation to create.

    ``expectedRelationSetVersion`` with ``relationSetDirection`` claims one end's relation set
    (ADR-022): the write succeeds only while that set is still at the version the caller read, such
    as a relation matrix row's ``relationSetVersion``. ``outgoing`` names the from end's set.
    """

    model_config = ConfigDict(extra="forbid")

    relationTypeKey: str
    fromObjectId: UUID4
    toObjectId: UUID4
    attributes: dict[str, Any] = Field(default_factory=dict)
    changeSetId: UUID4 | None = None
    expectedChangeSetVersion: int | None = Field(default=None, ge=1)
    expectedRelationSetVersion: int | None = Field(default=None, ge=0)
    relationSetDirection: Literal["outgoing", "incoming"] | None = None


class RelationUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    attributes: dict[str, Any]
    expectedVersion: int = Field(ge=1)
    changeSetId: UUID4 | None = None
    expectedChangeSetVersion: int | None = Field(default=None, ge=1)


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
