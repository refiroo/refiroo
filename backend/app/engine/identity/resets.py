"""Setting a password: with a one-time link an administrator makes (D272), or by the person who is
signed in, who gives the current one (Product 0.12 I2). Either way the password meets D252's rules
and the person's other sessions end.
"""

from collections.abc import Callable
from datetime import UTC, datetime, timedelta

from sqlalchemy import delete, or_, select
from sqlalchemy.orm import Session

from ...errors import api_error
from ...models.database import PasswordResetLink, User, UserSession
from ..mail import security_notice
from . import managed, providers, security_events, sessions, sign_in
from .lookup import load_user
from .passwords import check_password, digest, hash_secret, new_token, verify_secret
from .settings import IdentitySettings


def _set(user: User, password: str, now: datetime) -> None:
    user.password_hash = hash_secret(password)
    user.version += 1
    user.updated_at = now


def create_link(
    session: Session,
    settings: IdentitySettings,
    user_public_id: str,
    *,
    base: str | None = None,
    check: Callable[[User], None] | None = None,
    before_commit: Callable[[User, str, bool], None] | None = None,
    requested: bool = False,
) -> tuple[str, datetime]:
    """A one-time link that sets this person's password, answered once. An administrator's link
    replaces every earlier one; a link the person asked for (``requested``) replaces only the
    earlier ones they asked for, so it never cancels an administrator's.
    Refused while local sign-in is off for a person who does not keep it (I3, D365). ``check``
    may refuse before the earlier link is replaced; ``before_commit`` gets the person, the link
    and whether the link was sent (SP3: it queues the mail), so both commit together. ``base`` is
    the address the token is added to (``mail.settings.reset_link_base``, I6); without it the link
    opens the engine's own page. Commits."""
    user = load_user(session, user_public_id, for_update=True)
    providers.refuse_while_off(session, user)
    if check is not None:
        check(user)
    now = datetime.now(UTC)
    replaced = delete(PasswordResetLink).where(PasswordResetLink.user_id == user.id)
    if requested:
        replaced = replaced.where(PasswordResetLink.requested.is_(True))
    session.execute(replaced)
    token = new_token()
    expires_at = now + timedelta(hours=settings.password_reset_hours)
    session.add(
        PasswordResetLink(
            token_hash=digest(token),
            user_id=user.id,
            created_at=now,
            expires_at=expires_at,
            requested=requested,
        )
    )
    # The link itself is never recorded (D317).
    security_events.record(
        session, "user", user.public_id, "password-link-created", about=[user.public_id],
        details={"expiresAt": expires_at.isoformat(), "sent": before_commit is not None},
    )  # fmt: skip
    page = base or f"{settings.issuer}/oauth/password"
    url = f"{page}?token={token}"
    if before_commit is not None:
        before_commit(user, url, user.password_hash is not None)
    session.commit()
    return url, expires_at


def link_user(session: Session, token: str) -> User | None:
    """The person a link sets the password of, while it is valid."""
    return session.scalar(
        select(User)
        .join(PasswordResetLink, PasswordResetLink.user_id == User.id)
        .where(
            PasswordResetLink.token_hash == digest(token),
            PasswordResetLink.used_at.is_(None),
            PasswordResetLink.expires_at > datetime.now(UTC),
            User.active.is_(True),
            # A link a person asked for is gone once an administrator manages their sign-in.
            or_(PasswordResetLink.requested.is_(False), User.sign_in_managed.is_(False)),
        )
    )


def use_link(session: Session, settings: IdentitySettings, token: str, password: str) -> bool:
    """Set the password a valid link names and end the person's sessions; ``False`` when the link
    is used, replaced, expired or unknown, or one the person asked for while an administrator manages
    their sign-in; using a link removes the person's other links. A password the rules refuse raises
    ``422 PASSWORD_REJECTED`` and leaves the link as it was. Commits."""
    now = datetime.now(UTC)
    row = session.execute(
        select(PasswordResetLink, User)
        .join(User, User.id == PasswordResetLink.user_id)
        .where(PasswordResetLink.token_hash == digest(token))
        .with_for_update()
    ).one_or_none()
    if row is None:
        return False
    link, user = row
    if link.used_at is not None or now >= link.expires_at or not user.active:
        return False
    if link.requested and user.sign_in_managed:
        return False
    check_password(password, user.email, settings.password_min_length)
    was_reset = user.password_hash is not None
    _set(user, password, now)
    link.used_at = now
    # Using one link ends the person's others, so a link asked for beside an administrator's cannot
    # set the password again.
    session.execute(
        delete(PasswordResetLink).where(
            PasswordResetLink.user_id == user.id, PasswordResetLink.id != link.id
        )
    )
    sessions.end_all(session, user.id, "passwordReset", now)
    security_events.record(
        session, "user", user.public_id, "password-set", about=[user.public_id],
        version=user.version, by=("user", user.id),
    )  # fmt: skip
    if was_reset:
        security_notice.notify(session, settings, user, "password-reset", now=now)
    session.commit()
    return True


def change_password(
    session: Session,
    settings: IdentitySettings,
    user_public_id: str,
    session_public_id: str | None,
    current: str,
    new: str,
    address: str | None = None,
) -> None:
    """A signed-in person's new password: the current one must match (``422
    PASSWORD_INCORRECT``), the new one meet the rules; every other session ends. A wrong current
    password is counted like a wrong sign-in (D271, ``429 SIGN_IN_SLOWED`` while a wait runs), so
    a stolen session cannot guess it. Refused ``403 SIGN_IN_MANAGED`` for a person an
    administrator manages (SA1). Commits."""
    user = load_user(session, user_public_id, for_update=True)
    managed.refuse(user)
    now = datetime.now(UTC)
    wait = sign_in.seconds_to_wait(session, user.email, address, now)
    if wait > 0:
        session.rollback()
        raise api_error(
            429,
            "SIGN_IN_SLOWED",
            "Too many wrong passwords for this account or from this address; try again later",
            {"waitSeconds": wait},
        )
    if user.password_hash is None or not verify_secret(current, user.password_hash):
        sign_in.record_failure(session, user.email, address, now)
        security_events.record(
            session, "sign-in", user.public_id, "failed", about=[user.public_id], by=None,
            details={"email": user.email, "address": address, "reason": "password-change"},
        )  # fmt: skip
        session.commit()
        raise api_error(422, "PASSWORD_INCORRECT", "The current password is not right")
    check_password(new, user.email, settings.password_min_length)
    _set(user, new, now)
    kept = None
    if session_public_id is not None:
        kept = session.scalar(
            select(UserSession.id).where(UserSession.public_id == session_public_id)
        )
    sessions.end_all(session, user.id, "passwordChanged", now, keep=kept)
    security_events.record(
        session, "user", user.public_id, "password-changed", about=[user.public_id],
        version=user.version, by=("user", user.id),
    )  # fmt: skip
    security_notice.notify(session, settings, user, "password-changed", now=now)
    session.commit()
