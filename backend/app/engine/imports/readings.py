"""How a source's table is read before its columns are bound (0.17 PL3b, PP-D6 and PP-D7).

A source may carry three readings, applied to the rows its reader gives, in this order: ``headings``
(a row holding only a heading is not a record; its text becomes a column of the rows beneath it),
``fillDown`` (an empty cell takes the nearest filled one above it) and ``unpivot`` (a wide row
becomes one row per filled cell of the listed columns). They add columns at the end of the table,
which a binding names like any header (:func:`virtual_columns`), and they leave the file, the cells'
positions and every later step as they are: the binding, the dry run and the saved profile read the
result like any table. The rows stream through; nothing holds the set.
"""

from collections.abc import Iterator
from typing import Any

from ...models.imports import Source
from .cells import is_empty
from .readers import Table


def virtual_columns(source: Source) -> list[str]:
    """The columns the source's readings add, in the order they are appended to the table."""
    added: list[str] = []
    if source.headings is not None:
        added.append(source.headings.into)
    if source.unpivot is not None:
        added += [source.unpivot.nameColumn, source.unpivot.valueColumn]
    return added


def reading_columns(source: Source) -> list[tuple[str, str]]:
    """Every column of the file the readings name, with its pointer in the source."""
    named: list[tuple[str, str]] = []
    if source.headings is not None:
        named.append(("/headings/column", source.headings.column))
    for position, name in enumerate(source.fillDown or []):
        named.append((f"/fillDown/{position}", name))
    if source.unpivot is not None:
        for position, name in enumerate(source.unpivot.columns):
            named.append((f"/unpivot/columns/{position}", name))
    return named


def has_readings(source: Source) -> bool:
    return source.headings is not None or source.fillDown is not None or source.unpivot is not None


def clashes(source: Source, table: Table) -> list[tuple[str, str]]:
    """The added columns whose name the table's header already has, with their pointers."""
    if not has_readings(source):
        return []
    taken = set(table.columns())
    found: list[tuple[str, str]] = []
    if source.headings is not None and source.headings.into in taken:
        found.append(("/headings/into", source.headings.into))
    if source.unpivot is not None:
        for member in ("nameColumn", "valueColumn"):
            name = getattr(source.unpivot, member)
            if name in taken:
                found.append((f"/unpivot/{member}", name))
    return found


def apply_readings(table: Table, source: Source) -> Table:
    """``table`` as the source's readings read it. The added columns come last; a name the table
    already has is a mismatch the caller raises first (:func:`clashes`)."""
    if not has_readings(source):
        return table
    positions = table.columns()
    width = len(table.header)
    added = virtual_columns(source)
    heading_at = positions.get(source.headings.column) if source.headings else None
    into_at = width + added.index(source.headings.into) if source.headings else None
    fill = [positions[name] for name in source.fillDown or [] if name in positions]
    wide = (
        [positions[name] for name in source.unpivot.columns if name in positions]
        if source.unpivot
        else []
    )
    name_at = width + added.index(source.unpivot.nameColumn) if source.unpivot else None
    value_at = width + added.index(source.unpivot.valueColumn) if source.unpivot else None
    header = [*table.header, *added]
    rows = table.rows

    def read() -> Iterator[tuple[int, list[Any]]]:
        heading: Any = None
        last: dict[int, Any] = {}
        for number, cells in rows:
            if (
                heading_at is not None
                and heading_at < len(cells)
                and not is_empty(cells[heading_at])
                and all(is_empty(value) for at, value in enumerate(cells) if at != heading_at)
            ):
                heading = cells[heading_at]
                continue
            row = [*cells, *([None] * len(added))]
            if into_at is not None:
                row[into_at] = heading
            for at in fill:
                if is_empty(row[at]):
                    row[at] = last.get(at)
                else:
                    last[at] = row[at]
            if name_at is None or value_at is None:
                yield number, row
                continue
            for at in wide:
                if is_empty(row[at]):
                    continue
                yield (
                    number,
                    [
                        *row[:name_at],
                        table.header[at],
                        row[at],
                        *row[value_at + 1 :],
                    ],
                )

    return Table(header, read(), table.first_column)
