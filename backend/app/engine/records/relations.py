from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from ...errors import api_error
from ...models.commands import RelationCreate
from ...models.database import ObjectRelation, RdmObject
from ...models.schema import EngineModel, ObjectTypeRelationDefinition
from ..model.traversal import ancestor_type_keys
from ..reads.mapping_projection import context_projection
from ..reads.relation_grid import record_ids_selector
from ..workspaces.catalogue import resolve_workspace
from . import rules
from .batch_lookup import LiveBatchLookup
from .bulk import write_live
from .context import load_object
from .refusals import LIVE
from .relation_batch import RelationValues, decide_relation_values
from .relation_grid_change import GridChange, GridChangeResult, decide_grid_change, plan_grid_change
from .relation_set_versions import SetClaim
from .relation_writes import decide_relation_create, decide_relation_delete, decide_relation_update
from .writes import LiveWrites


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
        raise api_error(404, "RELATION_NOT_FOUND", f"Relation '{relation_id}' not found")
    return relation


def _endpoint(session: Session, object_id: str) -> RdmObject:
    """A relation's end, which must exist: ``422 relation_endpoint_missing`` as in a change set (an
    E-D4 row settled in H4c, deviation 11)."""
    item = session.scalar(select(RdmObject).where(RdmObject.id == object_id))
    if item is None:
        raise rules.relation_endpoint_missing(object_id)
    return item


def _live_relation_lookup(
    session: Session, from_object: RdmObject, to_object: RdmObject
) -> tuple[LiveWrites, LiveBatchLookup]:
    """The workspace lock and a batch lookup for a single relation write (a batch of one)."""
    if from_object.workspace_key != to_object.workspace_key:
        raise api_error(422, "RELATION_WRONG_SCOPE", "Related objects must share a workspace")
    resolve_workspace(session, from_object.workspace_key, require_active=True)
    writes = LiveWrites(session, from_object.workspace_key)
    return writes, LiveBatchLookup.of(session, from_object.workspace_key)


def create_live_relation(
    session: Session, model: EngineModel, payload: RelationCreate, claim: SetClaim | None = None
) -> tuple[ObjectRelation, int | None]:
    """Create a relation in the live object store and commit the transaction.

    With ``claim``, the claimed end's set must still be at the version the caller read; the new
    version is returned with the relation. Engine-maintained containment edges (the parent
    relation of an object type) are refused; they are written with the owning object's parent.
    """
    from_object = _endpoint(session, str(payload.fromObjectId))
    to_object = _endpoint(session, str(payload.toObjectId))
    writes, lookup = _live_relation_lookup(session, from_object, to_object)
    with lookup.deciding():
        relation = decide_relation_create(
            lookup,
            model,
            payload.relationTypeKey,
            from_object,
            to_object,
            payload.attributes,
            claim,
        )
    write_live(writes, model, lookup.changes())
    session.commit()
    return load_relation(session, relation.relation_id), (
        claim.expected + 1 if claim is not None else None
    )


def _claimed_relation(
    session: Session, relation_id: str
) -> tuple[LiveWrites, LiveBatchLookup, ObjectRelation]:
    relation = load_relation(session, relation_id)
    writes, lookup = _live_relation_lookup(
        session,
        load_object(session, relation.from_object_id),
        load_object(session, relation.to_object_id),
    )
    # Read again under the workspace lock: a write committed meanwhile is the one to claim against.
    session.refresh(relation)
    return writes, lookup, relation


def update_live_relation(
    session: Session, model: EngineModel, relation_id: str, payload: Any
) -> ObjectRelation:
    """Update a live relation's attributes under optimistic concurrency.

    Endpoints and relation type are identity and cannot change through the update contract; only
    the relation attributes are mutable.  Engine-maintained containment edges are rejected.
    """
    writes, lookup, relation = _claimed_relation(session, relation_id)
    with lookup.deciding():
        decide_relation_update(lookup, model, relation, payload.expectedVersion, payload.attributes)
    write_live(writes, model, lookup.changes())
    session.commit()
    return load_relation(session, relation_id)


def update_live_relations(
    session: Session, model: EngineModel, workspace_key: str, items: list[RelationValues]
) -> list[ObjectRelation]:
    """Set values on many live relationships of one workspace as one write, in the order of
    ``items``; any item refused refuses all of them (``RELATION_BATCH_REFUSED``)."""
    resolve_workspace(session, workspace_key, require_active=True)
    writes = LiveWrites(session, workspace_key)
    lookup = LiveBatchLookup.of(session, workspace_key)
    decide_relation_values(lookup, model, items)
    write_live(writes, model, lookup.changes())
    session.commit()
    rows = {
        row.id: row
        for row in session.scalars(
            select(ObjectRelation).where(ObjectRelation.id.in_([item.relation_id for item in items]))
        )
    }
    return [rows[item.relation_id] for item in items]


def change_live_grid(
    session: Session,
    model: EngineModel,
    workspace_key: str,
    change: GridChange,
    *,
    dry_run: bool,
    max_items: int,
) -> GridChangeResult:
    """One value set on the live relationships of a grid's selection as one write, or on a dry
    run only counted and decided (``RELATION_BATCH_REFUSED`` items are then the answer's
    ``refused``). The write holds the workspace lock from before the selection is read."""
    resolve_workspace(session, workspace_key, require_active=not dry_run)
    writes = None if dry_run else LiveWrites(session, workspace_key)
    objects, relations = context_projection(session, workspace_key, None, None)
    plan = plan_grid_change(
        session,
        model,
        change,
        objects,
        relations,
        live=True,
        record_ids=record_ids_selector(
            session, model, workspace_key=workspace_key, change_set_id=None, publication_id=None
        ),
        max_items=max_items,
        collect=True,
    )
    lookup = LiveBatchLookup.of(session, workspace_key)
    refused = decide_grid_change(lookup, model, plan, collect=dry_run)
    if writes is not None:
        write_live(writes, model, lookup.changes())
        session.commit()
    return GridChangeResult(plan, refused)


def delete_live_relation(
    session: Session,
    model: EngineModel,
    relation_id: str,
    expected_version: int,
    claim: SetClaim | None = None,
) -> None:
    """Delete a live relation that is not engine-maintained and not required; with ``claim``, only
    while the claimed end's set is at the version the caller read."""
    writes, lookup, relation = _claimed_relation(session, relation_id)
    with lookup.deciding():
        decide_relation_delete(lookup, model, relation, expected_version, claim)
    write_live(writes, model, lookup.changes())
    session.commit()
