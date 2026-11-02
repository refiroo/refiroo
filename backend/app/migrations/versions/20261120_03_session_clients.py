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
    # Only the client the engine made for all sessions: an API client of that name that never
    # authenticated with a secret and holds no grant but the engine's own roles. One an integrator
    # made and uses (last_used_at is set when it signs in) or granted otherwise stays as it is.
    op.execute(
        "UPDATE oauth_clients SET active = false WHERE name = 'AI assistant' AND kind = 'api' "
        "AND last_used_at IS NULL AND NOT EXISTS (SELECT 1 FROM grants g "
        "LEFT JOIN roles r ON r.id = g.role_id WHERE g.client_id = oauth_clients.id "
        "AND (r.id IS NULL OR r.name NOT LIKE 'AI assistant:%'))"
    )


def downgrade() -> None:
    # The session clients become inactive API clients, as the old check allows only api and agent.
    op.execute("UPDATE oauth_clients SET kind = 'api', active = false WHERE kind = 'session'")
    op.drop_column("ai_calls", "task_id")
    op.drop_column("ai_calls", "cost_usd")
    op.drop_index("uq_ai_tasks_client", table_name="ai_tasks")
    op.drop_constraint("fk_ai_tasks_client_id_oauth_clients", "ai_tasks", type_="foreignkey")
    op.drop_column("ai_tasks", "client_id")
    op.drop_constraint("ck_oauth_clients_kind", "oauth_clients", type_="check")
    op.create_check_constraint("ck_oauth_clients_kind", "oauth_clients", "kind IN ('api', 'agent')")
