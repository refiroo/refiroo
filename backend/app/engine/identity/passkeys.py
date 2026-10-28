"""Passkeys for local accounts (Product 0.12 I4c, D389–D394).

A passkey is a WebAuthn credential the person's device holds; the engine keeps its public key. Both
ceremonies run on the engine's own pages, which belong to ``PUBLIC_URL``'s host, the relying party
(D392): a passkey made there works there and nowhere else, so a look-alike page cannot ask for it.
``webauthn`` (py_webauthn) verifies the browser's answers (D391): no attestation is asked, and the
user must be verified, so a passkey on its own is possession and the device's fingerprint, face or
PIN. A ceremony's challenge is kept with the sign-in steps (``sign_in_steps``, single use, five
minutes), so any process finishes it: ``passkey-add`` for a person with a session registering one,
``passkey-in`` for signing in with a passkey alone (no one is known yet), and the password's own
``code`` step when a passkey is the second step. A wrong answer is counted in the same slowing as a
wrong password (D271).
"""

import json
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any
from urllib.parse import urlsplit

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session
from webauthn import (
    generate_authentication_options,
    generate_registration_options,
    options_to_json,
    verify_authentication_response,
    verify_registration_response,
)
from webauthn.helpers import base64url_to_bytes
from webauthn.helpers.exceptions import WebAuthnException
from webauthn.helpers.structs import (
    AttestationConveyancePreference,
    AuthenticatorSelectionCriteria,
    PublicKeyCredentialDescriptor,
    ResidentKeyRequirement,
    UserVerificationRequirement,
)

from ...common.pagination import Page, PageRequest, integer_key, paginate_statement
from ...errors import api_error
from ...models.database import SignInStep, User, UserPasskey, UserSecondFactor
from . import providers, security_events, sign_in
from .passwords import digest, new_token
from .settings import IdentitySettings

CEREMONY_MINUTES = 5
MAX_PASSKEYS = 25
# Passkey-alone ceremonies wait in the database before anyone is known, so an open endpoint could
# fill it; this many unexpired at once, then the engine answers 429 until they lapse.
MAX_OPEN_CEREMONIES = 2000
ADD = "passkey-add"
ALONE = "passkey-in"
SECOND = "code"
_KEYS = (integer_key("sequenceId", UserPasskey.id, "id"),)


class PasskeyRefused(Exception):
    """A ceremony that cannot go on: ``message`` is for the person, ``status`` the answer's."""

    def __init__(self, message: str, status: int = 401, wait_seconds: int = 0):
        super().__init__(message)
        self.message = message
        self.status = status
        self.wait_seconds = wait_seconds


@dataclass(frozen=True)
class Authenticated:
    """Who a passkey signed in, and the step it ended: its browser request and which way."""

    user: User
    request: dict[str, str]
    second_step: bool
    step: SignInStep


def relying_party(settings: IdentitySettings) -> tuple[str, str]:
    """The relying party's ID, the host of ``PUBLIC_URL``, and the origin its pages are served from
    (D392)."""
    parts = urlsplit(settings.issuer)
    return parts.hostname or "", f"{parts.scheme}://{parts.netloc}"


def _count(session: Session, user_id: int) -> int:
    return (
        session.scalar(
            select(func.count()).select_from(UserPasskey).where(UserPasskey.user_id == user_id)
        )
        or 0
    )


def counts(session: Session, user_ids: list[int]) -> dict[int, int]:
    """How many passkeys each person has."""
    if not user_ids:
        return {}
    return {
        user_id: count
        for user_id, count in session.execute(
            select(UserPasskey.user_id, func.count())
            .where(UserPasskey.user_id.in_(user_ids))
            .group_by(UserPasskey.user_id)
        )
    }


def any_exist(session: Session) -> bool:
    """Whether anyone has a passkey: the sign-in page offers the button only then."""
    return session.scalar(select(UserPasskey.id).limit(1)) is not None


def has_any(session: Session, user: User) -> bool:
    return _count(session, user.id) > 0


def passkey_page(
    session: Session, user: User, *, page: PageRequest, page_size: int
) -> Page[UserPasskey]:
    """A person's passkeys in the order they were made."""
    return paginate_statement(
        session,
        select(UserPasskey).where(UserPasskey.user_id == user.id),
        keys=_KEYS,
        scope="passkeys",
        filters={"user": user.public_id},
        page=page,
        page_size=page_size,
        message="Passkey list cursor is invalid",
    )


def _load(session: Session, user: User, public_id: str) -> UserPasskey:
    row = session.scalar(
        select(UserPasskey)
        .where(UserPasskey.user_id == user.id, UserPasskey.public_id == public_id)
        .with_for_update()
    )
    if row is None:
        raise api_error(404, "PASSKEY_NOT_FOUND", f"Passkey '{public_id}' not found")
    return row


def _clean(name: str | None) -> str:
    return (name or "").strip()[:100] or "Passkey"


def rename(session: Session, user: User, public_id: str, name: str) -> UserPasskey:
    row = _load(session, user, public_id)
    row.name = _clean(name)
    security_events.record(
        session, "user", user.public_id, "passkey-renamed", about=[user.public_id],
        details={"name": row.name},
    )  # fmt: skip
    session.commit()
    return row


def remove(session: Session, user: User, public_id: str, *, by: str) -> None:
    """Remove a passkey: the person's own (refused while the instance requires a second factor and
    it is their last one, ``409 SECOND_FACTOR_REQUIRED``) or an administrator's (D394)."""
    row = _load(session, user, public_id)
    has_app = session.scalar(
        select(UserSecondFactor.id).where(
            UserSecondFactor.user_id == user.id, UserSecondFactor.confirmed_at.is_not(None)
        )
    )
    if (
        by == "self"
        and providers.local_state(session).second_factor_required
        and _count(session, user.id) == 1
        and has_app is None
    ):
        raise api_error(
            409,
            "SECOND_FACTOR_REQUIRED",
            "This instance requires a second factor with a password, and this is your last one; "
            "add another passkey or set up an authenticator app first",
        )
    session.execute(delete(UserPasskey).where(UserPasskey.id == row.id))
    security_events.record(
        session, "user", user.public_id, "passkey-removed", about=[user.public_id],
        details={"name": row.name, "by": by},
    )  # fmt: skip
    session.commit()


# --- the ceremonies ---------------------------------------------------------------------------------


def _open(
    session: Session,
    stage: str,
    challenge: bytes,
    request: dict[str, str],
    now: datetime,
    user: User | None = None,
) -> str:
    session.execute(delete(SignInStep).where(SignInStep.expires_at < now - timedelta(days=1)))
    token = new_token()
    session.add(
        SignInStep(
            token_hash=digest(token),
            user_id=user.id if user else None,
            stage=stage,
            request=request,
            challenge=challenge,
            created_at=now,
            expires_at=now + timedelta(minutes=CEREMONY_MINUTES),
        )
    )
    session.commit()
    return token


def _ceremony(session: Session, token: str, stages: tuple[str, ...], now: datetime) -> SignInStep:
    row = session.scalar(
        select(SignInStep).where(SignInStep.token_hash == digest(token)).with_for_update()
    )
    if (
        row is None
        or row.stage not in stages
        or row.used_at is not None
        or row.expires_at <= now
        or row.challenge is None
    ):
        raise PasskeyRefused(
            "This took longer than five minutes, or was already used. Start again.", status=410
        )
    return row


def begin_registration(
    session: Session, settings: IdentitySettings, user: User, product: str, now: datetime
) -> tuple[str, dict[str, Any]]:
    """The browser's creation options for a new passkey of ``user``, with the ceremony's token."""
    if user.password_hash is None:
        raise api_error(
            409,
            "PASSWORD_REQUIRED",
            "A passkey goes with a password; a person who signs in with a provider has none",
        )
    if _count(session, user.id) >= MAX_PASSKEYS:
        raise api_error(409, "TOO_MANY_PASSKEYS", f"A person has at most {MAX_PASSKEYS} passkeys")
    rp_id, _ = relying_party(settings)
    held = session.scalars(select(UserPasskey.credential_id).where(UserPasskey.user_id == user.id))
    options = generate_registration_options(
        rp_id=rp_id,
        rp_name=product,
        user_id=user.public_id.encode(),
        user_name=user.username,
        user_display_name=user.name,
        attestation=AttestationConveyancePreference.NONE,
        authenticator_selection=AuthenticatorSelectionCriteria(
            resident_key=ResidentKeyRequirement.REQUIRED,
            user_verification=UserVerificationRequirement.REQUIRED,
        ),
        exclude_credentials=[PublicKeyCredentialDescriptor(id=held_id) for held_id in held],
    )
    token = _open(session, ADD, options.challenge, {}, now, user)
    return token, json.loads(options_to_json(options))


def finish_registration(
    session: Session,
    settings: IdentitySettings,
    user: User,
    token: str,
    credential: dict[str, Any],
    name: str | None,
    now: datetime,
) -> UserPasskey:
    """Check the browser's new credential and keep it as ``user``'s passkey. Commits."""
    row = _ceremony(session, token, (ADD,), now)
    if row.user_id != user.id:
        raise PasskeyRefused("This passkey was started for another person.", status=403)
    rp_id, origin = relying_party(settings)
    row.used_at = now
    session.commit()
    try:
        verified = verify_registration_response(
            credential=credential,
            expected_challenge=row.challenge,
            expected_rp_id=rp_id,
            expected_origin=origin,
            require_user_verification=True,
        )
    except (WebAuthnException, ValueError, KeyError, TypeError) as failure:
        raise PasskeyRefused(
            "The browser's answer could not be confirmed: the passkey must be made here, "
            f"with your fingerprint, face or PIN ({failure}).",
            status=422,
        ) from None
    if session.scalar(
        select(UserPasskey.id).where(UserPasskey.credential_id == verified.credential_id)
    ):
        raise PasskeyRefused("This passkey is already registered.", status=409)
    passkey = UserPasskey(
        user_id=user.id,
        credential_id=verified.credential_id,
        public_key=verified.credential_public_key,
        sign_count=verified.sign_count,
        name=_clean(name),
        created_at=now,
    )
    session.add(passkey)
    security_events.record(
        session, "user", user.public_id, "passkey-added", about=[user.public_id],
        details={"name": passkey.name},
    )  # fmt: skip
    session.commit()
    return passkey


def begin_authentication(
    session: Session,
    settings: IdentitySettings,
    now: datetime,
    *,
    step: tuple[SignInStep, User] | None = None,
    request: dict[str, str] | None = None,
) -> tuple[str, dict[str, Any]]:
    """The browser's request options: for the second step of a password sign-in (``step``, the
    person's own passkeys) or for a passkey alone (``request``, the browser's authorization
    request, no one known yet). Answers the ceremony's token, the step's own for the first."""
    rp_id, _ = relying_party(settings)
    allowed: list[PublicKeyCredentialDescriptor] | None = None
    if step is not None:
        row, user = step
        held = list(
            session.scalars(select(UserPasskey.credential_id).where(UserPasskey.user_id == user.id))
        )
        if not held:
            raise PasskeyRefused("You have no passkey to use here.", status=404)
        allowed = [PublicKeyCredentialDescriptor(id=held_id) for held_id in held]
    options = generate_authentication_options(
        rp_id=rp_id,
        allow_credentials=allowed,
        user_verification=UserVerificationRequirement.REQUIRED,
    )
    if step is not None:
        row.challenge = options.challenge
        session.commit()
        return "", json.loads(options_to_json(options))
    open_now = session.scalar(
        select(func.count())
        .select_from(SignInStep)
        .where(SignInStep.stage == ALONE, SignInStep.used_at.is_(None), SignInStep.expires_at > now)
    )
    if (open_now or 0) >= MAX_OPEN_CEREMONIES:
        raise PasskeyRefused(
            "Many sign-ins are waiting for a passkey; try again in a few minutes.", 429, 60
        )
    token = _open(session, ALONE, options.challenge, request or {}, now)
    return token, json.loads(options_to_json(options))


def _refuse(
    session: Session,
    message: str,
    *,
    user: User | None,
    address: str | None,
    now: datetime,
    detail: str = "",
) -> PasskeyRefused:
    """Count a passkey that did not sign anyone in, as a wrong password is (D271)."""
    sign_in.record_failure(session, user.username if user else "", address, now)
    security_events.record(
        session, "sign-in", user.public_id if user else "unknown", "failed",
        about=[user.public_id] if user else [], by=None,
        details={"username": user.username if user else None, "address": address,
                 "reason": "passkey", "method": "passkey", "detail": detail[:200]},
    )  # fmt: skip
    session.commit()
    return PasskeyRefused(message)


def finish_authentication(
    session: Session,
    settings: IdentitySettings,
    token: str,
    credential: dict[str, Any],
    *,
    second_step: tuple[SignInStep, User] | None,
    address: str | None,
    now: datetime,
) -> Authenticated:
    """Check the browser's assertion. For a second step (``second_step``, loaded by its token) the
    passkey must be that person's; alone, it names the person. On success the sign-in is whole
    (logged, the account's failures cleared) and the ceremony used up. Commits."""
    row = second_step[0] if second_step else _ceremony(session, token, (ALONE,), now)
    if second_step is None and row.stage != ALONE:
        raise PasskeyRefused("This passkey sign-in is not one the engine started.", status=410)
    if row.challenge is None:
        raise PasskeyRefused("Start the passkey again.", status=410)
    wait = sign_in.seconds_to_wait(
        session, second_step[1].username if second_step else "", address, now
    )
    if wait > 0:
        raise PasskeyRefused(
            "Too many wrong attempts for this account or from this address.", 429, wait
        )
    try:
        credential_id = base64url_to_bytes(str(credential["id"]))
    except KeyError, ValueError, TypeError, WebAuthnException:
        raise _refuse(
            session, "The browser's answer is not a passkey's.", user=None, address=address, now=now
        ) from None
    passkey = session.scalar(
        select(UserPasskey).where(UserPasskey.credential_id == credential_id).with_for_update()
    )
    owner = session.get(User, passkey.user_id) if passkey else None
    expected = second_step[1] if second_step else None
    if passkey is None or owner is None or (expected is not None and owner.id != expected.id):
        raise _refuse(
            session, "That passkey is not known here for this sign-in.", user=expected,
            address=address, now=now, detail="unknown credential",
        )  # fmt: skip
    rp_id, origin = relying_party(settings)
    try:
        verified = verify_authentication_response(
            credential=credential,
            expected_challenge=row.challenge,
            expected_rp_id=rp_id,
            expected_origin=origin,
            credential_public_key=passkey.public_key,
            credential_current_sign_count=passkey.sign_count,
            require_user_verification=True,
        )
    except (WebAuthnException, ValueError, KeyError, TypeError) as failure:
        raise _refuse(
            session,
            "The passkey could not be confirmed: it must be one made here, used with your "
            "fingerprint, face or PIN.",
            user=owner, address=address, now=now, detail=str(failure),
        ) from None  # fmt: skip
    handle = (credential.get("response") or {}).get("userHandle")
    try:
        handled = base64url_to_bytes(str(handle)) if handle else None
    except ValueError, TypeError:
        handled = b""
    if handle and handled != owner.public_id.encode():
        raise _refuse(
            session, "That passkey belongs to someone else.", user=owner, address=address,
            now=now, detail="user handle",
        )  # fmt: skip
    if not owner.active:
        raise PasskeyRefused("Your account is deactivated. Ask a security administrator.", 403)
    if second_step is None and not owner.local_kept and not providers.local_enabled(session):
        raise _refuse(
            session, "Local sign-in is off: only administrators made on the server use a passkey.",
            user=owner, address=address, now=now, detail="local sign-in off",
        )  # fmt: skip
    passkey.sign_count = verified.new_sign_count
    passkey.last_used_at = now
    row.used_at = now
    sign_in.complete(session, owner, owner.username, address, method="passkey")
    session.commit()
    return Authenticated(owner, dict(row.request), second_step is not None, row)
