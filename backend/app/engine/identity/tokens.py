"""Access tokens: JWTs signed with ES256 that prove who calls, never what they may do (D226, D258).

Claims: ``iss`` (``PUBLIC_URL``), ``sub`` (the principal's public ID), ``aud`` (``management``,
``consumer`` or ``agent``), ``iat``, ``exp``, ``jti``, ``principalKind`` and, for a person, ``sid``, the browser
session the token was issued in (I2). Verification accepts ES256 alone and
requires every claim; what PyJWT refuses becomes a reason the API names.
"""

import time
from dataclasses import dataclass
from typing import Literal
from uuid import uuid4

import jwt
from cryptography.hazmat.primitives.asymmetric import ec
from sqlalchemy.orm import Session

from . import keys
from .settings import IdentitySettings

Audience = Literal["management", "consumer", "agent"]
AUDIENCES: tuple[Audience, ...] = ("management", "consumer", "agent")
PrincipalKind = Literal["user", "client"]
PRINCIPAL_KINDS: tuple[PrincipalKind, ...] = ("user", "client")
ALGORITHM = "ES256"
_REQUIRED = ["iss", "sub", "aud", "iat", "exp", "jti", "principalKind"]

# Why a token is refused: ``expired``, ``revoked`` (the principal is inactive), ``audience``,
# ``unknownKey`` (no key, or a retired one, has its ``kid``), ``malformed`` (not a JWT this engine
# issues) and ``signature`` (the signature or a claim does not verify).
Reason = Literal["expired", "revoked", "audience", "unknownKey", "malformed", "signature"]


class TokenRefused(Exception):
    def __init__(self, reason: Reason):
        super().__init__(reason)
        self.reason: Reason = reason


@dataclass(frozen=True)
class Unverified:
    """What a token says before it is verified: enough to find its key and principal."""

    kid: str
    subject: str
    kind: PrincipalKind
    # A person's session; ``None`` for a client.
    session: str | None = None


def issue(
    session: Session,
    settings: IdentitySettings,
    *,
    subject: str,
    kind: PrincipalKind,
    audience: Audience,
    session_id: str | None = None,
) -> str:
    kid, private = keys.signing_key(session, settings)
    now = int(time.time())
    claims = {
        "iss": settings.issuer,
        "sub": subject,
        "aud": audience,
        "iat": now,
        "exp": now + settings.access_token_seconds,
        "jti": uuid4().hex,
        "principalKind": kind,
    }
    if session_id is not None:
        claims["sid"] = session_id
    return jwt.encode(claims, private, algorithm=ALGORITHM, headers={"kid": kid})


def read_unverified(token: str) -> Unverified:
    try:
        header = jwt.get_unverified_header(token)
        claims = jwt.decode(token, options={"verify_signature": False})
    except jwt.PyJWTError:
        raise TokenRefused("malformed") from None
    kid, subject, kind = header.get("kid"), claims.get("sub"), claims.get("principalKind")
    if header.get("alg") != ALGORITHM or not isinstance(kid, str) or not isinstance(subject, str):
        raise TokenRefused("malformed")
    if kind not in PRINCIPAL_KINDS:
        raise TokenRefused("malformed")
    session = claims.get("sid")
    # A person's token is always issued in a session; a client's never.
    if (kind == "user") != isinstance(session, str):
        raise TokenRefused("malformed")
    return Unverified(kid, subject, kind, session)


def verify(
    token: str,
    key: ec.EllipticCurvePublicKey,
    settings: IdentitySettings,
    audience: Audience | tuple[Audience, ...],
) -> dict[str, object]:
    """The token's claims, verified; ``audience`` names the one audience a route takes, or the
    several it accepts."""
    try:
        return jwt.decode(
            token,
            key,
            algorithms=[ALGORITHM],
            audience=list(audience) if isinstance(audience, tuple) else audience,
            issuer=settings.issuer,
            options={"require": _REQUIRED},
        )
    except jwt.ExpiredSignatureError:
        raise TokenRefused("expired") from None
    except jwt.InvalidAudienceError:
        raise TokenRefused("audience") from None
    except jwt.PyJWTError:
        raise TokenRefused("signature") from None
