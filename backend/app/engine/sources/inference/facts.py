"""What the table patterns read (Product 0.10 A6, D90): a workbook's sheets, each column's
statistics from its profile (A3), and the facts between columns, asked of the staged cells.

The rules (``patterns.py``) read a :class:`Workbook` of :class:`Table` objects and never the
database: :class:`StagedWorkbook` answers each question with one set statement over
``source_file_cells`` (D66), so a 10,000-row sheet is never loaded into Python (principle 6); a
test builds the same interface over rows it generates.

A sheet of one block is read whole. Of a sheet with several blocks, its **main block** is read when
one is clearly the table (:func:`main_block`: at least :data:`MAIN_COLUMNS` columns and
:data:`MAIN_SHARE` of the sheet's cells; reported by the user on a real workbook, 2026-10-14: a table
with a two-column note beside it proposed nothing); the other blocks are named in the inference's
warnings. A sheet laid out for reading (its profile's ``laidOut``, 0.10 A8a, D115) is read list by
list: each of its blocks is a :class:`BlockTable` of the workbook's ``blocks``.
"""

import json
import re
from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any, Protocol

from openpyxl.utils import column_index_from_string
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from ....models.database import SourceFile, SourceFileColumn, SourceFileSheet

# A list's table index (BlockTable.index): above every sheet's own.
BLOCK_INDEX = 100_000
# A sheet's main block: this many columns at least, and this share of the sheet's cells.
MAIN_COLUMNS = 3
MAIN_SHARE = 0.6

GUID = r"^\s*[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\s*$"
_GUID = re.compile(GUID)
# A column whose cells average more than this many characters holds sentences, not names.
PROSE_AVERAGE = 60


@dataclass(frozen=True)
class Column:
    """A column's statistics (A3's profile) and the facts of its own cells."""

    number: int
    letter: str
    header: str
    rows: int
    filled: int
    distinct: int
    value_types: dict[str, int]
    candidate_key: bool
    delimiters: tuple[dict[str, Any], ...] = ()
    placeholders: tuple[dict[str, Any], ...] = ()
    values: tuple[dict[str, Any], ...] = ()
    overlaps: tuple[dict[str, Any], ...] = ()
    # Cells holding white space, cells that are GUIDs, the longest cell's length and the average.
    spaced: int = 0
    guids: int = 0
    longest: int = 0
    average: float = 0.0

    def all(self, value_type: str) -> bool:
        """Whether every filled cell reads as ``value_type``."""
        return self.filled > 0 and self.value_types.get(value_type, 0) == self.filled

    @property
    def textual(self) -> bool:
        """Text that is not a number, a date or a GUID."""
        return (
            self.filled > 0
            and not self.all("decimal")
            and not self.all("date")
            and not self.all("dateTime")
            and self.guids < self.filled
        )

    @property
    def guid(self) -> bool:
        return self.filled > 0 and self.guids == self.filled

    @property
    def code_like(self) -> bool:
        """Short text without spaces holding a letter and a digit, as codes are."""
        if not self.textual or self.spaced or self.longest > 40:
            return False
        sample = [str(v["value"]) for v in self.values]
        return bool(sample) and all(
            re.search(r"[A-Za-z]", s) and re.search(r"\d", s) for s in sample
        )

    def value_type(self) -> str:
        """The value type every filled cell reads as, the narrowest first; text otherwise."""
        for name in ("integer", "decimal", "boolean", "date", "dateTime"):
            if self.all(name):
                return name
        return "longText" if self.longest > 255 or self.prose else "text"

    @property
    def prose(self) -> bool:
        """Sentences rather than names: text averaging more than 60 characters (decided 2026-10-14
        on the user's workbooks, where repeated descriptions were read as parents)."""
        return self.textual and self.average > PROSE_AVERAGE


class Table(Protocol):
    """A sheet: its columns, and the questions the rules ask of its rows."""

    name: str
    index: int
    header_row: int
    rows: int
    columns: Sequence[Column]

    def constant_within(self, group: int, others: Sequence[int]) -> dict[int, int]:
        """For each of ``others``, the values of ``group`` within whose rows it holds one value."""
        ...

    def pairs(self, first: int, second: int) -> int:
        """The distinct pairs of the two columns' values on rows where both are filled."""
        ...

    def names_per_code(self, code: int, name: int) -> list[dict[str, Any]]:
        """The codes with more than one name, each with its names and their counts."""
        ...

    def split_parts(self, column: int, delimiter: str) -> tuple[int, int]:
        """The parts of the cells holding ``delimiter``, and how many of them are found as a whole
        cell of the column."""
        ...

    def same(self, first: int, second: int) -> int:
        """The rows where both columns are filled and hold the same value."""
        ...

    def distinct_values(self, column: int, limit: int) -> list[dict[str, Any]] | None:
        """Every distinct value of the column with its count, most frequent first; ``None`` when it
        holds more than ``limit`` (0.10 A7: a description's type and target columns)."""
        ...

    def rows_of(self, columns: Sequence[int], limit: int) -> list[tuple[str | None, ...]] | None:
        """The columns' cells, row by row in sheet order, for rows holding one of them; ``None``
        when there are more than ``limit`` such rows (0.10 A7: a description's fields)."""
        ...


@dataclass
class BlockTable:
    """A list of a sheet laid out for reading (0.10 A8a): where it stands, the titles above it, its
    note (D119) and its columns' statistics over its rows."""

    name: str
    # Unique among the workbook's tables, so columns of two lists share attribute types (D98).
    index: int
    sheet_index: int
    block: int
    first_column: str
    last_column: str
    header_row: int
    last_row: int
    rows: int
    titles: tuple[str, ...] = ()
    note: dict[str, Any] | None = None
    columns: list[Column] = field(default_factory=list)

    @property
    def range(self) -> str:
        return f"{self.first_column}{self.header_row}:{self.last_column}{self.last_row}"

    def described(self) -> dict[str, Any]:
        return {
            "range": self.range,
            "firstColumn": self.first_column,
            "lastColumn": self.last_column,
            "headerRow": self.header_row,
            "lastRow": self.last_row,
            "rows": self.rows,
        }


class Workbook(Protocol):
    sheets: Sequence[Table]
    # Sheets of several blocks neither holding a table nor read list by list.
    skipped: Sequence[str]
    # The lists of sheets laid out for reading (0.10 A8a), and those sheets' names.
    blocks: Sequence[BlockTable]
    laid_out: Sequence[str]

    def common(self, first: tuple[int, int], second: tuple[int, int]) -> int:
        """The distinct values two columns (sheet index, column number) share."""
        ...


@dataclass
class StagedTable:
    session: Session
    file_id: int
    name: str
    index: int
    header_row: int
    rows: int
    columns: list[Column] = field(default_factory=list)
    # The import's block of a sheet's main block (``firstColumn``, ``lastColumn``); none for a sheet
    # of one block.
    block: dict[str, Any] | None = None

    def _parameters(self, **more: Any) -> dict[str, Any]:
        return {"file": self.file_id, "sheet": self.index, "header": self.header_row, **more}

    def constant_within(self, group: int, others: Sequence[int]) -> dict[int, int]:
        if not others:
            return {}
        found = self.session.execute(
            text(
                """
                WITH g AS (
                    SELECT row_number, text FROM source_file_cells
                    WHERE source_file_id = :file AND sheet_index = :sheet AND column_number = :group
                      AND row_number > :header),
                o AS (
                    SELECT row_number, column_number, text FROM source_file_cells
                    WHERE source_file_id = :file AND sheet_index = :sheet
                      AND column_number = ANY(:others) AND row_number > :header),
                per AS (
                    SELECT o.column_number, g.text, count(DISTINCT o.text) AS n
                    FROM g JOIN o USING (row_number) GROUP BY o.column_number, g.text)
                SELECT column_number, count(*) FILTER (WHERE n = 1) FROM per GROUP BY column_number
                """
            ),
            self._parameters(group=group, others=list(others)),
        )
        return {column: constant for column, constant in found}

    def pairs(self, first: int, second: int) -> int:
        return self.session.scalar(
            text(
                """
                SELECT count(DISTINCT (a.text, b.text)) FROM source_file_cells a
                JOIN source_file_cells b ON b.source_file_id = a.source_file_id
                    AND b.sheet_index = a.sheet_index AND b.row_number = a.row_number
                    AND b.column_number = :second
                WHERE a.source_file_id = :file AND a.sheet_index = :sheet
                  AND a.column_number = :first AND a.row_number > :header
                """
            ),
            self._parameters(first=first, second=second),
        )

    def names_per_code(self, code: int, name: int) -> list[dict[str, Any]]:
        found = self.session.execute(
            text(
                """
                WITH pairs AS (
                    SELECT a.text AS code, b.text AS name, count(*) AS n FROM source_file_cells a
                    JOIN source_file_cells b ON b.source_file_id = a.source_file_id
                        AND b.sheet_index = a.sheet_index AND b.row_number = a.row_number
                        AND b.column_number = :name
                    WHERE a.source_file_id = :file AND a.sheet_index = :sheet
                      AND a.column_number = :code AND a.row_number > :header
                    GROUP BY a.text, b.text)
                SELECT code, json_agg(json_build_object('value', name, 'count', n)
                                      ORDER BY n DESC, name)
                FROM pairs GROUP BY code HAVING count(*) > 1 ORDER BY code
                """
            ),
            self._parameters(code=code, name=name),
        )
        return [{"code": code_value, "names": names} for code_value, names in found]

    def split_parts(self, column: int, delimiter: str) -> tuple[int, int]:
        total, found = self.session.execute(
            text(
                """
                WITH c AS (
                    SELECT text FROM source_file_cells
                    WHERE source_file_id = :file AND sheet_index = :sheet AND column_number = :column
                      AND row_number > :header),
                whole AS (SELECT DISTINCT btrim(text) AS part FROM c WHERE strpos(text, :d) = 0),
                parts AS (
                    SELECT btrim(p) AS part FROM c, string_to_table(c.text, :d) AS p
                    WHERE strpos(c.text, :d) > 0 AND btrim(p) <> '')
                SELECT count(*), count(*) FILTER (WHERE part IN (SELECT part FROM whole)) FROM parts
                """
            ),
            self._parameters(column=column, d=delimiter),
        ).one()
        return total, found

    def same(self, first: int, second: int) -> int:
        return self.session.scalar(
            text(
                """
                SELECT count(*) FROM source_file_cells a
                JOIN source_file_cells b ON b.source_file_id = a.source_file_id
                    AND b.sheet_index = a.sheet_index AND b.row_number = a.row_number
                    AND b.column_number = :second
                WHERE a.source_file_id = :file AND a.sheet_index = :sheet
                  AND a.column_number = :first AND a.row_number > :header AND a.text = b.text
                """
            ),
            self._parameters(first=first, second=second),
        )

    def distinct_values(self, column: int, limit: int) -> list[dict[str, Any]] | None:
        found = self.session.execute(
            text(
                """
                SELECT text, count(*) AS n FROM source_file_cells
                WHERE source_file_id = :file AND sheet_index = :sheet AND column_number = :column
                  AND row_number > :header
                GROUP BY text ORDER BY n DESC, text LIMIT :limit
                """
            ),
            self._parameters(column=column, limit=limit + 1),
        ).all()
        if len(found) > limit:
            return None
        return [{"value": value, "count": count} for value, count in found]

    def rows_of(self, columns: Sequence[int], limit: int) -> list[tuple[str | None, ...]] | None:
        wanted = list(columns)
        found = self.session.execute(
            text(
                """
                SELECT row_number, json_object_agg(column_number, text) FROM source_file_cells
                WHERE source_file_id = :file AND sheet_index = :sheet
                  AND column_number = ANY(:columns) AND row_number > :header
                GROUP BY row_number ORDER BY row_number LIMIT :limit
                """
            ),
            self._parameters(columns=wanted, limit=limit + 1),
        ).all()
        if len(found) > limit:
            return None
        return [tuple(cells.get(str(number)) for number in wanted) for _, cells in found]


@dataclass
class StagedWorkbook:
    session: Session
    file_id: int
    sheets: list[StagedTable] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)
    blocks: list[BlockTable] = field(default_factory=list)
    laid_out: list[str] = field(default_factory=list)
    # Sheets read by their main block: (sheet, the block's range, the other blocks' ranges).
    partial: list[tuple[str, str, list[str]]] = field(default_factory=list)
    # Columns left out for a header an earlier column of the sheet has: (sheet, header, letter).
    repeated: list[tuple[str, str, str]] = field(default_factory=list)

    def common(self, first: tuple[int, int], second: tuple[int, int]) -> int:
        return self.session.scalar(
            text(
                """
                SELECT count(*) FROM (
                    SELECT DISTINCT a.text FROM source_file_cells a
                    WHERE a.source_file_id = :file AND a.sheet_index = :s1 AND a.column_number = :c1
                      AND a.row_number > :h1
                    INTERSECT
                    SELECT DISTINCT b.text FROM source_file_cells b
                    WHERE b.source_file_id = :file AND b.sheet_index = :s2 AND b.column_number = :c2
                      AND b.row_number > :h2) shared
                """
            ),
            {
                "file": self.file_id,
                "s1": first[0],
                "c1": first[1],
                "h1": self._header(first[0]),
                "s2": second[0],
                "c2": second[1],
                "h2": self._header(second[0]),
            },
        )

    def _header(self, sheet_index: int) -> int:
        return next(s.header_row for s in self.sheets if s.index == sheet_index)


def staged_workbook(session: Session, source: SourceFile) -> StagedWorkbook:
    """The file's sheets of one block with a header row, their columns' statistics and the facts
    of each column's own cells, read once."""
    workbook = StagedWorkbook(session, source.id)
    sheets = list(
        session.scalars(
            select(SourceFileSheet)
            .where(SourceFileSheet.source_file_id == source.id)
            .order_by(SourceFileSheet.sheet_index)
        )
    )
    columns: dict[int, list[tuple[int, dict[str, Any]]]] = {}
    for sheet_index, number, statistics in session.execute(
        select(
            SourceFileColumn.sheet_index, SourceFileColumn.column_number, SourceFileColumn.statistics
        )
        .where(SourceFileColumn.source_file_id == source.id)
        .order_by(
            SourceFileColumn.sheet_index, SourceFileColumn.block_index, SourceFileColumn.column_number
        )
    ):
        columns.setdefault(sheet_index, []).append((number, statistics))
    for sheet in sheets:
        profile = sheet.profile or {}
        blocks = profile.get("blocks") or []
        if profile.get("laidOut"):
            workbook.laid_out.append(sheet.name)
            workbook.blocks += block_tables(session, source.id, sheet, blocks, columns.get(sheet.sheet_index, []))
            continue
        chosen = 0 if len(blocks) == 1 else main_block(blocks)
        if chosen is None or not blocks[chosen].get("headerRow"):
            if blocks:
                workbook.skipped.append(sheet.name)
            continue
        main = blocks[chosen]
        if len(blocks) > 1:
            workbook.partial.append((sheet.name, main["range"], [b["range"] for b in blocks if b is not main]))
        header_row = main["headerRow"]
        facts = {
            number: (spaced, guids, longest, average)
            for number, spaced, guids, longest, average in session.execute(
                text(
                    """
                    SELECT column_number, count(*) FILTER (WHERE text ~ '\\s'),
                        count(*) FILTER (WHERE text ~ :guid), max(char_length(text)),
                        avg(char_length(text))
                    FROM source_file_cells
                    WHERE source_file_id = :file AND sheet_index = :sheet AND row_number > :header
                    GROUP BY column_number
                    """
                ),
                {"file": source.id, "sheet": sheet.sheet_index, "header": header_row, "guid": GUID},
            )
        }
        table = StagedTable(
            session,
            source.id,
            sheet.name,
            sheet.sheet_index,
            header_row,
            main.get("rows") or 0,
            block={"firstColumn": main["firstColumn"], "lastColumn": main["lastColumn"]} if len(blocks) > 1 else None,
        )
        seen: dict[str, str] = {}
        for number, statistics in columns.get(sheet.sheet_index, []):
            if statistics.get("block", 0) != chosen:
                continue
            header = statistics.get("header")
            if not isinstance(header, str) or not header.strip():
                continue
            # A column is bound by its header: a second column of the same header would take the
            # first's binding (found on a workbook repeating its headers per language).
            if header.strip() in seen:
                workbook.repeated.append((sheet.name, header.strip(), statistics.get("letter", "")))
                continue
            seen[header.strip()] = statistics.get("letter", "")
            spaced, guids, longest, average = facts.get(number, (0, 0, 0, 0))
            table.columns.append(column_of(number, statistics, spaced, guids, longest or 0, float(average or 0)))
        workbook.sheets.append(table)
    return workbook


def block_tables(
    session: Session,
    file_id: int,
    sheet: SourceFileSheet,
    blocks: Sequence[dict[str, Any]],
    columns: Sequence[tuple[int, dict[str, Any]]],
) -> list[BlockTable]:
    """The lists of a sheet laid out for reading, each with its columns and the facts of their
    cells over its rows, read by one statement (D115)."""
    facts = {
        (block, number): (spaced, guids, longest, average)
        for block, number, spaced, guids, longest, average in session.execute(
            text(
                """
                SELECT b.index, c.column_number, count(*) FILTER (WHERE c.text ~ '\\s'),
                    count(*) FILTER (WHERE c.text ~ :guid), max(char_length(c.text)),
                    avg(char_length(c.text))
                FROM jsonb_to_recordset(CAST(:blocks AS jsonb))
                    AS b(index integer, first integer, last integer, header integer, final integer,
                         note integer)
                JOIN source_file_cells c ON c.source_file_id = :file AND c.sheet_index = :sheet
                    AND c.column_number BETWEEN b.first AND b.last AND c.row_number > b.header
                    AND c.row_number <= b.final AND c.row_number <> b.note
                GROUP BY b.index, c.column_number
                """
            ),
            {
                "file": file_id,
                "sheet": sheet.sheet_index,
                "guid": GUID,
                "blocks": json.dumps(
                    [
                        {
                            "index": b["index"],
                            "first": column_index_from_string(b["firstColumn"]),
                            "last": column_index_from_string(b["lastColumn"]),
                            "header": b.get("headerRow") or 0,
                            "final": b["lastRow"],
                            "note": (b.get("note") or {}).get("row") or 0,
                        }
                        for b in blocks
                    ]
                ),
            },
        )
    }
    found = []
    for block in blocks:
        if not block.get("headerRow"):
            continue
        table = BlockTable(
            name=sheet.name,
            index=BLOCK_INDEX + sheet.sheet_index * BLOCK_INDEX + block["index"],
            sheet_index=sheet.sheet_index,
            block=block["index"],
            first_column=block["firstColumn"],
            last_column=block["lastColumn"],
            header_row=block["headerRow"],
            last_row=block["lastRow"],
            rows=block.get("rows") or 0,
            titles=tuple(block.get("titles") or ()),
            note=block.get("note"),
        )
        for number, statistics in columns:
            header = statistics.get("header")
            if statistics.get("block") != block["index"] or not isinstance(header, str) or not header.strip():
                continue
            spaced, guids, longest, average = facts.get((block["index"], number), (0, 0, 0, 0))
            table.columns.append(column_of(number, statistics, spaced, guids, longest or 0, float(average or 0)))
        found.append(table)
    return found


def main_block(blocks: Sequence[dict[str, Any]]) -> int | None:
    """The block that is clearly a sheet's table: the one with the most cells, at least
    :data:`MAIN_COLUMNS` columns wide and holding :data:`MAIN_SHARE` of the sheet's cells; ``None``
    for a sheet of lists side by side."""

    def width(block: dict[str, Any]) -> int:
        return column_index_from_string(block["lastColumn"]) - column_index_from_string(block["firstColumn"]) + 1

    cells = [width(b) * max(b.get("rows") or 0, 0) for b in blocks]
    total = sum(cells)
    if not total:
        return None
    best = max(range(len(blocks)), key=lambda index: cells[index])
    if width(blocks[best]) < MAIN_COLUMNS or cells[best] < MAIN_SHARE * total:
        return None
    return best


def column_of(
    number: int, statistics: dict[str, Any], spaced: int, guids: int, longest: int, average: float = 0.0
) -> Column:
    return Column(
        number=number,
        letter=statistics.get("letter", ""),
        header=statistics["header"].strip(),
        rows=statistics.get("rows", 0),
        filled=statistics.get("filled", 0),
        distinct=statistics.get("distinct", 0),
        value_types=dict(statistics.get("valueTypes") or {}),
        candidate_key=bool(statistics.get("candidateKey")),
        delimiters=tuple(statistics.get("delimiters") or ()),
        placeholders=tuple(statistics.get("placeholders") or ()),
        values=tuple(statistics.get("values") or ()),
        overlaps=tuple(statistics.get("overlaps") or ()),
        spaced=spaced,
        guids=guids,
        longest=longest,
        average=average,
    )


def is_guid(value: str) -> bool:
    return bool(_GUID.match(value))
