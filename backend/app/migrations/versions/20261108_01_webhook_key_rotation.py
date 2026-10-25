"""A webhook's previous signing key during a rotation (Product 0.12 K1, D238).

``consumer_subscriptions.previous_signing_key`` holds the key a rotation replaced, sealed like the
current one, and ``previous_signing_key_expires_at`` the end of the overlap in which deliveries are
signed with both. Both are empty for a subscription never rotated. One transaction, so an interrupted
run leaves the database at ``20261107_01``.
"""

import sqlalchemy as sa
from alembic import op

revision = "20261108_01"
down_revision = "20261107_01"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "consumer_subscriptions", sa.Column("previous_signing_key", sa.LargeBinary(), nullable=True)
    )
    op.add_column(
        "consumer_subscriptions",
        sa.Column("previous_signing_key_expires_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("consumer_subscriptions", "previous_signing_key_expires_at")
    op.drop_column("consumer_subscriptions", "previous_signing_key")
