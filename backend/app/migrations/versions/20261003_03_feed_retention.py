"""Feed retention (Base 0.9 F2, INTEGRATION_API §F5, D8, D40).

The feed answers positions within ``FEED_RETENTION_DAYS``; its floor is the first entry within the
period. ``ix_audit_events_feed_time`` finds that entry in one probe per read, over a workspace's feed
entries only, however long the feed and however busy other workspaces are. No data changes.
PostgreSQL runs the DDL in the migration's transaction, so an interrupted run leaves the database at
``20261003_02``.
"""

import sqlalchemy as sa
from alembic import op

revision = "20261003_03"
down_revision = "20261003_02"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index(
        "ix_audit_events_feed_time",
        "audit_events",
        ["workspace_key", "occurred_at", "feed_position"],
        postgresql_where=sa.text("feed_position IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index("ix_audit_events_feed_time", table_name="audit_events")
