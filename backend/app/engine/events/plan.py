"""What a feed entry changes for a consumer API definition (Base 0.9 C10, CONSUMER_API C-D82).

An object is ``updated`` when a read of it by ID would answer differently in an output, also for a
change in another record it shows. :class:`EventPlan` reads that from a definition alone, once per
release: for each kind of raw change, which objects it reaches and which of their outputs change.
It knows changes by name, never by value (C-D87): an output changed when one of its sources is among
the names an entry records.

A change reaches:

1. the record itself, when its type is exposed: ``created``, ``deleted``, ``updated`` naming the
   outputs its changed names feed (a move changes ``parent``, ``path`` and ``hierarchy``), or a type
   change, which each event sees as one of the three (C-D83);
2. its children, whose ``parent`` shows its name, code or type;
3. its descendants at any depth, whose ``path`` and ``hierarchy`` show its name, or all of whose
   chains change when it moves;
4. the owners of a projection it is an item of, when a field the projection reads changed;
5. the owners of the projected records below it, when an ``ancestor:`` field reads it, or when it
   moved (their ancestors changed);
6. a relation's owner end, when a relation of a projection's type is created or deleted, or updated
   while a field reads the relationship's own values (``relation:<attribute>``); and for a
   projection over a containment relation, which has no relation entries, the record's parents
   before and after (C-D95).

The plan gives :class:`Own` rows for the first and :class:`Reach` rows for the rest; the deriver
resolves each reach's objects in the database (``deriver.py``).
"""

from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from typing import Any

from ...models.database import AuditEvent
from ...models.schema import ConsumerApiDefinition, ConsumerEvent, EngineModel
from ..model.consumer_contract import (
    OBJECT_ROLES,
    PROJECTION_TYPE_SOURCE,
    split_ancestor_reference,
    split_relation_reference,
)
from ..records.feed import changed_names

# The output every object carries; a type change changes it (C-D83).
OBJECT_TYPE = "objectType"
# What a reach starts from: the record itself, its children, its descendants, or both of the last.
SELF, CHILDREN, DESCENDANTS, SELF_AND_DESCENDANTS = "self", "children", "descendants", "self-descendants"


@dataclass(frozen=True)
class FeedChange:
    """A feed entry as the plan reads it: what changed, by name, never by value."""

    position: int
    kind: str
    action: str
    record_id: str
    object_type_key: str | None = None
    previous_object_type_key: str | None = None
    parent_id: str | None = None
    previous_parent_id: str | None = None
    moved: bool = False
    # The attribute types it changed, and ``name`` when the name changed.
    names: frozenset[str] = frozenset()
    relation_type_key: str | None = None
    from_id: str | None = None
    to_id: str | None = None

    @classmethod
    def of(cls, event: AuditEvent) -> FeedChange | None:
        """The change an audit entry with a feed position records; ``None`` for a publication's
        own entry and a withdrawal, which change no object."""
        if event.aggregate_type not in ("object", "relation") or event.feed_position is None:
            return None
        subject = event.subject or {}
        fields, keys = changed_names(event)
        if event.aggregate_type == "relation":
            return cls(
                position=event.feed_position,
                kind="relation",
                action=event.action,
                record_id=event.aggregate_id,
                relation_type_key=subject.get("relationTypeKey"),
                from_id=subject.get("fromObjectId"),
                to_id=subject.get("toObjectId"),
            )
        changes = event.changes if isinstance(event.changes, dict) else {}
        # Entries written before C-D95 name no parent; a live move's changes still hold both.
        move = changes.get("parentObjectId")
        move = move if isinstance(move, dict) else {}
        names = set(keys) | ({"name"} if "name" in fields else set())
        return cls(
            position=event.feed_position,
            kind="object",
            action=event.action,
            record_id=event.aggregate_id,
            object_type_key=subject.get("objectTypeKey"),
            previous_object_type_key=subject.get("previousObjectTypeKey"),
            parent_id=subject.get("parentObjectId", move.get("to")),
            previous_parent_id=subject.get("previousParentObjectId", move.get("from")),
            moved=event.action in ("updated", "reclassified") and "parentObjectId" in fields,
            names=frozenset(names),
        )


@dataclass(frozen=True)
class Own:
    """An event about the entry's own record: ``change`` is ``created``, ``updated``, ``deleted``
    or ``reclassified`` (from ``previous_type_key``); ``outputs`` its changed outputs."""

    position: int
    object_id: str
    change: str
    type_key: str
    previous_type_key: str | None
    outputs: tuple[str, ...]


@dataclass(frozen=True)
class Reach:
    """Objects a change reaches: those ``base`` names from ``record_id``, through ``relation`` in
    ``direction`` to its owners when given; ``outputs`` changes for each of them."""

    position: int
    record_id: str
    base: str
    relation: str | None
    direction: str | None
    outputs: tuple[str, ...]


@dataclass(frozen=True)
class _Projection:
    output: str
    relation: str
    direction: str
    # Names of the item's own fields the projection reads (attribute keys, ``name``).
    item_names: frozenset[str]
    reads_item_type: bool
    # A field reads the relationship's own values (``relation:<attribute>``).
    reads_relation: bool
    # Per ancestor type, the names of its fields the projection reads.
    ancestors: dict[str, frozenset[str]]
    # Over a containment relation: items join and leave with the record's parent (C-D95).
    containment: bool


class EventPlan:
    """A definition's events and what each kind of raw change reaches, for one release."""

    def __init__(self, model: EngineModel, definition: ConsumerApiDefinition, store_key: str | None = None) -> None:
        self.definition = definition
        # The ``consumer_api`` its events are stored under: the API's key, or for an earlier version the
        # model keeps (0.13 DF3) ``<key>@v<n>``, so each version has the events its own declaration names
        # and its own output names in ``changed``.
        self.store_key = store_key or definition.key
        self.events: tuple[ConsumerEvent, ...] = tuple(definition.events)
        self.types = frozenset(definition.objectTypes)
        self.public_names = {key: item.publicName for key, item in definition.objectTypes.items()}
        shape = definition.object
        self._own: dict[str, set[str]] = {}
        name_sources: tuple[str, ...] = ()
        code_sources: tuple[str, ...] = ()
        for role in OBJECT_ROLES:
            declared = getattr(shape, role)
            if declared is None:
                continue
            self._read(declared.source, declared.output)
            if role == "name":
                name_sources = tuple(declared.source)
            if role == "code":
                code_sources = tuple(declared.source)
        for output, attribute in shape.attributes.items():
            self._read(attribute.source, output)
        # A parent's or ancestor's name is the name role, falling back to the built-in name.
        shown_name = frozenset(name_sources) | {"name"}
        self.moved_outputs = tuple(
            output for output in (shape.parent.output if shape.parent else None, shape.path, shape.hierarchy) if output
        )
        self.parent_output = shape.parent.output if shape.parent else None
        parent_fields = set(shape.parent.fields) if shape.parent else set()
        self.parent_names = frozenset(
            (shown_name if "name" in parent_fields else set())
            | (set(code_sources) if "code" in parent_fields else set())
        ) - {"id"}
        self.parent_type = OBJECT_TYPE in parent_fields
        self.path_outputs = tuple(output for output in (shape.path, shape.hierarchy) if output)
        self.path_names = shown_name if self.path_outputs else frozenset()
        containment = frozenset(
            key for item in model.objectTypes for key in model.containment_relation_keys(item.key)
        )
        self.projections = [
            _projection(name, item.from_.relation, item.from_.direction, item.fields, containment)
            for name, item in definition.projections.items()
        ]
        self._containment_of = model.containment_relation_keys

    def _read(self, sources: Iterable[str], output: str) -> None:
        for source in sources:
            if source != "id":
                self._own.setdefault(source, set()).add(output)

    def own_outputs(self, names: Iterable[str]) -> set[str]:
        """The object's own outputs that read any of ``names``."""
        return {output for name in names for output in self._own.get(name, ())}

    def seeds(self, changes: Iterable[FeedChange]) -> tuple[list[Own], list[Reach]]:
        """The own events and the reaches of a set of changes."""
        owns: list[Own] = []
        reaches: list[Reach] = []
        for change in changes:
            if change.kind == "relation":
                reaches += self._relation(change)
            else:
                own, reached = self._object(change)
                owns += own
                reaches += reached
        return owns, reaches

    def _relation(self, change: FeedChange) -> list[Reach]:
        found = []
        for projection in self.projections:
            if projection.relation != change.relation_type_key:
                continue
            # An update changes only the relationship's values, so it reaches the projections that
            # read them, whichever value changed.
            if change.action not in ("created", "deleted") and not (
                change.action == "updated" and projection.reads_relation
            ):
                continue
            owner = change.from_id if projection.direction == "outgoing" else change.to_id
            if owner is not None:
                found.append(Reach(change.position, owner, SELF, None, None, (projection.output,)))
        return found

    def _object(self, change: FeedChange) -> tuple[list[Own], list[Reach]]:
        record, position = change.record_id, change.position
        type_key = change.object_type_key
        previous = change.previous_object_type_key
        retyped = change.action == "reclassified"
        names = change.names
        owns: list[Own] = []
        reaches: list[Reach] = []

        def reach(base: str, outputs: Sequence[str], projection: _Projection | None = None, at: str | None = None) -> None:
            if outputs:
                reaches.append(
                    Reach(
                        position,
                        at or record,
                        base,
                        projection.relation if projection else None,
                        projection.direction if projection else None,
                        tuple(sorted(outputs)),
                    )
                )

        # 6, containment: the parents whose projection gains or loses the record.
        holders = self._containment_holders(change)
        for projection in self.projections:
            if (
                projection.containment
                and projection.direction == "outgoing"
                and self._contains(projection.relation, type_key, previous)
            ):
                for parent in holders:
                    reach(SELF, (projection.output,), at=parent)

        if change.action in ("created", "deleted"):
            if type_key in self.types:
                owns.append(Own(position, record, change.action, type_key, None, ()))
            return owns, reaches

        # 1, the record itself.
        outputs = self.own_outputs(names)
        if change.moved:
            outputs |= set(self.moved_outputs)
            outputs |= {
                p.output
                for p in self.projections
                if p.containment and p.direction == "incoming" and self._contains(p.relation, type_key, previous)
            }
        if retyped:
            if type_key in self.types or previous in self.types:
                owns.append(Own(position, record, "reclassified", type_key, previous, tuple(sorted(outputs | {OBJECT_TYPE}))))
        elif outputs and type_key in self.types:
            owns.append(Own(position, record, "updated", type_key, None, tuple(sorted(outputs))))

        # 2, children showing it as their parent.
        if self.parent_output and (names & self.parent_names or (retyped and self.parent_type)):
            reach(CHILDREN, (self.parent_output,))
        # 3, descendants showing it in their path, or whose chain it moved.
        if self.path_outputs and (names & self.path_names or change.moved):
            reach(DESCENDANTS, self.path_outputs)
        for projection in self.projections:
            # 4, the owners of the record as an item.
            if names & projection.item_names or (retyped and projection.reads_item_type):
                reach(SELF, (projection.output,), projection)
            # 5, the owners of the items below it.
            for ancestor, read in projection.ancestors.items():
                if ancestor in (type_key, previous) and (names & read or retyped):
                    reach(DESCENDANTS, (projection.output,), projection)
            if change.moved and projection.ancestors:
                reach(SELF_AND_DESCENDANTS, (projection.output,), projection)
        return owns, reaches

    def _containment_holders(self, change: FeedChange) -> list[str]:
        """The parents a containment projection's item set changes for: the parent of a created or
        deleted record, both parents of a moved one, the parent of a retyped one."""
        if change.action in ("created", "deleted") or change.action == "reclassified":
            parents = [change.parent_id]
        elif change.moved:
            parents = [change.previous_parent_id, change.parent_id]
        else:
            parents = []
        if change.moved and change.action == "reclassified":
            parents.append(change.previous_parent_id)
        return [parent for parent in dict.fromkeys(parents) if parent is not None]

    def _contains(self, relation: str, type_key: str | None, previous: str | None) -> bool:
        return any(relation in self._containment_of(key) for key in (type_key, previous) if key)


def _projection(
    output: str, relation: str, direction: str, fields: Any, containment: frozenset[str]
) -> _Projection:
    item_names: set[str] = set()
    ancestors: dict[str, set[str]] = {}
    reads_type = False
    reads_relation = False
    for source in fields.values():
        reference = split_ancestor_reference(source)
        if split_relation_reference(source) is not None:
            reads_relation = True
        elif reference is not None:
            ancestor_type, name = reference
            if name != "id":
                ancestors.setdefault(ancestor_type, set()).add(name)
        elif source == PROJECTION_TYPE_SOURCE:
            reads_type = True
        elif source != "id":
            item_names.add(source)
    return _Projection(
        output=output,
        relation=relation,
        direction=direction,
        item_names=frozenset(item_names),
        reads_item_type=reads_type,
        reads_relation=reads_relation,
        ancestors={key: frozenset(names) for key, names in ancestors.items()},
        containment=relation in containment,
    )
