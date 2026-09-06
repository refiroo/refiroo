from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from fastapi.encoders import jsonable_encoder
from sqlalchemy import delete, func, or_, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..errors import api_error
from ..models.api import (
    AttributeInput,
    InitialRelationInput,
    ObjectDraftActivationRequest,
    ObjectDraftCreate,
    ObjectDraftResponse,
    ObjectDraftUpdate,
    ObjectRetirementImpactResponse,
    ObjectRetirementResponse,
    ObjectRevisionResponse,
    RequiredRelationshipOutput,
    RetirementImpactObject,
)
from ..models.database import (
    AttributeValue,
    ModelRelease,
    ModelRuntimeState,
    ObjectDraft,
    ObjectRelation,
    ObjectRevision,
    RdmObject,
)
from ..models.schema import EngineModel, ObjectTypeDefinition
from .attributes import (
    check_attribute_uniqueness,
    current_attribute_values,
    save_attribute_values,
    validate_attributes,
    validate_object_attribute_rules,
)
from .audit import record_audit_event
from .model.compiler import parse_model
from .model.diagnostics import ModelValidationError
from .objects import (
    attributes_to_dict,
    get_object_type,
    load_object,
    validate_application_object_type,
    validate_parent,
)
from .relations import find_allowed_relation, validate_relation_attributes
from .workspaces import resolve_workspace


def create_root_draft(
    session: Session,
    model: EngineModel,
    *,
    model_release_db_id: int,
    payload: ObjectDraftCreate,
    commit: bool = True,
) -> ObjectDraft:
    workspace = resolve_workspace(session, payload.workspaceKey, require_active=True)
    object_type = get_object_type(model, payload.objectTypeKey)
    validate_application_object_type(model, payload.applicationKey, payload.objectTypeKey)
    object_id = str(payload.objectId) if payload.objectId is not None else str(uuid4())
    if session.scalar(select(RdmObject.id).where(RdmObject.id == object_id)):
        raise api_error(
            409, "object_already_exists", f"An object with ID '{object_id}' already exists"
        )
    attributes = validate_attributes(
        model, object_type, attributes_to_dict(payload.attributes)
    )
    relationships = _relationship_dicts(payload.requiredRelationships)
    parent_id = str(payload.parentObjectId) if payload.parentObjectId is not None else None
    _validate_snapshot(
        session,
        model,
        object_type=object_type,
        application_key=payload.applicationKey,
        workspace_key=workspace.key,
        object_id=object_id,
        name=payload.name,
        parent_object_id=parent_id,
        attributes=attributes,
        relationships=relationships,
    )
    item = RdmObject(
        workspace_key=workspace.key,
        application_key=payload.applicationKey,
        object_type_key=payload.objectTypeKey,
        parent_object_id=None,
        state="draft",
        name=payload.name,
        version=0,
    )
    item.id = object_id
    session.add(item)
    try:
        session.flush()
    except IntegrityError as exc:
        session.rollback()
        raise api_error(
            409,
            "object_already_exists",
            f"An object with ID '{object_id}' already exists",
        ) from exc
    draft = ObjectDraft(
        object_id=item.id,
        model_release_id=model_release_db_id,
        name=payload.name,
        parent_object_id=parent_id,
        attributes=jsonable_encoder(attributes),
        required_relations=relationships,
    )
    session.add(draft)
    session.flush()
    record_audit_event(
        session,
        aggregate_type="object-draft",
        aggregate_id=draft.id,
        action="created",
        version=draft.version,
        changes={"objectId": item.id, "derivedFromRevisionId": None},
        object_ids=[item.id],
    )
    if commit:
        session.commit()
    return draft


def effective_model_release_id(session: Session, requested_id: int) -> int:
    """Resolve synthetic dependency-override snapshots to the selected persisted release."""
    if requested_id > 0:
        if session.scalar(select(ModelRelease.id).where(ModelRelease.id == requested_id)):
            return requested_id
        raise api_error(
            500,
            "invalid_model_release",
            f"Model release database ID '{requested_id}' does not exist",
        )
    selected = session.scalar(
        select(ModelRuntimeState.active_model_release_id).where(ModelRuntimeState.id == 1)
    )
    if selected is None:
        raise api_error(503, "model_registry_unavailable", "No active model release is selected")
    return selected


def clone_revision_to_draft(
    session: Session,
    model: EngineModel,
    *,
    model_release_db_id: int,
    object_type_key: str,
    object_id: str,
    derived_from_revision_id: str,
    commit: bool = True,
) -> ObjectDraft:
    item = load_identity(session, object_id, object_type_key)
    resolve_workspace(session, item.workspace_key, require_active=True)
    revision = load_revision(session, derived_from_revision_id)
    if revision.object_id != item.id:
        raise api_error(
            422,
            "revision_wrong_object",
            "The selected revision does not belong to this logical object",
        )
    object_type = get_object_type(model, item.object_type_key)
    _validate_snapshot(
        session,
        model,
        object_type=object_type,
        application_key=item.application_key,
        workspace_key=item.workspace_key,
        object_id=item.id,
        name=revision.name,
        parent_object_id=revision.parent_object_id,
        attributes=revision.attributes,
        relationships=revision.required_relations,
    )
    draft = ObjectDraft(
        object_id=item.id,
        model_release_id=model_release_db_id,
        derived_from_revision_id=revision.id,
        name=revision.name,
        parent_object_id=revision.parent_object_id,
        attributes=revision.attributes,
        required_relations=revision.required_relations,
    )
    session.add(draft)
    session.flush()
    record_audit_event(
        session,
        aggregate_type="object-draft",
        aggregate_id=draft.id,
        action="created",
        version=1,
        changes={"objectId": item.id, "derivedFromRevisionId": revision.id},
        object_ids=[item.id],
    )
    if commit:
        session.commit()
    return draft


def update_draft(
    session: Session,
    model: EngineModel,
    draft_id: str,
    payload: ObjectDraftUpdate,
    *,
    commit: bool = True,
) -> ObjectDraft:
    draft = load_draft(session, draft_id)
    item = load_identity(session, draft.object_id)
    resolve_workspace(session, item.workspace_key, require_active=True)
    model = _pinned_draft_model(session, draft)
    if draft.version != payload.expectedVersion:
        _draft_conflict(draft)

    name = payload.name if payload.name is not None else draft.name
    parent_id = draft.parent_object_id
    if "parentObjectId" in payload.model_fields_set:
        parent_id = str(payload.parentObjectId) if payload.parentObjectId is not None else None
    attributes = draft.attributes
    if payload.attributes is not None:
        attributes = attributes_to_dict(payload.attributes)
        read_only_keys = {
            binding.attributeTypeKey
            for binding in get_object_type(model, item.object_type_key).attributes
            if binding.readOnly
        }
        changed_read_only = sorted(
            key
            for key in read_only_keys
            if attributes.get(key) != draft.attributes.get(key)
            or (key in attributes) != (key in draft.attributes)
        )
        if changed_read_only:
            raise api_error(
                422,
                "read_only_attributes",
                f"Read-only attributes: {changed_read_only}",
            )
    relationships = draft.required_relations
    if payload.requiredRelationships is not None:
        relationships = _relationship_dicts(payload.requiredRelationships)
    object_type = get_object_type(model, item.object_type_key)
    normalized_attributes = _validate_snapshot(
        session,
        model,
        object_type=object_type,
        application_key=item.application_key,
        workspace_key=item.workspace_key,
        object_id=item.id,
        name=name,
        parent_object_id=parent_id,
        attributes=attributes,
        relationships=relationships,
    )
    result = session.execute(
        update(ObjectDraft)
        .where(ObjectDraft.id == draft.id, ObjectDraft.version == payload.expectedVersion)
        .values(
            name=name,
            parent_object_id=parent_id,
            attributes=jsonable_encoder(normalized_attributes),
            required_relations=relationships,
            version=payload.expectedVersion + 1,
            updated_at=datetime.now(UTC),
        )
        .execution_options(synchronize_session=False)
    )
    if result.rowcount != 1:
        session.rollback()
        current = load_draft(session, draft_id)
        _draft_conflict(current)
    session.refresh(draft)
    record_audit_event(
        session,
        aggregate_type="object-draft",
        aggregate_id=draft.id,
        action="updated",
        version=draft.version,
        changes={"fields": sorted(payload.model_fields_set - {"expectedVersion"})},
        object_ids=[item.id],
    )
    if commit:
        session.commit()
    return draft


def discard_draft(session: Session, draft_id: str, expected_version: int) -> None:
    draft = load_draft(session, draft_id)
    item = load_identity(session, draft.object_id)
    resolve_workspace(session, item.workspace_key, require_active=True)
    if draft.version != expected_version:
        _draft_conflict(draft)
    object_id = draft.object_id
    record_audit_event(
        session,
        aggregate_type="object-draft",
        aggregate_id=draft.id,
        action="discarded",
        version=draft.version,
        changes={"objectId": object_id},
        object_ids=[object_id],
    )
    result = session.execute(
        delete(ObjectDraft).where(
            ObjectDraft.id == draft.id, ObjectDraft.version == expected_version
        )
    )
    if result.rowcount != 1:
        session.rollback()
        _draft_conflict(load_draft(session, draft_id))
    has_revision = session.scalar(
        select(ObjectRevision.sequence_id).where(ObjectRevision.object_id == object_id).limit(1)
    )
    has_draft = session.scalar(
        select(ObjectDraft.sequence_id).where(ObjectDraft.object_id == object_id).limit(1)
    )
    if not has_revision and not has_draft:
        session.delete(item)
    session.commit()


def activate_draft(
    session: Session,
    model: EngineModel,
    *,
    current_model_release_db_id: int,
    draft_id: str,
    payload: ObjectDraftActivationRequest,
) -> ObjectRevision:
    draft = load_draft(session, draft_id)
    item = load_identity(session, draft.object_id)
    resolve_workspace(session, item.workspace_key, require_active=True)
    if draft.version != payload.expectedDraftVersion:
        _draft_conflict(draft)
    expected_active_id = (
        str(payload.expectedActiveRevisionId)
        if payload.expectedActiveRevisionId is not None
        else None
    )
    if item.active_revision_id != expected_active_id:
        raise api_error(
            409,
            "active_revision_conflict",
            "The logical object's active revision has changed",
            {
                "expectedActiveRevisionId": expected_active_id,
                "currentActiveRevisionId": item.active_revision_id,
            },
        )
    if draft.model_release_id != current_model_release_db_id:
        raise api_error(
            409,
            "draft_model_release_conflict",
            "The draft is pinned to a different model release",
            {
                "draftModelReleaseId": _release_public_id(session, draft.model_release_id),
                "currentModelReleaseId": _release_public_id(
                    session, current_model_release_db_id
                ),
            },
        )
    object_type = get_object_type(model, item.object_type_key)
    normalized_attributes = _validate_snapshot(
        session,
        model,
        object_type=object_type,
        application_key=item.application_key,
        workspace_key=item.workspace_key,
        object_id=item.id,
        name=draft.name,
        parent_object_id=draft.parent_object_id,
        attributes=draft.attributes,
        relationships=draft.required_relations,
    )
    now = datetime.now(UTC)
    next_number = (
        session.scalar(
            select(func.max(ObjectRevision.revision_number)).where(
                ObjectRevision.object_id == item.id
            )
        )
        or 0
    ) + 1
    revision = ObjectRevision(
        object_id=item.id,
        model_release_id=draft.model_release_id,
        revision_number=next_number,
        status="active",
        derived_from_revision_id=draft.derived_from_revision_id,
        supersedes_revision_id=expected_active_id,
        name=draft.name,
        parent_object_id=draft.parent_object_id,
        attributes=jsonable_encoder(normalized_attributes),
        required_relations=draft.required_relations,
        created_at=draft.created_at,
        activated_at=now,
    )
    session.add(revision)
    session.flush()
    active_clause = (
        RdmObject.active_revision_id.is_(None)
        if expected_active_id is None
        else RdmObject.active_revision_id == expected_active_id
    )
    claimed = session.execute(
        update(RdmObject)
        .where(RdmObject.id == item.id, active_clause)
        .values(
            active_revision_id=revision.id,
            parent_object_id=draft.parent_object_id,
            state="active",
            name=draft.name,
            version=RdmObject.version + 1,
            updated_at=now,
        )
        .execution_options(synchronize_session=False)
    )
    if claimed.rowcount != 1:
        session.rollback()
        current = load_identity(session, item.id)
        raise api_error(
            409,
            "active_revision_conflict",
            "The logical object's active revision has changed",
            {"currentActiveRevisionId": current.active_revision_id},
        )
    if expected_active_id:
        retired = session.execute(
            update(ObjectRevision)
            .where(
                ObjectRevision.id == expected_active_id,
                ObjectRevision.status == "active",
            )
            .values(status="retired", retired_at=now)
        )
        if retired.rowcount != 1:
            session.rollback()
            raise api_error(
                409,
                "active_revision_conflict",
                "The logical object's active revision has changed",
            )
    _replace_owned_projection(
        session,
        model,
        item=item,
        attributes=normalized_attributes,
        parent_object_id=draft.parent_object_id,
        relationships=draft.required_relations,
    )
    record_audit_event(
        session,
        aggregate_type="object-revision",
        aggregate_id=revision.id,
        action="activated",
        version=revision.revision_number,
        changes={
            "objectId": item.id,
            "derivedFromRevisionId": revision.derived_from_revision_id,
            "supersedesRevisionId": revision.supersedes_revision_id,
            "modelReleaseId": _release_public_id(session, revision.model_release_id),
        },
        object_ids=[item.id],
    )
    deleted_draft = session.execute(
        delete(ObjectDraft)
        .where(
            ObjectDraft.id == draft.id,
            ObjectDraft.version == payload.expectedDraftVersion,
        )
        .execution_options(synchronize_session=False)
    )
    if deleted_draft.rowcount != 1:
        session.rollback()
        current_version = session.scalar(
            select(ObjectDraft.version).where(ObjectDraft.id == draft_id)
        )
        raise api_error(
            409,
            "draft_version_conflict",
            "Object draft changed or was discarded during activation",
            {"currentVersion": current_version},
        )
    try:
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        raise api_error(
            409, "activation_conflict", "The draft could not be activated atomically"
        ) from exc
    session.refresh(item)
    session.refresh(revision)
    return revision


def retire_active_revision(
    session: Session,
    model: EngineModel,
    *,
    object_type_key: str,
    object_id: str,
    expected_active_revision_id: str,
    cascade: bool,
) -> ObjectRetirementResponse:
    root = load_active_object(session, object_id, object_type_key)
    resolve_workspace(session, root.workspace_key, require_active=True)
    if root.active_revision_id != expected_active_revision_id:
        raise api_error(
            409,
            "active_revision_conflict",
            "The logical object's active revision has changed",
            {"currentActiveRevisionId": root.active_revision_id},
        )
    planned, reasons = _retirement_dependants(session, model, root)
    if len(planned) > 1 and not cascade:
        retained_associations = _retained_association_count(
            session, model, set(planned)
        )
        raise api_error(
            409,
            "object_has_dependants",
            "Retiring this object requires dependant confirmation",
            {
                "rootObjectId": root.id,
                "objectsToRetire": [
                    _impact(item, reasons[item.id]).model_dump()
                    for item in planned.values()
                    if item.id != root.id
                ],
                "objectCount": len(planned),
                "retainedAssociationCount": retained_associations,
            },
        )
    now = datetime.now(UTC)
    retired_revisions: dict[str, ObjectRevision] = {}
    for item in planned.values():
        revision = load_revision(session, item.active_revision_id or "")
        claimed = session.execute(
            update(RdmObject)
            .where(
                RdmObject.id == item.id,
                RdmObject.active_revision_id == revision.id,
            )
            .values(
                active_revision_id=None,
                parent_object_id=None,
                state="retired",
                version=RdmObject.version + 1,
                updated_at=now,
            )
            .execution_options(synchronize_session=False)
        )
        if claimed.rowcount != 1:
            session.rollback()
            raise api_error(
                409,
                "active_revision_conflict",
                "A dependant's active revision changed during retirement",
                {"objectId": item.id},
            )
        revision.status = "retired"
        revision.retired_at = now
        retired_revisions[item.id] = revision
        record_audit_event(
            session,
            aggregate_type="object-revision",
            aggregate_id=revision.id,
            action="retired",
            version=revision.revision_number,
            changes={"objectId": item.id, "cascadeRootObjectId": root.id},
            object_ids=[item.id],
        )
    retained_associations = _remove_owned_projection_relations(
        session, model, set(planned)
    )
    session.commit()
    root_revision = retired_revisions[root.id]
    return ObjectRetirementResponse(
        retiredRevision=revision_response(session, root_revision),
        retiredDependants=[
            _impact(item, reasons[item.id])
            for item in planned.values()
            if item.id != root.id
        ],
        retainedAssociationCount=retained_associations,
    )


def retirement_impact(
    session: Session,
    model: EngineModel,
    *,
    object_type_key: str,
    object_id: str,
    expected_active_revision_id: str,
) -> ObjectRetirementImpactResponse:
    root = load_active_object(session, object_id, object_type_key)
    if root.active_revision_id != expected_active_revision_id:
        raise api_error(
            409,
            "active_revision_conflict",
            "The logical object's active revision has changed",
            {"currentActiveRevisionId": root.active_revision_id},
        )
    planned, reasons = _retirement_dependants(session, model, root)
    dependants = [
        _impact(item, reasons[item.id])
        for item in planned.values()
        if item.id != root.id
    ]
    return ObjectRetirementImpactResponse(
        activeRevisionId=expected_active_revision_id,
        dependants=dependants,
        retainedAssociationCount=_retained_association_count(
            session, model, set(planned)
        ),
        cascadeRequired=bool(dependants),
    )


def load_identity(
    session: Session, object_id: str, object_type_key: str | None = None
) -> RdmObject:
    return load_object(session, object_id, object_type_key)


def load_active_object(
    session: Session, object_id: str, object_type_key: str | None = None
) -> RdmObject:
    item = load_identity(session, object_id, object_type_key)
    if item.active_revision_id is None:
        raise api_error(404, "object_not_found", f"Active object '{object_id}' not found")
    return item


def load_draft(session: Session, draft_id: str) -> ObjectDraft:
    draft = session.scalar(select(ObjectDraft).where(ObjectDraft.id == draft_id))
    if draft is None:
        raise api_error(404, "object_draft_not_found", f"Object draft '{draft_id}' not found")
    return draft


def load_revision(session: Session, revision_id: str) -> ObjectRevision:
    revision = session.scalar(select(ObjectRevision).where(ObjectRevision.id == revision_id))
    if revision is None:
        raise api_error(
            404, "object_revision_not_found", f"Object revision '{revision_id}' not found"
        )
    return revision


def draft_response(session: Session, draft: ObjectDraft) -> ObjectDraftResponse:
    item = load_identity(session, draft.object_id)
    return ObjectDraftResponse(
        id=draft.id,
        objectId=item.id,
        workspaceKey=item.workspace_key,
        applicationKey=item.application_key,
        objectTypeKey=item.object_type_key,
        modelReleaseId=_release_public_id(session, draft.model_release_id),
        derivedFromRevisionId=draft.derived_from_revision_id,
        name=draft.name,
        parentObjectId=draft.parent_object_id,
        attributes=_attribute_inputs(draft.attributes),
        requiredRelationships=_relationship_outputs(draft.required_relations),
        version=draft.version,
        createdAt=draft.created_at,
        updatedAt=draft.updated_at,
    )


def revision_response(
    session: Session, revision: ObjectRevision
) -> ObjectRevisionResponse:
    item = load_identity(session, revision.object_id)
    return ObjectRevisionResponse(
        id=revision.id,
        objectId=item.id,
        workspaceKey=item.workspace_key,
        applicationKey=item.application_key,
        objectTypeKey=item.object_type_key,
        modelReleaseId=_release_public_id(session, revision.model_release_id),
        revisionNumber=revision.revision_number,
        lifecycle=revision.status,
        derivedFromRevisionId=revision.derived_from_revision_id,
        supersedesRevisionId=revision.supersedes_revision_id,
        name=revision.name,
        parentObjectId=revision.parent_object_id,
        attributes=_attribute_inputs(revision.attributes),
        requiredRelationships=_relationship_outputs(revision.required_relations),
        createdAt=revision.created_at,
        activatedAt=revision.activated_at,
        retiredAt=revision.retired_at,
    )


def _validate_snapshot(
    session: Session,
    model: EngineModel,
    *,
    object_type: ObjectTypeDefinition,
    application_key: str,
    workspace_key: str,
    object_id: str | None,
    name: str,
    parent_object_id: str | None,
    attributes: dict[str, Any],
    relationships: list[dict[str, Any]],
) -> dict[str, Any]:
    if not name.strip():
        raise api_error(422, "invalid_object_name", "Object name must not be blank")
    normalized = validate_attributes(
        model,
        object_type,
        attributes,
        apply_defaults=False,
        allow_read_only=True,
    )
    validate_object_attribute_rules(object_type, normalized)
    check_attribute_uniqueness(
        session,
        model,
        normalized,
        workspace_key=workspace_key,
        exclude_object_id=object_id,
    )
    validate_parent(
        session,
        model,
        object_type.key,
        application_key,
        workspace_key,
        parent_object_id,
        moving_object_id=object_id,
    )
    _validate_required_relationships(
        session, model, object_type, workspace_key, object_id, relationships
    )
    _validate_snapshot_scoped_uniqueness(
        session,
        model,
        object_type=object_type,
        object_id=object_id,
        parent_object_id=parent_object_id,
        attributes=normalized,
        relationships=relationships,
    )
    return normalized


def _validate_required_relationships(
    session: Session,
    model: EngineModel,
    object_type: ObjectTypeDefinition,
    workspace_key: str,
    object_id: str | None,
    relationships: list[dict[str, Any]],
) -> None:
    parent_keys = set(object_type.behavior.get("parentRelationTypeKeys", []))
    required = {
        relation.relationTypeKey: relation
        for relation in model.objectTypeRelations
        if relation.toObjectTypeKey == object_type.key
        and relation.required
        and relation.relationTypeKey not in parent_keys
    }
    seen: set[str] = set()
    for relationship in relationships:
        key = relationship["relationTypeKey"]
        if key in seen:
            raise api_error(422, "duplicate_required_relation", f"Relationship '{key}' occurs more than once")
        seen.add(key)
        if relationship["direction"] != "incoming" or key not in required:
            raise api_error(
                422,
                "invalid_required_relation",
                f"Relationship '{key}' is not an object-owned required relationship",
            )
        other = load_active_object(session, relationship["otherObjectId"])
        if other.workspace_key != workspace_key:
            raise api_error(422, "relation_wrong_scope", "Related objects must share a workspace")
        allowed = find_allowed_relation(model, key, other.object_type_key, object_type.key)
        cardinality_conflict = ObjectRelation.relation_type_key == key
        if allowed.cardinality == "one-to-one":
            cardinality_conflict = or_(
                ObjectRelation.from_object_id == other.id,
                ObjectRelation.to_object_id == object_id,
            )
        elif allowed.cardinality == "one-to-many":
            cardinality_conflict = ObjectRelation.to_object_id == object_id
        else:
            cardinality_conflict = None
        if cardinality_conflict is not None:
            existing = session.scalar(
                select(ObjectRelation.id)
                .where(
                    ObjectRelation.relation_type_key == key,
                    cardinality_conflict,
                    or_(
                        ObjectRelation.from_object_id != other.id,
                        ObjectRelation.to_object_id != object_id,
                    ),
                )
                .limit(1)
            )
            if existing:
                raise api_error(
                    409,
                    "cardinality_violation",
                    "Required relationship cardinality would be violated",
                )
        relationship["attributes"] = validate_relation_attributes(
            model, allowed, relationship.get("attributes", {})
        )
    missing = sorted(set(required) - seen)
    if missing:
        raise api_error(
            422,
            "missing_required_relations",
            f"Required relationships missing: {missing}",
            {"relationTypeKeys": missing},
        )


def _validate_snapshot_scoped_uniqueness(
    session: Session,
    model: EngineModel,
    *,
    object_type: ObjectTypeDefinition,
    object_id: str | None,
    parent_object_id: str | None,
    attributes: dict[str, Any],
    relationships: list[dict[str, Any]],
) -> None:
    for relationship in relationships:
        source = load_active_object(session, relationship["otherObjectId"])
        allowed = find_allowed_relation(
            model,
            relationship["relationTypeKey"],
            source.object_type_key,
            object_type.key,
        )
        ancestor_type_key = allowed.features.get("uniqueToAncestorTypeKey")
        if not ancestor_type_key:
            continue
        condition = allowed.features.get("uniqueWhenToAttributeEquals")
        if condition and attributes.get(condition["attributeTypeKey"]) != condition["value"]:
            continue
        candidate_ancestor = _snapshot_ancestor_id(
            session,
            object_type_key=object_type.key,
            object_id=object_id,
            parent_object_id=parent_object_id,
            ancestor_type_key=ancestor_type_key,
        )
        if candidate_ancestor is None:
            raise api_error(
                422,
                "relation_ancestor_required",
                f"Related object must belong to an ancestor of type '{ancestor_type_key}'",
            )
        existing_target_ids = session.scalars(
            select(ObjectRelation.to_object_id).where(
                ObjectRelation.relation_type_key == relationship["relationTypeKey"],
                ObjectRelation.from_object_id == source.id,
                ObjectRelation.to_object_id != object_id,
            )
        )
        for target_id in existing_target_ids:
            target = load_identity(session, target_id)
            if target.active_revision_id is None:
                continue
            if condition and current_attribute_values(session, target.id).get(
                condition["attributeTypeKey"]
            ) != condition["value"]:
                continue
            if (
                _snapshot_ancestor_id(
                    session,
                    object_type_key=target.object_type_key,
                    object_id=target.id,
                    parent_object_id=target.parent_object_id,
                    ancestor_type_key=ancestor_type_key,
                )
                == candidate_ancestor
            ):
                raise api_error(
                    409,
                    "duplicate_relation_scope",
                    "A related object already exists for this ancestor scope",
                    {
                        "ancestorObjectTypeKey": ancestor_type_key,
                        "ancestorObjectId": candidate_ancestor,
                        "conflictingObjectId": target.id,
                    },
                )


def _snapshot_ancestor_id(
    session: Session,
    *,
    object_type_key: str,
    object_id: str | None,
    parent_object_id: str | None,
    ancestor_type_key: str,
) -> str | None:
    if object_type_key == ancestor_type_key:
        return object_id
    current_id = parent_object_id
    visited: set[str] = set()
    while current_id and current_id not in visited:
        visited.add(current_id)
        current = load_active_object(session, current_id)
        if current.object_type_key == ancestor_type_key:
            return current.id
        current_id = current.parent_object_id
    return None


def _replace_owned_projection(
    session: Session,
    model: EngineModel,
    *,
    item: RdmObject,
    attributes: dict[str, Any],
    parent_object_id: str | None,
    relationships: list[dict[str, Any]],
) -> None:
    session.execute(delete(AttributeValue).where(AttributeValue.object_id == item.id))
    save_attribute_values(session, model, item.id, attributes)
    _delete_owned_relations_for_object(session, model, item)
    if parent_object_id:
        parent, relation_key = validate_parent(
            session,
            model,
            item.object_type_key,
            item.application_key,
            item.workspace_key,
            parent_object_id,
            moving_object_id=item.id,
        )
        if parent and relation_key:
            session.add(
                ObjectRelation(
                    relation_type_key=relation_key,
                    from_object_id=parent.id,
                    to_object_id=item.id,
                )
            )
    for relationship in relationships:
        session.add(
            ObjectRelation(
                relation_type_key=relationship["relationTypeKey"],
                from_object_id=relationship["otherObjectId"],
                to_object_id=item.id,
                attributes=relationship.get("attributes", {}),
            )
        )


def _delete_owned_relations_for_object(
    session: Session, model: EngineModel, item: RdmObject
) -> None:
    relations = list(
        session.scalars(select(ObjectRelation).where(ObjectRelation.to_object_id == item.id))
    )
    for relation in relations:
        source = load_identity(session, relation.from_object_id)
        allowed = find_allowed_relation(
            model,
            relation.relation_type_key,
            source.object_type_key,
            item.object_type_key,
        )
        parent_keys = set(
            get_object_type(model, item.object_type_key).behavior.get(
                "parentRelationTypeKeys", []
            )
        )
        if allowed.required or relation.relation_type_key in parent_keys:
            session.delete(relation)


def _retirement_dependants(
    session: Session, model: EngineModel, root: RdmObject
) -> tuple[dict[str, RdmObject], dict[str, str]]:
    planned = {root.id: root}
    reasons = {root.id: "root"}
    pending = [root]
    while pending:
        current = pending.pop()
        children = session.scalars(
            select(RdmObject).where(
                RdmObject.parent_object_id == current.id,
                RdmObject.active_revision_id.is_not(None),
            )
        )
        for child in children:
            if child.workspace_key != root.workspace_key:
                raise api_error(
                    409,
                    "invalid_runtime_scope",
                    "Retirement stopped because a containment edge crosses workspace boundaries",
                    {"fromObjectId": current.id, "toObjectId": child.id},
                )
            if child.id not in planned:
                planned[child.id] = child
                reasons[child.id] = "containment"
                pending.append(child)
        outgoing = session.scalars(
            select(ObjectRelation).where(ObjectRelation.from_object_id == current.id)
        )
        for relation in outgoing:
            target = load_identity(session, relation.to_object_id)
            if target.active_revision_id is None:
                continue
            if target.workspace_key != root.workspace_key:
                raise api_error(
                    409,
                    "invalid_runtime_scope",
                    "Retirement stopped because a relationship crosses workspace boundaries",
                    {
                        "relationId": relation.id,
                        "fromObjectId": current.id,
                        "toObjectId": target.id,
                    },
                )
            allowed = find_allowed_relation(
                model,
                relation.relation_type_key,
                current.object_type_key,
                target.object_type_key,
            )
            if (
                allowed.required
                and allowed.cardinality in {"one-to-one", "one-to-many"}
                and target.id not in planned
            ):
                planned[target.id] = target
                reasons[target.id] = "required-ownership"
                pending.append(target)
    return planned, reasons


def _remove_owned_projection_relations(
    session: Session, model: EngineModel, object_ids: set[str]
) -> int:
    relations = list(
        session.scalars(
            select(ObjectRelation).where(
                or_(
                    ObjectRelation.from_object_id.in_(object_ids),
                    ObjectRelation.to_object_id.in_(object_ids),
                )
            )
        )
    )
    retained = 0
    for relation in relations:
        source = load_identity(session, relation.from_object_id)
        target = load_identity(session, relation.to_object_id)
        allowed = find_allowed_relation(
            model,
            relation.relation_type_key,
            source.object_type_key,
            target.object_type_key,
        )
        parent_keys = set(
            get_object_type(model, target.object_type_key).behavior.get(
                "parentRelationTypeKeys", []
            )
        )
        if allowed.required or relation.relation_type_key in parent_keys:
            session.delete(relation)
        else:
            retained += 1
    return retained


def _retained_association_count(
    session: Session, model: EngineModel, object_ids: set[str]
) -> int:
    relations = session.scalars(
        select(ObjectRelation).where(
            or_(
                ObjectRelation.from_object_id.in_(object_ids),
                ObjectRelation.to_object_id.in_(object_ids),
            )
        )
    )
    retained = 0
    for relation in relations:
        source = load_identity(session, relation.from_object_id)
        target = load_identity(session, relation.to_object_id)
        allowed = find_allowed_relation(
            model,
            relation.relation_type_key,
            source.object_type_key,
            target.object_type_key,
        )
        parent_keys = set(
            get_object_type(model, target.object_type_key).behavior.get(
                "parentRelationTypeKeys", []
            )
        )
        if not allowed.required and relation.relation_type_key not in parent_keys:
            retained += 1
    return retained


def _relationship_dicts(
    relationships: list[InitialRelationInput],
) -> list[dict[str, Any]]:
    return [
        {
            "relationTypeKey": relationship.relationTypeKey,
            "direction": relationship.direction,
            "otherObjectId": str(relationship.otherObjectId),
            "attributes": jsonable_encoder(relationship.attributes),
        }
        for relationship in relationships
    ]


def _relationship_outputs(
    relationships: list[dict[str, Any]],
) -> list[RequiredRelationshipOutput]:
    return [RequiredRelationshipOutput.model_validate(relationship) for relationship in relationships]


def _attribute_inputs(attributes: dict[str, Any]) -> list[AttributeInput]:
    return [
        AttributeInput(attributeTypeKey=key, value=value)
        for key, value in attributes.items()
    ]


def _release_public_id(session: Session, release_db_id: int) -> str:
    public_id = session.scalar(
        select(ModelRelease.public_id).where(ModelRelease.id == release_db_id)
    )
    if public_id is None:
        raise api_error(500, "invalid_model_release", "Snapshot model release is missing")
    return public_id


def _pinned_draft_model(session: Session, draft: ObjectDraft) -> EngineModel:
    source = session.scalar(
        select(ModelRelease.model_json).where(ModelRelease.id == draft.model_release_id)
    )
    if source is None:
        raise api_error(500, "invalid_model_release", "Draft model release is missing")
    try:
        return parse_model(source)
    except ModelValidationError as exc:
        raise api_error(
            500,
            "invalid_installed_model",
            "The draft's pinned model release cannot be parsed",
        ) from exc


def _draft_conflict(draft: ObjectDraft) -> None:
    raise api_error(
        409,
        "draft_version_conflict",
        "Object draft version has changed",
        {"currentVersion": draft.version},
    )


def _impact(item: RdmObject, reason: str) -> RetirementImpactObject:
    return RetirementImpactObject(
        id=item.id,
        objectTypeKey=item.object_type_key,
        name=item.name,
        reason=reason,
    )
