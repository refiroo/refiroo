"""A model draft's proposals and the inference job (Product 0.10 A6, D87–D89).

``model_draft_proposals`` holds the proposals of a draft's latest inference, deleted with the draft;
``jobs.kind`` gains ``inference``. PostgreSQL runs the DDL in the migration's transaction, so an
interrupted run leaves the database at ``20261013_01``.
"""

import sqlalchemy as sa
from alembic import op

revision = "20261014_01"
down_revision = "20261013_01"
branch_labels = None
depends_on = None

KINDS = "kind IN ('batch', 'import', 'export', 'profile', 'dryRun', 'inference')"
OLD_KINDS = "kind IN ('batch', 'import', 'export', 'profile', 'dryRun')"


def upgrade() -> None:
    op.create_table(
        "model_draft_proposals",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("public_id", sa.String(36), nullable=False),
        sa.Column(
            "draft_id",
            sa.Integer(),
            sa.ForeignKey("model_drafts.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("inference_id", sa.String(36), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("pattern", sa.String(60), nullable=False),
        sa.Column("signature", sa.Text(), nullable=False),
        sa.Column("body", sa.JSON(), nullable=False),
    )
    op.create_index(
        "ix_model_draft_proposals_public_id", "model_draft_proposals", ["public_id"], unique=True
    )
    op.create_index(
        "ix_model_draft_proposals_draft", "model_draft_proposals", ["draft_id", "position"]
    )
    op.drop_constraint("ck_job_kind", "jobs", type_="check")
    op.create_check_constraint("ck_job_kind", "jobs", KINDS)


def downgrade() -> None:
    op.execute("DELETE FROM jobs WHERE kind = 'inference'")
    op.drop_constraint("ck_job_kind", "jobs", type_="check")
    op.create_check_constraint("ck_job_kind", "jobs", OLD_KINDS)
    op.drop_index("ix_model_draft_proposals_draft", table_name="model_draft_proposals")
    op.drop_index("ix_model_draft_proposals_public_id", table_name="model_draft_proposals")
    op.drop_table("model_draft_proposals")
