"""Sign-in providers, people's provider identities and provider groups (Product 0.12 I3, D361–D366).

``sign_in_providers`` holds each OpenID Connect provider's settings, its client secret sealed with
``SECRETS_ENCRYPTION_KEY`` (D253); ``local_sign_in`` is one row saying whether passwords sign people
in (D365). ``user_identities`` finds a person by the provider and the token's subject (D363);
``provider_sign_ins`` holds a sign-in between the engine's redirect to the provider and its return
(D361). A group from a provider names it and its claim value, and a member of one when they were
last seen in it (D364). ``users.local_kept`` marks the people who keep local sign-in while it is
off: those whose ``created`` event names no actor, made on the server by ``create_admin``, and those
with no ``created`` event, made before 0.12 Z4 recorded them (the first administrator among them). Security events gain the aggregate ``sign-in-provider``. One transaction,
so an interrupted run leaves the database at ``20261103_01``.
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "20261104_01"
down_revision = "20261103_01"
branch_labels = None
depends_on = None

_SECURITY_BEFORE = (
    "aggregate_type IN ('user', 'group', 'role', 'grant', 'client', 'token-signing-key', 'sign-in')"
)
_SECURITY_AFTER = (
    "aggregate_type IN ('user', 'group', 'role', 'grant', 'client', 'token-signing-key', "
    "'sign-in', 'sign-in-provider')"
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
        "sign_in_providers",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("key", sa.String(64), nullable=False, unique=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("issuer", sa.Text(), nullable=False),
        sa.Column("client_id", sa.String(255), nullable=False),
        sa.Column("client_secret", sa.LargeBinary(), nullable=False),
        sa.Column("groups_claim", sa.String(200), nullable=True),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_sign_in_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_table(
        "local_sign_in",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("id = 1", name="ck_local_sign_in_one_row"),
    )
    op.execute(
        "INSERT INTO local_sign_in (id, enabled, version, updated_at) VALUES (1, true, 1, now())"
    )
    op.create_table(
        "user_identities",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column(
            "provider_id",
            sa.Integer(),
            sa.ForeignKey("sign_in_providers.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("subject", sa.String(255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_sign_in_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("provider_id", "subject", name="ux_user_identities_provider_subject"),
    )
    op.create_index("ix_user_identities_user", "user_identities", ["user_id"])
    op.create_table(
        "provider_sign_ins",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "provider_id",
            sa.Integer(),
            sa.ForeignKey("sign_in_providers.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("state_hash", sa.String(64), nullable=False, unique=True),
        sa.Column("browser_hash", sa.String(64), nullable=False),
        sa.Column("nonce", sa.String(64), nullable=False),
        sa.Column("verifier", sa.String(128), nullable=False),
        sa.Column("request", postgresql.JSONB(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_provider_sign_ins_expires", "provider_sign_ins", ["expires_at"])
    op.add_column(
        "user_groups",
        sa.Column(
            "provider_id",
            sa.Integer(),
            sa.ForeignKey("sign_in_providers.id", ondelete="CASCADE"),
            nullable=True,
        ),
    )
    op.add_column("user_groups", sa.Column("claim_value", sa.String(200), nullable=True))
    op.create_check_constraint(
        "ck_user_groups_source",
        "user_groups",
        "(provider_id IS NULL) = (claim_value IS NULL)",
    )
    op.create_index(
        "ux_user_groups_provider_claim",
        "user_groups",
        ["provider_id", "claim_value"],
        unique=True,
        postgresql_where=sa.text("provider_id IS NOT NULL"),
    )
    op.add_column(
        "user_group_members", sa.Column("seen_at", sa.DateTime(timezone=True), nullable=True)
    )
    op.add_column(
        "users",
        sa.Column("local_kept", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.alter_column("users", "local_kept", server_default=None)
    op.execute(
        """
        UPDATE users SET local_kept = true
        WHERE public_id IN (
            SELECT aggregate_id FROM audit_events
            WHERE aggregate_type = 'user' AND action = 'created' AND actor_kind IS NULL
        )
        OR NOT EXISTS (
            SELECT 1 FROM audit_events
            WHERE aggregate_type = 'user' AND action = 'created' AND aggregate_id = users.public_id
        )
        """
    )
    _security_index(_SECURITY_AFTER)


def downgrade() -> None:
    op.execute("DELETE FROM audit_events WHERE aggregate_type = 'sign-in-provider'")
    _security_index(_SECURITY_BEFORE)
    op.drop_column("users", "local_kept")
    op.drop_column("user_group_members", "seen_at")
    op.execute("DELETE FROM user_groups WHERE provider_id IS NOT NULL")
    op.drop_index("ux_user_groups_provider_claim", "user_groups")
    op.drop_constraint("ck_user_groups_source", "user_groups")
    op.drop_column("user_groups", "claim_value")
    op.drop_column("user_groups", "provider_id")
    op.drop_index("ix_provider_sign_ins_expires", "provider_sign_ins")
    op.drop_table("provider_sign_ins")
    op.drop_index("ix_user_identities_user", "user_identities")
    op.drop_table("user_identities")
    op.drop_table("local_sign_in")
    op.drop_table("sign_in_providers")
