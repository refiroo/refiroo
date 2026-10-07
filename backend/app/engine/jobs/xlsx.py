"""A streaming XLSX writer for exports (Base 0.9 J1, D51).

An export's sheets can hold hundreds of thousands of rows, so the workbook is written as SpreadsheetML
straight into its ZIP container, row by row: inline strings, numbers, booleans and dates, never one
object per cell. Each data sheet holds one named table, whose header row is the column keys, under a
row of labels, with dropdown lists read from a hidden sheet. Values arrive as the canonical text the
API writes (PostgreSQL extracts them, as for CSV), and :func:`cell` decides how each becomes a cell,
so a machine reading the workbook gets back exactly the stored value.
"""

import re
import zipfile
from collections.abc import Callable, Iterable, Iterator, Sequence
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

# Excel holds a number exactly up to 15 significant digits; a value beyond is written as text.
EXCEL_DIGITS = 15
# A sheet holds 1,048,576 rows: a label row, the table's header and the rest for data.
SHEET_ROWS = 1_048_576 - 2
# Excel's day 0 for the 1900 date system, as the day number every date cell counts from.
_EPOCH = date(1899, 12, 30).toordinal()
# XML 1.0 cannot hold these characters; XLSX writes them as ``_xHHHH_``, which Excel reads back.
_XML_ILLEGAL = re.compile("[\x00-\x08\x0b\x0c\x0e-\x1f\ufffe\uffff]")
_XML_ESCAPE = re.compile(r"_(x[0-9A-Fa-f]{4})_")
_MARKUP = str.maketrans({"&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;"})
# Rows are joined and written in blocks of about this many characters.
_BLOCK = 1 << 20

_MAIN = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
_RELATIONSHIPS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
_PACKAGE = "http://schemas.openxmlformats.org/package/2006/relationships"
_TYPES = "http://schemas.openxmlformats.org/package/2006/content-types"
_DOCUMENT = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
_HEADER = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'


def xlsx_text(value: str) -> str:
    """Text as an XLSX cell holds it: characters XML cannot hold as ``_xHHHH_``, and a literal
    ``_xHHHH_`` escaped as ``_x005F_xHHHH_``, so Excel reads back exactly the text."""
    value = _XML_ESCAPE.sub(r"_x005F_\1_", value)
    return _XML_ILLEGAL.sub(lambda match: f"_x{ord(match.group()):04X}_", value)


def _escaped(value: str) -> str:
    return xlsx_text(value).translate(_MARKUP)


def text_cell(ref: str, value: str | None) -> str:
    """A text cell, never read as a number, a date or a formula."""
    if value is None:
        return ""
    return f'<c r="{ref}" t="inlineStr"><is><t xml:space="preserve">{_escaped(value)}</t></is></c>'


def number_cell(ref: str, value: int | str) -> str:
    return f'<c r="{ref}"><v>{value}</v></c>'


def cell(ref: str, value: str | None, value_type: str) -> str:
    """An attribute's canonical text as the cell a reader can trust: integers and decimals as numbers
    when Excel holds them exactly, otherwise as text; booleans as booleans; dates as date cells;
    date-times, JSON and text as text."""
    if value is None:
        return ""
    if value_type in {"integer", "decimal"}:
        return number_cell(ref, value) if _digits(value) <= EXCEL_DIGITS else text_cell(ref, value)
    if value_type == "boolean":
        return f'<c r="{ref}" t="b"><v>{1 if value == "true" else 0}</v></c>'
    if value_type == "date":
        return f'<c r="{ref}" s="1"><v>{date.fromisoformat(value).toordinal() - _EPOCH}</v></c>'
    return text_cell(ref, value)


def _digits(value: str) -> int:
    """Significant digits of a canonical number, which is what a double holds exactly up to 15 of:
    ``-0.00125`` has 3, ``1000`` has 1, ``1000000000000001`` has 16."""
    whole, _, fraction = value.lstrip("-").partition(".")
    return len((whole + fraction).strip("0"))


def column(index: int) -> str:
    """The letter of the 1-based column ``index``: 1 is A, 27 is AA."""
    letters = ""
    while index:
        index, rest = divmod(index - 1, 26)
        letters = chr(65 + rest) + letters
    return letters


@dataclass
class Sheet:
    """One data sheet's table: its keys and labels, how many rows it holds, the rows, how a row
    becomes its cells' XML at a row number (with :func:`cell` and friends), and its dropdown lists
    as (column letter, list range)."""

    title: str
    table: str
    keys: Sequence[str]
    labels: Sequence[str]
    count: int
    rows: Iterable[Sequence[object]]
    encode: Callable[[Sequence[object], int], str]
    lists: list[tuple[str, str]] = field(default_factory=list)


@dataclass
class _Written:
    title: str
    hidden: bool = False
    table: tuple[str, str, Sequence[str]] | None = None  # name, ref, keys


class Workbook:
    """Sheets written one after another into ``path``, then the parts that name them."""

    def __init__(self, path: Path, on_row: Callable[[], None]) -> None:
        self._zip = zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED, compresslevel=1)
        self._sheets: list[_Written] = []
        self._on_row = on_row

    def data(self, sheet: Sheet) -> None:
        """``sheet.rows`` on as many sheets as they need (continued as "Title 2" and so on)."""
        rows = iter(sheet.rows)
        pages = max(1, -(-sheet.count // SHEET_ROWS))
        for page in range(1, pages + 1):
            count = min(SHEET_ROWS, sheet.count - (page - 1) * SHEET_ROWS)
            title = sheet.title if page == 1 else f"{sheet.title} {page}"
            table = sheet.table if page == 1 else f"{sheet.table}_{page}"
            self._data_page(title, table, sheet, count, rows)

    def lists(self, columns: Sequence[Sequence[str]]) -> None:
        """The hidden sheet the dropdowns read: one column per list."""
        height = max((len(values) for values in columns), default=0)
        rows = (
            "".join(
                text_cell(f"{column(index)}{number}", values[number - 1])
                for index, values in enumerate(columns, 1)
                if number <= len(values)
            )
            for number in range(1, height + 1)
        )
        self._sheet("Lists", rows, hidden=True)

    def close(self) -> None:
        self._parts()
        self._zip.close()

    def _data_page(self, title: str, table: str, sheet: Sheet, count: int, rows: Iterator) -> None:
        last_column = column(len(sheet.keys))
        last_row = 2 + max(count, 1)
        letters = [column(index) for index in range(1, len(sheet.keys) + 1)]
        head = [
            "".join(text_cell(f"{letter}1", label) for letter, label in zip(letters, sheet.labels, strict=True)),
            "".join(text_cell(f"{letter}2", key) for letter, key in zip(letters, sheet.keys, strict=True)),
        ]

        def body() -> Iterator[str]:
            yield from head
            for number in range(3, 3 + count):
                yield sheet.encode(next(rows), number)
                self._on_row()

        validations = "".join(
            f'<dataValidation type="list" allowBlank="1" showErrorMessage="1" '
            f'sqref="{letter}3:{letter}{last_row}"><formula1>{source}</formula1></dataValidation>'
            for letter, source in sheet.lists
        )
        after = (
            (f'<dataValidations count="{len(sheet.lists)}">{validations}</dataValidations>' if validations else "")
            + '<tableParts count="1"><tablePart r:id="rId1"/></tableParts>'
        )
        ref = f"A2:{last_column}{last_row}"
        self._sheet(title, body(), dimension=f"A1:{last_column}{last_row}", frozen=True, after=after)
        self._sheets[-1].table = (table, ref, sheet.keys)

    def _sheet(
        self,
        title: str,
        rows: Iterable[str],
        *,
        hidden: bool = False,
        dimension: str | None = None,
        frozen: bool = False,
        after: str = "",
    ) -> None:
        number = len(self._sheets) + 1
        self._sheets.append(_Written(title, hidden))
        view = (
            '<sheetViews><sheetView workbookViewId="0"><pane ySplit="2" topLeftCell="A3" '
            'activePane="bottomLeft" state="frozen"/></sheetView></sheetViews>'
            if frozen
            else ""
        )
        with self._zip.open(f"xl/worksheets/sheet{number}.xml", "w") as part:
            part.write(
                (
                    f'{_HEADER}<worksheet xmlns="{_MAIN}" xmlns:r="{_RELATIONSHIPS}">'
                    + (f'<dimension ref="{dimension}"/>' if dimension else "")
                    + f"{view}<sheetData>"
                ).encode()
            )
            block: list[str] = []
            size = 0
            for index, row in enumerate(rows, 1):
                text = f'<row r="{index}">{row}</row>'
                block.append(text)
                size += len(text)
                if size >= _BLOCK:
                    part.write("".join(block).encode())
                    block, size = [], 0
            part.write(("".join(block) + f"</sheetData>{after}</worksheet>").encode())

    def _parts(self) -> None:
        tables = [(number, item) for number, item in enumerate(self._sheets, 1) if item.table]
        for table_id, (number, item) in enumerate(tables, 1):
            name, ref, keys = item.table
            columns = "".join(
                f'<tableColumn id="{index}" name="{key.translate(_MARKUP)}"/>'
                for index, key in enumerate(keys, 1)
            )
            self._write(
                f"xl/tables/table{table_id}.xml",
                f'<table xmlns="{_MAIN}" id="{table_id}" name="{name}" displayName="{name}" '
                f'ref="{ref}" totalsRowShown="0"><autoFilter ref="{ref}"/>'
                f'<tableColumns count="{len(keys)}">{columns}</tableColumns>'
                '<tableStyleInfo name="TableStyleMedium2" showFirstColumn="0" showLastColumn="0" '
                'showRowStripes="1" showColumnStripes="0"/></table>',
            )
            self._write(
                f"xl/worksheets/_rels/sheet{number}.xml.rels",
                f'<Relationships xmlns="{_PACKAGE}"><Relationship Id="rId1" '
                f'Type="{_DOCUMENT}/table" Target="../tables/table{table_id}.xml"/></Relationships>',
            )
        sheets = "".join(
            f'<sheet name="{item.title.translate(_MARKUP)}" sheetId="{number}"'
            + (' state="hidden"' if item.hidden else "")
            + f' r:id="rId{number}"/>'
            for number, item in enumerate(self._sheets, 1)
        )
        self._write(
            "xl/workbook.xml",
            f'<workbook xmlns="{_MAIN}" xmlns:r="{_RELATIONSHIPS}"><sheets>{sheets}</sheets></workbook>',
        )
        links = "".join(
            f'<Relationship Id="rId{number}" Type="{_DOCUMENT}/worksheet" '
            f'Target="worksheets/sheet{number}.xml"/>'
            for number in range(1, len(self._sheets) + 1)
        )
        styles = len(self._sheets) + 1
        self._write(
            "xl/_rels/workbook.xml.rels",
            f'<Relationships xmlns="{_PACKAGE}">{links}<Relationship Id="rId{styles}" '
            f'Type="{_DOCUMENT}/styles" Target="styles.xml"/></Relationships>',
        )
        self._write("xl/styles.xml", _STYLES)
        self._write(
            "_rels/.rels",
            f'<Relationships xmlns="{_PACKAGE}"><Relationship Id="rId1" '
            f'Type="{_DOCUMENT}/officeDocument" Target="xl/workbook.xml"/></Relationships>',
        )
        sheet_types = "".join(
            f'<Override PartName="/xl/worksheets/sheet{number}.xml" ContentType="application/'
            'vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
            for number in range(1, len(self._sheets) + 1)
        )
        table_types = "".join(
            f'<Override PartName="/xl/tables/table{table_id}.xml" ContentType="application/'
            'vnd.openxmlformats-officedocument.spreadsheetml.table+xml"/>'
            for table_id in range(1, len(tables) + 1)
        )
        self._write(
            "[Content_Types].xml",
            f'<Types xmlns="{_TYPES}">'
            '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
            '<Default Extension="xml" ContentType="application/xml"/>'
            '<Override PartName="/xl/workbook.xml" ContentType="application/'
            'vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
            '<Override PartName="/xl/styles.xml" ContentType="application/'
            'vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>'
            f"{sheet_types}{table_types}</Types>",
        )

    def _write(self, name: str, xml: str) -> None:
        self._zip.writestr(name, _HEADER + xml)


# Style 0 is the default; style 1 shows a date as YYYY-MM-DD.
_STYLES = (
    f'<styleSheet xmlns="{_MAIN}">'
    '<numFmts count="1"><numFmt numFmtId="164" formatCode="yyyy-mm-dd"/></numFmts>'
    '<fonts count="1"><font><sz val="11"/><name val="Calibri"/></font></fonts>'
    '<fills count="2"><fill><patternFill patternType="none"/></fill>'
    '<fill><patternFill patternType="gray125"/></fill></fills>'
    '<borders count="1"><border><left/><right/><top/><bottom/><diagonal/></border></borders>'
    '<cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs>'
    '<cellXfs count="2"><xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/>'
    '<xf numFmtId="164" fontId="0" fillId="0" borderId="0" xfId="0" applyNumberFormat="1"/></cellXfs>'
    '<cellStyles count="1"><cellStyle name="Normal" xfId="0" builtinId="0"/></cellStyles>'
    "</styleSheet>"
)
