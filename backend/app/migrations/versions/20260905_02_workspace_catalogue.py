"""Add the authoritative workspace catalogue and default runtime state."""

from datetime import UTC, datetime

import sqlalchemy as sa
from alembic import op

revision = "20260905_02"
down_revision = "20260905_01"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "workspaces",
        sa.Column("key", sa.String(length=160), nullable=False),
        sa.Column("label", sa.String(length=300), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("status IN ('active', 'retired')", name="ck_workspace_status"),
        sa.PrimaryKeyConstraint("key"),
    )
    op.create_index("ix_workspaces_status", "workspaces", ["status"], unique=False)

    connection = op.get_bind()
    now = datetime.now(UTC)
    keys = [
        str(row[0])
        for row in connection.execute(
            sa.text("SELECT DISTINCT workspace_key FROM objects ORDER BY workspace_key")
        )
        if row[0] is not None
    ]
    workspace_keys = list(dict.fromkeys(["default", *keys]))
    connection.execute(
        sa.text(
            "INSERT INTO workspaces (key, label, status, version, created_at, updated_at) "
            "VALUES (:key, :label, 'active', 1, :created_at, :updated_at)"
        ),
        [
            {
                "key": key,
                "label": "Default" if key == "default" else key,
                "created_at": now,
                "updated_at": now,
            }
            for key in workspace_keys
        ],
    )

    op.create_table(
        "workspace_runtime_state",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("default_workspace_key", sa.String(length=160), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("id = 1", name="ck_workspace_runtime_state_singleton"),
        sa.ForeignKeyConstraint(["default_workspace_key"], ["workspaces.key"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    connection.execute(
        sa.text(
            "INSERT INTO workspace_runtime_state "
            "(id, default_workspace_key, version, updated_at) "
            "VALUES (1, 'default', 1, :updated_at)"
        ),
        {"updated_at": now},
    )

    with op.batch_alter_table("objects") as batch_op:
        batch_op.create_foreign_key(
            "fk_objects_workspace_key_workspaces",
            "workspaces",
            ["workspace_key"],
            ["key"],
            ondelete="RESTRICT",
        )


def downgrade() -> None:
    with op.batch_alter_table("objects") as batch_op:
        batch_op.drop_constraint("fk_objects_workspace_key_workspaces", type_="foreignkey")
    op.drop_table("workspace_runtime_state")
    op.drop_index("ix_workspaces_status", table_name="workspaces")
    op.drop_table("workspaces")
