"""The keys that sign access tokens (D253, D254, D264).

ES256 keys live in the database, each private key sealed with ``SECRETS_ENCRYPTION_KEY`` and bound
to its ``kid``, so every process signs and verifies with the same set. One key at most is current.
The first token issued makes one; a token issued when the current key is older than
``TOKEN_SIGNING_KEY_DAYS`` replaces it, under a lock, so processes issuing together make one key. A
rotated key verifies the tokens it signed until they expire; "rotate now" retires it at once.
"""

import base64
import secrets
from datetime import UTC, datetime, timedelta
from typing import Any

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec
from sqlalchemy import or_, select, text
from sqlalchemy.orm import Session

from ...common.pagination import Page, PageRequest, integer_key, paginate_statement
from ...common.sealing import seal, unseal
from ...models.database import TokenSigningKey
from .settings import IdentitySettings

# pg_advisory_xact_lock's key for replacing the current key: any constant no other lock uses.
_ROTATION_LOCK = 0x7D3A_0012

_KEYS = (integer_key("sequenceId", TokenSigningKey.id, "id", descending=True),)

# Keys are immutable once made, so each process keeps what it has unsealed or parsed.
_private_keys: dict[str, ec.EllipticCurvePrivateKey] = {}
_public_keys: dict[str, ec.EllipticCurvePublicKey] = {}


def _context(kid: str) -> bytes:
    return b"token-signing-key:" + kid.encode()


def _b64(number: int) -> str:
    return base64.urlsafe_b64encode(number.to_bytes(32, "big")).rstrip(b"=").decode()


def _unb64(value: str) -> int:
    return int.from_bytes(base64.urlsafe_b64decode(value + "=" * (-len(value) % 4)), "big")


def _new_key(settings: IdentitySettings, now: datetime) -> TokenSigningKey:
    private = ec.generate_private_key(ec.SECP256R1())
    numbers = private.public_key().public_numbers()
    kid = secrets.token_urlsafe(12)
    der = private.private_bytes(
        serialization.Encoding.DER,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    )
    _private_keys[kid] = private
    return TokenSigningKey(
        kid=kid,
        private_key=seal(settings.encryption_key, der, _context(kid)),
        public_jwk={
            "kty": "EC",
            "crv": "P-256",
            "x": _b64(numbers.x),
            "y": _b64(numbers.y),
            "kid": kid,
            "use": "sig",
            "alg": "ES256",
        },
        created_at=now,
    )


def _current(session: Session) -> TokenSigningKey | None:
    return session.scalar(
        select(TokenSigningKey)
        .where(TokenSigningKey.rotated_at.is_(None))
        .execution_options(populate_existing=True)
    )


def _due(key: TokenSigningKey | None, settings: IdentitySettings, now: datetime) -> bool:
    return key is None or now - key.created_at >= timedelta(days=settings.signing_key_days)


def _replace(
    session: Session, settings: IdentitySettings, now: datetime, *, immediate: bool
) -> TokenSigningKey:
    current = _current(session)
    if current is not None:
        current.rotated_at = now
        current.retired_at = (
            now if immediate else now + timedelta(seconds=settings.access_token_seconds)
        )
        # The old key stops being current before the new one is, for the one-current index.
        session.flush()
    replacement = _new_key(settings, now)
    session.add(replacement)
    session.flush()
    return replacement


def _lock(session: Session) -> None:
    session.execute(text("SELECT pg_advisory_xact_lock(:key)"), {"key": _ROTATION_LOCK})


def signing_key(
    session: Session, settings: IdentitySettings
) -> tuple[str, ec.EllipticCurvePrivateKey]:
    """The current key's ``kid`` and private key, made or replaced first when due (D264); a key made
    here is committed before it signs anything."""
    now = datetime.now(UTC)
    current = _current(session)
    if _due(current, settings, now):
        _lock(session)
        current = _current(session)
        if _due(current, settings, now):
            current = _replace(session, settings, now, immediate=False)
        session.commit()
    assert current is not None
    return current.kid, _private_key(settings, current)


def _private_key(settings: IdentitySettings, key: TokenSigningKey) -> ec.EllipticCurvePrivateKey:
    cached = _private_keys.get(key.kid)
    if cached is None:
        der = unseal(settings.encryption_key, key.private_key, _context(key.kid))
        loaded = serialization.load_der_private_key(der, password=None)
        assert isinstance(loaded, ec.EllipticCurvePrivateKey)
        cached = _private_keys[key.kid] = loaded
    return cached


def rotate(session: Session, settings: IdentitySettings, *, immediate: bool) -> TokenSigningKey:
    """Replace the current key now. The old one verifies its tokens until they expire, or, with
    ``immediate``, no longer (J43.2)."""
    _lock(session)
    replacement = _replace(session, settings, datetime.now(UTC), immediate=immediate)
    session.commit()
    return replacement


def public_key(kid: str, jwk: dict[str, Any]) -> ec.EllipticCurvePublicKey:
    cached = _public_keys.get(kid)
    if cached is None:
        numbers = ec.EllipticCurvePublicNumbers(_unb64(jwk["x"]), _unb64(jwk["y"]), ec.SECP256R1())
        cached = _public_keys[kid] = numbers.public_key()
    return cached


def verifies(key: TokenSigningKey | None, now: datetime) -> bool:
    return key is not None and (key.retired_at is None or key.retired_at > now)


def published(session: Session) -> list[dict[str, Any]]:
    """The public keys that verify tokens now, newest first (``/oauth/jwks``)."""
    now = datetime.now(UTC)
    rows = session.scalars(
        select(TokenSigningKey)
        .where(or_(TokenSigningKey.retired_at.is_(None), TokenSigningKey.retired_at > now))
        .order_by(TokenSigningKey.id.desc())
    )
    return [row.public_jwk for row in rows]


def key_page(session: Session, page: PageRequest, page_size: int) -> Page[TokenSigningKey]:
    """Every signing key, newest first, without its private half."""
    return paginate_statement(
        session,
        select(TokenSigningKey),
        keys=_KEYS,
        scope="token-signing-keys",
        filters={},
        page=page,
        page_size=page_size,
        message="Signing key list cursor is invalid",
    )
