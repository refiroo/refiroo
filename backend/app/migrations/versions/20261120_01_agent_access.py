"""Agent access (0.16 AG1): the assistants people sign in with, each call, an agent client, the role.

``agent_applications`` holds an assistant that registered itself or that an administrator registered
(AG-D12); a person's session started for one issues only ``agent`` tokens. ``agent_calls`` is one row
per tool call, with argument names and never their values, and removed after ``MCP_CALLS_DAYS``
(AG-D16). ``oauth_clients.kind`` keeps an agent client from ever holding another token (AG-D14).
"""

import sqlalchemy as sa
from alembic import op

revision = "20261120_01"
down_revision = "20261119_04"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "agent_applications",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("public_id", sa.String(36), nullable=False, unique=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("redirect_uris", sa.JSON(), nullable=False),
        sa.Column("source", sa.String(16), nullable=False),
        sa.Column("blocked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "source IN ('registered', 'administrator')", name="ck_agent_applications_source"
        ),
    )
    op.create_index("ix_agent_applications_order", "agent_applications", ["id"])
    op.create_table(
        "agent_calls",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("public_id", sa.String(36), nullable=False, unique=True),
        sa.Column(
            "user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=True
        ),
        sa.Column(
            "client_id",
            sa.Integer(),
            sa.ForeignKey("oauth_clients.id", ondelete="RESTRICT"),
            nullable=True,
        ),
        sa.Column(
            "application_id",
            sa.Integer(),
            sa.ForeignKey("agent_applications.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("tool", sa.String(120), nullable=False),
        sa.Column("arguments", sa.JSON(), nullable=False),
        sa.Column("outcome", sa.String(16), nullable=False),
        sa.Column("duration_ms", sa.Integer(), nullable=False),
        sa.Column("request_id", sa.String(64), nullable=True),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "num_nonnulls(user_id, client_id) = 1", name="ck_agent_calls_one_principal"
        ),
        sa.CheckConstraint(
            "outcome IN ('answered', 'refused', 'limited', 'failed')", name="ck_agent_calls_outcome"
        ),
    )
    op.create_index("ix_agent_calls_occurred", "agent_calls", ["occurred_at", "id"])
    op.create_index(
        "ix_agent_calls_user",
        "agent_calls",
        ["user_id", "occurred_at"],
        postgresql_where=sa.text("user_id IS NOT NULL"),
    )
    op.create_index(
        "ix_agent_calls_client",
        "agent_calls",
        ["client_id", "occurred_at"],
        postgresql_where=sa.text("client_id IS NOT NULL"),
    )
    op.create_index(
        "ix_agent_calls_application",
        "agent_calls",
        ["application_id"],
        postgresql_where=sa.text("application_id IS NOT NULL"),
    )
    op.add_column(
        "oauth_clients", sa.Column("kind", sa.String(16), nullable=False, server_default="api")
    )
    op.create_check_constraint("ck_oauth_clients_kind", "oauth_clients", "kind IN ('api', 'agent')")
    op.add_column(
        "user_sessions",
        sa.Column(
            "agent_application_id",
            sa.Integer(),
            sa.ForeignKey("agent_applications.id", ondelete="CASCADE"),
            nullable=True,
        ),
    )
    op.create_index(
        "ix_user_sessions_agent_application",
        "user_sessions",
        ["agent_application_id"],
        postgresql_where=sa.text("agent_application_id IS NOT NULL"),
    )
    op.execute(
        sa.text(
            "INSERT INTO roles (key, name, description, predefined, version, created_at, "
            "updated_at) VALUES ('agent', 'Agent', 'Reads and prepares changes for approval; "
            "never approves or publishes', true, 1, now(), now())"
        )
    )


def downgrade() -> None:
    op.execute("DELETE FROM grants WHERE role_id IN (SELECT id FROM roles WHERE key = 'agent')")
    op.execute("DELETE FROM roles WHERE key = 'agent'")
    op.drop_index("ix_user_sessions_agent_application", table_name="user_sessions")
    op.drop_column("user_sessions", "agent_application_id")
    op.drop_constraint("ck_oauth_clients_kind", "oauth_clients")
    op.drop_column("oauth_clients", "kind")
    op.drop_table("agent_calls")
    op.drop_table("agent_applications")
