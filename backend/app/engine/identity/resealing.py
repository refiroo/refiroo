"""Re-sealing every sealed secret under a new ``SECRETS_ENCRYPTION_KEY`` (Product 0.12 K1, D414).

The engine stores what it must read back sealed with AES-256-GCM (``common/sealing``), each value
bound to what it belongs to: the token signing keys, the webhook signing keys (the current and the
previous one of a rotation), a sign-in provider's client secret, a person's authenticator secret and
the provider ID tokens kept while a sign-in is under way or open. ``reseal`` opens each with the old
key and seals it again with the new one, in one transaction: either every value is re-sealed or none
is. Every value is opened first; if any does not open (another key, damaged data) nothing is
written and the refusal names each one by kind and identity, never by content.

The secrets are few and the key must stay outside the database, so this is not a set statement in
SQL. The engine must be stopped meanwhile: a process running with the old key would seal new values
with it after this reads them.
"""

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from sqlalchemy import Select, select, update
from sqlalchemy.orm import Session

from ...common.sealing import SealError, seal, unseal
from ...models.database import (
    AuthorizationCode,
    ConsumerSubscription,
    SignInProvider,
    TokenSigningKey,
    User,
    UserSecondFactor,
    UserSession,
)
from ..events import subscriptions
from . import keys, providers, second_factor

# How many values a refusal lists by name.
LISTED = 20


@dataclass(frozen=True)
class Sealed:
    """One kind of sealed value: ``rows`` selects each one's row key, its sealed bytes and what
    names it (an identity, shown in a refusal), ``context`` the binding the value was sealed with
    from that identity, and ``column`` the attribute that holds it on ``model``, ``key`` its row key."""

    kind: str
    model: Any
    key: str
    column: str
    rows: Select[Any]
    context: Callable[[str], bytes]


SEALED = (
    Sealed(
        "token signing key",
        TokenSigningKey,
        "id",
        "private_key",
        select(TokenSigningKey.id, TokenSigningKey.private_key, TokenSigningKey.kid),
        keys.context,
    ),
    Sealed(
        "webhook signing key",
        ConsumerSubscription,
        "sequence_id",
        "signing_key",
        select(
            ConsumerSubscription.sequence_id,
            ConsumerSubscription.signing_key,
            ConsumerSubscription.public_id,
        ),
        subscriptions.context,
    ),
    Sealed(
        "previous webhook signing key",
        ConsumerSubscription,
        "sequence_id",
        "previous_signing_key",
        select(
            ConsumerSubscription.sequence_id,
            ConsumerSubscription.previous_signing_key,
            ConsumerSubscription.public_id,
        ).where(ConsumerSubscription.previous_signing_key.is_not(None)),
        subscriptions.context,
    ),
    Sealed(
        "sign-in provider client secret",
        SignInProvider,
        "id",
        "client_secret",
        select(SignInProvider.id, SignInProvider.client_secret, SignInProvider.key),
        providers.context,
    ),
    Sealed(
        "authenticator secret",
        UserSecondFactor,
        "id",
        "secret",
        select(UserSecondFactor.id, UserSecondFactor.secret, User.public_id).join(
            User, User.id == UserSecondFactor.user_id
        ),
        second_factor.context,
    ),
    Sealed(
        "session's provider ID token",
        UserSession,
        "id",
        "provider_id_token",
        select(UserSession.id, UserSession.provider_id_token, UserSession.signed_in_with).where(
            UserSession.provider_id_token.is_not(None)
        ),
        providers.id_token_context,
    ),
    Sealed(
        "sign-in's provider ID token",
        AuthorizationCode,
        "id",
        "provider_id_token",
        select(
            AuthorizationCode.id,
            AuthorizationCode.provider_id_token,
            AuthorizationCode.signed_in_with,
        ).where(AuthorizationCode.provider_id_token.is_not(None)),
        providers.id_token_context,
    ),
)


class ResealRefused(Exception):
    """Some sealed values do not open with the old key: ``failures`` is how many, ``named`` the first
    of them as ``(kind, identity)``."""

    def __init__(self, failures: int, named: list[tuple[str, str]]) -> None:
        self.failures = failures
        self.named = named
        listed = ", ".join(f"{kind} {identity}" for kind, identity in named)
        more = f" and {failures - len(named)} more" if failures > len(named) else ""
        super().__init__(
            f"{failures} sealed value(s) do not open with the current SECRETS_ENCRYPTION_KEY: "
            f"{listed}{more}. Nothing was changed"
        )


def reseal(
    session: Session, old_key: bytes, new_key: bytes, *, check_only: bool = False
) -> dict[str, int]:
    """Re-seal every sealed value from ``old_key`` to ``new_key`` and commit; how many of each kind.
    With ``check_only`` only prove that every one opens with ``old_key``, and write nothing. Raises
    ``ResealRefused`` before any write when one does not open."""
    opened: list[tuple[Sealed, int, bytes, bytes]] = []
    failures: list[tuple[str, str]] = []
    counts: dict[str, int] = {}
    for sealed in SEALED:
        for row_key, value, identity in session.execute(sealed.rows):
            bound = sealed.context(identity)
            try:
                plain = unseal(old_key, value, bound)
            except SealError:
                failures.append((sealed.kind, identity))
                continue
            opened.append((sealed, row_key, plain, bound))
            counts[sealed.kind] = counts.get(sealed.kind, 0) + 1
    if failures:
        session.rollback()
        raise ResealRefused(len(failures), failures[:LISTED])
    if not check_only:
        for sealed, row_key, plain, bound in opened:
            session.execute(
                update(sealed.model)
                .where(getattr(sealed.model, sealed.key) == row_key)
                .values({sealed.column: seal(new_key, plain, bound)})
            )
        session.commit()
    else:
        session.rollback()
    return counts
