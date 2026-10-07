"""Job notifications at commit (Base 0.9 J1u, D58).

A trigger on ``jobs`` sends ``pg_notify('rdm_job_events', <job id>)`` after a job is inserted, or
updated in its state, progress, total, cancel request or output; lease renewals alone send nothing.
PostgreSQL delivers a notification only when its transaction commits, so a listener hears of
committed changes only, from every path that changes a job. The job event stream
(``GET /jobs/{id}/events``) listens for them. PostgreSQL runs the DDL in the migration's
transaction, so an interrupted run leaves the database at ``20261007_04``.
"""

from alembic import op

revision = "20261007_05"
down_revision = "20261007_04"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE FUNCTION rdm_notify_job() RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
            IF TG_OP = 'INSERT'
               OR NEW.state IS DISTINCT FROM OLD.state
               OR NEW.processed IS DISTINCT FROM OLD.processed
               OR NEW.total IS DISTINCT FROM OLD.total
               OR NEW.cancel_requested_at IS DISTINCT FROM OLD.cancel_requested_at
               OR NEW.output::text IS DISTINCT FROM OLD.output::text
            THEN
                PERFORM pg_notify('rdm_job_events', NEW.id);
            END IF;
            RETURN NULL;
        END
        $$
    """)
    op.execute(
        "CREATE TRIGGER jobs_notify AFTER INSERT OR UPDATE ON jobs "
        "FOR EACH ROW EXECUTE FUNCTION rdm_notify_job()"
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER jobs_notify ON jobs")
    op.execute("DROP FUNCTION rdm_notify_job()")
