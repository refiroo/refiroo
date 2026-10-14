"""Import profiles (Base 0.9 J2, INTEGRATION_API §J3)."""

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field
from pydantic.json_schema import SkipJsonSchema

from ...models.imports import CsvOptions, Source
from .common import ApiErrorBody, CollectionPage, omitted_when_none, without_default
from .jobs import BindingReportSource
from .sources import DryRunSummary


class ImportProfileProblem(BaseModel):
    """Something in the profile the model release does not resolve, at its JSON pointer."""

    path: str
    code: str
    message: str


class ImportLoadCounts(BaseModel):
    created: int
    updated: int
    deleted: int
    rejected: int


class ImportProfileLastLoad(BaseModel):
    """The latest import naming the profile (0.10 A5c) and what became of what it loaded:
    ``live`` (loaded into live data), ``inChangeSet`` (its change set still holds it),
    ``published`` (``publicationId``) or ``discarded`` (its change set is gone and no publication
    of it is on record); null until the job completes. A job past its retention is not found."""

    jobId: str
    state: str
    fileName: str | None
    sourceFileId: str | None = Field(description="The stored source file it read; null for a file sent with the import")
    workspaceKey: str
    changeSetId: str | None
    createdAt: datetime
    finishedAt: datetime | None
    counts: ImportLoadCounts
    outcome: Literal["live", "inChangeSet", "published", "discarded"] | None
    publicationId: str | None


class ImportProfileResponse(BaseModel):
    """A stored profile. ``checkedAgainst`` is the release it was saved against; ``valid`` and
    ``problems`` say how it reads under the active release, so a profile a later release broke
    shows what to fix before an import is refused for it."""

    key: str
    name: str
    version: int
    checkedAgainst: str
    lastLoad: ImportProfileLastLoad | None = None
    valid: bool
    problems: list[ImportProfileProblem]
    createdAt: datetime
    updatedAt: datetime
    csv: CsvOptions | SkipJsonSchema[None] = Field(
        default=None, exclude_if=omitted_when_none, json_schema_extra=without_default
    )
    sources: list[Source]
    valueMaps: dict[str, dict[str, Any]]


class ImportProfilePage(CollectionPage[ImportProfileResponse]):
    """Import profiles in key order."""


# --- a profile's check of its next file (Product 0.10 A5c, D83) ---------------------------------


class CheckNewColumn(BaseModel):
    column: str
    letter: str


class CheckMissingColumn(BaseModel):
    column: str


class CheckRenamedColumn(BaseModel):
    """A column the profile names that the file holds under another header at the same position,
    sharing ``shared`` of the larger distinct value count (at least half, D83)."""

    from_: str = Field(alias="from", serialization_alias="from")
    to: str
    letter: str
    shared: float

    model_config = {"populate_by_name": True}


class CheckColumns(BaseModel):
    new: list[CheckNewColumn] = Field(
        description="Headers in neither the profile nor the file it read before"
    )
    missing: list[CheckMissingColumn] = Field(
        description="Columns the profile names that the file lacks; the check reads the file "
        "without them, a load is refused IMPORT_FILE_MISMATCH"
    )
    renamed: list[CheckRenamedColumn]


class CheckSource(BaseModel):
    """One source of the profile (``profileSource``, its position in the profile). ``source`` is
    its position in the load order of the check's run, as ``…/check/rows`` and the findings take
    it, or null when the check did not read it: its sheet is gone (``sheetFound``), no column it
    loads is left, or the profile has problems."""

    profileSource: int
    source: int | None
    sheet: str | None
    objectTypeKey: str
    missing: Literal["report", "delete"]
    sheetFound: bool
    columns: CheckColumns | None
    newValues: int = Field(description="Values of its match columns naming no record")
    drift: int = Field(description="Rows whose key finds a record of another name")
    missingRecords: int = Field(description="Records of its type no row names (D82)")


class ProfileCheckResponse(BaseModel):
    """The check of an import profile's latest file (D83): ``checking`` while its job runs, then
    ``completed`` with the report, ``failed`` with the error, or ``cancelled`` when a newer check
    started. ``valid`` and ``problems`` are the profile against ``releaseId``, the active release
    the check ran under; ``dryRun`` is what the load would do, null when the profile has problems
    or nothing of the file could be read through it."""

    jobId: str
    state: Literal["checking", "completed", "failed", "cancelled", "expired"]
    profileKey: str
    profileVersion: int | None
    sourceFileId: str
    previousSourceFileId: str | None
    workspaceKey: str
    releaseId: str | None
    valid: bool | None
    problems: list[ImportProfileProblem]
    sources: list[CheckSource]
    dryRun: DryRunSummary | None
    bindingReport: list[BindingReportSource] | None
    error: ApiErrorBody | None


class CheckNewValue(BaseModel):
    """A value of a match column naming no record of the context: one the load creates
    (``created``, the column's ``missing: create``) or refuses ``REFERENCE_NOT_FOUND``."""

    source: int
    column: str
    value: Any
    created: bool
    cells: int


class CheckNewValuePage(CollectionPage[CheckNewValue]):
    """New values in source, column and value order."""


class CheckDrift(BaseModel):
    """A row whose key finds a record named otherwise: ``name`` the row's, ``recordName`` the
    record's."""

    source: int
    row: int
    recordId: str
    key: Any
    name: str
    recordName: str | None


class CheckDriftPage(CollectionPage[CheckDrift]):
    """Drifting names in source and row order."""


class CheckMissingRecord(BaseModel):
    """A record of the source's type with the key filled that no row names (D82)."""

    source: int
    recordId: str
    name: str
    key: Any


class CheckMissingRecordPage(CollectionPage[CheckMissingRecord]):
    """Records missing from the file in source and name order."""
