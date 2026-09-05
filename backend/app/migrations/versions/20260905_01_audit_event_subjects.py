"""Add indexed object subjects for audit history."""

import json

import sqlalchemy as sa

from alembic import op

revision = "20260905_01"
down_revision = "20260904_02"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "audit_event_subjects",
        sa.Column("sequence_id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("audit_event_id", sa.Integer(), nullable=False),
        sa.Column("object_id", sa.String(length=36), nullable=False),
        sa.ForeignKeyConstraint(
            ["audit_event_id"], ["audit_events.sequence_id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("sequence_id"),
        sa.UniqueConstraint("audit_event_id", "object_id", name="uq_audit_event_subject"),
    )
    op.create_index(
        "ix_audit_event_subjects_audit_event_id",
        "audit_event_subjects",
        ["audit_event_id"],
        unique=False,
    )
    op.create_index(
        "ix_audit_event_subjects_object_id",
        "audit_event_subjects",
        ["object_id"],
        unique=False,
    )

    connection = op.get_bind()
    rows = connection.execute(
        sa.text(
            "SELECT sequence_id, aggregate_type, aggregate_id, changes FROM audit_events"
        )
    ).mappings()
    subjects: list[dict[str, object]] = []
    for row in rows:
        object_ids: list[str] = []
        if row["aggregate_type"] == "object":
            object_ids.append(str(row["aggregate_id"]))
        elif row["aggregate_type"] == "relation":
            changes = row["changes"]
            if isinstance(changes, str):
                try:
                    changes = json.loads(changes)
                except json.JSONDecodeError:
                    changes = {}
            if isinstance(changes, dict):
                for key in ("fromObjectId", "toObjectId"):
                    value = changes.get(key)
                    if isinstance(value, str):
                        object_ids.append(value)
        for object_id in dict.fromkeys(object_ids):
            subjects.append(
                {
                    "audit_event_id": row["sequence_id"],
                    "object_id": object_id,
                }
            )
    if subjects:
        connection.execute(
            sa.text(
                "INSERT INTO audit_event_subjects (audit_event_id, object_id) "
                "VALUES (:audit_event_id, :object_id)"
            ),
            subjects,
        )


def downgrade() -> None:
    op.drop_index("ix_audit_event_subjects_object_id", table_name="audit_event_subjects")
    op.drop_index("ix_audit_event_subjects_audit_event_id", table_name="audit_event_subjects")
    op.drop_table("audit_event_subjects")
