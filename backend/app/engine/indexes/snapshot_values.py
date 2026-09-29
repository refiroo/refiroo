"""Typed value index for change set, change-set base and publication object rows (D1, Base 0.8 S2).

Change set and history rows hold attribute values as JSON. ``snapshot_attribute_values`` mirrors them as
typed rows, like live ``attribute_values``, so change set and history reads filter and sort in SQL with
the same query builder as live reads.

The index is derived data. A ``before_flush`` hook rewrites an object row's typed values whenever
the ORM inserts, changes or deletes that row, so no write path can persist JSON without its index.
Bulk writes that bypass the ORM (migrations, test fixtures, whole-base deletion) call the helpers
here themselves.
"""

from collections.abc import Iterable, Mapping
from typing import Any

from sqlalchemy import Connection, delete, event, insert, select
from sqlalchemy.orm import Session

from ...models.database import (
    AttributeTypeMeta,
    ChangeSet,
    ChangeSetBase,
    ChangeSetBaseObject,
    ChangeSetObject,
    Publication,
    PublicationObject,
    SnapshotAttributeValue,
)
from ..records.values import typed_value_columns

# Object row class -> (owner kind, owner column on the row, owner table carrying the release).
_OWNERS: dict[type, tuple[str, str, Any]] = {
    PublicationObject: ("publication", "publication_id", Publication),
    ChangeSetBaseObject: ("base", "base_id", ChangeSetBase),
    ChangeSetObject: ("change_set", "change_set_id", ChangeSet),
}
_TABLE = SnapshotAttributeValue.__table__


def value_rows(
    owner_kind: str,
    owner_id: str,
    object_id: str,
    attributes: Mapping[str, Any] | None,
    value_types: Mapping[str, str],
) -> list[dict[str, Any]]:
    """The typed index rows for one object row's JSON attributes."""
    return [
        {
            "owner_kind": owner_kind,
            "owner_id": owner_id,
            "object_id": object_id,
            "attribute_type_key": key,
            **typed_value_columns(value_types.get(key), value),
        }
        for key, value in (attributes or {}).items()
    ]


def release_value_types(connection: Connection, model_release_id: int) -> dict[str, str]:
    """Declared value type per attribute key of one installed model release."""
    return {
        key: value_type
        for key, value_type in connection.execute(
            select(AttributeTypeMeta.key, AttributeTypeMeta.value_type).where(
                AttributeTypeMeta.model_release_id == model_release_id
            )
        )
    }


def delete_owner_values(session: Session, owner_id: str) -> None:
    """Remove the whole index of one publication, change set base or change set (bulk deletion paths)."""
    session.execute(delete(SnapshotAttributeValue).where(SnapshotAttributeValue.owner_id == owner_id))


@event.listens_for(Session, "before_flush")
def _index_changed_object_rows(session: Session, _context: Any, _instances: Any) -> None:
    changed = [
        item
        for item in (*session.new, *session.dirty)
        if type(item) in _OWNERS and (item in session.new or session.is_modified(item))
    ]
    removed = [item for item in session.deleted if type(item) in _OWNERS]
    if not changed and not removed:
        return
    # Core statements on the flush connection: they join the flush transaction without
    # re-entering the ORM flush that is already in progress.
    connection = session.connection()
    releases: dict[tuple[str, str], int | None] = {}
    value_types: dict[int, dict[str, str]] = {}
    stale: dict[str, list[str]] = {}
    rows: list[dict[str, Any]] = []
    for item in (*changed, *removed):
        kind, owner_column, _owner = _OWNERS[type(item)]
        owner_id = getattr(item, owner_column)
        stale.setdefault(owner_id, []).append(item.object_id)
        if item in removed or getattr(item, "is_deleted", False):
            continue
        release_id = _owner_release(connection, releases, type(item), owner_id)
        if release_id is not None and release_id not in value_types:
            value_types[release_id] = release_value_types(connection, release_id)
        rows.extend(
            value_rows(
                kind,
                owner_id,
                item.object_id,
                item.attributes,
                value_types.get(release_id, {}) if release_id is not None else {},
            )
        )
    for owner_id, object_ids in stale.items():
        for start in range(0, len(object_ids), 500):
            connection.execute(
                delete(_TABLE).where(
                    _TABLE.c.owner_id == owner_id,
                    _TABLE.c.object_id.in_(object_ids[start : start + 500]),
                )
            )
    insert_value_rows(connection, rows)


def _owner_release(
    connection: Connection,
    cache: dict[tuple[str, str], int | None],
    row_type: type,
    owner_id: str,
) -> int | None:
    kind, _column, owner = _OWNERS[row_type]
    if (kind, owner_id) not in cache:
        cache[(kind, owner_id)] = connection.scalar(
            select(owner.model_release_id).where(owner.id == owner_id)
        )
    return cache[(kind, owner_id)]


def insert_value_rows(connection: Connection, rows: Iterable[dict[str, Any]]) -> None:
    """Insert precomputed index rows in bounded batches."""
    batch: list[dict[str, Any]] = []
    for row in rows:
        batch.append(row)
        if len(batch) == 5000:
            connection.execute(insert(_TABLE), batch)
            batch = []
    if batch:
        connection.execute(insert(_TABLE), batch)
