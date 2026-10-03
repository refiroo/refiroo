"""Batches: a job of kind ``batch`` whose items are decided by the single writes' rules and written
in bulk (ADR-036; 0.9.0-alpha.1 PG3b, PG-D12–PG-D17).

A create, update or upsert item is decided as its single write decides it, through the same
service's decide step and the same rules, so it is refused with the same code. The items of an
inline batch or a background chunk are decided one after another through one batch lookup
(``records/batch_lookup.py``): it reads once what the items name and lays each accepted item over
what it read, so each item sees the items before it (D23). The accepted items are then written
together, each kind of row in multi-row statements (``records/bulk.py``). A refused item writes
nothing, so no item needs a savepoint (PG-D15); a bulk write that fails on something the rules did
not foresee is redone item by item, each as a batch of one, so the failing item gets its single
write's answer. A delete item keeps the single delete's path, one item at a time (PG-D18).

The batch adds what single writes lack (INTEGRATION_API B): records named by a unique key, upsert,
``unchanged`` and the failure policies.

- ``atomic``: items apply in order, each against what the items before it left; the first
  rejection rolls every item back and the others are ``unprocessed``.
- ``independent``: a rejected item is left out; the others apply.

In a change set the job claims the change set's version once for all its items (P3); a job that
applies nothing leaves the version as it was. A live batch holds the workspace lock for the inline
batch or the chunk (PG-D14).
"""

from collections.abc import Callable, Iterator, Sequence
from contextlib import nullcontext
from dataclasses import dataclass
from typing import Any

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ...errors import ApiError, api_error
from ...models.commands import (
    RELATION_ITEMS,
    BatchCreateItem,
    BatchCreateRelationItem,
    BatchDeleteItem,
    BatchDeleteRelationItem,
    BatchInitialRelation,
    BatchItem,
    BatchReplaceRelationSetItem,
    BatchRequest,
    BatchUpdateItem,
    BatchUpdateRelationItem,
    BatchUpsertItem,
    ChangeSetObjectUpdate,
    ChangeSetObjectWrite,
    InitialRelationInput,
    ObjectCreate,
    ObjectUpdate,
    RecordReference,
)
from ...models.database import ChangeSet
from ...models.schema import EngineModel
from ..change_sets.access import change_set_model, load_change_set
from ..change_sets.records import (
    apply_change_set_object_delete,
    decide_change_set_object_create,
    decide_change_set_object_update,
)
from ..indexes import matrix_states
from ..model import registry
from ..model.registry import resolve_model_snapshot
from ..records import rules
from ..records.audit import audit_cause
from ..records.batch_lookup import BatchLookup, ChangeSetBatchLookup, LiveBatchLookup
from ..records.bulk import write_change_set, write_live
from ..records.deletion import apply_object_delete
from ..records.objects import (
    attributes_to_dict,
    decide_object_create,
    decide_object_update,
    duplicate_relation,
)
from ..records.refusals import CHANGE_SET, LIVE
from ..records.relation_set_versions import SetClaim, set_claim
from ..records.relation_sets import SetBinding, SetTarget, decide_set_replacement
from ..records.relation_writes import (
    decide_relation_create,
    decide_relation_delete,
    decide_relation_update,
)
from ..records.values import normalize_value, stored_json_value
from ..records.writes import ChangeSetWrites, LiveWrites
from ..workspaces.catalogue import resolve_workspace
from .store import ItemOutcome

# A cancel request is looked for before every this many items an atomic job decides, and before
# its items are written (D28).
STOP_CHECK_ITEMS = 500

# Where in an item a single write's refusal points, by its code; otherwise at the item.
_POINTERS = {
    "version_conflict": "expectedVersion",
    "parent_required": "parent",
    "parent_wrong_scope": "parent",
    "invalid_parent_type": "parent",
    "parent_cycle": "parent",
    "object_already_exists": "id",
    "relation_not_found": "id",
    "relation_set_version_conflict": "expectedRelationSetVersion",
    "relation_set_claim_incomplete": "expectedRelationSetVersion",
    "unknown_relation_attributes": "attributes",
    "missing_required_relations": "initialRelations",
    "duplicate_initial_relation": "initialRelations",
    **{
        code: "attributes"
        for code in (
            "unknown_attributes",
            "read_only_attributes",
            "missing_required_attributes",
            "duplicate_attribute",
            "duplicate_attribute_value",
            "invalid_attribute_value",
            "attribute_below_minimum",
            "attribute_above_maximum",
            "object_attribute_rule_violation",
            "invalid_effective_period",
        )
    },
}


@dataclass(frozen=True)
class BatchContext:
    """Where a batch writes: live data of a workspace, or one change set; and its model."""

    workspace_key: str
    change_set: ChangeSet | None
    model: EngineModel
    model_release_id: int
    model_hash: str | None


def check_batch_context(request: BatchRequest) -> None:
    """The request names exactly one context, with a change set's version claim (§B1)."""
    if (request.workspaceKey is None) == (request.changeSetId is None):
        raise api_error(
            422,
            "invalid_batch_context",
            "Name workspaceKey for live data or changeSetId for a change set, not both",
            {"pointer": "/workspaceKey" if request.workspaceKey else "/changeSetId"},
        )
    if request.changeSetId is None and request.expectedChangeSetVersion is not None:
        raise api_error(
            422,
            "invalid_batch_context",
            "expectedChangeSetVersion applies only with changeSetId",
            {"pointer": "/expectedChangeSetVersion"},
        )
    if request.changeSetId is not None and request.expectedChangeSetVersion is None:
        raise api_error(
            409,
            "change_set_required",
            "expectedChangeSetVersion is required when targeting a change set",
        )


def open_batch_context(session: Session, request: BatchRequest) -> BatchContext:
    """The request's context, or the request-level refusal that creates no job (P2)."""
    check_batch_context(request)
    if request.changeSetId is None:
        workspace = resolve_workspace(session, request.workspaceKey, require_active=True)
        snapshot = resolve_model_snapshot(session)
        return BatchContext(
            workspace.key, None, snapshot.model, snapshot.release_db_id, snapshot.model_hash
        )
    change_set = load_change_set(session, str(request.changeSetId), for_update=True)
    return BatchContext(
        change_set.workspace_key,
        change_set,
        change_set_model(session, change_set),
        change_set.model_release_id,
        None,
    )


def run_batch(
    session: Session, context: BatchContext, request: BatchRequest, job_id: str
) -> list[ItemOutcome]:
    """Apply every item of an inline request; the caller records the outcomes and commits."""
    return run_items(
        session,
        context,
        list(enumerate(request.items)),
        policy=request.policy,
        on_existing=request.onExisting,
        expected_change_set_version=request.expectedChangeSetVersion,
        job_id=job_id,
    )


def run_items(
    session: Session,
    context: BatchContext,
    items: Sequence[tuple[int, BatchItem]],
    *,
    policy: str,
    on_existing: str,
    expected_change_set_version: int | None,
    job_id: str,
    should_stop: Callable[[], bool] | None = None,
) -> list[ItemOutcome]:
    """Apply ``items`` (each with its index in the job) under the policy; the caller records the
    outcomes and commits. An inline batch is one call; a background job one call per chunk.

    A stale ``expectedChangeSetVersion`` raises before any item runs. ``should_stop`` is asked
    before every ``STOP_CHECK_ITEMS`` items and before the items are written; when it answers
    ``True`` the items are rolled back and ``JobCancelled`` is raised.
    """
    outer = session.begin_nested()
    try:
        # The outer savepoint's release applies the items' matrix notes once (ADR-033).
        with audit_cause(session, "job", job_id), matrix_states.deferred(session):
            claim = (
                ChangeSetWrites(session, context.change_set).hold_claim(expected_change_set_version)
                if context.change_set is not None
                else nullcontext()
            )
            with claim:
                outcomes = _Batch(session, context, items, policy, on_existing, should_stop).run()
    except JobCancelled:
        outer.rollback()
        raise
    rejected = any(outcome.status == "rejected" for outcome in outcomes)
    if policy == "atomic" and rejected:
        outer.rollback()
        rolled_back = {"reason": "batch_rolled_back"}
        outcomes = [
            outcome
            if outcome.status == "rejected"
            else ItemOutcome(outcome.index, outcome.ref, "unprocessed", rolled_back)
            for outcome in outcomes
        ]
        outcomes += [
            ItemOutcome(index, item.ref, "unprocessed", rolled_back)
            for index, item in items[len(outcomes) :]
        ]
    elif not any(
        outcome.status == "applied" and outcome.fields["action"] != "unchanged"
        for outcome in outcomes
    ):
        # Nothing changed: the change set keeps its version.
        outer.rollback()
    else:
        # The release is checked, under the runtime-state row's share lock, before the outer
        # savepoint's release writes the matrix states: an activation that drops a matrix shape
        # then waits for this chunk, never the other way round as well (PG3b).
        registry.require_resolved_release(session)
        outer.commit()
    return outcomes


class JobCancelled(Exception):
    """A cancel request reached the job while its items were applied (D28)."""


def _segments(
    items: Sequence[tuple[int, BatchItem]],
) -> Iterator[Sequence[tuple[int, BatchItem]]]:
    """Runs of items decided together, and each delete item on its own (PG-D18)."""
    start = 0
    for position, (_index, item) in enumerate(items):
        if isinstance(item, BatchDeleteItem):
            if position > start:
                yield items[start:position]
            yield items[position : position + 1]
            start = position + 1
    if start < len(items):
        yield items[start:]


class _Batch:
    def __init__(
        self,
        session: Session,
        context: BatchContext,
        items: Sequence[tuple[int, BatchItem]],
        policy: str,
        on_existing: str,
        should_stop: Callable[[], bool] | None,
    ) -> None:
        self.writer = (
            _ChangeSetItems(session, context) if context.change_set else _LiveItems(session, context)
        )
        self.items = items
        self.policy = policy
        self.on_existing = on_existing
        self.should_stop = should_stop
        self.session = session

    def run(self) -> list[ItemOutcome]:
        outcomes: list[ItemOutcome] = []
        for segment in _segments(self.items):
            bulk = not isinstance(segment[0][1], BatchDeleteItem)
            go_on = self._together(segment, outcomes) if bulk else self._one_by_one(segment, outcomes)
            if not go_on:
                break
        return outcomes

    def _stop_check(self) -> None:
        if self.should_stop is not None and self.should_stop():
            raise JobCancelled

    def _together(
        self, segment: Sequence[tuple[int, BatchItem]], outcomes: list[ItemOutcome]
    ) -> bool:
        """Decide the items in order and write the accepted ones together; ``False`` when an
        atomic batch stops at a rejection."""
        lookup = self.writer.open()
        self.writer.prefetch([item for _index, item in segment])
        decided: list[ItemOutcome] = []
        for number, (index, item) in enumerate(segment):
            if number % STOP_CHECK_ITEMS == 0:
                self._stop_check()
            try:
                with lookup.deciding():
                    fields = self.apply(index, item)
            except ApiError as error:
                decided.append(
                    ItemOutcome(index, item.ref, "rejected", {"error": _error(index, error)})
                )
                if self.policy == "atomic":
                    outcomes.extend(decided)
                    return False
                continue
            decided.append(ItemOutcome(index, item.ref, "applied", fields))
        self._stop_check()
        if lookup.changes():
            try:
                with self.session.begin_nested():
                    self.writer.write()
            except IntegrityError:
                # A row the rules did not foresee (PG-D15): each item again as a batch of one.
                return self._one_by_one(segment, outcomes)
        outcomes.extend(decided)
        return True

    def _one_by_one(
        self, segment: Sequence[tuple[int, BatchItem]], outcomes: list[ItemOutcome]
    ) -> bool:
        """Apply each item as a batch of one in a savepoint of its own; ``False`` when an atomic
        batch stops at a rejection."""
        for index, item in segment:
            self._stop_check()
            try:
                with self.session.begin_nested():
                    lookup = self.writer.open()
                    with lookup.deciding():
                        fields = self.apply(index, item)
                    if lookup.changes():
                        self.writer.write_one(fields)
            except ApiError as error:
                outcomes.append(
                    ItemOutcome(index, item.ref, "rejected", {"error": _error(index, error)})
                )
                if self.policy == "atomic":
                    return False
                continue
            outcomes.append(ItemOutcome(index, item.ref, "applied", fields))
        return True

    def apply(self, index: int, item: BatchItem) -> dict[str, Any]:
        at = f"/items/{index}"
        if isinstance(item, BatchCreateItem):
            return self.create(item, at, object_id=str(item.id) if item.id else None)
        if isinstance(item, BatchUpdateItem):
            record = self.writer.resolve(item.target, f"{at}/target")
            return self.update(item, record, at, item.expectedVersion)
        if isinstance(item, BatchUpsertItem):
            return self.upsert(item, at)
        if isinstance(item, BatchDeleteItem):
            record = self.writer.resolve(item.target, f"{at}/target")
            self.writer.delete(record, item.expectedVersion)
            return {
                "action": "deleted",
                "id": record.object_id,
                "objectTypeKey": record.object_type_key,
            }
        if isinstance(item, RELATION_ITEMS):
            return self.relation_item(item, at)
        if isinstance(item, BatchReplaceRelationSetItem):
            return self.replace_set(item, at)
        raise AssertionError(f"Unknown batch item {item!r}")

    def relation_item(self, item: Any, at: str) -> dict[str, Any]:
        """A relation item through its single write's decide step (0.9 B3, §B4)."""
        lookup, model = self.writer.lookup, self.writer.model
        if isinstance(item, BatchUpdateRelationItem):
            relation = self.writer.relation(str(item.id), f"{at}/id")
            changed = decide_relation_update(
                lookup, model, relation, item.expectedVersion, item.attributes
            )
            return {
                "action": "updated",
                "relationId": changed.relation_id,
                "version": changed.version,
            }
        if isinstance(item, BatchDeleteRelationItem):
            claim = set_claim(item.expectedRelationSetVersion, item.relationSetDirection)
            relation = self.writer.relation(str(item.id), f"{at}/id")
            decide_relation_delete(lookup, model, relation, item.expectedVersion, claim)
            return {"action": "deleted", "relationId": relation.relation_id, **_claimed(claim)}
        claim = (
            set_claim(item.expectedRelationSetVersion, item.relationSetDirection)
            if isinstance(item, BatchCreateRelationItem)
            else None
        )
        source = self.writer.resolve(item.from_, f"{at}/from")
        target = self.writer.resolve(item.to, f"{at}/to")
        existing = None
        if not isinstance(item, BatchCreateRelationItem):
            existing = next(
                (
                    relation
                    for relation in lookup.relations(
                        [source.object_id], "outgoing", [item.relationTypeKey]
                    )
                    if relation.to_object_id == target.object_id
                ),
                None,
            )
        if existing is None:
            created = decide_relation_create(
                lookup, model, item.relationTypeKey, source, target, item.attributes or {}, claim
            )
            return {
                "action": "created",
                "relationId": created.relation_id,
                "version": created.version,
                **_claimed(claim),
            }
        return self.ensure(item, at, source, target, existing)

    def replace_set(self, item: BatchReplaceRelationSetItem, at: str) -> dict[str, Any]:
        """A set replacement (§B4): the mapping PUT's step with any number of targets."""
        set_ = SetBinding(
            item.relationTypeKey, item.fromObjectTypeKey, item.toObjectTypeKey, item.direction
        )
        anchor_type = (
            item.fromObjectTypeKey if item.direction == "outgoing" else item.toObjectTypeKey
        )
        anchor = self._typed(item.anchor, f"{at}/anchor", anchor_type)
        targets = [
            SetTarget(
                self._typed(target.object, f"{at}/targets/{number}/object", set_.other_type),
                target.attributes,
            )
            for number, target in enumerate(item.targets)
        ]
        replaced = decide_set_replacement(
            self.writer.lookup,
            self.writer.model,
            set_,
            anchor,
            targets,
            expected=item.expectedRelationSetVersion,
            on_existing=self.on_existing,
            pointer=at,
        )
        return {
            "action": "updated" if replaced.changed else "unchanged",
            "relationSetVersion": replaced.version,
            "relationIds": {
                "created": replaced.created,
                "kept": replaced.kept,
                "removed": replaced.removed,
            },
        }

    def _typed(self, reference: RecordReference, pointer: str, object_type_key: str) -> Any:
        record = self.writer.resolve(reference, pointer)
        if record.object_type_key != object_type_key:
            raise _type_mismatch(pointer, record, object_type_key)
        return record

    def ensure(self, item: Any, at: str, source: Any, target: Any, existing: Any) -> dict[str, Any]:
        """An ``ensureRelation`` that found its relation: ``unchanged`` first, then P4 (D24)."""
        lookup, model = self.writer.lookup, self.writer.model
        rules.mutable_relation(model, item.relationTypeKey, target.object_type_key, lookup.refusals)
        identity = {"relationId": existing.relation_id}
        if item.attributes is not None:
            binding = rules.relation_binding(
                model,
                item.relationTypeKey,
                source.object_type_key,
                target.object_type_key,
                lookup.refusals,
            )
            wanted = rules.relation_attributes(model, binding, item.attributes)
        if item.attributes is None or wanted == dict(existing.attributes or {}):
            return {"action": "unchanged", **identity, "version": existing.version}
        expected, audit = item.expectedVersion, {}
        if expected is None:
            if self.on_existing != "overwrite":
                raise api_error(
                    409,
                    "version_required",
                    "The relation exists with other values; send expectedVersion, or declare "
                    'onExisting: "overwrite"',
                    {"pointer": f"{at}/expectedVersion", **identity, "version": existing.version},
                )
            expected = existing.version
            audit = {"overwrite": {"previousVersion": existing.version}}
        changed = decide_relation_update(
            lookup, model, existing, expected, item.attributes, audit_changes=audit
        )
        outcome = {"action": "updated", **identity, "version": changed.version}
        if audit:
            outcome["previousVersion"] = existing.version
        return outcome

    def create(
        self, item: BatchCreateItem | BatchUpsertItem, at: str, *, object_id: str | None
    ) -> dict[str, Any]:
        parent = self.writer.resolve(item.parent, f"{at}/parent") if item.parent else None
        relations = [
            (
                relation,
                self.writer.resolve(relation.object, f"{at}/initialRelations/{number}/object"),
            )
            for number, relation in enumerate(item.initialRelations)
        ]
        created = self.writer.create(item, object_id, parent, relations)
        return {
            "action": "created",
            "id": created.object_id,
            "objectTypeKey": created.object_type_key,
            "version": created.version,
        }

    def update(
        self,
        item: BatchUpdateItem | BatchUpsertItem,
        record: Any,
        at: str,
        expected_version: int | None,
    ) -> dict[str, Any]:
        """Update ``record`` as a PATCH would; ``unchanged`` first, then the version claim (D24)."""
        parent_given = "parent" in item.model_fields_set
        parent = self.writer.resolve(item.parent, f"{at}/parent") if item.parent else None
        attributes = attributes_to_dict(item.attributes) if item.attributes is not None else None
        identity = {"id": record.object_id, "objectTypeKey": record.object_type_key}
        if self.writer.unchanged(record, item.name, parent_given, parent, attributes):
            return {"action": "unchanged", **identity, "version": record.version}
        audit: dict[str, Any] = {}
        if expected_version is None:
            if self.on_existing != "overwrite":
                raise api_error(
                    409,
                    "version_required",
                    "The upsert found an existing record; send expectedVersion, or declare "
                    'onExisting: "overwrite"',
                    {
                        "pointer": f"{at}/expectedVersion",
                        "id": record.object_id,
                        "version": record.version,
                    },
                )
            expected_version = record.version
            audit = {"overwrite": {"previousVersion": record.version}}
        version = self.writer.update(
            record, expected_version, item.name, parent_given, parent, item.attributes, audit
        )
        outcome = {"action": "updated", **identity, "version": version}
        if audit:
            outcome["previousVersion"] = audit["overwrite"]["previousVersion"]
        return outcome

    def upsert(self, item: BatchUpsertItem, at: str) -> dict[str, Any]:
        rules.object_identity(
            self.writer.model, item.applicationKey, item.objectTypeKey, self.writer.refusals
        )
        if item.key.id is not None:
            object_id = str(item.key.id)
            record = self.writer.find(object_id)
        else:
            key = item.key.attributeTypeKey
            value = next(
                (
                    attribute.value
                    for attribute in item.attributes
                    if attribute.attributeTypeKey == key
                ),
                None,
            )
            definition = self.writer.unique_key(
                item.objectTypeKey, key, f"{at}/key/attributeTypeKey"
            )
            if value is None or value == "":
                raise api_error(
                    422,
                    "missing_record_key",
                    f"The upsert key '{key}' needs a value among the item's attributes",
                    {"pointer": f"{at}/attributes", "attributeTypeKey": key},
                )
            object_id = None
            holder = self.writer.holder(definition, value, f"{at}/attributes")
            record = self.writer.find(holder) if holder else None
        if record is None:
            return self.create(item, at, object_id=object_id)
        if (record.object_type_key, record.application_key) != (
            item.objectTypeKey,
            item.applicationKey,
        ):
            raise _type_mismatch(f"{at}/key", record, item.objectTypeKey)
        return self.update(item, record, at, item.expectedVersion)


class _Items:
    """What an item does in one context; ``_LiveItems`` and ``_ChangeSetItems`` read alike.

    ``open`` starts a batch lookup for a run of items, which ``prefetch`` fills with what they
    name; ``create`` and ``update`` decide an item over it, and ``write`` writes what was decided.
    """

    session: Session
    model: EngineModel
    refusals: Any
    lookup: BatchLookup

    def open(self) -> BatchLookup:
        raise NotImplementedError

    def find(self, object_id: str) -> Any | None:
        return self.lookup.object(object_id)

    def relation(self, relation_id: str, pointer: str) -> Any:
        """A relation of the context by its ID, as the items before it leave it."""
        relation = self.lookup.relation(relation_id)
        if relation is None:
            raise api_error(
                404,
                "relation_not_found",
                f"Relation '{relation_id}' not found",
                {"pointer": pointer, "id": relation_id},
            )
        return relation

    def resolve(self, reference: RecordReference, pointer: str) -> Any:
        """The record a reference names (§B2), against the context as it stands now."""
        if reference.id is not None:
            record = self.find(str(reference.id))
            if record is None:
                raise _not_found(pointer, {"id": str(reference.id)})
            return record
        key = reference.key
        definition = self.unique_key(
            reference.objectTypeKey, key.attributeTypeKey, f"{pointer}/key/attributeTypeKey"
        )
        holder = self.holder(definition, key.value, f"{pointer}/key/value")
        record = self.find(holder) if holder else None
        if record is None:
            raise _not_found(
                pointer,
                {
                    "objectTypeKey": reference.objectTypeKey,
                    "attributeTypeKey": key.attributeTypeKey,
                    "value": key.value,
                },
            )
        if record.object_type_key != reference.objectTypeKey:
            raise _type_mismatch(pointer, record, reference.objectTypeKey)
        return record

    def unique_key(self, object_type_key: str, attribute_type_key: str, pointer: str) -> Any:
        """The attribute a key names: declared ``unique`` and bound to the type (ADR-010)."""
        object_type = rules.object_type(self.model, object_type_key, self.refusals)
        definition = self.model.attribute_type(attribute_type_key)
        bound = any(item.attributeTypeKey == attribute_type_key for item in object_type.attributes)
        if definition is None or not bound or not definition.features.get("unique"):
            raise api_error(
                422,
                "invalid_record_key",
                f"'{attribute_type_key}' is not an attribute declared unique on '{object_type_key}'",
                {
                    "pointer": pointer,
                    "objectTypeKey": object_type_key,
                    "attributeTypeKey": attribute_type_key,
                },
            )
        return definition

    def holder(self, definition: Any, value: Any, pointer: str) -> str | None:
        try:
            normalized = normalize_value(definition, value)
        except ApiError as error:
            raise _at(error, pointer) from None
        return self.lookup.unique_value_holder(
            definition.key, definition.valueType, self.key_form(normalized), exclude_object_id=""
        )

    def key_form(self, normalized: Any) -> Any:
        return normalized

    def unchanged(
        self,
        record: Any,
        name: str | None,
        parent_given: bool,
        parent: Any | None,
        attributes: dict[str, Any] | None,
    ) -> bool:
        """Whether the item would leave the record as it is: same name, parent and values."""
        if name is not None and name != record.name:
            return False
        if parent_given and (parent.object_id if parent else None) != record.parent_object_id:
            return False
        if not attributes:
            return True
        current = self.lookup.values(record)
        for key, value in attributes.items():
            definition = self.model.attribute_type(key)
            if definition is None:
                return False
            try:
                same = _canonical(definition, value) == _canonical(definition, current.get(key))
            except ApiError:
                return False
            if not same:
                return False
        return True

    def prefetch(self, items: Sequence[BatchItem]) -> None:
        """Read once, per kind, what ``items`` name (PG-D12): the records their references,
        targets and upsert keys name, the holders of their unique values, the values and incoming
        relations of the records they may update, the ancestors of the parents they name, and the
        relations at the other ends of their initial relations. What an item reads beyond that is
        read when it asks."""
        lookup = self.lookup
        ids: dict[str, set[str]] = {"target": set(), "parent": set(), "other": set(), "own": set()}
        keyed: dict[str, dict[str, list[Any]]] = {}
        named_by_key: dict[str, list[tuple[str, Any]]] = {name: [] for name in ids}
        relation_types: set[str] = set()

        def name(role: str, reference: RecordReference | None) -> None:
            if reference is None:
                return
            if reference.id is not None:
                ids[role].add(str(reference.id))
            else:
                named_by_key[role].append((reference.key.attributeTypeKey, reference.key.value))
                keyed.setdefault(reference.key.attributeTypeKey, []).append(reference.key.value)

        for item in items:
            if isinstance(item, BatchUpdateItem):
                name("target", item.target)
            if isinstance(item, BatchCreateItem) and item.id is not None:
                ids["own"].add(str(item.id))
            if isinstance(item, BatchUpsertItem):
                if item.key.id is not None:
                    ids["target"].add(str(item.key.id))
                else:
                    value = next(
                        (
                            attribute.value
                            for attribute in item.attributes
                            if attribute.attributeTypeKey == item.key.attributeTypeKey
                        ),
                        None,
                    )
                    named_by_key["target"].append((item.key.attributeTypeKey, value))
            if isinstance(item, BatchReplaceRelationSetItem):
                name("other", item.anchor)
                for target in item.targets:
                    name("other", target.object)
                relation_types.add(item.relationTypeKey)
                continue
            if isinstance(item, RELATION_ITEMS):
                if hasattr(item, "from_"):
                    name("other", item.from_)
                    name("other", item.to)
                    relation_types.add(item.relationTypeKey)
                continue
            name("parent", item.parent)
            for relation in getattr(item, "initialRelations", None) or ():
                name("other", relation.object)
                relation_types.add(relation.relationTypeKey)
            for attribute in item.attributes or ():
                keyed.setdefault(attribute.attributeTypeKey, []).append(attribute.value)

        # Holders of each unique value, by the value as an item gives it.
        holders: dict[tuple[str, str], set[str]] = {}
        for attribute_type_key, values in keyed.items():
            definition = self.model.attribute_type(attribute_type_key)
            if definition is None or not definition.features.get("unique"):
                continue
            forms = {
                repr(value): form
                for value in values
                if (form := self._key_form_of(definition, value)) is not None
            }
            lookup.prefetch_holders(attribute_type_key, definition.valueType, forms.values())
            for given, form in forms.items():
                holders[(attribute_type_key, given)] = lookup.prefetch_holders(
                    attribute_type_key, definition.valueType, [form]
                )
        for role, named in named_by_key.items():
            for attribute_type_key, value in named:
                ids[role] |= holders.get((attribute_type_key, repr(value)), set())

        self.prefetch_ids(ids["own"])
        lookup.prefetch_objects(set().union(*ids.values()))
        targets = list(lookup.objects(ids["target"]).values())
        lookup.prefetch_values(targets)
        lookup.prefetch_relations([item.object_id for item in targets], "incoming", None)
        lookup.prefetch_ancestors(ids["parent"])
        if relation_types and ids["other"]:
            types = sorted(relation_types)
            lookup.prefetch_relations(ids["other"], "both", types)
            scoped = any(
                binding.features.get("uniqueToAncestorTypeKey")
                for binding in self.model.objectTypeRelations
                if binding.relationTypeKey in relation_types
            )
            if scoped:
                far = {
                    end
                    for relation in lookup.relations(ids["other"], "both", types)
                    for end in (relation.from_object_id, relation.to_object_id)
                }
                lookup.prefetch_ancestors(far)
                lookup.prefetch_values(lookup.objects(far).values())
        lookup.prefetch_relation_ids(
            str(item.id)
            for item in items
            if isinstance(item, BatchUpdateRelationItem | BatchDeleteRelationItem)
        )
        # The versions of the sets the items replace, read once (0.9 B3).
        sets = []
        for item in items:
            if isinstance(item, BatchReplaceRelationSetItem):
                try:
                    anchor = self.resolve(item.anchor, "")
                except ApiError:
                    continue
                sets.append(
                    SetBinding(
                        item.relationTypeKey,
                        item.fromObjectTypeKey,
                        item.toObjectTypeKey,
                        item.direction,
                    ).key(anchor.object_id)
                )
        lookup.prefetch_set_versions(sets)

    def _key_form_of(self, definition: Any, value: Any) -> Any | None:
        if value is None or value == "":
            return None
        try:
            return self.key_form(normalize_value(definition, value))
        except ApiError:
            return None

    def prefetch_ids(self, object_ids: set[str]) -> None:
        """IDs items give the records they create, read for whether they are taken."""

    def create(self, item, object_id, parent, relations) -> Any:
        raise NotImplementedError

    def update(
        self, record, expected_version, name, parent_given, parent, attributes, audit
    ) -> int:
        raise NotImplementedError

    def delete(self, record: Any, expected_version: int) -> None:
        raise NotImplementedError

    def write(self) -> None:
        raise NotImplementedError

    def write_one(self, fields: dict[str, Any]) -> None:
        """Write one decided item, answering a row it collides with as its single write does."""
        self.write()


class _LiveItems(_Items):
    refusals = LIVE

    def __init__(self, session: Session, context: BatchContext) -> None:
        self.session = session
        self.context = context
        self.model = context.model
        # The workspace lock (PG-D5) is taken before any item resolves a record and held for the
        # inline batch or the chunk, so every item is decided and written under it (PG-D14).
        self.writes = LiveWrites(session, context.workspace_key)

    def open(self) -> LiveBatchLookup:
        self.lookup = LiveBatchLookup.of(self.session, self.context.workspace_key)
        return self.lookup

    def find(self, object_id: str) -> Any | None:
        record = self.lookup.object(object_id)
        return record if record is not None and self.lookup.shares_workspace(record) else None

    def create(self, item, object_id, parent, relations) -> Any:
        return decide_object_create(
            self.lookup,
            self.model,
            ObjectCreate(
                id=object_id,
                applicationKey=item.applicationKey,
                objectTypeKey=item.objectTypeKey,
                name=item.name,
                workspaceKey=self.context.workspace_key,
                parentObjectId=parent.object_id if parent else None,
                attributes=item.attributes,
                initialRelations=_initial_relations(relations),
            ),
        )

    def update(
        self, record, expected_version, name, parent_given, parent, attributes, audit
    ) -> int:
        fields: dict[str, Any] = {"expectedVersion": expected_version}
        if name is not None:
            fields["name"] = name
        if parent_given:
            fields["parentObjectId"] = parent.object_id if parent else None
        if attributes is not None:
            fields["attributes"] = attributes
        updated = decide_object_update(
            self.lookup, self.model, record, ObjectUpdate(**fields), audit_changes=audit
        )
        return updated.version

    def delete(self, record: Any, expected_version: int) -> None:
        apply_object_delete(
            self.session,
            self.model,
            record.object_type_key,
            record.object_id,
            expected_version,
            model_identity=self.context.model_hash or "",
        )

    def write(self) -> None:
        write_live(self.writes, self.model, self.lookup.changes())

    def write_one(self, fields: dict[str, Any]) -> None:
        try:
            self.write()
        except IntegrityError:
            if fields["action"] != "created":
                raise
            # A single live create answers a colliding row so (``create_object_record``).
            raise duplicate_relation() from None


class _ChangeSetItems(_Items):
    refusals = CHANGE_SET

    def __init__(self, session: Session, context: BatchContext) -> None:
        self.session = session
        self.context = context
        self.model = context.model
        self.change_set_id = context.change_set.id
        self.writes = ChangeSetWrites(session, context.change_set)

    def open(self) -> ChangeSetBatchLookup:
        self.lookup = ChangeSetBatchLookup.of(self.session, self.change_set_id)
        return self.lookup

    def key_form(self, normalized: Any) -> Any:
        # Change set rows hold JSON; their value index matches the stored form.
        return stored_json_value(normalized)

    def prefetch_ids(self, object_ids: set[str]) -> None:
        self.lookup.prefetch_taken(object_ids)

    def _claimed_version(self) -> int:
        # The job holds the change set's claim; its items claim nothing more.
        return self.context.change_set.version

    def create(self, item, object_id, parent, relations) -> Any:
        return decide_change_set_object_create(
            self.lookup,
            self.writes,
            self.model,
            ChangeSetObjectWrite(
                id=object_id,
                applicationKey=item.applicationKey,
                objectTypeKey=item.objectTypeKey,
                name=item.name,
                parentObjectId=parent.object_id if parent else None,
                attributes=attributes_to_dict(item.attributes),
                initialRelations=_initial_relations(relations),
                expectedChangeSetVersion=self._claimed_version(),
            ),
        )

    def update(
        self, record, expected_version, name, parent_given, parent, attributes, audit
    ) -> int:
        fields: dict[str, Any] = {
            "expectedChangeSetVersion": self._claimed_version(),
            "expectedRecordVersion": expected_version,
        }
        if name is not None:
            fields["name"] = name
        if parent_given:
            fields["parentObjectId"] = parent.object_id if parent else None
        if attributes is not None:
            fields["attributes"] = attributes_to_dict(attributes)
        updated = decide_change_set_object_update(
            self.lookup,
            self.writes,
            self.model,
            record.object_id,
            ChangeSetObjectUpdate(**fields),
            object_type_key=record.object_type_key,
            audit_changes=audit,
        )
        return updated.version

    def delete(self, record: Any, expected_version: int) -> None:
        apply_change_set_object_delete(
            self.session,
            self.change_set_id,
            record.object_type_key,
            record.object_id,
            self._claimed_version(),
            expected_version,
        )

    def write(self) -> None:
        write_change_set(self.writes, self.lookup.changes())


def _claimed(claim: SetClaim | None) -> dict[str, Any]:
    """A claimed set's new version: the claim's, advanced by the item's write."""
    return {"relationSetVersion": claim.expected + 1} if claim is not None else {}


def _initial_relations(
    relations: list[tuple[BatchInitialRelation, Any]],
) -> list[InitialRelationInput]:
    return [
        InitialRelationInput(
            relationTypeKey=relation.relationTypeKey,
            direction=relation.direction,
            otherObjectId=other.object_id,
            attributes=relation.attributes,
        )
        for relation, other in relations
    ]


def _canonical(definition: Any, value: Any) -> Any:
    """A value in one comparable form, whether given by a client, stored live or in a change set."""
    if value is None or value == "":
        return None
    return stored_json_value(normalize_value(definition, value))


def _not_found(pointer: str, reference: dict[str, Any]) -> ApiError:
    return api_error(
        404,
        "reference_not_found",
        "No record matches the reference in this batch's context",
        {"pointer": pointer, **reference},
    )


def _type_mismatch(pointer: str, record: Any, expected: str) -> ApiError:
    return api_error(
        422,
        "reference_type_mismatch",
        f"The referenced record is a '{record.object_type_key}' record, not '{expected}'",
        {
            "pointer": pointer,
            "id": record.object_id,
            "objectTypeKey": record.object_type_key,
            "applicationKey": record.application_key,
        },
    )


def _details(error: ApiError) -> dict[str, Any]:
    if isinstance(error.details, dict):
        return dict(error.details)
    return {} if error.details is None else {"errors": error.details}


def _at(error: ApiError, pointer: str) -> ApiError:
    return ApiError(
        error.status, error.code, error.message, {**_details(error), "pointer": pointer}
    )


def _error(index: int, error: ApiError) -> dict[str, Any]:
    """A rejection in the API error shape, with a pointer into the item (P2). A batch deletes
    without cascade, so a dependants refusal carries no preview token (§B3)."""
    details = _details(error)
    details.pop("deletionPreviewToken", None)
    if "pointer" not in details:
        field = _POINTERS.get(error.code)
        details["pointer"] = f"/items/{index}/{field}" if field else f"/items/{index}"
    return {"code": error.code, "message": error.message, "details": details}
