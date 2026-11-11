"""A person whose sign-in an administrator manages (0.17 SA1).

``users.sign_in_managed``: while it is on, the person cannot change their own password, second
factor, passkeys or other sessions; an administrator still can. Every existing person starts with
it off. One statement, so an interrupted run leaves the database at ``20261128_01``.
"""

import sqlalchemy as sa
from alembic import op

revision = "20261129_01"
down_revision = "20261128_01"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("sign_in_managed", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.alter_column("users", "sign_in_managed", server_default=None)


def downgrade() -> None:
    op.drop_column("users", "sign_in_managed")
