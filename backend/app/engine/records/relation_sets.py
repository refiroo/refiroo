"""Relation-set replacement (ADR-022; 0.9 B3, INTEGRATION_API B4): one record's directional set
of one binding becomes a given list of records, decided over a batch lookup.

The mapping PUT (one target or none, ``mapping_replacement.py``) and a batch's
``replaceRelationSet`` item (any number of targets) are this one step. A target the record already
relates to keeps its relation and, unless new attributes are given, its values; the others are
removed and the new ones added, each through the single relation write's rules over what the
earlier ones left, so cardinality at both ends and ancestor scope answer with their usual codes.

The record's set advances once and every other record whose set changed advances once, and one
``transition`` entry summarises the change beside the relations' own entries.
"""

from dataclasses import dataclass
from typing import Any
from uuid import uuid4

from ...errors import ApiError, api_error
from ...models.schema import EngineModel, ObjectTypeRelationDefinition
from . import rules
from .audit import AuditEntry
from .batch_lookup import BatchLookup, ChangeSetBatchLookup, Relation, SetKey
from .relation_writes import audit_relation


@dataclass(frozen=True)
class SetBinding:
    """The set: a binding read from one end, ``outgoing`` from its from type."""

    relation_type_key: str
    from_object_type_key: str
    to_object_type_key: str
    direction: str

    @property
    def other_type(self) -> str:
        return (
            self.to_object_type_key if self.direction == "outgoing" else self.from_object_type_key
        )

    def key(self, anchor_id: str) -> SetKey:
        return (
            self.relation_type_key,
            self.from_object_type_key,
            self.to_object_type_key,
            anchor_id,
            self.direction,
        )

    def opposite(self, other_id: str) -> SetKey:
        return (
            self.relation_type_key,
            self.from_object_type_key,
            self.to_object_type_key,
            other_id,
            "incoming" if self.direction == "outgoing" else "outgoing",
        )


@dataclass(frozen=True)
class SetTarget:
    """A record the set is to hold; ``attributes`` ``None`` keeps a kept relation's values."""

    record: Any
    attributes: dict[str, Any] | None = None


@dataclass(frozen=True)
class SetReplaced:
    """The set's version after the step, what it did to the set's relations, and whether it
    changed anything (``unchanged`` writes nothing)."""

    version: int
    created: list[str]
    kept: list[str]
    removed: list[str]
    changed: bool
    # The relation to each target, by target ID, as the set now holds it.
    relations: dict[str, str]


class SetVersionConflict(ApiError):
    """``409 relation_set_version_conflict``: the set moved since the caller read it."""

    def __init__(self, key: SetKey, version: int, pointer: str | None) -> None:
        details: dict[str, Any] = {
            "anchorObjectId": key[3],
            "direction": key[4],
            "relationSetVersion": version,
        }
        if pointer is not None:
            details["pointer"] = pointer
        super().__init__(
            409,
            "relation_set_version_conflict",
            "The relation set has changed since it was read; refresh it before retrying",
            details,
        )
        self.version = version


def set_binding(
    model: EngineModel, set_: SetBinding, refusals: Any
) -> ObjectTypeRelationDefinition:
    """The binding a set replacement may change: not containment, not required ownership."""
    binding = rules.relation_binding(
        model,
        set_.relation_type_key,
        set_.from_object_type_key,
        set_.to_object_type_key,
        refusals,
    )
    rules.mutable_relation(model, set_.relation_type_key, set_.to_object_type_key, refusals)
    if binding.required and binding.cardinality in {"one-to-one", "one-to-many"}:
        raise api_error(
            422,
            "required_ownership_binding",
            "Mapping replacement is not permitted on required-ownership bindings",
        )
    return binding


def set_edges(lookup: BatchLookup, set_: SetBinding, anchor_id: str) -> tuple[list[Any], dict]:
    """The anchor's relations of the set, in relation-ID order, and the records at their other
    ends by ID."""
    relations = lookup.relations([anchor_id], set_.direction, [set_.relation_type_key])
    others = lookup.objects(_other(relation, set_.direction) for relation in relations)
    edges = [
        relation
        for relation in relations
        if (other := others.get(_other(relation, set_.direction))) is not None
        and other.object_type_key == set_.other_type
        and lookup.shares_workspace(other)
    ]
    return edges, others


def decide_set_replacement(
    lookup: BatchLookup,
    model: EngineModel,
    set_: SetBinding,
    anchor: Any,
    targets: list[SetTarget],
    *,
    expected: int | None,
    on_existing: str = "reject",
    pointer: str | None = None,
) -> SetReplaced:
    """Make ``anchor``'s set hold exactly ``targets``.

    An equal set is ``unchanged`` before any claim (as D24): it needs no version, and a stale one
    does not refuse it. Otherwise ``expected`` must be the set's version, or ``on_existing`` be
    ``overwrite`` (INTEGRATION_API P4). ``pointer`` locates refusals in a batch item.
    """
    binding = set_binding(model, set_, lookup.refusals)
    anchor_id = anchor.object_id
    if not targets and binding.required:
        raise _at(
            api_error(422, "required_relation", "A required relationship cannot be cleared"),
            pointer,
            "targets",
        )
    seen: set[str] = set()
    for number, target in enumerate(targets):
        if target.record.object_id in seen:
            raise _at(
                api_error(409, "duplicate_relation", "A record is listed twice in the set"),
                pointer,
                f"targets/{number}",
            )
        seen.add(target.record.object_id)

    edges, _others = set_edges(lookup, set_, anchor_id)
    by_other = {_other(edge, set_.direction): edge for edge in edges}
    kept: dict[str, tuple[Any, dict[str, Any]]] = {}
    added: list[tuple[int, SetTarget]] = []
    for number, target in enumerate(targets):
        other_id = target.record.object_id
        edge = by_other.get(other_id)
        if edge is None:
            added.append((number, target))
            continue
        values = dict(edge.attributes or {})
        if target.attributes is not None:
            values = _target(
                lambda target=target: rules.relation_attributes(model, binding, target.attributes),
                pointer,
                number,
            )
        kept[other_id] = (edge, values)
    obsolete = [edge for other, edge in by_other.items() if other not in kept]
    changed_values = [
        (edge, values) for edge, values in kept.values() if values != dict(edge.attributes or {})
    ]
    key = set_.key(anchor_id)
    current = lookup.set_version(key)
    if not obsolete and not added and not changed_values:
        return SetReplaced(
            current,
            [],
            [edge.relation_id for edge, _values in kept.values()],
            [],
            False,
            {other: edge.relation_id for other, (edge, _values) in kept.items()},
        )
    if expected is None:
        if on_existing != "overwrite":
            raise api_error(
                409,
                "version_required",
                "The set would change; send expectedRelationSetVersion, or declare "
                'onExisting: "overwrite"',
                {
                    **({"pointer": f"{pointer}/expectedRelationSetVersion"} if pointer else {}),
                    "anchorObjectId": anchor_id,
                    "relationSetVersion": current,
                },
            )
    elif expected != current:
        raise SetVersionConflict(
            key, current, f"{pointer}/expectedRelationSetVersion" if pointer else None
        )

    if binding.required and set_.direction == "outgoing":
        _keep_required(lookup, set_, obsolete, pointer)
    affected: set[str] = set()
    for edge in obsolete:
        lookup.remove_relation(edge)
        affected.add(_other(edge, set_.direction))
        audit_relation(
            lookup,
            edge,
            "deleted",
            edge.version + 1,
            {
                "relationTypeKey": edge.relation_type_key,
                "fromObjectId": edge.from_object_id,
                "toObjectId": edge.to_object_id,
            },
        )
    for edge, values in changed_values:
        changed = Relation(
            edge.relation_id,
            edge.relation_type_key,
            edge.from_object_id,
            edge.to_object_id,
            values,
            edge.version + 1,
        )
        lookup.change_relation(changed)
        affected.add(_other(edge, set_.direction))
        audit_relation(lookup, changed, "updated", changed.version, {"attributes": values})
    relations = {other: edge.relation_id for other, (edge, _values) in kept.items()}
    values_of = {other: values for other, (_edge, values) in kept.items()}
    created: list[str] = []
    for number, target in added:
        source, end = (
            (anchor, target.record) if set_.direction == "outgoing" else (target.record, anchor)
        )
        stored = _target(
            lambda source=source, end=end, target=target: rules.relation(
                lookup, model, set_.relation_type_key, source, end, target.attributes or {}
            ),
            pointer,
            number,
        )
        relation = Relation(
            str(uuid4()), set_.relation_type_key, source.object_id, end.object_id, stored
        )
        lookup.add_relation(relation)
        audit_relation(
            lookup,
            relation,
            "created",
            1,
            {
                "relationTypeKey": relation.relation_type_key,
                "fromObjectId": relation.from_object_id,
                "toObjectId": relation.to_object_id,
                "attributes": stored,
            },
        )
        created.append(relation.relation_id)
        relations[target.record.object_id] = relation.relation_id
        values_of[target.record.object_id] = stored
        affected.add(target.record.object_id)

    lookup.advance_set(key)
    for other_id in sorted(affected):
        lookup.advance_set(set_.opposite(other_id))
    version = current + 1
    final = [
        {
            "relationId": relations[target.record.object_id],
            "objectId": target.record.object_id,
            "attributes": values_of[target.record.object_id],
        }
        for target in targets
    ]
    lookup.audit(
        AuditEntry(
            "mapping",
            anchor_id,
            "transition",
            version,
            {
                "relationTypeKey": set_.relation_type_key,
                "fromObjectTypeKey": set_.from_object_type_key,
                "toObjectTypeKey": set_.to_object_type_key,
                "direction": set_.direction,
                "changeSetId": (
                    lookup.change_set_id if isinstance(lookup, ChangeSetBatchLookup) else None
                ),
                "previousTargets": [
                    {
                        "relationId": edge.relation_id,
                        "objectId": _other(edge, set_.direction),
                        "attributes": dict(edge.attributes or {}),
                    }
                    for edge in edges
                ],
                "newTargets": final,
            },
            (anchor_id, *sorted(affected | set(kept))),
            feed=False,
        )
    )
    return SetReplaced(
        version,
        created,
        [edge.relation_id for edge, _values in kept.values()],
        [edge.relation_id for edge in obsolete],
        True,
        relations,
    )


def _keep_required(
    lookup: BatchLookup, set_: SetBinding, obsolete: list[Any], pointer: str | None
) -> None:
    """D36: a removed relation of a required binding must not leave the record at its other end,
    which requires one, with none."""
    removed = {edge.relation_id for edge in obsolete}
    for edge in obsolete:
        other = _other(edge, set_.direction)
        remaining = [
            relation
            for relation in lookup.relations([other], "incoming", [set_.relation_type_key])
            if relation.relation_id not in removed
        ]
        if not remaining:
            error = api_error(
                422,
                "required_relation",
                "The replacement would leave a record without a relationship it requires",
                {"objectId": other, "relationId": edge.relation_id},
            )
            raise _at(error, pointer, "targets")


def _other(relation: Any, direction: str) -> str:
    return relation.to_object_id if direction == "outgoing" else relation.from_object_id


def _at(error: ApiError, pointer: str | None, field: str) -> ApiError:
    """``error`` pointing into the batch item at ``field``, unless it already points."""
    if pointer is None:
        return error
    details = dict(error.details) if isinstance(error.details, dict) else {}
    details.setdefault("pointer", f"{pointer}/{field}")
    return ApiError(error.status, error.code, error.message, details)


def _target(decide: Any, pointer: str | None, number: int) -> Any:
    try:
        return decide()
    except ApiError as error:
        raise _at(error, pointer, f"targets/{number}") from None
