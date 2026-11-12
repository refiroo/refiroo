"""A model draft's canvas: where each card of the workbook canvas sits.

``model_drafts.canvas_json`` holds the card positions the canvas keeps for the draft, a map of card
key to ``{x, y}``; ``NULL`` for none. It is the draft's own and not part of its model, its version,
its history or a release. One transaction, so an interrupted run leaves the database at
``20261201_01``.
"""

import sqlalchemy as sa
from alembic import op

revision = "20261202_01"
down_revision = "20261201_01"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("model_drafts", sa.Column("canvas_json", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("model_drafts", "canvas_json")
