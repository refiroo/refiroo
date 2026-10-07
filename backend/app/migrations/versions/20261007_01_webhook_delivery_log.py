"""Webhook names and the delivery log (Base 0.9 U5a, C-D115–C-D119).

``consumer_subscriptions`` gains ``name``, filled for existing subscriptions with their URL's host
and path (C-D115). Three tables keep what was delivered (C-D116): each request of a batch with its
status and latest body, the events (or the notice) it carries, and each attempt with its start,
completion, answer or error. They go with their subscription (``CASCADE``) and are pruned after
``CONSUMER_WEBHOOK_LOG_RETENTION_DAYS`` (C-D118). PostgreSQL runs the DDL in the migration's
transaction, so an interrupted run leaves the database at ``20261006_03``.
"""

import sqlalchemy as sa
from alembic import op

revision = "20261007_01"
down_revision = "20261006_03"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("consumer_subscriptions", sa.Column("name", sa.String(200), nullable=True))
    # The host and path of the URL, without a trailing slash; the URL itself if it has neither.
    op.execute(
        "UPDATE consumer_subscriptions SET name = left(coalesce(nullif(rtrim("
        "substring(url FROM '^[a-zA-Z]+://(?:[^@/]*@)?([^?#]*)'), '/'), ''), url), 200)"
    )
    op.alter_column("consumer_subscriptions", "name", nullable=False)
    op.create_table(
        "consumer_webhook_requests",
        sa.Column("sequence_id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "subscription_sequence_id",
            sa.Integer(),
            sa.ForeignKey("consumer_subscriptions.sequence_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("delivery_id", sa.String(36), nullable=False),
        sa.Column("batch_id", sa.String(36), nullable=False),
        sa.Column("kind", sa.String(10), nullable=False),
        sa.Column("status", sa.String(10), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("request_body", sa.Text(), nullable=True),
        sa.Column("request_bytes", sa.Integer(), nullable=True),
        sa.Column("last_status", sa.Integer(), nullable=True),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("kind IN ('events', 'notice')", name="ck_consumer_webhook_request_kind"),
        sa.CheckConstraint(
            "status IN ('queued', 'sending', 'retrying', 'succeeded', 'failed', 'dropped')",
            name="ck_consumer_webhook_request_status",
        ),
        sa.UniqueConstraint("subscription_sequence_id", "delivery_id", name="uq_consumer_webhook_request_delivery"),
    )
    op.create_index(
        "ix_consumer_webhook_requests_batch", "consumer_webhook_requests", ["subscription_sequence_id", "batch_id"]
    )
    op.create_index("ix_consumer_webhook_requests_created", "consumer_webhook_requests", ["created_at"])
    op.create_table(
        "consumer_webhook_request_events",
        sa.Column(
            "request_sequence_id",
            sa.Integer(),
            sa.ForeignKey("consumer_webhook_requests.sequence_id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("ordinal", sa.Integer(), primary_key=True),
        sa.Column("event_id", sa.String(36), nullable=True),
        sa.Column("event_key", sa.String(160), nullable=False),
        sa.Column("change", sa.String(20), nullable=True),
        sa.Column("object_type", sa.String(300), nullable=True),
        sa.Column("object_id", sa.String(36), nullable=True),
        sa.Column("position", sa.Integer(), nullable=False),
    )
    op.create_table(
        "consumer_webhook_attempts",
        sa.Column(
            "request_sequence_id",
            sa.Integer(),
            sa.ForeignKey("consumer_webhook_requests.sequence_id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("number", sa.Integer(), primary_key=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column("response_status", sa.Integer(), nullable=True),
        sa.Column("error_kind", sa.String(20), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("response_body", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("consumer_webhook_attempts")
    op.drop_table("consumer_webhook_request_events")
    op.drop_index("ix_consumer_webhook_requests_created", table_name="consumer_webhook_requests")
    op.drop_index("ix_consumer_webhook_requests_batch", table_name="consumer_webhook_requests")
    op.drop_table("consumer_webhook_requests")
    op.drop_column("consumer_subscriptions", "name")
