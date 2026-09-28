from datetime import UTC, datetime
from typing import Any

from fastapi.encoders import jsonable_encoder
from sqlalchemy import or_, select, update
from sqlalchemy.orm import Session

from ..errors import api_error
from ..models.api import RelationCreate, RelationResponse
from ..models.database import ObjectRelation, RdmObject
from ..models.schema import EngineModel, ObjectTypeRelationDefinition
from .attributes import current_attribute_values, normalize_value
from .audit import record_audit_event
from .model.traversal import ancestor_type_keys
from .relation_set_versions import SetClaim, advance_set_versions, increment_set_versions


def find_allowed_relation(model: EngineModel, relation_type_key: str, from_type: str, to_type: str):
    relation_type = model.relation_type(relation_type_key)
    if not relation_type:
        raise api_error(
            404, "unknown_relation_type", f"Relation type '{relation_type_key}' not found"
        )
    allowed = next(
        (
            item
            for item in model.objectTypeRelations
            if item.relationTypeKey == relation_type_key
            and item.fromObjectTypeKey == from_type
            and item.toObjectTypeKey == to_type
        ),
        None,
    )
    if not allowed:
        raise api_error(
            422,
            "invalid_relation_pair",
            "Relation is not permitted between these object types",
        )
    return allowed


def validate_cardinality(session: Session, allowed, payload: RelationCreate) -> None:
    from_id = str(payload.fromObjectId)
    to_id = str(payload.toObjectId)
    clauses = []
    if allowed.cardinality == "one-to-one":
        clauses = [
            ObjectRelation.from_object_id == from_id,
            ObjectRelation.to_object_id == to_id,
        ]
    elif allowed.cardinality == "one-to-many":
        clauses = [ObjectRelation.to_object_id == to_id]
    if clauses:
        existing = session.scalar(
            select(ObjectRelation.id)
            .where(ObjectRelation.relation_type_key == payload.relationTypeKey, or_(*clauses))
            .limit(1)
        )
        if existing:
            raise api_error(409, "cardinality_violation", "Relation cardinality would be violated")


def validate_relation_attributes(
    model: EngineModel,
    allowed: ObjectTypeRelationDefinition,
    attributes: dict[str, Any],
) -> dict[str, Any]:
    permitted = set(allowed.attributeTypeKeys)
    unknown = set(attributes) - permitted
    if unknown:
        raise api_error(
            422,
            "unknown_relation_attributes",
            f"Unknown relation attributes: {sorted(unknown)}",
        )

    result: dict[str, Any] = {}
    for key, value in attributes.items():
        definition = model.attribute_type(key)
        if definition is None:  # Model validation should make this unreachable.
            raise api_error(500, "internal_error", f"Unknown model attribute '{key}'")
        result[key] = jsonable_encoder(normalize_value(definition, value))
    return result


def create_relation_instance(
    session: Session,
    model: EngineModel,
    payload: RelationCreate,
    *,
    from_object: RdmObject | None = None,
    to_object: RdmObject | None = None,
) -> ObjectRelation:
    """Create a relation in the live object store of a shared active workspace.

    Both endpoints must be live objects of the same active (non-retired) workspace.  Engine-
    maintained containment edges (the parent relation of an object type) are rejected here; they
    are written atomically when the owning object's parent changes.
    """
    from .objects import load_object
    from .workspaces import resolve_workspace

    from_object = from_object or load_object(session, str(payload.fromObjectId))
    to_object = to_object or load_object(session, str(payload.toObjectId))
    if from_object.workspace_key != to_object.workspace_key:
        raise api_error(422, "relation_wrong_scope", "Related objects must share a workspace")
    resolve_workspace(session, from_object.workspace_key, require_active=True)
    allowed = find_allowed_relation(
        model,
        payload.relationTypeKey,
        from_object.object_type_key,
        to_object.object_type_key,
    )
    ensure_relation_mutable(model, payload.relationTypeKey, to_object.object_type_key)
    validate_cardinality(session, allowed, payload)
    validate_unique_to_ancestor(session, allowed, payload, to_object)
    attributes = validate_relation_attributes(model, allowed, payload.attributes)
    relation = ObjectRelation(
        relation_type_key=payload.relationTypeKey,
        from_object_id=from_object.id,
        to_object_id=to_object.id,
        attributes=attributes,
    )
    session.add(relation)
    session.flush()
    record_audit_event(
        session,
        aggregate_type="relation",
        aggregate_id=relation.id,
        action="created",
        version=1,
        changes={
            **payload.model_dump(),
            "attributes": attributes,
        },
        object_ids=[from_object.id, to_object.id],
    )
    return relation


def validate_unique_to_ancestor(
    session: Session,
    allowed: ObjectTypeRelationDefinition,
    payload: RelationCreate,
    to_object: RdmObject,
    *,
    exclude_relation_id: str | None = None,
    exclude_relation_ids: set[str] | None = None,
) -> None:
    ancestor_type_key = allowed.features.get("uniqueToAncestorTypeKey")
    if not ancestor_type_key:
        return
    if not _matches_unique_condition(session, allowed, to_object):
        return
    ancestor_id = _ancestor_id(session, to_object, ancestor_type_key)
    if ancestor_id is None:
        raise api_error(
            422,
            "relation_ancestor_required",
            f"Related object must belong to an ancestor of type '{ancestor_type_key}'",
        )
    statement = select(ObjectRelation.id, ObjectRelation.to_object_id).where(
        ObjectRelation.relation_type_key == payload.relationTypeKey,
        ObjectRelation.from_object_id == str(payload.fromObjectId),
    )
    if exclude_relation_id is not None:
        statement = statement.where(ObjectRelation.id != exclude_relation_id)
    if exclude_relation_ids:
        statement = statement.where(ObjectRelation.id.not_in(exclude_relation_ids))
    existing_relations = dict(session.execute(statement).all())
    if not existing_relations:
        return
    existing_targets = session.scalars(
        select(RdmObject)
        .where(RdmObject.id.in_(set(existing_relations.values())))
        .order_by(RdmObject.id)
    )
    for existing in existing_targets:
        if (
            _matches_unique_condition(session, allowed, existing)
            and _ancestor_id(session, existing, ancestor_type_key) == ancestor_id
        ):
            raise api_error(
                409,
                "duplicate_relation_scope",
                "A related object already exists for this ancestor scope",
                {
                    "ancestorObjectTypeKey": ancestor_type_key,
                    "ancestorObjectId": ancestor_id,
                    # The record already in the scope, so a caller can point to it.
                    "conflictingObjectId": existing.id,
                    "conflictingRelationId": min(
                        key for key, target in existing_relations.items() if target == existing.id
                    ),
                },
            )


def _matches_unique_condition(session: Session, allowed, item: RdmObject) -> bool:
    condition = allowed.features.get("uniqueWhenToAttributeEquals")
    if not condition:
        return True
    values = current_attribute_values(session, item.id)
    return values.get(condition["attributeTypeKey"]) == condition["value"]


def validate_scoped_relations(
    session: Session, model: EngineModel, root: RdmObject, *, moved: bool
) -> None:
    """Re-check ancestor-scoped uniqueness for the relations a write to ``root`` can affect.

    A binding's ``uniqueToAncestorTypeKey`` scope is the nearest record of that type at or above
    the related record, and its condition reads the related record's own values. An attribute
    write can change only ``root``'s own conditions. A move (``moved``) also changes the scope of
    each record under ``root`` whose scope record is above ``root``; one with a scope record at or
    below ``root`` keeps it. So the check reads only relations of scoped bindings, into ``root``
    and, after a move, into the records under it that such a binding can reach, and a move under
    which no scoped binding can apply reads nothing below ``root``, however large its subtree.
    """
    scoped = [
        allowed
        for allowed in model.objectTypeRelations
        if allowed.features.get("uniqueToAncestorTypeKey")
    ]
    if not scoped:
        return
    targets = _scoped_subtree(session, model, root, scoped) if moved else {root.id}
    relation_types = sorted({allowed.relationTypeKey for allowed in scoped})
    relations = [
        relation
        for chunk in _chunked(targets)
        for relation in session.scalars(
            select(ObjectRelation).where(
                ObjectRelation.to_object_id.in_(chunk),
                ObjectRelation.relation_type_key.in_(relation_types),
            )
        )
    ]
    if not relations:
        return
    objects = {
        item.id: item
        for chunk in _chunked(
            {
                object_id
                for relation in relations
                for object_id in (relation.from_object_id, relation.to_object_id)
            }
        )
        for item in session.scalars(select(RdmObject).where(RdmObject.id.in_(chunk)))
    }
    for relation in relations:
        from_object = objects[relation.from_object_id]
        to_object = objects[relation.to_object_id]
        allowed = find_allowed_relation(
            model,
            relation.relation_type_key,
            from_object.object_type_key,
            to_object.object_type_key,
        )
        validate_unique_to_ancestor(
            session,
            allowed,
            RelationCreate(
                relationTypeKey=relation.relation_type_key,
                fromObjectId=relation.from_object_id,
                toObjectId=relation.to_object_id,
                attributes=relation.attributes,
            ),
            to_object,
            exclude_relation_id=relation.id,
        )


def _scoped_subtree(
    session: Session, model: EngineModel, root: RdmObject, scoped: list[ObjectTypeRelationDefinition]
) -> set[str]:
    """``root`` and the records under it whose scope in some scoped binding a move of ``root``
    changes: a binding's related type with no record of its scope type between it and ``root``.

    The walk goes down level by level through types that can hold a related type, and leaves a
    branch once every binding it could reach has its scope inside the branch.
    """
    # (related type, scope type) per binding, and for each type a walk can pass through, the
    # bindings whose related type it is or can hold.
    pairs = {
        (allowed.toObjectTypeKey, allowed.features["uniqueToAncestorTypeKey"]) for allowed in scoped
    }
    scope_types = {scope for _related, scope in pairs}
    reaching: dict[str, set[tuple[str, str]]] = {}
    for pair in pairs:
        for type_key in (pair[0], *ancestor_type_keys(model, pair[0])):
            reaching.setdefault(type_key, set()).add(pair)
    walkable = sorted(reaching)
    targets: set[str] = set()
    # Records to descend from, with the scope types met from ``root`` down to each.
    level: dict[str, frozenset[str]] = {}

    def visit(object_id: str, type_key: str, met: frozenset[str]) -> None:
        met = met | ({type_key} & scope_types)
        if any(related == type_key and scope not in met for related, scope in pairs):
            targets.add(object_id)
        if any(scope not in met for _related, scope in reaching.get(type_key, ())):
            level[object_id] = met

    visit(root.id, root.object_type_key, frozenset())
    seen = {root.id}
    while level:
        parents, level = level, {}
        for chunk in _chunked(parents):
            for child_id, type_key, parent_id in session.execute(
                select(RdmObject.id, RdmObject.object_type_key, RdmObject.parent_object_id).where(
                    RdmObject.parent_object_id.in_(chunk), RdmObject.object_type_key.in_(walkable)
                )
            ):
                if child_id not in seen:
                    seen.add(child_id)
                    visit(child_id, type_key, parents[parent_id])
    return targets


def _chunked(ids: set[str], size: int = 500) -> list[list[str]]:
    ordered = sorted(ids)
    return [ordered[index : index + size] for index in range(0, len(ordered), size)]


def _ancestor_id(session: Session, item: RdmObject, object_type_key: str) -> str | None:
    current = item
    visited: set[str] = set()
    while current.id not in visited:
        visited.add(current.id)
        if current.object_type_key == object_type_key:
            return current.id
        if current.parent_object_id is None:
            return None
        parent = session.scalar(select(RdmObject).where(RdmObject.id == current.parent_object_id))
        if parent is None:
            return None
        current = parent
    return None


def ensure_relation_deletable(allowed) -> None:
    if allowed.required:
        raise api_error(
            422,
            "required_relation",
            "A required relationship cannot be deleted independently",
        )


def load_relation(session: Session, relation_id: str) -> ObjectRelation:
    relation = session.scalar(select(ObjectRelation).where(ObjectRelation.id == relation_id))
    if not relation:
        raise api_error(404, "relation_not_found", f"Relation '{relation_id}' not found")
    return relation


def ensure_relation_mutable(
    model: EngineModel, relation_type_key: str, to_object_type_key: str
) -> None:
    """Reject relations the engine maintains itself (parent containment/hierarchy).

    A relation is engine-maintained when its relation type is wired as the parent-containment
    relation of the target (child) object type via ``behavior.parentRelationTypeKeys``; such edges
    are written atomically on parent changes and must not be mutated through the relations API.
    """
    definition = model.object_type(to_object_type_key)
    if definition and relation_type_key in definition.behavior.get("parentRelationTypeKeys", []):
        raise api_error(
            422,
            "immutable_relation",
            "Engine-maintained relation cannot be created, updated or deleted directly",
        )


def claim_relation_version(
    session: Session, relation: ObjectRelation, expected_version: int
) -> None:
    result = session.execute(
        update(ObjectRelation)
        .where(ObjectRelation.id == relation.id, ObjectRelation.version == expected_version)
        .values(version=expected_version + 1, updated_at=datetime.now(UTC))
        .execution_options(synchronize_session=False)
    )
    if result.rowcount != 1:
        raise api_error(409, "version_conflict", "Relation version has changed")
    session.refresh(relation)


def create_live_relation(
    session: Session, model: EngineModel, payload: RelationCreate, claim: SetClaim | None = None
) -> tuple[ObjectRelation, int | None]:
    """Create a relation in the live object store and commit the transaction.

    With ``claim``, the claimed end's set must still be at the version the caller read; the new
    version is returned with the relation.
    """
    from .objects import load_object

    from_object = load_object(session, str(payload.fromObjectId))
    to_object = load_object(session, str(payload.toObjectId))
    relation = create_relation_instance(
        session, model, payload, from_object=from_object, to_object=to_object
    )
    set_version = advance_set_versions(
        session,
        workspace_key=from_object.workspace_key,
        change_set_id=None,
        relation_type_key=payload.relationTypeKey,
        from_object_type_key=from_object.object_type_key,
        to_object_type_key=to_object.object_type_key,
        from_object_id=from_object.id,
        to_object_id=to_object.id,
        claim=claim,
    )
    session.commit()
    return relation, set_version


def update_live_relation(
    session: Session, model: EngineModel, relation_id: str, payload: Any
) -> ObjectRelation:
    """Update a live relation's attributes under optimistic concurrency.

    Endpoints and relation type are identity and cannot change through the update contract; only
    the relation attributes are mutable.  Engine-maintained containment edges are rejected.
    """
    from .objects import load_object
    from .workspaces import resolve_workspace

    relation = load_relation(session, relation_id)
    from_object = load_object(session, relation.from_object_id)
    to_object = load_object(session, relation.to_object_id)
    resolve_workspace(session, from_object.workspace_key, require_active=True)
    ensure_relation_mutable(model, relation.relation_type_key, to_object.object_type_key)
    allowed = find_allowed_relation(
        model,
        relation.relation_type_key,
        from_object.object_type_key,
        to_object.object_type_key,
    )
    attributes = validate_relation_attributes(model, allowed, payload.attributes)
    claim_relation_version(session, relation, payload.expectedVersion)
    relation.attributes = attributes
    record_audit_event(
        session,
        aggregate_type="relation",
        aggregate_id=relation.id,
        action="updated",
        version=relation.version,
        changes={"attributes": attributes},
        object_ids=[relation.from_object_id, relation.to_object_id],
    )
    increment_set_versions(
        session,
        workspace_key=from_object.workspace_key,
        change_set_id=None,
        relation_type_key=relation.relation_type_key,
        from_object_type_key=from_object.object_type_key,
        to_object_type_key=to_object.object_type_key,
        from_object_id=relation.from_object_id,
        to_object_id=relation.to_object_id,
    )
    session.commit()
    return relation


def delete_live_relation(
    session: Session,
    model: EngineModel,
    relation_id: str,
    expected_version: int,
    claim: SetClaim | None = None,
) -> None:
    """Delete a live relation that is not engine-maintained and not required; with ``claim``, only
    while the claimed end's set is at the version the caller read."""
    from .objects import load_object
    from .workspaces import resolve_workspace

    relation = load_relation(session, relation_id)
    from_object = load_object(session, relation.from_object_id)
    to_object = load_object(session, relation.to_object_id)
    resolve_workspace(session, from_object.workspace_key, require_active=True)
    ensure_relation_mutable(model, relation.relation_type_key, to_object.object_type_key)
    allowed = find_allowed_relation(
        model,
        relation.relation_type_key,
        from_object.object_type_key,
        to_object.object_type_key,
    )
    ensure_relation_deletable(allowed)
    claim_relation_version(session, relation, expected_version)
    record_audit_event(
        session,
        aggregate_type="relation",
        aggregate_id=relation.id,
        action="deleted",
        version=relation.version,
        changes={
            "relationTypeKey": relation.relation_type_key,
            "fromObjectId": relation.from_object_id,
            "toObjectId": relation.to_object_id,
        },
        object_ids=[relation.from_object_id, relation.to_object_id],
    )
    advance_set_versions(
        session,
        workspace_key=from_object.workspace_key,
        change_set_id=None,
        relation_type_key=relation.relation_type_key,
        from_object_type_key=from_object.object_type_key,
        to_object_type_key=to_object.object_type_key,
        from_object_id=relation.from_object_id,
        to_object_id=relation.to_object_id,
        claim=claim,
    )
    session.delete(relation)
    session.commit()


def build_relation_response(relation: ObjectRelation) -> RelationResponse:
    return RelationResponse(
        id=relation.id,
        relationTypeKey=relation.relation_type_key,
        fromObjectId=relation.from_object_id,
        toObjectId=relation.to_object_id,
        attributes=relation.attributes,
        version=relation.version,
        createdAt=relation.created_at,
        updatedAt=relation.updated_at,
    )
