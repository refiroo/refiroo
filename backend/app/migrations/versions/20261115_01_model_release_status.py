"""A model release may be retired (Product 0.12 MR1, D457).

``model_releases`` gains ``status`` (``active`` or ``retired``), ``status_version`` for optimistic
concurrency on it and ``retired_at``. Every stored release is active. One transaction, so an
interrupted run leaves the database at ``20261114_01``.
"""

import sqlalchemy as sa
from alembic import op

revision = "20261115_01"
down_revision = "20261114_01"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "model_releases",
        sa.Column("status", sa.String(20), nullable=False, server_default="active"),
    )
    op.add_column(
        "model_releases",
        sa.Column("status_version", sa.Integer(), nullable=False, server_default="1"),
    )
    op.add_column(
        "model_releases", sa.Column("retired_at", sa.DateTime(timezone=True), nullable=True)
    )
    op.create_check_constraint(
        "ck_model_release_status", "model_releases", "status IN ('active', 'retired')"
    )
    op.create_index("ix_model_releases_status", "model_releases", ["status"])


def downgrade() -> None:
    op.drop_index("ix_model_releases_status", table_name="model_releases")
    op.drop_constraint("ck_model_release_status", "model_releases", type_="check")
    op.drop_column("model_releases", "retired_at")
    op.drop_column("model_releases", "status_version")
    op.drop_column("model_releases", "status")
