"""An assistant task's design: its model draft and the design itself (Product 0.16 AP6).

A task that designs works on a draft of its workspace's model (``draft_id``; the draft goes with
the person's editing, so a deleted draft leaves the task without it) and keeps the assistant's
design (``design``: the model operations applied, the records the structure needs, the profile, the
questions and the last outcome). Both nullable: a task read by the rules alone has neither.
"""

import sqlalchemy as sa
from alembic import op

revision = "20261119_03"
down_revision = "20261119_02"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("ai_tasks", sa.Column("design", sa.JSON(), nullable=True))
    op.add_column(
        "ai_tasks",
        sa.Column(
            "draft_id",
            sa.Integer(),
            sa.ForeignKey("model_drafts.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.create_index("ix_ai_tasks_draft", "ai_tasks", ["draft_id"])


def downgrade() -> None:
    op.drop_index("ix_ai_tasks_draft", table_name="ai_tasks")
    op.drop_column("ai_tasks", "draft_id")
    op.drop_column("ai_tasks", "design")
