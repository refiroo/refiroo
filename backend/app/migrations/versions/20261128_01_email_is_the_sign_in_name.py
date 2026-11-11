"""The e-mail is the sign-in name; the username is gone (0.17 EM1, PP-D14 to PP-D17).

An active person without an e-mail whose username is an address takes it as the e-mail. If an
active person still has none, or two people share an address ignoring case, the migration stops and
names them, so an operator fixes them first; nothing is invented (PP-D17). Then ``users.username``
and its index are dropped, ``ux_users_email`` (unique ignoring case, over the people who have one)
is created, and ``ck_users_active_email`` requires an address of every active person; a
deactivated person may have none (PP-D16). One transaction, so an interrupted run leaves the
database at ``20261127_02``. Past security events keep the username they recorded.

The downgrade restores a username from the e-mail (a placeholder for a person without one) and removes the new index and check.
"""

import sqlalchemy as sa
from alembic import op

revision = "20261128_01"
down_revision = "20261127_02"
branch_labels = None
depends_on = None

_ADDRESS = r"^[^@[:space:]]+@[^@[:space:]]+$"


def upgrade() -> None:
    connection = op.get_bind()
    connection.execute(
        sa.text("UPDATE users SET email = NULL WHERE email IS NOT NULL AND btrim(email) = ''")
    )
    connection.execute(
        sa.text(
            "UPDATE users SET email = username "
            f"WHERE active AND email IS NULL AND username ~ '{_ADDRESS}'"
        )
    )
    missing = (
        connection.execute(
            sa.text("SELECT username FROM users WHERE active AND email IS NULL ORDER BY id")
        )
        .scalars()
        .all()
    )
    shared = connection.execute(
        sa.text(
            "SELECT lower(email) AS address, string_agg(username, ', ' ORDER BY id) AS people "
            "FROM users WHERE email IS NOT NULL GROUP BY lower(email) HAVING count(*) > 1 "
            "ORDER BY lower(email)"
        )
    ).all()
    if missing or shared:
        lines = []
        if missing:
            lines.append(
                "Active people without an e-mail address (give each an address, or deactivate "
                "them): " + ", ".join(missing)
            )
        for address, people in shared:
            lines.append(f"People sharing the address {address} (give each their own): {people}")
        raise RuntimeError(
            "The e-mail address becomes the sign-in name, and the upgrade stops until this is "
            "fixed in the database. " + " | ".join(lines)
        )
    op.drop_index("ux_users_username", table_name="users")
    op.drop_column("users", "username")
    op.create_index(
        "ux_users_email",
        "users",
        [sa.text("lower(email)")],
        unique=True,
        postgresql_where=sa.text("email IS NOT NULL"),
    )
    op.create_check_constraint(
        "ck_users_active_email", "users", "active IS FALSE OR email IS NOT NULL"
    )


def downgrade() -> None:
    op.drop_constraint("ck_users_active_email", "users")
    op.drop_index("ux_users_email", table_name="users")
    op.add_column("users", sa.Column("username", sa.String(150), nullable=True))
    op.execute("UPDATE users SET username = coalesce(email, 'person-' || id)")
    op.alter_column("users", "username", nullable=False)
    op.create_index("ux_users_username", "users", [sa.text("lower(username)")], unique=True)
