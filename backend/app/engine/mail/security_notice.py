"""A message to a person when their sign-in changes (0.17 SM1, D421).

The password was changed or reset, an authenticator app or a passkey was added or removed. The
message is queued in the transaction of the change, as the activation mail is, and says what changed
and when; it carries no secret, code or link that signs in. A person cannot switch these messages
off. Nothing is queued when mail is not set up or the person has no e-mail address: the change itself
is never held back by mail.
"""

from datetime import UTC, datetime

from sqlalchemy.orm import Session

from ...models.database import User
from ..identity.settings import IdentitySettings
from . import outbox, templates
from . import settings as mail_settings


def notify(
    session: Session,
    identity: IdentitySettings,
    user: User,
    change: str,
    *,
    now: datetime | None = None,
) -> bool:
    """Queue the message for ``change`` (a key of ``templates.SECURITY_CHANGES``) to ``user`` in the
    caller's transaction; ``False`` when nothing was queued (no mail settings, no address)."""
    if not user.email or mail_settings.load(session) is None:
        return False
    message = templates.security_change(
        templates.product(session), user.name, change, now or datetime.now(UTC)
    )
    outbox.enqueue(session, identity, user.email, message, now=now, recipient_name=user.name)
    return True
