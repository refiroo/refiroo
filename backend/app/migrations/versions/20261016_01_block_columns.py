"""A source file's column statistics per block (Product 0.10 A8a, D115).

A sheet laid out for reading stacks lists in the same columns, so a column holds several blocks and
its statistics are kept per block: ``source_file_columns`` gains ``block_index`` in its key, filled
from the statistics' ``block`` of the rows already stored. PostgreSQL runs the DDL in the
migration's transaction, so an interrupted run leaves the database at ``20261015_01``.
"""

import sqlalchemy as sa
from alembic import op

revision = "20261016_01"
down_revision = "20261015_01"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "source_file_columns",
        sa.Column("block_index", sa.Integer(), nullable=False, server_default="0"),
    )
    op.execute(
        "UPDATE source_file_columns SET block_index = (statistics ->> 'block')::integer"
        " WHERE statistics ->> 'block' IS NOT NULL"
    )
    op.alter_column("source_file_columns", "block_index", server_default=None)
    op.drop_constraint("pk_source_file_columns", "source_file_columns", type_="primary")
    op.create_primary_key(
        "pk_source_file_columns",
        "source_file_columns",
        ["source_file_id", "sheet_index", "block_index", "column_number"],
    )


def downgrade() -> None:
    # A column of two blocks keeps its first block's statistics.
    op.execute(
        "DELETE FROM source_file_columns c USING source_file_columns f"
        " WHERE f.source_file_id = c.source_file_id AND f.sheet_index = c.sheet_index"
        " AND f.column_number = c.column_number AND f.block_index < c.block_index"
    )
    op.drop_constraint("pk_source_file_columns", "source_file_columns", type_="primary")
    op.create_primary_key(
        "pk_source_file_columns",
        "source_file_columns",
        ["source_file_id", "sheet_index", "column_number"],
    )
    op.drop_column("source_file_columns", "block_index")
