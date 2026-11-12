"""Source files, their profiles and the dry run (Product 0.10 A3, API.md § Model authoring)."""

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

from .common import ApiErrorBody, CollectionPage
from .jobs import BindingReportSource


class SourceFileOwnerResponse(BaseModel):
    draftId: str | None = None
    profileKey: str | None = None


class SourceFileProfileState(BaseModel):
    """Where the file's profile stands: ``completed`` once stored, otherwise its job's state."""

    state: Literal["queued", "running", "completed", "failed", "cancelled", "expired"]
    jobId: str | None
    error: ApiErrorBody | None = None


class SourceFileResponse(BaseModel):
    """A file a model draft or an import profile owns (D5). ``supersededAt`` is set once a newer
    file of the same owner arrived; the file is deleted ``JOB_RETENTION_DAYS`` later."""

    id: str
    name: str
    format: Literal["xlsx", "csv"]
    bytes: int
    sha256: str
    owner: SourceFileOwnerResponse
    workspaceKey: str | None = Field(
        description="The workspace whose records the profile compared the columns with (D69)"
    )
    csvDelimiter: str | None
    uploadedAt: datetime
    supersededAt: datetime | None
    version: int
    profile: SourceFileProfileState


class SourceFilePage(CollectionPage[SourceFileResponse]):
    """Source files, newest first (ADR-030)."""


class SourceBlockNote(BaseModel):
    """A note under a list's header (0.10 A8a, D119): its row, its text and what it says of the
    list: ``many`` answers, ``one``, ``free`` (a free field, no list), or ``heading``: a second
    header row, answering none of the list's yes/no columns (0.10 A8c, D144)."""

    row: int
    text: str
    meaning: Literal["many", "one", "free", "heading"]


class SourceBlock(BaseModel):
    """A run of columns holding cells, between empty columns (D68), or on a sheet laid out for
    reading one list of such a run, between empty rows (0.10 A8a, D115); usable as an import
    profile source's ``headerRow`` and ``block``."""

    index: int
    range: str
    firstColumn: str
    lastColumn: str
    headerRow: int | None
    lastRow: int
    rows: int = Field(description="Rows below the header with a cell in the block, its note left out")
    titles: list[str] = Field(
        default_factory=list, description="The titles above the list, the outermost first (D115)"
    )
    note: SourceBlockNote | None = None


class SourceSheetResponse(BaseModel):
    index: int
    name: str
    rows: int = Field(description="Rows with a cell")
    headerRow: int | None = Field(description="The first block's header row")
    laidOut: bool = Field(
        default=False,
        description="Laid out for reading: lists side by side or stacked, read list by list (D115)",
    )
    blocks: list[SourceBlock]


class SourceSheetPage(CollectionPage[SourceSheetResponse]):
    """A source file's sheets in workbook order."""


class SourceDelimiter(BaseModel):
    character: str
    cells: int
    share: float


class SourcePlaceholder(BaseModel):
    value: str
    count: int


class SourceOverlap(BaseModel):
    """Another column (``sheet``, ``column``, ``header``), or a field of a type's records in a
    workspace (``workspaceKey``, ``objectTypeKey``, and ``field: name`` or ``attributeTypeKey``),
    holding ``values`` of the column's compared distinct values (``share`` of them)."""

    values: int
    share: float
    sheet: str | None = None
    column: str | None = None
    block: int | None = None
    header: str | None = None
    workspaceKey: str | None = None
    objectTypeKey: str | None = None
    field: Literal["name"] | None = None
    attributeTypeKey: str | None = None


class SourceColumnLimits(BaseModel):
    overlapValues: int = Field(description="Distinct values of the column compared, at most")
    overlapsListed: int
    placeholdersListed: int
    valuesListed: int = Field(default=10, description="Most frequent values listed, at most")


class SourceColumnResponse(BaseModel):
    """A column of a block, with its statistics over the rows below the block's header (D68–D70),
    the block's note left out (0.10 A8a)."""

    sheet: str
    letter: str
    header: str | None
    block: int
    rows: int
    filled: int
    distinct: int
    valueTypes: dict[str, int] = Field(
        description="Cells readable as each value type the attribute registry converts"
    )
    candidateKey: bool = Field(description="Filled on every row, no value twice")
    delimiters: list[SourceDelimiter]
    placeholders: list[SourcePlaceholder]
    values: list[SourcePlaceholder] = Field(
        default_factory=list, description="The most frequent values with their counts (0.10 A6)"
    )
    overlaps: list[SourceOverlap]
    limits: SourceColumnLimits


class SourceColumnPage(CollectionPage[SourceColumnResponse]):
    """A sheet's profiled columns, block by block, each block's in column order."""


class SourceCell(BaseModel):
    """A staged cell: its text as an import matches it, and its value type."""

    text: str
    kind: str = Field(description="text, integer, decimal, boolean, date or dateTime")


class SourceCellRow(BaseModel):
    row: int
    cells: dict[str, SourceCell] = Field(description="The row's filled cells in the range, by column letter")


class SourceCellPage(CollectionPage[SourceCellRow]):
    """The rows of a range holding a cell, in row order (0.10 A8b)."""


class DryRunRejection(BaseModel):
    code: str
    rows: int


class DryRunRecords(BaseModel):
    created: int
    updated: int
    unchanged: int
    deleted: int = Field(default=0, description="Records missing from the file a source deletes")


class DryRunSource(BaseModel):
    """One source of the profile, in load order (``source``, as ``GET …/dry-run/rows`` takes it;
    ``profileSource`` is its position in the profile)."""

    source: int
    profileSource: int
    sheet: str | None
    objectTypeKey: str
    rows: int
    records: DryRunRecords
    values: int
    relationships: int
    relatedRecords: int
    missingRecords: int = Field(
        default=0, description="Records of the type no row names (0.10 A5c, D82)"
    )
    skippedRows: int = Field(
        default=0,
        description="Rows without a key the source skips (rowsWithoutKey: skip, 0.10 A7, D110)",
    )
    rejections: list[DryRunRejection]


class DryRunFigure(BaseModel):
    now: int
    was: int


class DryRunDifference(BaseModel):
    source: int | None
    objectTypeKey: str
    sheet: str | None
    figures: dict[str, DryRunFigure] = Field(
        description="Each figure that changed since the previous dry run, by name: rows, "
        "records.created, values, rejections.<code>, …"
    )


class DryRunRows(BaseModel):
    total: int
    run: int


class DryRunSummary(BaseModel):
    coverage: Literal["complete"]
    rows: DryRunRows
    sources: list[DryRunSource]
    difference: list[DryRunDifference] | None = Field(
        description="What changed since the draft's previous completed dry run of the file; null "
        "for its first"
    )
    previousJobId: str | None
    ranAt: datetime


class ItemsExampleValue(BaseModel):
    attributeTypeKey: str | None
    value: Any


class ItemsExampleLink(BaseModel):
    relationTypeKey: str | None
    direction: Literal["outgoing", "incoming"]
    objectTypeKey: str | None
    name: str | None


class ItemsExampleError(BaseModel):
    code: str | None
    message: str | None


class ItemsExample(BaseModel):
    """One item of a type, with the cells it comes from."""

    index: int
    ref: str | None
    objectTypeKey: str
    action: Literal["created", "updated", "unchanged", "refused"]
    name: str | None
    id: str | None
    values: list[ItemsExampleValue]
    links: list[ItemsExampleLink]
    error: ItemsExampleError | None


class ItemsType(BaseModel):
    """What the items do to the records of one object type: new records, existing records found
    (``matched``, of which ``changed`` were updated), records removed and items refused, the types
    its records are linked to by the load, and up to three example items."""

    objectTypeKey: str
    new: int
    matched: int
    changed: int
    removed: int
    refused: int
    linkedTo: list[str]
    examples: list[ItemsExample]


class ItemsRelationship(BaseModel):
    relationTypeKey: str
    new: int
    matched: int
    refused: int


class ItemsSheet(BaseModel):
    sheet: str
    rows: int


class ItemsPart(BaseModel):
    """Cells of the file, by sheet and columns, that became one type's records (or one relation
    type's relationships), from the items' ``ref``."""

    sheet: str
    firstColumn: str
    lastColumn: str
    firstRow: int
    lastRow: int
    objectTypeKey: str | None
    relationTypeKey: str | None
    items: int


class ItemsParent(BaseModel):
    id: str
    name: str
    objectTypeKey: str


class ItemsFinding(BaseModel):
    """The engine's finding: a name that appears more than once in one type once the load is in,
    with the parent each of its records sits under (``null`` at the root)."""

    kind: Literal["nameTwice"]
    objectTypeKey: str
    name: str
    count: int
    parents: list[ItemsParent | None]


class ItemsRefusal(BaseModel):
    """A refused item: its place in the items, the cells it came from, and why."""

    index: int
    ref: str | None
    key: str | None
    code: str | None
    message: str | None


class ItemsRefusedCode(BaseModel):
    code: str
    items: int


class ItemsFigures(BaseModel):
    recordsNew: int
    recordsMatched: int
    recordsChanged: int
    recordsRemoved: int
    relationshipsNew: int
    parentLinksNew: int = 0
    relationshipsMatched: int
    refused: int
    rowsRead: int


class ItemsDryRunSummary(BaseModel):
    """What a dry run of items found (0.13 AB): per type and relation type what the items would do,
    the engine's findings, the refused items with their refs, and where in the file the items came
    from. Nothing was written."""

    mode: Literal["items"]
    jobId: str
    draftId: str
    draftVersion: int
    workspaceKey: str
    items: int
    figures: ItemsFigures
    types: list[ItemsType]
    relationships: list[ItemsRelationship]
    sheets: list[ItemsSheet]
    parts: list[ItemsPart]
    partsTotal: int
    findings: list[ItemsFinding]
    refused: list[ItemsRefusal]
    refusedByCode: list[ItemsRefusedCode]
    ranAt: datetime


class DryRunResponse(BaseModel):
    """A model draft's dry run (D67): ``checking`` while its job runs, then ``completed`` with its
    summary of the whole file (``summary``) or of the whole set of items (``items``), ``failed``
    with the error, or ``cancelled`` when the draft changed or a newer dry run started."""

    jobId: str
    state: Literal["checking", "completed", "failed", "cancelled", "expired"]
    draftId: str
    draftVersion: int
    sourceFileId: str | None
    workspaceKey: str
    summary: DryRunSummary | None
    bindingReport: list[BindingReportSource] | None
    error: ApiErrorBody | None
    items: ItemsDryRunSummary | None = None


class InferenceDisagreement(BaseModel):
    """A column the draft reads otherwise than a pattern does (D92): its sheet, the source, how
    the draft binds it and how the pattern would, the pattern's finding, and the step that
    decided it."""

    proposalId: str
    pattern: str
    sheet: str | None
    column: str
    source: str
    binding: str
    proposed: str
    found: str
    step: int | None


class ProposedElement(BaseModel):
    """An element still as a proposal step left it: the engine's, until the administrator
    changes it (D92). Elements are named as the history names them, and ``source:<id>``,
    ``column:<source>/<header>``, ``valueMap:<name>`` for the draft's profile."""

    element: str
    proposalId: str | None
    pattern: str | None


class InferenceCounts(BaseModel):
    open: int
    applied: int
    held: int
    rejected: int


class InferenceResponse(BaseModel):
    """A model draft's latest inference (0.10 A6, D87): ``checking`` while its job runs, then
    ``completed`` with its proposals' counts by status, what the workbook disagrees with, its
    warnings, and the elements still as proposed; ``failed`` with the error."""

    jobId: str
    state: Literal["checking", "completed", "failed", "cancelled", "expired"]
    mode: Literal["newApplication", "extend"]
    draftVersion: int
    sourceFileId: str
    counts: InferenceCounts
    disagreements: list[InferenceDisagreement]
    warnings: list[str]
    proposed: list[ProposedElement]
    error: ApiErrorBody | None


class ProposalAlternative(BaseModel):
    label: str
    operations: list[dict[str, Any]]


class ProposalResponse(BaseModel):
    """A proposal (D89, D90): the pattern found, on which sheet and columns, in one sentence, with
    the evidence it rests on; the operations it applies (the kinds of ``POST …/operations``), its
    alternatives as operations to send after it, the proposals it requires, and its status:
    ``open``, ``applied``, ``held`` (the draft decides those columns already) or ``rejected`` (an
    undone proposal, not applied again)."""

    id: str
    position: int
    pattern: str
    sheet: str | None
    columns: list[str]
    summary: str
    evidence: dict[str, Any]
    operations: list[dict[str, Any]]
    alternatives: list[ProposalAlternative]
    requires: list[str]
    status: Literal["open", "applied", "held", "rejected"]


class ProposalPage(CollectionPage[ProposalResponse]):
    """The latest inference's proposals in the order they apply."""


class JoinColumnResponse(BaseModel):
    """The dropped column, read over every row: its sheet, letter and header, its filled rows and
    how many of them differ."""

    sheet: str
    letter: str
    header: str | None
    rows: int
    distinct: int


class JoinCandidate(BaseModel):
    """A column that the dropped column's values may point at, compared over every row."""

    sheet: str
    letter: str
    header: str | None
    rows: int = Field(description="The candidate's filled rows")
    distinct: int = Field(description="Its different values")
    matchedValues: int = Field(description="The dropped column's different values the candidate holds")
    matchedRows: int = Field(description="The dropped column's rows whose value the candidate holds")
    share: float = Field(description="``matchedRows`` over the dropped column's rows")
    unique: bool = Field(description="Every filled cell of the candidate differs: it reads as a list")


class JoinCandidatesResponse(BaseModel):
    """The columns the dropped column joins, best first (0.17 PP-D8). ``tie`` is true when two or more
    match exactly as much: ``best`` is then ``null``, ``tied`` lists them and the client asks."""

    column: JoinColumnResponse
    candidates: list[JoinCandidate]
    best: str | None = Field(description="The letter of the one column that matches most, when no other ties it")
    tie: bool
    tied: list[str]


class ListProposalResponse(BaseModel):
    """A rectangle read as a list (0.10 A8b, D128): a ``listBlock`` proposal built against the
    draft as it is, not stored; its ``operations`` go to ``POST …/operations`` as one step."""

    pattern: str
    sheet: str | None
    columns: list[str]
    summary: str
    evidence: dict[str, Any]
    operations: list[dict[str, Any]]
    alternatives: list[dict[str, Any]]
