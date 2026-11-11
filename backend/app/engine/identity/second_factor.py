"""A second factor for local accounts: an authenticator app and recovery codes (Product 0.12 I4b,
D383–D388).

The app is TOTP as RFC 6238 specifies it: HMAC-SHA-1, six digits, 30-second steps, the step before
and after accepted for a clock that is a little off, and each step accepted once (``last_step``).
The secret is sealed with ``SECRETS_ENCRYPTION_KEY``; it is answered once, while the person sets it
up, as a key, an ``otpauth://`` address and a drawn QR code (``segno`` supplies the modules; the
page needs no script). Ten recovery codes, shown once and stored as an HMAC-SHA-256 under
``SECRETS_ENCRYPTION_KEY`` (a leaked table cannot be searched offline), each sign in once. A wrong code is counted in the same slowing as a wrong password (D271), whether it is typed on
the sign-in page or into Account. A person's factor is removed by them, with a code, unless the
instance requires one, or by a Security administrator (D387).
"""

import base64
import hashlib
import hmac
import re
import secrets
import struct
from dataclasses import dataclass
from datetime import datetime, timedelta
from urllib.parse import quote

import segno
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from ...common.sealing import seal, unseal
from ...errors import ApiError, api_error
from ...models.database import (
    SignInStep,
    User,
    UserRecoveryCode,
    UserSecondFactor,
)
from ..model.registry import resolve_model_snapshot
from . import passkeys, providers, security_events, sign_in
from .passwords import digest, new_token, verify_secret
from .settings import IdentitySettings

STEP_SECONDS = 30
DIGITS = 6
# A code of the step before or after is accepted: a clock a little off.
WINDOW = 1
SECRET_BYTES = 20
RECOVERY_CODES = 10
# No look-alikes (0 o, 1 l i), so a code read from paper is typed right.
_ALPHABET = "abcdefghjkmnpqrstuvwxyz23456789"
STEP_MINUTES = 5
# Time to copy the recovery codes before the sign-in goes on.
CODES_MINUTES = 15
_QUIET_ZONE = 4


def hotp(key: bytes, counter: int, digits: int = DIGITS) -> str:
    """RFC 4226: the ``digits``-digit code of an HMAC-SHA-1 counter."""
    mac = hmac.new(key, struct.pack(">Q", counter), hashlib.sha1).digest()
    offset = mac[-1] & 0x0F
    number = struct.unpack(">I", mac[offset : offset + 4])[0] & 0x7FFFFFFF
    return f"{number % 10**digits:0{digits}d}"


def totp_step(now: datetime) -> int:
    return int(now.timestamp()) // STEP_SECONDS


def accepted_step(key: bytes, code: str, now: datetime, last_step: int | None) -> int | None:
    """The time step ``code`` is right for, later than the last one used; none when it is wrong or
    already used. Spaces in the code are ignored."""
    typed = re.sub(r"\s", "", code)
    if len(typed) != DIGITS or not (typed.isascii() and typed.isdigit()):
        return None
    current = totp_step(now)
    found = None
    for step in range(current - WINDOW, current + WINDOW + 1):
        if hmac.compare_digest(hotp(key, step), typed) and (last_step is None or step > last_step):
            found = step
    return found


def product_name(session: Session, fallback: str) -> str:
    """The name the authenticator app labels the account with, and the pages carry: the default
    workspace's product."""
    try:
        return resolve_model_snapshot(session, None).model.product.name
    except ApiError:
        return fallback


def context(user_id: str) -> bytes:
    """What a person's sealed secret is bound to: their public ID."""
    return b"second-factor:" + user_id.encode()


def _context(user: User) -> bytes:
    return context(user.public_id)


def _key(settings: IdentitySettings, user: User, row: UserSecondFactor) -> bytes:
    return unseal(settings.encryption_key, row.secret, _context(user))


# --- what the person is shown ---------------------------------------------------------------------


def qr_svg(text: str) -> str:
    """The QR code of ``text`` as an inline SVG on a white ground with its quiet zone, dark modules
    in horizontal runs: it scales with its container and is the same in light and dark."""
    matrix = segno.make_qr(text, error="m").matrix
    size = len(matrix)
    total = size + 2 * _QUIET_ZONE
    runs = []
    for y, row in enumerate(matrix):
        x = 0
        while x < size:
            if row[x]:
                start = x
                while x < size and row[x]:
                    x += 1
                runs.append(f"M{start + _QUIET_ZONE} {y + _QUIET_ZONE}h{x - start}v1h-{x - start}z")
            else:
                x += 1
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {total} {total}" role="img" '
        'aria-label="QR code for the authenticator app" shape-rendering="crispEdges">'
        f'<rect width="{total}" height="{total}" fill="#fff"/>'
        f'<path fill="#1d1c1a" d="{"".join(runs)}"/></svg>'
    )


@dataclass(frozen=True)
class Enrolment:
    """What a person needs to set the app up: the key to type, the address a QR code carries and
    the drawing of it."""

    secret: str
    uri: str
    svg: str


def _enrolment(key: bytes, user: User, issuer: str) -> Enrolment:
    secret = base64.b32encode(key).decode().rstrip("=")
    label = f"{quote(issuer, safe='')}:{quote(user.email, safe='')}"
    uri = (
        f"otpauth://totp/{label}?secret={secret}&issuer={quote(issuer, safe='')}"
        f"&algorithm=SHA1&digits={DIGITS}&period={STEP_SECONDS}"
    )
    return Enrolment(secret, uri, qr_svg(uri))


@dataclass(frozen=True)
class Summary:
    confirmed_at: datetime
    recovery_left: int


def summaries(session: Session, user_ids: list[int]) -> dict[int, Summary]:
    """The confirmed second factors of some people, with the recovery codes each has left."""
    if not user_ids:
        return {}
    left = {
        user_id: count
        for user_id, count in session.execute(
            select(UserRecoveryCode.user_id, func.count())
            .where(UserRecoveryCode.user_id.in_(user_ids), UserRecoveryCode.used_at.is_(None))
            .group_by(UserRecoveryCode.user_id)
        )
    }
    return {
        row.user_id: Summary(row.confirmed_at, left.get(row.user_id, 0))
        for row in session.scalars(
            select(UserSecondFactor).where(
                UserSecondFactor.user_id.in_(user_ids), UserSecondFactor.confirmed_at.is_not(None)
            )
        )
    }


def summary(session: Session, user: User) -> Summary | None:
    return summaries(session, [user.id]).get(user.id)


def _row(session: Session, user: User, *, lock: bool = False) -> UserSecondFactor | None:
    statement = select(UserSecondFactor).where(UserSecondFactor.user_id == user.id)
    return session.scalar(statement.with_for_update() if lock else statement)


# --- setting it up ----------------------------------------------------------------------------------


def begin(
    session: Session,
    settings: IdentitySettings,
    user: User,
    issuer: str,
    now: datetime,
    *,
    restart: bool = True,
) -> Enrolment:
    """A secret for the person to set up, replacing one not yet confirmed (a new one unless
    ``restart`` is false, which re-reads it for a page shown again). ``409 SECOND_FACTOR_EXISTS``
    when they have one. Commits."""
    if user.password_hash is None:
        raise api_error(
            409,
            "PASSWORD_REQUIRED",
            "A second factor goes with a password; a person who signs in with a provider has none",
        )
    row = _row(session, user, lock=True)
    if row is not None and row.confirmed_at is not None:
        raise api_error(409, "SECOND_FACTOR_EXISTS", "A second factor is already set up")
    if row is not None and not restart:
        return _enrolment(_key(settings, user, row), user, issuer)
    key = secrets.token_bytes(SECRET_BYTES)
    sealed = seal(settings.encryption_key, key, _context(user))
    if row is None:
        session.add(UserSecondFactor(user_id=user.id, secret=sealed, created_at=now))
    else:
        row.secret, row.created_at = sealed, now
    session.commit()
    return _enrolment(key, user, issuer)


class CodeRefused(Exception):
    """A code that does not sign in or confirm: ``wrong`` (also a used one), or ``slowed`` while
    the account's or address's wait runs (D271)."""

    def __init__(self, reason: str, wait_seconds: int = 0):
        super().__init__(reason)
        self.reason = reason
        self.wait_seconds = wait_seconds


def _is_app_code(code: str) -> bool:
    return len(re.sub(r"\s", "", code)) == DIGITS


def _normal(code: str) -> str:
    return re.sub(r"[\s-]", "", code).lower()


def _recovery_hash(settings: IdentitySettings, code: str) -> str:
    """A recovery code as stored: keyed, so the table alone does not let its 60-bit codes be
    searched offline."""
    return hmac.new(
        settings.encryption_key, b"recovery-code:" + _normal(code).encode(), hashlib.sha256
    ).hexdigest()


def _use_recovery(
    session: Session, settings: IdentitySettings, user: User, code: str, now: datetime
) -> bool:
    row = session.scalar(
        select(UserRecoveryCode)
        .where(
            UserRecoveryCode.user_id == user.id,
            UserRecoveryCode.code_hash == _recovery_hash(settings, code),
            UserRecoveryCode.used_at.is_(None),
        )
        .with_for_update()
    )
    if row is None:
        return False
    row.used_at = now
    return True


def _use_app_code(
    session: Session, settings: IdentitySettings, user: User, code: str, now: datetime,
    *, confirming: bool,
) -> bool:  # fmt: skip
    row = _row(session, user, lock=True)
    if row is None or (row.confirmed_at is None) != confirming:
        return False
    step = accepted_step(_key(settings, user, row), code, now, row.last_step)
    if step is None:
        return False
    row.last_step = step
    return True


def check(
    session: Session,
    settings: IdentitySettings,
    user: User,
    code: str,
    *,
    now: datetime,
    address: str | None,
    kind: str = "any",
) -> None:
    """Accept ``code`` once, or raise ``CodeRefused``. ``kind``: ``app`` (a code from the app),
    ``recovery`` (a recovery code), ``any`` (the app's by its six digits, else a recovery code) or
    ``confirm`` (the app's, for a factor not yet confirmed). A wrong code is counted and logged
    like a wrong password; a right one is used up. Commits."""
    wait = sign_in.seconds_to_wait(session, user.email, address, now)
    if wait > 0:
        raise CodeRefused("slowed", wait)
    if kind == "any":
        kind = "app" if _is_app_code(code) else "recovery"
    accepted = (
        _use_recovery(session, settings, user, code, now)
        if kind == "recovery"
        else _use_app_code(session, settings, user, code, now, confirming=kind == "confirm")
    )
    if not accepted:
        sign_in.record_failure(session, user.email, address, now)
        security_events.record(
            session, "sign-in", user.public_id, "failed", about=[user.public_id], by=None,
            details={"email": user.email, "address": address, "reason": "code"},
        )  # fmt: skip
        session.commit()
        raise CodeRefused("wrong")
    session.commit()


def _refused(failure: CodeRefused) -> ApiError:
    if failure.reason == "slowed":
        return api_error(
            429,
            "SIGN_IN_SLOWED",
            "Too many wrong codes for this account or from this address; try again later",
            {"waitSeconds": failure.wait_seconds},
        )
    return api_error(422, "CODE_INCORRECT", "That code is not right, or was already used")


def _new_codes(
    session: Session, settings: IdentitySettings, user: User, now: datetime
) -> list[str]:
    """Ten recovery codes, the earlier ones void; the plain codes, once. The caller commits."""
    session.execute(delete(UserRecoveryCode).where(UserRecoveryCode.user_id == user.id))
    plain = ["-".join(_group() for _ in range(3)) for _ in range(RECOVERY_CODES)]
    session.add_all(
        UserRecoveryCode(user_id=user.id, code_hash=_recovery_hash(settings, code), created_at=now)
        for code in plain
    )
    return plain


def _group() -> str:
    return "".join(secrets.choice(_ALPHABET) for _ in range(4))


def confirm(
    session: Session,
    settings: IdentitySettings,
    user: User,
    code: str,
    *,
    now: datetime,
    address: str | None,
    api: bool = True,
) -> list[str]:
    """The person proved the app works: the factor is on and ten recovery codes are made, answered
    once. ``404 SECOND_FACTOR_NOT_FOUND`` without a secret to confirm. Commits."""
    row = _row(session, user)
    if row is None or row.confirmed_at is not None:
        raise api_error(404, "SECOND_FACTOR_NOT_FOUND", "No second factor is being set up")
    try:
        check(session, settings, user, code, now=now, address=address, kind="confirm")
    except CodeRefused as failure:
        if api:
            raise _refused(failure) from None
        raise
    row = _row(session, user, lock=True)
    assert row is not None
    row.confirmed_at = now
    codes = _new_codes(session, settings, user, now)
    security_events.record(
        session, "user", user.public_id, "second-factor-added", about=[user.public_id],
        details={"method": "authenticator-app"},
    )  # fmt: skip
    session.commit()
    return codes


def new_recovery_codes(
    session: Session,
    settings: IdentitySettings,
    user: User,
    code: str,
    *,
    now: datetime,
    address: str | None,
) -> list[str]:
    """Ten new recovery codes, the old ones void, on a code from the app or a recovery code."""
    _confirmed(session, user)
    try:
        check(session, settings, user, code, now=now, address=address)
    except CodeRefused as failure:
        raise _refused(failure) from None
    codes = _new_codes(session, settings, user, now)
    security_events.record(
        session, "user", user.public_id, "recovery-codes-created", about=[user.public_id],
        details={"count": RECOVERY_CODES},
    )  # fmt: skip
    session.commit()
    return codes


def _confirmed(session: Session, user: User) -> UserSecondFactor:
    row = _row(session, user)
    if row is None or row.confirmed_at is None:
        raise api_error(404, "SECOND_FACTOR_NOT_FOUND", "No second factor is set up")
    return row


def remove(
    session: Session,
    settings: IdentitySettings,
    user: User,
    code: str,
    *,
    now: datetime,
    address: str | None,
) -> None:
    """The person removes their own factor with a code, unless the instance requires one
    (``409 SECOND_FACTOR_REQUIRED``)."""
    _confirmed(session, user)
    if providers.local_state(session).second_factor_required and not passkeys.has_any(
        session, user
    ):
        raise api_error(
            409,
            "SECOND_FACTOR_REQUIRED",
            "This instance requires a second factor with a password; add a passkey first, or "
            "ask a security administrator to remove yours",
        )
    try:
        check(session, settings, user, code, now=now, address=address)
    except CodeRefused as failure:
        raise _refused(failure) from None
    _delete(session, user, "self")
    session.commit()


def prove(
    session: Session,
    settings: IdentitySettings,
    user: User,
    proof: str | None,
    *,
    now: datetime,
    address: str | None,
) -> None:
    """Ask a signed-in person to prove it is them again before something that lowers their
    protection (removing a passkey): their password, or a code from the app or a recovery code.
    A wrong proof is counted like a wrong password (D271); ``422 PROOF_REQUIRED`` without one.
    Nothing is asked of a person who has neither a password nor an app."""
    has_app = summary(session, user) is not None
    if user.password_hash is None and not has_app:
        return
    if not proof:
        raise api_error(
            422, "PROOF_REQUIRED", "Type your password, or a code from your authenticator app"
        )
    wait = sign_in.seconds_to_wait(session, user.email, address, now)
    if wait > 0:
        raise _refused(CodeRefused("slowed", wait))
    if user.password_hash is not None and verify_secret(proof, user.password_hash):
        return
    if has_app:
        try:
            check(session, settings, user, proof, now=now, address=address)
        except CodeRefused as failure:
            raise _refused(failure) from None
        return
    sign_in.record_failure(session, user.email, address, now)
    security_events.record(
        session, "sign-in", user.public_id, "failed", about=[user.public_id], by=None,
        details={"email": user.email, "address": address, "reason": "proof"},
    )  # fmt: skip
    session.commit()
    raise api_error(422, "CODE_INCORRECT", "That is not right")


def remove_for(session: Session, user: User) -> None:
    """A Security administrator removes a person's factor, with its recovery codes (D387)."""
    _confirmed(session, user)
    _delete(session, user, "administrator")
    session.commit()


def _delete(session: Session, user: User, by: str) -> None:
    session.execute(delete(UserRecoveryCode).where(UserRecoveryCode.user_id == user.id))
    session.execute(delete(UserSecondFactor).where(UserSecondFactor.user_id == user.id))
    security_events.record(
        session, "user", user.public_id, "second-factor-removed", about=[user.public_id],
        details={"by": by},
    )  # fmt: skip


# --- the sign-in page's second step -----------------------------------------------------------------


def required_step(session: Session, user: User) -> str | None:
    """What the person's password leads to: ``code`` (they have a second factor, an authenticator
    app or a passkey), ``setup`` (the instance requires one and they have none), or none (D388)."""
    row = _row(session, user)
    if (row is not None and row.confirmed_at is not None) or passkeys.has_any(session, user):
        return "code"
    return "setup" if providers.local_state(session).second_factor_required else None


def open_step(
    session: Session, user: User, request: dict[str, str], stage: str, now: datetime
) -> str:
    """Keep a sign-in between its password and its second step; the token goes in the page's form.
    Commits."""
    session.execute(delete(SignInStep).where(SignInStep.expires_at < now - timedelta(days=1)))
    token = new_token()
    session.add(
        SignInStep(
            token_hash=digest(token),
            user_id=user.id,
            stage=stage,
            request=request,
            created_at=now,
            expires_at=now + timedelta(minutes=STEP_MINUTES),
        )
    )
    session.commit()
    return token


def load_step(session: Session, token: str, now: datetime) -> tuple[SignInStep, User] | None:
    """The open step a token names and its person; none when unknown, used or expired."""
    row = session.execute(
        select(SignInStep, User)
        .join(User, User.id == SignInStep.user_id)
        .where(SignInStep.token_hash == digest(token))
        .with_for_update(of=SignInStep)
    ).one_or_none()
    if row is None:
        return None
    step, user = row
    if step.used_at is not None or step.expires_at <= now or not user.active:
        return None
    return step, user


def advance(step: SignInStep, stage: str, now: datetime) -> None:
    step.stage = stage
    step.expires_at = now + timedelta(minutes=CODES_MINUTES)


def finish_step(
    session: Session, step: SignInStep, user: User, address: str | None, now: datetime
) -> None:
    """The sign-in is whole: the step is used and the password sign-in is logged. The caller
    commits."""
    step.used_at = now
    sign_in.complete(session, user, user.email, address)
