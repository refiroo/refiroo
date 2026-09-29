from typing import Any

from sqlalchemy import select
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
    current_attribute_values,
    validate_attribute_change,
    validate_attributes,
    validate_deletable_attribute,
    validate_object_attribute_rules,
)
from .audit import record_audit_event
from .context import LiveLookup, load_object
from .refusals import LIVE
from .relation_set_versions import increment_set_versions
from .relations import create_relation_instance, validate_scoped_relations
from .writes import LiveWrites


def create_object_record(session: Session, model: EngineModel, payload: ObjectCreate) -> RdmObject:
    """Create one object in the workspace's live object store.

    Requires an active (non-retired) workspace.  The record is immediately part of the
    authoritative live projection; no publication is minted.
    """
    workspace = resolve_workspace(session, payload.workspaceKey, require_active=True)
    workspace_key = workspace.key
    writes = LiveWrites(session, workspace_key)
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
    if public_id is not None:
        existing = session.scalar(select(RdmObject.id).where(RdmObject.id == public_id))
        if existing:
            raise LIVE.object_exists(public_id)

    lookup = LiveLookup.of(session, workspace_key)
    parent, parent_relation = rules.parent(
        lookup,
        model,
        object_type_key,
        payload.applicationKey,
        str(payload.parentObjectId) if payload.parentObjectId is not None else None,
    )
    rules.unique_values(lookup, model, None, attributes)
    item = writes.add_object(
        object_id=public_id,
        application_key=payload.applicationKey,
        object_type_key=object_type_key,
        parent_object_id=parent.id if parent else None,
        name=payload.name,
    )
    writes.save_values(model, item.id, attributes)
    if parent and parent_relation:
        writes.add_relation(parent_relation, parent.id, item.id, flush=False)
    for initial in payload.initialRelations:
        other = load_object(session, str(initial.otherObjectId))
        if other.workspace_key != workspace_key:
            raise api_error(422, "relation_wrong_scope", "Related objects must share a workspace")
        from_object, to_object = (item, other) if initial.direction == "outgoing" else (other, item)
        try:
            create_relation_instance(
                writes,
                model,
                RelationCreate(
                    relationTypeKey=initial.relationTypeKey,
                    fromObjectId=from_object.id,
                    toObjectId=to_object.id,
                    attributes=initial.attributes,
                ),
                from_object=from_object,
                to_object=to_object,
            )
        except IntegrityError:
            session.rollback()
            raise api_error(409, "duplicate_relation", "Relation already exists") from None
        # Like any relation write, an initial relation advances both ends' sets (ADR-022).
        increment_set_versions(
            session,
            workspace_key=workspace_key,
            change_set_id=None,
            relation_type_key=initial.relationTypeKey,
            from_object_type_key=from_object.object_type_key,
            to_object_type_key=to_object.object_type_key,
            from_object_id=from_object.id,
            to_object_id=to_object.id,
        )
    record_audit_event(
        session,
        aggregate_type="object",
        aggregate_id=item.id,
        action="created",
        version=1,
        changes={
            "objectTypeKey": object_type_key,
            "attributes": attributes,
            "initialRelations": [
                relation.model_dump(mode="json") for relation in payload.initialRelations
            ],
        },
        object_ids=[item.id],
    )
    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        raise api_error(409, "duplicate_relation", "Relation already exists") from None
    return item


def update_object_record(
    session: Session,
    model: EngineModel,
    object_type_key: str,
    object_id: str,
    payload: ObjectUpdate,
) -> RdmObject:
    """Apply a partial live object update under optimistic concurrency."""
    object_type = rules.get_object_type(model, object_type_key)
    attributes = (
        validate_attributes(
            model, object_type, attributes_to_dict(payload.attributes), partial=True
        )
        if payload.attributes is not None
        else None
    )

    item = load_object(session, object_id, object_type_key)
    resolve_workspace(session, item.workspace_key, require_active=True)
    writes = LiveWrites(session, item.workspace_key)
    writes.claim_object(item, payload.expectedVersion)

    if attributes is not None:
        validate_attribute_change(session, model, object_type, item, attributes)

    changes: dict[str, Any] = {}
    if payload.name is not None:
        changes["name"] = {"from": item.name, "to": payload.name}
        item.name = payload.name
    if "parentObjectId" in payload.model_fields_set:
        old_parent = item.parent_object_id
        parent, parent_relation = rules.parent(
            LiveLookup.of(session, item.workspace_key),
            model,
            object_type_key,
            item.application_key,
            str(payload.parentObjectId) if payload.parentObjectId is not None else None,
            object_id=item.id,
            moving=True,
        )
        writes.place(
            item,
            parent.id if parent else None,
            parent_relation,
            model.containment_relation_keys(item.object_type_key),
        )
        changes["parentObjectId"] = {
            "from": old_parent,
            "to": parent.id if parent else None,
        }
    if attributes is not None:
        writes.save_values(model, item.id, attributes)
        changes["attributes"] = attributes

    # A name changes no scope; values change the record's own conditions; a move, the scopes
    # of the records under it.
    if "parentObjectId" in changes or attributes is not None:
        validate_scoped_relations(session, model, item, moved="parentObjectId" in changes)

    record_audit_event(
        session,
        aggregate_type="object",
        aggregate_id=item.id,
        action="updated",
        version=item.version,
        changes=changes,
        object_ids=[item.id],
    )
    session.commit()
    return item


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
            "attribute_already_exists",
            f"Attribute '{attribute_type_key}' already has a value on object '{object_id}'",
        )
    if not create_only and not present:
        raise api_error(
            404,
            "attribute_not_found",
            f"Attribute '{attribute_type_key}' has no value on object '{object_id}'",
        )
    normalized = validate_attributes(model, object_type, {attribute_type_key: value}, partial=True)
    writes.claim_object(item, expected_version)
    apply_attribute_values(writes, model, object_type, item, normalized)
    record_audit_event(
        session,
        aggregate_type="object",
        aggregate_id=item.id,
        action="updated",
        version=item.version,
        changes={"attributes": normalized},
        object_ids=[item.id],
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
            "attribute_not_found",
            f"Attribute '{attribute_type_key}' has no value on object '{object_id}'",
        )
    remaining = {
        key: value for key, value in current.items() if key != attribute_type_key
    }
    validate_object_attribute_rules(object_type, remaining)
    writes.claim_object(item, expected_version)
    writes.remove_value(item.id, attribute_type_key)
    record_audit_event(
        session,
        aggregate_type="object",
        aggregate_id=item.id,
        action="updated",
        version=item.version,
        changes={"attributes": {attribute_type_key: None}},
        object_ids=[item.id],
    )
    session.commit()
    return item


def attributes_to_dict(attributes: list) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for item in attributes:
        if item.attributeTypeKey in result:
            raise api_error(
                422,
                "duplicate_attribute",
                f"Attribute '{item.attributeTypeKey}' occurs more than once",
            )
        result[item.attributeTypeKey] = item.value
    return result
