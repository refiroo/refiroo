"""Contains matches read one type's names in one workspace in one probe (Base 0.9 C14).

XREF and batch resolve read a term's contains matches of a name rule: the names of the definition's
types in one workspace. Through the trigram index on the name alone, PostgreSQL also scanned the type
index and intersected the two (about 1 ms more per probe on 110,000 records). This GIN index holds the
workspace and type beside the trigrams, which needs the ``btree_gin`` extension (shipped with the
contrib modules, as ``pg_trgm``); startup creates it when it may (``db.py``).

The same index on attribute values (attribute key beside the trigrams) was measured and left out: it
made PostgreSQL underestimate a term matching every value and read all of them in one process, so
XREF's refusal of such a term took 181 ms instead of 127 ms, for about 1.5 ms saved per ordinary
probe. PostgreSQL runs the DDL in the migration's transaction, so an interrupted run leaves the
database at ``20261005_01``.
"""

from alembic import op

revision = "20261005_02"
down_revision = "20261005_01"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS btree_gin")
    op.create_index(
        "ix_objects_type_name_trigram",
        "objects",
        ["workspace_key", "object_type_key", "name"],
        postgresql_using="gin",
        postgresql_ops={"name": "gin_trgm_ops"},
    )


def downgrade() -> None:
    op.drop_index("ix_objects_type_name_trigram", table_name="objects")
