"""The move into a reviewed change set (Product 0.11 X3, D132, D135).

``record_origins`` holds where each record a move created came from (D23, D132): the record's ID
and workspace, the workspace and ID of the record it was copied from, and the job. It has no
foreign keys: a row is written when the move loads its change set, before the record is live, and
outlives a discarded change set, since every lookup joins a record that exists.
``change_sets.waits_for_change_set_id`` names, on a move's deletion change set in its source
workspace, the change set of the target holding the copy, which must publish first (D135).
PostgreSQL runs the DDL in the migration's transaction, so an interrupted run leaves the database at
``20261021_01``.
"""

import sqlalchemy as sa
from alembic import op

revision = "20261022_01"
down_revision = "20261021_01"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "record_origins",
        sa.Column("object_id", sa.String(36), primary_key=True),
        sa.Column("workspace_key", sa.String(160), nullable=False),
        sa.Column("origin_workspace_key", sa.String(160), nullable=False),
        sa.Column("origin_object_id", sa.String(36), nullable=False),
        sa.Column("job_id", sa.String(36), nullable=False),
        sa.Column(
            "recorded_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
    )
    op.create_index("ix_record_origins_workspace_key", "record_origins", ["workspace_key"])
    op.add_column("change_sets", sa.Column("waits_for_change_set_id", sa.String(36), nullable=True))


def downgrade() -> None:
    op.drop_column("change_sets", "waits_for_change_set_id")
    op.drop_index("ix_record_origins_workspace_key", table_name="record_origins")
    op.drop_table("record_origins")
