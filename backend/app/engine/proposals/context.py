"""The context builder (AP-D3): the only code that reads data for a provider.

``AI_SEND_LEVEL`` is the ceiling: ``structure`` sends keys, labels, headers, attribute names and
types and no value; ``samples`` adds values, at most ``AI_SAMPLE_VALUES`` per column whatever a feature asks for;
``values`` sends the values a feature asks for, as many as it needs. A file is sent as its
profile (0.16 AP-D14): each column's counts, type and most frequent values, computed in the
database over every row; no raw row is read here. A value is sent only when the level allows it. A
feature that needs more than the ceiling is not offered (``FEATURE_LEVELS``).
"""

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Any

from ...config import SEND_LEVELS, SendLevel
from .provider import Purpose

# The least each purpose needs to be useful. The inference's names work from headers alone, and
# are better with the columns' values.
FEATURE_LEVELS: dict[Purpose, SendLevel] = {
    "connectionTest": "structure",
    # Record names are values (AP2-D3).
    "mappingTarget": "values",
    # Record names and codes are values (AP6a).
    "workbookLoad": "values",
}


@dataclass(frozen=True)
class Policy:
    level: SendLevel
    samples: int

    def allows(self, needed: SendLevel) -> bool:
        return SEND_LEVELS.index(needed) <= SEND_LEVELS.index(self.level)

    def offers(self, purpose: Purpose) -> bool:
        return self.allows(FEATURE_LEVELS[purpose])

    def values(self, wanted: int) -> int:
        """How many of the ``wanted`` values may be sent: none at ``structure``, at most
        ``AI_SAMPLE_VALUES`` at ``samples``, all of them at ``values``."""
        if not self.allows("samples"):
            return 0
        return wanted if self.allows("values") else min(wanted, self.samples)


# The characters a token holds at the least (JSON with codes tokenises densely).
CHARS_PER_TOKEN = 3


def estimated_tokens(characters: int) -> int:
    """The tokens ``characters`` of a request cost, estimated."""
    return characters // CHARS_PER_TOKEN


def within_window(characters: int, context_tokens: int | None, answer_tokens: int = 0) -> bool:
    """Whether a request of ``characters`` and an answer of ``answer_tokens`` fit half of the
    model's window (the rest is the model's); always without a window."""
    if context_tokens is None:
        return True
    return estimated_tokens(characters) + answer_tokens <= context_tokens // 2


def _column(policy: Policy, column: Any) -> dict[str, Any]:
    shown: dict[str, Any] = {
        "header": column.header,
        "rows": column.rows,
        "filled": column.filled,
        "distinct": column.distinct,
        "valueType": column.value_type(),
        "candidateKey": column.candidate_key,
    }
    if column.delimiters:
        shown["delimiters"] = [
            {"character": d["character"], "cells": d["cells"], "share": d["share"]}
            for d in column.delimiters
        ]
    if column.placeholders:
        if policy.allows("samples"):
            shown["placeholders"] = [
                {"value": p["value"], "count": p["count"]}
                for p in column.placeholders[: policy.values(len(column.placeholders))]
            ]
        else:
            shown["placeholderCells"] = sum(p["count"] for p in column.placeholders)
    overlaps = []
    for overlap in column.overlaps:
        if "sheet" in overlap:
            overlaps.append(
                {"sheet": overlap["sheet"], "column": overlap.get("header") or overlap["column"]}
            )
        else:
            overlaps.append({"existingType": overlap.get("objectTypeKey")})
            if overlap.get("attributeTypeKey"):
                overlaps[-1]["attribute"] = overlap["attributeTypeKey"]
        overlaps[-1]["share"] = overlap["share"]
    if overlaps:
        shown["overlaps"] = overlaps
    allowed = policy.values(len(column.values))
    if allowed:
        shown["values"] = [
            {"value": v["value"], "count": v["count"]} for v in column.values[:allowed]
        ]
    return shown


def workbook_profile(
    policy: Policy,
    tables: Sequence[Any],
    fits: Callable[[list[dict[str, Any]]], bool] | None = None,
) -> list[dict[str, Any]]:
    """The profiled tables of a staged workbook (``inference.facts`` tables) as a provider sees
    them (AP-D14): each table's name, titles and row count, and per column its counts, value type,
    candidate key, delimiters, placeholders, overlaps with other columns and most frequent values,
    all from the profile over every row. ``fits`` says whether a request carrying the tables is
    within the model's window; when it is not, the frequent values of the columns with the most
    distinct values go first, never the structure."""
    shown = []
    for table in tables:
        entry: dict[str, Any] = {"name": table.name}
        titles = getattr(table, "titles", ())
        if titles:
            entry["titles"] = list(titles)
        entry["rows"] = table.rows
        entry["columns"] = [_column(policy, column) for column in table.columns]
        shown.append(entry)
    if fits is not None and not fits(shown):
        columns = sorted(
            (c for t in shown for c in t["columns"] if "values" in c),
            key=lambda c: -c["distinct"],
        )
        for column in columns:
            del column["values"]
            if fits(shown):
                break
    return shown
