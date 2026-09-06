"""Make runtime-object drafts and immutable revisions authoritative."""

import json
from datetime import date, datetime
from decimal import Decimal
from uuid import uuid4

import sqlalchemy as sa
from alembic import op

revision = "20260906_01"
down_revision = "20260905_02"
branch_labels = None
depends_on = None

_REVISION_COLUMNS = {
    "sequence_id",
    "id",
    "object_id",
    "model_release_id",
    "revision_number",
    "status",
    "derived_from_revision_id",
    "supersedes_revision_id",
    "name",
    "parent_object_id",
    "attributes",
    "required_relations",
    "created_at",
    "activated_at",
    "retired_at",
}
_DRAFT_COLUMNS = {
    "sequence_id",
    "id",
    "object_id",
    "model_release_id",
    "derived_from_revision_id",
    "name",
    "parent_object_id",
    "attributes",
    "required_relations",
    "version",
    "created_at",
    "updated_at",
}


def _json_value(value):
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    return value


def _clear_empty_partial_schema(connection) -> None:
    """Recover SQLite DDL left behind before Alembic could record this revision."""
    inspector = sa.inspect(connection)
    tables = set(inspector.get_table_names())
    object_columns = {column["name"] for column in inspector.get_columns("objects")}
    partial_tables = tables & {"object_revisions", "object_drafts"}
    has_active_pointer = "active_revision_id" in object_columns
    if not partial_tables and not has_active_pointer:
        return

    if connection.dialect.name != "sqlite":
        raise RuntimeError(
            "The database contains partial object-lifecycle schema while Alembic is still at the "
            "preceding revision. Automatic recovery is supported only for SQLite. Stop all "
            "application processes, take a consistent database backup, and report the database "
            "engine, current Alembic revision, and detected lifecycle tables or columns. Do not "
            "delete tables or stamp the migration manually."
        )

    problems = []
    for table_name, expected_columns in (
        ("object_revisions", _REVISION_COLUMNS),
        ("object_drafts", _DRAFT_COLUMNS),
    ):
        if table_name not in partial_tables:
            continue
        actual_columns = {
            column["name"] for column in inspector.get_columns(table_name)
        }
        if actual_columns != expected_columns:
            problems.append(
                f"{table_name} has unexpected columns "
                f"{sorted(actual_columns ^ expected_columns)}"
            )
        row_count = connection.scalar(sa.text(f"SELECT COUNT(*) FROM {table_name}"))
        if row_count:
            problems.append(f"{table_name} contains {row_count} row(s)")
    if has_active_pointer:
        active_pointer_count = connection.scalar(
            sa.text("SELECT COUNT(*) FROM objects WHERE active_revision_id IS NOT NULL")
        )
        if active_pointer_count:
            problems.append(
                f"objects.active_revision_id contains {active_pointer_count} value(s)"
            )
    if problems:
        raise RuntimeError(
            "The database contains an incomplete object-lifecycle migration that cannot be "
            "recovered automatically: "
            + "; ".join(problems)
            + ". Stop all application processes, take a consistent database backup, and report "
            "this message together with the current Alembic revision. Do not delete tables or "
            "stamp the migration manually."
        )

    if has_active_pointer:
        object_indexes = {index["name"] for index in inspector.get_indexes("objects")}
        with op.batch_alter_table("objects") as batch_op:
            if "ix_objects_active_revision_id" in object_indexes:
                batch_op.drop_index("ix_objects_active_revision_id")
            batch_op.drop_column("active_revision_id")
    if "object_drafts" in partial_tables:
        op.drop_table("object_drafts")
    if "object_revisions" in partial_tables:
        op.drop_table("object_revisions")


def upgrade() -> None:
    connection = op.get_bind()
    state_counts = connection.execute(
        sa.text("SELECT state, COUNT(*) FROM objects GROUP BY state ORDER BY state")
    ).all()
    unknown = [(str(state), int(count)) for state, count in state_counts if state not in {"active", "draft", "retired"}]
    if unknown:
        summary = ", ".join(f"{state} ({count})" for state, count in unknown)
        raise RuntimeError(
            "Cannot migrate runtime-object lifecycle; unknown object states exist: " + summary
        )

    _clear_empty_partial_schema(connection)

    op.create_table(
        "object_revisions",
        sa.Column("sequence_id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("object_id", sa.String(length=36), nullable=False),
        sa.Column("model_release_id", sa.Integer(), nullable=False),
        sa.Column("revision_number", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("derived_from_revision_id", sa.String(length=36), nullable=True),
        sa.Column("supersedes_revision_id", sa.String(length=36), nullable=True),
        sa.Column("name", sa.String(length=500), nullable=False),
        sa.Column("parent_object_id", sa.String(length=36), nullable=True),
        sa.Column("attributes", sa.JSON(), nullable=False),
        sa.Column("required_relations", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("activated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("retired_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("status IN ('active', 'retired')", name="ck_object_revision_status"),
        sa.ForeignKeyConstraint(["derived_from_revision_id"], ["object_revisions.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["model_release_id"], ["model_releases.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["object_id"], ["objects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["supersedes_revision_id"], ["object_revisions.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("sequence_id"),
        sa.UniqueConstraint("id"),
        sa.UniqueConstraint("object_id", "revision_number", name="uq_object_revision_number"),
    )
    for column in ("id", "object_id", "model_release_id", "status", "derived_from_revision_id", "supersedes_revision_id", "parent_object_id"):
        op.create_index(f"ix_object_revisions_{column}", "object_revisions", [column], unique=column == "id")

    op.create_table(
        "object_drafts",
        sa.Column("sequence_id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("object_id", sa.String(length=36), nullable=False),
        sa.Column("model_release_id", sa.Integer(), nullable=False),
        sa.Column("derived_from_revision_id", sa.String(length=36), nullable=True),
        sa.Column("name", sa.String(length=500), nullable=False),
        sa.Column("parent_object_id", sa.String(length=36), nullable=True),
        sa.Column("attributes", sa.JSON(), nullable=False),
        sa.Column("required_relations", sa.JSON(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["derived_from_revision_id"], ["object_revisions.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["model_release_id"], ["model_releases.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["object_id"], ["objects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("sequence_id"),
        sa.UniqueConstraint("id"),
    )
    for column in ("id", "object_id", "model_release_id", "derived_from_revision_id"):
        op.create_index(f"ix_object_drafts_{column}", "object_drafts", [column], unique=column == "id")

    with op.batch_alter_table("objects") as batch_op:
        batch_op.add_column(sa.Column("active_revision_id", sa.String(length=36), nullable=True))
        batch_op.create_index("ix_objects_active_revision_id", ["active_revision_id"], unique=False)
        batch_op.create_foreign_key(
            "fk_objects_active_revision_id_object_revisions",
            "object_revisions",
            ["active_revision_id"],
            ["id"],
            ondelete="RESTRICT",
        )

    active_model_release_id = connection.scalar(
        sa.text("SELECT active_model_release_id FROM model_runtime_state WHERE id = 1")
    )
    if active_model_release_id is None and state_counts:
        raise RuntimeError("Cannot migrate runtime objects without an active model release")
    raw_model = connection.scalar(
        sa.text("SELECT model_json FROM model_releases WHERE id = :release_id"),
        {"release_id": active_model_release_id},
    ) if active_model_release_id is not None else {}
    model = json.loads(raw_model) if isinstance(raw_model, str) else (raw_model or {})
    parent_keys_by_target = {
        item.get("key"): set(item.get("behavior", {}).get("parentRelationTypeKeys", []))
        for item in model.get("objectTypes", [])
    }
    required_bindings = {
        (item.get("relationTypeKey"), item.get("toObjectTypeKey"))
        for item in model.get("objectTypeRelations", [])
        if item.get("required")
        and item.get("relationTypeKey")
        not in parent_keys_by_target.get(item.get("toObjectTypeKey"), set())
    }

    objects = connection.execute(sa.text("SELECT * FROM objects ORDER BY sequence_id")).mappings().all()
    for item in objects:
        attributes = {}
        for value in connection.execute(
            sa.text("SELECT * FROM attribute_values WHERE object_id = :object_id ORDER BY sequence_id"),
            {"object_id": item["id"]},
        ).mappings():
            column = {
                "text": "text_value", "longText": "text_value", "integer": "integer_value",
                "decimal": "decimal_value", "boolean": "boolean_value", "date": "date_value",
                "dateTime": "datetime_value", "json": "json_value",
            }[value["value_type"]]
            attributes[value["attribute_type_key"]] = _json_value(value[column])
        required_relations = []
        if required_bindings:
            for relation in connection.execute(
                sa.text(
                    "SELECT relation_type_key, from_object_id, attributes FROM object_relations "
                    "WHERE to_object_id = :object_id ORDER BY sequence_id"
                ),
                {"object_id": item["id"]},
            ).mappings():
                if (
                    relation["relation_type_key"],
                    item["object_type_key"],
                ) in required_bindings:
                    attrs = relation["attributes"]
                    required_relations.append({
                        "relationTypeKey": relation["relation_type_key"],
                        "direction": "incoming",
                        "otherObjectId": relation["from_object_id"],
                        "attributes": json.loads(attrs) if isinstance(attrs, str) else (attrs or {}),
                    })
        snapshot = {
            "object_id": item["id"], "model_release_id": active_model_release_id,
            "name": item["name"], "parent_object_id": item["parent_object_id"],
            "attributes": json.dumps(attributes),
            "required_relations": json.dumps(required_relations),
            "created_at": item["created_at"],
        }
        if item["state"] == "draft":
            connection.execute(sa.text(
                "INSERT INTO object_drafts (id, object_id, model_release_id, derived_from_revision_id, "
                "name, parent_object_id, attributes, required_relations, version, created_at, updated_at) "
                "VALUES (:id, :object_id, :model_release_id, NULL, :name, :parent_object_id, "
                ":attributes, :required_relations, :version, :created_at, :updated_at)"
            ), {**snapshot, "id": str(uuid4()), "version": item["version"], "updated_at": item["updated_at"]})
            continue
        revision_id = str(uuid4())
        status = item["state"]
        connection.execute(sa.text(
            "INSERT INTO object_revisions (id, object_id, model_release_id, revision_number, status, "
            "derived_from_revision_id, supersedes_revision_id, name, parent_object_id, attributes, "
            "required_relations, created_at, activated_at, retired_at) VALUES "
            "(:id, :object_id, :model_release_id, 1, :status, NULL, NULL, :name, :parent_object_id, "
            ":attributes, :required_relations, :created_at, :activated_at, :retired_at)"
        ), {
            **snapshot, "id": revision_id, "status": status,
            "activated_at": item["updated_at"],
            "retired_at": item["updated_at"] if status == "retired" else None,
        })
        if status == "active":
            connection.execute(
                sa.text("UPDATE objects SET active_revision_id = :revision_id WHERE id = :object_id"),
                {"revision_id": revision_id, "object_id": item["id"]},
            )


def downgrade() -> None:
    with op.batch_alter_table("objects") as batch_op:
        batch_op.drop_constraint(
            "fk_objects_active_revision_id_object_revisions", type_="foreignkey"
        )
        batch_op.drop_index("ix_objects_active_revision_id")
        batch_op.drop_column("active_revision_id")
    op.drop_table("object_drafts")
    op.drop_table("object_revisions")
