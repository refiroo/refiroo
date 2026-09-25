"""WP8 workspace lifecycle orchestration over ADR-024 persistence.

WP8 owns the workspace-scoped draft / revision / validation / activation / retirement lifecycle on
top of the WP6 copy-on-write storage layout. Objects and relations are ordinary live records;
optional staged edits use the canonical routers with ``workspaceDraftId``. Activation merges authored
changes into live data and records an immutable revision snapshot (ADR-026/027).
"""

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from sqlalchemy import delete, or_, select, update
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from ..errors import ApiError, api_error
from ..models.database import (
    AttributeValue,
    ModelRelease,
    ModelRuntimeState,
    ObjectRelation,
    RdmObject,
    RelationSetVersion,
    Workspace,
    WorkspaceDraft,
    WorkspaceDraftBase,
    WorkspaceDraftBaseObject,
    WorkspaceDraftBaseRelation,
    WorkspaceDraftObject,
    WorkspaceDraftRelation,
    WorkspaceRevision,
    WorkspaceRevisionObject,
    WorkspaceRevisionRelation,
)
from .attributes import (
    load_attribute_values,
    save_attribute_values,
    stored_json_value,
    validate_attributes,
    validate_deletable_attribute,
    validate_object_attribute_rules,
)
from .audit import record_audit_event
from .model.registry import resolve_pinned_release
from .relation_set_versions import (
    delete_draft_set_versions,
    increment_set_versions,
    merge_draft_set_versions_to_live,
)
from .relations import validate_relation_attributes
from .snapshot_values import delete_owner_values
from .workspace_audit import (
    record_draft_created,
    record_draft_derived,
    record_draft_discarded,
    record_draft_renamed,
    record_publication_retired,
    record_revision_activated,
)


@dataclass(frozen=True)
class EffectiveDraftMembership:
    draft: WorkspaceDraft
    objects: tuple[WorkspaceRevisionObject | WorkspaceDraftBaseObject | WorkspaceDraftObject, ...]
    relations: tuple[
        WorkspaceRevisionRelation | WorkspaceDraftBaseRelation | WorkspaceDraftRelation, ...
    ]


def effective_draft_membership(session: Session, draft_id: str) -> EffectiveDraftMembership:
    """Resolve a draft's immutable base plus its changed rows and tombstones.

    A draft row replaces the same stable public ID from its base.  A tombstone hides that base row;
    therefore an edit does not copy unrelated records from the source revision.
    """
    draft = session.scalar(select(WorkspaceDraft).where(WorkspaceDraft.id == draft_id))
    if draft is None:
        raise api_error(404, "workspace_draft_not_found", f"Workspace draft '{draft_id}' not found")
    objects: dict[
        str, WorkspaceRevisionObject | WorkspaceDraftBaseObject | WorkspaceDraftObject
    ] = {}
    relations: dict[
        str, WorkspaceRevisionRelation | WorkspaceDraftBaseRelation | WorkspaceDraftRelation
    ] = {}
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
    if draft.base_id is not None:
        base = session.get(WorkspaceDraftBase, draft.base_id)
        if base is None or base.workspace_key != draft.workspace_key:
            raise api_error(
                409,
                "workspace_draft_base_invalid",
                "Workspace draft current-live base is missing or belongs to another workspace",
            )
        objects = {
            item.object_id: item
            for item in session.scalars(
                select(WorkspaceDraftBaseObject).where(WorkspaceDraftBaseObject.base_id == base.id)
            )
        }
        relations = {
            item.relation_id: item
            for item in session.scalars(
                select(WorkspaceDraftBaseRelation).where(
                    WorkspaceDraftBaseRelation.base_id == base.id
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
            raise api_error(
                404, "workspace_not_found", f"Workspace '{item.workspace_key}' not found"
            )
        if workspace.status != "active":
            raise api_error(409, "workspace_retired", "Workspace is retired and cannot be mutated")
    return item


def ensure_draft_writable(session: Session, draft_id: str) -> WorkspaceDraft:
    """Resolve a draft and reject mutations against a retired workspace."""
    return _draft(session, draft_id, for_update=True)


def claim_draft_version(session: Session, draft: WorkspaceDraft, expected: int) -> None:
    """Claim the draft aggregate version for an external write operation."""
    _claim_draft(session, draft, expected)


def _claim_draft(
    session: Session,
    draft: WorkspaceDraft,
    expected: int,
    *,
    conflict_code: str = "workspace_draft_version_conflict",
    conflict_message: str = "Workspace draft version has changed",
) -> None:
    if draft.version != expected:
        raise api_error(409, conflict_code, conflict_message)
    # SQLite ignores FOR UPDATE; claim the aggregate in SQL before flushing candidate writes.
    with session.no_autoflush:
        result = session.execute(
            update(WorkspaceDraft)
            .where(WorkspaceDraft.id == draft.id, WorkspaceDraft.version == expected)
            .values(version=expected + 1, updated_at=datetime.now(UTC))
            .execution_options(synchronize_session=False)
        )
        if result.rowcount != 1:
            raise api_error(409, conflict_code, conflict_message)
        session.refresh(draft, attribute_names=["version", "updated_at"])


def create_draft(
    session: Session,
    workspace_key: str,
    model_release_id: int,
    *,
    name: str | None = None,
    source_revision_id: str | None = None,
    source: str | None = None,
    expected_model_runtime_release_id: int | None = None,
    validate_selected_model: bool = False,
) -> WorkspaceDraft:
    if source not in (None, "currentLive", "revision"):
        raise api_error(422, "workspace_draft_source_invalid", "Workspace draft source is invalid")
    if source == "revision" and source_revision_id is None:
        raise api_error(
            422,
            "workspace_draft_source_invalid",
            "A historical source requires a workspace revision id",
        )
    if source == "currentLive" and source_revision_id is not None:
        raise api_error(
            422,
            "workspace_draft_source_invalid",
            "A current-live source cannot include a workspace revision id",
        )
    if source == "currentLive":
        return _create_current_live_draft(
            session,
            workspace_key,
            model_release_id,
            name=name,
            expected_model_runtime_release_id=expected_model_runtime_release_id,
            validate_selected_model=validate_selected_model,
        )
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
    session.flush()
    if validate_selected_model:
        require_draft_compatible(session, draft, _draft_model(session, draft))
    if source_revision_id is not None:
        record_draft_derived(session, draft=draft)
    else:
        record_draft_created(session, draft=draft)
    session.commit()
    session.refresh(draft)
    return draft


def _create_current_live_draft(
    session: Session,
    workspace_key: str,
    model_release_id: int,
    *,
    name: str | None,
    expected_model_runtime_release_id: int | None,
    validate_selected_model: bool,
) -> WorkspaceDraft:
    """Capture one private base under SQLite's database-wide writer reservation.

    SQLite is the supported Base 0.6 runtime database.  ``BEGIN IMMEDIATE`` prevents a concurrent
    live writer (including model activation) from committing between graph rows, attributes, edges and
    the runtime-state comparison.  Other dialects are refused until their equivalent capture protocol
    is implemented, rather than silently returning a weaker mixed snapshot.
    """
    if session.bind is None or session.bind.dialect.name != "sqlite":
        raise api_error(
            409,
            "workspace_draft_snapshot_unsupported",
            "Current-live draft capture is supported only on SQLite in this release",
        )
    # Active-model dependency resolution may have opened a read transaction before this service.
    # Discard it so the capture starts at the explicit writer reservation rather than a stale read view.
    session.rollback()
    try:
        session.connection().exec_driver_sql("BEGIN IMMEDIATE")
    except OperationalError as exc:
        session.rollback()
        raise api_error(
            409,
            "workspace_draft_snapshot_retry",
            "Current live data is busy; retry starting the draft after the active write finishes",
        ) from exc
    try:
        workspace = session.get(Workspace, workspace_key)
        if workspace is None:
            raise api_error(404, "workspace_not_found", f"Workspace '{workspace_key}' not found")
        if workspace.status != "active":
            raise api_error(409, "workspace_retired", "Retired workspaces cannot be edited")
        state = session.get(ModelRuntimeState, 1)
        if (
            state is None
            or (
                expected_model_runtime_release_id is None
                and state.active_model_release_id != model_release_id
            )
            or (
                expected_model_runtime_release_id is not None
                and state.active_model_release_id != expected_model_runtime_release_id
            )
        ):
            raise api_error(
                409,
                "workspace_draft_snapshot_retry",
                "The selected model changed before current-live capture; retry with the current model",
            )
        base = WorkspaceDraftBase(
            workspace_key=workspace_key,
            model_release_id=state.active_model_release_id,
            model_runtime_version=state.version,
        )
        session.add(base)
        session.flush()
        live_objects, attributes, live_relations = _load_live_membership(session, workspace_key)
        for item in live_objects:
            session.add(
                WorkspaceDraftBaseObject(
                    base_id=base.id,
                    object_id=item.id,
                    application_key=item.application_key,
                    object_type_key=item.object_type_key,
                    name=item.name,
                    parent_object_id=item.parent_object_id,
                    attributes={
                        key: value for key, (_row_id, value) in attributes[item.id].items()
                    },
                    version=item.version,
                )
            )
        for item in live_relations:
            session.add(
                WorkspaceDraftBaseRelation(
                    base_id=base.id,
                    relation_id=item.id,
                    relation_type_key=item.relation_type_key,
                    from_object_id=item.from_object_id,
                    to_object_id=item.to_object_id,
                    attributes=dict(item.attributes or {}),
                    version=item.version,
                )
            )
        draft = WorkspaceDraft(
            workspace_key=workspace_key,
            model_release_id=model_release_id,
            base_id=base.id,
            name=name,
        )
        session.add(draft)
        session.flush()
        if validate_selected_model:
            require_draft_compatible(
                session,
                draft,
                _draft_model(session, draft),
                source_release_id=base.model_release_id,
            )
        record_draft_created(session, draft=draft)
        session.commit()
        session.refresh(draft)
        return draft
    except Exception:
        session.rollback()
        raise


def _load_live_membership(
    session: Session, workspace_key: str
) -> tuple[list[RdmObject], dict[str, dict[str, tuple[str, Any]]], list[ObjectRelation]]:
    """Load the graph after current-live capture has acquired its SQLite writer reservation."""
    objects = list(
        session.scalars(select(RdmObject).where(RdmObject.workspace_key == workspace_key))
    )
    object_ids = [item.id for item in objects]
    attributes = load_attribute_values(session, object_ids)
    relations: list[ObjectRelation] = []
    if object_ids:
        relations = list(
            session.scalars(
                select(ObjectRelation).where(
                    ObjectRelation.from_object_id.in_(object_ids),
                    ObjectRelation.to_object_id.in_(object_ids),
                )
            )
        )
    return objects, attributes, relations


def update_draft(
    session: Session, draft_id: str, expected_version: int, name: str | None
) -> WorkspaceDraft:
    draft = _draft(session, draft_id, for_update=True)
    previous_name = draft.name
    _claim_draft(session, draft, expected_version)
    if previous_name != name:
        record_draft_renamed(session, draft=draft, from_name=previous_name, to_name=name)
    draft.name = name
    session.commit()
    return draft


def discard_draft(session: Session, draft_id: str, expected_version: int) -> None:
    draft = _draft(session, draft_id, for_update=True)
    _claim_draft(session, draft, expected_version)
    record_draft_discarded(session, draft=draft)
    _delete_draft_and_base(session, draft)
    session.commit()


def _delete_draft_and_base(session: Session, draft: WorkspaceDraft) -> None:
    """Remove a private base explicitly because SQLite does not enable FK cascades by default."""
    base_id = draft.base_id
    delete_draft_set_versions(session, draft.id)
    delete_owner_values(session, draft.id)
    session.delete(draft)
    session.flush()
    if base_id is None:
        return
    delete_owner_values(session, base_id)
    session.execute(
        delete(WorkspaceDraftBaseRelation).where(WorkspaceDraftBaseRelation.base_id == base_id)
    )
    session.execute(
        delete(WorkspaceDraftBaseObject).where(WorkspaceDraftBaseObject.base_id == base_id)
    )
    session.execute(delete(WorkspaceDraftBase).where(WorkspaceDraftBase.id == base_id))


def _record_conflict(expected: int | None, actual: int, label: str) -> None:
    if expected is not None and expected != actual:
        raise api_error(409, "version_conflict", f"{label} version has changed")


def _draft_model(session: Session, draft: WorkspaceDraft) -> Any:
    return resolve_pinned_release(session, draft.model_release_id, require_ready=False).model


def _normalize_object_attributes(
    model: Any, object_type_key: str, attributes: dict[str, Any], *, partial: bool
) -> dict[str, Any]:
    object_type = model.object_type(object_type_key)
    if object_type is None:
        raise api_error(
            422,
            "unknown_object_type",
            f"Object type '{object_type_key}' is not in the pinned model",
        )
    normalized = validate_attributes(
        model, object_type, attributes, partial=partial, apply_defaults=not partial
    )
    # Draft rows are JSON; store the same form that current-live capture copies from live rows.
    return {key: stored_json_value(value) for key, value in normalized.items()}


def _validate_object_identity(model: Any, application_key: str, object_type_key: str) -> None:
    object_type = model.object_type(object_type_key)
    if object_type is None:
        raise api_error(
            422,
            "unknown_object_type",
            f"Object type '{object_type_key}' is not in the pinned model",
        )
    application = next((item for item in model.applications if item.key == application_key), None)
    if application is None or object_type_key not in application.objectTypeKeys:
        raise api_error(
            422,
            "object_type_not_in_application",
            f"Object type '{object_type_key}' is not enabled in application '{application_key}'",
        )


def _normalize_relation(
    model: Any, relation_type_key: str, from_type: str, to_type: str, attributes: dict[str, Any]
) -> dict[str, Any]:
    relation = model.relation_type(relation_type_key)
    if relation is None:
        raise api_error(
            422,
            "unknown_relation_type",
            f"Relation type '{relation_type_key}' is not in the pinned model",
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
    if allowed is None:
        raise api_error(
            422, "invalid_relation_pair", "Relation is not permitted between these object types"
        )
    return validate_relation_attributes(model, allowed, attributes)


def validate_draft_relation(
    model: Any,
    membership: EffectiveDraftMembership,
    relation_type_key: str,
    from_id: str,
    to_id: str,
    attributes: dict[str, Any],
    *,
    exclude_id: str | None = None,
    exclude_ids: set[str] | None = None,
) -> dict[str, Any]:
    objects = {item.object_id: item for item in membership.objects}
    source, target = objects.get(from_id), objects.get(to_id)
    if source is None or target is None:
        raise api_error(
            422, "relation_endpoint_missing", "Relation endpoints must exist in the workspace draft"
        )
    allowed = next(
        (
            item
            for item in model.objectTypeRelations
            if item.relationTypeKey == relation_type_key
            and item.fromObjectTypeKey == source.object_type_key
            and item.toObjectTypeKey == target.object_type_key
        ),
        None,
    )
    normalized = _normalize_relation(
        model, relation_type_key, source.object_type_key, target.object_type_key, attributes
    )
    if allowed.features.get("parent") or relation_type_key in set(
        (model.object_type(target.object_type_key).behavior or {}).get("parentRelationTypeKeys", [])
    ):
        raise api_error(
            422,
            "immutable_relation",
            "Engine-maintained containment relations are changed through object edits",
        )
    existing = [
        row
        for row in membership.relations
        if row.relation_id != exclude_id
        and row.relation_id not in (exclude_ids or set())
        and row.relation_type_key == relation_type_key
    ]
    if allowed.cardinality == "one-to-one" and any(
        row.from_object_id == from_id or row.to_object_id == to_id for row in existing
    ):
        raise api_error(409, "cardinality_violation", "Relation cardinality would be violated")
    if allowed.cardinality == "one-to-many" and any(row.to_object_id == to_id for row in existing):
        raise api_error(409, "cardinality_violation", "Relation cardinality would be violated")
    ancestor_type = allowed.features.get("uniqueToAncestorTypeKey")
    if ancestor_type:
        condition = allowed.features.get("uniqueWhenToAttributeEquals")
        if (
            condition
            and (target.attributes or {}).get(condition["attributeTypeKey"]) != condition["value"]
        ):
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
        if target_ancestor is None:
            raise api_error(
                422,
                "relation_ancestor_required",
                f"Related object must belong to an ancestor of type '{ancestor_type}'",
            )
        if any(
            row.from_object_id == from_id
            and ancestor(objects.get(row.to_object_id)) == target_ancestor
            and (
                not condition
                or (objects.get(row.to_object_id).attributes or {}).get(
                    condition["attributeTypeKey"]
                )
                == condition["value"]
            )
            for row in existing
        ):
            raise api_error(
                409,
                "duplicate_relation_scope",
                "A related object already exists for this ancestor scope",
            )
    return normalized


def put_draft_object(session: Session, draft_id: str, payload: Any) -> WorkspaceDraftObject:
    draft = _draft(session, draft_id, for_update=True)
    model = _draft_model(session, draft)
    _validate_object_identity(model, payload.applicationKey, payload.objectTypeKey)
    attributes = _normalize_object_attributes(
        model, payload.objectTypeKey, payload.attributes, partial=False
    )
    validate_object_attribute_rules(model.object_type(payload.objectTypeKey), attributes)
    membership = effective_draft_membership(session, draft_id)
    if payload.parentObjectId is not None and not any(
        item.object_id == str(payload.parentObjectId) for item in membership.objects
    ):
        raise api_error(422, "parent_wrong_scope", "Parent must exist in the workspace draft")
    _claim_draft(session, draft, payload.expectedDraftVersion)
    object_id = str(payload.id) if payload.id else str(uuid4())
    if any(item.object_id == object_id for item in membership.objects) or session.scalar(
        select(RdmObject.id).where(RdmObject.id == object_id)
    ):
        raise api_error(409, "object_already_exists", f"Object '{object_id}' already exists")
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
            raise api_error(
                422, "duplicate_initial_relation", "Initial relationships must not repeat"
            )
        objects = {
            item.object_id: item for item in effective_draft_membership(session, draft_id).objects
        }
        objects[row.object_id] = row
        candidate_relations = list(membership.relations)
        for initial in payload.initialRelations:
            from_id = (
                row.object_id if initial.direction == "outgoing" else str(initial.otherObjectId)
            )
            to_id = str(initial.otherObjectId) if initial.direction == "outgoing" else row.object_id
            target = objects.get(to_id)
            source = objects.get(from_id)
            if source is None or target is None:
                raise api_error(
                    422,
                    "relation_endpoint_missing",
                    "Relation endpoints must exist in the workspace draft",
                )
            candidate = EffectiveDraftMembership(
                draft, tuple(objects.values()), tuple(candidate_relations)
            )
            attrs = validate_draft_relation(
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
    parent_keys = (
        set(
            (model.object_type(row.object_type_key).behavior or {}).get(
                "parentRelationTypeKeys", []
            )
        )
        if model.object_type(row.object_type_key)
        else set()
    )
    required = {
        item.relationTypeKey
        for item in model.objectTypeRelations
        if item.toObjectTypeKey == row.object_type_key
        and item.required
        and item.relationTypeKey not in parent_keys
    }
    provided = {
        item.relationTypeKey
        for item in getattr(payload, "initialRelations", [])
        if item.direction == "incoming"
    }
    if required - provided:
        raise api_error(
            422,
            "missing_required_relations",
            f"Required relationships missing: {sorted(required - provided)}",
            {"relationTypeKeys": sorted(required - provided)},
        )
    record_audit_event(
        session,
        aggregate_type="object-draft",
        aggregate_id=row.object_id,
        action="created",
        version=row.version,
        changes={"attributes": attributes, "workspaceDraftId": draft.id},
        object_ids=[row.object_id],
    )
    session.commit()
    return row


def update_draft_object(
    session: Session, draft_id: str, object_id: str, payload: Any
) -> WorkspaceDraftObject:
    draft = _draft(session, draft_id, for_update=True)
    model = _draft_model(session, draft)
    membership = effective_draft_membership(session, draft_id)
    _claim_draft(session, draft, payload.expectedDraftVersion)
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
            **_normalize_object_attributes(
                model, row.object_type_key, payload.attributes, partial=True
            ),
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
            validate_draft_relation(
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
    record_audit_event(
        session,
        aggregate_type="object-draft",
        aggregate_id=row.object_id,
        action="updated",
        version=row.version,
        changes={"attributes": row.attributes or {}, "workspaceDraftId": draft.id},
        object_ids=[row.object_id],
    )
    session.commit()
    return row


def delete_draft_object(
    session: Session,
    draft_id: str,
    object_type_key: str,
    object_id: str,
    expected_draft_version: int,
    expected_record_version: int,
    *,
    cascade: bool = False,
    deletion_preview: str | None = None,
) -> None:
    from .deletion import (
        deletion_preview_changed,
        deletion_preview_token,
        require_deletion_preview,
        require_matching_deletion_preview,
    )

    if cascade:
        require_deletion_preview(deletion_preview)

    draft = _draft(session, draft_id, for_update=True)
    model = _draft_model(session, draft)
    # The aggregate claim serializes all draft mutations before the hierarchy is re-read. A preview
    # response rolls this claim back; a confirmed delete retains it in the mutation transaction.
    _claim_draft(
        session,
        draft,
        expected_draft_version,
        conflict_code=(
            "deletion_preview_changed" if cascade else "workspace_draft_version_conflict"
        ),
        conflict_message=(
            "The object was modified by another session. Please retry."
            if cascade
            else "Workspace draft version has changed"
        ),
    )
    membership = effective_draft_membership(session, draft_id)
    objects = {item.object_id: item for item in membership.objects}
    root = objects.get(object_id)
    if root is None or root.object_type_key != object_type_key:
        if cascade and deletion_preview is not None:
            raise deletion_preview_changed()
        raise api_error(404, "object_not_found", f"Object '{object_id}' not found in draft")
    if cascade and deletion_preview is not None and expected_record_version != root.version:
        raise api_error(
            409,
            "deletion_preview_changed",
            "The object was modified by another session. Please retry.",
        )
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
            source, target = (
                objects.get(relation.from_object_id),
                objects.get(relation.to_object_id),
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
                planned_ids.add(target.object_id)
                reasons[target.object_id] = "required-ownership"
                frontier.append(target.object_id)
    incident = [
        relation
        for relation in membership.relations
        if relation.from_object_id in planned_ids or relation.to_object_id in planned_ids
    ]

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
        "draftId": draft_id,
        "objectTypeKey": object_type_key,
        "objectId": object_id,
        "modelReleaseId": draft.model_release_id,
    }
    object_identity = [
        (item.object_id, item.version, item.parent_object_id)
        for item in membership.objects
        if item.object_id in planned_ids
    ]
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
                "deletionPreviewToken": deletion_preview_token(
                    scope="draft-deletion",
                    context=context,
                    objects=object_identity,
                    relations=relation_identity,
                ),
            },
        )
    if cascade:
        require_matching_deletion_preview(
            deletion_preview,
            scope="draft-deletion",
            context=context,
            objects=object_identity,
            relations=relation_identity,
        )
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
        increment_set_versions(
            session,
            workspace_key=draft.workspace_key,
            workspace_draft_id=draft.id,
            relation_type_key=relation.relation_type_key,
            from_object_type_key=objects[relation.from_object_id].object_type_key,
            to_object_type_key=objects[relation.to_object_id].object_type_key,
            from_object_id=relation.from_object_id,
            to_object_id=relation.to_object_id,
        )
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


def _validate_candidate_parent(model: Any, row: Any, objects: dict[str, Any]) -> None:
    object_type = model.object_type(row.object_type_key)
    if row.parent_object_id is None:
        if not object_type.features.get("rootCreatable", False):
            raise api_error(422, "parent_required", "This object type requires a parent")
        return
    parent = objects.get(row.parent_object_id)
    if parent is None or parent.application_key != row.application_key:
        raise api_error(
            422, "parent_wrong_scope", "Parent must be in the same application and workspace"
        )
    keys = set(object_type.behavior.get("parentRelationTypeKeys", []))
    matches = [
        pair
        for pair in model.objectTypeRelations
        if pair.relationTypeKey in keys
        and pair.fromObjectTypeKey == parent.object_type_key
        and pair.toObjectTypeKey == row.object_type_key
    ]
    if len(matches) != 1:
        raise api_error(
            422, "invalid_parent_type", "Parent type is not permitted for this object type"
        )
    seen = {row.object_id}
    current = parent
    while current is not None:
        if current.object_id in seen:
            raise api_error(422, "parent_cycle", "Parent selection would create a cycle")
        seen.add(current.object_id)
        current = objects.get(current.parent_object_id)


def _sync_draft_parent_relation(
    session: Session, draft: WorkspaceDraft, model: Any, row: WorkspaceDraftObject
) -> None:
    """Maintain the typed containment edge with a draft object edit.

    The effective edge may come from the draft base; like a live update, an unchanged parent keeps
    that edge and its identity, and a changed parent tombstones it before adding the new one.
    """
    membership = effective_draft_membership(session, draft.id)
    objects = {item.object_id: item for item in membership.objects}
    _validate_candidate_parent(model, row, objects)
    keys = (
        set(
            (model.object_type(row.object_type_key).behavior or {}).get(
                "parentRelationTypeKeys", []
            )
        )
        if model.object_type(row.object_type_key)
        else set()
    )
    if not keys:
        return
    current = [
        relation
        for relation in membership.relations
        if relation.to_object_id == row.object_id and relation.relation_type_key in keys
    ]
    if [relation.from_object_id for relation in current] == (
        [row.parent_object_id] if row.parent_object_id else []
    ):
        return
    for relation in current:
        stored = session.scalar(
            select(WorkspaceDraftRelation).where(
                WorkspaceDraftRelation.draft_id == draft.id,
                WorkspaceDraftRelation.relation_id == relation.relation_id,
            )
        )
        if stored is None:
            session.add(
                WorkspaceDraftRelation(
                    draft_id=draft.id,
                    relation_id=relation.relation_id,
                    relation_type_key=relation.relation_type_key,
                    from_object_id=relation.from_object_id,
                    to_object_id=relation.to_object_id,
                    attributes=dict(relation.attributes or {}),
                    version=relation.version + 1,
                    is_deleted=True,
                )
            )
        else:
            stored.is_deleted = True
            stored.version += 1
    if row.parent_object_id:
        parent = objects.get(row.parent_object_id)
        if parent is None:
            raise api_error(422, "parent_wrong_scope", "Parent must exist in the workspace draft")
        allowed = next(
            (
                item
                for item in model.objectTypeRelations
                if item.relationTypeKey in keys
                and item.fromObjectTypeKey == parent.object_type_key
                and item.toObjectTypeKey == row.object_type_key
            ),
            None,
        )
        if allowed is None:
            raise api_error(
                422, "invalid_parent_type", "Parent type is not permitted for this object type"
            )
        session.add(
            WorkspaceDraftRelation(
                draft_id=draft.id,
                relation_id=str(uuid4()),
                relation_type_key=allowed.relationTypeKey,
                from_object_id=parent.object_id,
                to_object_id=row.object_id,
                attributes={},
                version=1,
            )
        )


def _increment_draft_relation_set_versions(
    session: Session,
    draft: WorkspaceDraft,
    membership: EffectiveDraftMembership,
    row: WorkspaceDraftRelation,
) -> None:
    objects = {item.object_id: item for item in membership.objects}
    from_obj = objects.get(row.from_object_id)
    to_obj = objects.get(row.to_object_id)
    if from_obj is None or to_obj is None:
        return
    increment_set_versions(
        session,
        workspace_key=draft.workspace_key,
        workspace_draft_id=draft.id,
        relation_type_key=row.relation_type_key,
        from_object_type_key=from_obj.object_type_key,
        to_object_type_key=to_obj.object_type_key,
        from_object_id=row.from_object_id,
        to_object_id=row.to_object_id,
    )


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
    attributes = validate_draft_relation(
        model,
        membership,
        payload.relationTypeKey,
        str(payload.fromObjectId),
        str(payload.toObjectId),
        payload.attributes,
    )
    _claim_draft(session, draft, payload.expectedDraftVersion)
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
    record_audit_event(
        session,
        aggregate_type="relation",
        aggregate_id=row.relation_id,
        action="created" if row.version == 1 else "updated",
        version=row.version,
        changes={"attributes": attributes, "workspaceDraftId": draft.id},
        object_ids=[row.from_object_id, row.to_object_id],
    )
    _increment_draft_relation_set_versions(session, draft, membership, row)
    session.commit()
    return row


def update_draft_relation(
    session: Session, draft_id: str, relation_id: str, payload: Any
) -> WorkspaceDraftRelation:
    draft = _draft(session, draft_id, for_update=True)
    model = _draft_model(session, draft)
    row = session.scalar(
        select(WorkspaceDraftRelation).where(
            WorkspaceDraftRelation.draft_id == draft_id,
            WorkspaceDraftRelation.relation_id == relation_id,
        )
    )
    if row is None:
        base = next(
            (
                item
                for item in effective_draft_membership(session, draft_id).relations
                if item.relation_id == relation_id
            ),
            None,
        )
        if base is None:
            raise api_error(
                404, "relation_not_found", f"Relation '{relation_id}' not found in draft"
            )
        row = WorkspaceDraftRelation(
            draft_id=draft_id,
            relation_id=relation_id,
            relation_type_key=base.relation_type_key,
            from_object_id=base.from_object_id,
            to_object_id=base.to_object_id,
            attributes=dict(base.attributes or {}),
            version=base.version,
        )
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
    attrs = validate_draft_relation(
        model, membership, relation_type, from_id, to_id, attrs, exclude_id=relation_id
    )
    _claim_draft(session, draft, payload.expectedDraftVersion)
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
        changes={"attributes": attrs, "workspaceDraftId": draft.id},
        object_ids=[row.from_object_id, row.to_object_id],
    )
    _increment_draft_relation_set_versions(session, draft, membership, row)
    session.commit()
    return row


def delete_draft_relation(
    session: Session,
    draft_id: str,
    relation_id: str,
    expected_draft_version: int,
    expected_record_version: int,
) -> None:
    draft = _draft(session, draft_id, for_update=True)
    model = _draft_model(session, draft)
    membership = effective_draft_membership(session, draft_id)
    row = session.scalar(
        select(WorkspaceDraftRelation).where(
            WorkspaceDraftRelation.draft_id == draft_id,
            WorkspaceDraftRelation.relation_id == relation_id,
        )
    )
    if row is None:
        base = next(
            (
                item
                for item in effective_draft_membership(session, draft_id).relations
                if item.relation_id == relation_id
            ),
            None,
        )
        if base is None:
            raise api_error(
                404, "relation_not_found", f"Relation '{relation_id}' not found in draft"
            )
        row = WorkspaceDraftRelation(
            draft_id=draft_id,
            relation_id=relation_id,
            relation_type_key=base.relation_type_key,
            from_object_id=base.from_object_id,
            to_object_id=base.to_object_id,
            attributes=dict(base.attributes or {}),
            version=base.version,
        )
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
            raise api_error(
                422,
                "immutable_relation",
                "Engine-maintained containment relations cannot be deleted directly",
            )
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
            raise api_error(
                422, "required_relation", "Required relationships cannot be deleted directly"
            )
    _record_conflict(expected_record_version, row.version, "Relation record")
    _claim_draft(session, draft, expected_draft_version)
    row.version += 1
    row.is_deleted = True
    _increment_draft_relation_set_versions(session, draft, membership, row)
    session.commit()


def patch_draft_attribute(
    session: Session,
    draft_id: str,
    object_id: str,
    key: str,
    value: Any,
    expected_draft_version: int,
    expected_record_version: int,
) -> WorkspaceDraftObject:
    draft = _draft(session, draft_id, for_update=True)
    membership = effective_draft_membership(session, draft_id)
    base = next((item for item in membership.objects if item.object_id == object_id), None)
    if base is None:
        raise api_error(404, "object_not_found", f"Object '{object_id}' not found in draft")
    row = session.scalar(
        select(WorkspaceDraftObject).where(
            WorkspaceDraftObject.draft_id == draft_id, WorkspaceDraftObject.object_id == object_id
        )
    )
    if row is None:
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
    _record_conflict(expected_record_version, row.version, "Object record")
    model = _draft_model(session, draft)
    normalized = _normalize_object_attributes(
        model, row.object_type_key, {key: value}, partial=True
    )
    _claim_draft(session, draft, expected_draft_version)
    row.attributes = {**(row.attributes or {}), **normalized}
    _validate_draft_attribute_uniqueness(model, membership, row.object_id, row.attributes)
    row.version += 1
    record_audit_event(
        session,
        aggregate_type="object-draft",
        aggregate_id=row.object_id,
        action="updated",
        version=row.version,
        changes={"attributes": {key: value}, "workspaceDraftId": draft.id},
        object_ids=[row.object_id],
    )
    session.commit()
    return row


def delete_draft_attribute(
    session: Session,
    draft_id: str,
    object_id: str,
    key: str,
    expected_draft_version: int,
    expected_record_version: int,
) -> WorkspaceDraftObject:
    draft = _draft(session, draft_id, for_update=True)
    membership = effective_draft_membership(session, draft_id)
    base = next((item for item in membership.objects if item.object_id == object_id), None)
    if base is None:
        raise api_error(404, "object_not_found", f"Object '{object_id}' not found in draft")
    row = session.scalar(
        select(WorkspaceDraftObject).where(
            WorkspaceDraftObject.draft_id == draft_id, WorkspaceDraftObject.object_id == object_id
        )
    )
    if row is None:
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
    _record_conflict(expected_record_version, row.version, "Object record")
    model = _draft_model(session, draft)
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
    _claim_draft(session, draft, expected_draft_version)
    row.attributes = remaining
    row.version += 1
    record_audit_event(
        session,
        aggregate_type="object-draft",
        aggregate_id=row.object_id,
        action="updated",
        version=row.version,
        changes={"attributes": {key: None}, "workspaceDraftId": draft.id},
        object_ids=[row.object_id],
    )
    session.commit()
    return row


def _diagnostics(
    membership: EffectiveDraftMembership, model: Any, *, apply_defaults: bool = True
) -> list[dict[str, Any]]:
    errors: list[dict[str, Any]] = []
    objects = {item.object_id: item for item in membership.objects}
    relation_rows = list(membership.relations)
    # Stable object and relation identities share one integration namespace; a collision makes the
    # graph ambiguous for consumers addressing records by stable id.
    object_ids = set(objects)
    for shared_id in sorted(
        object_ids.intersection(item.relation_id for item in membership.relations)
    ):
        errors.append(
            {
                "code": "identity_collision",
                "message": f"Stable id '{shared_id}' is used by both an object and a relation",
                "details": {"id": shared_id},
            }
        )
    effective_attributes: dict[str, dict[str, Any]] = {}
    for item in membership.objects:
        object_type = model.object_type(item.object_type_key)
        if object_type is None:
            errors.append(
                {
                    "code": "unknown_object_type",
                    "message": f"Object type '{item.object_type_key}' is not in the pinned model",
                    "details": {"objectId": item.object_id},
                }
            )
        else:
            try:
                _validate_candidate_parent(model, item, objects)
            except ApiError as exc:
                errors.append(
                    {
                        "code": exc.code,
                        "message": exc.message,
                        "details": {"objectId": item.object_id},
                    }
                )
            try:
                # Stored/defaulted read-only values are valid graph content. Write boundaries
                # reject authoring them; snapshot validation must still type-check their values.
                attrs = validate_attributes(
                    model,
                    object_type,
                    dict(item.attributes or {}),
                    partial=False,
                    allow_read_only=True,
                    apply_defaults=apply_defaults,
                )
                validate_object_attribute_rules(object_type, attrs)
            except ApiError as exc:
                errors.append(
                    {
                        "code": exc.code,
                        "message": exc.message,
                        "details": {"objectId": item.object_id, **(exc.details or {})}
                        if isinstance(exc.details, dict)
                        else {"objectId": item.object_id},
                    }
                )
            else:
                effective_attributes[item.object_id] = attrs
            _validate_application_diagnostic(errors, model, item)
            # Attribute uniqueness is scoped to the candidate graph, never to the mutable active
            # projection (which may still contain a different publication).
            for key, definition in (
                (key, model.attribute_type(key)) for key in (item.attributes or {})
            ):
                if definition and definition.features.get("unique"):
                    same = [
                        other.object_id
                        for other in membership.objects
                        if other.object_id != item.object_id
                        and (other.attributes or {}).get(key) == (item.attributes or {}).get(key)
                    ]
                    if same:
                        errors.append(
                            {
                                "code": "duplicate_attribute_value",
                                "message": f"Attribute '{key}' must be unique",
                                "details": {
                                    "objectId": item.object_id,
                                    "attributeTypeKey": key,
                                    "conflictingObjectIds": sorted(same),
                                },
                            }
                        )
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
                errors.append(
                    {
                        "code": "containment_relation_missing",
                        "message": "Containment parent is not represented by its declared parent relation",
                        "details": {
                            "objectId": current.object_id,
                            "parentObjectId": parent.object_id,
                        },
                    }
                )
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
            _normalize_relation(
                model,
                relation.relation_type_key,
                source.object_type_key,
                target.object_type_key,
                dict(relation.attributes or {}),
            )
        except ApiError as exc:
            errors.append(
                {
                    "code": exc.code,
                    "message": exc.message,
                    "details": {"relationId": relation.relation_id},
                }
            )
        else:
            valid_relations.append((relation, allowed))
    for relation, allowed in valid_relations:
        if allowed.cardinality in {"one-to-one", "one-to-many", "many-to-one"}:
            same = [
                other
                for other, other_allowed in valid_relations
                if other_allowed.relationTypeKey == allowed.relationTypeKey
                and other.relation_id != relation.relation_id
            ]
            if allowed.cardinality in {"one-to-one", "many-to-one"} and any(
                other.from_object_id == relation.from_object_id for other in same
            ):
                errors.append(
                    {
                        "code": "relation_cardinality_violation",
                        "message": f"Relation '{allowed.relationTypeKey}' exceeds source cardinality",
                        "details": {"relationId": relation.relation_id},
                    }
                )
            if allowed.cardinality in {"one-to-one", "one-to-many"} and any(
                other.to_object_id == relation.to_object_id for other in same
            ):
                errors.append(
                    {
                        "code": "relation_cardinality_violation",
                        "message": f"Relation '{allowed.relationTypeKey}' exceeds target cardinality",
                        "details": {"relationId": relation.relation_id},
                    }
                )
    # Ancestor-scoped uniqueness (language/target uniqueness for translations): a scoped relation may
    # appear once per source object per ancestor scope while the optional target-attribute condition
    # holds. Mirrors the draft write path in validate_draft_relation.
    for relation, allowed in valid_relations:
        ancestor_type_key = allowed.features.get("uniqueToAncestorTypeKey")
        if not ancestor_type_key:
            continue
        condition = allowed.features.get("uniqueWhenToAttributeEquals")
        target = objects.get(relation.to_object_id)
        target_values = effective_attributes.get(target.object_id, target.attributes or {})
        if condition and target_values.get(condition["attributeTypeKey"]) != condition["value"]:
            continue
        target_ancestor = _ancestor_object_id(objects, target, ancestor_type_key)
        if target_ancestor is None:
            continue
        for other, other_allowed in valid_relations:
            if (
                other.relation_id >= relation.relation_id
                or other_allowed.relationTypeKey != allowed.relationTypeKey
            ):
                continue
            other_target = objects.get(other.to_object_id)
            other_values = effective_attributes.get(
                other_target.object_id, other_target.attributes or {}
            )
            if (
                other.from_object_id == relation.from_object_id
                and (
                    not condition
                    or other_values.get(condition["attributeTypeKey"]) == condition["value"]
                )
                and _ancestor_object_id(objects, other_target, ancestor_type_key) == target_ancestor
            ):
                errors.append(
                    {
                        "code": "duplicate_relation_scope",
                        "message": f"Relation '{allowed.relationTypeKey}' already exists for this ancestor scope",
                        "details": {
                            "relationId": relation.relation_id,
                            "conflictingRelationId": other.relation_id,
                            "objectId": relation.from_object_id,
                            "ancestorObjectId": target_ancestor,
                        },
                    }
                )
                break
    # Required relationships bind at the target side: every object that is the target of a required
    # non-parent pair must carry an incoming relation of that type from an allowed source.  This
    # matches the workspace draft object-create contract, model compatibility counting and the
    # PK->FK ownership cascade used by delete.
    required_by_target: dict[tuple[str, str], set[str]] = {}
    for pair in model.objectTypeRelations:
        if pair.required and not _is_parent_pair(model, pair):
            required_by_target.setdefault((pair.relationTypeKey, pair.toObjectTypeKey), set()).add(
                pair.fromObjectTypeKey
            )
    for target in membership.objects:
        for (relation_key, target_type), source_types in sorted(required_by_target.items()):
            if target_type != target.object_type_key:
                continue
            satisfied = any(
                rel.to_object_id == target.object_id
                and rel.relation_type_key == relation_key
                and objects[rel.from_object_id].object_type_key in source_types
                for rel, _allowed in valid_relations
            )
            if not satisfied:
                errors.append(
                    {
                        "code": "missing_required_relation",
                        "message": f"Required relationship '{relation_key}' is missing for object '{target.object_id}'",
                        "details": {"objectId": target.object_id, "relationTypeKey": relation_key},
                    }
                )
    return errors


def _validate_application_diagnostic(errors: list[dict[str, Any]], model: Any, item: Any) -> None:
    application = next((x for x in model.applications if x.key == item.application_key), None)
    if application is None or item.object_type_key not in application.objectTypeKeys:
        errors.append(
            {
                "code": "object_type_not_in_application",
                "message": f"Object type '{item.object_type_key}' is not enabled in application '{item.application_key}'",
                "details": {"objectId": item.object_id},
            }
        )


def _parent_pair_exists(model: Any, child: Any, parent: Any, relations: list[Any]) -> bool:
    keys = (
        set(model.object_type(child.object_type_key).behavior.get("parentRelationTypeKeys", []))
        if model.object_type(child.object_type_key)
        else set()
    )
    return not keys or any(
        r.from_object_id == parent.object_id
        and r.to_object_id == child.object_id
        and r.relation_type_key in keys
        for r in relations
    )


def _is_parent_pair(model: Any, pair: Any) -> bool:
    child = model.object_type(pair.toObjectTypeKey)
    return bool(child and pair.relationTypeKey in child.behavior.get("parentRelationTypeKeys", []))


def _ancestor_object_id(objects: dict[str, Any], item: Any, object_type_key: str) -> str | None:
    """Return the nearest ancestor object id of ``item`` whose type is ``object_type_key``."""
    seen: set[str] = set()
    current = item
    while current is not None and current.object_id not in seen:
        seen.add(current.object_id)
        if current.object_type_key == object_type_key:
            return current.object_id
        current = objects.get(current.parent_object_id) if current.parent_object_id else None
    return None


def validate_draft(session: Session, draft_id: str, model: Any) -> list[dict[str, Any]]:
    return _diagnostics(effective_draft_membership(session, draft_id), model)


def selected_draft_release(session: Session, public_id: str) -> ModelRelease:
    """Resolve an installed public release identity using pinned-model errors."""
    release = session.scalar(select(ModelRelease).where(ModelRelease.public_id == public_id))
    if release is None:
        raise api_error(
            409,
            "pinned_model_unavailable",
            "The selected model release is not installed",
            {"modelReleaseId": public_id},
        )
    resolve_pinned_release(session, release.id, require_ready=False)
    return release


def require_draft_compatible(
    session: Session, draft: WorkspaceDraft, model: Any, *, source_release_id: int | None = None
) -> None:
    """Check complete effective membership, without conversion or live-table analysis."""
    membership = effective_draft_membership(session, draft.id)
    source_model = resolve_pinned_release(
        session,
        source_release_id if source_release_id is not None else draft.model_release_id,
        require_ready=False,
    ).model
    diagnostics = _diagnostics(membership, model, apply_defaults=False)
    # Match the existing model-compatibility type-change rule over effective membership. Target
    # normalizers can accept a value under another declared type, which would be conversion.
    for old_definition in source_model.attributeTypes:
        target_definition = model.attribute_type(old_definition.key)
        if target_definition is None or old_definition.valueType == target_definition.valueType:
            continue
        for rows, code, count_key in (
            (membership.objects, "attribute_value_type_changed", "objectCount"),
            (membership.relations, "relation_attribute_value_type_changed", "relationCount"),
        ):
            count = sum(old_definition.key in (row.attributes or {}) for row in rows)
            if count:
                diagnostics.append(
                    {
                        "code": code,
                        "message": "The selected release changes the declared type of stored values; conversion is required",
                        "details": {
                            "attributeTypeKey": old_definition.key,
                            "sourceValueType": old_definition.valueType,
                            "targetValueType": target_definition.valueType,
                            count_key: count,
                        },
                    }
                )
    # Preserve the source model's containment interpretation, matching model compatibility.
    objects = {row.object_id: row for row in membership.objects}
    target_pairs = {
        (pair.relationTypeKey, pair.fromObjectTypeKey, pair.toObjectTypeKey)
        for pair in model.objectTypeRelations
    }
    for pair in source_model.objectTypeRelations:
        if not _is_parent_pair(source_model, pair):
            continue
        source_relation = source_model.relation_type(pair.relationTypeKey)
        target_relation = model.relation_type(pair.relationTypeKey)
        identity = (pair.relationTypeKey, pair.fromObjectTypeKey, pair.toObjectTypeKey)
        if (
            identity in target_pairs
            and _is_parent_pair(model, pair)
            and target_relation is not None
            and all(
                bool(source_relation.features.get(key)) == bool(target_relation.features.get(key))
                for key in ("parentOf", "hierarchical")
            )
        ):
            continue
        count = sum(
            row.relation_type_key == pair.relationTypeKey
            and row.from_object_id in objects
            and row.to_object_id in objects
            and objects[row.from_object_id].object_type_key == pair.fromObjectTypeKey
            and objects[row.to_object_id].object_type_key == pair.toObjectTypeKey
            for row in membership.relations
        )
        if count:
            diagnostics.append(
                {
                    "code": "parent_relation_semantics_changed",
                    "message": "Stored containment uses source model semantics; changing them requires conversion",
                    "details": {
                        "relationTypeKey": pair.relationTypeKey,
                        "fromObjectTypeKey": pair.fromObjectTypeKey,
                        "toObjectTypeKey": pair.toObjectTypeKey,
                        "relationCount": count,
                    },
                }
            )
    if diagnostics:
        bounded = []
        for diagnostic in diagnostics[:20]:
            details = dict(diagnostic.get("details") or {})
            conflicting_ids = details.get("conflictingObjectIds")
            if conflicting_ids is not None and len(conflicting_ids) > 20:
                details.update(
                    conflictingObjectIds=conflicting_ids[:20],
                    conflictingObjectCount=len(conflicting_ids),
                    conflictingObjectsTruncated=True,
                )
            bounded.append({**diagnostic, **({"details": details} if details else {})})
        raise api_error(
            409,
            "draft_content_incompatible",
            "Draft content does not fit the selected model. Keep its current version or choose a compatible release; conversion requires the migration workflow.",
            {
                "diagnostics": bounded,
                "diagnosticCount": len(diagnostics),
                "diagnosticsTruncated": len(diagnostics) > 20,
            },
        )


def change_draft_model_release(
    session: Session, workspace_key: str, draft_id: str, public_id: str, expected_version: int
) -> WorkspaceDraft:
    """Claim, validate and change a single draft pin in one transaction."""
    try:
        draft = _draft(session, draft_id, for_update=True)
        if draft.workspace_key != workspace_key:
            raise api_error(404, "workspace_draft_not_found", "Workspace draft not found")
        release = selected_draft_release(session, public_id)
        if draft.version != expected_version:
            raise api_error(
                409, "workspace_draft_version_conflict", "Workspace draft version has changed"
            )
        # Claim even a no-op to serialize against edits, then roll it back without an audit/version bump.
        _claim_draft(session, draft, expected_version)
        if draft.model_release_id == release.id:
            session.rollback()
            return _draft(session, draft_id)
        old_release = session.get(ModelRelease, draft.model_release_id)
        require_draft_compatible(
            session, draft, resolve_pinned_release(session, release.id, require_ready=False).model
        )
        draft.model_release_id = release.id

        def identity(item: ModelRelease) -> dict[str, str]:
            return {"id": item.public_id, "key": item.release_key, "version": item.release_version}

        record_audit_event(
            session,
            aggregate_type="workspace-draft",
            aggregate_id=draft.id,
            action="model-release-changed",
            version=draft.version,
            changes={
                "modelRelease": {
                    "from": identity(old_release) if old_release else None,
                    "to": identity(release),
                }
            },
            object_ids=(),
        )
        session.commit()
        session.refresh(draft)
        return draft
    except Exception:
        session.rollback()
        raise


def pinned_model(session: Session, draft_id: str) -> tuple[WorkspaceDraft, Any]:
    draft = _draft(session, draft_id)
    return draft, _draft_model(session, draft)


@dataclass(frozen=True)
class _MergedObject:
    object_id: str
    application_key: str
    object_type_key: str
    name: str
    parent_object_id: str | None
    attributes: dict[str, Any]
    version: int


@dataclass(frozen=True)
class _MergedRelation:
    relation_id: str
    relation_type_key: str
    from_object_id: str
    to_object_id: str
    attributes: dict[str, Any]
    version: int


@dataclass
class _LiveMerge:
    membership: EffectiveDraftMembership
    authored_object_ids: set[str]
    authored_relation_ids: set[str]
    removed_object_ids: set[str]
    removed_relation_ids: set[str]


def _revision_snapshot_maps(
    session: Session, draft: WorkspaceDraft
) -> tuple[
    dict[str, WorkspaceRevisionObject | WorkspaceDraftBaseObject],
    dict[str, WorkspaceRevisionRelation | WorkspaceDraftBaseRelation],
]:
    """Index the immutable source snapshot by stable id (empty for a legacy root draft)."""
    if draft.base_id is not None:
        base = session.get(WorkspaceDraftBase, draft.base_id)
        if base is None or base.workspace_key != draft.workspace_key:
            raise api_error(
                409,
                "workspace_draft_base_invalid",
                "Workspace draft current-live base is missing or belongs to another workspace",
            )
        return (
            {
                item.object_id: item
                for item in session.scalars(
                    select(WorkspaceDraftBaseObject).where(
                        WorkspaceDraftBaseObject.base_id == base.id
                    )
                )
            },
            {
                item.relation_id: item
                for item in session.scalars(
                    select(WorkspaceDraftBaseRelation).where(
                        WorkspaceDraftBaseRelation.base_id == base.id
                    )
                )
            },
        )
    if draft.derived_from_revision_id is None:
        return {}, {}
    objects = {
        item.object_id: item
        for item in session.scalars(
            select(WorkspaceRevisionObject).where(
                WorkspaceRevisionObject.revision_id == draft.derived_from_revision_id
            )
        )
    }
    relations = {
        item.relation_id: item
        for item in session.scalars(
            select(WorkspaceRevisionRelation).where(
                WorkspaceRevisionRelation.revision_id == draft.derived_from_revision_id
            )
        )
    }
    return objects, relations


def _merge_version_conflict(
    kind: str, conflict_id: str, *, expected: int | None, actual: int | None
) -> dict[str, Any]:
    return {
        "kind": kind,
        "id": conflict_id,
        "code": "version_mismatch",
        "message": f"{kind.title()} changed live after the draft's base revision",
        "expectedVersion": expected,
        "actualVersion": actual,
    }


def _mapping_set_merge_conflicts(
    session: Session,
    draft: WorkspaceDraft,
    model: Any,
    base_objects: dict[str, Any],
    base_relations: dict[str, Any],
    live_objects: dict[str, RdmObject],
    live_relations: dict[str, ObjectRelation],
) -> list[dict[str, Any]]:
    """Compare the complete source/live sets touched by staged mutable relation writes.

    Edge identities and edge versions are the immutable source's fingerprint. This catches
    additions/removals elsewhere in a touched set, which individual COW-row checks miss.
    Containment/ownership retain the existing record and complete-graph merge semantics.
    """
    mutable_bindings = {
        (pair.relationTypeKey, pair.fromObjectTypeKey, pair.toObjectTypeKey)
        for pair in model.objectTypeRelations
        if not _is_parent_pair(model, pair)
        and not (pair.required and pair.cardinality in {"one-to-one", "one-to-many"})
    }
    touched = {
        (
            row.relation_type_key,
            row.from_object_type_key,
            row.to_object_type_key,
            row.anchor_object_id,
            row.direction,
        )
        for row in session.scalars(
            select(RelationSetVersion).where(
                RelationSetVersion.workspace_key == draft.workspace_key,
                RelationSetVersion.workspace_draft_id == draft.id,
            )
        )
        if (row.relation_type_key, row.from_object_type_key, row.to_object_type_key)
        in mutable_bindings
    }
    if not touched:
        return []

    def fingerprints(objects, relations):
        result = {key: {} for key in touched}
        for relation_id, edge in relations.items():
            source, target = objects.get(edge.from_object_id), objects.get(edge.to_object_id)
            if source is None or target is None:
                continue
            binding = (edge.relation_type_key, source.object_type_key, target.object_type_key)
            for anchor, direction in (
                (edge.from_object_id, "outgoing"),
                (edge.to_object_id, "incoming"),
            ):
                key = (*binding, anchor, direction)
                if key in result:
                    result[key][relation_id] = edge.version
        return result

    expected = fingerprints(base_objects, base_relations)
    actual = fingerprints(live_objects, live_relations)
    return [
        {
            "kind": "mapping-set",
            "id": anchor,
            "anchorObjectId": anchor,
            "relationTypeKey": relation_type,
            "fromObjectTypeKey": from_type,
            "toObjectTypeKey": to_type,
            "direction": direction,
            "code": "mapping_set_changed",
            "expectedTargetCount": len(expected[key]),
            "actualTargetCount": len(actual[key]),
            "message": "Mapping relationships changed live since this draft's source. "
            "Review live mappings and reapply the intended changes in a draft created "
            "from current live data before retrying activation.",
        }
        for key in sorted(touched)
        for relation_type, from_type, to_type, anchor, direction in [key]
        if expected[key] != actual[key]
    ]


def _merge_draft_over_live(
    session: Session,
    draft: WorkspaceDraft,
    base_objects: dict[str, WorkspaceRevisionObject | WorkspaceDraftBaseObject],
    base_relations: dict[str, WorkspaceRevisionRelation | WorkspaceDraftBaseRelation],
    model: Any,
) -> _LiveMerge:
    """Compute the live content that would result from applying the draft's delta.

    The current live projection is authoritative and is the substrate; only records the draft
    actually authored (created / edited / tombstoned relative to its derived-from revision) are
    applied onto it.  A draft touch on a base record requires the live record to still sit at the
    exact base-revision version (no concurrent live edit since the snapshot), and a draft-created id
    must not already exist live; any divergence is a per-record conflict (``409 version_conflict``)
    rather than an overwrite.  Live content the draft never touched is preserved untouched.
    """
    workspace_key = draft.workspace_key
    live_objects = {
        item.id: item
        for item in session.scalars(
            select(RdmObject).where(RdmObject.workspace_key == workspace_key)
        )
    }
    object_ids = sorted(live_objects)
    attribute_rows = load_attribute_values(session, object_ids)
    merged_objects: dict[str, _MergedObject] = {}
    for object_id in object_ids:
        live = live_objects[object_id]
        merged_objects[object_id] = _MergedObject(
            object_id=object_id,
            application_key=live.application_key,
            object_type_key=live.object_type_key,
            name=live.name,
            parent_object_id=live.parent_object_id,
            attributes={key: value for key, (_row_id, value) in attribute_rows[object_id].items()},
            version=live.version,
        )
    live_relations: dict[str, ObjectRelation] = {}
    if object_ids:
        live_relations = {
            item.id: item
            for item in session.scalars(
                select(ObjectRelation).where(
                    or_(
                        ObjectRelation.from_object_id.in_(object_ids),
                        ObjectRelation.to_object_id.in_(object_ids),
                    )
                )
            )
        }
    merged_relations: dict[str, _MergedRelation] = {
        relation_id: _MergedRelation(
            relation_id=relation_id,
            relation_type_key=relation.relation_type_key,
            from_object_id=relation.from_object_id,
            to_object_id=relation.to_object_id,
            attributes=dict(relation.attributes or {}),
            version=relation.version,
        )
        for relation_id, relation in live_relations.items()
    }

    mapping_conflicts = _mapping_set_merge_conflicts(
        session, draft, model, base_objects, base_relations, live_objects, live_relations
    )
    conflicts: list[dict[str, Any]] = mapping_conflicts[:20]
    authored_object_ids: set[str] = set()
    draft_objects = {
        item.object_id: item
        for item in session.scalars(
            select(WorkspaceDraftObject).where(WorkspaceDraftObject.draft_id == draft.id)
        )
    }
    global_object_ids = set(
        session.scalars(select(RdmObject.id).where(RdmObject.id.in_(draft_objects)))
    )
    for object_id, row in draft_objects.items():
        base = base_objects.get(object_id)
        if row.is_deleted:
            if base is None:
                continue  # created then deleted inside the draft: never reached live
            live = live_objects.get(object_id)
            if live is not None and live.version != base.version:
                conflicts.append(
                    _merge_version_conflict(
                        "object", object_id, expected=base.version, actual=live.version
                    )
                )
            merged_objects.pop(object_id, None)
            continue
        authored_object_ids.add(object_id)
        authored = _MergedObject(
            object_id=object_id,
            application_key=row.application_key,
            object_type_key=row.object_type_key,
            name=row.name,
            parent_object_id=row.parent_object_id,
            attributes=dict(row.attributes or {}),
            version=row.version,
        )
        if base is not None:
            live = live_objects.get(object_id)
            if live is None or live.version != base.version:
                conflicts.append(
                    _merge_version_conflict(
                        "object",
                        object_id,
                        expected=base.version,
                        actual=live.version if live is not None else None,
                    )
                )
            merged_objects[object_id] = authored
        else:
            if object_id in global_object_ids:
                conflicts.append(
                    {
                        "kind": "object",
                        "id": object_id,
                        "code": "id_collision",
                        "message": "Draft-created object id already exists in live data",
                    }
                )
            merged_objects[object_id] = authored

    authored_relation_ids: set[str] = set()
    draft_relations = {
        item.relation_id: item
        for item in session.scalars(
            select(WorkspaceDraftRelation).where(WorkspaceDraftRelation.draft_id == draft.id)
        )
    }
    global_relation_ids = set(
        session.scalars(select(ObjectRelation.id).where(ObjectRelation.id.in_(draft_relations)))
    )
    for relation_id, row in draft_relations.items():
        base = base_relations.get(relation_id)
        if row.is_deleted:
            if base is None:
                continue
            live = live_relations.get(relation_id)
            if live is not None and live.version != base.version:
                conflicts.append(
                    _merge_version_conflict(
                        "relation", relation_id, expected=base.version, actual=live.version
                    )
                )
            merged_relations.pop(relation_id, None)
            continue
        authored_relation_ids.add(relation_id)
        authored = _MergedRelation(
            relation_id=relation_id,
            relation_type_key=row.relation_type_key,
            from_object_id=row.from_object_id,
            to_object_id=row.to_object_id,
            attributes=dict(row.attributes or {}),
            version=row.version,
        )
        if base is not None:
            live = live_relations.get(relation_id)
            if live is None or live.version != base.version:
                conflicts.append(
                    _merge_version_conflict(
                        "relation",
                        relation_id,
                        expected=base.version,
                        actual=live.version if live is not None else None,
                    )
                )
            merged_relations[relation_id] = authored
        else:
            if relation_id in global_relation_ids:
                conflicts.append(
                    {
                        "kind": "relation",
                        "id": relation_id,
                        "code": "id_collision",
                        "message": "Draft-created relation id already exists in live data",
                    }
                )
            merged_relations[relation_id] = authored

    # A tombstoned object drops its incident live relations even when the draft never saw them; a
    # live relation cannot outlive an endpoint.  Any other dangling endpoint would fail whole-graph
    # validation below and abort the activation before any row is touched.
    for relation_id in [
        relation_id
        for relation_id, relation in merged_relations.items()
        if relation.from_object_id not in merged_objects
        or relation.to_object_id not in merged_objects
    ]:
        merged_relations.pop(relation_id, None)

    # The live table enforces one directed edge per (type, from, to).  A draft edge duplicating a
    # live one (distinct ids) would violate that constraint mid-apply; surface it as a conflict
    # instead of leaking an IntegrityError out of the activation transaction.
    seen_edges: dict[tuple[str, str, str], str] = {}
    for relation_id in sorted(merged_relations):
        relation = merged_relations[relation_id]
        edge = (relation.relation_type_key, relation.from_object_id, relation.to_object_id)
        prior = seen_edges.get(edge)
        if prior is not None:
            conflicts.append(
                {
                    "kind": "relation",
                    "id": relation_id,
                    "conflictingRelationId": prior,
                    "code": "duplicate_edge",
                    "message": "Draft and live both define the same directed relation",
                }
            )
        else:
            seen_edges[edge] = relation_id

    if conflicts:
        raise api_error(
            409,
            "version_conflict",
            "Workspace draft conflicts with the live active data",
            {
                "conflicts": conflicts,
                "mappingSetConflictCount": len(mapping_conflicts),
                "mappingSetConflictsTruncated": len(mapping_conflicts) > 20,
            },
        )
    membership = EffectiveDraftMembership(
        draft=draft,
        objects=tuple(sorted(merged_objects.values(), key=lambda item: item.object_id)),
        relations=tuple(sorted(merged_relations.values(), key=lambda item: item.relation_id)),
    )
    return _LiveMerge(
        membership=membership,
        authored_object_ids=authored_object_ids,
        authored_relation_ids=authored_relation_ids,
        removed_object_ids=set(live_objects) - set(merged_objects),
        removed_relation_ids=set(live_relations) - set(merged_relations),
    )


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
    # Claim before reading the merge population. On SQLite this also obtains the writer lock,
    # keeping the live graph stable until the publication transaction completes.
    _claim_draft(session, draft, expected_draft_version)
    workspace = session.scalar(
        select(Workspace).where(Workspace.key == draft.workspace_key).with_for_update()
    )
    if workspace is None:
        raise api_error(404, "workspace_not_found", "Workspace not found")
    if workspace.active_revision_id != expected_active_revision_id:
        raise api_error(
            409, "workspace_active_revision_conflict", "Active workspace revision has changed"
        )
    # The draft is applied as a delta onto the *current* live projection, then the merged graph is
    # validated whole before anything is written; live content newer than the draft base is preserved.
    merged = _merge_draft_over_live(
        session,
        draft,
        *_revision_snapshot_maps(session, draft),
        model,
    )
    diagnostics = _diagnostics(merged.membership, model)
    if diagnostics:
        raise api_error(
            422,
            "workspace_graph_invalid",
            "Workspace draft failed complete graph validation over the live active data",
            diagnostics,
        )
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
    for item in merged.membership.objects:
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
    for item in merged.membership.relations:
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
    record_revision_activated(
        session,
        revision=revision,
        draft=draft,
        object_count=len(merged.membership.objects),
        relation_count=len(merged.membership.relations),
    )
    # Apply only the delta onto the live projection: remove tombstoned rows, upsert the authored
    # objects and relations, and leave every untouched live row exactly as it is.
    if merged.removed_relation_ids:
        session.execute(
            delete(ObjectRelation).where(ObjectRelation.id.in_(merged.removed_relation_ids))
        )
    if merged.removed_object_ids:
        # The parent FK is RESTRICT; detach the removed rows from each other so bulk deletion cannot
        # trip the constraint regardless of parent/child ordering.
        # Surviving authored children may still point at a tombstoned parent.  Detach them before
        # deleting the removed rows; their final parent is assigned after all upserts exist.
        session.execute(
            update(RdmObject)
            .where(
                RdmObject.parent_object_id.in_(merged.removed_object_ids),
                ~RdmObject.id.in_(merged.removed_object_ids),
            )
            .values(parent_object_id=None)
        )
        session.execute(
            update(RdmObject)
            .where(RdmObject.id.in_(merged.removed_object_ids))
            .values(parent_object_id=None)
        )
        session.execute(
            delete(AttributeValue).where(AttributeValue.object_id.in_(merged.removed_object_ids))
        )
        session.execute(delete(RdmObject).where(RdmObject.id.in_(merged.removed_object_ids)))
    authored_objects = {
        item.object_id: item
        for item in merged.membership.objects
        if item.object_id in merged.authored_object_ids
    }
    live_objects = {
        item.id: item
        for item in session.scalars(
            select(RdmObject).where(RdmObject.workspace_key == draft.workspace_key)
        )
    }
    for object_id in sorted(authored_objects):
        authored = authored_objects[object_id]
        live = live_objects.get(object_id)
        if live is None:
            live = RdmObject(
                id=object_id,
                workspace_key=draft.workspace_key,
                application_key=authored.application_key,
                object_type_key=authored.object_type_key,
                name=authored.name,
                parent_object_id=None,
                version=authored.version,
            )
            session.add(live)
            session.flush()
        else:
            live.application_key = authored.application_key
            live.object_type_key = authored.object_type_key
            live.name = authored.name
            live.version = authored.version
    session.flush()
    for object_id in sorted(authored_objects):
        authored = authored_objects[object_id]
        attribute_delete = delete(AttributeValue).where(AttributeValue.object_id == object_id)
        if authored.attributes:
            attribute_delete = attribute_delete.where(
                ~AttributeValue.attribute_type_key.in_(set(authored.attributes))
            )
        session.execute(attribute_delete)
        save_attribute_values(session, model, object_id, authored.attributes or {})
    session.flush()
    for object_id in sorted(authored_objects):
        # Set containment pointers only after every merged object row exists (whole-graph validation
        # guarantees the parent is present in the merged graph) so a new parent never precedes its row.
        authored = authored_objects[object_id]
        live = session.scalar(select(RdmObject).where(RdmObject.id == object_id))
        live.parent_object_id = authored.parent_object_id
    for authored in sorted(
        (
            item
            for item in merged.membership.relations
            if item.relation_id in merged.authored_relation_ids
        ),
        key=lambda item: item.relation_id,
    ):
        live = session.scalar(
            select(ObjectRelation).where(ObjectRelation.id == authored.relation_id)
        )
        if live is None:
            session.add(
                ObjectRelation(
                    id=authored.relation_id,
                    relation_type_key=authored.relation_type_key,
                    from_object_id=authored.from_object_id,
                    to_object_id=authored.to_object_id,
                    attributes=authored.attributes or {},
                    version=authored.version,
                )
            )
        else:
            live.relation_type_key = authored.relation_type_key
            live.from_object_id = authored.from_object_id
            live.to_object_id = authored.to_object_id
            live.attributes = authored.attributes or {}
            live.version = authored.version
    if workspace.active_revision_id:
        old = session.scalar(
            select(WorkspaceRevision).where(WorkspaceRevision.id == workspace.active_revision_id)
        )
        old.status = "retired"
        old.retired_at = datetime.now(UTC)
    revision.activated_at = datetime.now(UTC)
    workspace.active_revision_id = revision.id
    merge_draft_set_versions_to_live(session, draft.id, draft.workspace_key)
    _delete_draft_and_base(session, draft)
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
    if workspace.status == "retired":
        raise api_error(409, "workspace_retired", "Workspace is retired and cannot be mutated")
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
    # Record the publication retirement identity in the same transaction as the pointer clear and
    # revision retire so a rolled-back retirement never leaves an orphan event (D3a).  The event is
    # aggregated on the workspace key and carries no AuditEventSubject rows.
    record_publication_retired(session, revision=revision)
    session.commit()
