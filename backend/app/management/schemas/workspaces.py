from datetime import datetime
from typing import Literal

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


class WorkspaceResponse(BaseModel):
    key: str
    label: str
    status: Literal["active", "retired"]
    version: int
    createdAt: datetime
    updatedAt: datetime
    model: WorkspaceModelResponse


class WorkspaceDetailResponse(WorkspaceResponse):
    """One workspace and whether it may be deleted; computed for single-workspace responses only."""

    deletable: bool
    deleteBlockedBy: Literal["default", "published", "notEmpty", "subscribed"] | None = None


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
