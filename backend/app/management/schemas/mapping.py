from typing import Any, Literal

from pydantic import BaseModel
from pydantic.json_schema import SkipJsonSchema

from .common import ChangeOrigin, CollectionPage, optional_origin, requested_count


class MappingObjectSummary(BaseModel):
    id: str
    objectTypeKey: str
    name: str
    fields: dict[str, Any]


class MappingTargetSummary(BaseModel):
    relationId: str
    attributes: dict[str, Any]
    object: MappingObjectSummary
    # Set when the AI proposed this target and nobody has changed it since (0.16 AP2).
    origin: ChangeOrigin | SkipJsonSchema[None] = optional_origin()


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
    """One relationship of the workspace edge list. ``relationVersion`` is the relationship's own
    version, which a change to its ``attributes`` claims; ``mappingVersion`` is its relation set's.
    On a relationships table ``source`` is the ``from`` record and ``target`` the ``to`` record,
    their ``fields`` the view's ``fromColumns`` and ``toColumns``."""

    relationId: str
    relationTypeKey: str
    direction: Literal["outgoing", "incoming"]
    source: MappingObjectSummary
    target: MappingObjectSummary
    attributes: dict[str, Any]
    relationVersion: int
    mappingVersion: int


class MappingListPage(CollectionPage[MappingListRow]):
    """``groupCounts`` is set on a relationships table with ``groupBy``: for each group record the
    page shows, how many rows it holds under the request's filters."""

    groupCounts: dict[str, int] | SkipJsonSchema[None] = requested_count()


class RelationGridColumn(BaseModel):
    """One column group of a relationships grid: a ``to`` record. ``label`` is the view's first
    ``toColumns`` field, ``fields`` all of them, ``linkedCount`` how many of the rows under the
    request's filters (on every page) are related to it."""

    id: str
    objectTypeKey: str
    name: str
    label: str
    fields: dict[str, Any]
    linkedCount: int


class RelationGridRelation(BaseModel):
    """A row's relationship to one column record: its ID and version (what a change to its
    ``attributes`` claims), the values of the attributes the request chose (every stored value without a choice), and whether a change
    set proposes it (it stages that relationship; always false live and in a publication)."""

    relationId: str
    version: int
    attributes: dict[str, Any]
    proposed: bool


class RelationGridRow(BaseModel):
    """One ``from`` record with the relationships it has to the shown column records, by their ID.
    ``mappingVersion`` is the version of its set of this binding, which a link claims."""

    source: MappingObjectSummary
    mappingVersion: int
    relations: dict[str, RelationGridRelation]


class RelationGridPage(CollectionPage[RelationGridRow]):
    """A relationships grid's page of rows with the column groups it shows. ``columnTotal`` is
    how many records match the column filters and the pick, of which at most
    ``COLUMN_CAP`` (50) are in ``columns``; ``rowTotal`` how many rows match the row filters."""

    columns: list[RelationGridColumn]
    columnTotal: int
    rowTotal: int


class MappingReplacementResponse(BaseModel):
    sourceObjectId: str
    mappingVersion: int
    state: Literal["mapped", "unmapped"]
    relationId: str | None = None
    changeSetVersion: int | None = None
