"""Which kinds of inbox notice a person is mailed (Product 0.12 M2 follow-up, D434, D435).

``users.notice_mail_kinds_off`` holds the kinds switched off; everything is on by default, so a
person who switched mail on keeps receiving every kind. One transaction, so an interrupted run
leaves the database at ``20261112_01``.
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "20261113_01"
down_revision = "20261112_01"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column(
            "notice_mail_kinds_off",
            postgresql.ARRAY(sa.String(160)),
            nullable=False,
            server_default="{}",
        ),
    )


def downgrade() -> None:
    op.drop_column("users", "notice_mail_kinds_off")
