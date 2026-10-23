"""People, clients and signing keys as the API answers them (Product 0.12 I1)."""

from datetime import UTC, datetime

from sqlalchemy.orm import Session

from ...common.pagination import Page
from ...engine.identity import keys
from ...engine.identity.authentication import Principal
from ...engine.identity.clients import secrets_of
from ...models.database import (
    OAuthClient,
    OAuthClientSecret,
    TokenSigningKey,
    User,
    UserSession,
)
from ..schemas.identity import (
    ClientPage,
    ClientResponse,
    ClientSecretInfo,
    ClientWithSecret,
    MeResponse,
    SessionPage,
    SessionResponse,
    SigningKeyPage,
    SigningKeyResponse,
    UserPage,
    UserResponse,
)


def me_response(principal: Principal) -> MeResponse:
    return MeResponse(
        id=principal.id,
        kind=principal.kind,
        name=principal.name,
        username=principal.username,
        email=principal.email,
        lastSignInAt=principal.last_sign_in_at,
        signedInWith=principal.signed_in_with,
        sessionId=principal.session_id,
    )


def session_page(page: Page[UserSession], current: str | None) -> SessionPage:
    return SessionPage(
        items=[
            SessionResponse(
                id=item.public_id,
                current=item.public_id == current,
                signedInWith=item.signed_in_with,
                userAgent=item.user_agent,
                createdAt=item.created_at,
                lastUsedAt=item.last_used_at,
                endsAt=min(item.idle_ends_at, item.ends_at),
            )
            for item in page.items
        ],
        **page.links(),
    )


def user_response(user: User) -> UserResponse:
    return UserResponse(
        id=user.public_id,
        username=user.username,
        name=user.name,
        email=user.email,
        active=user.active,
        hasPassword=user.password_hash is not None,
        version=user.version,
        createdAt=user.created_at,
        updatedAt=user.updated_at,
        lastSignInAt=user.last_sign_in_at,
    )


def user_page(page: Page[User]) -> UserPage:
    return UserPage(items=[user_response(user) for user in page.items], **page.links())


def _secret(secret: OAuthClientSecret) -> ClientSecretInfo:
    return ClientSecretInfo(
        id=secret.public_id,
        createdAt=secret.created_at,
        expiresAt=secret.expires_at,
        lastUsedAt=secret.last_used_at,
    )


def client_response(session: Session, client: OAuthClient) -> ClientResponse:
    return ClientResponse(
        id=client.public_id,
        name=client.name,
        active=client.active,
        version=client.version,
        createdAt=client.created_at,
        updatedAt=client.updated_at,
        lastUsedAt=client.last_used_at,
        secrets=[_secret(secret) for secret in secrets_of(session, client)],
    )


def client_with_secret(
    session: Session, client: OAuthClient, secret_id: str, secret: str
) -> ClientWithSecret:
    return ClientWithSecret(
        **client_response(session, client).model_dump(), secretId=secret_id, secret=secret
    )


def client_page(session: Session, page: Page[OAuthClient]) -> ClientPage:
    return ClientPage(
        items=[client_response(session, client) for client in page.items], **page.links()
    )


def signing_key_response(key: TokenSigningKey) -> SigningKeyResponse:
    if key.rotated_at is None:
        state = "current"
    elif keys.verifies(key, datetime.now(UTC)):
        state = "verifying"
    else:
        state = "retired"
    return SigningKeyResponse(
        kid=key.kid,
        state=state,
        createdAt=key.created_at,
        rotatedAt=key.rotated_at,
        retiredAt=key.retired_at,
    )


def signing_key_page(page: Page[TokenSigningKey]) -> SigningKeyPage:
    return SigningKeyPage(items=[signing_key_response(key) for key in page.items], **page.links())
