"""Typed value rows for revision, draft-base and draft objects (Base 0.8 S2, decision D1).

Draft and history rows keep attribute values as JSON. This revision adds
``snapshot_attribute_values``, a typed index of those values that mirrors live
``attribute_values``, and backfills it from every existing revision, draft-base and draft row using
the value types of the model release each owner is pinned to.

The index is derived from the JSON columns, which this revision does not change. SQLite commits DDL
as it runs, so an interrupted run can leave the table behind without the version bump; a table with
the expected columns is therefore dropped and rebuilt, and any other shape is refused.
"""

import json
from datetime import UTC, date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any

import sqlalchemy as sa
from alembic import op

revision = "20260925_01"
down_revision = "20260912_01"
branch_labels = None
depends_on = None

TABLE = "snapshot_attribute_values"
_VALUE_COLUMNS = {
    "text": "text_value",
    "longText": "text_value",
    "integer": "integer_value",
    "decimal": "decimal_value",
    "boolean": "boolean_value",
    "date": "date_value",
    "dateTime": "datetime_value",
    "json": "json_value",
}
_COLUMNS = {
    "sequence_id",
    "owner_kind",
    "owner_id",
    "object_id",
    "attribute_type_key",
    "value_type",
    *_VALUE_COLUMNS.values(),
}
# (owner kind, object table, owner column, owner table, tombstone column)
_OWNERS = (
    ("revision", "workspace_revision_objects", "revision_id", "workspace_revisions", None),
    ("base", "workspace_draft_base_objects", "base_id", "workspace_draft_bases", None),
    ("draft", "workspace_draft_objects", "draft_id", "workspace_drafts", "is_deleted"),
)
_INDEXES = {
    "ix_snapshot_attribute_values_owner_key": ["owner_id", "attribute_type_key"],
}
# Ordered draft and history pages by type and by parent: (table, index, columns).
_PAGE_INDEXES = tuple(
    (table, f"ix_{table}_{suffix}", [owner, *columns])
    for table, owner in (
        ("workspace_revision_objects", "revision_id"),
        ("workspace_draft_base_objects", "base_id"),
    )
    for suffix, columns in (
        ("type_name", ["object_type_key", "name", "object_id"]),
        ("parent_name", ["parent_object_id", "object_type_key", "name", "object_id"]),
    )
)


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if TABLE in inspector.get_table_names():
        existing = {column["name"] for column in inspector.get_columns(TABLE)}
        if existing != _COLUMNS:
            raise RuntimeError(
                f"{TABLE} has an unexpected schema from an earlier interrupted or manual change; "
                "restore the pre-upgrade backup and rerun the upgrade"
            )
        # A derived index left by an interrupted run: rebuild it completely.
        op.drop_table(TABLE)
    table = op.create_table(
        TABLE,
        sa.Column("sequence_id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("owner_kind", sa.String(length=10), nullable=False),
        sa.Column("owner_id", sa.String(length=36), nullable=False),
        sa.Column("object_id", sa.String(length=36), nullable=False),
        sa.Column("attribute_type_key", sa.String(length=160), nullable=False),
        sa.Column("value_type", sa.String(length=40), nullable=False),
        sa.Column("text_value", sa.Text(), nullable=True),
        sa.Column("integer_value", sa.Integer(), nullable=True),
        sa.Column("decimal_value", sa.Numeric(), nullable=True),
        sa.Column("boolean_value", sa.Boolean(), nullable=True),
        sa.Column("date_value", sa.Date(), nullable=True),
        sa.Column("datetime_value", sa.DateTime(timezone=True), nullable=True),
        sa.Column("json_value", sa.JSON(), nullable=True),
        sa.CheckConstraint(
            "owner_kind IN ('revision', 'base', 'draft')", name="ck_snapshot_attribute_owner_kind"
        ),
        sa.PrimaryKeyConstraint("sequence_id"),
        sa.UniqueConstraint(
            "owner_id", "object_id", "attribute_type_key", name="uq_snapshot_attribute_value"
        ),
    )
    for name, columns in _INDEXES.items():
        op.create_index(name, TABLE, columns)
    for object_table, name, columns in _PAGE_INDEXES:
        # An interrupted run may already have created some of these.
        if name not in {index["name"] for index in inspector.get_indexes(object_table)}:
            op.create_index(name, object_table, columns)
    _backfill(bind, table)


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    for object_table, name, _columns in _PAGE_INDEXES:
        if name in {index["name"] for index in inspector.get_indexes(object_table)}:
            op.drop_index(name, table_name=object_table)
    if TABLE in inspector.get_table_names():
        op.drop_table(TABLE)


def _backfill(bind: sa.Connection, table: sa.Table) -> None:
    value_types = _release_value_types(bind)
    for kind, object_table, owner_column, owner_table, tombstone in _OWNERS:
        live_filter = f" AND NOT o.{tombstone}" if tombstone else ""
        result = bind.execute(
            sa.text(
                f"SELECT o.{owner_column}, o.object_id, o.attributes, t.model_release_id "
                f"FROM {object_table} o LEFT JOIN {owner_table} t ON t.id = o.{owner_column} "
                f"WHERE 1 = 1{live_filter}"
            )
        )
        batch: list[dict[str, Any]] = []
        for owner_id, object_id, attributes, release_id in result:
            types = value_types.get(release_id, {})
            values = json.loads(attributes) if isinstance(attributes, str) else attributes
            for key, value in (values or {}).items():
                batch.append(
                    {
                        "owner_kind": kind,
                        "owner_id": owner_id,
                        "object_id": object_id,
                        "attribute_type_key": key,
                        **_typed(types.get(key), value),
                    }
                )
            if len(batch) >= 5000:
                bind.execute(table.insert(), batch)
                batch = []
        if batch:
            bind.execute(table.insert(), batch)


def _release_value_types(bind: sa.Connection) -> dict[int, dict[str, str]]:
    result: dict[int, dict[str, str]] = {}
    for release_id, model_json in bind.execute(sa.text("SELECT id, model_json FROM model_releases")):
        model = json.loads(model_json) if isinstance(model_json, str) else model_json
        result[release_id] = {
            item["key"]: item.get("valueType")
            for item in (model or {}).get("attributeTypes", [])
            if isinstance(item, dict) and "key" in item
        }
    return result


def _typed(value_type: str | None, value: Any) -> dict[str, Any]:
    """Typed columns for one JSON value; mirrors ``services.attributes.typed_value_columns``."""
    columns: dict[str, Any] = dict.fromkeys(set(_VALUE_COLUMNS.values()))
    try:
        if value_type not in _VALUE_COLUMNS:
            raise TypeError
        typed: Any = value
        if value is None or value_type == "json":
            pass
        elif value_type in {"text", "longText"}:
            if not isinstance(value, str):
                raise TypeError
        elif value_type == "integer":
            if isinstance(value, bool) or not isinstance(value, int):
                raise TypeError
        elif value_type == "decimal":
            if isinstance(value, bool):
                raise TypeError
            typed = Decimal(str(value))
            if not typed.is_finite():
                raise ValueError
            typed = Decimal(0) if typed.is_zero() else typed.normalize()
        elif value_type == "boolean":
            if not isinstance(value, bool):
                raise TypeError
        elif value_type == "date":
            typed = date.fromisoformat(value)
        elif value_type == "dateTime":
            parsed = datetime.fromisoformat(value)
            typed = (
                parsed.replace(tzinfo=UTC) if parsed.tzinfo is None else parsed.astimezone(UTC)
            )
    except (TypeError, ValueError, InvalidOperation):
        columns["json_value"] = value
        return {"value_type": "json", **columns}
    columns[_VALUE_COLUMNS[value_type]] = typed
    return {"value_type": value_type, **columns}
