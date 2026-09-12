"""Add relation_set_versions table for atomic mapping concurrency.

Each row tracks the optimistic version of one exact relation-binding set: a specific workspace,
optional draft, relation type, from/to object-type pair, anchor object and direction.  Untouched
sets have implicit version 0; the first mutation inserts with version 1.
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy import text

revision = "20260912_01"
down_revision = "20260909_01"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "relation_set_versions",
        sa.Column("sequence_id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("workspace_key", sa.String(length=160), nullable=False),
        sa.Column("workspace_draft_id", sa.String(length=36), nullable=True),
        sa.Column("relation_type_key", sa.String(length=160), nullable=False),
        sa.Column("from_object_type_key", sa.String(length=160), nullable=False),
        sa.Column("to_object_type_key", sa.String(length=160), nullable=False),
        sa.Column("anchor_object_id", sa.String(length=36), nullable=False),
        sa.Column("direction", sa.String(length=10), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("direction IN ('outgoing', 'incoming')", name="ck_rsv_direction"),
        sa.ForeignKeyConstraint(["workspace_key"], ["workspaces.key"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["workspace_draft_id"], ["workspace_drafts.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("sequence_id"),
        sa.UniqueConstraint(
            "workspace_key",
            "workspace_draft_id",
            "relation_type_key",
            "from_object_type_key",
            "to_object_type_key",
            "anchor_object_id",
            "direction",
            name="uq_relation_set_version",
        ),
    )
    for column in ("workspace_key", "workspace_draft_id", "anchor_object_id"):
        op.create_index(
            f"ix_relation_set_versions_{column}", "relation_set_versions", [column]
        )
    # NULL != NULL in unique constraints, so uq_relation_set_version does not protect
    # live-context rows (workspace_draft_id IS NULL).  Add a partial unique index.
    op.create_index(
        "uq_relation_set_version_live",
        "relation_set_versions",
        [
            "workspace_key",
            "relation_type_key",
            "from_object_type_key",
            "to_object_type_key",
            "anchor_object_id",
            "direction",
        ],
        unique=True,
        sqlite_where=text("workspace_draft_id IS NULL"),
        postgresql_where=text("workspace_draft_id IS NULL"),
    )


def downgrade() -> None:
    op.drop_table("relation_set_versions")
