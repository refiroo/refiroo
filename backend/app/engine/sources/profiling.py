"""A source file's profile (Product 0.10 A3, D66, D68–D70): its sheets, header rows, blocks and
column statistics.

The ``profile`` job reads the file once through the import readers and stages every filled cell in
``source_file_cells`` by ``COPY`` (``values.py`` says how a cell is kept). Everything after that is a
statement over the staged cells (principle 6):

- **Blocks** (D68) are runs of columns holding a cell, separated by columns with none. A block's
  **header row** is the first row whose cells in the block are all text, fill every column of the
  block and are followed by a row filled only in those columns. When a sheet has several blocks
  and one row is such a header for each of them, that row is every block's header, so a title,
  section or group row above a one-column block is not taken for its header. Without such a row
  (a header with an empty cell), the text row with the most cells is the header, the first of
  equals; a block without a text row above another row has none. Colour and
  formatting are not read.
- **Columns**, per block over the rows below its header: ``filled``, ``distinct``,
  ``valueTypes`` (cells readable as each value type the attribute registry converts),
  ``candidateKey`` (filled on every row, no value twice), ``values`` (the most frequent, with
  their counts, 0.10 A6), ``delimiters`` (``;``, ``,``, ``|``,
  ``/`` and line breaks, with the share of cells holding one), ``placeholders`` (D70) and
  ``overlaps``: the columns, and with a workspace named the record names and unique text
  attributes of the model's types, holding the most of the column's distinct values (D69).

Overlaps compare at most :data:`OVERLAP_VALUES` distinct values per column, the first in text
order, and list the best :data:`OVERLAPS_LISTED`; placeholders list at most
:data:`PLACEHOLDERS_LISTED`. The limits are in each column's statistics.
"""

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from openpyxl.utils import get_column_letter
from sqlalchemy import delete, insert, select, text
from sqlalchemy.orm import Session

from ...errors import api_error
from ...models.database import (
    ModelDraft,
    SourceFile,
    SourceFileCell,
    SourceFileColumn,
    SourceFileSheet,
)
from ...models.schema import EngineModel
from ..imports.readers import CSV_SHEET, PROFILE_SHEET, open_tabular
from ..model.compiler import compile_authored_model
from ..model.registry import resolve_model_snapshot
from .values import staged

# Cells written per round of COPY, and read between cancel checks.
CHUNK_CELLS = 20_000
# Rows of a block looked at for its header row.
HEADER_ROWS = 50
OVERLAP_VALUES = 1_000
OVERLAPS_LISTED = 5
PLACEHOLDERS_LISTED = 10
# A column's most frequent values listed with their counts (0.10 A6).
VALUES_LISTED = 10
# D70: values that stand for "no value", ignoring case; and a value of at most two characters,
# none a letter or digit, found in at least this share of a column's cells.
PLACEHOLDER_VALUES = ("n/a", "na", "-", "--", "?", "tbd", "none")
PLACEHOLDER_SHARE = 0.01
DELIMITERS = (";", ",", "|", "/", "\n")


# Each profiled column with its block's header and last row.
_COLUMNS_TABLE = (
    "CREATE TEMPORARY TABLE profile_columns (sheet_index integer, column_number integer,"
    " block_index integer, header_row integer, last_row integer, rows integer) ON COMMIT DROP"
)


@dataclass(frozen=True)
class BlockLayout:
    first_column: int
    last_column: int
    header_row: int | None
    last_row: int

    def describe(self, index: int, data_rows: int) -> dict[str, Any]:
        first, last = get_column_letter(self.first_column), get_column_letter(self.last_column)
        top = self.header_row or 1
        return {
            "index": index,
            "range": f"{first}{top}:{last}{self.last_row}",
            "firstColumn": first,
            "lastColumn": last,
            "headerRow": self.header_row,
            "lastRow": self.last_row,
            "rows": data_rows,
        }


def profile_source_file(
    session: Session, source_file_id: str, path: Path, check: Callable[[], None]
) -> None:
    """Stage the file's cells and store its profile; the caller commits. ``check`` is called
    every :data:`CHUNK_CELLS` cells read and raises to stop."""
    source = session.scalar(
        select(SourceFile).where(SourceFile.public_id == source_file_id).with_for_update()
    )
    if source is None:
        raise api_error(
            404,
            "SOURCE_FILE_NOT_FOUND",
            f"Source file '{source_file_id}' was deleted before it was profiled",
        )
    if not path.is_file():
        raise api_error(
            410,
            "SOURCE_FILE_MISSING",
            f"The file of source file '{source_file_id}' is no longer in the job file directory; "
            "upload it again. Operators: check JOB_FILE_DIR and what removes files from it",
        )
    for table in (SourceFileColumn, SourceFileSheet, SourceFileCell):
        session.execute(delete(table).where(table.source_file_id == source.id))
    names = _stage(session, source, path, check)
    # Cells staged by COPY have no statistics yet; without them the statements over them (the
    # profile's, an inference's joins between columns) are planned as for an empty table (0.10 A6).
    session.execute(text("ANALYZE source_file_cells"))
    session.execute(text(_COLUMNS_TABLE))
    for sheet_index, name in enumerate(names):
        layouts = _layouts(session, source.id, sheet_index)
        blocks = []
        for block_index, layout in enumerate(layouts):
            rows = _data_rows(session, source.id, sheet_index, layout)
            blocks.append(layout.describe(block_index, rows))
            session.execute(
                text(
                    "INSERT INTO profile_columns SELECT :sheet, n, :block, :header, :last, :rows"
                    " FROM generate_series(CAST(:first AS integer), CAST(:final AS integer)) n"
                ),
                {
                    "sheet": sheet_index,
                    "block": block_index,
                    "header": layout.header_row or 0,
                    "last": layout.last_row,
                    "rows": rows,
                    "first": layout.first_column,
                    "final": layout.last_column,
                },
            )
        filled_rows = session.scalar(
            select(text("count(DISTINCT row_number)"))
            .select_from(SourceFileCell)
            .where(
                SourceFileCell.source_file_id == source.id,
                SourceFileCell.sheet_index == sheet_index,
            )
        )
        session.execute(
            insert(SourceFileSheet).values(
                source_file_id=source.id,
                sheet_index=sheet_index,
                name=name,
                profile={
                    "rows": filled_rows,
                    "headerRow": blocks[0]["headerRow"] if blocks else None,
                    "blocks": blocks,
                },
            )
        )
    _store_columns(session, source, _model_for(session, source))


def _stage(session: Session, source: SourceFile, path: Path, check: Callable[[], None]) -> list[str]:
    """Every filled cell of every sheet into ``source_file_cells``; the sheets' names. A
    workbook's import profile sheet (0.9 J6) is not data and is left out."""
    book = open_tabular(path, source.format, source.csv_delimiter or ",")
    statement = (
        "COPY source_file_cells (source_file_id, sheet_index, row_number, column_number, kind,"
        " text, value) FROM STDIN"
    )
    connection = session.connection().connection.driver_connection
    names: list[str] = []
    try:
        sheets = (
            [CSV_SHEET]
            if source.format == "csv"
            else [name for name in book.sheet_names if name != PROFILE_SHEET]
        )
        pending: list[tuple[Any, ...]] = []

        def flush() -> None:
            if pending:
                with connection.cursor() as cursor, cursor.copy(statement) as copy:
                    for row in pending:
                        copy.write_row(row)
                pending.clear()
                check()

        for sheet_index, name in enumerate(sheets):
            names.append(name)
            for row_number, cells in book.rows(name):
                for column_number, raw in enumerate(cells, start=1):
                    cell = staged(raw)
                    if cell is not None:
                        pending.append((source.id, sheet_index, row_number, column_number, *cell))
                if len(pending) >= CHUNK_CELLS:
                    flush()
        flush()
    finally:
        book.close()
    return names


def _layouts(session: Session, file_id: int, sheet_index: int) -> list[BlockLayout]:
    """The sheet's blocks with their header rows (D68)."""
    columns = list(
        session.execute(
            text(
                "SELECT column_number, max(row_number) FROM source_file_cells"
                " WHERE source_file_id = :file AND sheet_index = :sheet"
                " GROUP BY column_number ORDER BY column_number"
            ),
            {"file": file_id, "sheet": sheet_index},
        ).all()
    )
    spans: list[list[tuple[int, int]]] = []
    for column, last in columns:
        if spans and spans[-1][-1][0] == column - 1:
            spans[-1].append((column, last))
        else:
            spans.append([(column, last)])
    heads = [
        _head_rows(session, file_id, sheet_index, span[0][0], span[-1][0]) for span in spans
    ]
    headers = find_headers(
        [(span[0][0], span[-1][0]) for span in spans], heads
    )
    return [
        BlockLayout(span[0][0], span[-1][0], header, max(last for _c, last in span))
        for span, header in zip(spans, headers, strict=True)
    ]


Row = tuple[int, frozenset[int], bool]


def _head_rows(
    session: Session, file_id: int, sheet_index: int, first: int, last: int
) -> list[Row]:
    """A block's first rows: each row's number, its filled columns and whether all are text."""
    return [
        (number, frozenset(found), all_text)
        for number, found, all_text in session.execute(
            text(
                "SELECT row_number, array_agg(column_number), bool_and(kind = 'text')"
                " FROM source_file_cells WHERE source_file_id = :file AND sheet_index = :sheet"
                " AND column_number BETWEEN :first AND :last"
                " GROUP BY row_number ORDER BY row_number LIMIT :rows"
            ),
            {"file": file_id, "sheet": sheet_index, "first": first, "last": last, "rows": HEADER_ROWS},
        ).all()
    ]


def find_headers(
    blocks: Sequence[tuple[int, int]], heads: Sequence[Sequence[Row]]
) -> list[int | None]:
    """Each block's header row (D68): a row shared by every block when the sheet has several and
    one fits them all, otherwise each block's own."""
    full = [
        {number for number, _c, _t in rows if _header(rows, number, set(range(a, b + 1)))}
        for (a, b), rows in zip(blocks, heads, strict=True)
    ]
    if len(blocks) > 1:
        shared = set.intersection(*full)
        if shared:
            row = min(shared)
            return [row] * len(blocks)
    found: list[int | None] = []
    for rows, candidates in zip(heads, full, strict=True):
        if candidates:
            found.append(min(candidates))
            continue
        # A header with an empty cell: the text row with the most cells, the first of equals.
        loose = [
            (-len(columns), number)
            for position, (number, columns, all_text) in enumerate(rows)
            if all_text and position + 1 < len(rows)
        ]
        found.append(min(loose)[1] if loose else None)
    return found


def _header(rows: Sequence[Row], number: int, width: set[int]) -> bool:
    """Whether row ``number`` can be a header: all text, filling ``width``, and the next row
    filled only in its columns."""
    position = next(index for index, row in enumerate(rows) if row[0] == number)
    _n, columns, all_text = rows[position]
    if not all_text or columns != width:
        return False
    if position + 1 >= len(rows):
        return False
    return rows[position + 1][1] <= columns


def _data_rows(session: Session, file_id: int, sheet_index: int, layout: BlockLayout) -> int:
    return session.scalar(
        text(
            "SELECT count(DISTINCT row_number) FROM source_file_cells"
            " WHERE source_file_id = :file AND sheet_index = :sheet"
            " AND column_number BETWEEN :first AND :last AND row_number > :header"
        ),
        {
            "file": file_id,
            "sheet": sheet_index,
            "first": layout.first_column,
            "last": layout.last_column,
            "header": layout.header_row or 0,
        },
    )


# Each column's statistics over the rows below its block's header (D68–D70), as JSON.
_STATISTICS = """
WITH data AS (
    SELECT p.sheet_index, p.column_number, p.rows, c.kind, c.text, c.value
    FROM profile_columns p
    JOIN source_file_cells c ON c.source_file_id = :file AND c.sheet_index = p.sheet_index
        AND c.column_number = p.column_number AND c.row_number > p.header_row
),
basic AS (
    SELECT sheet_index, column_number, min(rows) AS rows, count(*) AS filled,
        count(DISTINCT text) AS distinct_values,
        count(*) FILTER (WHERE kind = 'integer'
            OR CASE WHEN kind = 'decimal' THEN (value #>> '{}')::numeric
                = trunc((value #>> '{}')::numeric) ELSE false END
            OR (kind = 'text' AND text ~ '^\\s*[+-]?\\d+\\s*$')) AS integer_cells,
        count(*) FILTER (WHERE kind IN ('integer', 'decimal')
            OR (kind = 'text' AND text ~ '^\\s*[+-]?(\\d+\\.?\\d*|\\.\\d+)([eE][+-]?\\d+)?\\s*$'))
            AS decimal_cells,
        count(*) FILTER (WHERE kind = 'boolean'
            OR (kind = 'text' AND lower(btrim(text)) IN ('true', 'false'))) AS boolean_cells,
        count(*) FILTER (WHERE kind = 'date'
            OR (kind = 'text' AND text ~ '^\\s*\\d{4}-\\d{2}-\\d{2}\\s*$')) AS date_cells,
        count(*) FILTER (WHERE kind IN ('date', 'dateTime')
            OR (kind = 'text' AND text ~ '^\\s*\\d{4}-\\d{2}-\\d{2}([T ]\\d{2}:\\d{2}.*)?$'))
            AS datetime_cells,
        count(*) FILTER (WHERE kind = 'text' AND strpos(text, ';') > 0) AS d_semicolon,
        count(*) FILTER (WHERE kind = 'text' AND strpos(text, ',') > 0) AS d_comma,
        count(*) FILTER (WHERE kind = 'text' AND strpos(text, '|') > 0) AS d_bar,
        count(*) FILTER (WHERE kind = 'text' AND strpos(text, '/') > 0) AS d_slash,
        count(*) FILTER (WHERE kind = 'text' AND strpos(text, E'\\n') > 0) AS d_newline
    FROM data GROUP BY sheet_index, column_number
),
placeholders AS (
    SELECT sheet_index, column_number,
        json_agg(json_build_object('value', text, 'count', n) ORDER BY n DESC, text) AS found
    FROM (
        SELECT d.sheet_index, d.column_number, d.text, count(*) AS n,
            row_number() OVER (PARTITION BY d.sheet_index, d.column_number
                               ORDER BY count(*) DESC, d.text) AS rank
        FROM data d
        WHERE d.kind = 'text'
        GROUP BY d.sheet_index, d.column_number, d.text
        HAVING lower(btrim(d.text)) = ANY(:placeholders)
            OR (char_length(btrim(d.text)) <= 2 AND btrim(d.text) !~ '[[:alnum:]]'
                AND count(*) >= :share * (SELECT count(*) FROM data e
                    WHERE e.sheet_index = d.sheet_index AND e.column_number = d.column_number))
    ) ranked
    WHERE rank <= :listed_placeholders
    GROUP BY sheet_index, column_number
),
frequent AS (
    SELECT sheet_index, column_number,
        json_agg(json_build_object('value', text, 'count', n) ORDER BY n DESC, text) AS found
    FROM (
        SELECT sheet_index, column_number, text, count(*) AS n,
            row_number() OVER (PARTITION BY sheet_index, column_number
                               ORDER BY count(*) DESC, text) AS rank
        FROM data GROUP BY sheet_index, column_number, text
    ) ranked
    WHERE rank <= :listed_values
    GROUP BY sheet_index, column_number
)
SELECT b.*, p.found AS placeholders, f.found AS frequent, h.text AS header
FROM basic b
LEFT JOIN placeholders p USING (sheet_index, column_number)
LEFT JOIN frequent f USING (sheet_index, column_number)
LEFT JOIN profile_columns pc USING (sheet_index, column_number)
LEFT JOIN source_file_cells h ON h.source_file_id = :file AND h.sheet_index = b.sheet_index
    AND h.column_number = b.column_number AND h.row_number = pc.header_row
"""

_VALUES = """
CREATE TEMPORARY TABLE profile_values ON COMMIT DROP AS
SELECT sheet_index, column_number, text FROM (
    SELECT sheet_index, column_number, text,
        row_number() OVER (PARTITION BY sheet_index, column_number ORDER BY text) AS rank
    FROM (
        SELECT DISTINCT c.sheet_index, c.column_number, c.text
        FROM profile_columns p
        JOIN source_file_cells c ON c.source_file_id = :file AND c.sheet_index = p.sheet_index
            AND c.column_number = p.column_number AND c.row_number > p.header_row
    ) found
) ranked
WHERE rank <= :values
"""

_COLUMN_OVERLAPS = """
SELECT a.sheet_index, a.column_number, b.sheet_index, b.column_number, count(*)
FROM profile_values a
JOIN profile_values b ON b.text = a.text
    AND (b.sheet_index, b.column_number) <> (a.sheet_index, a.column_number)
GROUP BY a.sheet_index, a.column_number, b.sheet_index, b.column_number
"""

_NAME_OVERLAPS = """
SELECT v.sheet_index, v.column_number, o.object_type_key, count(DISTINCT v.text)
FROM profile_values v
JOIN objects o ON o.workspace_key = :workspace AND o.object_type_key = ANY(:types)
    AND o.name = v.text
GROUP BY v.sheet_index, v.column_number, o.object_type_key
"""

_ATTRIBUTE_OVERLAPS = """
SELECT v.sheet_index, v.column_number, o.object_type_key, a.attribute_type_key,
    count(DISTINCT v.text)
FROM profile_values v
JOIN attribute_values a ON a.attribute_type_key = ANY(:attributes) AND a.text_value = v.text
JOIN objects o ON o.id = a.object_id AND o.workspace_key = :workspace
GROUP BY v.sheet_index, v.column_number, o.object_type_key, a.attribute_type_key
"""


def _store_columns(session: Session, source: SourceFile, model: EngineModel | None) -> None:
    parameters = {"file": source.id}
    columns = {
        (row.sheet_index, row.column_number): row
        for row in session.execute(
            text(_STATISTICS),
            parameters
            | {
                "placeholders": list(PLACEHOLDER_VALUES),
                "share": PLACEHOLDER_SHARE,
                "listed_placeholders": PLACEHOLDERS_LISTED,
                "listed_values": VALUES_LISTED,
            },
        ).all()
    }
    layout = {
        (row.sheet_index, row.column_number): row
        for row in session.execute(text("SELECT * FROM profile_columns")).all()
    }
    session.execute(text(_VALUES), parameters | {"values": OVERLAP_VALUES})
    sampled = dict(
        session.execute(
            text(
                "SELECT sheet_index || ':' || column_number, count(*) FROM profile_values"
                " GROUP BY sheet_index, column_number"
            )
        ).all()
    )
    sheets = dict(
        session.execute(
            select(SourceFileSheet.sheet_index, SourceFileSheet.name).where(
                SourceFileSheet.source_file_id == source.id
            )
        ).all()
    )
    overlaps: dict[tuple[int, int], list[dict[str, Any]]] = {}

    def add(at: tuple[int, int], found: int, entry: dict[str, Any]) -> None:
        total = sampled.get(f"{at[0]}:{at[1]}") or 0
        if total and found:
            entry["values"] = found
            entry["share"] = round(found / total, 3)
            overlaps.setdefault(at, []).append(entry)

    for sheet_a, column_a, sheet_b, column_b, found in session.execute(text(_COLUMN_OVERLAPS)):
        other = columns.get((sheet_b, column_b))
        add(
            (sheet_a, column_a),
            found,
            {
                "sheet": sheets[sheet_b],
                "column": get_column_letter(column_b),
                "header": other.header if other is not None else None,
            },
        )
    if model is not None and source.workspace_key is not None:
        types = [item.key for item in model.objectTypes]
        for sheet, column, type_key, found in session.execute(
            text(_NAME_OVERLAPS), {"workspace": source.workspace_key, "types": types}
        ):
            add(
                (sheet, column),
                found,
                {"workspaceKey": source.workspace_key, "objectTypeKey": type_key, "field": "name"},
            )
        attributes = [
            item.key
            for item in model.attributeTypes
            if item.features.get("unique") and item.valueType in {"text", "longText"}
        ]
        if attributes:
            for sheet, column, type_key, attribute, found in session.execute(
                text(_ATTRIBUTE_OVERLAPS),
                {"workspace": source.workspace_key, "attributes": attributes},
            ):
                add(
                    (sheet, column),
                    found,
                    {
                        "workspaceKey": source.workspace_key,
                        "objectTypeKey": type_key,
                        "attributeTypeKey": attribute,
                    },
                )
    rows = []
    for at, row in sorted(columns.items()):
        place = layout[at]
        listed = sorted(
            overlaps.get(at, []), key=lambda entry: (-entry["share"], -entry["values"])
        )
        rows.append(
            {
                "source_file_id": source.id,
                "sheet_index": at[0],
                "column_number": at[1],
                "statistics": _statistics(row, place, listed),
            }
        )
    if rows:
        session.execute(insert(SourceFileColumn), rows)


def _statistics(row: Any, place: Any, overlaps: list[dict[str, Any]]) -> dict[str, Any]:
    filled = row.filled
    value_types = {
        name: count
        for name, count in (
            ("text", filled),
            ("integer", row.integer_cells),
            ("decimal", row.decimal_cells),
            ("boolean", row.boolean_cells),
            ("date", row.date_cells),
            ("dateTime", row.datetime_cells),
        )
        if count
    }
    delimiters = sorted(
        (
            {"character": character, "cells": count, "share": round(count / filled, 3)}
            for character, count in (
                (";", row.d_semicolon),
                (",", row.d_comma),
                ("|", row.d_bar),
                ("/", row.d_slash),
                ("\n", row.d_newline),
            )
            if count
        ),
        key=lambda entry: -entry["cells"],
    )
    return {
        "header": row.header,
        "letter": get_column_letter(row.column_number),
        "block": place.block_index,
        "rows": place.rows,
        "filled": filled,
        "distinct": row.distinct_values,
        "valueTypes": value_types,
        "candidateKey": filled == place.rows and row.distinct_values == filled,
        "delimiters": delimiters,
        "placeholders": row.placeholders or [],
        "values": row.frequent or [],
        "overlaps": overlaps[:OVERLAPS_LISTED],
        "limits": {
            "overlapValues": OVERLAP_VALUES,
            "overlapsListed": OVERLAPS_LISTED,
            "placeholdersListed": PLACEHOLDERS_LISTED,
            "valuesListed": VALUES_LISTED,
        },
    }


def _model_for(session: Session, source: SourceFile) -> EngineModel | None:
    """The model whose records a column is compared with (D69): a draft's own when it compiles,
    the active release's otherwise and for a profile's file."""
    if source.draft_id is not None:
        draft = session.get(ModelDraft, source.draft_id)
        if draft is not None:
            compiled = compile_authored_model(draft.model_json)
            if compiled.valid and compiled.model is not None:
                return compiled.model
    return resolve_model_snapshot(session).model
