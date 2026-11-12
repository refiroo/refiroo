"""The e-mail template an operator edits (one row, absent until saved).

``mail_template`` holds the Markdown body with its placeholders and the uploaded logo (PNG, JPEG or
SVG, at most 512 KB, enforced by the application) that wrap the content of each mail the engine
sends. Without a row the engine's own layout applies. One transaction, so an interrupted run leaves
the database at ``20261130_01``.
"""

import sqlalchemy as sa
from alembic import op

revision = "20261201_01"
down_revision = "20261130_01"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "mail_template",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("logo", sa.LargeBinary(), nullable=True),
        sa.Column("logo_type", sa.String(32), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("id = 1", name="ck_mail_template_one_row"),
        sa.CheckConstraint(
            "(logo IS NULL) = (logo_type IS NULL)", name="ck_mail_template_logo_with_type"
        ),
    )


def downgrade() -> None:
    op.drop_table("mail_template")
