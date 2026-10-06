"""Write inputs the engine accepts for records, relations, mappings and workspaces.

The management API takes them as request bodies unchanged, and batch items reuse them, so a batch
item and its single-write route validate one shape.
"""

from typing import Annotated, Any, Literal

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


# --- batches (Base 0.9 B1, INTEGRATION_API B) ---------------------------------------------------


class RecordKeyValue(BaseModel):
    model_config = ConfigDict(extra="forbid")

    attributeTypeKey: str
    value: Any


class RecordReference(BaseModel):
    """An existing record, by its public ID or by a unique attribute's value on a type (§B2)."""

    model_config = ConfigDict(extra="forbid")

    id: UUID4 | None = None
    objectTypeKey: str | None = None
    key: RecordKeyValue | None = None

    @model_validator(mode="after")
    def one_form(self) -> RecordReference:
        by_id = self.id is not None and self.objectTypeKey is None and self.key is None
        by_key = self.id is None and self.objectTypeKey is not None and self.key is not None
        if not (by_id or by_key):
            raise ValueError("A reference is either {id} or {objectTypeKey, key}")
        return self


class UpsertKey(BaseModel):
    """What an upsert finds its record by: a client-assigned ID or a unique attribute (D2)."""

    model_config = ConfigDict(extra="forbid")

    id: UUID4 | None = None
    attributeTypeKey: str | None = None

    @model_validator(mode="after")
    def one_form(self) -> UpsertKey:
        if (self.id is None) == (self.attributeTypeKey is None):
            raise ValueError("An upsert key is either {id} or {attributeTypeKey}")
        return self


class BatchInitialRelation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    relationTypeKey: str
    direction: Literal["outgoing", "incoming"]
    object: RecordReference
    attributes: dict[str, Any] = Field(default_factory=dict)


class _BatchItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ref: str | None = Field(default=None, min_length=1, max_length=200)


class BatchCreateItem(_BatchItem):
    op: Literal["create"]
    id: UUID4 | None = None
    applicationKey: str
    objectTypeKey: str
    name: str = Field(min_length=1, max_length=500)
    parent: RecordReference | None = None
    attributes: list[AttributeInput] = Field(default_factory=list)
    initialRelations: list[BatchInitialRelation] = Field(default_factory=list)


class BatchUpdateItem(_BatchItem):
    """As a PATCH: only the fields given change; ``parent: null`` moves the record to the root."""

    op: Literal["update"]
    target: RecordReference
    expectedVersion: int = Field(ge=1)
    name: str | None = Field(default=None, min_length=1, max_length=500)
    parent: RecordReference | None = None
    attributes: list[AttributeInput] | None = None


class BatchUpsertItem(_BatchItem):
    """Creates the record ``key`` finds none for, otherwise updates it as an update item would.
    ``initialRelations`` are used only when it creates."""

    op: Literal["upsert"]
    applicationKey: str
    objectTypeKey: str
    key: UpsertKey
    name: str = Field(min_length=1, max_length=500)
    parent: RecordReference | None = None
    attributes: list[AttributeInput] = Field(default_factory=list)
    initialRelations: list[BatchInitialRelation] = Field(default_factory=list)
    expectedVersion: int | None = Field(default=None, ge=1)


class BatchDeleteItem(_BatchItem):
    op: Literal["delete"]
    target: RecordReference
    expectedVersion: int = Field(ge=1)


class _RelationSetClaim(_BatchItem):
    """An optional claim on one end's relation set (ADR-022), as on ``POST /relations``."""

    expectedRelationSetVersion: int | None = Field(default=None, ge=0)
    relationSetDirection: Literal["outgoing", "incoming"] | None = None


class _RelationEnds(BaseModel):
    """``from`` and ``to``, record references (§B2); ``from`` is a Python keyword, so the field is
    ``from_`` and the JSON name ``from``."""

    model_config = ConfigDict(extra="forbid", validate_by_alias=True, serialize_by_alias=True)

    from_: RecordReference = Field(alias="from")
    to: RecordReference


class BatchCreateRelationItem(_RelationEnds, _RelationSetClaim):
    """As ``POST /relations``, the ends named by reference."""

    op: Literal["createRelation"]
    relationTypeKey: str
    attributes: dict[str, Any] = Field(default_factory=dict)


class BatchEnsureRelationItem(_RelationEnds, _BatchItem):
    """Creates the relation unless one of the type already joins the ends; then ``unchanged`` when
    ``attributes`` are omitted or equal, otherwise an update under ``expectedVersion`` (P4)."""

    op: Literal["ensureRelation"]
    relationTypeKey: str
    attributes: dict[str, Any] | None = None
    expectedVersion: int | None = Field(default=None, ge=1)


class BatchUpdateRelationItem(_BatchItem):
    """As ``PATCH /relations/{id}``: the relation's attributes, replaced."""

    op: Literal["updateRelation"]
    id: UUID4
    expectedVersion: int = Field(ge=1)
    attributes: dict[str, Any]


class BatchDeleteRelationItem(_RelationSetClaim):
    """As ``DELETE /relations/{id}``."""

    op: Literal["deleteRelation"]
    id: UUID4
    expectedVersion: int = Field(ge=1)


class RelationSetTarget(BaseModel):
    """A record a set is to hold; omitted ``attributes`` keep a kept relation's values."""

    model_config = ConfigDict(extra="forbid")

    object: RecordReference
    attributes: dict[str, Any] | None = None


class BatchReplaceRelationSetItem(_BatchItem):
    """The anchor's directional set of one binding becomes ``targets`` (possibly empty), under
    ``expectedRelationSetVersion`` or the request's ``onExisting: "overwrite"`` (§B4)."""

    op: Literal["replaceRelationSet"]
    relationTypeKey: str
    fromObjectTypeKey: str
    toObjectTypeKey: str
    direction: Literal["outgoing", "incoming"]
    anchor: RecordReference
    targets: list[RelationSetTarget]
    expectedRelationSetVersion: int | None = Field(default=None, ge=0)


RELATION_ITEMS = (
    BatchCreateRelationItem,
    BatchEnsureRelationItem,
    BatchUpdateRelationItem,
    BatchDeleteRelationItem,
)

BatchItem = Annotated[
    BatchCreateItem
    | BatchUpdateItem
    | BatchUpsertItem
    | BatchDeleteItem
    | BatchCreateRelationItem
    | BatchEnsureRelationItem
    | BatchUpdateRelationItem
    | BatchDeleteRelationItem
    | BatchReplaceRelationSetItem,
    Field(discriminator="op"),
]


class BatchRequest(BaseModel):
    """``POST /batches``: items, a failure policy and one context (INTEGRATION_API B1)."""

    model_config = ConfigDict(extra="forbid")

    workspaceKey: str | None = None
    changeSetId: UUID4 | None = None
    expectedChangeSetVersion: int | None = Field(default=None, ge=1)
    policy: Literal["atomic", "independent"]
    run: Literal["inline", "background"]
    onExisting: Literal["reject", "overwrite"] = "reject"
    items: list[BatchItem] = Field(min_length=1)


# A subscription filter's value: one text or a list of texts, as a batch resolve item holds them.
FilterValue = Annotated[str, Field(min_length=1)] | Annotated[
    list[Annotated[str, Field(min_length=1)]], Field(min_length=1)
]
SubscriptionMode = Literal["perChange", "coalesced"]
SubscriptionPayload = Literal["full", "identity"]
# The longest a coalesced subscription waits for quiet: the maximum wait during continuous change.
MAX_DEBOUNCE_SECONDS = 600


class ConsumerSubscriptionCreate(BaseModel):
    """A webhook subscription (Base 0.9 C11, CONSUMER_API "Subscriptions"). ``workspaceKey`` defaults
    to the default workspace, resolved and stored; ``debounceSeconds`` is for ``coalesced`` only
    (default 60); ``startAfter`` an earlier position to start after (C-D97)."""

    model_config = ConfigDict(extra="forbid")

    consumerApi: str = Field(min_length=1, max_length=160)
    workspaceKey: str | None = Field(default=None, min_length=1, max_length=160)
    events: list[Annotated[str, Field(min_length=1, max_length=160)]] = Field(min_length=1, max_length=100)
    filters: dict[str, FilterValue] = Field(default_factory=dict)
    url: str = Field(min_length=1)
    mode: SubscriptionMode = "perChange"
    debounceSeconds: int | None = Field(default=None, ge=1, le=MAX_DEBOUNCE_SECONDS)
    payload: SubscriptionPayload = "full"
    startAfter: int | None = Field(default=None, ge=0)

    @model_validator(mode="after")
    def debounce_only_when_coalesced(self) -> ConsumerSubscriptionCreate:
        if self.debounceSeconds is not None and self.mode != "coalesced":
            raise ValueError("debounceSeconds applies to mode 'coalesced' only")
        return self


class ConsumerSubscriptionUpdate(BaseModel):
    """An edit of a subscription with the version read; the consumer API and workspace stay."""

    model_config = ConfigDict(extra="forbid")

    expectedVersion: int = Field(ge=1)
    events: list[Annotated[str, Field(min_length=1, max_length=160)]] | None = Field(
        default=None, min_length=1, max_length=100
    )
    filters: dict[str, FilterValue] | None = None
    url: str | None = Field(default=None, min_length=1)
    mode: SubscriptionMode | None = None
    debounceSeconds: int | None = Field(default=None, ge=1, le=MAX_DEBOUNCE_SECONDS)
    payload: SubscriptionPayload | None = None

    @model_validator(mode="after")
    def require_subscription_change(self) -> ConsumerSubscriptionUpdate:
        if not self.model_fields_set - {"expectedVersion"}:
            raise ValueError("At least one field besides 'expectedVersion' is required")
        if self.debounceSeconds is not None and self.mode == "perChange":
            raise ValueError("debounceSeconds applies to mode 'coalesced' only")
        return self


class ConsumerSubscriptionVersion(BaseModel):
    model_config = ConfigDict(extra="forbid")

    expectedVersion: int = Field(ge=1)


class ConsumerSubscriptionResume(BaseModel):
    """A resume; ``acknowledgeLoss`` goes on past events that expired while suspended (C-D93)."""

    model_config = ConfigDict(extra="forbid")

    expectedVersion: int = Field(ge=1)
    acknowledgeLoss: bool = False
