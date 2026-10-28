"""The caller, people, OAuth clients, token signing keys and sign-in providers (Product 0.12 I1, I2,
I3, API.md § Security).

The caller's own routes are for anyone signed in; the rest need Security administration at the
instance (Z1).
"""

from datetime import UTC, datetime

from fastapi import APIRouter, Query, Request, Response

from ...engine.identity import (
    keys,
    links,
    passkeys,
    providers,
    resets,
    second_factor,
    security_events,
    sessions,
)
from ...engine.identity.clients import (
    add_secret,
    client_page,
    create_client,
    load_client,
    remove_secret,
    update_client,
)
from ...engine.identity.users import create_user, load_user, update_user, user_page
from ...engine.mail import links as mail_links
from ...engine.mail import settings as mail_settings
from ...errors import api_error
from ...models.commands import (
    ClientCreate,
    ClientSecretCreate,
    ClientUpdate,
    IdentityLink,
    LocalSignInUpdate,
    PasskeyRemoval,
    PasskeyRename,
    PasswordChange,
    PasswordResetRequest,
    SecondFactorCode,
    SigningKeyRotation,
    SignInProviderCreate,
    SignInProviderUpdate,
    UserCreate,
    UserUpdate,
)
from ...models.database import User
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
    MySecondFactorResponse,
    PasskeyPage,
    PasskeyResponse,
    PasswordResetLinkResponse,
    RecoveryCodesResponse,
    SecondFactorEnrolment,
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
    """Change the caller's password: the current one must be right (``422 PASSWORD_INCORRECT``,
    counted like a wrong sign-in: ``429 SIGN_IN_SLOWED`` while a wait runs) and the new one meet the
    rules (``422 PASSWORD_REJECTED``). Every other session ends (J39.6)."""
    resets.change_password(
        session,
        request.app.state.identity_settings,
        _person(principal),
        principal.session_id,
        payload.currentPassword,
        payload.newPassword,
        _address(request),
    )
    return Response(status_code=204)


def _caller(principal: CurrentPrincipal, session: DbSession) -> User:
    """The signed-in person, as a row (a client has no second factor: ``403 NOT_A_PERSON``)."""
    return load_user(session, _person(principal))


def _address(request: Request) -> str | None:
    return request.client.host if request.client else None


def _factor_state(session: DbSession, user: User) -> MySecondFactorResponse:
    found = second_factor.summary(session, user)
    return MySecondFactorResponse(
        enabled=found is not None,
        confirmedAt=found.confirmed_at if found else None,
        recoveryCodesLeft=found.recovery_left if found else 0,
        passkeys=passkeys.counts(session, [user.id]).get(user.id, 0),
        required=providers.local_state(session).second_factor_required,
    )


@router.get("/me/second-factor", response_model=MySecondFactorResponse)
@requires("signed-in", at=SIGNED_IN)
def get_my_second_factor(principal: CurrentPrincipal, session: DbSession) -> MySecondFactorResponse:
    """Whether the caller has an authenticator app and how many recovery codes are left, and whether
    the instance requires one with a password (0.12 I4b)."""
    return _factor_state(session, _caller(principal, session))


@router.post("/me/second-factor", response_model=SecondFactorEnrolment, status_code=201)
@requires("signed-in", at=SIGNED_IN)
def post_my_second_factor(
    request: Request, principal: CurrentPrincipal, session: DbSession
) -> SecondFactorEnrolment:
    """Start setting up an authenticator app: a new secret, answered once as a key, an
    ``otpauth://`` address and a QR code drawn as an SVG (D386); a secret not yet confirmed is
    replaced. ``409 SECOND_FACTOR_EXISTS`` when one is set up. It works once confirmed."""
    user = _caller(principal, session)
    made = second_factor.begin(
        session,
        request.app.state.identity_settings,
        user,
        second_factor.product_name(session, "RDM Engine"),
        datetime.now(UTC),
    )
    return SecondFactorEnrolment(secret=made.secret, otpauthUri=made.uri, qrSvg=made.svg)


@router.post("/me/second-factor/confirmation", response_model=RecoveryCodesResponse)
@requires("signed-in", at=SIGNED_IN)
def post_my_second_factor_confirmation(
    payload: SecondFactorCode, request: Request, principal: CurrentPrincipal, session: DbSession
) -> RecoveryCodesResponse:
    """Confirm the app with a code it shows: the second factor is on and ten recovery codes are
    answered, once (D385). ``422 CODE_INCORRECT``, ``404 SECOND_FACTOR_NOT_FOUND`` without a secret
    made, ``429 SIGN_IN_SLOWED`` after repeated wrong codes (D271)."""
    codes = second_factor.confirm(
        session,
        request.app.state.identity_settings,
        _caller(principal, session),
        payload.code,
        now=datetime.now(UTC),
        address=_address(request),
    )
    return RecoveryCodesResponse(recoveryCodes=codes)


@router.post("/me/second-factor/recovery-codes", response_model=RecoveryCodesResponse)
@requires("signed-in", at=SIGNED_IN)
def post_my_recovery_codes(
    payload: SecondFactorCode, request: Request, principal: CurrentPrincipal, session: DbSession
) -> RecoveryCodesResponse:
    """Ten new recovery codes, answered once; the old ones stop working. The body's ``code`` is one
    from the app or an unused recovery code."""
    codes = second_factor.new_recovery_codes(
        session,
        request.app.state.identity_settings,
        _caller(principal, session),
        payload.code,
        now=datetime.now(UTC),
        address=_address(request),
    )
    return RecoveryCodesResponse(recoveryCodes=codes)


@router.delete("/me/second-factor", status_code=204)
@requires("signed-in", at=SIGNED_IN)
def delete_my_second_factor(
    payload: SecondFactorCode, request: Request, principal: CurrentPrincipal, session: DbSession
) -> Response:
    """Remove the caller's second factor with a code from the app or a recovery code; refused
    while the instance requires one (``409 SECOND_FACTOR_REQUIRED``)."""
    second_factor.remove(
        session,
        request.app.state.identity_settings,
        _caller(principal, session),
        payload.code,
        now=datetime.now(UTC),
        address=_address(request),
    )
    return Response(status_code=204)


@router.get("/me/passkeys", response_model=PasskeyPage)
@requires("signed-in", at=SIGNED_IN)
def list_my_passkeys(
    principal: CurrentPrincipal,
    session: DbSession,
    paging: PageQuery,
    page_size: int = Query(default=50, ge=1, le=500, alias="pageSize"),
) -> PasskeyPage:
    """The caller's passkeys in the order they were made, by the name they gave (0.12 I4c, D394);
    never the credential. A passkey is added on the engine's own page, `/oauth/passkeys/new`."""
    user = _caller(principal, session)
    return present.passkey_page(
        passkeys.passkey_page(session, user, page=paging, page_size=page_size)
    )


@router.patch("/me/passkeys/{passkey_id}", response_model=PasskeyResponse)
@requires("signed-in", at=SIGNED_IN)
def patch_my_passkey(
    passkey_id: str, payload: PasskeyRename, principal: CurrentPrincipal, session: DbSession
) -> PasskeyResponse:
    """Rename one of the caller's passkeys. `404 PASSKEY_NOT_FOUND` for another person's."""
    user = _caller(principal, session)
    return present.passkey_response(passkeys.rename(session, user, passkey_id, payload.name))


@router.delete("/me/passkeys/{passkey_id}", status_code=204)
@requires("signed-in", at=SIGNED_IN)
def delete_my_passkey(
    passkey_id: str,
    request: Request,
    principal: CurrentPrincipal,
    session: DbSession,
    payload: PasskeyRemoval | None = None,
) -> Response:
    """Remove one of the caller's passkeys. The body's ``proof`` is their password, or a code from
    the app or a recovery code (`422 PROOF_REQUIRED`, `422 CODE_INCORRECT`, `429 SIGN_IN_SLOWED`),
    so a stolen session cannot strip a person's passkeys; their last one is refused while the
    instance requires a second factor and they have no authenticator app
    (`409 SECOND_FACTOR_REQUIRED`)."""
    user = _caller(principal, session)
    second_factor.prove(
        session,
        request.app.state.identity_settings,
        user,
        payload.proof if payload else None,
        now=datetime.now(UTC),
        address=_address(request),
    )
    passkeys.remove(session, user, passkey_id, by="self")
    return Response(status_code=204)


@router.get("/users/{user_id}/passkeys", response_model=PasskeyPage)
@requires("security.manage", at=INSTANCE)
def list_user_passkeys(
    user_id: str,
    session: DbSession,
    paging: PageQuery,
    page_size: int = Query(default=50, ge=1, le=500, alias="pageSize"),
) -> PasskeyPage:
    """A person's passkeys, as they named them (D394); never the credential."""
    user = load_user(session, user_id)
    return present.passkey_page(
        passkeys.passkey_page(session, user, page=paging, page_size=page_size)
    )


@router.delete("/users/{user_id}/passkeys/{passkey_id}", status_code=204)
@requires("security.manage", at=INSTANCE)
def delete_user_passkey(user_id: str, passkey_id: str, session: DbSession) -> Response:
    """Remove a person's passkey, for someone who lost the device (D387, D394); a security event
    records it."""
    passkeys.remove(session, load_user(session, user_id), passkey_id, by="administrator")
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
    ``localKept`` says whether they sign in with a password while local sign-in is off (D365); while
    it is off, the last active person who keeps it can neither lose it nor be deactivated
    (``409 LAST_LOCAL_ADMINISTRATOR``, D381)."""
    return present.user_response(session, update_user(session, user_id, payload))


@router.post(
    "/users/{user_id}/password-reset", response_model=PasswordResetLinkResponse, status_code=201
)
@requires("security.manage", at=INSTANCE)
def post_password_reset(
    user_id: str,
    request: Request,
    session: DbSession,
    payload: PasswordResetRequest | None = None,
) -> PasswordResetLinkResponse:
    """A one-time link that sets the person's password, answered this once and valid for
    ``PASSWORD_RESET_HOURS``; it replaces any earlier link. Using it ends their sessions (D272).
    With ``send: true`` it is also queued as mail to the person's address and ``sentTo`` names it
    (SP3, D418); ``409 MAIL_NOT_SET_UP`` and ``409 NO_EMAIL`` leave the earlier link as it was.
    While local sign-in is off, refused for a person who does not keep it
    (``409 LOCAL_SIGN_IN_OFF``, D365)."""
    identity = request.app.state.identity_settings
    if payload is not None and payload.send:
        url, expires_at, sent_to = mail_links.create_and_send(session, identity, user_id)
        return PasswordResetLinkResponse(url=url, expiresAt=expires_at, sentTo=sent_to)
    base = mail_settings.reset_link_base(session, identity)
    url, expires_at = resets.create_link(session, identity, user_id, base=base)
    return PasswordResetLinkResponse(url=url, expiresAt=expires_at)


@router.post("/users/{user_id}/identities", response_model=UserResponse)
@requires("security.manage", at=INSTANCE)
def post_user_identities(user_id: str, payload: IdentityLink, session: DbSession) -> UserResponse:
    """Move the provider identities and provider-group memberships of the person ``fromUserId`` (the
    one a provider sign-in made) onto this person, and deactivate that person; their sessions end.
    Refused `409 PERSON_HAS_ACCESS` when they have a password, direct roles or local groups,
    `409 IDENTITY_PROVIDER_TAKEN` when this person already signs in with one of those providers,
    `409 NO_IDENTITY_TO_LINK` when they have none (D377, D378)."""
    return present.user_response(session, links.link(session, user_id, payload))


@router.delete("/users/{user_id}/identities/{provider}", status_code=204)
@requires("security.manage", at=INSTANCE)
def delete_user_identity(user_id: str, provider: str, session: DbSession) -> Response:
    """Undo a link: remove the person's identity at a provider, their memberships in its groups and
    the sessions it started. The next sign-in with that provider makes a new person."""
    links.unlink(session, user_id, provider)
    return Response(status_code=204)


@router.delete("/users/{user_id}/second-factor", status_code=204)
@requires("security.manage", at=INSTANCE)
def delete_user_second_factor(user_id: str, session: DbSession) -> Response:
    """Remove a person's second factor and recovery codes, for someone who lost the phone and the
    codes (D387); a security event records it, and they set one up again at their next sign-in
    when the instance requires it. ``404 SECOND_FACTOR_NOT_FOUND`` when they have none."""
    second_factor.remove_for(session, load_user(session, user_id))
    return Response(status_code=204)


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
        request.app.state.identity_settings,
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
    return present.sign_in_provider_response(session, provider, request.app.state.identity_settings)


@router.get("/sign-in-providers/local", response_model=LocalSignInResponse)
@requires("security.manage", at=INSTANCE)
def get_local_sign_in(session: DbSession) -> LocalSignInResponse:
    """Whether people sign in with a password, and how many keep it while it is off (D365)."""
    return present.local_sign_in_response(session, providers.local_state(session))


@router.patch("/sign-in-providers/local", response_model=LocalSignInResponse)
@requires("security.manage", at=INSTANCE)
def patch_local_sign_in(payload: LocalSignInUpdate, session: DbSession) -> LocalSignInResponse:
    """Turn local sign-in off or on, and require a second factor with a password or not. Off only
    once an enabled provider has signed someone in (``409 NO_WORKING_PROVIDER``); then only the
    people who keep it (made on the server by ``create_admin``) sign in with a password, and clients
    are not affected (D365). With ``secondFactorRequired`` a person with a password but no
    authenticator app sets one up on the sign-in page before their session starts; a provider's
    sign-ins are never asked (D388)."""
    return present.local_sign_in_response(session, providers.set_local(session, payload))


@router.get("/sign-in-providers/{key}", response_model=SignInProviderResponse)
@requires("security.manage", at=INSTANCE)
def get_sign_in_provider(key: str, request: Request, session: DbSession) -> SignInProviderResponse:
    return present.sign_in_provider_response(
        session, providers.load_provider(session, key), request.app.state.identity_settings
    )


@router.patch("/sign-in-providers/{key}", response_model=SignInProviderResponse)
@requires("security.manage", at=INSTANCE)
def patch_sign_in_provider(
    key: str, payload: SignInProviderUpdate, request: Request, session: DbSession
) -> SignInProviderResponse:
    """Change a provider's settings; a new ``clientSecret`` replaces the saved one. Enabling it, or
    changing an enabled one's issuer, reads it first. Disabling it ends the sessions it started
    (D367)."""
    provider = providers.update_provider(session, request.app.state.identity_settings, key, payload)
    return present.sign_in_provider_response(session, provider, request.app.state.identity_settings)


@router.delete("/sign-in-providers/{key}", status_code=204)
@requires("security.manage", at=INSTANCE)
def delete_sign_in_provider(key: str, session: DbSession) -> Response:
    """Delete a provider nobody has signed in with, and the groups made for it; otherwise disable
    it (``409 SIGN_IN_PROVIDER_IN_USE``)."""
    providers.delete_provider(session, key)
    return Response(status_code=204)
