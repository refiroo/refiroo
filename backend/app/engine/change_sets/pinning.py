"""The model release a change set is pinned to, and moving it to another compatible release."""

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from ...errors import api_error
from ...models.database import ChangeSet, ModelRelease
from ..indexes import matrix_states
from ..model.registry import resolve_pinned_release
from ..records.audit import record_audit_event
from ..records.writes import ChangeSetWrites
from .access import change_set_model, effective_change_set_membership, load_change_set
from .validation import graph_diagnostics, is_parent_pair


def selected_change_set_release(session: Session, public_id: str) -> ModelRelease:
    """Resolve an installed public release identity using pinned-model errors."""
    release = session.scalar(select(ModelRelease).where(ModelRelease.public_id == public_id))
    if release is None:
        raise api_error(
            409,
            "PINNED_MODEL_UNAVAILABLE",
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
    diagnostics = graph_diagnostics(membership, model, apply_defaults=False)
    # Match the existing model-compatibility type-change rule over effective membership. Target
    # normalizers can accept a value under another declared type, which would be conversion.
    for old_definition in source_model.attributeTypes:
        target_definition = model.attribute_type(old_definition.key)
        if target_definition is None or old_definition.valueType == target_definition.valueType:
            continue
        for rows, code, count_key in (
            (membership.objects, "ATTRIBUTE_VALUE_TYPE_CHANGED", "objectCount"),
            (membership.relations, "RELATION_ATTRIBUTE_VALUE_TYPE_CHANGED", "relationCount"),
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
        if not is_parent_pair(source_model, pair):
            continue
        source_relation = source_model.relation_type(pair.relationTypeKey)
        target_relation = model.relation_type(pair.relationTypeKey)
        identity = (pair.relationTypeKey, pair.fromObjectTypeKey, pair.toObjectTypeKey)
        if (
            identity in target_pairs
            and is_parent_pair(model, pair)
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
                    "code": "PARENT_RELATION_SEMANTICS_CHANGED",
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
            "CHANGE_SET_CONTENT_INCOMPATIBLE",
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
        change_set = load_change_set(session, change_set_id, for_update=True)
        writes = ChangeSetWrites(session, change_set)
        release = selected_change_set_release(session, public_id)
        if change_set.version != expected_version:
            raise api_error(
                409, "CHANGE_SET_VERSION_CONFLICT", "Change set version has changed"
            )
        # Claim even a no-op to serialize against edits, then roll it back without an audit/version bump.
        writes.claim(expected_version)
        if change_set.model_release_id == release.id:
            session.rollback()
            return load_change_set(session, change_set_id)
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
        session.flush()
        # The change set's cells follow its new release's matrix shapes.
        matrix_states.sync_workspace(session, change_set.workspace_key)
        session.commit()
        session.refresh(change_set)
        return change_set
    except Exception:
        session.rollback()
        raise


def pinned_model(session: Session, change_set_id: str) -> tuple[ChangeSet, Any]:
    change_set = load_change_set(session, change_set_id)
    return change_set, change_set_model(session, change_set)
