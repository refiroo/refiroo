"""Bounded lookups for writes: the records a write touches, in live data or in one change set.

A write checks the records it touches: its parent and ancestors, the relations at its ends, the
holders of a unique value and, for a deletion, the subtree it removes. A lookup answers each
question with a statement over the context's rows: live tables, or a change set's effective rows
(``snapshot_reads``, Base 0.8 S2b). So a write costs what it touches rather than the whole graph,
and the write rules (``rules.py``) are one implementation over either context.

Statements run through the session, which flushes pending rows first: a lookup sees the write's own
changes.

Both lookups return rows that read alike: records carry ``object_id``, ``application_key``,
``object_type_key``, ``parent_object_id``, ``name`` and ``version``; relations carry
``relation_id``, ``relation_type_key``, ``from_object_id``, ``to_object_id``, ``attributes`` and
``version``. A record's attribute values are read with ``values``.
"""

from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from typing import Any

from sqlalchemy import Row, or_, select
from sqlalchemy.orm import Session

from ...errors import api_error
from ...models.database import AttributeValue, ObjectRelation, RdmObject, SnapshotAttributeValue
from ..reads.snapshot_reads import (
    SnapshotContext,
    change_set_context,
    find_objects,
    find_relation,
    object_projection,
    relation_projection,
)
from .refusals import CHANGE_SET, LIVE, Refusals
from .rules import object_type_changed
from .values import VALUE_COLUMNS, row_value, stored_json_value, typed_value_columns


def load_object(session: Session, object_id: str, object_type_key: str | None = None) -> RdmObject:
    """A live record by ID; ``404 object_not_found``, or ``409 object_type_changed`` when the route
    names another type than the record's."""
    item = session.scalar(select(RdmObject).where(RdmObject.id == object_id))
    if not item:
        raise api_error(404, "object_not_found", f"Object '{object_id}' not found")
    if object_type_key and item.object_type_key != object_type_key:
        raise object_type_changed(object_id, item.object_type_key, object_type_key)
    return item


def load_active_projection(
    session: Session, object_id: str, object_type_key: str | None = None
) -> RdmObject:
    """Load a live record from the workspace's active object store.

    The active object store is the authoritative, directly-mutable projection; an object is
    visible here as soon as it is written, with no publication required.
    """
    return load_object(session, object_id, object_type_key)


# Bounds the IDs bound into one statement.
_CHUNK = 500


def _chunks(ids: Sequence[Any]) -> Iterable[list[Any]]:
    for start in range(0, len(ids), _CHUNK):
        yield list(ids[start : start + _CHUNK])


class Ancestors:
    """The ancestor walk both lookups share; it reads records through ``objects``."""

    def objects(self, object_ids: Iterable[str]) -> dict[str, Any]:
        raise NotImplementedError

    def ancestor_of_type(self, item: Any, object_type_key: str) -> str | None:
        """The ID of ``item`` or its nearest ancestor of ``object_type_key``: one read per level."""
        return self.ancestors_of_type([item], object_type_key).get(item.object_id)

    def ancestors_of_type(
        self, items: Iterable[Any], object_type_key: str
    ) -> dict[str, str | None]:
        """Per record, itself or its nearest ancestor of ``object_type_key``, resolved level by
        level for the whole batch."""
        result: dict[str, str | None] = {}
        seen: dict[str, set[str]] = {}
        frontier: dict[str, Any] = {}
        for item in items:
            if item is None:
                continue
            result[item.object_id] = None
            seen[item.object_id] = set()
            frontier[item.object_id] = item
        while frontier:
            parents: dict[str, str] = {}
            for origin, current in frontier.items():
                if current.object_id in seen[origin]:
                    continue
                seen[origin].add(current.object_id)
                if current.object_type_key == object_type_key:
                    result[origin] = current.object_id
                elif current.parent_object_id:
                    parents[origin] = current.parent_object_id
            found = self.objects(parents.values())
            frontier = {
                origin: found[parent_id]
                for origin, parent_id in parents.items()
                if parent_id in found
            }
        return result


@dataclass(frozen=True)
class LiveLookup(Ancestors):
    """Live records and relations; unique values are held within one workspace."""

    session: Session
    workspace_key: str
    refusals: Refusals = LIVE

    @classmethod
    def of(cls, session: Session, workspace_key: str) -> LiveLookup:
        return cls(session, workspace_key)

    def object(self, object_id: str | None) -> RdmObject | None:
        if not object_id:
            return None
        return self.objects([object_id]).get(object_id)

    def objects(self, object_ids: Iterable[str]) -> dict[str, RdmObject]:
        ids = [item for item in dict.fromkeys(object_ids) if item]
        found: dict[str, RdmObject] = {}
        for chunk in _chunks(ids):
            found.update(
                (row.id, row)
                for row in self.session.scalars(select(RdmObject).where(RdmObject.id.in_(chunk)))
            )
        return found

    def relations(
        self,
        object_ids: Iterable[str],
        direction: str = "both",
        relation_type_keys: Sequence[str] | None = None,
    ) -> list[ObjectRelation]:
        """Relations leaving (``outgoing``), entering (``incoming``) or touching any of
        ``object_ids``, once each, in relation-ID order."""
        ids = list(dict.fromkeys(object_ids))
        rows: dict[str, ObjectRelation] = {}
        for chunk in _chunks(ids):
            ends = []
            if direction in {"outgoing", "both"}:
                ends.append(ObjectRelation.from_object_id.in_(chunk))
            if direction in {"incoming", "both"}:
                ends.append(ObjectRelation.to_object_id.in_(chunk))
            statement = select(ObjectRelation).where(or_(*ends))
            if relation_type_keys:
                statement = statement.where(ObjectRelation.relation_type_key.in_(relation_type_keys))
            rows.update((row.id, row) for row in self.session.scalars(statement))
        return [rows[key] for key in sorted(rows)]

    def relation(self, relation_id: str) -> ObjectRelation | None:
        return self.relations_by_id([relation_id]).get(relation_id)

    def relations_by_id(self, relation_ids: Iterable[str]) -> dict[str, ObjectRelation]:
        """Relations of the workspace by ID: both their ends are the workspace's records."""
        found: dict[str, ObjectRelation] = {}
        for chunk in _chunks(list(dict.fromkeys(relation_ids))):
            found.update(
                (row.id, row)
                for row in self.session.scalars(
                    select(ObjectRelation).where(ObjectRelation.id.in_(chunk))
                )
            )
        ends = self.objects(
            end for row in found.values() for end in (row.from_object_id, row.to_object_id)
        )
        return {
            relation_id: row
            for relation_id, row in found.items()
            if all(
                end in ends and self.shares_workspace(ends[end])
                for end in (row.from_object_id, row.to_object_id)
            )
        }

    def values(self, item: Any) -> dict[str, Any]:
        """The record's attribute values in their JSON form."""
        return {
            row.attribute_type_key: row_value(row)
            for row in self.session.scalars(
                select(AttributeValue).where(AttributeValue.object_id == item.object_id)
            )
        }

    def children(
        self, parent_ids: Iterable[str], object_type_keys: Iterable[str] | None = None
    ) -> list[RdmObject]:
        """The records directly under any of ``parent_ids`` (of ``object_type_keys``), in ID
        order."""
        types = sorted(object_type_keys) if object_type_keys is not None else None
        rows: list[RdmObject] = []
        for chunk in _chunks(list(dict.fromkeys(parent_ids))):
            statement = select(RdmObject).where(RdmObject.parent_object_id.in_(chunk))
            if types is not None:
                statement = statement.where(RdmObject.object_type_key.in_(types))
            rows.extend(self.session.scalars(statement))
        return sorted(rows, key=lambda row: row.id)

    def shares_workspace(self, item: Any) -> bool:
        return item.workspace_key == self.workspace_key

    def unique_value_holder(
        self, attribute_type_key: str, value_type: str, value: Any, *, exclude_object_id: str | None
    ) -> str | None:
        """Another record of the workspace holding ``value``, compared in its typed column."""
        holders = [
            object_id
            for _value, object_id in self.value_holders(attribute_type_key, value_type, [value])
            if object_id != exclude_object_id
        ]
        return min(holders) if holders else None

    def value_holders(
        self, attribute_type_key: str, value_type: str, values: Iterable[Any]
    ) -> list[tuple[Any, str]]:
        """The records of the workspace holding any of ``values`` (normalized), compared in their
        typed column: each as the value in its JSON form and the record's ID."""
        column = getattr(AttributeValue, VALUE_COLUMNS[value_type])
        found: list[tuple[Any, str]] = []
        for chunk in _chunks(list(values)):
            found.extend(
                (stored_json_value(value), object_id)
                for object_id, value in self.session.execute(
                    select(RdmObject.id, column)
                    .join(AttributeValue, AttributeValue.object_id == RdmObject.id)
                    .where(
                        AttributeValue.attribute_type_key == attribute_type_key,
                        column.in_(chunk),
                        RdmObject.workspace_key == self.workspace_key,
                    )
                )
            )
        return found


@dataclass(frozen=True)
class ChangeSetLookup(Ancestors):
    """The effective records and relations of one change set, read by what a write touches."""

    session: Session
    context: SnapshotContext
    refusals: Refusals = CHANGE_SET

    def values(self, item: Any) -> dict[str, Any]:
        """The record's attribute values in their JSON form."""
        return dict(item.attributes or {})

    def shares_workspace(self, _item: Any) -> bool:
        return True

    @classmethod
    def of(cls, session: Session, change_set_id: str) -> ChangeSetLookup:
        return cls(session, change_set_context(session, change_set_id))

    def object(self, object_id: str | None) -> Row | None:
        if not object_id:
            return None
        return self.objects([object_id]).get(object_id)

    def objects(self, object_ids: Iterable[str]) -> dict[str, Row]:
        ids = [item for item in dict.fromkeys(object_ids) if item]
        found: dict[str, Row] = {}
        for chunk in _chunks(ids):
            found.update(find_objects(self.session, self.context, chunk))
        return found

    def relation(self, relation_id: str) -> Row | None:
        return find_relation(self.session, self.context, relation_id)

    def relations_by_id(self, relation_ids: Iterable[str]) -> dict[str, Row]:
        found: dict[str, Row] = {}
        for chunk in _chunks(list(dict.fromkeys(relation_ids))):
            projection = relation_projection(self.context, relation_ids=chunk)
            found.update((row.relation_id, row) for row in self.session.execute(select(projection)))
        return found

    def children(
        self, parent_ids: Iterable[str], object_type_keys: Iterable[str] | None = None
    ) -> list[Row]:
        """The records directly under any of ``parent_ids`` (of ``object_type_keys``), in ID
        order."""
        rows: list[Row] = []
        for chunk in _chunks(list(dict.fromkeys(parent_ids))):
            projection = object_projection(
                self.context, parent_object_ids=chunk, object_type_keys=object_type_keys
            )
            rows.extend(self.session.execute(select(projection)))
        return sorted(rows, key=lambda row: row.object_id)

    def relations(
        self,
        object_ids: Iterable[str],
        direction: str = "both",
        relation_type_keys: Sequence[str] | None = None,
    ) -> list[Row]:
        """Relations leaving (``outgoing``), entering (``incoming``) or touching any of
        ``object_ids``, once each, in relation-ID order."""
        ids = list(dict.fromkeys(object_ids))
        rows: dict[str, Row] = {}
        # A chunk's "both" arms exclude relations between its own records only; keying by ID
        # removes a relation that joins records of two chunks.
        for chunk in _chunks(ids):
            projection = relation_projection(
                self.context,
                direction=direction,
                relation_type_keys=relation_type_keys,
                endpoint_ids=chunk,
            )
            for row in self.session.execute(select(projection)):
                rows[row.relation_id] = row
        return [rows[key] for key in sorted(rows)]

    def unique_value_holder(
        self, attribute_type_key: str, value_type: str, value: Any, *, exclude_object_id: str
    ) -> str | None:
        """Another effective record holding ``value`` for the attribute, by the typed index."""
        holders = [
            object_id
            for _value, object_id in self.value_holders(attribute_type_key, value_type, [value])
            if object_id != exclude_object_id
        ]
        return min(holders) if holders else None

    def value_holders(
        self, attribute_type_key: str, value_type: str, values: Iterable[Any]
    ) -> list[tuple[Any, str]]:
        """The effective records holding any of ``values`` (in their JSON form) for the attribute:
        each as the value in its JSON form and the record's ID.

        Index rows of the base and of the change set both match; a base row counts only while no
        change set row replaces it, and a change set row only while it is not deleted, which the
        effective lookup of the few matching records decides.
        """
        index = SnapshotAttributeValue
        column_name = VALUE_COLUMNS.get(value_type)
        typed: list[Any] = []
        untyped: list[Any] = []
        for value in values:
            converted = (
                typed_value_columns(value_type, value).get(column_name)
                if column_name not in (None, "json_value")
                else None
            )
            if converted is None:
                untyped.append(value)
            else:
                typed.append(converted)
        candidates: list[tuple[str, str, Any]] = []
        for chunk in _chunks(typed):
            column = getattr(index, column_name)
            candidates.extend(
                (owner_id, object_id, stored_json_value(stored))
                for owner_id, object_id, stored in self.session.execute(
                    select(index.owner_id, index.object_id, column).where(
                        index.owner_id.in_(self._owners()),
                        index.attribute_type_key == attribute_type_key,
                        column.in_(chunk),
                    )
                )
            )
        if untyped:
            # JSON has no portable equality in SQL: read the key's rows and compare decoded values.
            candidates.extend(
                (owner_id, object_id, stored)
                for owner_id, object_id, stored in self.session.execute(
                    select(index.owner_id, index.object_id, index.json_value).where(
                        index.owner_id.in_(self._owners()),
                        index.attribute_type_key == attribute_type_key,
                    )
                )
                if stored in untyped
            )
        effective = self.objects(object_id for _owner, object_id, _value in candidates)
        return sorted(
            (
                (value, object_id)
                for owner_id, object_id, value in candidates
                if object_id in effective and effective[object_id].values_owner_id == owner_id
            ),
            key=lambda found: found[1],
        )

    def _owners(self) -> list[str]:
        owners = [self.context.id]
        if self.context.base is not None:
            owners.append(self.context.base.owner_id)
        return owners
