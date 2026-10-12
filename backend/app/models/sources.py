"""Source files and the dry run: what a client sends (Product 0.10 A3, API.md § Model authoring).

A source file belongs to a model draft or an import profile (D5). A dry run names a draft's source
file and the import profile to bind it with (D65), and runs the import against the draft's model in
a workspace, writing nothing (D67).
"""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .imports import CsvOptions, InlineProfile

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
    """``POST /model-drafts/{id}/dry-run``: the draft's source file, the workspace the import would
    write in, and the profile that binds the file (D65), checked against the draft's model."""

    model_config = ConfigDict(extra="forbid")

    sourceFileId: str
    workspaceKey: str = Field(min_length=1)
    profile: InlineProfile
    onExisting: Literal["reject", "overwrite"] = "reject"
