"""Background jobs: item inputs, the worker's lease and cancellation (Base 0.9 B2, INTEGRATION_API P6).

Adds ``job_inputs`` (a background job's items, one row per item until the job reaches a final
state, D27) and, on ``jobs``, ``lease_owner`` and ``lease_expires_at`` (the worker holding the job)
and ``cancel_requested_at`` (D28), with an index the worker finds queued and running jobs by.

Adds ``ix_attribute_values_key_text``: a live write's unique-value check and a record reference by
key seek to the value instead of reading every value of the attribute, whose cost grew with the
data (found by the B2 budget), as a change set's already do.

SQLite commits DDL as it runs, so an interrupted run can leave some of these behind without the
version bump. No background job can be written before the revision completes, so a ``job_inputs``
table with the expected columns is dropped and created again, and a column or index already added
is kept; a table of any other shape is refused.
"""

import sqlalchemy as sa
from alembic import op

revision = "20261001_01"
down_revision = "20260930_01"
branch_labels = None
depends_on = None

JOBS, INPUTS = "jobs", "job_inputs"
_INPUT_COLUMNS = {"sequence_id", "job_id", "item_index", "ref", "item"}
_JOB_COLUMNS = (
    ("lease_owner", sa.String(120)),
    ("lease_expires_at", sa.DateTime(timezone=True)),
    ("cancel_requested_at", sa.DateTime(timezone=True)),
)
_STATE_INDEX = "ix_jobs_state"
VALUES, _VALUE_INDEX = "attribute_values", "ix_attribute_values_key_text"


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if INPUTS in inspector.get_table_names():
        columns = {column["name"] for column in inspector.get_columns(INPUTS)}
        if columns != _INPUT_COLUMNS:
            raise RuntimeError(
                f"{INPUTS} has an unexpected schema from an earlier interrupted or manual change; "
                "restore the pre-upgrade backup and rerun the upgrade"
            )
        op.drop_table(INPUTS)

    job_columns = {column["name"] for column in inspector.get_columns(JOBS)}
    for name, column_type in _JOB_COLUMNS:
        if name not in job_columns:
            op.add_column(JOBS, sa.Column(name, column_type, nullable=True))
    if _STATE_INDEX not in {index["name"] for index in inspector.get_indexes(JOBS)}:
        op.create_index(_STATE_INDEX, JOBS, ["state", "sequence_id"])
    if _VALUE_INDEX not in {index["name"] for index in inspector.get_indexes(VALUES)}:
        op.create_index(_VALUE_INDEX, VALUES, ["attribute_type_key", "text_value", "object_id"])

    op.create_table(
        INPUTS,
        sa.Column("sequence_id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "job_id",
            sa.Integer(),
            sa.ForeignKey("jobs.sequence_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("item_index", sa.Integer(), nullable=False),
        sa.Column("ref", sa.String(200), nullable=True),
        sa.Column("item", sa.JSON(), nullable=False),
        sa.UniqueConstraint("job_id", "item_index", name="uq_job_input"),
    )


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if _VALUE_INDEX in {index["name"] for index in inspector.get_indexes(VALUES)}:
        op.drop_index(_VALUE_INDEX, table_name=VALUES)
    if INPUTS in inspector.get_table_names():
        op.drop_table(INPUTS)
    if _STATE_INDEX in {index["name"] for index in inspector.get_indexes(JOBS)}:
        op.drop_index(_STATE_INDEX, table_name=JOBS)
    columns = {column["name"] for column in inspector.get_columns(JOBS)}
    with op.batch_alter_table(JOBS) as batch:
        for name, _ in reversed(_JOB_COLUMNS):
            if name in columns:
                batch.drop_column(name)
