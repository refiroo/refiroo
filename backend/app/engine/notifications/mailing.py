"""Inbox notices by mail (Product 0.12 M2, D432).

A person who switched it on (``users.notice_mail_since``) is mailed one plain-text message per
notice, naming the kind of event and linking to the application. The mail sender calls
``queue_notices`` at the start of each round: it queues the message of each notice that is unread,
unhandled (``mailed_at`` empty), made since the person switched it on and under 24 hours old, and
marks the notice handled in the same transaction, so a notice is mailed once. Without saved mail
settings nothing is queued or marked: notices wait, and are mailed once mail is saved if they are
still under 24 hours old. A notice of a person who switched it off, has no address or is inactive
is left alone. So is a notice of a kind the person switched off (``users.notice_mail_kinds_off``,
D434): only the mail stops; the notice stays in the inbox and is unchanged. Clients have no mail.

Each kind is mailed **at once** (the default), **in the digest** (``users.notice_mail_kinds_digest``)
or **not at all** (0.16 AO3, AO-D33). ``queue_digests`` runs in the same round: a person whose
``notice_digest_due_at`` has passed gets one message of their unread, unhandled notices of the digest
kinds, and the due time moves to the next 07:00 (daily) or Monday 07:00 (weekly) in their time zone.
The person row is locked ``FOR UPDATE SKIP LOCKED`` and the due time moves in the same commit, so
two processes make one digest. A digest names kinds, counts and links, and no name (D432, AO-D31).
"""

from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import ARRAY, Integer, all_, any_, func, literal, select, update
from sqlalchemy.orm import Session

from ...errors import api_error
from ...models.database import Job, Notification, User
from ..identity.settings import IdentitySettings
from ..mail import outbox, templates
from ..mail import settings as mail_settings
from . import kinds

# A notice older than this is no longer news: it is not mailed.
MAIL_WITHIN = timedelta(hours=24)
BATCH = 100

MAIL_NOT_SET_UP = "mail-not-set-up"
NO_EMAIL = "no-email"
NOT_A_PERSON = "not-a-person"


# How a kind reaches the person (AO-D33), and how often the digest comes (AO-D34).
NOW, DIGEST, OFF = "now", "digest", "off"
DELIVERIES = (NOW, DIGEST, OFF)
DAILY, WEEKLY = "daily", "weekly"
SEND_AT = time(7, 0)
# Digest lines before "and N more" (AO-D36).
DIGEST_LINES = 50


@dataclass(frozen=True)
class Digest:
    """The person's digest: how often, the time zone it is read in and when the next is due."""

    every: str
    time_zone: str
    next_at: datetime


@dataclass(frozen=True)
class NoticeMail:
    """A person's setting: ``enabled``, and ``reason`` it cannot work now (None when it can)."""

    enabled: bool
    reason: str | None
    email: str | None
    # Every kind of notice with how the person is mailed it: now, in the digest or off.
    kinds: tuple[tuple[str, str, str], ...] = ()
    digest: Digest | None = None


def _kind_states(user: User | None) -> tuple[tuple[str, str, str], ...]:
    off = set(user.notice_mail_kinds_off or ()) if user else set()
    digest = set(user.notice_mail_kinds_digest or ()) if user else set()
    return tuple(
        (kind, label, OFF if kind in off else DIGEST if kind in digest else NOW)
        for kind, label in kinds.NOTICE_KINDS
    )


def next_digest(every: str, time_zone: str, after: datetime) -> datetime:
    """The first 07:00 in ``time_zone`` after ``after`` (UTC): the next morning, or for ``weekly`` the
    next Monday. 07:00 is read on the zone's clock, so it holds across a daylight-saving change."""
    if every not in (DAILY, WEEKLY):
        raise ValueError(f"Not a digest frequency: {every}")
    zone = ZoneInfo(time_zone)
    day: date = after.astimezone(zone).date()
    step = 1 if every == DAILY else 7
    if every == WEEKLY:
        day += timedelta(days=(7 - day.weekday()) % 7)
    while (found := datetime.combine(day, SEND_AT, tzinfo=zone)) <= after:
        day += timedelta(days=step)
    return found.astimezone(UTC)


def state(session: Session, user: User | None) -> NoticeMail:
    """The setting of ``user`` (None: a client, who has no mail)."""
    if user is None:
        return NoticeMail(False, NOT_A_PERSON, None, _kind_states(None))
    if mail_settings.load(session) is None:
        reason = MAIL_NOT_SET_UP
    elif not user.email:
        reason = NO_EMAIL
    else:
        reason = None
    digest = (
        Digest(user.notice_digest_every, user.notice_digest_zone, user.notice_digest_due_at)
        if user.notice_digest_every
        else None
    )
    return NoticeMail(
        user.notice_mail_since is not None, reason, user.email or None, _kind_states(user), digest
    )


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
        if user.notice_digest_every:
            # The first digest after switching on, not one owed from before.
            user.notice_digest_due_at = next_digest(
                user.notice_digest_every, user.notice_digest_zone, now
            )
    session.commit()
    return state(session, user)


def set_digest(user: User, every: str, time_zone: str, now: datetime) -> None:
    """Choose how often the person's digest comes and the time zone 07:00 is read in. An unknown
    zone is ``422 UNKNOWN_TIME_ZONE`` and nothing changes. The next time is worked out from now
    unless the choice is the one already made. Does not commit."""
    try:
        ZoneInfo(time_zone)
    except KeyError, ValueError, OSError:
        raise api_error(
            422,
            "UNKNOWN_TIME_ZONE",
            f"Not a time zone: {time_zone}",
            {"timeZone": time_zone},
        ) from None
    if (user.notice_digest_every, user.notice_digest_zone) == (every, time_zone):
        return
    user.notice_digest_every = every
    user.notice_digest_zone = time_zone
    user.notice_digest_due_at = next_digest(every, time_zone, now)


def choose_kinds(session: Session, user: User, chosen: dict[str, str]) -> None:
    """Set how the named kinds reach the person (``now``, ``digest`` or ``off``); the others stay as
    they are. An unknown kind is ``422 UNKNOWN_NOTICE_KIND``, and ``digest`` for a person with no
    digest set is ``422 DIGEST_NOT_SET``; nothing changes. Does not commit. It may be done while mail
    is off or unavailable: it is the person's preference."""
    unknown = [kind for kind in chosen if kind not in kinds.LABELS]
    if unknown:
        raise api_error(
            422,
            "UNKNOWN_NOTICE_KIND",
            f"Not a kind of notice: {', '.join(unknown)}",
            {"kinds": unknown},
        )
    wanting = [kind for kind, how in chosen.items() if how == DIGEST]
    if wanting and not user.notice_digest_every:
        raise api_error(
            422,
            "DIGEST_NOT_SET",
            "Choose how often the digest comes before putting a kind in it",
            {"kinds": wanting},
        )
    off = set(user.notice_mail_kinds_off or ())
    digest = set(user.notice_mail_kinds_digest or ())
    for kind, how in chosen.items():
        (off.add if how == OFF else off.discard)(kind)
        (digest.add if how == DIGEST else digest.discard)(kind)
    # Stored in the order the kinds are listed, so a repeat changes nothing.
    user.notice_mail_kinds_off = [kind for kind, _ in kinds.NOTICE_KINDS if kind in off]
    user.notice_mail_kinds_digest = [kind for kind, _ in kinds.NOTICE_KINDS if kind in digest]


def queue_notices(
    session: Session, identity: IdentitySettings, now: datetime, *, batch: int = BATCH
) -> int:
    """Queue the mail of up to ``batch`` due notices and mark them handled; how many. Commits."""
    row = mail_settings.load(session)
    if row is None:
        return 0
    notices = session.execute(
        select(Notification, User.email, User.name)
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
            Notification.kind != all_(User.notice_mail_kinds_off),
            Notification.kind != all_(User.notice_mail_kinds_digest),
        )
        .order_by(Notification.sequence_id)
        .limit(batch)
        .with_for_update(of=Notification, skip_locked=True)
    ).all()
    if not notices:
        return 0
    product = templates.product(session)
    url = mail_settings.application_url(identity, row)
    for notification, address, name in notices:
        outbox.enqueue(
            session,
            identity,
            address,
            templates.notice(product, notification.kind, url),
            now=now,
            recipient_name=name,
        )
        notification.mailed_at = now
    session.commit()
    return len(notices)


def queue_digests(
    session: Session, identity: IdentitySettings, now: datetime, *, batch: int = BATCH
) -> int:
    """Queue the digest of up to ``batch`` people whose time has come; how many messages. One person
    per transaction: their unread, unhandled notices of the digest kinds made since they switched
    mail on are marked handled, the message queued and the next time set in one commit. Nothing to
    say makes no message and still moves the time. Without saved mail nothing is queued and nothing
    moves. Someone who switched mail off, has no address or is inactive is not made a digest."""
    row = mail_settings.load(session)
    if row is None:
        return 0
    eligible = (
        User.active.is_(True),
        User.email.is_not(None),
        User.email != "",
        User.notice_mail_since.is_not(None),
        User.notice_digest_due_at <= now,
    )
    ids = list(
        session.scalars(
            select(User.id)
            .where(*eligible)
            .order_by(User.notice_digest_due_at, User.id)
            .limit(batch)
        )
    )
    if not ids:
        session.rollback()
        return 0
    product = templates.product(session)
    url = mail_settings.application_url(identity, row)
    queued = 0
    for user_id in ids:
        user = session.scalar(
            select(User)
            .where(User.id == user_id, *eligible)
            .with_for_update(skip_locked=True)
            .execution_options(populate_existing=True)
        )
        if user is not None:
            queued += _queue_digest(session, identity, user, now, product, url)
        session.commit()
    return queued


def _queue_digest(
    session: Session, identity: IdentitySettings, user: User, now: datetime, product: str, url: str
) -> int:
    """One person's digest, in the caller's transaction (it commits); 1 if a message was queued."""
    waiting = select(Notification.sequence_id).where(
        Notification.user_id == user.id,
        Notification.mailed_at.is_(None),
        Notification.read_at.is_(None),
        Notification.created_at >= user.notice_mail_since,
        Notification.kind.in_(list(user.notice_mail_kinds_digest or ())),
    )
    # The set is locked and fixed first, so the counts, the lines and the marking are one set.
    ids = list(session.scalars(waiting.order_by(Notification.sequence_id).with_for_update()))
    queued = 0
    if ids:
        chosen = Notification.sequence_id == any_(literal(ids, ARRAY(Integer)))
        counts = dict(
            session.execute(
                select(Notification.kind, func.count()).where(chosen).group_by(Notification.kind)
            ).all()
        )
        lines = session.execute(
            select(
                Notification.id,
                Notification.kind,
                Notification.created_at,
                Notification.details["jobKind"].as_string(),
                Job.counts,
            )
            .outerjoin(
                Job, (Notification.subject_kind == "job") & (Job.id == Notification.subject_id)
            )
            .where(chosen)
            .order_by(Notification.sequence_id.desc())
            .limit(DIGEST_LINES)
        ).all()
        outbox.enqueue(
            session,
            identity,
            user.email,
            templates.digest(
                product,
                url,
                user.notice_digest_every,
                counts,
                [
                    templates.DigestLine(
                        notice_id,
                        kind,
                        created_at.astimezone(ZoneInfo(user.notice_digest_zone)),
                        job_kind,
                        job_counts,
                    )
                    for notice_id, kind, created_at, job_kind, job_counts in lines
                ],
            ),
            now=now,
            recipient_name=user.name,
        )
        session.execute(
            update(Notification)
            .where(chosen)
            .values(mailed_at=now)
            .execution_options(synchronize_session=False)
        )
        queued = 1
    user.notice_digest_due_at = next_digest(user.notice_digest_every, user.notice_digest_zone, now)
    return queued
