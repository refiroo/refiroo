"""The task and the draft a job names, as stored columns (Product 0.13 JG).

The Jobs page groups jobs by the assistant task or model draft they belong to. A job's
``parameters`` is JSON, whose text PostgreSQL parses for every row it reads a key from, so grouping
the whole list through ``parameters ->> 'taskId'`` cost about a tenth of a millisecond per job.
``task_ref`` and ``draft_ref`` hold those two keys as the database writes them (generated, stored),
and ``task_ref`` has an index for one task's jobs. One transaction: an interrupted run leaves the
database at ``20261123_01``.
"""

import sqlalchemy as sa
from alembic import op

revision = "20261124_01"
down_revision = "20261123_01"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "jobs",
        sa.Column("task_ref", sa.String(), sa.Computed("parameters ->> 'taskId'", persisted=True)),
    )
    op.add_column(
        "jobs",
        sa.Column(
            "draft_ref", sa.String(), sa.Computed("parameters ->> 'draftId'", persisted=True)
        ),
    )
    op.create_index(
        "ix_jobs_task_ref",
        "jobs",
        ["task_ref", "sequence_id"],
        postgresql_where=sa.text("task_ref IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index("ix_jobs_task_ref", table_name="jobs")
    op.drop_column("jobs", "draft_ref")
    op.drop_column("jobs", "task_ref")
