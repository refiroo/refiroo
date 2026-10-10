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
# The technical tables (J1) or a workbook for people shaped by one collection (0.9 J6, D179).
ExportLayout = Literal["technical", "people"]


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


class OwnedColumns(BaseModel):
    """An owned relationship's sheet as columns per parent (0.9 J6a, D191, D192): the parents added
    to those already holding an owned record of an exported one, and the owned records' fields
    (``name`` or an attribute), each parent getting one column per field."""

    model_config = ConfigDict(extra="forbid")

    parents: list[UUID4] = Field(default_factory=list)
    fields: list[str] | None = Field(
        default=None, min_length=1, description="The owned type's writable attributes when omitted"
    )


class PeopleLayout(BaseModel):
    """What a workbook for people holds (0.9 J6, D180–D182, D188): the main sheet's columns as a
    table view names them, the relationships that get a sheet of their own (relation keys or reverse
    keys), and the field a ``related:<key>`` column shows instead of the related records' names."""

    model_config = ConfigDict(extra="forbid")

    columns: list[str] | None = Field(
        default=None,
        min_length=1,
        description="As a table view's columns; the name and the type's attributes when omitted",
    )
    sheets: list[str] = Field(default_factory=list)
    columnFields: dict[str, str] = Field(default_factory=dict)
    ownedColumns: dict[str, OwnedColumns] = Field(
        default_factory=dict,
        description="Sheets of owned records laid out as columns per parent, by their relation key",
    )
    referenceLists: list[str] | None = Field(
        default=None,
        description=(
            "Relation keys whose pointer cells offer a list of the records they may choose; every"
            " relationship the workbook names when omitted (0.9 J6a, D196, D197)"
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
    layout: ExportLayout = "technical"
    people: PeopleLayout | None = None
