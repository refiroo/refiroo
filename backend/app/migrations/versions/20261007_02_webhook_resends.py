"""Resending a delivered webhook event by hand (Base 0.9 U5a revision, C-D129–C-D131).

``consumer_webhook_requests`` gains ``resend_of``: for a resend, the delivery ID of the request it
repeats. Existing requests are not resends. PostgreSQL runs the DDL in the migration's transaction,
so an interrupted run leaves the database at ``20261007_01``.
"""

import sqlalchemy as sa
from alembic import op

revision = "20261007_02"
down_revision = "20261007_01"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("consumer_webhook_requests", sa.Column("resend_of", sa.String(36), nullable=True))


def downgrade() -> None:
    op.drop_column("consumer_webhook_requests", "resend_of")
