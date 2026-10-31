"""The assistant task and the job that works on it (Product 0.16 AP6a, AP-D23 to AP-D26).

``ai_tasks`` holds a workbook read against a workspace and planned into a load: who asked, the
person's words, the reading, the plan, the check of the latest dry run, the notes shown to the
person, the result of the load, the job it waits for and when it expires. A task owns its workbook
as a source file (``source_files.task_id``, deleted with the task). ``jobs.kind`` gains ``aiTask``
and the inbox trigger notices it when it finishes. One transaction, so an interrupted run leaves
the database at ``20261118_01``.
"""

import sqlalchemy as sa
from alembic import op

revision = "20261119_01"
down_revision = "20261118_01"
branch_labels = None
depends_on = None

KINDS = (
    "kind IN ('batch', 'import', 'export', 'profile', 'dryRun', 'inference', 'profileCheck', "
    "'migration', 'mappingInference', 'move', 'aiProposal', 'aiTask')"
)
OLD_KINDS = (
    "kind IN ('batch', 'import', 'export', 'profile', 'dryRun', 'inference', 'profileCheck', "
    "'migration', 'mappingInference', 'move', 'aiProposal')"
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


def upgrade() -> None:
    op.create_table(
        "ai_tasks",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("public_id", sa.String(36), nullable=False, unique=True),
        sa.Column(
            "requested_by_user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=True,
        ),
        sa.Column(
            "requested_by_client_id",
            sa.Integer(),
            sa.ForeignKey("oauth_clients.id", ondelete="RESTRICT"),
            nullable=True,
        ),
        sa.Column("workspace_key", sa.String(160), nullable=False),
        sa.Column("words", sa.Text(), nullable=True),
        sa.Column("state", sa.String(16), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("reading", sa.JSON(), nullable=True),
        sa.Column("plan", sa.JSON(), nullable=True),
        sa.Column("check_report", sa.JSON(), nullable=True),
        sa.Column("notes", sa.JSON(), nullable=False),
        sa.Column("result", sa.JSON(), nullable=True),
        sa.Column("job_id", sa.String(36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "state IN ('reading', 'read', 'checking', 'checked', 'loading', 'loaded', 'failed', "
            "'cancelled')",
            name="ck_ai_tasks_state",
        ),
        sa.CheckConstraint(
            "num_nonnulls(requested_by_user_id, requested_by_client_id) <= 1",
            name="ck_ai_tasks_one_requested_by",
        ),
    )
    op.create_index("ix_ai_tasks_requested_by_user", "ai_tasks", ["requested_by_user_id", "id"])
    op.create_index("ix_ai_tasks_requested_by_client", "ai_tasks", ["requested_by_client_id", "id"])
    op.create_index("ix_ai_tasks_workspace", "ai_tasks", ["workspace_key", "id"])
    op.create_index("ix_ai_tasks_expires", "ai_tasks", ["expires_at"])

    op.add_column(
        "source_files",
        sa.Column(
            "task_id", sa.Integer(), sa.ForeignKey("ai_tasks.id", ondelete="CASCADE"), nullable=True
        ),
    )
    op.create_index("ix_source_files_task", "source_files", ["task_id"])
    op.drop_constraint("ck_source_files_one_owner", "source_files", type_="check")
    op.create_check_constraint(
        "ck_source_files_one_owner",
        "source_files",
        "num_nonnulls(draft_id, profile_key, task_id) = 1",
    )

    op.drop_constraint("ck_job_kind", "jobs", type_="check")
    op.create_check_constraint("ck_job_kind", "jobs", KINDS)
    op.execute(_NOTIFY_JOB)


def downgrade() -> None:
    op.execute(_NOTIFY_JOB_BEFORE)
    op.execute("DELETE FROM jobs WHERE kind = 'aiTask'")
    op.drop_constraint("ck_job_kind", "jobs", type_="check")
    op.create_check_constraint("ck_job_kind", "jobs", OLD_KINDS)
    op.drop_constraint("ck_source_files_one_owner", "source_files", type_="check")
    op.execute("DELETE FROM source_files WHERE task_id IS NOT NULL")
    op.create_check_constraint(
        "ck_source_files_one_owner", "source_files", "(draft_id IS NULL) <> (profile_key IS NULL)"
    )
    op.drop_index("ix_source_files_task", table_name="source_files")
    op.drop_column("source_files", "task_id")
    op.drop_table("ai_tasks")
