"""A model draft's operation history (Product 0.10 A2, D4, ADR-041).

``model_draft_operations`` holds each operation applied to a draft: its kind, parameters and inverse,
the step (one request) it belongs to, the draft version it produced, its origin, the elements it
created, re-keyed and named (D8's dependants) and, once undone, the step that undid it. Rows go with
their draft. Existing drafts start with an empty history. PostgreSQL
runs the DDL in the migration's transaction, so an interrupted run leaves the database at
``20261007_08``.
"""

import sqlalchemy as sa
from alembic import op

revision = "20261011_01"
down_revision = "20261007_08"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "model_draft_operations",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "draft_id",
            sa.Integer(),
            sa.ForeignKey("model_drafts.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("step", sa.Integer(), nullable=False),
        sa.Column("kind", sa.String(60), nullable=False),
        sa.Column("parameters", sa.JSON(), nullable=False),
        sa.Column("inverse", sa.JSON(), nullable=False),
        sa.Column("draft_version", sa.Integer(), nullable=False),
        sa.Column("author", sa.String(300), nullable=True),
        sa.Column("origin", sa.JSON(), nullable=False),
        sa.Column("effects", sa.JSON(), nullable=False),
        sa.Column("undone_by_step", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("draft_id", "sequence", name="uq_model_draft_operations_sequence"),
    )
    op.create_index(
        "ix_model_draft_operations_step", "model_draft_operations", ["draft_id", "step"]
    )


def downgrade() -> None:
    op.drop_index("ix_model_draft_operations_step", table_name="model_draft_operations")
    op.drop_table("model_draft_operations")
