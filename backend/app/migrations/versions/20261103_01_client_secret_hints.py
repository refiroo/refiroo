"""A client secret's last four characters (Product 0.12 SP2, D350).

``oauth_client_secrets.hint`` holds the last four characters of a secret, stored when it is made, so
an administrator tells a client's secrets apart during an overlap. Secrets made before keep
``NULL``: only their hash was stored. One transaction, so an interrupted run leaves the database at
``20261102_01``.
"""

import sqlalchemy as sa
from alembic import op

revision = "20261103_01"
down_revision = "20261102_01"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("oauth_client_secrets", sa.Column("hint", sa.String(4), nullable=True))


def downgrade() -> None:
    op.drop_column("oauth_client_secrets", "hint")
