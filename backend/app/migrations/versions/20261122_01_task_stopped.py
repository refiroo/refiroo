"""A task the person stopped before any proposal exists is ``stopped`` (Product 0.16 AP13, AP-D55).

The state check of ``ai_tasks`` gains one value. One constraint swapped in one transaction: an
interrupted run leaves the database at ``20261121_01``.
"""

from alembic import op

revision = "20261122_01"
down_revision = "20261121_01"
branch_labels = None
depends_on = None

_BEFORE = "state IN ('reading', 'read', 'checking', 'checked', 'loading', 'loaded', 'failed', 'cancelled')"
_AFTER = (
    "state IN ('reading', 'read', 'checking', 'checked', 'loading', 'loaded', 'failed', "
    "'cancelled', 'stopped')"
)


def upgrade() -> None:
    op.drop_constraint("ck_ai_tasks_state", "ai_tasks", type_="check")
    op.create_check_constraint("ck_ai_tasks_state", "ai_tasks", _AFTER)


def downgrade() -> None:
    op.execute("UPDATE ai_tasks SET state = 'cancelled' WHERE state = 'stopped'")
    op.drop_constraint("ck_ai_tasks_state", "ai_tasks", type_="check")
    op.create_check_constraint("ck_ai_tasks_state", "ai_tasks", _BEFORE)
