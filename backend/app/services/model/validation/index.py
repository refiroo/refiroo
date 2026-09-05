"""Key indexes over a parsed model, plus the uniqueness rules that build them."""

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

from ....common.json_pointer import pointer_segment
from ....models.schema import (
    ApplicationDefinition,
    AttributeTypeDefinition,
    EngineModel,
    ObjectTypeDefinition,
    RelationTypeDefinition,
)
from ..diagnostics import ModelReferenceError


@dataclass(frozen=True)
class ModelIndex:
    """Definitions of one model keyed for lookup by the reference rules."""

    attribute_types: dict[str, AttributeTypeDefinition]
    object_types: dict[str, ObjectTypeDefinition]
    relation_types: dict[str, RelationTypeDefinition]
    applications: dict[str, ApplicationDefinition]


def build_index(model: EngineModel) -> ModelIndex:
    """Index every top-level collection, rejecting duplicate keys as it goes."""
    return ModelIndex(
        attribute_types=_unique_map(model.attributeTypes, "attribute type", "attributeTypes"),
        object_types=_unique_map(model.objectTypes, "object type", "objectTypes"),
        relation_types=_unique_map(model.relationTypes, "relation type", "relationTypes"),
        applications=_unique_map(model.applications, "application", "applications"),
    )


def _unique_map(items: Sequence[Any], label: str, collection: str) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for item in items:
        if item.key in result:
            raise ModelReferenceError(
                "duplicate_key",
                f"/{collection}/{pointer_segment(item.key)}",
                f"Duplicate {label} key '{item.key}'",
            )
        result[item.key] = item
    return result
