from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from ...errors import api_error
from ...models.commands import RelationCreate
from ...models.database import ObjectRelation, RdmObject
from ...models.schema import EngineModel, ObjectTypeRelationDefinition
from ..model.traversal import ancestor_type_keys
from ..workspaces.catalogue import resolve_workspace
from . import rules
from .audit import record_audit_event
from .context import LiveLookup, load_object
from .refusals import LIVE
from .relation_set_versions import SetClaim, advance_set_versions, increment_set_versions
from .writes import LiveWrites


def create_relation_instance(
    writes: LiveWrites,
    model: EngineModel,
    payload: RelationCreate,
    *,
    from_object: RdmObject,
    to_object: RdmObject,
) -> ObjectRelation:
    """Create a relation between two live records of the unit's workspace.

    Engine-maintained containment edges (the parent relation of an object type) are rejected here;
    they are written atomically when the owning object's parent changes.
    """
    session = writes.session
    attributes = rules.relation(
        LiveLookup.of(session, writes.workspace_key),
        model,
        payload.relationTypeKey,
        from_object,
        to_object,
        payload.attributes,
    )
    relation = writes.add_relation(
        payload.relationTypeKey, from_object.id, to_object.id, attributes
    )
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


def validate_scoped_relations(lookup: Any, model: EngineModel, root: Any, *, moved: bool) -> None:
    """Re-check ancestor-scoped uniqueness for the relations a write to ``root`` can affect,
    reading the live records through ``lookup``.

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
    targets = _scoped_subtree(lookup, model, root, scoped) if moved else {root.object_id}
    relation_types = sorted({allowed.relationTypeKey for allowed in scoped})
    relations = lookup.relations(sorted(targets), "incoming", relation_types)
    if not relations:
        return
    objects = lookup.objects(
        object_id
        for relation in relations
        for object_id in (relation.from_object_id, relation.to_object_id)
    )
    for relation in relations:
        from_object = objects[relation.from_object_id]
        to_object = objects[relation.to_object_id]
        binding = rules.relation_binding(
            model,
            relation.relation_type_key,
            from_object.object_type_key,
            to_object.object_type_key,
            LIVE,
        )
        rules.relation_scope(
            lookup, binding, relation.from_object_id, to_object, frozenset({relation.relation_id})
        )


def _scoped_subtree(
    lookup: Any, model: EngineModel, root: Any, scoped: list[ObjectTypeRelationDefinition]
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

    visit(root.object_id, root.object_type_key, frozenset())
    seen = {root.object_id}
    while level:
        parents, level = level, {}
        for child in lookup.children(sorted(parents), walkable):
            if child.object_id not in seen:
                seen.add(child.object_id)
                visit(child.object_id, child.object_type_key, parents[child.parent_object_id])
    return targets


def load_relation(session: Session, relation_id: str) -> ObjectRelation:
    relation = session.scalar(select(ObjectRelation).where(ObjectRelation.id == relation_id))
    if not relation:
        raise api_error(404, "relation_not_found", f"Relation '{relation_id}' not found")
    return relation


def _endpoint(session: Session, object_id: str) -> RdmObject:
    """A relation's end, which must exist: ``422 relation_endpoint_missing`` as in a change set (an
    E-D4 row settled in H4c, deviation 11)."""
    item = session.scalar(select(RdmObject).where(RdmObject.id == object_id))
    if item is None:
        raise rules.relation_endpoint_missing(object_id)
    return item


def create_live_relation(
    session: Session, model: EngineModel, payload: RelationCreate, claim: SetClaim | None = None
) -> tuple[ObjectRelation, int | None]:
    """Create a relation in the live object store and commit the transaction.

    With ``claim``, the claimed end's set must still be at the version the caller read; the new
    version is returned with the relation.
    """
    from_object = _endpoint(session, str(payload.fromObjectId))
    to_object = _endpoint(session, str(payload.toObjectId))
    if from_object.workspace_key != to_object.workspace_key:
        raise api_error(422, "relation_wrong_scope", "Related objects must share a workspace")
    resolve_workspace(session, from_object.workspace_key, require_active=True)
    writes = LiveWrites(session, from_object.workspace_key)
    relation = create_relation_instance(
        writes, model, payload, from_object=from_object, to_object=to_object
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
    relation = load_relation(session, relation_id)
    from_object = load_object(session, relation.from_object_id)
    to_object = load_object(session, relation.to_object_id)
    resolve_workspace(session, from_object.workspace_key, require_active=True)
    writes = LiveWrites(session, from_object.workspace_key)
    rules.mutable_relation(model, relation.relation_type_key, to_object.object_type_key, LIVE)
    binding = rules.relation_binding(
        model,
        relation.relation_type_key,
        from_object.object_type_key,
        to_object.object_type_key,
        LIVE,
    )
    attributes = rules.relation_attributes(model, binding, payload.attributes)
    writes.claim_relation(relation, payload.expectedVersion)
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
    relation = load_relation(session, relation_id)
    from_object = load_object(session, relation.from_object_id)
    to_object = load_object(session, relation.to_object_id)
    resolve_workspace(session, from_object.workspace_key, require_active=True)
    writes = LiveWrites(session, from_object.workspace_key)
    rules.mutable_relation(
        model, relation.relation_type_key, to_object.object_type_key, LIVE, deleting=True
    )
    binding = rules.relation_binding(
        model,
        relation.relation_type_key,
        from_object.object_type_key,
        to_object.object_type_key,
        LIVE,
    )
    rules.deletable_relation(binding, LIVE)
    writes.claim_relation(relation, expected_version)
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
    writes.remove_relation(relation)
    session.commit()
