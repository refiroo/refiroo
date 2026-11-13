"""A minimal OpenID Connect provider for the harness (Product 0.12 I3, D369).

It serves its discovery document, its keys (one RS256 key made at start), an authorize page where
the test or the person at the browser chooses who signs in (subject, name, e-mail, username and
groups), and a token endpoint that checks the client's secret and the PKCE verifier and answers an
ID token. ``misbehave`` makes the next tokens wrong in one way (another issuer, a wrong nonce,
another audience), the authorize step answer ``access_denied``, or the redirect carry another
provider's ``iss`` (``redirect-issuer``).

The journeys run it in a thread (``OidcProvider``); the browser runner runs it as a script:

    python tests/oidc_provider.py --port 8790 --client-id engine --client-secret <secret>
"""

import argparse
import base64
import hashlib
import json
import secrets
import threading
import time
from dataclasses import dataclass, field
from html import escape
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Self
from urllib.parse import parse_qs, urlencode, urlsplit

import httpx2
import jwt
from cryptography.hazmat.primitives.asymmetric import rsa

PERSON_FIELDS = ("sub", "name", "email", "email_verified", "preferred_username", "groups")


@dataclass
class _Code:
    client_id: str
    redirect_uri: str
    challenge: str
    nonce: str | None
    claims: dict[str, Any]


@dataclass
class OidcProvider:
    """The provider, served on a loopback port once started."""

    client_id: str = "engine"
    client_secret: str = field(default_factory=lambda: secrets.token_urlsafe(24))
    port: int = 0
    misbehave: str | None = None
    # True: the redirect back carries ``iss`` (RFC 9207) and a ``session_state``, as Keycloak's
    # does; ``misbehave = "redirect-issuer"`` makes that ``iss`` another provider's.
    send_extra_parameters: bool = False
    # False: the discovery document names no sign-out address (I4a).
    end_session: bool = True
    # What the sign-out endpoint was asked, newest last (I4a).
    logouts: list[dict[str, str]] = field(default_factory=list)
    _codes: dict[str, _Code] = field(default_factory=dict)
    _server: ThreadingHTTPServer | None = None

    def __post_init__(self) -> None:
        self._key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        self.kid = secrets.token_urlsafe(8)

    @property
    def issuer(self) -> str:
        assert self._server is not None, "start the provider first"
        return f"http://127.0.0.1:{self._server.server_address[1]}"

    def start(self) -> Self:
        provider = self

        class Handler(_Handler):
            owner = provider

        self._server = ThreadingHTTPServer(("127.0.0.1", self.port), Handler)
        threading.Thread(target=self._server.serve_forever, daemon=True).start()
        return self

    def stop(self) -> None:
        if self._server is not None:
            self._server.shutdown()
            self._server.server_close()

    def __enter__(self) -> Self:
        return self.start()

    def __exit__(self, *_: object) -> None:
        self.stop()

    def sign_in(self, authorize_url: str, **person: str | list[str]) -> str:
        """Answer the authorize request at ``authorize_url`` as ``person`` (``sub``, ``name``,
        ``email``, ``email_verified`` as "true" or "false", ``preferred_username``, ``groups``); the address the provider sends the browser
        back to."""
        query = {k: v[0] for k, v in parse_qs(urlsplit(authorize_url).query).items()}
        groups = person.pop("groups", [])
        form = {
            **query,
            **person,
            "groups": ",".join(groups) if isinstance(groups, list) else groups,
        }
        response = httpx2.post(f"{self.issuer}/authorize", data=form, follow_redirects=False)
        assert response.status_code == 302, response.text
        return response.headers["location"]

    # -- what the handler answers --------------------------------------------------------------

    def sign_out(self, logout_url: str) -> str:
        """Answer the sign-out request at ``logout_url``: the address the provider sends the browser
        to afterwards (the request's ``post_logout_redirect_uri`` with its ``state``)."""
        response = httpx2.get(logout_url, follow_redirects=False)
        assert response.status_code == 302, response.text
        return response.headers["location"]

    def logout(self, query: dict[str, str]) -> str:
        """RP-Initiated Logout 1.0: remember the request, send the browser on."""
        self.logouts.append(query)
        target = query.get("post_logout_redirect_uri")
        if not target:
            return f"{self.issuer}/signed-out"
        if not query.get("state"):
            return target
        return f"{target}{'&' if '?' in target else '?'}{urlencode({'state': query['state']})}"

    def discovery(self) -> dict[str, Any]:
        return {
            "issuer": self.issuer,
            "authorization_endpoint": f"{self.issuer}/authorize",
            "token_endpoint": f"{self.issuer}/token",
            "jwks_uri": f"{self.issuer}/jwks",
            "response_types_supported": ["code"],
            "subject_types_supported": ["public"],
            "id_token_signing_alg_values_supported": ["RS256"],
            "token_endpoint_auth_methods_supported": ["client_secret_basic", "client_secret_post"],
            "code_challenge_methods_supported": ["S256"],
            "scopes_supported": ["openid", "profile", "email"],
            **({"end_session_endpoint": f"{self.issuer}/logout"} if self.end_session else {}),
        }

    def jwks(self) -> dict[str, Any]:
        jwk = json.loads(jwt.algorithms.RSAAlgorithm.to_jwk(self._key.public_key()))
        return {"keys": [{**jwk, "kid": self.kid, "use": "sig", "alg": "RS256"}]}

    def authorize(self, form: dict[str, str]) -> str:
        """Where the browser goes after the person is chosen: back with a code, or an error."""
        redirect = form["redirect_uri"]
        state = form.get("state", "")
        if self.misbehave == "error":
            return f"{redirect}?{urlencode({'error': 'access_denied', 'state': state})}"
        code = secrets.token_urlsafe(24)
        claims: dict[str, Any] = {k: form[k] for k in PERSON_FIELDS[:-1] if form.get(k)}
        if "email_verified" in claims:  # a form field is text; the claim is a boolean
            claims["email_verified"] = claims["email_verified"] == "true"
        groups = [g.strip() for g in form.get("groups", "").split(",") if g.strip()]
        claims["groups"] = groups
        self._codes[code] = _Code(
            form["client_id"], redirect, form.get("code_challenge", ""), form.get("nonce"), claims
        )
        answer = {"code": code, "state": state}
        if self.send_extra_parameters or self.misbehave == "redirect-issuer":
            answer["session_state"] = secrets.token_urlsafe(12)
            answer["iss"] = (
                f"{self.issuer}/other" if self.misbehave == "redirect-issuer" else self.issuer
            )
        return f"{redirect}?{urlencode(answer)}"

    def token(self, form: dict[str, str], authorization: str | None) -> tuple[int, dict[str, Any]]:
        client_id, secret = form.get("client_id"), form.get("client_secret")
        if authorization and authorization.lower().startswith("basic "):
            decoded = base64.b64decode(authorization[6:]).decode()
            client_id, _, secret = decoded.partition(":")
        if (client_id, secret) != (self.client_id, self.client_secret):
            return 401, {"error": "invalid_client"}
        stored = self._codes.pop(form.get("code", ""), None)
        if stored is None or stored.redirect_uri != form.get("redirect_uri"):
            return 400, {"error": "invalid_grant"}
        verifier = form.get("code_verifier", "")
        digest = hashlib.sha256(verifier.encode()).digest()
        if base64.urlsafe_b64encode(digest).rstrip(b"=").decode() != stored.challenge:
            return 400, {"error": "invalid_grant", "error_description": "PKCE"}
        now = int(time.time())
        claims = {
            **stored.claims,
            "iss": f"{self.issuer}/other" if self.misbehave == "issuer" else self.issuer,
            "aud": "someone-else" if self.misbehave == "audience" else self.client_id,
            "iat": now,
            "exp": now + 300,
            "nonce": "not-the-nonce" if self.misbehave == "nonce" else stored.nonce,
        }
        id_token = jwt.encode(claims, self._key, "RS256", {"kid": self.kid})
        return 200, {
            "access_token": secrets.token_urlsafe(16),
            "token_type": "Bearer",
            "expires_in": 300,
            "id_token": id_token,
        }


class _Handler(BaseHTTPRequestHandler):
    owner: OidcProvider

    def log_message(self, *_: object) -> None:
        pass

    def _json(self, status: int, body: dict[str, Any]) -> None:
        data = json.dumps(body).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _form(self) -> dict[str, str]:
        length = int(self.headers.get("Content-Length") or 0)
        body = self.rfile.read(length).decode()
        return {k: v[0] for k, v in parse_qs(body, keep_blank_values=True).items()}

    def do_GET(self) -> None:
        parts = urlsplit(self.path)
        if parts.path == "/.well-known/openid-configuration":
            return self._json(200, self.owner.discovery())
        if parts.path == "/jwks":
            return self._json(200, self.owner.jwks())
        if parts.path == "/logout":
            query = {k: v[0] for k, v in parse_qs(parts.query).items()}
            self.send_response(302)
            self.send_header("Location", self.owner.logout(query))
            self.send_header("Content-Length", "0")
            self.end_headers()
            return None
        if parts.path == "/authorize":
            return self._page({k: v[0] for k, v in parse_qs(parts.query).items()})
        self._json(404, {"error": "not_found"})

    def do_POST(self) -> None:
        path = urlsplit(self.path).path
        form = self._form()
        if path == "/authorize":
            self.send_response(302)
            self.send_header("Location", self.owner.authorize(form))
            self.send_header("Content-Length", "0")
            self.end_headers()
            return None
        if path == "/token":
            status, body = self.owner.token(form, self.headers.get("Authorization"))
            return self._json(status, body)
        self._json(404, {"error": "not_found"})

    def _page(self, request: dict[str, str]) -> None:
        """Choose who signs in; the request's fields travel hidden."""
        hidden = "".join(
            f'<input type="hidden" name="{escape(k)}" value="{escape(v)}">'
            for k, v in request.items()
        )
        fields = "".join(
            f'<p><label for="{name}">{label}</label><br><input id="{name}" name="{name}" '
            f'value="{escape(default)}"></p>'
            for name, label, default in (
                ("sub", "Subject", "p-1001"),
                ("name", "Name", "Pat Provider"),
                ("email", "E-mail", "pat@provider.example"),
                ("preferred_username", "Username", "pat@provider.example"),
                ("groups", "Groups (comma separated)", "staff"),
            )
        )
        html = (
            '<!doctype html><html lang="en"><head><meta charset="utf-8"><title>Harness provider'
            '</title></head><body><main><h1>Harness provider</h1><form method="post" '
            f'action="/authorize">{hidden}{fields}<button type="submit">Sign in</button></form>'
            "</main></body></html>"
        ).encode()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(html)))
        self.end_headers()
        self.wfile.write(html)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--port", type=int, default=8790)
    parser.add_argument("--client-id", default="engine")
    parser.add_argument("--client-secret", required=True)
    args = parser.parse_args()
    provider = OidcProvider(args.client_id, args.client_secret, args.port).start()
    print(f"Harness provider at {provider.issuer}", flush=True)
    try:
        threading.Event().wait()
    except KeyboardInterrupt:
        provider.stop()


if __name__ == "__main__":
    main()
