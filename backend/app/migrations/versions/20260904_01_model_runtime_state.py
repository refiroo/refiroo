"""Add authoritative model runtime state and release identity uniqueness."""

from datetime import UTC, datetime

import sqlalchemy as sa
from alembic import op

revision = "20260904_01"
down_revision = "20260903_01"
branch_labels = None
depends_on = None


def upgrade() -> None:
    connection = op.get_bind()
    active_release_ids = list(
        connection.scalars(sa.text("SELECT id FROM model_releases WHERE is_active = true"))
    )
    if len(active_release_ids) > 1:
        raise RuntimeError(
            "Cannot initialize model runtime state: multiple legacy active releases exist"
        )

    duplicate_identities = connection.execute(
        sa.text(
            "SELECT release_key, release_version, COUNT(*) AS release_count "
            "FROM model_releases GROUP BY release_key, release_version HAVING COUNT(*) > 1"
        )
    ).fetchall()
    if duplicate_identities:
        identities = ", ".join(f"{key}@{version}" for key, version, _count in duplicate_identities)
        raise RuntimeError(
            "Cannot add model release identity uniqueness; duplicate releases exist: " + identities
        )

    with op.batch_alter_table("model_releases") as batch_op:
        batch_op.create_unique_constraint(
            "uq_model_release_identity", ["release_key", "release_version"]
        )

    op.create_table(
        "model_runtime_state",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("active_model_release_id", sa.Integer(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("id = 1", name="ck_model_runtime_state_singleton"),
        sa.ForeignKeyConstraint(
            ["active_model_release_id"], ["model_releases.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_model_runtime_state_active_model_release_id",
        "model_runtime_state",
        ["active_model_release_id"],
        unique=False,
    )

    if active_release_ids:
        connection.execute(
            sa.text(
                "INSERT INTO model_runtime_state "
                "(id, active_model_release_id, version, updated_at) "
                "VALUES (1, :release_id, 1, :updated_at)"
            ),
            {
                "release_id": active_release_ids[0],
                "updated_at": datetime.now(UTC).isoformat(),
            },
        )


def downgrade() -> None:
    op.drop_index(
        "ix_model_runtime_state_active_model_release_id", table_name="model_runtime_state"
    )
    op.drop_table("model_runtime_state")
    with op.batch_alter_table("model_releases") as batch_op:
        batch_op.drop_constraint("uq_model_release_identity", type_="unique")
