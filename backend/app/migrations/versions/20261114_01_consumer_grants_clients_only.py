"""A consumer API is granted to a client only (Product 0.12 Z3 amended, D306).

Grants of a consumer API to a person or a group are removed: people read through the management
API, and a group's members are people. One statement in one transaction, so an interrupted run
leaves the database at ``20261113_01``.
"""

from alembic import op

revision = "20261114_01"
down_revision = "20261113_01"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "DELETE FROM grants WHERE consumer_api IS NOT NULL "
        "AND (user_id IS NOT NULL OR group_id IS NOT NULL)"
    )


def downgrade() -> None:
    """Nothing to undo: the removed grants are not restored."""
