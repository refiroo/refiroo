"""``engine/model/authoring/mapping.py``: a source moved to another header row or narrowed keeps
each binding on its column letter (0.10 A8b, D126).

A sheet of three columns whose rows are generated: a header row moved down or up names each bound
column by the text its letter holds on the new row; a column left outside a narrower block, or
whose cell on the new header row is empty, becomes an unmapped entry; a key column follows like a
binding; and the step's inverse puts the profile back whole.
"""

import copy
from typing import Any

import pytest
from configurations import example

from app.engine.model.authoring.document import PROFILE, PROFILE_IDENTITIES, Document
from app.engine.model.authoring.kinds import Context, Sheet, apply_operation

MODEL = example().model
TYPE = MODEL["objectTypes"][0]["key"]
APP = next(a["key"] for a in MODEL["applications"] if TYPE in a["objectTypeKeys"])

# Rows 2–6 of columns A–C; row 4 has no cell in C.
GRID: dict[int, dict[int, str]] = {
    2: {1: "Title", 2: "Title de", 3: "Title fr"},
    3: {1: "Name", 2: "Name de", 3: "Name fr"},
    4: {1: "First", 2: "Erste"},
    5: {1: "Second", 2: "Zweite", 3: "Deuxième"},
    6: {1: "Third", 2: "Dritte", 3: "Troisième"},
}


def _profile(key: dict[str, Any] | None = None) -> dict[str, Any]:
    return {
        "key": "lists",
        "name": "Lists",
        "valueMaps": {},
        "sources": [
            {
                "id": "s",
                "sheet": "S",
                "headerRow": 3,
                "block": {"firstColumn": "A", "lastColumn": "C", "lastRow": 6},
                "applicationKey": APP,
                "objectTypeKey": TYPE,
                "key": key,
                "columns": [
                    {"column": "Name", "field": "name"},
                    {"column": "Name de", "ignore": True},
                    {"column": "Name fr", "ignore": True},
                ],
            }
        ],
    }


def _apply(profile: dict[str, Any], **change: Any) -> tuple[dict[str, Any], dict[str, Any]]:
    """The setSource step applied; its inverse."""
    model = copy.deepcopy(MODEL)
    document = Document(model)
    sheet = Sheet("S", 3, ("Name", "Name de", "Name fr"), lambda row: dict(GRID.get(row, {})))
    context = Context(
        document,
        lambda _atom: False,
        Document(profile, name=PROFILE, identities=PROFILE_IDENTITIES, log=document.log),
        {"S": sheet},
    )
    applied = apply_operation(context, {"kind": "setSource", "source": "s", **change})
    return profile, applied.inverse


def _columns(profile: dict[str, Any]) -> list[str]:
    return [b["column"] for b in profile["sources"][0]["columns"]]


def _unmapped(profile: dict[str, Any]) -> list[str]:
    return [u.get("column", "key") for u in profile.get("unmapped") or []]


@pytest.mark.parametrize(
    ("change", "columns", "unmapped"),
    [
        pytest.param({"headerRow": 5}, ["Second", "Zweite", "Deuxième"], [], id="moved-down"),
        pytest.param({"headerRow": 2}, ["Title", "Title de", "Title fr"], [], id="moved-up"),
        pytest.param({"headerRow": 4}, ["First", "Erste"], ["Name fr"], id="empty-new-header-cell"),
        pytest.param(
            {"block": {"firstColumn": "A", "lastColumn": "B", "lastRow": 6}},
            ["Name", "Name de"],
            ["Name fr"],
            id="narrowed",
        ),
        pytest.param(
            {"headerRow": 5, "block": {"firstColumn": "B", "lastColumn": "C", "lastRow": 6}},
            ["Zweite", "Deuxième"],
            ["Name"],
            id="moved-and-narrowed",
        ),
    ],
)
def test_bindings_follow_their_letter_and_the_inverse_restores_them(change, columns, unmapped):
    profile = _profile()
    original = copy.deepcopy(profile)
    profile, inverse = _apply(profile, **change)
    assert _columns(profile) == columns
    assert _unmapped(profile) == unmapped
    model = copy.deepcopy(MODEL)
    document = Document(model)
    apply_operation(
        Context(
            document,
            lambda _atom: False,
            Document(profile, name=PROFILE, identities=PROFILE_IDENTITIES, log=document.log),
        ),
        inverse,
    )
    assert profile == original


def test_a_key_column_follows_its_letter_or_is_unmapped():
    moved, _ = _apply(_profile({"column": "Name de"}), headerRow=5)
    assert moved["sources"][0]["key"] == {"column": "Zweite"}
    narrowed, _ = _apply(
        _profile({"column": "Name fr"}), block={"firstColumn": "A", "lastColumn": "B", "lastRow": 6}
    )
    assert narrowed["sources"][0].get("key") is None
    assert "key" in _unmapped(narrowed)


def test_a_source_whose_header_row_is_unchanged_keeps_its_bindings():
    profile, _ = _apply(_profile(), block={"firstColumn": "A", "lastColumn": "C", "lastRow": 5})
    assert _columns(profile) == ["Name", "Name de", "Name fr"]
    assert _unmapped(profile) == []


def test_a_header_is_matched_without_its_surrounding_whitespace_and_saved_trimmed():
    """The profile lists a header as its cell holds it; the import's reader names it trimmed."""
    profile = _profile()
    profile["sources"][0]["columns"] = []
    model = copy.deepcopy(MODEL)
    document = Document(model)
    sheet = Sheet("S", 3, ("Name", "Name de", "Name fr"), lambda row: dict(GRID.get(row, {})))
    context = Context(
        document,
        lambda _atom: False,
        Document(profile, name=PROFILE, identities=PROFILE_IDENTITIES, log=document.log),
        {"S": sheet},
    )
    for name in ("Name ", " Name de"):
        apply_operation(context, {"kind": "ignoreColumn", "source": "s", "column": name})
    apply_operation(context, {"kind": "setSource", "source": "s", "key": {"column": "Name fr "}})
    assert _columns(profile) == ["Name", "Name de"]
    assert profile["sources"][0]["key"] == {"column": "Name fr"}
