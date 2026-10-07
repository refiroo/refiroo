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
    A relation item carries ``relationId`` and the relation's ``version`` (none after a delete),
    and ``relationSetVersion`` when it claimed a set; a set replacement carries the anchor's
    ``relationSetVersion`` and ``relationIds``;
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
    objectTypeKey: str | SkipJsonSchema[None] = _by_status()
    version: int | SkipJsonSchema[None] = _by_status()
    previousVersion: int | SkipJsonSchema[None] = _by_status()
    relationId: str | SkipJsonSchema[None] = _by_status()
    relationSetVersion: int | SkipJsonSchema[None] = _by_status()
    relationIds: RelationIds | SkipJsonSchema[None] = _by_status()
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
