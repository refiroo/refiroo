"""Jobs, item outcomes and idempotency keys; a cause on audit events (Base 0.9 B1, ADR-036).

Adds ``jobs`` (a bulk write, import or export with its state and counts), ``job_items`` (one
outcome per item, in item order) and ``idempotency_keys`` (a client key per route and workspace
with the request's fingerprint). ``audit_events`` gains ``cause_kind`` and ``cause_id``: an entry
written by a job names it, and existing entries keep no cause.

SQLite commits DDL as it runs, so an interrupted run can leave some of these behind without the
version bump. No job can be written before the revision completes, so a new table with the
expected columns is dropped and created again, and a cause column already added is kept; a table of
any other shape is refused.
"""

import sqlalchemy as sa
from alembic import op

revision = "20260930_01"
down_revision = "20260928_01"
branch_labels = None
depends_on = None

JOBS, ITEMS, KEYS, AUDIT = "jobs", "job_items", "idempotency_keys", "audit_events"
_COLUMNS = {
    JOBS: {
        "sequence_id",
        "id",
        "kind",
        "workspace_key",
        "change_set_id",
        "model_release_id",
        "parameters",
        "state",
        "stage",
        "total",
        "processed",
        "counts",
        "result",
        "error",
        "change_set_version",
        "created_at",
        "started_at",
        "finished_at",
        "expires_at",
    },
    ITEMS: {"sequence_id", "job_id", "item_index", "ref", "status", "outcome"},
    KEYS: {
        "sequence_id",
        "scope",
        "workspace_key",
        "key",
        "fingerprint",
        "job_id",
        "created_at",
        "expires_at",
    },
}


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    existing = set(inspector.get_table_names())
    for table in (JOBS, ITEMS, KEYS):
        if table not in existing:
            continue
        columns = {column["name"] for column in inspector.get_columns(table)}
        if columns != _COLUMNS[table]:
            raise RuntimeError(
                f"{table} has an unexpected schema from an earlier interrupted or manual change; "
                "restore the pre-upgrade backup and rerun the upgrade"
            )
    for table in (KEYS, ITEMS, JOBS):
        if table in existing:
            op.drop_table(table)

    audit_columns = {column["name"] for column in inspector.get_columns(AUDIT)}
    audit_indexes = {index["name"] for index in inspector.get_indexes(AUDIT)}
    if "cause_kind" not in audit_columns:
        op.add_column(AUDIT, sa.Column("cause_kind", sa.String(20), nullable=True))
    if "cause_id" not in audit_columns:
        op.add_column(AUDIT, sa.Column("cause_id", sa.String(36), nullable=True))
    if "ix_audit_events_cause_id" not in audit_indexes:
        op.create_index("ix_audit_events_cause_id", AUDIT, ["cause_id"])

    op.create_table(
        JOBS,
        sa.Column("sequence_id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("kind", sa.String(20), nullable=False),
        sa.Column("workspace_key", sa.String(160), nullable=False),
        sa.Column("change_set_id", sa.String(36), nullable=True),
        sa.Column(
            "model_release_id",
            sa.Integer(),
            sa.ForeignKey("model_releases.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("parameters", sa.JSON(), nullable=False),
        sa.Column("state", sa.String(30), nullable=False),
        sa.Column("stage", sa.String(30), nullable=True),
        sa.Column("total", sa.Integer(), nullable=True),
        sa.Column("processed", sa.Integer(), nullable=False),
        sa.Column("counts", sa.JSON(), nullable=False),
        sa.Column("result", sa.String(20), nullable=True),
        sa.Column("error", sa.JSON(), nullable=True),
        sa.Column("change_set_version", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("kind IN ('batch', 'import', 'export')", name="ck_job_kind"),
        sa.CheckConstraint(
            "state IN ('queued', 'running', 'awaiting_confirmation', 'completed', 'failed', "
            "'cancelled', 'expired')",
            name="ck_job_state",
        ),
    )
    op.create_index("ix_jobs_id", JOBS, ["id"], unique=True)
    op.create_index("ix_jobs_model_release_id", JOBS, ["model_release_id"])
    op.create_index("ix_jobs_workspace_created", JOBS, ["workspace_key", "sequence_id"])
    op.create_table(
        ITEMS,
        sa.Column("sequence_id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "job_id",
            sa.Integer(),
            sa.ForeignKey("jobs.sequence_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("item_index", sa.Integer(), nullable=False),
        sa.Column("ref", sa.String(200), nullable=True),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("outcome", sa.JSON(), nullable=False),
        sa.UniqueConstraint("job_id", "item_index", name="uq_job_item"),
        sa.CheckConstraint(
            "status IN ('applied', 'rejected', 'unprocessed')", name="ck_job_item_status"
        ),
    )
    op.create_index("ix_job_items_status", ITEMS, ["job_id", "status", "item_index"])
    op.create_table(
        KEYS,
        sa.Column("sequence_id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("scope", sa.String(80), nullable=False),
        sa.Column("workspace_key", sa.String(160), nullable=False),
        sa.Column("key", sa.String(200), nullable=False),
        sa.Column("fingerprint", sa.String(64), nullable=False),
        sa.Column(
            "job_id",
            sa.Integer(),
            sa.ForeignKey("jobs.sequence_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("scope", "workspace_key", "key", name="uq_idempotency_key"),
    )
    op.create_index("ix_idempotency_keys_job_id", KEYS, ["job_id"])


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    existing = set(inspector.get_table_names())
    for table in (KEYS, ITEMS, JOBS):
        if table in existing:
            op.drop_table(table)
    if "ix_audit_events_cause_id" in {index["name"] for index in inspector.get_indexes(AUDIT)}:
        op.drop_index("ix_audit_events_cause_id", table_name=AUDIT)
    columns = {column["name"] for column in inspector.get_columns(AUDIT)}
    with op.batch_alter_table(AUDIT) as batch:
        for column in ("cause_id", "cause_kind"):
            if column in columns:
                batch.drop_column(column)
