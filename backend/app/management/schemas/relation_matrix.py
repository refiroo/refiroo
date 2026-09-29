from typing import Any, Literal

from pydantic import BaseModel

from .common import CollectionPage


class RelationMatrixRecord(BaseModel):
    """A row record with the values of the view's ``rowColumns``."""

    id: str
    objectTypeKey: str
    name: str
    fields: dict[str, Any]


class RelationMatrixColumn(BaseModel):
    """A column record; ``label`` is the value of the view's ``columnLabelField``."""

    id: str
    name: str
    label: Any


class RelationMatrixCellRecord(BaseModel):
    """A related record in a cell, with the relation that joins it to the row.

    ``meetsCondition`` is whether it meets the binding's ``uniqueWhenToAttributeEquals`` condition
    (always true without one); ``fields`` holds the view's ``cellFields``. ``version`` is the
    record's and ``relationVersion`` the relation's, which an edit and an unlink claim.
    """

    id: str
    name: str
    version: int
    relationId: str
    relationVersion: int
    meetsCondition: bool
    fields: dict[str, Any]


class RelationMatrixPublicationReference(BaseModel):
    id: str
    number: int


class RelationMatrixCell(BaseModel):
    """One row's related records under one column record (D11).

    ``recordCount`` and ``matchingCount`` count every record the cell holds and those meeting the
    condition; ``records`` lists at most five of them, those meeting it first. A ``historyOnly``
    cell lists and counts the records of the latest earlier publication that held any, named by
    ``publication``.
    """

    columnId: str
    state: Literal["one", "several", "inactive", "historyOnly", "none"]
    conflict: bool
    recordCount: int
    matchingCount: int
    records: list[RelationMatrixCellRecord]
    publication: RelationMatrixPublicationReference | None = None


class RelationMatrixRow(BaseModel):
    """A row with its cells in column order.

    ``relationSetVersion`` is the row's version of the view's relation set, which a link or unlink
    from the row claims (ADR-022); 0 until the set is first changed, and in a publication.
    """

    row: RelationMatrixRecord
    relationSetVersion: int
    cells: list[RelationMatrixCell]


class RelationMatrixPage(CollectionPage[RelationMatrixRow]):
    """A page of rows, and the columns their cells are in.

    Columns page with their own cursors when the request does not name them (D10).
    """

    columns: list[RelationMatrixColumn]
    columnsNextCursor: str | None = None
    columnsPrevCursor: str | None = None


class RelationMatrixPathPart(BaseModel):
    id: str
    name: str
    objectTypeKey: str


class RelationMatrixContainer(BaseModel):
    """A record a new cell record can go into: the column record or a record under it whose type
    can directly contain the cell type. ``path`` runs from below the column record to this record,
    so it is empty for the column record itself."""

    id: str
    objectTypeKey: str
    name: str
    path: list[RelationMatrixPathPart]


class RelationMatrixContainerPage(CollectionPage[RelationMatrixContainer]):
    """Containers in path order. ``defaultContainerId`` names the column's only container, whatever
    the search, and is null when it has none or several (D13)."""

    defaultContainerId: str | None


class RelationMatrixLinkCandidate(BaseModel):
    """A cell-type record under the column record that the row could be linked to.

    An ineligible candidate is listed, not hidden, with ``reason``: ``alreadyLinked`` (the row
    already relates to it), ``rowCardinality`` or ``candidateCardinality`` (the binding's
    cardinality allows no further relation at that end), or ``scopeTaken`` (the binding's
    uniqueness scope is the column and the row already holds a record in it that meets the
    condition, as this one does).
    """

    id: str
    objectTypeKey: str
    name: str
    version: int
    path: list[RelationMatrixPathPart]
    fields: dict[str, Any]
    eligible: bool
    reason: Literal["alreadyLinked", "rowCardinality", "candidateCardinality", "scopeTaken"] | None


class RelationMatrixLinkCandidatePage(CollectionPage[RelationMatrixLinkCandidate]):
    """Candidates in name order, with the row's ``relationSetVersion`` a link claims."""

    relationSetVersion: int
