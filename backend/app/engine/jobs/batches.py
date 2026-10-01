"""Batches: a job of kind ``batch`` whose items go through the single-write services (ADR-036).

Each item is applied by the service its single-write route uses, in a savepoint of its own, so it
is validated exactly as that write and refused with the same code. The batch adds what single writes
lack (INTEGRATION_API B): records named by a unique key, upsert, ``unchanged`` and the failure
policies.

- ``atomic``: items apply in order, each against what the items before it left (D23); the first
  rejection rolls every item back and the others are ``unprocessed``.
- ``independent``: a rejected item rolls back only itself.

In a change set the job claims the change set's version once for all its items (P3); a job that
applies nothing leaves the version as it was.
"""

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Any

from sqlalchemy.orm import Session

from ...errors import ApiError, api_error
from ...models.commands import (
    BatchCreateItem,
    BatchDeleteItem,
    BatchInitialRelation,
    BatchItem,
    BatchRequest,
    BatchUpdateItem,
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
    apply_change_set_object_create,
    apply_change_set_object_delete,
    apply_change_set_object_update,
)
from ..indexes import matrix_states
from ..model.registry import resolve_model_snapshot
from ..records import rules
from ..records.attributes import current_attribute_values
from ..records.audit import audit_cause
from ..records.context import ChangeSetLookup, LiveLookup
from ..records.deletion import apply_object_delete
from ..records.objects import apply_object_create, apply_object_update, attributes_to_dict
from ..records.refusals import CHANGE_SET, LIVE
from ..records.values import normalize_value, stored_json_value
from ..records.writes import ChangeSetWrites
from ..workspaces.catalogue import resolve_workspace
from .store import ItemOutcome

# Where in an item a single write's refusal points, by its code; otherwise at the item.
_POINTERS = {
    "version_conflict": "expectedVersion",
    "parent_required": "parent",
    "parent_wrong_scope": "parent",
    "invalid_parent_type": "parent",
    "parent_cycle": "parent",
    "object_already_exists": "id",
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
    before each item; when it answers ``True`` the items are rolled back and ``JobCancelled`` is
    raised.
    """
    writer = (
        _ChangeSetItems(session, context) if context.change_set else _LiveItems(session, context)
    )
    batch = _Batch(writer, items, policy, on_existing, should_stop)
    outcomes: list[ItemOutcome] = []
    outer = session.begin_nested()
    try:
        # The outer savepoint's release applies the items' matrix notes once (ADR-033).
        with audit_cause(session, "job", job_id), matrix_states.deferred(session):
            if context.change_set is not None:
                with ChangeSetWrites(session, context.change_set).hold_claim(
                    expected_change_set_version
                ):
                    batch.apply_all(outcomes)
            else:
                batch.apply_all(outcomes)
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
        outer.commit()
    return outcomes


class JobCancelled(Exception):
    """A cancel request reached the job while its items were applied (D28)."""


class _Batch:
    def __init__(
        self,
        writer: _Items,
        items: Sequence[tuple[int, BatchItem]],
        policy: str,
        on_existing: str,
        should_stop: Callable[[], bool] | None,
    ) -> None:
        self.writer = writer
        self.items = items
        self.policy = policy
        self.on_existing = on_existing
        self.should_stop = should_stop
        self.session = writer.session

    def apply_all(self, outcomes: list[ItemOutcome]) -> None:
        for index, item in self.items:
            if self.should_stop is not None and self.should_stop():
                raise JobCancelled
            try:
                with self.session.begin_nested():
                    fields = self.apply(index, item)
                outcomes.append(ItemOutcome(index, item.ref, "applied", fields))
            except ApiError as error:
                outcomes.append(
                    ItemOutcome(index, item.ref, "rejected", {"error": _error(index, error)})
                )
                if self.policy == "atomic":
                    return

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
        raise AssertionError(f"Unknown batch item {item!r}")

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
    """What an item does in one context; ``_LiveItems`` and ``_ChangeSetItems`` read alike."""

    session: Session
    model: EngineModel
    refusals: Any
    lookup: Any

    def find(self, object_id: str) -> Any | None:
        return self.lookup.object(object_id)

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
        current = self.values(record)
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

    def values(self, record: Any) -> dict[str, Any]:
        raise NotImplementedError

    def create(self, item, object_id, parent, relations) -> Any:
        raise NotImplementedError

    def update(
        self, record, expected_version, name, parent_given, parent, attributes, audit
    ) -> int:
        raise NotImplementedError

    def delete(self, record: Any, expected_version: int) -> None:
        raise NotImplementedError


class _LiveItems(_Items):
    refusals = LIVE

    def __init__(self, session: Session, context: BatchContext) -> None:
        self.session = session
        self.context = context
        self.model = context.model
        self.lookup = LiveLookup.of(session, context.workspace_key)

    def find(self, object_id: str) -> Any | None:
        record = self.lookup.object(object_id)
        return record if record is not None and self.lookup.shares_workspace(record) else None

    def values(self, record: Any) -> dict[str, Any]:
        return current_attribute_values(self.session, record.object_id)

    def create(self, item, object_id, parent, relations) -> Any:
        return apply_object_create(
            self.session,
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
        updated = apply_object_update(
            self.session,
            self.model,
            record.object_type_key,
            record.object_id,
            ObjectUpdate(**fields),
            audit_changes=audit,
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


class _ChangeSetItems(_Items):
    refusals = CHANGE_SET

    def __init__(self, session: Session, context: BatchContext) -> None:
        self.session = session
        self.context = context
        self.model = context.model
        self.change_set_id = context.change_set.id
        self.lookup = ChangeSetLookup.of(session, self.change_set_id)

    def key_form(self, normalized: Any) -> Any:
        # Change set rows hold JSON; their value index matches the stored form.
        return stored_json_value(normalized)

    def values(self, record: Any) -> dict[str, Any]:
        return self.lookup.values(record)

    def _claimed_version(self) -> int:
        # The job holds the change set's claim; its items claim nothing more.
        return self.context.change_set.version

    def create(self, item, object_id, parent, relations) -> Any:
        return apply_change_set_object_create(
            self.session,
            self.change_set_id,
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
        row = apply_change_set_object_update(
            self.session,
            self.change_set_id,
            record.object_id,
            ChangeSetObjectUpdate(**fields),
            object_type_key=record.object_type_key,
            audit_changes=audit,
        )
        return row.version

    def delete(self, record: Any, expected_version: int) -> None:
        apply_change_set_object_delete(
            self.session,
            self.change_set_id,
            record.object_type_key,
            record.object_id,
            self._claimed_version(),
            expected_version,
        )


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
