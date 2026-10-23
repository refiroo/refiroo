"""The engine as its own OAuth 2.0 authorization server (Product 0.12 I1, ADR-043, C-D1).

Outside ``/api/v1`` and needing no token (D245): the server's metadata (RFC 8414), the public keys
that verify its tokens, and the token endpoint. I1 serves the client credentials grant; the
browser's authorization code and refresh token grants come with I2. Errors here are in RFC 6749's
shape, ``{"error", "error_description"}``, which OAuth client libraries parse (D250).
"""

import base64
import binascii
from typing import Annotated
from urllib.parse import unquote

from fastapi import APIRouter, Depends, Form, Header, Request
from fastapi.responses import JSONResponse

from ...engine.identity import keys, tokens
from ...engine.identity.authentication import require_started
from ...engine.identity.clients import authenticate_client
from ...engine.identity.settings import IdentitySettings
from ..dependencies import DbSession

router = APIRouter(tags=["oauth"])

GRANT_TYPES = ["client_credentials"]
AUTH_METHODS = ["client_secret_basic", "client_secret_post"]
# Token responses are never cached (RFC 6749 §5.1).
_NO_STORE = {"Cache-Control": "no-store", "Pragma": "no-cache"}


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
        "token_endpoint": f"{issuer}/oauth/token",
        "jwks_uri": f"{issuer}/oauth/jwks",
        "grant_types_supported": GRANT_TYPES,
        "token_endpoint_auth_methods_supported": AUTH_METHODS,
        "scopes_supported": list(tokens.AUDIENCES),
        "response_types_supported": [],
        "code_challenge_methods_supported": ["S256"],
    }


# Checked before the request's session is opened: in maintenance mode the database may be unusable.
_STARTED = [Depends(require_started)]


@router.get("/oauth/jwks", dependencies=_STARTED)
def json_web_keys(session: DbSession) -> dict[str, object]:
    """The public keys that verify access tokens now, by ``kid`` (RFC 7517); every process serves
    the same set."""
    return {"keys": keys.published(session)}


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


@router.post("/oauth/token", dependencies=_STARTED)
def token(
    request: Request,
    session: DbSession,
    grant_type: Annotated[str | None, Form()] = None,
    scope: Annotated[str | None, Form()] = None,
    client_id: Annotated[str | None, Form()] = None,
    client_secret: Annotated[str | None, Form()] = None,
    authorization: Annotated[str | None, Header(alias="Authorization")] = None,
) -> JSONResponse:
    """An access token for a client's credentials (``grant_type=client_credentials``), sent as
    ``client_secret_basic`` or ``client_secret_post``. ``scope`` is ``management`` (the default) or
    ``consumer``, the API the token is for (D260). The answer is RFC 6749's: ``access_token``,
    ``token_type: "Bearer"``, ``expires_in`` and ``scope``."""
    if not grant_type:
        return _error(400, "invalid_request", "grant_type is required")
    if grant_type not in GRANT_TYPES:
        return _error(
            400, "unsupported_grant_type", f"This server issues tokens for {', '.join(GRANT_TYPES)}"
        )
    basic = _basic(authorization) if authorization else None
    if basic is not None and (client_id is not None or client_secret is not None):
        return _error(400, "invalid_request", "Send the client's credentials one way, not both")
    credentials = basic or (client_id, client_secret)
    challenge = {"WWW-Authenticate": 'Basic realm="oauth"'} if basic is not None else None
    if not credentials[0] or not credentials[1]:
        return _error(401, "invalid_client", "The client's credentials are missing", challenge)
    audience = scope.strip() if scope and scope.strip() else "management"
    if audience not in tokens.AUDIENCES:
        return _error(
            400, "invalid_scope", f"scope is one of {', '.join(tokens.AUDIENCES)}, not {scope!r}"
        )
    client = authenticate_client(session, credentials[0], credentials[1])
    if client is None:
        return _error(
            401,
            "invalid_client",
            "The client is unknown, inactive or its secret is wrong",
            challenge,
        )
    settings = _settings(request)
    access_token = tokens.issue(
        session, settings, subject=client.public_id, kind="client", audience=audience
    )
    return JSONResponse(
        {
            "access_token": access_token,
            "token_type": "Bearer",
            "expires_in": settings.access_token_seconds,
            "scope": audience,
        },
        headers=_NO_STORE,
    )
