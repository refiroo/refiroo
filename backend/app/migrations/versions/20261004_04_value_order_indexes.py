"""Attribute values in value order (Base 0.9 C3a, D46).

A list sorted by an attribute reads the records with a value through an index on (attribute, typed
value, record), in value order, and stops at the page's end; before it, every page computed every
record's value and sorted the whole set. Text already has ``ix_attribute_values_key_text``; JSON is
not sortable. Creating indexes is transactional, so an interrupted run leaves the database at
``20261004_03``.
"""

from alembic import op

revision = "20261004_04"
down_revision = "20261004_03"
branch_labels = None
depends_on = None

_COLUMNS = ("integer_value", "decimal_value", "boolean_value", "date_value", "datetime_value")


def _name(column: str) -> str:
    return f"ix_attribute_values_key_{column.removesuffix('_value')}"


def upgrade() -> None:
    for column in _COLUMNS:
        op.create_index(_name(column), "attribute_values", ["attribute_type_key", column, "object_id"])


def downgrade() -> None:
    for column in _COLUMNS:
        op.drop_index(_name(column), table_name="attribute_values")
