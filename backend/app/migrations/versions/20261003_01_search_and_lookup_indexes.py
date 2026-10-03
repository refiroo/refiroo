"""Trigram search indexes over record names; one redundant value index dropped (0.9.0-alpha.1 PG5).

``pg_trgm`` GIN indexes on ``name`` of ``objects``, ``publication_objects``,
``change_set_base_objects`` and ``change_set_objects``, beside the value indexes of
``20261001_02``: a search reads the records whose name or value matches its phrase from the
indexes instead of matching every record of the type (``models/search_index.py``).

``ix_snapshot_attribute_values_owner_key`` (owner, attribute) is dropped. Its columns are the
prefix of ``ix_snapshot_attribute_values_owner_key_text``, which serves every (owner, attribute)
read. On rows written since the last ``ANALYZE`` (a change set's base just captured), the planner
chose it over the unique (owner, record, attribute) key to find one record's value and read every
value of the attribute in the owner for each record.

PostgreSQL runs the DDL in the migration's transaction, so an interrupted run leaves the database
at ``20261001_02``.
"""

from alembic import op

revision = "20261003_01"
down_revision = "20261001_02"
branch_labels = None
depends_on = None

_INDEXES = (
    ("ix_objects_name_search", "objects"),
    ("ix_publication_objects_name_search", "publication_objects"),
    ("ix_change_set_base_objects_name_search", "change_set_base_objects"),
    ("ix_change_set_objects_name_search", "change_set_objects"),
)
_DROPPED = ("ix_snapshot_attribute_values_owner_key", "snapshot_attribute_values")


def upgrade() -> None:
    for name, table in _INDEXES:
        op.create_index(
            name,
            table,
            ["name"],
            postgresql_using="gin",
            postgresql_ops={"name": "gin_trgm_ops"},
        )
    name, table = _DROPPED
    op.drop_index(name, table_name=table)


def downgrade() -> None:
    name, table = _DROPPED
    op.create_index(name, table, ["owner_id", "attribute_type_key"])
    for name, table in reversed(_INDEXES):
        op.drop_index(name, table_name=table)
