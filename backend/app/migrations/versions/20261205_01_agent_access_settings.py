"""Assistants' own session limits (0.17 AS-D2, AS-D3).

``agent_access_settings`` is one row: the days an assistant's session may go without a renewal (30)
and its days in all (90), set on the Agent access page. Security events gain the aggregate
``agent-access-settings``. One transaction, so an interrupted run leaves the database at
``20261204_01``.
"""

import sqlalchemy as sa
from alembic import op

revision = "20261205_01"
down_revision = "20261204_01"
branch_labels = None
depends_on = None

_SECURITY_BEFORE = (
    "aggregate_type IN ('user', 'group', 'role', 'grant', 'client', 'token-signing-key', "
    "'sign-in', 'sign-in-provider', 'mail-settings', 'approval-policy')"
)
_SECURITY_AFTER = (
    "aggregate_type IN ('user', 'group', 'role', 'grant', 'client', 'token-signing-key', "
    "'sign-in', 'sign-in-provider', 'mail-settings', 'approval-policy', 'agent-access-settings')"
)


def _security_index(predicate: str) -> None:
    op.drop_index("ix_audit_events_security", "audit_events")
    op.create_index(
        "ix_audit_events_security",
        "audit_events",
        ["occurred_at", "sequence_id"],
        postgresql_where=sa.text(predicate),
    )


def upgrade() -> None:
    op.create_table(
        "agent_access_settings",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("session_idle_days", sa.Integer(), nullable=False),
        sa.Column("session_days", sa.Integer(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("id = 1", name="ck_agent_access_settings_one_row"),
        sa.CheckConstraint(
            "session_idle_days BETWEEN 1 AND 365", name="ck_agent_access_settings_idle_days"
        ),
        sa.CheckConstraint(
            "session_days BETWEEN session_idle_days AND 365", name="ck_agent_access_settings_days"
        ),
    )
    op.execute(
        "INSERT INTO agent_access_settings (id, session_idle_days, session_days, version, "
        "updated_at) VALUES (1, 30, 90, 1, now())"
    )
    _security_index(_SECURITY_AFTER)


def downgrade() -> None:
    op.execute("DELETE FROM audit_events WHERE aggregate_type = 'agent-access-settings'")
    _security_index(_SECURITY_BEFORE)
    op.drop_table("agent_access_settings")
