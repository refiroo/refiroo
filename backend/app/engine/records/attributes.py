from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from ...errors import api_error
from ...models.database import AttributeValue, RdmObject
from ...models.schema import AttributeTypeDefinition, EngineModel, ObjectTypeDefinition
from . import rules
from .context import LiveLookup
from .relations import validate_scoped_relations
from .values import normalize_value, row_value
from .writes import LiveWrites


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
    rules.effective_period(object_type, attributes)


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
    rules.unique_values(LiveLookup.of(session, item.workspace_key), model, item.id, attributes)


def apply_attribute_values(
    writes: LiveWrites,
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
    validate_attribute_change(writes.session, model, object_type, item, attributes)
    writes.save_values(model, item.id, attributes)
    validate_scoped_relations(writes.session, model, item, moved=False)


def current_attribute_values(session: Session, object_id: str) -> dict[str, Any]:
    return {
        key: value
        for key, (_value_id, value) in load_attribute_values(session, [object_id])[object_id].items()
    }


def load_attribute_values(
    session: Session, object_ids: list[str]
) -> dict[str, dict[str, tuple[str, Any]]]:
    result: dict[str, dict[str, tuple[str, Any]]] = {object_id: {} for object_id in object_ids}
    if not object_ids:
        return result
    for row in session.scalars(
        select(AttributeValue).where(AttributeValue.object_id.in_(object_ids))
    ):
        result[row.object_id][row.attribute_type_key] = (row.id, row_value(row))
    return result


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


def _attribute_definition(model: EngineModel, key: str) -> AttributeTypeDefinition:
    definition = model.attribute_type(key)
    if not definition:
        raise api_error(500, "internal_error", f"Unknown model attribute '{key}'")
    return definition


def _field_names(model: EngineModel, keys: list[str]) -> str:
    """Model field names for a user-facing message; keys stay in the error details."""
    return ", ".join(_attribute_definition(model, key).name for key in keys)
