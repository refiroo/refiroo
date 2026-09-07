"""Replace rejected per-object lifecycle storage with workspace revisions.

The preceding migration is intentionally retained as an input format.  This migration is the
release boundary: it converts one unambiguous effective graph per workspace and then removes all
object-level lifecycle tables and pointers.
"""

import json
from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import uuid4

import sqlalchemy as sa
from alembic import op

revision = "20260907_01"
down_revision = "20260906_01"
branch_labels = None
depends_on = None


def _json(value):
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, str):
        try:
            return json.loads(value)
        except (TypeError, json.JSONDecodeError):
            return value
    return value


_ATTRIBUTE_COLUMNS = {
    "text": "text_value",
    "longText": "text_value",
    "integer": "integer_value",
    "decimal": "decimal_value",
    "boolean": "boolean_value",
    "date": "date_value",
    "dateTime": "datetime_value",
    "json": "json_value",
}


def _sync_attribute_projection(connection, object_id, attributes) -> None:
    """Rebuild the legacy query projection from the selected lifecycle snapshot.

    Attribute rows are not lifecycle authority, but retaining their stable row IDs and declared
    value types avoids turning a corrective migration into a type downgrade or an audit join break.
    """
    rows = connection.execute(
        sa.text("SELECT * FROM attribute_values WHERE object_id = :object_id ORDER BY sequence_id"),
        {"object_id": object_id},
    ).mappings().all()
    by_key = {row["attribute_type_key"]: row for row in rows}
    for key, row in by_key.items():
        if key not in attributes:
            connection.execute(
                sa.text("DELETE FROM attribute_values WHERE id = :id"), {"id": row["id"]}
            )

    for key, raw_value in attributes.items():
        row = by_key.get(key)
        value_type = row["value_type"] if row is not None else _infer_value_type(raw_value)
        column = _ATTRIBUTE_COLUMNS.get(value_type)
        if column is None:
            raise RuntimeError(
                f"Cannot rebuild attribute projection for object '{object_id}': "
                f"unsupported declared value type {value_type!r}"
            )
        value = raw_value
        if value_type == "decimal":
            value = str(raw_value) if raw_value is not None else None
        elif value_type == "date" and isinstance(raw_value, str):
            value = date.fromisoformat(raw_value)
        elif value_type == "dateTime" and isinstance(raw_value, str):
            value = datetime.fromisoformat(raw_value)
        elif value_type == "json" and raw_value is not None:
            value = json.dumps(raw_value)
        values = {
            "object_id": object_id,
            "attribute_type_key": key,
            "value_type": value_type,
            "value": value,
        }
        if row is None:
            connection.execute(
                sa.text(
                    "INSERT INTO attribute_values "
                    "(id, object_id, attribute_type_key, value_type, "
                    f"{column}, value_source, version) "
                    "VALUES (:id, :object_id, :attribute_type_key, :value_type, :value, 'own', 1)"
                ),
                {**values, "id": str(uuid4())},
            )
            continue
        clear = ", ".join(f"{name} = NULL" for name in _ATTRIBUTE_COLUMNS.values())
        connection.execute(
            sa.text(
                f"UPDATE attribute_values SET {clear}, value_type = :value_type, "
                f"{column} = :value WHERE id = :id"
            ),
            {**values, "id": row["id"]},
        )


def _infer_value_type(value):
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, int) and not isinstance(value, bool):
        return "integer"
    if isinstance(value, float):
        return "decimal"
    if isinstance(value, (dict, list)):
        return "json"
    return "text"


def _create_tables() -> None:
    op.create_table(
        "workspace_revisions",
        sa.Column("sequence_id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("workspace_key", sa.String(160), nullable=False),
        sa.Column("model_release_id", sa.Integer(), nullable=False),
        sa.Column("revision_number", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("derived_from_revision_id", sa.String(36), nullable=True),
        sa.Column("supersedes_revision_id", sa.String(36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("activated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("retired_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("status IN ('active', 'retired')", name="ck_workspace_revision_status"),
        sa.ForeignKeyConstraint(["model_release_id"], ["model_releases.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["workspace_key"], ["workspaces.key"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["derived_from_revision_id"], ["workspace_revisions.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["supersedes_revision_id"], ["workspace_revisions.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("sequence_id"),
        sa.UniqueConstraint("id"),
        sa.UniqueConstraint("workspace_key", "revision_number", name="uq_workspace_revision_number"),
    )
    for column in ("id", "workspace_key", "model_release_id", "status", "derived_from_revision_id", "supersedes_revision_id"):
        op.create_index(f"ix_workspace_revisions_{column}", "workspace_revisions", [column], unique=column == "id")
    op.create_table(
        "workspace_drafts",
        sa.Column("sequence_id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("workspace_key", sa.String(160), nullable=False),
        sa.Column("model_release_id", sa.Integer(), nullable=False),
        sa.Column("derived_from_revision_id", sa.String(36), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["model_release_id"], ["model_releases.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["workspace_key"], ["workspaces.key"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["derived_from_revision_id"], ["workspace_revisions.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("sequence_id"),
        sa.UniqueConstraint("id"),
    )
    for column in ("id", "workspace_key", "model_release_id", "derived_from_revision_id"):
        op.create_index(f"ix_workspace_drafts_{column}", "workspace_drafts", [column], unique=column == "id")
    for table, parent, key, unique_name in (
        ("workspace_revision_objects", "revision_id", "workspace_revisions.id", "uq_workspace_revision_object"),
        ("workspace_draft_objects", "draft_id", "workspace_drafts.id", "uq_workspace_draft_object"),
    ):
        op.create_table(
            table,
            sa.Column("sequence_id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column(parent, sa.String(36), nullable=False),
            sa.Column("object_id", sa.String(36), nullable=False),
            sa.Column("application_key", sa.String(160), nullable=False),
            sa.Column("object_type_key", sa.String(160), nullable=False),
            sa.Column("name", sa.String(500), nullable=False),
            sa.Column("parent_object_id", sa.String(36), nullable=True),
            sa.Column("attributes", sa.JSON(), nullable=False),
            sa.Column("version", sa.Integer(), nullable=False),
            *(
                [sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.false())]
                if table == "workspace_draft_objects"
                else []
            ),
            sa.ForeignKeyConstraint([parent], [key], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("sequence_id"),
            sa.UniqueConstraint(parent, "object_id", name=unique_name),
        )
        op.create_index(f"ix_{table}_{parent}", table, [parent])
        op.create_index(f"ix_{table}_object_id", table, ["object_id"])
    for table, parent, key, unique_name in (
        ("workspace_revision_relations", "revision_id", "workspace_revisions.id", "uq_workspace_revision_relation"),
        ("workspace_draft_relations", "draft_id", "workspace_drafts.id", "uq_workspace_draft_relation"),
    ):
        op.create_table(
            table,
            sa.Column("sequence_id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column(parent, sa.String(36), nullable=False),
            sa.Column("relation_id", sa.String(36), nullable=False),
            sa.Column("relation_type_key", sa.String(160), nullable=False),
            sa.Column("from_object_id", sa.String(36), nullable=False),
            sa.Column("to_object_id", sa.String(36), nullable=False),
            sa.Column("attributes", sa.JSON(), nullable=False),
            sa.Column("version", sa.Integer(), nullable=False),
            *(
                [sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.false())]
                if table == "workspace_draft_relations"
                else []
            ),
            sa.ForeignKeyConstraint([parent], [key], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("sequence_id"),
            sa.UniqueConstraint(parent, "relation_id", name=unique_name),
        )
        op.create_index(f"ix_{table}_{parent}", table, [parent])
        op.create_index(f"ix_{table}_relation_id", table, ["relation_id"])


def _recover_empty_partial_schema(connection) -> None:
    """Recover only an empty SQLite DDL attempt; never discard converted data."""
    inspector = sa.inspect(connection)
    lifecycle_tables = {
        "workspace_revisions", "workspace_drafts", "workspace_revision_objects",
        "workspace_revision_relations", "workspace_draft_objects", "workspace_draft_relations",
    }
    present = lifecycle_tables & set(inspector.get_table_names())
    has_pointer = "active_revision_id" in {column["name"] for column in inspector.get_columns("workspaces")}
    if not present and not has_pointer:
        return
    if connection.dialect.name != "sqlite":
        raise RuntimeError(
            "The database contains a partial workspace-revision migration. Automatic recovery is "
            "supported only for SQLite; stop application processes, take a consistent backup, "
            "and report the database engine and current Alembic revision."
        )
    expected_columns = {
        "workspace_revisions": {
            "sequence_id", "id", "workspace_key", "model_release_id", "revision_number",
            "status", "derived_from_revision_id", "supersedes_revision_id", "created_at",
            "activated_at", "retired_at",
        },
        "workspace_drafts": {
            "sequence_id", "id", "workspace_key", "model_release_id", "derived_from_revision_id",
            "version", "created_at", "updated_at",
        },
        "workspace_revision_objects": {
            "sequence_id", "revision_id", "object_id", "application_key", "object_type_key",
            "name", "parent_object_id", "attributes", "version",
        },
        "workspace_draft_objects": {
            "sequence_id", "draft_id", "object_id", "application_key", "object_type_key",
            "name", "parent_object_id", "attributes", "version", "is_deleted",
        },
        "workspace_revision_relations": {
            "sequence_id", "revision_id", "relation_id", "relation_type_key", "from_object_id",
            "to_object_id", "attributes", "version",
        },
        "workspace_draft_relations": {
            "sequence_id", "draft_id", "relation_id", "relation_type_key", "from_object_id",
            "to_object_id", "attributes", "version", "is_deleted",
        },
    }
    populated = [
        f"{table} contains {connection.scalar(sa.text(f'SELECT COUNT(*) FROM {table}'))} row(s)"
        for table in sorted(present)
        if connection.scalar(sa.text(f"SELECT COUNT(*) FROM {table}"))
    ]
    malformed = [
        table
        for table in sorted(present)
        if {column["name"] for column in inspector.get_columns(table)} != expected_columns[table]
    ]
    if malformed:
        populated.extend(f"{table} has an unexpected schema" for table in malformed)
    if has_pointer:
        pointer_count = connection.scalar(sa.text("SELECT COUNT(*) FROM workspaces WHERE active_revision_id IS NOT NULL"))
        if pointer_count:
            populated.append(f"workspaces.active_revision_id contains {pointer_count} value(s)")
    if populated:
        raise RuntimeError(
            "The database contains an incomplete workspace-revision migration that cannot be "
            "recovered automatically: " + "; ".join(populated) + ". Stop all processes, take a "
            "consistent backup, and report this message; do not stamp the schema manually."
        )
    if has_pointer:
        indexes = {index["name"] for index in inspector.get_indexes("workspaces")}
        with op.batch_alter_table("workspaces") as batch:
            if "ix_workspaces_active_revision_id" in indexes:
                batch.drop_index("ix_workspaces_active_revision_id")
            batch.drop_column("active_revision_id")
    for table in sorted(present, reverse=True):
        op.drop_table(table)


def _copy_graph(connection, workspace_key, states, model_release_id, now) -> None:
    if not states:
        return
    objects = connection.execute(
        sa.text("SELECT * FROM objects WHERE workspace_key = :workspace_key ORDER BY sequence_id"),
        {"workspace_key": workspace_key},
    ).mappings().all()

    # 20260906_01 left the base object row as a query projection.  Its lifecycle tables are the
    # only authoritative source during this corrective migration: the row can legitimately have
    # diverged from its selected revision while a rejected WP4 editor was running.
    effective = []
    lifecycle_diagnostics = []
    for item in objects:
        object_id = item["id"]
        active_pointer = item.get("active_revision_id")
        revisions = connection.execute(
            sa.text(
                "SELECT * FROM object_revisions WHERE object_id = :object_id "
                "ORDER BY revision_number, sequence_id"
            ),
            {"object_id": object_id},
        ).mappings().all()
        drafts = connection.execute(
            sa.text(
                "SELECT * FROM object_drafts WHERE object_id = :object_id "
                "ORDER BY sequence_id"
            ),
            {"object_id": object_id},
        ).mappings().all()
        if active_pointer is not None:
            selected = [row for row in revisions if row["id"] == active_pointer]
            if len(selected) != 1 or selected[0]["status"] != "active":
                lifecycle_diagnostics.append(
                    f"object {object_id} points to missing or non-active revision {active_pointer}"
                )
                continue
            if drafts:
                lifecycle_diagnostics.append(
                    f"object {object_id} has active revision {active_pointer} and "
                    f"{len(drafts)} draft snapshot(s)"
                )
                continue
            snapshot = selected[0]
            effective.append({"item": item, "snapshot": snapshot, "state": "active"})
            continue

        if item["state"] == "draft":
            if len(drafts) != 1:
                lifecycle_diagnostics.append(
                    f"object {object_id} has {len(drafts)} draft snapshots; exactly one is required"
                )
                continue
            if revisions:
                lifecycle_diagnostics.append(
                    f"draft object {object_id} also has {len(revisions)} immutable revision(s)"
                )
                continue
            effective.append({"item": item, "snapshot": drafts[0], "state": "draft"})
            continue

        if item["state"] == "retired":
            retired = [row for row in revisions if row["status"] == "retired"]
            if len(retired) != 1 or drafts:
                lifecycle_diagnostics.append(
                    f"retired object {object_id} requires exactly one retired revision and no draft"
                )
                continue
            effective.append({"item": item, "snapshot": retired[0], "state": "retired"})
            continue

        lifecycle_diagnostics.append(f"object {object_id} has unknown state {item['state']!r}")

    if lifecycle_diagnostics:
        raise RuntimeError(
            f"Cannot convert workspace '{workspace_key}': effective object snapshots are ambiguous "
            "or incomplete: " + "; ".join(lifecycle_diagnostics) + ". "
            "Resolve the rejected object drafts/revisions so one effective graph remains, then retry migration."
        )

    effective_states = {entry["state"] for entry in effective}
    if len(effective_states) > 1:
        rendered = ", ".join(
            f"{state} ({sum(entry['state'] == state for entry in effective)})"
            for state in sorted(effective_states)
        )
        raise RuntimeError(
            f"Cannot convert workspace '{workspace_key}': object lifecycle states are ambiguous ({rendered}). "
            "Resolve the rejected object drafts/revisions so one effective graph remains, then retry migration."
        )
    state = next(iter(effective_states), next(iter(states)))
    effective_ids = {entry["item"]["id"] for entry in effective}
    relations = connection.execute(
        sa.text(
            "SELECT * FROM object_relations WHERE from_object_id IN "
            "(SELECT id FROM objects WHERE workspace_key = :workspace_key) ORDER BY sequence_id"
        ),
        {"workspace_key": workspace_key},
    ).mappings().all()
    invalid_relations = [
        relation["id"]
        for relation in relations
        if relation["from_object_id"] not in effective_ids
        or relation["to_object_id"] not in effective_ids
    ]
    if invalid_relations:
        raise RuntimeError(
            f"Cannot convert workspace '{workspace_key}': relation endpoint(s) are absent from the "
            "selected effective graph (" + ", ".join(sorted(invalid_relations)) + "). "
            "Resolve those relations, then retry migration."
        )
    # ADR-024 has no per-record draft lifecycle.  A coherent legacy draft graph is therefore
    # materialized once as the workspace's initial publication instead of being retained as a
    # second, object-derived authority.  Retired graphs stay historical and unselected.
    revision_status = "active" if state in {"active", "draft"} else "retired"
    parent_id, object_table, relation_table = (
        str(uuid4()),
        "workspace_revision_objects",
        "workspace_revision_relations",
    )
    connection.execute(sa.text(
        "INSERT INTO workspace_revisions (id, workspace_key, model_release_id, revision_number, status, derived_from_revision_id, supersedes_revision_id, created_at, activated_at, retired_at) "
        "VALUES (:id, :workspace_key, :model_release_id, 1, :status, NULL, NULL, :now, :now, :retired)"
    ), {"id": parent_id, "workspace_key": workspace_key, "model_release_id": model_release_id, "status": revision_status, "now": now, "retired": now if revision_status == "retired" else None})
    parent_column = "revision_id"
    if revision_status == "active":
        connection.execute(sa.text("UPDATE workspaces SET active_revision_id = :revision_id WHERE key = :workspace_key"), {"revision_id": parent_id, "workspace_key": workspace_key})
    for entry in effective:
        item = entry["item"]
        snapshot = entry["snapshot"]
        attributes = {}
        snapshot_attributes = snapshot.get("attributes")
        if snapshot_attributes is not None:
            parsed_attributes = _json(snapshot_attributes)
            if not isinstance(parsed_attributes, dict):
                raise RuntimeError(
                    f"Cannot convert workspace '{workspace_key}': object {item['id']} has an "
                    "invalid lifecycle attribute snapshot; expected a JSON object."
                )
            attributes = parsed_attributes
        else:
            for value in connection.execute(sa.text("SELECT * FROM attribute_values WHERE object_id = :object_id ORDER BY sequence_id"), {"object_id": item["id"]}).mappings():
                column = {"text": "text_value", "longText": "text_value", "integer": "integer_value", "decimal": "decimal_value", "boolean": "boolean_value", "date": "date_value", "dateTime": "datetime_value", "json": "json_value"}[value["value_type"]]
                attributes[value["attribute_type_key"]] = _json(value[column])
        name = snapshot.get("name", item["name"])
        parent_object_id = snapshot.get("parent_object_id", item["parent_object_id"])
        version = snapshot.get("version", item["version"])
        connection.execute(sa.text(f"INSERT INTO {object_table} ({parent_column}, object_id, application_key, object_type_key, name, parent_object_id, attributes, version) VALUES (:parent_id, :object_id, :application_key, :object_type_key, :name, :parent_object_id, :attributes, :version)"), {"parent_id": parent_id, "object_id": item["id"], "application_key": item["application_key"], "object_type_key": item["object_type_key"], "name": name, "parent_object_id": parent_object_id, "attributes": json.dumps(attributes), "version": version})
        _sync_attribute_projection(connection, item["id"], attributes)
        # Keep the old rows as a projection until the final DDL removes lifecycle authority.
        # Updating them here prevents a restart between migration and projection rebuild from
        # exposing the rejected WP4 snapshot instead of the selected workspace membership.
        connection.execute(sa.text("UPDATE objects SET name = :name, parent_object_id = :parent_object_id, version = :version WHERE id = :object_id"), {"name": name, "parent_object_id": parent_object_id, "version": version, "object_id": item["id"]})
    for relation in relations:
        attrs = _json(relation["attributes"]) or {}
        connection.execute(sa.text(f"INSERT INTO {relation_table} ({parent_column}, relation_id, relation_type_key, from_object_id, to_object_id, attributes, version) VALUES (:parent_id, :relation_id, :relation_type_key, :from_object_id, :to_object_id, :attributes, :version)"), {"parent_id": parent_id, "relation_id": relation["id"], "relation_type_key": relation["relation_type_key"], "from_object_id": relation["from_object_id"], "to_object_id": relation["to_object_id"], "attributes": json.dumps(attrs), "version": relation["version"]})


def upgrade() -> None:
    connection = op.get_bind()
    _recover_empty_partial_schema(connection)
    _create_tables()
    with op.batch_alter_table("workspaces") as batch:
        batch.add_column(sa.Column("active_revision_id", sa.String(36), nullable=True))
        batch.create_index("ix_workspaces_active_revision_id", ["active_revision_id"], unique=False)
        batch.create_foreign_key("fk_workspaces_active_revision_id_workspace_revisions", "workspace_revisions", ["active_revision_id"], ["id"], ondelete="RESTRICT")
    model_release_id = connection.scalar(sa.text("SELECT active_model_release_id FROM model_runtime_state WHERE id = 1"))
    now = datetime.now(UTC)
    workspaces = connection.execute(sa.text("SELECT key FROM workspaces ORDER BY key")).scalars().all()
    for workspace_key in workspaces:
        rows = connection.execute(sa.text("SELECT state, COUNT(*) FROM objects WHERE workspace_key = :workspace_key GROUP BY state"), {"workspace_key": workspace_key}).all()
        _copy_graph(connection, workspace_key, {str(state): int(count) for state, count in rows}, model_release_id, now)
    with op.batch_alter_table("objects") as batch:
        batch.drop_index("ix_objects_active_revision_id")
        batch.drop_index("ix_objects_state")
        batch.drop_column("active_revision_id")
        batch.drop_column("state")
    op.drop_table("object_drafts")
    op.drop_table("object_revisions")


def downgrade() -> None:
    raise RuntimeError("Workspace revision storage cannot be downgraded automatically")
