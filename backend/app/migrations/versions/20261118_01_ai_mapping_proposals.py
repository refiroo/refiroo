"""Provenance on change-set rows and the AI proposal job (Product 0.16 AP2, AP2-D5).

``change_set_relations`` and ``change_set_objects`` gain a nullable ``origin`` (JSON): who proposed
the change when a person did not, ``{kind: "ai", provider, model, promptVersion, confidence, reason,
proposedBy}``. ``jobs.kind`` gains ``aiProposal`` and the inbox trigger notices it when it finishes.
One transaction, so an interrupted run leaves the database at ``20261117_01``.
"""

import sqlalchemy as sa
from alembic import op

revision = "20261118_01"
down_revision = "20261117_01"
branch_labels = None
depends_on = None

KINDS = (
    "kind IN ('batch', 'import', 'export', 'profile', 'dryRun', 'inference', 'profileCheck', "
    "'migration', 'mappingInference', 'move', 'aiProposal')"
)
OLD_KINDS = (
    "kind IN ('batch', 'import', 'export', 'profile', 'dryRun', 'inference', 'profileCheck', "
    "'migration', 'mappingInference', 'move')"
)

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
           AND NEW.kind IN ('batch', 'import', 'export', 'migration', 'move', 'aiProposal')
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


def upgrade() -> None:
    op.add_column("change_set_relations", sa.Column("origin", sa.JSON(), nullable=True))
    op.add_column("change_set_objects", sa.Column("origin", sa.JSON(), nullable=True))
    op.drop_constraint("ck_job_kind", "jobs", type_="check")
    op.create_check_constraint("ck_job_kind", "jobs", KINDS)
    op.execute(_NOTIFY_JOB)


def downgrade() -> None:
    op.execute(_NOTIFY_JOB_BEFORE)
    op.execute("DELETE FROM jobs WHERE kind = 'aiProposal'")
    op.drop_constraint("ck_job_kind", "jobs", type_="check")
    op.create_check_constraint("ck_job_kind", "jobs", OLD_KINDS)
    op.drop_column("change_set_objects", "origin")
    op.drop_column("change_set_relations", "origin")
