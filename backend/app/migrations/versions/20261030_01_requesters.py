"""Who asked for a job, and who uploaded a source file (Product 0.12 Z2, D294, D295).

``jobs`` and ``source_files`` gain the person or client behind them: at most one of
``*_user_id`` and ``*_client_id``, never removed while a row names them (principals are
deactivated, never deleted, D237). Rows from before have neither: a job then finishes under the
route check alone, and a file follows its workspace's holders. New columns only, in one
transaction, so an interrupted run leaves the database at ``20261029_01``.
"""

import sqlalchemy as sa
from alembic import op

revision = "20261030_01"
down_revision = "20261029_01"
branch_labels = None
depends_on = None

_COLUMNS = (("jobs", "requested_by"), ("source_files", "uploaded_by"))


def upgrade() -> None:
    for table, prefix in _COLUMNS:
        op.add_column(
            table,
            sa.Column(
                f"{prefix}_user_id",
                sa.Integer(),
                sa.ForeignKey("users.id", ondelete="RESTRICT"),
                nullable=True,
            ),
        )
        op.add_column(
            table,
            sa.Column(
                f"{prefix}_client_id",
                sa.Integer(),
                sa.ForeignKey("oauth_clients.id", ondelete="RESTRICT"),
                nullable=True,
            ),
        )
        op.create_check_constraint(
            f"ck_{table}_one_{prefix}",
            table,
            f"num_nonnulls({prefix}_user_id, {prefix}_client_id) <= 1",
        )
        op.create_index(f"ix_{table}_{prefix}_user", table, [f"{prefix}_user_id"])
        op.create_index(f"ix_{table}_{prefix}_client", table, [f"{prefix}_client_id"])


def downgrade() -> None:
    for table, prefix in _COLUMNS:
        op.drop_index(f"ix_{table}_{prefix}_client", table)
        op.drop_index(f"ix_{table}_{prefix}_user", table)
        op.drop_constraint(f"ck_{table}_one_{prefix}", table)
        op.drop_column(table, f"{prefix}_client_id")
        op.drop_column(table, f"{prefix}_user_id")
