"""The Microsoft 365 check no longer passes a row without tenant and application IDs (R13-F5).

``20261127_01`` asked ``ms_identity_mode = 'direct'``, which is NULL, not false, for a row with a
secret or a certificate; a NULL clause passes a CHECK, so such a row could be stored without
``ms_tenant_id`` and ``ms_client_id``. The constraint is replaced with ``IS NOT DISTINCT FROM`` so
that a missing mode counts as "not direct". No data changes: the application never wrote such a
row. One transaction, so an interrupted run leaves the database at ``20261127_01``.

The downgrade restores the previous constraint and removes nothing.
"""

from alembic import op

revision = "20261127_02"
down_revision = "20261127_01"
branch_labels = None
depends_on = None

_NO_SMTP = (
    "host IS NULL AND port IS NULL AND security IS NULL AND username IS NULL AND password IS NULL"
)
_COMMON = (
    "ms_authority_url IS NOT NULL AND ms_graph_url IS NOT NULL "
    "AND ((ms_client_secret IS NOT NULL)::int + (ms_certificate IS NOT NULL)::int "
    "+ (ms_identity_mode IS NOT NULL)::int = 1) "
    "AND ((ms_certificate IS NULL) = (ms_certificate_thumbprint IS NULL)) "
    "AND ((ms_certificate IS NULL) = (ms_certificate_expires_at IS NULL)) "
)
_TAIL = (
    "AND (ms_identity_mode IS DISTINCT FROM 'federated' OR ms_identity_client_id IS NOT NULL) "
    "AND (ms_identity_mode IS NOT NULL OR ms_identity_client_id IS NULL)"
)
_MS_FIELDS = (
    _COMMON + "AND ((ms_identity_mode IS NOT DISTINCT FROM 'direct') = "
    "(ms_tenant_id IS NULL AND ms_client_id IS NULL)) "
    "AND (ms_identity_mode IS NOT DISTINCT FROM 'direct' "
    "OR (ms_tenant_id IS NOT NULL AND ms_client_id IS NOT NULL)) " + _TAIL
)
_PREVIOUS_MS_FIELDS = (
    _COMMON
    + "AND ((ms_identity_mode = 'direct') = (ms_tenant_id IS NULL AND ms_client_id IS NULL)) "
    "AND (ms_identity_mode = 'direct' OR (ms_tenant_id IS NOT NULL AND ms_client_id IS NOT NULL)) "
    + _TAIL
)


def _replace(fields: str) -> None:
    op.drop_constraint("ck_mail_settings_microsoft365_fields", "mail_settings")
    op.create_check_constraint(
        "ck_mail_settings_microsoft365_fields",
        "mail_settings",
        f"method <> 'microsoft365' OR ({fields} AND {_NO_SMTP})",
    )


def upgrade() -> None:
    _replace(_MS_FIELDS)


def downgrade() -> None:
    _replace(_PREVIOUS_MS_FIELDS)
