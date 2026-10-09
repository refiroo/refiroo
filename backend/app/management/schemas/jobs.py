"""Jobs and batches (Base 0.9, ADR-036, INTEGRATION_API P and B)."""

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field
from pydantic.json_schema import SkipJsonSchema

from .common import ApiErrorBody, CollectionPage, omitted_when_none, without_default


def _by_status() -> Any:
    """A field of some outcome statuses only: omitted from the others rather than null."""
    return Field(default=None, exclude_if=omitted_when_none, json_schema_extra=without_default)


class JobProgress(BaseModel):
    total: int | None
    processed: int


class JobCounts(BaseModel):
    """Items by status, and applied items by action."""

    applied: int = 0
    rejected: int = 0
    unprocessed: int = 0
    created: int = 0
    updated: int = 0
    unchanged: int = 0
    deleted: int = 0


class ExportCounts(BaseModel):
    """Records by object type (every exported type, zero included) and relationships by type."""

    records: dict[str, int]
    relations: dict[str, int]


class ExportedContext(BaseModel):
    workspaceKey: str
    changeSetId: str | None
    changeSetVersion: int | None
    publicationId: str | None


class ExportOutput(BaseModel):
    """What a completed export's file holds (0.9 J1, D52): read before downloading it from
    ``GET /jobs/{jobId}/output``. ``feedPosition`` is the position the export equals: the feed head
    it read live data at, a publication's own position, ``null`` for a change set. ``asOfApplied``
    names the types ``asOf`` dated."""

    format: Literal["jsonl", "csv", "xlsx"]
    contentType: str
    counts: ExportCounts
    context: ExportedContext
    feedPosition: int | None
    asOf: str | None
    asOfApplied: list[str]
    modelReleaseId: str
    bytes: int
    sha256: str


class PreviewItems(BaseModel):
    total: int
    previewed: int


class PreviewRows(BaseModel):
    """The file's rows: how many, how many every item of which ran, how many refused."""

    total: int
    previewed: int
    rejected: int


class PreviewCounts(BaseModel):
    created: int
    updated: int
    unchanged: int
    deleted: int
    rejected: int


class DeletionTotals(BaseModel):
    """What delete items remove together (0.9 K2b, D121): their records by type, the
    relationships incident to them, and how many of those reach records that stay."""

    objectCount: int
    objectsByType: dict[str, int]
    relationshipCount: int
    retainedAssociationCount: int


class DeletionImpact(DeletionTotals):
    """One delete item's impact: its record with the records that go with it, and the token that
    confirms exactly this impact (as the single ``DELETE``'s)."""

    deletionPreviewToken: str


class JobPreview(BaseModel):
    """What executing a previewed import (0.9 J3, D80–D83) or batch (0.9 K2, D112) would do.
    ``coverage`` is ``complete`` when every item ran, ``sample`` when only the first
    ``JOB_PREVIEW_MAX_ITEMS`` did (an import's rows were still all bound, so every binding refusal
    is listed). ``result`` is what execution would give under the request's policy: ``rejected``
    for an ``atomic`` job with any refusal. ``rows`` is an import's only. Execution is
    authoritative: data may change before confirmation."""

    coverage: Literal["complete", "sample"]
    items: PreviewItems
    rows: PreviewRows | SkipJsonSchema[None] = Field(
        default=None,
        exclude_if=omitted_when_none,
        json_schema_extra=without_default,
        description="An import's rows of its file; omitted for a batch",
    )
    counts: PreviewCounts
    deletion: DeletionTotals | SkipJsonSchema[None] = Field(
        default=None,
        exclude_if=omitted_when_none,
        json_schema_extra=without_default,
        description="What the batch's delete items would remove together; omitted when none does",
    )
    result: Literal["applied", "partial", "rejected"]
    previewedAt: datetime


class BindingReportColumn(BaseModel):
    """What binding made of one column's cells (D86). A converted column (``field``,
    ``attributeTypeKey``, ``relatedRecord``, ``key``) counts ``converted``, ``valueMapped`` and
    ``refused`` cells; a match column (``parent``, ``relation``, ``relationFlags``) counts
    ``refused`` cells and the values that found one record (``resolved``), none (``notFound``) or
    several (``ambiguous``): a split cell holds several values."""

    column: str
    binding: Literal[
        "field",
        "attributeTypeKey",
        "key",
        "parent",
        "relation",
        "relationFlags",
        "relatedRecord",
    ]
    target: str | None
    cells: int
    empty: int
    converted: int | SkipJsonSchema[None] = _by_status()
    valueMapped: int | SkipJsonSchema[None] = _by_status()
    refused: int
    resolved: int | SkipJsonSchema[None] = _by_status()
    notFound: int | SkipJsonSchema[None] = _by_status()
    ambiguous: int | SkipJsonSchema[None] = _by_status()


class BindingReportSource(BaseModel):
    """One source of the file (a sheet, or the CSV) in load order: its rows, the rows binding or
    execution refused before they ran, and its columns. ``objectTypeKey`` is null for an export's
    table layout, whose sheets may hold several types."""

    sheet: str
    objectTypeKey: str | None
    rows: int
    rejectedRows: int
    columns: list[BindingReportColumn]


class JobNotice(BaseModel):
    """Something about an import's file as a whole, found once it is bound (0.9 J4a): for example
    ``RECORD_IDS_OF_ANOTHER_WORKSPACE`` (``details``: ``workspaceKey``, ``rows``), rows naming their
    records by IDs another workspace's records hold, which cannot load here."""

    code: str
    message: str
    details: dict[str, Any]


class JobResponse(BaseModel):
    """A job. ``result`` says whether every item applied: a ``completed`` job may be ``partial``.

    ``parameters`` holds the kind's choices: ``run`` and ``onExisting`` for a batch; ``context``,
    ``scope``, ``include`` and ``format`` for an export, whose ``result`` stays ``null`` (it has no
    item outcomes) and whose ``output`` describes its file once completed.
    ``changeSetVersion``, for a job in a change set, is the version the job holds: its claim while
    it is queued or running, the version it left once finished. ``leaseOwner`` and
    ``leaseExpiresAt`` name the worker running a background job; ``cancelRequestedAt`` is set by a
    cancel request, which the worker carries out at its next chunk.
    """

    id: str
    kind: Literal["batch", "import", "export"]
    workspaceKey: str
    changeSetId: str | None
    changeSetVersion: int | None
    policy: Literal["atomic", "independent"] | None
    parameters: dict[str, Any]
    modelReleaseId: str
    state: Literal[
        "queued", "running", "awaiting_confirmation", "completed", "failed", "cancelled", "expired"
    ]
    stage: str | None
    progress: JobProgress
    counts: JobCounts
    result: Literal["applied", "partial", "rejected"] | None
    error: ApiErrorBody | None
    createdAt: datetime
    startedAt: datetime | None
    finishedAt: datetime | None
    expiresAt: datetime
    cancelRequestedAt: datetime | None
    leaseOwner: str | None
    leaseExpiresAt: datetime | None
    output: ExportOutput | None = Field(
        default=None, description="A completed export's manifest; null for other jobs and states"
    )
    confirmedAt: datetime | None = Field(
        default=None,
        description="When a previewed import (0.9 J3) or batch (0.9 K2) was confirmed",
    )
    preview: JobPreview | None = Field(
        default=None,
        description="A previewed import's or batch's summary, kept after confirmation; null "
        "otherwise",
    )
    bindingReport: list[BindingReportSource] | None = Field(
        default=None,
        description="An import's binding report per source and column once its file is bound; "
        "null before, for a JSON Lines file and for other jobs",
    )
    notices: list[JobNotice] | None = Field(
        default=None,
        description="An import's notices about its file as a whole once bound (0.9 J4a), empty "
        "when there are none; null before and for other jobs",
    )


class JobPage(CollectionPage[JobResponse]):
    """Jobs, newest first (ADR-030)."""


class RelationIds(BaseModel):
    """What a relation-set replacement did to the set's relations (0.9 B3)."""

    created: list[str]
    kept: list[str]
    removed: list[str]


class JobItemResponse(BaseModel):
    """One item's outcome (INTEGRATION_API P2).

    ``applied`` carries ``action`` and the record's ``id``, ``objectTypeKey`` and ``version``
    (none after a live delete), and ``previousVersion`` when it overwrote without a version claim.
    A delete item carries its ``impact``, or ``unchanged`` with ``deletedWithItem``, the earlier
    item whose impact held its record (0.9 K2b).
    A relation item carries ``relationId`` and the relation's ``version`` (none after a delete),
    and ``relationSetVersion`` when it claimed a set; a set replacement carries the anchor's
    ``relationSetVersion``, the version it found (``previousRelationSetVersion``, which confirming a
    preview carries into the item, 0.9 K3) and ``relationIds``; an ``ensureNoRelation`` that found
    no relation is ``unchanged`` without ``relationId``;
    ``rejected`` carries ``error`` with the single write's code and a JSON ``pointer`` into the
    request in its ``details``; ``unprocessed`` carries ``reason``.
    """

    index: int
    ref: str | None
    status: Literal["applied", "rejected", "unprocessed"]
    action: Literal["created", "updated", "unchanged", "deleted"] | SkipJsonSchema[None] = (
        _by_status()
    )
    id: str | SkipJsonSchema[None] = _by_status()
    # The ID the request gave, when the record written is its counterpart (0.9 J5, D97).
    sourceId: str | SkipJsonSchema[None] = _by_status()
    objectTypeKey: str | SkipJsonSchema[None] = _by_status()
    version: int | SkipJsonSchema[None] = _by_status()
    previousVersion: int | SkipJsonSchema[None] = _by_status()
    relationId: str | SkipJsonSchema[None] = _by_status()
    relationSetVersion: int | SkipJsonSchema[None] = _by_status()
    previousRelationSetVersion: int | SkipJsonSchema[None] = _by_status()
    relationIds: RelationIds | SkipJsonSchema[None] = _by_status()
    impact: DeletionImpact | SkipJsonSchema[None] = _by_status()
    deletedWithItem: int | SkipJsonSchema[None] = _by_status()
    error: ApiErrorBody | SkipJsonSchema[None] = _by_status()
    reason: (
        Literal["BATCH_ROLLED_BACK", "JOB_CANCELLED", "MODEL_RELEASE_CHANGED", "JOB_FAILED"]
        | SkipJsonSchema[None]
    ) = _by_status()


class JobItemPage(CollectionPage[JobItemResponse]):
    """A job's outcomes in item order (ADR-030)."""


class BatchResponse(JobItemPage):
    """A batch run inline: the finished job and the first page of its outcomes; later pages come
    from ``GET /jobs/{jobId}/items``."""

    job: JobResponse


class JobActions(BaseModel):
    """A row's applied items by action."""

    created: int
    updated: int
    unchanged: int
    deleted: int


class JobRowResponse(BaseModel):
    """One row of an import's file (0.9 J3, D84): its ``status`` is its worst item's
    (``rejected``, then ``unprocessed``, then ``applied``), ``actions`` counts its applied items,
    and ``outcomes`` holds its rejected and unprocessed items' outcomes. Every item of the row
    reads at ``GET /jobs/{jobId}/items?ref=``."""

    ref: str
    sheet: str | None
    row: int
    status: Literal["applied", "rejected", "unprocessed"]
    actions: JobActions
    outcomes: list[JobItemResponse]


class JobRowPage(CollectionPage[JobRowResponse]):
    """An import's rows in source then row order (ADR-030)."""
