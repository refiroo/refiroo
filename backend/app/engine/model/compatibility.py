from collections import defaultdict
from collections.abc import Callable, Sequence
from contextvars import ContextVar
from typing import Any

from sqlalchemy import Numeric, Select, and_, cast, exists, func, or_, select
from sqlalchemy.orm import Session, aliased

from ...models.database import AttributeValue, ObjectRelation, RdmObject
from ...models.schema import EngineModel, ObjectTypeRelationDefinition
from ..records.values import VALUE_COLUMNS, normalize_value
from .compiler import ModelDiagnostic


class CompatibilityResult:
    def __init__(self, active_release_id: str, diagnostics: list[ModelDiagnostic]):
        self.classification = "migration_required" if diagnostics else "compatible"
        self.active_release_id = active_release_id
        self.diagnostics = tuple(diagnostics)


# The workspaces whose data an analysis counts (0.11 M1): the activation's workspace, or those
# running the release a draft or a diff is compared with. Set by ``analyze_compatibility``.
_SCOPE: ContextVar[tuple[str, ...]] = ContextVar("compatibility_scope", default=())


def _in_scope(item: Any) -> Any:
    """A live row of one of the analysed workspaces, retired catalogues included: live objects are
    authoritative independently of whether their workspace still has an active publication, and
    another workspace's data runs under its own release (ADR-042)."""
    return item.workspace_key.in_(_SCOPE.get())


# Takes the records behind each counted rule a record can break (0.11 V1, D72): a ``SELECT`` of
# their IDs, the diagnostic's code, path and message. A migration lists its refusals with it.
Listing = Callable[[Select[Any], str, str, str], None]
_LISTING: ContextVar[Listing | None] = ContextVar("compatibility_listing", default=None)


def analyze_compatibility(
    session: Session,
    active_model: EngineModel,
    candidate_model: EngineModel,
    active_release_id: str,
    workspace_keys: Sequence[str],
    *,
    listing: Listing | None = None,
) -> CompatibilityResult:
    """Assess a valid candidate against the stored data of ``workspace_keys`` using bounded SQL
    queries. ``listing`` also takes the records behind every rule a record breaks (the removal
    rules count model elements in use, which a record does not break, and list nothing)."""
    token = _SCOPE.set(tuple(workspace_keys))
    listed = _LISTING.set(listing)
    try:
        return _analyze(session, active_model, candidate_model, active_release_id)
    finally:
        _LISTING.reset(listed)
        _SCOPE.reset(token)


def _analyze(
    session: Session,
    active_model: EngineModel,
    candidate_model: EngineModel,
    active_release_id: str,
) -> CompatibilityResult:
    diagnostics: list[ModelDiagnostic] = []
    active_objects = {item.key: item for item in active_model.objectTypes}
    candidate_objects = {item.key: item for item in candidate_model.objectTypes}
    active_apps = {item.key: item for item in active_model.applications}
    candidate_apps = {item.key: item for item in candidate_model.applications}
    active_attributes = {item.key: item for item in active_model.attributeTypes}
    candidate_attributes = {item.key: item for item in candidate_model.attributeTypes}

    for key in sorted(set(active_apps) - set(candidate_apps)):
        _append_counted(
            diagnostics,
            _count_objects(session, RdmObject.application_key == key),
            "APPLICATION_IN_USE",
            f"/applications/{_pointer(key)}",
            f"Application '{key}' is used by stored objects",
        )

    for key in sorted(set(active_objects) - set(candidate_objects)):
        _append_counted(
            diagnostics,
            _count_objects(session, RdmObject.object_type_key == key),
            "OBJECT_TYPE_IN_USE",
            f"/objectTypes/{_pointer(key)}",
            f"Object type '{key}' is used by stored objects",
        )

    for key in sorted(set(active_apps) & set(candidate_apps)):
        removed = set(active_apps[key].objectTypeKeys) - set(candidate_apps[key].objectTypeKeys)
        for object_type_key in sorted(removed):
            _append_counted(
                diagnostics,
                _count_objects(
                    session,
                    RdmObject.application_key == key,
                    RdmObject.object_type_key == object_type_key,
                ),
                "APPLICATION_OBJECT_TYPE_IN_USE",
                f"/applications/{_pointer(key)}/objectTypeKeys/{_pointer(object_type_key)}",
                f"Object type '{object_type_key}' is used in application '{key}'",
            )

    _check_attributes(
        session,
        active_model,
        candidate_model,
        active_objects,
        candidate_objects,
        active_attributes,
        candidate_attributes,
        diagnostics,
    )
    _check_relations(session, active_model, candidate_model, diagnostics)
    _check_parent_semantics(session, active_model, candidate_model, diagnostics)

    return CompatibilityResult(active_release_id, diagnostics)


def _check_attributes(
    session: Session,
    active_model: EngineModel,
    candidate_model: EngineModel,
    active_objects: dict,
    candidate_objects: dict,
    active_attributes: dict,
    candidate_attributes: dict,
    diagnostics: list[ModelDiagnostic],
) -> None:
    for key in sorted(set(active_attributes) - set(candidate_attributes)):
        _append_counted(
            diagnostics,
            _count_attribute_values(session, key),
            "ATTRIBUTE_TYPE_IN_USE",
            f"/attributeTypes/{_pointer(key)}",
            f"Attribute type '{key}' has stored values",
        )

    for key in sorted(set(active_attributes) & set(candidate_attributes)):
        if active_attributes[key].valueType != candidate_attributes[key].valueType:
            _append_counted(
                diagnostics,
                _count_attribute_values(session, key),
                "ATTRIBUTE_VALUE_TYPE_CHANGED",
                f"/attributeTypes/{_pointer(key)}/valueType",
                f"Attribute type '{key}' changes the declared type of stored values",
            )

    for object_type_key in sorted(set(active_objects) & set(candidate_objects)):
        active_bindings = {
            item.attributeTypeKey: item for item in active_objects[object_type_key].attributes
        }
        candidate_bindings = {
            item.attributeTypeKey: item for item in candidate_objects[object_type_key].attributes
        }
        for key in sorted(set(active_bindings) - set(candidate_bindings)):
            _append_counted(
                diagnostics,
                _count_attribute_values(session, key, object_type_key),
                "ATTRIBUTE_BINDING_IN_USE",
                f"/objectTypes/{_pointer(object_type_key)}/attributes/{_pointer(key)}",
                f"Attribute '{key}' has stored values on object type '{object_type_key}'",
            )
        for key, binding in sorted(candidate_bindings.items()):
            active_binding = active_bindings.get(key)
            if binding.required and (active_binding is None or not active_binding.required):
                _append_records(
                    diagnostics,
                    session,
                    _missing_required_attribute(
                        object_type_key, key, candidate_attributes[key].valueType
                    ),
                    "REQUIRED_ATTRIBUTE_MISSING",
                    f"/objectTypes/{_pointer(object_type_key)}/attributes/{_pointer(key)}/required",
                    f"Stored '{object_type_key}' objects do not satisfy required attribute '{key}'",
                )

        active_rule = tuple(active_objects[object_type_key].validation.get("atLeastOneOf", ()))
        candidate_rule = tuple(
            candidate_objects[object_type_key].validation.get("atLeastOneOf", ())
        )
        if candidate_rule and candidate_rule != active_rule:
            _append_records(
                diagnostics,
                session,
                _missing_at_least_one(object_type_key, candidate_rule, candidate_attributes),
                "OBJECT_VALIDATION_RULE_VIOLATED",
                f"/objectTypes/{_pointer(object_type_key)}/validation/atLeastOneOf",
                f"Stored '{object_type_key}' objects do not satisfy atLeastOneOf",
            )

        # D20: a period declared or moved to other attributes counts the records it would refuse.
        period = candidate_objects[object_type_key].effectivePeriod
        if period is not None and period != active_objects[object_type_key].effectivePeriod:
            _append_records(
                diagnostics,
                session,
                _invalid_periods(
                    object_type_key, period.startAttributeTypeKey, period.endAttributeTypeKey
                ),
                "INVALID_EFFECTIVE_PERIOD",
                f"/objectTypes/{_pointer(object_type_key)}/effectivePeriod",
                f"Stored '{object_type_key}' objects have an effective period that does not end "
                "after it starts",
            )

    for key, attribute in sorted(candidate_attributes.items()):
        active_attribute = active_attributes.get(key)
        if attribute.features.get("unique") and (
            active_attribute is None or not active_attribute.features.get("unique")
        ):
            groups, records = _duplicate_attribute_groups(key, attribute.valueType)
            _append_records(
                diagnostics,
                session,
                records,
                "ATTRIBUTE_UNIQUENESS_VIOLATED",
                f"/attributeTypes/{_pointer(key)}/features/unique",
                f"Stored values violate uniqueness for attribute '{key}'",
                count=int(session.scalar(select(func.count()).select_from(groups)) or 0),
            )
        _check_numeric_bounds(session, key, active_attribute, attribute, diagnostics)


def _check_numeric_bounds(
    session: Session,
    key: str,
    active_attribute: Any | None,
    candidate_attribute: Any,
    diagnostics: list[ModelDiagnostic],
) -> None:
    if candidate_attribute.valueType not in {"integer", "decimal"}:
        return
    column = getattr(AttributeValue, VALUE_COLUMNS[candidate_attribute.valueType])
    for bound, operator in (
        ("minimum", lambda value: column < value),
        ("maximum", lambda value: column > value),
    ):
        candidate_value = candidate_attribute.validation.get(bound)
        active_value = active_attribute.validation.get(bound) if active_attribute else None
        if candidate_value is None or candidate_value == active_value:
            continue
        # One value per record and attribute: the records are the values counted.
        records = (
            select(RdmObject.id)
            .join(AttributeValue, AttributeValue.object_id == RdmObject.id)
            .where(
                _in_scope(RdmObject),
                AttributeValue.attribute_type_key == key,
                operator(candidate_value),
            )
        )
        relations = _relation_attribute_bound_violations(key, bound, candidate_value)
        object_count = int(
            session.scalar(select(func.count()).select_from(records.subquery())) or 0
        )
        relation_count = int(session.scalar(select(func.count()).select_from(relations)) or 0)
        _append_records(
            diagnostics,
            session,
            records.union(select(relations.c.from_object_id)),
            "ATTRIBUTE_VALIDATION_VIOLATED",
            f"/attributeTypes/{_pointer(key)}/validation/{bound}",
            f"Stored values violate {bound} for attribute '{key}'",
            count=object_count + relation_count,
        )


def _check_relations(
    session: Session,
    active_model: EngineModel,
    candidate_model: EngineModel,
    diagnostics: list[ModelDiagnostic],
) -> None:
    active_pairs = {_relation_identity(item): item for item in active_model.objectTypeRelations}
    candidate_pairs = {
        _relation_identity(item): item for item in candidate_model.objectTypeRelations
    }
    active_attributes = {item.key: item for item in active_model.attributeTypes}
    candidate_attributes = {item.key: item for item in candidate_model.attributeTypes}

    for identity in sorted(set(active_pairs) - set(candidate_pairs)):
        count = _count_relation_pair(session, active_pairs[identity])
        _append_counted(
            diagnostics,
            count,
            "RELATION_PAIR_IN_USE",
            _relation_path(identity),
            f"Allowed relation {identity!r} is used by stored relations",
        )

    for identity in sorted(set(active_pairs) & set(candidate_pairs)):
        active_pair = active_pairs[identity]
        candidate_pair = candidate_pairs[identity]
        for key in sorted(
            set(active_pair.attributeTypeKeys) - set(candidate_pair.attributeTypeKeys)
        ):
            count = _count_relations_with_attribute(session, active_pair, key)
            _append_counted(
                diagnostics,
                count,
                "RELATION_ATTRIBUTE_IN_USE",
                f"{_relation_path(identity)}/attributeTypeKeys/{_pointer(key)}",
                f"Relation attribute '{key}' has stored values",
            )
        for key in sorted(
            set(active_pair.attributeTypeKeys) & set(candidate_pair.attributeTypeKeys)
        ):
            if active_attributes[key].valueType != candidate_attributes[key].valueType:
                count = _count_relations_with_attribute(session, active_pair, key)
                _append_counted(
                    diagnostics,
                    count,
                    "RELATION_ATTRIBUTE_VALUE_TYPE_CHANGED",
                    f"/attributeTypes/{_pointer(key)}/valueType",
                    f"Relation attribute '{key}' changes the type of stored values",
                )

    required_by_target: dict[tuple[str, str], set[str]] = defaultdict(set)
    active_required_keys = {
        (pair.relationTypeKey, pair.toObjectTypeKey)
        for pair in active_pairs.values()
        if pair.required and not is_parent_pair(active_model, pair)
    }
    for pair in candidate_pairs.values():
        if pair.required and not is_parent_pair(candidate_model, pair):
            required_by_target[(pair.relationTypeKey, pair.toObjectTypeKey)].add(
                pair.fromObjectTypeKey
            )
    for (relation_key, target_key), source_keys in sorted(required_by_target.items()):
        if (relation_key, target_key) in active_required_keys:
            continue
        _append_records(
            diagnostics,
            session,
            _missing_required_relation(relation_key, target_key, source_keys),
            "REQUIRED_RELATION_MISSING",
            f"/objectTypeRelations/{_pointer(relation_key)}/*/{_pointer(target_key)}/required",
            f"Stored '{target_key}' objects lack required relation '{relation_key}'",
        )

    for identity, pair in sorted(candidate_pairs.items()):
        active_pair = active_pairs.get(identity)
        active_restrictions = _cardinality_restrictions(active_pair) if active_pair else set()
        candidate_restrictions = _cardinality_restrictions(pair)
        if candidate_restrictions - active_restrictions:
            _check_cardinality(session, identity, pair, diagnostics)
        active_scope = active_pair.features.get("uniqueToAncestorTypeKey") if active_pair else None
        active_condition = (
            active_pair.features.get("uniqueWhenToAttributeEquals") if active_pair else None
        )
        if pair.features.get("uniqueToAncestorTypeKey") and (
            pair.features.get("uniqueToAncestorTypeKey") != active_scope
            or pair.features.get("uniqueWhenToAttributeEquals") != active_condition
        ):
            conflicts = _scoped_uniqueness_conflicts(pair, candidate_model)
            _append_records(
                diagnostics,
                session,
                select(conflicts.c.from_object_id).distinct(),
                "RELATION_UNIQUENESS_VIOLATED",
                f"{_relation_path(identity)}/features/uniqueToAncestorTypeKey",
                f"Stored relations violate scoped uniqueness for '{pair.relationTypeKey}'",
                count=int(session.scalar(select(func.count()).select_from(conflicts)) or 0),
            )


def _check_parent_semantics(
    session: Session,
    active_model: EngineModel,
    candidate_model: EngineModel,
    diagnostics: list[ModelDiagnostic],
) -> None:
    candidate_objects = {item.key: item for item in candidate_model.objectTypes}
    candidate_pairs = {
        _relation_identity(item): item for item in candidate_model.objectTypeRelations
    }
    active_relations = {item.key: item for item in active_model.relationTypes}
    candidate_relations = {item.key: item for item in candidate_model.relationTypes}
    active_objects = {item.key: item for item in active_model.objectTypes}

    for object_type in candidate_model.objectTypes:
        active_object = active_objects.get(object_type.key)
        if (
            not object_type.features.get("rootCreatable", False)
            and active_object is not None
            and active_object.features.get("rootCreatable", False)
        ):
            _append_records(
                diagnostics,
                session,
                _objects(
                    RdmObject.object_type_key == object_type.key,
                    RdmObject.parent_object_id.is_(None),
                ),
                "PARENT_REQUIRED",
                f"/objectTypes/{_pointer(object_type.key)}/features/rootCreatable",
                f"Stored '{object_type.key}' objects require a parent",
            )

    for pair in active_model.objectTypeRelations:
        if not is_parent_pair(active_model, pair):
            continue
        identity = _relation_identity(pair)
        candidate_child = candidate_objects.get(pair.toObjectTypeKey)
        candidate_relation = candidate_relations.get(pair.relationTypeKey)
        active_relation = active_relations[pair.relationTypeKey]
        remains_parent = (
            candidate_child is not None
            and identity in candidate_pairs
            and pair.relationTypeKey in candidate_child.behavior.get("parentRelationTypeKeys", ())
            and candidate_relation is not None
            and bool(candidate_relation.features.get("parentOf"))
            == bool(active_relation.features.get("parentOf"))
            and bool(candidate_relation.features.get("hierarchical"))
            == bool(active_relation.features.get("hierarchical"))
        )
        if not remains_parent:
            _append_counted(
                diagnostics,
                _count_relation_pair(session, pair),
                "PARENT_RELATION_SEMANTICS_CHANGED",
                f"/objectTypes/{_pointer(pair.toObjectTypeKey)}/behavior/parentRelationTypeKeys",
                f"Stored containment uses parent relation '{pair.relationTypeKey}'",
            )


def _check_cardinality(
    session: Session,
    identity: tuple[str, str, str],
    pair: ObjectTypeRelationDefinition,
    diagnostics: list[ModelDiagnostic],
) -> None:
    count = 0
    ends: list[Select[Any]] = []
    for end in ("from", "to"):
        if not pair.holds_one(end):
            continue
        record = aliased(RdmObject)
        end_id = ObjectRelation.from_object_id if end == "from" else ObjectRelation.to_object_id
        end_type = pair.fromObjectTypeKey if end == "from" else pair.toObjectTypeKey
        conflicts = (
            select(end_id.label("object_id"))
            .join(record, record.id == end_id)
            .where(
                ObjectRelation.relation_type_key == pair.relationTypeKey,
                record.object_type_key == end_type,
                _in_scope(record),
            )
            .group_by(end_id)
            .having(func.count() > 1)
        )
        ends.append(conflicts)
        count += int(session.scalar(select(func.count()).select_from(conflicts.subquery())) or 0)
    if not ends:
        return
    _append_records(
        diagnostics,
        session,
        ends[0].union(*ends[1:]) if len(ends) > 1 else ends[0],
        "RELATION_CARDINALITY_VIOLATED",
        f"{_relation_path(identity)}/cardinality",
        f"Stored relations violate cardinality '{pair.cardinality}'",
        count=count,
    )


def _scoped_uniqueness_conflicts(pair: ObjectTypeRelationDefinition, model: EngineModel) -> Any:
    """The (source, nearest ancestor) groups holding more than one relationship of the pair."""
    ancestor_type = pair.features["uniqueToAncestorTypeKey"]
    # Each target of the pair's relationships climbs its parents and stops at the first record of
    # the scope's type (itself, when it is one): one row per step, from the records the rule covers
    # only. Walking every record of the workspace to its root and grouping the walk took minutes at
    # 100,000 records (0.11 V1).
    start, related = aliased(RdmObject), aliased(RdmObject)
    lineage = (
        select(
            start.id.label("descendant_id"),
            start.id.label("ancestor_id"),
            start.parent_object_id.label("parent_id"),
            start.object_type_key.label("ancestor_type"),
        )
        .where(
            _in_scope(start),
            start.object_type_key == pair.toObjectTypeKey,
            exists(
                select(ObjectRelation.sequence_id)
                .join(related, related.id == ObjectRelation.from_object_id)
                .where(
                    ObjectRelation.to_object_id == start.id,
                    ObjectRelation.relation_type_key == pair.relationTypeKey,
                    related.object_type_key == pair.fromObjectTypeKey,
                )
            ),
        )
        .cte("scope_lineage", recursive=True)
    )
    parent = aliased(RdmObject)
    lineage = lineage.union_all(
        select(
            lineage.c.descendant_id,
            parent.id,
            parent.parent_object_id,
            parent.object_type_key,
        )
        .join(parent, parent.id == lineage.c.parent_id)
        .where(lineage.c.ancestor_type != ancestor_type)
    )
    nearest_ancestor = (
        select(lineage.c.descendant_id, lineage.c.ancestor_id)
        .where(lineage.c.ancestor_type == ancestor_type)
        .subquery()
    )
    source = aliased(RdmObject)
    target = aliased(RdmObject)
    statement = (
        select(ObjectRelation.from_object_id, nearest_ancestor.c.ancestor_id)
        .join(source, source.id == ObjectRelation.from_object_id)
        .join(target, target.id == ObjectRelation.to_object_id)
        .join(
            nearest_ancestor,
            nearest_ancestor.c.descendant_id == ObjectRelation.to_object_id,
        )
        .where(
            ObjectRelation.relation_type_key == pair.relationTypeKey,
            source.object_type_key == pair.fromObjectTypeKey,
            target.object_type_key == pair.toObjectTypeKey,
            _in_scope(source),
            _in_scope(target),
        )
    )
    condition = pair.features.get("uniqueWhenToAttributeEquals")
    if condition:
        attribute = model.attribute_type(condition["attributeTypeKey"])
        if attribute is not None:
            column = getattr(AttributeValue, VALUE_COLUMNS[attribute.valueType])
            normalized = normalize_value(attribute, condition["value"])
            statement = statement.where(
                exists(
                    select(AttributeValue.sequence_id).where(
                        AttributeValue.object_id == ObjectRelation.to_object_id,
                        AttributeValue.attribute_type_key == attribute.key,
                        column == normalized,
                    )
                )
            )
    return (
        statement.group_by(ObjectRelation.from_object_id, nearest_ancestor.c.ancestor_id)
        .having(func.count() > 1)
        .subquery()
    )


def _objects(*conditions: Any) -> Select[Any]:
    """The analysed workspaces' records meeting ``conditions``, by ID."""
    return select(RdmObject.id).where(_in_scope(RdmObject), *conditions)


def _count_objects(session: Session, *conditions: Any) -> int:
    return int(
        session.scalar(
            select(func.count()).select_from(RdmObject).where(_in_scope(RdmObject), *conditions)
        )
        or 0
    )


def _count_attribute_values(
    session: Session, attribute_key: str, object_type_key: str | None = None
) -> int:
    statement = (
        select(func.count())
        .select_from(AttributeValue)
        .join(RdmObject, RdmObject.id == AttributeValue.object_id)
        .where(_in_scope(RdmObject))
    )
    if object_type_key is not None:
        statement = statement.where(RdmObject.object_type_key == object_type_key)
    return int(
        session.scalar(statement.where(AttributeValue.attribute_type_key == attribute_key)) or 0
    )


def _missing_required_attribute(
    object_type_key: str, attribute_key: str, value_type: str
) -> Select[Any]:
    column = getattr(AttributeValue, VALUE_COLUMNS[value_type])
    usable = [column.is_not(None)]
    if value_type in {"text", "longText"}:
        usable.append(column != "")
    present = exists(
        select(AttributeValue.sequence_id).where(
            AttributeValue.object_id == RdmObject.id,
            AttributeValue.attribute_type_key == attribute_key,
            *usable,
        )
    )
    return _objects(RdmObject.object_type_key == object_type_key, ~present)


def _missing_at_least_one(
    object_type_key: str,
    attribute_keys: tuple[str, ...],
    attribute_types: dict,
) -> Select[Any]:
    predicates = []
    for key in attribute_keys:
        value_type = attribute_types[key].valueType
        column = getattr(AttributeValue, VALUE_COLUMNS[value_type])
        usable = [column.is_not(None)]
        if value_type in {"text", "longText"}:
            usable.append(column != "")
        predicates.append(
            exists(
                select(AttributeValue.sequence_id).where(
                    AttributeValue.object_id == RdmObject.id,
                    AttributeValue.attribute_type_key == key,
                    *usable,
                )
            )
        )
    return _objects(RdmObject.object_type_key == object_type_key, ~or_(*predicates))


def _invalid_periods(object_type_key: str, start_key: str, end_key: str) -> Select[Any]:
    """Records of the type whose end date is not after their start date (both given)."""
    start, end = aliased(AttributeValue), aliased(AttributeValue)
    return (
        select(RdmObject.id)
        .join(start, and_(start.object_id == RdmObject.id, start.attribute_type_key == start_key))
        .join(end, and_(end.object_id == RdmObject.id, end.attribute_type_key == end_key))
        .where(
            _in_scope(RdmObject),
            RdmObject.object_type_key == object_type_key,
            end.date_value <= start.date_value,
        )
    )


def _duplicate_attribute_groups(key: str, value_type: str) -> tuple[Any, Select[Any]]:
    """The groups of records sharing a value of the attribute in one workspace, and the records
    in them."""
    column = getattr(AttributeValue, VALUE_COLUMNS[value_type])
    conditions = [AttributeValue.attribute_type_key == key, column.is_not(None)]
    if value_type in {"text", "longText"}:
        conditions.append(column != "")
    conflicts = (
        select(RdmObject.workspace_key, column.label("value"))
        .join(AttributeValue, AttributeValue.object_id == RdmObject.id)
        .where(*conditions)
        .where(_in_scope(RdmObject))
        .group_by(RdmObject.workspace_key, column)
        .having(func.count() > 1)
        .subquery()
    )
    records = (
        select(RdmObject.id)
        .join(AttributeValue, AttributeValue.object_id == RdmObject.id)
        .join(
            conflicts,
            and_(conflicts.c.workspace_key == RdmObject.workspace_key, conflicts.c.value == column),
        )
        .where(*conditions)
    )
    return conflicts, records


def _count_relation_pair(session: Session, pair: ObjectTypeRelationDefinition) -> int:
    from_object = aliased(RdmObject)
    to_object = aliased(RdmObject)
    return int(
        session.scalar(
            select(func.count())
            .select_from(ObjectRelation)
            .join(from_object, from_object.id == ObjectRelation.from_object_id)
            .join(to_object, to_object.id == ObjectRelation.to_object_id)
            .where(
                ObjectRelation.relation_type_key == pair.relationTypeKey,
                from_object.object_type_key == pair.fromObjectTypeKey,
                to_object.object_type_key == pair.toObjectTypeKey,
                _in_scope(from_object),
                _in_scope(to_object),
            )
        )
        or 0
    )


def _relation_attribute_bound_violations(key: str, bound_name: str, bound_value: Any) -> Any:
    """The relationships whose value of the attribute lies outside the bound, by source record."""
    numeric_value = cast(ObjectRelation.attributes[key].as_string(), Numeric)
    violation = (
        numeric_value < bound_value if bound_name == "minimum" else numeric_value > bound_value
    )
    from_object = aliased(RdmObject)
    to_object = aliased(RdmObject)
    return (
        select(ObjectRelation.from_object_id)
        .join(from_object, from_object.id == ObjectRelation.from_object_id)
        .join(to_object, to_object.id == ObjectRelation.to_object_id)
        .where(
            violation,
            _in_scope(from_object),
            _in_scope(to_object),
        )
        .subquery()
    )


def _count_relations_with_attribute(
    session: Session, pair: ObjectTypeRelationDefinition, key: str
) -> int:
    from_object = aliased(RdmObject)
    to_object = aliased(RdmObject)
    # ``->`` answers SQL NULL only for a missing key; a key holding JSON null counts.
    has_key = ObjectRelation.attributes.op("->")(key).is_not(None)
    return int(
        session.scalar(
            select(func.count())
            .select_from(ObjectRelation)
            .join(from_object, from_object.id == ObjectRelation.from_object_id)
            .join(to_object, to_object.id == ObjectRelation.to_object_id)
            .where(
                ObjectRelation.relation_type_key == pair.relationTypeKey,
                from_object.object_type_key == pair.fromObjectTypeKey,
                to_object.object_type_key == pair.toObjectTypeKey,
                _in_scope(from_object),
                _in_scope(to_object),
                has_key,
            )
        )
        or 0
    )


def _missing_required_relation(
    relation_key: str,
    target_key: str,
    source_keys: set[str],
) -> Select[Any]:
    source = aliased(RdmObject)
    present = exists(
        select(ObjectRelation.sequence_id)
        .join(source, source.id == ObjectRelation.from_object_id)
        .where(
            ObjectRelation.to_object_id == RdmObject.id,
            ObjectRelation.relation_type_key == relation_key,
            source.object_type_key.in_(source_keys),
            _in_scope(source),
        )
    )
    return _objects(RdmObject.object_type_key == target_key, ~present)


def _relation_identity(item: ObjectTypeRelationDefinition) -> tuple[str, str, str]:
    return item.relationTypeKey, item.fromObjectTypeKey, item.toObjectTypeKey


def _cardinality_restrictions(pair: ObjectTypeRelationDefinition) -> set[str]:
    return {end for end in ("from", "to") if pair.holds_one(end)}


def is_parent_pair(model: EngineModel, pair: ObjectTypeRelationDefinition) -> bool:
    child = model.object_type(pair.toObjectTypeKey)
    return bool(child and pair.relationTypeKey in child.behavior.get("parentRelationTypeKeys", ()))


def _append_counted(
    diagnostics: list[ModelDiagnostic],
    count: int,
    code: str,
    path: str,
    message: str,
) -> None:
    if count:
        diagnostics.append(
            ModelDiagnostic(
                severity="error",
                code=code,
                path=path,
                message=message,
                count=count,
            )
        )


def _append_records(
    diagnostics: list[ModelDiagnostic],
    session: Session,
    records: Select[Any],
    code: str,
    path: str,
    message: str,
    *,
    count: int | None = None,
) -> None:
    """A rule records break: ``records`` selects their IDs, counted unless the rule counts
    something else (``count``: groups, values or relationships), and listed when the analysis
    lists (D72)."""
    if count is None:
        count = int(session.scalar(select(func.count()).select_from(records.subquery())) or 0)
    listing = _LISTING.get()
    if count and listing is not None:
        listing(records, code, path, message)
    _append_counted(diagnostics, count, code, path, message)


def _relation_path(identity: tuple[str, str, str]) -> str:
    return "/objectTypeRelations/" + "/".join(_pointer(item) for item in identity)


def _pointer(value: str) -> str:
    return value.replace("~", "~0").replace("/", "~1")
