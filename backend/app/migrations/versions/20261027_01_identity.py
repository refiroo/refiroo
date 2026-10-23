"""People, OAuth clients and token signing keys (Product 0.12 I1, ADR-043).

``users`` and ``oauth_clients`` are the principals; neither is ever deleted (D237).
``oauth_client_secrets`` holds each client's Argon2id-hashed secrets, two during a rotation.
``token_signing_keys`` holds the ES256 keys that sign access tokens, each private key sealed with
``SECRETS_ENCRYPTION_KEY``; at most one is current. New tables only, created in one transaction, so
an interrupted run leaves the database at ``20261026_01``.
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "20261027_01"
down_revision = "20261026_01"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("public_id", sa.String(36), nullable=False, unique=True),
        sa.Column("username", sa.String(150), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("email", sa.String(320), nullable=True),
        sa.Column("password_hash", sa.Text(), nullable=True),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_sign_in_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ux_users_username", "users", [sa.text("lower(username)")], unique=True)
    op.create_table(
        "oauth_clients",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("public_id", sa.String(36), nullable=False, unique=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_table(
        "oauth_client_secrets",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("public_id", sa.String(36), nullable=False, unique=True),
        sa.Column(
            "client_id",
            sa.Integer(),
            sa.ForeignKey("oauth_clients.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("secret_hash", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_oauth_client_secrets_client", "oauth_client_secrets", ["client_id", "id"])
    op.create_table(
        "token_signing_keys",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("kid", sa.String(64), nullable=False, unique=True),
        sa.Column("private_key", sa.LargeBinary(), nullable=False),
        sa.Column("public_jwk", JSONB(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("rotated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("retired_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "ux_token_signing_keys_current",
        "token_signing_keys",
        [sa.text("(rotated_at IS NULL)")],
        unique=True,
        postgresql_where=sa.text("rotated_at IS NULL"),
    )


def downgrade() -> None:
    op.drop_table("token_signing_keys")
    op.drop_table("oauth_client_secrets")
    op.drop_table("oauth_clients")
    op.drop_table("users")
