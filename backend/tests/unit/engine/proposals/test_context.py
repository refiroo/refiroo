"""The context builder (``engine/proposals/context.py``, AP-D3, AP-D14): a file is sent as its
profile, no value leaves above its level, and the window drops values before structure."""

import json

import pytest

from app.engine.proposals.context import FEATURE_LEVELS, Policy, within_window, workbook_profile
from app.engine.sources.inference.facts import Column


def _column(number: int, header: str, distinct: int, values: int = 8, **more) -> Column:
    return Column(
        number=number,
        letter="ABC"[number - 1],
        header=header,
        rows=500,
        filled=480,
        distinct=distinct,
        value_types={"text": 480},
        candidate_key=False,
        values=tuple({"value": f"{header}-{n}", "count": 60 - n} for n in range(values)),
        **more,
    )


class _Table:
    def __init__(self, name: str, columns: list[Column], titles: tuple[str, ...] = ()) -> None:
        self.name, self.rows, self.columns, self.titles = name, 500, columns, titles


def _tables() -> list[_Table]:
    return [
        _Table(
            "Items",
            [
                _column(
                    1,
                    "Code",
                    distinct=20,
                    delimiters=({"character": ";", "cells": 5, "share": 0.01},),
                    placeholders=({"value": "N/A", "count": 7},),
                    overlaps=({"sheet": "Parts", "column": "A", "header": "Ref", "share": 0.9},),
                ),
                _column(2, "Name", distinct=300),
            ],
            titles=("Spring list",),
        )
    ]


def test_structure_sends_counts_and_names_and_no_value():
    shown = workbook_profile(Policy("structure", 5), _tables())
    text = json.dumps(shown)
    assert "Code-0" not in text and "Name-0" not in text and "N/A" not in text
    table = shown[0]
    assert (table["name"], table["rows"], table["titles"]) == ("Items", 500, ["Spring list"])
    code = table["columns"][0]
    assert (code["rows"], code["filled"], code["distinct"], code["valueType"]) == (
        500,
        480,
        20,
        "text",
    )
    assert code["placeholderCells"] == 7 and code["delimiters"][0]["character"] == ";"
    assert code["overlaps"] == [{"sheet": "Parts", "column": "Ref", "share": 0.9}]
    assert all("values" not in c and "placeholders" not in c for c in table["columns"])


def test_at_samples_at_most_the_sample_values_per_column():
    shown = workbook_profile(Policy("samples", 3), _tables())
    assert [len(c["values"]) for c in shown[0]["columns"]] == [3, 3]
    assert shown[0]["columns"][0]["values"][0] == {"value": "Code-0", "count": 60}
    assert shown[0]["columns"][0]["placeholders"] == [{"value": "N/A", "count": 7}]


def test_at_values_all_the_profiles_frequent_values_are_sent():
    shown = workbook_profile(Policy("values", 3), _tables())
    assert [len(c["values"]) for c in shown[0]["columns"]] == [8, 8]


def test_a_window_drops_the_values_of_the_most_distinct_columns_first_never_structure():
    policy = Policy("values", 3)
    full = len(json.dumps(workbook_profile(policy, _tables())))
    # Room for all but the larger column's values: only Name (300 distinct) loses its values.
    allowed = full - 50
    shown = workbook_profile(policy, _tables(), lambda t: len(json.dumps(t)) <= allowed)
    code, name = shown[0]["columns"]
    assert "values" in code and "values" not in name
    # No room at all: every value goes, every column stays with its counts.
    shown = workbook_profile(policy, _tables(), lambda t: False)
    assert [c["header"] for c in shown[0]["columns"]] == ["Code", "Name"]
    assert all("values" not in c and c["distinct"] for c in shown[0]["columns"])


def test_the_window_estimate_is_half_the_window_and_absent_without_one():
    assert within_window(10**9, None)
    assert within_window(300, 200) and not within_window(303, 200)
    assert not within_window(300, 200, answer_tokens=1)


def test_levels_are_ordered_and_a_feature_is_offered_only_at_its_level():
    assert Policy("values", 1).allows("samples") and Policy("samples", 1).allows("structure")
    assert not Policy("structure", 1).allows("samples")
    assert not Policy("samples", 1).allows("values")
    for purpose, needed in FEATURE_LEVELS.items():
        assert Policy(needed, 1).offers(purpose)


@pytest.mark.parametrize("level", ["structure", "samples", "values"])
def test_nothing_is_read_from_rows(level):
    # The builder takes only profiled tables: it has no session and no row reader.
    assert workbook_profile(Policy(level, 2), []) == []
