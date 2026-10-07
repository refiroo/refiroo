"""Import profiles (Base 0.9 J2, INTEGRATION_API §J3, D65).

One table, instance-wide: a profile maps a file to the model, and an import names the workspace.
PostgreSQL runs the DDL in the migration's transaction, so an interrupted run leaves the database at
``20261007_05``.
"""

import sqlalchemy as sa
from alembic import op

revision = "20261007_06"
down_revision = "20261007_05"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "import_profiles",
        sa.Column("sequence_id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("key", sa.String(160), nullable=False, unique=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("definition", sa.JSON(), nullable=False),
        sa.Column(
            "checked_release_id",
            sa.Integer(),
            sa.ForeignKey("model_releases.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_import_profiles_checked_release_id", "import_profiles", ["checked_release_id"]
    )


def downgrade() -> None:
    op.drop_index("ix_import_profiles_checked_release_id", table_name="import_profiles")
    op.drop_table("import_profiles")
