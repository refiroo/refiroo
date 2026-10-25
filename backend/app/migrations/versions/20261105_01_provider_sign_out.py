"""Signing out of the provider too (Product 0.12 I4a, D379, D380).

``sign_in_providers.sign_out_of_provider`` says a provider also signs people out of itself when they
sign out of the engine. A session started through such a provider keeps the provider's ID token,
sealed with ``SECRETS_ENCRYPTION_KEY``, until it ends (``user_sessions.provider_id_token``); the
sign-in's one-time code carries it from the callback to the session
(``authorization_codes.provider_id_token``). One transaction, so an interrupted run leaves the
database at ``20261104_01``.
"""

import sqlalchemy as sa
from alembic import op

revision = "20261105_01"
down_revision = "20261104_01"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "sign_in_providers",
        sa.Column("sign_out_of_provider", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.alter_column("sign_in_providers", "sign_out_of_provider", server_default=None)
    op.add_column("user_sessions", sa.Column("provider_id_token", sa.LargeBinary(), nullable=True))
    op.add_column(
        "authorization_codes", sa.Column("provider_id_token", sa.LargeBinary(), nullable=True)
    )


def downgrade() -> None:
    op.drop_column("authorization_codes", "provider_id_token")
    op.drop_column("user_sessions", "provider_id_token")
    op.drop_column("sign_in_providers", "sign_out_of_provider")
