"""Jobs found by the draft, profile or source file they serve (Product 0.10 R, R-F14).

A dry run's, a check's and an inference's supersede and latest-job reads filter
``jobs.parameters ->> 'draftId'``, ``'profileKey'`` or ``'sourceFileId'``: each gains a partial
expression index over the jobs that carry the key, so an editor step that queues a dry run no longer
scans every job of its kind. PostgreSQL runs the DDL in the migration's transaction, so an
interrupted run leaves the database at ``20261016_01``.
"""

from alembic import op

revision = "20261017_01"
down_revision = "20261016_01"
branch_labels = None
depends_on = None

KEYS = {"ix_jobs_draft": "draftId", "ix_jobs_profile": "profileKey", "ix_jobs_source_file": "sourceFileId"}


def upgrade() -> None:
    for name, key in KEYS.items():
        op.execute(
            f"CREATE INDEX {name} ON jobs ((parameters ->> '{key}'), sequence_id) "
            f"WHERE (parameters ->> '{key}') IS NOT NULL"
        )


def downgrade() -> None:
    for name in KEYS:
        op.drop_index(name, table_name="jobs")
