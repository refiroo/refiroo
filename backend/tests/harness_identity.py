"""How the tests reach an engine that needs a token on every route (Product 0.12 I1, D263).

The ``schema`` seed, which every test database is cloned from, holds a token signing key and a
harness client, both made by the engine's own functions as ``create_client`` makes them. Each test
process obtains one real token from ``POST /oauth/token`` with that client's credentials and sends
it with every request: the key and the client are the same in every clone, so the token is valid in
all of them, and the Argon2id check runs once per process rather than once per test.

A database not cloned from the seed (a test that builds one from empty or from an older revision)
has no harness client: a request the shared token cannot make is sent again with a token of a client
made in that database, as ``create_client`` makes one, once per database.

``TestClient`` is FastAPI's, carrying the token; ``TestClient(app, authenticated=False)`` sends
none, for a test of a refusal. An explicit ``Authorization`` header on a request wins.
"""

import base64
import os
import threading
import time
from collections.abc import Callable, Generator
from typing import Any

import httpx
from fastapi.testclient import TestClient as _FastApiTestClient

# The key every test database's secrets are sealed with: 32 bytes, URL-safe base64. Test data only.
SECRETS_ENCRYPTION_KEY = base64.urlsafe_b64encode(b"rdm-engine-test-harness-key-0001").decode()
os.environ.setdefault("SECRETS_ENCRYPTION_KEY", SECRETS_ENCRYPTION_KEY)
# Long enough that a seed's signing key is never replaced while it is reused (D264).
SIGNING_KEY_DAYS = "36500"
os.environ.setdefault("TOKEN_SIGNING_KEY_DAYS", SIGNING_KEY_DAYS)

_lock = threading.Lock()
_token: tuple[str, float] | None = None
_credentials: dict[str, str] | None = None
# Tokens of clients made in databases without the harness client, by database URL.
_own_tokens: dict[str, str] = {}


def create_harness_client() -> dict[str, str]:
    """Make the harness client and the first signing key in the configured database (the
    ``schema`` seed's build); the credentials go into the seed's payload."""
    from app.config import get_settings
    from app.db import SessionLocal
    from app.engine.identity import keys
    from app.engine.identity.clients import create_client
    from app.engine.identity.settings import IdentitySettings
    from app.models.commands import ClientCreate

    settings = get_settings()
    assert settings.secrets_encryption_key is not None
    identity = IdentitySettings(
        encryption_key=settings.secrets_encryption_key,
        issuer=settings.public_url,
        access_token_seconds=settings.access_token_minutes * 60,
        signing_key_days=settings.token_signing_key_days,
    )
    with SessionLocal() as session:
        client, secret = create_client(session, ClientCreate(name="Test harness"))
        keys.signing_key(session, identity)
        return {"clientId": client.public_id, "clientSecret": secret}


def credentials() -> dict[str, str]:
    global _credentials
    if _credentials is None:
        import seeds

        _credentials = dict(seeds.ensure("schema")["harness"])
    return _credentials


def basic_header(client_id: str, secret: str) -> str:
    return "Basic " + base64.b64encode(f"{client_id}:{secret}".encode()).decode()


def request_token(
    post: Callable[..., httpx.Response],
    client_id: str,
    secret: str,
    scope: str = "management",
) -> httpx.Response:
    """``POST /oauth/token`` with the client credentials grant, through any client's ``post``."""
    return post(
        "/oauth/token",
        data={"grant_type": "client_credentials", "scope": scope},
        headers={"Authorization": basic_header(client_id, secret)},
    )


def token(post: Callable[..., httpx.Response]) -> str | None:
    """This process's harness token, obtained once through ``post`` and renewed near its expiry;
    none when the database answering has no harness client."""
    global _token
    with _lock:
        if _token is None or _token[1] - time.monotonic() < 120:
            harness = credentials()
            response = request_token(post, harness["clientId"], harness["clientSecret"])
            if response.status_code != 200:
                return None
            body = response.json()
            _token = (body["access_token"], time.monotonic() + body["expires_in"])
        return _token[0]


def own_token(post: Callable[..., httpx.Response]) -> str | None:
    """A token of a client made in the configured database, for one not cloned from the seed; none
    when that database cannot hold one (not migrated, or unreachable)."""
    from sqlalchemy.exc import SQLAlchemyError

    from app.config import get_settings
    from app.db import DatabaseStartupError, SessionLocal
    from app.engine.identity.clients import create_client
    from app.models.commands import ClientCreate

    url = get_settings().database_url or ""
    with _lock:
        if url not in _own_tokens:
            try:
                with SessionLocal() as session:
                    client, secret = create_client(session, ClientCreate(name="Test harness"))
                    client_id = client.public_id
            except SQLAlchemyError, DatabaseStartupError:
                return None
            response = request_token(post, client_id, secret)
            if response.status_code != 200:
                return None
            _own_tokens[url] = response.json()["access_token"]
        return _own_tokens[url]


def forget_own_token() -> None:
    from app.config import get_settings

    with _lock:
        _own_tokens.pop(get_settings().database_url or "", None)


class HarnessAuth(httpx.Auth):
    """Adds the harness token to a request without an ``Authorization`` header of its own, and
    sends it again with the database's own client's token when the shared one is refused."""

    def __init__(self, post: Callable[..., httpx.Response]):
        self._post = post

    def auth_flow(self, request: httpx.Request) -> Generator[httpx.Request, httpx.Response]:
        if "Authorization" in request.headers:
            yield request
            return
        shared = token(self._post)
        if shared is not None:
            request.headers["Authorization"] = f"Bearer {shared}"
            response = yield request
            if response.status_code != 401:
                return
        own = own_token(self._post)
        if own is None:
            if shared is None:
                yield request
            return
        request.headers["Authorization"] = f"Bearer {own}"
        response = yield request
        if response.status_code == 401:
            # The database was rebuilt under the same URL (a downgrade and upgrade): its client is
            # gone, so a new one is made.
            forget_own_token()
            own = own_token(self._post)
            if own is not None:
                request.headers["Authorization"] = f"Bearer {own}"
                yield request


class TestClient(_FastApiTestClient):
    __test__ = False

    def __init__(self, *args: Any, authenticated: bool = True, **kwargs: Any):
        super().__init__(*args, **kwargs)
        if authenticated:
            self.auth = HarnessAuth(self.post)
