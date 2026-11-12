"""A person's one-time password link, mailed (Product 0.12 SP3, I6, D418, D420).

The link is made and its message queued in one transaction, so a person is never told of a link that
was not made, nor a link made for a message that was not queued. Mail not set up, or no address on
the person, is refused before the earlier link is replaced.
"""

from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ...errors import ApiError, api_error
from ...models.database import User
from ..identity import resets, sign_in
from ..identity.settings import IdentitySettings
from . import outbox, templates
from . import settings as mail_settings


def create_and_send(
    session: Session, settings: IdentitySettings, user_public_id: str, *, requested: bool = False
) -> tuple[str, datetime, str]:
    """Make the person's link and queue it for their address: ``(link, expires, address)``. A
    person with no password is welcomed, one with a password is told a new one was asked for.
    ``409 MAIL_NOT_SET_UP`` and ``409 NO_EMAIL`` leave the earlier link as it was. ``requested``: the
    person asked for it themselves, so it leaves an administrator's link valid (``resets.create_link``).
    Commits."""
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
        message = make(templates.product(session), user.name, url, settings.password_reset_hours)
        outbox.enqueue(session, settings, user.email, message, recipient_name=user.name)
        sent_to.append(user.email)

    url, expires_at = resets.create_link(
        session,
        settings,
        user_public_id,
        base=mail_settings.reset_link_base(session, settings),
        check=check,
        before_commit=queue,
        requested=requested,
    )
    return url, expires_at, sent_to[0]


def request_reset(
    session: Session,
    settings: IdentitySettings,
    email: str,
    address: str | None,
    now: datetime,
) -> int:
    """A person who forgot their password asks for a link by e-mail address (D420, 0.17 EM1).
    Returns the seconds still to wait, 0 when the request was taken. Taking it says nothing about
    whether anyone was written to: the ask is counted against the typed name and the address
    (slowed like sign-ins, D271) whatever it matches, and a link is sent only to an active person
    with a local password, a kept local sign-in and an address whose sign-in no administrator
    manages (SA1), one link each from this flow: an earlier link an administrator made stays valid. ``409
    MAIL_NOT_SET_UP`` when mail is not set up (it says nothing of any account). Commits."""
    mail_settings.require(session)
    wait = sign_in.seconds_to_wait(session, email, address, now, sign_in.RESET)
    if wait > 0:
        return wait
    sign_in.record_failure(session, email, address, now, sign_in.RESET)
    session.commit()
    typed = email.strip().lower()
    people = session.scalars(
        select(User.public_id).where(
            User.active.is_(True),
            User.password_hash.is_not(None),
            User.sign_in_managed.is_(False),
            func.lower(User.email) == typed,
        )
    ).all()
    for public_id in people:
        try:
            create_and_send(session, settings, public_id, requested=True)
        except ApiError:
            # No address, or local sign-in off for them: nothing is sent and nothing is said.
            session.rollback()
    return 0
