"""A file's cell as an attribute value (``engine/imports/cells.py``, 0.9 J2).

A workbook cell arrives typed, a CSV cell as text; both must give the value the API would take, in
its canonical form, or ``INVALID_ATTRIBUTE_VALUE``. The 15-digit text numbers and ``_xHHHH_`` escapes
are the forms J1's export writes.
"""

# Workbook cells hold dates and times without a zone, so the cases do too.
# ruff: noqa: DTZ001

from datetime import date, datetime

import pytest

from app.engine.imports.cells import (
    attribute_value,
    cell_text,
    decode_excel_text,
    flag_set,
    is_empty,
)
from app.errors import ApiError
from app.models.schema import AttributeTypeDefinition


def definition(value_type, **validation):
    return AttributeTypeDefinition(key="k", name="K", valueType=value_type, validation=validation)


@pytest.mark.parametrize(
    ("value_type", "raw", "expected"),
    [
        ("text", "007", "007"),
        ("text", 7.0, "7"),
        ("text", 7, "7"),
        ("text", True, "true"),
        ("text", " padded ", " padded "),
        ("longText", "line\nbreak", "line\nbreak"),
        ("integer", 42, 42),
        ("integer", 42.0, 42),
        ("integer", "-42", -42),
        ("integer", " 42 ", 42),
        ("decimal", "12.50", "12.5"),
        ("decimal", 0.1, "0.1"),
        ("decimal", 3, "3"),
        ("decimal", "123456789012345678.25", "123456789012345678.25"),
        ("boolean", True, True),
        ("boolean", "FALSE", False),
        ("boolean", "true", True),
        ("date", date(2026, 3, 4), "2026-03-04"),
        ("date", datetime(2026, 3, 4), "2026-03-04"),
        ("date", "2026-03-04", "2026-03-04"),
        ("dateTime", datetime(2026, 3, 4, 10, 30), "2026-03-04T10:30:00+00:00"),
        ("dateTime", "2026-03-04T10:30:00+02:00", "2026-03-04T08:30:00+00:00"),
        ("json", '{"a": [1, 2]}', {"a": [1, 2]}),
    ],
)
def test_a_cell_becomes_the_canonical_value_of_its_type(value_type, raw, expected):
    assert attribute_value(definition(value_type), raw) == expected


@pytest.mark.parametrize("raw", [None, "", "   ", "\t"])
def test_an_empty_cell_is_no_value(raw):
    assert is_empty(raw)
    assert attribute_value(definition("integer"), raw) is None


@pytest.mark.parametrize(
    ("value_type", "raw"),
    [
        ("integer", "twelve"),
        ("integer", 4.5),
        ("integer", True),
        ("integer", "4.0"),
        ("decimal", "NaN"),
        ("decimal", "1,5"),
        ("decimal", False),
        ("boolean", "yes"),
        ("boolean", 1),
        ("date", "04.03.2026"),
        ("date", datetime(2026, 3, 4, 9, 0)),
        ("dateTime", "tomorrow"),
        ("json", "{not json"),
    ],
)
def test_a_cell_that_does_not_convert_is_refused_naming_the_type(value_type, raw):
    with pytest.raises(ApiError) as caught:
        attribute_value(definition(value_type), raw)
    assert caught.value.code == "INVALID_ATTRIBUTE_VALUE"
    assert value_type in caught.value.message


def test_a_value_out_of_range_is_refused_by_the_registry():
    with pytest.raises(ApiError) as caught:
        attribute_value(definition("integer", minimum=0, maximum=100), "101")
    assert caught.value.code == "ATTRIBUTE_ABOVE_MAXIMUM"


def test_cell_text_matches_what_a_person_sees():
    assert cell_text(12.0) == "12"
    assert cell_text(12.5) == "12.5"
    assert cell_text(False) == "false"
    assert cell_text(datetime(2026, 1, 2)) == "2026-01-02"
    assert cell_text(datetime(2026, 1, 2, 3, 4)) == "2026-01-02T03:04:00"


def test_excel_escapes_are_decoded_once():
    assert decode_excel_text("a_x0001_b") == "a\x01b"
    assert decode_excel_text("lit _x005F_x0041_ here") == "lit _x0041_ here"
    assert decode_excel_text("plain") == "plain"


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("x", True),
        ("X", True),
        (" yes ", True),
        (True, True),
        (1, True),
        (1.0, True),
        ("no", False),
        ("", False),
        (None, False),
        (0, False),
        (False, False),
    ],
)
def test_a_flag_is_set_by_a_true_value_ignoring_case(raw, expected):
    assert flag_set(raw, ["x", "yes", "y", "true", "1"]) is expected
