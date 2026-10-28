"""J39, J40, J41, J43 — the engine as its own token issuer (USER_JOURNEYS.md § Security, 0.12 I1).

Every route needs an access token except the open ones (D245). A client obtains a token with its
credentials at ``POST /oauth/token`` and calls the API with it; its secret rotates with an overlap; a
deactivated client is refused at once; a token for one API is refused by the other; the signing key
rotates on request, with the old key's tokens still accepted until they expire or, after "rotate
now", refused. People are created, changed and deactivated, never deleted; the first administrator
comes from ``create_admin``. Every case runs on two configurations through the public API.
"""

import json
import os
import subprocess
import sys
import time

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import ec
from harness_identity import TestClient, basic_header, request_token
from scenario import ok, refused
from service import BACKEND, render

OPEN_ROUTES = (
    "/health",
    "/health/live",
    "/openapi.json",
    "/docs",
    "/.well-known/oauth-authorization-server",
    "/oauth/jwks",
)


def _anonymous(world) -> TestClient:
    """A client of the same running engine that sends no token."""
    return TestClient(world.api.client.app, authenticated=False)


def _client(world, name: str = "Nightly import") -> dict:
    return ok(world.api.post("/clients", {"name": name}), 201)


def _token(world, client: dict, secret: str | None = None, scope: str = "management") -> str:
    response = request_token(
        _anonymous(world).post, client["id"], secret or client["secret"], scope
    )
    return ok(response)["access_token"]


def _bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _workspaces(world, headers: dict[str, str]):
    return world.api.client.get("/api/v1/workspaces", headers=headers)


def _oauth_error(response, status: int, error: str) -> None:
    assert response.status_code == status, f"{response.status_code}: {response.text}"
    assert response.json()["error"] == error and response.json()["error_description"]
    assert response.headers["cache-control"] == "no-store"


def _invalid(response, reason: str) -> None:
    error = refused(response, 401, "TOKEN_INVALID")
    assert error["details"] == {"reason": reason}
    assert response.headers["www-authenticate"] == 'Bearer error="invalid_token"'


@pytest.mark.journey("J39")
def test_every_route_but_the_open_ones_needs_a_token(world):
    """Given the engine. When a management read, a consumer route and `/metrics` are called with no
    token, then each answers `401 AUTHENTICATION_REQUIRED` with `WWW-Authenticate: Bearer`; the
    health routes, the API document, `/docs`, the server metadata and the JWKS answer without one."""
    anonymous = _anonymous(world)
    for path in ("/api/v1/workspaces", "/api/consumer", "/metrics"):
        response = anonymous.get(path)
        refused(response, 401, "AUTHENTICATION_REQUIRED")
        assert response.headers["www-authenticate"] == "Bearer"
    for path in OPEN_ROUTES:
        assert anonymous.get(path).status_code == 200, path
    metadata = ok(anonymous.get("/.well-known/oauth-authorization-server"))
    assert metadata["token_endpoint"] == f"{metadata['issuer']}/oauth/token"
    assert metadata["grant_types_supported"] == [
        "authorization_code",
        "refresh_token",
        "client_credentials",
    ]
    assert metadata["authorization_endpoint"] == f"{metadata['issuer']}/oauth/authorize"
    assert {key["kid"] for key in ok(anonymous.get("/oauth/jwks"))["keys"]}


@pytest.mark.journey("J39")
def test_a_token_not_issued_here_is_refused(world):
    """Given a token signed by a key the engine never had, and one of its own tokens altered. When
    each calls a management read, then `401 TOKEN_INVALID`: `unknownKey`, and `signature`."""
    client = _client(world)
    issued = _token(world, client)
    claims = jwt.decode(issued, options={"verify_signature": False})
    header = jwt.get_unverified_header(issued)
    foreign = jwt.encode(claims, ec.generate_private_key(ec.SECP256R1()), "ES256", {"kid": "other"})
    _invalid(_workspaces(world, _bearer(foreign)), "unknownKey")
    forged = jwt.encode(claims, ec.generate_private_key(ec.SECP256R1()), "ES256", header)
    _invalid(_workspaces(world, _bearer(forged)), "signature")
    _invalid(_workspaces(world, _bearer("not-a-token")), "malformed")


@pytest.mark.journey("J41")
def test_a_client_obtains_a_token_and_calls_the_api(world):
    """Given an administrator creates a client, its secret answered once and never on a read, and
    grants it Data steward in the workspace (Z1). When the client posts its credentials to
    `/oauth/token`, in the header and in the body, then it gets a Bearer token for an hour; `GET
    /me` names it, and it creates and reads a record. A wrong secret answers `invalid_client` and an
    unknown grant `unsupported_grant_type`, in the RFC's shape."""
    client = _client(world)
    grant = {
        "principal": {"kind": "client", "id": client["id"]},
        "role": "steward",
        "scope": {"workspaceKey": "default"},
    }
    ok(world.api.post("/grants", grant), 201)
    assert client["secret"] and client["secrets"][0]["id"] == client["secretId"]
    read = ok(world.api.get(f"/clients/{client['id']}"))
    assert "secret" not in read and client["secret"] not in json.dumps(read)
    anonymous = _anonymous(world)
    answer = ok(request_token(anonymous.post, client["id"], client["secret"]))
    assert (answer["token_type"], answer["expires_in"], answer["scope"]) == (
        "Bearer",
        3600,
        "management",
    )
    in_body = anonymous.post(
        "/oauth/token",
        data={
            "grant_type": "client_credentials",
            "client_id": client["id"],
            "client_secret": client["secret"],
        },
    )
    caller = _bearer(ok(in_body)["access_token"])
    me = ok(anonymous.get("/api/v1/me", headers=caller))
    assert (me["id"], me["kind"], me["name"], me["username"]) == (
        client["id"],
        "client",
        "Nightly import",
        None,
    )
    assert me["lastSignInAt"] is not None
    body = {
        "applicationKey": world.app("R"),
        "objectTypeKey": world.key("R"),
        "workspaceKey": "default",
        "name": "Made by a client",
        "attributes": [
            {"attributeTypeKey": key, "value": value}
            for key, value in world.required_values("R").items()
        ],
    }
    made = ok(anonymous.post("/api/v1/objects", json=body, headers=caller), 201)
    assert ok(world.read("R", made["id"]))["name"] == "Made by a client"
    wrong = request_token(anonymous.post, client["id"], "not-the-secret")
    _oauth_error(wrong, 401, "invalid_client")
    assert wrong.headers["www-authenticate"].startswith("Basic")
    unknown = anonymous.post(
        "/oauth/token",
        data={"grant_type": "password", "username": "x", "password": "y"},
        headers={"Authorization": basic_header(client["id"], client["secret"])},
    )
    _oauth_error(unknown, 400, "unsupported_grant_type")


@pytest.mark.journey("J41")
def test_wrong_client_secrets_are_slowed_and_unknown_ids_cost_the_same(world, monkeypatch):
    """Given a client. When its secret is guessed wrong past the free failures, the next attempt is
    `429` `invalid_client` with `Retry-After`, even with the right secret; an ID that is no client
    is counted and slowed the same way and spends one password check, as a wrong secret does."""
    from app.engine.identity import sign_in

    checks = []
    real = sign_in.verify_secret
    monkeypatch.setattr(sign_in, "verify_secret", lambda *args: checks.append(1) or real(*args))
    client = _client(world)
    anonymous = _anonymous(world)
    for _ in range(6):
        _oauth_error(request_token(anonymous.post, client["id"], "wrong"), 401, "invalid_client")
    slowed = request_token(anonymous.post, client["id"], client["secret"])
    _oauth_error(slowed, 429, "invalid_client")
    assert int(slowed.headers["retry-after"]) >= 1
    assert "slowed" not in slowed.text and "Too many wrong secrets" in slowed.text
    time.sleep(int(slowed.headers["retry-after"]) + 0.2)
    assert request_token(anonymous.post, client["id"], client["secret"]).status_code == 200

    spent = len(checks)
    _oauth_error(request_token(anonymous.post, "no-such-client", "wrong"), 401, "invalid_client")
    assert len(checks) == spent + 1


@pytest.mark.journey("J41.3")
def test_the_secret_rotated_with_an_overlap(world):
    """Given a client. When a second secret is created with an overlap, then both obtain tokens;
    when the old one is deleted, only the new one does. A rotation with overlap 0 stops the previous
    secret at once."""
    client = _client(world)
    rotated = ok(
        world.api.post(
            f"/clients/{client['id']}/secrets",
            {"expectedVersion": client["version"], "overlapHours": 2},
        ),
        201,
    )
    assert rotated["secret"] != client["secret"] and len(rotated["secrets"]) == 2
    assert rotated["secrets"][0]["expiresAt"] is not None
    assert _token(world, client) and _token(world, client, rotated["secret"])
    after = ok(world.api.delete(f"/clients/{client['id']}/secrets/{client['secretId']}"))
    assert [secret["id"] for secret in after["secrets"]] == [rotated["secretId"]]
    _oauth_error(
        request_token(_anonymous(world).post, client["id"], client["secret"]), 401, "invalid_client"
    )
    at_once = ok(
        world.api.post(
            f"/clients/{client['id']}/secrets",
            {"expectedVersion": after["version"], "overlapHours": 0},
        ),
        201,
    )
    assert [secret["id"] for secret in at_once["secrets"]] == [at_once["secretId"]]
    _oauth_error(
        request_token(_anonymous(world).post, client["id"], rotated["secret"]),
        401,
        "invalid_client",
    )
    assert _token(world, client, at_once["secret"])


@pytest.mark.journey("J41.4")
def test_a_deactivated_client_is_refused_at_once(world):
    """Given a client holding a token. When it is deactivated, then that token's next request answers
    `401 TOKEN_INVALID` (`revoked`) and the token endpoint `invalid_client`."""
    client = _client(world)
    caller = _bearer(_token(world, client))
    assert _workspaces(world, caller).status_code == 200
    changed = ok(
        world.api.patch(
            f"/clients/{client['id']}", {"expectedVersion": client["version"], "active": False}
        )
    )
    assert changed["active"] is False
    _invalid(_workspaces(world, caller), "revoked")
    _oauth_error(
        request_token(_anonymous(world).post, client["id"], client["secret"]), 401, "invalid_client"
    )


@pytest.mark.journey("J41.5")
def test_a_token_for_the_other_api_is_refused(world):
    """Given a `consumer` token and a `management` token. When the consumer token calls the
    management API, or the management token a consumer API's data, then `401 TOKEN_INVALID`
    (`audience`); each is accepted by its own. The routes describing the consumer APIs (the index
    and each OpenAPI document) take either, as the browser holds a management token (D266); the
    client holds Reader and the consumer API's grant (Z3, D308)."""
    client = _client(world)
    consumer = _bearer(_token(world, client, scope="consumer"))
    management = _bearer(_token(world, client))
    anonymous = _anonymous(world)
    principal = {"kind": "client", "id": client["id"]}
    scope = {"workspaceKey": "default"}
    ok(world.api.post("/grants", {"principal": principal, "role": "reader", "scope": scope}), 201)
    index = ok(anonymous.get("/api/consumer", headers=management))
    entry = index["items"][0]
    granted = {"principal": principal, "consumerApi": entry["consumerApi"], "scope": scope}
    ok(world.api.post("/grants", granted), 201)
    _invalid(anonymous.get("/api/v1/workspaces", headers=consumer), "audience")
    assert ok(anonymous.get("/api/consumer", headers=consumer))["items"] == [entry]
    base = f"/api/consumer/{entry['consumerApi']}/v{entry['contractVersion']}"
    for token in (consumer, management, {}):
        assert anonymous.get(f"{base}/openapi.json", headers=token).status_code == 200
    # The document is the contract, not data (D412): open, but only for a workspace that exists, and
    # the index that lists what a caller may read still needs a token.
    refused(anonymous.get(f"{base}/openapi.json?workspace=nowhere"), 404, "WORKSPACE_NOT_FOUND")
    assert anonymous.get("/api/consumer").status_code == 401
    _invalid(anonymous.get(f"{base}/publications", headers=management), "audience")
    assert anonymous.get(f"{base}/publications", headers=consumer).status_code == 200
    assert anonymous.get("/api/v1/workspaces", headers=management).status_code == 200
    _oauth_error(
        request_token(anonymous.post, client["id"], client["secret"], "everything"),
        400,
        "invalid_scope",
    )


@pytest.mark.journey("J43.1", "J43.2")
def test_the_token_signing_key_rotated(world):
    """Given a client's token. When the key is rotated with `immediate: false`, then the old token
    still works, new tokens carry the new `kid` and the JWKS lists both. When it is rotated with
    `immediate: true`, the tokens of the key it replaces answer `401 TOKEN_INVALID` (`unknownKey`),
    the JWKS drops that key, and the client obtains a new token with its unchanged secret."""
    client = _client(world)
    first = _token(world, client)
    first_kid = jwt.get_unverified_header(first)["kid"]
    scheduled = ok(world.api.post("/token-signing-keys/rotation", {"immediate": False}), 201)
    assert scheduled["state"] == "current" and scheduled["kid"] != first_kid
    assert _workspaces(world, _bearer(first)).status_code == 200
    second = _token(world, client)
    assert jwt.get_unverified_header(second)["kid"] == scheduled["kid"]
    published = {key["kid"] for key in ok(_anonymous(world).get("/oauth/jwks"))["keys"]}
    assert {first_kid, scheduled["kid"]} <= published
    states = {key["kid"]: key["state"] for key in ok(world.api.get("/token-signing-keys"))["items"]}
    assert (states[first_kid], states[scheduled["kid"]]) == ("verifying", "current")
    leaked = ok(world.api.post("/token-signing-keys/rotation", {"immediate": True}), 201)
    _invalid(_workspaces(world, _bearer(second)), "unknownKey")
    published = {key["kid"] for key in ok(_anonymous(world).get("/oauth/jwks"))["keys"]}
    assert scheduled["kid"] not in published and leaked["kid"] in published
    renewed = _token(world, client)
    assert jwt.get_unverified_header(renewed)["kid"] == leaked["kid"]
    assert _workspaces(world, _bearer(renewed)).status_code == 200


@pytest.mark.journey("J40")
def test_people_are_created_changed_and_deactivated(world):
    """Given an administrator. When a person is created, read, changed and deactivated with
    `expectedVersion`, then each read shows it; a stale version answers `409 VERSION_CONFLICT`, a
    taken username `409 USERNAME_TAKEN`, and a person cannot be deleted."""
    person = ok(
        world.api.post("/users", {"username": "grace", "name": "Grace", "email": "g@example.org"}),
        201,
    )
    assert (person["active"], person["hasPassword"], person["version"]) == (True, False, 1)
    refused(
        world.api.post("/users", {"username": "GRACE", "name": "Another"}), 409, "USERNAME_TAKEN"
    )
    renamed = ok(
        world.api.patch(f"/users/{person['id']}", {"expectedVersion": 1, "name": "Grace H."})
    )
    refused(
        world.api.patch(f"/users/{person['id']}", {"expectedVersion": 1, "active": False}),
        409,
        "VERSION_CONFLICT",
    )
    gone = ok(
        world.api.patch(
            f"/users/{person['id']}", {"expectedVersion": renamed["version"], "active": False}
        )
    )
    assert (gone["name"], gone["active"]) == ("Grace H.", False)
    assert ok(world.api.get(f"/users/{person['id']}")) == gone
    refused(world.api.delete(f"/users/{person['id']}"), 405, "HTTP_ERROR")
    listed = ok(world.api.get("/users", q="grace"))["items"]
    assert [item["id"] for item in listed] == [person["id"]]


@pytest.mark.journey("J40")
def test_the_first_administrator_from_the_command_line(world):
    """Given the server. When `create_admin` is given a short password, then it refuses and creates
    nobody; given one that passes the rules, it creates the person with a password."""

    def create_admin(password: str):
        return subprocess.run(
            [
                sys.executable,
                "-m",
                "app.cli.create_admin",
                "--username",
                "ada",
                "--name",
                "Ada",
                "--password-stdin",
            ],
            input=password + "\n",
            cwd=BACKEND,
            env={**os.environ, "DATABASE_URL": render(world.database)},
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )

    short = create_admin("short")
    assert short.returncode == 2 and "at least 15 characters" in short.stderr
    assert ok(world.api.get("/users", q="ada"))["items"] == []
    common = create_admin("passwordpassword")
    assert common.returncode == 2 and "most common" in common.stderr
    created = create_admin("a long passphrase of mine")
    assert created.returncode == 0, created.stderr
    [admin] = ok(world.api.get("/users", q="ada"))["items"]
    # The first administrator holds what setting the instance up needs, at the instance (D282).
    grants = ok(world.api.get("/grants", principalId=admin["id"]))["items"]
    assert sorted(item["role"]["key"] for item in grants) == [
        "integration-admin",
        "model-admin",
        "operator",
        "owner",
        "security-admin",
        "workspace-admin",
    ]
    assert all(item["scope"]["instance"] for item in grants)
    assert (admin["username"], admin["hasPassword"], admin["active"]) == ("ada", True, True)
