"""Webhook delivery choices: batching, payload and CloudEvents (Base 0.9 C17, C-D120–C-D128).

``consumer_subscriptions`` gains ``max_events_per_batch`` (1 to 1,000) and ``format`` (``rdm`` or
``cloudevents``); every existing subscription takes the defaults, one event per request in RDM
JSON, whatever its mode was (C-D123). ``mode`` and ``debounce_seconds`` go with the coalesced mode
(C-D105 retired), and so do the delivery log's notices: their requests are deleted with their rows
and attempts (``CASCADE``), ``consumer_webhook_requests.kind`` is dropped, and an event row's ID,
change, type and object ID become required. PostgreSQL runs the DDL in the migration's transaction,
so an interrupted run leaves the database at ``20261007_02``.
"""

import sqlalchemy as sa
from alembic import op

revision = "20261007_03"
down_revision = "20261007_02"
branch_labels = None
depends_on = None

_EVENT_COLUMNS = ("event_id", "change", "object_type", "object_id")


def upgrade() -> None:
    op.add_column(
        "consumer_subscriptions",
        sa.Column("max_events_per_batch", sa.Integer(), nullable=False, server_default="1"),
    )
    op.add_column(
        "consumer_subscriptions",
        sa.Column("format", sa.String(20), nullable=False, server_default="rdm"),
    )
    op.alter_column("consumer_subscriptions", "max_events_per_batch", server_default=None)
    op.alter_column("consumer_subscriptions", "format", server_default=None)
    op.create_check_constraint(
        "ck_consumer_subscription_max_events_per_batch",
        "consumer_subscriptions",
        "max_events_per_batch BETWEEN 1 AND 1000",
    )
    op.create_check_constraint(
        "ck_consumer_subscription_format",
        "consumer_subscriptions",
        "format IN ('rdm', 'cloudevents')",
    )
    op.drop_constraint("ck_consumer_subscription_mode", "consumer_subscriptions", type_="check")
    op.drop_column("consumer_subscriptions", "mode")
    op.drop_column("consumer_subscriptions", "debounce_seconds")

    op.execute("DELETE FROM consumer_webhook_requests WHERE kind = 'notice'")
    op.drop_constraint("ck_consumer_webhook_request_kind", "consumer_webhook_requests", type_="check")
    op.drop_column("consumer_webhook_requests", "kind")
    for column in _EVENT_COLUMNS:
        op.alter_column("consumer_webhook_request_events", column, nullable=False)


def downgrade() -> None:
    for column in _EVENT_COLUMNS:
        op.alter_column("consumer_webhook_request_events", column, nullable=True)
    op.add_column(
        "consumer_webhook_requests",
        sa.Column("kind", sa.String(10), nullable=False, server_default="events"),
    )
    op.alter_column("consumer_webhook_requests", "kind", server_default=None)
    op.create_check_constraint(
        "ck_consumer_webhook_request_kind",
        "consumer_webhook_requests",
        "kind IN ('events', 'notice')",
    )
    op.add_column("consumer_subscriptions", sa.Column("debounce_seconds", sa.Integer(), nullable=True))
    op.add_column(
        "consumer_subscriptions",
        sa.Column("mode", sa.String(20), nullable=False, server_default="perChange"),
    )
    op.alter_column("consumer_subscriptions", "mode", server_default=None)
    op.create_check_constraint(
        "ck_consumer_subscription_mode",
        "consumer_subscriptions",
        "mode IN ('perChange', 'coalesced')",
    )
    op.drop_constraint("ck_consumer_subscription_format", "consumer_subscriptions", type_="check")
    op.drop_constraint("ck_consumer_subscription_max_events_per_batch", "consumer_subscriptions", type_="check")
    op.drop_column("consumer_subscriptions", "format")
    op.drop_column("consumer_subscriptions", "max_events_per_batch")
