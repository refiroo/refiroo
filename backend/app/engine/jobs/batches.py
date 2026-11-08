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
write's answer. A run of delete items is decided and written together by the deletion path the
single delete shares (``records/deletion.py``; 0.9 K2b, D120–D123): a cascading item is confirmed
by its token, which a preview gives, and a record an earlier item of the job deleted answers
``unchanged`` naming that item (D122).

The batch adds what single writes lack (INTEGRATION_API B): records named by a unique key, upsert,
``unchanged`` and the failure policies.

- ``atomic``: items apply in order, each against what the items before it left; the first
  rejection rolls every item back and the others are ``unprocessed``.
- ``independent``: a rejected item is left out; the others apply.

In a change set the job claims the change set's version once for all its items (P3); a job that
applies nothing leaves the version as it was. A live batch holds the workspace lock for the inline
batch or the chunk (PG-D14).
"""

from collections.abc import Callable, Iterable, Iterator, Sequence
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
    BatchEnsureNoRelationItem,
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
    decide_change_set_object_create,
    decide_change_set_object_update,
)
from ..indexes import matrix_states
from ..indexes.unique_values import DuplicateValueWritten
from ..model import expected_release, registry
from ..model.registry import resolve_model_snapshot
from ..records import rules
from ..records.audit import audit_cause, trial_run
from ..records.batch_lookup import BatchLookup, ChangeSetBatchLookup, LiveBatchLookup
from ..records.bulk import write_change_set, write_live
from ..records.counterparts import counterpart, held_elsewhere
from ..records.deletion import (
    ChangeSetScope,
    Deletion,
    DeletionScope,
    LiveScope,
    delete_records,
    deleted_by_job,
    deletion_preview_changed,
)
from ..records.objects import (
    attributes_to_dict,
    decide_object_create,
    decide_object_update,
    duplicate_relation,
)
from ..records.refusals import CHANGE_SET, ELSEWHERE, LIVE, counterparts_across_models
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
from .store import ItemOutcome, applied_deletions

# A cancel request is looked for before every this many items an atomic job decides, and before
# its items are written (D28).
STOP_CHECK_ITEMS = 500
# The ref an import's binding gives the delete item of a record its file no longer names (0.10 A5c).
MISSING_REF = "missing!"

# Where in an item a single write's refusal points, by its code; otherwise at the item.
_POINTERS = {
    "VERSION_CONFLICT": "expectedVersion",
    "PARENT_REQUIRED": "parent",
    "PARENT_WRONG_SCOPE": "parent",
    "INVALID_PARENT_TYPE": "parent",
    "PARENT_CYCLE": "parent",
    "OBJECT_ALREADY_EXISTS": "id",
    "RELATION_NOT_FOUND": "id",
    "RELATION_SET_VERSION_CONFLICT": "expectedRelationSetVersion",
    "RELATION_SET_CLAIM_INCOMPLETE": "expectedRelationSetVersion",
    "DELETION_PREVIEW_REQUIRED": "deletionPreviewToken",
    "DELETION_PREVIEW_CHANGED": "deletionPreviewToken",
    "UNKNOWN_RELATION_ATTRIBUTES": "attributes",
    "MISSING_REQUIRED_RELATIONS": "initialRelations",
    "DUPLICATE_INITIAL_RELATION": "initialRelations",
    **{
        code: "attributes"
        for code in (
            "UNKNOWN_ATTRIBUTES",
            "READ_ONLY_ATTRIBUTES",
            "MISSING_REQUIRED_ATTRIBUTES",
            "DUPLICATE_ATTRIBUTE",
            "DUPLICATE_ATTRIBUTE_VALUE",
            "INVALID_ATTRIBUTE_VALUE",
            "ATTRIBUTE_BELOW_MINIMUM",
            "ATTRIBUTE_ABOVE_MAXIMUM",
            "OBJECT_ATTRIBUTE_RULE_VIOLATION",
            "INVALID_EFFECTIVE_PERIOD",
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
            "INVALID_BATCH_CONTEXT",
            "Name workspaceKey for live data or changeSetId for a change set, not both",
            {"pointer": "/workspaceKey" if request.workspaceKey else "/changeSetId"},
        )
    if request.changeSetId is None and request.expectedChangeSetVersion is not None:
        raise api_error(
            422,
            "INVALID_BATCH_CONTEXT",
            "expectedChangeSetVersion applies only with changeSetId",
            {"pointer": "/expectedChangeSetVersion"},
        )
    if request.changeSetId is not None and request.expectedChangeSetVersion is None:
        raise api_error(
            409,
            "CHANGE_SET_REQUIRED",
            "expectedChangeSetVersion is required when targeting a change set",
        )


def open_batch_context(session: Session, request: BatchRequest) -> BatchContext:
    """The request's context, or the request-level refusal that creates no job (P2)."""
    check_batch_context(request)
    if request.changeSetId is None:
        workspace = resolve_workspace(session, request.workspaceKey, require_active=True)
        snapshot = resolve_model_snapshot(session, workspace.key)
        expected_release.check(session, workspace.key, snapshot.release_db_id)
        return BatchContext(
            workspace.key, None, snapshot.model, snapshot.release_db_id, snapshot.model_hash
        )
    change_set = load_change_set(session, str(request.changeSetId), for_update=True)
    expected_release.check(
        session, change_set.workspace_key, change_set.model_release_id, change_set_id=change_set.id
    )
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
        other_workspace_ids=request.otherWorkspaceIds,
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
    other_workspace_ids: str = "refuse",
    previewing: bool = False,
    file_rows: bool = False,
    own_links: bool = False,
) -> list[ItemOutcome]:
    """Apply ``items`` (each with its index in the job) under the policy; the caller records the
    outcomes and commits. An inline batch is one call; a background job one call per chunk; a
    preview (``previewing``) one call the caller rolls back.

    ``file_rows``: the items are a file's rows bound by an import, a dry run or a profile's check
    (``ROW_KINDS``), whose binding alone gives a delete item the ref ``missing!…``: a record its
    file no longer names, deleted with its own relationships (0.10 A5c, D104). ``own_links``:
    every delete item is so deleted (a move's deletion in its source, 0.11 X3, D134).

    A stale ``expectedChangeSetVersion`` raises before any item runs. ``should_stop`` is asked
    before every ``STOP_CHECK_ITEMS`` items and before the items are written; when it answers
    ``True`` the items are rolled back and ``JobCancelled`` is raised.
    """
    outer = session.begin_nested()
    try:
        # The outer savepoint's release applies the items' matrix notes once (ADR-033).
        with (
            audit_cause(session, "job", job_id),
            trial_run(session) if previewing else nullcontext(),
            matrix_states.deferred(session),
        ):
            claim = (
                ChangeSetWrites(session, context.change_set).hold_claim(expected_change_set_version)
                if context.change_set is not None
                else nullcontext()
            )
            with claim:
                outcomes = _Batch(
                    session,
                    context,
                    items,
                    policy,
                    on_existing,
                    should_stop,
                    other_workspace_ids,
                    job_id=job_id,
                    previewing=previewing,
                    file_rows=file_rows,
                    own_links=own_links,
                ).run()
    except JobCancelled:
        outer.rollback()
        raise
    rejected = any(outcome.status == "rejected" for outcome in outcomes)
    if policy == "atomic" and rejected:
        outer.rollback()
        rolled_back = {"reason": "BATCH_ROLLED_BACK"}
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
    """Runs of items decided together: delete items and the others in runs of their own, in
    order (0.9 K2b)."""
    start = 0
    for position in range(1, len(items) + 1):
        if position == len(items) or isinstance(items[position][1], BatchDeleteItem) != isinstance(
            items[start][1], BatchDeleteItem
        ):
            yield items[start:position]
            start = position


class _Batch:
    def __init__(
        self,
        session: Session,
        context: BatchContext,
        items: Sequence[tuple[int, BatchItem]],
        policy: str,
        on_existing: str,
        should_stop: Callable[[], bool] | None,
        other_workspace_ids: str = "refuse",
        *,
        job_id: str,
        previewing: bool = False,
        file_rows: bool = False,
        own_links: bool = False,
    ) -> None:
        self.writer = (
            _ChangeSetItems(session, context) if context.change_set else _LiveItems(session, context)
        )
        self.writer.counterparts = other_workspace_ids == "counterparts"
        self.items = items
        self.policy = policy
        self.on_existing = on_existing
        self.should_stop = should_stop
        self.session = session
        self.job_id = job_id
        self.previewing = previewing
        self.file_rows = file_rows
        self.own_links = own_links
        # The record each delete item of this call deleted, by its item: an earlier chunk's are
        # read from the job's outcomes (D122).
        self.deleting: dict[str, int] = {}

    def run(self) -> list[ItemOutcome]:
        outcomes: list[ItemOutcome] = []
        for segment in _segments(self.items):
            deletes = isinstance(segment[0][1], BatchDeleteItem)
            go_on = self._deletes(segment, outcomes) if deletes else self._together(segment, outcomes)
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
        self.writer.translate_ids(_named_ids(item for _index, item in segment))
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
            except (IntegrityError, DuplicateValueWritten):
                # A row the rules did not foresee (PG-D15), or a unique value written past them
                # (J2a): each item again as a batch of one.
                return self._one_by_one(segment, outcomes)
        outcomes.extend(decided)
        return True

    def _one_by_one(
        self, segment: Sequence[tuple[int, BatchItem]], outcomes: list[ItemOutcome]
    ) -> bool:
        """Apply each item as a batch of one in a savepoint of its own; ``False`` when an atomic
        batch stops at a rejection."""
        self.writer.translate_ids(_named_ids(item for _index, item in segment))
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

    def _deletes(
        self, segment: Sequence[tuple[int, BatchItem]], outcomes: list[ItemOutcome]
    ) -> bool:
        """A run of delete items, decided and written together by the deletion path (D123);
        ``False`` when an atomic batch stops at a rejection."""
        self.writer.translate_ids(_named_ids(item for _index, item in segment))
        lookup = self.writer.open()
        lookup.prefetch_objects(
            {
                self.writer.translate(str(item.target.id))
                for _index, item in segment
                if item.target.id is not None
            }
        )
        found: dict[int, Any] = {}
        decided: dict[int, ItemOutcome] = {}
        missing: dict[int, str] = {}
        for number, (index, item) in enumerate(segment):
            if number % STOP_CHECK_ITEMS == 0:
                self._stop_check()
            at = f"/items/{index}"
            try:
                self.writer.refuse_across_models(item)
                record = self.writer.resolve(item.target, f"{at}/target")
            except ApiError as error:
                if error.code == "REFERENCE_NOT_FOUND" and item.target.id is not None:
                    missing[index] = self.writer.translate(str(item.target.id))
                decided[index] = _rejected(index, item, error)
                continue
            # A counterpart's version is not the file's, which is the other workspace's (D98).
            claimed = None if self.writer.translated(item.target) else item.expectedVersion
            if claimed is not None and claimed != record.version:
                error = (
                    deletion_preview_changed()
                    if item.cascade and item.deletionPreviewToken is not None
                    else self.writer.version_conflict(record)
                )
                # The version found, as a version conflict names it: Preview again claims it.
                error.details = {"currentVersion": record.version, **_details(error)}
                decided[index] = _rejected(index, item, error)
                continue
            # Identity only: the records are deleted and expired by the run.
            found[index] = (record.object_id, record.object_type_key)
        # A record this job deleted already, with an earlier item's impact (D122).
        gone = deleted_by_job(self.session, self.job_id, sorted(set(missing.values())))
        if gone:
            earlier = {**applied_deletions(self.session, self.job_id, set(gone.values())), **self.deleting}
            for index, object_id in missing.items():
                owner = earlier.get(gone.get(object_id, ""))
                if owner is not None and owner < index:
                    item = dict(segment)[index]
                    decided[index] = ItemOutcome(
                        index,
                        item.ref,
                        "applied",
                        {"action": "unchanged", "id": object_id, "deletedWithItem": owner},
                    )
        first_refused = min(
            (index for index, outcome in decided.items() if outcome.status == "rejected"),
            default=None,
        )
        atomic = self.policy == "atomic"
        runs = [
            Deletion(
                index,
                *found[index],
                item.cascade,
                item.deletionPreviewToken,
                own_links=self.own_links
                or (self.file_rows and (item.ref or "").startswith(MISSING_REF)),
            )
            for index, item in segment
            if index in found and not (atomic and first_refused is not None and index > first_refused)
        ]
        results = {
            result.item: result
            for result in delete_records(
                self.writer.deletion_scope(),
                runs,
                previewing=self.previewing,
                atomic=atomic,
            )
        }
        items = dict(segment)
        for result in results.values():
            item, (object_id, object_type_key) = items[result.item], found[result.item]
            identity = {"id": object_id, "objectTypeKey": object_type_key}
            if result.error is not None:
                decided[result.item] = _rejected(result.item, item, result.error)
            elif result.deleted_with is not None:
                decided[result.item] = ItemOutcome(
                    result.item,
                    item.ref,
                    "applied",
                    {"action": "unchanged", **identity, "deletedWithItem": result.deleted_with},
                )
            else:
                self.deleting[object_id] = result.item
                decided[result.item] = ItemOutcome(
                    result.item, item.ref, "applied", {"action": "deleted", **identity, "impact": result.impact}
                )
        for index, _item in segment:
            if index not in decided:
                break
            outcomes.append(decided[index])
            if atomic and decided[index].status == "rejected":
                return False
        return True

    def apply(self, index: int, item: BatchItem) -> dict[str, Any]:
        at = f"/items/{index}"
        self.writer.refuse_across_models(item)
        if isinstance(item, BatchCreateItem):
            if item.id is None:
                return self.create(item, at, object_id=None)
            return self.writer.sourced(
                str(item.id), self.create(item, at, object_id=self.writer.translate(str(item.id)))
            )
        if isinstance(item, BatchUpdateItem):
            record = self.writer.resolve(item.target, f"{at}/target")
            # The file's version is the other workspace's record's (D98).
            claimed = None if self.writer.translated(item.target) else item.expectedVersion
            return self.update(item, record, at, claimed)
        if isinstance(item, BatchUpsertItem):
            return self.upsert(item, at)
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
        # A relationship between counterparts claims no version of the other workspace's (D98).
        claimed = not (self.writer.translated(item.from_) or self.writer.translated(item.to))
        if isinstance(item, BatchEnsureNoRelationItem):
            return self.apart(item, source, target, existing, claimed)
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
        return self.ensure(item, at, source, target, existing, claimed)

    def apart(
        self,
        item: BatchEnsureNoRelationItem,
        source: Any,
        target: Any,
        existing: Any | None,
        claimed: bool,
    ) -> dict[str, Any]:
        """An ``ensureNoRelation`` (0.9 K3, D129): the relation joining the ends deleted by the
        single delete's step, with its refusals; ``unchanged`` when none joins them."""
        lookup, model = self.writer.lookup, self.writer.model
        rules.relation_binding(
            model, item.relationTypeKey, source.object_type_key, target.object_type_key,
            lookup.refusals,
        )
        if existing is None:
            return {"action": "unchanged"}
        expected = item.expectedVersion if claimed and item.expectedVersion else existing.version
        decide_relation_delete(lookup, model, existing, expected)
        return {"action": "deleted", "relationId": existing.relation_id}

    def replace_set(self, item: BatchReplaceRelationSetItem, at: str) -> dict[str, Any]:
        """A set replacement (§B4): the mapping PUT's step with any number of targets."""
        set_ = SetBinding(
            item.relationTypeKey, item.fromObjectTypeKey, item.toObjectTypeKey, item.direction
        )
        anchor_type = (
            item.fromObjectTypeKey if item.direction == "outgoing" else item.toObjectTypeKey
        )
        anchor = self._typed(item.anchor, f"{at}/anchor", anchor_type)
        # The set's version as this item finds it: a preview needs no claim and reports it, and
        # confirming carries it into the item (0.9 K3, D130).
        found = self.writer.lookup.set_version(set_.key(anchor.object_id))
        expected = self._claim(item.expectedRelationSetVersion)
        if expected is None and self.previewing:
            expected = found
        try:
            return self._replace(item, at, set_, anchor, expected, found)
        except ApiError as error:
            # A refusal names the version found too, so a refused preview item carries its claim.
            error.details = {"relationSetVersion": found, **_details(error)}
            raise

    def _replace(
        self,
        item: BatchReplaceRelationSetItem,
        at: str,
        set_: SetBinding,
        anchor: Any,
        expected: int | None,
        found: int,
    ) -> dict[str, Any]:
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
            expected=expected,
            on_existing=self.on_existing,
            pointer=at,
        )
        return {
            "action": "updated" if replaced.changed else "unchanged",
            "relationSetVersion": replaced.version,
            "previousRelationSetVersion": found,
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

    def _claim(self, version: int | None) -> int | None:
        """A file's version claim: an import told to update records "anyway" writes over what it
        finds, so the versions its rows carry from the export are not held against the record
        (0.13 DOC11). A batch's own claims are always held."""
        return None if self.file_rows and self.on_existing == "overwrite" else version

    def ensure(
        self, item: Any, at: str, source: Any, target: Any, existing: Any, claimed: bool = True
    ) -> dict[str, Any]:
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
        expected, audit = self._claim(item.expectedVersion if claimed else None), {}
        if expected is None:
            if self.on_existing != "overwrite":
                raise api_error(
                    409,
                    "VERSION_REQUIRED",
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
        expected_version = self._claim(expected_version)
        if expected_version is None:
            if self.on_existing != "overwrite":
                raise api_error(
                    409,
                    "VERSION_REQUIRED",
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
        source_id = None
        if item.key.id is not None:
            object_id = self.writer.translate(str(item.key.id))
            if object_id != str(item.key.id):
                source_id = str(item.key.id)
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
                    "MISSING_RECORD_KEY",
                    f"The upsert key '{key}' needs a value among the item's attributes",
                    {"pointer": f"{at}/attributes", "attributeTypeKey": key},
                )
            object_id = None
            holder = self.writer.holder(definition, value, f"{at}/attributes")
            record = self.writer.find(holder) if holder else None
        if record is None:
            outcome = self.create(item, at, object_id=object_id)
        else:
            if (record.object_type_key, record.application_key) != (
                item.objectTypeKey,
                item.applicationKey,
            ):
                raise _type_mismatch(f"{at}/key", record, item.objectTypeKey)
            # A counterpart's version is not the file's, which is the other workspace's (D98).
            claimed = None if source_id else item.expectedVersion
            outcome = self.update(item, record, at, claimed)
        return {**outcome, "sourceId": source_id} if source_id else outcome


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

    # With counterparts (0.9 J5, D96): the segment's IDs another workspace's records hold, each
    # with its counterpart here and that workspace, read once per segment by ``translate_ids``.
    # IDs of records whose workspace runs another model are not translated: an item naming one is
    # refused (0.11 M4, D44), with that workspace and its model's key.
    counterparts = False
    counterpart_of: dict[str, tuple[str, str]]
    across_models: dict[str, tuple[str, str]]

    def translate_ids(self, object_ids: Iterable[str]) -> None:
        """Which of ``object_ids`` are another workspace's records: one statement per segment."""
        self.counterpart_of = {}
        self.across_models = {}
        if not self.counterparts:
            return
        workspace_key = self.context.workspace_key
        model_key = self.model.release.key
        for object_id, holder, holder_model in held_elsewhere(
            self.session, workspace_key, object_ids
        ):
            if holder_model != model_key:
                self.across_models[object_id] = (holder, holder_model)
            else:
                self.counterpart_of[object_id] = (counterpart(workspace_key, object_id), holder)

    def refuse_across_models(self, item: BatchItem) -> None:
        """Refuse an item naming a record of a workspace that runs another model (D44)."""
        for object_id in sorted(_named_ids((item,)) & self.across_models.keys()):
            holder, holder_model = self.across_models[object_id]
            raise counterparts_across_models(
                object_id, holder, holder_model, self.model.release.key
            )

    def translate(self, object_id: str) -> str:
        """The ID an item's ID stands for here: its counterpart when another workspace's record
        holds it, otherwise itself (this workspace's own, or no record's)."""
        found = self.counterpart_of.get(object_id)
        return found[0] if found else object_id

    def translated(self, reference: RecordReference | None) -> bool:
        return (
            reference is not None
            and reference.id is not None
            and str(reference.id) in self.counterpart_of
        )

    def sourced(self, source_id: str, outcome: dict[str, Any]) -> dict[str, Any]:
        """An outcome naming the file's ID when the record written is its counterpart."""
        return {**outcome, "sourceId": source_id} if source_id in self.counterpart_of else outcome

    def find(self, object_id: str) -> Any | None:
        return self.lookup.object(object_id)

    def relation(self, relation_id: str, pointer: str) -> Any:
        """A relation of the context by its ID, as the items before it leave it."""
        relation = self.lookup.relation(relation_id)
        if relation is None:
            raise api_error(
                404,
                "RELATION_NOT_FOUND",
                f"Relation '{relation_id}' not found",
                {"pointer": pointer, "id": relation_id},
            )
        return relation

    def resolve(self, reference: RecordReference, pointer: str) -> Any:
        """The record a reference names (§B2), against the context as it stands now."""
        if reference.id is not None:
            given = str(reference.id)
            record = self.find(self.translate(given))
            if record is None:
                if given in self.counterpart_of:
                    raise _counterpart_missing(pointer, given, self.counterpart_of[given][1])
                elsewhere = self.lookup.other_workspace(given)
                raise _not_found(pointer, {"id": given}, elsewhere)
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
                "INVALID_RECORD_KEY",
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
                ids[role].add(self.translate(str(reference.id)))
            else:
                named_by_key[role].append((reference.key.attributeTypeKey, reference.key.value))
                keyed.setdefault(reference.key.attributeTypeKey, []).append(reference.key.value)

        for item in items:
            if isinstance(item, BatchUpdateItem):
                name("target", item.target)
            if isinstance(item, BatchCreateItem) and item.id is not None:
                ids["own"].add(self.translate(str(item.id)))
            if isinstance(item, BatchUpsertItem):
                if item.key.id is not None:
                    ids["target"].add(self.translate(str(item.key.id)))
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
        # Which named records meet the candidate criteria of the bindings the items relate them
        # through, one statement per restricted end (0.9 K7, D177).
        restricted = [
            binding
            for binding in self.model.objectTypeRelations
            if binding.relationTypeKey in relation_types and binding.candidates
        ]
        if restricted and ids["other"]:
            # Whether a record is under one the chunk lays is read up its ancestors.
            lookup.prefetch_ancestors(ids["other"] | ids["target"])
            named = list(lookup.objects(ids["other"] | ids["target"]).values())
            for binding in restricted:
                for end, type_key in (
                    ("from", binding.fromObjectTypeKey),
                    ("to", binding.toObjectTypeKey),
                ):
                    criteria = binding.candidates_at(end)
                    if criteria:
                        lookup.prefetch_candidates(
                            self.model,
                            type_key,
                            criteria,
                            [record.object_id for record in named if record.object_type_key == type_key],
                        )
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

    def deletion_scope(self) -> DeletionScope:
        """Where a run of delete items deletes (``records/deletion.py``)."""
        raise NotImplementedError

    def version_conflict(self, record: Any) -> ApiError:
        """A delete item's stale version, refused as its single delete refuses it."""
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

    def deletion_scope(self) -> DeletionScope:
        return LiveScope(
            self.session, self.model, self.context.workspace_key, self.context.model_hash or ""
        )

    def version_conflict(self, record: Any) -> ApiError:
        return api_error(
            409, "VERSION_CONFLICT", "Object version has changed", {"currentVersion": record.version}
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

    def deletion_scope(self) -> DeletionScope:
        return ChangeSetScope(self.session, self.model, self.context.change_set)

    def version_conflict(self, record: Any) -> ApiError:
        return api_error(
            409,
            "VERSION_CONFLICT",
            "Object record version has changed",
            {"currentVersion": record.version},
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


def _named_ids(items: Iterable[BatchItem]) -> set[str]:
    """Every record ID the items name by ID: the records they create or upsert, their targets,
    parents, relationship ends, initial relations and set members (0.9 J5, D100). Relationship IDs
    are not record IDs and have no counterpart."""
    found: set[str] = set()

    def add(reference: RecordReference | None) -> None:
        if reference is not None and reference.id is not None:
            found.add(str(reference.id))

    for item in items:
        if isinstance(item, BatchCreateItem) and item.id is not None:
            found.add(str(item.id))
        if isinstance(item, BatchUpsertItem):
            add(item.key)
        add(getattr(item, "target", None))
        add(getattr(item, "parent", None))
        add(getattr(item, "from_", None))
        add(getattr(item, "to", None))
        add(getattr(item, "anchor", None))
        for relation in getattr(item, "initialRelations", None) or ():
            add(relation.object)
        for member in getattr(item, "targets", None) or ():
            add(member.object)
    return found


def _counterpart_missing(pointer: str, given: str, workspace_key: str) -> ApiError:
    """A reference to another workspace's record whose counterpart is not here yet (0.9 J5)."""
    parts = [part for part in pointer.split("/") if part and not part.isdigit()]
    field = next(
        (_REFERENCE_FIELDS[part] for part in reversed(parts) if part in _REFERENCE_FIELDS),
        "reference",
    )
    return api_error(
        404,
        "REFERENCE_NOT_FOUND",
        f"The {field} is record '{given}' of workspace '{workspace_key}', whose counterpart is not "
        "in this workspace: load the file holding it first",
        {"pointer": pointer, "id": given, "workspaceKey": workspace_key},
    )


# What an item's reference is for, by the field its pointer ends in (0.9 J4a).
_REFERENCE_FIELDS = {
    "parent": "parent",
    "target": "target",
    "from": "relationship's start",
    "to": "relationship's end",
    "object": "related record",
    "anchor": "set's record",
}


def _not_found(pointer: str, reference: dict[str, Any], elsewhere: str | None = None) -> ApiError:
    """A reference that names no record of the context. When its ID is a record of another
    workspace, the refusal says so: a file's IDs from another workspace are the common cause, and
    every row naming such a record is refused for it (0.9 J4a)."""
    if elsewhere is None:
        return api_error(
            404,
            "REFERENCE_NOT_FOUND",
            "No record matches the reference in this batch's context",
            {"pointer": pointer, **reference},
        )
    parts = [part for part in pointer.split("/") if part and not part.isdigit()]
    field = next(
        (_REFERENCE_FIELDS[part] for part in reversed(parts) if part in _REFERENCE_FIELDS),
        "reference",
    )
    return api_error(
        404,
        "REFERENCE_NOT_FOUND",
        f"The {field} is record '{reference['id']}' of workspace '{elsewhere}', not of this one. "
        f"{ELSEWHERE}",
        {"pointer": pointer, **reference, "workspaceKey": elsewhere},
    )


def _type_mismatch(pointer: str, record: Any, expected: str) -> ApiError:
    return api_error(
        422,
        "REFERENCE_TYPE_MISMATCH",
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


def _rejected(index: int, item: BatchItem, error: ApiError) -> ItemOutcome:
    return ItemOutcome(index, item.ref, "rejected", {"error": _error(index, error)})


def _error(index: int, error: ApiError) -> dict[str, Any]:
    """A rejection in the API error shape, with a pointer into the item (P2); a dependants
    refusal carries the item's ``impact`` with its token (0.9 K2b)."""
    details = _details(error)
    if "pointer" not in details:
        field = _POINTERS.get(error.code)
        details["pointer"] = f"/items/{index}/{field}" if field else f"/items/{index}"
    return {"code": error.code, "message": error.message, "details": details}
