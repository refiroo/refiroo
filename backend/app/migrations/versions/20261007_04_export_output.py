"""Export output on the job (Base 0.9 J1, D52).

``jobs`` gains ``output``: a completed export's manifest (format, counts, context, feed position,
release, size and SHA-256). The file itself lives in ``JOB_FILE_DIR`` under the job's ID (D12,
D55), so no path is stored. PostgreSQL runs the DDL in the migration's transaction, so an
interrupted run leaves the database at ``20261007_03``.
"""

import sqlalchemy as sa
from alembic import op

revision = "20261007_04"
down_revision = "20261007_03"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("jobs", sa.Column("output", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("jobs", "output")
