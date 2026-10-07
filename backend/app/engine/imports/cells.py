"""A file's cell as an attribute value (INTEGRATION_API §J2).

A workbook cell arrives typed (text, a number, a boolean, a date), a CSV cell as text. Each becomes
the value the API would take for the attribute's value type, then goes through the attribute
registry (``records/values.py``: ``normalize_value``, ``stored_json_value``), so it is checked and
put in its canonical form there, as every write's values are. A value that does not convert is
``INVALID_ATTRIBUTE_VALUE``; out of range, the registry's own code.

An empty cell, or one holding only spaces, is no value. Text is never trimmed otherwise.
"""

import json
import re
from datetime import date, datetime, time
from decimal import Decimal, InvalidOperation
from typing import Any

from ...errors import api_error
from ...models.schema import AttributeTypeDefinition
from ..records.values import normalize_value, stored_json_value

_INTEGER = re.compile(r"^[+-]?\d+$")
_BOOLEANS = {"true": True, "false": False}
# Excel writes characters XML cannot hold as _xHHHH_; _x005F_ escapes a literal underscore.
_EXCEL_ESCAPE = re.compile(r"_x([0-9A-Fa-f]{4})_")


def is_empty(raw: Any) -> bool:
    return raw is None or (isinstance(raw, str) and not raw.strip())


def cell_text(raw: Any) -> str:
    """A cell as text, as it is matched against names, IDs and value maps: a whole number without
    a decimal point, a boolean as ``true`` or ``false``, a date ISO 8601."""
    if isinstance(raw, bool):
        return "true" if raw else "false"
    if isinstance(raw, float) and raw.is_integer():
        return str(int(raw))
    if isinstance(raw, datetime):
        return raw.date().isoformat() if raw.time() == time() else raw.isoformat()
    if isinstance(raw, date):
        return raw.isoformat()
    return str(raw)


def decode_excel_text(text: str) -> str:
    """Excel's ``_xHHHH_`` escapes decoded, as the export writes them (J1)."""
    if "_x" not in text:
        return text
    return _EXCEL_ESCAPE.sub(lambda match: chr(int(match.group(1), 16)), text)


def attribute_value(definition: AttributeTypeDefinition, raw: Any) -> Any:
    """The cell's canonical JSON value for the attribute, or ``None`` for an empty cell."""
    if is_empty(raw):
        return None
    try:
        typed = _typed(definition.valueType, raw)
    except TypeError, ValueError, InvalidOperation, json.JSONDecodeError:
        raise api_error(
            422,
            "INVALID_ATTRIBUTE_VALUE",
            f"Attribute '{definition.key}' must be {definition.valueType}; the cell holds "
            f"'{cell_text(raw)[:80]}'",
        ) from None
    return stored_json_value(normalize_value(definition, typed))


def _typed(value_type: str, raw: Any) -> Any:
    if value_type in {"text", "longText"}:
        return cell_text(raw)
    if value_type == "integer":
        if isinstance(raw, bool):
            raise TypeError
        if isinstance(raw, int):
            return raw
        if isinstance(raw, float):
            if not raw.is_integer():
                raise ValueError
            return int(raw)
        text = str(raw).strip()
        if not _INTEGER.match(text):
            raise ValueError
        return int(text)
    if value_type == "decimal":
        if isinstance(raw, bool):
            raise TypeError
        if isinstance(raw, int | float):
            return Decimal(repr(raw)) if isinstance(raw, float) else Decimal(raw)
        value = Decimal(str(raw).strip())
        if not value.is_finite():
            raise ValueError
        return value
    if value_type == "boolean":
        if isinstance(raw, bool):
            return raw
        if isinstance(raw, str) and raw.strip().lower() in _BOOLEANS:
            return _BOOLEANS[raw.strip().lower()]
        raise ValueError
    if value_type == "date":
        if isinstance(raw, datetime):
            if raw.time() != time():
                raise ValueError
            return raw.date()
        if isinstance(raw, date):
            return raw
        return date.fromisoformat(str(raw).strip())
    if value_type == "dateTime":
        if isinstance(raw, datetime):
            return raw
        if isinstance(raw, date):
            return datetime.combine(raw, time())
        return datetime.fromisoformat(str(raw).strip())
    if value_type == "json":
        return json.loads(raw) if isinstance(raw, str) else raw
    return raw


def flag_set(raw: Any, true_values: list[str]) -> bool:
    """Whether a flag column's cell counts as set: a boolean TRUE, the number 1, or one of the
    binding's ``trueValues`` ignoring case."""
    if is_empty(raw):
        return False
    if isinstance(raw, bool):
        return raw
    if isinstance(raw, int | float):
        return raw == 1
    return str(raw).strip().lower() in {value.lower() for value in true_values}
