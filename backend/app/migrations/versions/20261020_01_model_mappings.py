"""The mapping between two models (Product 0.11 X1, D104–D113).

``model_mappings`` holds each saved mapping: its key, its two models, the two releases it is checked
against and its definition; ``model_mapping_operations`` its history, as ``model_draft_operations``
holds a draft's (D105); ``model_mapping_proposals`` the proposals of its latest inference, deleted
with it. ``jobs.kind`` gains ``mappingInference``, and ``jobs`` an index of the jobs a mapping has
(``parameters ->> 'mappingKey'``), as R-F14's of a draft's. PostgreSQL runs the DDL in the migration's
transaction, so an interrupted run leaves the database at ``20261019_01``.
"""

import sqlalchemy as sa
from alembic import op

revision = "20261020_01"
down_revision = "20261019_01"
branch_labels = None
depends_on = None

KINDS = (
    "kind IN ('batch', 'import', 'export', 'profile', 'dryRun', 'inference', 'profileCheck', "
    "'migration', 'mappingInference')"
)
OLD_KINDS = (
    "kind IN ('batch', 'import', 'export', 'profile', 'dryRun', 'inference', 'profileCheck', "
    "'migration')"
)


def upgrade() -> None:
    op.create_table(
        "model_mappings",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("key", sa.String(160), nullable=False, unique=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("source_model_key", sa.String(160), nullable=False),
        sa.Column("target_model_key", sa.String(160), nullable=False),
        sa.Column(
            "source_release_id",
            sa.Integer(),
            sa.ForeignKey("model_releases.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "target_release_id",
            sa.Integer(),
            sa.ForeignKey("model_releases.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("definition", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_model_mappings_models", "model_mappings", ["source_model_key", "target_model_key", "key"]
    )
    op.create_index("ix_model_mappings_source_release_id", "model_mappings", ["source_release_id"])
    op.create_index("ix_model_mappings_target_release_id", "model_mappings", ["target_release_id"])
    op.create_table(
        "model_mapping_operations",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "mapping_id",
            sa.Integer(),
            sa.ForeignKey("model_mappings.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("step", sa.Integer(), nullable=False),
        sa.Column("kind", sa.String(60), nullable=False),
        sa.Column("parameters", sa.JSON(), nullable=False),
        sa.Column("inverse", sa.JSON(), nullable=False),
        sa.Column("mapping_version", sa.Integer(), nullable=False),
        sa.Column("author", sa.String(300), nullable=True),
        sa.Column("origin", sa.JSON(), nullable=False),
        sa.Column("effects", sa.JSON(), nullable=False),
        sa.Column("undone_by_step", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("mapping_id", "sequence", name="uq_model_mapping_operations_sequence"),
    )
    op.create_index(
        "ix_model_mapping_operations_step", "model_mapping_operations", ["mapping_id", "step"]
    )
    op.create_table(
        "model_mapping_proposals",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("public_id", sa.String(36), nullable=False),
        sa.Column(
            "mapping_id",
            sa.Integer(),
            sa.ForeignKey("model_mappings.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("inference_id", sa.String(36), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("kind", sa.String(20), nullable=False),
        sa.Column("signature", sa.Text(), nullable=False),
        sa.Column("body", sa.JSON(), nullable=False),
    )
    op.create_index(
        "ix_model_mapping_proposals_public_id",
        "model_mapping_proposals",
        ["public_id"],
        unique=True,
    )
    op.create_index(
        "ix_model_mapping_proposals_mapping", "model_mapping_proposals", ["mapping_id", "position"]
    )
    op.drop_constraint("ck_job_kind", "jobs", type_="check")
    op.create_check_constraint("ck_job_kind", "jobs", KINDS)
    op.execute(
        "CREATE INDEX ix_jobs_mapping ON jobs ((parameters ->> 'mappingKey'), sequence_id) "
        "WHERE (parameters ->> 'mappingKey') IS NOT NULL"
    )


def downgrade() -> None:
    op.drop_index("ix_jobs_mapping", table_name="jobs")
    op.execute("DELETE FROM jobs WHERE kind = 'mappingInference'")
    op.drop_constraint("ck_job_kind", "jobs", type_="check")
    op.create_check_constraint("ck_job_kind", "jobs", OLD_KINDS)
    op.drop_table("model_mapping_proposals")
    op.drop_table("model_mapping_operations")
    op.drop_table("model_mappings")
