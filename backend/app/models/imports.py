"""Import profiles and the import request (Base 0.9 J2, INTEGRATION_API §J1–§J3, D64–D73).

The shapes are checked here: JSON types, unknown properties, one binding kind per column. What
the keys in a profile mean (a type in its application, an attribute the type binds, a relationship
the two types allow, a source order without a cycle) depends on the model and is checked by
``engine/imports/profiles.py``, which reports every problem at its JSON pointer.
"""

from typing import Any, Literal

from pydantic import UUID4, BaseModel, ConfigDict, Field, model_validator

Direction = Literal["outgoing", "incoming"]
ImportFormat = Literal["xlsx", "csv", "jsonl"]
COLUMN_LETTERS = r"^[A-Z]{1,3}$"


class MatchBy(BaseModel):
    """What a match compares a cell with: the record's name, its public ID or one attribute's
    value. A match need not be unique: a cell matching several records is refused by row."""

    model_config = ConfigDict(extra="forbid")

    field: Literal["name", "id"] | None = None
    attributeTypeKey: str | None = None

    @model_validator(mode="after")
    def one_form(self) -> MatchBy:
        if (self.field is None) == (self.attributeTypeKey is None):
            raise ValueError("matchBy is either {field} or {attributeTypeKey}")
        return self


class ParentBinding(BaseModel):
    model_config = ConfigDict(extra="forbid")

    objectTypeKey: str
    matchBy: MatchBy


class RelationBinding(BaseModel):
    """A relationship from the row's record (``outgoing``) or to it (``incoming``) to each record a
    cell matches; ``split`` cuts the cell into several values; ``replace`` makes the matched records
    the whole set instead of adding to it."""

    model_config = ConfigDict(extra="forbid")

    relationTypeKey: str
    direction: Direction = "outgoing"
    objectTypeKey: str
    matchBy: MatchBy
    split: str | None = Field(default=None, min_length=1)
    replace: bool = False


class FlagsBinding(BaseModel):
    """Columns that each stand for one record: a cell counted as set relates the row's record to it."""

    model_config = ConfigDict(extra="forbid")

    relationTypeKey: str
    direction: Direction = "outgoing"
    objectTypeKey: str
    matchBy: MatchBy
    targets: dict[str, str] = Field(min_length=1)
    trueValues: list[str] = Field(
        default_factory=lambda: ["x", "yes", "y", "true", "1"],
        description="Cell texts counted as set, compared ignoring case; a boolean TRUE cell is set",
    )


class RelatedParent(BaseModel):
    """Where a related record stands: the record ``matchBy`` finds for a fixed ``value``, or for the
    row's cell in ``column``."""

    model_config = ConfigDict(extra="forbid")

    objectTypeKey: str
    matchBy: MatchBy
    value: str | None = None
    column: str | None = None

    @model_validator(mode="after")
    def one_source(self) -> RelatedParent:
        if (self.value is None) == (self.column is None):
            raise ValueError("A related record's parent has either a value or a column")
        return self


class RelatedMatch(BaseModel):
    model_config = ConfigDict(extra="forbid")

    attributeTypeKey: str


class RelatedRecordBinding(BaseModel):
    """A record of ``objectTypeKey`` under ``parent``, related to the row's record by
    ``relationTypeKey``; this column is one of its values (D70). Columns naming the same relation,
    type and parent fill one related record."""

    model_config = ConfigDict(extra="forbid")

    relationTypeKey: str
    direction: Direction = "outgoing"
    applicationKey: str
    objectTypeKey: str
    parent: RelatedParent
    field: Literal["name"] | None = None
    attributeTypeKey: str | None = None
    matchBy: RelatedMatch | None = Field(
        default=None,
        description="Narrows which related record the row means, by one of its own values",
    )

    @model_validator(mode="after")
    def one_target(self) -> RelatedRecordBinding:
        if (self.field is None) == (self.attributeTypeKey is None):
            raise ValueError("A related record column fills either {field} or {attributeTypeKey}")
        return self


BINDING_KINDS = (
    "field",
    "attributeTypeKey",
    "parent",
    "relation",
    "relationFlags",
    "relatedRecord",
    "ignore",
)


class ColumnBinding(BaseModel):
    """One column (or, for ``relationFlags``, several) and what it fills. ``valueMap`` names a map
    applied to the cell's text before it is converted or matched."""

    model_config = ConfigDict(extra="forbid")

    column: str | None = Field(default=None, min_length=1)
    columns: list[str] | None = Field(default=None, min_length=1)
    field: Literal["name"] | None = None
    attributeTypeKey: str | None = None
    parent: ParentBinding | None = None
    relation: RelationBinding | None = None
    relationFlags: FlagsBinding | None = None
    relatedRecord: RelatedRecordBinding | None = None
    ignore: Literal[True] | None = None
    valueMap: str | None = None

    @model_validator(mode="after")
    def one_kind(self) -> ColumnBinding:
        kinds = [name for name in BINDING_KINDS if getattr(self, name) is not None]
        if len(kinds) != 1:
            raise ValueError(f"A column binding has exactly one of {', '.join(BINDING_KINDS)}")
        if self.relationFlags is not None:
            if self.columns is None or self.column is not None:
                raise ValueError("relationFlags names its columns in columns")
        elif self.column is None or self.columns is not None:
            raise ValueError("A column binding names its column in column")
        return self

    @property
    def kind(self) -> str:
        return next(name for name in BINDING_KINDS if getattr(self, name) is not None)


class Block(BaseModel):
    """A rectangle of a sheet: the source's header row is its first row."""

    model_config = ConfigDict(extra="forbid")

    firstColumn: str = Field(pattern=COLUMN_LETTERS)
    lastColumn: str = Field(pattern=COLUMN_LETTERS)
    lastRow: int | None = Field(default=None, ge=1)


class SourceKey(BaseModel):
    """What finds a row's existing record: one unique attribute (its value from the column that
    binds it) or a column holding the public ID (D2)."""

    model_config = ConfigDict(extra="forbid")

    attributeTypeKey: str | None = None
    column: str | None = Field(default=None, min_length=1)

    @model_validator(mode="after")
    def one_form(self) -> SourceKey:
        if (self.attributeTypeKey is None) == (self.column is None):
            raise ValueError("A source key is either {attributeTypeKey} or {column}")
        return self


class Source(BaseModel):
    """One object type loaded from a sheet (the first sheet when omitted, the file for CSV).
    ``record: existing`` finds each row's record by its key and writes only its relationships and
    related records."""

    model_config = ConfigDict(extra="forbid")

    sheet: str | None = Field(default=None, min_length=1)
    headerRow: int = Field(default=1, ge=1)
    block: Block | None = None
    applicationKey: str
    objectTypeKey: str
    record: Literal["upsert", "existing"] = "upsert"
    key: SourceKey | None = None
    columns: list[ColumnBinding] = Field(min_length=1)

    @model_validator(mode="after")
    def existing_needs_key(self) -> Source:
        if self.record == "existing" and self.key is None:
            raise ValueError("record: existing finds each row's record by its key")
        return self


class CsvOptions(BaseModel):
    model_config = ConfigDict(extra="forbid")

    delimiter: str = Field(default=",", min_length=1, max_length=1)


class ImportProfileDefinition(BaseModel):
    model_config = ConfigDict(extra="forbid")

    csv: CsvOptions | None = None
    sources: list[Source] = Field(min_length=1)
    valueMaps: dict[str, dict[str, Any]] = Field(default_factory=dict)


ProfileKey = Field(min_length=1, max_length=160, pattern=r"^[A-Za-z0-9][A-Za-z0-9_.-]*$")


class ImportProfileCreate(ImportProfileDefinition):
    key: str = ProfileKey
    name: str = Field(min_length=1, max_length=200)


class ImportProfileUpdate(ImportProfileDefinition):
    """The whole profile at ``expectedVersion``; its key is the path's."""

    name: str = Field(min_length=1, max_length=200)
    expectedVersion: int = Field(ge=1)


class InlineProfile(ImportProfileDefinition):
    name: str | None = None


class ImportRequest(BaseModel):
    """``POST /imports``'s ``request`` part. A stored profile by ``profileKey``, one given inline,
    or neither for a JSON Lines file or an export's table layout (D71). ``stage: execute`` runs the
    import as soon as its file is bound; J3 adds ``preview``."""

    model_config = ConfigDict(extra="forbid")

    workspaceKey: str | None = None
    changeSetId: UUID4 | None = None
    expectedChangeSetVersion: int | None = Field(default=None, ge=1)
    profileKey: str | None = None
    profile: InlineProfile | None = None
    format: ImportFormat | None = None
    policy: Literal["atomic", "independent"]
    onExisting: Literal["reject", "overwrite"] = "reject"
    stage: Literal["execute"]

    @model_validator(mode="after")
    def one_profile(self) -> ImportRequest:
        if self.profileKey is not None and self.profile is not None:
            raise ValueError("Name a stored profile or give one inline, not both")
        return self
