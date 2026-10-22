"""Backup rehearsals recorded in the instance (Product 0.11 O2, D200).

``backup_rehearsals`` holds one row per check of a restored copy (``app.cli.restore_check``), passed
or failed, with each workspace of the copy as JSON. The copy itself is deleted after the check, so
the instance that was backed up keeps the record. Creating a table is transactional, so an
interrupted run leaves the database at ``20261024_01``.
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "20261025_01"
down_revision = "20261024_01"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "backup_rehearsals",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("public_id", sa.String(length=36), nullable=False, unique=True),
        sa.Column("checked_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("backup", sa.String(length=500), nullable=True),
        sa.Column("data_as_of", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revision_before", sa.String(length=64), nullable=True),
        sa.Column("revision_after", sa.String(length=64), nullable=True),
        sa.Column("engine_version", sa.String(length=40), nullable=False),
        sa.Column("host", sa.String(length=255), nullable=False),
        sa.Column("result", sa.String(length=10), nullable=False),
        sa.Column("failure_code", sa.String(length=60), nullable=True),
        sa.Column("failure_message", sa.Text(), nullable=True),
        sa.Column("workspaces", JSONB(), nullable=False),
        sa.CheckConstraint("result IN ('passed', 'failed')", name="ck_backup_rehearsal_result"),
    )
    op.create_index(
        "ix_backup_rehearsals_checked", "backup_rehearsals", ["checked_at", "public_id"]
    )


def downgrade() -> None:
    op.drop_table("backup_rehearsals")
