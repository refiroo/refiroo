"""Who did it (0.16 AP9): a client of its own per assistant task, and a session's turns on record.

A task's session works as a client of the new kind ``session``, named on ``ai_tasks.client_id``; the
client all sessions shared goes inactive and stays, as audit entries name it. ``ai_calls`` gains
what a turn cost and the task it belongs to.
"""

import sqlalchemy as sa
from alembic import op

revision = "20261120_03"
down_revision = "20261120_02"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_constraint("ck_oauth_clients_kind", "oauth_clients", type_="check")
    op.create_check_constraint(
        "ck_oauth_clients_kind", "oauth_clients", "kind IN ('api', 'agent', 'session')"
    )
    op.add_column("ai_tasks", sa.Column("client_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "fk_ai_tasks_client_id_oauth_clients",
        "ai_tasks",
        "oauth_clients",
        ["client_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "uq_ai_tasks_client",
        "ai_tasks",
        ["client_id"],
        unique=True,
        postgresql_where=sa.text("client_id IS NOT NULL"),
    )
    op.add_column("ai_calls", sa.Column("cost_usd", sa.Numeric(12, 4), nullable=True))
    op.add_column("ai_calls", sa.Column("task_id", sa.String(36), nullable=True))
    op.execute("UPDATE oauth_clients SET active = false WHERE name = 'AI assistant'")


def downgrade() -> None:
    op.drop_column("ai_calls", "task_id")
    op.drop_column("ai_calls", "cost_usd")
    op.drop_index("uq_ai_tasks_client", table_name="ai_tasks")
    op.drop_constraint("fk_ai_tasks_client_id_oauth_clients", "ai_tasks", type_="foreignkey")
    op.drop_column("ai_tasks", "client_id")
    op.drop_constraint("ck_oauth_clients_kind", "oauth_clients", type_="check")
    op.create_check_constraint(
        "ck_oauth_clients_kind", "oauth_clients", "kind IN ('api', 'agent')"
    )
