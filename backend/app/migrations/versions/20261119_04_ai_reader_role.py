"""The role a derived sheet's query runs as: it can read nothing it is not granted (0.16 AP7)."""

from alembic import op
from sqlalchemy import text

revision = "20261119_04"
down_revision = "20261119_03"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """The role is the cluster's; a database whose owner may not create roles goes without, and a
    derived sheet is then refused with that reason."""
    connection = op.get_bind()
    may = connection.scalar(
        text("SELECT rolsuper OR rolcreaterole FROM pg_roles WHERE rolname = current_user")
    )
    if may:
        connection.execute(
            text(
                """
DO $$ BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'rdm_derived_reader') THEN
        CREATE ROLE rdm_derived_reader NOLOGIN;
    END IF;
    EXECUTE format('GRANT rdm_derived_reader TO %I', current_user);
END $$
"""
            )
        )


def downgrade() -> None:
    pass
