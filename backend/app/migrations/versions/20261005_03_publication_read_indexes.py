"""Consumer reads pinned to a publication use the indexes live reads use (Base 0.9 C6a, C-D67, C-D68).

A consumer API read with ``publication`` matches, sorts and pages a publication's rows as it does
live rows. These indexes give them what C3a, C4 and C14 gave the live tables: an exact lookup ignoring
case by name (``publication_objects``) and by text value, a contains lookup by one type's names in one
probe (the ``btree_gin`` trigram index, which ``20261005_02`` enabled), and attribute sorts in value
order. The value indexes are partial on ``owner_kind = 'publication'``: change-set bases and change
sets, which consumers never read (C-D6), do not maintain them. Text already sorts through
``ix_snapshot_attribute_values_owner_key_text``. Creating indexes is transactional, so an interrupted
run leaves the database at ``20261005_02``.
"""

import sqlalchemy as sa
from alembic import op

revision = "20261005_03"
down_revision = "20261005_02"
branch_labels = None
depends_on = None

_PUBLICATION = sa.text("owner_kind = 'publication'")
_COLUMNS = ("integer_value", "decimal_value", "boolean_value", "date_value", "datetime_value")


def _name(column: str) -> str:
    return f"ix_snapshot_attribute_values_publication_key_{column.removesuffix('_value')}"


def upgrade() -> None:
    op.create_index(
        "ix_publication_objects_lower_name", "publication_objects", ["publication_id", sa.text("lower(name)")]
    )
    op.create_index(
        "ix_publication_objects_type_name_trigram",
        "publication_objects",
        ["publication_id", "object_type_key", "name"],
        postgresql_using="gin",
        postgresql_ops={"name": "gin_trgm_ops"},
    )
    op.create_index(
        "ix_snapshot_attribute_values_publication_lower_text",
        "snapshot_attribute_values",
        ["owner_id", "attribute_type_key", sa.text("lower(text_value)")],
        postgresql_where=_PUBLICATION,
    )
    for column in _COLUMNS:
        op.create_index(
            _name(column),
            "snapshot_attribute_values",
            ["owner_id", "attribute_type_key", column, "object_id"],
            postgresql_where=_PUBLICATION,
        )


def downgrade() -> None:
    for column in _COLUMNS:
        op.drop_index(_name(column), table_name="snapshot_attribute_values")
    op.drop_index("ix_snapshot_attribute_values_publication_lower_text", table_name="snapshot_attribute_values")
    op.drop_index("ix_publication_objects_type_name_trigram", table_name="publication_objects")
    op.drop_index("ix_publication_objects_lower_name", table_name="publication_objects")
