"""Release-review fixes for identity and mail (R17-F20, R17-F22).

``sign_in_providers.emails_trusted``: whether a provider's e-mail addresses are taken as it sends
them. Existing providers are set to trusted, so the sign-ins that work keep working; a new provider
is not trusted until an administrator says so. ``mail_logos`` keeps each logo a message was rendered
with by the SHA-256 of its bytes; ``mail_template.logo_digest`` and ``mail_outbox.logo_digest`` refer
to it (the saved logo is copied in; messages already waiting have none and are sent with the current
logo, as before). The whole upgrade is one transaction, so an interrupted run leaves the database at the revision it started from.
"""

import sqlalchemy as sa
from alembic import op

revision = "20261203_01"
down_revision = "20261202_01"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "sign_in_providers",
        sa.Column("emails_trusted", sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    op.alter_column("sign_in_providers", "emails_trusted", server_default=None)
    op.create_table(
        "mail_logos",
        sa.Column("digest", sa.String(64), primary_key=True),
        sa.Column("logo", sa.LargeBinary(), nullable=False),
        sa.Column("logo_type", sa.String(32), nullable=False),
    )
    op.add_column("mail_template", sa.Column("logo_digest", sa.String(64), nullable=True))
    op.add_column("mail_outbox", sa.Column("logo_digest", sa.String(64), nullable=True))
    op.execute(
        "INSERT INTO mail_logos (digest, logo, logo_type) "
        "SELECT encode(sha256(logo), 'hex'), logo, logo_type FROM mail_template "
        "WHERE logo IS NOT NULL"
    )
    op.execute(
        "UPDATE mail_template SET logo_digest = encode(sha256(logo), 'hex') WHERE logo IS NOT NULL"
    )


def downgrade() -> None:
    op.drop_column("mail_outbox", "logo_digest")
    op.drop_column("mail_template", "logo_digest")
    op.drop_table("mail_logos")
    op.drop_column("sign_in_providers", "emails_trusted")
