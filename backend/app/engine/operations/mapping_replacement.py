"""Atomic mapping replacement (WP-5): the mapping PUT.

One source's targets of a mapping binding are replaced in one write, live or in a change set, by
the relation-set replacement (``relation_sets.py``, 0.9 B3) with one target or none. This module
keeps what is the PUT's own: its endpoint refusals, clearing without values, the change set's
claim and the version conflict with a preview of the set.
"""

from dataclasses import dataclass
from typing import Any, Literal

from sqlalchemy import update
from sqlalchemy.orm import Session

from ...errors import ApiError, api_error
from ...models.commands import MappingReplacementRequest
from ...models.database import Workspace
from ...models.schema import EngineModel
from ..change_sets.access import ensure_change_set_writable
from ..change_sets.pinning import pinned_model
from ..model.registry import resolve_request_model
from ..records.batch_lookup import ChangeSetBatchLookup, LiveBatchLookup
from ..records.bulk import write_change_set, write_live
from ..records.refusals import LIVE
from ..records.relation_sets import (
    SetBinding,
    SetTarget,
    decide_set_replacement,
    set_binding,
    set_edges,
)
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
            "MAPPING_VERSION_CONFLICT",
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
    """Replace one source's targets of a mapping binding, live or in the named change set: the set
    replacement (``relation_sets.py``) with one target or none, as a batch of one."""
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
        side: _LiveSide | _ChangeSetSide = _ChangeSetSide.open(session, workspace_key, request)
    else:
        side = _LiveSide.open(session, workspace_key)
    model, lookup = side.model, side.lookup
    set_ = SetBinding(
        request.relationTypeKey,
        request.fromObjectTypeKey,
        request.toObjectTypeKey,
        request.direction,
    )
    set_binding(model, set_, LIVE)
    source_type, target_type = _source_target_types(request)
    _validate_clear_attributes(request)

    source = side.endpoint(str(request.sourceObjectId), source_type, "source")
    target = (
        side.endpoint(str(request.targetObjectId), target_type, "target")
        if request.targetObjectId
        else None
    )
    source_id = source.object_id
    # The token is checked before an unchanged save is recognised (API.md, atomic replacement).
    actual_version = lookup.set_version(set_.key(source_id))
    if request.expectedMappingVersion != actual_version:
        edges, others = set_edges(lookup, set_, source_id)
        _raise_version_conflict(workspace_key, request, source_id, actual_version, edges, others)
    side.check_claim(request)
    with lookup.deciding():
        replaced = decide_set_replacement(
            lookup,
            model,
            set_,
            source,
            [SetTarget(target, request.attributes)] if target is not None else [],
            expected=request.expectedMappingVersion,
        )
    state = "mapped" if target is not None else "unmapped"
    relation_id = replaced.relations.get(target.object_id) if target is not None else None
    if replaced.changed:
        side.claim(request)
        side.write(lookup)
        session.commit()
    return side.result(source_id, replaced.version, state, relation_id)


class _LiveSide:
    """Mapping writes to live data, under the workspace lock."""

    change_set_id = None

    def __init__(self, writes: LiveWrites, model: EngineModel) -> None:
        self.writes, self.model = writes, model
        self.lookup = LiveBatchLookup.of(writes.session, writes.workspace_key)

    @classmethod
    def open(cls, session: Session, workspace_key: str) -> _LiveSide:
        resolve_workspace(session, workspace_key, require_active=True)
        model = resolve_request_model(session, workspace_key, None, None).model
        return cls(LiveWrites(session, workspace_key), model)

    def endpoint(self, object_id: str, expected_type: str, _end: str) -> Any:
        found = self.lookup.object(object_id)
        if found is None or not self.lookup.shares_workspace(found):
            raise api_error(404, "MAPPING_ENDPOINT_NOT_FOUND", "Mapping endpoint not found")
        if found.object_type_key != expected_type:
            raise api_error(
                422,
                "MAPPING_ENDPOINT_TYPE_MISMATCH",
                "Mapping endpoint type does not match binding",
            )
        return found

    def check_claim(self, _request: MappingReplacementRequest) -> None:
        pass

    def claim(self, _request: MappingReplacementRequest) -> None:
        pass

    def write(self, lookup: LiveBatchLookup) -> None:
        write_live(self.writes, self.model, lookup.changes())

    def result(self, source_id: str, version: int, state: str, relation_id: str | None = None):
        return MappingReplaced(
            source_object_id=source_id, mapping_version=version, state=state, relation_id=relation_id
        )


class _ChangeSetSide:
    """Mapping writes to a change set, under the change set's version claim."""

    def __init__(self, writes: ChangeSetWrites, model: EngineModel) -> None:
        self.writes, self.model = writes, model
        self.change_set_id = writes.change_set_id
        self.lookup = ChangeSetBatchLookup.of(writes.session, writes.change_set_id)

    @classmethod
    def open(
        cls, session: Session, workspace_key: str, request: MappingReplacementRequest
    ) -> _ChangeSetSide:
        change_set_id = str(request.changeSetId)
        change_set = ensure_change_set_writable(session, change_set_id)
        if change_set.workspace_key != workspace_key:
            raise api_error(404, "CHANGE_SET_NOT_FOUND", "Change set not found")
        _, model = pinned_model(session, change_set_id)
        return cls(ChangeSetWrites(session, change_set), model)

    def endpoint(self, object_id: str, expected_type: str, end: str) -> Any:
        found = self.lookup.object(object_id)
        if found is None or found.object_type_key != expected_type:
            raise api_error(
                404, "MAPPING_ENDPOINT_NOT_FOUND", f"Mapping {end} not found in change set"
            )
        return found

    def check_claim(self, request: MappingReplacementRequest) -> None:
        if request.expectedChangeSetVersion is None:
            raise api_error(
                409,
                "CHANGE_SET_REQUIRED",
                "expectedChangeSetVersion is required when targeting a change set",
            )
        if self.writes.change_set.version != request.expectedChangeSetVersion:
            raise api_error(409, "CHANGE_SET_VERSION_CONFLICT", "Change set version has changed")

    def claim(self, request: MappingReplacementRequest) -> None:
        self.writes.claim(request.expectedChangeSetVersion)

    def write(self, lookup: ChangeSetBatchLookup) -> None:
        write_change_set(self.writes, lookup.changes())

    def result(self, source_id: str, version: int, state: str, relation_id: str | None = None):
        return MappingReplaced(
            source_object_id=source_id,
            mapping_version=version,
            state=state,
            relation_id=relation_id,
            change_set_version=self.writes.change_set.version,
        )


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


def _source_target_types(
    request: MappingReplacementRequest,
) -> tuple[str, str]:
    if request.direction == "outgoing":
        return request.fromObjectTypeKey, request.toObjectTypeKey
    return request.toObjectTypeKey, request.fromObjectTypeKey


def _validate_clear_attributes(request: MappingReplacementRequest) -> None:
    if request.targetObjectId is None and request.attributes:
        raise api_error(
            422,
            "INVALID_CLEAR_ATTRIBUTES",
            "Clearing a mapping permits omitted or empty attributes only",
        )


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
