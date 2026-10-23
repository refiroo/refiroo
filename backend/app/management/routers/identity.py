"""The caller, people, OAuth clients and token signing keys (Product 0.12 I1, API.md § Security).

Until Z1 every active principal may use these routes; Z1 gives them to Security administration.
"""

from fastapi import APIRouter, Query, Request

from ...engine.identity import keys
from ...engine.identity.clients import (
    add_secret,
    client_page,
    create_client,
    load_client,
    remove_secret,
    update_client,
)
from ...engine.identity.users import create_user, load_user, update_user, user_page
from ...models.commands import (
    ClientCreate,
    ClientSecretCreate,
    ClientUpdate,
    SigningKeyRotation,
    UserCreate,
    UserUpdate,
)
from ..dependencies import CurrentPrincipal, DbSession
from ..paging import PageQuery
from ..projections import identity as present
from ..schemas.identity import (
    ClientPage,
    ClientResponse,
    ClientWithSecret,
    MeResponse,
    SigningKeyPage,
    SigningKeyResponse,
    UserPage,
    UserResponse,
)

router = APIRouter(prefix="/api/v1", tags=["security"])


@router.get("/me", response_model=MeResponse)
def get_me(principal: CurrentPrincipal) -> MeResponse:
    """Who the request's token belongs to: a person or a client."""
    return present.me_response(principal)


@router.get("/users", response_model=UserPage)
def list_users(
    session: DbSession,
    paging: PageQuery,
    q: str | None = Query(default=None, max_length=200),
    active: bool | None = None,
    page_size: int = Query(default=50, ge=1, le=500, alias="pageSize"),
) -> UserPage:
    """People in the order they were created; ``q`` matches the username, name or e-mail."""
    return present.user_page(
        user_page(session, q=q, active=active, page=paging, page_size=page_size)
    )


@router.post("/users", response_model=UserResponse, status_code=201)
def post_user(payload: UserCreate, session: DbSession) -> UserResponse:
    """A person, without a password until they set one; the username is unique ignoring case
    (``409 USERNAME_TAKEN``)."""
    return present.user_response(create_user(session, payload))


@router.get("/users/{user_id}", response_model=UserResponse)
def get_user(user_id: str, session: DbSession) -> UserResponse:
    return present.user_response(load_user(session, user_id))


@router.patch("/users/{user_id}", response_model=UserResponse)
def patch_user(user_id: str, payload: UserUpdate, session: DbSession) -> UserResponse:
    """Change a person's name or e-mail, or deactivate them with ``active: false``: their tokens are
    refused from the next request. A person is never deleted (D237)."""
    return present.user_response(update_user(session, user_id, payload))


@router.get("/clients", response_model=ClientPage)
def list_clients(
    session: DbSession,
    paging: PageQuery,
    active: bool | None = None,
    page_size: int = Query(default=50, ge=1, le=500, alias="pageSize"),
) -> ClientPage:
    """OAuth clients in the order they were created."""
    return present.client_page(
        session, client_page(session, active=active, page=paging, page_size=page_size)
    )


@router.post("/clients", response_model=ClientWithSecret, status_code=201)
def post_client(payload: ClientCreate, session: DbSession) -> ClientWithSecret:
    """A client and its first secret. The answer holds ``secret``, the ``client_secret``: it is never
    answered again."""
    client, secret = create_client(session, payload)
    first = present.client_response(session, client).secrets[0]
    return present.client_with_secret(session, client, first.id, secret)


@router.get("/clients/{client_id}", response_model=ClientResponse)
def get_client(client_id: str, session: DbSession) -> ClientResponse:
    return present.client_response(session, load_client(session, client_id))


@router.patch("/clients/{client_id}", response_model=ClientResponse)
def patch_client(client_id: str, payload: ClientUpdate, session: DbSession) -> ClientResponse:
    """Rename a client, or deactivate it with ``active: false``: it obtains no token and the tokens it
    holds are refused from the next request. A client is never deleted (D237)."""
    return present.client_response(session, update_client(session, client_id, payload))


@router.post("/clients/{client_id}/secrets", response_model=ClientWithSecret, status_code=201)
def post_client_secret(
    client_id: str, payload: ClientSecretCreate, session: DbSession
) -> ClientWithSecret:
    """A new secret, answered once. The client's other secrets stay valid for ``overlapHours``
    (24 by default, 0 to 168), so the system using it switches without a gap (J41.3)."""
    client, added, secret = add_secret(session, client_id, payload)
    return present.client_with_secret(session, client, added.public_id, secret)


@router.delete("/clients/{client_id}/secrets/{secret_id}", response_model=ClientResponse)
def delete_client_secret(client_id: str, secret_id: str, session: DbSession) -> ClientResponse:
    """Stop a secret at once, before its overlap ends."""
    return present.client_response(session, remove_secret(session, client_id, secret_id))


@router.get("/token-signing-keys", response_model=SigningKeyPage)
def list_signing_keys(
    session: DbSession,
    paging: PageQuery,
    page_size: int = Query(default=50, ge=1, le=500, alias="pageSize"),
) -> SigningKeyPage:
    """The keys that sign access tokens, newest first, with their state; never a private key."""
    return present.signing_key_page(keys.key_page(session, paging, page_size))


@router.post("/token-signing-keys/rotation", response_model=SigningKeyResponse, status_code=201)
def rotate_signing_key(
    payload: SigningKeyRotation, request: Request, session: DbSession
) -> SigningKeyResponse:
    """A new signing key for the tokens issued from now on. The previous key accepts the tokens it
    signed until they expire, or, with ``immediate: true`` after a leak, no longer: their holders
    obtain new ones (J43.2). Answers the new key."""
    return present.signing_key_response(
        keys.rotate(session, request.app.state.identity_settings, immediate=payload.immediate)
    )
