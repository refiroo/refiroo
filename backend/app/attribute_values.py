from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from .database import AttributeValue
from .model_schema import AttributeTypeDefinition, EngineModel, ObjectTypeDefinition

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


def validate_attributes(
    model: EngineModel,
    object_type: ObjectTypeDefinition,
    attributes: dict[str, Any],
    *,
    partial: bool = False,
) -> dict[str, Any]:
    bindings = {item.attributeTypeKey: item for item in object_type.attributes}
    unknown = set(attributes) - set(bindings)
    if unknown:
        raise HTTPException(status_code=422, detail=f"Unknown attributes: {sorted(unknown)}")

    read_only = [key for key in attributes if bindings[key].readOnly]
    if read_only:
        raise HTTPException(status_code=422, detail=f"Read-only attributes: {read_only}")

    result = dict(attributes)
    if not partial:
        for binding in object_type.attributes:
            definition = _attribute_definition(model, binding.attributeTypeKey)
            if binding.attributeTypeKey not in result and definition.default is not None:
                result[binding.attributeTypeKey] = definition.default
        missing = [
            binding.attributeTypeKey
            for binding in object_type.attributes
            if binding.required
            and (
                binding.attributeTypeKey not in result
                or result[binding.attributeTypeKey] is None
                or result[binding.attributeTypeKey] == ""
            )
        ]
        if missing:
            raise HTTPException(status_code=422, detail=f"Required attributes missing: {missing}")

    return {
        key: normalize_value(_attribute_definition(model, key), value)
        for key, value in result.items()
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
            normalized = Decimal(str(value))
        elif definition.valueType == "boolean":
            if not isinstance(value, bool):
                raise TypeError
            normalized = value
        elif definition.valueType == "date":
            normalized = value if isinstance(value, date) else date.fromisoformat(value)
        elif definition.valueType == "dateTime":
            normalized = value if isinstance(value, datetime) else datetime.fromisoformat(value)
        else:
            normalized = value
    except (TypeError, ValueError, InvalidOperation):
        raise HTTPException(
            status_code=422,
            detail=f"Attribute '{definition.key}' must be {definition.valueType}",
        ) from None

    minimum = definition.validation.get("minimum")
    maximum = definition.validation.get("maximum")
    if minimum is not None and normalized < minimum:
        raise HTTPException(
            status_code=422,
            detail=f"Attribute '{definition.key}' must be at least {minimum}",
        )
    if maximum is not None and normalized > maximum:
        raise HTTPException(
            status_code=422,
            detail=f"Attribute '{definition.key}' must be at most {maximum}",
        )
    return normalized


def save_attribute_values(
    session: Session,
    model: EngineModel,
    object_id: str,
    attributes: dict[str, Any],
) -> None:
    existing = {
        item.attribute_type_key: item
        for item in session.scalars(
            select(AttributeValue).where(
                AttributeValue.object_id == object_id,
                AttributeValue.attribute_type_key.in_(attributes),
            )
        )
    }
    for key, value in attributes.items():
        definition = _attribute_definition(model, key)
        row = existing.get(key)
        if row is None:
            row = AttributeValue(
                object_id=object_id,
                attribute_type_key=key,
                value_type=definition.valueType,
            )
            session.add(row)
        else:
            row.version += 1
        _set_row_value(row, definition.valueType, value)


def load_attribute_values(session: Session, object_ids: list[str]) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {object_id: {} for object_id in object_ids}
    if not object_ids:
        return result
    for row in session.scalars(
        select(AttributeValue).where(AttributeValue.object_id.in_(object_ids))
    ):
        result[row.object_id][row.attribute_type_key] = _get_row_value(row)
    return result


def _set_row_value(row: AttributeValue, value_type: str, value: Any) -> None:
    for column in set(VALUE_COLUMNS.values()):
        setattr(row, column, None)
    setattr(row, VALUE_COLUMNS[value_type], value)


def _get_row_value(row: AttributeValue) -> Any:
    value = getattr(row, VALUE_COLUMNS[row.value_type])
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    return value


def _attribute_definition(model: EngineModel, key: str) -> AttributeTypeDefinition:
    definition = model.attribute_type(key)
    if not definition:
        raise HTTPException(status_code=500, detail=f"Unknown model attribute '{key}'")
    return definition
