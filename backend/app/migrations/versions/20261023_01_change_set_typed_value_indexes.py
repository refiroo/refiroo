"""Numbers, decimals, dates and instants of change sets and their bases by value (Product 0.11 Q2,
D186, D187).

A change set write's unique check and a batch's key reference compare the value in its typed
column. ``snapshot_attribute_values`` had a value index for text only (and C6a's for publications),
so for any other type each check read every value of the attribute in the change set and its base,
which holds the whole workspace. Four partial indexes on (owner, attribute, typed value, record)
hold the rows of bases and change sets with a value of their type: a text value enters none, any
other one index. A boolean has none: a unique boolean has at most two holders. The indexes are the
same for every model; what follows a workspace's model is which values a check looks up (D186).
Creating indexes is transactional, so an interrupted run leaves the database at ``20261022_01``.
"""

from alembic import op
from sqlalchemy import text

revision = "20261023_01"
down_revision = "20261022_01"
branch_labels = None
depends_on = None

_TYPES = ("integer", "decimal", "date", "datetime")


def _name(name: str) -> str:
    return f"ix_snapshot_attribute_values_change_set_key_{name}"


def upgrade() -> None:
    for name in _TYPES:
        op.create_index(
            _name(name),
            "snapshot_attribute_values",
            ["owner_id", "attribute_type_key", f"{name}_value", "object_id"],
            postgresql_where=text(
                f"owner_kind IN ('base', 'change_set') AND {name}_value IS NOT NULL"
            ),
        )


def downgrade() -> None:
    for name in _TYPES:
        op.drop_index(_name(name), table_name="snapshot_attribute_values")
