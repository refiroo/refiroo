"""Notification digests and followed workspaces (Product 0.16 AO3, AO-D33 to AO-D38).

A person's mail choices gain the kinds mailed in a digest, the digest's frequency and time zone and the
time the next one is due; ``workspace_followers`` holds the workspaces a person follows. Every
person's kinds stay mailed at once, as they are. One transaction: an interrupted run leaves the
database at ``20261122_01``.
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "20261123_01"
down_revision = "20261122_01"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column(
            "notice_mail_kinds_digest",
            postgresql.ARRAY(sa.String(160)),
            nullable=False,
            server_default="{}",
        ),
    )
    op.add_column("users", sa.Column("notice_digest_every", sa.String(10), nullable=True))
    op.add_column("users", sa.Column("notice_digest_zone", sa.String(64), nullable=True))
    op.add_column(
        "users", sa.Column("notice_digest_due_at", sa.DateTime(timezone=True), nullable=True)
    )
    op.create_check_constraint(
        "ck_users_notice_digest_every",
        "users",
        "notice_digest_every IS NULL OR notice_digest_every IN ('daily', 'weekly')",
    )
    op.create_check_constraint(
        "ck_users_notice_digest_set",
        "users",
        "(notice_digest_every IS NULL) = (notice_digest_zone IS NULL) "
        "AND (notice_digest_every IS NULL) = (notice_digest_due_at IS NULL)",
    )
    op.create_index(
        "ix_users_notice_digest_due",
        "users",
        ["notice_digest_due_at"],
        postgresql_where=sa.text(
            "notice_digest_due_at IS NOT NULL AND notice_mail_since IS NOT NULL"
        ),
    )
    op.create_table(
        "workspace_followers",
        sa.Column(
            "user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column(
            "workspace_key",
            sa.String(160),
            sa.ForeignKey("workspaces.key", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("user_id", "workspace_key"),
    )
    op.create_index("ix_workspace_followers_workspace", "workspace_followers", ["workspace_key"])


def downgrade() -> None:
    op.drop_table("workspace_followers")
    op.drop_index("ix_users_notice_digest_due", table_name="users")
    op.drop_constraint("ck_users_notice_digest_set", "users", type_="check")
    op.drop_constraint("ck_users_notice_digest_every", "users", type_="check")
    op.drop_column("users", "notice_digest_due_at")
    op.drop_column("users", "notice_digest_zone")
    op.drop_column("users", "notice_digest_every")
    op.drop_column("users", "notice_mail_kinds_digest")
