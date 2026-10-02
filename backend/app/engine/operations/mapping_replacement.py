"""Atomic mapping replacement (WP-5).

One source's targets of a mapping binding are replaced in one write, live or in a change set.
"""

from dataclasses import dataclass
from typing import Any, Literal

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from ...errors import ApiError, api_error
from ...models.commands import MappingReplacementRequest
from ...models.database import (
    RelationSetVersion,
    Workspace,
)
from ...models.schema import EngineModel
from ..change_sets.access import ensure_change_set_writable
from ..change_sets.pinning import pinned_model
from ..model.registry import resolve_request_model
from ..records import rules
from ..records.audit import record_audit_event
from ..records.context import ChangeSetLookup, LiveLookup
from ..records.refusals import LIVE
from ..records.relation_set_versions import claim_set_version, increment_single_set_version
from ..records.writes import ChangeSetWrites, LiveWrites
from ..workspaces.catalogue import resolve_workspace

PREVIEW_SIZE = 20


@dataclass(frozen=True)
class MappingReplaced:
    source_object_id: str
    mapping_version: int
    state: Literal["mapped", "unmapped"]
    relation_id: str | None = None
    change_set_version: int | None = None


class MappingVersionConflict(ApiError):
    """``409 mapping_version_conflict`` with the first targets the source holds now.

    When it holds more than a preview, ``continuation`` names the set, and the API tier adds the
    first page of the set's targets as the mapping grid shows them.
    """

    def __init__(self, details: dict[str, Any], continuation: MappingConflictSet | None) -> None:
        super().__init__(
            409,
            "mapping_version_conflict",
            "Mapping version has changed; refresh mapping coverage before retrying",
            details,
        )
        self.continuation = continuation


@dataclass(frozen=True)
class MappingConflictSet:
    """The relation set a version conflict was raised for."""

    workspace_key: str
    change_set_id: str | None
    relation_type_key: str
    from_object_type_key: str
    to_object_type_key: str
    direction: str
    source_id: str
    version: int


def replace_mapping(
    session: Session, workspace_key: str, request: MappingReplacementRequest
) -> MappingReplaced:
    """Replace one source's targets of a mapping binding, live or in the named change set."""
    if request.changeSetId:
        # Claim active status before reading the graph. The update locks the workspace row (before
        # the change set, in the lock order), so retirement cannot invalidate the active-status
        # decision during this transaction. A live save takes the workspace lock in ``LiveWrites``.
        result = session.execute(
            update(Workspace)
            .where(Workspace.key == workspace_key, Workspace.status == "active")
            .values(updated_at=Workspace.updated_at)
            .execution_options(synchronize_session=False)
        )
        if result.rowcount != 1:
            resolve_workspace(session, workspace_key, require_active=True)
        side = _ChangeSetSide.open(session, workspace_key, request)
    else:
        side = _LiveSide.open(session, workspace_key)
    model = side.model
    allowed = _validate_binding_for_replacement(model, request)
    source_type, target_type = _source_target_types(request)
    _validate_clear_attributes(request)

    source = side.endpoint(str(request.sourceObjectId), source_type, "source")
    target = (
        side.endpoint(str(request.targetObjectId), target_type, "target")
        if request.targetObjectId
        else None
    )
    source_id = source.object_id
    target_id = target.object_id if target is not None else None

    actual_version = _get_set_version(
        session, workspace_key, side.change_set_id, request, source_id
    )
    edges, others = _edges(side.lookup, request, source_id, target_type)
    if request.expectedMappingVersion != actual_version:
        _raise_version_conflict(workspace_key, request, source_id, actual_version, edges, others)
    side.check_claim(request)

    if target is None:
        if allowed.required:
            raise api_error(422, "required_relation", "A required relationship cannot be cleared")
        if not edges:
            return side.result(source_id, actual_version, "unmapped")
        return _write(side, request, source_id, None, None, edges, None)

    if _needs_cross_cardinality_check(allowed, request.direction):
        _check_cross_cardinality(side.lookup, request, source_id, target_id)

    retained = next(
        (edge for edge in edges if _edge_other_id(edge, request.direction) == target_id), None
    )
    obsolete = [edge for edge in edges if edge is not retained]
    physical_source_id, physical_target = (
        (source_id, target) if request.direction == "outgoing" else (target_id, source)
    )
    rules.relation_scope(
        side.lookup,
        allowed,
        physical_source_id,
        physical_target,
        frozenset(edge.relation_id for edge in edges),
    )

    if retained is not None:
        if request.attributes is not None:
            new_attrs = rules.relation_attributes(model, allowed, request.attributes)
        else:
            new_attrs = dict(retained.attributes or {})
        if not obsolete and new_attrs == dict(retained.attributes or {}):
            return side.result(
                source_id, actual_version, "mapped", relation_id=retained.relation_id
            )
    else:
        new_attrs = rules.relation_attributes(model, allowed, request.attributes or {})
    return _write(side, request, source_id, target_id, retained, obsolete, new_attrs)


def _write(
    side: _LiveSide | _ChangeSetSide,
    request: MappingReplacementRequest,
    source_id: str,
    target_id: str | None,
    retained: Any | None,
    obsolete: list[Any],
    new_attrs: dict[str, Any] | None,
) -> MappingReplaced:
    """Claim the set, then clear it (no target), keep the target's relation, or add one."""
    session = side.writes.session
    side.claim(request)
    _claim_mapping_set(side, request, source_id)
    old_targets = [
        _old_target_audit(edge, request.direction)
        for edge in ([retained] if retained is not None else []) + obsolete
    ]
    affected_ids: set[str] = set()
    relation_id = None
    if retained is not None:
        relation_id = retained.relation_id
        if new_attrs != dict(retained.attributes or {}):
            side.change_attributes(retained, new_attrs)
            affected_ids.add(target_id)
    for edge in obsolete:
        side.remove(edge)
        affected_ids.add(_edge_other_id(edge, request.direction))
    if target_id is not None and retained is None:
        from_id, to_id = (
            (source_id, target_id) if request.direction == "outgoing" else (target_id, source_id)
        )
        relation_id = side.add(request.relationTypeKey, from_id, to_id, new_attrs)
        affected_ids.add(target_id)
    else:
        session.flush()
    new_version = request.expectedMappingVersion + 1
    _increment_affected_set_versions(
        session, side.writes.workspace_key, side.change_set_id, request, source_id, affected_ids
    )
    _record_transition(
        session,
        source_id,
        request,
        new_version,
        old_targets,
        {"relationId": relation_id, "objectId": target_id, "attributes": new_attrs}
        if target_id is not None
        else None,
        [source_id, *sorted(affected_ids | ({target_id} if target_id is not None else set()))],
    )
    session.commit()
    if target_id is None:
        return side.result(source_id, new_version, "unmapped")
    return side.result(source_id, new_version, "mapped", relation_id=relation_id)


class _LiveSide:
    """Mapping writes to live data: relations are removed, and each change audited as a live
    relation write."""

    change_set_id = None

    def __init__(self, writes: LiveWrites, model: EngineModel) -> None:
        self.writes, self.model = writes, model
        self.lookup = LiveLookup.of(writes.session, writes.workspace_key)

    @classmethod
    def open(cls, session: Session, workspace_key: str) -> _LiveSide:
        resolve_workspace(session, workspace_key, require_active=True)
        model = resolve_request_model(session, workspace_key, None, None).model
        return cls(LiveWrites(session, workspace_key), model)

    def fresh_lookup(self) -> LiveLookup:
        return LiveLookup.of(self.writes.session, self.writes.workspace_key)

    def endpoint(self, object_id: str, expected_type: str, _end: str) -> Any:
        found = self.lookup.object(object_id)
        if found is None or not self.lookup.shares_workspace(found):
            raise api_error(404, "mapping_endpoint_not_found", "Mapping endpoint not found")
        if found.object_type_key != expected_type:
            raise api_error(
                422,
                "mapping_endpoint_type_mismatch",
                "Mapping endpoint type does not match binding",
            )
        return found

    def check_claim(self, _request: MappingReplacementRequest) -> None:
        pass

    def claim(self, _request: MappingReplacementRequest) -> None:
        pass

    def change_attributes(self, relation: Any, attributes: dict[str, Any]) -> None:
        relation.attributes = attributes
        relation.version += 1
        record_audit_event(
            self.writes.session,
            aggregate_type="relation",
            aggregate_id=relation.id,
            action="updated",
            version=relation.version,
            changes={"attributes": attributes},
            object_ids=[relation.from_object_id, relation.to_object_id],
        )

    def remove(self, relation: Any) -> None:
        record_audit_event(
            self.writes.session,
            aggregate_type="relation",
            aggregate_id=relation.id,
            action="deleted",
            version=relation.version + 1,
            changes={
                "relationTypeKey": relation.relation_type_key,
                "fromObjectId": relation.from_object_id,
                "toObjectId": relation.to_object_id,
            },
            object_ids=[relation.from_object_id, relation.to_object_id],
        )
        self.writes.remove_relation(relation)

    def add(
        self, relation_type_key: str, from_id: str, to_id: str, attributes: dict[str, Any]
    ) -> str:
        relation = self.writes.add_relation(relation_type_key, from_id, to_id, attributes)
        record_audit_event(
            self.writes.session,
            aggregate_type="relation",
            aggregate_id=relation.id,
            action="created",
            version=1,
            changes={
                "relationTypeKey": relation_type_key,
                "fromObjectId": from_id,
                "toObjectId": to_id,
                "attributes": attributes,
            },
            object_ids=[from_id, to_id],
        )
        return relation.id

    def result(self, source_id: str, version: int, state: str, relation_id: str | None = None):
        return MappingReplaced(
            source_object_id=source_id, mapping_version=version, state=state, relation_id=relation_id
        )


class _ChangeSetSide:
    """Mapping writes to a change set: relations are tombstoned, the change set's version is
    claimed, and each change audited with the change set named."""

    def __init__(self, writes: ChangeSetWrites, model: EngineModel) -> None:
        self.writes, self.model = writes, model
        self.change_set_id = writes.change_set_id
        self.lookup = ChangeSetLookup.of(writes.session, writes.change_set_id)

    @classmethod
    def open(
        cls, session: Session, workspace_key: str, request: MappingReplacementRequest
    ) -> _ChangeSetSide:
        change_set_id = str(request.changeSetId)
        change_set = ensure_change_set_writable(session, change_set_id)
        if change_set.workspace_key != workspace_key:
            raise api_error(404, "change_set_not_found", "Change set not found")
        _, model = pinned_model(session, change_set_id)
        return cls(ChangeSetWrites(session, change_set), model)

    def fresh_lookup(self) -> ChangeSetLookup:
        return ChangeSetLookup.of(self.writes.session, self.change_set_id)

    def endpoint(self, object_id: str, expected_type: str, end: str) -> Any:
        found = self.lookup.object(object_id)
        if found is None or found.object_type_key != expected_type:
            raise api_error(
                404, "mapping_endpoint_not_found", f"Mapping {end} not found in change set"
            )
        return found

    def check_claim(self, request: MappingReplacementRequest) -> None:
        if request.expectedChangeSetVersion is None:
            raise api_error(
                409,
                "change_set_required",
                "expectedChangeSetVersion is required when targeting a change set",
            )
        if self.writes.change_set.version != request.expectedChangeSetVersion:
            raise api_error(409, "change_set_version_conflict", "Change set version has changed")

    def claim(self, request: MappingReplacementRequest) -> None:
        self.writes.claim(request.expectedChangeSetVersion)

    def _record(self, row: Any, action: str) -> None:
        record_audit_event(
            self.writes.session,
            aggregate_type="relation",
            aggregate_id=row.relation_id,
            action=action,
            version=row.version,
            changes={
                "changeSetId": self.change_set_id,
                "relationTypeKey": row.relation_type_key,
                "fromObjectId": row.from_object_id,
                "toObjectId": row.to_object_id,
                "attributes": dict(row.attributes or {}),
            },
            object_ids=[row.from_object_id, row.to_object_id],
        )

    def change_attributes(self, relation: Any, attributes: dict[str, Any]) -> None:
        row = self.writes.own_relation(relation, flush=True)
        row.attributes = attributes
        row.version += 1
        row.is_deleted = False
        self._record(row, "updated")

    def remove(self, relation: Any) -> None:
        row = self.writes.own_relation(relation, flush=True)
        row.version += 1
        row.is_deleted = True
        self._record(row, "deleted")

    def add(
        self, relation_type_key: str, from_id: str, to_id: str, attributes: dict[str, Any]
    ) -> str:
        row = self.writes.add_relation(relation_type_key, from_id, to_id, attributes)
        self.writes.session.flush()
        record_audit_event(
            self.writes.session,
            aggregate_type="relation",
            aggregate_id=row.relation_id,
            action="created",
            version=1,
            changes={
                "relationTypeKey": relation_type_key,
                "fromObjectId": from_id,
                "toObjectId": to_id,
                "attributes": attributes,
                "changeSetId": self.change_set_id,
            },
            object_ids=[from_id, to_id],
        )
        return row.relation_id

    def result(self, source_id: str, version: int, state: str, relation_id: str | None = None):
        return MappingReplaced(
            source_object_id=source_id,
            mapping_version=version,
            state=state,
            relation_id=relation_id,
            change_set_version=self.writes.change_set.version,
        )


def _edges(lookup: Any, request: MappingReplacementRequest, source_id: str, target_type: str):
    """The source's relations of the mapping's type and direction to a record of the target type,
    in relation-ID order, and the records at their other ends by ID."""
    relations = lookup.relations([source_id], request.direction, [request.relationTypeKey])
    others = lookup.objects(_edge_other_id(item, request.direction) for item in relations)
    edges = [
        item
        for item in relations
        if (other := others.get(_edge_other_id(item, request.direction))) is not None
        and other.object_type_key == target_type
        and lookup.shares_workspace(other)
    ]
    return edges, others


def _edge_other_id(edge: Any, direction: str) -> str:
    return edge.to_object_id if direction == "outgoing" else edge.from_object_id


def _raise_version_conflict(
    workspace_key: str,
    request: MappingReplacementRequest,
    source_id: str,
    actual_version: int,
    edges: list[Any],
    others: dict[str, Any],
) -> None:
    targets = []
    for edge in edges[:PREVIEW_SIZE]:
        other = others.get(_edge_other_id(edge, request.direction))
        if other is not None:
            targets.append(
                _target_summary(
                    edge.relation_id,
                    edge.attributes,
                    other.object_id,
                    other.object_type_key,
                    other.name,
                )
            )
    _raise_conflict(workspace_key, request, source_id, actual_version, targets, len(edges))


def _claim_mapping_set(
    side: _LiveSide | _ChangeSetSide, request: MappingReplacementRequest, source_id: str
) -> None:
    session = side.writes.session
    workspace_key = side.writes.workspace_key
    if claim_set_version(
        session,
        workspace_key=workspace_key,
        change_set_id=side.change_set_id,
        relation_type_key=request.relationTypeKey,
        from_object_type_key=request.fromObjectTypeKey,
        to_object_type_key=request.toObjectTypeKey,
        anchor_object_id=source_id,
        direction=request.direction,
        expected=request.expectedMappingVersion,
    ):
        return
    session.rollback()
    actual = _get_set_version(session, workspace_key, side.change_set_id, request, source_id)
    edges, others = _edges(
        side.fresh_lookup(), request, source_id, _source_target_types(request)[1]
    )
    _raise_version_conflict(workspace_key, request, source_id, actual, edges, others)


def _check_cross_cardinality(
    lookup: Any, request: MappingReplacementRequest, source_id: str, target_id: str
) -> None:
    # The target's relations of the type from its other side, other than to the source.
    opposite = "incoming" if request.direction == "outgoing" else "outgoing"
    for relation in lookup.relations([target_id], opposite, [request.relationTypeKey]):
        if _edge_other_id(relation, opposite) != source_id:
            raise api_error(409, "cardinality_violation", "Relation cardinality would be violated")


def _old_target_audit(edge: Any, direction: str) -> dict[str, Any]:
    return {
        "relationId": edge.relation_id,
        "objectId": _edge_other_id(edge, direction),
        "attributes": edge.attributes or {},
    }


def _source_target_types(
    request: MappingReplacementRequest,
) -> tuple[str, str]:
    if request.direction == "outgoing":
        return request.fromObjectTypeKey, request.toObjectTypeKey
    return request.toObjectTypeKey, request.fromObjectTypeKey


def _validate_binding_for_replacement(model: EngineModel, request: MappingReplacementRequest):
    allowed = rules.relation_binding(
        model, request.relationTypeKey, request.fromObjectTypeKey, request.toObjectTypeKey, LIVE
    )
    rules.mutable_relation(model, request.relationTypeKey, request.toObjectTypeKey, LIVE)
    if allowed.required and allowed.cardinality in {"one-to-one", "one-to-many"}:
        raise api_error(
            422,
            "required_ownership_binding",
            "Mapping replacement is not permitted on required-ownership bindings",
        )
    return allowed


def _validate_clear_attributes(request: MappingReplacementRequest) -> None:
    if request.targetObjectId is None and request.attributes:
        raise api_error(
            422,
            "invalid_clear_attributes",
            "Clearing a mapping permits omitted or empty attributes only",
        )


def _needs_cross_cardinality_check(allowed, direction: str) -> bool:
    return allowed.cardinality == "one-to-one" or (
        allowed.cardinality == "one-to-many" and direction == "outgoing"
    )


def _get_set_version(
    session: Session,
    workspace_key: str,
    change_set_id: str | None,
    request: MappingReplacementRequest,
    source_id: str,
) -> int:
    change_set_filter = (
        RelationSetVersion.change_set_id == change_set_id
        if change_set_id is not None
        else RelationSetVersion.change_set_id.is_(None)
    )
    row = session.scalar(
        select(RelationSetVersion).where(
            RelationSetVersion.workspace_key == workspace_key,
            change_set_filter,
            RelationSetVersion.relation_type_key == request.relationTypeKey,
            RelationSetVersion.from_object_type_key == request.fromObjectTypeKey,
            RelationSetVersion.to_object_type_key == request.toObjectTypeKey,
            RelationSetVersion.anchor_object_id == source_id,
            RelationSetVersion.direction == request.direction,
        )
    )
    return row.version if row else 0


def _target_summary(
    relation_id: str, attributes: dict | None, object_id: str, object_type_key: str, name: str
) -> dict[str, Any]:
    return {
        "relationId": relation_id,
        "attributes": attributes or {},
        "object": {"id": object_id, "objectTypeKey": object_type_key, "name": name, "fields": {}},
    }


def _raise_conflict(
    workspace_key: str,
    request: MappingReplacementRequest,
    source_id: str,
    actual_version: int,
    targets: list[dict[str, Any]],
    count: int,
) -> None:
    continuation = (
        MappingConflictSet(
            workspace_key=workspace_key,
            change_set_id=str(request.changeSetId) if request.changeSetId else None,
            relation_type_key=request.relationTypeKey,
            from_object_type_key=request.fromObjectTypeKey,
            to_object_type_key=request.toObjectTypeKey,
            direction=request.direction,
            source_id=source_id,
            version=actual_version,
        )
        if count > PREVIEW_SIZE
        else None
    )
    raise MappingVersionConflict(
        {
            "mappingVersion": actual_version,
            "targetCount": count,
            "targets": targets,
            "targetsNextCursor": None,
        },
        continuation,
    )


def _increment_affected_set_versions(
    session: Session,
    workspace_key: str,
    change_set_id: str | None,
    request: MappingReplacementRequest,
    source_id: str,
    affected_target_ids: set[str],
) -> None:
    opposite = "incoming" if request.direction == "outgoing" else "outgoing"
    base = {
        "workspace_key": workspace_key,
        "change_set_id": change_set_id,
        "relation_type_key": request.relationTypeKey,
        "from_object_type_key": request.fromObjectTypeKey,
        "to_object_type_key": request.toObjectTypeKey,
    }
    for target_id in affected_target_ids:
        increment_single_set_version(
            session, **base, anchor_object_id=target_id, direction=opposite
        )


def _record_transition(
    session: Session,
    source_id: str,
    request: MappingReplacementRequest,
    new_version: int,
    old_targets: list[dict[str, Any]],
    new_target: dict[str, Any] | None,
    object_ids: list[str],
) -> None:
    record_audit_event(
        session,
        aggregate_type="mapping",
        aggregate_id=source_id,
        action="transition",
        version=new_version,
        changes={
            "relationTypeKey": request.relationTypeKey,
            "fromObjectTypeKey": request.fromObjectTypeKey,
            "toObjectTypeKey": request.toObjectTypeKey,
            "direction": request.direction,
            "changeSetId": str(request.changeSetId) if request.changeSetId else None,
            "previousTargets": old_targets,
            "newTarget": new_target,
        },
        object_ids=object_ids,
    )
