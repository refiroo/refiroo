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

from sqlalchemy import JSON, Connection, delete, event, func, insert, literal, select, text
from sqlalchemy.orm import Session
from sqlalchemy.util import IdentitySet

from ...models.database import (
    AttributeTypeMeta,
    AttributeValue,
    ChangeSet,
    ChangeSetBase,
    ChangeSetBaseObject,
    ChangeSetBaseRelation,
    ChangeSetObject,
    ObjectRelation,
    Publication,
    PublicationObject,
    PublicationRelation,
    RdmObject,
    SnapshotAttributeValue,
)
from ..records.values import TYPED_VALUE_COLUMNS, typed_value_columns, value_json

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
    session.execute(
        delete(SnapshotAttributeValue).where(SnapshotAttributeValue.owner_id == owner_id)
    )


@event.listens_for(Session, "before_flush")
def _index_changed_object_rows(session: Session, _context: Any, _instances: Any) -> None:
    # ``session.new`` builds a new set on every read: read it once, or a flush of n rows costs n².
    new = session.new
    changed = [
        item
        for item in (*new, *session.dirty)
        if type(item) in _OWNERS and (item in new or session.is_modified(item))
    ]
    removed = IdentitySet(item for item in session.deleted if type(item) in _OWNERS)
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


def copy_live(session: Session, owner_kind: str, owner_id: str, workspace_key: str) -> None:
    """Freeze live records, relationships and typed values with three set statements.

    The caller owns the capture snapshot or publication lock and flushes live changes first.
    Matrix states are copied separately by ``matrix_states`` in the same transaction.
    """
    object_type, relation_type, owner_column = {
        "base": (ChangeSetBaseObject, ChangeSetBaseRelation, "base_id"),
        "publication": (PublicationObject, PublicationRelation, "publication_id"),
    }[owner_kind]
    objects, values, relations = (
        RdmObject.__table__,
        AttributeValue.__table__,
        ObjectRelation.__table__,
    )
    # Each record's values gathered through its own index entries, so ``objects`` is read once.
    # A grouped subquery over the workspace's values, joined back to its records, was recomputed
    # per record when the records were newer than the statistics (0.11 X5: 122 s for 11,000).
    attributes = (
        select(
            func.json_object_agg(
                values.c.attribute_type_key,
                value_json(values),
            ).label("attributes"),
        )
        .where(values.c.object_id == objects.c.id)
        .lateral("attributes")
    )
    fields = ["application_key", "object_type_key", "name", "parent_object_id"]
    session.execute(
        insert(object_type).from_select(
            [owner_column, "object_id", *fields, "attributes", "version"],
            select(
                literal(owner_id),
                objects.c.id,
                *[objects.c[key] for key in fields],
                func.coalesce(attributes.c.attributes, literal({}, type_=JSON)),
                objects.c.version,
            )
            .select_from(objects.outerjoin(attributes, literal(True)))
            .where(objects.c.workspace_key == workspace_key),
        )
    )
    # A relationship is its ``from`` record's workspace's (relationships never cross workspaces,
    # D8), so ``objects`` is read once. Joining the ``to`` end as well let PostgreSQL pair every
    # record with every other when the workspace's records were newer than its statistics, as
    # after a move's load (0.11 X5: a publish of 11,000 moved records ran for 9 minutes).
    source = objects.alias("source")
    fields = ["relation_type_key", "from_object_id", "to_object_id", "attributes", "version"]
    session.execute(
        insert(relation_type).from_select(
            [owner_column, "relation_id", *fields],
            select(literal(owner_id), relations.c.id, *[relations.c[key] for key in fields])
            .select_from(relations.join(source, source.c.id == relations.c.from_object_id))
            .where(source.c.workspace_key == workspace_key),
        )
    )
    fields = ["object_id", "attribute_type_key", "value_type", *TYPED_VALUE_COLUMNS]
    # A decimal is indexed in its JSON form, as the flush hook indexes it (28 significant digits).
    copied = [
        func.rdm_decimal_text(values.c[key]).cast(values.c[key].type).label(key)
        if key == "decimal_value"
        else values.c[key]
        for key in fields
    ]
    session.execute(
        insert(_TABLE).from_select(
            ["owner_kind", "owner_id", *fields],
            select(literal(owner_kind), literal(owner_id), *copied)
            .join(objects, objects.c.id == values.c.object_id)
            .where(objects.c.workspace_key == workspace_key),
        )
    )


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


# The typed columns of one JSON value under its declared type, as ``typed_value_columns`` decides
# them: a value that does not hold its type, or a key the release does not declare, is indexed as
# JSON only. A decimal is indexed canonically; an instant without a zone is UTC.
_TYPED_INDEX = r"""
WITH entry AS (
    SELECT c.object_id, e.key, e.value, t.value_type AS declared,
        CASE WHEN jsonb_typeof(e.value) = 'string' THEN e.value #>> '{}' END AS raw
    FROM change_set_objects c
    CROSS JOIN LATERAL jsonb_each(c.attributes::jsonb) e
    LEFT JOIN model_attribute_types t ON t.model_release_id = :release AND t.key = e.key
    WHERE c.change_set_id = :owner AND NOT c.is_deleted
), typed AS (
    SELECT entry.*, coalesce(CASE
        WHEN declared IS NULL THEN false
        WHEN jsonb_typeof(value) = 'null' OR declared = 'json' THEN true
        WHEN declared IN ('text', 'longText') THEN jsonb_typeof(value) = 'string'
        WHEN declared = 'integer' THEN jsonb_typeof(value) = 'number'
            AND value::text ~ '^-?[0-9]+$' AND value::text::numeric BETWEEN -2147483648 AND 2147483647
        WHEN declared = 'decimal' THEN jsonb_typeof(value) = 'number'
            OR (raw IS NOT NULL AND raw ~ '^\s*[+-]?([0-9]+\.?[0-9]*|\.[0-9]+)([eE][+-]?[0-9]+)?\s*$')
        WHEN declared = 'boolean' THEN jsonb_typeof(value) = 'boolean'
        WHEN declared = 'date' THEN raw ~ '^\d{4}-\d{2}-\d{2}$' AND pg_input_is_valid(raw, 'date')
        WHEN declared = 'dateTime' THEN raw IS NOT NULL AND pg_input_is_valid(raw, 'timestamptz')
        ELSE false
    END, false) AS holds
    FROM entry
)
INSERT INTO snapshot_attribute_values (owner_kind, owner_id, object_id, attribute_type_key,
    value_type, text_value, integer_value, decimal_value, boolean_value, date_value,
    datetime_value, json_value)
SELECT 'change_set', CAST(:owner AS varchar), object_id, key,
    CASE WHEN holds THEN declared ELSE 'json' END,
    CASE WHEN holds AND declared IN ('text', 'longText') THEN raw END,
    CASE WHEN holds AND declared = 'integer' AND jsonb_typeof(value) = 'number'
        THEN value::text::integer END,
    CASE WHEN holds AND declared = 'decimal' AND jsonb_typeof(value) <> 'null'
        THEN rdm_decimal_text(btrim(coalesce(raw, value::text))::numeric)::numeric END,
    CASE WHEN holds AND declared = 'boolean' AND jsonb_typeof(value) = 'boolean'
        THEN value::text::boolean END,
    CASE WHEN holds AND declared = 'date' AND raw IS NOT NULL THEN raw::date END,
    CASE WHEN holds AND declared = 'dateTime' AND raw IS NOT NULL THEN
        CASE WHEN raw ~ '(Z|z|[+-]\d{2}(:?\d{2})?)$' THEN raw::timestamptz
            ELSE raw::timestamp AT TIME ZONE 'UTC' END
    END,
    CASE WHEN (NOT holds OR declared = 'json') AND jsonb_typeof(value) <> 'null'
        THEN value::json END
FROM typed
"""


def reindex_change_set(session: Session, change_set_id: str, model_release_id: int) -> None:
    """Rebuild a change set's whole typed index from its rows' JSON under ``model_release_id``, in
    two set statements, after a bulk write of its rows outside the ORM (0.11 V3)."""
    delete_owner_values(session, change_set_id)
    session.execute(text(_TYPED_INDEX), {"owner": change_set_id, "release": model_release_id})
