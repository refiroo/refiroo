"""A words task's title (Product 0.13 TN).

The task's own session states a short title with its first answer; the engine stores it on the task.
``title`` is null until the session has written one. One transaction: an interrupted run leaves
the database at ``20261124_01``.
"""

import sqlalchemy as sa
from alembic import op

revision = "20261125_01"
down_revision = "20261124_01"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("ai_tasks", sa.Column("title", sa.String(length=120), nullable=True))


def downgrade() -> None:
    op.drop_column("ai_tasks", "title")
