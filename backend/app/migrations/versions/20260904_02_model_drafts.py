"""Add persisted, versioned model drafts."""

import sqlalchemy as sa

from alembic import op

revision = "20260904_02"
down_revision = "20260904_01"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "model_drafts",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("public_id", sa.String(length=36), nullable=False),
        sa.Column("name", sa.String(length=300), nullable=False),
        sa.Column("base_model_release_id", sa.Integer(), nullable=True),
        sa.Column("model_json", sa.JSON(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["base_model_release_id"], ["model_releases.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_model_drafts_base_model_release_id",
        "model_drafts",
        ["base_model_release_id"],
        unique=False,
    )
    op.create_index(
        "ix_model_drafts_public_id", "model_drafts", ["public_id"], unique=True
    )


def downgrade() -> None:
    op.drop_index("ix_model_drafts_public_id", table_name="model_drafts")
    op.drop_index("ix_model_drafts_base_model_release_id", table_name="model_drafts")
    op.drop_table("model_drafts")
