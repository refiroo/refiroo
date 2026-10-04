"""Error codes in upper case (Base 0.9 T1b, D42–D43).

Every error code the APIs answer is written in upper case from this release. Finished jobs keep
their results for the retention period, and those results hold codes: a job's own error
(``jobs.error``), a rejected item's error and an unprocessed item's reason
(``job_items.outcome``). They are upper-cased here, one set statement each, so a job read after the
upgrade answers in the same spelling as a new one. Nothing else stores a code. PostgreSQL runs the
statements in the migration's transaction, so an interrupted run leaves the database at
``20261004_02``.
"""

from alembic import op

revision = "20261004_03"
down_revision = "20261004_02"
branch_labels = None
depends_on = None

# (table, JSON column, path of the code within it)
_CODES = (
    ("jobs", "error", "{code}"),
    ("job_items", "outcome", "{error,code}"),
    ("job_items", "outcome", "{reason}"),
)


def _respell(case: str) -> None:
    for table, column, path in _CODES:
        value = f"{column}::jsonb #>> '{path}'"
        op.execute(f"""
            UPDATE {table}
            SET {column} = jsonb_set({column}::jsonb, '{path}', to_jsonb({case}({value})))::json
            WHERE {value} IS NOT NULL AND {value} <> {case}({value})
        """)


def upgrade() -> None:
    _respell("upper")


def downgrade() -> None:
    _respell("lower")
