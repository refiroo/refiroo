"""Consumer subscriptions (Base 0.9 C11, CONSUMER_API "Subscriptions").

``consumer_subscriptions`` holds where each consumer API's events go: the workspace, the events and
filters, the URL, the delivery mode and payload, the contract version accepted, the state with its
suspension reason, where delivery continues, and the signing key sealed with the deployment key
(C-D96). A workspace with subscriptions cannot be deleted (C-D99), so the reference restricts.
PostgreSQL runs the DDL in the migration's transaction, so an interrupted run leaves the database at
``20261006_01``.
"""

import sqlalchemy as sa
from alembic import op

revision = "20261006_02"
down_revision = "20261006_01"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "consumer_subscriptions",
        sa.Column("sequence_id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("public_id", sa.String(36), nullable=False, unique=True),
        sa.Column("consumer_api", sa.String(160), nullable=False),
        sa.Column("contract_version", sa.Integer(), nullable=False),
        sa.Column(
            "workspace_key",
            sa.String(160),
            sa.ForeignKey("workspaces.key", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("event_keys", sa.JSON(), nullable=False),
        sa.Column("filters", sa.JSON(), nullable=False),
        sa.Column("url", sa.String(2048), nullable=False),
        sa.Column("mode", sa.String(20), nullable=False),
        sa.Column("debounce_seconds", sa.Integer(), nullable=True),
        sa.Column("payload", sa.String(20), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("suspension_reason", sa.String(40), nullable=True),
        sa.Column("suspension_message", sa.Text(), nullable=True),
        sa.Column("suspension_details", sa.JSON(), nullable=True),
        sa.Column("suspended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("acknowledged_position", sa.Integer(), nullable=False),
        sa.Column("acknowledged_ordinal", sa.Integer(), nullable=False),
        sa.Column("signing_key", sa.LargeBinary(), nullable=False),
        sa.Column("signing_key_created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("mode IN ('perChange', 'coalesced')", name="ck_consumer_subscription_mode"),
        sa.CheckConstraint("payload IN ('full', 'identity')", name="ck_consumer_subscription_payload"),
        sa.CheckConstraint("status IN ('active', 'suspended')", name="ck_consumer_subscription_status"),
    )
    op.create_index("ix_consumer_subscriptions_api", "consumer_subscriptions", ["consumer_api", "sequence_id"])
    op.create_index(
        "ix_consumer_subscriptions_workspace", "consumer_subscriptions", ["workspace_key", "sequence_id"]
    )


def downgrade() -> None:
    op.drop_table("consumer_subscriptions")
