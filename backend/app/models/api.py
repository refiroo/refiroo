from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


class ObjectCreate(BaseModel):
    applicationKey: str
    name: str = Field(min_length=1, max_length=500)
    workspaceKey: str = "default"
    parentObjectId: str | None = None
    state: str = "active"
    attributes: dict[str, Any] = Field(default_factory=dict)


class ObjectUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=500)
    state: str | None = None
    parentObjectId: str | None = None
    attributes: dict[str, Any] | None = None
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
    attributes: dict[str, Any]
    version: int
    createdAt: datetime
    updatedAt: datetime


class ObjectPage(BaseModel):
    items: list[ObjectResponse]
    nextCursor: str | None


class RelationCreate(BaseModel):
    relationTypeKey: str
    fromObjectId: str
    toObjectId: str
    attributes: dict[str, Any] = Field(default_factory=dict)


class RelationResponse(RelationCreate):
    id: str
    version: int
    createdAt: datetime
    updatedAt: datetime


class RelationExpansion(BaseModel):
    direction: Literal["outgoing", "incoming"]
    relation: RelationResponse
    object: ObjectResponse
