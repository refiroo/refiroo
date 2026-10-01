"""PostgreSQL baseline: the schema at 0.9 B2 as one revision (0.9.0-alpha.1, PG-D3).

Replaces the 23 SQLite-shaped revisions up to ``20261001_01`` and keeps that revision's ID, so a
SQLite database at it is the source the copy command expects (PG-D10). Generated from the ORM
metadata against PostgreSQL 17, plus the ``pg_trgm`` extension the search indexes need (PG-D7).
Later revisions are written and tested on PostgreSQL. PostgreSQL runs this DDL in the migration's
transaction, so an interrupted run leaves an empty, unversioned database. Foreign keys are added
after every table and index, and the default workspace with the runtime state naming it is
inserted, as the SQLite history did.
"""

from datetime import UTC, datetime

import sqlalchemy as sa
from alembic import op

revision = "20261001_01"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
    op.create_table(
        "audit_events",
        sa.Column("sequence_id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("event_id", sa.String(length=36), nullable=False),
        sa.Column("aggregate_type", sa.String(length=40), nullable=False),
        sa.Column("aggregate_id", sa.String(length=255), nullable=False),
        sa.Column("action", sa.String(length=80), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("changes", sa.JSON(), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("cause_kind", sa.String(length=20), nullable=True),
        sa.Column("cause_id", sa.String(length=36), nullable=True),
        sa.PrimaryKeyConstraint("sequence_id"),
        sa.UniqueConstraint("event_id"),
    )
    op.create_index(op.f("ix_audit_events_action"), "audit_events", ["action"], unique=False)
    op.create_index(
        op.f("ix_audit_events_aggregate_id"), "audit_events", ["aggregate_id"], unique=False
    )
    op.create_index(
        op.f("ix_audit_events_aggregate_type"), "audit_events", ["aggregate_type"], unique=False
    )
    op.create_index(op.f("ix_audit_events_cause_id"), "audit_events", ["cause_id"], unique=False)
    op.create_index(
        op.f("ix_audit_events_occurred_at"), "audit_events", ["occurred_at"], unique=False
    )
    op.create_table(
        "matrix_cell_states",
        sa.Column("sequence_id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("owner_kind", sa.String(length=20), nullable=False),
        sa.Column("owner_id", sa.String(length=160), nullable=False),
        sa.Column("shape_key", sa.String(length=32), nullable=False),
        sa.Column("row_id", sa.String(length=36), nullable=False),
        sa.Column("column_id", sa.String(length=36), nullable=False),
        sa.Column("record_count", sa.Integer(), nullable=False),
        sa.Column("matching_count", sa.Integer(), nullable=False),
        sa.Column("first_publication_number", sa.Integer(), nullable=True),
        sa.CheckConstraint(
            "owner_kind IN ('live', 'history', 'publication', 'base', 'change_set')",
            name="ck_matrix_cell_state_owner_kind",
        ),
        sa.PrimaryKeyConstraint("sequence_id"),
        sa.UniqueConstraint(
            "owner_kind",
            "owner_id",
            "shape_key",
            "row_id",
            "column_id",
            name="uq_matrix_cell_state",
        ),
    )
    op.create_index(
        "ix_matrix_cell_states_column",
        "matrix_cell_states",
        [
            "owner_kind",
            "owner_id",
            "shape_key",
            "column_id",
            "row_id",
            "record_count",
            "matching_count",
            "first_publication_number",
        ],
        unique=False,
    )
    op.create_table(
        "matrix_state_builds",
        sa.Column("sequence_id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("workspace_key", sa.String(length=160), nullable=False),
        sa.Column("owner_kind", sa.String(length=20), nullable=False),
        sa.Column("owner_id", sa.String(length=160), nullable=False),
        sa.Column("shape_key", sa.String(length=32), nullable=False),
        sa.Column("shape", sa.JSON(), nullable=False),
        sa.Column("built_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("sequence_id"),
        sa.UniqueConstraint("owner_kind", "owner_id", "shape_key", name="uq_matrix_state_build"),
    )
    op.create_index(
        op.f("ix_matrix_state_builds_workspace_key"),
        "matrix_state_builds",
        ["workspace_key"],
        unique=False,
    )
    op.create_table(
        "model_releases",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("public_id", sa.String(length=36), nullable=False),
        sa.Column("release_key", sa.String(length=160), nullable=False),
        sa.Column("release_name", sa.String(length=300), nullable=False),
        sa.Column("release_version", sa.String(length=80), nullable=False),
        sa.Column("schema_version", sa.String(length=40), nullable=False),
        sa.Column("model_hash", sa.String(length=64), nullable=False),
        sa.Column("model_json", sa.JSON(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("installed_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("model_hash"),
        sa.UniqueConstraint("release_key", "release_version", name="uq_model_release_identity"),
    )
    op.create_index(
        op.f("ix_model_releases_is_active"), "model_releases", ["is_active"], unique=False
    )
    op.create_index(
        op.f("ix_model_releases_public_id"), "model_releases", ["public_id"], unique=True
    )
    op.create_index(
        op.f("ix_model_releases_release_key"), "model_releases", ["release_key"], unique=False
    )
    op.create_table(
        "snapshot_attribute_values",
        sa.Column("sequence_id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("owner_kind", sa.String(length=20), nullable=False),
        sa.Column("owner_id", sa.String(length=36), nullable=False),
        sa.Column("object_id", sa.String(length=36), nullable=False),
        sa.Column("attribute_type_key", sa.String(length=160), nullable=False),
        sa.Column("value_type", sa.String(length=40), nullable=False),
        sa.Column("text_value", sa.Text(), nullable=True),
        sa.Column("integer_value", sa.Integer(), nullable=True),
        sa.Column("decimal_value", sa.Numeric(), nullable=True),
        sa.Column("boolean_value", sa.Boolean(), nullable=True),
        sa.Column("date_value", sa.Date(), nullable=True),
        sa.Column("datetime_value", sa.DateTime(timezone=True), nullable=True),
        sa.Column("json_value", sa.JSON(), nullable=True),
        sa.CheckConstraint(
            "owner_kind IN ('publication', 'base', 'change_set')",
            name="ck_snapshot_attribute_owner_kind",
        ),
        sa.PrimaryKeyConstraint("sequence_id"),
        sa.UniqueConstraint(
            "owner_id", "object_id", "attribute_type_key", name="uq_snapshot_attribute_value"
        ),
    )
    op.create_index(
        "ix_snapshot_attribute_values_owner_key",
        "snapshot_attribute_values",
        ["owner_id", "attribute_type_key"],
        unique=False,
    )
    op.create_index(
        "ix_snapshot_attribute_values_owner_key_text",
        "snapshot_attribute_values",
        ["owner_id", "attribute_type_key", "text_value", "object_id"],
        unique=False,
    )
    op.create_table(
        "workspaces",
        sa.Column("key", sa.String(length=160), nullable=False),
        sa.Column("label", sa.String(length=300), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("active_publication_id", sa.String(length=36), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("status IN ('active', 'retired')", name="ck_workspace_status"),
        sa.PrimaryKeyConstraint("key"),
    )
    op.create_index(
        op.f("ix_workspaces_active_publication_id"),
        "workspaces",
        ["active_publication_id"],
        unique=False,
    )
    op.create_index(op.f("ix_workspaces_status"), "workspaces", ["status"], unique=False)
    op.create_table(
        "audit_event_subjects",
        sa.Column("sequence_id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("audit_event_id", sa.Integer(), nullable=False),
        sa.Column("object_id", sa.String(length=36), nullable=False),
        sa.PrimaryKeyConstraint("sequence_id"),
        sa.UniqueConstraint("audit_event_id", "object_id", name="uq_audit_event_subject"),
    )
    op.create_index(
        op.f("ix_audit_event_subjects_audit_event_id"),
        "audit_event_subjects",
        ["audit_event_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_audit_event_subjects_object_id"),
        "audit_event_subjects",
        ["object_id"],
        unique=False,
    )
    op.create_table(
        "change_set_bases",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("workspace_key", sa.String(length=160), nullable=False),
        sa.Column("model_release_id", sa.Integer(), nullable=False),
        sa.Column("model_runtime_version", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_change_set_bases_model_release_id"),
        "change_set_bases",
        ["model_release_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_change_set_bases_workspace_key"),
        "change_set_bases",
        ["workspace_key"],
        unique=False,
    )
    op.create_table(
        "jobs",
        sa.Column("sequence_id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("kind", sa.String(length=20), nullable=False),
        sa.Column("workspace_key", sa.String(length=160), nullable=False),
        sa.Column("change_set_id", sa.String(length=36), nullable=True),
        sa.Column("model_release_id", sa.Integer(), nullable=False),
        sa.Column("parameters", sa.JSON(), nullable=False),
        sa.Column("state", sa.String(length=30), nullable=False),
        sa.Column("stage", sa.String(length=30), nullable=True),
        sa.Column("total", sa.Integer(), nullable=True),
        sa.Column("processed", sa.Integer(), nullable=False),
        sa.Column("counts", sa.JSON(), nullable=False),
        sa.Column("result", sa.String(length=20), nullable=True),
        sa.Column("error", sa.JSON(), nullable=True),
        sa.Column("change_set_version", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("lease_owner", sa.String(length=120), nullable=True),
        sa.Column("lease_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancel_requested_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("kind IN ('batch', 'import', 'export')", name="ck_job_kind"),
        sa.CheckConstraint(
            "state IN ('queued', 'running', 'awaiting_confirmation', 'completed', 'failed', 'cancelled', 'expired')",
            name="ck_job_state",
        ),
        sa.PrimaryKeyConstraint("sequence_id"),
    )
    op.create_index(op.f("ix_jobs_id"), "jobs", ["id"], unique=True)
    op.create_index(op.f("ix_jobs_model_release_id"), "jobs", ["model_release_id"], unique=False)
    op.create_index("ix_jobs_state", "jobs", ["state", "sequence_id"], unique=False)
    op.create_index(
        "ix_jobs_workspace_created", "jobs", ["workspace_key", "sequence_id"], unique=False
    )
    op.create_table(
        "model_application_object_types",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("public_id", sa.String(length=36), nullable=False),
        sa.Column("model_release_id", sa.Integer(), nullable=False),
        sa.Column("application_key", sa.String(length=160), nullable=False),
        sa.Column("object_type_key", sa.String(length=160), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "model_release_id",
            "application_key",
            "object_type_key",
            name="uq_model_application_object_type",
        ),
    )
    op.create_index(
        op.f("ix_model_application_object_types_application_key"),
        "model_application_object_types",
        ["application_key"],
        unique=False,
    )
    op.create_index(
        op.f("ix_model_application_object_types_model_release_id"),
        "model_application_object_types",
        ["model_release_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_model_application_object_types_object_type_key"),
        "model_application_object_types",
        ["object_type_key"],
        unique=False,
    )
    op.create_index(
        op.f("ix_model_application_object_types_public_id"),
        "model_application_object_types",
        ["public_id"],
        unique=True,
    )
    op.create_table(
        "model_applications",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("public_id", sa.String(length=36), nullable=False),
        sa.Column("model_release_id", sa.Integer(), nullable=False),
        sa.Column("key", sa.String(length=160), nullable=False),
        sa.Column("name", sa.String(length=300), nullable=False),
        sa.Column("definition", sa.JSON(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("model_release_id", "key", name="uq_model_application_key"),
    )
    op.create_index(
        op.f("ix_model_applications_model_release_id"),
        "model_applications",
        ["model_release_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_model_applications_public_id"), "model_applications", ["public_id"], unique=True
    )
    op.create_table(
        "model_attribute_types",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("public_id", sa.String(length=36), nullable=False),
        sa.Column("model_release_id", sa.Integer(), nullable=False),
        sa.Column("key", sa.String(length=160), nullable=False),
        sa.Column("name", sa.String(length=300), nullable=False),
        sa.Column("value_type", sa.String(length=40), nullable=False),
        sa.Column("definition", sa.JSON(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("model_release_id", "key", name="uq_model_attribute_type_key"),
    )
    op.create_index(
        op.f("ix_model_attribute_types_model_release_id"),
        "model_attribute_types",
        ["model_release_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_model_attribute_types_public_id"),
        "model_attribute_types",
        ["public_id"],
        unique=True,
    )
    op.create_table(
        "model_drafts",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("public_id", sa.String(length=36), nullable=False),
        sa.Column("name", sa.String(length=300), nullable=False),
        sa.Column("base_model_release_id", sa.Integer(), nullable=True),
        sa.Column("model_json", sa.JSON(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_model_drafts_base_model_release_id"),
        "model_drafts",
        ["base_model_release_id"],
        unique=False,
    )
    op.create_index(op.f("ix_model_drafts_public_id"), "model_drafts", ["public_id"], unique=True)
    op.create_table(
        "model_object_type_attributes",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("public_id", sa.String(length=36), nullable=False),
        sa.Column("model_release_id", sa.Integer(), nullable=False),
        sa.Column("object_type_key", sa.String(length=160), nullable=False),
        sa.Column("attribute_type_key", sa.String(length=160), nullable=False),
        sa.Column("required", sa.Boolean(), nullable=False),
        sa.Column("read_only", sa.Boolean(), nullable=False),
        sa.Column("display_order", sa.Integer(), nullable=False),
        sa.Column("definition", sa.JSON(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "model_release_id",
            "object_type_key",
            "attribute_type_key",
            name="uq_model_object_type_attribute",
        ),
    )
    op.create_index(
        op.f("ix_model_object_type_attributes_attribute_type_key"),
        "model_object_type_attributes",
        ["attribute_type_key"],
        unique=False,
    )
    op.create_index(
        op.f("ix_model_object_type_attributes_model_release_id"),
        "model_object_type_attributes",
        ["model_release_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_model_object_type_attributes_object_type_key"),
        "model_object_type_attributes",
        ["object_type_key"],
        unique=False,
    )
    op.create_index(
        op.f("ix_model_object_type_attributes_public_id"),
        "model_object_type_attributes",
        ["public_id"],
        unique=True,
    )
    op.create_table(
        "model_object_type_relations",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("public_id", sa.String(length=36), nullable=False),
        sa.Column("model_release_id", sa.Integer(), nullable=False),
        sa.Column("relation_type_key", sa.String(length=160), nullable=False),
        sa.Column("from_object_type_key", sa.String(length=160), nullable=False),
        sa.Column("to_object_type_key", sa.String(length=160), nullable=False),
        sa.Column("cardinality", sa.String(length=40), nullable=False),
        sa.Column("definition", sa.JSON(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "model_release_id",
            "relation_type_key",
            "from_object_type_key",
            "to_object_type_key",
            name="uq_model_object_type_relation",
        ),
    )
    op.create_index(
        op.f("ix_model_object_type_relations_from_object_type_key"),
        "model_object_type_relations",
        ["from_object_type_key"],
        unique=False,
    )
    op.create_index(
        op.f("ix_model_object_type_relations_model_release_id"),
        "model_object_type_relations",
        ["model_release_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_model_object_type_relations_public_id"),
        "model_object_type_relations",
        ["public_id"],
        unique=True,
    )
    op.create_index(
        op.f("ix_model_object_type_relations_relation_type_key"),
        "model_object_type_relations",
        ["relation_type_key"],
        unique=False,
    )
    op.create_index(
        op.f("ix_model_object_type_relations_to_object_type_key"),
        "model_object_type_relations",
        ["to_object_type_key"],
        unique=False,
    )
    op.create_table(
        "model_object_types",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("public_id", sa.String(length=36), nullable=False),
        sa.Column("model_release_id", sa.Integer(), nullable=False),
        sa.Column("key", sa.String(length=160), nullable=False),
        sa.Column("name", sa.String(length=300), nullable=False),
        sa.Column("definition", sa.JSON(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("model_release_id", "key", name="uq_model_object_type_key"),
    )
    op.create_index(
        op.f("ix_model_object_types_model_release_id"),
        "model_object_types",
        ["model_release_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_model_object_types_public_id"), "model_object_types", ["public_id"], unique=True
    )
    op.create_table(
        "model_relation_types",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("public_id", sa.String(length=36), nullable=False),
        sa.Column("model_release_id", sa.Integer(), nullable=False),
        sa.Column("key", sa.String(length=160), nullable=False),
        sa.Column("reverse_key", sa.String(length=160), nullable=False),
        sa.Column("name", sa.String(length=300), nullable=False),
        sa.Column("reverse_name", sa.String(length=300), nullable=False),
        sa.Column("is_oriented", sa.Boolean(), nullable=False),
        sa.Column("definition", sa.JSON(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("model_release_id", "key", name="uq_model_relation_type_key"),
    )
    op.create_index(
        op.f("ix_model_relation_types_model_release_id"),
        "model_relation_types",
        ["model_release_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_model_relation_types_public_id"),
        "model_relation_types",
        ["public_id"],
        unique=True,
    )
    op.create_table(
        "model_runtime_state",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("active_model_release_id", sa.Integer(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("id = 1", name="ck_model_runtime_state_singleton"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_model_runtime_state_active_model_release_id"),
        "model_runtime_state",
        ["active_model_release_id"],
        unique=False,
    )
    op.create_table(
        "model_view_definitions",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("public_id", sa.String(length=36), nullable=False),
        sa.Column("model_release_id", sa.Integer(), nullable=False),
        sa.Column("application_key", sa.String(length=160), nullable=False),
        sa.Column("key", sa.String(length=160), nullable=False),
        sa.Column("name", sa.String(length=300), nullable=False),
        sa.Column("view_type", sa.String(length=60), nullable=False),
        sa.Column("definition", sa.JSON(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("model_release_id", "application_key", "key", name="uq_model_view_key"),
    )
    op.create_index(
        op.f("ix_model_view_definitions_application_key"),
        "model_view_definitions",
        ["application_key"],
        unique=False,
    )
    op.create_index(
        op.f("ix_model_view_definitions_model_release_id"),
        "model_view_definitions",
        ["model_release_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_model_view_definitions_public_id"),
        "model_view_definitions",
        ["public_id"],
        unique=True,
    )
    op.create_table(
        "objects",
        sa.Column("sequence_id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("workspace_key", sa.String(length=160), nullable=False),
        sa.Column("application_key", sa.String(length=160), nullable=False),
        sa.Column("object_type_key", sa.String(length=160), nullable=False),
        sa.Column("parent_object_id", sa.String(length=36), nullable=True),
        sa.Column("name", sa.String(length=500), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("sequence_id"),
    )
    op.create_index(
        op.f("ix_objects_application_key"), "objects", ["application_key"], unique=False
    )
    op.create_index(op.f("ix_objects_id"), "objects", ["id"], unique=True)
    op.create_index(op.f("ix_objects_name"), "objects", ["name"], unique=False)
    op.create_index(
        op.f("ix_objects_object_type_key"), "objects", ["object_type_key"], unique=False
    )
    op.create_index(
        "ix_objects_parent_name",
        "objects",
        ["workspace_key", "parent_object_id", "object_type_key", "name", "sequence_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_objects_parent_object_id"), "objects", ["parent_object_id"], unique=False
    )
    op.create_index(
        "ix_objects_type_name",
        "objects",
        ["workspace_key", "object_type_key", "name", "sequence_id"],
        unique=False,
    )
    op.create_index(op.f("ix_objects_workspace_key"), "objects", ["workspace_key"], unique=False)
    op.create_table(
        "publications",
        sa.Column("sequence_id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("workspace_key", sa.String(length=160), nullable=False),
        sa.Column("model_release_id", sa.Integer(), nullable=False),
        sa.Column("publication_number", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("derived_from_publication_id", sa.String(length=36), nullable=True),
        sa.Column("supersedes_publication_id", sa.String(length=36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("withdrawn_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("status IN ('active', 'withdrawn')", name="ck_publication_status"),
        sa.PrimaryKeyConstraint("sequence_id"),
        sa.UniqueConstraint("workspace_key", "publication_number", name="uq_publication_number"),
    )
    op.create_index(
        op.f("ix_publications_derived_from_publication_id"),
        "publications",
        ["derived_from_publication_id"],
        unique=False,
    )
    op.create_index(op.f("ix_publications_id"), "publications", ["id"], unique=True)
    op.create_index(
        op.f("ix_publications_model_release_id"), "publications", ["model_release_id"], unique=False
    )
    op.create_index(op.f("ix_publications_status"), "publications", ["status"], unique=False)
    op.create_index(
        op.f("ix_publications_supersedes_publication_id"),
        "publications",
        ["supersedes_publication_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_publications_workspace_key"), "publications", ["workspace_key"], unique=False
    )
    op.create_table(
        "workspace_runtime_state",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("default_workspace_key", sa.String(length=160), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("id = 1", name="ck_workspace_runtime_state_singleton"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "attribute_values",
        sa.Column("sequence_id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("object_id", sa.String(length=36), nullable=False),
        sa.Column("attribute_type_key", sa.String(length=160), nullable=False),
        sa.Column("value_type", sa.String(length=40), nullable=False),
        sa.Column("text_value", sa.Text(), nullable=True),
        sa.Column("integer_value", sa.Integer(), nullable=True),
        sa.Column("decimal_value", sa.Numeric(), nullable=True),
        sa.Column("boolean_value", sa.Boolean(), nullable=True),
        sa.Column("date_value", sa.Date(), nullable=True),
        sa.Column("datetime_value", sa.DateTime(timezone=True), nullable=True),
        sa.Column("json_value", sa.JSON(), nullable=True),
        sa.Column("value_source", sa.String(length=40), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("sequence_id"),
        sa.UniqueConstraint("id"),
        sa.UniqueConstraint("object_id", "attribute_type_key", name="uq_object_attribute_value"),
    )
    op.create_index(
        op.f("ix_attribute_values_attribute_type_key"),
        "attribute_values",
        ["attribute_type_key"],
        unique=False,
    )
    op.create_index(
        "ix_attribute_values_key_text",
        "attribute_values",
        ["attribute_type_key", "text_value", "object_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_attribute_values_object_id"), "attribute_values", ["object_id"], unique=False
    )
    op.create_table(
        "change_set_base_objects",
        sa.Column("sequence_id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("base_id", sa.String(length=36), nullable=False),
        sa.Column("object_id", sa.String(length=36), nullable=False),
        sa.Column("application_key", sa.String(length=160), nullable=False),
        sa.Column("object_type_key", sa.String(length=160), nullable=False),
        sa.Column("name", sa.String(length=500), nullable=False),
        sa.Column("parent_object_id", sa.String(length=36), nullable=True),
        sa.Column("attributes", sa.JSON(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("sequence_id"),
        sa.UniqueConstraint("base_id", "object_id", name="uq_change_set_base_object"),
    )
    op.create_index(
        op.f("ix_change_set_base_objects_base_id"),
        "change_set_base_objects",
        ["base_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_change_set_base_objects_object_id"),
        "change_set_base_objects",
        ["object_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_change_set_base_objects_object_type_key"),
        "change_set_base_objects",
        ["object_type_key"],
        unique=False,
    )
    op.create_index(
        "ix_change_set_base_objects_parent_name",
        "change_set_base_objects",
        ["base_id", "parent_object_id", "object_type_key", "name", "object_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_change_set_base_objects_parent_object_id"),
        "change_set_base_objects",
        ["parent_object_id"],
        unique=False,
    )
    op.create_index(
        "ix_change_set_base_objects_type_name",
        "change_set_base_objects",
        ["base_id", "object_type_key", "name", "object_id"],
        unique=False,
    )
    op.create_table(
        "change_set_base_relations",
        sa.Column("sequence_id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("base_id", sa.String(length=36), nullable=False),
        sa.Column("relation_id", sa.String(length=36), nullable=False),
        sa.Column("relation_type_key", sa.String(length=160), nullable=False),
        sa.Column("from_object_id", sa.String(length=36), nullable=False),
        sa.Column("to_object_id", sa.String(length=36), nullable=False),
        sa.Column("attributes", sa.JSON(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("sequence_id"),
        sa.UniqueConstraint("base_id", "relation_id", name="uq_change_set_base_relation"),
    )
    op.create_index(
        op.f("ix_change_set_base_relations_base_id"),
        "change_set_base_relations",
        ["base_id"],
        unique=False,
    )
    op.create_index(
        "ix_change_set_base_relations_from",
        "change_set_base_relations",
        ["base_id", "from_object_id", "relation_type_key", "relation_id", "to_object_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_change_set_base_relations_from_object_id"),
        "change_set_base_relations",
        ["from_object_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_change_set_base_relations_relation_id"),
        "change_set_base_relations",
        ["relation_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_change_set_base_relations_relation_type_key"),
        "change_set_base_relations",
        ["relation_type_key"],
        unique=False,
    )
    op.create_index(
        "ix_change_set_base_relations_to",
        "change_set_base_relations",
        ["base_id", "to_object_id", "relation_type_key", "relation_id", "from_object_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_change_set_base_relations_to_object_id"),
        "change_set_base_relations",
        ["to_object_id"],
        unique=False,
    )
    op.create_table(
        "change_sets",
        sa.Column("sequence_id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("workspace_key", sa.String(length=160), nullable=False),
        sa.Column("model_release_id", sa.Integer(), nullable=False),
        sa.Column("derived_from_publication_id", sa.String(length=36), nullable=True),
        sa.Column("base_id", sa.String(length=36), nullable=True),
        sa.Column("name", sa.String(length=300), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("sequence_id"),
    )
    op.create_index(op.f("ix_change_sets_base_id"), "change_sets", ["base_id"], unique=False)
    op.create_index(
        op.f("ix_change_sets_derived_from_publication_id"),
        "change_sets",
        ["derived_from_publication_id"],
        unique=False,
    )
    op.create_index(op.f("ix_change_sets_id"), "change_sets", ["id"], unique=True)
    op.create_index(
        op.f("ix_change_sets_model_release_id"), "change_sets", ["model_release_id"], unique=False
    )
    op.create_index(
        op.f("ix_change_sets_workspace_key"), "change_sets", ["workspace_key"], unique=False
    )
    op.create_table(
        "idempotency_keys",
        sa.Column("sequence_id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("scope", sa.String(length=80), nullable=False),
        sa.Column("workspace_key", sa.String(length=160), nullable=False),
        sa.Column("key", sa.String(length=200), nullable=False),
        sa.Column("fingerprint", sa.String(length=64), nullable=False),
        sa.Column("job_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("sequence_id"),
        sa.UniqueConstraint("scope", "workspace_key", "key", name="uq_idempotency_key"),
    )
    op.create_index(
        op.f("ix_idempotency_keys_job_id"), "idempotency_keys", ["job_id"], unique=False
    )
    op.create_table(
        "job_inputs",
        sa.Column("sequence_id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("job_id", sa.Integer(), nullable=False),
        sa.Column("item_index", sa.Integer(), nullable=False),
        sa.Column("ref", sa.String(length=200), nullable=True),
        sa.Column("item", sa.JSON(), nullable=False),
        sa.PrimaryKeyConstraint("sequence_id"),
        sa.UniqueConstraint("job_id", "item_index", name="uq_job_input"),
    )
    op.create_table(
        "job_items",
        sa.Column("sequence_id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("job_id", sa.Integer(), nullable=False),
        sa.Column("item_index", sa.Integer(), nullable=False),
        sa.Column("ref", sa.String(length=200), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("outcome", sa.JSON(), nullable=False),
        sa.CheckConstraint(
            "status IN ('applied', 'rejected', 'unprocessed')", name="ck_job_item_status"
        ),
        sa.PrimaryKeyConstraint("sequence_id"),
        sa.UniqueConstraint("job_id", "item_index", name="uq_job_item"),
    )
    op.create_index(
        "ix_job_items_status", "job_items", ["job_id", "status", "item_index"], unique=False
    )
    op.create_table(
        "object_relations",
        sa.Column("sequence_id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("relation_type_key", sa.String(length=160), nullable=False),
        sa.Column("from_object_id", sa.String(length=36), nullable=False),
        sa.Column("to_object_id", sa.String(length=36), nullable=False),
        sa.Column("attributes", sa.JSON(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("sequence_id"),
        sa.UniqueConstraint("id"),
        sa.UniqueConstraint(
            "relation_type_key", "from_object_id", "to_object_id", name="uq_object_relation"
        ),
    )
    op.create_index(
        op.f("ix_object_relations_from_object_id"),
        "object_relations",
        ["from_object_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_object_relations_relation_type_key"),
        "object_relations",
        ["relation_type_key"],
        unique=False,
    )
    op.create_index(
        op.f("ix_object_relations_to_object_id"), "object_relations", ["to_object_id"], unique=False
    )
    op.create_table(
        "publication_objects",
        sa.Column("sequence_id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("publication_id", sa.String(length=36), nullable=False),
        sa.Column("object_id", sa.String(length=36), nullable=False),
        sa.Column("application_key", sa.String(length=160), nullable=False),
        sa.Column("object_type_key", sa.String(length=160), nullable=False),
        sa.Column("name", sa.String(length=500), nullable=False),
        sa.Column("parent_object_id", sa.String(length=36), nullable=True),
        sa.Column("attributes", sa.JSON(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("sequence_id"),
        sa.UniqueConstraint("publication_id", "object_id", name="uq_publication_object"),
    )
    op.create_index(
        op.f("ix_publication_objects_object_id"), "publication_objects", ["object_id"], unique=False
    )
    op.create_index(
        "ix_publication_objects_parent_name",
        "publication_objects",
        ["publication_id", "parent_object_id", "object_type_key", "name", "object_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_publication_objects_publication_id"),
        "publication_objects",
        ["publication_id"],
        unique=False,
    )
    op.create_index(
        "ix_publication_objects_type_name",
        "publication_objects",
        ["publication_id", "object_type_key", "name", "object_id"],
        unique=False,
    )
    op.create_table(
        "publication_relations",
        sa.Column("sequence_id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("publication_id", sa.String(length=36), nullable=False),
        sa.Column("relation_id", sa.String(length=36), nullable=False),
        sa.Column("relation_type_key", sa.String(length=160), nullable=False),
        sa.Column("from_object_id", sa.String(length=36), nullable=False),
        sa.Column("to_object_id", sa.String(length=36), nullable=False),
        sa.Column("attributes", sa.JSON(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("sequence_id"),
        sa.UniqueConstraint("publication_id", "relation_id", name="uq_publication_relation"),
    )
    op.create_index(
        "ix_publication_relations_from",
        "publication_relations",
        ["publication_id", "from_object_id", "relation_type_key", "relation_id", "to_object_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_publication_relations_publication_id"),
        "publication_relations",
        ["publication_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_publication_relations_relation_id"),
        "publication_relations",
        ["relation_id"],
        unique=False,
    )
    op.create_index(
        "ix_publication_relations_to",
        "publication_relations",
        ["publication_id", "to_object_id", "relation_type_key", "relation_id", "from_object_id"],
        unique=False,
    )
    op.create_table(
        "change_set_objects",
        sa.Column("sequence_id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("change_set_id", sa.String(length=36), nullable=False),
        sa.Column("object_id", sa.String(length=36), nullable=False),
        sa.Column("application_key", sa.String(length=160), nullable=False),
        sa.Column("object_type_key", sa.String(length=160), nullable=False),
        sa.Column("name", sa.String(length=500), nullable=False),
        sa.Column("parent_object_id", sa.String(length=36), nullable=True),
        sa.Column("attributes", sa.JSON(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("is_deleted", sa.Boolean(), nullable=False),
        sa.PrimaryKeyConstraint("sequence_id"),
        sa.UniqueConstraint("change_set_id", "object_id", name="uq_change_set_object"),
    )
    op.create_index(
        op.f("ix_change_set_objects_change_set_id"),
        "change_set_objects",
        ["change_set_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_change_set_objects_object_id"), "change_set_objects", ["object_id"], unique=False
    )
    op.create_index(
        "ix_change_set_objects_parent_name",
        "change_set_objects",
        ["change_set_id", "parent_object_id", "object_type_key", "name", "object_id"],
        unique=False,
    )
    op.create_index(
        "ix_change_set_objects_type_name",
        "change_set_objects",
        ["change_set_id", "object_type_key", "name", "object_id"],
        unique=False,
    )
    op.create_table(
        "change_set_relations",
        sa.Column("sequence_id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("change_set_id", sa.String(length=36), nullable=False),
        sa.Column("relation_id", sa.String(length=36), nullable=False),
        sa.Column("relation_type_key", sa.String(length=160), nullable=False),
        sa.Column("from_object_id", sa.String(length=36), nullable=False),
        sa.Column("to_object_id", sa.String(length=36), nullable=False),
        sa.Column("attributes", sa.JSON(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("is_deleted", sa.Boolean(), nullable=False),
        sa.PrimaryKeyConstraint("sequence_id"),
        sa.UniqueConstraint("change_set_id", "relation_id", name="uq_change_set_relation"),
    )
    op.create_index(
        op.f("ix_change_set_relations_change_set_id"),
        "change_set_relations",
        ["change_set_id"],
        unique=False,
    )
    op.create_index(
        "ix_change_set_relations_from",
        "change_set_relations",
        ["change_set_id", "from_object_id", "relation_type_key", "relation_id", "to_object_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_change_set_relations_relation_id"),
        "change_set_relations",
        ["relation_id"],
        unique=False,
    )
    op.create_index(
        "ix_change_set_relations_to",
        "change_set_relations",
        ["change_set_id", "to_object_id", "relation_type_key", "relation_id", "from_object_id"],
        unique=False,
    )
    op.create_table(
        "relation_set_versions",
        sa.Column("sequence_id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("workspace_key", sa.String(length=160), nullable=False),
        sa.Column("change_set_id", sa.String(length=36), nullable=True),
        sa.Column("relation_type_key", sa.String(length=160), nullable=False),
        sa.Column("from_object_type_key", sa.String(length=160), nullable=False),
        sa.Column("to_object_type_key", sa.String(length=160), nullable=False),
        sa.Column("anchor_object_id", sa.String(length=36), nullable=False),
        sa.Column("direction", sa.String(length=10), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("direction IN ('outgoing', 'incoming')", name="ck_rsv_direction"),
        sa.PrimaryKeyConstraint("sequence_id"),
        sa.UniqueConstraint(
            "workspace_key",
            "change_set_id",
            "relation_type_key",
            "from_object_type_key",
            "to_object_type_key",
            "anchor_object_id",
            "direction",
            name="uq_relation_set_version",
        ),
    )
    op.create_index(
        op.f("ix_relation_set_versions_anchor_object_id"),
        "relation_set_versions",
        ["anchor_object_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_relation_set_versions_change_set_id"),
        "relation_set_versions",
        ["change_set_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_relation_set_versions_workspace_key"),
        "relation_set_versions",
        ["workspace_key"],
        unique=False,
    )
    op.create_index(
        "uq_relation_set_version_live",
        "relation_set_versions",
        [
            "workspace_key",
            "relation_type_key",
            "from_object_type_key",
            "to_object_type_key",
            "anchor_object_id",
            "direction",
        ],
        unique=True,
        postgresql_where=sa.text("change_set_id IS NULL"),
    )
    # Foreign keys last: several reference a column that a unique index, created after its
    # table, makes unique, and workspaces and publications reference each other.
    op.create_foreign_key(
        "fk_workspaces_active_publication_id_publications",
        "workspaces",
        "publications",
        ["active_publication_id"],
        ["id"],
        ondelete="RESTRICT",
        use_alter=True,
    )
    op.create_foreign_key(
        "audit_event_subjects_audit_event_id_fkey",
        "audit_event_subjects",
        "audit_events",
        ["audit_event_id"],
        ["sequence_id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "change_set_bases_model_release_id_fkey",
        "change_set_bases",
        "model_releases",
        ["model_release_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_foreign_key(
        "change_set_bases_workspace_key_fkey",
        "change_set_bases",
        "workspaces",
        ["workspace_key"],
        ["key"],
        ondelete="RESTRICT",
    )
    op.create_foreign_key(
        "jobs_model_release_id_fkey",
        "jobs",
        "model_releases",
        ["model_release_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_foreign_key(
        "model_application_object_types_model_release_id_fkey",
        "model_application_object_types",
        "model_releases",
        ["model_release_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "model_applications_model_release_id_fkey",
        "model_applications",
        "model_releases",
        ["model_release_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "model_attribute_types_model_release_id_fkey",
        "model_attribute_types",
        "model_releases",
        ["model_release_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "model_drafts_base_model_release_id_fkey",
        "model_drafts",
        "model_releases",
        ["base_model_release_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "model_object_type_attributes_model_release_id_fkey",
        "model_object_type_attributes",
        "model_releases",
        ["model_release_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "model_object_type_relations_model_release_id_fkey",
        "model_object_type_relations",
        "model_releases",
        ["model_release_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "model_object_types_model_release_id_fkey",
        "model_object_types",
        "model_releases",
        ["model_release_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "model_relation_types_model_release_id_fkey",
        "model_relation_types",
        "model_releases",
        ["model_release_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "model_runtime_state_active_model_release_id_fkey",
        "model_runtime_state",
        "model_releases",
        ["active_model_release_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_foreign_key(
        "model_view_definitions_model_release_id_fkey",
        "model_view_definitions",
        "model_releases",
        ["model_release_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "objects_parent_object_id_fkey",
        "objects",
        "objects",
        ["parent_object_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_foreign_key(
        "objects_workspace_key_fkey",
        "objects",
        "workspaces",
        ["workspace_key"],
        ["key"],
        ondelete="RESTRICT",
    )
    op.create_foreign_key(
        "publications_derived_from_publication_id_fkey",
        "publications",
        "publications",
        ["derived_from_publication_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_foreign_key(
        "publications_model_release_id_fkey",
        "publications",
        "model_releases",
        ["model_release_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_foreign_key(
        "publications_supersedes_publication_id_fkey",
        "publications",
        "publications",
        ["supersedes_publication_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_foreign_key(
        "publications_workspace_key_fkey",
        "publications",
        "workspaces",
        ["workspace_key"],
        ["key"],
        ondelete="RESTRICT",
    )
    op.create_foreign_key(
        "workspace_runtime_state_default_workspace_key_fkey",
        "workspace_runtime_state",
        "workspaces",
        ["default_workspace_key"],
        ["key"],
        ondelete="RESTRICT",
    )
    op.create_foreign_key(
        "attribute_values_object_id_fkey",
        "attribute_values",
        "objects",
        ["object_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "change_set_base_objects_base_id_fkey",
        "change_set_base_objects",
        "change_set_bases",
        ["base_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "change_set_base_relations_base_id_fkey",
        "change_set_base_relations",
        "change_set_bases",
        ["base_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "change_sets_base_id_fkey",
        "change_sets",
        "change_set_bases",
        ["base_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_foreign_key(
        "change_sets_derived_from_publication_id_fkey",
        "change_sets",
        "publications",
        ["derived_from_publication_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_foreign_key(
        "change_sets_model_release_id_fkey",
        "change_sets",
        "model_releases",
        ["model_release_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_foreign_key(
        "change_sets_workspace_key_fkey",
        "change_sets",
        "workspaces",
        ["workspace_key"],
        ["key"],
        ondelete="RESTRICT",
    )
    op.create_foreign_key(
        "idempotency_keys_job_id_fkey",
        "idempotency_keys",
        "jobs",
        ["job_id"],
        ["sequence_id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "job_inputs_job_id_fkey",
        "job_inputs",
        "jobs",
        ["job_id"],
        ["sequence_id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "job_items_job_id_fkey",
        "job_items",
        "jobs",
        ["job_id"],
        ["sequence_id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "object_relations_from_object_id_fkey",
        "object_relations",
        "objects",
        ["from_object_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "object_relations_to_object_id_fkey",
        "object_relations",
        "objects",
        ["to_object_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "publication_objects_publication_id_fkey",
        "publication_objects",
        "publications",
        ["publication_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "publication_relations_publication_id_fkey",
        "publication_relations",
        "publications",
        ["publication_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "change_set_objects_change_set_id_fkey",
        "change_set_objects",
        "change_sets",
        ["change_set_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "change_set_relations_change_set_id_fkey",
        "change_set_relations",
        "change_sets",
        ["change_set_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "relation_set_versions_change_set_id_fkey",
        "relation_set_versions",
        "change_sets",
        ["change_set_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "relation_set_versions_workspace_key_fkey",
        "relation_set_versions",
        "workspaces",
        ["workspace_key"],
        ["key"],
        ondelete="CASCADE",
    )

    # The default workspace and the runtime state naming it, as the SQLite history created them.
    now = datetime.now(UTC)
    op.execute(
        sa.text(
            "INSERT INTO workspaces (key, label, status, version, created_at, updated_at) "
            "VALUES ('default', 'Default', 'active', 1, :now, :now)"
        ).bindparams(now=now)
    )
    op.execute(
        sa.text(
            "INSERT INTO workspace_runtime_state (id, default_workspace_key, version, updated_at) "
            "VALUES (1, 'default', 1, :now)"
        ).bindparams(now=now)
    )


def downgrade() -> None:
    raise NotImplementedError(
        "The baseline revision cannot be downgraded; restore a backup instead"
    )
