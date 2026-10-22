"""Booleans of change sets and their bases by value (Product 0.11 Q3, D207).

A change set's list sorted by an attribute reads the records with a value in the value's index order
(D205): its base's and its own, each through ``(owner, attribute, typed value, record)``. Q2's partial
indexes (``20261023_01``) hold numbers, decimals, dates and instants; a boolean had none, so a sort
by a flag read every record under the parent. This index holds the rows of bases and change sets with
a boolean value; a value of any other type enters none of it. Creating an index is transactional, so
an interrupted run leaves the database at ``20261025_01``.
"""

from alembic import op
from sqlalchemy import text

revision = "20261026_01"
down_revision = "20261025_01"
branch_labels = None
depends_on = None

_NAME = "ix_snapshot_attribute_values_change_set_key_boolean"


def upgrade() -> None:
    op.create_index(
        _NAME,
        "snapshot_attribute_values",
        ["owner_id", "attribute_type_key", "boolean_value", "object_id"],
        postgresql_where=text("owner_kind IN ('base', 'change_set') AND boolean_value IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index(_NAME, table_name="snapshot_attribute_values")
