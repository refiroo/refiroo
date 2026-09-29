from typing import Any, Literal

from pydantic import UUID4, BaseModel, ConfigDict, Field, field_validator
from pydantic.json_schema import SkipJsonSchema

from ...models.commands import AttributeInput
from .common import requested_count
from .records import ObjectPathPart

RestructuringOutcomeFilter = Literal[
    "typeChanged", "moved", "withoutPlace", "restored", "needsInput", "refused"
]


class RestructuringMove(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: Literal["move"]
    objectId: UUID4
    parentObjectId: UUID4 | None
    objectTypeKey: str | None = None


class RestructuringChangeType(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: Literal["changeType"]
    objectId: UUID4
    objectTypeKey: str


class RestructuringInsertLevel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: Literal["insertLevel"]
    parentObjectId: UUID4 | None
    childObjectIds: list[UUID4] = Field(min_length=1)
    objectTypeKey: str
    name: str = Field(min_length=1, max_length=500)

    @field_validator("childObjectIds")
    @classmethod
    def distinct_children(cls, value: list[Any]) -> list[Any]:
        if len(value) != len(set(value)):
            raise ValueError("childObjectIds must not repeat")
        return value


class RestructuringRemoveLevel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: Literal["removeLevel"]
    objectId: UUID4


class RestructuringChangeTypeUnder(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: Literal["changeTypeUnder"]
    objectId: UUID4
    fromObjectTypeKey: str
    objectTypeKey: str


class RestructuringTypeChoice(BaseModel):
    """The type a record of ``objectTypeKey`` becomes under a parent of the new type
    ``parentObjectTypeKey`` (null: the top level), where the plan asks."""

    model_config = ConfigDict(extra="forbid")

    objectTypeKey: str
    parentObjectTypeKey: str | None
    newObjectTypeKey: str


class RestructuringMappingAttribute(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    attributeTypeKey: str
    from_: str | None = Field(alias="from")


class RestructuringMappingChoice(BaseModel):
    """Per type pair, the source of attributes of the new type; attributes not listed keep the
    suggestion. ``restore`` takes the values and relationships offered back."""

    model_config = ConfigDict(extra="forbid")

    fromObjectTypeKey: str
    toObjectTypeKey: str
    attributes: list[RestructuringMappingAttribute] = Field(default_factory=list)
    restore: bool = True


class RestructuringChoices(BaseModel):
    model_config = ConfigDict(extra="forbid")

    types: list[RestructuringTypeChoice] = Field(default_factory=list)
    mappings: list[RestructuringMappingChoice] = Field(default_factory=list)


class RestructuringRelationInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    relationTypeKey: str
    direction: Literal["outgoing", "incoming"]
    objectId: UUID4
    attributes: dict[str, Any] = Field(default_factory=dict)


class RestructuringInput(BaseModel):
    """Values and relationships given for one record: a record's ID, or ``new`` for the record
    ``insertLevel`` creates."""

    model_config = ConfigDict(extra="forbid")

    objectId: str = Field(pattern=r"^(new|[0-9a-fA-F-]{36})$")
    attributes: list[AttributeInput] = Field(default_factory=list)
    relations: list[RestructuringRelationInput] = Field(default_factory=list)


class RestructuringRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    operation: (
        RestructuringMove
        | RestructuringChangeType
        | RestructuringInsertLevel
        | RestructuringRemoveLevel
        | RestructuringChangeTypeUnder
    ) = Field(discriminator="kind")
    choices: RestructuringChoices = Field(default_factory=RestructuringChoices)
    inputs: list[RestructuringInput] = Field(default_factory=list)

    @field_validator("inputs")
    @classmethod
    def one_input_per_record(cls, value: list[RestructuringInput]) -> list[RestructuringInput]:
        ids = [item.objectId for item in value]
        if len(ids) != len(set(ids)):
            raise ValueError("inputs must name each record once")
        return value


class RestructuringPreviewRequest(RestructuringRequest):
    """A restructuring to plan, and which page of its records to return."""

    expectedChangeSetVersion: int | None = Field(default=None, ge=1)
    outcome: list[RestructuringOutcomeFilter] = Field(default_factory=list)
    pageSize: int = Field(default=100, ge=1, le=500)
    cursor: str | None = None
    position: int | None = Field(default=None, ge=0)
    from_: Literal["start", "end"] = Field(default="start", alias="from")
    includeTotal: bool = False

    model_config = ConfigDict(extra="forbid", populate_by_name=True)


class RestructuringApplyRequest(RestructuringRequest):
    """The restructuring as previewed, claimed by the change set version and the plan digest."""

    expectedChangeSetVersion: int = Field(ge=1)
    planDigest: str = Field(min_length=1)


class RestructuringSummary(BaseModel):
    recordCount: int
    typeChangeCount: int
    moveCount: int
    createdCount: int
    removedCount: int
    valuesWithoutPlaceCount: int
    relationshipsWithoutPlaceCount: int
    restoredCount: int
    inputsNeededCount: int
    refusalCount: int


class RestructuringRefusal(BaseModel):
    """Why the plan cannot be applied: for the operation, or for one record (``objectId``)."""

    code: str
    message: str
    objectId: str | None = None
    conflictingObjectId: str | None = None
    details: dict[str, Any] | None = None


class RestructuringTypeQuestion(BaseModel):
    objectTypeKey: str
    parentObjectTypeKey: str | None
    options: list[str]
    chosen: str | None
    recordCount: int


class RestructuringPairAttribute(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    attributeTypeKey: str
    from_: str | None = Field(alias="from")
    rule: Literal["sameType", "display", "uniqueRequired", "choice", "none"]
    alternatives: list[str]
    kept: int
    mapped: int
    restored: int
    inputs: int
    empty: int


class RestructuringAttributeCount(BaseModel):
    attributeTypeKey: str
    count: int


class RestructuringRelationCount(BaseModel):
    relationTypeKey: str
    direction: Literal["outgoing", "incoming"]
    outcome: Literal["kept", "withoutPlace"]
    count: int


class RestructuringPair(BaseModel):
    """Every record of one (old type, new type) pair, with the pair's mapping."""

    fromObjectTypeKey: str
    toObjectTypeKey: str
    recordCount: int
    restore: bool
    attributes: list[RestructuringPairAttribute]
    withoutPlace: list[RestructuringAttributeCount]
    relations: list[RestructuringRelationCount]


class RestructuringRecordState(BaseModel):
    objectTypeKey: str | None
    parentObjectId: str | None


class RestructuringRecordAttribute(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    attributeTypeKey: str
    from_: str | None = Field(alias="from")
    outcome: Literal["kept", "mapped", "restored", "input", "default", "empty"]
    value: Any


class RestructuringValue(BaseModel):
    attributeTypeKey: str
    value: Any


class RestructuringRelationship(BaseModel):
    relationId: str
    relationTypeKey: str
    direction: Literal["outgoing", "incoming"]
    objectId: str
    objectTypeKey: str
    name: str


class RestructuringWithoutPlace(BaseModel):
    attributes: list[RestructuringValue]
    relationships: list[RestructuringRelationship]


class RestructuringInputNeeded(BaseModel):
    kind: Literal["attribute", "relation"]
    key: str
    reason: Literal["required", "invalidValue", "atLeastOneOf", "requiredRelation"]


class RestructuringRecord(BaseModel):
    """One record the operation changes. ``before`` is null for the record ``insertLevel``
    creates (whose ``objectId`` is ``new``), ``after`` for the one ``removeLevel`` deletes."""

    objectId: str
    name: str
    path: list[ObjectPathPart]
    before: RestructuringRecordState | None
    after: RestructuringRecordState | None
    outcomes: list[Literal["typeChanged", "moved", "created", "removed"]]
    attributes: list[RestructuringRecordAttribute]
    withoutPlace: RestructuringWithoutPlace
    restoredRelationships: list[RestructuringRelationship]
    inputsNeeded: list[RestructuringInputNeeded]
    refusals: list[RestructuringRefusal]


class RestructuringPreview(BaseModel):
    """A restructuring's plan (Base 0.8 C3, ADR-034) with a page of its records in plan order."""

    changeSetId: str
    changeSetVersion: int
    planDigest: str
    status: Literal["ready", "needsInput", "refused"]
    summary: RestructuringSummary
    typeQuestions: list[RestructuringTypeQuestion]
    pairs: list[RestructuringPair]
    refusals: list[RestructuringRefusal]
    refusalCount: int
    refusalsTruncated: bool
    records: list[RestructuringRecord]
    nextCursor: str | None
    prevCursor: str | None = None
    anchor: str | None = None
    totalCount: int | SkipJsonSchema[None] = requested_count()
    startIndex: int | SkipJsonSchema[None] = requested_count()


class RestructuringResult(BaseModel):
    operationId: str
    changeSetId: str
    changeSetVersion: int
    summary: RestructuringSummary
    createdObjectId: str | None = None
