"""WP8 workspace lifecycle orchestration over ADR-024 persistence.

WP8 owns the workspace-scoped change set / validation / publish / withdrawal lifecycle on top of
the WP6 copy-on-write storage layout. Objects and relations are ordinary live records; optional
staged edits use the canonical routers with ``changeSetId``. Publishing merges authored changes into
live data and records an immutable publication (ADR-026/027/031).
"""

from collections.abc import Iterable
from typing import Any
from uuid import uuid4

from sqlalchemy.orm import Session

from ...errors import api_error
from ...models.database import (
    ChangeSet,
    ChangeSetObject,
    ChangeSetRelation,
)
from ..reads.snapshot_reads import change_set_context, find_relation
from ..records import rules
from ..records.attributes import (
    validate_attributes,
    validate_deletable_attribute,
    validate_object_attribute_rules,
)
from ..records.audit import AuditEntry, record_audit_event
from ..records.batch_lookup import ChangeSetBatchLookup, Record, Relation
from ..records.bulk import write_change_set
from ..records.context import ChangeSetLookup
from ..records.deletion import (
    ChangeSetScope,
    Deletion,
    delete_records,
    deletion_preview_changed,
    require_deletion_preview,
)
from ..records.refusals import CHANGE_SET
from ..records.relation_set_versions import (
    SetClaim,
    advance_set_versions,
    increment_set_versions,
)
from ..records.relation_writes import (
    decide_relation_create,
    decide_relation_delete,
    decide_relation_update,
)
from ..records.rules import object_type_changed
from ..records.values import stored_json_value
from ..records.writes import ChangeSetWrites
from .access import change_set_model, load_change_set


def require_record_version(expected: int | None, actual: int, label: str) -> None:
    if expected is not None and expected != actual:
        raise api_error(
            409, "VERSION_CONFLICT", f"{label} version has changed", {"currentVersion": actual}
        )


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
        raise rules.relation_endpoint_missing(from_id if source is None else to_id)
    excluded = frozenset({exclude_id, *(exclude_ids or set())} - {None})
    return rules.relation(
        lookup, model, relation_type_key, source, target, attributes, excluded=excluded
    )


def put_change_set_object(session: Session, change_set_id: str, payload: Any) -> ChangeSetObject:
    row = apply_change_set_object_create(session, change_set_id, payload)
    session.commit()
    return row


def apply_change_set_object_create(
    session: Session, change_set_id: str, payload: Any
) -> ChangeSetObject:
    """Write a new record into a change set under its claim, as a batch of one; the caller
    commits."""
    change_set = load_change_set(session, change_set_id, for_update=True)
    writes = ChangeSetWrites(session, change_set)
    model = change_set_model(session, change_set)
    lookup = ChangeSetBatchLookup.of(session, change_set_id)
    with lookup.deciding():
        record = decide_change_set_object_create(lookup, writes, model, payload)
    return write_change_set(writes, lookup.changes())[record.object_id]


def decide_change_set_object_create(
    lookup: ChangeSetBatchLookup, writes: ChangeSetWrites, model: Any, payload: Any
) -> Record:
    """Check a new change set record against the rules under the change set's claim and lay it
    over ``lookup``; nothing is written (0.9.0-alpha.1 PG3b)."""
    rules.object_identity(model, payload.applicationKey, payload.objectTypeKey, CHANGE_SET)
    attributes = stored_attributes(
        model, payload.objectTypeKey, payload.attributes, partial=False
    )
    validate_object_attribute_rules(model.object_type(payload.objectTypeKey), attributes)
    if payload.parentObjectId is not None and lookup.object(str(payload.parentObjectId)) is None:
        raise api_error(422, "PARENT_WRONG_SCOPE", "Parent must exist in the change set")
    writes.claim(payload.expectedChangeSetVersion)
    object_id = str(payload.id) if payload.id else None
    if payload.expectedRecordVersion is not None and not (
        object_id is not None and lookup.id_taken(object_id)
    ):
        raise api_error(409, "VERSION_CONFLICT", "Object record does not exist")
    return decide_new_change_set_object(
        lookup,
        model,
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


def write_new_change_set_object(
    session: Session,
    change_set: ChangeSet,
    model: Any,
    lookup: ChangeSetLookup,
    *,
    object_id: str | None,
    application_key: str,
    object_type_key: str,
    name: str,
    parent_object_id: str | None,
    attributes: dict[str, Any],
    initial_relations: list[tuple[str, str, str, dict[str, Any]]],
    audit_changes: dict[str, Any] | None = None,
) -> ChangeSetObject:
    """Write a new record into a change set with its initial relationships, as a batch of one;
    the caller has normalized its attributes and claims and commits. See
    ``decide_new_change_set_object``."""
    batch = ChangeSetBatchLookup(lookup)
    with batch.deciding():
        record = decide_new_change_set_object(
            batch,
            model,
            object_id=object_id,
            application_key=application_key,
            object_type_key=object_type_key,
            name=name,
            parent_object_id=parent_object_id,
            attributes=attributes,
            initial_relations=initial_relations,
            audit_changes=audit_changes,
        )
    rows = write_change_set(ChangeSetWrites(session, change_set), batch.changes())
    return rows[record.object_id]


def decide_new_change_set_object(
    lookup: ChangeSetBatchLookup,
    model: Any,
    *,
    object_id: str | None,
    application_key: str,
    object_type_key: str,
    name: str,
    parent_object_id: str | None,
    attributes: dict[str, Any],
    initial_relations: list[tuple[str, str, str, dict[str, Any]]],
    audit_changes: dict[str, Any] | None = None,
) -> Record:
    """Lay a new change set record over ``lookup`` with its containment and initial
    relationships, checked by the rules; its attributes are normalized.

    ``object_id`` is the ID the caller gives, refused when taken; without one a new ID is drawn.
    ``initial_relations`` are ``(relationTypeKey, direction, otherObjectId, attributes)``.
    """
    if object_id is not None and lookup.id_taken(object_id):
        raise CHANGE_SET.object_exists(object_id, lookup.other_workspace(object_id))
    record = Record(
        object_id=object_id or str(uuid4()),
        application_key=application_key,
        object_type_key=object_type_key,
        parent_object_id=parent_object_id,
        name=name,
        version=1,
        attributes=dict(attributes),
    )
    lookup.lay(record, created=True)
    rules.unique_values(lookup, model, record.object_id, attributes)
    _place(lookup, model, record)
    rules.distinct_initial_relations(
        [(key, direction, other) for key, direction, other, _attrs in initial_relations]
    )
    # The new record and each relation added before the next count for the next one's checks.
    for relation_type_key, direction, other_id, relation_attributes in initial_relations:
        from_id = record.object_id if direction == "outgoing" else other_id
        to_id = other_id if direction == "outgoing" else record.object_id
        attrs = validate_change_set_relation(
            model, lookup, relation_type_key, from_id, to_id, relation_attributes
        )
        lookup.add_relation(Relation(str(uuid4()), relation_type_key, from_id, to_id, attrs))
        _advance_sets(lookup, relation_type_key, from_id, to_id)
    rules.required_initial_relations(
        model,
        record.object_type_key,
        (key for key, direction, _other, _attrs in initial_relations if direction == "incoming"),
    )
    lookup.audit(
        AuditEntry(
            "change-set-object",
            record.object_id,
            "created",
            record.version,
            {
                "attributes": attributes,
                "changeSetId": lookup.change_set_id,
                **(audit_changes or {}),
            },
            (record.object_id,),
        )
    )
    return record


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
    row = apply_change_set_object_update(
        session, change_set_id, object_id, payload, object_type_key=object_type_key
    )
    session.commit()
    return row


def apply_change_set_object_update(
    session: Session,
    change_set_id: str,
    object_id: str,
    payload: Any,
    *,
    object_type_key: str | None = None,
) -> ChangeSetObject:
    """Edit a record in a change set as ``update_change_set_object`` does, as a batch of one;
    the caller commits."""
    change_set = load_change_set(session, change_set_id, for_update=True)
    writes = ChangeSetWrites(session, change_set)
    model = change_set_model(session, change_set)
    lookup = ChangeSetBatchLookup.of(session, change_set_id)
    with lookup.deciding():
        record = decide_change_set_object_update(
            lookup, writes, model, object_id, payload, object_type_key=object_type_key
        )
    return write_change_set(writes, lookup.changes())[record.object_id]


def decide_change_set_object_update(
    lookup: ChangeSetBatchLookup,
    writes: ChangeSetWrites,
    model: Any,
    object_id: str,
    payload: Any,
    *,
    object_type_key: str | None = None,
    audit_changes: dict[str, Any] | None = None,
) -> Record:
    """Check an edit of a change set record under the change set's claim and lay the result over
    ``lookup``; nothing is written (0.9.0-alpha.1 PG3b). ``audit_changes`` adds to the audit
    entry. A record the change set deleted is edited back from its tombstone, as before."""
    writes.claim(payload.expectedChangeSetVersion)
    current = lookup.object(object_id)
    if current is not None and object_type_key and current.object_type_key != object_type_key:
        raise object_type_changed(object_id, current.object_type_key, object_type_key)
    if current is None:
        current = lookup.tombstone(object_id)
    if current is None:
        raise api_error(404, "OBJECT_NOT_FOUND", f"Object '{object_id}' not found in change set")
    require_record_version(payload.expectedRecordVersion, current.version, "Object record")
    record = Record(
        object_id=current.object_id,
        application_key=current.application_key,
        object_type_key=current.object_type_key,
        parent_object_id=current.parent_object_id,
        name=current.name,
        version=current.version + 1,
        attributes=dict(current.attributes or {}),
    )
    if payload.name is not None:
        record.name = payload.name
    if "parentObjectId" in payload.model_fields_set:
        record.parent_object_id = str(payload.parentObjectId) if payload.parentObjectId else None
    if payload.attributes is not None:
        record.attributes = {
            **record.attributes,
            **stored_attributes(model, record.object_type_key, payload.attributes, partial=True),
        }
    rules.effective_period(model.object_type(record.object_type_key), record.attributes)
    # The edited record is laid over the lookup: each relation into it is checked against it.
    lookup.lay(record)
    rules.unique_values(lookup, model, record.object_id, record.attributes)
    parent_keys = model.containment_relation_keys(record.object_type_key)
    for relation in lookup.relations([record.object_id], "incoming"):
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
    _place(lookup, model, record)
    lookup.audit(
        AuditEntry(
            "change-set-object",
            record.object_id,
            "updated",
            record.version,
            {
                "attributes": record.attributes,
                "changeSetId": lookup.change_set_id,
                **(audit_changes or {}),
            },
            (record.object_id,),
        )
    )
    return record


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
    apply_change_set_object_delete(
        session,
        change_set_id,
        object_type_key,
        object_id,
        expected_change_set_version,
        expected_record_version,
        cascade=cascade,
        deletion_preview=deletion_preview,
    )
    session.commit()


def apply_change_set_object_delete(
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
    """Delete a record in a change set as ``delete_change_set_object`` does; the caller commits."""
    if cascade:
        require_deletion_preview(deletion_preview)

    change_set = load_change_set(session, change_set_id, for_update=True)
    writes = ChangeSetWrites(session, change_set)
    model = change_set_model(session, change_set)
    # The aggregate claim serializes all change set mutations before the hierarchy is re-read. A preview
    # response rolls this claim back; a confirmed delete retains it in the mutation transaction.
    writes.claim(expected_change_set_version,
        conflict_code=(
            "DELETION_PREVIEW_CHANGED" if cascade else "CHANGE_SET_VERSION_CONFLICT"
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
        raise api_error(404, "OBJECT_NOT_FOUND", f"Object '{object_id}' not found in change set")
    if cascade and deletion_preview is not None and expected_record_version != root.version:
        raise deletion_preview_changed()
    require_record_version(expected_record_version, root.version, "Object record")
    # A run of one through the deletion path every delete shares (0.9 K2b, D123).
    (result,) = delete_records(
        ChangeSetScope(session, model, change_set),
        [Deletion(0, object_id, object_type_key, cascade, deletion_preview)],
        single=True,
    )
    if result.error is not None:
        raise result.error


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
    parent = placed_parent(lookup, model, row)
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


def placed_parent(lookup: Any, model: Any, row: Any) -> Any | None:
    """The parent a change set record names, checked as a move: allowed for its type, in the
    change set, and not at or under the record."""
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
        raise api_error(422, "PARENT_WRONG_SCOPE", "Parent must exist in the change set")
    return parent


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
    change = containment_change(
        model,
        lookup,
        child_id=child_id,
        child_type_key=child_type_key,
        parent=parent,
        previous_type_key=previous_type_key,
    )
    if change is None:
        return
    removed, added = change
    writes = ChangeSetWrites(session, change_set)
    for relation in removed:
        writes.remove_relation(relation)
    if added is not None:
        writes.add_relation(added, parent.object_id, child_id, {})


def containment_change(
    model: Any,
    lookup: Any,
    *,
    child_id: str,
    child_type_key: str,
    parent: Any | None,
    previous_type_key: str | None = None,
) -> tuple[list[Any], str | None] | None:
    """The containment edges ``sync_containment_edge`` removes and the relation type of the one it
    adds from ``parent``; ``None`` when the child's edge stays as it is."""
    keys = model.containment_relation_keys(child_type_key)
    searched = keys | model.containment_relation_keys(previous_type_key)
    if not searched:
        return None
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
                422, "INVALID_PARENT_TYPE", "Parent type is not permitted for this object type"
            )
    current = lookup.relations([child_id], "incoming", sorted(searched))
    if [(relation.from_object_id, relation.relation_type_key) for relation in current] == (
        [(parent.object_id, allowed.relationTypeKey)] if parent is not None else []
    ):
        return None
    return current, allowed.relationTypeKey if allowed is not None else None


def _place(lookup: ChangeSetBatchLookup, model: Any, record: Record) -> None:
    """``place_record`` for a decided record: its containment edge laid over the lookup."""
    parent = placed_parent(lookup, model, record)
    change = containment_change(
        model,
        lookup,
        child_id=record.object_id,
        child_type_key=record.object_type_key,
        parent=parent,
    )
    if change is None:
        return
    removed, added = change
    for relation in removed:
        lookup.remove_relation(relation)
    if added is not None:
        lookup.add_relation(
            Relation(str(uuid4()), added, parent.object_id, record.object_id, {})
        )


def _advance_sets(
    lookup: ChangeSetBatchLookup, relation_type_key: str, from_id: str, to_id: str
) -> None:
    """``advance_relation_sets`` for a decided relation."""
    ends = lookup.objects([from_id, to_id])
    if from_id in ends and to_id in ends:
        lookup.advance_sets(
            relation_type_key,
            ends[from_id].object_type_key,
            ends[to_id].object_type_key,
            from_id,
            to_id,
        )


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


def _change_set_relation_lookup(
    session: Session, change_set_id: str
) -> tuple[ChangeSet, ChangeSetWrites, Any, ChangeSetBatchLookup]:
    """The change set's row lock, its model and a batch lookup for a single relation write."""
    change_set = load_change_set(session, change_set_id, for_update=True)
    writes = ChangeSetWrites(session, change_set)
    model = change_set_model(session, change_set)
    return change_set, writes, model, ChangeSetBatchLookup.of(session, change_set_id)


def _stored_change_set_relation(session: Session, change_set_id: str, relation_id: str) -> Any:
    row = find_relation(session, change_set_context(session, change_set_id), relation_id)
    if row is None:
        raise api_error(
            404, "RELATION_NOT_FOUND", f"Relation '{relation_id}' not found in change set"
        )
    return row


def _written_relation(writes: ChangeSetWrites, relation_id: str) -> ChangeSetRelation:
    writes.session.flush()
    row = writes.stored_relation(relation_id)
    assert row is not None
    return row


def put_change_set_relation(
    session: Session, change_set_id: str, payload: Any, claim: SetClaim | None = None
) -> tuple[ChangeSetRelation, int | None]:
    """Stage a new relation; with ``claim``, only while the claimed end's set in the change set is
    at the version the caller read. Returns the row and the claimed set's new version."""
    _change_set, writes, model, lookup = _change_set_relation_lookup(session, change_set_id)
    with lookup.deciding():
        ends = lookup.objects([str(payload.fromObjectId), str(payload.toObjectId)])
        for end in (str(payload.fromObjectId), str(payload.toObjectId)):
            if end not in ends:
                raise rules.relation_endpoint_missing(end)
        relation = decide_relation_create(
            lookup,
            model,
            payload.relationTypeKey,
            ends[str(payload.fromObjectId)],
            ends[str(payload.toObjectId)],
            payload.attributes,
            claim,
            relation_id=str(payload.id) if payload.id else None,
        )
    writes.claim(payload.expectedChangeSetVersion)
    write_change_set(writes, lookup.changes())
    row = _written_relation(writes, relation.relation_id)
    session.commit()
    return row, claim.expected + 1 if claim is not None else None


def update_change_set_relation(
    session: Session, change_set_id: str, relation_id: str, payload: Any
) -> ChangeSetRelation:
    """Replace a staged relation's attributes under its version (its ends and type are its
    identity, as live)."""
    _change_set, writes, model, lookup = _change_set_relation_lookup(session, change_set_id)
    relation = _stored_change_set_relation(session, change_set_id, relation_id)
    with lookup.deciding():
        decide_relation_update(
            lookup,
            model,
            relation,
            payload.expectedRecordVersion,
            payload.attributes
            if payload.attributes is not None
            else dict(relation.attributes or {}),
        )
    writes.claim(payload.expectedChangeSetVersion)
    write_change_set(writes, lookup.changes())
    row = _written_relation(writes, relation_id)
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
    _change_set, writes, model, lookup = _change_set_relation_lookup(session, change_set_id)
    relation = _stored_change_set_relation(session, change_set_id, relation_id)
    with lookup.deciding():
        decide_relation_delete(lookup, model, relation, expected_record_version, claim)
    writes.claim(expected_change_set_version)
    write_change_set(writes, lookup.changes())
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
        raise api_error(404, "OBJECT_NOT_FOUND", f"Object '{object_id}' not found in change set")
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
        raise api_error(404, "OBJECT_NOT_FOUND", f"Object '{object_id}' not found in change set")
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
            "UNKNOWN_ATTRIBUTES",
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
