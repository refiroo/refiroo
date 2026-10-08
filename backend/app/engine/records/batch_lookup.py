"""The batch lookup (0.9.0-alpha.1 PG3b, PG-D13): what a chunk's writes read, preloaded per chunk,
with the items accepted earlier in the chunk laid over it.

A chunk's items are decided in memory, in order, through the write rules (``rules.py``) and written
together at the end (PG-D12). The rules read through this lookup as they read through
``LiveLookup`` or ``ChangeSetLookup``, and it answers from, in turn:

1. the item being decided (``deciding``), so its own rows count for its later checks;
2. the items accepted before it in the chunk, so each item sees what they left (D23);
3. its base lookup: rows the chunk's items name, read once per kind (``prefetch``) and kept. A
   question the prefetch did not cover reads the base and keeps the answer, so a rare path costs a
   read, never a wrong answer.

An item refused by a rule is discarded with everything it laid over. The lookup never writes: what
the accepted items change is collected (``changes``) for the write unit to write in bulk
(``bulk.py``). A single write is a batch of one through the same lookup.
"""

import json
from collections import Counter
from collections.abc import Iterable, Iterator, Sequence
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from ...models.database import AttributeValue, ChangeSetObject, RdmObject, RelationSetVersion
from .audit import AuditEntry
from .context import Ancestors, ChangeSetLookup, LiveLookup
from .refusals import Refusals
from .values import row_value, stored_json_value


@dataclass
class Record:
    """A record as the items decided so far leave it; ``attributes`` holds its values in their
    JSON form."""

    object_id: str
    application_key: str
    object_type_key: str
    parent_object_id: str | None
    name: str
    version: int
    attributes: dict[str, Any]
    workspace_key: str | None = None

    @property
    def id(self) -> str:
        return self.object_id


@dataclass(frozen=True)
class Relation:
    """A relation an item adds, or one whose attributes it changed (``version`` then counts the
    change)."""

    relation_id: str
    relation_type_key: str
    from_object_id: str
    to_object_id: str
    attributes: dict[str, Any]
    version: int = 1

    @property
    def id(self) -> str:
        return self.relation_id


# A relation set one end of a written relation advances: relation type, the two ends' types, the
# anchoring record and the direction (ADR-022).
SetKey = tuple[str, str, str, str, str]


@dataclass
class Changes:
    """What decided items change: the rows to write, in the order they were decided."""

    records: dict[str, Record] = field(default_factory=dict)
    created: set[str] = field(default_factory=set)
    # Per record, how often each attribute value was saved (a live value row's version).
    saved: dict[str, Counter[str]] = field(default_factory=dict)
    added: dict[str, Relation] = field(default_factory=dict)
    # Existing relations whose attributes an item replaced, as they then stand (0.9 B3).
    changed: dict[str, Relation] = field(default_factory=dict)
    removed: dict[str, Any] = field(default_factory=dict)
    sets: Counter[SetKey] = field(default_factory=Counter)
    audit: list[AuditEntry] = field(default_factory=list)
    # Indexes over the rows above, for the lookups.
    ends: dict[str, set[str]] = field(default_factory=dict)
    holding: dict[tuple[str, Any], set[str]] = field(default_factory=dict)
    children: dict[str, set[str]] = field(default_factory=dict)

    def __bool__(self) -> bool:
        return bool(self.records or self.added or self.changed or self.removed or self.audit)

    def absorb(self, item: Changes) -> None:
        """Take over what an accepted item changed."""
        self.records.update(item.records)
        self.created |= item.created
        for object_id, saved in item.saved.items():
            self.saved.setdefault(object_id, Counter()).update(saved)
        for relation_id, relation in item.removed.items():
            self.changed.pop(relation_id, None)
            if self.added.pop(relation_id, None) is None:
                self.removed[relation_id] = relation
        for relation_id, relation in item.changed.items():
            if relation_id in self.added:
                self.added[relation_id] = relation
            else:
                self.changed[relation_id] = relation
        self.added.update(item.added)
        self.sets.update(item.sets)
        self.audit.extend(item.audit)
        for index, other in (
            (self.ends, item.ends),
            (self.holding, item.holding),
            (self.children, item.children),
        ):
            for key, ids in other.items():
                index.setdefault(key, set()).update(ids)


def canonical(value: Any) -> Any:
    """A value in one hashable form, whether normalized, read from a typed column or stored as
    JSON."""
    value = stored_json_value(value)
    if isinstance(value, dict | list):
        return json.dumps(value, sort_keys=True)
    return value


_MISSING = object()


class BatchLookup(Ancestors):
    """The lookup a chunk's items are decided through; see the module docstring."""

    base: Any
    session: Session
    refusals: Refusals

    def __init__(self, base: Any) -> None:
        self.base = base
        self.session = base.session
        self.refusals = base.refusals
        self.chunk = Changes()
        self._item: Changes | None = None
        self._objects: dict[str, Any] = {}
        self._values: dict[str, dict[str, Any]] = {}
        # (record, direction, relation type or None for all types) -> the base's relations.
        self._relations: dict[tuple[str, str, str | None], list[Any]] = {}
        self._holders: dict[tuple[str, Any], set[str]] = {}
        self._set_versions: dict[SetKey, int] = {}
        self._relation_rows: dict[str, Any] = {}

    # --- deciding ---------------------------------------------------------------------------------

    def other_workspace(self, object_id: str) -> str | None:
        """The workspace whose live record has the ID, when it is another one (0.9 J4a). Record IDs
        are unique across the instance, so a file's IDs from another workspace are taken there and
        name nothing here; a refusal says where they are. Read only when a write is refused."""
        holder = self.session.scalar(
            select(RdmObject.workspace_key).where(RdmObject.id == object_id)
        )
        return holder if holder is not None and holder != self._set_scope()[0] else None

    @contextmanager
    def deciding(self) -> Iterator[None]:
        """Decide one item: what it lays over is kept when the block ends, and discarded when a
        rule refuses it."""
        self._item = Changes()
        try:
            yield
            self.chunk.absorb(self._item)
        finally:
            self._item = None

    def changes(self) -> Changes:
        return self.chunk

    def _layers(self) -> list[Changes]:
        return [self._item, self.chunk] if self._item is not None else [self.chunk]

    def lay(self, record: Record, *, created: bool = False, saved: Iterable[str] = ()) -> None:
        """Lay a record as the item leaves it over what came before."""
        item = self._current()
        item.records[record.object_id] = record
        if created:
            item.created.add(record.object_id)
        saved = list(saved)
        if saved:
            item.saved.setdefault(record.object_id, Counter()).update(saved)
        for key, value in record.attributes.items():
            if value is not None:
                item.holding.setdefault((key, canonical(value)), set()).add(record.object_id)
        if record.parent_object_id:
            item.children.setdefault(record.parent_object_id, set()).add(record.object_id)

    def add_relation(self, relation: Relation) -> None:
        item = self._current()
        item.added[relation.relation_id] = relation
        for end in (relation.from_object_id, relation.to_object_id):
            item.ends.setdefault(end, set()).add(relation.relation_id)

    def remove_relation(self, relation: Any) -> None:
        item = self._current()
        item.changed.pop(relation.relation_id, None)
        if item.added.pop(relation.relation_id, None) is None:
            item.removed[relation.relation_id] = relation

    def change_relation(self, relation: Relation) -> None:
        """Lay a relation as an item's attribute change leaves it (0.9 B3)."""
        item = self._current()
        if relation.relation_id in item.added:
            item.added[relation.relation_id] = relation
        else:
            item.changed[relation.relation_id] = relation

    def advance_sets(
        self, relation_type_key: str, from_type: str, to_type: str, from_id: str, to_id: str
    ) -> None:
        """Both ends' relation sets advance by one for a relation written (ADR-022)."""
        sets = self._current().sets
        sets[(relation_type_key, from_type, to_type, from_id, "outgoing")] += 1
        sets[(relation_type_key, from_type, to_type, to_id, "incoming")] += 1

    def advance_set(self, key: SetKey) -> None:
        """One set advances by one: a set replacement advances each affected set once (0.9 B3)."""
        self._current().sets[key] += 1

    def set_version(self, key: SetKey) -> int:
        """A relation set's version as the items decided so far leave it: the stored version
        (0 when no write touched it) plus their advances. The write holds the workspace lock, or
        the change set's, so the stored version cannot move before the items are written."""
        if key not in self._set_versions:
            self.prefetch_set_versions([key])
        return self._set_versions[key] + sum(layer.sets.get(key, 0) for layer in self._layers())

    def audit(self, entry: AuditEntry) -> None:
        self._current().audit.append(entry)

    def _current(self) -> Changes:
        if self._item is None:
            raise RuntimeError("An item is laid over only while it is decided")
        return self._item

    def has_relation(self, relation_type_key: str, from_id: str, to_id: str) -> bool:
        """Whether the items decided so far added this relation."""
        layers = self._layers()
        return any(
            (relation := layer.added.get(relation_id)) is not None
            and relation.relation_type_key == relation_type_key
            and relation.to_object_id == to_id
            and not any(relation_id in other.removed for other in layers)
            for layer in layers
            for relation_id in layer.ends.get(from_id, ())
        )

    def is_new(self, object_id: str) -> bool:
        return any(object_id in layer.created for layer in self._layers())

    # --- records ----------------------------------------------------------------------------------

    def _record(self, object_id: str) -> Record | None:
        for layer in self._layers():
            record = layer.records.get(object_id)
            if record is not None:
                return record
        return None

    def object(self, object_id: str | None) -> Any | None:
        if not object_id:
            return None
        return self.objects([object_id]).get(object_id)

    def objects(self, object_ids: Iterable[str]) -> dict[str, Any]:
        found: dict[str, Any] = {}
        missing: list[str] = []
        for object_id in dict.fromkeys(object_ids):
            if not object_id:
                continue
            record = self._record(object_id)
            if record is not None:
                found[object_id] = record
                continue
            base = self._objects.get(object_id, _MISSING)
            if base is _MISSING:
                missing.append(object_id)
            elif base is not None:
                found[object_id] = base
        if missing:
            fetched = self.base.objects(missing)
            for object_id in missing:
                self._objects[object_id] = fetched.get(object_id)
                if object_id in fetched:
                    found[object_id] = fetched[object_id]
        return found

    def values(self, item: Any) -> dict[str, Any]:
        record = self._record(item.object_id)
        if record is not None:
            return dict(record.attributes)
        if item.object_id not in self._values:
            self.prefetch_values([item])
        return dict(self._values[item.object_id])

    def children(
        self, parent_ids: Iterable[str], object_type_keys: Iterable[str] | None = None
    ) -> list[Any]:
        """The records directly under any of ``parent_ids`` (of ``object_type_keys``), in ID
        order."""
        parents = set(parent_ids)
        types = set(object_type_keys) if object_type_keys is not None else None
        candidates = {
            row.object_id: row
            for row in self.base.children(
                [parent for parent in parents if not self.is_new(parent)], object_type_keys
            )
        }
        for layer in self._layers():
            for parent in parents:
                for object_id in layer.children.get(parent, ()):
                    candidates.setdefault(object_id, None)
        found = []
        for object_id, row in candidates.items():
            current = self._record(object_id) or row
            if current is None or current.parent_object_id not in parents:
                continue
            if types is not None and current.object_type_key not in types:
                continue
            found.append(current)
        return sorted(found, key=lambda row: row.object_id)

    # --- relations --------------------------------------------------------------------------------

    def relations(
        self,
        object_ids: Iterable[str],
        direction: str = "both",
        relation_type_keys: Sequence[str] | None = None,
    ) -> list[Any]:
        """Relations leaving (``outgoing``), entering (``incoming``) or touching any of
        ``object_ids``, once each, in relation-ID order."""
        ids = list(dict.fromkeys(object_ids))
        types = list(relation_type_keys) if relation_type_keys else None
        directions = ("outgoing", "incoming") if direction == "both" else (direction,)
        layers = self._layers()
        removed = set().union(*(layer.removed for layer in layers))
        found: dict[str, Any] = {}
        for way in directions:
            for relation in self._base_relations(ids, way, types):
                if relation.relation_id not in removed:
                    found[relation.relation_id] = relation
        wanted = set(ids)
        for layer in layers:
            for object_id in ids:
                for relation_id in layer.ends.get(object_id, ()):
                    relation = layer.added.get(relation_id)
                    if relation is None or relation_id in removed:
                        continue
                    if types is not None and relation.relation_type_key not in types:
                        continue
                    if ("outgoing" in directions and relation.from_object_id in wanted) or (
                        "incoming" in directions and relation.to_object_id in wanted
                    ):
                        found[relation_id] = relation
        for relation_id in found:
            changed = self._changed(relation_id)
            if changed is not None:
                found[relation_id] = changed
        return [found[key] for key in sorted(found)]

    def _changed(self, relation_id: str) -> Relation | None:
        for layer in self._layers():
            if relation_id in layer.changed:
                return layer.changed[relation_id]
        return None

    def relation(self, relation_id: str) -> Any | None:
        """One relation as the items decided so far leave it, or ``None``."""
        for layer in self._layers():
            if relation_id in layer.removed:
                return None
            if relation_id in layer.added:
                return layer.added[relation_id]
        changed = self._changed(relation_id)
        if changed is not None:
            return changed
        if relation_id not in self._relation_rows:
            self.prefetch_relation_ids([relation_id])
        return self._relation_rows[relation_id]

    def prefetch_relation_ids(self, relation_ids: Iterable[str]) -> None:
        """The base's relations by ID, and the records at their ends, read once."""
        wanted = [item for item in dict.fromkeys(relation_ids) if item not in self._relation_rows]
        if not wanted:
            return
        found = self.base.relations_by_id(wanted)
        for relation_id in wanted:
            self._relation_rows[relation_id] = found.get(relation_id)
        self.prefetch_objects(
            end for row in found.values() for end in (row.from_object_id, row.to_object_id)
        )

    def _base_relations(
        self, ids: list[str], direction: str, types: list[str] | None
    ) -> list[Any]:
        """The base's relations at ``ids`` in one direction, read once per record and type."""
        keys = types if types is not None else [None]
        missing = [
            object_id
            for object_id in ids
            if not self.is_new(object_id)
            and (object_id, direction, None) not in self._relations
            and any((object_id, direction, key) not in self._relations for key in keys)
        ]
        if missing:
            self.prefetch_relations(missing, direction, types)
        found: list[Any] = []
        for object_id in ids:
            if self.is_new(object_id):
                continue
            everything = self._relations.get((object_id, direction, None))
            for key in keys:
                if everything is not None:
                    found.extend(
                        relation
                        for relation in everything
                        if key is None or relation.relation_type_key == key
                    )
                else:
                    found.extend(self._relations[(object_id, direction, key)])
        return found

    # --- values -----------------------------------------------------------------------------------

    def unique_value_holder(
        self, attribute_type_key: str, value_type: str, value: Any, *, exclude_object_id: str | None
    ) -> str | None:
        """Another record holding ``value``: the base's holders less those an item changed, and
        the records the items gave the value."""
        key = (attribute_type_key, canonical(value))
        if key not in self._holders:
            self.prefetch_holders(attribute_type_key, value_type, [value])
        candidates = set(self._holders[key])
        for layer in self._layers():
            candidates |= layer.holding.get(key, set())
        holders = []
        for object_id in candidates:
            if object_id == exclude_object_id:
                continue
            record = self._record(object_id)
            if record is None or canonical(record.attributes.get(attribute_type_key)) == key[1]:
                holders.append(object_id)
        return min(holders) if holders else None

    # --- prefetching ------------------------------------------------------------------------------

    def prefetch_objects(self, object_ids: Iterable[str]) -> None:
        self.objects(object_ids)

    def prefetch_ancestors(self, object_ids: Iterable[str]) -> None:
        """The records and every record above them, one read per level."""
        frontier = self.objects(object_ids)
        seen = set(frontier)
        while frontier:
            parents = {
                item.parent_object_id
                for item in frontier.values()
                if item.parent_object_id and item.parent_object_id not in seen
            }
            seen |= parents
            frontier = self.objects(parents)

    def prefetch_relations(
        self, object_ids: Iterable[str], direction: str, relation_type_keys: Sequence[str] | None
    ) -> None:
        ids = [object_id for object_id in dict.fromkeys(object_ids) if not self.is_new(object_id)]
        directions = ("outgoing", "incoming") if direction == "both" else (direction,)
        types = list(relation_type_keys) if relation_type_keys else None
        for way in directions:
            todo = [
                object_id
                for object_id in ids
                if (object_id, way, None) not in self._relations
                and (types is None or any((object_id, way, key) not in self._relations for key in types))
            ]
            if not todo:
                continue
            for object_id in todo:
                for key in types or [None]:
                    self._relations[(object_id, way, key)] = []
            for relation in self.base.relations(todo, way, types):
                end = relation.from_object_id if way == "outgoing" else relation.to_object_id
                if end in todo:
                    key = relation.relation_type_key if types is not None else None
                    self._relations[(end, way, key)].append(relation)

    def prefetch_values(self, items: Iterable[Any]) -> None:
        raise NotImplementedError

    def _set_scope(self) -> tuple[str, str | None]:
        """The workspace and change set (``None`` live) the sets are read in."""
        raise NotImplementedError

    def prefetch_set_versions(self, keys: Iterable[SetKey]) -> None:
        """The stored versions of ``keys``, one read per thousand anchors."""
        wanted = [key for key in dict.fromkeys(keys) if key not in self._set_versions]
        if not wanted:
            return
        workspace_key, change_set_id = self._set_scope()
        for key in wanted:
            self._set_versions[key] = 0
        anchors = sorted({key[3] for key in wanted})
        for start in range(0, len(anchors), 1000):
            for row in self.session.execute(
                select(
                    RelationSetVersion.relation_type_key,
                    RelationSetVersion.from_object_type_key,
                    RelationSetVersion.to_object_type_key,
                    RelationSetVersion.anchor_object_id,
                    RelationSetVersion.direction,
                    RelationSetVersion.version,
                ).where(
                    RelationSetVersion.workspace_key == workspace_key,
                    # ``== None`` renders IS NULL for the live sets.
                    RelationSetVersion.change_set_id == change_set_id,
                    RelationSetVersion.anchor_object_id.in_(anchors[start : start + 1000]),
                )
            ):
                key = tuple(row[:5])
                if key in self._set_versions:
                    self._set_versions[key] = row.version  # type: ignore[index]

    def prefetch_holders(
        self, attribute_type_key: str, value_type: str, values: Iterable[Any]
    ) -> set[str]:
        """The base's holders of each of ``values`` (in this context's form) for the attribute;
        returns every holder of them, read now or before."""
        wanted = {}
        keys = set()
        for value in values:
            if value is None:
                continue
            key = (attribute_type_key, canonical(value))
            keys.add(key)
            if key not in self._holders:
                wanted[key[1]] = value
        if wanted:
            for key in wanted:
                self._holders[(attribute_type_key, key)] = set()
            for value, object_id in self.base.value_holders(
                attribute_type_key, value_type, list(wanted.values())
            ):
                holders = self._holders.get((attribute_type_key, canonical(value)))
                if holders is not None:
                    holders.add(object_id)
        return set().union(*(self._holders[key] for key in keys))


class LiveBatchLookup(BatchLookup):
    """Live records of one workspace (over ``LiveLookup``)."""

    base: LiveLookup

    @classmethod
    def of(cls, session: Session, workspace_key: str) -> LiveBatchLookup:
        return cls(LiveLookup.of(session, workspace_key))

    @property
    def workspace_key(self) -> str:
        return self.base.workspace_key

    def shares_workspace(self, item: Any) -> bool:
        return item.workspace_key == self.base.workspace_key

    def _set_scope(self) -> tuple[str, str | None]:
        return self.base.workspace_key, None

    def id_taken(self, object_id: str) -> bool:
        """Whether a record has the ID in any workspace, or an item gave it one."""
        return self.object(object_id) is not None

    def prefetch_values(self, items: Iterable[Any]) -> None:
        ids = [
            item.object_id
            for item in items
            if item is not None and item.object_id not in self._values and not self.is_new(item.object_id)
        ]
        for object_id in ids:
            self._values[object_id] = {}
        for start in range(0, len(ids), 500):
            for row in self.session.scalars(
                select(AttributeValue).where(AttributeValue.object_id.in_(ids[start : start + 500]))
            ):
                self._values[row.object_id][row.attribute_type_key] = row_value(row)


class ChangeSetBatchLookup(BatchLookup):
    """The effective records of one change set (over ``ChangeSetLookup``)."""

    base: ChangeSetLookup

    @classmethod
    def of(cls, session: Session, change_set_id: str) -> ChangeSetBatchLookup:
        return cls(ChangeSetLookup.of(session, change_set_id))

    def __init__(self, base: ChangeSetLookup) -> None:
        super().__init__(base)
        self._taken: dict[str, bool] = {}

    @property
    def change_set_id(self) -> str:
        return self.base.context.id

    def shares_workspace(self, _item: Any) -> bool:
        return True

    def _set_scope(self) -> tuple[str, str | None]:
        return self.base.context.workspace_key, self.change_set_id

    def tombstone(self, object_id: str) -> ChangeSetObject | None:
        """The change set's deleted row for a record, if it deleted one."""
        return self.session.scalar(
            select(ChangeSetObject).where(
                ChangeSetObject.change_set_id == self.change_set_id,
                ChangeSetObject.object_id == object_id,
                ChangeSetObject.is_deleted.is_(True),
            )
        )

    def id_taken(self, object_id: str) -> bool:
        """Whether the ID is the change set's (effective, or a row it deleted), live data's, or
        an item's."""
        if self.object(object_id) is not None:
            return True
        if object_id not in self._taken:
            self.prefetch_taken([object_id])
        return self._taken[object_id]

    def prefetch_taken(self, object_ids: Iterable[str]) -> None:
        ids = [object_id for object_id in dict.fromkeys(object_ids) if object_id not in self._taken]
        for object_id in ids:
            self._taken[object_id] = False
        for start in range(0, len(ids), 500):
            chunk = ids[start : start + 500]
            for object_id in self.session.scalars(select(RdmObject.id).where(RdmObject.id.in_(chunk))):
                self._taken[object_id] = True
            for object_id in self.session.scalars(
                select(ChangeSetObject.object_id).where(
                    ChangeSetObject.change_set_id == self.change_set_id,
                    ChangeSetObject.object_id.in_(chunk),
                )
            ):
                self._taken[object_id] = True

    def prefetch_values(self, items: Iterable[Any]) -> None:
        for item in items:
            if item is not None and item.object_id not in self._values:
                self._values[item.object_id] = dict(item.attributes or {})
