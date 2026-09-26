"""Value lookup index on the snapshot typed value index (Base 0.8 S2b).

A draft write checks a unique attribute across the whole draft. Since S2b it asks the typed index
which records of the draft or its base hold the value, rather than loading the membership. The S2
index (owner, attribute) made that read every value of the attribute: 100,000 codes for one rename.
This revision adds (owner, attribute, text value, object), so the check seeks to the value and reads
the index alone. Text holds the unique codes and names in practice; other value types still read the
attribute's values.

Indexes only: no data changes. An index with the expected columns is kept and one with the same name
but other columns is rebuilt, so an interrupted run completes on the next start.
"""

import sqlalchemy as sa
from alembic import op

revision = "20260926_02"
down_revision = "20260926_01"
branch_labels = None
depends_on = None

TABLE = "snapshot_attribute_values"
NAME = "ix_snapshot_attribute_values_owner_key_text"
COLUMNS = ["owner_id", "attribute_type_key", "text_value", "object_id"]


def upgrade() -> None:
    existing = {
        index["name"]: index["column_names"] for index in sa.inspect(op.get_bind()).get_indexes(TABLE)
    }
    if existing.get(NAME) == COLUMNS:
        return
    if NAME in existing:
        op.drop_index(NAME, table_name=TABLE)
    op.create_index(NAME, TABLE, COLUMNS)


def downgrade() -> None:
    existing = {index["name"] for index in sa.inspect(op.get_bind()).get_indexes(TABLE)}
    if NAME in existing:
        op.drop_index(NAME, table_name=TABLE)
