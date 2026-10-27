"""Inbox notices by mail (Product 0.12 M2, D432).

A person who switched it on (``users.notice_mail_since``) is mailed one plain-text message per
notice, naming the kind of event and linking to the application. The mail sender calls
``queue_notices`` at the start of each round: it queues the message of each notice that is unread,
unhandled (``mailed_at`` empty), made since the person switched it on and under 24 hours old, and
marks the notice handled in the same transaction, so a notice is mailed once. Without saved mail
settings nothing is queued or marked: notices wait, and are mailed once mail is saved if they are
still under 24 hours old. A notice of a person who switched it off, has no address or is inactive
is left alone. Clients have no mail.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from ...errors import api_error
from ...models.database import Notification, User
from ..identity.settings import IdentitySettings
from ..mail import outbox, templates
from ..mail import settings as mail_settings

# A notice older than this is no longer news: it is not mailed.
MAIL_WITHIN = timedelta(hours=24)
BATCH = 100

MAIL_NOT_SET_UP = "mail-not-set-up"
NO_EMAIL = "no-email"
NOT_A_PERSON = "not-a-person"


@dataclass(frozen=True)
class NoticeMail:
    """A person's setting: ``enabled``, and ``reason`` it cannot work now (None when it can)."""

    enabled: bool
    reason: str | None
    email: str | None


def state(session: Session, user: User | None) -> NoticeMail:
    """The setting of ``user`` (None: a client, who has no mail)."""
    if user is None:
        return NoticeMail(False, NOT_A_PERSON, None)
    if mail_settings.load(session) is None:
        reason = MAIL_NOT_SET_UP
    elif not user.email:
        reason = NO_EMAIL
    else:
        reason = None
    return NoticeMail(user.notice_mail_since is not None, reason, user.email or None)


def switch(session: Session, user: User, enabled: bool, now: datetime) -> NoticeMail:
    """Switch mail for the person's inbox on or off; commits. Switching on needs saved mail
    settings (``409 MAIL_NOT_SET_UP``) and an address on the person (``409 NO_EMAIL``), and
    only notices made from now on are mailed; switching on again keeps the first time. Switching
    off is always allowed and repeats harmlessly."""
    if not enabled:
        user.notice_mail_since = None
    elif user.notice_mail_since is None:
        found = state(session, user)
        if found.reason == MAIL_NOT_SET_UP:
            mail_settings.require(session)
        if found.reason == NO_EMAIL:
            raise api_error(
                409,
                "NO_EMAIL",
                "You have no e-mail address: ask an administrator to add one to your account",
            )
        user.notice_mail_since = now
    session.commit()
    return state(session, user)


def queue_notices(
    session: Session, identity: IdentitySettings, now: datetime, *, batch: int = BATCH
) -> int:
    """Queue the mail of up to ``batch`` due notices and mark them handled; how many. Commits."""
    row = mail_settings.load(session)
    if row is None:
        return 0
    notices = session.execute(
        select(Notification, User.email)
        .join(User, User.id == Notification.user_id)
        .where(
            Notification.mailed_at.is_(None),
            Notification.read_at.is_(None),
            Notification.created_at > now - MAIL_WITHIN,
            User.active.is_(True),
            User.email.is_not(None),
            User.email != "",
            User.notice_mail_since.is_not(None),
            Notification.created_at >= User.notice_mail_since,
        )
        .order_by(Notification.sequence_id)
        .limit(batch)
        .with_for_update(of=Notification, skip_locked=True)
    ).all()
    if not notices:
        return 0
    product = templates.product(session)
    url = mail_settings.application_url(identity, row)
    for notification, address in notices:
        outbox.enqueue(
            session, identity, address, templates.notice(product, notification.kind, url), now=now
        )
        notification.mailed_at = now
    session.commit()
    return len(notices)
