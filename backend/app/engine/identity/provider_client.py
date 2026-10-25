"""Talking to a sign-in provider (Product 0.12 I3, D361, D362).

The provider's discovery document (``<issuer>/.well-known/openid-configuration``) names its
endpoints and keys; its issuer must be the configured one exactly. Requests go through the webhook
client's checked connection (a link-local address is refused) with 10 seconds each, ``https`` unless
the issuer names a loopback host. The discovery document and the keys are kept per process for an
hour, and the keys fetched again once when a token names a ``kid`` they lack, so a provider's key
rotation is followed at once. An ID token is checked as OpenID Connect Core §3.1.3.7 asks: its
signature (RS256, PS256 or ES256 only), ``iss``, ``aud``, ``azp``, ``exp``, ``iat`` and ``nonce``.
"""

import base64
import json
import time
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlencode, urlsplit

import jwt

from ..events import webhook_client
from ..events.webhook_urls import LOOPBACK

TIMEOUT_SECONDS = 10.0
CACHE_SECONDS = 3600
READ_BYTES = 256 * 1024
ALGORITHMS = ("RS256", "PS256", "ES256")
SCOPES = "openid profile email"


class ProviderError(Exception):
    """Why the provider could not be used, in words an administrator can act on; ``kind`` is the
    reason's key in the security event."""

    def __init__(self, kind: str, message: str):
        super().__init__(message)
        self.kind = kind


@dataclass(frozen=True)
class Discovery:
    issuer: str
    authorization_endpoint: str
    token_endpoint: str
    jwks_uri: str
    auth_methods: tuple[str, ...]
    # RP-Initiated Logout 1.0: where the browser goes to sign out of the provider (I4a, D380).
    end_session_endpoint: str | None = None


_discoveries: dict[str, tuple[float, Discovery]] = {}
_keys: dict[str, tuple[float, dict[str, Any]]] = {}


def _checked_url(url: str, what: str) -> None:
    parts = urlsplit(url)
    host = (parts.hostname or "").lower()
    if parts.scheme == "https" or (parts.scheme == "http" and host in LOOPBACK):
        return
    raise ProviderError(
        "address", f"The {what} {url!r} must use https (plain http only on this machine)"
    )


def _get(url: str, what: str) -> Any:
    _checked_url(url, what)
    answer = webhook_client.exchange(
        "GET",
        url,
        None,
        {"Accept": "application/json"},
        timeout=TIMEOUT_SECONDS,
        read_bytes=READ_BYTES,
    )
    if not answer.ok:
        raise ProviderError(
            "unreachable", f"The {what} could not be read: {answer.error['message']}"
        )
    try:
        return json.loads(answer.body or "")
    except ValueError:
        raise ProviderError("unreachable", f"The {what} at {url} is not JSON") from None


def discover(issuer: str, *, fresh: bool = False) -> Discovery:
    """The provider's endpoints, from its discovery document; checked against ``issuer``."""
    now = time.monotonic()
    cached = _discoveries.get(issuer)
    if cached and not fresh and now - cached[0] < CACHE_SECONDS:
        return cached[1]
    document = _get(f"{issuer.rstrip('/')}/.well-known/openid-configuration", "discovery document")
    if not isinstance(document, dict):
        raise ProviderError("unreachable", "The discovery document is not a JSON object")
    if document.get("issuer") != issuer:
        raise ProviderError(
            "issuer",
            f"The discovery document names the issuer {document.get('issuer')!r}, not {issuer!r}; "
            "copy the issuer exactly as the provider states it",
        )
    missing = [
        name
        for name in ("authorization_endpoint", "token_endpoint", "jwks_uri")
        if not isinstance(document.get(name), str)
    ]
    if missing:
        raise ProviderError("unreachable", f"The discovery document has no {', '.join(missing)}")
    if "code" not in document.get("response_types_supported", ["code"]):
        raise ProviderError(
            "unreachable", "The provider does not offer the authorization code flow"
        )
    for name in ("authorization_endpoint", "token_endpoint", "jwks_uri"):
        _checked_url(document[name], name.replace("_", " "))
    end_session = document.get("end_session_endpoint")
    if isinstance(end_session, str):
        _checked_url(end_session, "end session endpoint")
    found = Discovery(
        issuer=issuer,
        authorization_endpoint=document["authorization_endpoint"],
        token_endpoint=document["token_endpoint"],
        jwks_uri=document["jwks_uri"],
        auth_methods=tuple(document.get("token_endpoint_auth_methods_supported") or ()),
        end_session_endpoint=end_session if isinstance(end_session, str) else None,
    )
    _discoveries[issuer] = (now, found)
    return found


def keys(discovery: Discovery, *, fresh: bool = False) -> dict[str, Any]:
    """The provider's published keys (a JWKS)."""
    now = time.monotonic()
    cached = _keys.get(discovery.jwks_uri)
    if cached and not fresh and now - cached[0] < CACHE_SECONDS:
        return cached[1]
    document = _get(discovery.jwks_uri, "provider's keys")
    if not isinstance(document, dict) or not document.get("keys"):
        raise ProviderError("unreachable", "The provider publishes no keys")
    _keys[discovery.jwks_uri] = (now, document)
    return document


def check(issuer: str) -> None:
    """Whether a provider at ``issuer`` can be used: its discovery document and keys, read now."""
    keys(discover(issuer, fresh=True), fresh=True)


def check_sign_out(issuer: str) -> None:
    """Whether the provider at ``issuer`` offers a sign-out address, read now."""
    if discover(issuer, fresh=True).end_session_endpoint is None:
        raise ProviderError(
            "sign-out", "Its discovery document names no end_session_endpoint to sign people out at"
        )


def sign_out_url(
    discovery: Discovery, *, id_token_hint: str, post_logout_redirect_uri: str, state: str
) -> str | None:
    """Where the browser goes to sign out of the provider, or none when it offers no such address
    (RP-Initiated Logout 1.0 §2)."""
    if discovery.end_session_endpoint is None:
        return None
    query = urlencode(
        {
            "id_token_hint": id_token_hint,
            "post_logout_redirect_uri": post_logout_redirect_uri,
            "state": state,
        }
    )
    separator = "&" if "?" in discovery.end_session_endpoint else "?"
    return f"{discovery.end_session_endpoint}{separator}{query}"


def authorization_url(
    discovery: Discovery,
    *,
    client_id: str,
    redirect_uri: str,
    state: str,
    nonce: str,
    challenge: str,
) -> str:
    query = urlencode(
        {
            "response_type": "code",
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "scope": SCOPES,
            "state": state,
            "nonce": nonce,
            "code_challenge": challenge,
            "code_challenge_method": "S256",
        }
    )
    separator = "&" if "?" in discovery.authorization_endpoint else "?"
    return f"{discovery.authorization_endpoint}{separator}{query}"


def exchange_code(
    discovery: Discovery,
    *,
    client_id: str,
    client_secret: str,
    code: str,
    redirect_uri: str,
    verifier: str,
) -> str:
    """The ID token the provider answers for ``code``. The client authenticates with
    ``client_secret_basic`` unless the provider offers only ``client_secret_post``."""
    form = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": redirect_uri,
        "code_verifier": verifier,
    }
    headers = {"Content-Type": "application/x-www-form-urlencoded", "Accept": "application/json"}
    methods = discovery.auth_methods
    if methods and "client_secret_basic" not in methods and "client_secret_post" in methods:
        form |= {"client_id": client_id, "client_secret": client_secret}
    else:
        pair = f"{_quote(client_id)}:{_quote(client_secret)}".encode()
        headers["Authorization"] = "Basic " + base64.b64encode(pair).decode()
    answer = webhook_client.exchange(
        "POST",
        discovery.token_endpoint,
        urlencode(form).encode(),
        headers,
        timeout=TIMEOUT_SECONDS,
        read_bytes=READ_BYTES,
    )
    if not answer.ok:
        raise ProviderError("exchange", f"The provider refused the code: {answer.error['message']}")
    try:
        token = json.loads(answer.body or "").get("id_token")
    except ValueError, AttributeError:
        token = None
    if not isinstance(token, str):
        raise ProviderError("exchange", "The provider's answer holds no ID token")
    return token


def _quote(value: str) -> str:
    """RFC 6749 §2.3.1: the client ID and secret form-encoded before Basic."""
    return urlencode({"": value})[1:]


def verify_id_token(
    discovery: Discovery, token: str, *, client_id: str, nonce: str
) -> dict[str, Any]:
    """The ID token's claims once its signature and claims hold; ``ProviderError`` naming the claim
    that does not."""
    try:
        header = jwt.get_unverified_header(token)
    except jwt.PyJWTError:
        raise ProviderError("token", "The ID token cannot be read") from None
    algorithm = header.get("alg")
    if algorithm not in ALGORITHMS:
        raise ProviderError(
            "token", f"The ID token is signed with {algorithm!r}, which is not accepted"
        )
    key = _signing_key(discovery, header.get("kid"), algorithm)
    try:
        claims = jwt.decode(
            token,
            key,
            algorithms=[algorithm],
            audience=client_id,
            issuer=discovery.issuer,
            leeway=60,
            options={"require": ["iss", "sub", "aud", "exp", "iat"]},
        )
    except jwt.InvalidIssuerError:
        raise ProviderError("issuer", "The ID token names another issuer") from None
    except jwt.InvalidAudienceError:
        raise ProviderError("audience", "The ID token is for another client") from None
    except jwt.PyJWTError as error:
        raise ProviderError("token", f"The ID token is not valid: {error}") from None
    audiences = claims["aud"] if isinstance(claims["aud"], list) else [claims["aud"]]
    if (len(audiences) > 1 or "azp" in claims) and claims.get("azp") != client_id:
        raise ProviderError("audience", "The ID token was issued to another client (azp)")
    if claims.get("nonce") != nonce:
        raise ProviderError("nonce", "The ID token's nonce is not this sign-in's")
    return claims


def _signing_key(discovery: Discovery, kid: str | None, algorithm: str) -> Any:
    for fresh in (False, True):
        for jwk in keys(discovery, fresh=fresh)["keys"]:
            if kid is None or jwk.get("kid") == kid:
                try:
                    return jwt.PyJWK(jwk, algorithm).key
                except jwt.PyJWTError:
                    continue
    raise ProviderError("token", f"The provider publishes no key {kid!r}")
