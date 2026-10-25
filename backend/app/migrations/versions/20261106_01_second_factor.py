"""A second factor for local accounts (Product 0.12 I4b, D383–D388).

``user_second_factors`` holds a person's authenticator app: the TOTP secret sealed with
``SECRETS_ENCRYPTION_KEY``, when it was confirmed (none while it is being set up) and the last
time step used, so a code works once. ``user_recovery_codes`` holds the ten one-time codes as
SHA-256 hashes. ``sign_in_steps`` holds a sign-in between the right password and its second step
(the token's hash, the stage, the browser's request); ``local_sign_in.second_factor_required`` is
the instance's requirement. One transaction, so an interrupted run leaves the database at
``20261105_01``.
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "20261106_01"
down_revision = "20261105_01"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "user_second_factors",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column("secret", sa.LargeBinary(), nullable=False),
        sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_step", sa.BigInteger(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "user_recovery_codes",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("code_hash", sa.String(64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_user_recovery_codes_user", "user_recovery_codes", ["user_id"])
    op.create_table(
        "sign_in_steps",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("token_hash", sa.String(64), nullable=False, unique=True),
        sa.Column(
            "user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("stage", sa.String(16), nullable=False),
        sa.Column("request", postgresql.JSONB(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_sign_in_steps_expires", "sign_in_steps", ["expires_at"])
    op.add_column(
        "local_sign_in",
        sa.Column(
            "second_factor_required", sa.Boolean(), nullable=False, server_default=sa.false()
        ),
    )
    op.alter_column("local_sign_in", "second_factor_required", server_default=None)


def downgrade() -> None:
    op.drop_column("local_sign_in", "second_factor_required")
    op.drop_index("ix_sign_in_steps_expires", "sign_in_steps")
    op.drop_table("sign_in_steps")
    op.drop_index("ix_user_recovery_codes_user", "user_recovery_codes")
    op.drop_table("user_recovery_codes")
    op.drop_table("user_second_factors")
