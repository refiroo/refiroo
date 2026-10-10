"""How an export writes values into an XLSX workbook (0.9 J1, D51).

A machine reading the workbook must get back exactly the stored value: numbers Excel cannot hold
exactly stay text, text is never read as a number or a formula, and characters XML cannot hold
survive as Excel's ``_xHHHH_`` escape. Each case writes a workbook and reads it back with openpyxl.
"""

import re
from datetime import datetime

import pytest
from openpyxl import load_workbook

from app.engine.jobs import xlsx


def _written(tmp_path, values, kinds=("text",)):
    """One table, its first row holding ``values`` as cells of ``kinds``, read back."""
    path = tmp_path / "book.xlsx"
    book = xlsx.Workbook(path, lambda: None)
    keys = [f"#k{index}" for index in range(len(values))]
    letters = [xlsx.column(index) for index in range(1, len(keys) + 1)]
    book.data(
        xlsx.Sheet(
            title="Records",
            table="records",
            keys=keys,
            labels=keys,
            count=1,
            rows=[values],
            encode=lambda row, number: "".join(
                xlsx.cell(f"{letter}{number}", value, kind)
                for letter, value, kind in zip(letters, row, kinds, strict=True)
            ),
        )
    )
    book.lists([["a", "b"]])
    book.close()
    workbook = load_workbook(path)
    sheet = workbook["Records"]
    assert list(sheet.tables) == ["records"] and workbook["Lists"].sheet_state == "hidden"
    return [cell.value for cell in sheet[3]]


@pytest.mark.parametrize(
    ("value", "kind", "expected"),
    [
        ("007", "text", "007"),
        ("=SUM(A1)", "longText", "=SUM(A1)"),
        ("42", "integer", 42),
        ("-999999999999999", "integer", -999999999999999),
        ("1000000000000000", "integer", 1000000000000000),
        ("1000000000000001", "integer", "1000000000000001"),
        ("12.5", "decimal", 12.5),
        ("-0.00125", "decimal", -0.00125),
        ("1234567890.123456", "decimal", "1234567890.123456"),
        ("true", "boolean", True),
        ("false", "boolean", False),
        ("2026-03-04", "date", datetime.fromisoformat("2026-03-04T00:00:00")),
        ("2026-03-04T10:00:00+00:00", "dateTime", "2026-03-04T10:00:00+00:00"),
        ('{"a": [1, null]}', "json", '{"a": [1, null]}'),
        (None, "integer", None),
    ],
)
def test_each_value_type_becomes_the_cell_a_reader_can_trust(tmp_path, value, kind, expected):
    (read,) = _written(tmp_path, [value], (kind,))
    assert read == expected
    assert type(read) is type(expected)


@pytest.mark.parametrize(
    "text",
    [
        "plain",
        " padded ",
        "tab\tand\nnewline",
        "bell\x07 and vertical\x0b tab",
        "a <b> & c",
        "a literal _x0041_ stays",
    ],
)
def test_text_round_trips_through_a_workbook(tmp_path, text):
    (read,) = _written(tmp_path, [text])
    assert _unescaped(read) == text


def test_a_column_letter_follows_excel():
    assert [xlsx.column(n) for n in (1, 26, 27, 52, 703)] == ["A", "Z", "AA", "AZ", "AAA"]


def _unescaped(value: str) -> str:
    """Excel's reading of ``_xHHHH_``, which openpyxl leaves to the reader."""
    return re.sub(r"_x([0-9A-Fa-f]{4})_", lambda m: chr(int(m.group(1), 16)), value)


@pytest.mark.parametrize(
    ("text", "taken", "expected"),
    [
        ("Values", set(), "Values"),
        ("Rates: buy/sell [EUR]?", set(), "Rates  buy sell  EUR"),
        (
            "A relationship named far beyond thirty-one characters",
            set(),
            "A relationship named far beyond",
        ),
        ("Values", {"values"}, "Values 2"),
        (
            "A relationship named far beyond thirty-one characters",
            {"a relationship named far beyond"},
            "A relationship named far beyo 2",
        ),
        ("'quoted'", set(), "quoted"),
        ("***", set(), "Sheet"),
    ],
)
def test_a_sheet_title_is_one_excel_takes(text, taken, expected):
    """0.9 J6: a title from a model's name loses the characters Excel refuses, fits 31 characters
    and differs from the workbook's other titles ignoring case."""
    assert xlsx.sheet_title(text, taken) == expected
    assert expected.lower() in taken


def test_a_sheet_for_people_is_frozen_filtered_sized_hidden_and_styled(tmp_path):
    """0.9 J6: one header row, frozen and filtered; widths and a hidden column; a style per fill,
    ink and boldness, made once."""
    path = tmp_path / "people.xlsx"
    book = xlsx.Workbook(path, lambda: None)
    fill = book.styles.xf(fill="FFDDF4EF", ink="FF0B6E62")
    assert book.styles.xf(fill="FFDDF4EF", ink="FF0B6E62") == fill
    header = book.styles.xf(fill="FFDDF4EF", ink="FF0B6E62", bold=True)
    titles = book.plain(
        xlsx.PlainSheet(
            title="Values",
            labels=["Name", "When", "Record ID"],
            header_styles=[header, header, 0],
            widths=[20.0, 12.0, 10.0],
            hidden=[False, False, True],
            count=1,
            rows=[("First", "2026-10-10", "id-1")],
            encode=lambda row, number: (
                xlsx.text_cell(f"A{number}", row[0], fill)
                + xlsx.cell(f"B{number}", row[1], "date")
                + xlsx.text_cell(f"C{number}", row[2])
            ),
        )
    )
    book.text("Hidden", [["mark", "{}"]], hidden=True)
    book.close()
    assert titles == ["Values"]
    workbook = load_workbook(path)
    sheet = workbook["Values"]
    assert sheet.freeze_panes == "A2" and sheet.auto_filter.ref == "A1:C2"
    assert sheet.column_dimensions["C"].hidden and sheet.column_dimensions["A"].width == 20
    assert sheet["A1"].font.b and sheet["A2"].fill.fgColor.rgb == "FFDDF4EF"
    assert sheet["B2"].value.date().isoformat() == "2026-10-10"
    assert sheet["B2"].number_format == "yyyy-mm-dd"
    assert workbook["Hidden"].sheet_state == "hidden"


def test_a_cell_has_a_border_and_a_column_chooses_from_a_sheet_written_later(tmp_path):
    """0.9 J6a: a bordered style; a list rule naming a sheet whose title was reserved first and
    which is written after it."""
    path = tmp_path / "lists.xlsx"
    book = xlsx.Workbook(path, lambda: None)
    bordered = book.styles.xf(border=True)
    title = book.reserve("List · Tokens")
    book.plain(
        xlsx.PlainSheet(
            title="Values",
            labels=["Token"],
            header_styles=[bordered],
            widths=[20.0],
            hidden=[False],
            count=1,
            rows=[("Alpha",)],
            encode=lambda row, number: xlsx.text_cell(f"A{number}", row[0], bordered),
            lists=[("A", f"'{title}'!$A$2:$A$3")],
        )
    )
    book.plain(
        xlsx.PlainSheet(
            title=title,
            labels=["Name"],
            header_styles=[bordered],
            widths=[20.0],
            hidden=[False],
            count=2,
            rows=[("Alpha",), ("Beta",)],
            encode=lambda row, number: xlsx.text_cell(f"A{number}", row[0], bordered),
            reserved=True,
        )
    )
    book.close()
    workbook = load_workbook(path)
    assert workbook.sheetnames == ["Values", "List · Tokens"]
    sheet = workbook["Values"]
    assert sheet["A2"].border.left.style == "thin" and sheet["A1"].border.bottom.style == "thin"
    (rule,) = sheet.data_validations.dataValidation
    assert rule.type == "list" and rule.formula1 == "'List · Tokens'!$A$2:$A$3"
    assert [row[0].value for row in workbook["List · Tokens"].iter_rows(min_row=2)] == [
        "Alpha",
        "Beta",
    ]
