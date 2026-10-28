"""The inbox closes a job's request and expires in the worker (Product 0.12 NT1, D464, D465).

``rdm_notify_job_inbox`` also marks a job's unread "waiting for your confirmation" notices read once
the job leaves ``awaiting_confirmation``: the request is answered. The 90-day delete leaves the
insert (``notifications_prune``) for the job worker's hourly sweep (``inbox.expire``), so old notices
go on a day nothing arrives too. One transaction, so an interrupted run leaves the database at
``20261115_01``.
"""

from alembic import op

revision = "20261116_01"
down_revision = "20261115_01"
branch_labels = None
depends_on = None

_NOTIFY_JOB = """
    CREATE OR REPLACE FUNCTION rdm_notify_job_inbox() RETURNS trigger LANGUAGE plpgsql AS $$
    BEGIN
        IF OLD.state = 'awaiting_confirmation' AND NEW.state IS DISTINCT FROM OLD.state THEN
            UPDATE notifications SET read_at = now()
            WHERE subject_kind = 'job' AND subject_id = NEW.id
              AND kind = 'job.awaiting-confirmation' AND read_at IS NULL;
        END IF;
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
"""

_NOTIFY_JOB_BEFORE = """
    CREATE OR REPLACE FUNCTION rdm_notify_job_inbox() RETURNS trigger LANGUAGE plpgsql AS $$
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
"""


def upgrade() -> None:
    op.execute("DROP TRIGGER notifications_prune ON notifications")
    op.execute("DROP FUNCTION rdm_prune_inbox()")
    op.execute(_NOTIFY_JOB)


def downgrade() -> None:
    op.execute(_NOTIFY_JOB_BEFORE)
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
