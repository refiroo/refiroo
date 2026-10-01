"""Trigram search indexes over attribute text values (0.9.0-alpha.1 PG2, PG-D7).

``pg_trgm`` GIN indexes on ``attribute_values.text_value`` and
``snapshot_attribute_values.text_value`` replace the SQLite FTS5 tables of Base 0.8 S8, with the
same contract: the index decides how fast a search answers, never which records it returns
(``models/search_index.py``). The baseline created the extension. PostgreSQL runs the DDL in the
migration's transaction, so an interrupted run leaves the database at ``20261001_01``.
"""

from alembic import op

revision = "20261001_02"
down_revision = "20261001_01"
branch_labels = None
depends_on = None

_INDEXES = (
    ("ix_attribute_values_text_search", "attribute_values"),
    ("ix_snapshot_attribute_values_text_search", "snapshot_attribute_values"),
)


def upgrade() -> None:
    for name, table in _INDEXES:
        op.create_index(
            name,
            table,
            ["text_value"],
            postgresql_using="gin",
            postgresql_ops={"text_value": "gin_trgm_ops"},
        )


def downgrade() -> None:
    for name, table in reversed(_INDEXES):
        op.drop_index(name, table_name=table)
