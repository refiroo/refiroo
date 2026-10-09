"""Whole-graph validation of a change set: every rule over the effective records and relations, as diagnostics."""

from collections import Counter, defaultdict
from dataclasses import dataclass
from typing import Any

from sqlalchemy.orm import Session

from ...errors import ApiError
from ..records import rules
from ..records.attributes import validate_attributes, validate_object_attribute_rules
from ..records.refusals import CHANGE_SET, Refusals
from .access import EffectiveChangeSetMembership, effective_change_set_membership


@dataclass(frozen=True)
class _Loaded:
    """Records already read, answering the lookups a rule makes during validation."""

    records: dict[str, Any]
    refusals: Refusals = CHANGE_SET

    def object(self, object_id: str | None) -> Any | None:
        return self.records.get(object_id) if object_id else None

    def shares_workspace(self, _item: Any) -> bool:
        return True


def graph_diagnostics(
    membership: EffectiveChangeSetMembership, model: Any, *, apply_defaults: bool = True
) -> list[dict[str, Any]]:
    errors: list[dict[str, Any]] = []
    objects = {item.object_id: item for item in membership.objects}
    relation_rows = list(membership.relations)
    # Stable object and relation identities share one integration namespace; a collision makes the
    # graph ambiguous for consumers addressing records by stable id.
    object_ids = set(objects)
    for shared_id in sorted(
        object_ids.intersection(item.relation_id for item in membership.relations)
    ):
        errors.append(
            {
                "code": "IDENTITY_COLLISION",
                "message": f"Stable id '{shared_id}' is used by both an object and a relation",
                "details": {"id": shared_id},
            }
        )
    effective_attributes: dict[str, dict[str, Any]] = {}
    # Indexes keep every check linear in the graph (C5): each answers what a scan of every record or
    # relation answered, with the same diagnostics in the same order.
    holders = _ValueHolders(membership.objects)
    parent_edges = {
        (relation.from_object_id, relation.to_object_id, relation.relation_type_key)
        for relation in relation_rows
    }
    for item in membership.objects:
        object_type = model.object_type(item.object_type_key)
        if object_type is None:
            errors.append(
                {
                    "code": "UNKNOWN_OBJECT_TYPE",
                    "message": f"Object type '{item.object_type_key}' is not in the pinned model",
                    "details": {"objectId": item.object_id},
                }
            )
        else:
            try:
                rules.parent(
                    _Loaded(objects),
                    model,
                    item.object_type_key,
                    item.application_key,
                    item.parent_object_id,
                    object_id=item.object_id,
                    moving=True,
                )
            except ApiError as exc:
                errors.append(
                    {
                        "code": exc.code,
                        "message": exc.message,
                        "details": {"objectId": item.object_id},
                    }
                )
            try:
                # Stored/defaulted read-only values are valid graph content. Write boundaries
                # reject authoring them; snapshot validation must still type-check their values.
                attrs = validate_attributes(
                    model,
                    object_type,
                    dict(item.attributes or {}),
                    partial=False,
                    allow_read_only=True,
                    apply_defaults=apply_defaults,
                )
                validate_object_attribute_rules(object_type, attrs)
            except ApiError as exc:
                errors.append(
                    {
                        "code": exc.code,
                        "message": exc.message,
                        "details": {"objectId": item.object_id, **(exc.details or {})}
                        if isinstance(exc.details, dict)
                        else {"objectId": item.object_id},
                    }
                )
            else:
                effective_attributes[item.object_id] = attrs
            _validate_application_diagnostic(errors, model, item)
            # Attribute uniqueness is scoped to the candidate graph, never to the mutable active
            # projection (which may still contain a different publication).
            for key, definition in (
                (key, model.attribute_type(key)) for key in (item.attributes or {})
            ):
                if definition and definition.features.get("unique"):
                    if (item.attributes or {}).get(key) in (None, ""):
                        continue  # empty text is no value (E-D4, H4c)
                    same = [
                        other_id
                        for other_id in holders.of(key, (item.attributes or {}).get(key))
                        if other_id != item.object_id
                    ]
                    if same:
                        errors.append(
                            {
                                "code": "DUPLICATE_ATTRIBUTE_VALUE",
                                "message": f"Attribute '{key}' must be unique",
                                "details": {
                                    "objectId": item.object_id,
                                    "attributeTypeKey": key,
                                    "conflictingObjectIds": sorted(same),
                                },
                            }
                        )
        seen: set[str] = {item.object_id}
        current = item
        while current.parent_object_id:
            parent = objects.get(current.parent_object_id)
            if parent is None or current.parent_object_id in seen:
                errors.append(
                    {
                        "code": "CONTAINMENT_CYCLE",
                        "message": "Containment graph contains a cycle or missing parent",
                    }
                )
                break
            seen.add(parent.object_id)
            if not _parent_pair_exists(model, current, parent, parent_edges):
                errors.append(
                    {
                        "code": "CONTAINMENT_RELATION_MISSING",
                        "message": "Containment parent is not represented by its declared parent relation",
                        "details": {
                            "objectId": current.object_id,
                            "parentObjectId": parent.object_id,
                        },
                    }
                )
            current = parent
    valid_relations = []
    for relation in relation_rows:
        if relation.from_object_id not in objects or relation.to_object_id not in objects:
            errors.append(
                {
                    "code": "RELATION_ENDPOINT_MISSING",
                    "message": "Relation endpoint is not in the candidate graph",
                }
            )
            continue
        source, target = objects[relation.from_object_id], objects[relation.to_object_id]
        allowed = model.allowed_relation(
            relation.relation_type_key, source.object_type_key, target.object_type_key
        )
        if allowed is None:
            errors.append(
                {
                    "code": "INVALID_RELATION_PAIR",
                    "message": "Relation is not permitted by the pinned model",
                }
            )
            continue
        try:
            rules.relation_attributes(model, allowed, dict(relation.attributes or {}))
        except ApiError as exc:
            errors.append(
                {
                    "code": exc.code,
                    "message": exc.message,
                    "details": {"relationId": relation.relation_id},
                }
            )
        else:
            valid_relations.append((relation, allowed))
    # How many valid relations of each type leave or enter each record, by relation id.
    leaving: dict[tuple[str, str], Counter[str]] = defaultdict(Counter)
    entering: dict[tuple[str, str], Counter[str]] = defaultdict(Counter)
    for relation, allowed in valid_relations:
        leaving[(allowed.relationTypeKey, relation.from_object_id)][relation.relation_id] += 1
        entering[(allowed.relationTypeKey, relation.to_object_id)][relation.relation_id] += 1

    def another(counts: Counter[str], relation_id: str) -> bool:
        return counts.total() > counts[relation_id]

    for relation, allowed in valid_relations:
        if allowed.holds_one("from") and another(
            leaving[(allowed.relationTypeKey, relation.from_object_id)], relation.relation_id
        ):
            errors.append(
                {
                    "code": "RELATION_CARDINALITY_VIOLATION",
                    "message": f"Relation '{allowed.relationTypeKey}' exceeds source cardinality",
                    "details": {"relationId": relation.relation_id},
                }
            )
        if allowed.holds_one("to") and another(
            entering[(allowed.relationTypeKey, relation.to_object_id)], relation.relation_id
        ):
            errors.append(
                {
                    "code": "RELATION_CARDINALITY_VIOLATION",
                    "message": f"Relation '{allowed.relationTypeKey}' exceeds target cardinality",
                    "details": {"relationId": relation.relation_id},
                }
            )
    # Ancestor-scoped uniqueness (language/target uniqueness for translations): a scoped relation may
    # appear once per source object per ancestor scope while the optional target-attribute condition
    # holds. Mirrors the change set write path in validate_change_set_relation. Only relations of the
    # same type from the same source can conflict, so each looks among those, in list order.
    by_source: dict[tuple[str, str], list[tuple[Any, Any]]] = defaultdict(list)
    for relation, allowed in valid_relations:
        by_source[(allowed.relationTypeKey, relation.from_object_id)].append((relation, allowed))
    for relation, allowed in valid_relations:
        ancestor_type_key = allowed.features.get("uniqueToAncestorTypeKey")
        if not ancestor_type_key:
            continue
        condition = allowed.features.get("uniqueWhenToAttributeEquals")
        target = objects.get(relation.to_object_id)
        target_values = effective_attributes.get(target.object_id, target.attributes or {})
        if condition and target_values.get(condition["attributeTypeKey"]) != condition["value"]:
            continue
        target_ancestor = _ancestor_object_id(objects, target, ancestor_type_key)
        if target_ancestor is None:
            continue
        for other, _other_allowed in by_source[(allowed.relationTypeKey, relation.from_object_id)]:
            if other.relation_id >= relation.relation_id:
                continue
            other_target = objects.get(other.to_object_id)
            other_values = effective_attributes.get(
                other_target.object_id, other_target.attributes or {}
            )
            if (
                other.from_object_id == relation.from_object_id
                and (
                    not condition
                    or other_values.get(condition["attributeTypeKey"]) == condition["value"]
                )
                and _ancestor_object_id(objects, other_target, ancestor_type_key) == target_ancestor
            ):
                errors.append(
                    {
                        "code": "DUPLICATE_RELATION_SCOPE",
                        "message": f"Relation '{allowed.relationTypeKey}' already exists for this ancestor scope",
                        "details": {
                            "relationId": relation.relation_id,
                            "conflictingRelationId": other.relation_id,
                            "conflictingObjectId": other.to_object_id,
                            "objectId": relation.from_object_id,
                            "ancestorObjectId": target_ancestor,
                        },
                    }
                )
                break
    # Required relationships bind at the target side: every object that is the target of a required
    # non-parent pair must carry an incoming relation of that type from an allowed source.  This
    # matches the change set object-create contract, model compatibility counting and the
    # PK->FK ownership cascade used by delete.
    required_by_target: dict[tuple[str, str], set[str]] = {}
    for pair in model.objectTypeRelations:
        if pair.required and not is_parent_pair(model, pair):
            required_by_target.setdefault((pair.relationTypeKey, pair.toObjectTypeKey), set()).add(
                pair.fromObjectTypeKey
            )
    incoming = {
        (rel.to_object_id, rel.relation_type_key, objects[rel.from_object_id].object_type_key)
        for rel, _allowed in valid_relations
    }
    for target in membership.objects:
        for (relation_key, target_type), source_types in sorted(required_by_target.items()):
            if target_type != target.object_type_key:
                continue
            satisfied = any(
                (target.object_id, relation_key, source_type) in incoming
                for source_type in source_types
            )
            if not satisfied:
                errors.append(
                    {
                        "code": "MISSING_REQUIRED_RELATION",
                        "message": f"Required relationship '{relation_key}' is missing for object '{target.object_id}'",
                        "details": {"objectId": target.object_id, "relationTypeKey": relation_key},
                    }
                )
    return errors


def _validate_application_diagnostic(errors: list[dict[str, Any]], model: Any, item: Any) -> None:
    application = next((x for x in model.applications if x.key == item.application_key), None)
    if application is None or item.object_type_key not in application.objectTypeKeys:
        errors.append(
            {
                "code": "OBJECT_TYPE_NOT_IN_APPLICATION",
                "message": f"Object type '{item.object_type_key}' is not enabled in application '{item.application_key}'",
                "details": {"objectId": item.object_id},
            }
        )


def _parent_pair_exists(
    model: Any, child: Any, parent: Any, edges: set[tuple[str, str, str]]
) -> bool:
    """Whether ``edges`` (source, target, relation type) hold one of ``child``'s parent relations."""
    keys = (
        set(model.object_type(child.object_type_key).behavior.get("parentRelationTypeKeys", []))
        if model.object_type(child.object_type_key)
        else set()
    )
    return not keys or any((parent.object_id, child.object_id, key) in edges for key in keys)


class _ValueHolders:
    """Records by attribute value, per attribute type, built once per attribute type asked for.

    ``of(key, value)`` lists, in membership order, the records whose ``key`` equals ``value`` by
    ``==`` (a record without ``key`` holds ``None``), as a scan comparing every record would. Values
    that cannot be hashed (JSON lists and objects) are compared one by one among themselves.
    """

    def __init__(self, objects: Any) -> None:
        self._objects = list(objects)
        self._by_key: dict[str, tuple[dict[Any, list[str]], list[tuple[Any, str]]]] = {}

    def of(self, key: str, value: Any) -> list[str]:
        if key not in self._by_key:
            hashed: dict[Any, list[str]] = {}
            unhashable: list[tuple[Any, str]] = []
            for other in self._objects:
                held = (other.attributes or {}).get(key)
                try:
                    hashed.setdefault(held, []).append(other.object_id)
                except TypeError:
                    unhashable.append((held, other.object_id))
            self._by_key[key] = (hashed, unhashable)
        hashed, unhashable = self._by_key[key]
        try:
            return hashed.get(value, [])
        except TypeError:
            return [object_id for held, object_id in unhashable if held == value]


def is_parent_pair(model: Any, pair: Any) -> bool:
    child = model.object_type(pair.toObjectTypeKey)
    return bool(child and pair.relationTypeKey in child.behavior.get("parentRelationTypeKeys", []))


def _ancestor_object_id(objects: dict[str, Any], item: Any, object_type_key: str) -> str | None:
    """Return the nearest ancestor object id of ``item`` whose type is ``object_type_key``."""
    seen: set[str] = set()
    current = item
    while current is not None and current.object_id not in seen:
        seen.add(current.object_id)
        if current.object_type_key == object_type_key:
            return current.object_id
        current = objects.get(current.parent_object_id) if current.parent_object_id else None
    return None


def validate_change_set(session: Session, change_set_id: str, model: Any) -> list[dict[str, Any]]:
    return graph_diagnostics(effective_change_set_membership(session, change_set_id), model)
