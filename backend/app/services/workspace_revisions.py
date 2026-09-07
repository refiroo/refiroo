"""Persistence-only helpers for ADR-024 workspace revision membership.

WP6 deliberately exposes no lifecycle routes.  These helpers define the copy-on-write read rule so
WP7 editing and publication can reuse one authoritative interpretation of draft membership.
"""

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from ..errors import ApiError, api_error
from ..models.database import (
    AttributeValue,
    ModelRelease,
    ObjectRelation,
    RdmObject,
    Workspace,
    WorkspaceDraft,
    WorkspaceDraftObject,
    WorkspaceDraftRelation,
    WorkspaceRevision,
    WorkspaceRevisionObject,
    WorkspaceRevisionRelation,
)
from .attributes import (
    save_attribute_values,
    validate_attributes,
    validate_object_attribute_rules,
)
from .audit import record_audit_event
from .model.compiler import parse_model
from .relations import validate_relation_attributes


@dataclass(frozen=True)
class EffectiveDraftMembership:
    draft: WorkspaceDraft
    objects: tuple[WorkspaceRevisionObject | WorkspaceDraftObject, ...]
    relations: tuple[WorkspaceRevisionRelation | WorkspaceDraftRelation, ...]


def effective_draft_membership(session: Session, draft_id: str) -> EffectiveDraftMembership:
    """Resolve a draft's immutable base plus its changed rows and tombstones.

    A draft row replaces the same stable public ID from its base.  A tombstone hides that base row;
    therefore an edit does not copy unrelated records from the source revision.
    """
    draft = session.scalar(select(WorkspaceDraft).where(WorkspaceDraft.id == draft_id))
    if draft is None:
        raise api_error(404, "workspace_draft_not_found", f"Workspace draft '{draft_id}' not found")
    objects: dict[str, WorkspaceRevisionObject | WorkspaceDraftObject] = {}
    relations: dict[str, WorkspaceRevisionRelation | WorkspaceDraftRelation] = {}
    if draft.derived_from_revision_id is not None:
        revision = session.scalar(
            select(WorkspaceRevision).where(WorkspaceRevision.id == draft.derived_from_revision_id)
        )
        if revision is None or revision.workspace_key != draft.workspace_key:
            raise api_error(
                409,
                "workspace_draft_base_invalid",
                "Workspace draft base revision is missing or belongs to another workspace",
            )
        objects = {
            item.object_id: item
            for item in session.scalars(
                select(WorkspaceRevisionObject).where(
                    WorkspaceRevisionObject.revision_id == revision.id
                )
            )
        }
        relations = {
            item.relation_id: item
            for item in session.scalars(
                select(WorkspaceRevisionRelation).where(
                    WorkspaceRevisionRelation.revision_id == revision.id
                )
            )
        }
    for item in session.scalars(
        select(WorkspaceDraftObject).where(WorkspaceDraftObject.draft_id == draft.id)
    ):
        if item.is_deleted:
            objects.pop(item.object_id, None)
        else:
            objects[item.object_id] = item
    for item in session.scalars(
        select(WorkspaceDraftRelation).where(WorkspaceDraftRelation.draft_id == draft.id)
    ):
        if item.is_deleted:
            relations.pop(item.relation_id, None)
        else:
            relations[item.relation_id] = item
    return EffectiveDraftMembership(
        draft=draft,
        objects=tuple(objects[key] for key in sorted(objects)),
        relations=tuple(relations[key] for key in sorted(relations)),
    )


def _draft(session: Session, draft_id: str, *, for_update: bool = False) -> WorkspaceDraft:
    statement = select(WorkspaceDraft).where(WorkspaceDraft.id == draft_id)
    if for_update:
        statement = statement.with_for_update()
    item = session.scalar(statement)
    if item is None:
        raise api_error(404, "workspace_draft_not_found", f"Workspace draft '{draft_id}' not found")
    if for_update:
        workspace = session.get(Workspace, item.workspace_key)
        if workspace is None:
            raise api_error(404, "workspace_not_found", f"Workspace '{item.workspace_key}' not found")
        if workspace.status != "active":
            raise api_error(409, "workspace_retired", "Workspace is retired and cannot be mutated")
    return item


def ensure_draft_writable(session: Session, draft_id: str) -> WorkspaceDraft:
    """Resolve a draft and reject mutations against a retired workspace."""
    return _draft(session, draft_id, for_update=True)


def _claim_draft(draft: WorkspaceDraft, expected: int) -> None:
    if draft.version != expected:
        raise api_error(
            409, "workspace_draft_version_conflict", "Workspace draft version has changed"
        )
    draft.version += 1
    draft.updated_at = datetime.now(UTC)


def create_draft(
    session: Session,
    workspace_key: str,
    model_release_id: int,
    *,
    name: str | None = None,
    source_revision_id: str | None = None,
) -> WorkspaceDraft:
    workspace = session.get(Workspace, workspace_key)
    if workspace is None:
        raise api_error(404, "workspace_not_found", f"Workspace '{workspace_key}' not found")
    if workspace.status != "active":
        raise api_error(409, "workspace_retired", "Retired workspaces cannot be edited")
    if source_revision_id is not None:
        revision = session.scalar(
            select(WorkspaceRevision).where(WorkspaceRevision.id == source_revision_id)
        )
        if revision is None or revision.workspace_key != workspace_key:
            raise api_error(
                404, "workspace_revision_not_found", "Source workspace revision was not found"
            )
        model_release_id = revision.model_release_id
    draft = WorkspaceDraft(
        workspace_key=workspace_key,
        model_release_id=model_release_id,
        derived_from_revision_id=source_revision_id,
        name=name,
    )
    session.add(draft)
    session.commit()
    session.refresh(draft)
    return draft


def update_draft(
    session: Session, draft_id: str, expected_version: int, name: str | None
) -> WorkspaceDraft:
    draft = _draft(session, draft_id, for_update=True)
    _claim_draft(draft, expected_version)
    draft.name = name
    session.commit()
    return draft


def discard_draft(session: Session, draft_id: str, expected_version: int) -> None:
    draft = _draft(session, draft_id, for_update=True)
    _claim_draft(draft, expected_version)
    session.delete(draft)
    session.commit()


def _record_conflict(expected: int | None, actual: int, label: str) -> None:
    if expected is not None and expected != actual:
        raise api_error(409, "version_conflict", f"{label} version has changed")


def _draft_model(session: Session, draft: WorkspaceDraft) -> Any:
    release = session.get(ModelRelease, draft.model_release_id)
    if release is None:
        raise api_error(409, "workspace_draft_model_release_conflict", "Pinned model release is unavailable")
    try:
        return parse_model(release.model_json)
    except Exception as exc:  # controlled public error; preserve cause for diagnostics
        raise api_error(409, "workspace_draft_model_release_conflict", "Pinned model release cannot be compiled") from exc


def _normalize_object_attributes(model: Any, object_type_key: str, attributes: dict[str, Any], *, partial: bool) -> dict[str, Any]:
    object_type = model.object_type(object_type_key)
    if object_type is None:
        raise api_error(422, "unknown_object_type", f"Object type '{object_type_key}' is not in the pinned model")
    return validate_attributes(model, object_type, attributes, partial=partial, apply_defaults=not partial)


def _validate_object_identity(model: Any, application_key: str, object_type_key: str) -> None:
    object_type = model.object_type(object_type_key)
    if object_type is None:
        raise api_error(422, "unknown_object_type", f"Object type '{object_type_key}' is not in the pinned model")
    application = next((item for item in model.applications if item.key == application_key), None)
    if application is None or object_type_key not in application.objectTypeKeys:
        raise api_error(422, "object_type_not_in_application", f"Object type '{object_type_key}' is not enabled in application '{application_key}'")


def _normalize_relation(model: Any, relation_type_key: str, from_type: str, to_type: str, attributes: dict[str, Any]) -> dict[str, Any]:
    relation = model.relation_type(relation_type_key)
    if relation is None:
        raise api_error(422, "unknown_relation_type", f"Relation type '{relation_type_key}' is not in the pinned model")
    allowed = next((item for item in model.objectTypeRelations if item.relationTypeKey == relation_type_key and item.fromObjectTypeKey == from_type and item.toObjectTypeKey == to_type), None)
    if allowed is None:
        raise api_error(422, "invalid_relation_pair", "Relation is not permitted between these object types")
    return validate_relation_attributes(model, allowed, attributes)


def _validate_draft_relation(model: Any, membership: EffectiveDraftMembership, relation_type_key: str, from_id: str, to_id: str, attributes: dict[str, Any], *, exclude_id: str | None = None) -> dict[str, Any]:
    objects = {item.object_id: item for item in membership.objects}
    source, target = objects.get(from_id), objects.get(to_id)
    if source is None or target is None:
        raise api_error(422, "relation_endpoint_missing", "Relation endpoints must exist in the workspace draft")
    allowed = next((item for item in model.objectTypeRelations if item.relationTypeKey == relation_type_key and item.fromObjectTypeKey == source.object_type_key and item.toObjectTypeKey == target.object_type_key), None)
    normalized = _normalize_relation(model, relation_type_key, source.object_type_key, target.object_type_key, attributes)
    if allowed.features.get("parent") or relation_type_key in set((model.object_type(target.object_type_key).behavior or {}).get("parentRelationTypeKeys", [])):
        raise api_error(422, "immutable_relation", "Engine-maintained containment relations are changed through object edits")
    existing = [row for row in membership.relations if row.relation_id != exclude_id and row.relation_type_key == relation_type_key]
    if allowed.cardinality == "one-to-one" and any(row.from_object_id == from_id or row.to_object_id == to_id for row in existing):
        raise api_error(409, "cardinality_violation", "Relation cardinality would be violated")
    if allowed.cardinality == "one-to-many" and any(row.to_object_id == to_id for row in existing):
        raise api_error(409, "cardinality_violation", "Relation cardinality would be violated")
    ancestor_type = allowed.features.get("uniqueToAncestorTypeKey")
    if ancestor_type:
        condition = allowed.features.get("uniqueWhenToAttributeEquals")
        if condition and (target.attributes or {}).get(condition["attributeTypeKey"]) != condition["value"]:
            return normalized
        def ancestor(item):
            seen = set()
            while item and item.object_id not in seen:
                seen.add(item.object_id)
                if item.object_type_key == ancestor_type:
                    return item.object_id
                item = objects.get(item.parent_object_id) if item.parent_object_id else None
            return None
        target_ancestor = ancestor(target)
        if target_ancestor and any(
            row.from_object_id == from_id
            and ancestor(objects.get(row.to_object_id)) == target_ancestor
            and (
                not condition
                or (objects.get(row.to_object_id).attributes or {}).get(condition["attributeTypeKey"])
                == condition["value"]
            )
            for row in existing
        ):
            raise api_error(409, "duplicate_relation_scope", "A related object already exists for this ancestor scope")
    return normalized


def put_draft_object(session: Session, draft_id: str, payload: Any) -> WorkspaceDraftObject:
    draft = _draft(session, draft_id, for_update=True)
    model = _draft_model(session, draft)
    _validate_object_identity(model, payload.applicationKey, payload.objectTypeKey)
    attributes = _normalize_object_attributes(model, payload.objectTypeKey, payload.attributes, partial=False)
    validate_object_attribute_rules(model.object_type(payload.objectTypeKey), attributes)
    membership = effective_draft_membership(session, draft_id)
    if payload.parentObjectId is not None and not any(item.object_id == str(payload.parentObjectId) for item in membership.objects):
        raise api_error(422, "parent_wrong_scope", "Parent must exist in the workspace draft")
    _claim_draft(draft, payload.expectedDraftVersion)
    object_id = str(payload.id) if payload.id else str(uuid4())
    row = session.scalar(
        select(WorkspaceDraftObject).where(
            WorkspaceDraftObject.draft_id == draft_id, WorkspaceDraftObject.object_id == object_id
        )
    )
    if row is not None:
        raise api_error(409, "object_already_exists", f"Object '{object_id}' already exists")
    else:
        if payload.expectedRecordVersion is not None:
            raise api_error(409, "version_conflict", "Object record does not exist")
        row = WorkspaceDraftObject(
            draft_id=draft_id,
            object_id=object_id,
            application_key=payload.applicationKey,
            object_type_key=payload.objectTypeKey,
            name=payload.name,
            parent_object_id=str(payload.parentObjectId) if payload.parentObjectId else None,
            attributes=attributes,
            version=1,
        )
        session.add(row)
    _validate_draft_attribute_uniqueness(model, membership, row.object_id, attributes)
    _sync_draft_parent_relation(session, draft, model, row)
    if getattr(payload, "initialRelations", None):
        identities = [
            (item.relationTypeKey, item.direction, str(item.otherObjectId))
            for item in payload.initialRelations
        ]
        if len(identities) != len(set(identities)):
            raise api_error(422, "duplicate_initial_relation", "Initial relationships must not repeat")
        objects = {item.object_id: item for item in effective_draft_membership(session, draft_id).objects}
        objects[row.object_id] = row
        candidate_relations = list(membership.relations)
        for initial in payload.initialRelations:
            from_id = row.object_id if initial.direction == "outgoing" else str(initial.otherObjectId)
            to_id = str(initial.otherObjectId) if initial.direction == "outgoing" else row.object_id
            target = objects.get(to_id)
            source = objects.get(from_id)
            if source is None or target is None:
                raise api_error(422, "relation_endpoint_missing", "Relation endpoints must exist in the workspace draft")
            candidate = EffectiveDraftMembership(draft, tuple(objects.values()), tuple(candidate_relations))
            attrs = _validate_draft_relation(
                model, candidate, initial.relationTypeKey, from_id, to_id, initial.attributes
            )
            relation = WorkspaceDraftRelation(
                draft_id=draft.id,
                relation_id=str(uuid4()),
                relation_type_key=initial.relationTypeKey,
                from_object_id=from_id,
                to_object_id=to_id,
                attributes=attrs,
                version=1,
            )
            candidate_relations.append(relation)
            session.add(relation)
    parent_keys = set((model.object_type(row.object_type_key).behavior or {}).get("parentRelationTypeKeys", [])) if model.object_type(row.object_type_key) else set()
    required = {item.relationTypeKey for item in model.objectTypeRelations if item.toObjectTypeKey == row.object_type_key and item.required and item.relationTypeKey not in parent_keys}
    provided = {item.relationTypeKey for item in getattr(payload, "initialRelations", []) if item.direction == "incoming"}
    if required - provided:
        raise api_error(422, "missing_required_relations", f"Required relationships missing: {sorted(required - provided)}", {"relationTypeKeys": sorted(required - provided)})
    record_audit_event(session, aggregate_type="object-draft", aggregate_id=row.object_id,
                       action="created", version=row.version,
                       changes={"attributes": attributes, "workspaceDraftId": draft.id}, object_ids=[row.object_id])
    session.commit()
    return row


def update_draft_object(
    session: Session, draft_id: str, object_id: str, payload: Any
) -> WorkspaceDraftObject:
    draft = _draft(session, draft_id, for_update=True)
    model = _draft_model(session, draft)
    membership = effective_draft_membership(session, draft_id)
    _claim_draft(draft, payload.expectedDraftVersion)
    row = session.scalar(
        select(WorkspaceDraftObject).where(
            WorkspaceDraftObject.draft_id == draft_id, WorkspaceDraftObject.object_id == object_id
        )
    )
    if row is None:
        base = next(
            (
                item
                for item in effective_draft_membership(session, draft_id).objects
                if item.object_id == object_id
            ),
            None,
        )
        if base is None:
            raise api_error(404, "object_not_found", f"Object '{object_id}' not found in draft")
        row = WorkspaceDraftObject(
            draft_id=draft_id,
            object_id=object_id,
            application_key=base.application_key,
            object_type_key=base.object_type_key,
            name=base.name,
            parent_object_id=base.parent_object_id,
            attributes=dict(base.attributes or {}),
            version=base.version,
        )
        session.add(row)
        session.flush()
    _record_conflict(payload.expectedRecordVersion, row.version, "Object record")
    if payload.name is not None:
        row.name = payload.name
    if "parentObjectId" in payload.model_fields_set:
        row.parent_object_id = str(payload.parentObjectId) if payload.parentObjectId else None
    if payload.attributes is not None:
        row.attributes = {
            **(row.attributes or {}),
            **_normalize_object_attributes(model, row.object_type_key, payload.attributes, partial=True),
        }
    _validate_draft_attribute_uniqueness(model, membership, row.object_id, row.attributes or {})
    candidate_objects = tuple(
        row if item.object_id == row.object_id else item for item in membership.objects
    )
    candidate = EffectiveDraftMembership(draft, candidate_objects, membership.relations)
    for relation in membership.relations:
        if relation.to_object_id == row.object_id:
            parent_keys = set(
                (model.object_type(row.object_type_key).behavior or {}).get(
                    "parentRelationTypeKeys", []
                )
            )
            if relation.relation_type_key in parent_keys:
                continue
            _validate_draft_relation(
                model,
                candidate,
                relation.relation_type_key,
                relation.from_object_id,
                relation.to_object_id,
                dict(relation.attributes or {}),
                exclude_id=relation.relation_id,
            )
    row.version += 1
    row.is_deleted = False
    _sync_draft_parent_relation(session, draft, model, row)
    record_audit_event(session, aggregate_type="object-draft", aggregate_id=row.object_id,
                       action="updated", version=row.version,
                       changes={"attributes": row.attributes or {}, "workspaceDraftId": draft.id}, object_ids=[row.object_id])
    session.commit()
    return row


def delete_draft_object(
    session: Session,
    draft_id: str,
    object_id: str,
    expected_draft_version: int,
    expected_record_version: int,
    *,
    cascade: bool = False,
) -> None:
    draft = _draft(session, draft_id, for_update=True)
    model = _draft_model(session, draft)
    membership = effective_draft_membership(session, draft_id)
    objects = {item.object_id: item for item in membership.objects}
    root = objects.get(object_id)
    if root is None:
        raise api_error(404, "object_not_found", f"Object '{object_id}' not found in draft")
    _record_conflict(expected_record_version, root.version, "Object record")

    planned_ids = {object_id}
    reasons: dict[str, str] = {object_id: "root"}
    frontier = [object_id]
    while frontier:
        parent_id = frontier.pop()
        children = [
            item.object_id
            for item in membership.objects
            if item.parent_object_id == parent_id and item.object_id not in planned_ids
        ]
        planned_ids.update(children)
        reasons.update({child: "child" for child in children})
        frontier.extend(children)
        for relation in membership.relations:
            if relation.from_object_id != parent_id or relation.to_object_id in planned_ids:
                continue
            source, target = objects.get(relation.from_object_id), objects.get(relation.to_object_id)
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
            if allowed is not None and allowed.required and allowed.cardinality in {"one-to-one", "one-to-many"}:
                planned_ids.add(target.object_id)
                reasons[target.object_id] = "required-ownership"
                frontier.append(target.object_id)
    incident = [
        relation
        for relation in membership.relations
        if relation.from_object_id in planned_ids or relation.to_object_id in planned_ids
    ]
    if not cascade and len(planned_ids) > 1:
        dependants = [
            {
                "id": item.object_id,
                "name": item.name,
                "objectTypeKey": item.object_type_key,
                "applicationKey": item.application_key,
                "parentObjectId": item.parent_object_id,
                "reason": reasons[item.object_id],
            }
            for item in membership.objects
            if item.object_id in planned_ids and item.object_id != object_id
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
            },
        )
    _claim_draft(draft, expected_draft_version)
    for deleted_id in planned_ids:
        base = objects[deleted_id]
        row = session.scalar(
            select(WorkspaceDraftObject).where(
                WorkspaceDraftObject.draft_id == draft_id,
                WorkspaceDraftObject.object_id == deleted_id,
            )
        )
        if row is None:
            row = WorkspaceDraftObject(
                draft_id=draft_id,
                object_id=deleted_id,
                application_key=base.application_key,
                object_type_key=base.object_type_key,
                name=base.name,
                parent_object_id=base.parent_object_id,
                attributes=dict(base.attributes or {}),
                version=base.version + 1,
                is_deleted=True,
            )
            session.add(row)
        else:
            row.version += 1
            row.is_deleted = True
    for relation in incident:
        row = session.scalar(
            select(WorkspaceDraftRelation).where(
                WorkspaceDraftRelation.draft_id == draft_id,
                WorkspaceDraftRelation.relation_id == relation.relation_id,
            )
        )
        if row is None:
            row = WorkspaceDraftRelation(
                draft_id=draft_id,
                relation_id=relation.relation_id,
                relation_type_key=relation.relation_type_key,
                from_object_id=relation.from_object_id,
                to_object_id=relation.to_object_id,
                attributes=dict(relation.attributes or {}),
                version=relation.version + 1,
                is_deleted=True,
            )
            session.add(row)
        else:
            row.version += 1
            row.is_deleted = True
    session.commit()


def _validate_draft_attribute_uniqueness(
    model: Any,
    membership: EffectiveDraftMembership,
    object_id: str,
    attributes: dict[str, Any],
) -> None:
    for key, value in attributes.items():
        definition = model.attribute_type(key)
        if definition is None or not definition.features.get("unique"):
            continue
        conflict = next(
            (
                item.object_id
                for item in membership.objects
                if item.object_id != object_id and (item.attributes or {}).get(key) == value
            ),
            None,
        )
        if conflict is not None:
            raise api_error(
                409,
                "duplicate_attribute_value",
                f"Attribute '{key}' must be unique in the workspace draft",
                {"attributeTypeKey": key, "conflictingObjectId": conflict},
            )


def _sync_draft_parent_relation(session: Session, draft: WorkspaceDraft, model: Any, row: WorkspaceDraftObject) -> None:
    """Maintain the typed containment edge with a draft object edit."""
    keys = set((model.object_type(row.object_type_key).behavior or {}).get("parentRelationTypeKeys", [])) if model.object_type(row.object_type_key) else set()
    if not keys:
        return
    existing = list(session.scalars(select(WorkspaceDraftRelation).where(WorkspaceDraftRelation.draft_id == draft.id, WorkspaceDraftRelation.to_object_id == row.object_id, WorkspaceDraftRelation.relation_type_key.in_(keys))))
    for relation in existing:
        relation.is_deleted = True
        relation.version += 1
    if row.parent_object_id:
        parent = next((item for item in effective_draft_membership(session, draft.id).objects if item.object_id == row.parent_object_id), None)
        if parent is None:
            raise api_error(422, "parent_wrong_scope", "Parent must exist in the workspace draft")
        allowed = next((item for item in model.objectTypeRelations if item.relationTypeKey in keys and item.fromObjectTypeKey == parent.object_type_key and item.toObjectTypeKey == row.object_type_key), None)
        if allowed is None:
            raise api_error(422, "invalid_parent_type", "Parent type is not permitted for this object type")
        session.add(WorkspaceDraftRelation(draft_id=draft.id, relation_id=str(uuid4()), relation_type_key=allowed.relationTypeKey, from_object_id=parent.object_id, to_object_id=row.object_id, attributes={}, version=1))


def put_draft_relation(session: Session, draft_id: str, payload: Any) -> WorkspaceDraftRelation:
    draft = _draft(session, draft_id, for_update=True)
    model = _draft_model(session, draft)
    membership = effective_draft_membership(session, draft_id)
    relation_id = str(payload.id) if payload.id else str(uuid4())
    row = session.scalar(
        select(WorkspaceDraftRelation).where(
            WorkspaceDraftRelation.draft_id == draft_id,
            WorkspaceDraftRelation.relation_id == relation_id,
        )
    )
    attributes = _validate_draft_relation(model, membership, payload.relationTypeKey, str(payload.fromObjectId), str(payload.toObjectId), payload.attributes)
    _claim_draft(draft, payload.expectedDraftVersion)
    if row is None:
        row = WorkspaceDraftRelation(
            draft_id=draft_id,
            relation_id=relation_id,
            relation_type_key=payload.relationTypeKey,
            from_object_id=str(payload.fromObjectId),
            to_object_id=str(payload.toObjectId),
            attributes=attributes,
            version=1,
        )
        session.add(row)
    else:
        _record_conflict(payload.expectedRecordVersion, row.version, "Relation record")
        row.version += 1
        row.relation_type_key = payload.relationTypeKey
        row.from_object_id = str(payload.fromObjectId)
        row.to_object_id = str(payload.toObjectId)
        row.attributes = attributes
        row.is_deleted = False
    record_audit_event(session, aggregate_type="relation", aggregate_id=row.relation_id,
                       action="created" if row.version == 1 else "updated", version=row.version,
                       changes={"attributes": attributes, "workspaceDraftId": draft.id}, object_ids=[row.from_object_id, row.to_object_id])
    session.commit()
    return row


def update_draft_relation(session: Session, draft_id: str, relation_id: str, payload: Any) -> WorkspaceDraftRelation:
    draft = _draft(session, draft_id, for_update=True)
    model = _draft_model(session, draft)
    row = session.scalar(select(WorkspaceDraftRelation).where(WorkspaceDraftRelation.draft_id == draft_id, WorkspaceDraftRelation.relation_id == relation_id))
    if row is None:
        base = next((item for item in effective_draft_membership(session, draft_id).relations if item.relation_id == relation_id), None)
        if base is None:
            raise api_error(404, "relation_not_found", f"Relation '{relation_id}' not found in draft")
        row = WorkspaceDraftRelation(draft_id=draft_id, relation_id=relation_id, relation_type_key=base.relation_type_key, from_object_id=base.from_object_id, to_object_id=base.to_object_id, attributes=dict(base.attributes or {}), version=base.version)
        session.add(row)
        session.flush()
    _record_conflict(payload.expectedRecordVersion, row.version, "Relation record")
    membership = effective_draft_membership(session, draft_id)
    relation_type = payload.relationTypeKey or row.relation_type_key
    from_id = str(payload.fromObjectId) if payload.fromObjectId else row.from_object_id
    to_id = str(payload.toObjectId) if payload.toObjectId else row.to_object_id
    attrs = row.attributes or {}
    if payload.attributes is not None:
        attrs = payload.attributes
    attrs = _validate_draft_relation(model, membership, relation_type, from_id, to_id, attrs, exclude_id=relation_id)
    _claim_draft(draft, payload.expectedDraftVersion)
    row.relation_type_key, row.from_object_id, row.to_object_id, row.attributes = relation_type, from_id, to_id, attrs
    row.version += 1
    row.is_deleted = False
    record_audit_event(session, aggregate_type="relation", aggregate_id=row.relation_id,
                       action="updated", version=row.version,
                       changes={"attributes": attrs, "workspaceDraftId": draft.id}, object_ids=[row.from_object_id, row.to_object_id])
    session.commit()
    return row


def delete_draft_relation(session: Session, draft_id: str, relation_id: str, expected_draft_version: int, expected_record_version: int) -> None:
    draft = _draft(session, draft_id, for_update=True)
    model = _draft_model(session, draft)
    membership = effective_draft_membership(session, draft_id)
    row = session.scalar(select(WorkspaceDraftRelation).where(WorkspaceDraftRelation.draft_id == draft_id, WorkspaceDraftRelation.relation_id == relation_id))
    if row is None:
        base = next((item for item in effective_draft_membership(session, draft_id).relations if item.relation_id == relation_id), None)
        if base is None:
            raise api_error(404, "relation_not_found", f"Relation '{relation_id}' not found in draft")
        row = WorkspaceDraftRelation(draft_id=draft_id, relation_id=relation_id, relation_type_key=base.relation_type_key, from_object_id=base.from_object_id, to_object_id=base.to_object_id, attributes=dict(base.attributes or {}), version=base.version)
        session.add(row)
        session.flush()
    objects = {item.object_id: item for item in membership.objects}
    target = objects.get(row.to_object_id)
    if target is not None:
        parent_keys = set(
            (model.object_type(target.object_type_key).behavior or {}).get(
                "parentRelationTypeKeys", []
            )
        )
        if row.relation_type_key in parent_keys:
            raise api_error(422, "immutable_relation", "Engine-maintained containment relations cannot be deleted directly")
        allowed = next(
            (
                item
                for item in model.objectTypeRelations
                if item.relationTypeKey == row.relation_type_key
                and item.fromObjectTypeKey == objects.get(row.from_object_id).object_type_key
                and item.toObjectTypeKey == target.object_type_key
            ),
            None,
        )
        if allowed is not None and allowed.required:
            raise api_error(422, "required_relation", "Required relationships cannot be deleted directly")
    _record_conflict(expected_record_version, row.version, "Relation record")
    _claim_draft(draft, expected_draft_version)
    row.version += 1
    row.is_deleted = True
    session.commit()


def patch_draft_attribute(session: Session, draft_id: str, object_id: str, key: str, value: Any, expected_draft_version: int, expected_record_version: int) -> WorkspaceDraftObject:
    draft = _draft(session, draft_id, for_update=True)
    membership = effective_draft_membership(session, draft_id)
    base = next((item for item in membership.objects if item.object_id == object_id), None)
    if base is None:
        raise api_error(404, "object_not_found", f"Object '{object_id}' not found in draft")
    row = session.scalar(select(WorkspaceDraftObject).where(WorkspaceDraftObject.draft_id == draft_id, WorkspaceDraftObject.object_id == object_id))
    if row is None:
        row = WorkspaceDraftObject(draft_id=draft_id, object_id=object_id, application_key=base.application_key, object_type_key=base.object_type_key, name=base.name, parent_object_id=base.parent_object_id, attributes=dict(base.attributes or {}), version=base.version)
        session.add(row)
        session.flush()
    _record_conflict(expected_record_version, row.version, "Object record")
    model = _draft_model(session, draft)
    normalized = _normalize_object_attributes(model, row.object_type_key, {key: value}, partial=True)
    _claim_draft(draft, expected_draft_version)
    row.attributes = {**(row.attributes or {}), **normalized}
    _validate_draft_attribute_uniqueness(model, membership, row.object_id, row.attributes)
    row.version += 1
    record_audit_event(session, aggregate_type="object-draft", aggregate_id=row.object_id,
                       action="updated", version=row.version,
                       changes={"attributes": {key: value}, "workspaceDraftId": draft.id}, object_ids=[row.object_id])
    session.commit()
    return row


def delete_draft_attribute(session: Session, draft_id: str, object_id: str, key: str, expected_draft_version: int, expected_record_version: int) -> WorkspaceDraftObject:
    draft = _draft(session, draft_id, for_update=True)
    membership = effective_draft_membership(session, draft_id)
    base = next((item for item in membership.objects if item.object_id == object_id), None)
    if base is None:
        raise api_error(404, "object_not_found", f"Object '{object_id}' not found in draft")
    row = session.scalar(select(WorkspaceDraftObject).where(WorkspaceDraftObject.draft_id == draft_id, WorkspaceDraftObject.object_id == object_id))
    if row is None:
        row = WorkspaceDraftObject(draft_id=draft_id, object_id=object_id, application_key=base.application_key, object_type_key=base.object_type_key, name=base.name, parent_object_id=base.parent_object_id, attributes=dict(base.attributes or {}), version=base.version)
        session.add(row)
        session.flush()
    _record_conflict(expected_record_version, row.version, "Object record")
    model = _draft_model(session, draft)
    object_type = model.object_type(row.object_type_key)
    binding = next((item for item in object_type.attributes if item.attributeTypeKey == key), None) if object_type else None
    if binding is None:
        raise api_error(422, "unknown_attributes", f"Attribute '{key}' is not defined on object type '{row.object_type_key}'")
    if binding.required:
        raise api_error(422, "cannot_delete_required_attribute", f"Attribute '{key}' is required")
    remaining = {item_key: item_value for item_key, item_value in (row.attributes or {}).items() if item_key != key}
    validate_object_attribute_rules(object_type, remaining)
    _claim_draft(draft, expected_draft_version)
    row.attributes = remaining
    row.version += 1
    record_audit_event(session, aggregate_type="object-draft", aggregate_id=row.object_id,
                       action="updated", version=row.version,
                       changes={"attributes": {key: None}, "workspaceDraftId": draft.id}, object_ids=[row.object_id])
    session.commit()
    return row


def _diagnostics(membership: EffectiveDraftMembership, model: Any) -> list[dict[str, Any]]:
    errors: list[dict[str, Any]] = []
    objects = {item.object_id: item for item in membership.objects}
    relation_rows = list(membership.relations)
    for item in membership.objects:
        object_type = model.object_type(item.object_type_key)
        if object_type is None:
            errors.append(
                {
                    "code": "unknown_object_type",
                    "message": f"Object type '{item.object_type_key}' is not in the pinned model",
                }
            )
        else:
            try:
                attrs = validate_attributes(model, object_type, dict(item.attributes or {}), partial=False)
                validate_object_attribute_rules(object_type, attrs)
            except ApiError as exc:
                errors.append({"code": exc.code, "message": exc.message, "details": {"objectId": item.object_id, **(exc.details or {})} if isinstance(exc.details, dict) else {"objectId": item.object_id}})
            _validate_application_diagnostic(errors, model, item)
            # Attribute uniqueness is scoped to the candidate graph, never to the mutable active
            # projection (which may still contain a different publication).
            for key, definition in ((key, model.attribute_type(key)) for key in (item.attributes or {})):
                if definition and definition.features.get("unique"):
                    same = [other.object_id for other in membership.objects if other.object_id != item.object_id and (other.attributes or {}).get(key) == (item.attributes or {}).get(key)]
                    if same:
                        errors.append({"code": "duplicate_attribute_value", "message": f"Attribute '{key}' must be unique", "details": {"objectId": item.object_id, "attributeTypeKey": key, "conflictingObjectIds": sorted(same)}})
        seen: set[str] = {item.object_id}
        current = item
        while current.parent_object_id:
            parent = objects.get(current.parent_object_id)
            if parent is None or current.parent_object_id in seen:
                errors.append(
                    {
                        "code": "containment_cycle",
                        "message": "Containment graph contains a cycle or missing parent",
                    }
                )
                break
            seen.add(parent.object_id)
            if not _parent_pair_exists(model, current, parent, relation_rows):
                errors.append({"code": "containment_relation_missing", "message": "Containment parent is not represented by its declared parent relation", "details": {"objectId": current.object_id, "parentObjectId": parent.object_id}})
            current = parent
    valid_relations = []
    for relation in relation_rows:
        if relation.from_object_id not in objects or relation.to_object_id not in objects:
            errors.append(
                {
                    "code": "relation_endpoint_missing",
                    "message": "Relation endpoint is not in the candidate graph",
                }
            )
            continue
        source, target = objects[relation.from_object_id], objects[relation.to_object_id]
        allowed = next(
            (
                pair
                for pair in model.objectTypeRelations
                if pair.relationTypeKey == relation.relation_type_key
                and pair.fromObjectTypeKey == source.object_type_key
                and pair.toObjectTypeKey == target.object_type_key
            ),
            None,
        )
        if allowed is None:
            errors.append(
                {
                    "code": "invalid_relation_pair",
                    "message": "Relation is not permitted by the pinned model",
                }
            )
            continue
        try:
            _normalize_relation(model, relation.relation_type_key, source.object_type_key, target.object_type_key, dict(relation.attributes or {}))
        except ApiError as exc:
            errors.append({"code": exc.code, "message": exc.message, "details": {"relationId": relation.relation_id}})
        else:
            valid_relations.append((relation, allowed))
    for relation, allowed in valid_relations:
        if allowed.cardinality in {"one-to-one", "one-to-many", "many-to-one"}:
            same = [other for other, other_allowed in valid_relations if other_allowed.relationTypeKey == allowed.relationTypeKey and other.relation_id != relation.relation_id]
            if allowed.cardinality in {"one-to-one", "many-to-one"} and any(other.from_object_id == relation.from_object_id for other in same):
                errors.append({"code": "relation_cardinality_violation", "message": f"Relation '{allowed.relationTypeKey}' exceeds source cardinality", "details": {"relationId": relation.relation_id}})
            if allowed.cardinality in {"one-to-one", "one-to-many"} and any(other.to_object_id == relation.to_object_id for other in same):
                errors.append({"code": "relation_cardinality_violation", "message": f"Relation '{allowed.relationTypeKey}' exceeds target cardinality", "details": {"relationId": relation.relation_id}})
    for pair in model.objectTypeRelations:
        if pair.required:
            for source in (x for x in membership.objects if x.object_type_key == pair.fromObjectTypeKey):
                if not any(a.relationTypeKey == pair.relationTypeKey and r.from_object_id == source.object_id for r, a in valid_relations):
                    errors.append({"code": "missing_required_relation", "message": f"Required relationship '{pair.relationTypeKey}' is missing for object '{source.object_id}'", "details": {"objectId": source.object_id, "relationTypeKey": pair.relationTypeKey}})
    return errors


def _validate_application_diagnostic(errors: list[dict[str, Any]], model: Any, item: Any) -> None:
    application = next((x for x in model.applications if x.key == item.application_key), None)
    if application is None or item.object_type_key not in application.objectTypeKeys:
        errors.append({"code": "object_type_not_in_application", "message": f"Object type '{item.object_type_key}' is not enabled in application '{item.application_key}'", "details": {"objectId": item.object_id}})


def _parent_pair_exists(model: Any, child: Any, parent: Any, relations: list[Any]) -> bool:
    keys = set(model.object_type(child.object_type_key).behavior.get("parentRelationTypeKeys", [])) if model.object_type(child.object_type_key) else set()
    return not keys or any(r.from_object_id == parent.object_id and r.to_object_id == child.object_id and r.relation_type_key in keys for r in relations)


def validate_draft(
    session: Session, draft_id: str, model: Any, active_release_id: int
) -> list[dict[str, Any]]:
    draft = _draft(session, draft_id)
    if draft.model_release_id != active_release_id:
        return [
            {
                "code": "workspace_draft_model_release_conflict",
                "message": "Draft is pinned to a different application-model release",
            }
        ]
    return _diagnostics(effective_draft_membership(session, draft_id), model)


def pinned_model(session: Session, draft_id: str) -> tuple[WorkspaceDraft, Any]:
    draft = _draft(session, draft_id)
    release = session.get(ModelRelease, draft.model_release_id)
    if release is None:
        raise api_error(
            409,
            "workspace_draft_model_release_conflict",
            "Draft model release is no longer installed",
        )
    try:
        return draft, parse_model(release.model_json)
    except Exception as exc:
        raise api_error(
            409, "workspace_draft_model_release_conflict", "Draft model release cannot be compiled"
        ) from exc


def activate_draft(
    session: Session,
    draft_id: str,
    model: Any,
    active_release_id: int,
    expected_draft_version: int,
    expected_active_revision_id: str | None,
) -> WorkspaceRevision:
    draft = _draft(session, draft_id, for_update=True)
    if draft.model_release_id != active_release_id:
        raise api_error(
            409,
            "workspace_draft_model_release_conflict",
            "Draft is pinned to a different application-model release",
        )
    if draft.version != expected_draft_version:
        raise api_error(
            409, "workspace_draft_version_conflict", "Workspace draft version has changed"
        )
    workspace = session.scalar(
        select(Workspace).where(Workspace.key == draft.workspace_key).with_for_update()
    )
    if workspace is None:
        raise api_error(404, "workspace_not_found", "Workspace not found")
    if workspace.active_revision_id != expected_active_revision_id:
        raise api_error(
            409, "workspace_active_revision_conflict", "Active workspace revision has changed"
        )
    diagnostics = validate_draft(session, draft_id, model, active_release_id)
    if diagnostics:
        raise api_error(
            422,
            "workspace_graph_invalid",
            "Workspace draft failed complete graph validation",
            diagnostics,
        )
    membership = effective_draft_membership(session, draft_id)
    number = (
        session.scalar(
            select(WorkspaceRevision.revision_number)
            .where(WorkspaceRevision.workspace_key == draft.workspace_key)
            .order_by(WorkspaceRevision.revision_number.desc())
            .limit(1)
        )
        or 0
    ) + 1
    revision = WorkspaceRevision(
        workspace_key=draft.workspace_key,
        model_release_id=draft.model_release_id,
        revision_number=number,
        status="active",
        derived_from_revision_id=draft.derived_from_revision_id,
        supersedes_revision_id=workspace.active_revision_id,
    )
    session.add(revision)
    session.flush()
    for item in membership.objects:
        session.add(
            WorkspaceRevisionObject(
                revision_id=revision.id,
                object_id=item.object_id,
                application_key=item.application_key,
                object_type_key=item.object_type_key,
                name=item.name,
                parent_object_id=item.parent_object_id,
                attributes=item.attributes,
                version=item.version,
            )
        )
    for item in membership.relations:
        session.add(
            WorkspaceRevisionRelation(
                revision_id=revision.id,
                relation_id=item.relation_id,
                relation_type_key=item.relation_type_key,
                from_object_id=item.from_object_id,
                to_object_id=item.to_object_id,
                attributes=item.attributes,
                version=item.version,
            )
        )
    # Rebuild the active projection in the same transaction as the pointer switch.
    existing_ids = set(
        session.scalars(select(RdmObject.id).where(RdmObject.workspace_key == draft.workspace_key))
    )
    if existing_ids:
        session.execute(
            delete(ObjectRelation).where(
                ObjectRelation.from_object_id.in_(existing_ids)
                | ObjectRelation.to_object_id.in_(existing_ids)
            )
        )
        # Clear self-references before removing projection rows absent from the candidate.  The
        # revision snapshot remains the authoritative immutable record if this transaction fails.
        candidate_ids = {item.object_id for item in membership.objects}
        removed_ids = existing_ids - candidate_ids
        if removed_ids:
            session.query(RdmObject).filter(RdmObject.id.in_(removed_ids)).update({RdmObject.parent_object_id: None}, synchronize_session=False)
            session.execute(delete(RdmObject).where(RdmObject.id.in_(removed_ids)))
    for item in membership.objects:
        current = session.get(RdmObject, item.object_id)
        if current is None:
            current = RdmObject(
                id=item.object_id,
                workspace_key=draft.workspace_key,
                application_key=item.application_key,
                object_type_key=item.object_type_key,
                name=item.name,
                parent_object_id=item.parent_object_id,
                version=item.version,
            )
            session.add(current)
        else:
            current.workspace_key = draft.workspace_key
            current.application_key = item.application_key
            current.object_type_key = item.object_type_key
            current.name = item.name
            current.parent_object_id = item.parent_object_id
            current.version = item.version
        session.flush()
        attribute_delete = delete(AttributeValue).where(AttributeValue.object_id == current.id)
        if item.attributes:
            attribute_delete = attribute_delete.where(
                ~AttributeValue.attribute_type_key.in_(set(item.attributes))
            )
        session.execute(attribute_delete)
        save_attribute_values(session, model, current.id, item.attributes or {})
    for item in membership.relations:
        session.add(
            ObjectRelation(
                id=item.relation_id,
                relation_type_key=item.relation_type_key,
                from_object_id=item.from_object_id,
                to_object_id=item.to_object_id,
                attributes=item.attributes or {},
                version=item.version,
            )
        )
    if workspace.active_revision_id:
        old = session.scalar(
            select(WorkspaceRevision).where(WorkspaceRevision.id == workspace.active_revision_id)
        )
        old.status = "retired"
        old.retired_at = datetime.now(UTC)
    revision.activated_at = datetime.now(UTC)
    workspace.active_revision_id = revision.id
    session.delete(draft)
    session.commit()
    return revision


def retire_publication(
    session: Session, workspace_key: str, expected_active_revision_id: str
) -> None:
    workspace = session.scalar(
        select(Workspace).where(Workspace.key == workspace_key).with_for_update()
    )
    if workspace is None:
        raise api_error(404, "workspace_not_found", "Workspace not found")
    if workspace.active_revision_id != expected_active_revision_id:
        raise api_error(
            409, "workspace_active_revision_conflict", "Active workspace revision has changed"
        )
    revision = session.scalar(
        select(WorkspaceRevision).where(WorkspaceRevision.id == expected_active_revision_id)
    )
    if revision is None:
        raise api_error(404, "workspace_revision_not_found", "Workspace revision not found")
    revision.status = "retired"
    revision.retired_at = datetime.now(UTC)
    workspace.active_revision_id = None
    session.commit()
