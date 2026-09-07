"""Shared keyset pagination.

Every public collection pages with a signed, filter-bound keyset cursor. The two entry points here
own that mechanism so each endpoint only declares its sort keys:

* :func:`paginate_statement` pages a SQLAlchemy select over persisted rows;
* :func:`paginate_sequence` pages an in-memory sequence of model definitions.

Sort keys must form a strict total order: the last key of a statement paginator has to be unique
within the filtered set, otherwise rows can be skipped or repeated across a page boundary.
"""

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from sqlalchemy import and_, or_
from sqlalchemy.orm import Session

from ..common.time import as_utc
from ..errors import api_error
from .cursors import decode_cursor, encode_cursor


@dataclass(frozen=True)
class SortKey:
    """One component of a keyset sort.

    ``name`` is the token recorded in the cursor, ``column`` orders and filters the statement, and
    ``attribute`` names the mapped attribute the position value is read back from. ``parse``
    converts a cursor token into a comparable value for the column.
    """

    name: str
    column: Any
    attribute: str
    descending: bool = False
    parse: Callable[[str], Any] = str
    format: Callable[[Any], str] = str
    extract: Callable[[Session, Any], Any] | None = None


def integer_key(name: str, column: Any, attribute: str, *, descending: bool = False) -> SortKey:
    return SortKey(
        name=name, column=column, attribute=attribute, descending=descending, parse=int
    )


def datetime_key(name: str, column: Any, attribute: str, *, descending: bool = False) -> SortKey:
    return SortKey(
        name=name,
        column=column,
        attribute=attribute,
        descending=descending,
        parse=datetime.fromisoformat,
        format=lambda value: as_utc(value).isoformat(),
    )


def text_key(name: str, column: Any, attribute: str, *, descending: bool = False) -> SortKey:
    return SortKey(name=name, column=column, attribute=attribute, descending=descending)


def cursor_sort(keys: Sequence[SortKey]) -> tuple[str, ...]:
    """The sort tokens bound into a cursor for these keys."""
    return tuple(f"-{key.name}" if key.descending else key.name for key in keys)


def paginate_statement[Row](
    session: Session,
    statement: Any,
    *,
    keys: Sequence[SortKey],
    scope: str,
    filters: dict[str, Any],
    cursor: str | None,
    page_size: int,
    cursor_sort_tokens: tuple[str, ...] | None = None,
    message: str = "Cursor is invalid",
) -> tuple[list[Row], str | None]:
    """Page a select with a lexicographic keyset predicate over ``keys``."""
    if not keys:
        raise ValueError("Keyset pagination requires at least one sort key")
    sort = cursor_sort(keys) if cursor_sort_tokens is None else cursor_sort_tokens
    if len(sort) != len(keys):
        raise ValueError("Cursor sort tokens must match the keyset width")

    if cursor is not None:
        position = decode_cursor(
            cursor,
            scope=scope,
            sort=sort,
            filters=filters,
            position_size=len(keys),
            message=message,
        )
        values = _parse_position(keys, position, message)
        statement = statement.where(_keyset_predicate(keys, values))

    statement = statement.order_by(
        *(key.column.desc() if key.descending else key.column.asc() for key in keys)
    )
    rows = list(session.scalars(statement.limit(page_size + 1)))
    visible = rows[:page_size]
    next_cursor = None
    if len(rows) > page_size:
        next_cursor = encode_cursor(
            _row_position(session, keys, visible[-1]),
            scope=scope,
            sort=sort,
            filters=filters,
        )
    return visible, next_cursor


def paginate_sequence[Item](
    items: Sequence[Item],
    identity: Callable[[Item], tuple[str, ...]],
    *,
    scope: str,
    filters: dict[str, Any] | None = None,
    cursor: str | None,
    page_size: int,
    sort: tuple[str, ...] = ("key",),
    descending: bool = False,
    message: str = "Cursor is invalid",
) -> tuple[list[Item], str | None]:
    """Page an in-memory sequence ordered by its identity tuple."""
    cursor_filters = filters or {}
    ordered = sorted(items, key=identity, reverse=descending)
    if cursor is not None:
        cursor_identity = decode_cursor(
            cursor,
            scope=scope,
            sort=sort,
            filters=cursor_filters,
            message=message,
        )
        expected_width = len(identity(ordered[0])) if ordered else len(cursor_identity)
        if len(cursor_identity) != expected_width:
            raise api_error(422, "invalid_cursor", message)
        ordered = [
            item
            for item in ordered
            if (identity(item) < cursor_identity if descending else identity(item) > cursor_identity)
        ]
    page = ordered[: page_size + 1]
    visible = page[:page_size]
    next_cursor = (
        encode_cursor(
            identity(visible[-1]),
            scope=scope,
            sort=sort,
            filters=cursor_filters,
        )
        if len(page) > page_size
        else None
    )
    return visible, next_cursor


def _parse_position(
    keys: Sequence[SortKey], position: tuple[str, ...], message: str
) -> list[Any]:
    try:
        return [key.parse(token) for key, token in zip(keys, position, strict=True)]
    except ValueError:
        raise api_error(422, "invalid_cursor", message) from None


def _keyset_predicate(keys: Sequence[SortKey], values: Sequence[Any]) -> Any:
    """Lexicographic ``(k0, k1, ...) > (v0, v1, ...)`` honoring each key's direction."""
    clauses = []
    for index, (key, value) in enumerate(zip(keys, values, strict=True)):
        comparison = None if value is None else (key.column < value if key.descending else key.column > value)
        equalities = [
            previous.column == previous_value
            for previous, previous_value in zip(keys[:index], values[:index], strict=True)
        ]
        if comparison is not None:
            clauses.append(and_(*equalities, comparison) if equalities else comparison)
    return or_(*clauses)


def _row_position(session: Session, keys: Sequence[SortKey], row: Any) -> tuple[str, ...]:
    return tuple(
        key.format(key.extract(session, row) if key.extract else getattr(row, key.attribute))
        for key in keys
    )
