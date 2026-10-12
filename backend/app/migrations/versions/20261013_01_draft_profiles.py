"""A model draft's import profile (Product 0.10 A5, D75).

``model_drafts.profile_json`` holds the draft's one import profile, changed only by operations and
undone with the model. A draft without a profile has ``NULL``. PostgreSQL runs the DDL in the
migration's transaction, so an interrupted run leaves the database at ``20261012_01``.
"""

import sqlalchemy as sa
from alembic import op

revision = "20261013_01"
down_revision = "20261012_01"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("model_drafts", sa.Column("profile_json", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("model_drafts", "profile_json")
