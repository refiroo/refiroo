"""Rules for relation types, permitted object-type triples and parent containment."""

from ....common.json_pointer import pointer_segment, relation_path
from ....models.schema import EngineModel, ObjectTypeRelationDefinition
from ..candidates import CandidateCriterionError, check_candidate_criteria
from ..diagnostics import ModelReferenceError
from .fields import require_schema
from .index import ModelIndex


def check_relation_type_keys(model: EngineModel, _index: ModelIndex) -> None:
    """Relation keys and reverse keys share one namespace."""
    seen: set[str] = set()
    for relation in model.relationTypes:
        for field, key in (("key", relation.key), ("reverseKey", relation.reverseKey)):
            if key in seen:
                raise ModelReferenceError(
                    "DUPLICATE_KEY",
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
        _check_many_to_one(model, allowed, path)
        _check_candidates(model, allowed, path)
        if identity in identities:
            raise ModelReferenceError(
                "DUPLICATE_KEY", path, f"Duplicate object-type relation {identity}"
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
                    "INVALID_REFERENCE",
                    f"/objectTypes/{pointer_segment(object_type.key)}/behavior/"
                    f"parentRelationTypeKeys/{pointer_segment(parent_relation)}",
                    f"Object type '{object_type.key}' has incompatible parent relation "
                    f"'{parent_relation}'",
                )


def _check_many_to_one(
    model: EngineModel, allowed: ObjectTypeRelationDefinition, path: str
) -> None:
    """``many-to-one`` is schema 0.9 and optional only (0.9 K3a, D136, D137): ``required`` means the
    ``to`` record is created with its relationship, not that every ``from`` record holds one."""
    if allowed.cardinality != "many-to-one":
        return
    require_schema(model, "0.9", f"{path}/cardinality", "Cardinality 'many-to-one'")
    if allowed.required:
        raise ModelReferenceError(
            "INVALID_MODEL",
            f"{path}/required",
            f"Object-type relation '{allowed.relationTypeKey}' cannot be required with "
            "cardinality 'many-to-one'",
        )


def _check_candidates(
    model: EngineModel, allowed: ObjectTypeRelationDefinition, path: str
) -> None:
    """``candidates`` (0.9 K7, D168–D170): schema 0.9, each end's criteria resolving on that end's
    type, refused at the criterion's field, operator or value."""
    if allowed.candidates is None:
        return
    require_schema(model, "0.9", f"{path}/candidates", "A binding's candidates")
    for end, type_key in (("from", allowed.fromObjectTypeKey), ("to", allowed.toObjectTypeKey)):
        object_type = model.object_type(type_key)
        assert object_type is not None
        try:
            check_candidate_criteria(model, object_type, allowed.candidates_at(end))
        except CandidateCriterionError as error:
            raise ModelReferenceError(
                "INVALID_REFERENCE", f"{path}/candidates/{end}/{error.index}/{error.part}", str(error)
            ) from error


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
            "UNKNOWN_RELATION_TYPE",
            f"{path}/relationTypeKey",
            f"Object-type relation references unknown relation type "
            f"'{allowed.relationTypeKey}'",
        )
    if allowed.fromObjectTypeKey not in index.object_types:
        raise ModelReferenceError(
            "UNKNOWN_OBJECT_TYPE",
            f"{path}/fromObjectTypeKey",
            f"Object-type relation has unknown source '{allowed.fromObjectTypeKey}'",
        )
    if allowed.toObjectTypeKey not in index.object_types:
        raise ModelReferenceError(
            "UNKNOWN_OBJECT_TYPE",
            f"{path}/toObjectTypeKey",
            f"Object-type relation has unknown target '{allowed.toObjectTypeKey}'",
        )
    unknown_attributes = set(allowed.attributeTypeKeys) - set(index.attribute_types)
    if unknown_attributes:
        first_unknown = next(
            key for key in allowed.attributeTypeKeys if key in unknown_attributes
        )
        raise ModelReferenceError(
            "UNKNOWN_ATTRIBUTE_TYPE",
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
            "INVALID_REFERENCE",
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
            "INVALID_MODEL",
            f"{path}/features/uniqueWhenToAttributeEquals",
            f"Object-type relation '{allowed.relationTypeKey}' has an invalid "
            "uniqueWhenToAttributeEquals condition",
        )
