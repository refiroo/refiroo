"""The inbox and workspace events (Product 0.12 A2, D233).

``notifications`` is a person's or client's inbox: a request waiting for them, a decision on theirs,
a job they started that finished. A trigger on it sends ``pg_notify('rdm_notifications', <principal>)``
at commit (the stream listens) and deletes notices older than 90 days. A trigger on ``jobs`` writes
the job notices, so every path that finishes a job is covered. ``workspace_events`` holds the
change-set events a webhook subscription with the workspace source delivers; ``workspace_event_heads``
gives each workspace's events a gapless order, taken last in a transaction so it waits on no other
lock. One transaction, so an interrupted run leaves the database at ``20261110_01``.
"""

import sqlalchemy as sa
from alembic import op

revision = "20261111_01"
down_revision = "20261110_01"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "notifications",
        sa.Column("sequence_id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("id", sa.String(36), nullable=False, unique=True),
        sa.Column(
            "user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=True
        ),
        sa.Column(
            "client_id",
            sa.Integer(),
            sa.ForeignKey("oauth_clients.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column("kind", sa.String(40), nullable=False),
        sa.Column(
            "workspace_key",
            sa.String(160),
            sa.ForeignKey("workspaces.key", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("subject_kind", sa.String(20), nullable=False),
        sa.Column("subject_id", sa.String(36), nullable=False),
        sa.Column("details", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "num_nonnulls(user_id, client_id) = 1", name="ck_notifications_one_principal"
        ),
    )
    op.create_index("ix_notifications_user", "notifications", ["user_id", "sequence_id"])
    op.create_index("ix_notifications_client", "notifications", ["client_id", "sequence_id"])
    op.create_index(
        "ix_notifications_unread_user",
        "notifications",
        ["user_id", "sequence_id"],
        postgresql_where=sa.text("read_at IS NULL"),
    )
    op.create_index(
        "ix_notifications_unread_client",
        "notifications",
        ["client_id", "sequence_id"],
        postgresql_where=sa.text("read_at IS NULL"),
    )
    op.create_index("ix_notifications_subject", "notifications", ["subject_kind", "subject_id"])
    op.create_index("ix_notifications_created", "notifications", ["created_at"])
    op.execute("""
        CREATE FUNCTION rdm_notify_inbox() RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
            PERFORM pg_notify(
                'rdm_notifications',
                CASE WHEN NEW.user_id IS NOT NULL THEN 'user:' || NEW.user_id
                     ELSE 'client:' || NEW.client_id END
            );
            RETURN NULL;
        END
        $$
    """)
    op.execute(
        "CREATE TRIGGER notifications_notify AFTER INSERT ON notifications "
        "FOR EACH ROW EXECUTE FUNCTION rdm_notify_inbox()"
    )
    op.execute("""
        CREATE FUNCTION rdm_prune_inbox() RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
            DELETE FROM notifications WHERE created_at < now() - interval '90 days';
            RETURN NULL;
        END
        $$
    """)
    op.execute(
        "CREATE TRIGGER notifications_prune AFTER INSERT ON notifications "
        "FOR EACH STATEMENT EXECUTE FUNCTION rdm_prune_inbox()"
    )
    op.execute("""
        CREATE FUNCTION rdm_notify_job_inbox() RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
            IF NEW.state IS DISTINCT FROM OLD.state
               AND NEW.state IN ('completed', 'failed', 'awaiting_confirmation')
               AND (NEW.requested_by_user_id IS NOT NULL OR NEW.requested_by_client_id IS NOT NULL)
               AND NEW.kind IN ('batch', 'import', 'export', 'migration', 'move')
               AND NOT (NEW.kind = 'batch' AND COALESCE(NEW.parameters ->> 'run', '') <> 'background')
               AND EXISTS (SELECT 1 FROM workspaces WHERE key = NEW.workspace_key)
            THEN
                INSERT INTO notifications
                    (id, user_id, client_id, kind, workspace_key, subject_kind, subject_id,
                     details, created_at)
                VALUES (
                    gen_random_uuid()::text,
                    NEW.requested_by_user_id,
                    NEW.requested_by_client_id,
                    'job.' || replace(NEW.state, '_', '-'),
                    NEW.workspace_key,
                    'job',
                    NEW.id,
                    json_build_object('jobKind', NEW.kind, 'state', NEW.state),
                    now()
                );
            END IF;
            RETURN NULL;
        END
        $$
    """)
    op.execute(
        "CREATE TRIGGER jobs_inbox AFTER UPDATE ON jobs "
        "FOR EACH ROW EXECUTE FUNCTION rdm_notify_job_inbox()"
    )
    op.create_table(
        "workspace_event_heads",
        sa.Column(
            "workspace_key",
            sa.String(160),
            sa.ForeignKey("workspaces.key", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("position", sa.Integer(), nullable=False),
    )
    op.create_table(
        "workspace_events",
        sa.Column("sequence_id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("event_id", sa.String(36), nullable=False, unique=True),
        sa.Column(
            "workspace_key",
            sa.String(160),
            sa.ForeignKey("workspaces.key", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("event_key", sa.String(160), nullable=False),
        sa.Column("change_set_id", sa.String(36), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("workspace_key", "position", name="uq_workspace_event_order"),
    )
    op.create_index("ix_workspace_events_occurred", "workspace_events", ["occurred_at"])


def downgrade() -> None:
    op.drop_table("workspace_events")
    op.drop_table("workspace_event_heads")
    op.execute("DROP TRIGGER jobs_inbox ON jobs")
    op.execute("DROP FUNCTION rdm_notify_job_inbox()")
    op.drop_table("notifications")
    op.execute("DROP FUNCTION rdm_prune_inbox()")
    op.execute("DROP FUNCTION rdm_notify_inbox()")
