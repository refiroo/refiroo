"""A staged cell keeps what the reader gave (``engine/sources/values.py``, 0.10 A3, D66)."""

# A workbook's dates are naive, as openpyxl reads them.
# ruff: noqa: DTZ001

import itertools
import json
from datetime import date, datetime, time

import pytest

from app.engine.imports.cells import cell_text
from app.engine.sources.values import staged, unstaged

READ = [
    ("Paper", "text"),
    ("  padded  ", "text"),
    (42, "integer"),
    (-7, "integer"),
    (2.5, "decimal"),
    (3.0, "decimal"),
    (True, "boolean"),
    (False, "boolean"),
    (datetime(2026, 10, 12), "date"),
    (datetime(2026, 10, 12, 8, 30), "dateTime"),
    (date(2026, 1, 2), "date"),
    (time(9, 15), "text"),
]


@pytest.mark.parametrize(("raw", "kind"), READ)
def test_a_cell_comes_back_as_the_reader_gave_it_with_its_kind_and_text(raw, kind):
    found = staged(raw)
    assert found is not None
    assert found[0] == kind
    assert found[1] == cell_text(raw)
    value = unstaged(json.loads(found[2]))
    assert value == raw and type(value) is type(raw)


@pytest.mark.parametrize("raw", [None, "", "   ", "\t"])
def test_an_empty_cell_is_not_staged(raw):
    assert staged(raw) is None


def test_text_holding_a_nul_character_is_kept_without_it():
    kind, text, value = staged("a\x00b")
    assert (kind, text, json.loads(value)) == ("text", "ab", "ab")


@pytest.mark.parametrize("pair", list(itertools.combinations([raw for raw, _ in READ], 2)))
def test_different_cells_stay_different(pair):
    first, second = (json.loads(staged(raw)[2]) for raw in pair)
    if pair[0] != pair[1] or type(pair[0]) is not type(pair[1]):
        assert (first, staged(pair[0])[0]) != (second, staged(pair[1])[0])
