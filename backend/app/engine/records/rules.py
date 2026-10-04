"""The write rules, one implementation for live data and change sets.

A rule reads the records it needs through a lookup (``context.py``): ``LiveLookup`` for live data,
``ChangeSetLookup`` for one change set. Both answer the same questions, so a rule is written once.
Where the two contexts word a refusal differently, the rule raises through the lookup's
``refusals`` (``refusals.py``). What a context checks, and when, stays with the write that calls the
rules: a change set defers the whole-graph checks to validation.
"""

from collections.abc import Iterable
from datetime import date, datetime
from typing import Any

from ...common.encoding import to_jsonable
from ...errors import ApiError, api_error
from ...models.schema import (
    ApplicationDefinition,
    EngineModel,
    ObjectTypeDefinition,
    ObjectTypeRelationDefinition,
)
from .refusals import LIVE, Refusals
from .values import normalize_value

# --- identity -----------------------------------------------------------------------------------


def object_type(model: EngineModel, key: str, refusals: Refusals) -> ObjectTypeDefinition:
    definition = model.object_type(key)
    if definition is None:
        raise refusals.unknown_object_type(key)
    return definition


def object_identity(
    model: EngineModel, application_key: str, object_type_key: str, refusals: Refusals
) -> ObjectTypeDefinition:
    """The object type, declared and enabled in the application."""
    definition = object_type(model, object_type_key, refusals)
    application = next((item for item in model.applications if item.key == application_key), None)
    if application is None:
        raise refusals.unknown_application(application_key, object_type_key)
    if object_type_key not in application.objectTypeKeys:
        raise refusals.type_not_in_application(application_key, object_type_key)
    return definition


def get_object_type(model: EngineModel, key: str) -> ObjectTypeDefinition:
    """The object type a route names; ``404 unknown_object_type`` when the model has none."""
    return object_type(model, key, LIVE)


def get_application(model: EngineModel, application_key: str) -> ApplicationDefinition:
    application = next((item for item in model.applications if item.key == application_key), None)
    if application is None:
        raise LIVE.unknown_application(application_key, "")
    return application


def validate_application_object_type(
    model: EngineModel, application_key: str, object_type_key: str
) -> None:
    """A route's application and object type, with the live refusals."""
    application = get_application(model, application_key)
    if object_type_key not in application.objectTypeKeys:
        raise LIVE.type_not_in_application(application_key, object_type_key)


def object_type_changed(object_id: str, current: str, requested: str) -> ApiError:
    """A route named a type the record does not have in the selected context (D42, ADR-034).

    The record keeps its ID across a type change; the error says where it now is.
    """
    return api_error(
        409,
        "OBJECT_TYPE_CHANGED",
        f"Object '{object_id}' is a '{current}' record, not '{requested}'",
        {"objectId": object_id, "objectTypeKey": current, "requestedObjectTypeKey": requested},
    )


# --- attributes ---------------------------------------------------------------------------------


def unique_values(lookup: Any, model: EngineModel, object_id: str | None, attributes: dict) -> None:
    """No other record of the context holds a value a unique attribute type gives this record."""
    refusals: Refusals = lookup.refusals
    for key, value in attributes.items():
        # Empty text is no value, so records may share it (an E-D4 row settled in H4c).
        if value is None or value == "":
            continue
        definition = model.attribute_type(key)
        if definition is None or not definition.features.get("unique"):
            continue
        holder = lookup.unique_value_holder(
            key, definition.valueType, value, exclude_object_id=object_id
        )
        if holder is not None:
            raise refusals.duplicate_value(key, definition.name or key, holder)


def effective_period(object_type: ObjectTypeDefinition, attributes: dict[str, Any]) -> None:
    """The declared period's end is after its start, when both are given (ADR-038).

    ``attributes`` are the record's values after the write, normalized or in their stored JSON
    form; an empty start or end is open, so only two dates can conflict.
    """
    period = object_type.effectivePeriod
    if period is None:
        return
    start = _date_value(attributes.get(period.startAttributeTypeKey))
    end = _date_value(attributes.get(period.endAttributeTypeKey))
    if start is None or end is None or end > start:
        return
    raise api_error(
        422,
        "INVALID_EFFECTIVE_PERIOD",
        f"The effective period must end after it starts: '{period.endAttributeTypeKey}' "
        f"{end.isoformat()} is not after '{period.startAttributeTypeKey}' {start.isoformat()}",
        {
            "startAttributeTypeKey": period.startAttributeTypeKey,
            "endAttributeTypeKey": period.endAttributeTypeKey,
            "start": start.isoformat(),
            "end": end.isoformat(),
        },
    )


def _date_value(value: Any) -> date | None:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, str) and value:
        return date.fromisoformat(value)
    return None


# --- placement ----------------------------------------------------------------------------------


def parent(
    lookup: Any,
    model: EngineModel,
    object_type_key: str,
    application_key: str,
    parent_id: str | None,
    *,
    object_id: str | None = None,
    moving: bool = False,
) -> tuple[Any | None, str | None]:
    """The record's parent and the containment relation type that places it there.

    With ``moving``, the record already exists and the parent must not be at or under it.
    """
    definition = model.object_type(object_type_key)
    if parent_id is None:
        if not definition.features.get("rootCreatable", False):
            raise api_error(422, "PARENT_REQUIRED", "This object type requires a parent")
        return None, None
    found = lookup.object(parent_id)
    if found is None:
        raise lookup.refusals.missing_parent(parent_id)
    if found.application_key != application_key or not lookup.shares_workspace(found):
        raise api_error(
            422, "PARENT_WRONG_SCOPE", "Parent must be in the same application and workspace"
        )
    matches = [
        binding.relationTypeKey
        for key in model.containment_relation_keys(object_type_key)
        if (binding := model.allowed_relation(key, found.object_type_key, object_type_key))
    ]
    if len(matches) != 1:
        raise api_error(
            422, "INVALID_PARENT_TYPE", "Parent type is not permitted for this object type"
        )
    if moving:
        seen = {object_id}
        current = found
        while current is not None:
            if current.object_id in seen:
                raise api_error(422, "PARENT_CYCLE", "Parent selection would create a cycle")
            seen.add(current.object_id)
            current = lookup.object(current.parent_object_id)
    return found, matches[0]


def relation_endpoint_missing(object_id: str) -> ApiError:
    """A relation names a record the context does not hold (live and change set alike since H4c)."""
    return api_error(
        422, "RELATION_ENDPOINT_MISSING", f"Relation endpoint '{object_id}' does not exist"
    )


def distinct_initial_relations(identities: list[tuple[str, str, str]]) -> None:
    """A new record's initial relations (type, direction, other record) must not repeat, live and
    in a change set alike (E-D4, settled in H4c)."""
    if len(identities) != len(set(identities)):
        raise api_error(422, "DUPLICATE_INITIAL_RELATION", "Initial relationships must not repeat")


def required_initial_relations(
    model: EngineModel, object_type_key: str, provided: Iterable[str]
) -> None:
    """A new record brings, as incoming initial relations, each required binding into its type
    that is not its containment."""
    containment = model.containment_relation_keys(object_type_key)
    required = {
        binding.relationTypeKey
        for binding in model.objectTypeRelations
        if binding.toObjectTypeKey == object_type_key
        and binding.required
        and binding.relationTypeKey not in containment
    }
    missing = sorted(required - set(provided))
    if missing:
        raise api_error(
            422,
            "MISSING_REQUIRED_RELATIONS",
            f"Required relationships missing: {missing}",
            {"relationTypeKeys": missing},
        )


# --- relations ----------------------------------------------------------------------------------


def relation_binding(
    model: EngineModel, relation_type_key: str, from_type: str, to_type: str, refusals: Refusals
) -> ObjectTypeRelationDefinition:
    if model.relation_type(relation_type_key) is None:
        raise refusals.unknown_relation_type(relation_type_key)
    binding = model.allowed_relation(relation_type_key, from_type, to_type)
    if binding is None:
        raise api_error(
            422, "INVALID_RELATION_PAIR", "Relation is not permitted between these object types"
        )
    return binding


def mutable_relation(
    model: EngineModel,
    relation_type_key: str,
    to_type: str,
    refusals: Refusals,
    *,
    deleting: bool = False,
) -> None:
    """Containment relations are the engine's: written with the record's parent, never directly."""
    if relation_type_key in model.containment_relation_keys(to_type):
        raise refusals.immutable_relation(deleting)


def deletable_relation(binding: ObjectTypeRelationDefinition, refusals: Refusals) -> None:
    if binding.required:
        raise refusals.required_relation()


def relation_attributes(
    model: EngineModel, binding: ObjectTypeRelationDefinition, attributes: dict[str, Any]
) -> dict[str, Any]:
    """The binding's relation attributes, normalized and in their JSON form."""
    unknown = set(attributes) - set(binding.attributeTypeKeys)
    if unknown:
        raise api_error(
            422,
            "UNKNOWN_RELATION_ATTRIBUTES",
            f"Unknown relation attributes: {sorted(unknown)}",
        )
    result: dict[str, Any] = {}
    for key, value in attributes.items():
        definition = model.attribute_type(key)
        if definition is None:  # Model validation should make this unreachable.
            raise api_error(500, "INTERNAL_ERROR", f"Unknown model attribute '{key}'")
        result[key] = to_jsonable(normalize_value(definition, value))
    return result


def relation_cardinality(
    lookup: Any,
    binding: ObjectTypeRelationDefinition,
    from_id: str,
    to_id: str,
    excluded: frozenset[str] = frozenset(),
) -> None:
    def taken(object_id: str, direction: str) -> bool:
        return any(
            row.relation_id not in excluded
            for row in lookup.relations([object_id], direction, [binding.relationTypeKey])
        )

    if binding.cardinality == "one-to-one" and (
        taken(from_id, "outgoing") or taken(to_id, "incoming")
    ):
        raise api_error(409, "CARDINALITY_VIOLATION", "Relation cardinality would be violated")
    if binding.cardinality == "one-to-many" and taken(to_id, "incoming"):
        raise api_error(409, "CARDINALITY_VIOLATION", "Relation cardinality would be violated")


def relation_scope(
    lookup: Any,
    binding: ObjectTypeRelationDefinition,
    from_id: str,
    target: Any,
    excluded: frozenset[str] = frozenset(),
) -> None:
    """``uniqueToAncestorTypeKey``: the source relates to one record per ancestor of that type,
    counting the related records the binding's condition selects. A change set holds a breach for
    validation to report and publishing to refuse (``Refusals.holds_scope_breaches``)."""
    ancestor_type = binding.features.get("uniqueToAncestorTypeKey")
    if not ancestor_type:
        return
    condition = binding.features.get("uniqueWhenToAttributeEquals")

    def in_scope(item: Any) -> bool:
        return (
            not condition
            or lookup.values(item).get(condition["attributeTypeKey"]) == condition["value"]
        )

    if not in_scope(target):
        return
    target_ancestor = lookup.ancestor_of_type(target, ancestor_type)
    if target_ancestor is None:
        raise api_error(
            422,
            "RELATION_ANCESTOR_REQUIRED",
            f"Related object must belong to an ancestor of type '{ancestor_type}'",
        )
    if lookup.refusals.holds_scope_breaches:
        return
    # Only the source's own relations of this type can share the scope.
    outgoing = [
        row
        for row in lookup.relations([from_id], "outgoing", [binding.relationTypeKey])
        if row.relation_id not in excluded
    ]
    related = lookup.objects(row.to_object_id for row in outgoing)
    scoped = [item for item in related.values() if in_scope(item)]
    ancestors = lookup.ancestors_of_type(scoped, ancestor_type)
    conflicting = sorted(key for key, value in ancestors.items() if value == target_ancestor)
    if conflicting:
        raise api_error(
            409,
            "DUPLICATE_RELATION_SCOPE",
            "A related object already exists for this ancestor scope",
            {
                "ancestorObjectTypeKey": ancestor_type,
                "ancestorObjectId": target_ancestor,
                # The record already in the scope, so a caller can point to it.
                "conflictingObjectId": conflicting[0],
                "conflictingRelationId": min(
                    row.relation_id for row in outgoing if row.to_object_id == conflicting[0]
                ),
            },
        )


def relation(
    lookup: Any,
    model: EngineModel,
    relation_type_key: str,
    source: Any,
    target: Any,
    attributes: dict[str, Any],
    *,
    excluded: frozenset[str] = frozenset(),
) -> dict[str, Any]:
    """A relation between two records the context holds, as a write would store it: its binding,
    not a containment relation, within cardinality and ancestor scope, with valid attributes.
    ``excluded`` names relations the write replaces. Returns the normalized attributes."""
    refusals: Refusals = lookup.refusals
    binding = relation_binding(
        model, relation_type_key, source.object_type_key, target.object_type_key, refusals
    )
    mutable_relation(model, relation_type_key, target.object_type_key, refusals)
    relation_cardinality(lookup, binding, source.object_id, target.object_id, excluded)
    relation_scope(lookup, binding, source.object_id, target, excluded)
    return relation_attributes(model, binding, attributes)
