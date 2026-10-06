"""Webhook delivery state (Base 0.9 C12, CONSUMER_API "Delivery").

``consumer_subscriptions`` gains what the dispatcher keeps per subscription: its lease, so one process
at a time delivers a subscription (C-D106); the batch being sent or retried, by its delivery ID and
the event key it ends at (C-D111); the failed attempts, since when and the next one, with the last
error (C-D103, C-D108); and when a batch was last acknowledged. A partial index finds the active
subscriptions that are due. Existing subscriptions have no batch pending and continue after their
acknowledged position. PostgreSQL runs the DDL in the migration's transaction, so an interrupted run
leaves the database at ``20261006_02``.
"""

import sqlalchemy as sa
from alembic import op

revision = "20261006_03"
down_revision = "20261006_02"
branch_labels = None
depends_on = None

_COLUMNS = (
    ("lease_owner", sa.String(120)),
    ("lease_expires_at", sa.DateTime(timezone=True)),
    ("pending_delivery_id", sa.String(36)),
    ("pending_position", sa.Integer()),
    ("pending_ordinal", sa.Integer()),
    ("failing_since", sa.DateTime(timezone=True)),
    ("last_attempt_at", sa.DateTime(timezone=True)),
    ("next_attempt_at", sa.DateTime(timezone=True)),
    ("last_error", sa.JSON()),
    ("last_delivered_at", sa.DateTime(timezone=True)),
)


def upgrade() -> None:
    for name, kind in _COLUMNS:
        op.add_column("consumer_subscriptions", sa.Column(name, kind, nullable=True))
    op.add_column(
        "consumer_subscriptions", sa.Column("attempts", sa.Integer(), nullable=False, server_default="0")
    )
    op.create_index(
        "ix_consumer_subscriptions_due",
        "consumer_subscriptions",
        ["next_attempt_at"],
        postgresql_where=sa.text("status = 'active'"),
    )


def downgrade() -> None:
    op.drop_index("ix_consumer_subscriptions_due", table_name="consumer_subscriptions")
    op.drop_column("consumer_subscriptions", "attempts")
    for name, _kind in reversed(_COLUMNS):
        op.drop_column("consumer_subscriptions", name)
