"""A person's one-time password link, mailed (Product 0.12 SP3, D418).

The link is made and its message queued in one transaction, so a person is never told of a link that
was not made, nor a link made for a message that was not queued. Mail not set up, or no address on
the person, is refused before the earlier link is replaced.
"""

from datetime import datetime

from sqlalchemy.orm import Session

from ...errors import api_error
from ...models.database import User
from ..identity import resets
from ..identity.settings import IdentitySettings
from . import outbox, templates
from . import settings as mail_settings


def create_and_send(
    session: Session, settings: IdentitySettings, user_public_id: str, product: str
) -> tuple[str, datetime, str]:
    """Make the person's link and queue it for their address: ``(link, expires, address)``. A
    person with no password is welcomed, one with a password is told a new one was asked for.
    ``409 MAIL_NOT_SET_UP`` and ``409 NO_EMAIL`` leave the earlier link as it was. Commits."""
    mail_settings.require(session)
    sent_to: list[str] = []

    def check(user: User) -> None:
        if not user.email:
            raise api_error(
                409,
                "NO_EMAIL",
                f"{user.name} has no e-mail address; add one to the person, or pass the link on yourself",
            )

    def queue(user: User, url: str, has_password: bool) -> None:
        make = templates.password_reset if has_password else templates.activation
        message = make(product, user.name, url, settings.password_reset_hours)
        outbox.enqueue(session, settings, user.email, message)
        sent_to.append(user.email)

    url, expires_at = resets.create_link(
        session, settings, user_public_id, check=check, before_commit=queue
    )
    return url, expires_at, sent_to[0]
