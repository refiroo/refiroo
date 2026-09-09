"""Widen audit_events.aggregate_id to hold the longest legal workspace key.

Publication retirement audits on the ``workspace`` aggregate with the real workspace key as its
aggregate id.  ``Workspace.key`` is ``String(160)`` while ``audit_events.aggregate_id`` was
``String(36)``, so on a length-strict database the retirement commit failed for any key longer than
36 characters.  Widen the audit aggregate id to ``String(255)`` so the workspace aggregate stays
addressable by the real workspace key.
"""

import sqlalchemy as sa
from alembic import op

revision = "20260908_01"
down_revision = "20260907_03"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("audit_events") as batch_op:
        batch_op.alter_column(
            "aggregate_id",
            existing_type=sa.String(length=36),
            type_=sa.String(length=200),
            existing_nullable=False,
            nullable=False,
        )


def downgrade() -> None:
    with op.batch_alter_table("audit_events") as batch_op:
        batch_op.alter_column(
            "aggregate_id",
            existing_type=sa.String(length=200),
            type_=sa.String(length=36),
            existing_nullable=False,
            nullable=False,
        )
