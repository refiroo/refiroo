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
    ["plain", " padded ", "tab\tand\nnewline", "bell\x07 and vertical\x0b tab", "a <b> & c", "a literal _x0041_ stays"],
)
def test_text_round_trips_through_a_workbook(tmp_path, text):
    (read,) = _written(tmp_path, [text])
    assert _unescaped(read) == text


def test_a_column_letter_follows_excel():
    assert [xlsx.column(n) for n in (1, 26, 27, 52, 703)] == ["A", "Z", "AA", "AZ", "AAA"]


def _unescaped(value: str) -> str:
    """Excel's reading of ``_xHHHH_``, which openpyxl leaves to the reader."""
    return re.sub(r"_x([0-9A-Fa-f]{4})_", lambda m: chr(int(m.group(1), 16)), value)
