"""The workspace a model draft remembers (0.16 WM1, WM-D1): at most one draft per workspace."""

import sqlalchemy as sa
from alembic import op

revision = "20261120_02"
down_revision = "20261120_01"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("model_drafts", sa.Column("workspace_key", sa.String(160), nullable=True))
    op.create_foreign_key(
        "fk_model_drafts_workspace_key_workspaces",
        "model_drafts",
        "workspaces",
        ["workspace_key"],
        ["key"],
        ondelete="SET NULL",
    )
    op.create_index(
        "uq_model_drafts_workspace",
        "model_drafts",
        ["workspace_key"],
        unique=True,
        postgresql_where=sa.text("workspace_key IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index("uq_model_drafts_workspace", table_name="model_drafts")
    op.drop_constraint(
        "fk_model_drafts_workspace_key_workspaces", "model_drafts", type_="foreignkey"
    )
    op.drop_column("model_drafts", "workspace_key")
