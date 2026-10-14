"""The inference's table interface over rows a test generates (``engine/sources/inference/facts.py``).

The engine answers these questions with statements over the staged cells; here the same answers
are worked out in Python from the rows, with the profile's statistics as A3 states them (D68–D70),
so a rule is tested on a generated table without a database.
"""

import re
from collections import Counter
from dataclasses import dataclass, field
from typing import Any

from openpyxl.utils import get_column_letter

from app.engine.sources.inference.facts import Column, is_guid
from app.engine.sources.profiling import DELIMITERS, PLACEHOLDER_VALUES


def _text(value: Any) -> str | None:
    if value is None or (isinstance(value, str) and not value.strip()):
        return None
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


def _types(values: list[Any]) -> dict[str, int]:
    texts = [_text(v) for v in values if _text(v) is not None]
    counts = {
        "text": len(texts),
        "integer": sum(bool(re.fullmatch(r"\s*[+-]?\d+\s*", t)) for t in texts),
        "decimal": sum(bool(re.fullmatch(r"\s*[+-]?(\d+\.?\d*|\.\d+)\s*", t)) for t in texts),
        "boolean": sum(t.strip().lower() in ("true", "false") for t in texts),
        "date": sum(bool(re.fullmatch(r"\s*\d{4}-\d{2}-\d{2}\s*", t)) for t in texts),
    }
    return {k: v for k, v in counts.items() if v}


@dataclass
class MemoryTable:
    name: str
    index: int
    data: dict[str, list[Any]]
    header_row: int = 1
    columns: list[Column] = field(default_factory=list)

    @property
    def rows(self) -> int:
        return max((len(v) for v in self.data.values()), default=0)

    def cells(self, number: int) -> list[str | None]:
        header = list(self.data)[number - 1]
        return [_text(v) for v in self.data[header]]

    def constant_within(self, group: int, others: list[int]) -> dict[int, int]:
        keys = self.cells(group)
        found = {}
        for other in others:
            seen: dict[str, set[str]] = {}
            for key, value in zip(keys, self.cells(other), strict=True):
                if key is not None and value is not None:
                    seen.setdefault(key, set()).add(value)
            found[other] = sum(1 for values in seen.values() if len(values) == 1)
        return found

    def pairs(self, first: int, second: int) -> int:
        return len({(a, b) for a, b in zip(self.cells(first), self.cells(second), strict=True) if a and b})

    def names_per_code(self, code: int, name: int) -> list[dict[str, Any]]:
        counts: dict[str, Counter] = {}
        for a, b in zip(self.cells(code), self.cells(name), strict=True):
            if a and b:
                counts.setdefault(a, Counter())[b] += 1
        return [
            {"code": c, "names": [{"value": v, "count": n} for v, n in sorted(found.items(), key=lambda i: (-i[1], i[0]))]}
            for c, found in sorted(counts.items())
            if len(found) > 1
        ]

    def split_parts(self, column: int, delimiter: str) -> tuple[int, int]:
        cells = [c for c in self.cells(column) if c]
        whole = {c.strip() for c in cells if delimiter not in c}
        parts = [p.strip() for c in cells if delimiter in c for p in c.split(delimiter) if p.strip()]
        return len(parts), sum(p in whole for p in parts)

    def same(self, first: int, second: int) -> int:
        return sum(1 for a, b in zip(self.cells(first), self.cells(second), strict=True) if a and a == b)

    def distinct_values(self, column: int, limit: int) -> list[dict[str, Any]] | None:
        counts = Counter(c for c in self.cells(column) if c is not None)
        if len(counts) > limit:
            return None
        return [{"value": v, "count": n} for v, n in sorted(counts.items(), key=lambda i: (-i[1], i[0]))]

    def rows_of(self, columns: list[int], limit: int) -> list[tuple[str | None, ...]] | None:
        found = [row for row in zip(*(self.cells(n) for n in columns), strict=True) if any(c is not None for c in row)]
        return None if len(found) > limit else found


@dataclass
class MemoryWorkbook:
    sheets: list[MemoryTable]
    skipped: list[str] = field(default_factory=list)

    def common(self, first: tuple[int, int], second: tuple[int, int]) -> int:
        a = set(filter(None, self.sheets[first[0]].cells(first[1])))
        b = set(filter(None, self.sheets[second[0]].cells(second[1])))
        return len(a & b)


def workbook(*sheets: tuple[str, dict[str, list[Any]]], extra: tuple[tuple[str, str, dict[str, Any]], ...] = ()) -> MemoryWorkbook:
    """A workbook of the named sheets, each column's statistics worked out as A3's profile states
    them, with its overlaps with every other column of the workbook, and the ``extra`` overlaps given
    as (sheet, header, entry), such as a workspace's records (D69)."""
    tables = [MemoryTable(name, index, dict(data)) for index, (name, data) in enumerate(sheets)]
    distinct = {
        (t.index, n): set(filter(None, t.cells(n))) for t in tables for n in range(1, len(t.data) + 1)
    }
    for table in tables:
        for number, header in enumerate(table.data, start=1):
            cells = table.cells(number)
            filled = [c for c in cells if c is not None]
            counts = Counter(filled)
            delimiters = []
            for character in DELIMITERS:
                found = sum(character in c for c in filled)
                if found:
                    delimiters.append({"character": character, "cells": found, "share": round(found / len(filled), 3)})
            delimiters.sort(key=lambda d: -d["cells"])
            placeholders = [
                {"value": v, "count": n}
                for v, n in sorted(counts.items(), key=lambda i: (-i[1], i[0]))
                if v.strip().lower() in PLACEHOLDER_VALUES
                or (len(v.strip()) <= 2 and not re.search(r"[A-Za-z0-9]", v) and n >= 0.01 * len(filled))
            ]
            own = distinct[(table.index, number)]
            overlaps = []
            for (sheet_index, other), values in distinct.items():
                if (sheet_index, other) == (table.index, number) or not own:
                    continue
                shared = len(own & values)
                if shared:
                    overlaps.append(
                        {
                            "sheet": tables[sheet_index].name,
                            "column": get_column_letter(other),
                            "header": list(tables[sheet_index].data)[other - 1],
                            "values": shared,
                            "share": round(shared / len(own), 3),
                        }
                    )
            overlaps += [entry for sheet, column_header, entry in extra if (sheet, column_header) == (table.name, header)]
            overlaps.sort(key=lambda o: (-o["share"], -o["values"]))
            statistics = {
                "header": header,
                "letter": get_column_letter(number),
                "rows": table.rows,
                "filled": len(filled),
                "distinct": len(counts),
                "valueTypes": _types(filled),
                "candidateKey": len(filled) == table.rows and len(counts) == len(filled),
                "delimiters": delimiters,
                "placeholders": placeholders[:10],
                "values": [{"value": v, "count": n} for v, n in sorted(counts.items(), key=lambda i: (-i[1], i[0]))[:10]],
                "overlaps": overlaps[:5],
            }
            table.columns.append(
                Column(
                    number=number,
                    letter=statistics["letter"],
                    header=header,
                    rows=statistics["rows"],
                    filled=statistics["filled"],
                    distinct=statistics["distinct"],
                    value_types=statistics["valueTypes"],
                    candidate_key=statistics["candidateKey"],
                    delimiters=tuple(delimiters),
                    placeholders=tuple(placeholders[:10]),
                    values=tuple(statistics["values"]),
                    overlaps=tuple(overlaps[:5]),
                    spaced=sum(bool(re.search(r"\s", c)) for c in filled),
                    guids=sum(is_guid(c) for c in filled),
                    longest=max((len(c) for c in filled), default=0),
                    average=sum(len(c) for c in filled) / len(filled) if filled else 0.0,
                )
            )
    return MemoryWorkbook(tables)
