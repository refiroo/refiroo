"""Each engine process reports itself (Product 0.11 O1, D192).

``engine_processes`` holds one row per running process, upserted by its heartbeat: whether it is
ready, its background threads, its pool, the releases it cannot serve and its counters. The
readiness and process reads and ``/metrics`` read every process from it, since a request reaches
only one. Creating a table is transactional, so an interrupted run leaves the database at
``20261023_01``.
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "20261024_01"
down_revision = "20261023_01"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "engine_processes",
        sa.Column("process_id", sa.String(length=200), primary_key=True),
        sa.Column("host", sa.String(length=255), nullable=False),
        sa.Column("pid", sa.Integer(), nullable=False),
        sa.Column("engine_version", sa.String(length=40), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("heartbeat_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("report", JSONB(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("engine_processes")
