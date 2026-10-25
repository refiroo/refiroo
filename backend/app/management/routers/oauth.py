"""The engine as its own OAuth 2.0 authorization server (Product 0.12 I1, I2, ADR-043, C-D1).

Outside ``/api/v1`` and needing no token (D245): the server's metadata (RFC 8414), the public keys
that verify its tokens, the token endpoint, the sign-in page and its form, revocation, and the page
a password-reset link opens, and a sign-in provider's start and return (I3). Clients obtain tokens
with their credentials (I1); the browser signs a person in with the authorization code flow and
PKCE (I2), with a password or through a provider (I3), its session held in an ``HttpOnly``,
``SameSite=Strict`` refresh cookie that only ``/oauth`` reads (D234). Errors of the token and
revocation endpoints are in RFC 6749's shape, ``{"error", "error_description"}``, which OAuth client
libraries parse (D250); the pages explain theirs on the page.
"""

import base64
import binascii
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated
from urllib.parse import unquote, urlencode, urlsplit

from fastapi import APIRouter, Depends, Form, Header, Query, Request, Response
from fastapi.responses import JSONResponse, RedirectResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from ...engine.identity import (
    keys,
    passkeys,
    provider_sign_in,
    providers,
    resets,
    second_factor,
    sessions,
    sign_in,
    tokens,
)
from ...engine.identity.clients import authenticate_client
from ...engine.identity.settings import IdentitySettings
from ...errors import ApiError
from ...models.commands import (
    PasskeyAuthentication,
    PasskeyAuthenticationStart,
    PasskeyRegistration,
)
from ...models.database import SignInProvider, User
from .. import sign_in_pages as pages
from ..dependencies import DbSession, started

router = APIRouter(tags=["oauth"])

# The engine's one script (I4c, D390), served at /oauth/passkey.js.
PASSKEY_SCRIPT = Path(__file__).resolve().parent.parent / "passkey.js"

GRANT_TYPES = ["authorization_code", "refresh_token", "client_credentials"]
AUTH_METHODS = ["client_secret_basic", "client_secret_post", "none"]
# The browser's refresh token: read only by the token and revocation endpoints (D234).
REFRESH_COOKIE = "oauth_refresh"
_COOKIE_PATH = "/oauth"
# A provider sign-in's binding to the browser that started it (I3, D361): Lax, since the provider's
# redirect back is a navigation from another site.
PROVIDER_COOKIE = "oauth_provider"
_PROVIDER_PATH = "/oauth/providers"
# Where signing out of a provider returns the browser to once the provider sends it back (I4a).
SIGNED_OUT_COOKIE = "oauth_signed_out"
# Token responses are never cached (RFC 6749 §5.1).
_NO_STORE = {"Cache-Control": "no-store", "Pragma": "no-cache"}
# The fields of an authorization request the sign-in form carries back.
_REQUEST_FIELDS = (
    "response_type",
    "client_id",
    "redirect_uri",
    "code_challenge",
    "code_challenge_method",
    "state",
)


def _settings(request: Request) -> IdentitySettings:
    return request.app.state.identity_settings


def _error(
    status: int, error: str, description: str, headers: dict[str, str] | None = None
) -> JSONResponse:
    return JSONResponse(
        {"error": error, "error_description": description},
        status_code=status,
        headers={**_NO_STORE, **(headers or {})},
    )


@router.get("/.well-known/oauth-authorization-server")
def server_metadata(request: Request) -> dict[str, object]:
    """The authorization server's metadata (RFC 8414): its issuer, endpoints and what it supports."""
    issuer = _settings(request).issuer
    return {
        "issuer": issuer,
        "authorization_endpoint": f"{issuer}/oauth/authorize",
        "token_endpoint": f"{issuer}/oauth/token",
        "revocation_endpoint": f"{issuer}/oauth/revoke",
        "jwks_uri": f"{issuer}/oauth/jwks",
        "grant_types_supported": GRANT_TYPES,
        "token_endpoint_auth_methods_supported": AUTH_METHODS,
        "revocation_endpoint_auth_methods_supported": ["none"],
        "scopes_supported": list(tokens.AUDIENCES),
        "response_types_supported": ["code"],
        "code_challenge_methods_supported": ["S256"],
    }


# Checked before the request's session is opened: in maintenance mode the database may be unusable.
_STARTED = [Depends(started)]


@router.get("/oauth/jwks", dependencies=_STARTED)
def json_web_keys(session: DbSession) -> dict[str, object]:
    """The public keys that verify access tokens now, by ``kid`` (RFC 7517); every process serves
    the same set."""
    return {"keys": keys.published(session)}


# ---------------------------------------------------------------------------------------------
# The sign-in page (I2)


def _product(session: Session) -> str:
    """The name the pages carry: the default workspace's product, as the app's top bar shows it."""
    return second_factor.product_name(session, "Sign in")


def _origins(settings: IdentitySettings) -> tuple[str, ...]:
    return tuple(
        f"{urlsplit(uri).scheme}://{urlsplit(uri).netloc}" for uri in settings.redirect_uris()
    )


def _redirect(redirect_uri: str, **params: str | None) -> RedirectResponse:
    query = urlencode({name: value for name, value in params.items() if value is not None})
    return RedirectResponse(f"{redirect_uri}?{query}", status_code=303, headers=_NO_STORE)


def _authorization_request(
    session: Session, settings: IdentitySettings, fields: dict[str, str | None]
) -> dict[str, str] | Response:
    """The authorization request's fields when the page may serve it; otherwise its answer: an
    explanation for an unknown client or address, which is never redirected to (RFC 6749 §4.1.2.1),
    or a redirect carrying the error."""
    redirect_uri = fields.get("redirect_uri") or ""
    if fields.get("client_id") != sign_in.BROWSER_CLIENT_ID or (
        redirect_uri not in settings.redirect_uris()
    ):
        return pages.problem(
            _product(session),
            "The application that sent you here is not one this engine signs people in to. "
            "Open the application from its usual address and try again.",
            issuer=settings.issuer,
            redirect_origins=_origins(settings),
        )
    state = fields.get("state")
    if fields.get("response_type") != "code":
        return _redirect(redirect_uri, error="unsupported_response_type", state=state)
    if fields.get("code_challenge_method") != "S256" or not sign_in.valid_challenge(
        fields.get("code_challenge")
    ):
        return _redirect(
            redirect_uri,
            error="invalid_request",
            error_description="A PKCE code_challenge with code_challenge_method=S256 is required",
            state=state,
        )
    return {name: value for name in _REQUEST_FIELDS if (value := fields.get(name)) is not None}


@router.get("/oauth/authorize", dependencies=_STARTED, include_in_schema=False)
def authorize_page(
    request: Request,
    session: DbSession,
    response_type: str | None = None,
    client_id: str | None = None,
    redirect_uri: str | None = None,
    code_challenge: str | None = None,
    code_challenge_method: str | None = None,
    state: str | None = None,
    session_ended: Annotated[str | None, Query(alias="session")] = None,
    local: str | None = None,
) -> Response:
    """The engine's sign-in page for the browser (the authorization code flow with PKCE ``S256``).
    ``session=ended`` adds that the person's session ended; ``local=1`` shows the password form
    while local sign-in is off (D365)."""
    settings = _settings(request)
    fields = {
        "response_type": response_type,
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "code_challenge": code_challenge,
        "code_challenge_method": code_challenge_method,
        "state": state,
    }
    checked = _authorization_request(session, settings, fields)
    if isinstance(checked, Response):
        return checked
    local_on = providers.local_enabled(session)
    return pages.sign_in(
        _product(session),
        checked,
        issuer=settings.issuer,
        redirect_origins=_origins(settings),
        ended=session_ended == "ended",
        providers=_buttons(session, checked),
        local=local_on,
        local_link=None
        if local_on or local == "1"
        else _query("/oauth/authorize", checked, local="1"),
        passkey=passkeys.any_exist(session),
    )


def _query(path: str, fields: dict[str, str], **more: str) -> str:
    return f"{path}?{urlencode({**fields, **more})}"


def _buttons(session: Session, fields: dict[str, str]) -> tuple[tuple[str, str], ...]:
    """The enabled providers' buttons, each starting a sign-in with the browser's request (I3)."""
    return tuple(
        (provider.name, _query(f"{_PROVIDER_PATH}/{provider.key}/start", fields))
        for provider in providers.enabled_providers(session)
    )


def _foreign(request: Request, settings: IdentitySettings) -> bool:
    """A form posted from a page that is not the engine's: a forged sign-in (D275). The engine's
    page is at ``PUBLIC_URL``, or at the address this request reached it by."""
    origin = request.headers.get("origin")
    if origin is None:
        return False
    issuer = urlsplit(settings.issuer)
    own = urlsplit(str(request.base_url))
    return origin not in (
        f"{issuer.scheme}://{issuer.netloc}",
        f"{own.scheme}://{own.netloc}",
    )


def _address(request: Request) -> str | None:
    return request.client.host if request.client else None


@router.post("/oauth/authorize", dependencies=_STARTED, include_in_schema=False)
def authorize_form(
    request: Request,
    session: DbSession,
    username: Annotated[str, Form(max_length=320)] = "",
    password: Annotated[str, Form(max_length=1024)] = "",
    response_type: Annotated[str | None, Form()] = None,
    client_id: Annotated[str | None, Form()] = None,
    redirect_uri: Annotated[str | None, Form()] = None,
    code_challenge: Annotated[str | None, Form()] = None,
    code_challenge_method: Annotated[str | None, Form()] = None,
    state: Annotated[str | None, Form()] = None,
) -> Response:
    """The sign-in form: right credentials redirect to the browser with a one-time code and the
    ``state``; wrong ones show the page again without saying which part was wrong; after repeated
    failures it says how long to wait (D271)."""
    settings = _settings(request)
    fields = {
        "response_type": response_type,
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "code_challenge": code_challenge,
        "code_challenge_method": code_challenge_method,
        "state": state,
    }
    checked = _authorization_request(session, settings, fields)
    if isinstance(checked, Response):
        return checked
    origins = _origins(settings)
    if _foreign(request, settings):
        return pages.problem(
            _product(session),
            "This sign-in was sent from another site. Open the application and sign in there.",
            issuer=settings.issuer,
            redirect_origins=origins,
            status=403,
        )
    now = datetime.now(UTC)
    local_on = providers.local_enabled(session)
    outcome = sign_in.check_password(
        session, username, password, _address(request), now, kept_only=not local_on, finish=False
    )
    if isinstance(outcome, sign_in.Refused):
        slowed = outcome.reason == "slowed"
        return pages.sign_in(
            _product(session),
            checked,
            issuer=settings.issuer,
            redirect_origins=origins,
            username=username,
            wrong=not slowed,
            wait_seconds=outcome.wait_seconds,
            status=429 if slowed else 401,
            providers=_buttons(session, checked),
            local=local_on,
            passkey=passkeys.any_exist(session),
        )
    stage = second_factor.required_step(session, outcome)
    if stage is None:
        sign_in.complete(session, outcome, username, _address(request))
        session.commit()
        return _issue(session, checked, outcome, now)
    token = second_factor.open_step(session, outcome, checked, stage, now)
    return _factor_page(
        session,
        settings,
        checked,
        outcome,
        token,
        stage,
        now=now,
        product=_product(session),
        fresh=True,
    )


def _issue(session: Session, checked: dict[str, str], user: User, now: datetime) -> Response:
    """The browser's one-time code for a sign-in with a password that is whole."""
    code = sign_in.issue_code(
        session,
        user,
        redirect_uri=checked["redirect_uri"],
        code_challenge=checked["code_challenge"],
        signed_in_with="password",
        now=now,
    )
    return _redirect(checked["redirect_uri"], code=code, state=checked.get("state"))


def _factor_page(
    session: Session,
    settings: IdentitySettings,
    checked: dict[str, str],
    user: User,
    token: str,
    stage: str,
    *,
    now: datetime,
    product: str,
    recovery: bool = False,
    wrong: bool = False,
    wait_seconds: int = 0,
    fresh: bool = False,
) -> Response:
    """The page of a sign-in's second step: the code, or the set-up that the requirement asks of a
    person without a second factor (I4b, D388)."""
    status = 429 if wait_seconds else 401 if wrong else 200
    common = {"issuer": settings.issuer, "redirect_origins": _origins(settings)}
    if stage == "setup":
        made = second_factor.begin(session, settings, user, product, now, restart=fresh)
        return pages.second_factor_setup(
            product, token, secret=made.secret, svg=made.svg, wrong=wrong,
            wait_seconds=wait_seconds, status=status, **common,
        )  # fmt: skip
    return pages.second_factor_code(
        product, token, user.username, start_again=_query("/oauth/authorize", checked),
        recovery=recovery, wrong=wrong, wait_seconds=wait_seconds, status=status,
        app=second_factor.summary(session, user) is not None,
        passkey=passkeys.has_any(session, user), **common,
    )  # fmt: skip


@router.post("/oauth/second-factor", dependencies=_STARTED, include_in_schema=False)
def second_factor_form(
    request: Request,
    session: DbSession,
    step: Annotated[str, Form(max_length=128)] = "",
    code: Annotated[str, Form(max_length=64)] = "",
    recovery: Annotated[str, Form(max_length=64)] = "",
    view: Annotated[str | None, Form(max_length=16)] = None,
    carry_on: Annotated[str | None, Form(alias="continue", max_length=8)] = None,
) -> Response:
    """The second step of a sign-in with a password (I4b, D388): the code from the authenticator
    app or a recovery code; or, when the instance requires a second factor and the person has none,
    the set-up (a code to confirm, then the recovery codes before **Continue**). A wrong code is
    counted like a wrong password (D271). The step's token, from the password page, is the only
    state; it lasts five minutes and is used once."""
    settings = _settings(request)
    product = _product(session)
    origins = _origins(settings)
    if _foreign(request, settings):
        return pages.problem(
            product,
            "This sign-in was sent from another site. Open the application and sign in there.",
            issuer=settings.issuer,
            redirect_origins=origins,
            status=403,
        )
    now = datetime.now(UTC)
    loaded = second_factor.load_step(session, step, now)
    if loaded is None:
        return pages.problem(
            product,
            "This sign-in took longer than five minutes, or was already used. Open the application "
            "and sign in again.",
            issuer=settings.issuer,
            redirect_origins=origins,
            status=410,
        )
    row, user = loaded
    checked = _authorization_request(session, settings, dict(row.request))
    if isinstance(checked, Response):
        return checked
    address = _address(request)

    def again(*, recovering: bool = False, **more: bool | int) -> Response:
        return _factor_page(
            session, settings, checked, user, step, row.stage, now=now, product=product,
            recovery=recovering, **more,
        )  # fmt: skip

    def done() -> Response:
        second_factor.finish_step(session, row, user, address, now)
        session.commit()
        return _issue(session, checked, user, now)

    if row.stage == "codes":
        return done()
    typed = recovery.strip() or code.strip()
    recovering = bool(recovery.strip()) or (view == "recovery" and not code.strip())
    if not typed:
        return again(recovering=recovering)
    try:
        if row.stage == "setup":
            codes = second_factor.confirm(
                session, settings, user, typed, now=now, address=address, api=False
            )
        else:
            second_factor.check(
                session, settings, user, typed, now=now, address=address,
                kind="recovery" if recovering else "app",
            )  # fmt: skip
    except second_factor.CodeRefused as refused:
        return again(
            recovering=recovering,
            wrong=refused.reason == "wrong",
            wait_seconds=refused.wait_seconds,
        )
    if row.stage == "setup":
        second_factor.advance(row, "codes", now)
        session.commit()
        return pages.recovery_codes(
            product, step, codes, issuer=settings.issuer, redirect_origins=origins
        )
    return done()


# ---------------------------------------------------------------------------------------------
# A sign-in provider (I3)


def _provider(session: Session, settings: IdentitySettings, key: str) -> SignInProvider | Response:
    provider = session.scalar(select(SignInProvider).where(SignInProvider.key == key))
    if provider is None:
        return pages.problem(
            _product(session),
            "There is no such sign-in provider. Open the application and sign in from its page.",
            issuer=settings.issuer,
            redirect_origins=_origins(settings),
            status=404,
        )
    return provider


def _provider_problem(
    session: Session,
    settings: IdentitySettings,
    provider: SignInProvider,
    failed: provider_sign_in.SignInFailed,
) -> Response:
    retry = _query("/oauth/authorize", failed.request) if failed.request else None
    response = pages.provider_problem(
        _product(session),
        provider.name,
        failed.message,
        retry_url=retry,
        issuer=settings.issuer,
        redirect_origins=_origins(settings),
        status=403 if failed.reason in ("disabled", "deactivated") else 400,
    )
    response.delete_cookie(
        PROVIDER_COOKIE, path=_PROVIDER_PATH, secure=settings.secure_cookies, httponly=True,
        samesite="lax",
    )  # fmt: skip
    return response


@router.get("/oauth/providers/{key}/start", dependencies=_STARTED, include_in_schema=False)
def provider_start(
    key: str,
    request: Request,
    session: DbSession,
    response_type: str | None = None,
    client_id: str | None = None,
    redirect_uri: str | None = None,
    code_challenge: str | None = None,
    code_challenge_method: str | None = None,
    state: str | None = None,
) -> Response:
    """The sign-in page's "Continue with" button: the browser's authorization request is kept and
    the browser sent to the provider (D361)."""
    settings = _settings(request)
    fields = {
        "response_type": response_type,
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "code_challenge": code_challenge,
        "code_challenge_method": code_challenge_method,
        "state": state,
    }
    checked = _authorization_request(session, settings, fields)
    if isinstance(checked, Response):
        return checked
    provider = _provider(session, settings, key)
    if isinstance(provider, Response):
        return provider
    try:
        started = provider_sign_in.start(
            session, settings, provider, checked, address=_address(request), now=datetime.now(UTC)
        )
    except provider_sign_in.SignInFailed as failed:
        return _provider_problem(session, settings, provider, failed)
    response = RedirectResponse(started.url, status_code=303, headers=_NO_STORE)
    response.set_cookie(
        PROVIDER_COOKIE,
        started.browser_token,
        max_age=provider_sign_in.SIGN_IN_MINUTES * 60,
        path=_PROVIDER_PATH,
        secure=settings.secure_cookies,
        httponly=True,
        samesite="lax",
    )
    return response


@router.get("/oauth/providers/{key}/callback", dependencies=_STARTED, include_in_schema=False)
def provider_callback(
    key: str,
    request: Request,
    session: DbSession,
    state: str | None = None,
    code: str | None = None,
    error: str | None = None,
    error_description: str | None = None,
) -> Response:
    """Where the provider returns the browser: the answer checked, the person found or created, and
    the browser sent back with a one-time code as the password form does (D361, D368)."""
    settings = _settings(request)
    provider = _provider(session, settings, key)
    if isinstance(provider, Response):
        return provider
    now = datetime.now(UTC)
    try:
        user, browser_request, id_token = provider_sign_in.finish(
            session,
            settings,
            provider,
            state=state,
            code=code,
            error=(error or "")[:200] or None,
            error_description=(error_description or "")[:300] or None,
            browser_token=request.cookies.get(PROVIDER_COOKIE),
            address=_address(request),
            now=now,
        )
    except provider_sign_in.SignInFailed as failed:
        return _provider_problem(session, settings, provider, failed)
    checked = _authorization_request(session, settings, browser_request)
    if isinstance(checked, Response):
        return checked
    issued = sign_in.issue_code(
        session,
        user,
        redirect_uri=checked["redirect_uri"],
        code_challenge=checked["code_challenge"],
        signed_in_with=provider.key,
        now=now,
        provider_id_token=id_token,
    )
    response = _redirect(checked["redirect_uri"], code=issued, state=checked.get("state"))
    response.delete_cookie(
        PROVIDER_COOKIE, path=_PROVIDER_PATH, secure=settings.secure_cookies, httponly=True,
        samesite="lax",
    )  # fmt: skip
    return response


def _return_address(settings: IdentitySettings, requested: str | None) -> str:
    """Where signing out ends: the application's address when it is one of the browser's origins,
    else the first origin's front page (never another site, so the endpoint cannot be used to
    redirect anywhere)."""
    origins = _origins(settings)
    if requested:
        parts = urlsplit(requested)
        if f"{parts.scheme}://{parts.netloc}" in origins:
            return requested
    return f"{origins[0]}/" if origins else settings.issuer


@router.get("/oauth/sign-out", dependencies=_STARTED, include_in_schema=False)
def sign_out(
    request: Request,
    session: DbSession,
    return_to: Annotated[str | None, Query(alias="return", max_length=2000)] = None,
) -> Response:
    """Sign out by navigation: the session ends from the browser's cookie, which is cleared, and
    the browser goes back to the application, or first to the provider's sign-out address when the
    provider that started the session signs people out too (I4a, D380)."""
    settings = _settings(request)
    target = _return_address(settings, return_to)
    presented = request.cookies.get(REFRESH_COOKIE)
    provider_url = provider_sign_in.sign_out(session, settings, presented) if presented else None
    response = RedirectResponse(provider_url or target, status_code=303, headers=_NO_STORE)
    if provider_url:
        response.set_cookie(
            SIGNED_OUT_COOKIE, target, max_age=600, path=_PROVIDER_PATH,
            secure=settings.secure_cookies, httponly=True, samesite="lax",
        )  # fmt: skip
    _clear_refresh_cookie(response, settings)
    return response


@router.get("/oauth/providers/{key}/signed-out", dependencies=_STARTED, include_in_schema=False)
def provider_signed_out(key: str, request: Request, state: str | None = None) -> Response:
    """Where a provider returns the browser after signing the person out: back to the application
    sign-out started from."""
    # The address is registered per provider and the provider echoes the ``state`` it was sent;
    # the cookie holds where this browser goes.
    del key, state
    settings = _settings(request)
    response = RedirectResponse(
        _return_address(settings, request.cookies.get(SIGNED_OUT_COOKIE)),
        status_code=303,
        headers=_NO_STORE,
    )
    response.delete_cookie(
        SIGNED_OUT_COOKIE, path=_PROVIDER_PATH, secure=settings.secure_cookies, httponly=True,
        samesite="lax",
    )  # fmt: skip
    return response


# ---------------------------------------------------------------------------------------------
# Passkeys (I4c): the engine's own pages and the one script they load


@router.get("/oauth/passkey.js", include_in_schema=False)
def passkey_script() -> Response:
    """The engine's one script (D390): it asks the browser for a passkey and posts the answer to the
    endpoints below. The pages that offer a passkey allow this file and nothing else."""
    return Response(
        PASSKEY_SCRIPT.read_text(encoding="utf-8"),
        media_type="text/javascript",
        headers={"Cache-Control": "no-cache", "X-Content-Type-Options": "nosniff"},
    )


def _passkey_error(message: str, status: int, wait_seconds: int = 0) -> JSONResponse:
    headers = {"Retry-After": str(wait_seconds)} if wait_seconds else None
    return JSONResponse(
        {"error": message}, status_code=status, headers={**_NO_STORE, **(headers or {})}
    )


def _cookie_user(request: Request, session: Session) -> User | None:
    """The person whose session the browser's cookie holds, which only ``/oauth`` reads (D234)."""
    token = request.cookies.get(REFRESH_COOKIE)
    return sessions.user_of_refresh_token(session, token, datetime.now(UTC)) if token else None


@router.get("/oauth/passkeys/new", dependencies=_STARTED, include_in_schema=False)
def passkey_add_page(
    request: Request,
    session: DbSession,
    return_to: Annotated[str | None, Query(alias="return", max_length=2000)] = None,
) -> Response:
    """Add a passkey (D392): the page asks the person's name for it and runs the browser's prompt.
    It serves a person with a session in this browser; ``return`` is where it goes afterwards, an
    address at one of the browser's origins."""
    settings = _settings(request)
    user = _cookie_user(request, session)
    if user is None:
        return pages.problem(
            _product(session),
            "Sign in to the application first, then add a passkey from Account.",
            issuer=settings.issuer,
            redirect_origins=_origins(settings),
            status=401,
        )
    return pages.passkey_add(
        _product(session),
        user.username,
        _return_address(settings, return_to),
        issuer=settings.issuer,
        redirect_origins=_origins(settings),
    )


def _ceremony_guard(request: Request, settings: IdentitySettings) -> JSONResponse | None:
    """A passkey ceremony posted from another site is refused, as a forged sign-in is (D275)."""
    if _foreign(request, settings):
        return _passkey_error("This was sent from another site.", 403)
    return None


@router.post("/oauth/passkeys/registration/options", dependencies=_STARTED, include_in_schema=False)
def passkey_registration_options(request: Request, session: DbSession) -> Response:
    """The browser's options for creating a passkey of the person this browser is signed in as; the
    answer is ``{ceremony, options}``."""
    settings = _settings(request)
    if refused := _ceremony_guard(request, settings):
        return refused
    user = _cookie_user(request, session)
    if user is None:
        return _passkey_error("Sign in to the application first.", 401)
    try:
        token, options = passkeys.begin_registration(
            session, settings, user, _product(session), datetime.now(UTC)
        )
    except ApiError as failure:
        return _passkey_error(failure.message, failure.status_code)
    return JSONResponse({"ceremony": token, "options": options}, headers=_NO_STORE)


@router.post("/oauth/passkeys/registration/verify", dependencies=_STARTED, include_in_schema=False)
def passkey_registration_verify(
    payload: PasskeyRegistration, request: Request, session: DbSession
) -> Response:
    """Check what the browser created and keep it as the person's passkey."""
    settings = _settings(request)
    if refused := _ceremony_guard(request, settings):
        return refused
    user = _cookie_user(request, session)
    if user is None:
        return _passkey_error("Sign in to the application first.", 401)
    try:
        passkey = passkeys.finish_registration(
            session, settings, user, payload.ceremony, payload.credential, payload.name,
            datetime.now(UTC),
        )  # fmt: skip
    except passkeys.PasskeyRefused as failure:
        return _passkey_error(failure.message, failure.status)
    return JSONResponse({"id": passkey.public_id, "name": passkey.name}, headers=_NO_STORE)


@router.post(
    "/oauth/passkeys/authentication/options", dependencies=_STARTED, include_in_schema=False
)
def passkey_authentication_options(
    payload: PasskeyAuthenticationStart, request: Request, session: DbSession
) -> Response:
    """The browser's options for signing in with a passkey: for the second step of a password
    sign-in (``step``, the token its page carries) or alone (the browser's authorization request).
    The answer is ``{ceremony, options}``."""
    settings = _settings(request)
    if refused := _ceremony_guard(request, settings):
        return refused
    now = datetime.now(UTC)
    try:
        if payload.step:
            loaded = second_factor.load_step(session, payload.step, now)
            if loaded is None or loaded[0].stage != "code":
                return _passkey_error(
                    "This sign-in took too long, or was already used. Start again.", 410
                )
            _, options = passkeys.begin_authentication(session, settings, now, step=loaded)
            return JSONResponse({"ceremony": payload.step, "options": options}, headers=_NO_STORE)
        checked = _authorization_request(session, settings, payload.request_fields())
        if isinstance(checked, Response):
            return _passkey_error("This sign-in request is not one the engine serves.", 400)
        token, options = passkeys.begin_authentication(session, settings, now, request=checked)
    except passkeys.PasskeyRefused as failure:
        return _passkey_error(failure.message, failure.status, failure.wait_seconds)
    return JSONResponse({"ceremony": token, "options": options}, headers=_NO_STORE)


@router.post(
    "/oauth/passkeys/authentication/verify", dependencies=_STARTED, include_in_schema=False
)
def passkey_authentication_verify(
    payload: PasskeyAuthentication, request: Request, session: DbSession
) -> Response:
    """Check the browser's answer. A passkey that signs the person in ends as the password form
    does: the answer is ``{redirect}``, the browser's address with a one-time code and its
    ``state``. A wrong one is ``401``, counted like a wrong password (D271)."""
    settings = _settings(request)
    if refused := _ceremony_guard(request, settings):
        return refused
    now = datetime.now(UTC)
    try:
        second = second_factor.load_step(session, payload.ceremony, now)
        done = passkeys.finish_authentication(
            session, settings, payload.ceremony, payload.credential,
            second_step=second if second and second[0].stage == "code" else None,
            address=_address(request), now=now,
        )  # fmt: skip
    except passkeys.PasskeyRefused as failure:
        return _passkey_error(failure.message, failure.status, failure.wait_seconds)
    checked = _authorization_request(session, settings, done.request)
    if isinstance(checked, Response):
        return _passkey_error("This sign-in request is not one the engine serves.", 400)
    code = sign_in.issue_code(
        session,
        done.user,
        redirect_uri=checked["redirect_uri"],
        code_challenge=checked["code_challenge"],
        signed_in_with="password" if done.second_step else "passkey",
        now=now,
    )
    query = urlencode({"code": code, **({"state": checked["state"]} if "state" in checked else {})})
    return JSONResponse({"redirect": f"{checked['redirect_uri']}?{query}"}, headers=_NO_STORE)


# ---------------------------------------------------------------------------------------------
# The token endpoint


def _basic(authorization: str) -> tuple[str, str] | None:
    """The client ID and secret of an ``Authorization: Basic`` header (RFC 6749 §2.3.1)."""
    scheme, _, encoded = authorization.strip().partition(" ")
    if scheme.lower() != "basic":
        return None
    try:
        decoded = base64.b64decode(encoded.strip(), validate=True).decode()
    except binascii.Error, UnicodeDecodeError:
        return None
    client_id, colon, secret = decoded.partition(":")
    if not colon:
        return None
    return unquote(client_id), unquote(secret)


def _token_response(settings: IdentitySettings, access_token: str, audience: str) -> JSONResponse:
    return JSONResponse(
        {
            "access_token": access_token,
            "token_type": "Bearer",
            "expires_in": settings.access_token_seconds,
            "scope": audience,
        },
        headers=_NO_STORE,
    )


def _set_refresh_cookie(
    response: Response, settings: IdentitySettings, token: str, ends_at: datetime
) -> None:
    response.set_cookie(
        REFRESH_COOKIE,
        token,
        max_age=max(int((ends_at - datetime.now(UTC)).total_seconds()), 0),
        path=_COOKIE_PATH,
        secure=settings.secure_cookies,
        httponly=True,
        samesite="strict",
    )


def _clear_refresh_cookie(response: Response, settings: IdentitySettings) -> None:
    response.delete_cookie(
        REFRESH_COOKIE,
        path=_COOKIE_PATH,
        secure=settings.secure_cookies,
        httponly=True,
        samesite="strict",
    )


def _person_token(
    request: Request,
    session: Session,
    audience: tokens.Audience,
    user_session_id: str,
    user_public_id: str,
    refresh_token: str,
    ends_at: datetime,
) -> JSONResponse:
    settings = _settings(request)
    access_token = tokens.issue(
        session,
        settings,
        subject=user_public_id,
        kind="user",
        audience=audience,
        session_id=user_session_id,
    )
    response = _token_response(settings, access_token, audience)
    _set_refresh_cookie(response, settings, refresh_token, ends_at)
    return response


@router.post("/oauth/token", dependencies=_STARTED)
def token(
    request: Request,
    session: DbSession,
    grant_type: Annotated[str | None, Form()] = None,
    scope: Annotated[str | None, Form()] = None,
    client_id: Annotated[str | None, Form()] = None,
    client_secret: Annotated[str | None, Form()] = None,
    code: Annotated[str | None, Form()] = None,
    code_verifier: Annotated[str | None, Form()] = None,
    redirect_uri: Annotated[str | None, Form()] = None,
    refresh_token: Annotated[str | None, Form()] = None,
    authorization: Annotated[str | None, Header(alias="Authorization")] = None,
) -> JSONResponse:
    """An access token. ``client_credentials``: a client's credentials, sent as
    ``client_secret_basic`` or ``client_secret_post``. ``authorization_code``: the browser's
    sign-in code with its PKCE ``code_verifier`` and ``redirect_uri``, ``client_id=browser``; it
    starts a session. ``refresh_token``: the session's refresh token, from the cookie (or the
    form), ``client_id=browser``; each is used once. The browser's grants answer a new refresh
    cookie. ``scope`` is ``management`` (the default) or ``consumer``, the API the token is for
    (D260). The answer is RFC 6749's: ``access_token``, ``token_type: "Bearer"``, ``expires_in``
    and ``scope``."""
    if not grant_type:
        return _error(400, "invalid_request", "grant_type is required")
    if grant_type not in GRANT_TYPES:
        return _error(
            400, "unsupported_grant_type", f"This server issues tokens for {', '.join(GRANT_TYPES)}"
        )
    audience = scope.strip() if scope and scope.strip() else "management"
    if audience not in tokens.AUDIENCES:
        return _error(
            400, "invalid_scope", f"scope is one of {', '.join(tokens.AUDIENCES)}, not {scope!r}"
        )
    settings = _settings(request)
    if grant_type != "client_credentials":
        if authorization or client_secret or client_id != sign_in.BROWSER_CLIENT_ID:
            return _error(
                401,
                "invalid_client",
                f"This grant is for the browser's client, client_id={sign_in.BROWSER_CLIENT_ID}, "
                "with no secret",
            )
        if grant_type == "authorization_code":
            if not code or not code_verifier or not redirect_uri:
                return _error(
                    400, "invalid_request", "code, code_verifier and redirect_uri are required"
                )
            try:
                user_session, user, refresh = sign_in.redeem_code(
                    session,
                    settings,
                    code=code,
                    verifier=code_verifier,
                    redirect_uri=redirect_uri,
                    user_agent=request.headers.get("user-agent"),
                )
            except sign_in.CodeRefused:
                return _error(
                    400,
                    "invalid_grant",
                    "The code is unknown, expired or used, or its verifier or address differs",
                )
            return _person_token(
                request,
                session,
                audience,
                user_session.public_id,
                user.public_id,
                refresh,
                user_session.ends_at,
            )
        presented = refresh_token or request.cookies.get(REFRESH_COOKIE)
        if not presented:
            return _error(400, "invalid_request", "No refresh token was sent")
        try:
            renewed = sessions.renew(session, settings, presented, datetime.now(UTC))
        except sessions.SessionRefused:
            response = _error(400, "invalid_grant", "The session has ended; sign in again")
            _clear_refresh_cookie(response, settings)
            return response
        return _person_token(
            request,
            session,
            audience,
            renewed.user_session.public_id,
            renewed.user.public_id,
            renewed.refresh_token,
            renewed.user_session.ends_at,
        )
    basic = _basic(authorization) if authorization else None
    if basic is not None and (client_id is not None or client_secret is not None):
        return _error(400, "invalid_request", "Send the client's credentials one way, not both")
    credentials = basic or (client_id, client_secret)
    challenge = {"WWW-Authenticate": 'Basic realm="oauth"'} if basic is not None else None
    if not credentials[0] or not credentials[1]:
        return _error(401, "invalid_client", "The client's credentials are missing", challenge)
    client = authenticate_client(session, credentials[0], credentials[1])
    if client is None:
        return _error(
            401,
            "invalid_client",
            "The client is unknown, inactive or its secret is wrong",
            challenge,
        )
    access_token = tokens.issue(
        session, settings, subject=client.public_id, kind="client", audience=audience
    )
    return _token_response(settings, access_token, audience)


@router.post("/oauth/revoke", dependencies=_STARTED)
def revoke(
    request: Request,
    session: DbSession,
    token: Annotated[str | None, Form()] = None,
    token_type_hint: Annotated[str | None, Form()] = None,
) -> Response:
    """Sign out (RFC 7009): the session the refresh token belongs to ends, from the form's
    ``token`` or the browser's cookie, and the cookie is cleared. An unknown token, or an access
    token, is answered the same: ``200``."""
    del token_type_hint  # Only refresh tokens are revoked here; the hint changes nothing.
    presented = token or request.cookies.get(REFRESH_COOKIE)
    if presented:
        sessions.end_by_refresh_token(session, presented, "signedOut")
    response = Response(status_code=200, headers=_NO_STORE)
    _clear_refresh_cookie(response, _settings(request))
    return response


# ---------------------------------------------------------------------------------------------
# The password-reset link's page (D272)


def _link_gone(session: Session, settings: IdentitySettings) -> Response:
    return pages.problem(
        _product(session),
        "This link has been used, replaced by a newer one, or has expired. Ask a security "
        "administrator for a new one.",
        issuer=settings.issuer,
        redirect_origins=_origins(settings),
        status=410,
    )


@router.get("/oauth/password", dependencies=_STARTED, include_in_schema=False)
def password_page(
    request: Request, session: DbSession, token: Annotated[str, Query(max_length=128)] = ""
) -> Response:
    """The page a password-reset link opens: a new password for the person it names."""
    settings = _settings(request)
    user = resets.link_user(session, token) if token else None
    if user is None:
        return _link_gone(session, settings)
    return pages.password(
        _product(session),
        token,
        issuer=settings.issuer,
        redirect_origins=_origins(settings),
        username=user.username,
        min_length=settings.password_min_length,
    )


@router.post("/oauth/password", dependencies=_STARTED, include_in_schema=False)
def password_form(
    request: Request,
    session: DbSession,
    token: Annotated[str, Form(max_length=128)] = "",
    password: Annotated[str, Form(max_length=1024)] = "",
    repeat: Annotated[str, Form(max_length=1024)] = "",
) -> Response:
    """Set the password a valid link names under the rules; the person's sessions end and they
    sign in with it."""
    settings = _settings(request)
    origins = _origins(settings)
    user = resets.link_user(session, token) if token else None
    if user is None:
        return _link_gone(session, settings)
    product = _product(session)
    if _foreign(request, settings):
        return pages.problem(
            product,
            "This form was sent from another site. Open the link you were given again.",
            issuer=settings.issuer,
            redirect_origins=origins,
            status=403,
        )

    def again(message: str) -> Response:
        return pages.password(
            product,
            token,
            issuer=settings.issuer,
            redirect_origins=origins,
            username=user.username,
            min_length=settings.password_min_length,
            message=message,
            status=422,
        )

    if password != repeat:
        return again("The two passwords differ. Type the same password twice.")
    try:
        used = resets.use_link(session, settings, token, password)
    except ApiError as refusal:
        return again(refusal.message)
    if not used:
        return _link_gone(session, settings)
    return pages.password_set(
        product,
        app_url=settings.browser_origins[0] if settings.browser_origins else None,
        issuer=settings.issuer,
        redirect_origins=origins,
    )
