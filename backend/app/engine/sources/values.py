"""A source file's cell as it is staged, and back (Product 0.10 A3, D66).

A staged cell keeps what the reader gave, so an import bound from staged rows converts it exactly
as it converts the file's cell (``imports/cells.py``): its **kind** (``text``, ``integer``,
``decimal``, ``boolean``, ``date``, ``dateTime``), its **text** as an import matches it
(``cell_text``), and its **value** as JSON: text, numbers and booleans as themselves, a date, a
timestamp or a time of day as ``{"$": "date" | "dateTime" | "time", "v": ISO 8601}``. An empty
cell, or one of spaces only, is not staged: an import reads it as no value either.
"""

import json
import math
from datetime import date, datetime, time
from typing import Any

from ..imports.cells import cell_text, is_empty

_TAG = "$"


def staged(raw: Any) -> tuple[str, str, str] | None:
    """The cell's kind, text and value (JSON text), or ``None`` for an empty cell."""
    if is_empty(raw):
        return None
    if isinstance(raw, bool):
        kind, value = "boolean", raw
    elif isinstance(raw, int):
        kind, value = "integer", raw
    elif isinstance(raw, float) and math.isfinite(raw):
        kind, value = "decimal", raw
    elif isinstance(raw, datetime):
        kind = "date" if raw.time() == time() and raw.tzinfo is None else "dateTime"
        value = {_TAG: "dateTime", "v": raw.isoformat()}
    elif isinstance(raw, date):
        kind, value = "date", {_TAG: "date", "v": raw.isoformat()}
    elif isinstance(raw, time):
        kind, value = "text", {_TAG: "time", "v": raw.isoformat()}
    else:
        kind, value = "text", _clean(str(raw))
    text = _clean(cell_text(raw))
    return kind, text, json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def unstaged(value: Any) -> Any:
    """The reader's value back from its staged JSON."""
    if isinstance(value, dict):
        tag, text = value.get(_TAG), value.get("v")
        if tag == "dateTime":
            return datetime.fromisoformat(text)
        if tag == "date":
            return date.fromisoformat(text)
        if tag == "time":
            return time.fromisoformat(text)
    return value


def _clean(text: str) -> str:
    # PostgreSQL text holds no NUL character.
    return text.replace("\x00", "")
