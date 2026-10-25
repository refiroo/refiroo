"""Relation writes decided over a batch lookup (0.9 B3, D35).

A relation create, attribute change or delete is checked against the rules and laid over the lookup;
nothing is written until the write unit writes what the lookup collected (``bulk.py``). A single
relation write is a batch of one through these steps, and a batch's relation items are decided by
them in order, each seeing the items before it (D23), so both answer with the same codes.

A relation-set claim (``expectedRelationSetVersion`` with ``relationSetDirection``, ADR-022) is
checked against the set's version as the items before it leave it. The write holds the workspace
lock (live) or the change set's row (a change set) from before its first read, so the stored
version cannot move before the items are written.
"""

from typing import Any
from uuid import uuid4

from ...errors import api_error
from ...models.commands import RelationCreate
from ...models.schema import EngineModel
from . import rules
from .audit import AuditEntry
from .batch_lookup import BatchLookup, ChangeSetBatchLookup, Relation, SetKey
from .feed import relation_subject
from .relation_set_versions import SetClaim


def set_key(relation: Any, ends: dict[str, Any], direction: str) -> SetKey:
    """The set of one end of ``relation``: ``outgoing`` anchors at its from end."""
    anchor = relation.from_object_id if direction == "outgoing" else relation.to_object_id
    return (
        relation.relation_type_key,
        ends[relation.from_object_id].object_type_key,
        ends[relation.to_object_id].object_type_key,
        anchor,
        direction,
    )


def check_set_claim(lookup: BatchLookup, key: SetKey, expected: int) -> None:
    """The set must still be at the version the caller read."""
    actual = lookup.set_version(key)
    if actual != expected:
        raise api_error(
            409,
            "RELATION_SET_VERSION_CONFLICT",
            "The relation set has changed since it was read; refresh it before retrying",
            {"anchorObjectId": key[3], "direction": key[4], "relationSetVersion": actual},
        )


def check_relation_version(relation: Any, expected: int) -> None:
    if relation.version != expected:
        raise api_error(
            409,
            "VERSION_CONFLICT",
            "Relation version has changed",
            {"currentVersion": relation.version},
        )


def relation_ends(lookup: BatchLookup, relation: Any) -> dict[str, Any]:
    ends = lookup.objects([relation.from_object_id, relation.to_object_id])
    for end in (relation.from_object_id, relation.to_object_id):
        if end not in ends:
            raise rules.relation_endpoint_missing(end)
    return ends


def _staged(lookup: BatchLookup) -> str | None:
    return lookup.change_set_id if isinstance(lookup, ChangeSetBatchLookup) else None


def audit_relation(
    lookup: BatchLookup, relation: Any, action: str, version: int, changes: dict[str, Any]
) -> None:
    """A relation's audit entry, naming its type and ends; in a change set also the change set."""
    change_set_id = _staged(lookup)
    lookup.audit(
        AuditEntry(
            "relation",
            relation.relation_id,
            action,
            version,
            {**changes, "changeSetId": change_set_id} if change_set_id else changes,
            (relation.from_object_id, relation.to_object_id),
            relation_subject(
                relation.relation_type_key, relation.from_object_id, relation.to_object_id
            ),
        )
    )


def decide_relation_create(
    lookup: BatchLookup,
    model: EngineModel,
    relation_type_key: str,
    source: Any,
    target: Any,
    attributes: dict[str, Any],
    claim: SetClaim | None = None,
    *,
    relation_id: str | None = None,
) -> Relation:
    """A new relation between two records the context holds."""
    stored = rules.relation(lookup, model, relation_type_key, source, target, attributes)
    if any(
        relation.to_object_id == target.object_id
        for relation in lookup.relations([source.object_id], "outgoing", [relation_type_key])
    ):
        raise api_error(409, "DUPLICATE_RELATION", "Relation already exists")
    relation = Relation(
        relation_id or str(uuid4()), relation_type_key, source.object_id, target.object_id, stored
    )
    ends = {source.object_id: source, target.object_id: target}
    if claim is not None:
        check_set_claim(lookup, set_key(relation, ends, claim.direction), claim.expected)
    lookup.add_relation(relation)
    lookup.advance_sets(
        relation_type_key,
        source.object_type_key,
        target.object_type_key,
        source.object_id,
        target.object_id,
    )
    if _staged(lookup):
        changes: dict[str, Any] = {"attributes": stored}
    else:
        changes = {
            **RelationCreate(
                relationTypeKey=relation_type_key,
                fromObjectId=source.object_id,
                toObjectId=target.object_id,
                attributes=attributes,
                expectedRelationSetVersion=claim.expected if claim else None,
                relationSetDirection=claim.direction if claim else None,
            ).model_dump(),
            "attributes": stored,
        }
    audit_relation(lookup, relation, "created", 1, changes)
    return relation


def decide_relation_update(
    lookup: BatchLookup,
    model: EngineModel,
    relation: Any,
    expected_version: int,
    attributes: dict[str, Any],
    *,
    audit_changes: dict[str, Any] | None = None,
) -> Relation:
    """A relation's attributes replaced under its version; its ends and type are its identity. A
    stale version is answered first, so the caller refreshes before correcting anything else."""
    check_relation_version(relation, expected_version)
    ends = relation_ends(lookup, relation)
    source, target = ends[relation.from_object_id], ends[relation.to_object_id]
    rules.mutable_relation(
        model, relation.relation_type_key, target.object_type_key, lookup.refusals
    )
    binding = rules.relation_binding(
        model,
        relation.relation_type_key,
        source.object_type_key,
        target.object_type_key,
        lookup.refusals,
    )
    stored = rules.relation_attributes(model, binding, attributes)
    changed = Relation(
        relation.relation_id,
        relation.relation_type_key,
        relation.from_object_id,
        relation.to_object_id,
        stored,
        relation.version + 1,
    )
    lookup.change_relation(changed)
    lookup.advance_sets(
        relation.relation_type_key,
        source.object_type_key,
        target.object_type_key,
        relation.from_object_id,
        relation.to_object_id,
    )
    audit_relation(
        lookup, changed, "updated", changed.version, {"attributes": stored, **(audit_changes or {})}
    )
    return changed


def decide_relation_delete(
    lookup: BatchLookup,
    model: EngineModel,
    relation: Any,
    expected_version: int,
    claim: SetClaim | None = None,
) -> None:
    """A relation removed under its version, unless it is the engine's or required."""
    ends = relation_ends(lookup, relation)
    source, target = ends[relation.from_object_id], ends[relation.to_object_id]
    rules.mutable_relation(
        model, relation.relation_type_key, target.object_type_key, lookup.refusals, deleting=True
    )
    binding = model.allowed_relation(
        relation.relation_type_key, source.object_type_key, target.object_type_key
    )
    if binding is not None:
        rules.deletable_relation(binding, lookup.refusals)
    check_relation_version(relation, expected_version)
    if claim is not None:
        check_set_claim(lookup, set_key(relation, ends, claim.direction), claim.expected)
    lookup.remove_relation(relation)
    lookup.advance_sets(
        relation.relation_type_key,
        source.object_type_key,
        target.object_type_key,
        relation.from_object_id,
        relation.to_object_id,
    )
    audit_relation(
        lookup,
        relation,
        "deleted",
        relation.version + 1,
        {
            "relationTypeKey": relation.relation_type_key,
            "fromObjectId": relation.from_object_id,
            "toObjectId": relation.to_object_id,
        },
    )
