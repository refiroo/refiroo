from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from .common import CollectionPage


class WorkspaceResponse(BaseModel):
    key: str
    label: str
    status: Literal["active", "retired"]
    version: int
    createdAt: datetime
    updatedAt: datetime


class WorkspaceDetailResponse(WorkspaceResponse):
    """One workspace and whether it may be deleted; computed for single-workspace responses only."""

    deletable: bool
    deleteBlockedBy: Literal["default", "published", "notEmpty"] | None = None


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
