"""Coherence rules for global attribute type declarations."""

from decimal import Decimal, InvalidOperation

from ....common.json_pointer import pointer_segment
from ....models.schema import AttributeTypeDefinition, EngineModel
from ..diagnostics import ModelReferenceError
from .index import ModelIndex

NUMERIC_VALUE_TYPES = {"integer", "decimal"}
UNIQUE_UNSUPPORTED_VALUE_TYPES = {"json"}


def check(model: EngineModel, _index: ModelIndex) -> None:
    for attribute in model.attributeTypes:
        _check_uniqueness_support(attribute)
        _check_bounds(attribute)


def _base_path(attribute: AttributeTypeDefinition) -> str:
    return f"/attributeTypes/{pointer_segment(attribute.key)}"


def _check_uniqueness_support(attribute: AttributeTypeDefinition) -> None:
    if attribute.features.get("unique") and attribute.valueType in UNIQUE_UNSUPPORTED_VALUE_TYPES:
        raise ModelReferenceError(
            "INVALID_MODEL",
            f"{_base_path(attribute)}/features/unique",
            f"Attribute type '{attribute.key}' declares 'unique' but valueType "
            f"'{attribute.valueType}' does not support uniqueness",
        )


def _check_bounds(attribute: AttributeTypeDefinition) -> None:
    for bound in ("minimum", "maximum"):
        if bound not in attribute.validation:
            continue
        path = f"{_base_path(attribute)}/validation/{bound}"
        if attribute.valueType not in NUMERIC_VALUE_TYPES:
            raise ModelReferenceError(
                "INVALID_MODEL",
                path,
                f"Attribute type '{attribute.key}' declares 'validation.{bound}' but valueType "
                f"'{attribute.valueType}' does not support numeric bounds",
            )
        value = attribute.validation[bound]
        if isinstance(value, bool) or not isinstance(value, (int, float, Decimal)):
            raise ModelReferenceError(
                "INVALID_MODEL",
                path,
                f"Attribute type '{attribute.key}' validation.{bound} must be a finite number",
            )
        try:
            numeric_value = Decimal(str(value))
        except (InvalidOperation, ValueError):
            numeric_value = Decimal("NaN")
        if not numeric_value.is_finite():
            raise ModelReferenceError(
                "INVALID_MODEL",
                path,
                f"Attribute type '{attribute.key}' validation.{bound} must be a finite number",
            )

    minimum = attribute.validation.get("minimum")
    maximum = attribute.validation.get("maximum")
    if (
        minimum is not None
        and maximum is not None
        and Decimal(str(minimum)) > Decimal(str(maximum))
    ):
        raise ModelReferenceError(
            "INVALID_MODEL",
            f"{_base_path(attribute)}/validation/minimum",
            f"Attribute type '{attribute.key}' validation.minimum must not exceed "
            "validation.maximum",
        )
