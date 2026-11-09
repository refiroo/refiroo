"""Source files, the dry run and the inference: what a client sends (Product 0.10 A3, A6, API.md
§ Model authoring).

A source file belongs to a model draft or an import profile (D5). A dry run names a draft's source
file and the import profile to bind it with (D65), and runs the import against the draft's model in
a workspace, writing nothing (D67).
"""

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from .commands import BatchItem
from .imports import Block, CsvOptions, InlineProfile

SourceFormat = Literal["xlsx", "csv"]


class SourceFileOwner(BaseModel):
    model_config = ConfigDict(extra="forbid")

    draftId: str | None = None
    profileKey: str | None = None

    @model_validator(mode="after")
    def one_owner(self) -> SourceFileOwner:
        if (self.draftId is None) == (self.profileKey is None):
            raise ValueError("A source file belongs to one model draft (draftId) or one profile")
        return self


class SourceFileRequest(BaseModel):
    """``POST /source-files``'s ``request`` part. ``workspaceKey`` names the workspace whose
    records the profile compares the columns with (D69); without it, columns are compared with
    each other only."""

    model_config = ConfigDict(extra="forbid")

    owner: SourceFileOwner
    format: SourceFormat | None = None
    csv: CsvOptions | None = None
    workspaceKey: str | None = Field(default=None, min_length=1)


class DryRunRequest(BaseModel):
    """``POST /model-drafts/{id}/dry-run``: either the draft's source file, the workspace the import
    would write in, and the profile that binds the file (D65), checked against the draft's model; or
    ``items``, the batch items of ``POST /batches`` (each with an optional ``ref`` naming the cells
    it comes from), previewed against the draft's model in the workspace (0.13 AB). Exactly one of
    ``sourceFileId`` and ``items``. Without ``profile`` a source file is read with the profile the
    draft holds (0.13 AT); one sent may be the profile ``GET /model-drafts/{id}/profile`` answered,
    whose read-only ``key``, ``unmapped``, ``ignoredSheets`` and source ``id`` are ignored."""

    model_config = ConfigDict(extra="forbid")

    sourceFileId: str | None = None
    workspaceKey: str = Field(min_length=1)
    profile: InlineProfile | None = None
    onExisting: Literal["reject", "overwrite"] = "reject"
    items: list[BatchItem] | None = Field(default=None, min_length=1)

    @model_validator(mode="after")
    def _a_file_or_items(self) -> DryRunRequest:
        if (self.sourceFileId is None) == (self.items is None):
            raise ValueError("Send either sourceFileId (a source file) or items, not both")
        if self.items is not None and self.profile is not None:
            raise ValueError("profile applies only to a source file")
        return self

    @field_validator("profile", mode="before")
    @classmethod
    def without_read_only_members(cls, value: Any) -> Any:
        """What the draft's profile read adds to an import profile is not an input."""
        if not isinstance(value, dict):
            return value
        kept = {n: m for n, m in value.items() if n not in ("key", "unmapped", "ignoredSheets")}
        if isinstance(kept.get("sources"), list):
            kept["sources"] = [
                {n: m for n, m in source.items() if n != "id"}
                if isinstance(source, dict)
                else source
                for source in kept["sources"]
            ]
        return kept


class InferenceRequest(BaseModel):
    """``POST /model-drafts/{id}/inference`` (0.10 A6, D87): what the table patterns propose for
    the draft's current source file: a new application (named ``applicationName``, by default after
    the file, keyed ``applicationKey`` when given), or additions to the draft's model, new types
    going into ``applicationKey`` (by default the application most matched types are in, D91)."""

    model_config = ConfigDict(extra="forbid")

    mode: Literal["newApplication", "extend"]
    applicationKey: str | None = Field(default=None, min_length=1)
    applicationName: str | None = Field(default=None, min_length=1)


class ListProposalRequest(BaseModel):
    """``POST /model-drafts/{id}/inference/list`` (0.10 A8b, D128): a rectangle of the draft's
    file to read as a list, its header row and ``block`` as a source takes them; new types go into
    ``applicationKey``, by default the application the sheet's sources load into."""

    model_config = ConfigDict(extra="forbid")

    sheet: str = Field(min_length=1)
    headerRow: int = Field(ge=1)
    block: Block
    applicationKey: str | None = Field(default=None, min_length=1)


class InferenceApplicationRequest(BaseModel):
    """``POST /model-drafts/{id}/inference/application`` (D89): the proposals of the draft's latest
    inference to apply, each its own step; by default every one that is open."""

    model_config = ConfigDict(extra="forbid")

    expectedVersion: int = Field(ge=1)
    proposals: list[str] | None = Field(default=None, min_length=1)
