"""Mail through Microsoft 365 as a second sending method (Product 0.13 MS).

``mail_settings`` gains ``method`` (``smtp`` or ``microsoft365``; an existing row is ``smtp``) and the
Microsoft 365 fields: tenant ID, application (client) ID, a sealed client secret or a sealed
certificate (private key and certificate, with its thumbprint and expiry in the clear), and the token
authority and Graph addresses. The SMTP-only columns become nullable; check constraints keep each
method's fields together and the other's empty. One transaction, so an interrupted run leaves the
database at ``20261125_01``.
"""

import sqlalchemy as sa
from alembic import op

revision = "20261126_01"
down_revision = "20261125_01"
branch_labels = None
depends_on = None

_SMTP_FIELDS = "host IS NOT NULL AND port IS NOT NULL AND security IS NOT NULL"
_NO_SMTP = (
    "host IS NULL AND port IS NULL AND security IS NULL AND username IS NULL AND password IS NULL"
)
_MS_FIELDS = (
    "ms_tenant_id IS NOT NULL AND ms_client_id IS NOT NULL AND ms_authority_url IS NOT NULL "
    "AND ms_graph_url IS NOT NULL AND ((ms_client_secret IS NULL) <> (ms_certificate IS NULL)) "
    "AND ((ms_certificate IS NULL) = (ms_certificate_thumbprint IS NULL)) "
    "AND ((ms_certificate IS NULL) = (ms_certificate_expires_at IS NULL))"
)
_NO_MS = (
    "ms_tenant_id IS NULL AND ms_client_id IS NULL AND ms_client_secret IS NULL "
    "AND ms_certificate IS NULL AND ms_certificate_thumbprint IS NULL "
    "AND ms_certificate_expires_at IS NULL AND ms_authority_url IS NULL AND ms_graph_url IS NULL"
)


def upgrade() -> None:
    op.add_column(
        "mail_settings",
        sa.Column("method", sa.String(16), nullable=False, server_default="smtp"),
    )
    op.add_column("mail_settings", sa.Column("ms_tenant_id", sa.String(200), nullable=True))
    op.add_column("mail_settings", sa.Column("ms_client_id", sa.String(200), nullable=True))
    op.add_column("mail_settings", sa.Column("ms_client_secret", sa.LargeBinary(), nullable=True))
    op.add_column("mail_settings", sa.Column("ms_certificate", sa.LargeBinary(), nullable=True))
    op.add_column(
        "mail_settings", sa.Column("ms_certificate_thumbprint", sa.String(64), nullable=True)
    )
    op.add_column(
        "mail_settings",
        sa.Column("ms_certificate_expires_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column("mail_settings", sa.Column("ms_authority_url", sa.Text(), nullable=True))
    op.add_column("mail_settings", sa.Column("ms_graph_url", sa.Text(), nullable=True))
    op.alter_column("mail_settings", "host", existing_type=sa.String(255), nullable=True)
    op.alter_column("mail_settings", "port", existing_type=sa.Integer(), nullable=True)
    op.alter_column("mail_settings", "security", existing_type=sa.String(16), nullable=True)
    op.create_check_constraint(
        "ck_mail_settings_method", "mail_settings", "method IN ('smtp', 'microsoft365')"
    )
    op.create_check_constraint(
        "ck_mail_settings_smtp_fields",
        "mail_settings",
        f"method <> 'smtp' OR ({_SMTP_FIELDS} AND {_NO_MS})",
    )
    op.create_check_constraint(
        "ck_mail_settings_microsoft365_fields",
        "mail_settings",
        f"method <> 'microsoft365' OR ({_MS_FIELDS} AND {_NO_SMTP})",
    )


def downgrade() -> None:
    op.execute("DELETE FROM mail_settings WHERE method = 'microsoft365'")
    op.drop_constraint("ck_mail_settings_microsoft365_fields", "mail_settings")
    op.drop_constraint("ck_mail_settings_smtp_fields", "mail_settings")
    op.drop_constraint("ck_mail_settings_method", "mail_settings")
    op.alter_column("mail_settings", "security", existing_type=sa.String(16), nullable=False)
    op.alter_column("mail_settings", "port", existing_type=sa.Integer(), nullable=False)
    op.alter_column("mail_settings", "host", existing_type=sa.String(255), nullable=False)
    for column in (
        "ms_graph_url",
        "ms_authority_url",
        "ms_certificate_expires_at",
        "ms_certificate_thumbprint",
        "ms_certificate",
        "ms_client_secret",
        "ms_client_id",
        "ms_tenant_id",
        "method",
    ):
        op.drop_column("mail_settings", column)
