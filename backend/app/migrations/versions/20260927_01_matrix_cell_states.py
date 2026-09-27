"""Stored relation matrix cell states (Base 0.8 A3b, ADR-033).

Adds ``matrix_cell_states``, the derived state of each relation matrix cell per owner (live
records, a publication, a change set base, a change set overlay, a workspace's publication
history) and matrix shape, and ``matrix_state_builds``, which records the owners and shapes whose
states are complete.

The states are derived from records and the installed models, so this revision creates the tables
empty. The application builds every missing (owner, shape) at startup with the service that also
maintains them (``services/matrix_states.py``), one committed build at a time: a stopped build
resumes on the next start, and until a build exists the matrix derives its cells from records.

SQLite commits DDL as it runs, so an interrupted run can leave either table behind without the
version bump. A table with the expected columns holds only derived data and is dropped and created
again; a table of any other shape is refused.
"""

import sqlalchemy as sa
from alembic import op

revision = "20260927_01"
down_revision = "20260926_04"
branch_labels = None
depends_on = None

STATES, BUILDS = "matrix_cell_states", "matrix_state_builds"
_COLUMNS = {
    STATES: {
        "sequence_id",
        "owner_kind",
        "owner_id",
        "shape_key",
        "row_id",
        "column_id",
        "record_count",
        "matching_count",
        "first_publication_number",
    },
    BUILDS: {"sequence_id", "workspace_key", "owner_kind", "owner_id", "shape_key", "shape", "built_at"},
}


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    existing = set(inspector.get_table_names())
    for table in (STATES, BUILDS):
        if table not in existing:
            continue
        columns = {column["name"] for column in inspector.get_columns(table)}
        if columns != _COLUMNS[table]:
            raise RuntimeError(
                f"{table} has an unexpected schema from an earlier interrupted or manual change; "
                "restore the pre-upgrade backup and rerun the upgrade"
            )
    # Derived data left by an interrupted run: create both tables again, empty.
    for table in (STATES, BUILDS):
        if table in existing:
            op.drop_table(table)

    op.create_table(
        STATES,
        sa.Column("sequence_id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("owner_kind", sa.String(20), nullable=False),
        sa.Column("owner_id", sa.String(160), nullable=False),
        sa.Column("shape_key", sa.String(32), nullable=False),
        sa.Column("row_id", sa.String(36), nullable=False),
        sa.Column("column_id", sa.String(36), nullable=False),
        sa.Column("record_count", sa.Integer(), nullable=False),
        sa.Column("matching_count", sa.Integer(), nullable=False),
        sa.Column("first_publication_number", sa.Integer(), nullable=True),
        sa.UniqueConstraint(
            "owner_kind", "owner_id", "shape_key", "row_id", "column_id", name="uq_matrix_cell_state"
        ),
        sa.CheckConstraint(
            "owner_kind IN ('live', 'history', 'publication', 'base', 'change_set')",
            name="ck_matrix_cell_state_owner_kind",
        ),
    )
    op.create_index(
        "ix_matrix_cell_states_column",
        STATES,
        [
            "owner_kind",
            "owner_id",
            "shape_key",
            "column_id",
            "row_id",
            "record_count",
            "matching_count",
            "first_publication_number",
        ],
    )
    op.create_table(
        BUILDS,
        sa.Column("sequence_id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("workspace_key", sa.String(160), nullable=False),
        sa.Column("owner_kind", sa.String(20), nullable=False),
        sa.Column("owner_id", sa.String(160), nullable=False),
        sa.Column("shape_key", sa.String(32), nullable=False),
        sa.Column("shape", sa.JSON(), nullable=False),
        sa.Column("built_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("owner_kind", "owner_id", "shape_key", name="uq_matrix_state_build"),
    )
    op.create_index("ix_matrix_state_builds_workspace_key", BUILDS, ["workspace_key"])


def downgrade() -> None:
    existing = set(sa.inspect(op.get_bind()).get_table_names())
    for table in (BUILDS, STATES):
        if table in existing:
            op.drop_table(table)
