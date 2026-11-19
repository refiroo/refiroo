"""J51 — Reach the engine from an assistant (USER_JOURNEYS.md § Agent access, 0.16 AG1).

An operator turns agent access on; an agent client, or a person through their assistant, connects to
``/mcp`` with the protocol's own client, sees only what its grants allow and stops on its next call
once revoked. An ``agent`` token reaches nothing else, and no other token reaches ``/mcp``. Every case
runs on two configurations through the public API.
"""

from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from typing import Any
from urllib.parse import parse_qs, urlsplit

import httpx
import pytest
from harness_identity import TestClient
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client
from scenario import W1, ok, refused
from sqlalchemy import select
from test_j39_sign_in import PASSWORD, _bearer, _person, _pkce, _used_long_ago
from test_j39_sign_in import _sign_in as browser_sign_in
from test_j39_sign_in import address as email_of

from app.engine.identity.passwords import digest
from app.models.database import SessionRefreshToken

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

    http_client = httpx.AsyncClient(
        transport=transport, base_url="http://testserver", headers=_bearer(token)
    )

    async with (
        http_client,
        streamable_http_client("http://testserver/mcp", http_client=http_client) as (
            read,
            write,
            _,
        ),
        ClientSession(read, write) as session,
    ):
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


def _sign_in(browser: TestClient, application: str, name: str, callback: str = CALLBACK):
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
        data={**request, "email": email_of(name), "password": PASSWORD},
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
    assert {"describe_access", "list_workspaces"} <= set(_tools(world, token))
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
    assert {"describe_access", "list_workspaces"} <= set(_tools(world, tokens["access_token"]))
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
@pytest.mark.settings(**ON)
def test_block_and_restore_answer_the_people_signed_in_as_the_list_does(world):
    """Given a person signed in through an assistant. When the assistant is restored while not
    blocked, the answer counts that person as the list does; when it is blocked, the sessions end
    and the answer counts none."""
    browser = _browser(world)
    application = ok(_register(browser), 201)["client_id"]
    person = _person(world, "quinn")
    _grant(world, "user", person["id"], "reader")
    ok(_sign_in(browser, application, "quinn"))
    restored = ok(world.api.post(f"/agent-access/applications/{application}/restore", {}))
    assert (restored["blocked"], restored["signedIn"]) == (False, 1)
    blocked = ok(world.api.post(f"/agent-access/applications/{application}/block", {}))
    assert (blocked["blocked"], blocked["signedIn"]) == (True, 0)


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
    the refused call is on the list as limited. The protocol's client lists the tools before it calls
    one, and a listing counts as a call (R-F12)."""
    first = _agent_client(world)
    token = ok(_client_token(world, first))["access_token"]
    assert not _call(world, token, "describe_access").isError
    limited = _call(world, token, "describe_access")
    assert limited.isError and "try again in" in limited.content[0].text
    other = ok(_client_token(world, _agent_client(world, "Another")))["access_token"]
    assert not _call(world, other, "describe_access").isError
    calls = ok(world.api.get("/agent-access/calls"))["items"]
    assert sorted(call["outcome"] for call in calls) == ["answered"] * 4 + ["limited"]
    assert {call["tool"] for call in calls} == {"describe_access", "tools/list"}


@pytest.mark.journey("J51.4")
@pytest.mark.settings(**ON)
def test_an_assistants_refresh_token_gets_no_management_token_from_the_console(world):
    """Given a person signed in through an assistant, when its refresh token is presented to the
    API console as a browser's cookie, then there is no session: no management token and no page of
    the engine opens for it; the same person's browser session still gets one."""
    browser = _browser(world)
    application = ok(_register(browser), 201)["client_id"]
    person = _person(world, "petra")
    _grant(world, "user", person["id"], "reader")
    tokens = ok(_sign_in(browser, application, "petra"))
    asking = _browser(world)
    answer = asking.post(
        "/oauth/console-token", headers={"Cookie": f"oauth_refresh={tokens['refresh_token']}"}
    )
    assert (answer.status_code, answer.json()["error"]) == (401, "not_signed_in")
    own = _browser(world)
    browser_sign_in(own, "petra")
    assert own.post("/oauth/console-token").status_code == 200


@pytest.mark.journey("J51.2")
@pytest.mark.settings(**ON)
def test_a_request_from_another_site_is_refused_before_any_token_is_read(world):
    """Given agent access on, when a web page of another site posts to /mcp, then it is 403 with or
    without a token; a request with no origin goes on to the token check."""
    agent = _agent_client(world)
    token = ok(_client_token(world, agent))["access_token"]
    browser = _browser(world)
    for headers in (_bearer(token), {}):
        answer = browser.post(
            "/mcp", json={}, headers={"Origin": "https://evil.example", **headers}
        )
        assert answer.status_code == 403, headers
    assert browser.post("/mcp", json={}).status_code == 401


@pytest.mark.journey("J51.6")
@pytest.mark.settings(**ON)
def test_what_a_self_registration_may_carry_and_how_often_one_address_may_register(world):
    """Given open registration, a registration with more than ten addresses, or one longer than 2,000
    characters, is refused; one address registering again and again is slowed with a wait."""
    browser = _browser(world)
    many = [f"http://localhost:{port}/callback" for port in range(40000, 40011)]
    assert _register(browser, redirect_uris=many).json()["error"] == "invalid_redirect_uri"
    long = "http://localhost:43123/" + "a" * 2000
    assert _register(browser, redirect_uris=[long]).json()["error"] == "invalid_redirect_uri"
    ok(_register(browser, redirect_uris=many[:10]), 201)
    for _ in range(9):
        ok(_register(browser), 201)
    for _ in range(3):
        _register(browser)
    slowed = _register(browser)
    assert slowed.status_code == 429 and slowed.json()["error"] == "temporarily_unavailable"
    assert "try again in" in slowed.json()["error_description"]


def _assistant_ends(world, name: str, application: str) -> list[float]:
    """Days until each of a person's open assistant sessions ends, as the sessions API shows them
    (a fresh browser sign-in of the person lists them), in the order they started."""
    own = _browser(world)
    access = browser_sign_in(own, name)
    items = ok(world.api.client.get("/api/v1/me/sessions", headers=_bearer(access)))["items"]
    return [
        _days_from_now(datetime.fromisoformat(item["endsAt"]))
        for item in items
        if item["application"] == application
    ]


def _issued_long_ago(world, refresh_token: str, days: int) -> None:
    """Age a refresh token's issue by ``days``, as that time passing would."""
    with world.api.client.app.state.session_factory() as session:
        token = session.scalar(
            select(SessionRefreshToken).where(
                SessionRefreshToken.token_hash == digest(refresh_token)
            )
        )
        token.issued_at = token.issued_at - timedelta(days=days)
        session.commit()


def _tokens_held(world, *refresh_tokens: str) -> int:
    """How many of these refresh tokens the engine still holds (no API shows it)."""
    with world.api.client.app.state.session_factory() as session:
        return len(
            session.scalars(
                select(SessionRefreshToken.id).where(
                    SessionRefreshToken.token_hash.in_([digest(t) for t in refresh_tokens])
                )
            ).all()
        )


def _days_from_now(moment: datetime) -> float:
    return (moment - datetime.now(UTC)).total_seconds() / 86400


@pytest.mark.journey("J51.8")
@pytest.mark.settings(**ON)
def test_a_spent_refresh_token_renews_an_assistant_but_still_ends_a_browser(world):
    """Given a person signed in through an assistant that several windows share. When a window
    presents a token already used, minutes after its use, then it renews and answers a new token,
    again and again, and the session stays open. When a browser session's used token comes again
    after the reuse grace, then it still ends."""
    browser = _browser(world)
    application = ok(_register(browser), 201)["client_id"]
    person = _person(world, "petra")
    _grant(world, "user", person["id"], "reader")
    first = ok(_sign_in(browser, application, "petra"))
    second = ok(_renew(browser, application, first["refresh_token"]))
    _used_long_ago(world, first["refresh_token"])
    third = ok(_renew(browser, application, first["refresh_token"]))
    again = ok(_renew(browser, application, first["refresh_token"]))
    behind = ok(_renew(browser, application, second["refresh_token"]))
    assert len({first["refresh_token"], second["refresh_token"], third["refresh_token"]}) == 3
    assert again["refresh_token"] not in {third["refresh_token"], behind["refresh_token"]}
    assert not _call(world, behind["access_token"], "describe_access").isError
    assert not _call(world, third["access_token"], "describe_access").isError

    own = _browser(world)
    browser_sign_in(own, "petra")
    cookie = own.cookies.get("oauth_refresh")
    ok(own.post("/oauth/token", data={"grant_type": "refresh_token", "client_id": "browser"}))
    newer = own.cookies.get("oauth_refresh")
    _used_long_ago(world, cookie)
    for presented in (cookie, newer):
        gone = own.post(
            "/oauth/token",
            data={
                "grant_type": "refresh_token",
                "client_id": "browser",
                "refresh_token": presented,
            },
        )
        assert gone.json()["error"] == "invalid_grant"


@pytest.mark.journey("J51.8")
@pytest.mark.settings(**ON)
def test_the_limits_set_on_the_page_decide_when_a_session_ends(world):
    """Given the defaults, an assistant's sign-in ends 30 days ahead unless renewed and 90 days in all
     (the sessions API's end). When an administrator sets 10 days without use and 20 in all,
    then the next renewal ends the session 10 days ahead, as does a new sign-in; with both at 15 a new
    sign-in ends 15 days ahead, the days in all. The browser keeps its own limits. A change is a
    security event."""
    shown = ok(world.api.get("/agent-access"))
    assert (shown["sessionIdleDays"], shown["sessionDays"]) == (30, 90)
    assert (shown["browserSessionIdleHours"], shown["browserSessionDays"]) == (12, 14)
    browser = _browser(world)
    application = ok(_register(browser), 201)["client_id"]
    person = _person(world, "petra")
    _grant(world, "user", person["id"], "reader")
    tokens = ok(_sign_in(browser, application, "petra"))
    [first_end] = _assistant_ends(world, "petra", "Claude Code")
    assert 29 < first_end <= 30

    changed = ok(
        world.api.patch(
            "/agent-access",
            {
                "sessionIdleDays": 10,
                "sessionDays": 20,
                "expectedVersion": shown["sessionLimitsVersion"],
            },
        )
    )
    assert (changed["sessionIdleDays"], changed["sessionDays"]) == (10, 20)
    assert changed["sessionLimitsVersion"] > shown["sessionLimitsVersion"]
    ok(_renew(browser, application, tokens["refresh_token"]))
    ok(_sign_in(_browser(world), application, "petra"))
    renewed_end, fresh_end = _assistant_ends(world, "petra", "Claude Code")
    assert 9 < renewed_end <= 10 and 9 < fresh_end <= 10

    events = ok(world.api.get("/security-events", aggregateType="agent-access-settings"))
    [event] = events["items"]
    assert event["details"]["changedFields"] == ["sessionIdleDays", "sessionDays"]
    assert (event["details"]["sessionIdleDays"], event["details"]["sessionDays"]) == (10, 20)

    both = ok(world.api.patch("/agent-access", {"sessionIdleDays": 15, "sessionDays": 15}))
    assert (both["sessionIdleDays"], both["sessionDays"]) == (15, 15)
    ok(_sign_in(_browser(world), application, "petra"))
    assert 14 < _assistant_ends(world, "petra", "Claude Code")[-1] <= 15

    one = ok(world.api.patch("/agent-access", {"sessionIdleDays": 5}))
    assert (one["sessionIdleDays"], one["sessionDays"]) == (5, 15)


@pytest.mark.journey("J51.8")
@pytest.mark.settings(**ON)
def test_a_spent_token_stops_at_sign_out_a_block_and_the_window(world):
    """Given a spent refresh token of an assistant's session. When the person signs out, or the
    assistant is blocked, then the spent token and the newest both get `invalid_grant` (while it is blocked the application itself is refused as `invalid_client`). When the
    days without use have passed since the spent token was issued, then it is refused while the
    newest still renews and the session stays open (AS-D4); the next sweep deletes the spent token
    and, once a session has ended, all of its tokens."""
    browser = _browser(world)
    application = ok(_register(browser), 201)["client_id"]
    person = _person(world, "petra")
    _grant(world, "user", person["id"], "reader")

    def spent_pair() -> tuple[str, str]:
        first = ok(_sign_in(browser, application, "petra"))["refresh_token"]
        return first, ok(_renew(browser, application, first))["refresh_token"]

    sweep = world.api.client.app.state.job_worker.sweep

    spent, newest = spent_pair()
    ok(browser.post("/oauth/revoke", data={"token": newest}))
    for token in (spent, newest):
        assert _renew(browser, application, token).json()["error"] == "invalid_grant"
    sweep()
    assert _tokens_held(world, spent, newest) == 0

    spent, newest = spent_pair()
    ok(world.api.post(f"/agent-access/applications/{application}/block", {}))
    for token in (spent, newest):  # a blocked application is no client at all
        assert _renew(browser, application, token).json()["error"] == "invalid_client"
    ok(world.api.post(f"/agent-access/applications/{application}/restore", {}))
    for token in (spent, newest):  # and its sessions stay ended once it is restored
        assert _renew(browser, application, token).json()["error"] == "invalid_grant"

    spent, newest = spent_pair()
    _issued_long_ago(world, spent, 31)
    assert _renew(browser, application, spent).json()["error"] == "invalid_grant"
    renewed = ok(_renew(browser, application, newest))
    assert len(_assistant_ends(world, "petra", "Claude Code")) == 1
    sweep()
    assert _tokens_held(world, spent) == 0 and _tokens_held(world, newest) == 1
    ok(_renew(browser, application, renewed["refresh_token"]))


@pytest.mark.journey("J51.8")
@pytest.mark.settings(**ON)
def test_two_windows_renew_one_session_at_the_same_moment(world):
    """Given two windows holding different tokens of one assistant session. When both renew at the
    same moment, then both succeed with new tokens, the person has one assistant session, and each
    new token renews it."""
    application = ok(_register(_browser(world)), 201)["client_id"]
    person = _person(world, "petra")
    _grant(world, "user", person["id"], "reader")
    first = ok(_sign_in(_browser(world), application, "petra"))["refresh_token"]
    second = ok(_renew(_browser(world), application, first))["refresh_token"]
    windows = [(_browser(world), first), (_browser(world), second)]
    with ThreadPoolExecutor(max_workers=2) as pool:
        answers = [
            ok(done) for done in pool.map(lambda w: _renew(w[0], application, w[1]), windows)
        ]
    new = [answer["refresh_token"] for answer in answers]
    assert len(set(new) | {first, second}) == 4
    assert len(_assistant_ends(world, "petra", "Claude Code")) == 1
    for token in new:
        ok(_renew(_browser(world), application, token))


@pytest.mark.journey("J51.8")
@pytest.mark.settings(**ON)
def test_limits_outside_the_range_or_by_someone_who_may_not_are_refused(world):
    """Given the limits, when a value is outside 1 to 365, or the days in all are fewer than the days
    without use, or the version read is stale, then the change is refused and nothing changes; a
    person without Security administration may not read or change them."""
    before = ok(world.api.get("/agent-access"))
    for body in ({"sessionIdleDays": 0}, {"sessionDays": 366}, {"sessionIdleDays": 1.5}):
        refused(world.api.patch("/agent-access", body), 422, "REQUEST_VALIDATION_ERROR")
    refused(
        world.api.patch("/agent-access", {"sessionIdleDays": 60, "sessionDays": 30}),
        422,
        "AGENT_SESSION_LIMITS_INVALID",
    )
    refused(
        world.api.patch("/agent-access", {"sessionIdleDays": 100}),
        422,
        "AGENT_SESSION_LIMITS_INVALID",
    )
    refused(
        world.api.patch("/agent-access", {"sessionDays": 5, "expectedVersion": 99}),
        409,
        "VERSION_CONFLICT",
    )
    after = ok(world.api.get("/agent-access"))
    assert (after["sessionIdleDays"], after["sessionDays"]) == (
        before["sessionIdleDays"],
        before["sessionDays"],
    )

    person = _person(world, "rita")
    _grant(world, "user", person["id"], "reader")
    own = _browser(world)
    access = browser_sign_in(own, "rita")
    for answer in (
        own.get("/api/v1/agent-access", headers=_bearer(access)),
        own.patch("/api/v1/agent-access", json={"sessionDays": 5}, headers=_bearer(access)),
    ):
        assert answer.status_code == 403, answer.text
        assert answer.json()["error"]["code"] == "FORBIDDEN"
