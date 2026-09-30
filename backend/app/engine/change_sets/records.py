"""WP8 workspace lifecycle orchestration over ADR-024 persistence.

WP8 owns the workspace-scoped change set / validation / publish / withdrawal lifecycle on top of
the WP6 copy-on-write storage layout. Objects and relations are ordinary live records; optional
staged edits use the canonical routers with ``changeSetId``. Publishing merges authored changes into
live data and records an immutable publication (ADR-026/027/031).
"""

from collections.abc import Iterable
from typing import Any
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from ...errors import api_error
from ...models.database import (
    ChangeSet,
    ChangeSetObject,
    ChangeSetRelation,
    RdmObject,
)
from ..records import rules
from ..records.attributes import (
    validate_attributes,
    validate_deletable_attribute,
    validate_object_attribute_rules,
)
from ..records.audit import record_audit_event
from ..records.context import ChangeSetLookup
from ..records.deletion import (
    deletion_preview_changed,
    deletion_preview_token,
    require_deletion_preview,
    require_matching_deletion_preview,
)
from ..records.refusals import CHANGE_SET
from ..records.relation_set_versions import (
    SetClaim,
    advance_set_versions,
    increment_set_versions,
)
from ..records.rules import object_type_changed
from ..records.values import stored_json_value
from ..records.writes import ChangeSetWrites
from .access import change_set_model, load_change_set


def require_record_version(expected: int | None, actual: int, label: str) -> None:
    if expected is not None and expected != actual:
        raise api_error(409, "version_conflict", f"{label} version has changed")


def stored_attributes(
    model: Any, object_type_key: str, attributes: dict[str, Any], *, partial: bool
) -> dict[str, Any]:
    object_type = rules.object_type(model, object_type_key, CHANGE_SET)
    normalized = validate_attributes(
        model, object_type, attributes, partial=partial, apply_defaults=not partial
    )
    # Change set rows are JSON; store the same form that current-live capture copies from live rows.
    return {key: stored_json_value(value) for key, value in normalized.items()}


def validate_change_set_relation(
    model: Any,
    lookup: ChangeSetLookup,
    relation_type_key: str,
    from_id: str,
    to_id: str,
    attributes: dict[str, Any],
    *,
    exclude_id: str | None = None,
    exclude_ids: set[str] | None = None,
) -> dict[str, Any]:
    """Check one candidate relation against the relations at its own ends (S2b)."""
    endpoints = lookup.objects([from_id, to_id])
    source, target = endpoints.get(from_id), endpoints.get(to_id)
    if source is None or target is None:
        raise api_error(
            422, "relation_endpoint_missing", "Relation endpoints must exist in the change set"
        )
    excluded = frozenset({exclude_id, *(exclude_ids or set())} - {None})
    return rules.relation(
        lookup, model, relation_type_key, source, target, attributes, excluded=excluded
    )


def put_change_set_object(session: Session, change_set_id: str, payload: Any) -> ChangeSetObject:
    change_set = load_change_set(session, change_set_id, for_update=True)
    writes = ChangeSetWrites(session, change_set)
    model = change_set_model(session, change_set)
    rules.object_identity(model, payload.applicationKey, payload.objectTypeKey, CHANGE_SET)
    attributes = stored_attributes(
        model, payload.objectTypeKey, payload.attributes, partial=False
    )
    validate_object_attribute_rules(model.object_type(payload.objectTypeKey), attributes)
    lookup = ChangeSetLookup.of(session, change_set_id)
    if payload.parentObjectId is not None and lookup.object(str(payload.parentObjectId)) is None:
        raise api_error(422, "parent_wrong_scope", "Parent must exist in the change set")
    writes.claim(payload.expectedChangeSetVersion)
    object_id = str(payload.id) if payload.id else str(uuid4())
    if payload.expectedRecordVersion is not None and not _object_exists(
        session, lookup, change_set_id, object_id
    ):
        raise api_error(409, "version_conflict", "Object record does not exist")
    row = write_new_change_set_object(
        session,
        change_set,
        model,
        lookup,
        object_id=object_id,
        application_key=payload.applicationKey,
        object_type_key=payload.objectTypeKey,
        name=payload.name,
        parent_object_id=str(payload.parentObjectId) if payload.parentObjectId else None,
        attributes=attributes,
        initial_relations=[
            (item.relationTypeKey, item.direction, str(item.otherObjectId), item.attributes)
            for item in getattr(payload, "initialRelations", None) or ()
        ],
    )
    session.commit()
    return row


def _object_exists(
    session: Session, lookup: ChangeSetLookup, change_set_id: str, object_id: str
) -> bool:
    return bool(
        lookup.object(object_id) is not None
        or session.scalar(select(RdmObject.id).where(RdmObject.id == object_id))
        or session.scalar(
            select(ChangeSetObject.object_id).where(
                ChangeSetObject.change_set_id == change_set_id,
                ChangeSetObject.object_id == object_id,
            )
        )
    )


def write_new_change_set_object(
    session: Session,
    change_set: ChangeSet,
    model: Any,
    lookup: ChangeSetLookup,
    *,
    object_id: str,
    application_key: str,
    object_type_key: str,
    name: str,
    parent_object_id: str | None,
    attributes: dict[str, Any],
    initial_relations: list[tuple[str, str, str, dict[str, Any]]],
    audit_changes: dict[str, Any] | None = None,
) -> ChangeSetObject:
    """Write a new record into a change set with its initial relationships; the caller has
    normalized its attributes and claims and commits.

    ``initial_relations`` are ``(relationTypeKey, direction, otherObjectId, attributes)``.
    """
    if _object_exists(session, lookup, change_set.id, object_id):
        raise CHANGE_SET.object_exists(object_id)
    writes = ChangeSetWrites(session, change_set)
    row = writes.add_object(
        object_id=object_id,
        application_key=application_key,
        object_type_key=object_type_key,
        name=name,
        parent_object_id=parent_object_id,
        attributes=attributes,
    )
    rules.unique_values(lookup, model, row.object_id, attributes)
    place_record(session, change_set, model, row, lookup)
    identities = [(key, direction, other) for key, direction, other, _attrs in initial_relations]
    if len(identities) != len(set(identities)):
        raise api_error(422, "duplicate_initial_relation", "Initial relationships must not repeat")
    # The new row and each relation added before the next are flushed into the lookups.
    for relation_type_key, direction, other_id, relation_attributes in initial_relations:
        from_id = row.object_id if direction == "outgoing" else other_id
        to_id = other_id if direction == "outgoing" else row.object_id
        attrs = validate_change_set_relation(
            model, lookup, relation_type_key, from_id, to_id, relation_attributes
        )
        relation = writes.add_relation(relation_type_key, from_id, to_id, attrs)
        advance_relation_sets(session, change_set, lookup, relation)
    rules.required_initial_relations(
        model,
        row.object_type_key,
        (key for key, direction, _other, _attrs in initial_relations if direction == "incoming"),
    )
    record_audit_event(
        session,
        aggregate_type="change-set-object",
        aggregate_id=row.object_id,
        action="created",
        version=row.version,
        changes={"attributes": attributes, "changeSetId": change_set.id, **(audit_changes or {})},
        object_ids=[row.object_id],
    )
    return row


def update_change_set_object(
    session: Session,
    change_set_id: str,
    object_id: str,
    payload: Any,
    *,
    object_type_key: str | None = None,
) -> ChangeSetObject:
    """Edit a record in a change set. An edit never changes the type (ADR-034); a route naming
    another type than the record's is ``409 object_type_changed`` (D42)."""
    change_set = load_change_set(session, change_set_id, for_update=True)
    writes = ChangeSetWrites(session, change_set)
    model = change_set_model(session, change_set)
    lookup = ChangeSetLookup.of(session, change_set_id)
    writes.claim(payload.expectedChangeSetVersion)
    effective = lookup.object(object_id)
    if effective is not None and object_type_key and effective.object_type_key != object_type_key:
        raise object_type_changed(object_id, effective.object_type_key, object_type_key)
    row = writes.stored_object(object_id)
    if row is None:
        base = effective
        if base is None:
            raise api_error(404, "object_not_found", f"Object '{object_id}' not found in change set")
        row = writes.own_object(base, flush=True)
    require_record_version(payload.expectedRecordVersion, row.version, "Object record")
    if payload.name is not None:
        row.name = payload.name
    if "parentObjectId" in payload.model_fields_set:
        row.parent_object_id = str(payload.parentObjectId) if payload.parentObjectId else None
    if payload.attributes is not None:
        row.attributes = {
            **(row.attributes or {}),
            **stored_attributes(
                model, row.object_type_key, payload.attributes, partial=True
            ),
        }
    rules.effective_period(model.object_type(row.object_type_key), row.attributes or {})
    rules.unique_values(lookup, model, row.object_id, row.attributes or {})
    # The edited row is flushed into the lookups: each relation into it is checked against it.
    parent_keys = model.containment_relation_keys(row.object_type_key)
    for relation in lookup.relations([row.object_id], "incoming"):
        if relation.relation_type_key in parent_keys:
            continue
        validate_change_set_relation(
            model,
            lookup,
            relation.relation_type_key,
            relation.from_object_id,
            relation.to_object_id,
            dict(relation.attributes or {}),
            exclude_id=relation.relation_id,
        )
    row.version += 1
    row.is_deleted = False
    place_record(session, change_set, model, row, lookup)
    record_audit_event(
        session,
        aggregate_type="change-set-object",
        aggregate_id=row.object_id,
        action="updated",
        version=row.version,
        changes={"attributes": row.attributes or {}, "changeSetId": change_set.id},
        object_ids=[row.object_id],
    )
    session.commit()
    return row


def delete_change_set_object(
    session: Session,
    change_set_id: str,
    object_type_key: str,
    object_id: str,
    expected_change_set_version: int,
    expected_record_version: int,
    *,
    cascade: bool = False,
    deletion_preview: str | None = None,
) -> None:
    if cascade:
        require_deletion_preview(deletion_preview)

    change_set = load_change_set(session, change_set_id, for_update=True)
    writes = ChangeSetWrites(session, change_set)
    model = change_set_model(session, change_set)
    # The aggregate claim serializes all change set mutations before the hierarchy is re-read. A preview
    # response rolls this claim back; a confirmed delete retains it in the mutation transaction.
    writes.claim(expected_change_set_version,
        conflict_code=(
            "deletion_preview_changed" if cascade else "change_set_version_conflict"
        ),
        conflict_message=(
            "The object was modified by another session. Please retry."
            if cascade
            else "Change set version has changed"
        ),
    )
    lookup = ChangeSetLookup.of(session, change_set_id)
    root = lookup.object(object_id)
    if root is None or root.object_type_key != object_type_key:
        if cascade and deletion_preview is not None:
            raise deletion_preview_changed()
        if root is not None:
            raise object_type_changed(object_id, root.object_type_key, object_type_key)
        raise api_error(404, "object_not_found", f"Object '{object_id}' not found in change set")
    if cascade and deletion_preview is not None and expected_record_version != root.version:
        raise api_error(
            409,
            "deletion_preview_changed",
            "The object was modified by another session. Please retry.",
        )
    require_record_version(expected_record_version, root.version, "Object record")

    # The walk reads the planned subtree level by level: its children, and the records its required
    # owning relations reach. Its cost is the deleted subtree, not the change set.
    objects: dict[str, Any] = {object_id: root}
    reasons: dict[str, str] = {object_id: "root"}
    frontier = [object_id]
    while frontier:
        reached: list[str] = []
        for child in lookup.children(frontier):
            if child.object_id not in objects:
                objects[child.object_id] = child
                reasons[child.object_id] = "child"
                reached.append(child.object_id)
        outgoing = [
            relation
            for relation in lookup.relations(frontier, "outgoing")
            if relation.to_object_id not in objects
        ]
        targets = lookup.objects(relation.to_object_id for relation in outgoing)
        for relation in outgoing:
            if relation.to_object_id in objects:
                continue
            source, target = (
                objects.get(relation.from_object_id),
                targets.get(relation.to_object_id),
            )
            allowed = next(
                (
                    item
                    for item in model.objectTypeRelations
                    if source is not None
                    and target is not None
                    and item.relationTypeKey == relation.relation_type_key
                    and item.fromObjectTypeKey == source.object_type_key
                    and item.toObjectTypeKey == target.object_type_key
                ),
                None,
            )
            relation_type = model.relation_type(relation.relation_type_key)
            if (
                allowed is not None
                and relation_type is not None
                and relation_type.isOriented
                and allowed.required
                and allowed.cardinality in {"one-to-one", "one-to-many"}
            ):
                objects[target.object_id] = target
                reasons[target.object_id] = "required-ownership"
                reached.append(target.object_id)
        frontier = reached
    planned_ids = set(objects)
    incident = lookup.relations(planned_ids, "both")
    # Relations leaving the subtree name records outside it: the set versions need their types.
    objects.update(
        lookup.objects(
            end
            for relation in incident
            for end in (relation.from_object_id, relation.to_object_id)
            if end not in objects
        )
    )

    def is_parent_relation(relation) -> bool:
        target = objects.get(relation.to_object_id)
        object_type = model.object_type(target.object_type_key) if target is not None else None
        return bool(
            object_type
            and relation.relation_type_key
            in (object_type.behavior or {}).get("parentRelationTypeKeys", [])
        )

    has_non_parent_incident = any(not is_parent_relation(item) for item in incident)
    context = {
        "changeSetId": change_set_id,
        "objectTypeKey": object_type_key,
        "objectId": object_id,
        "modelReleaseId": change_set.model_release_id,
    }
    planned = [objects[key] for key in sorted(planned_ids)]
    object_identity = [(item.object_id, item.version, item.parent_object_id) for item in planned]
    relation_identity = [
        (
            item.relation_id,
            item.version,
            item.relation_type_key,
            item.from_object_id,
            item.to_object_id,
        )
        for item in incident
    ]
    if not cascade and (len(planned_ids) > 1 or has_non_parent_incident):
        dependants = [
            {
                "id": item.object_id,
                "name": item.name,
                "objectTypeKey": item.object_type_key,
                "applicationKey": item.application_key,
                "parentObjectId": item.parent_object_id,
                "reason": reasons[item.object_id],
            }
            for item in planned
            if item.object_id != object_id
        ]
        raise api_error(
            409,
            "object_has_dependants",
            "Object has dependant records or relationships; repeat with cascade=true",
            {
                "objectsToDelete": dependants,
                "objectsToRetire": dependants,
                "relationshipsToRemove": [
                    {"id": item.relation_id, "relationTypeKey": item.relation_type_key}
                    for item in incident
                ],
                "objectCount": len(planned_ids),
                "relationshipCount": len(incident),
                "retainedAssociationCount": sum(
                    1
                    for relation in incident
                    if relation.from_object_id not in planned_ids
                    or relation.to_object_id not in planned_ids
                ),
                "deletionPreviewToken": deletion_preview_token(
                    scope="change-set-deletion",
                    context=context,
                    objects=object_identity,
                    relations=relation_identity,
                ),
            },
        )
    if cascade:
        require_matching_deletion_preview(
            deletion_preview,
            scope="change-set-deletion",
            context=context,
            objects=object_identity,
            relations=relation_identity,
        )
    tombstone_change_set_records(session, change_set, objects, planned_ids, incident)
    session.commit()


def tombstone_change_set_records(
    session: Session,
    change_set: ChangeSet,
    objects: dict[str, Any],
    object_ids: Iterable[str],
    incident: Iterable[Any],
) -> None:
    """Delete records and their relationships in a change set; the caller claims and commits.

    ``objects`` holds each record and each end of an ``incident`` relationship as the change set
    holds it, since the relationship's sets advance under its ends' types.
    """
    writes = ChangeSetWrites(session, change_set)
    for deleted_id in object_ids:
        writes.remove_object(objects[deleted_id])
    for relation in incident:
        writes.remove_relation(relation)
        increment_set_versions(
            session,
            workspace_key=change_set.workspace_key,
            change_set_id=change_set.id,
            relation_type_key=relation.relation_type_key,
            from_object_type_key=objects[relation.from_object_id].object_type_key,
            to_object_type_key=objects[relation.to_object_id].object_type_key,
            from_object_id=relation.from_object_id,
            to_object_id=relation.to_object_id,
        )


def place_record(
    session: Session,
    change_set: ChangeSet,
    model: Any,
    row: ChangeSetObject,
    lookup: ChangeSetLookup,
    *,
    previous_type_key: str | None = None,
) -> None:
    """Maintain the typed containment edge with a change set object edit.

    The effective edge may come from the change set base; like a live update, an unchanged parent keeps
    that edge and its identity, and a changed parent tombstones it before adding the new one.
    """
    # The ancestor walk is one lookup per level; the row itself is read as edited.
    rules.parent(
        lookup,
        model,
        row.object_type_key,
        row.application_key,
        row.parent_object_id,
        object_id=row.object_id,
        moving=True,
    )
    parent = lookup.object(row.parent_object_id) if row.parent_object_id else None
    if row.parent_object_id and parent is None:
        raise api_error(422, "parent_wrong_scope", "Parent must exist in the change set")
    sync_containment_edge(
        session,
        change_set,
        model,
        lookup,
        child_id=row.object_id,
        child_type_key=row.object_type_key,
        parent=parent,
        previous_type_key=previous_type_key,
    )


def sync_containment_edge(
    session: Session,
    change_set: ChangeSet,
    model: Any,
    lookup: ChangeSetLookup,
    *,
    child_id: str,
    child_type_key: str,
    parent: Any | None,
    previous_type_key: str | None = None,
) -> None:
    """Make the child's one containment edge the relation the model allows from ``parent``.

    An edge from the same parent of the allowed relation type keeps its identity; any other is
    tombstoned before the allowed one is added. With ``previous_type_key`` (a type change, Base 0.8
    C1), edges of the child's former parent relation types are found and replaced too.
    """
    keys = model.containment_relation_keys(child_type_key)
    searched = keys | model.containment_relation_keys(previous_type_key)
    if not searched:
        return
    allowed = None
    if parent is not None:
        allowed = next(
            (
                binding
                for key in sorted(keys)
                if (binding := model.allowed_relation(key, parent.object_type_key, child_type_key))
            ),
            None,
        )
        if allowed is None:
            raise api_error(
                422, "invalid_parent_type", "Parent type is not permitted for this object type"
            )
    current = lookup.relations([child_id], "incoming", sorted(searched))
    if [(relation.from_object_id, relation.relation_type_key) for relation in current] == (
        [(parent.object_id, allowed.relationTypeKey)] if parent is not None else []
    ):
        return
    writes = ChangeSetWrites(session, change_set)
    for relation in current:
        writes.remove_relation(relation)
    if parent is not None:
        writes.add_relation(allowed.relationTypeKey, parent.object_id, child_id, {})


def advance_relation_sets(
    session: Session,
    change_set: ChangeSet,
    lookup: ChangeSetLookup,
    row: ChangeSetRelation,
    claim: SetClaim | None = None,
) -> int | None:
    objects = lookup.objects([row.from_object_id, row.to_object_id])
    from_obj = objects.get(row.from_object_id)
    to_obj = objects.get(row.to_object_id)
    if from_obj is None or to_obj is None:
        return None
    return advance_set_versions(
        session,
        workspace_key=change_set.workspace_key,
        change_set_id=change_set.id,
        relation_type_key=row.relation_type_key,
        from_object_type_key=from_obj.object_type_key,
        to_object_type_key=to_obj.object_type_key,
        from_object_id=row.from_object_id,
        to_object_id=row.to_object_id,
        claim=claim,
    )


def put_change_set_relation(
    session: Session, change_set_id: str, payload: Any, claim: SetClaim | None = None
) -> tuple[ChangeSetRelation, int | None]:
    """Stage a relation; with ``claim``, only while the claimed end's set in the change set is at
    the version the caller read. Returns the row and the claimed set's new version."""
    change_set = load_change_set(session, change_set_id, for_update=True)
    writes = ChangeSetWrites(session, change_set)
    model = change_set_model(session, change_set)
    lookup = ChangeSetLookup.of(session, change_set_id)
    relation_id = str(payload.id) if payload.id else str(uuid4())
    row = writes.stored_relation(relation_id)
    attributes = validate_change_set_relation(
        model,
        lookup,
        payload.relationTypeKey,
        str(payload.fromObjectId),
        str(payload.toObjectId),
        payload.attributes,
    )
    writes.claim(payload.expectedChangeSetVersion)
    if row is None:
        row = writes.add_relation(
            payload.relationTypeKey,
            str(payload.fromObjectId),
            str(payload.toObjectId),
            attributes,
            relation_id=relation_id,
        )
    else:
        require_record_version(payload.expectedRecordVersion, row.version, "Relation record")
        row.version += 1
        row.relation_type_key = payload.relationTypeKey
        row.from_object_id = str(payload.fromObjectId)
        row.to_object_id = str(payload.toObjectId)
        row.attributes = attributes
        row.is_deleted = False
    record_audit_event(
        session,
        aggregate_type="relation",
        aggregate_id=row.relation_id,
        action="created" if row.version == 1 else "updated",
        version=row.version,
        changes={"attributes": attributes, "changeSetId": change_set.id},
        object_ids=[row.from_object_id, row.to_object_id],
    )
    set_version = advance_relation_sets(
        session, change_set, lookup, row, claim
    )
    session.commit()
    return row, set_version


def update_change_set_relation(
    session: Session, change_set_id: str, relation_id: str, payload: Any
) -> ChangeSetRelation:
    change_set = load_change_set(session, change_set_id, for_update=True)
    writes = ChangeSetWrites(session, change_set)
    model = change_set_model(session, change_set)
    row = writes.stored_relation(relation_id)
    lookup = ChangeSetLookup.of(session, change_set_id)
    if row is None:
        base = lookup.relation(relation_id)
        if base is None:
            raise api_error(
                404, "relation_not_found", f"Relation '{relation_id}' not found in change set"
            )
        row = writes.own_relation(base, flush=True)
    require_record_version(payload.expectedRecordVersion, row.version, "Relation record")
    relation_type = payload.relationTypeKey or row.relation_type_key
    from_id = str(payload.fromObjectId) if payload.fromObjectId else row.from_object_id
    to_id = str(payload.toObjectId) if payload.toObjectId else row.to_object_id
    attrs = row.attributes or {}
    if payload.attributes is not None:
        attrs = payload.attributes
    attrs = validate_change_set_relation(
        model, lookup, relation_type, from_id, to_id, attrs, exclude_id=relation_id
    )
    writes.claim(payload.expectedChangeSetVersion)
    row.relation_type_key, row.from_object_id, row.to_object_id, row.attributes = (
        relation_type,
        from_id,
        to_id,
        attrs,
    )
    row.version += 1
    row.is_deleted = False
    record_audit_event(
        session,
        aggregate_type="relation",
        aggregate_id=row.relation_id,
        action="updated",
        version=row.version,
        changes={"attributes": attrs, "changeSetId": change_set.id},
        object_ids=[row.from_object_id, row.to_object_id],
    )
    advance_relation_sets(session, change_set, lookup, row)
    session.commit()
    return row


def delete_change_set_relation(
    session: Session,
    change_set_id: str,
    relation_id: str,
    expected_change_set_version: int,
    expected_record_version: int,
    claim: SetClaim | None = None,
) -> None:
    change_set = load_change_set(session, change_set_id, for_update=True)
    writes = ChangeSetWrites(session, change_set)
    model = change_set_model(session, change_set)
    row = writes.stored_relation(relation_id)
    lookup = ChangeSetLookup.of(session, change_set_id)
    if row is None:
        base = lookup.relation(relation_id)
        if base is None:
            raise api_error(
                404, "relation_not_found", f"Relation '{relation_id}' not found in change set"
            )
        row = writes.own_relation(base, flush=True)
    objects = lookup.objects([row.from_object_id, row.to_object_id])
    target = objects.get(row.to_object_id)
    if target is not None:
        rules.mutable_relation(
            model, row.relation_type_key, target.object_type_key, CHANGE_SET, deleting=True
        )
        allowed = model.allowed_relation(
            row.relation_type_key,
            objects.get(row.from_object_id).object_type_key,
            target.object_type_key,
        )
        if allowed is not None:
            rules.deletable_relation(allowed, CHANGE_SET)
    require_record_version(expected_record_version, row.version, "Relation record")
    writes.claim(expected_change_set_version)
    row.version += 1
    row.is_deleted = True
    advance_relation_sets(session, change_set, lookup, row, claim)
    session.commit()


def patch_change_set_attribute(
    session: Session,
    change_set_id: str,
    object_id: str,
    key: str,
    value: Any,
    expected_change_set_version: int,
    expected_record_version: int,
) -> ChangeSetObject:
    change_set = load_change_set(session, change_set_id, for_update=True)
    writes = ChangeSetWrites(session, change_set)
    lookup = ChangeSetLookup.of(session, change_set_id)
    base = lookup.object(object_id)
    if base is None:
        raise api_error(404, "object_not_found", f"Object '{object_id}' not found in change set")
    row = writes.stored_object(object_id)
    if row is None:
        row = writes.own_object(base, flush=True)
    require_record_version(expected_record_version, row.version, "Object record")
    model = change_set_model(session, change_set)
    normalized = stored_attributes(
        model, row.object_type_key, {key: value}, partial=True
    )
    rules.effective_period(
        model.object_type(row.object_type_key), {**(row.attributes or {}), **normalized}
    )
    writes.claim(expected_change_set_version)
    row.attributes = {**(row.attributes or {}), **normalized}
    rules.unique_values(lookup, model, row.object_id, row.attributes)
    row.version += 1
    record_audit_event(
        session,
        aggregate_type="change-set-object",
        aggregate_id=row.object_id,
        action="updated",
        version=row.version,
        changes={"attributes": {key: value}, "changeSetId": change_set.id},
        object_ids=[row.object_id],
    )
    session.commit()
    return row


def delete_change_set_attribute(
    session: Session,
    change_set_id: str,
    object_id: str,
    key: str,
    expected_change_set_version: int,
    expected_record_version: int,
) -> ChangeSetObject:
    change_set = load_change_set(session, change_set_id, for_update=True)
    writes = ChangeSetWrites(session, change_set)
    lookup = ChangeSetLookup.of(session, change_set_id)
    base = lookup.object(object_id)
    if base is None:
        raise api_error(404, "object_not_found", f"Object '{object_id}' not found in change set")
    row = writes.stored_object(object_id)
    if row is None:
        row = writes.own_object(base, flush=True)
    require_record_version(expected_record_version, row.version, "Object record")
    model = change_set_model(session, change_set)
    object_type = model.object_type(row.object_type_key)
    binding = (
        next((item for item in object_type.attributes if item.attributeTypeKey == key), None)
        if object_type
        else None
    )
    if binding is None:
        raise api_error(
            422,
            "unknown_attributes",
            f"Attribute '{key}' is not defined on object type '{row.object_type_key}'",
        )
    validate_deletable_attribute(object_type, key)
    remaining = {
        item_key: item_value
        for item_key, item_value in (row.attributes or {}).items()
        if item_key != key
    }
    validate_object_attribute_rules(object_type, remaining)
    writes.claim(expected_change_set_version)
    row.attributes = remaining
    row.version += 1
    record_audit_event(
        session,
        aggregate_type="change-set-object",
        aggregate_id=row.object_id,
        action="updated",
        version=row.version,
        changes={"attributes": {key: None}, "changeSetId": change_set.id},
        object_ids=[row.object_id],
    )
    session.commit()
    return row
