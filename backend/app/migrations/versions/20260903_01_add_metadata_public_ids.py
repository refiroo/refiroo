"""Add public UUID columns to model metadata tables.

This is the initial migration, so it first provisions missing tables from the frozen schema snapshot
in this revision. For an existing pre-migration database the tables are already present and only the
``public_id`` columns are added.
"""

from uuid import uuid4

import sqlalchemy as sa

from alembic import op

revision = "20260903_01"
down_revision = None
branch_labels = None
depends_on = None

TABLES = (
    "model_releases",
    "model_applications",
    "model_attribute_types",
    "model_object_types",
    "model_object_type_attributes",
    "model_relation_types",
    "model_object_type_relations",
    "model_application_object_types",
    "model_view_definitions",
)


def _initial_schema() -> sa.MetaData:
    """Return the schema snapshot owned by this revision.

    Keep this definition frozen. Later ORM changes belong in later Alembic revisions and must not
    change what a fresh database receives while executing this historical revision.
    """
    metadata = sa.MetaData()
    sa.Table(
        "model_releases",
        metadata,
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("public_id", sa.String(36), nullable=False, index=True, unique=True),
        sa.Column("release_key", sa.String(160), nullable=False, index=True),
        sa.Column("release_name", sa.String(300), nullable=False),
        sa.Column("release_version", sa.String(80), nullable=False),
        sa.Column("schema_version", sa.String(40), nullable=False),
        sa.Column("model_hash", sa.String(64), nullable=False, unique=True),
        sa.Column("model_json", sa.JSON(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, index=True),
        sa.Column("installed_at", sa.DateTime(timezone=True), nullable=False),
    )
    sa.Table(
        "model_applications",
        metadata,
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("public_id", sa.String(36), nullable=False, index=True, unique=True),
        sa.Column(
            "model_release_id",
            sa.Integer(),
            sa.ForeignKey("model_releases.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("key", sa.String(160), nullable=False),
        sa.Column("name", sa.String(300), nullable=False),
        sa.Column("definition", sa.JSON(), nullable=False),
        sa.UniqueConstraint("model_release_id", "key", name="uq_model_application_key"),
    )
    sa.Table(
        "model_attribute_types",
        metadata,
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("public_id", sa.String(36), nullable=False, index=True, unique=True),
        sa.Column(
            "model_release_id",
            sa.Integer(),
            sa.ForeignKey("model_releases.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("key", sa.String(160), nullable=False),
        sa.Column("name", sa.String(300), nullable=False),
        sa.Column("value_type", sa.String(40), nullable=False),
        sa.Column("definition", sa.JSON(), nullable=False),
        sa.UniqueConstraint("model_release_id", "key", name="uq_model_attribute_type_key"),
    )
    sa.Table(
        "model_object_types",
        metadata,
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("public_id", sa.String(36), nullable=False, index=True, unique=True),
        sa.Column(
            "model_release_id",
            sa.Integer(),
            sa.ForeignKey("model_releases.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("key", sa.String(160), nullable=False),
        sa.Column("name", sa.String(300), nullable=False),
        sa.Column("definition", sa.JSON(), nullable=False),
        sa.UniqueConstraint("model_release_id", "key", name="uq_model_object_type_key"),
    )
    sa.Table(
        "model_object_type_attributes",
        metadata,
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("public_id", sa.String(36), nullable=False, index=True, unique=True),
        sa.Column(
            "model_release_id",
            sa.Integer(),
            sa.ForeignKey("model_releases.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("object_type_key", sa.String(160), nullable=False, index=True),
        sa.Column("attribute_type_key", sa.String(160), nullable=False, index=True),
        sa.Column("required", sa.Boolean(), nullable=False),
        sa.Column("read_only", sa.Boolean(), nullable=False),
        sa.Column("display_order", sa.Integer(), nullable=False),
        sa.Column("definition", sa.JSON(), nullable=False),
        sa.UniqueConstraint(
            "model_release_id",
            "object_type_key",
            "attribute_type_key",
            name="uq_model_object_type_attribute",
        ),
    )
    sa.Table(
        "model_relation_types",
        metadata,
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("public_id", sa.String(36), nullable=False, index=True, unique=True),
        sa.Column(
            "model_release_id",
            sa.Integer(),
            sa.ForeignKey("model_releases.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("key", sa.String(160), nullable=False),
        sa.Column("reverse_key", sa.String(160), nullable=False),
        sa.Column("name", sa.String(300), nullable=False),
        sa.Column("reverse_name", sa.String(300), nullable=False),
        sa.Column("is_oriented", sa.Boolean(), nullable=False),
        sa.Column("definition", sa.JSON(), nullable=False),
        sa.UniqueConstraint("model_release_id", "key", name="uq_model_relation_type_key"),
    )
    sa.Table(
        "model_object_type_relations",
        metadata,
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("public_id", sa.String(36), nullable=False, index=True, unique=True),
        sa.Column(
            "model_release_id",
            sa.Integer(),
            sa.ForeignKey("model_releases.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("relation_type_key", sa.String(160), nullable=False, index=True),
        sa.Column("from_object_type_key", sa.String(160), nullable=False, index=True),
        sa.Column("to_object_type_key", sa.String(160), nullable=False, index=True),
        sa.Column("cardinality", sa.String(40), nullable=False),
        sa.Column("definition", sa.JSON(), nullable=False),
        sa.UniqueConstraint(
            "model_release_id",
            "relation_type_key",
            "from_object_type_key",
            "to_object_type_key",
            name="uq_model_object_type_relation",
        ),
    )
    sa.Table(
        "model_application_object_types",
        metadata,
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("public_id", sa.String(36), nullable=False, index=True, unique=True),
        sa.Column(
            "model_release_id",
            sa.Integer(),
            sa.ForeignKey("model_releases.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("application_key", sa.String(160), nullable=False, index=True),
        sa.Column("object_type_key", sa.String(160), nullable=False, index=True),
        sa.UniqueConstraint(
            "model_release_id",
            "application_key",
            "object_type_key",
            name="uq_model_application_object_type",
        ),
    )
    sa.Table(
        "model_view_definitions",
        metadata,
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("public_id", sa.String(36), nullable=False, index=True, unique=True),
        sa.Column(
            "model_release_id",
            sa.Integer(),
            sa.ForeignKey("model_releases.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("application_key", sa.String(160), nullable=False, index=True),
        sa.Column("key", sa.String(160), nullable=False),
        sa.Column("name", sa.String(300), nullable=False),
        sa.Column("view_type", sa.String(60), nullable=False),
        sa.Column("definition", sa.JSON(), nullable=False),
        sa.UniqueConstraint(
            "model_release_id", "application_key", "key", name="uq_model_view_key"
        ),
    )
    sa.Table(
        "objects",
        metadata,
        sa.Column("sequence_id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("id", sa.String(36), nullable=False, index=True, unique=True),
        sa.Column("workspace_key", sa.String(160), nullable=False, index=True),
        sa.Column("application_key", sa.String(160), nullable=False, index=True),
        sa.Column("object_type_key", sa.String(160), nullable=False, index=True),
        sa.Column(
            "parent_object_id",
            sa.String(36),
            sa.ForeignKey("objects.id", ondelete="RESTRICT"),
            nullable=True,
            index=True,
        ),
        sa.Column("state", sa.String(60), nullable=False, index=True),
        sa.Column("name", sa.String(500), nullable=False, index=True),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    sa.Table(
        "attribute_values",
        metadata,
        sa.Column("sequence_id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("id", sa.String(36), nullable=False, unique=True),
        sa.Column(
            "object_id",
            sa.String(36),
            sa.ForeignKey("objects.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("attribute_type_key", sa.String(160), nullable=False, index=True),
        sa.Column("value_type", sa.String(40), nullable=False),
        sa.Column("text_value", sa.Text(), nullable=True),
        sa.Column("integer_value", sa.Integer(), nullable=True),
        sa.Column("decimal_value", sa.Numeric(), nullable=True),
        sa.Column("boolean_value", sa.Boolean(), nullable=True),
        sa.Column("date_value", sa.Date(), nullable=True),
        sa.Column("datetime_value", sa.DateTime(timezone=True), nullable=True),
        sa.Column("json_value", sa.JSON(), nullable=True),
        sa.Column("value_source", sa.String(40), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.UniqueConstraint("object_id", "attribute_type_key", name="uq_object_attribute_value"),
    )
    sa.Table(
        "object_relations",
        metadata,
        sa.Column("sequence_id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("id", sa.String(36), nullable=False, unique=True),
        sa.Column("relation_type_key", sa.String(160), nullable=False, index=True),
        sa.Column(
            "from_object_id",
            sa.String(36),
            sa.ForeignKey("objects.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "to_object_id",
            sa.String(36),
            sa.ForeignKey("objects.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("attributes", sa.JSON(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint(
            "relation_type_key", "from_object_id", "to_object_id", name="uq_object_relation"
        ),
    )
    sa.Table(
        "audit_events",
        metadata,
        sa.Column("sequence_id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("event_id", sa.String(36), nullable=False, unique=True),
        sa.Column("aggregate_type", sa.String(40), nullable=False, index=True),
        sa.Column("aggregate_id", sa.String(36), nullable=False, index=True),
        sa.Column("action", sa.String(80), nullable=False, index=True),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("changes", sa.JSON(), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False, index=True),
    )
    return metadata


def upgrade() -> None:
    connection = op.get_bind()
    _initial_schema().create_all(bind=connection)
    inspector = sa.inspect(connection)
    available_tables = set(inspector.get_table_names())

    for table in TABLES:
        if table not in available_tables:
            continue
        columns = {column["name"]: column for column in inspector.get_columns(table)}
        if "public_id" not in columns:
            op.add_column(table, sa.Column("public_id", sa.String(length=36), nullable=True))

        missing_ids = connection.execute(
            sa.text(f"SELECT id FROM {table} WHERE public_id IS NULL")
        ).fetchall()
        for (row_id,) in missing_ids:
            connection.execute(
                sa.text(f"UPDATE {table} SET public_id = :public_id WHERE id = :row_id"),
                {"public_id": str(uuid4()), "row_id": row_id},
            )

        columns = {column["name"]: column for column in sa.inspect(connection).get_columns(table)}
        if columns["public_id"].get("nullable", True):
            with op.batch_alter_table(table) as batch_op:
                batch_op.alter_column(
                    "public_id",
                    existing_type=sa.String(length=36),
                    nullable=False,
                )

        index_name = f"ix_{table}_public_id"
        indexes = {index["name"] for index in sa.inspect(connection).get_indexes(table)}
        if index_name not in indexes:
            op.create_index(index_name, table, ["public_id"], unique=True)


def downgrade() -> None:
    connection = op.get_bind()
    available_tables = set(sa.inspect(connection).get_table_names())
    for table in reversed(TABLES):
        if table not in available_tables:
            continue
        columns = {column["name"] for column in sa.inspect(connection).get_columns(table)}
        if "public_id" not in columns:
            continue
        index_name = f"ix_{table}_public_id"
        indexes = {index["name"] for index in sa.inspect(connection).get_indexes(table)}
        if index_name in indexes:
            op.drop_index(index_name, table_name=table)
        with op.batch_alter_table(table) as batch_op:
            batch_op.drop_column("public_id")
