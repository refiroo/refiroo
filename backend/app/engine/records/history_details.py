"""What a record's history says about each change beyond its names (0.12 RH1, D389–D392).

An entry's kind (`values`, `relationships`, `structure`), the values it changed, each with the value
before, and, on a relationship's entry, the record at its other end. D389 revises D16 for history:
a record's history answers values; the change feed and consumer events still name changes only.

The new value is what the entry stored. The value before is what the record's previous entry in the
same context stored for that field (D390): live entries for a live entry, live entries and the same
change set's for a change set's. Where that previous entry stored names only (a publish, a type
change), the value before is not known and is said so, never guessed; where no earlier entry named
the field, it had no value. One query a page finds them, in PostgreSQL.
"""

from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy import ColumnElement, and_, bindparam, cast, false, not_, or_, select, text
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import Session
from sqlalchemy.types import BigInteger, String

from ...models.database import AuditEvent, RdmObject

HISTORY_KINDS = ("values", "relationships", "structure")
_RECORD_AGGREGATES = ("object", "change-set-object")
_RELATION_AGGREGATES = ("relation", "mapping")
_STRUCTURE_ACTIONS = ("reclassified", "moved")


@dataclass
class HistoryDetails:
    kind: str
    values: list[dict[str, Any]] = field(default_factory=list)
    related: dict[str, Any] | None = None


def kind_condition(kind: str) -> ColumnElement[bool]:
    """The entries of one kind, as the history read filters them (D391)."""
    changes = cast(AuditEvent.changes, JSONB)
    structure = and_(
        AuditEvent.aggregate_type.in_(_RECORD_AGGREGATES),
        or_(
            AuditEvent.action.in_(_STRUCTURE_ACTIONS),
            changes.has_key("parentObjectId"),
            # Containment answers false, never null, where an entry names no fields.
            changes.contains({"changedFields": ["parentObjectId"]}),
        ),
    )
    if kind == "relationships":
        return AuditEvent.aggregate_type.in_(_RELATION_AGGREGATES)
    if kind == "structure":
        return structure
    if kind == "values":
        return and_(AuditEvent.aggregate_type.in_(_RECORD_AGGREGATES), not_(structure))
    return false()


def entry_kind(event: AuditEvent) -> str:
    """An entry's kind, as `kind_condition` selects it."""
    if event.aggregate_type in _RELATION_AGGREGATES:
        return "relationships"
    changes = _changes(event)
    if event.action in _STRUCTURE_ACTIONS or "parentObjectId" in changes:
        return "structure"
    if "parentObjectId" in (changes.get("changedFields") or []):
        return "structure"
    return "values"


# The value each (entry, attribute) pair had before, from the record's latest earlier entry that
# named the attribute: `known` is false where that entry stored names only.
_PREVIOUS = text(
    """
    SELECT wanted.seq, wanted.key, prior.known, prior.value
    FROM unnest(:seqs, :keys) AS wanted(seq, key)
    JOIN audit_events AS entry ON entry.sequence_id = wanted.seq
    JOIN LATERAL (
        SELECT (earlier.changes::jsonb -> 'attributes') ? wanted.key AS known,
               earlier.changes::jsonb -> 'attributes' -> wanted.key AS value
        FROM audit_events AS earlier
        WHERE earlier.aggregate_id = entry.aggregate_id
          AND earlier.sequence_id < entry.sequence_id
          AND (
            earlier.aggregate_type = 'object'
            OR (
              entry.aggregate_type = 'change-set-object'
              AND earlier.aggregate_type = 'change-set-object'
              AND earlier.changes::jsonb ->> 'changeSetId' = entry.changes::jsonb ->> 'changeSetId'
            )
          )
          AND (
            (earlier.changes::jsonb -> 'attributes') ? wanted.key
            OR (earlier.changes::jsonb -> 'attributeTypeKeys') ? wanted.key
          )
        ORDER BY earlier.sequence_id DESC
        LIMIT 1
    ) AS prior ON true
    """
).bindparams(
    bindparam("seqs", type_=ARRAY(BigInteger)),
    bindparam("keys", type_=ARRAY(String)),
)


def history_details(
    session: Session, object_id: str, events: Sequence[AuditEvent]
) -> dict[int, HistoryDetails]:
    """Each entry's kind, values and other end, by sequence ID, for ``object_id``'s history page."""
    wanted = [
        (event.sequence_id, key)
        for event in events
        if event.aggregate_type in _RECORD_AGGREGATES and not _names_only(event)
        for key in (_changes(event).get("attributes") or {})
    ]
    previous: dict[tuple[int, str], tuple[bool, Any]] = {}
    if wanted:
        rows = session.execute(
            _PREVIOUS, {"seqs": [seq for seq, _ in wanted], "keys": [key for _, key in wanted]}
        )
        previous = {(row.seq, row.key): (bool(row.known), row.value) for row in rows}
    records = _records(session, _record_ids(object_id, events))
    return {event.sequence_id: _details(event, object_id, previous, records) for event in events}


def _details(
    event: AuditEvent,
    object_id: str,
    previous: dict[tuple[int, str], tuple[bool, Any]],
    records: dict[str, tuple[str, str]],
) -> HistoryDetails:
    details = HistoryDetails(entry_kind(event))
    changes = _changes(event)
    subject = event.subject or {}
    if event.aggregate_type == "relation":
        outgoing = subject.get("fromObjectId") == object_id
        other = subject.get("toObjectId") if outgoing else subject.get("fromObjectId")
        details.related = {
            "relationTypeKey": subject.get("relationTypeKey"),
            "direction": "outgoing" if outgoing else "incoming",
            **_record(records, other),
        }
        return details
    if event.aggregate_type == "mapping":
        details.related = {
            "relationTypeKey": changes.get("relationTypeKey"),
            "direction": changes.get("direction", "outgoing"),
        }
        details.values.append(
            {
                "field": str(changes.get("relationTypeKey")),
                "kind": "relation",
                "from": _target_names(records, changes.get("previousTargets")),
                "to": _target_names(records, changes.get("newTargets")),
                "fromKnown": True,
            }
        )
        return details
    if event.aggregate_type not in _RECORD_AGGREGATES or _names_only(event):
        return details
    name = changes.get("name")
    if isinstance(name, dict):
        details.values.append(_change("name", "name", name.get("from"), name.get("to")))
    parent = changes.get("parentObjectId")
    if isinstance(parent, dict):
        before, after = (_record(records, parent.get(end)) for end in ("from", "to"))
        details.values.append(_change("parent", "parent", before.get("name"), after.get("name")))
    for key, value in (changes.get("attributes") or {}).items():
        known, before = previous.get((event.sequence_id, key), (True, None))
        if known and before == value:
            continue
        details.values.append(_change(key, "attribute", before if known else None, value, known))
    return details


def _change(name: str, kind: str, before: Any, after: Any, known: bool = True) -> dict[str, Any]:
    return {"field": name, "kind": kind, "from": before, "to": after, "fromKnown": known}


def _changes(event: AuditEvent) -> dict[str, Any]:
    return event.changes if isinstance(event.changes, dict) else {}


def _names_only(event: AuditEvent) -> bool:
    """A publish's entry and a type change name what changed and keep no values (D15, ADR-034)."""
    return "changedFields" in _changes(event)


def _record_ids(object_id: str, events: Sequence[AuditEvent]) -> set[str]:
    ids: set[str] = set()
    for event in events:
        changes, subject = _changes(event), event.subject or {}
        if event.aggregate_type == "relation":
            ids.update(str(subject.get(end)) for end in ("fromObjectId", "toObjectId"))
        elif event.aggregate_type == "mapping":
            for side in ("previousTargets", "newTargets"):
                ids.update(
                    str(target.get("objectId"))
                    for target in changes.get(side) or []
                    if isinstance(target, dict)
                )
        elif isinstance(changes.get("parentObjectId"), dict):
            ids.update(str(value) for value in changes["parentObjectId"].values() if value)
    ids.discard(object_id)
    return ids


def _records(session: Session, ids: set[str]) -> dict[str, tuple[str, str]]:
    if not ids:
        return {}
    rows = session.execute(
        select(RdmObject.id, RdmObject.name, RdmObject.object_type_key).where(RdmObject.id.in_(ids))
    )
    return {row.id: (row.name, row.object_type_key) for row in rows}


def _record(records: dict[str, tuple[str, str]], object_id: Any) -> dict[str, Any]:
    """A record named by its current name; one no longer in live data by its ID alone."""
    if not object_id:
        return {}
    found = records.get(str(object_id))
    if found is None:
        return {"objectId": str(object_id)}
    return {"objectId": str(object_id), "name": found[0], "objectTypeKey": found[1]}


def _target_names(records: dict[str, tuple[str, str]], targets: Any) -> list[str]:
    names = []
    for target in targets or []:
        if isinstance(target, dict):
            found = _record(records, target.get("objectId"))
            names.append(found.get("name") or found.get("objectId") or "")
    return names
