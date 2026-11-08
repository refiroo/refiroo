"""A source file read from its staged cells (Product 0.10 A3, D66).

``StagedFile`` is a ``TabularFile`` over ``source_file_cells``: the import binding reads it as it
reads a workbook or a CSV file, so a dry run binds the rows the profile staged without reading the
file again and through the same binding. A table's header and rows are those the reader would give
for the same area: cells as the reader gave them (``values.unstaged``), empty rows left out.
"""

from collections.abc import Iterator
from dataclasses import dataclass
from typing import Any

from openpyxl.utils.cell import range_boundaries
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from ...errors import api_error
from ...models.database import SourceFileCell, SourceFileSheet
from ..imports.readers import Area, Table, header_cell
from .values import unstaged

# Rows read per statement while a table is streamed.
WINDOW_ROWS = 2_000

_CELLS = """
SELECT row_number, column_number, value FROM source_file_cells
WHERE source_file_id = :file AND sheet_index = :sheet
  AND row_number > :after AND row_number <= :until
  AND column_number BETWEEN :first AND :last
ORDER BY row_number, column_number
"""


@dataclass(frozen=True)
class CellRange:
    """A rectangle of a sheet (``A3:C12``), 1-based and inclusive (0.10 A8b, D124)."""

    first_column: int
    first_row: int
    last_column: int
    last_row: int


def cell_range(session: Session, file_id: int, sheet_index: int, raw: str) -> CellRange:
    """``raw`` read as a range of the sheet; ``422 INVALID_RANGE`` for one that is not a range,
    is empty (its end before its start) or holds no cell of the sheet's used area."""

    def refuse(reason: str) -> Exception:
        return api_error(422, "INVALID_RANGE", f"'{raw}' {reason}", {"range": raw, "path": "/query/range"})

    try:
        first_column, first_row, last_column, last_row = range_boundaries(raw.strip().upper())
    except (ValueError, TypeError):
        raise refuse("is not a range such as A3:C12") from None
    if None in (first_column, first_row, last_column, last_row):
        raise refuse("names whole rows or columns; name its corners, such as A3:C12")
    if last_column < first_column or last_row < first_row:
        raise refuse("is empty: its end is before its start")
    rows, columns = session.execute(
        select(func.max(SourceFileCell.row_number), func.max(SourceFileCell.column_number)).where(
            SourceFileCell.source_file_id == file_id, SourceFileCell.sheet_index == sheet_index
        )
    ).one()
    if rows is None or first_row > rows or first_column > columns:
        raise refuse(f"is outside the sheet, which holds cells up to row {rows or 0}")
    return CellRange(first_column, first_row, last_column, last_row)


def cell_rows(file_id: int, sheet_index: int, area: CellRange) -> Any:
    """The rows of ``area`` holding a cell, each its ``row_number`` and ``cells``: the cells by
    column number, each its ``text`` and ``kind`` (one statement over the staged cells)."""
    return (
        select(
            SourceFileCell.row_number.label("row_number"),
            func.jsonb_object_agg(
                SourceFileCell.column_number,
                func.jsonb_build_object("text", SourceFileCell.text, "kind", SourceFileCell.kind),
            ).label("cells"),
        )
        .where(
            SourceFileCell.source_file_id == file_id,
            SourceFileCell.sheet_index == sheet_index,
            SourceFileCell.row_number.between(area.first_row, area.last_row),
            SourceFileCell.column_number.between(area.first_column, area.last_column),
        )
        .group_by(SourceFileCell.row_number)
    )


class StagedFile:
    def __init__(self, session: Session, file_id: int) -> None:
        self.session = session
        self.file_id = file_id
        self.sheet_names = list(
            session.scalars(
                select(SourceFileSheet.name)
                .where(SourceFileSheet.source_file_id == file_id)
                .order_by(SourceFileSheet.sheet_index)
            )
        )

    def table(self, sheet: str | None, area: Area) -> Table | None:
        index = 0 if sheet is None else self.sheet_names.index(sheet)
        last_row, last_column = self._extent(index)
        if last_row is None or area.header_row > last_row:
            return None
        first = area.first_column or 1
        last = area.last_column or last_column
        until = min(area.last_row, last_row) if area.last_row else last_row
        header = [None] * (last - first + 1)
        for _number, cells in self._rows(index, area.header_row - 1, area.header_row, first, last):
            header = [header_cell(value) for value in cells]
        return Table(header, self._rows(index, area.header_row, until, first, last), first)

    def rows(self, sheet: str) -> Iterator[tuple[int, list[Any]]]:
        index = self.sheet_names.index(sheet)
        last_row, last_column = self._extent(index)
        if last_row is None:
            return iter(())
        return self._rows(index, 0, last_row, 1, last_column)

    def _extent(self, sheet: int) -> tuple[int | None, int | None]:
        """The sheet's last row and last column holding a cell."""
        last_row, last_column = self.session.execute(
            text(
                "SELECT max(row_number), max(column_number) FROM source_file_cells"
                " WHERE source_file_id = :file AND sheet_index = :sheet"
            ),
            {"file": self.file_id, "sheet": sheet},
        ).one()
        return last_row, last_column

    def _rows(
        self, sheet: int, after: int, until: int, first: int, last: int
    ) -> Iterator[tuple[int, list[Any]]]:
        """Each row with a cell between ``after`` (exclusive) and ``until``, padded to the area's
        width, read a window of rows at a time; each window is fetched whole, so the binding may
        write on the connection between rows."""
        width = last - first + 1
        start = after
        while start < until:
            end = min(start + WINDOW_ROWS, until)
            current: int | None = None
            cells: list[Any] = []
            for number, column, value in self.session.execute(
                text(_CELLS),
                {
                    "file": self.file_id,
                    "sheet": sheet,
                    "after": start,
                    "until": end,
                    "first": first,
                    "last": last,
                },
            ).all():
                if number != current:
                    if current is not None:
                        yield current, cells
                    current, cells = number, [None] * width
                cells[column - first] = unstaged(value)
            if current is not None:
                yield current, cells
            start = end

    def close(self) -> None:
        pass

