"""Cells of a workbook that no source of a design reads (Product 0.16 AP13, found on the real walk-through).

A design can load cleanly and still leave a column of a table behind: a column whose header is empty
under the header row a second source reads, or a block that stops short of the table's last row. The
profile names columns by their header, so a cell no source binds is silently not loaded. This reads
the staged cells of the file in PostgreSQL (no cell comes into Python) and reports, per sheet, the
filled cells inside a table the design reads that no source's bound column covers. It knows no file,
sheet or name.
"""

from typing import Any

from openpyxl.utils import column_index_from_string, get_column_letter
from sqlalchemy import text
from sqlalchemy.orm import Session

from .sql import LAST_ROW

_SAMPLES = 3

_HEADERS = text(
    """
SELECT x.i, c.column_number, btrim(c.text) FROM unnest(CAST(:i AS int[]), CAST(:s AS int[]),
    CAST(:h AS int[]), CAST(:c1 AS int[]), CAST(:c2 AS int[])) AS x(i, s, h, c1, c2)
JOIN source_file_cells c ON c.source_file_id = :file AND c.sheet_index = x.s AND c.row_number = x.h
  AND c.column_number BETWEEN x.c1 AND x.c2 AND btrim(c.text) <> ''
"""
)

_LEFT = text(
    """
WITH t AS (SELECT * FROM unnest(CAST(:ts AS int[]), CAST(:tr1 AS int[]), CAST(:tr2 AS int[]),
        CAST(:tc1 AS int[]), CAST(:tc2 AS int[])) AS a(s, r1, r2, c1, c2)),
v AS (SELECT * FROM unnest(CAST(:vs AS int[]), CAST(:vr1 AS int[]), CAST(:vr2 AS int[]),
        CAST(:vc AS int[])) AS b(s, r1, r2, c)),
found AS (
    SELECT DISTINCT cell.sheet_index AS s, cell.row_number AS r, cell.column_number AS c
    FROM t JOIN source_file_cells cell ON cell.source_file_id = :file AND cell.sheet_index = t.s
      AND cell.row_number BETWEEN t.r1 AND t.r2 AND cell.column_number BETWEEN t.c1 AND t.c2
      AND btrim(cell.text) <> ''
    WHERE EXISTS (SELECT 1 FROM v WHERE v.s = t.s AND v.c BETWEEN t.c1 AND t.c2
                  AND v.r1 <= t.r2 AND v.r2 >= t.r1)
      AND NOT EXISTS (SELECT 1 FROM v WHERE v.s = cell.sheet_index AND v.c = cell.column_number
                      AND cell.row_number BETWEEN v.r1 AND v.r2))
SELECT s, count(*), (array_agg(r ORDER BY r, c))[1:3], (array_agg(c ORDER BY r, c))[1:3]
FROM found GROUP BY s ORDER BY s
"""
)


def _bound(source: dict[str, Any]) -> tuple[set[str], set[int]]:
    """The headers a source's bindings (and its key) read and the column numbers its bindings name by
    letter (0.13 AQ); a column it ignores is left out on purpose."""
    names: set[str] = set()
    numbers: set[int] = set()
    for column in source.get("columns") or []:
        if column.get("column"):
            names.add(column["column"])
        if column.get("letter"):
            numbers.add(column_index_from_string(column["letter"]))
        names.update(column.get("columns") or [])
    key = source.get("key") or {}
    names.update(key[part] for part in ("column", "nameColumn", "versionColumn") if key.get(part))
    return names, numbers


def cells_left_out(
    session: Session,
    *,
    file_id: int,
    tables: list[dict[str, Any]],
    profile: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    """``[{sheet, count, cells}]``: the filled cells of the tables the profile reads that no source
    covers, with the first three as ``C41``. A source covers the rows below its header row, down to
    its block's last row, in the columns whose header (the cell on its header row) it binds."""
    index = {
        table["sheet"]: table["place"]["sheetIndex"]
        for table in tables
        if "sheetIndex" in (table.get("place") or {})
    }
    sources = []
    for source in (profile or {}).get("sources") or []:
        sheet = index.get(source.get("sheet"))
        if sheet is None:
            continue
        block = source.get("block") or {}
        sources.append(
            (
                sheet,
                source.get("headerRow") or 1,
                block.get("lastRow") or LAST_ROW,
                column_index_from_string(block.get("firstColumn") or "A"),
                column_index_from_string(block.get("lastColumn") or "XFD"),
                *_bound(source),
            )
        )
    if not sources:
        return []
    headers: dict[int, list[tuple[int, str]]] = {}
    for found, number, header in session.execute(
        _HEADERS,
        {
            "file": file_id,
            "i": list(range(len(sources))),
            "s": [s[0] for s in sources],
            "h": [s[1] for s in sources],
            "c1": [s[3] for s in sources],
            "c2": [s[4] for s in sources],
        },
    ):
        headers.setdefault(found, []).append((number, header))
    covers = [
        (sheet, header_row, last, number)
        for at, (sheet, header_row, last, _, _, names, lettered) in enumerate(sources)
        for number, header in headers.get(at, [])
        if header in names and number not in lettered
    ]
    # A column named by its letter is covered whatever its header cell holds, empty or not.
    covers += [
        (sheet, header_row, last, number)
        for sheet, header_row, last, first, final, _, lettered in sources
        for number in sorted(lettered)
        if first <= number <= final
    ]
    shapes = []
    for table in tables:
        place = table.get("place") or {}
        numbers = [c["number"] for c in table.get("columns") or [] if "number" in c]
        if "sheetIndex" not in place or not numbers:
            continue
        shapes.append(
            (
                place["sheetIndex"],
                place.get("headerRow") or 1,
                place.get("lastRow") or LAST_ROW,
                min(numbers),
                max(numbers),
            )
        )
    if not covers or not shapes:
        return []
    names = {sheet: name for name, sheet in index.items()}
    return [
        {
            "sheet": names.get(sheet, ""),
            "count": count,
            "cells": [
                f"{get_column_letter(column)}{row}"
                for row, column in zip(rows, columns, strict=True)
            ],
        }
        for sheet, count, rows, columns in session.execute(
            _LEFT,
            {
                "file": file_id,
                "ts": [s[0] for s in shapes],
                "tr1": [s[1] for s in shapes],
                "tr2": [s[2] for s in shapes],
                "tc1": [s[3] for s in shapes],
                "tc2": [s[4] for s in shapes],
                "vs": [c[0] for c in covers],
                "vr1": [c[1] for c in covers],
                "vr2": [c[2] for c in covers],
                "vc": [c[3] for c in covers],
            },
        )
    ]
