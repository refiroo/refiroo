"""One attribute value in its forms.

The declared type it is checked against, the JSON form change set and publication rows keep, and
the typed column live rows and the snapshot index store it in.
"""

from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any

from ...common.time import as_utc
from ...errors import api_error
from ...models.database import AttributeValue
from ...models.schema import AttributeTypeDefinition

# Value-type pairs a value may cross because nothing is lost (ADR-034, D40): a type change's mapped
# value, and a display attribute a migration's type mapping carries (0.11 V1).
WIDENINGS = frozenset({("text", "longText"), ("integer", "decimal")})

VALUE_COLUMNS = {
    "text": "text_value",
    "longText": "text_value",
    "integer": "integer_value",
    "decimal": "decimal_value",
    "boolean": "boolean_value",
    "date": "date_value",
    "dateTime": "datetime_value",
    "json": "json_value",
}


def normalize_value(definition: AttributeTypeDefinition, value: Any) -> Any:
    if value is None:
        return None
    try:
        if definition.valueType in {"text", "longText"}:
            if not isinstance(value, str):
                raise TypeError
            normalized = value
        elif definition.valueType == "integer":
            if isinstance(value, bool) or not isinstance(value, int):
                raise TypeError
            normalized = value
        elif definition.valueType == "decimal":
            if isinstance(value, bool):
                raise TypeError
            normalized = canonical_decimal(Decimal(str(value)))
            if not normalized.is_finite():
                raise ValueError
        elif definition.valueType == "boolean":
            if not isinstance(value, bool):
                raise TypeError
            normalized = value
        elif definition.valueType == "date":
            normalized = value if isinstance(value, date) else date.fromisoformat(value)
        elif definition.valueType == "dateTime":
            # One instant, one form: a zone-less value is UTC, as in filters and cursors.
            parsed = value if isinstance(value, datetime) else datetime.fromisoformat(value)
            normalized = as_utc(parsed)
        else:
            normalized = value
    except (TypeError, ValueError, InvalidOperation):
        raise api_error(
            422,
            "INVALID_ATTRIBUTE_VALUE",
            f"Attribute '{definition.key}' must be {definition.valueType}",
        ) from None

    minimum = definition.validation.get("minimum")
    maximum = definition.validation.get("maximum")
    if definition.valueType in {"integer", "decimal"}:
        if definition.valueType == "decimal":
            minimum = Decimal(str(minimum)) if minimum is not None else None
            maximum = Decimal(str(maximum)) if maximum is not None else None
        if minimum is not None and normalized < minimum:
            raise api_error(
                422,
                "ATTRIBUTE_BELOW_MINIMUM",
                f"Attribute '{definition.key}' must be at least {minimum}",
            )
        if maximum is not None and normalized > maximum:
            raise api_error(
                422,
                "ATTRIBUTE_ABOVE_MAXIMUM",
                f"Attribute '{definition.key}' must be at most {maximum}",
            )
    return normalized


def row_value(row: AttributeValue) -> Any:
    return stored_json_value(getattr(row, VALUE_COLUMNS[row.value_type]))


def stored_json_value(value: Any) -> Any:
    """Return the JSON form of a normalized value, as live reads and change set rows carry it."""
    if isinstance(value, Decimal):
        return format(canonical_decimal(value), "f")
    if isinstance(value, datetime):
        return as_utc(value).isoformat()
    if isinstance(value, date):
        return value.isoformat()
    return value


def typed_value_columns(value_type: str | None, value: Any) -> dict[str, Any]:
    """The typed columns for one attribute value held in a JSON ``attributes`` column.

    Change set, change-set base and publication rows keep values in their JSON form; their typed index
    (``snapshot_attribute_values``) stores them as live ``attribute_values`` rows do. Stored JSON
    was validated when written, so this converts without re-checking range rules; a value that no
    longer converts, or a key the owning release does not declare, is indexed as JSON only.
    """
    columns: dict[str, Any] = dict.fromkeys(set(VALUE_COLUMNS.values()))
    try:
        if value_type not in VALUE_COLUMNS:
            raise TypeError
        typed: Any = value
        if value is None or value_type == "json":
            pass
        elif value_type in {"text", "longText"}:
            if not isinstance(value, str):
                raise TypeError
        elif value_type == "integer":
            if isinstance(value, bool) or not isinstance(value, int):
                raise TypeError
        elif value_type == "decimal":
            if isinstance(value, bool):
                raise TypeError
            typed = canonical_decimal(Decimal(str(value)))
            if not typed.is_finite():
                raise ValueError
        elif value_type == "boolean":
            if not isinstance(value, bool):
                raise TypeError
        elif value_type == "date":
            typed = value if isinstance(value, date) else date.fromisoformat(value)
        elif value_type == "dateTime":
            typed = as_utc(value if isinstance(value, datetime) else datetime.fromisoformat(value))
    except (TypeError, ValueError, InvalidOperation):
        columns["json_value"] = value
        return {"value_type": "json", **columns}
    columns[VALUE_COLUMNS[value_type]] = typed
    return {"value_type": value_type, **columns}


def canonical_decimal(value: Decimal) -> Decimal:
    """Drop trailing zeros so equal decimals share one form in every context.

    A live read comes back padded to the column scale (``12.5000000000``) while a change set row keeps the
    submitted text; both must read, compare and deduplicate as ``12.5``.
    """
    return Decimal(0) if value.is_zero() else value.normalize()
