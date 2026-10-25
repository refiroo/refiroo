"""The caller, people, OAuth clients, token signing keys and sign-in providers (Product 0.12 I1, I2,
I3, API.md § Security).

The caller's own routes are for anyone signed in; the rest need Security administration at the
instance (Z1).
"""

from fastapi import APIRouter, Query, Request, Response

from ...engine.identity import keys, providers, resets, security_events, sessions
from ...engine.identity.clients import (
    add_secret,
    client_page,
    create_client,
    load_client,
    remove_secret,
    update_client,
)
from ...engine.identity.users import create_user, load_user, update_user, user_page
from ...errors import api_error
from ...models.commands import (
    ClientCreate,
    ClientSecretCreate,
    ClientUpdate,
    LocalSignInUpdate,
    PasswordChange,
    SigningKeyRotation,
    SignInProviderCreate,
    SignInProviderUpdate,
    UserCreate,
    UserUpdate,
)
from ..access import (
    INSTANCE,
    SIGNED_IN,
    AuthorizedRoute,
    requires,
)
from ..dependencies import CurrentPrincipal, DbSession
from ..paging import PageQuery
from ..projections import identity as present
from ..schemas.identity import (
    ClientPage,
    ClientResponse,
    ClientWithSecret,
    LocalSignInResponse,
    MeResponse,
    PasswordResetLinkResponse,
    SecurityAggregate,
    SecurityEventPage,
    SessionPage,
    SigningKeyPage,
    SigningKeyResponse,
    SignInProviderPage,
    SignInProviderResponse,
    UserPage,
    UserResponse,
)

router = APIRouter(route_class=AuthorizedRoute, prefix="/api/v1", tags=["security"])


@router.get("/me", response_model=MeResponse)
@requires("signed-in", at=SIGNED_IN)
def get_me(principal: CurrentPrincipal, session: DbSession) -> MeResponse:
    """Who the request's token belongs to: a person or a client; for a person, how they signed in."""
    return present.me_response(session, principal)


def _person(principal: CurrentPrincipal) -> str:
    """The signed-in person's ID; a client has no sessions or password (``403 NOT_A_PERSON``)."""
    if principal.kind != "user":
        raise api_error(403, "NOT_A_PERSON", "Only a signed-in person has sessions and a password")
    return principal.id


@router.get("/me/sessions", response_model=SessionPage)
@requires("signed-in", at=SIGNED_IN)
def list_my_sessions(
    principal: CurrentPrincipal,
    session: DbSession,
    paging: PageQuery,
    page_size: int = Query(default=50, ge=1, le=500, alias="pageSize"),
) -> SessionPage:
    """Where the caller is signed in: their open sessions, ``current`` marking this one."""
    page = sessions.session_page(session, _person(principal), page=paging, page_size=page_size)
    return present.session_page(page, principal.session_id)


@router.delete("/me/sessions/{session_id}", status_code=204)
@requires("signed-in", at=SIGNED_IN)
def delete_my_session(session_id: str, principal: CurrentPrincipal, session: DbSession) -> Response:
    """Sign out one of the caller's sessions; its tokens are refused from the next request and it
    renews no more."""
    sessions.end_session_of(session, _person(principal), session_id)
    return Response(status_code=204)


@router.delete("/me/sessions", status_code=204)
@requires("signed-in", at=SIGNED_IN)
def delete_my_sessions(principal: CurrentPrincipal, session: DbSession) -> Response:
    """Sign out everywhere, this session included (J39.3)."""
    sessions.end_sessions_of(session, _person(principal), "signedOutEverywhere")
    return Response(status_code=204)


@router.post("/me/password", status_code=204)
@requires("signed-in", at=SIGNED_IN)
def post_my_password(
    payload: PasswordChange, principal: CurrentPrincipal, request: Request, session: DbSession
) -> Response:
    """Change the caller's password: the current one must be right (``422 PASSWORD_INCORRECT``) and
    the new one meet the rules (``422 PASSWORD_REJECTED``). Every other session ends (J39.6)."""
    resets.change_password(
        session,
        request.app.state.identity_settings,
        _person(principal),
        principal.session_id,
        payload.currentPassword,
        payload.newPassword,
    )
    return Response(status_code=204)


@router.get("/users", response_model=UserPage)
@requires("security.manage", at=INSTANCE)
def list_users(
    session: DbSession,
    paging: PageQuery,
    q: str | None = Query(default=None, max_length=200),
    active: bool | None = None,
    page_size: int = Query(default=50, ge=1, le=500, alias="pageSize"),
) -> UserPage:
    """People in the order they were created, each with the roles they hold, directly or through a
    group, and where (D298); ``q`` matches the username, name or e-mail."""
    return present.user_page(
        session, user_page(session, q=q, active=active, page=paging, page_size=page_size)
    )


@router.post("/users", response_model=UserResponse, status_code=201)
@requires("security.manage", at=INSTANCE)
def post_user(payload: UserCreate, session: DbSession) -> UserResponse:
    """A person, without a password until they set one; the username is unique ignoring case
    (``409 USERNAME_TAKEN``)."""
    return present.user_response(session, create_user(session, payload))


@router.get("/users/{user_id}", response_model=UserResponse)
@requires("security.manage", at=INSTANCE)
def get_user(user_id: str, session: DbSession) -> UserResponse:
    return present.user_response(session, load_user(session, user_id))


@router.patch("/users/{user_id}", response_model=UserResponse)
@requires("security.manage", at=INSTANCE)
def patch_user(user_id: str, payload: UserUpdate, session: DbSession) -> UserResponse:
    """Change a person's name or e-mail, or deactivate them with ``active: false``: their tokens are
    refused from the next request and their sessions end. A person is never deleted (D237).
    ``localKept`` says whether they sign in with a password while local sign-in is off (D365)."""
    return present.user_response(session, update_user(session, user_id, payload))


@router.post(
    "/users/{user_id}/password-reset", response_model=PasswordResetLinkResponse, status_code=201
)
@requires("security.manage", at=INSTANCE)
def post_password_reset(
    user_id: str, request: Request, session: DbSession
) -> PasswordResetLinkResponse:
    """A one-time link that sets the person's password, answered this once and valid for
    ``PASSWORD_RESET_HOURS``; it replaces any earlier link. Using it ends their sessions (D272).
    While local sign-in is off, refused for a person who does not keep it
    (``409 LOCAL_SIGN_IN_OFF``, D365)."""
    url, expires_at = resets.create_link(session, request.app.state.identity_settings, user_id)
    return PasswordResetLinkResponse(url=url, expiresAt=expires_at)


@router.delete("/users/{user_id}/sessions", status_code=204)
@requires("security.manage", at=INSTANCE)
def delete_user_sessions(user_id: str, session: DbSession) -> Response:
    """Sign the person out everywhere: every session's tokens are refused from the next request."""
    sessions.end_sessions_of(session, user_id, "administrator")
    return Response(status_code=204)


@router.get("/clients", response_model=ClientPage)
@requires("security.manage", at=INSTANCE)
def list_clients(
    session: DbSession,
    paging: PageQuery,
    q: str | None = Query(default=None, max_length=200),
    active: bool | None = None,
    page_size: int = Query(default=50, ge=1, le=500, alias="pageSize"),
) -> ClientPage:
    """OAuth clients in the order they were created; ``q`` matches the name (D300)."""
    return present.client_page(
        session, client_page(session, q=q, active=active, page=paging, page_size=page_size)
    )


@router.post("/clients", response_model=ClientWithSecret, status_code=201)
@requires("security.manage", at=INSTANCE)
def post_client(payload: ClientCreate, session: DbSession) -> ClientWithSecret:
    """A client and its first secret. The answer holds ``secret``, the ``client_secret``: it is never
    answered again."""
    client, secret = create_client(session, payload)
    first = present.client_response(session, client).secrets[0]
    return present.client_with_secret(session, client, first.id, secret)


@router.get("/clients/{client_id}", response_model=ClientResponse)
@requires("security.manage", at=INSTANCE)
def get_client(client_id: str, session: DbSession) -> ClientResponse:
    return present.client_response(session, load_client(session, client_id))


@router.patch("/clients/{client_id}", response_model=ClientResponse)
@requires("security.manage", at=INSTANCE)
def patch_client(client_id: str, payload: ClientUpdate, session: DbSession) -> ClientResponse:
    """Rename a client, or deactivate it with ``active: false``: it obtains no token and the tokens it
    holds are refused from the next request. A client is never deleted (D237)."""
    return present.client_response(session, update_client(session, client_id, payload))


@router.post("/clients/{client_id}/secrets", response_model=ClientWithSecret, status_code=201)
@requires("security.manage", at=INSTANCE)
def post_client_secret(
    client_id: str, payload: ClientSecretCreate, session: DbSession
) -> ClientWithSecret:
    """A new secret, answered once. The client's other secrets stay valid for ``overlapHours``
    (24 by default, 0 to 168), so the system using it switches without a gap (J41.3)."""
    client, added, secret = add_secret(session, client_id, payload)
    return present.client_with_secret(session, client, added.public_id, secret)


@router.delete("/clients/{client_id}/secrets/{secret_id}", response_model=ClientResponse)
@requires("security.manage", at=INSTANCE)
def delete_client_secret(client_id: str, secret_id: str, session: DbSession) -> ClientResponse:
    """Stop a secret at once, before its overlap ends."""
    return present.client_response(session, remove_secret(session, client_id, secret_id))


@router.get("/token-signing-keys", response_model=SigningKeyPage)
@requires("security.manage", at=INSTANCE)
def list_signing_keys(
    session: DbSession,
    paging: PageQuery,
    page_size: int = Query(default=50, ge=1, le=500, alias="pageSize"),
) -> SigningKeyPage:
    """The keys that sign access tokens, newest first, with their state; never a private key."""
    return present.signing_key_page(keys.key_page(session, paging, page_size))


@router.post("/token-signing-keys/rotation", response_model=SigningKeyResponse, status_code=201)
@requires("security.manage", at=INSTANCE)
def rotate_signing_key(
    payload: SigningKeyRotation, request: Request, session: DbSession
) -> SigningKeyResponse:
    """A new signing key for the tokens issued from now on. The previous key accepts the tokens it
    signed until they expire, or, with ``immediate: true`` after a leak, no longer: their holders
    obtain new ones (J43.2). Answers the new key."""
    return present.signing_key_response(
        keys.rotate(session, request.app.state.identity_settings, immediate=payload.immediate)
    )


_AGGREGATE_TYPE = Query(default=None, alias="aggregateType")


@router.get("/security-events", response_model=SecurityEventPage)
@requires("security.manage", at=INSTANCE)
def list_security_events(
    session: DbSession,
    paging: PageQuery,
    principal_id: str | None = Query(default=None, alias="principalId", max_length=36),
    aggregate_type: list[SecurityAggregate] | None = _AGGREGATE_TYPE,
    page_size: int = Query(default=50, ge=1, le=500, alias="pageSize"),
) -> SecurityEventPage:
    """Changes to people, groups, roles, grants, clients and signing keys, and sign-ins, newest
    first, each naming who made it (D317, D318). ``principalId`` keeps those a person or client
    made or that are about them (a group's ID, those about the group)."""
    return present.security_event_page(
        session,
        security_events.event_page(
            session,
            principal_id=principal_id,
            aggregate_types=aggregate_type,
            page=paging,
            page_size=page_size,
        ),
    )


def _redirect_uri(request: Request):
    settings = request.app.state.identity_settings
    return lambda key: providers.redirect_uri(settings, key)


@router.get("/sign-in-providers", response_model=SignInProviderPage)
@requires("security.manage", at=INSTANCE)
def list_sign_in_providers(
    request: Request,
    session: DbSession,
    paging: PageQuery,
    page_size: int = Query(default=50, ge=1, le=500, alias="pageSize"),
) -> SignInProviderPage:
    """The OpenID Connect providers people sign in with, as created (0.12 I3); never a secret."""
    return present.sign_in_provider_page(
        session,
        providers.provider_page(session, page=paging, page_size=page_size),
        _redirect_uri(request),
    )


@router.post("/sign-in-providers", response_model=SignInProviderResponse, status_code=201)
@requires("security.manage", at=INSTANCE)
def post_sign_in_provider(
    payload: SignInProviderCreate, request: Request, session: DbSession
) -> SignInProviderResponse:
    """A provider; its client secret is sealed and never answered (D366). An enabled one is read
    first: its discovery document must name this issuer and it must publish keys
    (``422 SIGN_IN_PROVIDER_UNREACHABLE`` with the reason). The key is fixed
    (``409 SIGN_IN_PROVIDER_KEY_TAKEN``); register ``redirectUri`` with the provider."""
    provider = providers.create_provider(session, request.app.state.identity_settings, payload)
    return present.sign_in_provider_response(
        session, provider, _redirect_uri(request)(provider.key)
    )


@router.get("/sign-in-providers/local", response_model=LocalSignInResponse)
@requires("security.manage", at=INSTANCE)
def get_local_sign_in(session: DbSession) -> LocalSignInResponse:
    """Whether people sign in with a password, and how many keep it while it is off (D365)."""
    return present.local_sign_in_response(session, providers.local_state(session))


@router.patch("/sign-in-providers/local", response_model=LocalSignInResponse)
@requires("security.manage", at=INSTANCE)
def patch_local_sign_in(payload: LocalSignInUpdate, session: DbSession) -> LocalSignInResponse:
    """Turn local sign-in off or on. Off only once an enabled provider has signed someone in
    (``409 NO_WORKING_PROVIDER``); then only the people who keep it (made on the server by
    ``create_admin``) sign in with a password, and clients are not affected (D365)."""
    return present.local_sign_in_response(session, providers.set_local(session, payload))


@router.get("/sign-in-providers/{key}", response_model=SignInProviderResponse)
@requires("security.manage", at=INSTANCE)
def get_sign_in_provider(key: str, request: Request, session: DbSession) -> SignInProviderResponse:
    return present.sign_in_provider_response(
        session, providers.load_provider(session, key), _redirect_uri(request)(key)
    )


@router.patch("/sign-in-providers/{key}", response_model=SignInProviderResponse)
@requires("security.manage", at=INSTANCE)
def patch_sign_in_provider(
    key: str, payload: SignInProviderUpdate, request: Request, session: DbSession
) -> SignInProviderResponse:
    """Change a provider's settings; a new ``clientSecret`` replaces the saved one. Enabling it, or
    changing an enabled one's issuer, reads it first. Disabling it ends the sessions it started
    (D367)."""
    provider = providers.update_provider(
        session, request.app.state.identity_settings, key, payload
    )
    return present.sign_in_provider_response(session, provider, _redirect_uri(request)(key))


@router.delete("/sign-in-providers/{key}", status_code=204)
@requires("security.manage", at=INSTANCE)
def delete_sign_in_provider(key: str, session: DbSession) -> Response:
    """Delete a provider nobody has signed in with, and the groups made for it; otherwise disable
    it (``409 SIGN_IN_PROVIDER_IN_USE``)."""
    providers.delete_provider(session, key)
    return Response(status_code=204)
