"""Feed positions (Base 0.9 F1, INTEGRATION_API §F3, D5).

``workspaces.feed_position`` counts the workspace's feed: a live write increments it under the
workspace row lock it already holds (PG-D5) and gives its audit entries the positions it took, so
positions are gapless and in commit order. ``audit_events`` gains the workspace, the position, the
model release the write ran under and ``feed_subject``, the identity a feed entry names (object or
relation type and ends) kept with the entry, since a later delete leaves nothing to look it up by.
``publications.feed_position`` is the position of the publication's ``published`` entry.

No backfill: earlier entries keep no position, so every feed starts empty at this revision.
PostgreSQL runs the DDL in the migration's transaction, so an interrupted run leaves the database at
``20261003_01``.
"""

import sqlalchemy as sa
from alembic import op

revision = "20261003_02"
down_revision = "20261003_01"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "workspaces",
        sa.Column("feed_position", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column("audit_events", sa.Column("workspace_key", sa.String(160), nullable=True))
    op.add_column("audit_events", sa.Column("feed_position", sa.Integer(), nullable=True))
    op.add_column(
        "audit_events",
        sa.Column(
            "model_release_id",
            sa.Integer(),
            sa.ForeignKey(
                "model_releases.id",
                name="fk_audit_events_model_release_id_model_releases",
                ondelete="RESTRICT",
            ),
            nullable=True,
        ),
    )
    op.add_column("audit_events", sa.Column("feed_subject", sa.JSON(), nullable=True))
    op.create_unique_constraint(
        "uq_audit_event_feed_position", "audit_events", ["workspace_key", "feed_position"]
    )
    op.add_column("publications", sa.Column("feed_position", sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column("publications", "feed_position")
    op.drop_constraint("uq_audit_event_feed_position", "audit_events", type_="unique")
    op.drop_column("audit_events", "feed_subject")
    op.drop_column("audit_events", "model_release_id")
    op.drop_column("audit_events", "feed_position")
    op.drop_column("audit_events", "workspace_key")
    op.drop_column("workspaces", "feed_position")
