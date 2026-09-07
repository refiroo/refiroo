"""Add optional human name to workspace drafts."""

import sqlalchemy as sa
from alembic import op

revision = "20260907_02"
down_revision = "20260907_01"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("workspace_drafts", sa.Column("name", sa.String(length=300), nullable=True))


def downgrade() -> None:
    op.drop_column("workspace_drafts", "name")
