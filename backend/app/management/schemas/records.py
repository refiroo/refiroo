from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field
from pydantic.json_schema import SkipJsonSchema

from ...models.commands import RelationCreate
from .common import CollectionPage, omitted_when_none, without_default


class AttributeOutput(BaseModel):
    id: str
    attributeTypeKey: str
    name: str
    valueType: str
    value: Any


class AttributeValueResponse(AttributeOutput):
    objectVersion: int
    changeSetVersion: int | None = None


class ObjectResponse(BaseModel):
    id: str
    workspaceKey: str
    applicationKey: str
    objectTypeKey: str
    parentObjectId: str | None
    name: str
    path: list[dict[str, str]]
    attributes: list[AttributeOutput]
    version: int
    # Null in change-set and publication contexts, which do not record timestamps.
    createdAt: datetime | None
    updatedAt: datetime | None
    changeSetVersion: int | None = None


class ObjectPage(CollectionPage[ObjectResponse]):
    pass


class ObjectPathPart(BaseModel):
    id: str
    name: str
    objectTypeKey: str


class ParentCandidate(BaseModel):
    """A record the model allows as the moved record's parent (Base 0.8 B2).

    ``path`` runs from the root to the candidate itself, so same-named candidates can be told
    apart. An ineligible candidate is listed, not hidden, so pages and totals stay truthful (D14),
    with ``reason``: ``self`` (the record itself, when its type may contain its own), ``descendant``
    (a record under it, which would make a cycle) or ``currentParent`` (where it already is).
    """

    id: str
    objectTypeKey: str
    name: str
    path: list[ObjectPathPart]
    eligible: bool
    reason: Literal["self", "descendant", "currentParent"] | None
    # Base 0.8 C3: with includeTypeChanges=true, the types the record would be under the candidate.
    objectTypeKeys: list[str] | SkipJsonSchema[None] = Field(
        default=None, exclude_if=omitted_when_none, json_schema_extra=without_default
    )


class ParentCandidatePage(CollectionPage[ParentCandidate]):
    """Candidates of every permitted parent type in name order."""


class RelationResponse(RelationCreate):
    id: str
    version: int
    # Null in change-set and publication contexts, which do not record timestamps.
    createdAt: datetime | None
    updatedAt: datetime | None
    changeSetVersion: int | None = None
    # The claimed set's new version, when the write claimed one.
    relationSetVersion: int | None = None


class RelationExpansion(BaseModel):
    direction: Literal["outgoing", "incoming"]
    relation: RelationResponse
    object: ObjectResponse


class RelationPage(CollectionPage[RelationExpansion]):
    pass


class AuditEventResponse(BaseModel):
    id: str
    aggregateType: str
    aggregateId: str
    action: str
    version: int
    changedFields: list[str]
    attributeTypeKeys: list[str]
    occurredAt: datetime


class AuditEventPage(CollectionPage[AuditEventResponse]):
    pass
