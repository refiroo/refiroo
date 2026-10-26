"""Approvals: a workspace's policy, publication requests and their decisions (Product 0.12 A1, D424-D427).

``approval_policies`` holds a workspace's two flags (absent: both off). ``change_set_submissions``
is one row per submission of a change set; its change set is no foreign key because an approved
change set is deleted by its publication and the request stays as history. ``change_set_decisions``
is one row per decision on a submission. Security events gain the aggregate ``approval-policy``.
One transaction, so an interrupted run leaves the database at ``20261109_01``.
"""

import sqlalchemy as sa
from alembic import op

revision = "20261110_01"
down_revision = "20261109_01"
branch_labels = None
depends_on = None

_SECURITY_BEFORE = (
    "aggregate_type IN ('user', 'group', 'role', 'grant', 'client', 'token-signing-key', "
    "'sign-in', 'sign-in-provider', 'mail-settings')"
)
_SECURITY_AFTER = (
    "aggregate_type IN ('user', 'group', 'role', 'grant', 'client', 'token-signing-key', "
    "'sign-in', 'sign-in-provider', 'mail-settings', 'approval-policy')"
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
        "approval_policies",
        sa.Column(
            "workspace_key",
            sa.String(160),
            sa.ForeignKey("workspaces.key", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("require_approval", sa.Boolean(), nullable=False),
        sa.Column("second_person", sa.Boolean(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "NOT second_person OR require_approval", name="ck_approval_policies_second_person"
        ),
    )
    op.create_table(
        "change_set_submissions",
        sa.Column("sequence_id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("id", sa.String(36), nullable=False, unique=True),
        sa.Column(
            "workspace_key",
            sa.String(160),
            sa.ForeignKey("workspaces.key", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("change_set_id", sa.String(36), nullable=False),
        sa.Column("change_set_name", sa.String(300), nullable=True),
        sa.Column("version_submitted", sa.Integer(), nullable=False),
        sa.Column(
            "submitted_by_user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=True,
        ),
        sa.Column(
            "submitted_by_client_id",
            sa.Integer(),
            sa.ForeignKey("oauth_clients.id", ondelete="RESTRICT"),
            nullable=True,
        ),
        sa.Column("comment", sa.Text(), nullable=True),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("state", sa.String(16), nullable=False),
        sa.Column(
            "publication_id",
            sa.String(36),
            sa.ForeignKey("publications.id", ondelete="RESTRICT"),
            nullable=True,
        ),
        sa.CheckConstraint(
            "state IN ('submitted', 'withdrawn', 'approved', 'sentBack')",
            name="ck_change_set_submissions_state",
        ),
        sa.CheckConstraint(
            "num_nonnulls(submitted_by_user_id, submitted_by_client_id) <= 1",
            name="ck_change_set_submissions_submitted_by_one",
        ),
    )
    op.create_index(
        "ix_change_set_submissions_change_set",
        "change_set_submissions",
        ["change_set_id", "sequence_id"],
    )
    op.create_index(
        "ix_change_set_submissions_workspace",
        "change_set_submissions",
        ["workspace_key", "sequence_id"],
    )
    op.create_index(
        "uq_change_set_submissions_open",
        "change_set_submissions",
        ["change_set_id"],
        unique=True,
        postgresql_where=sa.text("state = 'submitted'"),
    )
    op.create_table(
        "change_set_decisions",
        sa.Column("sequence_id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("id", sa.String(36), nullable=False, unique=True),
        sa.Column(
            "submission_sequence_id",
            sa.Integer(),
            sa.ForeignKey("change_set_submissions.sequence_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "decided_by_user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=True,
        ),
        sa.Column(
            "decided_by_client_id",
            sa.Integer(),
            sa.ForeignKey("oauth_clients.id", ondelete="RESTRICT"),
            nullable=True,
        ),
        sa.Column("outcome", sa.String(16), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("comment", sa.Text(), nullable=True),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "outcome IN ('approve', 'sendBack')", name="ck_change_set_decisions_outcome"
        ),
        sa.CheckConstraint(
            "num_nonnulls(decided_by_user_id, decided_by_client_id) <= 1",
            name="ck_change_set_decisions_decided_by_one",
        ),
    )
    op.create_index(
        "ix_change_set_decisions_submission",
        "change_set_decisions",
        ["submission_sequence_id", "sequence_id"],
    )
    _security_index(_SECURITY_AFTER)


def downgrade() -> None:
    op.execute("DELETE FROM audit_events WHERE aggregate_type = 'approval-policy'")
    _security_index(_SECURITY_BEFORE)
    op.drop_index("ix_change_set_decisions_submission", "change_set_decisions")
    op.drop_table("change_set_decisions")
    op.drop_index("uq_change_set_submissions_open", "change_set_submissions")
    op.drop_index("ix_change_set_submissions_workspace", "change_set_submissions")
    op.drop_index("ix_change_set_submissions_change_set", "change_set_submissions")
    op.drop_table("change_set_submissions")
    op.drop_table("approval_policies")
