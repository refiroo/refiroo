"""Rules for relation types, permitted object-type triples and parent containment."""

from ....common.json_pointer import pointer_segment, relation_path
from ....models.schema import EngineModel, ObjectTypeRelationDefinition
from ..diagnostics import ModelReferenceError
from .index import ModelIndex


def check_relation_type_keys(model: EngineModel, _index: ModelIndex) -> None:
    """Relation keys and reverse keys share one namespace."""
    seen: set[str] = set()
    for relation in model.relationTypes:
        for field, key in (("key", relation.key), ("reverseKey", relation.reverseKey)):
            if key in seen:
                raise ModelReferenceError(
                    "duplicate_key",
                    f"/relationTypes/{pointer_segment(relation.key)}/{field}",
                    f"Duplicate relation or reverse key '{key}'",
                )
            seen.add(key)


def check_object_type_relations(model: EngineModel, index: ModelIndex) -> None:
    identities: set[tuple[str, str, str]] = set()
    for allowed in model.objectTypeRelations:
        identity = _identity(allowed)
        path = relation_path(identity)
        _check_references(allowed, identity, path, index)
        _check_unique_features(allowed, path, index)
        if identity in identities:
            raise ModelReferenceError(
                "duplicate_key", path, f"Duplicate object-type relation {identity}"
            )
        identities.add(identity)


def check_parent_relations(model: EngineModel, _index: ModelIndex) -> None:
    """A declared parent relation must be a permitted triple ending at the child type."""
    for object_type in model.objectTypes:
        for parent_relation in object_type.behavior.get("parentRelationTypeKeys", []):
            if not any(
                item.relationTypeKey == parent_relation
                and item.toObjectTypeKey == object_type.key
                for item in model.objectTypeRelations
            ):
                raise ModelReferenceError(
                    "invalid_reference",
                    f"/objectTypes/{pointer_segment(object_type.key)}/behavior/"
                    f"parentRelationTypeKeys/{pointer_segment(parent_relation)}",
                    f"Object type '{object_type.key}' has incompatible parent relation "
                    f"'{parent_relation}'",
                )


def _identity(allowed: ObjectTypeRelationDefinition) -> tuple[str, str, str]:
    return (
        allowed.relationTypeKey,
        allowed.fromObjectTypeKey,
        allowed.toObjectTypeKey,
    )


def _check_references(
    allowed: ObjectTypeRelationDefinition,
    identity: tuple[str, str, str],
    path: str,
    index: ModelIndex,
) -> None:
    if allowed.relationTypeKey not in index.relation_types:
        raise ModelReferenceError(
            "unknown_relation_type",
            f"{path}/relationTypeKey",
            f"Object-type relation references unknown relation type "
            f"'{allowed.relationTypeKey}'",
        )
    if allowed.fromObjectTypeKey not in index.object_types:
        raise ModelReferenceError(
            "unknown_object_type",
            f"{path}/fromObjectTypeKey",
            f"Object-type relation has unknown source '{allowed.fromObjectTypeKey}'",
        )
    if allowed.toObjectTypeKey not in index.object_types:
        raise ModelReferenceError(
            "unknown_object_type",
            f"{path}/toObjectTypeKey",
            f"Object-type relation has unknown target '{allowed.toObjectTypeKey}'",
        )
    unknown_attributes = set(allowed.attributeTypeKeys) - set(index.attribute_types)
    if unknown_attributes:
        first_unknown = next(
            key for key in allowed.attributeTypeKeys if key in unknown_attributes
        )
        raise ModelReferenceError(
            "unknown_attribute_type",
            f"{path}/attributeTypeKeys/{pointer_segment(first_unknown)}",
            f"Object-type relation '{allowed.relationTypeKey}' has unknown attributes: "
            f"{sorted(unknown_attributes)}",
        )


def _check_unique_features(
    allowed: ObjectTypeRelationDefinition, path: str, index: ModelIndex
) -> None:
    unique_ancestor = allowed.features.get("uniqueToAncestorTypeKey")
    if unique_ancestor is not None and (
        not isinstance(unique_ancestor, str) or unique_ancestor not in index.object_types
    ):
        raise ModelReferenceError(
            "invalid_reference",
            f"{path}/features/uniqueToAncestorTypeKey",
            f"Object-type relation '{allowed.relationTypeKey}' references unknown unique "
            f"ancestor object type '{unique_ancestor}'",
        )

    unique_condition = allowed.features.get("uniqueWhenToAttributeEquals")
    if unique_condition is None:
        return
    target_bindings = {
        binding.attributeTypeKey
        for binding in index.object_types[allowed.toObjectTypeKey].attributes
    }
    if (
        not isinstance(unique_condition, dict)
        or set(unique_condition) != {"attributeTypeKey", "value"}
        or unique_condition.get("attributeTypeKey") not in target_bindings
    ):
        raise ModelReferenceError(
            "invalid_model",
            f"{path}/features/uniqueWhenToAttributeEquals",
            f"Object-type relation '{allowed.relationTypeKey}' has an invalid "
            "uniqueWhenToAttributeEquals condition",
        )
