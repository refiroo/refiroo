"""A streaming XLSX writer for exports (Base 0.9 J1, D51; J6).

An export's sheets can hold hundreds of thousands of rows, so the workbook is written as SpreadsheetML
straight into its ZIP container, row by row: inline strings, numbers, booleans and dates, never one
object per cell. Values arrive as the canonical text the API writes (PostgreSQL extracts them, as for
CSV), and :func:`cell` decides how each becomes a cell, so a machine reading the workbook gets back
exactly the stored value.

Two kinds of sheet: the technical export's (:meth:`Workbook.data`), one named table whose header row
is the column keys under a row of labels, with dropdown lists read from a hidden sheet; and a sheet
for people (:meth:`Workbook.plain`, 0.9 J6): one header row of labels, frozen and filtered, columns
sized and some hidden, cells styled from the workbook's style table (:class:`Styles`).
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
# A sheet for people has one header row.
PLAIN_ROWS = 1_048_576 - 1
# The most columns a sheet holds.
SHEET_COLUMNS = 16_384
# The most characters a cell holds.
CELL_CHARACTERS = 32_767
# What a sheet's title may not hold, and its length.
_TITLE_ILLEGAL = re.compile(r"[\\/?*\[\]:]")
TITLE_LENGTH = 31
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
# The custom number format of a date, and the style that shows one (YYYY-MM-DD).
_DATE_FORMAT = 164
DATE_STYLE = 1
# A thin border's colour: a neutral grey that reads on white and on the type hues' fills.
_BORDER = "FFC9CED6"


def xlsx_text(value: str) -> str:
    """Text as an XLSX cell holds it: characters XML cannot hold as ``_xHHHH_``, and a literal
    ``_xHHHH_`` escaped as ``_x005F_xHHHH_``, so Excel reads back exactly the text."""
    value = _XML_ESCAPE.sub(r"_x005F_\1_", value)
    return _XML_ILLEGAL.sub(lambda match: f"_x{ord(match.group()):04X}_", value)


def _escaped(value: str) -> str:
    return xlsx_text(value).translate(_MARKUP)


def _style(style: int | None) -> str:
    return f' s="{style}"' if style else ""


def text_cell(ref: str, value: str | None, style: int | None = None) -> str:
    """A text cell, never read as a number, a date or a formula."""
    if value is None:
        return f'<c r="{ref}"{_style(style)}/>' if style else ""
    return (
        f'<c r="{ref}"{_style(style)} t="inlineStr"><is><t xml:space="preserve">'
        f"{_escaped(value)}</t></is></c>"
    )


def number_cell(ref: str, value: int | str, style: int | None = None) -> str:
    return f'<c r="{ref}"{_style(style)}><v>{value}</v></c>'


def cell(ref: str, value: str | None, value_type: str, style: int | None = None) -> str:
    """An attribute's canonical text as the cell a reader can trust: integers and decimals as numbers
    when Excel holds them exactly, otherwise as text; booleans as booleans; dates as date cells
    (``style`` then a style that shows a date); date-times, JSON and text as text."""
    if value is None:
        return text_cell(ref, None, style)
    if value_type in {"integer", "decimal"}:
        if _digits(value) <= EXCEL_DIGITS:
            return number_cell(ref, value, style)
        return text_cell(ref, value, style)
    if value_type == "boolean":
        return f'<c r="{ref}"{_style(style)} t="b"><v>{1 if value == "true" else 0}</v></c>'
    if value_type == "date":
        days = date.fromisoformat(value).toordinal() - _EPOCH
        return f'<c r="{ref}" s="{style or DATE_STYLE}"><v>{days}</v></c>'
    return text_cell(ref, value, style)


def sheet_title(text: str, taken: set[str]) -> str:
    """``text`` as a sheet title Excel takes: without the characters it refuses, at most 31
    characters, and unlike every title in ``taken`` (ignoring case), which it joins."""
    base = _TITLE_ILLEGAL.sub(" ", text).strip().strip("'") or "Sheet"
    title, number = base[:TITLE_LENGTH].rstrip(), 1
    while title.lower() in taken:
        number += 1
        suffix = f" {number}"
        title = base[: TITLE_LENGTH - len(suffix)].rstrip() + suffix
    taken.add(title.lower())
    return title


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
class PlainSheet:
    """A sheet for people (0.9 J6): one header row of ``labels`` styled ``header_styles``, then the
    rows, each encoded at its row number; each column's width in characters and whether it is
    hidden, and dropdown lists as (column letter, list formula). Rows past a sheet's last continue
    on "Title 2" and so on."""

    title: str
    labels: Sequence[str]
    header_styles: Sequence[int]
    widths: Sequence[float]
    hidden: Sequence[bool]
    count: int
    rows: Iterable[Sequence[object]]
    encode: Callable[[Sequence[object], int], str]
    lists: list[tuple[str, str]] = field(default_factory=list)
    # The title was taken already (``Workbook.reserve``), so other sheets could name it first.
    reserved: bool = False


class Styles:
    """The workbook's cell styles: style 0 is the default, style 1 a date; :meth:`xf` adds a style
    of a fill, an ink, bold, the date format and a thin border (0.9 J6a, D199), once each."""

    def __init__(self) -> None:
        self._fonts: list[tuple[str | None, bool]] = [(None, False)]
        self._fills: list[str | None] = [None, None]  # none, gray125: Excel's two fixed fills
        self._xfs: list[tuple[int, int, int, int]] = [(0, 0, 0, 0), (_DATE_FORMAT, 0, 0, 0)]

    def xf(
        self,
        *,
        fill: str | None = None,
        ink: str | None = None,
        bold: bool = False,
        date: bool = False,
        border: bool = False,
    ) -> int:
        font = (ink, bold)
        if font not in self._fonts:
            self._fonts.append(font)
        if fill is not None and fill not in self._fills:
            self._fills.append(fill)
        xf = (
            _DATE_FORMAT if date else 0,
            self._fonts.index(font),
            0 if fill is None else self._fills.index(fill),
            1 if border else 0,
        )
        if xf not in self._xfs:
            self._xfs.append(xf)
        return self._xfs.index(xf)

    def xml(self) -> str:
        fonts = "".join(
            "<font>"
            + ("<b/>" if bold else "")
            + '<sz val="11"/>'
            + (f'<color rgb="{ink}"/>' if ink else "")
            + '<name val="Calibri"/></font>'
            for ink, bold in self._fonts
        )
        fills = '<fill><patternFill patternType="none"/></fill><fill><patternFill patternType="gray125"/></fill>'
        fills += "".join(
            f'<fill><patternFill patternType="solid"><fgColor rgb="{fill}"/><bgColor indexed="64"/>'
            "</patternFill></fill>"
            for fill in self._fills[2:]
        )
        xfs = "".join(
            f'<xf numFmtId="{number}" fontId="{font}" fillId="{fill}" borderId="{border}" xfId="0"'
            + (' applyNumberFormat="1"' if number else "")
            + (' applyFont="1"' if font else "")
            + (' applyFill="1"' if fill else "")
            + (' applyBorder="1"' if border else "")
            + "/>"
            for number, font, fill, border in self._xfs
        )
        return (
            f'<styleSheet xmlns="{_MAIN}">'
            f'<numFmts count="1"><numFmt numFmtId="{_DATE_FORMAT}" formatCode="yyyy-mm-dd"/></numFmts>'
            f'<fonts count="{len(self._fonts)}">{fonts}</fonts>'
            f'<fills count="{len(self._fills)}">{fills}</fills>'
            '<borders count="2"><border><left/><right/><top/><bottom/><diagonal/></border>'
            + "<border>"
            + "".join(
                f'<{side} style="thin"><color rgb="{_BORDER}"/></{side}>'
                for side in ("left", "right", "top", "bottom")
            )
            + "<diagonal/></border></borders>"
            '<cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs>'
            f'<cellXfs count="{len(self._xfs)}">{xfs}</cellXfs>'
            '<cellStyles count="1"><cellStyle name="Normal" xfId="0" builtinId="0"/></cellStyles>'
            "</styleSheet>"
        )


@dataclass
class _Written:
    title: str
    hidden: bool = False
    table: tuple[str, str, Sequence[str]] | None = None  # name, ref, keys
    filtered: str | None = None  # the AutoFilter's range


class Workbook:
    """Sheets written one after another into ``path``, then the parts that name them."""

    def __init__(self, path: Path, on_row: Callable[[], None]) -> None:
        self._zip = zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED, compresslevel=1)
        self._sheets: list[_Written] = []
        self._on_row = on_row
        self.styles = Styles()
        self.titles: set[str] = set()

    def data(self, sheet: Sheet) -> None:
        """``sheet.rows`` on as many sheets as they need (continued as "Title 2" and so on)."""
        rows = iter(sheet.rows)
        pages = max(1, -(-sheet.count // SHEET_ROWS))
        for page in range(1, pages + 1):
            count = min(SHEET_ROWS, sheet.count - (page - 1) * SHEET_ROWS)
            title = sheet.title if page == 1 else f"{sheet.title} {page}"
            table = sheet.table if page == 1 else f"{sheet.table}_{page}"
            self._data_page(title, table, sheet, count, rows)

    def plain(self, sheet: PlainSheet) -> list[str]:
        """A sheet for people, on as many sheets as its rows need; the titles written."""
        rows = iter(sheet.rows)
        pages = max(1, -(-sheet.count // PLAIN_ROWS))
        titles = []
        for page in range(1, pages + 1):
            count = min(PLAIN_ROWS, sheet.count - (page - 1) * PLAIN_ROWS)
            title = (
                sheet.title
                if page == 1 and sheet.reserved
                else sheet_title(sheet.title if page == 1 else f"{sheet.title} {page}", self.titles)
            )
            titles.append(title)
            self._plain_page(title, sheet, count, rows)
        return titles

    def reserve(self, title: str) -> str:
        """Take a title for a sheet written later (a list rule names it before it exists)."""
        return sheet_title(title, self.titles)

    def text(self, title: str, rows: Sequence[Sequence[str]], *, hidden: bool) -> None:
        """A sheet of text cells titled exactly ``title`` (the caller keeps it unlike the others)."""
        self.titles.add(title.lower())
        self._sheet(
            title,
            (
                "".join(
                    text_cell(f"{column(index)}{number}", value)
                    for index, value in enumerate(row, 1)
                )
                for number, row in enumerate(rows, 1)
            ),
            hidden=hidden,
        )

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
            "".join(
                text_cell(f"{letter}1", label)
                for letter, label in zip(letters, sheet.labels, strict=True)
            ),
            "".join(
                text_cell(f"{letter}2", key)
                for letter, key in zip(letters, sheet.keys, strict=True)
            ),
        ]

        def body() -> Iterator[str]:
            yield from head
            for number in range(3, 3 + count):
                yield sheet.encode(next(rows), number)
                self._on_row()

        validations = "".join(
            f'<dataValidation type="list" allowBlank="1" showErrorMessage="1" '
            f'sqref="{letter}3:{letter}{last_row}"><formula1>{source.translate(_MARKUP)}</formula1></dataValidation>'
            for letter, source in sheet.lists
        )
        after = (
            f'<dataValidations count="{len(sheet.lists)}">{validations}</dataValidations>'
            if validations
            else ""
        ) + '<tableParts count="1"><tablePart r:id="rId1"/></tableParts>'
        ref = f"A2:{last_column}{last_row}"
        self._sheet(title, body(), dimension=f"A1:{last_column}{last_row}", frozen=2, after=after)
        self._sheets[-1].table = (table, ref, sheet.keys)

    def _plain_page(self, title: str, sheet: PlainSheet, count: int, rows: Iterator) -> None:
        letters = [column(index) for index in range(1, len(sheet.labels) + 1)]
        last_row = 1 + max(count, 1)
        head = "".join(
            text_cell(f"{letter}1", label, style)
            for letter, label, style in zip(letters, sheet.labels, sheet.header_styles, strict=True)
        )

        def body() -> Iterator[str]:
            yield head
            for number in range(2, 2 + count):
                yield sheet.encode(next(rows), number)
                self._on_row()

        cols = "".join(
            f'<col min="{index}" max="{index}" width="{width:.1f}" customWidth="1"'
            + (' hidden="1"' if hidden else "")
            + "/>"
            for index, (width, hidden) in enumerate(zip(sheet.widths, sheet.hidden, strict=True), 1)
        )
        filtered = f"A1:{letters[-1]}{last_row}"
        validations = "".join(
            f'<dataValidation type="list" allowBlank="1" showErrorMessage="1" '
            f'sqref="{letter}2:{letter}{last_row}"><formula1>{source.translate(_MARKUP)}</formula1></dataValidation>'
            for letter, source in sheet.lists
        )
        after = f'<autoFilter ref="{filtered}"/>' + (
            f'<dataValidations count="{len(sheet.lists)}">{validations}</dataValidations>'
            if validations
            else ""
        )
        self._sheet(
            title,
            body(),
            dimension=f"A1:{letters[-1]}{last_row}",
            frozen=1,
            before=f"<cols>{cols}</cols>",
            after=after,
        )
        self._sheets[-1].filtered = filtered

    def _sheet(
        self,
        title: str,
        rows: Iterable[str],
        *,
        hidden: bool = False,
        dimension: str | None = None,
        frozen: int = 0,
        before: str = "",
        after: str = "",
    ) -> None:
        """A worksheet part: ``frozen`` header rows stay in view; ``before`` goes between the view
        and the data (column widths), ``after`` after it."""
        number = len(self._sheets) + 1
        self._sheets.append(_Written(title, hidden))
        view = (
            f'<sheetViews><sheetView workbookViewId="0"><pane ySplit="{frozen}" '
            f'topLeftCell="A{frozen + 1}" activePane="bottomLeft" state="frozen"/></sheetView>'
            "</sheetViews>"
            if frozen
            else ""
        )
        with self._zip.open(f"xl/worksheets/sheet{number}.xml", "w") as part:
            part.write(
                (
                    f'{_HEADER}<worksheet xmlns="{_MAIN}" xmlns:r="{_RELATIONSHIPS}">'
                    + (f'<dimension ref="{dimension}"/>' if dimension else "")
                    + f"{view}{before}<sheetData>"
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
        # Excel names each AutoFilter's range (a hidden name of its sheet).
        names = "".join(
            f'<definedName name="_xlnm._FilterDatabase" localSheetId="{number - 1}" hidden="1">'
            f"{_reference(item.title, item.filtered)}</definedName>"
            for number, item in enumerate(self._sheets, 1)
            if item.filtered
        )
        self._write(
            "xl/workbook.xml",
            f'<workbook xmlns="{_MAIN}" xmlns:r="{_RELATIONSHIPS}"><sheets>{sheets}</sheets>'
            + (f"<definedNames>{names}</definedNames>" if names else "")
            + "</workbook>",
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
        self._write("xl/styles.xml", self.styles.xml())
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


def _reference(title: str, area: str) -> str:
    """``area`` of sheet ``title`` as an absolute reference."""
    start, end = area.split(":")
    absolute = ":".join(re.sub(r"([A-Z]+)(\d+)", r"$\1$\2", part) for part in (start, end))
    return f"'{title.replace(chr(39), chr(39) * 2)}'!{absolute}".translate(_MARKUP)
