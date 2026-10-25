"""People, clients and signing keys as the API answers them (Product 0.12 I1)."""

from datetime import UTC, datetime

from sqlalchemy.orm import Session

from ...common.pagination import Page
from ...common.time import as_utc
from ...engine.authorization.administration import (
    HeldRole,
    client_consumer_apis,
    client_roles,
    held_roles,
)
from ...engine.identity import keys
from ...engine.identity.authentication import Principal
from ...engine.identity.clients import creators, secrets_of
from ...engine.identity.principals import actors
from ...models.database import (
    AuditEvent,
    OAuthClient,
    OAuthClientSecret,
    TokenSigningKey,
    User,
    UserSession,
)
from ..schemas.common import PrincipalResponse
from ..schemas.identity import (
    ClientConsumerApi,
    ClientPage,
    ClientResponse,
    ClientSecretInfo,
    ClientWithSecret,
    MeResponse,
    SecurityEventPage,
    SecurityEventResponse,
    SessionPage,
    SessionResponse,
    SigningKeyPage,
    SigningKeyResponse,
    UserPage,
    UserResponse,
    UserRole,
    UserRoleWorkspace,
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


def user_response(
    session: Session, user: User, roles: list[HeldRole] | None = None
) -> UserResponse:
    if roles is None:
        roles = held_roles(session, [user.id]).get(user.id, [])
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
        roles=_roles(roles),
    )


def _roles(roles: list[HeldRole]) -> list[UserRole]:
    return [
        UserRole(
            key=role.key,
            name=role.name,
            instance=role.instance,
            workspaces=[UserRoleWorkspace(key=key, label=label) for key, label in role.workspaces],
        )
        for role in roles
    ]


def user_page(session: Session, page: Page[User]) -> UserPage:
    roles = held_roles(session, [user.id for user in page.items])
    return UserPage(
        items=[user_response(session, user, roles.get(user.id, [])) for user in page.items],
        **page.links(),
    )


def _secret(secret: OAuthClientSecret) -> ClientSecretInfo:
    return ClientSecretInfo(
        id=secret.public_id,
        createdAt=secret.created_at,
        expiresAt=secret.expires_at,
        lastUsedAt=secret.last_used_at,
        hint=secret.hint,
    )


def _client_responses(session: Session, clients: list[OAuthClient]) -> list[ClientResponse]:
    """Clients with their access and creator, in one statement each for the page (D348, D349)."""
    ids = [client.id for client in clients]
    roles = client_roles(session, ids)
    apis = client_consumer_apis(session, ids)
    made_by = creators(session, [client.public_id for client in clients])
    return [
        ClientResponse(
            id=client.public_id,
            name=client.name,
            active=client.active,
            version=client.version,
            createdAt=client.created_at,
            updatedAt=client.updated_at,
            lastUsedAt=client.last_used_at,
            secrets=[_secret(secret) for secret in secrets_of(session, client)],
            roles=_roles(roles.get(client.id, [])),
            consumerApis=[
                ClientConsumerApi(
                    key=key,
                    workspaces=[UserRoleWorkspace(key=w, label=label) for w, label in workspaces],
                )
                for key, workspaces in apis.get(client.id, [])
            ],
            createdBy=(
                PrincipalResponse(**made_by[client.public_id])
                if made_by.get(client.public_id)
                else None
            ),
        )
        for client in clients
    ]


def client_response(session: Session, client: OAuthClient) -> ClientResponse:
    return _client_responses(session, [client])[0]


def client_with_secret(
    session: Session, client: OAuthClient, secret_id: str, secret: str
) -> ClientWithSecret:
    return ClientWithSecret(
        **client_response(session, client).model_dump(), secretId=secret_id, secret=secret
    )


def client_page(session: Session, page: Page[OAuthClient]) -> ClientPage:
    return ClientPage(items=_client_responses(session, list(page.items)), **page.links())


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


def security_event_page(session: Session, page: Page[AuditEvent]) -> SecurityEventPage:
    named = actors(session, page.items)
    return SecurityEventPage(
        items=[
            SecurityEventResponse(
                id=event.event_id,
                aggregateType=event.aggregate_type,
                aggregateId=event.aggregate_id,
                action=event.action,
                version=event.version,
                occurredAt=as_utc(event.occurred_at),
                actor=named[event.sequence_id],
                details=event.changes if isinstance(event.changes, dict) else {},
            )
            for event in page.items
        ],
        **page.links(),
    )
