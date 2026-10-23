"""Browser sessions, sign-in codes, password-reset links and failed sign-ins (Product 0.12 I2).

``user_sessions`` holds a person's browser sessions and ``session_refresh_tokens`` the refresh
tokens that renew them, each used once (D251). ``authorization_codes`` holds a sign-in's one-time
code with its PKCE challenge, ``password_reset_links`` the one-time links that set a password
(D272), and ``sign_in_failures`` the counts that slow guessing (D271). Tokens, codes and links are
stored as SHA-256. New tables only, created in one transaction, so an interrupted run leaves the
database at ``20261027_01``.
"""

import sqlalchemy as sa
from alembic import op

revision = "20261028_01"
down_revision = "20261027_01"
branch_labels = None
depends_on = None


def _user() -> sa.Column:
    return sa.Column(
        "user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )


def upgrade() -> None:
    op.create_table(
        "user_sessions",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("public_id", sa.String(36), nullable=False, unique=True),
        _user(),
        sa.Column("signed_in_with", sa.String(64), nullable=False),
        sa.Column("user_agent", sa.String(512), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("idle_ends_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ends_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ended_reason", sa.String(32), nullable=True),
    )
    op.create_index("ix_user_sessions_user", "user_sessions", ["user_id", "id"])
    op.create_table(
        "session_refresh_tokens",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "session_id",
            sa.Integer(),
            sa.ForeignKey("user_sessions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("token_hash", sa.String(64), nullable=False, unique=True),
        sa.Column("issued_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_session_refresh_tokens_session", "session_refresh_tokens", ["session_id"])
    op.create_table(
        "authorization_codes",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("code_hash", sa.String(64), nullable=False, unique=True),
        _user(),
        sa.Column("client_id", sa.String(64), nullable=False),
        sa.Column("redirect_uri", sa.Text(), nullable=False),
        sa.Column("code_challenge", sa.String(128), nullable=False),
        sa.Column("signed_in_with", sa.String(64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "session_id",
            sa.Integer(),
            sa.ForeignKey("user_sessions.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.create_table(
        "password_reset_links",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("token_hash", sa.String(64), nullable=False, unique=True),
        _user(),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_password_reset_links_user", "password_reset_links", ["user_id"])
    op.create_table(
        "sign_in_failures",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("kind", sa.String(16), nullable=False),
        sa.Column("key", sa.String(320), nullable=False),
        sa.Column("count", sa.Integer(), nullable=False),
        sa.Column("last_failure_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("kind", "key", name="ux_sign_in_failures_kind_key"),
    )


def downgrade() -> None:
    op.drop_table("sign_in_failures")
    op.drop_table("password_reset_links")
    op.drop_table("authorization_codes")
    op.drop_table("session_refresh_tokens")
    op.drop_table("user_sessions")
