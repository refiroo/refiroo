"""Reading an import's file (INTEGRATION_API §J2, A-D10, D68).

A reader yields rows; nothing holds the file. XLSX through openpyxl's read-only mode, with each
formula's cached value, never the formula; CSV through the standard library, UTF-8 with or without a
byte order mark, RFC 4180 quoting, the profile's delimiter; JSON Lines line by line. A file the
reader cannot read is ``IMPORT_FILE_UNREADABLE`` with what failed and where.
"""

import csv
import json
import zipfile
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import Any, BinaryIO, Protocol

from openpyxl import load_workbook
from openpyxl.utils import column_index_from_string
from openpyxl.utils.exceptions import InvalidFileException

from ...errors import ApiError, api_error
from .cells import cell_text, decode_excel_text, is_empty

CSV_SHEET = "csv"
JSONL_SHEET = "jsonl"
# The hidden sheet a workbook for people carries its import profile on (0.9 J6, D185): A1 the
# mark, B1 what the workbook is (JSON), column A from row 2 the profile's JSON in pieces.
PROFILE_SHEET = "Import profile"
PROFILE_MARK = "rdm-engine import profile"


# What openpyxl raises on a workbook whose parts are damaged or shaped unexpectedly: a bad zip, an XML
# part that does not parse (``SyntaxError``), a missing part, a part of another shape.
_XLSX_ERRORS = (
    zipfile.BadZipFile,
    zipfile.LargeZipFile,
    InvalidFileException,
    KeyError,
    OSError,
    ValueError,
    SyntaxError,
    AttributeError,
    TypeError,
    IndexError,
    EOFError,
    NotImplementedError,
)


@dataclass(frozen=True)
class Area:
    """Where a table starts: its header row, and optionally its columns and last row."""

    header_row: int = 1
    first_column: int | None = None
    last_column: int | None = None
    last_row: int | None = None

    @classmethod
    def of(cls, header_row: int, block: Any | None) -> Area:
        if block is None:
            return cls(header_row)
        return cls(
            header_row,
            column_index_from_string(block.firstColumn),
            column_index_from_string(block.lastColumn),
            block.lastRow,
        )


@dataclass
class Table:
    """A table's header (the column names, ``None`` for an empty header cell) and its rows: the
    row's number in the sheet and its cells, empty rows left out."""

    header: list[str | None]
    rows: Iterator[tuple[int, list[Any]]]
    # The sheet column number of the table's first column, for a binding that names a letter (0.13 AQ).
    first_column: int = 1

    def columns(self) -> dict[str, int]:
        """Each named column's position. Of equal names the first has the name and each later one
        the name with its place among them, ``Currency #2``, unless a column is really called that."""
        positions: dict[str, int] = {}
        for index, name in enumerate(self.header):
            if name is not None:
                positions.setdefault(name, index)
        seen: dict[str, int] = {}
        for index, name in enumerate(self.header):
            if name is not None:
                seen[name] = seen.get(name, 0) + 1
                if seen[name] > 1:
                    positions.setdefault(f"{name} #{seen[name]}", index)
        return positions


class TabularFile(Protocol):
    sheet_names: list[str]

    def table(self, sheet: str | None, area: Area) -> Table | None:
        """The table at ``area`` of ``sheet`` (the first sheet when ``None``), or ``None`` when the
        sheet has no row at the header row."""
        ...

    def rows(self, sheet: str) -> Iterator[tuple[int, list[Any]]]:
        """Every row of ``sheet`` with its number, from the first, empty rows left out: what a
        source file's profile reads (0.10 A3), before any header is known."""
        ...

    def close(self) -> None: ...


def unreadable(message: str, **details: Any) -> ApiError:
    return api_error(422, "IMPORT_FILE_UNREADABLE", message, details or None)


class XlsxFile:
    def __init__(self, path: Path) -> None:
        # Opened as a file, not by name: openpyxl judges a name by its extension, and the stored
        # upload's is ``.source``.
        self._file = path.open("rb")
        try:
            self._book = load_workbook(self._file, read_only=True, data_only=True)
        except _XLSX_ERRORS as error:
            self._file.close()
            raise unreadable(
                f"The file is not an XLSX workbook that can be read ({type(error).__name__})"
            ) from None
        self.sheet_names = list(self._book.sheetnames)

    def table(self, sheet: str | None, area: Area) -> Table | None:
        name = sheet if sheet is not None else self.sheet_names[0]
        declared = self._book[name].max_column
        rows = _guarded(self._rows(name, area))
        try:
            header = list(next(rows))
        except StopIteration:
            return None
        # The table is as wide as the sheet declares, as before: a column whose heading is empty
        # still counts (a binding by letter names it), and a value in it is read, not cut off.
        if area.last_column is None and declared:
            header += [None] * (declared - (area.first_column or 1) + 1 - len(header))
        width = len(header)
        return Table(
            [header_cell(value) for value in header],
            _numbered(
                area.header_row,
                (_padded([_xlsx_cell(value) for value in row], width) for row in rows),
            ),
            area.first_column or 1,
        )

    def _rows(self, name: str, area: Area) -> Iterator[tuple[Any, ...]]:
        sheet = self._book[name]
        # A file declaring a wrong ``<dimension>`` is read to its end, not to the declared corner.
        sheet.reset_dimensions()
        return sheet.iter_rows(
            min_row=area.header_row,
            max_row=area.last_row,
            min_col=area.first_column,
            max_col=area.last_column,
            values_only=True,
        )

    def rows(self, sheet: str) -> Iterator[tuple[int, list[Any]]]:
        found = self._book[sheet]
        found.reset_dimensions()
        cells = _guarded(found.iter_rows(values_only=True))
        return _numbered(0, ([_xlsx_cell(value) for value in row] for row in cells))

    def close(self) -> None:
        self._book.close()
        self._file.close()


class CsvFile:
    def __init__(self, path: Path, delimiter: str) -> None:
        self.sheet_names = [CSV_SHEET]
        self.path = path
        self.delimiter = delimiter

    def table(self, sheet: str | None, area: Area) -> Table | None:
        lines = self._records()
        number = 0
        for number, record in enumerate(lines, start=1):
            if number == area.header_row:
                header = _cut(record, area)
                break
        else:
            return None
        width = len(header)
        rows = (
            _padded(_cut(record, area), width)
            for record in _until(lines, area.last_row - number if area.last_row else None)
        )
        return Table(
            [header_cell(value) for value in header],
            _numbered(number, rows),
            area.first_column or 1,
        )

    def rows(self, sheet: str) -> Iterator[tuple[int, list[Any]]]:
        return _numbered(0, self._records())

    def _records(self) -> Iterator[list[str]]:
        try:
            with self.path.open(encoding="utf-8-sig", newline="") as file:
                reader = csv.reader(file, delimiter=self.delimiter, strict=True)
                try:
                    yield from reader
                except csv.Error as error:
                    raise unreadable(
                        f"The CSV file breaks its quoting at line {reader.line_num}: {error}",
                        line=reader.line_num,
                    ) from None
        except UnicodeDecodeError as error:
            raise unreadable(
                f"The CSV file is not UTF-8 text (byte {error.start} cannot be read)"
            ) from None

    def close(self) -> None:
        pass


def jsonl_lines(path: Path) -> Iterator[tuple[int, Any]]:
    """Each line's number and its JSON value, blank lines left out; a line that is not JSON gives
    the ``ValueError`` in place of a value, for the line's own refusal."""
    try:
        with path.open(encoding="utf-8-sig") as file:
            for number, line in enumerate(file, start=1):
                if not line.strip():
                    continue
                try:
                    yield number, json.loads(line)
                except ValueError as error:
                    yield number, error
    except UnicodeDecodeError as error:
        raise unreadable(
            f"The JSON Lines file is not UTF-8 text (byte {error.start} cannot be read)"
        ) from None


def carried_profile(file: BinaryIO) -> tuple[dict[str, Any], Any] | None:
    """The description and import profile a workbook for people carries (0.9 J6, D185), or
    ``None`` for any other workbook; ``file`` is read from its start and left there."""
    file.seek(0)
    try:
        book = load_workbook(file, read_only=True, data_only=True)
    except _XLSX_ERRORS as error:
        raise unreadable(
            f"The file is not an XLSX workbook that can be read ({type(error).__name__})"
        ) from None
    try:
        if PROFILE_SHEET not in book.sheetnames:
            return None
        sheet = book[PROFILE_SHEET]
        sheet.reset_dimensions()
        rows = _guarded(sheet.iter_rows(max_col=2, values_only=True))
        first = next(rows, None)
        if not first or first[0] != PROFILE_MARK:
            return None
        pieces = "".join(str(row[0]) for row in rows if row and row[0] is not None)
        try:
            return json.loads(first[1] or "{}"), json.loads(pieces)
        except ValueError, TypeError:
            raise unreadable(
                f"The workbook's sheet '{PROFILE_SHEET}' does not hold an import profile that can "
                "be read; export the workbook again, or name a profile"
            ) from None
    finally:
        book.close()
        file.seek(0)


def open_tabular(path: Path, file_format: str, delimiter: str = ",") -> TabularFile:
    if file_format == "xlsx":
        return XlsxFile(path)
    return CsvFile(path, delimiter)


def header_cell(value: Any) -> str | None:
    """A header cell as a column name: trimmed text, ``None`` when empty."""
    if is_empty(value):
        return None
    text = cell_text(value).strip()
    return decode_excel_text(text) if isinstance(value, str) else text


def _guarded(rows: Iterator[tuple[Any, ...]]) -> Iterator[tuple[Any, ...]]:
    """A sheet's rows, a part that breaks while it is read refused as an unreadable file."""
    try:
        yield from rows
    except _XLSX_ERRORS as error:
        raise unreadable(
            f"The XLSX workbook cannot be read to its end ({type(error).__name__})"
        ) from None


def _padded(row: list[Any], width: int) -> list[Any]:
    """``row`` filled with empty cells up to ``width``: a row that ends at its last filled cell, or
    a CSV record shorter than its header, still has every column."""
    if len(row) < width:
        row.extend([None] * (width - len(row)))
    return row


def _xlsx_cell(value: Any) -> Any:
    return decode_excel_text(value) if isinstance(value, str) else value


def _cut(record: list[str], area: Area) -> list[str]:
    if area.first_column is None:
        return record
    return record[area.first_column - 1 : area.last_column]


def _until(records: Iterator[list[str]], count: int | None) -> Iterator[list[str]]:
    if count is None:
        yield from records
        return
    for index, record in enumerate(records):
        if index >= count:
            return
        yield record


def _numbered(header_row: int, rows: Any) -> Iterator[tuple[int, list[Any]]]:
    for number, row in enumerate(rows, start=header_row + 1):
        if any(not is_empty(value) for value in row):
            yield number, list(row)
