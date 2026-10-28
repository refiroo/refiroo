"""The proposal provider's call record (Product 0.16 AP1, AP-D4).

``ai_calls`` holds one row per call to the provider: who asked and for what, the provider and model,
the send level, the sizes and the outcome. The request and answer are kept only when the operator
turned ``AI_LOG_CONTENT`` on, and are emptied after ``AI_LOG_CONTENT_DAYS``. One transaction, so an
interrupted run leaves the database at ``20261116_01``.
"""

import sqlalchemy as sa
from alembic import op

revision = "20261117_01"
down_revision = "20261116_01"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "ai_calls",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("public_id", sa.String(36), nullable=False, unique=True),
        sa.Column("purpose", sa.String(40), nullable=False),
        sa.Column("provider", sa.String(160), nullable=False),
        sa.Column("model", sa.String(160), nullable=False),
        sa.Column("send_level", sa.String(16), nullable=False),
        sa.Column("prompt_version", sa.String(40), nullable=False),
        sa.Column(
            "requested_by_user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=True,
        ),
        sa.Column(
            "requested_by_client_id",
            sa.Integer(),
            sa.ForeignKey("oauth_clients.id", ondelete="RESTRICT"),
            nullable=True,
        ),
        sa.Column("job_id", sa.String(36), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("duration_ms", sa.Integer(), nullable=False),
        sa.Column("bytes_in", sa.Integer(), nullable=False),
        sa.Column("bytes_out", sa.Integer(), nullable=False),
        sa.Column("tokens_in", sa.Integer(), nullable=True),
        sa.Column("tokens_out", sa.Integer(), nullable=True),
        sa.Column("outcome", sa.String(16), nullable=False),
        sa.Column("failure_kind", sa.String(32), nullable=True),
        sa.Column("failure", sa.Text(), nullable=True),
        sa.Column("content", sa.JSON(), nullable=True),
        sa.Column("content_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("outcome IN ('answered', 'failed')", name="ck_ai_calls_outcome"),
        sa.CheckConstraint(
            "num_nonnulls(requested_by_user_id, requested_by_client_id) <= 1",
            name="ck_ai_calls_one_requested_by",
        ),
    )
    op.create_index("ix_ai_calls_started", "ai_calls", ["started_at", "id"])
    op.create_index(
        "ix_ai_calls_content_expiry",
        "ai_calls",
        ["content_expires_at"],
        postgresql_where=sa.text("content_expires_at IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_table("ai_calls")
