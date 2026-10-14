"""The profile check job (Product 0.10 A5c, D83).

``jobs.kind`` gains ``profileCheck``: the check of an import profile's next file, which reports
its differences and previews its load. PostgreSQL runs the DDL in the migration's transaction, so an
interrupted run leaves the database at ``20261014_01``.
"""

from alembic import op

revision = "20261015_01"
down_revision = "20261014_01"
branch_labels = None
depends_on = None

KINDS = "kind IN ('batch', 'import', 'export', 'profile', 'dryRun', 'inference', 'profileCheck')"
OLD_KINDS = "kind IN ('batch', 'import', 'export', 'profile', 'dryRun', 'inference')"


def upgrade() -> None:
    op.drop_constraint("ck_job_kind", "jobs", type_="check")
    op.create_check_constraint("ck_job_kind", "jobs", KINDS)


def downgrade() -> None:
    op.execute("DELETE FROM jobs WHERE kind = 'profileCheck'")
    op.drop_constraint("ck_job_kind", "jobs", type_="check")
    op.create_check_constraint("ck_job_kind", "jobs", OLD_KINDS)
