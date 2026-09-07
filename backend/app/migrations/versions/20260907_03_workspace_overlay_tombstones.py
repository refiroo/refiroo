"""Ensure copy-on-write overlay tables have tombstone columns."""

import sqlalchemy as sa
from alembic import op

revision = "20260907_03"
down_revision = "20260907_02"
branch_labels = None
depends_on = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    for table in ("workspace_draft_objects", "workspace_draft_relations"):
        if table in inspector.get_table_names() and "is_deleted" not in {c["name"] for c in inspector.get_columns(table)}:
            op.add_column(table, sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.false()))


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    for table in ("workspace_draft_relations", "workspace_draft_objects"):
        if table in inspector.get_table_names() and "is_deleted" in {c["name"] for c in inspector.get_columns(table)}:
            op.drop_column(table, "is_deleted")
