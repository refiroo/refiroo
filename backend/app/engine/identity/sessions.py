"""A person's browser sessions (Product 0.12 I2, ADR-043, D234, D251).

A session starts when the browser exchanges a sign-in's code and is renewed with a refresh token
held in an ``HttpOnly`` cookie. Each refresh token is used once: renewing answers a new one, and a
used one presented again ends the session, since only a copy can present it twice. A session ends
after ``SESSION_IDLE_HOURS`` without a renewal or ``SESSION_DAYS`` in all, when signed out, and
when the person is deactivated or their password is changed or reset, and when the sign-in provider
that started it is disabled (I3, D367). Its access tokens carry
``sid`` and are refused from the next request once it has ended.

An assistant's session (0.17 AS-D1, AS-D2) differs in two ways: any refresh token it was given
renews it, so several windows sharing one sign-in never end it, and its limits are the days set on
the Agent access page (``agent_limits``), not the browser's.
"""

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Literal

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from ...common.pagination import Page, PageRequest, integer_key, paginate_statement
from ...errors import api_error
from ...models.database import SessionRefreshToken, User, UserSession
from . import agent_limits, managed, security_events
from .passwords import digest, new_token
from .settings import IdentitySettings

# Why a session ended, as the API and the log name it.
EndReason = Literal[
    "signedOut",
    "signedOutEverywhere",
    "administrator",
    "reused",
    "expired",
    "deactivated",
    "passwordChanged",
    "passwordReset",
    "providerDisabled",
    "identityUnlinked",
    "applicationBlocked",
]

# A used refresh token presented again within this long of its use renews from its successor once
# (OAuth providers' "reuse interval"): a reload that moves on at once can cancel the renewal after
# the engine rotated the token but before the browser kept the new cookie.
REFRESH_REUSE_GRACE = timedelta(seconds=30)

_KEYS = (integer_key("sequenceId", UserSession.id, "id"),)


class SessionRefused(Exception):
    """A refresh token that renews nothing: unknown, used, or its session ended or lapsed."""


@dataclass(frozen=True)
class Ended:
    """A session just signed out: how it started and the provider's ID token it held, sealed."""

    signed_in_with: str
    provider_id_token: bytes | None


@dataclass(frozen=True)
class Renewed:
    user_session: UserSession
    user: User
    refresh_token: str


def is_open(user_session: UserSession, now: datetime) -> bool:
    return (
        user_session.ended_at is None
        and now < user_session.idle_ends_at
        and now < user_session.ends_at
    )


def _refresh_token(session: Session, user_session: UserSession, now: datetime) -> str:
    token = new_token()
    session.add(
        SessionRefreshToken(session_id=user_session.id, token_hash=digest(token), issued_at=now)
    )
    return token


def start(
    session: Session,
    settings: IdentitySettings,
    user: User,
    *,
    signed_in_with: str,
    user_agent: str | None,
    now: datetime,
    provider_id_token: bytes | None = None,
    application_id: int | None = None,
) -> tuple[UserSession, str]:
    """A new session for a person who has just signed in, with its first refresh token. The caller
    commits."""
    if application_id is None:
        ends_at = now + timedelta(days=settings.session_days)
        idle_ends_at = min(now + timedelta(hours=settings.session_idle_hours), ends_at)
    else:
        limits = agent_limits.load(session)
        ends_at = now + timedelta(days=limits.days)
        idle_ends_at = min(now + timedelta(days=limits.idle_days), ends_at)
    user_session = UserSession(
        user_id=user.id,
        signed_in_with=signed_in_with,
        user_agent=(user_agent or None) and user_agent[:512],
        provider_id_token=provider_id_token,
        agent_application_id=application_id,
        created_at=now,
        last_used_at=now,
        idle_ends_at=idle_ends_at,
        ends_at=ends_at,
    )
    session.add(user_session)
    session.flush()
    user.last_sign_in_at = now
    return user_session, _refresh_token(session, user_session, now)


def end(user_session: UserSession, reason: EndReason, now: datetime) -> None:
    if user_session.ended_at is None:
        user_session.ended_at = now
        user_session.ended_reason = reason
        user_session.provider_id_token = None


def end_provider_sessions(session: Session, user_id: int, provider_key: str, now: datetime) -> None:
    """End a person's open sessions that a sign-in provider started (its identity was unlinked)."""
    session.execute(
        update(UserSession)
        .where(
            UserSession.user_id == user_id,
            UserSession.signed_in_with == provider_key,
            UserSession.ended_at.is_(None),
        )
        .values(ended_at=now, ended_reason="identityUnlinked", provider_id_token=None),
        execution_options={"synchronize_session": "fetch"},
    )


def end_all(
    session: Session,
    user_id: int,
    reason: EndReason,
    now: datetime,
    *,
    keep: int | None = None,
) -> None:
    """End every open session of a person, but ``keep``. The caller commits."""
    statement = update(UserSession).where(
        UserSession.user_id == user_id, UserSession.ended_at.is_(None)
    )
    if keep is not None:
        statement = statement.where(UserSession.id != keep)
    session.execute(
        statement.values(ended_at=now, ended_reason=reason, provider_id_token=None),
        execution_options={"synchronize_session": "fetch"},
    )


def renew(
    session: Session,
    settings: IdentitySettings,
    refresh_token: str,
    now: datetime,
    *,
    application_id: int | None = None,
) -> Renewed:
    """Use a refresh token once: the session goes on with a new one. A used token presented again
    ends its session (D251), except within ``REFRESH_REUSE_GRACE`` of its use while its successor is
    unused: then the session renews from the successor. An assistant's session never ends for a used
    token (0.17 AS-D1): the windows that share its sign-in each renew from whichever token they
    hold. A token presented after the session lapsed also ends it. A token of a session started for
    another assistant, or for the browser, renews nothing and spends nothing (0.16 AG-D12). Commits
    either way."""
    row = session.execute(
        select(SessionRefreshToken, UserSession, User)
        .join(UserSession, UserSession.id == SessionRefreshToken.session_id)
        .join(User, User.id == UserSession.user_id)
        .where(SessionRefreshToken.token_hash == digest(refresh_token))
        .with_for_update(of=[SessionRefreshToken, UserSession])
    ).one_or_none()
    if row is None:
        raise SessionRefused
    token, user_session, user = row
    if user_session.agent_application_id != application_id:
        raise SessionRefused
    assistant = user_session.agent_application_id is not None
    if token.used_at is not None and not assistant:
        # The successor is the session's next token: renewing issues it as the token is used.
        successor = (
            session.scalar(
                select(SessionRefreshToken)
                .where(
                    SessionRefreshToken.session_id == user_session.id,
                    SessionRefreshToken.id > token.id,
                )
                .order_by(SessionRefreshToken.id)
                .limit(1)
                .with_for_update()
            )
            if now - token.used_at <= REFRESH_REUSE_GRACE and is_open(user_session, now)
            else None
        )
        if successor is None or successor.used_at is not None:
            end(user_session, "reused", now)
            session.commit()
            raise SessionRefused
        token = successor
    if not is_open(user_session, now) or not user.active:
        end(user_session, "expired" if user.active else "deactivated", now)
        session.commit()
        raise SessionRefused
    if token.used_at is None:
        token.used_at = now
    user_session.last_used_at = now
    idle = (
        timedelta(days=agent_limits.load(session).idle_days)
        if assistant
        else timedelta(hours=settings.session_idle_hours)
    )
    user_session.idle_ends_at = min(now + idle, user_session.ends_at)
    renewed = _refresh_token(session, user_session, now)
    session.commit()
    return Renewed(user_session, user, renewed)


def end_by_refresh_token(session: Session, refresh_token: str, reason: EndReason) -> Ended | None:
    """Sign out the session a refresh token belongs to (``/oauth/revoke``); an unknown token is
    ignored, as RFC 7009 asks. What the session held, when this ended it."""
    user_session = session.scalar(
        select(UserSession)
        .join(SessionRefreshToken, SessionRefreshToken.session_id == UserSession.id)
        .where(SessionRefreshToken.token_hash == digest(refresh_token))
        .with_for_update(of=UserSession)
    )
    if user_session is None or user_session.ended_at is not None:
        return None
    held = Ended(user_session.signed_in_with, user_session.provider_id_token)
    end(user_session, reason, datetime.now(UTC))
    session.commit()
    return held


def open_session_of_refresh_token(
    session: Session, refresh_token: str, now: datetime
) -> tuple[UserSession, User] | None:
    """The open session and person this refresh token (the browser's cookie) belongs to, without
    renewing it (never an assistant application's session, R-F1): the engine's own pages know who is signed in (the passkey page, I4c; the API
    reference, C1). None when the token is unknown or used, or its session or person is no longer
    open."""
    row = session.execute(
        select(SessionRefreshToken, UserSession, User)
        .join(UserSession, UserSession.id == SessionRefreshToken.session_id)
        .join(User, User.id == UserSession.user_id)
        .where(SessionRefreshToken.token_hash == digest(refresh_token))
    ).one_or_none()
    if row is None:
        return None
    token, user_session, user = row
    # An assistant's session (an application's, 0.16) is no browser sign-in: it never opens the
    # engine's own pages or the console's management token.
    if (
        token.used_at is None
        and user_session.agent_application_id is None
        and is_open(user_session, now)
        and user.active
    ):
        return user_session, user
    return None


def user_of_refresh_token(session: Session, refresh_token: str, now: datetime) -> User | None:
    """The person whose open session holds this refresh token; see
    ``open_session_of_refresh_token``."""
    held = open_session_of_refresh_token(session, refresh_token, now)
    return held[1] if held else None


def _user_id(session: Session, public_id: str) -> int:
    user_id = session.scalar(select(User.id).where(User.public_id == public_id))
    if user_id is None:
        raise api_error(404, "USER_NOT_FOUND", f"User '{public_id}' not found")
    return user_id


def end_session_of(session: Session, user_public_id: str, session_public_id: str) -> None:
    """Sign out one of a person's own sessions; another's, or none, is ``404 SESSION_NOT_FOUND``."""
    user_session = session.scalar(
        select(UserSession)
        .join(User, User.id == UserSession.user_id)
        .where(User.public_id == user_public_id, UserSession.public_id == session_public_id)
        .with_for_update(of=UserSession)
    )
    if user_session is None or not is_open(user_session, datetime.now(UTC)):
        raise api_error(404, "SESSION_NOT_FOUND", f"Session '{session_public_id}' not found")
    end(user_session, "signedOut", datetime.now(UTC))
    session.commit()


def end_sessions_of(
    session: Session,
    user_public_id: str,
    reason: EndReason,
    *,
    keep: str | None = None,
) -> None:
    """Sign a person out everywhere, but the session ``keep``."""
    user_id = _user_id(session, user_public_id)
    kept = (
        session.scalar(select(UserSession.id).where(UserSession.public_id == keep))
        if keep
        else None
    )
    end_all(session, user_id, reason, datetime.now(UTC), keep=kept)
    security_events.record(
        session, "user", user_public_id, "signed-out-everywhere", about=[user_public_id],
        details={"reason": reason, "keptSession": keep},
    )  # fmt: skip
    session.commit()


def end_own_session(
    session: Session, user_public_id: str, session_public_id: str, current: str | None
) -> None:
    """A signed-in person ends one of their own sessions. A person an administrator manages ends
    only the one they hold (signing out); another is ``403 SIGN_IN_MANAGED`` (SA1)."""
    if session_public_id != current:
        managed.refuse_for(session, user_public_id)
    end_session_of(session, user_public_id, session_public_id)


def end_own_sessions(session: Session, user_public_id: str) -> None:
    """A signed-in person signs out everywhere, this session included (J39.3); ``403
    SIGN_IN_MANAGED`` for a person an administrator manages (SA1)."""
    managed.refuse_for(session, user_public_id)
    end_sessions_of(session, user_public_id, "signedOutEverywhere")


def own_session_page(
    session: Session,
    user_public_id: str,
    current: str | None,
    *,
    page: PageRequest,
    page_size: int,
) -> Page[UserSession]:
    """A signed-in person's open sessions; a person an administrator manages sees only the one
    they hold (SA1)."""
    only = (current or "") if managed.is_managed(session, user_public_id) else None
    return session_page(session, user_public_id, page=page, page_size=page_size, only=only)


def session_page(
    session: Session,
    user_public_id: str,
    *,
    page: PageRequest,
    page_size: int,
    only: str | None = None,
) -> Page[UserSession]:
    """A person's open sessions in the order they started; ``only`` keeps the one with that ID."""
    now = datetime.now(UTC)
    statement = (
        select(UserSession)
        .join(User, User.id == UserSession.user_id)
        .where(
            User.public_id == user_public_id,
            UserSession.ended_at.is_(None),
            UserSession.idle_ends_at > now,
            UserSession.ends_at > now,
        )
    )
    if only is not None:
        statement = statement.where(UserSession.public_id == only)
    return paginate_statement(
        session,
        statement,
        keys=_KEYS,
        scope="sessions",
        filters={"user": user_public_id, "only": only},
        page=page,
        page_size=page_size,
        message="Session list cursor is invalid",
    )
