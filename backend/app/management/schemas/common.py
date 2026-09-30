import re
from datetime import date
from typing import Annotated, Any

from pydantic import BaseModel, BeforeValidator, Field
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


class ApiErrorBody(BaseModel):
    code: str
    message: str
    details: Any | None = None


class ApiErrorResponse(BaseModel):
    error: ApiErrorBody
