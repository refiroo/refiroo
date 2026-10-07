"""Import preview, confirmation and outcomes by row (Base 0.9 J3, D80–D87).

``jobs`` gains ``report`` (an import's binding report and its preview's summary) and
``confirmed_at`` (when a previewed import was confirmed). ``job_inputs`` and ``job_items`` gain
``source_index`` and ``row_number``, set for an import's items only, so its outcomes page by row;
existing jobs keep nulls and read no rows. PostgreSQL runs the DDL in the migration's transaction,
so an interrupted run leaves the database at ``20261007_07``.
"""

import sqlalchemy as sa
from alembic import op

revision = "20261007_08"
down_revision = "20261007_07"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("jobs", sa.Column("report", sa.JSON(), nullable=True))
    op.add_column("jobs", sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=True))
    for table in ("job_inputs", "job_items"):
        op.add_column(table, sa.Column("source_index", sa.Integer(), nullable=True))
        op.add_column(table, sa.Column("row_number", sa.Integer(), nullable=True))
    op.create_index("ix_job_items_rows", "job_items", ["job_id", "source_index", "row_number"])


def downgrade() -> None:
    op.drop_index("ix_job_items_rows", table_name="job_items")
    for table in ("job_inputs", "job_items"):
        op.drop_column(table, "row_number")
        op.drop_column(table, "source_index")
    op.drop_column("jobs", "confirmed_at")
    op.drop_column("jobs", "report")
