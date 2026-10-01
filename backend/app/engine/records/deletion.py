from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass

from sqlalchemy import or_, select, text
from sqlalchemy.orm import Session

from ...common.cursors import decode_cursor, encode_cursor
from ...errors import ApiError, api_error
from ...models.database import ObjectRelation, RdmObject
from ...models.schema import EngineModel, ObjectTypeRelationDefinition
from ..workspaces.catalogue import resolve_workspace
from .audit import record_audit_event
from .context import load_object
from .relation_set_versions import increment_set_versions
from .writes import LiveWrites


@dataclass
class DeletePlan:
    """A live cascade: the root object plus every record the database cascade must remove.

    The dependant closure mirrors ``delete_change_set_object`` so the live delete surfaces exactly the
    same ``object_has_dependants`` contract as the change set path: containment children plus the
    targets of an outgoing required one-to-one / one-to-many relation.  ``relations`` holds every
    edge incident to the planned set (edges to surviving objects are removed with the delete).
    """

    root_id: str
    objects: dict[str, RdmObject]
    reasons: dict[str, str]
    relations: dict[str, ObjectRelation]

    @property
    def dependant_object_ids(self) -> list[str]:
        return [object_id for object_id in sorted(self.objects) if object_id != self.root_id]

    @property
    def incident_relations(self) -> list[ObjectRelation]:
        return list(self.relations.values())

    @property
    def has_dependants(self) -> bool:
        return len(self.objects) > 1


def deletion_preview_token(
    *,
    scope: str,
    context: dict[str, object],
    objects: list[tuple[str, int, str | None]],
    relations: list[tuple[str, int, str, str, str]],
) -> str:
    """Sign the exact hierarchy and incident edges shown by a deletion preview."""
    canonical = json.dumps(
        {"objects": sorted(objects), "relations": sorted(relations)},
        sort_keys=True,
        separators=(",", ":"),
    ).encode()
    digest = hashlib.sha256(canonical).hexdigest()
    return encode_cursor((digest,), scope=scope, sort=("deletion-impact",), filters=context)


def require_matching_deletion_preview(
    token: str | None,
    *,
    scope: str,
    context: dict[str, object],
    objects: list[tuple[str, int, str | None]],
    relations: list[tuple[str, int, str, str, str]],
) -> None:
    """Reject confirmation unless it matches the unchanged previewed hierarchy."""
    if token is None:
        raise api_error(
            409,
            "deletion_preview_required",
            "Deletion must be previewed before cascade confirmation",
        )
    expected = deletion_preview_token(
        scope=scope, context=context, objects=objects, relations=relations
    )
    try:
        supplied_digest = decode_cursor(
            token,
            scope=scope,
            sort=("deletion-impact",),
            filters=context,
            position_size=1,
            message="Deletion preview is invalid",
        )[0]
        expected_digest = decode_cursor(
            expected,
            scope=scope,
            sort=("deletion-impact",),
            filters=context,
            position_size=1,
        )[0]
    except ApiError as exc:
        if exc.code != "invalid_cursor":
            raise
        raise api_error(
            409,
            "deletion_preview_changed",
            "The object was modified by another session. Please retry.",
        ) from None
    if supplied_digest != expected_digest:
        raise api_error(
            409,
            "deletion_preview_changed",
            "The object was modified by another session. Please retry.",
        )


def require_deletion_preview(token: str | None) -> None:
    """Require preview confirmation before looking up or claiming mutable graph state."""
    if token is None:
        raise api_error(
            409,
            "deletion_preview_required",
            "Deletion must be previewed before cascade confirmation",
        )


def deletion_preview_changed() -> ApiError:
    """Return the stable conflict shown when a confirmed deletion preview is stale."""
    return api_error(
        409,
        "deletion_preview_changed",
        "The object was modified by another session. Please retry.",
    )


def _plan_identity(
    plan: DeletePlan,
) -> tuple[list[tuple[str, int, str | None]], list[tuple[str, int, str, str, str]]]:
    return (
        [(item.id, item.version, item.parent_object_id) for item in plan.objects.values()],
        [
            (
                item.id,
                item.version,
                item.relation_type_key,
                item.from_object_id,
                item.to_object_id,
            )
            for item in plan.relations.values()
        ],
    )


def _is_parent_relation(
    model: EngineModel, relation: ObjectRelation, objects: dict[str, RdmObject]
) -> bool:
    target = objects.get(relation.to_object_id)
    if target is None:
        return False
    object_type = model.object_type(target.object_type_key)
    return bool(
        object_type
        and relation.relation_type_key
        in (object_type.behavior or {}).get("parentRelationTypeKeys", [])
    )


def _has_non_parent_incident(plan: DeletePlan, model: EngineModel) -> bool:
    return any(
        not _is_parent_relation(model, relation, plan.objects)
        for relation in plan.incident_relations
    )


def build_delete_plan(
    session: Session, model: EngineModel, root: RdmObject, *, cascade: bool
) -> DeletePlan:
    """Compute the live dependant closure for ``root``.

    Children and required-ownership targets are dependants regardless of ``cascade``; the flag
    only authorises *executing* the plan instead of raising ``object_has_dependants``.
    """
    planned = {root.id: root}
    reasons: dict[str, str] = {root.id: "root"}
    frontier = [root.id]
    while frontier:
        current_id = frontier.pop()
        current = planned[current_id]
        for child in session.scalars(
            select(RdmObject).where(RdmObject.parent_object_id == current_id)
        ):
            _require_same_workspace(root.workspace_key, child, edge="parent")
            if child.id not in planned:
                planned[child.id] = child
                reasons[child.id] = "child"
                frontier.append(child.id)
        for relation in session.scalars(
            select(ObjectRelation).where(ObjectRelation.from_object_id == current_id)
        ):
            if relation.to_object_id in planned:
                continue
            target = session.scalar(select(RdmObject).where(RdmObject.id == relation.to_object_id))
            if target is None:  # A relation FK should make this unreachable.
                continue
            _require_same_workspace(root.workspace_key, target, edge=relation.id)
            allowed = _allowed_relation(model, relation, current, target)
            relation_type = model.relation_type(relation.relation_type_key)
            if (
                allowed is not None
                and relation_type is not None
                and relation_type.isOriented
                and allowed.required
                and allowed.cardinality in {"one-to-one", "one-to-many"}
            ):
                planned[target.id] = target
                reasons[target.id] = "required-ownership"
                frontier.append(target.id)

    planned_ids = set(planned)
    relations: dict[str, ObjectRelation] = {}
    for relation in session.scalars(
        select(ObjectRelation).where(
            or_(
                ObjectRelation.from_object_id.in_(planned_ids),
                ObjectRelation.to_object_id.in_(planned_ids),
            )
        )
    ):
        for endpoint_id in (relation.from_object_id, relation.to_object_id):
            endpoint = planned.get(endpoint_id) or session.scalar(
                select(RdmObject).where(RdmObject.id == endpoint_id)
            )
            if endpoint is not None:
                _require_same_workspace(root.workspace_key, endpoint, edge=relation.id)
        relations[relation.id] = relation
    return DeletePlan(root.id, planned, reasons, relations)


def delete_object_record(
    session: Session,
    model: EngineModel,
    object_type_key: str,
    object_id: str,
    expected_version: int,
    *,
    cascade: bool = False,
    deletion_preview: str | None = None,
    model_identity: str,
) -> None:
    """Delete a live object and, with ``cascade``, its dependant closure, and commit.

    ``expected_version`` is claimed against the live root before any change; a stale claim or a
    non-cascade delete with dependants raises inside the transaction so nothing is committed.
    """
    apply_object_delete(
        session,
        model,
        object_type_key,
        object_id,
        expected_version,
        cascade=cascade,
        deletion_preview=deletion_preview,
        model_identity=model_identity,
    )
    session.commit()


def apply_object_delete(
    session: Session,
    model: EngineModel,
    object_type_key: str,
    object_id: str,
    expected_version: int,
    *,
    cascade: bool = False,
    deletion_preview: str | None = None,
    model_identity: str,
) -> None:
    """Delete a live object as ``delete_object_record`` does; the caller commits."""
    if cascade:
        require_deletion_preview(deletion_preview)
    try:
        root = load_object(session, object_id, object_type_key)
    except ApiError as exc:
        if cascade and deletion_preview is not None and exc.code == "object_not_found":
            raise deletion_preview_changed() from None
        raise
    resolve_workspace(session, root.workspace_key, require_active=True)
    writes = LiveWrites(session, root.workspace_key)
    # This conditional write is the workspace mutation claim: it locks the workspace row, so the
    # active-status decision holds and retirement waits until this deletion commits or rolls back.
    if not writes.claim_active_workspace():
        raise api_error(
            409,
            "workspace_retired",
            f"Workspace '{root.workspace_key}' is retired and cannot be modified",
        )
    if cascade:
        # Wait for earlier graph writes, then prevent new object/attribute/relation writes while the
        # confirmed impact is re-read, compared and deleted in this transaction.
        session.execute(
            text(
                "LOCK TABLE objects, attribute_values, object_relations IN SHARE ROW EXCLUSIVE MODE"
            )
        )
    try:
        writes.claim_object(root, expected_version)
    except ApiError as exc:
        if cascade and deletion_preview is not None and exc.code == "version_conflict":
            raise deletion_preview_changed() from None
        raise
    plan = build_delete_plan(session, model, root, cascade=cascade)
    context = {
        "workspaceKey": root.workspace_key,
        "objectTypeKey": object_type_key,
        "objectId": object_id,
        "model": model_identity,
    }
    objects, relations = _plan_identity(plan)
    if not cascade and (plan.has_dependants or _has_non_parent_incident(plan, model)):
        dependants = [
            {
                "id": item.id,
                "name": item.name,
                "objectTypeKey": item.object_type_key,
                "applicationKey": item.application_key,
                "parentObjectId": item.parent_object_id,
                "reason": plan.reasons[item.id],
            }
            for item in (plan.objects[object_id] for object_id in plan.dependant_object_ids)
        ]
        incident = plan.incident_relations
        raise api_error(
            409,
            "object_has_dependants",
            "Object has dependant records or relationships; repeat with cascade=true",
            {
                "objectsToDelete": dependants,
                "objectsToRetire": dependants,
                "relationshipsToRemove": [
                    {"id": relation.id, "relationTypeKey": relation.relation_type_key}
                    for relation in incident
                ],
                "objectCount": len(plan.objects),
                "relationshipCount": len(incident),
                "retainedAssociationCount": sum(
                    1
                    for relation in incident
                    if relation.from_object_id not in plan.objects
                    or relation.to_object_id not in plan.objects
                ),
                "deletionPreviewToken": deletion_preview_token(
                    scope="live-deletion",
                    context=context,
                    objects=objects,
                    relations=relations,
                ),
            },
        )
    if cascade:
        require_matching_deletion_preview(
            deletion_preview,
            scope="live-deletion",
            context=context,
            objects=objects,
            relations=relations,
        )
    execute_delete_plan(writes, plan)


def execute_delete_plan(writes: LiveWrites, plan: DeletePlan) -> None:
    """Audit then physically remove the planned relations, attribute values and objects.

    Containment pointers are detached within the transaction before deleting a mixed parent/child
    batch, preserving the RESTRICT foreign-key boundary.  Live delete is physical: withdrawn and earlier publications and the audit log
    retain the record.
    """
    session = writes.session
    endpoint_ids: set[str] = set()
    for relation in plan.relations.values():
        record_audit_event(
            session,
            aggregate_type="relation",
            aggregate_id=relation.id,
            action="deleted",
            version=relation.version,
            changes={
                "relationTypeKey": relation.relation_type_key,
                "fromObjectId": relation.from_object_id,
                "toObjectId": relation.to_object_id,
                "cascadeRootObjectId": plan.root_id,
            },
            object_ids=[relation.from_object_id, relation.to_object_id],
        )
    for item in plan.objects.values():
        record_audit_event(
            session,
            aggregate_type="object",
            aggregate_id=item.id,
            action="deleted",
            version=item.version,
            changes={
                "objectTypeKey": item.object_type_key,
                "cascadeRootObjectId": plan.root_id,
            },
            object_ids=[item.id],
        )

    if plan.relations:
        endpoint_ids = {
            endpoint_id
            for relation in plan.relations.values()
            for endpoint_id in (relation.from_object_id, relation.to_object_id)
        }
        endpoints = {
            item.id: item
            for item in session.scalars(select(RdmObject).where(RdmObject.id.in_(endpoint_ids)))
        }
        for relation in plan.relations.values():
            source = endpoints[relation.from_object_id]
            target = endpoints[relation.to_object_id]
            increment_set_versions(
                session,
                workspace_key=source.workspace_key,
                change_set_id=None,
                relation_type_key=relation.relation_type_key,
                from_object_type_key=source.object_type_key,
                to_object_type_key=target.object_type_key,
                from_object_id=source.id,
                to_object_id=target.id,
            )
    writes.remove_records(list(plan.objects.values()), set(plan.relations), endpoint_ids)


def _allowed_relation(
    model: EngineModel,
    relation: ObjectRelation,
    from_object: RdmObject,
    to_object: RdmObject,
) -> ObjectTypeRelationDefinition | None:
    return model.allowed_relation(
        relation.relation_type_key, from_object.object_type_key, to_object.object_type_key
    )


def _require_same_workspace(workspace_key: str, item: RdmObject, *, edge: str) -> None:
    if item.workspace_key != workspace_key:
        raise api_error(
            409,
            "workspace_graph_invalid",
            "Object hierarchy crosses workspace boundaries; deletion was refused",
            {
                "workspaceKey": workspace_key,
                "otherWorkspaceKey": item.workspace_key,
                "objectId": item.id,
                "edge": edge,
            },
        )
