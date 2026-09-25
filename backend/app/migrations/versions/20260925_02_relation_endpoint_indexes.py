"""Endpoint indexes for revision, draft-base and draft relations (Base 0.8 S4).

A draft or history relation page reads the relations touching one record inside one owner (a
revision, a current-live base or a draft). Only the owner column was indexed on revision and draft
relations, so each such read scanned every relation of the owner. This revision adds
(owner, from_object_id, relation_id) and (owner, to_object_id, relation_id) indexes to all three
tables, so a relation page costs the record's own relations; the trailing relation ID serves the
default relation-ID order from the same index.

Indexes only: no data changes. An interrupted run can leave some of them behind, so an index that
already has the expected columns is kept and one with the same name but other columns is rebuilt.
"""

import sqlalchemy as sa
from alembic import op

revision = "20260925_02"
down_revision = "20260925_01"
branch_labels = None
depends_on = None

# (table, index, columns)
ENDPOINT_INDEXES = tuple(
    (table, f"ix_{table}_{end}", [owner, f"{end}_object_id", "relation_id"])
    for table, owner in (
        ("workspace_revision_relations", "revision_id"),
        ("workspace_draft_base_relations", "base_id"),
        ("workspace_draft_relations", "draft_id"),
    )
    for end in ("from", "to")
)


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    for table, name, columns in ENDPOINT_INDEXES:
        existing = {index["name"]: index["column_names"] for index in inspector.get_indexes(table)}
        if existing.get(name) == columns:
            continue
        if name in existing:
            op.drop_index(name, table_name=table)
        op.create_index(name, table, columns)


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    for table, name, _columns in ENDPOINT_INDEXES:
        if name in {index["name"] for index in inspector.get_indexes(table)}:
            op.drop_index(name, table_name=table)
