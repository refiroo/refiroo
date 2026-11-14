import re
from datetime import date
from typing import Annotated, Any, Literal

from pydantic import BaseModel, BeforeValidator, Field, TypeAdapter
from pydantic.json_schema import SkipJsonSchema

_CALENDAR_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _calendar_date(value: object) -> object:
    """Only a calendar date: no time, no timestamp (ADR-038 dates have no time zone)."""
    if isinstance(value, str) and not _CALENDAR_DATE.match(value):
        raise ValueError("must be a date (YYYY-MM-DD)")
    return value


# A business date such as asOf, written YYYY-MM-DD and nothing else.
CalendarDate = Annotated[date, BeforeValidator(_calendar_date)]


def without_default(schema: dict[str, Any]) -> None:
    schema.pop("default", None)


def omitted_when_none(value: object) -> bool:
    return value is None


def omitted() -> Any:
    """Omitted from the body rather than null."""
    return Field(default=None, exclude_if=omitted_when_none, json_schema_extra=without_default)


class ProposalOrigin(BaseModel):
    """Who proposed a change when a person did not (0.16 AP2, AP-D5): the provider and model that
    answered, the prompt's version, how confident it was and why, and the person or client whose
    request asked for it."""

    kind: Literal["ai"]
    provider: str
    model: str | None = None
    promptVersion: str
    # A session gives neither (0.16 AP9, AP-D32).
    confidence: float | SkipJsonSchema[None] = omitted()
    reason: str | SkipJsonSchema[None] = omitted()
    proposedBy: str | None = None
    proposedByName: str | SkipJsonSchema[None] = omitted()
    editedBy: str | SkipJsonSchema[None] = omitted()
    editedByName: str | SkipJsonSchema[None] = omitted()
    taskId: str | SkipJsonSchema[None] = omitted()


class AgentOrigin(BaseModel):
    """A change an assistant prepared through a tool (0.16 AG-D29): the name it gave itself, and the
    person or client it acted for."""

    kind: Literal["agent"]
    application: str
    proposedBy: str | None = None
    proposedByName: str | SkipJsonSchema[None] = omitted()
    editedBy: str | SkipJsonSchema[None] = omitted()
    editedByName: str | SkipJsonSchema[None] = omitted()


ChangeOrigin = Annotated[ProposalOrigin | AgentOrigin, Field(discriminator="kind")]
_CHANGE_ORIGIN: TypeAdapter[ProposalOrigin | AgentOrigin] = TypeAdapter(ChangeOrigin)


def change_origin(found: dict[str, Any]) -> ProposalOrigin | AgentOrigin:
    """A stored origin as a read shows it, of whichever kind."""
    return _CHANGE_ORIGIN.validate_python(found)


def optional_origin() -> Any:
    """An ``origin`` present only on what a proposal made: omitted otherwise."""
    return Field(default=None, exclude_if=omitted_when_none, json_schema_extra=without_default)


def requested_count() -> Any:
    """A count present only when asked for: omitted from the body rather than null, and documented
    as an optional integer."""
    return Field(default=None, exclude_if=omitted_when_none, json_schema_extra=without_default)


class CollectionPage[Item](BaseModel):
    """One page of a collection (ADR-030): ``items`` first, then the navigation fields.

    ``nextCursor`` and ``prevCursor`` continue after the last and before the first row and are
    null at the end and the start; ``anchor`` reopens this page. ``totalCount`` and ``startIndex``
    (the number of matching rows before the first row) are present only with ``includeTotal=true``
    and omitted otherwise.
    """

    items: list[Item]
    nextCursor: str | None
    prevCursor: str | None = None
    anchor: str | None = None
    totalCount: int | SkipJsonSchema[None] = requested_count()
    startIndex: int | SkipJsonSchema[None] = requested_count()


class PrincipalResponse(BaseModel):
    """A person or a client as a read names it now (0.12 Z4, D237): a renamed or deactivated one
    reads as it is."""

    kind: Literal["user", "client"]
    id: str
    name: str


class ActorResponse(BaseModel):
    """Who made a change (0.12 Z4, D313): a person or a client, or the engine for its own changes,
    which has no ID or name. An entry from before Z4 has no actor (``null``)."""

    kind: Literal["user", "client", "engine"]
    id: str | SkipJsonSchema[None] = Field(
        default=None, exclude_if=omitted_when_none, json_schema_extra=without_default
    )
    name: str | SkipJsonSchema[None] = Field(
        default=None, exclude_if=omitted_when_none, json_schema_extra=without_default
    )


class ApiErrorBody(BaseModel):
    code: str
    message: str
    details: Any | None = None


class ApiErrorResponse(BaseModel):
    error: ApiErrorBody
