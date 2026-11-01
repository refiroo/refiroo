"""Through which channel a change was made (0.16 AG3, AG-D30): ``mcp`` for an assistant's, else none."""

import sqlalchemy as sa
from alembic import op

revision = "20261120_04"
down_revision = "20261120_03"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("audit_events", sa.Column("channel", sa.String(20), nullable=True))


def downgrade() -> None:
    op.drop_column("audit_events", "channel")
