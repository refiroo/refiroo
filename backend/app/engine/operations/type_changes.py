"""A record's type changes in a change set (Base 0.8 C1, ADR-034).

A type change keeps the record's ID, history and every relationship its new type may have (D37).
It is staged in a change set only (D38), to one of the record's application's types (D39), and
nothing is declared for it in the model: the caller gives the attribute mapping, which the C2
planner derives by the D40 rules and the user may change.

One record changes per call, optionally under a new parent:

- values are kept (same attribute type), mapped (another source of the same value type, or a
  widening that loses nothing), restored or given as inputs; the rest have no place;
- the containment edge becomes the relation the model allows between the parent and the new type,
  and each child's edge the relation the new type may contain it by (a child the new type cannot
  contain is refused here; the planner cascades);
- relationships the new type may not have are removed, the others kept with their IDs, and those
  offered back are restored with their former IDs;
- uniqueness, required values and relations, uniqueness scopes and cycles are checked by the
  change set write services, in the same transaction;
- a ``reclassified`` audit event records the full before state.

Derived state follows the change set rows through their flush hooks: the typed value index, matrix
cell states and the search index. Relation set versions advance for each relationship whose binding
the type change moves, removes or adds.

:func:`change_object_type` writes into the session and neither claims nor commits, so an operation
of many records claims its change set once. :func:`apply_type_change` claims and commits one change;
:func:`check_type_change` runs the same checks and keeps nothing.
"""

from collections.abc import Collection, Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any, Literal
from uuid import uuid4

from sqlalchemy.orm import Session

from ...errors import api_error
from ...models.database import ChangeSet, ChangeSetObject
from ...models.schema import EngineModel, ObjectTypeDefinition
from ..change_sets.access import change_set_model, load_change_set
from ..change_sets.records import (
    advance_relation_sets,
    place_record,
    require_record_version,
    sync_containment_edge,
    validate_change_set_relation,
)
from ..records import rules
from ..records.attributes import validate_attributes, validate_object_attribute_rules
from ..records.audit import record_audit_event
from ..records.context import ChangeSetLookup
from ..records.feed import object_subject
from ..records.refusals import CHANGE_SET
from ..records.relation_set_versions import increment_set_versions
from ..records.values import WIDENINGS, stored_json_value
from ..records.writes import ChangeSetWrites


class Keep:
    def __repr__(self) -> str:
        return "KEEP"


KEEP_PARENT = Keep()


AttributeOutcomeKind = Literal["kept", "mapped", "restored", "input", "empty"]


@dataclass(frozen=True)
class RelationInput:
    """A relationship to create with the type change, as object creation's ``initialRelations``."""

    relation_type_key: str
    direction: Literal["incoming", "outgoing"]
    object_id: str
    attributes: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class RestoredRelation:
    """A relationship offered back from an effective reclassification, with its former ID."""

    relation_id: str
    relation_type_key: str
    from_object_id: str
    to_object_id: str
    attributes: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class TypeChange:
    """One record's new type, and where each value of the new type comes from.

    ``mapping`` names, per attribute type of the new type, its source attribute type on the old
    type, or ``None`` for none; an attribute not listed keeps the same attribute type when the old
    type binds it. ``values`` are inputs and win over the mapping; a ``None`` input leaves an
    optional attribute empty. ``restored_values`` are values offered back.
    """

    object_id: str
    object_type_key: str
    parent_object_id: str | None | Keep = KEEP_PARENT
    mapping: Mapping[str, str | None] = field(default_factory=dict)
    values: Mapping[str, Any] = field(default_factory=dict)
    relations: Sequence[RelationInput] = ()
    restored_values: Mapping[str, Any] = field(default_factory=dict)
    restored_relations: Sequence[RestoredRelation] = ()
    expected_record_version: int | None = None


@dataclass(frozen=True)
class AttributeOutcome:
    attribute_type_key: str
    source: str | None
    outcome: AttributeOutcomeKind
    value: Any


@dataclass(frozen=True)
class RelationshipState:
    """A relationship as the record held it, with the other end as the change set holds it."""

    relation_id: str
    relation_type_key: str
    direction: Literal["incoming", "outgoing"]
    from_object_id: str
    to_object_id: str
    other_object_id: str
    other_object_type_key: str
    other_name: str
    attributes: dict[str, Any]
    version: int

    def payload(self) -> dict[str, Any]:
        return {
            "relationId": self.relation_id,
            "relationTypeKey": self.relation_type_key,
            "direction": self.direction,
            "fromObjectId": self.from_object_id,
            "toObjectId": self.to_object_id,
            "otherObjectId": self.other_object_id,
            "otherObjectTypeKey": self.other_object_type_key,
            "attributes": self.attributes,
            "version": self.version,
        }


@dataclass(frozen=True)
class TypeChangeResult:
    object_id: str
    before_type_key: str
    after_type_key: str
    before_parent_id: str | None
    after_parent_id: str | None
    attributes: tuple[AttributeOutcome, ...]
    values_without_place: dict[str, Any]
    relationships_without_place: tuple[RelationshipState, ...]
    kept_relation_ids: tuple[str, ...]
    restored_relation_ids: tuple[str, ...]
    created_relation_ids: tuple[str, ...]
    version: int


def attribute_value_types_compatible(source: str, target: str) -> bool:
    """The same value type, or a widening that loses nothing (D40)."""
    return source == target or (source, target) in WIDENINGS


def apply_type_change(
    session: Session,
    change_set_id: str,
    expected_change_set_version: int,
    change: TypeChange,
    *,
    operation_id: str | None = None,
) -> TypeChangeResult:
    """Claim the change set, change one record's type and commit."""
    change_set = load_change_set(session, change_set_id, for_update=True)
    model = change_set_model(session, change_set)
    ChangeSetWrites(session, change_set).claim(expected_change_set_version)
    result = change_object_type(
        session, change_set, model, change, operation_id=operation_id or str(uuid4())
    )
    session.commit()
    return result


def check_type_change(session: Session, change_set_id: str, change: TypeChange) -> TypeChangeResult:
    """Run every check of :func:`apply_type_change` and keep no write.

    The writes are made and read back through the same lookups, then rolled back, so a check
    refuses exactly what applying would.
    """
    try:
        change_set = load_change_set(session, change_set_id, for_update=True)
        model = change_set_model(session, change_set)
        return change_object_type(session, change_set, model, change, operation_id=str(uuid4()))
    finally:
        session.rollback()


def change_object_type(
    session: Session,
    change_set: ChangeSet,
    model: EngineModel,
    change: TypeChange,
    *,
    operation_id: str,
    deferred_children: Collection[str] = (),
) -> TypeChangeResult:
    """Write one record's type change into the session; the caller claims and commits.

    ``deferred_children`` are children whose own type change follows in the same operation (the
    C2 cascade); their containment edges are left to that change's parent sync.
    """
    lookup = ChangeSetLookup.of(session, change_set.id)
    record = lookup.object(change.object_id)
    if record is None:
        raise api_error(
            404, "OBJECT_NOT_FOUND", f"Object '{change.object_id}' not found in change set"
        )
    old_type = model.object_type(record.object_type_key)
    new_type = model.object_type(change.object_type_key)
    if new_type is None:
        raise api_error(
            422,
            "UNKNOWN_OBJECT_TYPE",
            f"Object type '{change.object_type_key}' is not in the pinned model",
            {"objectTypeKey": change.object_type_key},
        )
    if old_type is None or old_type.key == new_type.key:
        raise api_error(
            422,
            "OBJECT_TYPE_UNCHANGED",
            f"Object '{change.object_id}' is already a '{new_type.key}' record",
            {"objectId": change.object_id, "objectTypeKey": new_type.key},
        )
    rules.object_identity(model, record.application_key, new_type.key, CHANGE_SET)
    ChangeSetWrites(session, change_set).permit_type_change(
        record, record.application_key, new_type.key
    )

    old_values = dict(record.attributes or {})
    outcomes, values = _new_values(model, old_type, new_type, old_values, change)
    used = {item.source for item in outcomes if item.outcome in {"kept", "mapped"}}
    without_place = {key: value for key, value in old_values.items() if key not in used}

    require_record_version(change.expected_record_version, record.version, "Object record")
    row = editable_row(session, change_set, record)
    before_parent = record.parent_object_id
    after_parent = (
        before_parent
        if isinstance(change.parent_object_id, Keep)
        else change.parent_object_id
    )

    # The record's relationships as the old type held them, before any row changes.
    old_keys = model.containment_relation_keys(old_type.key)
    touching = lookup.relations([record.object_id], "both")
    ends = lookup.objects(
        end
        for relation in touching
        for end in (relation.from_object_id, relation.to_object_id)
        if end != record.object_id
    )
    others = []
    for relation in touching:
        if relation.to_object_id == record.object_id and relation.relation_type_key in old_keys:
            continue  # the record's own containment edge, which the parent sync replaces
        other_id = (
            relation.to_object_id
            if relation.from_object_id == record.object_id
            else relation.from_object_id
        )
        other = ends.get(other_id, record)
        if relation.from_object_id == record.object_id and relation.relation_type_key in (
            model.containment_relation_keys(other.object_type_key)
        ):
            continue  # an edge to a child, which the child sync re-types
        others.append((relation, other))

    row.object_type_key = new_type.key
    row.parent_object_id = after_parent
    row.attributes = values
    row.version += 1
    row.is_deleted = False
    rules.unique_values(lookup, model, row.object_id, values)
    place_record(
        session, change_set, model, row, lookup, previous_type_key=old_type.key
    )
    _sync_children(session, change_set, model, lookup, row, frozenset(deferred_children))

    kept, lost = _classify_relationships(model, record.object_id, old_type, new_type, others)
    for relation, other, _state in lost:
        _advance_old_binding(session, change_set, record, old_type.key, relation, other)
        _remove_relation(session, change_set, relation)
    for relation, other, _state in kept:
        # Its binding moves from the old type to the new one: both sets advance.
        _advance_old_binding(session, change_set, record, old_type.key, relation, other)
        advance_relation_sets(session, change_set, lookup, relation)
    for relation, _other, _state in kept:
        validate_change_set_relation(
            model,
            lookup,
            relation.relation_type_key,
            relation.from_object_id,
            relation.to_object_id,
            dict(relation.attributes or {}),
            exclude_id=relation.relation_id,
        )
    restored = [
        _restore_relation(session, change_set, model, lookup, restoring)
        for restoring in change.restored_relations
    ]
    created = [
        _create_relation(session, change_set, model, lookup, row.object_id, item)
        for item in change.relations
    ]
    _require_relations(model, lookup, row)
    _recheck_scopes(model, lookup, row.object_id, old_type.key, new_type.key)

    lost_states = tuple(state for _relation, _other, state in lost)
    changed_fields = ["objectType"]
    if after_parent != before_parent:
        changed_fields.append("parent")
    if any(
        values.get(key) != old_values.get(key) for key in set(values) | set(old_values)
    ):
        changed_fields.append("attributes")
    if lost_states or restored or created:
        changed_fields.append("relationships")
    event_changes: dict[str, Any] = {
        "changeSetId": change_set.id,
        "operationId": operation_id,
        "objectType": {"before": old_type.key, "after": new_type.key},
        "mapping": {
            item.attribute_type_key: {"from": item.source, "outcome": item.outcome}
            for item in outcomes
        },
        "attributes": values,
        "before": {
            "name": record.name,
            "parentObjectId": before_parent,
            "attributes": old_values,
            "relationships": [state.payload() for state in lost_states],
        },
        "restoredRelationIds": restored,
        "createdRelationIds": created,
        "changedFields": changed_fields,
        # Each attribute type given a value, each mapped value's source, and each without a place.
        "attributeTypeKeys": sorted(
            {item.attribute_type_key for item in outcomes if item.outcome != "empty"}
            | {item.source for item in outcomes if item.outcome == "mapped"}
            | set(without_place)
        ),
    }
    if after_parent != before_parent:
        event_changes["parent"] = {"before": before_parent, "after": after_parent}
    record_audit_event(
        session,
        aggregate_type="change-set-object",
        aggregate_id=row.object_id,
        action="reclassified",
        version=row.version,
        changes=event_changes,
        object_ids=[row.object_id, *(state.other_object_id for state in lost_states)],
        subject=object_subject(row, old_type.key),
    )
    session.flush()
    return TypeChangeResult(
        object_id=row.object_id,
        before_type_key=old_type.key,
        after_type_key=new_type.key,
        before_parent_id=before_parent,
        after_parent_id=after_parent,
        attributes=tuple(outcomes),
        values_without_place=without_place,
        relationships_without_place=lost_states,
        kept_relation_ids=tuple(relation.relation_id for relation, _other, _state in kept),
        restored_relation_ids=tuple(restored),
        created_relation_ids=tuple(created),
        version=row.version,
    )


def editable_row(session: Session, change_set: ChangeSet, record: Any) -> ChangeSetObject:
    """The change set's own row for an effective record, copied from its base when it has none."""
    return ChangeSetWrites(session, change_set).own_object(record)


def _new_values(
    model: EngineModel,
    old_type: ObjectTypeDefinition,
    new_type: ObjectTypeDefinition,
    old_values: dict[str, Any],
    change: TypeChange,
) -> tuple[list[AttributeOutcome], dict[str, Any]]:
    """Each attribute of the new type with its source and outcome, and the values it stores."""
    old_bindings = {item.attributeTypeKey for item in old_type.attributes}
    new_bindings = {item.attributeTypeKey for item in new_type.attributes}
    for label, keys in (
        ("mapping", change.mapping),
        ("values", change.values),
        ("restored values", change.restored_values),
    ):
        unknown = sorted(set(keys) - new_bindings)
        if unknown:
            raise api_error(
                422,
                "UNKNOWN_ATTRIBUTES",
                f"Attributes in the {label} are not bound on '{new_type.key}': {unknown}",
                {"objectTypeKey": new_type.key, "attributeTypeKeys": unknown},
            )
    # Inputs are authored values: the new type's write rules apply, read-only bindings included.
    inputs = validate_attributes(
        model, new_type, dict(change.values), partial=True, apply_defaults=False
    )
    outcomes: list[AttributeOutcome] = []
    values: dict[str, Any] = {}
    for binding in new_type.attributes:
        key = binding.attributeTypeKey
        source = change.mapping.get(key, key if key in old_bindings else None)
        if source is not None:
            _require_compatible(model, old_bindings, old_type.key, source, key)
        if key in change.values:
            outcome, value = "input", inputs[key]
        elif key in change.restored_values:
            outcome, value = "restored", change.restored_values[key]
        elif source is not None and old_values.get(source) is not None:
            outcome, value = ("kept" if source == key else "mapped"), old_values[source]
        else:
            outcome, value = "empty", None
        if value is not None:
            values[key] = value
        outcomes.append(
            AttributeOutcome(key, source if outcome in {"kept", "mapped"} else None, outcome, value)
        )
    # Moved values pass the new binding's validation as stored values do; a value that does not
    # fit is an input to provide.
    normalized = validate_attributes(
        model, new_type, values, partial=False, apply_defaults=False, allow_read_only=True
    )
    validate_object_attribute_rules(new_type, normalized)
    stored = {key: stored_json_value(value) for key, value in normalized.items()}
    return [
        AttributeOutcome(item.attribute_type_key, item.source, item.outcome, stored.get(item.attribute_type_key))
        for item in outcomes
    ], stored


def _require_compatible(
    model: EngineModel, old_bindings: set[str], old_type_key: str, source: str, target: str
) -> None:
    if source not in old_bindings:
        raise api_error(
            422,
            "INVALID_TYPE_MAPPING",
            f"Source attribute '{source}' is not bound on '{old_type_key}'",
            {"attributeTypeKey": target, "from": source},
        )
    source_type = model.attribute_type(source).valueType
    target_type = model.attribute_type(target).valueType
    if not attribute_value_types_compatible(source_type, target_type):
        raise api_error(
            422,
            "INVALID_TYPE_MAPPING",
            f"A {source_type} value of '{source}' cannot become the {target_type} '{target}'",
            {
                "attributeTypeKey": target,
                "from": source,
                "fromValueType": source_type,
                "valueType": target_type,
            },
        )


def _classify_relationships(
    model: EngineModel,
    object_id: str,
    old_type: ObjectTypeDefinition,
    new_type: ObjectTypeDefinition,
    relations: list[tuple[Any, Any]],
) -> tuple[list[tuple[Any, Any, RelationshipState]], list[tuple[Any, Any, RelationshipState]]]:
    """Split the record's other relationships into those the new type keeps and those it cannot
    have: a relationship stays when the model binds the same relation type, in the same direction,
    between the other end's type and the new type."""
    kept, lost = [], []
    for relation, other in relations:
        outgoing = relation.from_object_id == object_id
        incoming = relation.to_object_id == object_id

        def at(end_is_record: bool, other_type: str, record_type: str) -> str:
            return record_type if end_is_record else other_type

        from_new = at(outgoing, other.object_type_key, new_type.key)
        to_new = at(incoming, other.object_type_key, new_type.key)
        state = RelationshipState(
            relation_id=relation.relation_id,
            relation_type_key=relation.relation_type_key,
            direction="outgoing" if outgoing else "incoming",
            from_object_id=relation.from_object_id,
            to_object_id=relation.to_object_id,
            other_object_id=other.object_id,
            other_object_type_key=other.object_type_key,
            other_name=other.name,
            attributes=dict(relation.attributes or {}),
            version=relation.version,
        )
        if model.allowed_relation(relation.relation_type_key, from_new, to_new) is not None:
            kept.append((relation, other, state))
            continue
        old_binding = model.allowed_relation(
            relation.relation_type_key,
            at(outgoing, other.object_type_key, old_type.key),
            at(incoming, other.object_type_key, old_type.key),
        )
        if old_binding is not None and old_binding.required and outgoing and not incoming:
            # The other end needs this relationship; removing it would break that record.
            raise api_error(
                422,
                "REQUIRED_RELATION_WITHOUT_PLACE",
                f"'{new_type.key}' cannot hold relationship '{relation.relation_type_key}', "
                f"which '{other.object_id}' requires",
                {
                    "relationId": relation.relation_id,
                    "relationTypeKey": relation.relation_type_key,
                    "objectId": other.object_id,
                },
            )
        lost.append((relation, other, state))
    return kept, lost


def _remove_relation(session: Session, change_set: ChangeSet, relation: Any) -> None:
    """Tombstone a relationship the new type has no place for."""
    ChangeSetWrites(session, change_set).remove_relation(relation)


def _advance_old_binding(
    session: Session,
    change_set: ChangeSet,
    record: Any,
    old_type_key: str,
    relation: Any,
    other: Any,
) -> None:
    """Advance a relationship's sets under the binding the old type gave it."""
    def type_of(end: str) -> str:
        return old_type_key if end == record.object_id else other.object_type_key

    increment_set_versions(
        session,
        workspace_key=change_set.workspace_key,
        change_set_id=change_set.id,
        relation_type_key=relation.relation_type_key,
        from_object_type_key=type_of(relation.from_object_id),
        to_object_type_key=type_of(relation.to_object_id),
        from_object_id=relation.from_object_id,
        to_object_id=relation.to_object_id,
    )


def _sync_children(
    session: Session,
    change_set: ChangeSet,
    model: EngineModel,
    lookup: ChangeSetLookup,
    row: ChangeSetObject,
    deferred: frozenset[str] = frozenset(),
) -> None:
    """Re-type each child's containment edge to the relation the new type contains it by."""
    for child in lookup.children([row.object_id]):
        if child.object_id in deferred:
            continue
        allowed = [
            binding
            for key in sorted(model.containment_relation_keys(child.object_type_key))
            if (binding := model.allowed_relation(key, row.object_type_key, child.object_type_key))
        ]
        if len(allowed) != 1:
            raise api_error(
                422,
                "CHILD_TYPE_NOT_ALLOWED",
                f"A '{row.object_type_key}' record cannot contain '{child.object_type_key}' "
                f"record '{child.object_id}'",
                {
                    "objectId": row.object_id,
                    "objectTypeKey": row.object_type_key,
                    "childObjectId": child.object_id,
                    "childObjectTypeKey": child.object_type_key,
                },
            )
        sync_containment_edge(
            session,
            change_set,
            model,
            lookup,
            child_id=child.object_id,
            child_type_key=child.object_type_key,
            parent=row,
        )


def _restore_relation(
    session: Session,
    change_set: ChangeSet,
    model: EngineModel,
    lookup: ChangeSetLookup,
    restoring: RestoredRelation,
) -> str:
    """Bring back a relationship the record lost, under its former ID."""
    if lookup.relation(restoring.relation_id) is not None:
        raise api_error(
            409,
            "RELATION_ALREADY_EXISTS",
            f"Relation '{restoring.relation_id}' already exists in the change set",
            {"relationId": restoring.relation_id},
        )
    attributes = validate_change_set_relation(
        model,
        lookup,
        restoring.relation_type_key,
        restoring.from_object_id,
        restoring.to_object_id,
        dict(restoring.attributes),
    )
    writes = ChangeSetWrites(session, change_set)
    writes.permit(relations=[(restoring.from_object_id, restoring.to_object_id)])
    stored = writes.stored_relation(restoring.relation_id)
    if stored is None:
        stored = writes.add_relation(
            restoring.relation_type_key,
            restoring.from_object_id,
            restoring.to_object_id,
            attributes,
            relation_id=restoring.relation_id,
        )
    else:
        stored.relation_type_key = restoring.relation_type_key
        stored.from_object_id = restoring.from_object_id
        stored.to_object_id = restoring.to_object_id
        stored.attributes = attributes
        stored.version += 1
        stored.is_deleted = False
    advance_relation_sets(session, change_set, lookup, stored)
    return stored.relation_id


def _create_relation(
    session: Session,
    change_set: ChangeSet,
    model: EngineModel,
    lookup: ChangeSetLookup,
    object_id: str,
    item: RelationInput,
) -> str:
    from_id, to_id = (
        (object_id, item.object_id) if item.direction == "outgoing" else (item.object_id, object_id)
    )
    attributes = validate_change_set_relation(
        model, lookup, item.relation_type_key, from_id, to_id, dict(item.attributes)
    )
    relation = ChangeSetWrites(session, change_set).add_relation(
        item.relation_type_key, from_id, to_id, attributes
    )
    advance_relation_sets(session, change_set, lookup, relation)
    return relation.relation_id


def _require_relations(model: EngineModel, lookup: ChangeSetLookup, row: ChangeSetObject) -> None:
    """The new type's required incoming relationships, as object creation requires them."""
    parents = model.containment_relation_keys(row.object_type_key)
    required: dict[str, set[str]] = {}
    for item in model.objectTypeRelations:
        if (
            item.toObjectTypeKey == row.object_type_key
            and item.required
            and item.relationTypeKey not in parents
        ):
            required.setdefault(item.relationTypeKey, set()).add(item.fromObjectTypeKey)
    if not required:
        return
    incoming = lookup.relations([row.object_id], "incoming", sorted(required))
    sources = lookup.objects(relation.from_object_id for relation in incoming)
    missing = sorted(
        key
        for key, types in required.items()
        if not any(
            relation.relation_type_key == key
            and relation.from_object_id in sources
            and sources[relation.from_object_id].object_type_key in types
            for relation in incoming
        )
    )
    if missing:
        raise api_error(
            422,
            "MISSING_REQUIRED_RELATIONS",
            f"Required relationships missing: {missing}",
            {"objectId": row.object_id, "relationTypeKeys": missing},
        )


def _recheck_scopes(
    model: EngineModel,
    lookup: ChangeSetLookup,
    object_id: str,
    old_type_key: str,
    new_type_key: str,
) -> None:
    """Re-check ancestor-scoped uniqueness below the record when its type starts or stops being
    a scope (``uniqueToAncestorTypeKey``): relations into its subtree may now share or lose one.

    It reads the subtree level by level only when a scoped binding names either type.
    """
    scoped = [
        item
        for item in model.objectTypeRelations
        if item.features.get("uniqueToAncestorTypeKey") in {old_type_key, new_type_key}
    ]
    if not scoped:
        return
    keys = sorted({item.relationTypeKey for item in scoped})
    targets = {item.toObjectTypeKey for item in scoped}
    subtree, frontier = [object_id], [object_id]
    while frontier:
        frontier = [child.object_id for child in lookup.children(frontier)]
        subtree.extend(frontier)
    records = lookup.objects(subtree)
    ids = [key for key, item in records.items() if item.object_type_key in targets]
    for relation in lookup.relations(ids, "incoming", keys):
        validate_change_set_relation(
            model,
            lookup,
            relation.relation_type_key,
            relation.from_object_id,
            relation.to_object_id,
            dict(relation.attributes or {}),
            exclude_id=relation.relation_id,
        )
