"""J51 — Reach the engine from an assistant (USER_JOURNEYS.md § Agent access, 0.16 AG1).

An operator turns agent access on; an agent client, or a person through their assistant, connects to
``/mcp`` with the protocol's own client, sees only what its grants allow and stops on its next call
once revoked. An ``agent`` token reaches nothing else, and no other token reaches ``/mcp``. Every case
runs on two configurations through the public API.
"""

from typing import Any
from urllib.parse import parse_qs, urlsplit

import httpx
import pytest
from harness_identity import TestClient
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client
from scenario import W1, ok, refused
from test_j39_sign_in import PASSWORD, _bearer, _person, _pkce
from test_j39_sign_in import _sign_in as browser_sign_in

ON = {"MCP_ENABLED": "true"}
CALLBACK = "http://localhost:43123/callback"


def _browser(world) -> TestClient:
    return TestClient(world.api.client.app, authenticated=False)


def _agent_client(world, name: str = "Reporting assistant") -> dict:
    return ok(world.api.post("/clients", {"name": name, "kind": "agent"}), 201)


def _grant(world, kind: str, principal_id: str, role: str, **scope: Any) -> None:
    ok(
        world.api.post(
            "/grants",
            {
                "principal": {"kind": kind, "id": principal_id},
                "role": role,
                "scope": scope or {"workspaceKey": W1},
            },
        ),
        201,
    )


def _client_token(world, client: dict, **data: str):
    return _browser(world).post(
        "/oauth/token",
        data={
            "grant_type": "client_credentials",
            "client_id": client["id"],
            "client_secret": client["secret"],
            **data,
        },
    )


async def _connected(app: Any, token: str, use: Any) -> Any:
    """The protocol's client over the application's own event loop."""
    transport = httpx.ASGITransport(app=app)

    def factory(headers=None, timeout=None, auth=None) -> httpx.AsyncClient:
        return httpx.AsyncClient(
            transport=transport,
            base_url="http://testserver",
            headers=headers,
            timeout=timeout,
            auth=auth,
        )

    async with streamablehttp_client(
        "http://testserver/mcp",
        headers=_bearer(token),
        httpx_client_factory=factory,
    ) as (read, write, _), ClientSession(read, write) as session:
        await session.initialize()
        return await use(session)


def _use(world, token: str, use: Any) -> Any:
    client = world.api.client
    return client.portal.call(_connected, client.app, token, use)


def _tools(world, token: str) -> list[str]:
    async def use(session):
        return [tool.name for tool in (await session.list_tools()).tools]

    return _use(world, token, use)


def _call(world, token: str, tool: str, arguments: dict | None = None) -> Any:
    async def use(session):
        return await session.call_tool(tool, arguments or {})

    return _use(world, token, use)


def _register(browser: TestClient, **body: Any):
    return browser.post(
        "/oauth/register",
        json={"client_name": "Claude Code", "redirect_uris": [CALLBACK], **body},
    )


def _sign_in(browser: TestClient, application: str, username: str, callback: str = CALLBACK):
    """What an assistant does: the page in the person's browser, then the code for tokens."""
    verifier, challenge = _pkce()
    request = {
        "response_type": "code",
        "client_id": application,
        "redirect_uri": callback,
        "code_challenge": challenge,
        "code_challenge_method": "S256",
        "state": "s",
    }
    page = browser.get(
        "/oauth/authorize", params={**request, "scope": "agent", "resource": _endpoint(browser)}
    )
    assert page.status_code == 200, page.text
    assert "It calls itself <strong>Claude Code</strong>" in page.text
    assert "this computer (localhost)" in page.text
    assert "Sign in and allow" in page.text
    origin = f"http://{urlsplit(callback).netloc}"
    assert origin in page.headers["content-security-policy"]
    done = browser.post(
        "/oauth/authorize",
        data={**request, "username": username, "password": PASSWORD},
        follow_redirects=False,
    )
    assert done.status_code == 303, done.text
    code = parse_qs(urlsplit(done.headers["location"]).query)["code"][0]
    return browser.post(
        "/oauth/token",
        data={
            "grant_type": "authorization_code",
            "client_id": application,
            "code": code,
            "code_verifier": verifier,
            "redirect_uri": callback,
            "resource": _endpoint(browser),
        },
    )


def _endpoint(browser: TestClient) -> str:
    return browser.get("/.well-known/oauth-protected-resource/mcp").json()["resource"]


def _renew(browser: TestClient, client_id: str, refresh_token: str, **more: str):
    return browser.post(
        "/oauth/token",
        data={
            "grant_type": "refresh_token",
            "client_id": client_id,
            "refresh_token": refresh_token,
            **more,
        },
    )


@pytest.mark.journey("J51.1")
def test_with_agent_access_off_nothing_of_it_exists(world):
    """Given the default, the endpoint, its metadata and registration do not exist, the agent token
    is not issued, and the server's metadata does not offer it."""
    browser = _browser(world)
    assert browser.post("/mcp", json={}).status_code == 404
    assert browser.get("/.well-known/oauth-protected-resource").status_code == 404
    assert browser.get("/.well-known/oauth-protected-resource/mcp").status_code == 404
    assert _register(browser).status_code == 404
    metadata = browser.get("/.well-known/oauth-authorization-server").json()
    assert "agent" not in metadata["scopes_supported"]
    assert "registration_endpoint" not in metadata
    assert ok(world.api.get("/system"))["mcp"] == {"enabled": False}
    assert ok(world.api.get("/agent-access"))["enabled"] is False
    client = _agent_client(world)
    answer = _client_token(world, client)
    assert (answer.status_code, answer.json()["error"]) == (400, "invalid_scope")


@pytest.mark.journey("J51.2")
@pytest.mark.settings(**ON)
def test_a_client_connects_sees_what_its_grants_allow_and_stops_when_deactivated(world):
    """Given an agent client with no grant, it lists only the tool every caller has, and the other is
    refused. Granted the Agent role in a workspace, it lists and reads that workspace, and each call
    is recorded with its argument names and never their values. Deactivated, it stops on the next
    request though its token has not expired."""
    client = _agent_client(world)
    assert client["kind"] == "agent"
    token = ok(_client_token(world, client))["access_token"]
    assert _tools(world, token) == ["describe_access"]
    hidden = _call(world, token, "list_workspaces")
    assert hidden.isError and "no tool named" in hidden.content[0].text

    _grant(world, "client", client["id"], "agent")
    assert _tools(world, token) == ["describe_access", "list_workspaces"]
    listed = _call(world, token, "list_workspaces", {"search": "a secret word"})
    assert not listed.isError
    assert listed.structuredContent["items"] == []
    every = _call(world, token, "list_workspaces")
    assert [item["key"] for item in every.structuredContent["items"]] == [W1]

    calls = ok(world.api.get("/agent-access/calls"))["items"]
    newest = next(call for call in calls if call["arguments"] == ["search"])
    assert (newest["tool"], newest["outcome"]) == ("list_workspaces", "answered")
    assert (newest["principal"], newest["application"]) == (client["name"], None)
    assert "a secret word" not in str(calls)
    assert any(call["outcome"] == "refused" for call in calls)
    [listed_client] = ok(world.api.get("/agent-access/clients"))["items"]
    assert listed_client["calls30Days"] == len(calls)
    assert ok(world.api.get("/agent-access"))["calls30Days"] == len(calls)

    ok(
        world.api.patch(
            f"/clients/{client['id']}", {"active": False, "expectedVersion": client["version"]}
        )
    )
    answer = _browser(world).post("/mcp", json={}, headers=_bearer(token))
    assert answer.status_code == 401
    assert answer.json()["code"] == "TOKEN_INVALID"


@pytest.mark.journey("J51.3")
@pytest.mark.settings(**ON)
def test_each_token_reaches_only_its_own_api(world):
    """An agent token is refused by the management and consumer APIs; a management or consumer token
    by ``/mcp``; an agent client asking for another token and an API client asking for agent are
    refused. A request without a token is told where to read how to sign in."""
    agent = _agent_client(world)
    token = ok(_client_token(world, agent))["access_token"]
    browser = _browser(world)
    refused(browser.get("/api/v1/me", headers=_bearer(token)), 401, "TOKEN_INVALID")
    refused(browser.get("/api/consumer", headers=_bearer(token)), 401, "TOKEN_INVALID")

    api_client = ok(world.api.post("/clients", {"name": "Nightly import"}), 201)
    for scope in ("management", "consumer"):
        other = ok(_client_token(world, api_client, scope=scope))["access_token"]
        answer = browser.post("/mcp", json={}, headers=_bearer(other))
        assert answer.status_code == 401, scope
        assert answer.json()["code"] == "TOKEN_INVALID"
    assert _client_token(world, api_client, scope="agent").json()["error"] == "invalid_scope"
    for scope in ("management", "consumer"):
        assert _client_token(world, agent, scope=scope).json()["error"] == "invalid_scope"

    anonymous = browser.post("/mcp", json={})
    assert anonymous.status_code == 401
    challenge = anonymous.headers["www-authenticate"]
    assert (
        '/.well-known/oauth-protected-resource/mcp"' in challenge and 'scope="agent"' in challenge
    )


@pytest.mark.journey("J51.4")
@pytest.mark.settings(**ON)
def test_a_person_signs_in_through_an_assistant_and_can_end_it(world):
    """An assistant finds the sign-in from the metadata, registers, and the person signs in with PKCE
    on a page saying who asks. Its session renews in rotation, only as agent: its refresh token never
    gets a management token, and a browser session never gets an agent one. The person's sessions name
    the assistant; ending the session stops it on the next call."""
    browser = _browser(world)
    metadata = browser.get("/.well-known/oauth-protected-resource/mcp").json()
    assert metadata["scopes_supported"] == ["agent"]
    server = browser.get("/.well-known/oauth-authorization-server").json()
    assert metadata["authorization_servers"] == [server["issuer"]]
    assert "agent" in server["scopes_supported"] and server["registration_endpoint"]

    registered = ok(_register(browser), 201)
    assert registered["token_endpoint_auth_method"] == "none"
    person = _person(world, "petra")
    _grant(world, "user", person["id"], "reader")
    # Any port: a local assistant takes a free one each time.
    tokens = ok(
        _sign_in(browser, registered["client_id"], "petra", "http://localhost:50999/callback")
    )
    assert tokens["scope"] == "agent" and tokens["refresh_token"]
    assert "oauth_refresh" not in browser.cookies
    assert _tools(world, tokens["access_token"]) == ["describe_access", "list_workspaces"]
    described = _call(world, tokens["access_token"], "describe_access").structuredContent
    assert (described["name"], described["through"]) == ("Petra", "Claude Code")

    client_id = registered["client_id"]
    wrong = _renew(browser, client_id, tokens["refresh_token"], scope="management")
    assert wrong.json()["error"] == "invalid_scope"
    as_browser = _renew(browser, "browser", tokens["refresh_token"])
    assert as_browser.json()["error"] == "invalid_grant"
    renewed = ok(_renew(browser, client_id, tokens["refresh_token"]))
    assert renewed["refresh_token"] != tokens["refresh_token"]
    assert renewed["scope"] == "agent"

    own = _browser(world)
    access = browser_sign_in(own, "petra")
    assert (
        own.post(
            "/oauth/token",
            data={"grant_type": "refresh_token", "client_id": "browser", "scope": "agent"},
        ).json()["error"]
        == "invalid_scope"
    )
    sessions = own.get("/api/v1/me/sessions", headers=_bearer(access)).json()["items"]
    named = next(item for item in sessions if item["application"] == "Claude Code")
    ended = own.delete(f"/api/v1/me/sessions/{named['id']}", headers=_bearer(access))
    assert ended.status_code in (200, 204), ended.text
    answer = browser.post("/mcp", json={}, headers=_bearer(renewed["access_token"]))
    assert answer.status_code == 401


@pytest.mark.journey("J51.5")
@pytest.mark.settings(**ON)
def test_an_assistant_never_holds_approve_or_publish(world):
    """A person holding Approve and Publish keeps neither through an assistant, whatever their role;
    an administrator with no reading role lists only the tool every caller has."""
    browser = _browser(world)
    application = ok(_register(browser), 201)["client_id"]
    owner = _person(world, "olga")
    _grant(world, "user", owner["id"], "owner")
    token = ok(_sign_in(browser, application, "olga"))["access_token"]
    [grant] = _call(world, token, "describe_access").structuredContent["grants"]
    names = {group for group in grant["actionGroups"]}
    assert names == {"Browse", "Work in change sets"}

    keeper = _person(world, "kim")
    _grant(world, "user", keeper["id"], "security-admin", instance=True)
    token = ok(_sign_in(_browser(world), application, "kim"))["access_token"]
    assert _tools(world, token) == ["describe_access"]


@pytest.mark.journey("J51.6")
@pytest.mark.settings(**ON, MCP_REDIRECT_HOSTS="assistant.example.com")
def test_where_a_self_registered_assistant_may_return(world):
    """An outside HTTP address and an HTTPS host not listed are refused; a listed host and this
    computer are taken. A sign-in naming another address than the registered one is not served, and a
    blocked assistant signs nobody in and its sessions end."""
    browser = _browser(world)
    for address in ("http://outside.example.com/cb", "https://elsewhere.example.com/cb"):
        answer = _register(browser, redirect_uris=[address])
        assert (answer.status_code, answer.json()["error"]) == (400, "invalid_redirect_uri")
    hosted = ok(_register(browser, redirect_uris=["https://assistant.example.com/cb"]), 201)
    _verifier, challenge = _pkce()
    page = browser.get(
        "/oauth/authorize",
        params={
            "response_type": "code",
            "client_id": hosted["client_id"],
            "redirect_uri": "https://assistant.example.com/other",
            "code_challenge": challenge,
            "code_challenge_method": "S256",
        },
    )
    assert "not one this engine signs people in to" in page.text

    application = ok(_register(browser), 201)["client_id"]
    person = _person(world, "petra")
    _grant(world, "user", person["id"], "reader")
    tokens = ok(_sign_in(browser, application, "petra"))
    items = ok(world.api.get("/agent-access/applications"))["items"]
    listed = next(item for item in items if item["id"] == application)
    assert (listed["signedIn"], listed["returnsTo"]) == (1, ["this computer (localhost)"])

    blocked = ok(world.api.post(f"/agent-access/applications/{application}/block", {}))
    assert blocked["blocked"] is True
    answer = browser.post("/mcp", json={}, headers=_bearer(tokens["access_token"]))
    assert answer.status_code == 401
    assert _renew(browser, application, tokens["refresh_token"]).json()["error"] == "invalid_client"
    ok(world.api.post(f"/agent-access/applications/{application}/restore", {}))
    assert _renew(browser, application, tokens["refresh_token"]).json()["error"] == "invalid_grant"
    refused(
        world.api.post("/agent-access/applications/nobody/block", {}),
        404,
        "AGENT_APPLICATION_NOT_FOUND",
    )


@pytest.mark.journey("J51.6")
@pytest.mark.settings(**ON, MCP_OPEN_REGISTRATION="false")
def test_with_registration_closed_only_a_registered_assistant_signs_in(world):
    """With open registration off, an assistant cannot register itself and the metadata offers no
    endpoint; one an administrator registered signs people in."""
    browser = _browser(world)
    assert _register(browser).status_code == 403
    server = browser.get("/.well-known/oauth-authorization-server").json()
    assert "registration_endpoint" not in server
    refused(
        world.api.post(
            "/agent-access/applications",
            {"name": "x", "redirectUris": ["http://outside.example/cb"]},
        ),
        422,
        "AGENT_APPLICATION_INVALID",
    )
    made = ok(
        world.api.post(
            "/agent-access/applications", {"name": "Claude Code", "redirectUris": [CALLBACK]}
        ),
        201,
    )
    person = _person(world, "petra")
    _grant(world, "user", person["id"], "reader")
    assert ok(_sign_in(browser, made["id"], "petra"))["scope"] == "agent"


@pytest.mark.journey("J51.7")
@pytest.mark.settings(**ON, MCP_RATE_PER_MINUTE="2")
def test_the_call_past_the_limit_is_refused_with_its_wait(world):
    """A caller past its calls a minute is told how long to wait; another caller is not held up, and
    the refused call is on the list as limited."""
    first = _agent_client(world)
    token = ok(_client_token(world, first))["access_token"]
    assert not _call(world, token, "describe_access").isError
    assert not _call(world, token, "describe_access").isError
    limited = _call(world, token, "describe_access")
    assert limited.isError and "try again in" in limited.content[0].text
    other = ok(_client_token(world, _agent_client(world, "Another")))["access_token"]
    assert not _call(world, other, "describe_access").isError
    outcomes = [call["outcome"] for call in ok(world.api.get("/agent-access/calls"))["items"]]
    assert sorted(outcomes) == ["answered", "answered", "answered", "limited"]
