"""WP8 workspace lifecycle orchestration over ADR-024 persistence.

WP8 owns the workspace-scoped change set / validation / publish / withdrawal lifecycle on top of
the WP6 copy-on-write storage layout. Objects and relations are ordinary live records; optional
staged edits use the canonical routers with ``changeSetId``. Publishing merges authored changes into
live data and records an immutable publication (ADR-026/027/031).
"""

from collections.abc import Callable
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
    ChangeSet,
    ChangeSetBase,
    ChangeSetBaseObject,
    ChangeSetBaseRelation,
    ChangeSetObject,
    ChangeSetRelation,
    ModelRelease,
    ModelRuntimeState,
    ObjectRelation,
    Publication,
    PublicationObject,
    PublicationRelation,
    RdmObject,
    RelationSetVersion,
    Workspace,
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
from .change_set_lookups import ChangeSetLookup
from .model.registry import resolve_pinned_release
from .relation_set_versions import (
    delete_change_set_relation_set_versions,
    increment_set_versions,
    merge_change_set_relation_set_versions_to_live,
)
from .relations import validate_relation_attributes
from .snapshot_values import delete_owner_values
from .workspace_audit import (
    record_change_set_created,
    record_change_set_derived,
    record_change_set_discarded,
    record_change_set_published,
    record_change_set_renamed,
    record_publication_withdrawn,
)


@dataclass(frozen=True)
class EffectiveChangeSetMembership:
    change_set: ChangeSet
    objects: tuple[PublicationObject | ChangeSetBaseObject | ChangeSetObject, ...]
    relations: tuple[
        PublicationRelation | ChangeSetBaseRelation | ChangeSetRelation, ...
    ]


def effective_change_set_membership(session: Session, change_set_id: str) -> EffectiveChangeSetMembership:
    """Resolve a change set's immutable base plus its changed rows and tombstones.

    A change set row replaces the same stable public ID from its base.  A tombstone hides that base row;
    therefore an edit does not copy unrelated records from the source publication.
    """
    change_set = session.scalar(select(ChangeSet).where(ChangeSet.id == change_set_id))
    if change_set is None:
        raise api_error(404, "change_set_not_found", f"Change set '{change_set_id}' not found")
    objects: dict[
        str, PublicationObject | ChangeSetBaseObject | ChangeSetObject
    ] = {}
    relations: dict[
        str, PublicationRelation | ChangeSetBaseRelation | ChangeSetRelation
    ] = {}
    if change_set.derived_from_publication_id is not None:
        publication = session.scalar(
            select(Publication).where(Publication.id == change_set.derived_from_publication_id)
        )
        if publication is None or publication.workspace_key != change_set.workspace_key:
            raise api_error(
                409,
                "change_set_base_invalid",
                "Change set base publication is missing or belongs to another workspace",
            )
        objects = {
            item.object_id: item
            for item in session.scalars(
                select(PublicationObject).where(
                    PublicationObject.publication_id == publication.id
                )
            )
        }
        relations = {
            item.relation_id: item
            for item in session.scalars(
                select(PublicationRelation).where(
                    PublicationRelation.publication_id == publication.id
                )
            )
        }
    if change_set.base_id is not None:
        base = session.get(ChangeSetBase, change_set.base_id)
        if base is None or base.workspace_key != change_set.workspace_key:
            raise api_error(
                409,
                "change_set_base_invalid",
                "Change set current-live base is missing or belongs to another workspace",
            )
        objects = {
            item.object_id: item
            for item in session.scalars(
                select(ChangeSetBaseObject).where(ChangeSetBaseObject.base_id == base.id)
            )
        }
        relations = {
            item.relation_id: item
            for item in session.scalars(
                select(ChangeSetBaseRelation).where(
                    ChangeSetBaseRelation.base_id == base.id
                )
            )
        }
    for item in session.scalars(
        select(ChangeSetObject).where(ChangeSetObject.change_set_id == change_set.id)
    ):
        if item.is_deleted:
            objects.pop(item.object_id, None)
        else:
            objects[item.object_id] = item
    for item in session.scalars(
        select(ChangeSetRelation).where(ChangeSetRelation.change_set_id == change_set.id)
    ):
        if item.is_deleted:
            relations.pop(item.relation_id, None)
        else:
            relations[item.relation_id] = item
    return EffectiveChangeSetMembership(
        change_set=change_set,
        objects=tuple(objects[key] for key in sorted(objects)),
        relations=tuple(relations[key] for key in sorted(relations)),
    )


def _change_set(session: Session, change_set_id: str, *, for_update: bool = False) -> ChangeSet:
    statement = select(ChangeSet).where(ChangeSet.id == change_set_id)
    if for_update:
        statement = statement.with_for_update()
    item = session.scalar(statement)
    if item is None:
        raise api_error(404, "change_set_not_found", f"Change set '{change_set_id}' not found")
    if for_update:
        workspace = session.get(Workspace, item.workspace_key)
        if workspace is None:
            raise api_error(
                404, "workspace_not_found", f"Workspace '{item.workspace_key}' not found"
            )
        if workspace.status != "active":
            raise api_error(409, "workspace_retired", "Workspace is retired and cannot be mutated")
    return item


def ensure_change_set_writable(session: Session, change_set_id: str) -> ChangeSet:
    """Resolve a change set and reject mutations against a retired workspace."""
    return _change_set(session, change_set_id, for_update=True)


def claim_change_set_version(session: Session, change_set: ChangeSet, expected: int) -> None:
    """Claim the change set aggregate version for an external write operation."""
    _claim_change_set(session, change_set, expected)


def _claim_change_set(
    session: Session,
    change_set: ChangeSet,
    expected: int,
    *,
    conflict_code: str = "change_set_version_conflict",
    conflict_message: str = "Change set version has changed",
) -> None:
    if change_set.version != expected:
        raise api_error(409, conflict_code, conflict_message)
    # SQLite ignores FOR UPDATE; claim the aggregate in SQL before flushing candidate writes.
    with session.no_autoflush:
        result = session.execute(
            update(ChangeSet)
            .where(ChangeSet.id == change_set.id, ChangeSet.version == expected)
            .values(version=expected + 1, updated_at=datetime.now(UTC))
            .execution_options(synchronize_session=False)
        )
        if result.rowcount != 1:
            raise api_error(409, conflict_code, conflict_message)
        session.refresh(change_set, attribute_names=["version", "updated_at"])


def create_change_set(
    session: Session,
    workspace_key: str,
    model_release_id: int,
    *,
    name: str | None = None,
    source_publication_id: str | None = None,
    source: str | None = None,
    expected_model_runtime_release_id: int | None = None,
    validate_selected_model: bool = False,
) -> ChangeSet:
    if source not in (None, "currentLive", "publication"):
        raise api_error(422, "change_set_source_invalid", "Change set source is invalid")
    if source == "publication" and source_publication_id is None:
        raise api_error(
            422,
            "change_set_source_invalid",
            "A publication source requires a publication id",
        )
    if source == "currentLive" and source_publication_id is not None:
        raise api_error(
            422,
            "change_set_source_invalid",
            "A current-live source cannot include a publication id",
        )
    if source == "currentLive":
        return _create_current_live_change_set(
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
    if source_publication_id is not None:
        publication = session.scalar(
            select(Publication).where(Publication.id == source_publication_id)
        )
        if publication is None or publication.workspace_key != workspace_key:
            raise api_error(
                404, "publication_not_found", "Source publication was not found"
            )
        model_release_id = publication.model_release_id
    change_set = ChangeSet(
        workspace_key=workspace_key,
        model_release_id=model_release_id,
        derived_from_publication_id=source_publication_id,
        name=name,
    )
    session.add(change_set)
    session.flush()
    if validate_selected_model:
        require_change_set_compatible(session, change_set, _change_set_model(session, change_set))
    if source_publication_id is not None:
        record_change_set_derived(session, change_set=change_set)
    else:
        record_change_set_created(session, change_set=change_set)
    session.commit()
    session.refresh(change_set)
    return change_set


def _create_current_live_change_set(
    session: Session,
    workspace_key: str,
    model_release_id: int,
    *,
    name: str | None,
    expected_model_runtime_release_id: int | None,
    validate_selected_model: bool,
) -> ChangeSet:
    """Capture one private base under SQLite's database-wide writer reservation.

    SQLite is the supported Base 0.6 runtime database.  ``BEGIN IMMEDIATE`` prevents a concurrent
    live writer (including model activation) from committing between graph rows, attributes, edges and
    the runtime-state comparison.  Other dialects are refused until their equivalent capture protocol
    is implemented, rather than silently returning a weaker mixed snapshot.
    """
    if session.bind is None or session.bind.dialect.name != "sqlite":
        raise api_error(
            409,
            "change_set_snapshot_unsupported",
            "Current-live change set capture is supported only on SQLite in this release",
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
            "change_set_snapshot_retry",
            "Current live data is busy; retry starting the change set after the active write finishes",
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
                "change_set_snapshot_retry",
                "The selected model changed before current-live capture; retry with the current model",
            )
        base = ChangeSetBase(
            workspace_key=workspace_key,
            model_release_id=state.active_model_release_id,
            model_runtime_version=state.version,
        )
        session.add(base)
        session.flush()
        live_objects, attributes, live_relations = _load_live_membership(session, workspace_key)
        for item in live_objects:
            session.add(
                ChangeSetBaseObject(
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
                ChangeSetBaseRelation(
                    base_id=base.id,
                    relation_id=item.id,
                    relation_type_key=item.relation_type_key,
                    from_object_id=item.from_object_id,
                    to_object_id=item.to_object_id,
                    attributes=dict(item.attributes or {}),
                    version=item.version,
                )
            )
        change_set = ChangeSet(
            workspace_key=workspace_key,
            model_release_id=model_release_id,
            base_id=base.id,
            name=name,
        )
        session.add(change_set)
        session.flush()
        if validate_selected_model:
            require_change_set_compatible(
                session,
                change_set,
                _change_set_model(session, change_set),
                source_release_id=base.model_release_id,
            )
        record_change_set_created(session, change_set=change_set)
        session.commit()
        session.refresh(change_set)
        return change_set
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


def update_change_set(
    session: Session, change_set_id: str, expected_version: int, name: str | None
) -> ChangeSet:
    change_set = _change_set(session, change_set_id, for_update=True)
    previous_name = change_set.name
    _claim_change_set(session, change_set, expected_version)
    if previous_name != name:
        record_change_set_renamed(session, change_set=change_set, from_name=previous_name, to_name=name)
    change_set.name = name
    session.commit()
    return change_set


def discard_change_set(session: Session, change_set_id: str, expected_version: int) -> None:
    change_set = _change_set(session, change_set_id, for_update=True)
    _claim_change_set(session, change_set, expected_version)
    record_change_set_discarded(session, change_set=change_set)
    _delete_change_set_and_base(session, change_set)
    session.commit()


def _delete_change_set_and_base(session: Session, change_set: ChangeSet) -> None:
    """Remove a private base explicitly because SQLite does not enable FK cascades by default."""
    base_id = change_set.base_id
    delete_change_set_relation_set_versions(session, change_set.id)
    delete_owner_values(session, change_set.id)
    session.delete(change_set)
    session.flush()
    if base_id is None:
        return
    delete_owner_values(session, base_id)
    session.execute(
        delete(ChangeSetBaseRelation).where(ChangeSetBaseRelation.base_id == base_id)
    )
    session.execute(
        delete(ChangeSetBaseObject).where(ChangeSetBaseObject.base_id == base_id)
    )
    session.execute(delete(ChangeSetBase).where(ChangeSetBase.id == base_id))


def _record_conflict(expected: int | None, actual: int, label: str) -> None:
    if expected is not None and expected != actual:
        raise api_error(409, "version_conflict", f"{label} version has changed")


def _change_set_model(session: Session, change_set: ChangeSet) -> Any:
    return resolve_pinned_release(session, change_set.model_release_id, require_ready=False).model


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
    # Change set rows are JSON; store the same form that current-live capture copies from live rows.
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
    excluded = {exclude_id, *(exclude_ids or set())}

    def existing(object_id: str, direction: str) -> list[Any]:
        return [
            row
            for row in lookup.relations([object_id], direction, [relation_type_key])
            if row.relation_id not in excluded
        ]

    if allowed.cardinality == "one-to-one" and (
        existing(from_id, "outgoing") or existing(to_id, "incoming")
    ):
        raise api_error(409, "cardinality_violation", "Relation cardinality would be violated")
    if allowed.cardinality == "one-to-many" and existing(to_id, "incoming"):
        raise api_error(409, "cardinality_violation", "Relation cardinality would be violated")
    ancestor_type = allowed.features.get("uniqueToAncestorTypeKey")
    if ancestor_type:
        condition = allowed.features.get("uniqueWhenToAttributeEquals")

        def in_scope(item: Any) -> bool:
            return (
                not condition
                or (item.attributes or {}).get(condition["attributeTypeKey"]) == condition["value"]
            )

        if not in_scope(target):
            return normalized
        target_ancestor = lookup.ancestor_of_type(target, ancestor_type)
        if target_ancestor is None:
            raise api_error(
                422,
                "relation_ancestor_required",
                f"Related object must belong to an ancestor of type '{ancestor_type}'",
            )
        # Only the source's own relations of this type can share the scope.
        related = lookup.objects(row.to_object_id for row in existing(from_id, "outgoing"))
        scoped = [item for item in related.values() if in_scope(item)]
        if target_ancestor in lookup.ancestors_of_type(scoped, ancestor_type).values():
            raise api_error(
                409,
                "duplicate_relation_scope",
                "A related object already exists for this ancestor scope",
            )
    return normalized


def put_change_set_object(session: Session, change_set_id: str, payload: Any) -> ChangeSetObject:
    change_set = _change_set(session, change_set_id, for_update=True)
    model = _change_set_model(session, change_set)
    _validate_object_identity(model, payload.applicationKey, payload.objectTypeKey)
    attributes = _normalize_object_attributes(
        model, payload.objectTypeKey, payload.attributes, partial=False
    )
    validate_object_attribute_rules(model.object_type(payload.objectTypeKey), attributes)
    lookup = ChangeSetLookup.of(session, change_set_id)
    if payload.parentObjectId is not None and lookup.object(str(payload.parentObjectId)) is None:
        raise api_error(422, "parent_wrong_scope", "Parent must exist in the change set")
    _claim_change_set(session, change_set, payload.expectedChangeSetVersion)
    object_id = str(payload.id) if payload.id else str(uuid4())
    if lookup.object(object_id) is not None or session.scalar(
        select(RdmObject.id).where(RdmObject.id == object_id)
    ):
        raise api_error(409, "object_already_exists", f"Object '{object_id}' already exists")
    row = session.scalar(
        select(ChangeSetObject).where(
            ChangeSetObject.change_set_id == change_set_id, ChangeSetObject.object_id == object_id
        )
    )
    if row is not None:
        raise api_error(409, "object_already_exists", f"Object '{object_id}' already exists")
    else:
        if payload.expectedRecordVersion is not None:
            raise api_error(409, "version_conflict", "Object record does not exist")
        row = ChangeSetObject(
            change_set_id=change_set_id,
            object_id=object_id,
            application_key=payload.applicationKey,
            object_type_key=payload.objectTypeKey,
            name=payload.name,
            parent_object_id=str(payload.parentObjectId) if payload.parentObjectId else None,
            attributes=attributes,
            version=1,
        )
        session.add(row)
    _validate_change_set_attribute_uniqueness(model, lookup, row.object_id, attributes)
    _sync_change_set_parent_relation(session, change_set, model, row, lookup)
    if getattr(payload, "initialRelations", None):
        identities = [
            (item.relationTypeKey, item.direction, str(item.otherObjectId))
            for item in payload.initialRelations
        ]
        if len(identities) != len(set(identities)):
            raise api_error(
                422, "duplicate_initial_relation", "Initial relationships must not repeat"
            )
        # The new row and each relation added before the next are flushed into the lookups.
        for initial in payload.initialRelations:
            from_id = (
                row.object_id if initial.direction == "outgoing" else str(initial.otherObjectId)
            )
            to_id = str(initial.otherObjectId) if initial.direction == "outgoing" else row.object_id
            attrs = validate_change_set_relation(
                model, lookup, initial.relationTypeKey, from_id, to_id, initial.attributes
            )
            relation = ChangeSetRelation(
                change_set_id=change_set.id,
                relation_id=str(uuid4()),
                relation_type_key=initial.relationTypeKey,
                from_object_id=from_id,
                to_object_id=to_id,
                attributes=attrs,
                version=1,
            )
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
        aggregate_type="change-set-object",
        aggregate_id=row.object_id,
        action="created",
        version=row.version,
        changes={"attributes": attributes, "changeSetId": change_set.id},
        object_ids=[row.object_id],
    )
    session.commit()
    return row


def update_change_set_object(
    session: Session, change_set_id: str, object_id: str, payload: Any
) -> ChangeSetObject:
    change_set = _change_set(session, change_set_id, for_update=True)
    model = _change_set_model(session, change_set)
    lookup = ChangeSetLookup.of(session, change_set_id)
    _claim_change_set(session, change_set, payload.expectedChangeSetVersion)
    row = session.scalar(
        select(ChangeSetObject).where(
            ChangeSetObject.change_set_id == change_set_id, ChangeSetObject.object_id == object_id
        )
    )
    if row is None:
        base = lookup.object(object_id)
        if base is None:
            raise api_error(404, "object_not_found", f"Object '{object_id}' not found in change set")
        row = ChangeSetObject(
            change_set_id=change_set_id,
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
    _validate_change_set_attribute_uniqueness(model, lookup, row.object_id, row.attributes or {})
    # The edited row is flushed into the lookups: each relation into it is checked against it.
    parent_keys = set(
        (model.object_type(row.object_type_key).behavior or {}).get("parentRelationTypeKeys", [])
    )
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
    _sync_change_set_parent_relation(session, change_set, model, row, lookup)
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
    from .deletion import (
        deletion_preview_changed,
        deletion_preview_token,
        require_deletion_preview,
        require_matching_deletion_preview,
    )

    if cascade:
        require_deletion_preview(deletion_preview)

    change_set = _change_set(session, change_set_id, for_update=True)
    model = _change_set_model(session, change_set)
    # The aggregate claim serializes all change set mutations before the hierarchy is re-read. A preview
    # response rolls this claim back; a confirmed delete retains it in the mutation transaction.
    _claim_change_set(
        session,
        change_set,
        expected_change_set_version,
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
        raise api_error(404, "object_not_found", f"Object '{object_id}' not found in change set")
    if cascade and deletion_preview is not None and expected_record_version != root.version:
        raise api_error(
            409,
            "deletion_preview_changed",
            "The object was modified by another session. Please retry.",
        )
    _record_conflict(expected_record_version, root.version, "Object record")

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
    for deleted_id in planned_ids:
        base = objects[deleted_id]
        row = session.scalar(
            select(ChangeSetObject).where(
                ChangeSetObject.change_set_id == change_set_id,
                ChangeSetObject.object_id == deleted_id,
            )
        )
        if row is None:
            row = ChangeSetObject(
                change_set_id=change_set_id,
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
            select(ChangeSetRelation).where(
                ChangeSetRelation.change_set_id == change_set_id,
                ChangeSetRelation.relation_id == relation.relation_id,
            )
        )
        if row is None:
            row = ChangeSetRelation(
                change_set_id=change_set_id,
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
            workspace_key=change_set.workspace_key,
            change_set_id=change_set.id,
            relation_type_key=relation.relation_type_key,
            from_object_type_key=objects[relation.from_object_id].object_type_key,
            to_object_type_key=objects[relation.to_object_id].object_type_key,
            from_object_id=relation.from_object_id,
            to_object_id=relation.to_object_id,
        )
    session.commit()


def _validate_change_set_attribute_uniqueness(
    model: Any,
    lookup: ChangeSetLookup,
    object_id: str,
    attributes: dict[str, Any],
) -> None:
    for key, value in attributes.items():
        definition = model.attribute_type(key)
        if definition is None or not definition.features.get("unique") or value is None:
            continue
        conflict = lookup.unique_value_holder(
            key, definition.valueType, value, exclude_object_id=object_id
        )
        if conflict is not None:
            raise api_error(
                409,
                "duplicate_attribute_value",
                f"Attribute '{key}' must be unique in the change set",
                {"attributeTypeKey": key, "conflictingObjectId": conflict},
            )


def _validate_candidate_parent(
    model: Any, row: Any, find: Callable[[str | None], Any | None]
) -> None:
    """Check a record's parent; ``find`` reads a record of the same graph by ID, or ``None``."""
    object_type = model.object_type(row.object_type_key)
    if row.parent_object_id is None:
        if not object_type.features.get("rootCreatable", False):
            raise api_error(422, "parent_required", "This object type requires a parent")
        return
    parent = find(row.parent_object_id)
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
        current = find(current.parent_object_id)


def _sync_change_set_parent_relation(
    session: Session,
    change_set: ChangeSet,
    model: Any,
    row: ChangeSetObject,
    lookup: ChangeSetLookup,
) -> None:
    """Maintain the typed containment edge with a change set object edit.

    The effective edge may come from the change set base; like a live update, an unchanged parent keeps
    that edge and its identity, and a changed parent tombstones it before adding the new one.
    """
    # The ancestor walk is one lookup per level; the row itself is read as edited.
    _validate_candidate_parent(
        model,
        row,
        lambda object_id: row if object_id == row.object_id else lookup.object(object_id),
    )
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
    current = lookup.relations([row.object_id], "incoming", sorted(keys))
    if [relation.from_object_id for relation in current] == (
        [row.parent_object_id] if row.parent_object_id else []
    ):
        return
    for relation in current:
        stored = session.scalar(
            select(ChangeSetRelation).where(
                ChangeSetRelation.change_set_id == change_set.id,
                ChangeSetRelation.relation_id == relation.relation_id,
            )
        )
        if stored is None:
            session.add(
                ChangeSetRelation(
                    change_set_id=change_set.id,
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
        parent = lookup.object(row.parent_object_id)
        if parent is None:
            raise api_error(422, "parent_wrong_scope", "Parent must exist in the change set")
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
            ChangeSetRelation(
                change_set_id=change_set.id,
                relation_id=str(uuid4()),
                relation_type_key=allowed.relationTypeKey,
                from_object_id=parent.object_id,
                to_object_id=row.object_id,
                attributes={},
                version=1,
            )
        )


def _increment_change_set_relation_set_versions(
    session: Session,
    change_set: ChangeSet,
    lookup: ChangeSetLookup,
    row: ChangeSetRelation,
) -> None:
    objects = lookup.objects([row.from_object_id, row.to_object_id])
    from_obj = objects.get(row.from_object_id)
    to_obj = objects.get(row.to_object_id)
    if from_obj is None or to_obj is None:
        return
    increment_set_versions(
        session,
        workspace_key=change_set.workspace_key,
        change_set_id=change_set.id,
        relation_type_key=row.relation_type_key,
        from_object_type_key=from_obj.object_type_key,
        to_object_type_key=to_obj.object_type_key,
        from_object_id=row.from_object_id,
        to_object_id=row.to_object_id,
    )


def put_change_set_relation(session: Session, change_set_id: str, payload: Any) -> ChangeSetRelation:
    change_set = _change_set(session, change_set_id, for_update=True)
    model = _change_set_model(session, change_set)
    lookup = ChangeSetLookup.of(session, change_set_id)
    relation_id = str(payload.id) if payload.id else str(uuid4())
    row = session.scalar(
        select(ChangeSetRelation).where(
            ChangeSetRelation.change_set_id == change_set_id,
            ChangeSetRelation.relation_id == relation_id,
        )
    )
    attributes = validate_change_set_relation(
        model,
        lookup,
        payload.relationTypeKey,
        str(payload.fromObjectId),
        str(payload.toObjectId),
        payload.attributes,
    )
    _claim_change_set(session, change_set, payload.expectedChangeSetVersion)
    if row is None:
        row = ChangeSetRelation(
            change_set_id=change_set_id,
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
        changes={"attributes": attributes, "changeSetId": change_set.id},
        object_ids=[row.from_object_id, row.to_object_id],
    )
    _increment_change_set_relation_set_versions(session, change_set, lookup, row)
    session.commit()
    return row


def update_change_set_relation(
    session: Session, change_set_id: str, relation_id: str, payload: Any
) -> ChangeSetRelation:
    change_set = _change_set(session, change_set_id, for_update=True)
    model = _change_set_model(session, change_set)
    row = session.scalar(
        select(ChangeSetRelation).where(
            ChangeSetRelation.change_set_id == change_set_id,
            ChangeSetRelation.relation_id == relation_id,
        )
    )
    lookup = ChangeSetLookup.of(session, change_set_id)
    if row is None:
        base = lookup.relation(relation_id)
        if base is None:
            raise api_error(
                404, "relation_not_found", f"Relation '{relation_id}' not found in change set"
            )
        row = ChangeSetRelation(
            change_set_id=change_set_id,
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
    relation_type = payload.relationTypeKey or row.relation_type_key
    from_id = str(payload.fromObjectId) if payload.fromObjectId else row.from_object_id
    to_id = str(payload.toObjectId) if payload.toObjectId else row.to_object_id
    attrs = row.attributes or {}
    if payload.attributes is not None:
        attrs = payload.attributes
    attrs = validate_change_set_relation(
        model, lookup, relation_type, from_id, to_id, attrs, exclude_id=relation_id
    )
    _claim_change_set(session, change_set, payload.expectedChangeSetVersion)
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
    _increment_change_set_relation_set_versions(session, change_set, lookup, row)
    session.commit()
    return row


def delete_change_set_relation(
    session: Session,
    change_set_id: str,
    relation_id: str,
    expected_change_set_version: int,
    expected_record_version: int,
) -> None:
    change_set = _change_set(session, change_set_id, for_update=True)
    model = _change_set_model(session, change_set)
    row = session.scalar(
        select(ChangeSetRelation).where(
            ChangeSetRelation.change_set_id == change_set_id,
            ChangeSetRelation.relation_id == relation_id,
        )
    )
    lookup = ChangeSetLookup.of(session, change_set_id)
    if row is None:
        base = lookup.relation(relation_id)
        if base is None:
            raise api_error(
                404, "relation_not_found", f"Relation '{relation_id}' not found in change set"
            )
        row = ChangeSetRelation(
            change_set_id=change_set_id,
            relation_id=relation_id,
            relation_type_key=base.relation_type_key,
            from_object_id=base.from_object_id,
            to_object_id=base.to_object_id,
            attributes=dict(base.attributes or {}),
            version=base.version,
        )
        session.add(row)
        session.flush()
    objects = lookup.objects([row.from_object_id, row.to_object_id])
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
    _claim_change_set(session, change_set, expected_change_set_version)
    row.version += 1
    row.is_deleted = True
    _increment_change_set_relation_set_versions(session, change_set, lookup, row)
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
    change_set = _change_set(session, change_set_id, for_update=True)
    lookup = ChangeSetLookup.of(session, change_set_id)
    base = lookup.object(object_id)
    if base is None:
        raise api_error(404, "object_not_found", f"Object '{object_id}' not found in change set")
    row = session.scalar(
        select(ChangeSetObject).where(
            ChangeSetObject.change_set_id == change_set_id, ChangeSetObject.object_id == object_id
        )
    )
    if row is None:
        row = ChangeSetObject(
            change_set_id=change_set_id,
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
    model = _change_set_model(session, change_set)
    normalized = _normalize_object_attributes(
        model, row.object_type_key, {key: value}, partial=True
    )
    _claim_change_set(session, change_set, expected_change_set_version)
    row.attributes = {**(row.attributes or {}), **normalized}
    _validate_change_set_attribute_uniqueness(model, lookup, row.object_id, row.attributes)
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
    change_set = _change_set(session, change_set_id, for_update=True)
    lookup = ChangeSetLookup.of(session, change_set_id)
    base = lookup.object(object_id)
    if base is None:
        raise api_error(404, "object_not_found", f"Object '{object_id}' not found in change set")
    row = session.scalar(
        select(ChangeSetObject).where(
            ChangeSetObject.change_set_id == change_set_id, ChangeSetObject.object_id == object_id
        )
    )
    if row is None:
        row = ChangeSetObject(
            change_set_id=change_set_id,
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
    model = _change_set_model(session, change_set)
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
    _claim_change_set(session, change_set, expected_change_set_version)
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


def _diagnostics(
    membership: EffectiveChangeSetMembership, model: Any, *, apply_defaults: bool = True
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
                _validate_candidate_parent(model, item, objects.get)
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
    # holds. Mirrors the change set write path in validate_change_set_relation.
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
    # matches the change set object-create contract, model compatibility counting and the
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


def validate_change_set(session: Session, change_set_id: str, model: Any) -> list[dict[str, Any]]:
    return _diagnostics(effective_change_set_membership(session, change_set_id), model)


def selected_change_set_release(session: Session, public_id: str) -> ModelRelease:
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


def require_change_set_compatible(
    session: Session, change_set: ChangeSet, model: Any, *, source_release_id: int | None = None
) -> None:
    """Check complete effective membership, without conversion or live-table analysis."""
    membership = effective_change_set_membership(session, change_set.id)
    source_model = resolve_pinned_release(
        session,
        source_release_id if source_release_id is not None else change_set.model_release_id,
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
            "change_set_content_incompatible",
            "Change set content does not fit the selected model. Keep its current version or choose a compatible release; conversion requires the migration workflow.",
            {
                "diagnostics": bounded,
                "diagnosticCount": len(diagnostics),
                "diagnosticsTruncated": len(diagnostics) > 20,
            },
        )


def set_change_set_model_release(
    session: Session, change_set_id: str, public_id: str, expected_version: int
) -> ChangeSet:
    """Claim, validate and change a single change set pin in one transaction."""
    try:
        change_set = _change_set(session, change_set_id, for_update=True)
        release = selected_change_set_release(session, public_id)
        if change_set.version != expected_version:
            raise api_error(
                409, "change_set_version_conflict", "Change set version has changed"
            )
        # Claim even a no-op to serialize against edits, then roll it back without an audit/version bump.
        _claim_change_set(session, change_set, expected_version)
        if change_set.model_release_id == release.id:
            session.rollback()
            return _change_set(session, change_set_id)
        old_release = session.get(ModelRelease, change_set.model_release_id)
        require_change_set_compatible(
            session, change_set, resolve_pinned_release(session, release.id, require_ready=False).model
        )
        change_set.model_release_id = release.id

        def identity(item: ModelRelease) -> dict[str, str]:
            return {"id": item.public_id, "key": item.release_key, "version": item.release_version}

        record_audit_event(
            session,
            aggregate_type="change-set",
            aggregate_id=change_set.id,
            action="model-release-changed",
            version=change_set.version,
            changes={
                "modelRelease": {
                    "from": identity(old_release) if old_release else None,
                    "to": identity(release),
                }
            },
            object_ids=(),
        )
        session.commit()
        session.refresh(change_set)
        return change_set
    except Exception:
        session.rollback()
        raise


def pinned_model(session: Session, change_set_id: str) -> tuple[ChangeSet, Any]:
    change_set = _change_set(session, change_set_id)
    return change_set, _change_set_model(session, change_set)


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
    membership: EffectiveChangeSetMembership
    authored_object_ids: set[str]
    authored_relation_ids: set[str]
    removed_object_ids: set[str]
    removed_relation_ids: set[str]


def _publication_snapshot_maps(
    session: Session, change_set: ChangeSet
) -> tuple[
    dict[str, PublicationObject | ChangeSetBaseObject],
    dict[str, PublicationRelation | ChangeSetBaseRelation],
]:
    """Index the immutable source snapshot by stable id (empty for a legacy root change set)."""
    if change_set.base_id is not None:
        base = session.get(ChangeSetBase, change_set.base_id)
        if base is None or base.workspace_key != change_set.workspace_key:
            raise api_error(
                409,
                "change_set_base_invalid",
                "Change set current-live base is missing or belongs to another workspace",
            )
        return (
            {
                item.object_id: item
                for item in session.scalars(
                    select(ChangeSetBaseObject).where(
                        ChangeSetBaseObject.base_id == base.id
                    )
                )
            },
            {
                item.relation_id: item
                for item in session.scalars(
                    select(ChangeSetBaseRelation).where(
                        ChangeSetBaseRelation.base_id == base.id
                    )
                )
            },
        )
    if change_set.derived_from_publication_id is None:
        return {}, {}
    objects = {
        item.object_id: item
        for item in session.scalars(
            select(PublicationObject).where(
                PublicationObject.publication_id == change_set.derived_from_publication_id
            )
        )
    }
    relations = {
        item.relation_id: item
        for item in session.scalars(
            select(PublicationRelation).where(
                PublicationRelation.publication_id == change_set.derived_from_publication_id
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
        "message": f"{kind.title()} changed live after the change set's base publication",
        "expectedVersion": expected,
        "actualVersion": actual,
    }


def _mapping_set_merge_conflicts(
    session: Session,
    change_set: ChangeSet,
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
                RelationSetVersion.workspace_key == change_set.workspace_key,
                RelationSetVersion.change_set_id == change_set.id,
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
            "message": "Mapping relationships changed live since this change set's source. "
            "Review live mappings and reapply the intended changes in a change set created "
            "from current live data before retrying the publish.",
        }
        for key in sorted(touched)
        for relation_type, from_type, to_type, anchor, direction in [key]
        if expected[key] != actual[key]
    ]


def _merge_change_set_over_live(
    session: Session,
    change_set: ChangeSet,
    base_objects: dict[str, PublicationObject | ChangeSetBaseObject],
    base_relations: dict[str, PublicationRelation | ChangeSetBaseRelation],
    model: Any,
) -> _LiveMerge:
    """Compute the live content that would result from applying the change set's delta.

    The current live projection is authoritative and is the substrate; only records the change set
    actually authored (created / edited / tombstoned relative to its derived-from publication) are
    applied onto it.  A change set touch on a base record requires the live record to still sit at the
    exact base-publication version (no concurrent live edit since the snapshot), and an id created in the change set
    must not already exist live; any divergence is a per-record conflict (``409 version_conflict``)
    rather than an overwrite.  Live content the change set never touched is preserved untouched.
    """
    workspace_key = change_set.workspace_key
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
        session, change_set, model, base_objects, base_relations, live_objects, live_relations
    )
    conflicts: list[dict[str, Any]] = mapping_conflicts[:20]
    authored_object_ids: set[str] = set()
    change_set_objects = {
        item.object_id: item
        for item in session.scalars(
            select(ChangeSetObject).where(ChangeSetObject.change_set_id == change_set.id)
        )
    }
    global_object_ids = set(
        session.scalars(select(RdmObject.id).where(RdmObject.id.in_(change_set_objects)))
    )
    for object_id, row in change_set_objects.items():
        base = base_objects.get(object_id)
        if row.is_deleted:
            if base is None:
                continue  # created then deleted inside the change set: never reached live
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
                        "message": "The id of an object created in the change set already exists in live data",
                    }
                )
            merged_objects[object_id] = authored

    authored_relation_ids: set[str] = set()
    change_set_relations = {
        item.relation_id: item
        for item in session.scalars(
            select(ChangeSetRelation).where(ChangeSetRelation.change_set_id == change_set.id)
        )
    }
    global_relation_ids = set(
        session.scalars(select(ObjectRelation.id).where(ObjectRelation.id.in_(change_set_relations)))
    )
    for relation_id, row in change_set_relations.items():
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
                        "message": "The id of a relation created in the change set already exists in live data",
                    }
                )
            merged_relations[relation_id] = authored

    # A tombstoned object drops its incident live relations even when the change set never saw them; a
    # live relation cannot outlive an endpoint.  Any other dangling endpoint would fail whole-graph
    # validation below and abort the publish before any row is touched.
    for relation_id in [
        relation_id
        for relation_id, relation in merged_relations.items()
        if relation.from_object_id not in merged_objects
        or relation.to_object_id not in merged_objects
    ]:
        merged_relations.pop(relation_id, None)

    # The live table enforces one directed edge per (type, from, to).  A change set edge duplicating a
    # live one (distinct ids) would violate that constraint mid-apply; surface it as a conflict
    # instead of leaking an IntegrityError out of the publish transaction.
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
                    "message": "Change set and live both define the same directed relation",
                }
            )
        else:
            seen_edges[edge] = relation_id

    if conflicts:
        raise api_error(
            409,
            "version_conflict",
            "Change set conflicts with the live active data",
            {
                "conflicts": conflicts,
                "mappingSetConflictCount": len(mapping_conflicts),
                "mappingSetConflictsTruncated": len(mapping_conflicts) > 20,
            },
        )
    membership = EffectiveChangeSetMembership(
        change_set=change_set,
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


def publish_change_set(
    session: Session,
    change_set_id: str,
    model: Any,
    active_release_id: int,
    expected_change_set_version: int,
    expected_active_publication_id: str | None,
) -> Publication:
    change_set = _change_set(session, change_set_id, for_update=True)
    if change_set.model_release_id != active_release_id:
        raise api_error(
            409,
            "change_set_model_release_conflict",
            "Change set is pinned to a different application-model release",
        )
    # Claim before reading the merge population. On SQLite this also obtains the writer lock,
    # keeping the live graph stable until the publication transaction completes.
    _claim_change_set(session, change_set, expected_change_set_version)
    workspace = session.scalar(
        select(Workspace).where(Workspace.key == change_set.workspace_key).with_for_update()
    )
    if workspace is None:
        raise api_error(404, "workspace_not_found", "Workspace not found")
    if workspace.active_publication_id != expected_active_publication_id:
        raise api_error(
            409, "workspace_active_publication_conflict", "Active publication has changed"
        )
    # The change set is applied as a delta onto the *current* live projection, then the merged graph is
    # validated whole before anything is written; live content newer than the change set base is preserved.
    merged = _merge_change_set_over_live(
        session,
        change_set,
        *_publication_snapshot_maps(session, change_set),
        model,
    )
    diagnostics = _diagnostics(merged.membership, model)
    if diagnostics:
        raise api_error(
            422,
            "workspace_graph_invalid",
            "Change set failed complete graph validation over the live active data",
            diagnostics,
        )
    number = (
        session.scalar(
            select(Publication.publication_number)
            .where(Publication.workspace_key == change_set.workspace_key)
            .order_by(Publication.publication_number.desc())
            .limit(1)
        )
        or 0
    ) + 1
    publication = Publication(
        workspace_key=change_set.workspace_key,
        model_release_id=change_set.model_release_id,
        publication_number=number,
        status="active",
        derived_from_publication_id=change_set.derived_from_publication_id,
        supersedes_publication_id=workspace.active_publication_id,
    )
    session.add(publication)
    session.flush()
    for item in merged.membership.objects:
        session.add(
            PublicationObject(
                publication_id=publication.id,
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
            PublicationRelation(
                publication_id=publication.id,
                relation_id=item.relation_id,
                relation_type_key=item.relation_type_key,
                from_object_id=item.from_object_id,
                to_object_id=item.to_object_id,
                attributes=item.attributes,
                version=item.version,
            )
        )
    record_change_set_published(
        session,
        publication=publication,
        change_set=change_set,
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
            select(RdmObject).where(RdmObject.workspace_key == change_set.workspace_key)
        )
    }
    for object_id in sorted(authored_objects):
        authored = authored_objects[object_id]
        live = live_objects.get(object_id)
        if live is None:
            live = RdmObject(
                id=object_id,
                workspace_key=change_set.workspace_key,
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
    if workspace.active_publication_id:
        old = session.scalar(
            select(Publication).where(Publication.id == workspace.active_publication_id)
        )
        old.status = "withdrawn"
        old.withdrawn_at = datetime.now(UTC)
    publication.published_at = datetime.now(UTC)
    workspace.active_publication_id = publication.id
    merge_change_set_relation_set_versions_to_live(session, change_set.id, change_set.workspace_key)
    _delete_change_set_and_base(session, change_set)
    session.commit()
    return publication


def withdraw_publication(session: Session, publication_id: str) -> None:
    """Remove the current-publication designation; live data and history are unchanged."""
    publication = session.scalar(select(Publication).where(Publication.id == publication_id))
    if publication is None:
        raise api_error(404, "publication_not_found", "Publication not found")
    workspace = session.scalar(
        select(Workspace).where(Workspace.key == publication.workspace_key).with_for_update()
    )
    if workspace is None:
        raise api_error(404, "workspace_not_found", "Workspace not found")
    if workspace.status == "retired":
        raise api_error(409, "workspace_retired", "Workspace is retired and cannot be mutated")
    # The path names the publication to withdraw, so it is also the concurrency claim: a publication
    # that is no longer current (withdrawn or superseded meanwhile) is refused.
    if workspace.active_publication_id != publication_id:
        raise api_error(
            409, "workspace_active_publication_conflict", "Active publication has changed"
        )
    publication.status = "withdrawn"
    publication.withdrawn_at = datetime.now(UTC)
    workspace.active_publication_id = None
    # Record the withdrawal in the same transaction as the pointer clear so a rolled-back
    # withdrawal never leaves an orphan event (D3a).  The event is aggregated on the workspace key
    # and carries no AuditEventSubject rows.
    record_publication_withdrawn(session, publication=publication)
    session.commit()
