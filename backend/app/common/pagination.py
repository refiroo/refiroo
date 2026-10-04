"""Shared keyset pagination (ADR-030).

Every public collection pages with a signed, filter-bound keyset cursor or, for jumps, a row
position. The two entry points here own that mechanism so each endpoint only declares its sort keys:

* :func:`paginate_statement` pages a SQLAlchemy select over persisted rows;
* :func:`paginate_sequence` pages an in-memory sequence of model definitions.

A statement over a large indexed base overlaid by a few rows of its own (a change set over its base)
can also name the parts it unions (:class:`Overlay`), so a position read resolves against the
base's index instead of skipping every earlier row through the union.

A request selects its page with at most one of ``cursor``, ``position``, ``seek`` or ``from=end``
(:class:`PageRequest`); none means the first page. Whatever it used, a page returns ``nextCursor``
and ``prevCursor`` to continue in either direction, an ``anchor`` that reopens the same page, and,
when asked, ``totalCount`` and ``startIndex``. Cursor reads never repeat or skip a row when data
changes between requests; position reads address rows by number and can.

Sort keys must form a strict total order: the last key of a statement paginator has to be unique
within the filtered set, otherwise rows can be skipped or repeated across a page boundary.
"""

from collections.abc import Callable, Sequence
from dataclasses import dataclass, replace
from datetime import datetime
from typing import Any

from sqlalchemy import and_, func, literal, or_, select
from sqlalchemy.orm import Session

from ..errors import api_error
from .cursors import CursorDirection, decode_directed_cursor, encode_cursor
from .time import as_utc


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


@dataclass(frozen=True)
class PageRequest:
    """Which page of a collection to read.

    At most one of ``cursor``, ``position``, ``seek`` and ``from_end`` selects the page; none selects
    the first page. ``include_total`` adds ``totalCount`` and ``startIndex``, counted under the same
    filters.
    """

    cursor: str | None = None
    position: int | None = None
    seek: str | None = None
    from_end: bool = False
    include_total: bool = False

    def __post_init__(self) -> None:
        chosen = [
            name
            for name, present in (
                ("cursor", self.cursor is not None),
                ("position", self.position is not None),
                ("seek", self.seek is not None),
                ("from", self.from_end),
            )
            if present
        ]
        if len(chosen) > 1:
            raise api_error(
                422,
                "CONFLICTING_PAGE_PARAMETERS",
                "Select a page with one of cursor, position, seek or from=end, not "
                + " and ".join(chosen),
                {"parameters": chosen},
            )
        if self.position is not None and self.position < 0:
            raise api_error(
                422,
                "INVALID_POSITION",
                "position must be zero or greater",
                {"path": "/query/position"},
            )


FIRST_PAGE = PageRequest()


@dataclass(frozen=True)
class Keyed:
    """A statement and the keyset it is ordered by."""

    statement: Any
    keys: Sequence[SortKey]


@dataclass(frozen=True)
class Overlay:
    """The parts of a statement whose rows are a base's, less those it replaces, plus its own.

    ``base`` holds every base row, replaced or not, ``replaced`` the base rows the overlay
    replaces or deletes, and ``added`` the overlay's own rows; each is filtered as the statement is
    and keyed by the same sort, in the same order. A position read then resolves in the base alone,
    where an index can skip the earlier rows, and corrects for the overlay rows before it (see
    :func:`_locate`); an overlay costs in proportion to its own size, not the base's.
    """

    base: Keyed
    replaced: Keyed
    added: Keyed


@dataclass(frozen=True)
class Page[Item]:
    """One page in list order, with the cursors to continue from it."""

    items: list[Item]
    next_cursor: str | None = None
    prev_cursor: str | None = None
    anchor: str | None = None
    total_count: int | None = None
    start_index: int | None = None

    def links(self) -> dict[str, Any]:
        """The page's navigation fields, as every page response names them."""
        return {
            "nextCursor": self.next_cursor,
            "prevCursor": self.prev_cursor,
            "anchor": self.anchor,
            "totalCount": self.total_count,
            "startIndex": self.start_index,
        }


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


def seek_predicate(keys: Sequence[SortKey], values: Sequence[Any]) -> Any:
    """Rows at or after ``values`` on a leading prefix of ``keys``, in list order."""
    return _keyset_predicate(keys[: len(values)], values, backward=False, inclusive=True)


def seek_error(message: str = "Seek value is invalid for the list's sort") -> Exception:
    return api_error(422, "INVALID_SEEK", message, {"path": "/query/seek"})


def leading_key_seek(keys: Sequence[SortKey]) -> Callable[[str], Any]:
    """Seek on the first sort key, parsed as its cursor token is."""

    def seek(raw: str) -> Any:
        try:
            value = keys[0].parse(raw)
        except ValueError:
            raise seek_error() from None
        return seek_predicate(keys, [value])

    return seek


def paginate_statement[Row](
    session: Session,
    statement: Any,
    *,
    keys: Sequence[SortKey],
    scope: str,
    filters: dict[str, Any],
    page: PageRequest,
    page_size: int,
    cursor_sort_tokens: tuple[str, ...] | None = None,
    message: str = "Cursor is invalid",
    rows: bool = False,
    seek: Callable[[str], Any] | None = None,
    overlay: Overlay | None = None,
) -> Page[Row]:
    """Page a select with a lexicographic keyset predicate over ``keys``.

    A statement over one mapped entity returns its instances; with ``rows=True`` a statement over
    labelled columns (a change set or publication projection) returns result rows. ``seek`` turns a
    ``seek`` value into a predicate; without it, seek applies to the first sort key. ``overlay``
    names the parts of a base-plus-overlay statement, which position reads resolve through.

    Besides the page itself a read costs at most one probe for the opposite edge and, with totals,
    two counts: its statement count does not grow with the dataset. A first or position page
    that reaches the end needs no count for its total.
    """
    if not keys:
        raise ValueError("Keyset pagination requires at least one sort key")
    sort = cursor_sort(keys) if cursor_sort_tokens is None else cursor_sort_tokens
    if len(sort) != len(keys):
        raise ValueError("Cursor sort tokens must match the keyset width")

    def fetch(where: Any, limit: int, *, backward: bool = False, offset: int = 0) -> list[Any]:
        selected = _ordered(statement, keys, where, limit, backward=backward, offset=offset)
        return list(session.execute(selected).all() if rows else session.scalars(selected))

    positions: dict[int, tuple[str, ...]] = {}

    def position_of(row: Any) -> tuple[str, ...]:
        if id(row) not in positions:
            positions[id(row)] = _row_position(session, keys, row)
        return positions[id(row)]

    def beyond(row: Any, *, backward: bool) -> Any:
        values = _parse_position(keys, position_of(row), message)
        return _keyset_predicate(keys, values, backward=backward, inclusive=False)

    backward = False
    # Rows before the page when known without a probe: the first page and position reads.
    known_before: int | None = None
    if page.cursor is not None:
        direction, token = decode_directed_cursor(
            page.cursor,
            scope=scope,
            sort=sort,
            filters=filters,
            position_size=len(keys),
            message=message,
        )
        backward = direction in {"before", "upto"}
        predicate = _keyset_predicate(
            keys,
            _parse_position(keys, token, message),
            backward=backward,
            inclusive=direction in {"from", "upto"},
        )
        fetched = fetch(predicate, page_size + 1, backward=backward)
    elif page.seek is not None:
        fetched = fetch((seek or leading_key_seek(keys))(page.seek), page_size + 1)
    elif page.position is not None:
        known_before = page.position
        located = (
            _locate(session, overlay, page.position, rows=rows, message=message)
            if overlay is not None
            else None
        )
        if located is None:
            fetched = fetch(None, page_size + 1, offset=page.position)
        else:
            values, skip = located
            at = _keyset_predicate(keys, values, backward=False, inclusive=True)
            fetched = fetch(at, page_size + 1, offset=skip)
    elif page.from_end:
        backward = True
        fetched = fetch(None, page_size + 1, backward=True)
    else:
        known_before = 0
        fetched = fetch(None, page_size + 1)

    visible = fetched[:page_size]
    more = len(fetched) > page_size
    if backward:
        visible.reverse()
    has_before, has_after = (more, False) if backward else (False, more)
    # An empty page has no row to continue from, so it continues from the nearest row instead.
    edge_first = edge_last = None
    if backward and not page.from_end:
        if visible:
            has_after = bool(fetch(beyond(visible[-1], backward=False), 1))
        else:
            edge_first = next(iter(fetch(None, 1)), None)
    elif not backward:
        if visible and known_before is None:
            has_before = bool(fetch(beyond(visible[0], backward=True), 1, backward=True))
        elif visible:
            has_before = known_before > 0
        elif known_before != 0:
            edge_last = next(iter(fetch(None, 1, backward=True)), None)

    def encode(row: Any, direction: CursorDirection) -> str:
        return encode_cursor(
            position_of(row), scope=scope, sort=sort, filters=filters, direction=direction
        )

    result = Page(
        items=visible,
        next_cursor=(
            encode(visible[-1], "after")
            if visible and has_after
            else encode(edge_first, "from") if edge_first is not None else None
        ),
        prev_cursor=(
            encode(visible[0], "before")
            if visible and has_before
            else encode(edge_last, "upto") if edge_last is not None else None
        ),
        anchor=encode(visible[0], "from") if visible else None,
    )
    if not page.include_total:
        return result
    if known_before is not None and not more and (visible or known_before == 0):
        # The page runs from a known position to the end: its rows are all that remain.
        total = known_before + len(visible)
    else:
        total = _total(session, statement, overlay)
    if not visible:
        start = 0 if backward or known_before == 0 else total
    elif known_before is not None:
        start = known_before
    elif page.from_end:
        start = total - len(visible)
    else:
        start = _count(session, statement.where(beyond(visible[0], backward=True)))
    return replace(result, total_count=total, start_index=start)


def paginate_sequence[Item](
    items: Sequence[Item],
    identity: Callable[[Item], tuple[str, ...]],
    *,
    scope: str,
    filters: dict[str, Any] | None = None,
    page: PageRequest = FIRST_PAGE,
    page_size: int,
    sort: tuple[str, ...] = ("key",),
    descending: bool = False,
    message: str = "Cursor is invalid",
) -> Page[Item]:
    """Page an in-memory sequence ordered by its identity tuple."""
    cursor_filters = filters or {}
    ordered = sorted(items, key=identity, reverse=descending)
    count = len(ordered)
    if page.seek is not None:
        raise seek_error("This collection does not support seek")
    if page.cursor is not None:
        direction, token = decode_directed_cursor(
            page.cursor, scope=scope, sort=sort, filters=cursor_filters, message=message
        )
        expected_width = len(identity(ordered[0])) if ordered else len(token)
        if len(token) != expected_width:
            raise api_error(422, "INVALID_CURSOR", message)
        precedes = (lambda item: item > token) if descending else (lambda item: item < token)
        before = sum(1 for item in ordered if precedes(identity(item)))
        through = sum(1 for item in ordered if precedes(identity(item)) or identity(item) == token)
        if direction in {"after", "from"}:
            start = through if direction == "after" else before
            end = min(count, start + page_size)
        else:
            end = before if direction == "before" else through
            start = max(0, end - page_size)
    elif page.position is not None:
        start = page.position
        end = min(count, start + page_size)
    elif page.from_end:
        end = count
        start = max(0, end - page_size)
    else:
        start, end = 0, min(count, page_size)
    visible = list(ordered[start:end])

    def encode(item: Item, direction: CursorDirection) -> str:
        return encode_cursor(
            identity(item), scope=scope, sort=sort, filters=cursor_filters, direction=direction
        )

    next_cursor = prev_cursor = None
    if visible:
        next_cursor = encode(visible[-1], "after") if end < count else None
        prev_cursor = encode(visible[0], "before") if start > 0 else None
    elif ordered and start >= count:
        prev_cursor = encode(ordered[-1], "upto")
    elif ordered:
        next_cursor = encode(ordered[0], "from")
    return Page(
        items=visible,
        next_cursor=next_cursor,
        prev_cursor=prev_cursor,
        anchor=encode(visible[0], "from") if visible else None,
        total_count=count if page.include_total else None,
        start_index=min(start, count) if page.include_total else None,
    )


def _locate(
    session: Session, overlay: Overlay, position: int, *, rows: bool, message: str
) -> tuple[list[Any], int] | None:
    """A keyset position and the rows after it to skip to reach row ``position`` of the union.

    With ``added`` overlay rows, at most ``added`` of them precede row ``position``, so the base
    row at ``position - added`` precedes it, or is it. Its rank in the union is its base rank, less
    the replaced base rows before it, plus the overlay rows before it; the remainder is at most
    the overlay's size. Returns ``None`` when no such base row exists: a shallow position or one
    past the base's end, which the caller reads by offset.
    """
    added = _count(session, overlay.added.statement)
    start = position - added
    if start < 0:
        return None
    base = overlay.base
    selected = _ordered(base.statement, base.keys, None, 1, offset=start)
    row = session.execute(selected).first() if rows else session.scalars(selected).first()
    if row is None:
        return None
    values = _parse_position(base.keys, _row_position(session, base.keys, row), message)

    def before(part: Keyed) -> Any:
        where = _keyset_predicate(part.keys, values, backward=True, inclusive=False)
        return (
            select(func.count())
            .select_from(part.statement.where(where).order_by(None).subquery())
            .scalar_subquery()
        )

    replaced, preceding = session.execute(
        select(before(overlay.replaced), before(overlay.added))
    ).one()
    return values, position - (start - replaced + preceding)


def _ordered(
    statement: Any,
    keys: Sequence[SortKey],
    where: Any,
    limit: int,
    *,
    backward: bool = False,
    offset: int = 0,
) -> Any:
    selected = statement if where is None else statement.where(where)
    selected = selected.order_by(*(_order(key, backward) for key in keys)).limit(limit)
    return selected.offset(offset) if offset else selected


def _order(key: SortKey, backward: bool) -> Any:
    return key.column.asc() if key.descending == backward else key.column.desc()


def _count(session: Session, statement: Any) -> int:
    return session.scalar(select(func.count()).select_from(statement.order_by(None).subquery()))


def _total(session: Session, statement: Any, overlay: Overlay | None) -> int:
    """The number of rows ``statement`` lists.

    An overlay's total is its base's, less the base rows it replaces, plus its own rows, in one
    statement. Each part reads its own index, where counting the union checks every base row
    against the overlay (Base 0.8 S8).
    """
    if overlay is None:
        return _count(session, statement)

    def count(part: Keyed) -> Any:
        return (
            select(func.count())
            .select_from(part.statement.order_by(None).subquery())
            .scalar_subquery()
        )

    base, replaced, added = session.execute(
        select(count(overlay.base), count(overlay.replaced), count(overlay.added))
    ).one()
    return base - replaced + added


def _parse_position(
    keys: Sequence[SortKey], position: tuple[str, ...], message: str
) -> list[Any]:
    try:
        return [key.parse(token) for key, token in zip(keys, position, strict=True)]
    except ValueError:
        raise api_error(422, "INVALID_CURSOR", message) from None


def _keyset_predicate(
    keys: Sequence[SortKey], values: Sequence[Any], *, backward: bool, inclusive: bool
) -> Any:
    """Lexicographic ``(k0, k1, ...) > (v0, v1, ...)`` in list order, honoring each key's direction.

    ``backward`` selects the rows before the position instead; ``inclusive`` adds the rows equal
    to it.
    """
    clauses = []
    # Bind positions as typed literals: SQLAlchemy refuses ``column > True`` for a bare boolean.
    bound = [
        None if value is None else literal(value, key.column.type)
        for key, value in zip(keys, values, strict=True)
    ]

    def past(key: SortKey, value: Any) -> Any:
        return key.column > value if key.descending == backward else key.column < value

    for index, (key, value) in enumerate(zip(keys, bound, strict=True)):
        comparison = None if value is None else past(key, value)
        equalities = [
            previous.column == previous_value
            for previous, previous_value in zip(keys[:index], bound[:index], strict=True)
        ]
        if comparison is not None:
            clauses.append(and_(*equalities, comparison) if equalities else comparison)
    if inclusive:
        clauses.append(and_(*(key.column == value for key, value in zip(keys, bound, strict=True))))
    first, first_value = keys[0], bound[0]
    if first_value is None:
        return or_(*clauses)
    # Implied by every clause; stated so an index on the first key can seek to the position instead
    # of scanning every row before it.
    leading = first.column >= first_value if first.descending == backward else first.column <= first_value
    return and_(leading, or_(*clauses))


def _row_position(session: Session, keys: Sequence[SortKey], row: Any) -> tuple[str, ...]:
    return tuple(
        key.format(key.extract(session, row) if key.extract else getattr(row, key.attribute))
        for key in keys
    )
