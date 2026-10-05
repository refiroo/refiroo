"""Consumer events (Base 0.9 C10, CONSUMER_API "How events are produced").

``consumer_events`` holds the events the deriver makes from the feed, one per position, consumer API,
event and object, ordered within a position by ``ordinal``; its unique key is also the pull feed's
index. ``consumer_event_checkpoints`` says how far each workspace is derived.

Each existing workspace starts at its active publication's feed position, or at 0 without one
(C-D92): a consumer re-syncing from that publication finds every later event, and the entries before
it, whose state is gone, are not derived. PostgreSQL runs the DDL in the migration's transaction, so
an interrupted run leaves the database at ``20261005_03``.
"""

import sqlalchemy as sa
from alembic import op

revision = "20261006_01"
down_revision = "20261005_03"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "consumer_events",
        sa.Column("sequence_id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("event_id", sa.String(36), nullable=False, unique=True),
        sa.Column(
            "workspace_key",
            sa.String(160),
            sa.ForeignKey("workspaces.key", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("consumer_api", sa.String(160), nullable=False),
        sa.Column("contract_version", sa.Integer(), nullable=False),
        sa.Column("event_key", sa.String(160), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("ordinal", sa.Integer(), nullable=False),
        sa.Column("change", sa.String(20), nullable=False),
        sa.Column("object_id", sa.String(36), nullable=False),
        sa.Column("object_type_key", sa.String(160), nullable=False),
        sa.Column("object_type", sa.String(300), nullable=False),
        sa.Column("changed", sa.JSON(), nullable=False),
        sa.Column("cause_kind", sa.String(20), nullable=True),
        sa.Column("cause_id", sa.String(36), nullable=True),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "model_release_id",
            sa.Integer(),
            sa.ForeignKey("model_releases.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.UniqueConstraint(
            "workspace_key", "consumer_api", "position", "ordinal", name="uq_consumer_event_order"
        ),
        sa.CheckConstraint(
            "change IN ('created', 'updated', 'deleted')", name="ck_consumer_event_change"
        ),
    )
    op.create_table(
        "consumer_event_checkpoints",
        sa.Column(
            "workspace_key",
            sa.String(160),
            sa.ForeignKey("workspaces.key", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("start_position", sa.Integer(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.execute(
        "INSERT INTO consumer_event_checkpoints (workspace_key, position, start_position, updated_at) "
        "SELECT w.key, coalesce(p.feed_position, 0), coalesce(p.feed_position, 0), now() "
        "FROM workspaces w LEFT JOIN publications p ON p.id = w.active_publication_id"
    )


def downgrade() -> None:
    op.drop_table("consumer_event_checkpoints")
    op.drop_table("consumer_events")
