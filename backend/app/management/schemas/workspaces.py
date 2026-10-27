from datetime import datetime
from typing import Annotated, Literal

from pydantic import UUID4, BaseModel, ConfigDict, Field, model_validator

from .common import CollectionPage


class WorkspaceModelResponse(BaseModel):
    """The release a workspace runs (0.11 M1, ADR-042); ``version`` is the assignment's own,
    raised by every activation into the workspace and claimed by the next."""

    releaseId: str
    releaseKey: str
    releaseName: str
    releaseVersion: str
    schemaVersion: str
    modelHash: str
    version: int
    updatedAt: datetime


class WorkspaceAssignmentResponse(WorkspaceModelResponse):
    workspaceKey: str


class WorkspaceAssignmentPage(CollectionPage[WorkspaceAssignmentResponse]):
    pass


class WorkspaceModelActivation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    releaseId: UUID4
    expectedVersion: int = Field(ge=1)
    expectedReleaseId: UUID4


class MigrationAttributeSource(BaseModel):
    """Where an attribute of the new type takes its values from: an attribute of the old type, or
    none (``from: null``)."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True, serialize_by_alias=True)

    attributeTypeKey: str
    from_: str | None = Field(alias="from")


class MigrationTypeMapping(BaseModel):
    """What a type of the workspace's model became in the target release (0.11 V1, D70): its
    records keep their IDs under the new type. Attributes not named take the values of the same
    attribute of the old type, and a display attribute the old type's display attribute."""

    model_config = ConfigDict(extra="forbid")

    fromObjectTypeKey: str
    toObjectTypeKey: str
    attributes: list[MigrationAttributeSource] = Field(default_factory=list, max_length=500)


class WorkspaceMigrationRequest(BaseModel):
    """A migration of the workspace's data to an installed release (0.11 V1). Naming a change set
    of the workspace (V2, D79–D80) migrates to that change set's release and publishes the change
    set in the same transaction; ``targetReleaseId`` may then be left out, and if sent must be the
    change set's release."""

    model_config = ConfigDict(extra="forbid")

    targetReleaseId: UUID4 | None = None
    expectedVersion: int = Field(ge=1)
    typeMappings: list[MigrationTypeMapping] = Field(default_factory=list, max_length=500)
    changeSetId: str | None = Field(default=None, max_length=36)
    expectedChangeSetVersion: int | None = Field(default=None, ge=1)

    @model_validator(mode="after")
    def _names_what_it_needs(self) -> WorkspaceMigrationRequest:
        if self.changeSetId is None:
            if self.targetReleaseId is None:
                raise ValueError("targetReleaseId is required unless a changeSetId is named")
            if self.expectedChangeSetVersion is not None:
                raise ValueError("expectedChangeSetVersion is sent only with a changeSetId")
        elif self.expectedChangeSetVersion is None:
            raise ValueError("a changeSetId is sent with its expectedChangeSetVersion")
        return self


class ChangeSetLeftBehind(BaseModel):
    """An open change set of the workspace pinned to the release it no longer runs (D26)."""

    id: str
    name: str | None
    version: int


class WorkspaceModelActivationResponse(WorkspaceAssignmentResponse):
    changeSetsLeftBehind: list[ChangeSetLeftBehind]


class WorkspaceAvailable(BaseModel):
    state: Literal["available"] = "available"


class WorkspaceUnavailable(BaseModel):
    """The workspace's model release cannot be served by this version, so its requests answer
    ``503 MODEL_REGISTRY_UNAVAILABLE`` (0.12 UW1)."""

    state: Literal["unavailable"] = "unavailable"
    reason: Literal["schemaLeftWindow", "schemaAfterWindow", "invalidRelease"] = Field(
        description="`schemaLeftWindow`: the release's schema is older than this version reads; "
        "`schemaAfterWindow`: it is of a later version; `invalidRelease`: it is of a readable "
        "schema but does not validate"
    )
    releaseId: str = Field(description="The release the workspace runs")
    schemaVersion: str = Field(description="The release's schema")
    supportedSchemaVersions: list[str] = Field(description="The schemas this version reads")
    raisable: bool = Field(
        description="`POST /model-releases/{releaseId}/raising` can bring the release up to date: "
        "its schema left the window and the raised document is valid and equals no other release"
    )


WorkspaceAvailability = Annotated[
    WorkspaceAvailable | WorkspaceUnavailable, Field(discriminator="state")
]


class WorkspaceResponse(BaseModel):
    key: str
    label: str
    status: Literal["active", "retired"]
    version: int
    createdAt: datetime
    updatedAt: datetime
    model: WorkspaceModelResponse
    availability: WorkspaceAvailability = Field(
        description="Whether this version can serve the workspace's model release"
    )


class WorkspaceDetailResponse(WorkspaceResponse):
    """One workspace and whether it may be deleted; computed for single-workspace responses only."""

    deletable: bool
    deleteBlockedBy: Literal["default", "published", "notEmpty", "subscribed"] | None = None


class WorkspacePage(CollectionPage[WorkspaceResponse]):
    pass


class WorkspaceApplication(BaseModel):
    """An application of the workspace's model, as the home page links it."""

    key: str
    name: str
    icon: str | None
    color: str | None
    defaultView: str


class OwnWorkspaceResponse(BaseModel):
    """A workspace the caller may browse, with what waits for them there (0.12 HM1, D332)."""

    key: str
    label: str
    isDefault: bool
    model: WorkspaceModelResponse
    # Empty when this version cannot serve the workspace's model (0.11 D29).
    applications: list[WorkspaceApplication]
    # The open change sets the caller created here.
    ownChangeSets: int
    # Every open change set here, for a caller holding Publish; null otherwise.
    openChangeSets: int | None


class OwnWorkspacePage(CollectionPage[OwnWorkspaceResponse]):
    pass


class WorkspaceRuntimeStateUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    defaultWorkspaceKey: str = Field(min_length=1, max_length=160)
    expectedVersion: int = Field(ge=1)


class WorkspaceRuntimeStateResponse(BaseModel):
    defaultWorkspaceKey: str
    version: int
    updatedAt: datetime
