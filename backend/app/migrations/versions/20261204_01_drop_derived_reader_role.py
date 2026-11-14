"""Drop the role 20261119_04 made for derived sheets' queries: nothing runs as it or is granted to it
since the derived sheet plan was removed (0.17 SR3, ``draft_plan.py``'s dead constants)."""

from alembic import op
from sqlalchemy import text

revision = "20261204_01"
down_revision = "20261203_01"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """The role is the cluster's: an owner that may not manage roles leaves it, and so does a
    cluster where another database still holds something of it (it is then dropped by hand)."""
    connection = op.get_bind()
    may = connection.scalar(
        text("SELECT rolsuper OR rolcreaterole FROM pg_roles WHERE rolname = current_user")
    )
    if may:
        connection.execute(
            text(
                """
DO $$ BEGIN
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'rdm_derived_reader') THEN
        DROP ROLE rdm_derived_reader;
    END IF;
EXCEPTION WHEN dependent_objects_still_exist THEN
    NULL;
END $$
"""
            )
        )


def downgrade() -> None:
    pass
