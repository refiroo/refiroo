"""Persist private immutable current-live bases for workspace drafts.

Existing drafts deliberately retain nullable ``base_id`` and their established empty/revision source;
this additive revision neither recreates identities nor rebases historical content.
"""

import sqlalchemy as sa
from alembic import op

revision = "20260909_01"
down_revision = "20260908_01"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "workspace_draft_bases",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("workspace_key", sa.String(length=160), nullable=False),
        sa.Column("model_release_id", sa.Integer(), nullable=False),
        sa.Column("model_runtime_version", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["workspace_key"], ["workspaces.key"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["model_release_id"], ["model_releases.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_workspace_draft_bases_workspace_key", "workspace_draft_bases", ["workspace_key"]
    )
    op.create_index(
        "ix_workspace_draft_bases_model_release_id", "workspace_draft_bases", ["model_release_id"]
    )
    op.create_table(
        "workspace_draft_base_objects",
        sa.Column("sequence_id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("base_id", sa.String(length=36), nullable=False),
        sa.Column("object_id", sa.String(length=36), nullable=False),
        sa.Column("application_key", sa.String(length=160), nullable=False),
        sa.Column("object_type_key", sa.String(length=160), nullable=False),
        sa.Column("name", sa.String(length=500), nullable=False),
        sa.Column("parent_object_id", sa.String(length=36), nullable=True),
        sa.Column("attributes", sa.JSON(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["base_id"], ["workspace_draft_bases.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("sequence_id"),
        sa.UniqueConstraint("base_id", "object_id", name="uq_workspace_draft_base_object"),
    )
    for column in ("base_id", "object_id", "object_type_key", "parent_object_id"):
        op.create_index(
            f"ix_workspace_draft_base_objects_{column}", "workspace_draft_base_objects", [column]
        )
    op.create_table(
        "workspace_draft_base_relations",
        sa.Column("sequence_id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("base_id", sa.String(length=36), nullable=False),
        sa.Column("relation_id", sa.String(length=36), nullable=False),
        sa.Column("relation_type_key", sa.String(length=160), nullable=False),
        sa.Column("from_object_id", sa.String(length=36), nullable=False),
        sa.Column("to_object_id", sa.String(length=36), nullable=False),
        sa.Column("attributes", sa.JSON(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["base_id"], ["workspace_draft_bases.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("sequence_id"),
        sa.UniqueConstraint("base_id", "relation_id", name="uq_workspace_draft_base_relation"),
    )
    for column in ("base_id", "relation_id", "relation_type_key", "from_object_id", "to_object_id"):
        op.create_index(
            f"ix_workspace_draft_base_relations_{column}",
            "workspace_draft_base_relations",
            [column],
        )
    with op.batch_alter_table("workspace_drafts") as batch_op:
        batch_op.add_column(sa.Column("base_id", sa.String(length=36), nullable=True))
        batch_op.create_foreign_key(
            "fk_workspace_drafts_base_id_workspace_draft_bases",
            "workspace_draft_bases",
            ["base_id"],
            ["id"],
            ondelete="RESTRICT",
        )
        batch_op.create_index("ix_workspace_drafts_base_id", ["base_id"])


def downgrade() -> None:
    with op.batch_alter_table("workspace_drafts") as batch_op:
        batch_op.drop_index("ix_workspace_drafts_base_id")
        batch_op.drop_constraint(
            "fk_workspace_drafts_base_id_workspace_draft_bases", type_="foreignkey"
        )
        batch_op.drop_column("base_id")
    op.drop_table("workspace_draft_base_relations")
    op.drop_table("workspace_draft_base_objects")
    op.drop_table("workspace_draft_bases")
