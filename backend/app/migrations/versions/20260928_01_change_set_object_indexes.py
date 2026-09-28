"""Owner-leading page indexes on change set objects (Base 0.8 A6, D28).

The ORM declared ten single-column indexes on the publication and change set tables that no
migration ever created, so every migrated database ran without them. D28 decided each from the
query plans and the volume baseline:

- ``publication_objects`` (parent, type) and ``publication_relations`` and ``change_set_relations``
  (from, to, type): every read names its owner, and the owner-leading indexes the S2, S4 and S4R1
  migrations created already serve it. The declarations are removed; nothing is created here.
- ``change_set_objects`` (parent, type): a change set's own rows had only an owner index, so the
  matrix walks down from a column record found a change set's children by parent through an
  automatic index built per statement. This revision gives the table the two page indexes the
  publication and base object tables have, (change set, type, name, object) and (change set,
  parent, type, name, object), which the walks seek by (change set, parent).

A database built with ``metadata.create_all`` before this revision holds the ten removed indexes;
they are dropped where present, so every database ends with the schema the ORM declares.

Indexes only: no data changes. An index with the expected columns is kept and one with the same
name but other columns is rebuilt, so an interrupted run completes on the next start.
"""

import sqlalchemy as sa
from alembic import op

revision = "20260928_01"
down_revision = "20260927_01"
branch_labels = None
depends_on = None

TABLE = "change_set_objects"
INDEXES = {
    "ix_change_set_objects_type_name": ["change_set_id", "object_type_key", "name", "object_id"],
    "ix_change_set_objects_parent_name": [
        "change_set_id",
        "parent_object_id",
        "object_type_key",
        "name",
        "object_id",
    ],
}
# Declared until this revision, created only by ``metadata.create_all``.
REMOVED = {
    "publication_objects": ("parent_object_id", "object_type_key"),
    "change_set_objects": ("parent_object_id", "object_type_key"),
    "publication_relations": ("from_object_id", "to_object_id", "relation_type_key"),
    "change_set_relations": ("from_object_id", "to_object_id", "relation_type_key"),
}


def _existing(table: str = TABLE) -> dict[str, list[str]]:
    return {
        index["name"]: index["column_names"] for index in sa.inspect(op.get_bind()).get_indexes(table)
    }


def upgrade() -> None:
    for table, columns in REMOVED.items():
        present = _existing(table)
        for column in columns:
            if f"ix_{table}_{column}" in present:
                op.drop_index(f"ix_{table}_{column}", table_name=table)
    existing = _existing()
    for name, columns in INDEXES.items():
        if existing.get(name) == columns:
            continue
        if name in existing:
            op.drop_index(name, table_name=TABLE)
        op.create_index(name, TABLE, columns)


def downgrade() -> None:
    existing = _existing()
    for name in INDEXES:
        if name in existing:
            op.drop_index(name, table_name=TABLE)
