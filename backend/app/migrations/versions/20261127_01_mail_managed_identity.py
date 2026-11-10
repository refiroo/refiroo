"""Managed identity as a third Microsoft 365 credential (Product 0.13 MS-D5).

``mail_settings`` gains ``ms_identity_mode`` (``direct``: the Azure host's identity in the
organisation's tenant; ``federated``: a user-assigned identity as an app's federated credential) and
``ms_identity_client_id`` (the user-assigned identity's client ID; empty for a system-assigned one in
``direct`` mode). No secret is stored for it. The Microsoft 365 check constraint now asks for exactly
one credential of the three, and the tenant and application IDs only where a tenant token is
requested (not ``direct``). One transaction, so an interrupted run leaves the database at
``20261126_01``.
"""

import sqlalchemy as sa
from alembic import op

revision = "20261127_01"
down_revision = "20261126_01"
branch_labels = None
depends_on = None

_NO_MS = (
    "ms_tenant_id IS NULL AND ms_client_id IS NULL AND ms_client_secret IS NULL "
    "AND ms_certificate IS NULL AND ms_certificate_thumbprint IS NULL "
    "AND ms_certificate_expires_at IS NULL AND ms_authority_url IS NULL AND ms_graph_url IS NULL "
    "AND ms_identity_mode IS NULL AND ms_identity_client_id IS NULL"
)
_NO_SMTP = (
    "host IS NULL AND port IS NULL AND security IS NULL AND username IS NULL AND password IS NULL"
)
_MS_FIELDS = (
    "ms_authority_url IS NOT NULL AND ms_graph_url IS NOT NULL "
    "AND ((ms_client_secret IS NOT NULL)::int + (ms_certificate IS NOT NULL)::int "
    "+ (ms_identity_mode IS NOT NULL)::int = 1) "
    "AND ((ms_certificate IS NULL) = (ms_certificate_thumbprint IS NULL)) "
    "AND ((ms_certificate IS NULL) = (ms_certificate_expires_at IS NULL)) "
    "AND ((ms_identity_mode = 'direct') = (ms_tenant_id IS NULL AND ms_client_id IS NULL)) "
    "AND (ms_identity_mode = 'direct' OR (ms_tenant_id IS NOT NULL AND ms_client_id IS NOT NULL)) "
    "AND (ms_identity_mode IS DISTINCT FROM 'federated' OR ms_identity_client_id IS NOT NULL) "
    "AND (ms_identity_mode IS NOT NULL OR ms_identity_client_id IS NULL)"
)
_OLD_MS_FIELDS = (
    "ms_tenant_id IS NOT NULL AND ms_client_id IS NOT NULL AND ms_authority_url IS NOT NULL "
    "AND ms_graph_url IS NOT NULL AND ((ms_client_secret IS NULL) <> (ms_certificate IS NULL)) "
    "AND ((ms_certificate IS NULL) = (ms_certificate_thumbprint IS NULL)) "
    "AND ((ms_certificate IS NULL) = (ms_certificate_expires_at IS NULL))"
)
_OLD_NO_MS = _NO_MS.replace(" AND ms_identity_mode IS NULL AND ms_identity_client_id IS NULL", "")


def upgrade() -> None:
    op.add_column("mail_settings", sa.Column("ms_identity_mode", sa.String(16), nullable=True))
    op.add_column(
        "mail_settings", sa.Column("ms_identity_client_id", sa.String(200), nullable=True)
    )
    op.drop_constraint("ck_mail_settings_microsoft365_fields", "mail_settings")
    op.drop_constraint("ck_mail_settings_smtp_fields", "mail_settings")
    op.create_check_constraint(
        "ck_mail_settings_identity_mode",
        "mail_settings",
        "ms_identity_mode IN ('direct', 'federated')",
    )
    op.create_check_constraint(
        "ck_mail_settings_smtp_fields",
        "mail_settings",
        "method <> 'smtp' OR (host IS NOT NULL AND port IS NOT NULL AND security IS NOT NULL "
        f"AND {_NO_MS})",
    )
    op.create_check_constraint(
        "ck_mail_settings_microsoft365_fields",
        "mail_settings",
        f"method <> 'microsoft365' OR ({_MS_FIELDS} AND {_NO_SMTP})",
    )


def downgrade() -> None:
    op.execute("DELETE FROM mail_settings WHERE ms_identity_mode IS NOT NULL")
    op.drop_constraint("ck_mail_settings_microsoft365_fields", "mail_settings")
    op.drop_constraint("ck_mail_settings_smtp_fields", "mail_settings")
    op.drop_constraint("ck_mail_settings_identity_mode", "mail_settings")
    op.create_check_constraint(
        "ck_mail_settings_smtp_fields",
        "mail_settings",
        "method <> 'smtp' OR (host IS NOT NULL AND port IS NOT NULL AND security IS NOT NULL "
        f"AND {_OLD_NO_MS})",
    )
    op.create_check_constraint(
        "ck_mail_settings_microsoft365_fields",
        "mail_settings",
        f"method <> 'microsoft365' OR ({_OLD_MS_FIELDS} AND {_NO_SMTP})",
    )
    op.drop_column("mail_settings", "ms_identity_client_id")
    op.drop_column("mail_settings", "ms_identity_mode")
