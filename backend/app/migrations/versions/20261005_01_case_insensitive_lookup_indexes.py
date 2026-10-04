"""Exact lookups ignoring case through an index (Base 0.9 C4).

XREF matches a term exactly, ignoring case, on a record's name and on its text values. Read through
the trigram indexes, such a match rechecks every record that merely contains the term, so a common
word cost about 50 ms per rule on 100,000 records. These indexes on ``lower(…)`` answer it as an
index seek: by workspace and lower-case name on ``objects``, by attribute and lower-case text on
``attribute_values``. Creating indexes is transactional, so an interrupted run leaves the database
at ``20261004_04``.
"""

import sqlalchemy as sa
from alembic import op

revision = "20261005_01"
down_revision = "20261004_04"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index("ix_objects_workspace_lower_name", "objects", ["workspace_key", sa.text("lower(name)")])
    op.create_index(
        "ix_attribute_values_key_lower_text", "attribute_values", ["attribute_type_key", sa.text("lower(text_value)")]
    )


def downgrade() -> None:
    op.drop_index("ix_attribute_values_key_lower_text", table_name="attribute_values")
    op.drop_index("ix_objects_workspace_lower_name", table_name="objects")
