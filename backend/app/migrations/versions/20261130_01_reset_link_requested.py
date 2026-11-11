"""Which password links a person asked for themselves (0.17 RF2).

``password_reset_links.requested``: true for a link the forgotten-password request made, false for one
an administrator made. A request replaces only the links it made, so it no longer cancels an
administrator's link; an administrator's link still replaces every earlier one. Existing links start
as an administrator's. One statement, so an interrupted run leaves the database at ``20261129_01``.
"""

import sqlalchemy as sa
from alembic import op

revision = "20261130_01"
down_revision = "20261129_01"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "password_reset_links",
        sa.Column("requested", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.alter_column("password_reset_links", "requested", server_default=None)


def downgrade() -> None:
    op.drop_column("password_reset_links", "requested")
