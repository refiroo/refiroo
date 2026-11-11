from typing import Any, Literal

from pydantic import BaseModel, Field

from .common import CollectionPage, omitted_when_none, without_default


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
    ``relationAttributes`` are the relation's own stored values (the binding's attributes), as
    ``GET /relations/{id}`` answers them.
    """

    id: str
    name: str
    version: int
    relationId: str
    relationVersion: int
    relationAttributes: dict[str, Any]
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
    emptyColumnsHidden: int | None = Field(
        default=None,
        description=(
            "With hideEmptyColumns and no columnIds: how many column records have no related record in "
            "any row the search and parent scope leave, and so are not in the column pages. Absent otherwise."
        ),
    )


class RelationMatrixPathPart(BaseModel):
    id: str
    name: str
    objectTypeKey: str


class RelationMatrixContainer(BaseModel):
    """A record a new cell record can go into: the column record or a record under it whose type
    can directly contain the cell type. ``path`` runs from below the column record to this record,
    so it is empty for the column record itself. ``cellCount`` is how many cell records stand
    directly under it: a container holding none is not used by the view yet."""

    id: str
    objectTypeKey: str
    name: str
    path: list[RelationMatrixPathPart]
    cellCount: int = 0
    applicationKey: str | None = Field(
        default=None,
        exclude_if=omitted_when_none,
        json_schema_extra=without_default,
        description=(
            "The application the container belongs to; a cell record created in it is created in the"
            " same application (a record stands in its parent's)"
        ),
    )


class RelationMatrixDerivedPlace(BaseModel):
    """The record the binding's candidate criteria fix as the place a new cell record goes (PP-D24):
    equalities on one ancestor type's fields that the model lets sit directly under the column
    record and directly hold the cell type. ``willBeCreated`` is true when no container of the
    column meets the criteria yet: creating a cell then creates this record first, in the same
    change."""

    objectTypeKey: str
    name: str
    attributes: dict[str, Any]
    willBeCreated: bool
    applicationKey: str | None = Field(
        default=None,
        exclude_if=omitted_when_none,
        json_schema_extra=without_default,
        description=(
            "With ``willBeCreated``: the application the new container is created in, its parent's"
            " (the column record's): a record stands in the application of its parent"
        ),
    )
    proposed: bool = Field(
        default=False,
        description=(
            "True when the model's rules fix no place and no container of the column holds cells of"
            " the view: the place is then proposed from the data (PP-D28), a new container of the"
            " type the view's other columns use, named as most of them are. The caller may change"
            " the name; creating the cell creates it first, in the same change"
        ),
    )


class RelationMatrixContainerPage(CollectionPage[RelationMatrixContainer]):
    """Containers in path order, only those a new cell record meets the binding's candidate
    criteria under, those holding cells of the view first. ``defaultContainerId`` names where the
    column's new cells go: the one container the criteria fix, else the container already holding
    cells of the view (the one holding most; none on a tie), whatever the search; a container
    holding no cells is never the default, even as the only one (PP-D24). ``derivedPlace`` is the place the criteria
    fix, null where they fix none: with none offered and no place derived, the cell cannot be
    created here."""

    defaultContainerId: str | None
    derivedPlace: RelationMatrixDerivedPlace | None = None


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
