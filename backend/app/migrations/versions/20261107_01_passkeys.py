"""Passkeys for local accounts (Product 0.12 I4c, D389–D394).

``user_passkeys`` holds a person's WebAuthn credentials: the credential ID, the public key and the
signature counter; the private key never leaves the person's device. A ceremony's challenge is kept
with the sign-in steps (I4b): ``sign_in_steps.challenge`` holds it, and ``user_id`` may be empty,
since a passkey alone is used before anyone is known. One transaction, so an interrupted run leaves
the database at ``20261106_01``.
"""

import sqlalchemy as sa
from alembic import op

revision = "20261107_01"
down_revision = "20261106_01"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "user_passkeys",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("public_id", sa.String(36), nullable=False, unique=True),
        sa.Column(
            "user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("credential_id", sa.LargeBinary(), nullable=False, unique=True),
        sa.Column("public_key", sa.LargeBinary(), nullable=False),
        sa.Column("sign_count", sa.BigInteger(), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_user_passkeys_user", "user_passkeys", ["user_id", "id"])
    op.add_column("sign_in_steps", sa.Column("challenge", sa.LargeBinary(), nullable=True))
    op.alter_column("sign_in_steps", "user_id", existing_type=sa.Integer(), nullable=True)


def downgrade() -> None:
    op.execute("DELETE FROM sign_in_steps WHERE user_id IS NULL")
    op.alter_column("sign_in_steps", "user_id", existing_type=sa.Integer(), nullable=False)
    op.drop_column("sign_in_steps", "challenge")
    op.drop_index("ix_user_passkeys_user", "user_passkeys")
    op.drop_table("user_passkeys")
