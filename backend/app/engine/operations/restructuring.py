"""The restructuring planner: a record and its subtree, planned before it changes (Base 0.8 C2).

An operation moves a record or changes its type in a change set (ADR-034). The planner works out
what that means for the record and every record below it, by the model alone:

- the types the record may have at its target: the one asked for, the current one where it is
  allowed, the only possible one, or a question asked once per (type, parent type) pair;
- level by level, each child the record's new type cannot contain becomes a type the new parent can
  contain, by the same rule; a child it can still contain keeps its type and the cascade stops;
- per (old type, new type) pair, the D40 source of each attribute of the new type (the same attribute
  type, display to display, the one unique and required attribute to the other's), which a choice
  per pair overrides, with the other compatible sources as alternatives;
- per record, each value kept, mapped, restored, given as an input or left empty, what has no place,
  the relationships kept or without a place, and the inputs still needed;
- values and relationships offered back from the record's effective ``reclassified`` events: those of
  the current change set and of published change sets, never of a discarded one;
- refusals, per record or for the operation.

A plan that is otherwise ready is dry-run through the change set write services (C1's
:func:`~.type_changes.change_object_type`), so the preview refuses what applying would; the dry run
stops at the first refusal. The plan is not stored: its digest covers the change set's identity and
version, the normalized request and the complete plan, and applying recomputes it in the write
transaction. One operation changes at most :data:`RECORD_LIMIT` records (D41).

C3 adds the other operation kinds (``insertLevel``, ``removeLevel``, ``changeTypeUnder``), the
paging of the plan's records and the routes (``management/routers/change_sets.py``).
"""

import hashlib
import json
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field, replace
from typing import Any, Literal
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from ...common.encoding import to_jsonable
from ...common.pagination import Page, PageRequest, paginate_sequence
from ...db import name_ranks
from ...errors import ApiError, api_error
from ...models.database import AuditEvent, ChangeSet
from ...models.schema import EngineModel, ObjectTypeDefinition
from ..change_sets.access import change_set_model, load_change_set
from ..change_sets.records import (
    place_record,
    stored_attributes,
    tombstone_change_set_records,
    validate_change_set_relation,
    write_new_change_set_object,
)
from ..model.placements import application_type_keys, possible_types
from ..records import rules
from ..records.attributes import validate_attributes, validate_object_attribute_rules
from ..records.audit import record_audit_event
from ..records.context import ChangeSetLookup
from ..records.feed import object_subject
from ..records.refusals import CHANGE_SET
from ..records.values import stored_json_value
from ..records.writes import ChangeSetWrites
from .type_changes import (
    KEEP_PARENT,
    Keep,
    RelationInput,
    RelationshipState,
    RestoredRelation,
    TypeChange,
    attribute_value_types_compatible,
    change_object_type,
    editable_row,
)

# D41 as D44 set it: the most records one operation changes, so that the preview's dry run through
# the per-record write path stays at a few seconds.
RECORD_LIMIT = 500
# The refusals a plan lists; ``refusalCount`` counts them all.
REFUSALS_SHOWN = 20
_CHUNK = 500

PlanStatus = Literal["ready", "needsInput", "refused"]
MappingRule = Literal["sameType", "display", "uniqueRequired", "choice", "none"]

# Engine write errors the dry run meets, as the plan's refusal codes; others keep the engine's code.
_REFUSAL_CODES = {
    "DUPLICATE_ATTRIBUTE_VALUE": "uniqueness",
    "DUPLICATE_RELATION_SCOPE": "uniqueness",
    "PARENT_CYCLE": "cycle",
    "OBJECT_TYPE_NOT_IN_APPLICATION": "application",
    "PARENT_WRONG_SCOPE": "application",
    "INVALID_PARENT_TYPE": "typeNotAllowed",
    "CHILD_TYPE_NOT_ALLOWED": "noPossibleType",
    "PARENT_REQUIRED": "notRoot",
    "REQUIRED_RELATION_WITHOUT_PLACE": "requiredRelationWithoutPlace",
}


# --- the request -------------------------------------------------------------------------------


@dataclass(frozen=True)
class MoveOperation:
    """Move a record, changing its type where the target needs it (``None`` parent: the top)."""

    object_id: str
    parent_object_id: str | None
    object_type_key: str | None = None


@dataclass(frozen=True)
class ChangeTypeOperation:
    """Change a record's type under the same parent."""

    object_id: str
    object_type_key: str


@dataclass(frozen=True)
class InsertLevelOperation:
    """Create a record of ``object_type_key`` under a parent (``None``: the top) and move the chosen
    children of that parent under it. Its inputs are given under :data:`NEW_OBJECT_ID`."""

    parent_object_id: str | None
    child_object_ids: tuple[str, ...]
    object_type_key: str
    name: str


@dataclass(frozen=True)
class RemoveLevelOperation:
    """Delete a record and move its children to its parent, changing type where needed."""

    object_id: str


@dataclass(frozen=True)
class ChangeTypeUnderOperation:
    """Change every record of ``from_object_type_key`` under a record, at any depth, each under
    its own parent."""

    object_id: str
    from_object_type_key: str
    object_type_key: str


Operation = (
    MoveOperation
    | ChangeTypeOperation
    | InsertLevelOperation
    | RemoveLevelOperation
    | ChangeTypeUnderOperation
)

# The ID a plan gives the record ``insertLevel`` creates; applying assigns its real one.
NEW_OBJECT_ID = "new"


def _operation_payload(operation: Operation) -> dict[str, Any]:
    if isinstance(operation, MoveOperation):
        return {
            "kind": "move",
            "objectId": operation.object_id,
            "parentObjectId": operation.parent_object_id,
            "objectTypeKey": operation.object_type_key,
        }
    if isinstance(operation, ChangeTypeOperation):
        return {
            "kind": "changeType",
            "objectId": operation.object_id,
            "objectTypeKey": operation.object_type_key,
        }
    if isinstance(operation, InsertLevelOperation):
        return {
            "kind": "insertLevel",
            "parentObjectId": operation.parent_object_id,
            "childObjectIds": sorted(set(operation.child_object_ids)),
            "objectTypeKey": operation.object_type_key,
            "name": operation.name,
        }
    if isinstance(operation, RemoveLevelOperation):
        return {"kind": "removeLevel", "objectId": operation.object_id}
    return {
        "kind": "changeTypeUnder",
        "objectId": operation.object_id,
        "fromObjectTypeKey": operation.from_object_type_key,
        "objectTypeKey": operation.object_type_key,
    }


@dataclass(frozen=True)
class TypeChoice:
    """The type a record of ``object_type_key`` becomes under a parent of the new type
    ``parent_object_type_key`` (``None``: the top level), where the plan asks."""

    object_type_key: str
    parent_object_type_key: str | None
    new_object_type_key: str


@dataclass(frozen=True)
class MappingChoice:
    """Per type pair, the source of attributes of the new type (``None``: no source), and whether
    values and relationships offered back are taken."""

    from_object_type_key: str
    to_object_type_key: str
    attributes: Mapping[str, str | None] = field(default_factory=dict)
    restore: bool = True


@dataclass(frozen=True)
class RecordInputs:
    """Values and relationships given for one record, as object creation takes them."""

    object_id: str
    attributes: Mapping[str, Any] = field(default_factory=dict)
    relations: Sequence[RelationInput] = ()


@dataclass(frozen=True)
class Restructuring:
    operation: Operation
    type_choices: Sequence[TypeChoice] = ()
    mapping_choices: Sequence[MappingChoice] = ()
    inputs: Sequence[RecordInputs] = ()

    def normalized(self) -> dict[str, Any]:
        """The request as the digest covers it: order-independent where order means nothing."""
        return to_jsonable(
            {
                "operation": _operation_payload(self.operation),
                "types": sorted(
                    [item.object_type_key, item.parent_object_type_key or "", item.new_object_type_key]
                    for item in self.type_choices
                ),
                "mappings": sorted(
                    (
                        {
                            "fromObjectTypeKey": item.from_object_type_key,
                            "toObjectTypeKey": item.to_object_type_key,
                            "attributes": dict(sorted(item.attributes.items())),
                            "restore": item.restore,
                        }
                        for item in self.mapping_choices
                    ),
                    key=lambda item: (item["fromObjectTypeKey"], item["toObjectTypeKey"]),
                ),
                "inputs": sorted(
                    (
                        {
                            "objectId": item.object_id,
                            "attributes": dict(sorted(item.attributes.items())),
                            "relations": sorted(
                                (
                                    [
                                        relation.relation_type_key,
                                        relation.direction,
                                        relation.object_id,
                                        dict(sorted(relation.attributes.items())),
                                    ]
                                    for relation in item.relations
                                ),
                                key=lambda relation: json.dumps(relation, sort_keys=True, default=str),
                            ),
                        }
                        for item in self.inputs
                    ),
                    key=lambda item: item["objectId"],
                ),
            }
        )


# --- the plan ----------------------------------------------------------------------------------


@dataclass(frozen=True)
class Refusal:
    code: str
    message: str
    object_id: str | None = None
    details: Mapping[str, Any] | None = None

    def payload(self) -> dict[str, Any]:
        result: dict[str, Any] = {"code": self.code, "message": self.message}
        if self.object_id is not None:
            result["objectId"] = self.object_id
        if self.details:
            result["details"] = dict(self.details)
            if "conflictingObjectId" in self.details:
                result["conflictingObjectId"] = self.details["conflictingObjectId"]
        return result


@dataclass(frozen=True)
class AttributeSource:
    """Where one attribute of the new type takes its value from, for a whole type pair."""

    attribute_type_key: str
    source: str | None
    rule: MappingRule
    alternatives: tuple[str, ...]


@dataclass
class TypeQuestion:
    object_type_key: str
    parent_object_type_key: str | None
    options: tuple[str, ...]
    chosen: str | None
    record_count: int = 0

    def payload(self) -> dict[str, Any]:
        return {
            "objectTypeKey": self.object_type_key,
            "parentObjectTypeKey": self.parent_object_type_key,
            "options": list(self.options),
            "chosen": self.chosen,
            "recordCount": self.record_count,
        }


def _relationship_payload(state: RelationshipState) -> dict[str, Any]:
    return {
        "relationId": state.relation_id,
        "relationTypeKey": state.relation_type_key,
        "direction": state.direction,
        "objectId": state.other_object_id,
        "objectTypeKey": state.other_object_type_key,
        "name": state.other_name,
    }


@dataclass
class PlannedRecord:
    """One record the operation changes, as it is before and after.

    A record ``insertLevel`` creates has no before state and the ID :data:`NEW_OBJECT_ID`; a record
    ``removeLevel`` deletes has no after state.
    """

    object_id: str
    name: str
    before_type: str | None
    before_parent: str | None
    after_type: str | None  # ``None`` while its type question is open or it is refused
    after_parent: str | None
    path: list[dict[str, Any]]
    attributes: list[dict[str, Any]] = field(default_factory=list)
    values_without_place: dict[str, Any] = field(default_factory=dict)
    relationships_without_place: list[RelationshipState] = field(default_factory=list)
    restored_relationships: list[RelationshipState] = field(default_factory=list)
    inputs_needed: list[dict[str, Any]] = field(default_factory=list)
    refusals: list[Refusal] = field(default_factory=list)
    deferred_children: list[str] = field(default_factory=list)
    change: TypeChange | None = None
    created: bool = False
    removed: bool = False
    # A created record's inputs and relationships, as object creation takes them.
    creation: RecordInputs | None = None

    @property
    def type_changed(self) -> bool:
        return (
            not self.created
            and not self.removed
            and self.after_type is not None
            and self.after_type != self.before_type
        )

    @property
    def moved(self) -> bool:
        return not self.created and not self.removed and self.after_parent != self.before_parent

    @property
    def restored_count(self) -> int:
        return sum(item["outcome"] == "restored" for item in self.attributes) + len(
            self.restored_relationships
        )

    def outcomes(self) -> list[str]:
        return [
            name
            for name, present in (
                ("typeChanged", self.type_changed),
                ("moved", self.moved),
                ("created", self.created),
                ("removed", self.removed),
            )
            if present
        ]

    def outcome_tags(self) -> list[str]:
        """The ``outcome`` filter values this record matches."""
        tags = [item for item in self.outcomes() if item in {"typeChanged", "moved"}]
        if self.values_without_place or self.relationships_without_place:
            tags.append("withoutPlace")
        if self.restored_count:
            tags.append("restored")
        if self.inputs_needed:
            tags.append("needsInput")
        if self.refusals:
            tags.append("refused")
        return tags

    def payload(self) -> dict[str, Any]:
        return {
            "objectId": self.object_id,
            "name": self.name,
            "path": self.path,
            "before": None
            if self.created
            else {"objectTypeKey": self.before_type, "parentObjectId": self.before_parent},
            "after": None
            if self.removed
            else {"objectTypeKey": self.after_type, "parentObjectId": self.after_parent},
            "outcomes": self.outcomes(),
            "attributes": self.attributes,
            "withoutPlace": {
                "attributes": [
                    {"attributeTypeKey": key, "value": value}
                    for key, value in sorted(self.values_without_place.items())
                ],
                "relationships": [
                    _relationship_payload(state) for state in self.relationships_without_place
                ],
            },
            "restoredRelationships": [
                _relationship_payload(state) for state in self.restored_relationships
            ],
            "inputsNeeded": self.inputs_needed,
            "refusals": [item.payload() for item in self.refusals],
        }


@dataclass
class TypePair:
    """Every record of one (old type, new type) pair, with the pair's mapping and its counts."""

    from_type: str
    to_type: str
    restore: bool
    sources: tuple[AttributeSource, ...]
    records: list[PlannedRecord] = field(default_factory=list)

    def payload(self) -> dict[str, Any]:
        attributes = []
        for source in self.sources:
            counts = dict.fromkeys(("kept", "mapped", "restored", "input", "empty"), 0)
            for record in self.records:
                for item in record.attributes:
                    if item["attributeTypeKey"] == source.attribute_type_key:
                        counts[item["outcome"]] += 1
            attributes.append(
                {
                    "attributeTypeKey": source.attribute_type_key,
                    "from": source.source,
                    "rule": source.rule,
                    "alternatives": list(source.alternatives),
                    "kept": counts["kept"],
                    "mapped": counts["mapped"],
                    "restored": counts["restored"],
                    "inputs": counts["input"],
                    "empty": counts["empty"],
                }
            )
        without_place: dict[str, int] = {}
        for record in self.records:
            for key in record.values_without_place:
                without_place[key] = without_place.get(key, 0) + 1
        relations: dict[tuple[str, str, str], int] = {}
        for record in self.records:
            kept = record.change.kept_relationships if record.change else ()
            for outcome, states in (
                ("kept", kept),
                ("withoutPlace", record.relationships_without_place),
            ):
                for state in states:
                    key = (state.relation_type_key, state.direction, outcome)
                    relations[key] = relations.get(key, 0) + 1
        return {
            "fromObjectTypeKey": self.from_type,
            "toObjectTypeKey": self.to_type,
            "recordCount": len(self.records),
            "restore": self.restore,
            "attributes": attributes,
            "withoutPlace": [
                {"attributeTypeKey": key, "count": count}
                for key, count in sorted(without_place.items())
            ],
            "relations": [
                {"relationTypeKey": key, "direction": direction, "outcome": outcome, "count": count}
                for (key, direction, outcome), count in sorted(relations.items())
            ],
        }


@dataclass
class RestructuringPlan:
    change_set_id: str
    change_set_version: int
    records: list[PlannedRecord]
    type_questions: list[TypeQuestion]
    pairs: list[TypePair]
    refusals: list[Refusal]  # of the operation, besides each record's
    plan_digest: str = ""
    # The ID applying gave the record ``insertLevel`` creates; not part of the plan.
    created_object_id: str | None = None

    def all_refusals(self) -> list[Refusal]:
        return [*self.refusals, *(item for record in self.records for item in record.refusals)]

    @property
    def status(self) -> PlanStatus:
        if self.all_refusals():
            return "refused"
        if any(question.chosen is None for question in self.type_questions) or any(
            record.inputs_needed for record in self.records
        ):
            return "needsInput"
        return "ready"

    def summary(self) -> dict[str, int]:
        return {
            "recordCount": len(self.records),
            "typeChangeCount": sum(record.type_changed for record in self.records),
            "moveCount": sum(record.moved for record in self.records),
            "createdCount": sum(record.created for record in self.records),
            "removedCount": sum(record.removed for record in self.records),
            "valuesWithoutPlaceCount": sum(
                len(record.values_without_place) for record in self.records
            ),
            "relationshipsWithoutPlaceCount": sum(
                len(record.relationships_without_place) for record in self.records
            ),
            "restoredCount": sum(record.restored_count for record in self.records),
            "inputsNeededCount": sum(len(record.inputs_needed) for record in self.records),
            "refusalCount": len(self.all_refusals()),
        }

    def payload(self, records: Iterable[PlannedRecord] | None = None) -> dict[str, Any]:
        """The plan in the API's shape, with ``records`` (all of them by default)."""
        refusals = self.all_refusals()
        return {
            "changeSetId": self.change_set_id,
            "changeSetVersion": self.change_set_version,
            "planDigest": self.plan_digest,
            "status": self.status,
            "summary": self.summary(),
            "typeQuestions": [question.payload() for question in self.type_questions],
            "pairs": [pair.payload() for pair in self.pairs],
            "refusals": [item.payload() for item in refusals[:REFUSALS_SHOWN]],
            "refusalCount": len(refusals),
            "refusalsTruncated": len(refusals) > REFUSALS_SHOWN,
            "records": [
                record.payload() for record in (self.records if records is None else records)
            ],
        }

    def records_with(self, outcomes: Iterable[str]) -> list[PlannedRecord]:
        """The records matching any of ``outcomes``, in plan order (all without a filter)."""
        wanted = set(outcomes)
        if not wanted:
            return list(self.records)
        return [record for record in self.records if wanted & set(record.outcome_tags())]

    def digest(self, request: Restructuring) -> str:
        content = self.payload()
        content.pop("planDigest")
        encoded = json.dumps(
            to_jsonable({"request": request.normalized(), "plan": content}),
            sort_keys=True,
            separators=(",", ":"),
            default=str,
        )
        return hashlib.sha256(encoded.encode()).hexdigest()


@dataclass(frozen=True)
class PlannedTypeChange(TypeChange):
    """The C1 type change a planned record applies, with what the planner saw it keep."""

    kept_relationships: tuple[RelationshipState, ...] = ()


@dataclass(frozen=True)
class RestructuringResult:
    operation_id: str
    change_set_id: str
    change_set_version: int
    summary: dict[str, int]
    created_object_id: str | None = None


# --- entry points ------------------------------------------------------------------------------


def preview_restructuring(
    session: Session,
    change_set_id: str,
    request: Restructuring,
    *,
    expected_change_set_version: int | None = None,
) -> RestructuringPlan:
    """Plan an operation and dry-run it; nothing is kept. A given version that is not the change
    set's is ``409 change_set_version_conflict``."""
    try:
        change_set = load_change_set(session, change_set_id)
        if (
            expected_change_set_version is not None
            and change_set.version != expected_change_set_version
        ):
            raise api_error(409, "CHANGE_SET_VERSION_CONFLICT", "Change set version has changed")
        model = change_set_model(session, change_set)
        return _run(session, change_set, model, request, operation_id=str(uuid4()))
    finally:
        session.rollback()


def page_plan_records(
    plan: RestructuringPlan,
    outcomes: Sequence[str],
    page: PageRequest,
    page_size: int,
) -> Page[PlannedRecord]:
    """A page of the plan's records matching any of ``outcomes``, by position in plan order.

    Cursors bind the change set, its version, the plan digest and the filter, so a later page of a
    changed plan is ``422 invalid_cursor``.
    """
    wanted = sorted(set(outcomes))
    indexed = [
        (index, record)
        for index, record in enumerate(plan.records)
        if not wanted or set(wanted) & set(record.outcome_tags())
    ]
    found = paginate_sequence(
        indexed,
        lambda item: (f"{item[0]:06d}",),
        scope="restructuring-records",
        filters={
            "changeSetId": plan.change_set_id,
            "changeSetVersion": plan.change_set_version,
            "planDigest": plan.plan_digest,
            "outcome": wanted,
        },
        page=page,
        page_size=page_size,
        sort=("planOrder",),
        message="Restructuring plan cursor is invalid",
    )
    return Page(
        items=[record for _index, record in found.items],
        next_cursor=found.next_cursor,
        prev_cursor=found.prev_cursor,
        anchor=found.anchor,
        total_count=found.total_count,
        start_index=found.start_index,
    )


def apply_restructuring(
    session: Session,
    change_set_id: str,
    request: Restructuring,
    *,
    expected_change_set_version: int,
    plan_digest: str,
) -> RestructuringResult:
    """Recompute the plan in the write transaction and keep it only when it is the one previewed.

    A stale version is ``409 change_set_version_conflict``, another plan ``409
    restructuring_plan_changed`` with the current digest and a plan that is not ready ``422
    restructuring_not_ready``; each writes nothing. The change set's version advances once.
    """
    try:
        change_set = load_change_set(session, change_set_id, for_update=True)
        if change_set.version != expected_change_set_version:
            raise api_error(409, "CHANGE_SET_VERSION_CONFLICT", "Change set version has changed")
        model = change_set_model(session, change_set)
        operation_id = str(uuid4())
        plan = _run(session, change_set, model, request, operation_id=operation_id)
        if plan.plan_digest != plan_digest:
            raise api_error(
                409,
                "RESTRUCTURING_PLAN_CHANGED",
                "The plan differs from the one previewed",
                {"planDigest": plan.plan_digest},
            )
        if plan.status != "ready":
            raise api_error(
                422,
                "RESTRUCTURING_NOT_READY",
                f"The plan is {plan.status}, not ready",
                {
                    "status": plan.status,
                    "summary": plan.summary(),
                    "refusals": [item.payload() for item in plan.all_refusals()[:REFUSALS_SHOWN]],
                },
            )
        ChangeSetWrites(session, change_set).claim(expected_change_set_version)
        result = RestructuringResult(
            operation_id=operation_id,
            change_set_id=change_set.id,
            change_set_version=change_set.version,
            summary=plan.summary(),
            created_object_id=plan.created_object_id,
        )
        session.commit()
        return result
    except BaseException:
        session.rollback()
        raise


def _run(
    session: Session,
    change_set: ChangeSet,
    model: EngineModel,
    request: Restructuring,
    *,
    operation_id: str,
) -> RestructuringPlan:
    """Plan, and when the plan is ready, write it into the session; the caller keeps or drops it."""
    version = change_set.version
    plan = _Planner(session, change_set, model, request).plan()
    plan.change_set_version = version
    if plan.status == "ready":
        plan.created_object_id = _execute(session, change_set, model, plan, operation_id=operation_id)
    plan.plan_digest = plan.digest(request)
    return plan


# --- the planner -------------------------------------------------------------------------------


def _chunks(ids: Sequence[str]) -> Iterable[list[str]]:
    for start in range(0, len(ids), _CHUNK):
        yield list(ids[start : start + _CHUNK])


def _path_part(object_id: str, object_type_key: str, name: str) -> dict[str, Any]:
    return {"id": object_id, "name": name, "objectTypeKey": object_type_key}


@dataclass
class _Place:
    """A record the cascade descends from: planned, or passed on the way down (``changeTypeUnder``)."""

    object_id: str
    after_type: str
    path: list[dict[str, Any]]
    record: PlannedRecord | None = None


def _place(record: PlannedRecord) -> _Place:
    assert record.after_type is not None
    return _Place(record.object_id, record.after_type, record.path, record)


class _Planner:
    def __init__(
        self, session: Session, change_set: ChangeSet, model: EngineModel, request: Restructuring
    ) -> None:
        self.session = session
        self.change_set = change_set
        self.model = model
        self.request = request
        self.lookup = ChangeSetLookup.of(session, change_set.id)
        self.refusals: list[Refusal] = []
        self.records: list[PlannedRecord] = []
        self.questions: dict[tuple[str, str | None], TypeQuestion] = {}
        self.pairs: dict[tuple[str, str], TypePair] = {}
        self._possible: dict[str | None, tuple[str, ...]] = {}
        self.type_choices = {
            (item.object_type_key, item.parent_object_type_key): item.new_object_type_key
            for item in request.type_choices
        }
        self.mapping_choices = {
            (item.from_object_type_key, item.to_object_type_key): item
            for item in request.mapping_choices
        }
        self.inputs = {item.object_id: item for item in request.inputs}
        self.application_key = ""
        self.application_types: tuple[str, ...] = ()
        self._row_of: dict[str, Any] = {}

    def plan(self) -> RestructuringPlan:
        self._plan_records()
        typed = [record for record in self.records if record.type_changed]
        self._plan_changes(typed)
        return RestructuringPlan(
            change_set_id=self.change_set.id,
            change_set_version=self.change_set.version,
            records=self.records,
            type_questions=[
                question for question in self.questions.values() if question.record_count
            ],
            pairs=list(self.pairs.values()),
            refusals=self.refusals,
        )

    # -- types and the cascade -------------------------------------------------------------------

    def possible_types(self, parent_type: str | None) -> tuple[str, ...]:
        """The application's types a parent of ``parent_type`` may contain (``None``: the top)."""
        if parent_type not in self._possible:
            self._possible[parent_type] = possible_types(
                self.model, self.application_types, parent_type
            )
        return self._possible[parent_type]

    def _choose(self, object_type: str, parent_type: str | None) -> str | None:
        """The type a record becomes where several are possible: the one chosen, else a question."""
        options = self.possible_types(parent_type)
        key = (object_type, parent_type)
        question = self.questions.get(key)
        if question is None:
            chosen = self.type_choices.get(key)
            if chosen is not None and chosen not in options:
                self.refusals.append(
                    Refusal(
                        "typeNotAllowed",
                        f"'{chosen}' is not a type a '{parent_type or 'top level'}' place can hold",
                        details={
                            "objectTypeKey": object_type,
                            "parentObjectTypeKey": parent_type,
                            "chosen": chosen,
                            "options": list(options),
                        },
                    )
                )
                chosen = None
            question = self.questions[key] = TypeQuestion(object_type, parent_type, options, chosen)
        question.record_count += 1
        return question.chosen

    def _type_at(self, object_type: str, parent_type: str | None) -> str | None:
        """The type a record of ``object_type`` has under a parent of ``parent_type``: its own
        where allowed, else the only one, else the answer to the pair's question; ``None`` while
        the question is open or when no type is possible."""
        options = self.possible_types(parent_type)
        if object_type in options:
            return object_type
        if len(options) == 1:
            return options[0]
        if options:
            return self._choose(object_type, parent_type)
        return None

    def _no_type(self, row: Any, parent_type: str | None) -> Refusal:
        return Refusal(
            "notRoot" if parent_type is None else "noPossibleType",
            f"No type of application '{self.application_key}' can be "
            + ("at the top level" if parent_type is None else f"under a '{parent_type}'")
            + f", where '{row.name}' goes",
            row.object_id,
            {"objectTypeKey": row.object_type_key, "parentObjectTypeKey": parent_type},
        )

    def _require_type(self, key: str) -> ObjectTypeDefinition:
        object_type = self.model.object_type(key)
        if object_type is None:
            raise api_error(
                422,
                "UNKNOWN_OBJECT_TYPE",
                f"Object type '{key}' is not in the pinned model",
                {"objectTypeKey": key},
            )
        return object_type

    def _record(self, object_id: str) -> Any | None:
        """A record the operation names, or ``None`` with the operation refused."""
        row = self.lookup.object(object_id)
        if row is None:
            self._refuse_operation(
                "notInChangeSet", f"Object '{object_id}' is not in the change set", object_id
            )
        return row

    def _use_application(self, application_key: str) -> None:
        self.application_key = application_key
        self.application_types = application_type_keys(self.model, application_key)
        self._possible.clear()

    def _plan_records(self) -> None:
        operation = self.request.operation
        if isinstance(operation, InsertLevelOperation):
            self._plan_insert(operation)
            return
        root = self._record(operation.object_id)
        if root is None:
            return
        self._use_application(root.application_key)
        if isinstance(operation, RemoveLevelOperation):
            self._plan_remove(root)
        elif isinstance(operation, ChangeTypeUnderOperation):
            self._plan_under(root, operation)
        else:
            self._plan_move(root, operation)

    def _plan_move(self, root: Any, operation: MoveOperation | ChangeTypeOperation) -> None:
        if isinstance(operation, MoveOperation):
            parent_id = operation.parent_object_id
        else:
            parent_id = root.parent_object_id
        parent = self._record(parent_id) if parent_id else None
        if parent_id and parent is None:
            return
        ancestors = self._ancestors(parent)
        if parent is not None and parent.application_key != root.application_key:
            self._refuse_operation(
                "application",
                f"'{parent_id}' belongs to another application",
                root.object_id,
                {"parentObjectId": parent_id, "applicationKey": parent.application_key},
            )
            return
        if any(item.object_id == root.object_id for item in ancestors):
            self._refuse_operation(
                "cycle",
                f"'{parent_id}' is '{root.object_id}' or below it",
                root.object_id,
                {"parentObjectId": parent_id},
            )
            return
        parent_type = parent.object_type_key if parent is not None else None
        after_type = self._root_type(root, parent_type)
        if self.refusals:
            return
        if after_type == root.object_type_key and parent_id == root.parent_object_id:
            return  # nothing changes
        record = self._add(root, after_type, parent_id, self._path(ancestors))
        self._cascade([_place(record)] if record.type_changed else [])

    def _root_type(self, root: Any, parent_type: str | None) -> str | None:
        operation = self.request.operation
        possible = self.possible_types(parent_type)
        requested = getattr(operation, "object_type_key", None)
        if requested is not None:
            self._require_type(requested)
            if isinstance(operation, ChangeTypeOperation) and requested == root.object_type_key:
                raise api_error(
                    422,
                    "OBJECT_TYPE_UNCHANGED",
                    f"Object '{root.object_id}' is already a '{requested}' record",
                    {"objectId": root.object_id, "objectTypeKey": requested},
                )
            self._check_new_type(root.object_id, requested, parent_type, possible)
            return requested
        after_type = self._type_at(root.object_type_key, parent_type)
        if after_type is None and not possible:
            self.refusals.append(self._no_type(root, parent_type))
        return after_type

    def _check_new_type(
        self,
        object_id: str,
        requested: str,
        parent_type: str | None,
        possible: tuple[str, ...],
    ) -> None:
        """Refuse the operation when the type asked for cannot be at its place."""
        if requested not in self.application_types:
            self._refuse_operation(
                "application",
                f"'{requested}' is not a type of application '{self.application_key}'",
                object_id,
                {"objectTypeKey": requested},
            )
        elif requested not in possible:
            self._refuse_operation(
                "notRoot" if parent_type is None else "typeNotAllowed",
                f"A '{requested}' record cannot be "
                + ("at the top level" if parent_type is None else f"under a '{parent_type}'"),
                object_id,
                {"objectTypeKey": requested, "parentObjectTypeKey": parent_type},
            )

    def _plan_insert(self, operation: InsertLevelOperation) -> None:
        parent_id = operation.parent_object_id
        parent = self._record(parent_id) if parent_id else None
        ids = list(dict.fromkeys(operation.child_object_ids))
        found = self.lookup.objects(ids)
        children = []
        for child_id in ids:
            child = found.get(child_id)
            if child is None:
                self._refuse_operation(
                    "notInChangeSet", f"Object '{child_id}' is not in the change set", child_id
                )
            elif child.parent_object_id != parent_id:
                self._refuse_operation(
                    "notUnderParent",
                    f"'{child.name}' is not directly under "
                    + (f"'{parent_id}'" if parent_id else "the top level"),
                    child_id,
                    {"parentObjectId": child.parent_object_id},
                )
            else:
                children.append(child)
        if self.refusals:
            return
        self._use_application(
            parent.application_key if parent is not None else children[0].application_key
        )
        for child in children:
            if child.application_key != self.application_key:
                self._refuse_operation(
                    "application",
                    f"'{child.name}' belongs to another application",
                    child.object_id,
                    {"applicationKey": child.application_key},
                )
        new_type = self._require_type(operation.object_type_key)
        parent_type = parent.object_type_key if parent is not None else None
        self._check_new_type(
            NEW_OBJECT_ID, new_type.key, parent_type, self.possible_types(parent_type)
        )
        if self.refusals:
            return
        created = PlannedRecord(
            object_id=NEW_OBJECT_ID,
            name=operation.name,
            before_type=None,
            before_parent=None,
            after_type=new_type.key,
            after_parent=parent_id,
            path=[
                *self._path(self._ancestors(parent)),
                _path_part(NEW_OBJECT_ID, new_type.key, operation.name),
            ],
            created=True,
        )
        self._append(created)
        self._created_values(created, new_type, self.inputs.get(NEW_OBJECT_ID))
        self._move_children(children, _place(created))

    def _plan_remove(self, root: Any) -> None:
        parent = self.lookup.object(root.parent_object_id)
        parent_path = self._path(self._ancestors(parent))
        removed = self._add(root, None, None, parent_path)
        removed.removed = True
        self._removed_relationships(removed, root)
        holder = (
            _Place(parent.object_id, parent.object_type_key, parent_path)
            if parent is not None
            else _Place("", "", [])
        )
        self._move_children(
            self.lookup.children([root.object_id]),
            holder,
            parent_type=parent.object_type_key if parent is not None else None,
        )

    def _move_children(
        self, children: list[Any], holder: _Place, *, parent_type: str | None | Keep = KEEP_PARENT
    ) -> None:
        """Place records under ``holder`` (for ``removeLevel`` a parent, or the top level), each
        keeping its type where allowed, then cascade below those whose type changes."""
        parent_id = holder.object_id or None
        container = holder.after_type if isinstance(parent_type, Keep) else parent_type
        frontier = []
        ranks = name_ranks(self.session, (child.name for child in children))
        for child in sorted(children, key=lambda row: (ranks[row.name], row.object_id)):
            new_type = self._type_at(child.object_type_key, container)
            record = self._add(child, new_type, parent_id, holder.path)
            if new_type is None and not self.possible_types(container):
                record.refusals.append(self._no_type(child, container))
            elif record.type_changed:
                frontier.append(_place(record))
        self._cascade(frontier)

    def _plan_under(self, root: Any, operation: ChangeTypeUnderOperation) -> None:
        from_type = self._require_type(operation.from_object_type_key).key
        to_type = self._require_type(operation.object_type_key).key
        if from_type == to_type:
            raise api_error(
                422,
                "OBJECT_TYPE_UNCHANGED",
                f"'{from_type}' records would stay '{to_type}' records",
                {"objectId": root.object_id, "objectTypeKey": to_type},
            )
        if to_type not in self.application_types:
            self._refuse_operation(
                "application",
                f"'{to_type}' is not a type of application '{self.application_key}'",
                root.object_id,
                {"objectTypeKey": to_type},
            )
            return
        start = _Place(root.object_id, root.object_type_key, self._path(self._ancestors(root)))
        self._cascade([start], under=(from_type, to_type))

    def _cascade(self, frontier: list[_Place], under: tuple[str, str] | None = None) -> None:
        """Level by level below ``frontier``: a child its parent's new type cannot contain takes a
        type it can, and nothing below a child that keeps its type changes. With ``under``, every
        record of the first type becomes the second and the walk covers the whole subtree."""
        while frontier:
            by_parent = {item.object_id: item for item in frontier}
            level: list[tuple[Any, _Place, str | None, Refusal | None]] = []
            passed: list[_Place] = []
            for child in self.lookup.children(by_parent):
                holder = by_parent[child.parent_object_id]
                options = self.possible_types(holder.after_type)
                changed = holder.record is not None and holder.record.type_changed
                if under is not None and child.object_type_key == under[0]:
                    refusal = None
                    if under[1] not in options:
                        refusal = Refusal(
                            "typeNotAllowed",
                            f"A '{under[1]}' record cannot be under a '{holder.after_type}'",
                            child.object_id,
                            {"objectTypeKey": under[1], "parentObjectTypeKey": holder.after_type},
                        )
                    level.append((child, holder, None if refusal else under[1], refusal))
                elif changed and child.object_type_key not in options:
                    new_type = self._type_at(child.object_type_key, holder.after_type)
                    refusal = None
                    if not options:
                        refusal = Refusal(
                            "noPossibleType",
                            f"A '{holder.after_type}' record can contain no type of this "
                            f"application, and '{child.name}' is under it",
                            child.object_id,
                            {
                                "objectTypeKey": child.object_type_key,
                                "parentObjectTypeKey": holder.after_type,
                            },
                        )
                    level.append((child, holder, new_type, refusal))
                elif under is not None:
                    passed.append(
                        _Place(
                            child.object_id,
                            child.object_type_key,
                            [
                                *holder.path,
                                _path_part(child.object_id, child.object_type_key, child.name),
                            ],
                        )
                    )
            frontier = passed
            ranks = name_ranks(self.session, (entry[0].name for entry in level))
            for child, holder, new_type, refusal in sorted(
                level, key=lambda entry: (ranks[entry[0].name], entry[0].object_id)
            ):
                planned = self._add(child, new_type, child.parent_object_id, holder.path)
                if holder.record is not None:
                    holder.record.deferred_children.append(child.object_id)
                if refusal is not None:
                    planned.refusals.append(refusal)
                elif planned.after_type is not None:
                    frontier.append(_place(planned))

    def _add(
        self, row: Any, after_type: str | None, after_parent: str | None, parent_path: list
    ) -> PlannedRecord:
        record = PlannedRecord(
            object_id=row.object_id,
            name=row.name,
            before_type=row.object_type_key,
            before_parent=row.parent_object_id,
            after_type=after_type,
            after_parent=after_parent,
            path=[
                *parent_path,
                _path_part(row.object_id, after_type or row.object_type_key, row.name),
            ],
        )
        self._row_of[row.object_id] = row
        return self._append(record)

    def _append(self, record: PlannedRecord) -> PlannedRecord:
        self.records.append(record)
        if len(self.records) > RECORD_LIMIT:
            raise api_error(
                422,
                "RESTRUCTURING_TOO_LARGE",
                f"The operation changes more than {RECORD_LIMIT} records",
                {"limit": RECORD_LIMIT},
            )
        return record

    def _ancestors(self, parent: Any | None) -> list[Any]:
        """``parent`` and its ancestors, nearest first; one read per level, stopping at a cycle."""
        chain, seen = [], set()
        current = parent
        while current is not None and current.object_id not in seen:
            chain.append(current)
            seen.add(current.object_id)
            current = self.lookup.object(current.parent_object_id)
        return chain

    @staticmethod
    def _path(ancestors: list[Any]) -> list[dict[str, Any]]:
        return [
            _path_part(item.object_id, item.object_type_key, item.name)
            for item in reversed(ancestors)
        ]

    def _refuse_operation(
        self,
        code: str,
        message: str,
        object_id: str | None,
        details: Mapping[str, Any] | None = None,
    ) -> None:
        self.refusals.append(Refusal(code, message, object_id, details))

    # -- created and removed records -------------------------------------------------------------

    def _created_values(
        self, record: PlannedRecord, new_type: ObjectTypeDefinition, given: RecordInputs | None
    ) -> None:
        """A created record's values: inputs, else the attribute type's default, else empty; and
        the inputs it still needs, as object creation requires them."""
        inputs = dict(given.attributes) if given else {}
        unknown = sorted(set(inputs) - {item.attributeTypeKey for item in new_type.attributes})
        if unknown:
            raise api_error(
                422,
                "UNKNOWN_ATTRIBUTES",
                f"Inputs for the new record are not bound on '{new_type.key}': {unknown}",
                {"objectTypeKey": new_type.key, "attributeTypeKeys": unknown},
            )
        applied: dict[str, Any] = {}
        result: dict[str, Any] = {}
        for binding in new_type.attributes:
            key = binding.attributeTypeKey
            default = self.model.attribute_type(key).default
            if inputs.get(key) is not None:
                value, valid = self._valid(new_type, key, inputs[key], input_value=True)
                if valid:
                    applied[key] = inputs[key]
                    outcome = "input"
                else:
                    record.inputs_needed.append(_input_needed(key, "invalidValue"))
                    outcome, value = "empty", None
            elif default is not None:
                value, _fits = self._valid(new_type, key, default)
                outcome = "default"
            else:
                outcome, value = "empty", None
            if value is not None:
                result[key] = value
            elif binding.required and not any(
                item["key"] == key for item in record.inputs_needed
            ):
                record.inputs_needed.append(_input_needed(key, "required"))
            record.attributes.append(
                {"attributeTypeKey": key, "from": None, "outcome": outcome, "value": value}
            )
        rule = list(new_type.validation.get("atLeastOneOf", []))
        if rule and not any(result.get(key) not in (None, "") for key in rule):
            record.inputs_needed.extend(_input_needed(key, "atLeastOneOf") for key in rule)
        self._required_relations(record, new_type, [], [], given)
        record.creation = RecordInputs(
            NEW_OBJECT_ID, applied, tuple(given.relations) if given else ()
        )

    def _removed_relationships(self, record: PlannedRecord, row: Any) -> None:
        """The relationships a removed record takes with it; one the other end requires is
        refused, as a type change refuses it."""
        own_parent_keys = self.model.containment_relation_keys(row.object_type_key)
        touching = self.lookup.relations([row.object_id], "both")
        ends = self.lookup.objects(
            end
            for relation in touching
            for end in (relation.from_object_id, relation.to_object_id)
            if end != row.object_id
        )
        for relation in sorted(touching, key=lambda item: item.relation_id):
            outgoing = relation.from_object_id == row.object_id
            if not outgoing and relation.relation_type_key in own_parent_keys:
                continue  # its own containment edge
            other_id = relation.to_object_id if outgoing else relation.from_object_id
            other = ends.get(other_id)
            other_type = other.object_type_key if other is not None else row.object_type_key
            if outgoing and relation.relation_type_key in self.model.containment_relation_keys(other_type):
                continue  # an edge to a child, which moves with the child
            state = RelationshipState(
                relation_id=relation.relation_id,
                relation_type_key=relation.relation_type_key,
                direction="outgoing" if outgoing else "incoming",
                from_object_id=relation.from_object_id,
                to_object_id=relation.to_object_id,
                other_object_id=other_id,
                other_object_type_key=other_type,
                other_name=other.name if other is not None else row.name,
                attributes=dict(relation.attributes or {}),
                version=relation.version,
            )
            binding = self.model.allowed_relation(
                relation.relation_type_key,
                row.object_type_key if outgoing else other_type,
                other_type if outgoing else row.object_type_key,
            )
            if binding is not None and binding.required and outgoing and other_id != row.object_id:
                record.refusals.append(
                    Refusal(
                        "requiredRelationWithoutPlace",
                        f"Removing '{row.name}' removes relationship "
                        f"'{relation.relation_type_key}', which '{other_id}' requires",
                        row.object_id,
                        {
                            "relationId": relation.relation_id,
                            "relationTypeKey": relation.relation_type_key,
                            "conflictingObjectId": other_id,
                        },
                    )
                )
            record.relationships_without_place.append(state)

    # -- values, relationships and offers --------------------------------------------------------

    def _plan_changes(self, typed: list[PlannedRecord]) -> None:
        if not typed:
            return
        ids = [record.object_id for record in typed]
        touching: dict[str, list[Any]] = {object_id: [] for object_id in ids}
        relations = self.lookup.relations(ids, "both")
        for relation in relations:
            for end in (relation.from_object_id, relation.to_object_id):
                if end in touching:
                    touching[end].append(relation)
        events = self._reclassifications(ids)
        offered_ends = {
            state["otherObjectId"]
            for items in events.values()
            for event in items
            for state in event.get("before", {}).get("relationships", [])
        }
        ends = self.lookup.objects(
            [
                *(
                    end
                    for relation in relations
                    for end in (relation.from_object_id, relation.to_object_id)
                ),
                *offered_ends,
            ]
        )
        current_type = {record.object_id: record.before_type for record in typed}
        # A removed record's relationships go with it.
        removed = {
            state.relation_id
            for record in self.records
            if record.removed
            for state in record.relationships_without_place
        }
        for record in typed:
            old_type = self.model.object_type(record.before_type)
            new_type = self.model.object_type(record.after_type)
            pair = self._pair(old_type, new_type)
            pair.records.append(record)
            kept = self._relationships(
                record, touching[record.object_id], ends, current_type, removed
            )
            current_type[record.object_id] = new_type.key
            restored_values, restored_relations = (
                self._offers(record, new_type, pair, events.get(record.object_id, []), ends, current_type)
                if pair.restore
                else ({}, [])
            )
            given = self.inputs.get(record.object_id)
            values = self._values(record, old_type, new_type, pair, restored_values, given)
            record.restored_relationships = [state for state, _item in restored_relations]
            self._required_relations(record, new_type, kept, record.restored_relationships, given)
            record.change = PlannedTypeChange(
                object_id=record.object_id,
                object_type_key=new_type.key,
                parent_object_id=record.after_parent if record.moved else KEEP_PARENT,
                mapping={source.attribute_type_key: source.source for source in pair.sources},
                values=values,
                relations=tuple(given.relations) if given else (),
                restored_values={
                    item["attributeTypeKey"]: item["value"]
                    for item in record.attributes
                    if item["outcome"] == "restored"
                },
                restored_relations=tuple(item for _state, item in restored_relations),
                kept_relationships=tuple(kept),
            )

    def _pair(self, old_type: ObjectTypeDefinition, new_type: ObjectTypeDefinition) -> TypePair:
        key = (old_type.key, new_type.key)
        if key not in self.pairs:
            choice = self.mapping_choices.get(key)
            self.pairs[key] = TypePair(
                old_type.key,
                new_type.key,
                choice.restore if choice else True,
                suggest_mapping(self.model, old_type, new_type, choice),
            )
        return self.pairs[key]

    def _relationships(
        self,
        record: PlannedRecord,
        touching: list[Any],
        ends: dict[str, Any],
        current_type: dict[str, str],
        removed: set[str],
    ) -> list[RelationshipState]:
        """The record's relationships kept and without a place, classified as C1 does at the
        record's turn in the plan: ends earlier in the plan already hold their new type."""
        model, object_id = self.model, record.object_id
        old_type, new_type = record.before_type, record.after_type
        own_parent_keys = model.containment_relation_keys(old_type)
        kept = []
        for relation in sorted(touching, key=lambda item: item.relation_id):
            if relation.relation_id in removed:
                continue
            outgoing = relation.from_object_id == object_id
            incoming = relation.to_object_id == object_id
            if incoming and relation.relation_type_key in own_parent_keys:
                continue  # the record's own containment edge
            other_id = relation.to_object_id if outgoing else relation.from_object_id
            other = ends.get(other_id)
            other_type = current_type.get(other_id, other.object_type_key if other else old_type)
            if outgoing and relation.relation_type_key in model.containment_relation_keys(other_type):
                continue  # an edge to a child, re-typed by the parent sync
            state = RelationshipState(
                relation_id=relation.relation_id,
                relation_type_key=relation.relation_type_key,
                direction="outgoing" if outgoing else "incoming",
                from_object_id=relation.from_object_id,
                to_object_id=relation.to_object_id,
                other_object_id=other_id,
                other_object_type_key=other_type,
                other_name=other.name if other else record.name,
                attributes=dict(relation.attributes or {}),
                version=relation.version,
            )
            if model.allowed_relation(
                relation.relation_type_key,
                new_type if outgoing else other_type,
                new_type if incoming else other_type,
            ):
                kept.append(state)
                continue
            before = model.allowed_relation(
                relation.relation_type_key,
                old_type if outgoing else other_type,
                old_type if incoming else other_type,
            )
            if before is not None and before.required and outgoing and not incoming:
                record.refusals.append(
                    Refusal(
                        "requiredRelationWithoutPlace",
                        f"A '{new_type}' record cannot hold relationship "
                        f"'{relation.relation_type_key}', which '{other_id}' requires",
                        object_id,
                        {
                            "relationId": relation.relation_id,
                            "relationTypeKey": relation.relation_type_key,
                            "conflictingObjectId": other_id,
                        },
                    )
                )
            record.relationships_without_place.append(state)
            removed.add(relation.relation_id)
        return kept

    def _reclassifications(self, object_ids: list[str]) -> dict[str, list[dict[str, Any]]]:
        """Per record, the payloads of its effective ``reclassified`` events, the latest first:
        those of this change set and of change sets that were published."""
        found: list[tuple[int, str, dict[str, Any]]] = []
        for chunk in _chunks(object_ids):
            found.extend(
                self.session.execute(
                    select(AuditEvent.sequence_id, AuditEvent.aggregate_id, AuditEvent.changes).where(
                        AuditEvent.aggregate_type == "change-set-object",
                        AuditEvent.action == "reclassified",
                        AuditEvent.aggregate_id.in_(chunk),
                    )
                ).all()
            )
        if not found:
            return {}
        others = sorted(
            {changes.get("changeSetId") for _sequence, _id, changes in found}
            - {self.change_set.id, None}
        )
        effective = {self.change_set.id}
        change_set_id = AuditEvent.changes["changeSetId"].as_string()
        for chunk in _chunks(others):
            effective.update(
                self.session.scalars(
                    select(change_set_id).where(
                        AuditEvent.aggregate_type == "publication",
                        AuditEvent.action == "published",
                        change_set_id.in_(chunk),
                    )
                )
            )
        events: dict[str, list[dict[str, Any]]] = {}
        for _sequence, object_id, changes in sorted(found, key=lambda item: -item[0]):
            if changes.get("changeSetId") in effective:
                events.setdefault(object_id, []).append(changes)
        return events

    def _offers(
        self,
        record: PlannedRecord,
        new_type: ObjectTypeDefinition,
        pair: TypePair,
        events: list[dict[str, Any]],
        ends: dict[str, Any],
        current_type: dict[str, str],
    ) -> tuple[dict[str, Any], list[tuple[RelationshipState, RestoredRelation]]]:
        """Values and relationships the record lost before and the new type has a place for.

        A value is offered from the latest event whose before state holds the attribute, when that
        event left it without a place; a value kept then and gone since was cleared on purpose.
        """
        values: dict[str, Any] = {}
        bound = {item.attributeTypeKey for item in new_type.attributes}
        decided: set[str] = set()
        for event in events:
            before = event.get("before", {}).get("attributes", {})
            used = {
                item.get("from")
                for item in event.get("mapping", {}).values()
                if item.get("outcome") in {"kept", "mapped"}
            }
            for key, value in before.items():
                if key not in bound or key in decided or value is None:
                    continue
                decided.add(key)
                if key not in used:
                    values[key] = value
        relations: list[tuple[RelationshipState, RestoredRelation]] = []
        seen: set[str] = set()
        for event in events:
            for state in event.get("before", {}).get("relationships", []):
                relation_id = state["relationId"]
                if relation_id in seen:
                    continue
                seen.add(relation_id)
                other = ends.get(state["otherObjectId"])
                if other is None or self.lookup.relation(relation_id) is not None:
                    continue
                other_type = current_type.get(other.object_id, other.object_type_key)
                outgoing = state["fromObjectId"] == record.object_id
                if not self.model.allowed_relation(
                    state["relationTypeKey"],
                    new_type.key if outgoing else other_type,
                    other_type if outgoing else new_type.key,
                ):
                    continue
                relations.append(
                    (
                        RelationshipState(
                            relation_id=relation_id,
                            relation_type_key=state["relationTypeKey"],
                            direction="outgoing" if outgoing else "incoming",
                            from_object_id=state["fromObjectId"],
                            to_object_id=state["toObjectId"],
                            other_object_id=other.object_id,
                            other_object_type_key=other_type,
                            other_name=other.name,
                            attributes=dict(state.get("attributes") or {}),
                            version=state.get("version", 0),
                        ),
                        RestoredRelation(
                            relation_id,
                            state["relationTypeKey"],
                            state["fromObjectId"],
                            state["toObjectId"],
                            dict(state.get("attributes") or {}),
                        ),
                    )
                )
        return values, relations

    def _values(
        self,
        record: PlannedRecord,
        old_type: ObjectTypeDefinition,
        new_type: ObjectTypeDefinition,
        pair: TypePair,
        offered: dict[str, Any],
        given: RecordInputs | None,
    ) -> dict[str, Any]:
        """Each attribute's outcome for the record, and the inputs it takes; returns the inputs
        that apply."""
        old_values = dict(self._row_of[record.object_id].attributes or {})
        inputs = dict(given.attributes) if given else {}
        applied: dict[str, Any] = {}
        used: set[str] = set()
        result: dict[str, Any] = {}
        for source in pair.sources:
            key = source.attribute_type_key
            binding = next(item for item in new_type.attributes if item.attributeTypeKey == key)
            if key in inputs:
                value, valid = self._valid(new_type, key, inputs[key], input_value=True)
                if valid:
                    applied[key] = inputs[key]
                    outcome, origin = "input", None
                else:
                    record.inputs_needed.append(_input_needed(key, "invalidValue"))
                    outcome, origin, value = "empty", None, None
            elif source.source is not None and old_values.get(source.source) is not None:
                value, valid = self._valid(new_type, key, old_values[source.source])
                used.add(source.source)
                if valid:
                    outcome = "kept" if source.source == key else "mapped"
                    origin = source.source
                else:
                    record.inputs_needed.append(_input_needed(key, "invalidValue"))
                    outcome, origin, value = "empty", None, None
            elif key in offered:
                value, valid = self._valid(new_type, key, offered[key])
                outcome, origin = ("restored", None) if valid else ("empty", None)
                value = value if valid else None
            else:
                outcome, origin, value = "empty", None, None
            if value is not None:
                result[key] = value
            elif binding.required and not any(
                item["key"] == key for item in record.inputs_needed
            ):
                record.inputs_needed.append(_input_needed(key, "required"))
            record.attributes.append(
                {"attributeTypeKey": key, "from": origin, "outcome": outcome, "value": value}
            )
        rule = list(new_type.validation.get("atLeastOneOf", []))
        if rule and not any(result.get(key) not in (None, "") for key in rule):
            record.inputs_needed.extend(_input_needed(key, "atLeastOneOf") for key in rule)
        record.values_without_place = {
            key: value
            for key, value in old_values.items()
            if key not in used and value is not None
        }
        return applied

    def _valid(
        self, new_type: ObjectTypeDefinition, key: str, value: Any, *, input_value: bool = False
    ) -> tuple[Any, bool]:
        """The value in its stored form under the new binding, and whether it passes it."""
        if value is None:
            return None, True
        try:
            normalized = validate_attributes(
                self.model,
                new_type,
                {key: value},
                partial=True,
                apply_defaults=False,
                allow_read_only=not input_value,
            )
        except ApiError:
            return None, False
        return stored_json_value(normalized[key]), True

    def _required_relations(
        self,
        record: PlannedRecord,
        new_type: ObjectTypeDefinition,
        kept: list[RelationshipState],
        restored: list[RelationshipState],
        given: RecordInputs | None,
    ) -> None:
        """The new type's required incoming relationships the record will not have: inputs."""
        parents = self.model.containment_relation_keys(new_type.key)
        required: dict[str, set[str]] = {}
        for item in self.model.objectTypeRelations:
            if (
                item.toObjectTypeKey == new_type.key
                and item.required
                and item.relationTypeKey not in parents
            ):
                required.setdefault(item.relationTypeKey, set()).add(item.fromObjectTypeKey)
        for key, sources in sorted(required.items()):
            held = any(
                state.direction == "incoming"
                and state.relation_type_key == key
                and state.other_object_type_key in sources
                for state in (*kept, *restored)
            ) or any(
                relation.direction == "incoming" and relation.relation_type_key == key
                for relation in (given.relations if given else ())
            )
            if not held:
                record.inputs_needed.append(
                    {"kind": "relation", "key": key, "reason": "requiredRelation"}
                )


def _input_needed(key: str, reason: str) -> dict[str, Any]:
    return {"kind": "attribute", "key": key, "reason": reason}


def suggest_mapping(
    model: EngineModel,
    old_type: ObjectTypeDefinition,
    new_type: ObjectTypeDefinition,
    choice: MappingChoice | None = None,
) -> tuple[AttributeSource, ...]:
    """Each attribute of the new type with its source by the D40 rules, in order: the same
    attribute type; display attribute to display attribute; the one ``unique`` and ``required``
    attribute to the other type's one. A source taken by an earlier rule is not suggested again.
    A choice for the pair overrides any of them; the other compatible sources are alternatives.
    """
    old_keys = [item.attributeTypeKey for item in old_type.attributes]
    new_keys = [item.attributeTypeKey for item in new_type.attributes]

    def value_type(key: str) -> str:
        return model.attribute_type(key).valueType

    def compatible(source: str, target: str) -> bool:
        return attribute_value_types_compatible(value_type(source), value_type(target))

    def unique_required(object_type: ObjectTypeDefinition) -> list[str]:
        return [
            item.attributeTypeKey
            for item in object_type.attributes
            if item.required and model.attribute_type(item.attributeTypeKey).features.get("unique")
        ]

    chosen: dict[str, tuple[str | None, MappingRule]] = {}
    for key in new_keys:
        if key in old_keys:
            chosen[key] = (key, "sameType")
    used = {source for source, _rule in chosen.values()}
    candidates: list[tuple[str | None, str | None, MappingRule]] = [
        (new_type.displayAttributeTypeKey, old_type.displayAttributeTypeKey, "display")
    ]
    new_unique, old_unique = unique_required(new_type), unique_required(old_type)
    if len(new_unique) == len(old_unique) == 1:
        candidates.append((new_unique[0], old_unique[0], "uniqueRequired"))
    for target, source, rule in candidates:
        if (
            target
            and source
            and target not in chosen
            and source not in used
            and source in old_keys
            and compatible(source, target)
        ):
            chosen[target] = (source, rule)
            used.add(source)
    for target, source in (choice.attributes.items() if choice else ()):
        if target not in new_keys:
            raise api_error(
                422,
                "INVALID_TYPE_MAPPING",
                f"Attribute '{target}' is not bound on '{new_type.key}'",
                {"attributeTypeKey": target, "toObjectTypeKey": new_type.key},
            )
        if source is not None and (source not in old_keys or not compatible(source, target)):
            raise api_error(
                422,
                "INVALID_TYPE_MAPPING",
                f"'{source}' cannot be the source of '{target}' from '{old_type.key}'",
                {
                    "attributeTypeKey": target,
                    "from": source,
                    "fromObjectTypeKey": old_type.key,
                    "toObjectTypeKey": new_type.key,
                },
            )
        chosen[target] = (source, "choice")
    result = []
    for key in new_keys:
        source, rule = chosen.get(key, (None, "none"))
        result.append(
            AttributeSource(
                key,
                source,
                rule,
                tuple(item for item in old_keys if item != source and compatible(item, key)),
            )
        )
    return tuple(result)


# --- writing a plan ----------------------------------------------------------------------------


def _execute(
    session: Session,
    change_set: ChangeSet,
    model: EngineModel,
    plan: RestructuringPlan,
    *,
    operation_id: str,
) -> str | None:
    """Write a ready plan into the session in plan order, parents before their children; a removed
    record goes last, once its children have moved. Returns the created record's ID.

    A write the change set services refuse becomes the record's refusal, and writing stops there.
    """
    created_id: str | None = None

    def actual(object_id: str | None) -> str | None:
        return created_id if object_id == NEW_OBJECT_ID else object_id

    ordered = [record for record in plan.records if not record.removed] + [
        record for record in plan.records if record.removed
    ]
    for record in ordered:
        try:
            if record.created:
                created_id = _create_object(session, change_set, model, plan, record, operation_id)
            elif record.removed:
                _remove_object(session, change_set, record, operation_id)
            elif record.change is not None:
                change = record.change
                if not isinstance(change.parent_object_id, Keep):
                    change = replace(change, parent_object_id=actual(change.parent_object_id))
                change_object_type(
                    session,
                    change_set,
                    model,
                    change,
                    operation_id=operation_id,
                    deferred_children=record.deferred_children,
                )
            elif record.moved:
                _move_object(
                    session, change_set, model, record, actual(record.after_parent), operation_id
                )
        except ApiError as error:
            details = error.details if isinstance(error.details, Mapping) else None
            message = error.message
            if created_id is not None:
                # The created record's ID is the dry run's own; the plan names it as applying will.
                message = message.replace(created_id, NEW_OBJECT_ID)
                if details is not None:
                    details = json.loads(json.dumps(details, default=str).replace(created_id, NEW_OBJECT_ID))
            record.refusals.append(
                Refusal(
                    _REFUSAL_CODES.get(error.code, error.code), message, record.object_id, details
                )
            )
            return created_id
    return created_id


def _create_object(
    session: Session,
    change_set: ChangeSet,
    model: EngineModel,
    plan: RestructuringPlan,
    record: PlannedRecord,
    operation_id: str,
) -> str:
    """Create the record ``insertLevel`` inserts, as a change set create does."""
    assert record.after_type is not None and record.creation is not None
    lookup = ChangeSetLookup.of(session, change_set.id)
    parent = lookup.object(record.after_parent)
    application_key = (
        parent.application_key
        if parent is not None
        else lookup.object(
            next(item.object_id for item in plan.records if not item.created)
        ).application_key
    )
    rules.object_identity(model, application_key, record.after_type, CHANGE_SET)
    attributes = stored_attributes(
        model, record.after_type, dict(record.creation.attributes), partial=False
    )
    validate_object_attribute_rules(model.object_type(record.after_type), attributes)
    row = write_new_change_set_object(
        session,
        change_set,
        model,
        lookup,
        object_id=str(uuid4()),
        application_key=application_key,
        object_type_key=record.after_type,
        name=record.name,
        parent_object_id=record.after_parent,
        attributes=attributes,
        initial_relations=[
            (item.relation_type_key, item.direction, item.object_id, dict(item.attributes))
            for item in record.creation.relations
        ],
        audit_changes={"operationId": operation_id},
    )
    session.flush()
    return row.object_id


def _remove_object(
    session: Session, change_set: ChangeSet, record: PlannedRecord, operation_id: str
) -> None:
    """Delete the record ``removeLevel`` removes, with its relationships, as a change set delete
    does; its children have moved by now."""
    lookup = ChangeSetLookup.of(session, change_set.id)
    row = lookup.object(record.object_id)
    if row is None:
        raise api_error(404, "OBJECT_NOT_FOUND", f"Object '{record.object_id}' not found in change set")
    remaining = lookup.children([row.object_id])
    if remaining:
        raise api_error(
            409,
            "OBJECT_HAS_DEPENDANTS",
            f"'{row.name}' still holds records",
            {"objectIds": [item.object_id for item in remaining]},
        )
    incident = lookup.relations([row.object_id], "both")
    objects: dict[str, Any] = {row.object_id: row}
    objects.update(
        lookup.objects(
            end
            for relation in incident
            for end in (relation.from_object_id, relation.to_object_id)
            if end != row.object_id
        )
    )
    tombstone_change_set_records(session, change_set, objects, [row.object_id], incident)
    record_audit_event(
        session,
        aggregate_type="change-set-object",
        aggregate_id=row.object_id,
        action="deleted",
        version=row.version + 1,
        changes={
            "changeSetId": change_set.id,
            "operationId": operation_id,
            "relationIds": sorted(relation.relation_id for relation in incident),
        },
        object_ids=[row.object_id],
        subject=object_subject(row),
    )
    session.flush()


def _move_object(
    session: Session,
    change_set: ChangeSet,
    model: EngineModel,
    record: PlannedRecord,
    parent_object_id: str | None,
    operation_id: str,
) -> None:
    """Move a record that keeps its type, as a change set edit of its parent does."""
    lookup = ChangeSetLookup.of(session, change_set.id)
    row = editable_row(session, change_set, lookup.object(record.object_id))
    row.parent_object_id = parent_object_id
    parent_keys = model.containment_relation_keys(row.object_type_key)
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
    place_record(session, change_set, model, row, lookup)
    record_audit_event(
        session,
        aggregate_type="change-set-object",
        aggregate_id=row.object_id,
        action="updated",
        version=row.version,
        changes={
            "attributes": row.attributes or {},
            "changeSetId": change_set.id,
            "operationId": operation_id,
            "parent": {"before": record.before_parent, "after": parent_object_id},
        },
        object_ids=[row.object_id],
        subject=object_subject(row),
    )
