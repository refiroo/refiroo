"""Signing a person in through a sign-in provider (Product 0.12 I3, D361, D363, D364, D368).

The sign-in page's button starts here with the browser's own authorization request. The engine
keeps the sign-in in ``provider_sign_ins`` (the state's hash, the nonce, its PKCE verifier and the
browser's request; ten minutes, used once), binds it to the browser with a cookie the router sets,
and sends the browser to the provider. When the provider returns it, the engine exchanges the code
with the client secret, checks the ID token, finds the person by the provider and the token's
subject (never by e-mail) or creates them, makes their memberships in the provider's groups those
the token names, and hands back the browser's request: the router ends as the password form does,
with a one-time code. A sign-in that cannot finish is a ``SignInFailed`` with a reason the page
shows and a ``sign-in`` ``failed`` security event.
"""

import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import delete, func, select, update
from sqlalchemy.orm import Session

from ...models.database import (
    ProviderSignIn,
    SignInProvider,
    User,
    UserGroup,
    UserGroupMember,
    UserIdentity,
)
from ..authorization.administration import free_group_name
from . import provider_client, providers, security_events
from .passwords import digest, new_token
from .settings import IdentitySettings
from .sign_in import challenge_of

SIGN_IN_MINUTES = 10
# Pending sign-ins are removed this long after they lapse.
KEPT_AFTER = timedelta(days=1)
_UNCONFIRMED = (
    "The engine could not confirm the answer from {name}. Try again; if it happens again, tell a "
    "security administrator."
)


class SignInFailed(Exception):
    """Why a provider sign-in cannot finish: ``reason`` for the security event, ``message`` for the
    person, and the browser's request when it is known, to start again."""

    def __init__(self, reason: str, message: str, request: dict[str, str] | None = None):
        super().__init__(message)
        self.reason = reason
        self.message = message
        self.request = request


@dataclass(frozen=True)
class Started:
    url: str
    browser_token: str


def _failed(
    session: Session,
    provider: SignInProvider,
    reason: str,
    message: str,
    *,
    request: dict[str, str] | None,
    address: str | None,
    user: User | None = None,
    detail: str | None = None,
) -> SignInFailed:
    """Record the failure (D368) and commit; the exception to raise."""
    details: dict[str, Any] = {"provider": provider.key, "reason": reason, "address": address}
    if detail:
        details["detail"] = detail[:300]
    security_events.record(
        session, "sign-in", user.public_id if user else "unknown", "failed",
        about=[user.public_id] if user else [], by=None, details=details,
    )  # fmt: skip
    session.commit()
    return SignInFailed(reason, message, request)


def start(
    session: Session,
    settings: IdentitySettings,
    provider: SignInProvider,
    request: dict[str, str],
    *,
    address: str | None,
    now: datetime,
) -> Started:
    """Keep the sign-in and answer where the browser goes at the provider. Commits."""
    if not provider.enabled:
        raise _failed(
            session, provider, "disabled", f"Signing in with {provider.name} is turned off.",
            request=request, address=address,
        )  # fmt: skip
    try:
        discovery = provider_client.discover(provider.issuer)
    except provider_client.ProviderError as error:
        raise _failed(
            session, provider, "unreachable",
            f"{provider.name} cannot be reached now. Try again later, or tell a security "
            "administrator if it goes on.",
            request=request, address=address, detail=str(error),
        ) from None  # fmt: skip
    session.execute(delete(ProviderSignIn).where(ProviderSignIn.expires_at < now - KEPT_AFTER))
    state, nonce, browser_token = new_token(), new_token(), new_token()
    verifier = secrets.token_urlsafe(48)
    session.add(
        ProviderSignIn(
            provider_id=provider.id,
            state_hash=digest(state),
            browser_hash=digest(browser_token),
            nonce=nonce,
            verifier=verifier,
            request=request,
            created_at=now,
            expires_at=now + timedelta(minutes=SIGN_IN_MINUTES),
        )
    )
    session.commit()
    url = provider_client.authorization_url(
        discovery,
        client_id=provider.client_id,
        redirect_uri=providers.redirect_uri(settings, provider.key),
        state=state,
        nonce=nonce,
        challenge=challenge_of(verifier),
    )
    return Started(url, browser_token)


def finish(
    session: Session,
    settings: IdentitySettings,
    provider: SignInProvider,
    *,
    state: str | None,
    code: str | None,
    error: str | None,
    error_description: str | None,
    browser_token: str | None,
    address: str | None,
    now: datetime,
) -> tuple[User, dict[str, str]]:
    """The person the provider signed in and the browser's request, or ``SignInFailed``. Commits."""
    pending = session.scalar(
        select(ProviderSignIn)
        .where(ProviderSignIn.state_hash == digest(state or ""))
        .with_for_update()
    )
    again = "This sign-in was already used or is not one the engine started. Start again."
    if pending is None or pending.provider_id != provider.id:
        raise _failed(session, provider, "unknown", again, request=None, address=address)
    request = dict(pending.request)
    if pending.used_at is not None:
        raise _failed(session, provider, "used", again, request=request, address=address)
    pending.used_at = now
    session.commit()

    def fail(reason: str, message: str, **more: Any) -> SignInFailed:
        return _failed(session, provider, reason, message, request=request, address=address, **more)

    if now >= pending.expires_at:
        raise fail(
            "expired",
            f"This sign-in took longer than {SIGN_IN_MINUTES} minutes. Start it again from here.",
        )
    if browser_token is None or digest(browser_token) != pending.browser_hash:
        raise fail(
            "browser", "This sign-in was started in another browser. Start it again from here."
        )
    if not provider.enabled:
        raise fail("disabled", f"Signing in with {provider.name} is turned off.")
    if error or not code:
        said = f"{error}: {error_description}" if error and error_description else error
        raise fail(
            "provider",
            f"{provider.name} answered: {said or 'no code'}. Try again, or ask whoever manages "
            f"{provider.name} whether you may use this application.",
            detail=said,
        )
    try:
        discovery = provider_client.discover(provider.issuer)
        id_token = provider_client.exchange_code(
            discovery,
            client_id=provider.client_id,
            client_secret=providers.client_secret(settings, provider),
            code=code,
            redirect_uri=providers.redirect_uri(settings, provider.key),
            verifier=pending.verifier,
        )
        claims = provider_client.verify_id_token(
            discovery, id_token, client_id=provider.client_id, nonce=pending.nonce
        )
    except provider_client.ProviderError as failure:
        raise fail(
            failure.kind, _UNCONFIRMED.format(name=provider.name), detail=str(failure)
        ) from None
    subject = str(claims["sub"])[:255]
    found = session.execute(
        select(User, UserIdentity)
        .join(UserIdentity, UserIdentity.user_id == User.id)
        .where(UserIdentity.provider_id == provider.id, UserIdentity.subject == subject)
        .with_for_update(of=UserIdentity)
    ).one_or_none()
    if found is not None:
        user, identity = found
        if not user.active:
            raise fail(
                "deactivated",
                "Your account is deactivated. Ask a security administrator.",
                user=user,
            )
        _refresh(user, claims, now)
        identity.last_sign_in_at = now
    else:
        user = _create_person(session, provider, claims, subject, now)
    _sync_groups(session, provider, user, claims, now)
    provider.last_sign_in_at = now
    security_events.record(
        session, "sign-in", user.public_id, "succeeded", about=[user.public_id],
        by=("user", user.id),
        details={"username": user.username, "address": address, "provider": provider.key},
    )  # fmt: skip
    session.commit()
    return user, request


# --- the person -----------------------------------------------------------------------------------


def _text(claims: dict[str, Any], name: str, limit: int) -> str | None:
    value = claims.get(name)
    if isinstance(value, str) and value.strip():
        return value.strip()[:limit]
    return None


def _name(claims: dict[str, Any], fallback: str) -> str:
    given = " ".join(
        part
        for part in (_text(claims, "given_name", 100), _text(claims, "family_name", 100))
        if part
    )
    return _text(claims, "name", 200) or given[:200] or fallback[:200]


def _email(claims: dict[str, Any]) -> str | None:
    email = _text(claims, "email", 320)
    return email if email and "@" in email else None


def _refresh(user: User, claims: dict[str, Any], now: datetime) -> None:
    """Name and e-mail follow the provider at each sign-in (D363)."""
    name, email = _name(claims, user.name), _email(claims) or user.email
    if (name, email) != (user.name, user.email):
        user.name, user.email = name, email
        user.version += 1
        user.updated_at = now


def username_for(session: Session, claims: dict[str, Any], key: str, subject: str) -> str:
    """``preferred_username``, else ``email``, else ``<provider key>-<sub>``; numbered when taken."""
    base = (
        _text(claims, "preferred_username", 140)
        or _text(claims, "email", 140)
        or f"{key}-{subject}"[:140]
    )
    candidate, number = base, 2
    while (
        session.scalar(select(User.id).where(func.lower(User.username) == candidate.lower()))
        is not None
    ):
        candidate = f"{base}-{number}"
        number += 1
    return candidate


def _create_person(
    session: Session, provider: SignInProvider, claims: dict[str, Any], subject: str, now: datetime
) -> User:
    username = username_for(session, claims, provider.key, subject)
    user = User(
        username=username,
        name=_name(claims, username),
        email=_email(claims),
        password_hash=None,
        active=True,
    )
    session.add(user)
    session.flush()
    session.add(
        UserIdentity(
            user_id=user.id,
            provider_id=provider.id,
            subject=subject,
            created_at=now,
            last_sign_in_at=now,
        )
    )
    security_events.record(
        session, "user", user.public_id, "created", about=[user.public_id], by=("user", user.id),
        details={"username": user.username, "name": user.name, "roles": [],
                 "provider": provider.key},
    )  # fmt: skip
    return user


# --- provider groups ------------------------------------------------------------------------------


def claim_values(claims: dict[str, Any], claim: str) -> list[str]:
    """The groups a token names: a list of strings (or numbers), or one string; at most 1000."""
    raw = claims.get(claim)
    items = [raw] if isinstance(raw, str) else raw if isinstance(raw, list) else []
    values = (str(item).strip()[:200] for item in items if isinstance(item, (str, int)))
    return list(dict.fromkeys(value for value in values if value))[:1000]


def _sync_groups(
    session: Session, provider: SignInProvider, user: User, claims: dict[str, Any], now: datetime
) -> None:
    """The person's memberships in the provider's groups become those the token names (D364)."""
    if not provider.groups_claim:
        return
    values = claim_values(claims, provider.groups_claim)
    named = {
        group.claim_value: group
        for group in session.scalars(
            select(UserGroup).where(
                UserGroup.provider_id == provider.id, UserGroup.claim_value.in_(values)
            )
        )
    }
    for value in values:
        if value in named:
            continue
        group = UserGroup(
            name=free_group_name(session, value, f"{value} ({provider.name})"),
            provider_id=provider.id,
            claim_value=value,
        )
        session.add(group)
        session.flush()
        named[value] = group
        security_events.record(
            session, "group", group.public_id, "created", about=[group.public_id],
            by=("user", user.id),
            details={"name": group.name, "provider": provider.key, "claimValue": value},
        )  # fmt: skip
    wanted = {group.id: group for group in named.values()}
    held = {
        group.id: group
        for group in session.scalars(
            select(UserGroup)
            .join(UserGroupMember, UserGroupMember.group_id == UserGroup.id)
            .where(UserGroupMember.user_id == user.id, UserGroup.provider_id == provider.id)
        )
    }
    left = [group for group_id, group in held.items() if group_id not in wanted]
    if left:
        session.execute(
            delete(UserGroupMember).where(
                UserGroupMember.user_id == user.id,
                UserGroupMember.group_id.in_([group.id for group in left]),
            )
        )
    if held.keys() & wanted.keys():
        session.execute(
            update(UserGroupMember)
            .where(
                UserGroupMember.user_id == user.id,
                UserGroupMember.group_id.in_(list(held.keys() & wanted.keys())),
            )
            .values(seen_at=now)
        )
    joined = [group for group_id, group in wanted.items() if group_id not in held]
    session.add_all(
        UserGroupMember(group_id=group.id, user_id=user.id, added_at=now, seen_at=now)
        for group in joined
    )
    for action, groups in (("member-removed", left), ("member-added", joined)):
        for group in groups:
            security_events.record(
                session, "group", group.public_id, action,
                about=[group.public_id, user.public_id], by=("user", user.id),
                details={"groupName": group.name, "userId": user.public_id,
                         "provider": provider.key},
            )  # fmt: skip
