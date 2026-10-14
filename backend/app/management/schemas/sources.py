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


class SourceBlock(BaseModel):
    """A run of columns holding cells, between empty columns (D68), usable as an import profile
    source's ``headerRow`` and ``block``."""

    index: int
    range: str
    firstColumn: str
    lastColumn: str
    headerRow: int | None
    lastRow: int
    rows: int = Field(description="Rows below the header with a cell in the block")


class SourceSheetResponse(BaseModel):
    index: int
    name: str
    rows: int = Field(description="Rows with a cell")
    headerRow: int | None = Field(description="The first block's header row")
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
    """A column's statistics over the rows below its block's header (D68–D70)."""

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
    """A sheet's profiled columns in column order."""


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


class DryRunResponse(BaseModel):
    """A model draft's dry run (D67): ``checking`` while its job runs, then ``completed`` with its
    summary of the whole file, ``failed`` with the error, or ``cancelled`` when the draft changed
    or a newer dry run started."""

    jobId: str
    state: Literal["checking", "completed", "failed", "cancelled", "expired"]
    draftId: str
    draftVersion: int
    sourceFileId: str
    workspaceKey: str
    summary: DryRunSummary | None
    bindingReport: list[BindingReportSource] | None
    error: ApiErrorBody | None



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
