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

A consumer API is read only with a grant of it in the workspace read (0.12 Z3, D306). The harness
client, refused one, is granted that API there by the engine's own grant function, as a Security
administrator would, and the request is sent again (D312): once per database, API and workspace.
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
# The person the browser runners sign in as, through the real sign-in page (0.12 I2, D274). Test
# data only.
# The harness client and person hold every predefined role at the instance (Z1), granted by the
# engine's own function as a Security administrator would.
EVERY_ROLE = (
    "reader",
    "contributor",
    "steward",
    "owner",
    "model-admin",
    "workspace-admin",
    "integration-admin",
    "operator",
    "security-admin",
)
HARNESS_PERSON = {"username": "harness", "password": "harness person passphrase 0001"}
# Long enough that a seed's signing key is never replaced while it is reused (D264).
SIGNING_KEY_DAYS = "36500"
os.environ.setdefault("TOKEN_SIGNING_KEY_DAYS", SIGNING_KEY_DAYS)

_lock = threading.Lock()
# The harness token for each audience, with when it expires.
_tokens: dict[str, tuple[str, float]] = {}
_credentials: dict[str, object] | None = None
# Tokens of clients made in databases without the harness client, by database URL and audience.
_own_tokens: dict[tuple[str, str], str] = {}
_own_clients: dict[str, tuple[str, str]] = {}


def create_harness_client() -> dict[str, object]:
    """Make the harness client, the harness person and the first signing key in the configured
    database (the ``schema`` seed's build); the credentials go into the seed's payload."""
    from app.config import get_settings
    from app.db import SessionLocal
    from app.engine.identity import keys
    from app.engine.identity.clients import create_client
    from app.engine.identity.settings import IdentitySettings
    from app.engine.identity.users import create_user
    from app.models.commands import ClientCreate, UserCreate

    settings = get_settings()
    assert settings.secrets_encryption_key is not None
    identity = IdentitySettings(
        encryption_key=settings.secrets_encryption_key,
        issuer=settings.public_url,
        access_token_seconds=settings.access_token_minutes * 60,
        signing_key_days=settings.token_signing_key_days,
    )
    with SessionLocal() as session:
        client, secret = create_client(session, ClientCreate(name="Test harness"), roles=EVERY_ROLE)
        keys.signing_key(session, identity)
        create_user(
            session,
            UserCreate(username=HARNESS_PERSON["username"], name="Test harness person"),
            password=HARNESS_PERSON["password"],
            roles=EVERY_ROLE,
        )
        return {"clientId": client.public_id, "clientSecret": secret, "person": HARNESS_PERSON}


def credentials() -> dict[str, object]:
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


def audience(path: str) -> str:
    """The audience a request's path needs: the consumer routes take a ``consumer`` token; the
    index and the OpenAPI documents are read with the ``management`` one, as the browser reads
    them, which lists every API (D266, D308); the documents need none (D412)."""
    describing = path.rstrip("/") == "/api/consumer" or path.endswith("/openapi.json")
    return "consumer" if path.startswith("/api/consumer") and not describing else "management"


def token(post: Callable[..., httpx.Response], scope: str = "management") -> str | None:
    """This process's harness token for ``scope``, obtained once through ``post`` and renewed near
    its expiry; none when the database answering has no harness client."""
    with _lock:
        held = _tokens.get(scope)
        if held is None or held[1] - time.monotonic() < 120:
            harness = credentials()
            response = request_token(
                post, str(harness["clientId"]), str(harness["clientSecret"]), scope
            )
            if response.status_code != 200:
                return None
            body = response.json()
            held = _tokens[scope] = (body["access_token"], time.monotonic() + body["expires_in"])
        return held[0]


def own_token(post: Callable[..., httpx.Response], scope: str = "management") -> str | None:
    """A token of a client made in the configured database, for one not cloned from the seed; none
    when that database cannot hold one (not migrated, or unreachable)."""
    from sqlalchemy.exc import SQLAlchemyError

    from app.config import get_settings
    from app.db import DatabaseStartupError, SessionLocal
    from app.engine.identity.clients import create_client
    from app.models.commands import ClientCreate

    url = get_settings().database_url or ""
    with _lock:
        if (url, scope) not in _own_tokens:
            if url not in _own_clients:
                try:
                    with SessionLocal() as session:
                        client, secret = create_client(
                            session, ClientCreate(name="Test harness"), roles=EVERY_ROLE
                        )
                        _own_clients[url] = (client.public_id, secret)
                except SQLAlchemyError, DatabaseStartupError:
                    return None
            response = request_token(post, *_own_clients[url], scope)
            if response.status_code != 200:
                return None
            _own_tokens[(url, scope)] = response.json()["access_token"]
        return _own_tokens[(url, scope)]


def _consumer_refusal(response: httpx.Response) -> tuple[str, str] | None:
    """The consumer API and workspace a consumer route refused for want of a grant (D309)."""
    if response.status_code != 403 or not response.request.url.path.startswith("/api/consumer"):
        return None
    response.read()
    details = response.json().get("error", {}).get("details") or {}
    if set(details) != {"consumerApi", "workspaceKey"}:
        return None
    return details["consumerApi"], details["workspaceKey"]


def grant_consumer_api(client_id: str, consumer_api: str, workspace_key: str) -> bool:
    """Grant ``consumer_api`` in ``workspace_key`` to the harness client ``client_id`` in the
    configured database, as ``POST /grants`` does; False when that cannot be done there."""
    from app.db import SessionLocal
    from app.engine.authorization.administration import create_grant
    from app.errors import ApiError
    from app.models.commands import GrantCreate

    payload = GrantCreate.model_validate(
        {
            "principal": {"kind": "client", "id": client_id},
            "consumerApi": consumer_api,
            "scope": {"workspaceKey": workspace_key},
        }
    )
    try:
        with SessionLocal() as session:
            create_grant(session, payload)
    except ApiError:
        return False
    return True


class HarnessAuth(httpx.Auth):
    """Adds the harness token to a request without an ``Authorization`` header of its own, and
    sends it again with the database's own client's token when the shared one is refused, or once
    its client is granted the consumer API it was refused (D312)."""

    def __init__(self, post: Callable[..., httpx.Response]):
        self._post = post

    def auth_flow(self, request: httpx.Request) -> Generator[httpx.Request, httpx.Response]:
        if "Authorization" in request.headers:
            yield request
            return
        scope = audience(request.url.path)
        shared = token(self._post, scope)
        if shared is not None:
            request.headers["Authorization"] = f"Bearer {shared}"
            response = yield request
            refusal = _consumer_refusal(response)
            if refusal is not None and grant_consumer_api(str(credentials()["clientId"]), *refusal):
                yield request
                return
            if response.status_code != 401:
                return
        own = own_token(self._post, scope)
        if own is None:
            if shared is None:
                yield request
            return
        request.headers["Authorization"] = f"Bearer {own}"
        response = yield request
        refusal = _consumer_refusal(response)
        if refusal is not None:
            from app.config import get_settings

            own_client = _own_clients.get(get_settings().database_url or "")
            if own_client is not None and grant_consumer_api(own_client[0], *refusal):
                yield request


class TestClient(_FastApiTestClient):
    __test__ = False

    def __init__(self, *args: Any, authenticated: bool = True, **kwargs: Any):
        super().__init__(*args, **kwargs)
        if authenticated:
            self.auth = HarnessAuth(self.post)
