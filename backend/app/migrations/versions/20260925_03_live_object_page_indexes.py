"""Ordered page indexes on live objects (Base 0.8 S3 follow-up).

A live object page filters by workspace and type, or by workspace, parent and type, and orders by
name with the internal sequence as tiebreak. Only single-column indexes existed, so a page past the
first, its previous-page probe, a count and above all a position read scanned the type: a position
three quarters into 100,000 records took about 500 ms. This revision adds (workspace, type, name,
sequence) and (workspace, parent, type, name, sequence) indexes, mirroring the S2 page indexes on
revision and draft-base objects, so a name-ordered page seeks to its position.

Indexes only: no data changes. An index that already has the expected columns is kept and one with
the same name but other columns is rebuilt, so an interrupted run completes.
"""

import sqlalchemy as sa
from alembic import op

revision = "20260925_03"
down_revision = "20260925_02"
branch_labels = None
depends_on = None

TABLE = "objects"
PAGE_INDEXES = {
    "ix_objects_type_name": ["workspace_key", "object_type_key", "name", "sequence_id"],
    "ix_objects_parent_name": [
        "workspace_key",
        "parent_object_id",
        "object_type_key",
        "name",
        "sequence_id",
    ],
}


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    existing = {index["name"]: index["column_names"] for index in inspector.get_indexes(TABLE)}
    for name, columns in PAGE_INDEXES.items():
        if existing.get(name) == columns:
            continue
        if name in existing:
            op.drop_index(name, table_name=TABLE)
        op.create_index(name, TABLE, columns)


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    existing = {index["name"] for index in inspector.get_indexes(TABLE)}
    for name in PAGE_INDEXES:
        if name in existing:
            op.drop_index(name, table_name=TABLE)
