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


def _base_path(object_type: ObjectTypeDefinition) -> str:
    return f"/objectTypes/{pointer_segment(object_type.key)}"


def _binding_map(
    object_type: ObjectTypeDefinition,
) -> dict[str, ObjectTypeAttributeDefinition]:
    result: dict[str, ObjectTypeAttributeDefinition] = {}
    for binding in object_type.attributes:
        if binding.attributeTypeKey in result:
            raise ModelReferenceError(
                "duplicate_key",
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
                "unknown_attribute_type",
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
            "invalid_model",
            f"{_base_path(object_type)}/displayAttributeTypeKey",
            f"Object type '{object_type.key}' display attribute '{display_key}' is not attached",
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
            "invalid_model",
            path,
            f"Object type '{object_type.key}' validation.atLeastOneOf must be a list of "
            "attribute keys",
        )
    if len(at_least_one) != len(set(at_least_one)):
        raise ModelReferenceError(
            "duplicate_key",
            path,
            f"Object type '{object_type.key}' validation.atLeastOneOf has duplicate keys",
        )
    unknown = set(at_least_one) - set(bindings)
    if unknown:
        raise ModelReferenceError(
            "unknown_attribute_type",
            path,
            f"Object type '{object_type.key}' validation.atLeastOneOf references unbound "
            f"attributes: {sorted(unknown)}",
        )
