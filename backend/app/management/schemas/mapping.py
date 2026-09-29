from typing import Any, Literal

from pydantic import BaseModel

from .common import CollectionPage


class MappingObjectSummary(BaseModel):
    id: str
    objectTypeKey: str
    name: str
    fields: dict[str, Any]


class MappingTargetSummary(BaseModel):
    relationId: str
    attributes: dict[str, Any]
    object: MappingObjectSummary


class MappingCoverageRow(BaseModel):
    source: MappingObjectSummary
    state: Literal["mapped", "unmapped", "ambiguous"]
    mappingVersion: int
    targetCount: int
    targets: list[MappingTargetSummary]
    targetsNextCursor: str | None


class MappingCoveragePage(CollectionPage[MappingCoverageRow]):
    pass


class MappingTargetPage(CollectionPage[MappingTargetSummary]):
    mappingVersion: int
    targetCount: int


class MappingCandidatePage(CollectionPage[MappingObjectSummary]):
    pass


class MappingListRow(BaseModel):
    relationId: str
    relationTypeKey: str
    direction: Literal["outgoing", "incoming"]
    source: MappingObjectSummary
    target: MappingObjectSummary
    attributes: dict[str, Any]
    mappingVersion: int


class MappingListPage(CollectionPage[MappingListRow]):
    pass


class MappingReplacementResponse(BaseModel):
    sourceObjectId: str
    mappingVersion: int
    state: Literal["mapped", "unmapped"]
    relationId: str | None = None
    changeSetVersion: int | None = None
