"""Setting a password: with a one-time link an administrator makes (D272), or by the person who is
signed in, who gives the current one (Product 0.12 I2). Either way the password meets D252's rules
and the person's other sessions end.
"""

from datetime import UTC, datetime, timedelta

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from ...errors import api_error
from ...models.database import PasswordResetLink, User, UserSession
from . import security_events, sessions
from .passwords import check_password, digest, hash_secret, new_token, verify_secret
from .settings import IdentitySettings
from .users import load_user


def _set(user: User, password: str, now: datetime) -> None:
    user.password_hash = hash_secret(password)
    user.version += 1
    user.updated_at = now


def create_link(
    session: Session, settings: IdentitySettings, user_public_id: str
) -> tuple[str, datetime]:
    """A one-time link that sets this person's password, replacing any earlier one; answered once.
    Commits."""
    user = load_user(session, user_public_id, for_update=True)
    now = datetime.now(UTC)
    session.execute(delete(PasswordResetLink).where(PasswordResetLink.user_id == user.id))
    token = new_token()
    expires_at = now + timedelta(hours=settings.password_reset_hours)
    session.add(
        PasswordResetLink(
            token_hash=digest(token), user_id=user.id, created_at=now, expires_at=expires_at
        )
    )
    # The link itself is never recorded (D317).
    security_events.record(
        session, "user", user.public_id, "password-link-created", about=[user.public_id],
        details={"expiresAt": expires_at.isoformat()},
    )  # fmt: skip
    session.commit()
    return f"{settings.issuer}/oauth/password?token={token}", expires_at


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
        )
    )


def use_link(session: Session, settings: IdentitySettings, token: str, password: str) -> bool:
    """Set the password a valid link names and end the person's sessions; ``False`` when the link
    is used, replaced, expired or unknown. A password the rules refuse raises
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
    check_password(password, user.username, settings.password_min_length)
    _set(user, password, now)
    link.used_at = now
    sessions.end_all(session, user.id, "passwordReset", now)
    security_events.record(
        session, "user", user.public_id, "password-set", about=[user.public_id],
        version=user.version, by=("user", user.id),
    )  # fmt: skip
    session.commit()
    return True


def change_password(
    session: Session,
    settings: IdentitySettings,
    user_public_id: str,
    session_public_id: str | None,
    current: str,
    new: str,
) -> None:
    """A signed-in person's new password: the current one must match (``422
    PASSWORD_INCORRECT``), the new one meet the rules; every other session ends. Commits."""
    user = load_user(session, user_public_id, for_update=True)
    if user.password_hash is None or not verify_secret(current, user.password_hash):
        raise api_error(422, "PASSWORD_INCORRECT", "The current password is not right")
    check_password(new, user.username, settings.password_min_length)
    now = datetime.now(UTC)
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
    session.commit()
