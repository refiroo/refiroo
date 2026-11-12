"""Where a column joins another: whole-set join candidates (0.17 PL3b, PP-D8).

The canvas asks which column of a table the values of one column point at. Every row of both
columns is compared, in one statement over the staged cells (``source_file_cells``): for each
candidate column, how many of the dropped column's rows hold a value the candidate holds too. The
profile's stored overlaps (the first thousand distinct values) stay a hint and are not read here.
Values compare as an import matches names: the cell's text, trimmed. Two candidates that match
exactly as much are a tie, and nothing picks one: the answer says so and the client asks.
"""

from dataclasses import dataclass
from typing import Any

from openpyxl.utils import get_column_letter
from openpyxl.utils.cell import column_index_from_string
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from ...errors import api_error
from ...models.database import SourceFileSheet
from ...models.sources import JoinCandidatesRequest, JoinColumnRef
from ..imports.readers import Table
from ..model.drafts import load_draft
from .draft_profile import current_source
from .store import require_profile

_HEADERS = text(
    "SELECT column_number, btrim(text) FROM source_file_cells"
    " WHERE source_file_id = :file AND sheet_index = :sheet AND row_number = :header"
    " AND column_number BETWEEN :first AND :last AND btrim(text) <> ''"
)

_EXTENT = text(
    "SELECT max(column_number) FROM source_file_cells"
    " WHERE source_file_id = :file AND sheet_index = :sheet"
)

# The columns of the table, each with its rows, its distinct values, how many of the dropped
# column's distinct values it holds, and how many of the dropped column's rows those are.
_COMPARE = text("""
WITH mine AS (
    SELECT btrim(text) AS v, count(*) AS n FROM source_file_cells
    WHERE source_file_id = :file AND sheet_index = :s1 AND column_number = :c1
      AND row_number > :h1 AND (CAST(:l1 AS integer) IS NULL OR row_number <= :l1)
      AND btrim(text) <> ''
    GROUP BY 1),
theirs AS (
    SELECT column_number AS col, btrim(text) AS v, count(*) AS n FROM source_file_cells
    WHERE source_file_id = :file AND sheet_index = :s2
      AND row_number > :h2 AND (CAST(:l2 AS integer) IS NULL OR row_number <= :l2)
      AND column_number BETWEEN :f2 AND :t2
      AND (CAST(:c2 AS integer) IS NULL OR column_number = :c2)
      AND btrim(text) <> ''
    GROUP BY 1, 2)
SELECT t.col, sum(t.n)::integer AS rows, count(*)::integer AS distinct_values,
       count(m.v)::integer AS matched_values, coalesce(sum(m.n), 0)::integer AS matched_rows
FROM theirs t LEFT JOIN mine m ON m.v = t.v
GROUP BY t.col ORDER BY t.col
""")

_OWN = text(
    "SELECT coalesce(sum(n), 0)::integer, count(*)::integer FROM ("
    " SELECT count(*) AS n FROM source_file_cells"
    " WHERE source_file_id = :file AND sheet_index = :s1 AND column_number = :c1"
    " AND row_number > :h1 AND (CAST(:l1 AS integer) IS NULL OR row_number <= :l1)"
    " AND btrim(text) <> '' GROUP BY btrim(text)) d"
)


@dataclass
class _Table:
    sheet: str
    index: int
    header_row: int
    first: int
    last: int
    last_row: int | None
    headers: dict[int, str]

    def number_of(self, name: str) -> int | None:
        """The column's number by its header, a repeated header named as a source names it."""
        header = [self.headers.get(n) for n in range(self.first, self.last + 1)]
        position = Table(header, iter(())).columns().get(name)
        return None if position is None else self.first + position


def _table(session: Session, file_id: int, ref: JoinColumnRef) -> _Table:
    sheet = session.scalar(
        select(SourceFileSheet).where(
            SourceFileSheet.source_file_id == file_id, SourceFileSheet.name == ref.sheet
        )
    )
    if sheet is None:
        raise api_error(
            404,
            "SOURCE_SHEET_NOT_FOUND",
            f"The source file has no sheet '{ref.sheet}'",
            {"sheet": ref.sheet},
        )
    header_row = ref.headerRow or (sheet.profile or {}).get("headerRow") or 1
    block = ref.block
    extent = session.scalar(_EXTENT, {"file": file_id, "sheet": sheet.sheet_index}) or 0
    first = column_index_from_string(block.firstColumn) if block else 1
    last = column_index_from_string(block.lastColumn) if block else extent
    if last < first:
        raise api_error(
            422, "INVALID_RANGE", "The block's last column is before its first", {"path": "/block"}
        )
    found = session.execute(
        _HEADERS,
        {
            "file": file_id,
            "sheet": sheet.sheet_index,
            "header": header_row,
            "first": first,
            "last": last,
        },
    )
    headers = {number: value for number, value in found}
    return _Table(
        sheet.name,
        sheet.sheet_index,
        header_row,
        first,
        last,
        block.lastRow if block else None,
        headers,
    )


def _column_number(table: _Table, ref: JoinColumnRef, where: str) -> int | None:
    if ref.letter is not None:
        number = column_index_from_string(ref.letter)
        if not table.first <= number <= table.last:
            raise api_error(
                422,
                "COLUMN_NOT_FOUND",
                f"Sheet '{table.sheet}' has no column {ref.letter} in the table",
                {"path": where},
            )
        return number
    if ref.column is None:
        return None
    number = table.number_of(ref.column)
    if number is None:
        raise api_error(
            422,
            "COLUMN_NOT_FOUND",
            f"Header row {table.header_row} of sheet '{table.sheet}' has no column '{ref.column}'",
            {"path": where},
        )
    return number


def join_candidates(
    session: Session, draft_id: str, request: JoinCandidatesRequest
) -> dict[str, Any]:
    """The columns of the ``against`` table that the dropped column's values point at, each with
    the figures over every row; refused ``404 SOURCE_FILE_NOT_FOUND``, ``409
    SOURCE_FILE_PROFILE_NOT_READY``, ``404 SOURCE_SHEET_NOT_FOUND``, ``422 COLUMN_NOT_FOUND``,
    ``422 INVALID_RANGE``."""
    draft = load_draft(session, draft_id)
    source = current_source(session, draft)
    if source is None:
        raise api_error(
            404, "SOURCE_FILE_NOT_FOUND", f"Model draft '{draft_id}' has no source file"
        )
    require_profile(session, source)
    mine = _table(session, source.id, request.column)
    theirs = _table(session, source.id, request.against)
    own = _column_number(mine, request.column, "/column")
    named = _column_number(theirs, request.against, "/against")
    if own is None:
        raise api_error(422, "COLUMN_NOT_FOUND", "Name the dropped column", {"path": "/column"})
    own_args = {
        "file": source.id,
        "s1": mine.index,
        "c1": own,
        "h1": mine.header_row,
        "l1": mine.last_row,
    }
    rows, distinct = session.execute(_OWN, own_args).one()
    found = session.execute(
        _COMPARE,
        {
            **own_args,
            "s2": theirs.index,
            "h2": theirs.header_row,
            "l2": theirs.last_row,
            "f2": theirs.first,
            "t2": theirs.last,
            "c2": named,
        },
    ).all()
    # Without a named column, the dropped column is no candidate for itself.
    own_place = named is None and theirs.index == mine.index
    candidates = [
        {
            "number": row.col,
            "sheet": theirs.sheet,
            "letter": get_column_letter(row.col),
            "header": theirs.headers.get(row.col),
            "rows": row.rows,
            "distinct": row.distinct_values,
            "matchedValues": row.matched_values,
            "matchedRows": row.matched_rows,
            "share": round(row.matched_rows / rows, 4) if rows else 0.0,
            "unique": row.rows == row.distinct_values,
        }
        for row in found
        if (named is not None or row.matched_values > 0) and not (own_place and row.col == own)
    ]
    candidates.sort(key=lambda c: (-c["matchedRows"], -c["matchedValues"], c["number"]))
    top = (
        [
            c
            for c in candidates
            if c["matchedValues"] > 0
            and (c["matchedRows"], c["matchedValues"])
            == (candidates[0]["matchedRows"], candidates[0]["matchedValues"])
        ]
        if candidates
        else []
    )
    for candidate in candidates:
        del candidate["number"]
    return {
        "column": {
            "sheet": mine.sheet,
            "letter": get_column_letter(own),
            "header": mine.headers.get(own),
            "rows": rows,
            "distinct": distinct,
        },
        "candidates": candidates,
        "best": top[0]["letter"] if len(top) == 1 else None,
        "tie": len(top) > 1,
        "tied": [c["letter"] for c in top] if len(top) > 1 else [],
    }
