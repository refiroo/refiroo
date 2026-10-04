from typing import Any
from uuid import uuid4

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ...errors import api_error
from ...models.commands import ObjectCreate, ObjectUpdate, RelationCreate
from ...models.database import RdmObject
from ...models.schema import EngineModel
from ..workspaces.catalogue import resolve_workspace
from . import rules
from .attributes import (
    apply_attribute_values,
    check_attribute_change,
    current_attribute_values,
    validate_attributes,
    validate_deletable_attribute,
    validate_object_attribute_rules,
)
from .audit import AuditEntry
from .batch_lookup import LiveBatchLookup, Record, Relation
from .bulk import write_live
from .context import load_object
from .feed import object_subject, relation_subject
from .refusals import LIVE
from .relations import validate_scoped_relations
from .values import stored_json_value
from .writes import LiveWrites


def create_object_record(session: Session, model: EngineModel, payload: ObjectCreate) -> RdmObject:
    """Create one object in the workspace's live object store and commit.

    Requires an active (non-retired) workspace.  The record is immediately part of the
    authoritative live projection; no publication is minted.
    """
    item = apply_object_create(session, model, payload)
    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        raise duplicate_relation() from None
    return item


def duplicate_relation() -> Exception:
    """What a live create answers when its rows collide with a row the rules did not see."""
    return api_error(409, "DUPLICATE_RELATION", "Relation already exists")


def apply_object_create(session: Session, model: EngineModel, payload: ObjectCreate) -> RdmObject:
    """Write a new live object and audit it, as a batch of one; the caller commits."""
    workspace = resolve_workspace(session, payload.workspaceKey, require_active=True)
    writes = LiveWrites(session, workspace.key)
    lookup = LiveBatchLookup.of(session, workspace.key)
    with lookup.deciding():
        record = decide_object_create(lookup, model, payload)
    try:
        return write_live(writes, model, lookup.changes())[record.object_id]
    except IntegrityError:
        raise duplicate_relation() from None


def decide_object_create(
    lookup: LiveBatchLookup, model: EngineModel, payload: ObjectCreate
) -> Record:
    """Check a new live object against the rules and lay it over ``lookup`` with its containment
    and initial relations; nothing is written (PG3b, PG-D12)."""
    workspace_key = lookup.workspace_key
    object_type_key = payload.objectTypeKey
    object_type = rules.object_identity(model, payload.applicationKey, object_type_key, LIVE)
    attributes = validate_attributes(model, object_type, attributes_to_dict(payload.attributes))
    validate_object_attribute_rules(object_type, attributes)
    rules.required_initial_relations(
        model,
        object_type_key,
        (item.relationTypeKey for item in payload.initialRelations if item.direction == "incoming"),
    )

    public_id = str(payload.id) if payload.id is not None else None
    if public_id is not None and lookup.id_taken(public_id):
        raise LIVE.object_exists(public_id)

    parent, parent_relation = rules.parent(
        lookup,
        model,
        object_type_key,
        payload.applicationKey,
        str(payload.parentObjectId) if payload.parentObjectId is not None else None,
    )
    rules.unique_values(lookup, model, None, attributes)
    record = Record(
        object_id=public_id or str(uuid4()),
        application_key=payload.applicationKey,
        object_type_key=object_type_key,
        parent_object_id=parent.object_id if parent else None,
        name=payload.name,
        version=1,
        attributes=json_values(attributes),
        workspace_key=workspace_key,
    )
    lookup.lay(record, created=True, saved=attributes)
    if parent and parent_relation:
        lookup.add_relation(
            Relation(str(uuid4()), parent_relation, parent.object_id, record.object_id, {})
        )
    rules.distinct_initial_relations(
        [
            (item.relationTypeKey, item.direction, str(item.otherObjectId))
            for item in payload.initialRelations
        ]
    )
    for initial in payload.initialRelations:
        other = lookup.object(str(initial.otherObjectId))
        if other is None:
            raise rules.relation_endpoint_missing(str(initial.otherObjectId))
        if not lookup.shares_workspace(other):
            raise api_error(422, "RELATION_WRONG_SCOPE", "Related objects must share a workspace")
        source, target = (record, other) if initial.direction == "outgoing" else (other, record)
        relation = RelationCreate(
            relationTypeKey=initial.relationTypeKey,
            fromObjectId=source.object_id,
            toObjectId=target.object_id,
            attributes=initial.attributes,
        )
        relation_attributes = rules.relation(
            lookup, model, relation.relationTypeKey, source, target, relation.attributes
        )
        if lookup.has_relation(relation.relationTypeKey, source.object_id, target.object_id):
            raise duplicate_relation()
        added = Relation(
            str(uuid4()),
            relation.relationTypeKey,
            source.object_id,
            target.object_id,
            relation_attributes,
        )
        lookup.add_relation(added)
        lookup.audit(
            AuditEntry(
                "relation",
                added.relation_id,
                "created",
                1,
                {**relation.model_dump(), "attributes": relation_attributes},
                (source.object_id, target.object_id),
                relation_subject(relation.relationTypeKey, source.object_id, target.object_id),
            )
        )
        # Like any relation write, an initial relation advances both ends' sets (ADR-022).
        lookup.advance_sets(
            relation.relationTypeKey,
            source.object_type_key,
            target.object_type_key,
            source.object_id,
            target.object_id,
        )
    lookup.audit(
        AuditEntry(
            "object",
            record.object_id,
            "created",
            1,
            {
                "objectTypeKey": object_type_key,
                "attributes": attributes,
                "initialRelations": [
                    relation.model_dump(mode="json") for relation in payload.initialRelations
                ],
            },
            (record.object_id,),
            object_subject(record),
        )
    )
    return record


def update_object_record(
    session: Session,
    model: EngineModel,
    object_type_key: str,
    object_id: str,
    payload: ObjectUpdate,
) -> RdmObject:
    """Apply a partial live object update under optimistic concurrency and commit."""
    item = apply_object_update(session, model, object_type_key, object_id, payload)
    session.commit()
    return item


def apply_object_update(
    session: Session,
    model: EngineModel,
    object_type_key: str,
    object_id: str,
    payload: ObjectUpdate,
) -> RdmObject:
    """Update a live object and audit it, as a batch of one; the caller commits."""
    # The model's refusals come before the record is read, as they always did.
    object_type = rules.get_object_type(model, object_type_key)
    if payload.attributes is not None:
        validate_attributes(
            model, object_type, attributes_to_dict(payload.attributes), partial=True
        )
    found = load_object(session, object_id, object_type_key)
    resolve_workspace(session, found.workspace_key, require_active=True)
    writes = LiveWrites(session, found.workspace_key)
    # Read again under the workspace lock: a write committed since it was found is seen, its
    # version included, which the decide step compares with the expected one.
    session.expire(found)
    item = load_object(session, object_id, object_type_key)
    lookup = LiveBatchLookup.of(session, item.workspace_key)
    with lookup.deciding():
        record = decide_object_update(lookup, model, item, payload)
    return write_live(writes, model, lookup.changes())[record.object_id]


def decide_object_update(
    lookup: LiveBatchLookup,
    model: EngineModel,
    item: Any,
    payload: ObjectUpdate,
    *,
    audit_changes: dict[str, Any] | None = None,
) -> Record:
    """Check a partial update of the live record ``item`` under its version and lay the result
    over ``lookup``; nothing is written (PG3b). ``audit_changes`` adds to the audit entry, such as
    a batch overwrite's previous version."""
    object_type = rules.get_object_type(model, item.object_type_key)
    attributes = (
        validate_attributes(
            model, object_type, attributes_to_dict(payload.attributes), partial=True
        )
        if payload.attributes is not None
        else None
    )
    # The workspace lock (PG-D5) is held: the version read is the one a write would claim.
    if item.version != payload.expectedVersion:
        raise api_error(
            409, "VERSION_CONFLICT", "Object version has changed", {"currentVersion": item.version}
        )
    if attributes is not None:
        check_attribute_change(lookup, model, object_type, item, attributes)

    values = lookup.values(item)
    record = Record(
        object_id=item.object_id,
        application_key=item.application_key,
        object_type_key=item.object_type_key,
        parent_object_id=item.parent_object_id,
        name=item.name,
        version=item.version + 1,
        attributes=values,
        workspace_key=item.workspace_key,
    )
    changes: dict[str, Any] = {}
    if payload.name is not None:
        changes["name"] = {"from": item.name, "to": payload.name}
        record.name = payload.name
    moved = "parentObjectId" in payload.model_fields_set
    if moved:
        parent, parent_relation = rules.parent(
            lookup,
            model,
            item.object_type_key,
            item.application_key,
            str(payload.parentObjectId) if payload.parentObjectId is not None else None,
            object_id=item.object_id,
            moving=True,
        )
        # The record's one containment relation is replaced, as a move always did.
        for relation in lookup.relations(
            [item.object_id],
            "incoming",
            sorted(model.containment_relation_keys(item.object_type_key)),
        ):
            lookup.remove_relation(relation)
        record.parent_object_id = parent.object_id if parent else None
        if parent and parent_relation:
            lookup.add_relation(
                Relation(str(uuid4()), parent_relation, parent.object_id, item.object_id, {})
            )
        changes["parentObjectId"] = {
            "from": item.parent_object_id,
            "to": record.parent_object_id,
        }
    if attributes is not None:
        record.attributes = {**values, **json_values(attributes)}
        changes["attributes"] = attributes
    lookup.lay(record, saved=attributes or ())

    # A name changes no scope; values change the record's own conditions; a move, the scopes
    # of the records under it.
    if moved or attributes is not None:
        validate_scoped_relations(lookup, model, record, moved=moved)

    lookup.audit(
        AuditEntry(
            "object",
            record.object_id,
            "updated",
            record.version,
            {**changes, **(audit_changes or {})},
            (record.object_id,),
            object_subject(record),
        )
    )
    return record


def json_values(attributes: dict[str, Any]) -> dict[str, Any]:
    """Normalized values in the JSON form live reads give them."""
    return {key: stored_json_value(value) for key, value in attributes.items()}


def set_live_attribute_value(
    session: Session,
    model: EngineModel,
    object_type_key: str,
    object_id: str,
    attribute_type_key: str,
    value: Any,
    expected_version: int,
    *,
    create_only: bool = False,
) -> RdmObject:
    """Set one live attribute value under the object's optimistic-concurrency version.

    ``create_only`` (POST) requires the value to be absent; otherwise the value must already exist
    (PATCH).  The object version is claimed and bumped, the merged rules are re-validated, and the
    attribute row is upserted.
    """
    object_type = rules.get_object_type(model, object_type_key)
    item = load_object(session, object_id, object_type_key)
    resolve_workspace(session, item.workspace_key, require_active=True)
    writes = LiveWrites(session, item.workspace_key)
    present = attribute_type_key in current_attribute_values(session, item.id)
    if create_only and present:
        raise api_error(
            409,
            "ATTRIBUTE_ALREADY_EXISTS",
            f"Attribute '{attribute_type_key}' already has a value on object '{object_id}'",
        )
    if not create_only and not present:
        raise api_error(
            404,
            "ATTRIBUTE_NOT_FOUND",
            f"Attribute '{attribute_type_key}' has no value on object '{object_id}'",
        )
    normalized = validate_attributes(model, object_type, {attribute_type_key: value}, partial=True)
    writes.claim_object(item, expected_version)
    apply_attribute_values(writes, model, object_type, item, normalized)
    writes.record(
        aggregate_type="object",
        aggregate_id=item.id,
        action="updated",
        version=item.version,
        changes={"attributes": normalized},
        object_ids=[item.id],
        subject=object_subject(item),
    )
    session.commit()
    return item


def delete_live_attribute_value(
    session: Session,
    model: EngineModel,
    object_type_key: str,
    object_id: str,
    attribute_type_key: str,
    expected_version: int,
) -> RdmObject:
    """Delete one live attribute value under the object's optimistic-concurrency version.

    Read-only and required attributes cannot be deleted; object-level rules are re-validated over
    the surviving values before the row is removed.
    """
    object_type = rules.get_object_type(model, object_type_key)
    item = load_object(session, object_id, object_type_key)
    resolve_workspace(session, item.workspace_key, require_active=True)
    writes = LiveWrites(session, item.workspace_key)
    validate_deletable_attribute(object_type, attribute_type_key)
    current = current_attribute_values(session, item.id)
    if attribute_type_key not in current:
        raise api_error(
            404,
            "ATTRIBUTE_NOT_FOUND",
            f"Attribute '{attribute_type_key}' has no value on object '{object_id}'",
        )
    remaining = {
        key: value for key, value in current.items() if key != attribute_type_key
    }
    validate_object_attribute_rules(object_type, remaining)
    writes.claim_object(item, expected_version)
    writes.remove_value(item.id, attribute_type_key)
    writes.record(
        aggregate_type="object",
        aggregate_id=item.id,
        action="updated",
        version=item.version,
        changes={"attributes": {attribute_type_key: None}},
        object_ids=[item.id],
        subject=object_subject(item),
    )
    session.commit()
    return item


def attributes_to_dict(attributes: list) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for item in attributes:
        if item.attributeTypeKey in result:
            raise api_error(
                422,
                "DUPLICATE_ATTRIBUTE",
                f"Attribute '{item.attributeTypeKey}' occurs more than once",
            )
        result[item.attributeTypeKey] = item.value
    return result
