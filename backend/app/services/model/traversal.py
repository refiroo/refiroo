"""Reads over a model's object-type graph shared by model validation and runtime queries.

They take only the model, so validation can decide what a list may sort by exactly as the query
builder will, without importing persistence.
"""

from collections.abc import Sequence

from ...models.schema import EngineModel, ObjectTypeDefinition


def parent_type_keys(model: EngineModel, object_type_key: str) -> set[str]:
    """The object types that can directly contain a record of ``object_type_key``."""
    child = model.object_type(object_type_key)
    if child is None:
        return set()
    parent_relations = set(child.behavior.get("parentRelationTypeKeys", []))
    return {
        allowed.fromObjectTypeKey
        for allowed in model.objectTypeRelations
        if allowed.relationTypeKey in parent_relations and allowed.toObjectTypeKey == child.key
    }


def ancestor_type_keys(model: EngineModel, object_type_key: str) -> set[str]:
    """The object types a record of ``object_type_key`` can sit under, at any depth."""
    found: set[str] = set()
    pending = [object_type_key]
    while pending:
        for parent in parent_type_keys(model, pending.pop()) - found:
            found.add(parent)
            pending.append(parent)
    return found


def related_object_types(
    model: EngineModel,
    anchor_type_key: str,
    direction: str,
    relation_type_keys: Sequence[str] | None,
) -> tuple[ObjectTypeDefinition, ...]:
    """The object types the model allows at the other end of the anchor's listed relations."""
    keys: list[str] = []
    for allowed in model.objectTypeRelations:
        if relation_type_keys and allowed.relationTypeKey not in relation_type_keys:
            continue
        if direction in {"outgoing", "both"} and allowed.fromObjectTypeKey == anchor_type_key:
            keys.append(allowed.toObjectTypeKey)
        if direction in {"incoming", "both"} and allowed.toObjectTypeKey == anchor_type_key:
            keys.append(allowed.fromObjectTypeKey)
    definitions = (model.object_type(key) for key in dict.fromkeys(keys))
    return tuple(definition for definition in definitions if definition is not None)
