"""The export request (Base 0.9 J1, INTEGRATION_API §J4, D49–D53).

The body's shape is checked here: JSON types, unknown properties, bounds, one context and each type
once. What the names in it mean (a type, a field, an operator, a relation binding) depends on the
model and is checked by ``engine/jobs/exports.py`` through the model query's own checks, refused as
``INVALID_QUERY`` at a JSON pointer into the body.
"""

from typing import Literal

from pydantic import UUID4, BaseModel, ConfigDict, Field, model_validator

from .queries import QueryContext, QueryCriterion

ExportFormat = Literal["jsonl", "csv", "xlsx"]
RelationInclusion = Literal["none", "withinScope", "all"]


class ExportContext(QueryContext):
    """Live data when empty, or one change set or publication."""

    @model_validator(mode="after")
    def one_context(self) -> ExportContext:
        if self.changeSetId is not None and self.publicationId is not None:
            raise ValueError("Name a change set or a publication, not both")
        return self


class ExportType(BaseModel):
    """One exported object type and its own criteria, as the model query's ``where``."""

    model_config = ConfigDict(extra="forbid")

    objectTypeKey: str
    where: list[QueryCriterion] = Field(default_factory=list)


class ExportScope(BaseModel):
    model_config = ConfigDict(extra="forbid")

    types: list[ExportType] = Field(min_length=1)
    parentObjectId: UUID4 | None = Field(
        default=None, description="Only records below this record, at any depth"
    )
    asOf: str | None = Field(
        default=None,
        description=(
            "A date (YYYY-MM-DD): the types that declare an effective period export the records"
            " effective on it; the others are exported undated (D50)"
        ),
    )

    @model_validator(mode="after")
    def each_type_once(self) -> ExportScope:
        keys = [item.objectTypeKey for item in self.types]
        if len(keys) != len(set(keys)):
            raise ValueError("Each object type is named once")
        return self


class ExportInclude(BaseModel):
    model_config = ConfigDict(extra="forbid")

    relations: RelationInclusion = Field(
        default="withinScope",
        description=(
            "none; withinScope, relationships whose both ends are exported; all, every"
            " relationship of an exported record"
        ),
    )


class ExportRequest(BaseModel):
    """An export of a stated scope of one workspace, run as a background job."""

    model_config = ConfigDict(extra="forbid")

    workspaceKey: str
    context: ExportContext = Field(default_factory=ExportContext)
    scope: ExportScope
    include: ExportInclude = Field(default_factory=ExportInclude)
    format: ExportFormat
