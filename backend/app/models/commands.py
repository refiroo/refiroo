"""Write inputs the engine accepts for records, relations, mappings and workspaces.

The management API takes them as request bodies unchanged, and batch items reuse them, so a batch
item and its single-write route validate one shape.
"""

from typing import Annotated, Any, Literal
from urllib.parse import urlsplit

from pydantic import (
    UUID4,
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    field_validator,
    model_validator,
)


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
    # The release the workspace runs; the default workspace's without it (0.11 D4, D31).
    modelReleaseId: UUID4 | None = None

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


class MappingProposalRequest(BaseModel):
    """Ask the AI provider for targets for the unmapped sources of a mapping view, into a change
    set (0.16 AP2, AP2-D1): ``changeSetId`` with ``expectedChangeSetVersion``, or ``changeSetName``
    for a new change set the request creates; exactly one. ``search`` and ``parentObjectId`` narrow
    the sources as the grid does; ``sendLevel`` a lower level than the instance's ceiling."""

    model_config = ConfigDict(extra="forbid")

    applicationKey: str
    viewKey: str
    search: str | None = Field(default=None, max_length=500)
    parentObjectId: UUID4 | None = None
    changeSetId: UUID4 | None = None
    expectedChangeSetVersion: int | None = Field(default=None, ge=1)
    changeSetName: str | None = Field(default=None, min_length=1, max_length=300)
    sendLevel: Literal["structure", "samples", "values"] | None = None

    @model_validator(mode="after")
    def one_change_set(self) -> MappingProposalRequest:
        if (self.changeSetId is None) == (self.changeSetName is None):
            raise ValueError("Send exactly one of changeSetId and changeSetName")
        if self.changeSetId is not None and self.expectedChangeSetVersion is None:
            raise ValueError("expectedChangeSetVersion is required with changeSetId")
        if self.changeSetName is not None and self.expectedChangeSetVersion is not None:
            raise ValueError("expectedChangeSetVersion belongs with changeSetId, not changeSetName")
        return self


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
    """As ``DELETE /objects/{type}/{id}``: without ``cascade`` a record with dependants is refused
    with its impact; with it, the impact confirmed by ``deletionPreviewToken`` is deleted. In a
    preview the token is not needed: the preview gives it, and confirming carries it (0.9 K2b,
    D120)."""

    op: Literal["delete"]
    target: RecordReference
    expectedVersion: int = Field(ge=1)
    cascade: bool = False
    deletionPreviewToken: str | None = Field(default=None, min_length=1, max_length=2000)


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


class BatchEnsureNoRelationItem(_RelationEnds, _BatchItem):
    """Deletes the relation of the type joining the ends, as ``DELETE /relations/{id}`` does, or is
    ``unchanged`` when none joins them; ``expectedVersion``, when given, claims the relation's
    version (0.9 K3, D129)."""

    op: Literal["ensureNoRelation"]
    relationTypeKey: str
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
    ``expectedRelationSetVersion`` or the request's ``onExisting: "overwrite"`` (§B4). In a preview
    no claim is needed: the outcome names the version found, and confirming carries it (0.9 K3,
    D130)."""

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
    BatchEnsureNoRelationItem,
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
    | BatchEnsureNoRelationItem
    | BatchUpdateRelationItem
    | BatchDeleteRelationItem
    | BatchReplaceRelationSetItem,
    Field(discriminator="op"),
]


class BatchRequest(BaseModel):
    """``POST /batches``: items, a failure policy and one context (INTEGRATION_API B1). ``stage:
    preview`` runs the items without writing and waits for confirmation (0.9 K2, D112); only a
    background batch is previewed (D113)."""

    model_config = ConfigDict(extra="forbid")

    workspaceKey: str | None = None
    changeSetId: UUID4 | None = None
    expectedChangeSetVersion: int | None = Field(default=None, ge=1)
    policy: Literal["atomic", "independent"]
    run: Literal["inline", "background"]
    stage: Literal["execute", "preview"] = "execute"
    onExisting: Literal["reject", "overwrite"] = "reject"
    # Whether IDs of another workspace's records stand for this workspace's own (0.9 J5, D96).
    otherWorkspaceIds: Literal["refuse", "counterparts"] = "refuse"
    items: list[BatchItem] = Field(min_length=1)

    @model_validator(mode="after")
    def _previewed_in_the_background(self) -> BatchRequest:
        if self.stage == "preview" and self.run != "background":
            raise ValueError("a preview runs in the background: send it with run: background")
        return self


# A subscription filter's value: one text or a list of texts, as a batch resolve item holds them.
FilterValue = (
    Annotated[str, Field(min_length=1)]
    | Annotated[list[Annotated[str, Field(min_length=1)]], Field(min_length=1)]
)
SubscriptionPayload = Literal["full", "identity"]
SubscriptionFormat = Literal["rdm", "cloudevents"]
# The most events a webhook request may carry (C-D120), reported in capabilities.
MAX_EVENTS_PER_BATCH = 1000


# What the operator calls a subscription (U5a, C-D115): 1–200 characters once trimmed, not unique.
SubscriptionName = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)
]


class ConsumerSubscriptionCreate(BaseModel):
    """A webhook subscription (Base 0.9 C11, CONSUMER_API "Subscriptions"). ``workspaceKey`` defaults
    to the default workspace, resolved and stored; ``maxEventsPerBatch`` 1 sends one event per
    request (C-D120, C-D122); ``startAfter`` an earlier position to start after (C-D97)."""

    model_config = ConfigDict(extra="forbid")

    name: SubscriptionName
    # ``workspace`` delivers the workspace's change-set events (A2) and names no consumer API.
    source: Literal["consumerApi", "workspace"] = "consumerApi"
    consumerApi: str | None = Field(default=None, min_length=1, max_length=160)
    workspaceKey: str | None = Field(default=None, min_length=1, max_length=160)
    events: list[Annotated[str, Field(min_length=1, max_length=160)]] = Field(
        min_length=1, max_length=100
    )
    filters: dict[str, FilterValue] = Field(default_factory=dict)
    url: str = Field(min_length=1)
    maxEventsPerBatch: int = Field(default=1, ge=1, le=MAX_EVENTS_PER_BATCH)
    payload: SubscriptionPayload = "full"
    format: SubscriptionFormat = "rdm"
    startAfter: int | None = Field(default=None, ge=0)

    @model_validator(mode="after")
    def require_source_fields(self) -> ConsumerSubscriptionCreate:
        if self.source == "consumerApi":
            if self.consumerApi is None:
                raise ValueError("'consumerApi' is required for the source 'consumerApi'")
        else:
            if self.consumerApi is not None:
                raise ValueError("'consumerApi' does not apply to the source 'workspace'")
            if self.filters or "payload" in self.model_fields_set:
                raise ValueError("'filters' and 'payload' do not apply to the source 'workspace'")
        return self


class ConsumerSubscriptionUpdate(BaseModel):
    """An edit of a subscription with the version read; the consumer API and workspace stay."""

    model_config = ConfigDict(extra="forbid")

    expectedVersion: int = Field(ge=1)
    name: SubscriptionName | None = None
    events: list[Annotated[str, Field(min_length=1, max_length=160)]] | None = Field(
        default=None, min_length=1, max_length=100
    )
    filters: dict[str, FilterValue] | None = None
    url: str | None = Field(default=None, min_length=1)
    maxEventsPerBatch: int | None = Field(default=None, ge=1, le=MAX_EVENTS_PER_BATCH)
    payload: SubscriptionPayload | None = None
    format: SubscriptionFormat | None = None

    @model_validator(mode="after")
    def require_subscription_change(self) -> ConsumerSubscriptionUpdate:
        if not self.model_fields_set - {"expectedVersion"}:
            raise ValueError("At least one field besides 'expectedVersion' is required")
        return self


class DeliveryResend(BaseModel):
    """A resend by hand (C-D129): the event of the request to send again."""

    model_config = ConfigDict(extra="forbid")

    eventId: str = Field(min_length=1, max_length=36)


class ConsumerSubscriptionVersion(BaseModel):
    model_config = ConfigDict(extra="forbid")

    expectedVersion: int = Field(ge=1)


class ConsumerSubscriptionResume(BaseModel):
    """A resume; ``reset`` starts after the workspace's feed head instead of the first event not
    acknowledged, skipping what happened meanwhile (C-D93 revised, C-D110)."""

    model_config = ConfigDict(extra="forbid")

    expectedVersion: int = Field(ge=1)
    reset: bool = False


# --- People, clients and signing keys (Product 0.12 I1, API.md "Security administration") ------

Username = Annotated[str, StringConstraints(min_length=1, max_length=150, pattern=r"^\S+$")]
PrincipalName = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)
]
Email = Annotated[
    str, StringConstraints(strip_whitespace=True, max_length=320, pattern=r"^[^@\s]+@[^@\s]+$")
]
# A rotation keeps the previous client secret valid for this many hours (D238's range).
MAX_OVERLAP_HOURS = 168


class UserCreate(BaseModel):
    """A person; they have no password until they set one (I2's link, or ``create_admin``)."""

    model_config = ConfigDict(extra="forbid")

    username: Username
    name: PrincipalName
    email: Email | None = None


class PasswordResetRequest(BaseModel):
    """A one-time password link; with ``send`` it is also mailed to the person's address (SP3)."""

    model_config = ConfigDict(extra="forbid")

    send: bool = False


class UserUpdate(BaseModel):
    """A change to a person with the version read; ``active: false`` deactivates (never deleted,
    D237) and ``active: true`` restores."""

    model_config = ConfigDict(extra="forbid")

    expectedVersion: int = Field(ge=1)
    name: PrincipalName | None = None
    email: Email | None = None
    active: bool | None = None
    localKept: bool | None = Field(
        default=None,
        description="Whether the person keeps signing in with a password while local sign-in is "
        "off (0.12 I3, D365)",
    )


class ClientCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: PrincipalName


class ClientUpdate(BaseModel):
    """A change to a client with the version read; ``active: false`` deactivates it at once."""

    model_config = ConfigDict(extra="forbid")

    expectedVersion: int = Field(ge=1)
    name: PrincipalName | None = None
    active: bool | None = None


class ClientSecretCreate(BaseModel):
    """A new secret, shown once; the client's other secrets stay valid for ``overlapHours`` (0:
    they stop at once)."""

    model_config = ConfigDict(extra="forbid")

    expectedVersion: int = Field(ge=1)
    overlapHours: int = Field(default=24, ge=0, le=MAX_OVERLAP_HOURS)


class ConsumerSubscriptionRotate(BaseModel):
    """A new signing key, shown once; the previous one keeps signing beside it for ``overlapHours``
    (0: it stops with the next delivery), as a client's secret does (0.12 K1, D238)."""

    model_config = ConfigDict(extra="forbid")

    expectedVersion: int = Field(ge=1)
    overlapHours: int = Field(default=24, ge=0, le=MAX_OVERLAP_HOURS)


class PasswordChange(BaseModel):
    """A signed-in person's new password, with the current one (I2, J39.6)."""

    model_config = ConfigDict(extra="forbid")

    currentPassword: str = Field(min_length=1, max_length=1024)
    newPassword: str = Field(min_length=1, max_length=1024)


class SigningKeyRotation(BaseModel):
    """Replace the token signing key; ``immediate`` refuses the old key's tokens at once (J43.2)."""

    model_config = ConfigDict(extra="forbid")

    immediate: bool = False


# --- Authorization (Product 0.12 Z1, ADR-044) -----------------------------------------------------

ActionGroupKey = Annotated[str, StringConstraints(min_length=1, max_length=64)]
ModelKey = Annotated[str, StringConstraints(min_length=1, max_length=160)]
Description = Annotated[str, StringConstraints(strip_whitespace=True, max_length=2000)]


class RoleCreate(BaseModel):
    """A custom role: its action groups, or a predefined or custom role's groups to start from
    (``copiedFrom``) with ``actionGroups`` left out."""

    model_config = ConfigDict(extra="forbid")

    name: PrincipalName
    description: Description | None = None
    actionGroups: list[ActionGroupKey] | None = None
    copiedFrom: str | None = Field(default=None, description="A role's key to copy the groups of")


class RoleUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    expectedVersion: int = Field(ge=1)
    name: PrincipalName | None = None
    description: Description | None = None
    actionGroups: list[ActionGroupKey] | None = None


class GroupSource(BaseModel):
    """A provider group: the provider's key and the groups claim's value it stands for (I3, D364)."""

    model_config = ConfigDict(extra="forbid")

    provider: str = Field(min_length=1, max_length=64)
    claimValue: str = Field(min_length=1, max_length=200)


class GroupCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: PrincipalName
    description: Description | None = None
    source: GroupSource | None = Field(
        default=None,
        description="Made ahead for a provider's group, whose members come from sign-ins (D364)",
    )


class GroupUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    expectedVersion: int = Field(ge=1)
    name: PrincipalName | None = None
    description: Description | None = None


ProviderKey = Annotated[str, Field(pattern=r"^[a-z][a-z0-9-]{0,62}$")]


class SignInProviderCreate(BaseModel):
    """An OpenID Connect provider (0.12 I3, D366); an enabled one is checked when saved."""

    model_config = ConfigDict(extra="forbid")

    key: ProviderKey = Field(description="In the provider's addresses; fixed once saved")
    name: PrincipalName = Field(description='The sign-in button reads "Continue with *name*"')
    issuer: str = Field(min_length=1, max_length=2000)
    clientId: str = Field(min_length=1, max_length=255)
    clientSecret: str = Field(min_length=1, max_length=2000, description="Write-only")
    groupsClaim: str | None = Field(default=None, max_length=200)
    enabled: bool = True
    signOutOfProvider: bool = Field(
        default=False,
        description="Signing out of the engine signs the person out of the provider too; needs "
        "the provider's end_session_endpoint (0.12 I4a, D379)",
    )


class SignInProviderUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    expectedVersion: int = Field(ge=1)
    name: PrincipalName | None = None
    issuer: str | None = Field(default=None, min_length=1, max_length=2000)
    clientId: str | None = Field(default=None, min_length=1, max_length=255)
    clientSecret: str | None = Field(default=None, min_length=1, max_length=2000)
    groupsClaim: str | None = Field(default=None, max_length=200)
    enabled: bool | None = None
    signOutOfProvider: bool | None = None


class IdentityLink(BaseModel):
    """Move the provider identities of the person ``fromUserId`` onto this person (0.12 I4a, D377,
    D378); ``expectedVersion`` is this person's."""

    model_config = ConfigDict(extra="forbid")

    expectedVersion: int = Field(ge=1)
    fromUserId: str = Field(min_length=1, max_length=36)


class LocalSignInUpdate(BaseModel):
    """Local sign-in on or off (D365), and whether a password needs a second factor (0.12 I4b,
    D388)."""

    model_config = ConfigDict(extra="forbid")

    expectedVersion: int = Field(ge=1)
    enabled: bool | None = None
    secondFactorRequired: bool | None = None


class PasskeyRegistrationStart(BaseModel):
    """What the Add a passkey page posts to start the ceremony: the person's password, or a code
    from the authenticator app or a recovery code, as removing a passkey asks (0.12 R, R-F5)."""

    model_config = ConfigDict(extra="forbid")

    proof: str | None = Field(default=None, max_length=200)


class PasskeyRegistration(BaseModel):
    """What the engine's Add a passkey page posts: the ceremony's token, the credential the browser
    created and the name the person gave it (0.12 I4c)."""

    model_config = ConfigDict(extra="forbid")

    ceremony: str = Field(min_length=1, max_length=128)
    credential: dict[str, Any]
    name: str | None = Field(default=None, max_length=100)


class PasskeyAuthenticationStart(BaseModel):
    """What the sign-in page's script posts to start a passkey sign-in: a password step's token, or
    the browser's authorization request for a passkey alone (0.12 I4c)."""

    model_config = ConfigDict(extra="forbid")

    step: str | None = Field(default=None, max_length=128)
    response_type: str | None = Field(default=None, max_length=64)
    client_id: str | None = Field(default=None, max_length=64)
    redirect_uri: str | None = Field(default=None, max_length=2000)
    code_challenge: str | None = Field(default=None, max_length=128)
    code_challenge_method: str | None = Field(default=None, max_length=16)
    state: str | None = Field(default=None, max_length=2000)

    def request_fields(self) -> dict[str, str | None]:
        return self.model_dump(exclude={"step"})


class BrowserRequest(BaseModel):
    """The browser's authorization request, as the application's sign-in screen carries it (0.12 I5)."""

    model_config = ConfigDict(extra="forbid")

    response_type: str | None = Field(default=None, max_length=64)
    client_id: str | None = Field(default=None, max_length=64)
    redirect_uri: str | None = Field(default=None, max_length=2000)
    code_challenge: str | None = Field(default=None, max_length=128)
    code_challenge_method: str | None = Field(default=None, max_length=16)
    state: str | None = Field(default=None, max_length=2000)

    def fields(self) -> dict[str, str | None]:
        return self.model_dump()


class AppPasswordSignIn(BaseModel):
    """A username and password posted by the application's sign-in screen (0.12 I5)."""

    model_config = ConfigDict(extra="forbid")

    request: BrowserRequest
    username: str = Field(default="", max_length=320)
    password: str = Field(default="", max_length=1024)


class AppResetRequest(BaseModel):
    """A forgotten password asked for on the application's sign-in screen: the username or the
    e-mail address (0.12 I6, D420)."""

    model_config = ConfigDict(extra="forbid")

    identifier: str = Field(min_length=1, max_length=320)


class AppPasswordReset(BaseModel):
    """The new password a mailed or made link sets, typed twice (0.12 I6)."""

    model_config = ConfigDict(extra="forbid")

    token: str = Field(max_length=128)
    password: str = Field(default="", max_length=1024)
    repeat: str = Field(default="", max_length=1024)


class AppSecondFactor(BaseModel):
    """The second step of a password sign-in from the application's screen: a code or a recovery
    code, or neither to go on after the recovery codes were shown (0.12 I5)."""

    model_config = ConfigDict(extra="forbid")

    step: str = Field(max_length=128)
    code: str = Field(default="", max_length=64)
    recovery: str = Field(default="", max_length=64)


class PasskeyAuthentication(BaseModel):
    """The credential the browser used, with the ceremony's token (0.12 I4c)."""

    model_config = ConfigDict(extra="forbid")

    ceremony: str = Field(min_length=1, max_length=128)
    credential: dict[str, Any]


class PasskeyRename(BaseModel):
    """A passkey's name, as the person tells their passkeys apart (0.12 I4c, D394)."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=100)


class PasskeyRemoval(BaseModel):
    """What proves it is the person before one of their passkeys is removed: their password, or a
    code from the authenticator app or a recovery code. Omitted only by a person with neither."""

    model_config = ConfigDict(extra="forbid")

    proof: str | None = Field(default=None, max_length=1024)


class SecondFactorCode(BaseModel):
    """A code from the authenticator app, or a recovery code (0.12 I4b)."""

    model_config = ConfigDict(extra="forbid")

    code: str = Field(min_length=1, max_length=40)


class GroupMemberAdd(BaseModel):
    model_config = ConfigDict(extra="forbid")

    userId: str


class GroupMembersAdd(BaseModel):
    """Several people added to a group at once (0.12 SP1b, D401): by their IDs, or by usernames or
    e-mail addresses as pasted, in any case; ``dryRun`` answers what would happen and changes
    nothing."""

    model_config = ConfigDict(extra="forbid")

    userIds: list[str] = Field(default_factory=list, max_length=500)
    identifiers: list[Annotated[str, Field(max_length=320)]] = Field(
        default_factory=list, max_length=500
    )
    dryRun: bool = False


class GroupMembersRemove(BaseModel):
    """Several people taken out of a group at once (0.12 SP1b, D402)."""

    model_config = ConfigDict(extra="forbid")

    userIds: list[str] = Field(min_length=1, max_length=500)


class GrantPrincipal(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: Literal["user", "client", "group"]
    id: str


class GrantScope(BaseModel):
    """The instance (``instance: true``), or one workspace, optionally narrowing writes to
    applications and record types of its model (D228, D243)."""

    model_config = ConfigDict(extra="forbid")

    instance: bool = False
    workspaceKey: str | None = None
    applications: list[ModelKey] = Field(default_factory=list)
    recordTypes: list[ModelKey] = Field(default_factory=list)


class GrantCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    principal: GrantPrincipal
    role: str | None = Field(default=None, description="The role's key; or give consumerApi")
    consumerApi: ModelKey | None = Field(
        default=None,
        description="Instead of a role, read of this consumer API in the scope's workspace (Z3)",
    )
    scope: GrantScope

    @model_validator(mode="after")
    def require_role_or_consumer_api(self) -> GrantCreate:
        if (self.role is None) == (self.consumerApi is None):
            raise ValueError("A grant names either a role or a consumer API")
        return self


# --- Mail (Product 0.12 M1, D419, D422) -------------------------------------------------------


class MailSettingsUpdate(BaseModel):
    """The SMTP connection mail is sent through, replacing what was saved.

    ``expectedVersion`` is the saved version, absent when none is saved yet. ``password`` omitted
    keeps the saved one; a ``username`` of null removes the login and with it the password.
    ``applicationUrl`` null means the first browser origin (``CORS_ORIGINS``).
    """

    model_config = ConfigDict(extra="forbid")

    expectedVersion: int | None = Field(default=None, ge=1)
    host: str = Field(min_length=1, max_length=255, pattern=r"^[^\s/]+$")
    port: int = Field(ge=1, le=65535)
    security: Literal["tls", "starttls", "none"] = Field(
        description="tls: encrypted from the first byte (usually port 465); starttls: upgraded "
        "after greeting (587); none: unencrypted, for a relay on a trusted network, and refused "
        "together with a login"
    )
    username: str | None = Field(default=None, min_length=1, max_length=255)
    password: str | None = Field(
        default=None, min_length=1, max_length=2000, description="Write-only"
    )
    fromAddress: Email
    applicationUrl: str | None = Field(default=None, max_length=2000)

    @field_validator("applicationUrl")
    @classmethod
    def origin_of_the_application(cls, value: str | None) -> str | None:
        if value is None:
            return None
        parts = urlsplit(value.strip())
        if parts.scheme not in ("http", "https") or not parts.hostname:
            raise ValueError(
                "must be an http or https address, such as https://refiroo.example.org"
            )
        if parts.query or parts.fragment or parts.username or parts.password:
            raise ValueError("must not carry a query, a fragment or a login")
        return f"{parts.scheme}://{parts.netloc}{parts.path.rstrip('/')}"


class MailTest(BaseModel):
    """A test message to one address, sent at once through the saved settings."""

    model_config = ConfigDict(extra="forbid")

    to: Email
