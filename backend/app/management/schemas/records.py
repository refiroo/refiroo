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


class RelationSetVersionItem(BaseModel):
    """A relation set the listed record anchors and its version, which a claimed write names
    (``expectedRelationSetVersion`` with ``relationSetDirection``, ADR-022)."""

    relationTypeKey: str
    fromObjectTypeKey: str
    toObjectTypeKey: str
    direction: Literal["outgoing", "incoming"]
    relationSetVersion: int


class RelationPage(CollectionPage[RelationExpansion]):
    """A record's relations, and every relation set it anchors in the listed direction and types,
    an empty one included (0.9 B3). A publication is read-only and names no sets."""

    relationSets: list[RelationSetVersionItem] | SkipJsonSchema[None] = Field(
        default=None, exclude_if=omitted_when_none, json_schema_extra=without_default
    )


class AuditCause(BaseModel):
    """What made a change other than a single write: a job (Base 0.9, INTEGRATION_API P6) or a
    publication, whose publish applied it to live data (D15)."""

    kind: Literal["job", "publication"]
    id: str


class AuditEventResponse(BaseModel):
    id: str
    aggregateType: str
    aggregateId: str
    action: str
    version: int
    changedFields: list[str]
    attributeTypeKeys: list[str]
    occurredAt: datetime
    # Omitted for a single write.
    cause: AuditCause | SkipJsonSchema[None] = Field(
        default=None, exclude_if=omitted_when_none, json_schema_extra=without_default
    )


class AuditEventPage(CollectionPage[AuditEventResponse]):
    pass


def _omitted() -> Any:
    return Field(default=None, exclude_if=omitted_when_none, json_schema_extra=without_default)


class FeedCause(BaseModel):
    """What made the change: a single write (``user``), a job or a publication."""

    kind: Literal["user", "job", "publication"]
    # Omitted for a single write.
    id: str | SkipJsonSchema[None] = _omitted()


class FeedEntry(BaseModel):
    """One change to a workspace's live data, at its position (INTEGRATION_API F2). Names what
    changed, never values; a reader that needs values reads the record."""

    position: int
    eventId: str
    occurredAt: datetime
    kind: Literal["object", "relation", "publication"]
    # object: created, updated, deleted, reclassified; relation: created, updated, deleted;
    # publication: published, withdrawn. Readers ignore actions they do not know.
    action: str
    # The record, relation or publication.
    id: str
    version: int
    # An object entry's type and application, and for ``reclassified`` the type it had.
    objectTypeKey: str | SkipJsonSchema[None] = _omitted()
    applicationKey: str | SkipJsonSchema[None] = _omitted()
    previousObjectTypeKey: str | SkipJsonSchema[None] = _omitted()
    # A relation entry's type and ends, which identify it after a delete.
    relationTypeKey: str | SkipJsonSchema[None] = _omitted()
    fromObjectId: str | SkipJsonSchema[None] = _omitted()
    toObjectId: str | SkipJsonSchema[None] = _omitted()
    changedFields: list[str]
    attributeTypeKeys: list[str]
    cause: FeedCause
    modelReleaseId: str | None


class FeedPage(BaseModel):
    """Entries after ``after`` in position order. Pass ``nextAfter`` as the next ``after``; the
    reader is caught up when ``nextAfter`` equals ``headPosition``."""

    items: list[FeedEntry]
    nextAfter: int
    headPosition: int
    earliestPosition: int
