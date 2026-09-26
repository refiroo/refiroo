"""Bounded lookups for draft writes (Base 0.8 S2b).

A draft write checks the records it touches: its parent and ancestors, the relations at its ends,
the draft-wide holders of a unique value and, for a deletion, the subtree it removes. Each check is
a statement over the draft's effective rows (``snapshot_reads``), so a write costs what it touches
rather than the whole membership.

Statements run through the session, which flushes pending rows first: a lookup sees the write's own
changes, as the candidate membership did before.
"""

from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from typing import Any

from sqlalchemy import Row, select
from sqlalchemy.orm import Session

from ..models.database import SnapshotAttributeValue
from .attributes import VALUE_COLUMNS, typed_value_columns
from .snapshot_reads import (
    SnapshotContext,
    draft_context,
    find_objects,
    find_relation,
    object_projection,
    relation_projection,
)

# Bounds the IDs bound into one statement.
_CHUNK = 500


def _chunks(ids: Sequence[str]) -> Iterable[list[str]]:
    for start in range(0, len(ids), _CHUNK):
        yield list(ids[start : start + _CHUNK])


@dataclass(frozen=True)
class DraftLookup:
    """The effective records and relations of one draft, read by what a write touches."""

    session: Session
    context: SnapshotContext

    @classmethod
    def of(cls, session: Session, draft_id: str) -> DraftLookup:
        return cls(session, draft_context(session, draft_id))

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

    def children(self, parent_ids: Iterable[str]) -> list[Row]:
        """The records directly under any of ``parent_ids``, in ID order."""
        rows: list[Row] = []
        for chunk in _chunks(list(dict.fromkeys(parent_ids))):
            projection = object_projection(self.context, parent_object_ids=chunk)
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

    def unique_value_holder(
        self, attribute_type_key: str, value_type: str, value: Any, *, exclude_object_id: str
    ) -> str | None:
        """Another effective record holding ``value`` for the attribute, by the typed index.

        Index rows of the base and of the draft both match; a base row counts only while no draft
        row replaces it, and a draft row only while it is not deleted, which the effective lookup
        of the few matching records decides.
        """
        column_name = VALUE_COLUMNS.get(value_type)
        if column_name is None or column_name == "json_value":
            return self._json_value_holder(attribute_type_key, value, exclude_object_id)
        typed = typed_value_columns(value_type, value).get(column_name)
        if typed is None:
            return self._json_value_holder(attribute_type_key, value, exclude_object_id)
        index = SnapshotAttributeValue
        candidates = self.session.execute(
            select(index.owner_id, index.object_id).where(
                index.owner_id.in_(self._owners()),
                index.attribute_type_key == attribute_type_key,
                getattr(index, column_name) == typed,
                index.object_id != exclude_object_id,
            )
        ).all()
        return self._effective_holder(candidates)

    def _json_value_holder(self, key: str, value: Any, exclude_object_id: str) -> str | None:
        # JSON has no portable equality in SQL: read the key's rows and compare decoded values.
        index = SnapshotAttributeValue
        candidates = [
            (owner_id, object_id)
            for owner_id, object_id, stored in self.session.execute(
                select(index.owner_id, index.object_id, index.json_value).where(
                    index.owner_id.in_(self._owners()),
                    index.attribute_type_key == key,
                    index.object_id != exclude_object_id,
                )
            )
            if stored == value
        ]
        return self._effective_holder(candidates)

    def _owners(self) -> list[str]:
        owners = [self.context.id]
        if self.context.base is not None:
            owners.append(self.context.base.owner_id)
        return owners

    def _effective_holder(self, candidates: Iterable[tuple[str, str]]) -> str | None:
        candidates = list(candidates)
        effective = self.objects(object_id for _owner, object_id in candidates)
        holders = sorted(
            object_id
            for owner_id, object_id in candidates
            if object_id in effective and effective[object_id].values_owner_id == owner_id
        )
        return holders[0] if holders else None
