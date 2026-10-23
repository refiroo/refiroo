"""Who a request comes from (Product 0.12 I1, ADR-043).

A request carries ``Authorization: Bearer <access token>``. Its key (by ``kid``), its principal and,
for a person, the session it was issued in (``sid``, I2) are read in one statement, so a retired
key, a deactivated client or person, or a session signed out applies on the next request in every
process, not when the token expires (D226, D251). Refusals are ``401`` with
``WWW-Authenticate: Bearer``: ``AUTHENTICATION_REQUIRED`` without a token, ``TOKEN_INVALID`` with
the reason otherwise.
"""

from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from ...errors import ApiError, api_error
from ...models.database import OAuthClient, TokenSigningKey, User, UserSession
from . import keys, tokens
from .settings import IdentitySettings
from .tokens import Audience, PrincipalKind, Reason, TokenRefused

_MESSAGES: dict[Reason, str] = {
    "expired": "The access token has expired; obtain a new one",
    "revoked": "The access token's client or person is no longer active, or its session ended",
    "audience": "The access token is for another API",
    "unknownKey": "The access token was signed with a key this engine no longer accepts",
    "malformed": "The access token is not one this engine issues",
    "signature": "The access token does not verify",
}


@dataclass(frozen=True)
class Principal:
    """The caller: a person or a client, as ``GET /me`` shows it."""

    kind: PrincipalKind
    id: str
    name: str
    username: str | None
    email: str | None
    last_sign_in_at: datetime | None
    # A person's session and how they signed in to it (I2); ``None`` for a client.
    session_id: str | None = None
    signed_in_with: str | None = None


def required() -> ApiError:
    return api_error(
        401,
        "AUTHENTICATION_REQUIRED",
        "This request needs an access token: Authorization: Bearer <token>",
        headers={"WWW-Authenticate": "Bearer"},
    )


def refused(reason: Reason) -> ApiError:
    return api_error(
        401,
        "TOKEN_INVALID",
        _MESSAGES[reason],
        {"reason": reason},
        headers={"WWW-Authenticate": 'Bearer error="invalid_token"'},
    )


def require_started(maintenance: bool) -> None:
    """Refuse, as every route did before tokens, while startup could not prepare the database
    (maintenance mode): its identity tables may not exist yet."""
    if maintenance:
        raise api_error(503, "MODEL_REGISTRY_UNAVAILABLE", "The model registry is unavailable")


def bearer_token(authorization: str | None) -> str:
    """The token of an ``Authorization: Bearer`` header; refused without one."""
    if not authorization or not authorization.strip():
        raise required()
    scheme, _, token = authorization.strip().partition(" ")
    if scheme.lower() != "bearer" or not token.strip():
        raise refused("malformed")
    return token.strip()


def authenticate(
    session: Session,
    settings: IdentitySettings,
    authorization: str | None,
    audience: Audience | tuple[Audience, ...],
) -> Principal:
    token = bearer_token(authorization)
    now = datetime.now(UTC)
    try:
        claimed = tokens.read_unverified(token)
        model = User if claimed.kind == "user" else OAuthClient
        statement = (
            select(TokenSigningKey, model)
            .select_from(TokenSigningKey)
            .outerjoin(model, model.public_id == claimed.subject)
            .where(TokenSigningKey.kid == claimed.kid)
        )
        if claimed.kind == "user":
            statement = statement.add_columns(UserSession).outerjoin(
                UserSession,
                (UserSession.public_id == claimed.session) & (UserSession.user_id == User.id),
            )
        row = session.execute(statement).one_or_none()
        key, principal = (row[0], row[1]) if row is not None else (None, None)
        if key is None or not keys.verifies(key, now):
            raise TokenRefused("unknownKey")
        tokens.verify(token, keys.public_key(key.kid, key.public_jwk), settings, audience)
        if principal is None or not principal.active:
            raise TokenRefused("revoked")
        user_session = row[2] if claimed.kind == "user" and row is not None else None
        if claimed.kind == "user" and (
            user_session is None or user_session.ended_at is not None or now >= user_session.ends_at
        ):
            raise TokenRefused("revoked")
    except TokenRefused as refusal:
        raise refused(refusal.reason) from None
    if isinstance(principal, User):
        assert user_session is not None
        return Principal(
            "user",
            principal.public_id,
            principal.name,
            principal.username,
            principal.email,
            principal.last_sign_in_at,
            user_session.public_id,
            user_session.signed_in_with,
        )
    return Principal(
        "client", principal.public_id, principal.name, None, None, principal.last_used_at
    )
