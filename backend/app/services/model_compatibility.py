from collections import defaultdict
from typing import Any

from sqlalchemy import and_, exists, func, literal, or_, select
from sqlalchemy.orm import Session, aliased

from ..models.database import AttributeValue, ObjectRelation, RdmObject
from ..models.schema import EngineModel, ObjectTypeRelationDefinition
from .attributes import VALUE_COLUMNS, normalize_value
from .model_compiler import ModelDiagnostic


class CompatibilityResult:
    def __init__(self, active_release_id: str, diagnostics: list[ModelDiagnostic]):
        self.classification = "migration_required" if diagnostics else "compatible"
        self.active_release_id = active_release_id
        self.diagnostics = tuple(diagnostics)


def analyze_compatibility(
    session: Session,
    active_model: EngineModel,
    candidate_model: EngineModel,
    active_release_id: str,
) -> CompatibilityResult:
    """Assess a valid candidate against stored runtime data using bounded SQL queries."""
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
            "application_in_use",
            f"/applications/{_pointer(key)}",
            f"Application '{key}' is used by stored objects",
        )

    for key in sorted(set(active_objects) - set(candidate_objects)):
        _append_counted(
            diagnostics,
            _count_objects(session, RdmObject.object_type_key == key),
            "object_type_in_use",
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
                "application_object_type_in_use",
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
            "attribute_type_in_use",
            f"/attributeTypes/{_pointer(key)}",
            f"Attribute type '{key}' has stored values",
        )

    for key in sorted(set(active_attributes) & set(candidate_attributes)):
        if active_attributes[key].valueType != candidate_attributes[key].valueType:
            _append_counted(
                diagnostics,
                _count_attribute_values(session, key),
                "attribute_value_type_changed",
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
                "attribute_binding_in_use",
                f"/objectTypes/{_pointer(object_type_key)}/attributes/{_pointer(key)}",
                f"Attribute '{key}' has stored values on object type '{object_type_key}'",
            )
        for key, binding in sorted(candidate_bindings.items()):
            active_binding = active_bindings.get(key)
            if binding.required and (active_binding is None or not active_binding.required):
                count = _count_missing_required_attribute(
                    session,
                    object_type_key,
                    key,
                    candidate_attributes[key].valueType,
                )
                _append_counted(
                    diagnostics,
                    count,
                    "required_attribute_missing",
                    f"/objectTypes/{_pointer(object_type_key)}/attributes/{_pointer(key)}/required",
                    f"Stored '{object_type_key}' objects do not satisfy required attribute '{key}'",
                )

        active_rule = tuple(active_objects[object_type_key].validation.get("atLeastOneOf", ()))
        candidate_rule = tuple(
            candidate_objects[object_type_key].validation.get("atLeastOneOf", ())
        )
        if candidate_rule and candidate_rule != active_rule:
            count = _count_missing_at_least_one(
                session,
                object_type_key,
                candidate_rule,
                candidate_attributes,
            )
            _append_counted(
                diagnostics,
                count,
                "object_validation_rule_violated",
                f"/objectTypes/{_pointer(object_type_key)}/validation/atLeastOneOf",
                f"Stored '{object_type_key}' objects do not satisfy atLeastOneOf",
            )

    for key, attribute in sorted(candidate_attributes.items()):
        active_attribute = active_attributes.get(key)
        if attribute.features.get("unique") and (
            active_attribute is None or not active_attribute.features.get("unique")
        ):
            count = _count_duplicate_attribute_groups(session, key, attribute.valueType)
            _append_counted(
                diagnostics,
                count,
                "attribute_uniqueness_violated",
                f"/attributeTypes/{_pointer(key)}/features/unique",
                f"Stored values violate uniqueness for attribute '{key}'",
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
        count = int(
            session.scalar(
                select(func.count())
                .select_from(AttributeValue)
                .where(
                    AttributeValue.attribute_type_key == key,
                    operator(candidate_value),
                )
            )
            or 0
        )
        _append_counted(
            diagnostics,
            count,
            "attribute_validation_violated",
            f"/attributeTypes/{_pointer(key)}/validation/{bound}",
            f"Stored values violate {bound} for attribute '{key}'",
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
            "relation_pair_in_use",
            _relation_path(identity),
            f"Allowed relation {identity!r} is used by stored relations",
        )

    for identity in sorted(set(active_pairs) & set(candidate_pairs)):
        active_pair = active_pairs[identity]
        candidate_pair = candidate_pairs[identity]
        for key in sorted(set(active_pair.attributeTypeKeys) - set(candidate_pair.attributeTypeKeys)):
            count = _count_relations_with_attribute(session, active_pair, key)
            _append_counted(
                diagnostics,
                count,
                "relation_attribute_in_use",
                f"{_relation_path(identity)}/attributeTypeKeys/{_pointer(key)}",
                f"Relation attribute '{key}' has stored values",
            )
        for key in sorted(set(active_pair.attributeTypeKeys) & set(candidate_pair.attributeTypeKeys)):
            if active_attributes[key].valueType != candidate_attributes[key].valueType:
                count = _count_relations_with_attribute(session, active_pair, key)
                _append_counted(
                    diagnostics,
                    count,
                    "relation_attribute_value_type_changed",
                    f"/attributeTypes/{_pointer(key)}/valueType",
                    f"Relation attribute '{key}' changes the type of stored values",
                )

    required_by_target: dict[tuple[str, str], set[str]] = defaultdict(set)
    active_required_keys = {
        (pair.relationTypeKey, pair.toObjectTypeKey)
        for pair in active_pairs.values()
        if pair.required and not _is_parent_pair(active_model, pair)
    }
    for pair in candidate_pairs.values():
        if pair.required and not _is_parent_pair(candidate_model, pair):
            required_by_target[(pair.relationTypeKey, pair.toObjectTypeKey)].add(
                pair.fromObjectTypeKey
            )
    for (relation_key, target_key), source_keys in sorted(required_by_target.items()):
        if (relation_key, target_key) in active_required_keys:
            continue
        count = _count_missing_required_relation(
            session, relation_key, target_key, source_keys
        )
        _append_counted(
            diagnostics,
            count,
            "required_relation_missing",
            f"/objectTypeRelations/{_pointer(relation_key)}/*/{_pointer(target_key)}/required",
            f"Stored '{target_key}' objects lack required relation '{relation_key}'",
        )

    for identity, pair in sorted(candidate_pairs.items()):
        active_pair = active_pairs.get(identity)
        active_restrictions = _cardinality_restrictions(active_pair.cardinality) if active_pair else set()
        candidate_restrictions = _cardinality_restrictions(pair.cardinality)
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
            count = _count_scoped_uniqueness_violations(session, pair, candidate_model)
            _append_counted(
                diagnostics,
                count,
                "relation_uniqueness_violated",
                f"{_relation_path(identity)}/features/uniqueToAncestorTypeKey",
                f"Stored relations violate scoped uniqueness for '{pair.relationTypeKey}'",
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
            count = _count_objects(
                session,
                RdmObject.object_type_key == object_type.key,
                RdmObject.parent_object_id.is_(None),
            )
            _append_counted(
                diagnostics,
                count,
                "parent_required",
                f"/objectTypes/{_pointer(object_type.key)}/features/rootCreatable",
                f"Stored '{object_type.key}' objects require a parent",
            )

    for pair in active_model.objectTypeRelations:
        if not _is_parent_pair(active_model, pair):
            continue
        identity = _relation_identity(pair)
        candidate_child = candidate_objects.get(pair.toObjectTypeKey)
        candidate_relation = candidate_relations.get(pair.relationTypeKey)
        active_relation = active_relations[pair.relationTypeKey]
        remains_parent = (
            candidate_child is not None
            and identity in candidate_pairs
            and pair.relationTypeKey
            in candidate_child.behavior.get("parentRelationTypeKeys", ())
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
                "parent_relation_semantics_changed",
                f"/objectTypes/{_pointer(pair.toObjectTypeKey)}/behavior/parentRelationTypeKeys",
                f"Stored containment uses parent relation '{pair.relationTypeKey}'",
            )


def _check_cardinality(
    session: Session,
    identity: tuple[str, str, str],
    pair: ObjectTypeRelationDefinition,
    diagnostics: list[ModelDiagnostic],
) -> None:
    if pair.cardinality == "many-to-many":
        return
    from_object = aliased(RdmObject)
    to_object = aliased(RdmObject)
    base = (
        select(ObjectRelation)
        .join(from_object, from_object.id == ObjectRelation.from_object_id)
        .join(to_object, to_object.id == ObjectRelation.to_object_id)
        .where(
            ObjectRelation.relation_type_key == pair.relationTypeKey,
            from_object.object_type_key == pair.fromObjectTypeKey,
            to_object.object_type_key == pair.toObjectTypeKey,
        )
    )
    groups = [ObjectRelation.to_object_id]
    if pair.cardinality == "one-to-one":
        groups.append(ObjectRelation.from_object_id)
    count = 0
    for group in groups:
        conflicts = base.with_only_columns(group).group_by(group).having(func.count() > 1).subquery()
        count += int(session.scalar(select(func.count()).select_from(conflicts)) or 0)
    _append_counted(
        diagnostics,
        count,
        "relation_cardinality_violated",
        f"{_relation_path(identity)}/cardinality",
        f"Stored relations violate cardinality '{pair.cardinality}'",
    )


def _count_scoped_uniqueness_violations(
    session: Session,
    pair: ObjectTypeRelationDefinition,
    model: EngineModel,
) -> int:
    ancestor_type = pair.features["uniqueToAncestorTypeKey"]
    lineage = select(
        RdmObject.id.label("descendant_id"),
        RdmObject.id.label("ancestor_id"),
        RdmObject.parent_object_id.label("parent_id"),
        RdmObject.object_type_key.label("ancestor_type"),
        literal(0).label("depth"),
    ).cte("object_lineage", recursive=True)
    parent = aliased(RdmObject)
    lineage = lineage.union_all(
        select(
            lineage.c.descendant_id,
            parent.id,
            parent.parent_object_id,
            parent.object_type_key,
            lineage.c.depth + 1,
        ).join(parent, parent.id == lineage.c.parent_id)
    )
    nearest = (
        select(
            lineage.c.descendant_id,
            func.min(lineage.c.depth).label("minimum_depth"),
        )
        .where(lineage.c.ancestor_type == ancestor_type)
        .group_by(lineage.c.descendant_id)
        .subquery()
    )
    nearest_ancestor = (
        select(lineage.c.descendant_id, lineage.c.ancestor_id)
        .join(
            nearest,
            and_(
                nearest.c.descendant_id == lineage.c.descendant_id,
                nearest.c.minimum_depth == lineage.c.depth,
            ),
        )
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
    conflicts = (
        statement.group_by(
            ObjectRelation.from_object_id, nearest_ancestor.c.ancestor_id
        )
        .having(func.count() > 1)
        .subquery()
    )
    return int(session.scalar(select(func.count()).select_from(conflicts)) or 0)


def _count_objects(session: Session, *conditions: Any) -> int:
    return int(
        session.scalar(select(func.count()).select_from(RdmObject).where(*conditions)) or 0
    )


def _count_attribute_values(
    session: Session, attribute_key: str, object_type_key: str | None = None
) -> int:
    statement = select(func.count()).select_from(AttributeValue)
    if object_type_key is not None:
        statement = statement.join(RdmObject, RdmObject.id == AttributeValue.object_id).where(
            RdmObject.object_type_key == object_type_key
        )
    return int(
        session.scalar(statement.where(AttributeValue.attribute_type_key == attribute_key)) or 0
    )


def _count_missing_required_attribute(
    session: Session, object_type_key: str, attribute_key: str, value_type: str
) -> int:
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
    return _count_objects(
        session, RdmObject.object_type_key == object_type_key, ~present
    )


def _count_missing_at_least_one(
    session: Session,
    object_type_key: str,
    attribute_keys: tuple[str, ...],
    attribute_types: dict,
) -> int:
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
    return _count_objects(
        session,
        RdmObject.object_type_key == object_type_key,
        ~or_(*predicates),
    )


def _count_duplicate_attribute_groups(session: Session, key: str, value_type: str) -> int:
    column = getattr(AttributeValue, VALUE_COLUMNS[value_type])
    conditions = [AttributeValue.attribute_type_key == key, column.is_not(None)]
    if value_type in {"text", "longText"}:
        conditions.append(column != "")
    conflicts = (
        select(RdmObject.workspace_key, column)
        .join(AttributeValue, AttributeValue.object_id == RdmObject.id)
        .where(*conditions)
        .group_by(RdmObject.workspace_key, column)
        .having(func.count() > 1)
        .subquery()
    )
    return int(session.scalar(select(func.count()).select_from(conflicts)) or 0)


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
            )
        )
        or 0
    )


def _count_relations_with_attribute(
    session: Session, pair: ObjectTypeRelationDefinition, key: str
) -> int:
    from_object = aliased(RdmObject)
    to_object = aliased(RdmObject)
    dialect = session.get_bind().dialect.name
    if dialect == "postgresql":
        has_key = ObjectRelation.attributes.op("?")(key)
    else:
        escaped = key.replace('"', '\\"')
        has_key = func.json_type(ObjectRelation.attributes, f'$."{escaped}"').is_not(None)
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
                has_key,
            )
        )
        or 0
    )


def _count_missing_required_relation(
    session: Session,
    relation_key: str,
    target_key: str,
    source_keys: set[str],
) -> int:
    source = aliased(RdmObject)
    present = exists(
        select(ObjectRelation.sequence_id)
        .join(source, source.id == ObjectRelation.from_object_id)
        .where(
            ObjectRelation.to_object_id == RdmObject.id,
            ObjectRelation.relation_type_key == relation_key,
            source.object_type_key.in_(source_keys),
        )
    )
    return _count_objects(
        session,
        RdmObject.object_type_key == target_key,
        ~present,
    )


def _relation_identity(item: ObjectTypeRelationDefinition) -> tuple[str, str, str]:
    return item.relationTypeKey, item.fromObjectTypeKey, item.toObjectTypeKey


def _cardinality_restrictions(cardinality: str) -> set[str]:
    if cardinality == "one-to-one":
        return {"from", "to"}
    if cardinality == "one-to-many":
        return {"to"}
    return set()


def _is_parent_pair(model: EngineModel, pair: ObjectTypeRelationDefinition) -> bool:
    child = model.object_type(pair.toObjectTypeKey)
    return bool(
        child
        and pair.relationTypeKey in child.behavior.get("parentRelationTypeKeys", ())
    )


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


def _relation_path(identity: tuple[str, str, str]) -> str:
    return "/objectTypeRelations/" + "/".join(_pointer(item) for item in identity)


def _pointer(value: str) -> str:
    return value.replace("~", "~0").replace("/", "~1")
