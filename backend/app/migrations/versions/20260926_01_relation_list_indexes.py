"""Covering endpoint indexes for revision, draft-base and draft relations (Base 0.8 S4R1).

Since S4R1 a draft or history relation page is ordered by a field of the related record (name by
default), so it reads every relation touching the record, filtered by relation type, rather than
the first page of an index in relation-ID order. The S4 endpoint indexes held (owner, end,
relation_id), so each relation cost a table read for its type and other end. This revision rebuilds
them as (owner, end, relation_type_key, relation_id, other end): the listing reads the index alone,
and a relation-type filter narrows it by prefix.

Indexes only: no data changes. The indexes keep their names; one with the expected columns is kept
and one with other columns is rebuilt, so an interrupted run completes on the next start.
"""

import sqlalchemy as sa
from alembic import op

revision = "20260926_01"
down_revision = "20260925_03"
branch_labels = None
depends_on = None

OWNERS = (
    ("workspace_revision_relations", "revision_id"),
    ("workspace_draft_base_relations", "base_id"),
    ("workspace_draft_relations", "draft_id"),
)
ENDS = (("from", "to"), ("to", "from"))

# (table, index, covering columns, S4 columns)
ENDPOINT_INDEXES = tuple(
    (
        table,
        f"ix_{table}_{end}",
        [owner, f"{end}_object_id", "relation_type_key", "relation_id", f"{other}_object_id"],
        [owner, f"{end}_object_id", "relation_id"],
    )
    for table, owner in OWNERS
    for end, other in ENDS
)


def _shape(table: str, name: str, columns: list[str]) -> None:
    existing = {
        index["name"]: index["column_names"] for index in sa.inspect(op.get_bind()).get_indexes(table)
    }
    if existing.get(name) == columns:
        return
    if name in existing:
        op.drop_index(name, table_name=table)
    op.create_index(name, table, columns)


def upgrade() -> None:
    for table, name, covering, _s4 in ENDPOINT_INDEXES:
        _shape(table, name, covering)


def downgrade() -> None:
    for table, name, _covering, s4 in ENDPOINT_INDEXES:
        _shape(table, name, s4)
