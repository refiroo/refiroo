"""Source files, their staged cells and profiles; profiling and dry-run jobs (Product 0.10 A3,
D5, D65–D71).

``source_files`` holds a file a model draft or an import profile owns (exactly one, deleted with it);
the file itself is in ``JOB_FILE_DIR`` as ``{id}.upload``. ``source_file_cells`` holds every filled
cell the profiling job read, typed, once per file (D66); ``source_file_sheets`` and
``source_file_columns`` hold the profile. ``jobs.kind`` gains ``profile`` and ``dryRun``. PostgreSQL
runs the DDL in the migration's transaction, so an interrupted run leaves the database at
``20261011_01``.
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "20261012_01"
down_revision = "20261011_01"
branch_labels = None
depends_on = None

KINDS = "kind IN ('batch', 'import', 'export', 'profile', 'dryRun')"
OLD_KINDS = "kind IN ('batch', 'import', 'export')"


def _file_key(name: str) -> sa.Column:
    return sa.Column(
        name, sa.Integer(), sa.ForeignKey("source_files.id", ondelete="CASCADE"), nullable=False
    )


def upgrade() -> None:
    op.create_table(
        "source_files",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("public_id", sa.String(36), nullable=False),
        sa.Column(
            "draft_id",
            sa.Integer(),
            sa.ForeignKey("model_drafts.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column(
            "profile_key",
            sa.String(160),
            sa.ForeignKey("import_profiles.key", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column("name", sa.String(300), nullable=False),
        sa.Column("format", sa.String(10), nullable=False),
        sa.Column("bytes", sa.BigInteger(), nullable=False),
        sa.Column("sha256", sa.String(64), nullable=False),
        sa.Column("csv_delimiter", sa.String(1), nullable=True),
        sa.Column("workspace_key", sa.String(160), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("uploaded_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("superseded_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("profile_job_id", sa.String(36), nullable=True),
        sa.CheckConstraint(
            "(draft_id IS NULL) <> (profile_key IS NULL)", name="ck_source_files_one_owner"
        ),
    )
    op.create_index("ix_source_files_public_id", "source_files", ["public_id"], unique=True)
    op.create_index("ix_source_files_draft", "source_files", ["draft_id", "id"])
    op.create_index("ix_source_files_profile", "source_files", ["profile_key", "id"])
    op.create_table(
        "source_file_cells",
        _file_key("source_file_id"),
        sa.Column("sheet_index", sa.Integer(), nullable=False),
        sa.Column("row_number", sa.Integer(), nullable=False),
        sa.Column("column_number", sa.Integer(), nullable=False),
        sa.Column("kind", sa.String(10), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("value", JSONB(), nullable=False),
        sa.PrimaryKeyConstraint(
            "source_file_id", "sheet_index", "row_number", "column_number",
            name="pk_source_file_cells",
        ),
    )
    op.create_table(
        "source_file_sheets",
        _file_key("source_file_id"),
        sa.Column("sheet_index", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(300), nullable=False),
        sa.Column("profile", sa.JSON(), nullable=False),
        sa.PrimaryKeyConstraint("source_file_id", "sheet_index", name="pk_source_file_sheets"),
    )
    op.create_table(
        "source_file_columns",
        _file_key("source_file_id"),
        sa.Column("sheet_index", sa.Integer(), nullable=False),
        sa.Column("column_number", sa.Integer(), nullable=False),
        sa.Column("statistics", sa.JSON(), nullable=False),
        sa.PrimaryKeyConstraint(
            "source_file_id", "sheet_index", "column_number", name="pk_source_file_columns"
        ),
    )
    op.drop_constraint("ck_job_kind", "jobs", type_="check")
    op.create_check_constraint("ck_job_kind", "jobs", KINDS)


def downgrade() -> None:
    op.execute("DELETE FROM jobs WHERE kind IN ('profile', 'dryRun')")
    op.drop_constraint("ck_job_kind", "jobs", type_="check")
    op.create_check_constraint("ck_job_kind", "jobs", OLD_KINDS)
    op.drop_table("source_file_columns")
    op.drop_table("source_file_sheets")
    op.drop_table("source_file_cells")
    op.drop_index("ix_source_files_profile", table_name="source_files")
    op.drop_index("ix_source_files_draft", table_name="source_files")
    op.drop_index("ix_source_files_public_id", table_name="source_files")
    op.drop_table("source_files")
