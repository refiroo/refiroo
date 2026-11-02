"""Signing a person in on the engine's own page (Product 0.12 I2, ADR-043).

The page checks a username and password and answers a one-time code bound to the browser's PKCE
challenge (``S256``) and the address it returns to; the browser exchanges the code with its
verifier for an access token and a session. Failed sign-ins are slowed per account and per address
with a growing wait, never locked (D252, D271): while a wait runs, an attempt is refused with the
time left before the password is checked.
"""

import base64
import hashlib
import logging
import re
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from functools import cache
from typing import Literal

from sqlalchemy import case, delete, func, select, tuple_
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from ...models.database import AuthorizationCode, SignInFailure, User, UserSession
from . import security_events, sessions
from .passwords import digest, hash_secret, new_token, verify_secret
from .settings import IdentitySettings

logger = logging.getLogger(__name__)

# The browser's built-in public client (D267): no secret, its redirect addresses from CORS_ORIGINS.
BROWSER_CLIENT_ID = "browser"
CODE_SECONDS = 60
# Failures that cost nothing, per account and per address, before each attempt waits (D271).
# A request for a reset link counts like a failure, under kinds of its own (I6, D420).
FREE_FAILURES: dict[str, int] = {
    "account": 5,
    "address": 20,
    "reset-account": 3,
    "reset-address": 20,
    "client-account": 5,
    "client-address": 20,
    "register-address": 10,
}
RESET = "reset-"
# A wrong client secret at the token endpoint counts against the client ID and the address (R).
CLIENT = "client-"
# An assistant's self-registration counts against the address (R-F10).
REGISTER = "register-"
LONGEST_WAIT_SECONDS = 15 * 60
# Counts lapse after this long without a failure.
FAILURES_LAPSE = timedelta(hours=24)
# RFC 7636 §4.1: 43 to 128 unreserved characters.
_VERIFIER = re.compile(r"^[A-Za-z0-9\-._~]{43,128}$")
_CHALLENGE = re.compile(r"^[A-Za-z0-9\-_]{43}$")


@cache
def _absent_hash() -> str:
    """Compared with when no account matches, so an unknown username takes as long as a wrong
    password."""
    return hash_secret(new_token())


def spend_verification(secret: str) -> None:
    """The work of checking a secret against a stored hash, for a name that matches no account or
    client, so the answer takes as long as a wrong secret and does not show which names exist."""
    verify_secret(secret, _absent_hash())


def wait_after(failures: int, kind: str) -> int:
    """Seconds an attempt waits after ``failures`` failures of an account or an address: none for
    the free ones, then 1 s doubling to at most 15 minutes."""
    beyond = failures - FREE_FAILURES[kind]
    if beyond <= 0:
        return 0
    return min(2 ** (beyond - 1), LONGEST_WAIT_SECONDS)


def _keys(username: str, address: str | None, scope: str = "") -> list[tuple[str, str]]:
    """What a failure is counted against: the account, when one is known, and the address. A
    ``scope`` (``RESET``) counts something else against the same two with kinds of its own."""
    keys = [(f"{scope}account", username.strip().casefold()[:320])] if username.strip() else []
    if address:
        keys.append((f"{scope}address", address[:320]))
    return keys


def seconds_to_wait(
    session: Session, username: str, address: str | None, now: datetime, scope: str = ""
) -> int:
    """How long the next attempt for this account or from this address must wait; 0 when it may
    go ahead."""
    rows = session.scalars(
        select(SignInFailure).where(
            tuple_(SignInFailure.kind, SignInFailure.key).in_(_keys(username, address, scope))
        )
    ).all()
    longest = 0
    for row in rows:
        if now - row.last_failure_at >= FAILURES_LAPSE:
            continue
        ends = row.last_failure_at + timedelta(seconds=wait_after(row.count, row.kind))
        longest = max(longest, int((ends - now).total_seconds() + 0.999))
    return longest


def record_failure(
    session: Session, username: str, address: str | None, now: datetime, scope: str = ""
) -> None:
    """Count a failed attempt against the account and the address (D271)."""
    for kind, key in _keys(username, address, scope):
        statement = insert(SignInFailure).values(kind=kind, key=key, count=1, last_failure_at=now)
        session.execute(
            statement.on_conflict_do_update(
                constraint="ux_sign_in_failures_kind_key",
                set_={
                    "count": case(
                        (SignInFailure.last_failure_at < now - FAILURES_LAPSE, 1),
                        else_=SignInFailure.count + 1,
                    ),
                    "last_failure_at": now,
                },
            )
        )


@dataclass(frozen=True)
class Refused:
    """Why a sign-in failed: the username or password (never which), or a wait still running."""

    reason: Literal["wrong", "slowed"]
    wait_seconds: int = 0


def check_password(
    session: Session,
    username: str,
    password: str,
    address: str | None,
    now: datetime,
    *,
    kept_only: bool = False,
    finish: bool = True,
) -> User | Refused:
    """The active person these credentials belong to, or why not. A failure is counted and logged;
    a success clears the account's count. With ``kept_only`` (local sign-in off, I3, D365) a person
    who does not keep local sign-in is refused as a wrong password is. With ``finish`` false (a
    second step may follow, I4b) a success is neither logged nor clears the count: ``complete``
    does, once the sign-in is whole, so guessing codes after a known password is still slowed.
    Commits."""
    wait = seconds_to_wait(session, username, address, now)
    if wait > 0:
        return Refused("slowed", wait)
    user = session.scalar(select(User).where(func.lower(User.username) == username.strip().lower()))
    usable = user is not None and user.active and (user.local_kept or not kept_only)
    stored = user.password_hash if usable else None
    matches = verify_secret(password, stored or _absent_hash())
    if user is None or stored is None or not matches:
        record_failure(session, username, address, now)
        # Checked, so bounded by the growing delay; a slowed attempt is only logged (D318).
        security_events.record(
            session, "sign-in", user.public_id if user else "unknown", "failed",
            about=[user.public_id] if user else [], by=None,
            details={"username": username[:150], "address": address},
        )  # fmt: skip
        session.commit()
        logger.warning(
            "A sign-in failed",
            extra={"event": "sign_in_failed", "username": username[:150], "address": address},
        )
        return Refused("wrong")
    if finish:
        complete(session, user, username, address)
        session.commit()
    return user


def complete(
    session: Session, user: User, username: str, address: str | None, *, method: str | None = None
) -> None:
    """A sign-in that is whole: the account's count of failures is cleared and the sign-in is a
    security event, with ``method`` when it was not by a password alone. The caller commits."""
    session.execute(
        delete(SignInFailure).where(
            SignInFailure.kind == "account", SignInFailure.key == username.strip().casefold()[:320]
        )
    )
    details = {"username": user.username, "address": address}
    if method:
        details["method"] = method
    security_events.record(
        session, "sign-in", user.public_id, "succeeded", about=[user.public_id],
        by=("user", user.id), details=details,
    )  # fmt: skip


def valid_challenge(challenge: str | None) -> bool:
    return challenge is not None and _CHALLENGE.match(challenge) is not None


def challenge_of(verifier: str) -> str:
    """The ``S256`` challenge a verifier answers (RFC 7636 §4.2)."""
    hashed = hashlib.sha256(verifier.encode("ascii")).digest()
    return base64.urlsafe_b64encode(hashed).rstrip(b"=").decode("ascii")


def issue_code(
    session: Session,
    user: User,
    *,
    redirect_uri: str,
    code_challenge: str,
    signed_in_with: str,
    now: datetime,
    provider_id_token: bytes | None = None,
    client_id: str = BROWSER_CLIENT_ID,
) -> str:
    """A one-time code for a person who has just proved who they are; with the provider's ID token
    (sealed) when its provider signs people out too (I4a). Commits."""
    code = new_token()
    session.add(
        AuthorizationCode(
            code_hash=digest(code),
            user_id=user.id,
            client_id=client_id,
            redirect_uri=redirect_uri,
            code_challenge=code_challenge,
            signed_in_with=signed_in_with,
            provider_id_token=provider_id_token,
            created_at=now,
            expires_at=now + timedelta(seconds=CODE_SECONDS),
        )
    )
    session.commit()
    return code


class CodeRefused(Exception):
    """A code that starts no session: unknown, expired, used, or not this browser's."""


def redeem_code(
    session: Session,
    settings: IdentitySettings,
    *,
    code: str,
    verifier: str,
    redirect_uri: str,
    user_agent: str | None,
    now: datetime | None = None,
    client_id: str = BROWSER_CLIENT_ID,
    application_id: int | None = None,
) -> tuple[UserSession, User, str]:
    """Exchange a code and its PKCE verifier for a new session and its first refresh token. A code
    presented a second time ends the session the first started (RFC 6749 §4.1.2). Commits."""
    now = now or datetime.now(UTC)
    row = session.execute(
        select(AuthorizationCode, User)
        .join(User, User.id == AuthorizationCode.user_id)
        .where(AuthorizationCode.code_hash == digest(code))
        .with_for_update(of=AuthorizationCode)
    ).one_or_none()
    if row is None:
        raise CodeRefused
    stored, user = row
    if stored.used_at is not None:
        if stored.session_id is not None:
            started = session.get(UserSession, stored.session_id, with_for_update=True)
            if started is not None:
                sessions.end(started, "reused", now)
                session.commit()
        raise CodeRefused
    stored.used_at = now
    held, stored.provider_id_token = stored.provider_id_token, None
    valid = (
        now < stored.expires_at
        and stored.client_id == client_id
        and stored.redirect_uri == redirect_uri
        and _VERIFIER.match(verifier) is not None
        and challenge_of(verifier) == stored.code_challenge
        and user.active
    )
    if not valid:
        session.commit()
        raise CodeRefused
    user_session, refresh_token = sessions.start(
        session,
        settings,
        user,
        signed_in_with=stored.signed_in_with,
        user_agent=user_agent,
        now=now,
        provider_id_token=held,
        application_id=application_id,
    )
    stored.session_id = user_session.id
    session.commit()
    return user_session, user, refresh_token
