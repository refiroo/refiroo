"""Rules for object type declarations: bindings, display attribute and object-level validation."""

from ....common.json_pointer import pointer_segment
from ....models.schema import EngineModel, ObjectTypeAttributeDefinition, ObjectTypeDefinition
from ..diagnostics import ModelReferenceError
from .index import ModelIndex


def check(model: EngineModel, index: ModelIndex) -> None:
    for object_type in model.objectTypes:
        bindings = _binding_map(object_type)
        _check_bound_attribute_types(object_type, bindings, index)
        _check_display_attribute(object_type, bindings)
        _check_at_least_one_of(object_type, bindings)
        _check_effective_period(model, object_type, bindings)


def _base_path(object_type: ObjectTypeDefinition) -> str:
    return f"/objectTypes/{pointer_segment(object_type.key)}"


def _binding_map(
    object_type: ObjectTypeDefinition,
) -> dict[str, ObjectTypeAttributeDefinition]:
    result: dict[str, ObjectTypeAttributeDefinition] = {}
    for binding in object_type.attributes:
        if binding.attributeTypeKey in result:
            raise ModelReferenceError(
                "DUPLICATE_KEY",
                f"{_base_path(object_type)}/attributes/"
                f"{pointer_segment(binding.attributeTypeKey)}",
                f"Duplicate attribute binding '{binding.attributeTypeKey}' in "
                f"'{object_type.key}'",
            )
        result[binding.attributeTypeKey] = binding
    return result


def _check_bound_attribute_types(
    object_type: ObjectTypeDefinition,
    bindings: dict[str, ObjectTypeAttributeDefinition],
    index: ModelIndex,
) -> None:
    for binding in object_type.attributes:
        if binding.attributeTypeKey not in index.attribute_types:
            raise ModelReferenceError(
                "UNKNOWN_ATTRIBUTE_TYPE",
                f"{_base_path(object_type)}/attributes/"
                f"{pointer_segment(binding.attributeTypeKey)}/attributeTypeKey",
                f"Object type '{object_type.key}' references unknown attribute type "
                f"'{binding.attributeTypeKey}'",
            )


def _check_display_attribute(
    object_type: ObjectTypeDefinition, bindings: dict[str, ObjectTypeAttributeDefinition]
) -> None:
    display_key = object_type.displayAttributeTypeKey
    if display_key and display_key not in bindings:
        raise ModelReferenceError(
            "INVALID_MODEL",
            f"{_base_path(object_type)}/displayAttributeTypeKey",
            f"Object type '{object_type.key}' display attribute '{display_key}' is not attached",
        )


def _check_effective_period(
    model: EngineModel,
    object_type: ObjectTypeDefinition,
    bindings: dict[str, ObjectTypeAttributeDefinition],
) -> None:
    """Schema 0.8 (ADR-038): two distinct ``date`` attributes the type binds."""
    period = object_type.effectivePeriod
    if period is None:
        return
    path = f"{_base_path(object_type)}/effectivePeriod"
    for role in ("startAttributeTypeKey", "endAttributeTypeKey"):
        key = getattr(period, role)
        if key not in bindings:
            raise ModelReferenceError(
                "UNKNOWN_ATTRIBUTE_TYPE",
                f"{path}/{role}",
                f"Object type '{object_type.key}' effective period names '{key}', which it does "
                "not bind",
            )
        definition = model.attribute_type(key)
        if definition is None or definition.valueType != "date":
            raise ModelReferenceError(
                "INVALID_MODEL",
                f"{path}/{role}",
                f"Object type '{object_type.key}' effective period attribute '{key}' must be a "
                "date attribute",
            )
    if period.startAttributeTypeKey == period.endAttributeTypeKey:
        raise ModelReferenceError(
            "INVALID_MODEL",
            f"{path}/endAttributeTypeKey",
            f"Object type '{object_type.key}' effective period needs two different attributes",
        )


def _check_at_least_one_of(
    object_type: ObjectTypeDefinition, bindings: dict[str, ObjectTypeAttributeDefinition]
) -> None:
    at_least_one = object_type.validation.get("atLeastOneOf", [])
    if not at_least_one:
        return
    path = f"{_base_path(object_type)}/validation/atLeastOneOf"
    if not isinstance(at_least_one, (list, tuple)) or not all(
        isinstance(key, str) for key in at_least_one
    ):
        raise ModelReferenceError(
            "INVALID_MODEL",
            path,
            f"Object type '{object_type.key}' validation.atLeastOneOf must be a list of "
            "attribute keys",
        )
    if len(at_least_one) != len(set(at_least_one)):
        raise ModelReferenceError(
            "DUPLICATE_KEY",
            path,
            f"Object type '{object_type.key}' validation.atLeastOneOf has duplicate keys",
        )
    unknown = set(at_least_one) - set(bindings)
    if unknown:
        raise ModelReferenceError(
            "UNKNOWN_ATTRIBUTE_TYPE",
            path,
            f"Object type '{object_type.key}' validation.atLeastOneOf references unbound "
            f"attributes: {sorted(unknown)}",
        )
