"""Read inputs the engine accepts: the model-aware object query (Base 0.9 Q3, INTEGRATION_API §Q3).

The management API takes the query as its request body unchanged. The body's shape is checked here
(D19): JSON types, unknown properties and bounds are request validation errors. What the names in it
mean — a field, an operator, a relation binding, a value of the field's type — depends on the model
and is checked by ``engine/reads/model_query.py``, which refuses it as ``invalid_query`` at a JSON
pointer into the body.
"""

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class QueryContext(BaseModel):
    """Where the query reads: live when empty, or one change set or publication."""

    model_config = ConfigDict(extra="forbid")

    changeSetId: str | None = None
    publicationId: str | None = None


class RelatedCriterion(BaseModel):
    """One relation hop: records at the other end of a binding the queried type has."""

    model_config = ConfigDict(extra="forbid")

    relationTypeKey: str
    direction: Literal["outgoing", "incoming"]
    where: list[QueryCriterion] = Field(
        default_factory=list,
        description="Criteria on the record at the other end, combined with AND; no further hop",
    )


class QueryCriterion(BaseModel):
    """``field``, ``op`` and ``value`` as on the object list, or a ``related`` hop.

    ``not`` inverts a hop: records with no related record matching its criteria.
    """

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    field: str | None = None
    op: str | None = None
    value: Any = None
    related: RelatedCriterion | None = None
    not_: bool = Field(default=False, alias="not")


class QueryExpansion(BaseModel):
    """Records at the other end of a binding, added to each item."""

    model_config = ConfigDict(extra="forbid")

    relationTypeKey: str
    direction: Literal["outgoing", "incoming"]
    select: list[str] | None = Field(
        default=None, description="Fields of each expanded record; omitted, the list's item shape"
    )
    limit: int = Field(default=20, ge=1, le=20)


class ModelQuery(BaseModel):
    """A query over one object type's records (INTEGRATION_API §Q3)."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    objectTypeKey: str
    context: QueryContext = Field(default_factory=QueryContext)
    asOf: str | None = Field(
        default=None,
        description=(
            "A date (YYYY-MM-DD): only records effective on it, by the type's declared effective"
            " period; as_of_not_supported on a type without one"
        ),
    )
    where: list[QueryCriterion] = Field(default_factory=list)
    sort: str | None = Field(
        default=None,
        description=(
            "One field as on the object list, prefix '-' for descending; name when omitted"
        ),
    )
    select: list[str] | None = Field(
        default=None, description="Fields each item returns; omitted, the list's item shape"
    )
    expand: list[QueryExpansion] = Field(default_factory=list)
    pageSize: int = Field(default=100, ge=1, le=500)
    cursor: str | None = None
    position: int | None = Field(default=None, ge=0)
    from_: Literal["start", "end"] = Field(default="start", alias="from")
    includeTotal: bool = False

    def criteria(self) -> dict[str, Any]:
        """The body without its page selection: what a cursor binds, so it pages this query only."""
        return self.model_dump(
            mode="json",
            by_alias=True,
            exclude={"cursor", "position", "from_", "includeTotal", "pageSize"},
        )
