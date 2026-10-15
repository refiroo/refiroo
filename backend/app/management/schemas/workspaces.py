from datetime import datetime
from typing import Literal

from pydantic import UUID4, BaseModel, ConfigDict, Field

from .common import CollectionPage


class WorkspaceModelResponse(BaseModel):
    """The release a workspace runs (0.11 M1, ADR-042); ``version`` is the assignment's own,
    raised by every activation into the workspace and claimed by the next."""

    releaseId: str
    releaseKey: str
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
