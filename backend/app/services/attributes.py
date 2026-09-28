from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..common.time import as_utc
from ..errors import api_error
from ..models.api import AttributeValueResponse
from ..models.database import AttributeValue, RdmObject
from ..models.schema import AttributeTypeDefinition, EngineModel, ObjectTypeDefinition

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
    apply_defaults: bool = True,
    allow_read_only: bool = False,
) -> dict[str, Any]:
    bindings = {item.attributeTypeKey: item for item in object_type.attributes}
    unknown = set(attributes) - set(bindings)
    if unknown:
        raise api_error(422, "unknown_attributes", f"Unknown attributes: {sorted(unknown)}")

    read_only = [key for key in attributes if bindings[key].readOnly]
    if read_only and not allow_read_only:
        raise api_error(
            422,
            "read_only_attributes",
            f"Read-only fields cannot be changed: {_field_names(model, read_only)}",
            {"attributeTypeKeys": read_only},
        )

    result = dict(attributes)
    if not partial and apply_defaults:
        for binding in object_type.attributes:
            definition = _attribute_definition(model, binding.attributeTypeKey)
            if binding.attributeTypeKey not in result and definition.default is not None:
                result[binding.attributeTypeKey] = definition.default

    missing = [
        binding.attributeTypeKey
        for binding in object_type.attributes
        if binding.required
        and (not partial or binding.attributeTypeKey in attributes)
        and (
            binding.attributeTypeKey not in result
            or result[binding.attributeTypeKey] is None
            or result[binding.attributeTypeKey] == ""
        )
    ]
    if missing:
        raise api_error(
            422,
            "missing_required_attributes",
            f"Required fields are missing: {_field_names(model, missing)}",
            {"attributeTypeKeys": missing},
        )

    return {
        key: normalize_value(_attribute_definition(model, key), value)
        for key, value in result.items()
    }


def validate_object_attribute_rules(
    object_type: ObjectTypeDefinition, attributes: dict[str, Any]
) -> None:
    at_least_one = object_type.validation.get("atLeastOneOf", [])
    if at_least_one and not any(
        key in attributes and attributes[key] is not None and attributes[key] != ""
        for key in at_least_one
    ):
        raise api_error(
            422,
            "object_attribute_rule_violation",
            f"At least one of these attributes is required: {at_least_one}",
            {"rule": "atLeastOneOf", "attributeTypeKeys": at_least_one},
        )


def validate_attribute_change(
    session: Session,
    model: EngineModel,
    object_type: ObjectTypeDefinition,
    item: RdmObject,
    attributes: dict[str, Any],
) -> None:
    """Check a pending attribute write against the object's other stored values.

    Object-level rules are evaluated over the merged result rather than the submitted subset, and
    uniqueness excludes the object being written so a no-op write never collides with itself.
    """
    merged = current_attribute_values(session, item.id)
    merged.update(attributes)
    validate_object_attribute_rules(object_type, merged)
    check_attribute_uniqueness(
        session,
        model,
        attributes,
        workspace_key=item.workspace_key,
        exclude_object_id=item.id,
    )


def apply_attribute_values(
    session: Session,
    model: EngineModel,
    object_type: ObjectTypeDefinition,
    item: RdmObject,
    attributes: dict[str, Any],
) -> None:
    """Validate, persist and re-check a live attribute write as a single sequence.

    Every path that writes attribute values must run these steps in this order; keeping them here
    stops a caller from performing the write while skipping one of the checks.  The caller is
    responsible for claiming the object's optimistic-concurrency version first.
    """
    from .relations import validate_scoped_relations

    validate_attribute_change(session, model, object_type, item, attributes)
    save_attribute_values(session, model, item.id, attributes)
    validate_scoped_relations(session, model, item, moved=False)


def current_attribute_values(session: Session, object_id: str) -> dict[str, Any]:
    return {
        key: value
        for key, (_value_id, value) in load_attribute_values(session, [object_id])[object_id].items()
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
            "invalid_attribute_value",
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
                "attribute_below_minimum",
                f"Attribute '{definition.key}' must be at least {minimum}",
            )
        if maximum is not None and normalized > maximum:
            raise api_error(
                422,
                "attribute_above_maximum",
                f"Attribute '{definition.key}' must be at most {maximum}",
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
        # Change set rows carry the JSON form; typed columns need the declared Python type.
        _set_row_value(row, definition.valueType, normalize_value(definition, value))


def load_attribute_values(
    session: Session, object_ids: list[str]
) -> dict[str, dict[str, tuple[str, Any]]]:
    result: dict[str, dict[str, tuple[str, Any]]] = {object_id: {} for object_id in object_ids}
    if not object_ids:
        return result
    for row in session.scalars(
        select(AttributeValue).where(AttributeValue.object_id.in_(object_ids))
    ):
        result[row.object_id][row.attribute_type_key] = (row.id, _get_row_value(row))
    return result


def check_attribute_uniqueness(
    session: Session,
    model: EngineModel,
    attributes: dict[str, Any],
    *,
    workspace_key: str,
    exclude_object_id: str | None = None,
) -> None:
    for key, value in attributes.items():
        if value is None or value == "":
            continue
        definition = _attribute_definition(model, key)
        if not definition.features.get("unique"):
            continue
        column = getattr(AttributeValue, VALUE_COLUMNS[definition.valueType])
        statement = (
            select(AttributeValue.id)
            .join(RdmObject, AttributeValue.object_id == RdmObject.id)
            .where(
                AttributeValue.attribute_type_key == key,
                column == value,
                RdmObject.workspace_key == workspace_key,
            )
        )
        if exclude_object_id is not None:
            statement = statement.where(RdmObject.id != exclude_object_id)
        if session.scalar(statement.limit(1)):
            raise api_error(
                409,
                "duplicate_attribute_value",
                f"Attribute '{definition.name or key}' must be unique",
            )


def load_attribute_value(
    session: Session, object_id: str, attribute_type_key: str
) -> AttributeValue:
    row = session.scalar(
        select(AttributeValue).where(
            AttributeValue.object_id == object_id,
            AttributeValue.attribute_type_key == attribute_type_key,
        )
    )
    if not row:
        raise api_error(
            404,
            "attribute_not_found",
            f"Attribute '{attribute_type_key}' has no value on object '{object_id}'",
        )
    return row


def remove_attribute_value_row(
    session: Session, object_id: str, attribute_type_key: str
) -> None:
    """Physically delete one live attribute value row (404 when absent)."""
    row = load_attribute_value(session, object_id, attribute_type_key)
    session.delete(row)


def ensure_attribute_value_absent(
    session: Session, object_id: str, attribute_type_key: str
) -> None:
    row = session.scalar(
        select(AttributeValue.id).where(
            AttributeValue.object_id == object_id,
            AttributeValue.attribute_type_key == attribute_type_key,
        )
    )
    if row:
        raise api_error(
            409,
            "attribute_already_exists",
            f"Attribute '{attribute_type_key}' already has a value on object '{object_id}'",
        )


def validate_deletable_attribute(
    object_type: ObjectTypeDefinition, attribute_type_key: str
) -> None:
    binding = next(
        (item for item in object_type.attributes if item.attributeTypeKey == attribute_type_key),
        None,
    )
    if binding is None:
        raise api_error(
            422,
            "unknown_attributes",
            f"Attribute type '{attribute_type_key}' is not defined on object type "
            f"'{object_type.key}'",
        )
    if binding.readOnly:
        raise api_error(
            422,
            "read_only_attributes",
            f"Read-only attributes: [{attribute_type_key}]",
        )
    if binding.required:
        raise api_error(
            422,
            "cannot_delete_required_attribute",
            f"Attribute '{attribute_type_key}' is required and cannot be deleted",
        )


def build_attribute_value_response(
    model: EngineModel, row: AttributeValue, object_version: int
) -> AttributeValueResponse:
    key = row.attribute_type_key
    definition = model.attribute_type(key)
    return AttributeValueResponse(
        id=row.id,
        attributeTypeKey=key,
        name=definition.name if definition else key,
        valueType=definition.valueType if definition else "text",
        value=_get_row_value(row),
        objectVersion=object_version,
    )


def _set_row_value(row: AttributeValue, value_type: str, value: Any) -> None:
    for column in set(VALUE_COLUMNS.values()):
        setattr(row, column, None)
    setattr(row, VALUE_COLUMNS[value_type], value)


def _get_row_value(row: AttributeValue) -> Any:
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


def _attribute_definition(model: EngineModel, key: str) -> AttributeTypeDefinition:
    definition = model.attribute_type(key)
    if not definition:
        raise api_error(500, "internal_error", f"Unknown model attribute '{key}'")
    return definition


def _field_names(model: EngineModel, keys: list[str]) -> str:
    """Model field names for a user-facing message; keys stay in the error details."""
    return ", ".join(_attribute_definition(model, key).name for key in keys)
