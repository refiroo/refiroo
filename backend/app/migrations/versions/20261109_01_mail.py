"""Sending mail: the SMTP settings and the outbox (Product 0.12 M1, D418, D419, D422).

``mail_settings`` is one row, absent until an administrator sets mail up; its password is sealed
with ``SECRETS_ENCRYPTION_KEY`` (D253). ``mail_outbox`` holds each message until the background
worker has sent it or given up after 24 hours; its body, which holds a one-time link, is sealed and
emptied when the message is finished. Security events gain the aggregate ``mail-settings``. One
transaction, so an interrupted run leaves the database at ``20261108_01``.
"""

import sqlalchemy as sa
from alembic import op

revision = "20261109_01"
down_revision = "20261108_01"
branch_labels = None
depends_on = None

_SECURITY_BEFORE = (
    "aggregate_type IN ('user', 'group', 'role', 'grant', 'client', 'token-signing-key', "
    "'sign-in', 'sign-in-provider')"
)
_SECURITY_AFTER = (
    "aggregate_type IN ('user', 'group', 'role', 'grant', 'client', 'token-signing-key', "
    "'sign-in', 'sign-in-provider', 'mail-settings')"
)


def _security_index(predicate: str) -> None:
    op.drop_index("ix_audit_events_security", "audit_events")
    op.create_index(
        "ix_audit_events_security",
        "audit_events",
        ["occurred_at", "sequence_id"],
        postgresql_where=sa.text(predicate),
    )


def upgrade() -> None:
    op.create_table(
        "mail_settings",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("host", sa.String(255), nullable=False),
        sa.Column("port", sa.Integer(), nullable=False),
        sa.Column("security", sa.String(16), nullable=False),
        sa.Column("username", sa.String(255), nullable=True),
        sa.Column("password", sa.LargeBinary(), nullable=True),
        sa.Column("from_address", sa.String(320), nullable=False),
        sa.Column("application_url", sa.Text(), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("id = 1", name="ck_mail_settings_one_row"),
        sa.CheckConstraint(
            "security IN ('tls', 'starttls', 'none')", name="ck_mail_settings_security"
        ),
        sa.CheckConstraint(
            "password IS NULL OR username IS NOT NULL", name="ck_mail_settings_password_user"
        ),
    )
    op.create_table(
        "mail_outbox",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("public_id", sa.String(36), nullable=False, unique=True),
        sa.Column("kind", sa.String(40), nullable=False),
        sa.Column("to_address", sa.String(320), nullable=False),
        sa.Column("subject", sa.String(300), nullable=False),
        sa.Column("body", sa.LargeBinary(), nullable=True),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("last_error_kind", sa.String(32), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("next_attempt_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("lease_owner", sa.String(160), nullable=True),
        sa.Column("lease_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("status IN ('pending', 'sent', 'failed')", name="ck_mail_outbox_status"),
    )
    op.create_index(
        "ix_mail_outbox_due",
        "mail_outbox",
        ["next_attempt_at"],
        postgresql_where=sa.text("status = 'pending'"),
    )
    op.create_index("ix_mail_outbox_created", "mail_outbox", ["created_at", "id"])
    _security_index(_SECURITY_AFTER)


def downgrade() -> None:
    op.execute("DELETE FROM audit_events WHERE aggregate_type = 'mail-settings'")
    _security_index(_SECURITY_BEFORE)
    op.drop_index("ix_mail_outbox_created", "mail_outbox")
    op.drop_index("ix_mail_outbox_due", "mail_outbox")
    op.drop_table("mail_outbox")
    op.drop_table("mail_settings")
