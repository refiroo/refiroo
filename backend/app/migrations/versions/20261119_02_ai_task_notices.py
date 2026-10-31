"""An assistant task's inbox notice when its reading is ready (Product 0.16 AP6a).

``20261119_01`` made the inbox trigger notice every finished ``aiTask`` job. A task works through
several (reading, planning, fixing), and a planning job completes while its dry run is still queued,
so its notice would announce a check that is not there yet. The trigger now notices a completed
``aiTask`` job only when it read the workbook (the reading waits for the person) and a failed one in
any phase. One statement, so an interrupted run leaves the database at ``20261119_01``.
"""

from alembic import op

revision = "20261119_02"
down_revision = "20261119_01"
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
           AND NEW.kind IN ('batch', 'import', 'export', 'migration', 'move', 'aiProposal', 'aiTask')
           AND NOT (NEW.kind = 'batch' AND COALESCE(NEW.parameters ->> 'run', '') <> 'background')
           AND NOT (NEW.kind = 'aiTask' AND NEW.state = 'completed'
                    AND COALESCE(NEW.parameters ->> 'phase', '') <> 'read')
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
        IF OLD.state = 'awaiting_confirmation' AND NEW.state IS DISTINCT FROM OLD.state THEN
            UPDATE notifications SET read_at = now()
            WHERE subject_kind = 'job' AND subject_id = NEW.id
              AND kind = 'job.awaiting-confirmation' AND read_at IS NULL;
        END IF;
        IF NEW.state IS DISTINCT FROM OLD.state
           AND NEW.state IN ('completed', 'failed', 'awaiting_confirmation')
           AND (NEW.requested_by_user_id IS NOT NULL OR NEW.requested_by_client_id IS NOT NULL)
           AND NEW.kind IN ('batch', 'import', 'export', 'migration', 'move', 'aiProposal', 'aiTask')
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
    op.execute(_NOTIFY_JOB)


def downgrade() -> None:
    op.execute(_NOTIFY_JOB_BEFORE)
