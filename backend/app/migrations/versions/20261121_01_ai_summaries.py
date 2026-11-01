"""The cache of the AI summaries (Product 0.16 AO1, AO-D15).

``ai_summaries`` keeps one answer per hash of what was asked (the facts, the language, the send
level, the provider, the model and the prompt's version) for an hour, so the same facts asked twice
make one provider call, also across worker processes. One table, one transaction: an interrupted
run leaves the database at ``20261120_04``.
"""

import sqlalchemy as sa
from alembic import op

revision = "20261121_01"
down_revision = "20261120_04"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "ai_summaries",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("purpose", sa.String(40), nullable=False),
        sa.Column("input_hash", sa.String(64), nullable=False, unique=True),
        sa.Column("answer", sa.JSON(), nullable=False),
        sa.Column("call_id", sa.String(36), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_ai_summaries_expires", "ai_summaries", ["expires_at"])


def downgrade() -> None:
    op.drop_table("ai_summaries")
