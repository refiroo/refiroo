"""Inbox notices by mail (Product 0.12 M2, D432).

``users.notice_mail_since`` is when a person switched on mail for their inbox (none: off); only
notices made after it are mailed. ``notifications.mailed_at`` is when the mail sender handled a
notice, so each is handled once. One transaction, so an interrupted run leaves the database at
``20261111_01``.
"""

import sqlalchemy as sa
from alembic import op

revision = "20261112_01"
down_revision = "20261111_01"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users", sa.Column("notice_mail_since", sa.DateTime(timezone=True), nullable=True)
    )
    op.add_column(
        "notifications", sa.Column("mailed_at", sa.DateTime(timezone=True), nullable=True)
    )
    op.create_index(
        "ix_notifications_unmailed",
        "notifications",
        ["sequence_id"],
        postgresql_where=sa.text("mailed_at IS NULL AND read_at IS NULL AND user_id IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index("ix_notifications_unmailed", "notifications")
    op.drop_column("notifications", "mailed_at")
    op.drop_column("users", "notice_mail_since")
