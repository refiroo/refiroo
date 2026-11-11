"""The ``security``, ``oauth`` and ``agent-access`` areas of the management API's reference, recorded
from a run on the guide's reference data (see ``test_reference_recording.py``, whose seed, scenario and
normaliser this file uses).

The administrator of the Graubünden instance gives a timetable team access: a role for editing stops, a
group, two people (each sets a password through the link the administrator passes on) and the grants that
let the group work in the Graubünden workspace on the network application only. A person sets up an
authenticator app and passkeys, changes their password and looks at their sessions; a client for a
nightly export gets a secret, rotates it and signs in; the organisation's sign-in provider is connected
(the harness's OpenID Connect provider, ``tests/oidc_provider.py``) and a person who signed in through it
is linked to the one who already had an account; the token signing key is rotated; an assistant is
registered and an agent client reaches the engine through ``/mcp``. Each step records the main
successful use of the operation it calls; the refusals the areas' text names are asserted without being
recorded.

What needs a browser is made as the browser makes it, with the harness's fakes: a passkey is added on the
engine's own page with ``tests/software_authenticator.py`` (the page is not an operation of the document;
the operations that list, rename and remove passkeys are recorded), and a sign-in through the provider
runs the provider's pages in this process. Every secret in an answer (a client's secret, an
authenticator's seed, recovery codes, tokens, reset links) is replaced by a fixed placeholder in the
recorded file (``SECRET_MASKS`` and the calls' ``mask``).

    cd backend && RDM_RECORD_EXAMPLES=1 .venv/bin/python -m pytest tests/test_reference_security.py -q
"""

import base64
import hashlib
import hmac
import os
import secrets
import struct
import time
from collections.abc import Iterator
from typing import Any
from urllib.parse import parse_qs, urlsplit

import pytest
import seeds
from harness_identity import TestClient
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client
from oidc_provider import OidcProvider
from software_authenticator import SoftwareAuthenticator
from test_reference_change_sets import Person
from test_reference_recording import (
    BASE,
    RECORDING,
    SEED,
    Scenario,
    _application,
    _register_seed,
)

GRAUBUENDEN = {"workspace_key": "graubuenden"}
REDIRECT = BASE + "/signed-in"
ASSISTANT_CALLBACK = "http://localhost:43123/callback"
FIRST = "a first long passphrase"
SECOND = "a second long passphrase"
SECRET_PLACEHOLDER = {"secret": "example-client-secret"}
SEED_PLACEHOLDER = {"secret": "JBSWY3DPEHPK3PXP"}
SETTINGS = {"MCP_ENABLED": "true", "MCP_OPEN_REGISTRATION": "true"}


def _totp(secret: str) -> str:
    """The six-digit code of the current 30-second step, by RFC 6238's own arithmetic."""
    padded = secret.replace(" ", "").upper()
    key = base64.b32decode(padded + "=" * (-len(padded) % 8))
    digest = hmac.new(key, struct.pack(">Q", int(time.time()) // 30), hashlib.sha1).digest()
    offset = digest[-1] & 0x0F
    number = struct.unpack(">I", digest[offset : offset + 4])[0] & 0x7FFFFFFF
    return f"{number % 10**6:06d}"


def _basic(client_id: str, secret: str) -> dict[str, str]:
    return {"Authorization": "Basic " + base64.b64encode(f"{client_id}:{secret}".encode()).decode()}


def _bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _pkce() -> tuple[str, str]:
    verifier = secrets.token_urlsafe(48)
    digest = hashlib.sha256(verifier.encode()).digest()
    return verifier, base64.urlsafe_b64encode(digest).rstrip(b"=").decode()


def _request(challenge: str) -> dict[str, str]:
    return {
        "response_type": "code",
        "client_id": "browser",
        "redirect_uri": REDIRECT,
        "code_challenge": challenge,
        "code_challenge_method": "S256",
        "state": "where-i-was",
    }


def _browser(s: Scenario) -> TestClient:
    """A browser of its own, with its own cookies, that sends no harness token."""
    return TestClient(s.client.app, authenticated=False)


def _signed_in_browser(s: Scenario, email: str, password: str) -> TestClient:
    """A browser signed in as the person, as the sign-in page does: the refresh cookie stays in it."""
    browser = _browser(s)
    verifier, challenge = _pkce()
    answer = browser.post(
        "/oauth/authorize",
        data={**_request(challenge), "email": email, "password": password},
        follow_redirects=False,
    )
    assert answer.status_code == 303, answer.text[:300]
    code = parse_qs(urlsplit(answer.headers["location"]).query)["code"][0]
    token = browser.post(
        "/oauth/token",
        data={
            "grant_type": "authorization_code",
            "client_id": "browser",
            "code": code,
            "code_verifier": verifier,
            "redirect_uri": REDIRECT,
        },
    )
    assert token.status_code == 200, token.text
    return browser


def _through_provider(s: Scenario, idp: OidcProvider, key: str, **person: Any) -> None:
    """A sign-in through the provider as ``person``: the person is made at the callback."""
    browser = _browser(s)
    _, challenge = _pkce()
    started = browser.get(
        f"/oauth/providers/{key}/start", params=_request(challenge), follow_redirects=False
    )
    assert started.status_code == 303, started.text[:300]
    back = urlsplit(idp.sign_in(started.headers["location"], **person))
    answer = browser.get(f"{back.path}?{back.query}", follow_redirects=False)
    assert answer.status_code == 303, answer.text[:300]


def _set_password(s: Scenario, person: dict, password: str) -> None:
    """The person follows the administrator's link, as they would in a browser."""
    link = s.call(
        "POST",
        "/api/v1/users/{user_id}/password-reset",
        path={"user_id": person["id"]},
        body={},
        status=201,
    )
    token = parse_qs(urlsplit(link["url"]).query)["token"][0]
    answer = _browser(s).post(
        "/oauth/password", data={"token": token, "password": password, "repeat": password}
    )
    assert answer.status_code == 200, answer.text[:300]


def _person_calls(s: Scenario, email: str, password: str) -> Person:
    return Person(s, email, password)


def _add_passkey(
    browser: TestClient, password: str, authenticator: SoftwareAuthenticator, name: str
) -> str:
    """A passkey added on the engine's own page as the browser does; its ID."""
    started = browser.post("/oauth/passkeys/registration/options", json={"proof": password})
    assert started.status_code == 200, started.text
    body = started.json()
    credential = authenticator.register(body["options"])
    done = browser.post(
        "/oauth/passkeys/registration/verify",
        json={"ceremony": body["ceremony"], "credential": credential, "name": name},
    )
    assert done.status_code == 200, done.text
    return done.json()["id"]


def _enrol(e: Scenario, record: bool = False) -> list[str]:
    """An authenticator app set up and confirmed; the ten recovery codes."""
    started = e.call(
        "POST",
        "/api/v1/me/second-factor",
        status=201,
        **(
            {
                "record": "enrolment",
                "summary": "A new secret for the authenticator app, shown once",
                "mask": SEED_PLACEHOLDER,
            }
            if record
            else {}
        ),
    )
    code = _totp(started["secret"])
    confirmed = e.call(
        "POST",
        "/api/v1/me/second-factor/confirmation",
        body={"code": code},
        status=200,
        **(
            {
                "record": "confirmed",
                "summary": "The app's code confirms it; ten recovery codes come with it",
                "mask": {
                    "code": "123456",
                    "recoveryCodes": [f"abcd-efgh-{n:04d}" for n in range(1, 11)],
                },
            }
            if record
            else {}
        ),
    )
    return confirmed["recoveryCodes"]


async def _connected(app: Any, token: str, use: Any) -> Any:
    """The protocol's client over the application's own event loop."""
    import httpx

    transport = httpx.ASGITransport(app=app)

    def factory(headers=None, timeout=None, auth=None) -> httpx.AsyncClient:
        return httpx.AsyncClient(
            transport=transport,
            base_url="http://testserver",
            headers=headers,
            timeout=timeout,
            auth=auth,
        )

    async with (
        streamablehttp_client(
            "http://testserver/mcp", headers=_bearer(token), httpx_client_factory=factory
        ) as (read, write, _),
        ClientSession(read, write) as session,
    ):
        await session.initialize()
        return await use(session)


def _call_tool(s: Scenario, token: str, tool: str, arguments: dict | None = None) -> Any:
    async def use(session):
        return await session.call_tool(tool, arguments or {})

    return s.client.portal.call(_connected, s.client.app, token, use)


@pytest.fixture(scope="module")
def security() -> Iterator[Scenario]:
    _register_seed()
    seeds.ensure(SEED)
    url = seeds.clone(SEED)
    saved = {key: os.environ.get(key) for key in SETTINGS}
    os.environ.update(SETTINGS)
    try:
        with _application(url) as client:
            scenario = Scenario(client)
            yield scenario
            if RECORDING:
                scenario.write_examples()
    finally:
        for key, value in saved.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        seeds.drop(url.database)


def test_an_administrator_gives_a_timetable_team_access(security):
    """People, roles, groups, grants and the caller's own view of them."""
    s = security
    groups = s.call(
        "GET",
        "/api/v1/action-groups",
        status=200,
        record="catalogue",
        summary="The action groups roles are made of, each with its actions and their operations",
    )
    assert "browse" in [item["key"] for item in groups["items"]]

    page = s.call(
        "GET",
        "/api/v1/roles",
        query={"pageSize": 3},
        status=200,
        record="firstPage",
        summary="The predefined roles come first",
    )
    assert page["items"][0]["predefined"] is True
    role = s.call(
        "POST",
        "/api/v1/roles",
        body={
            "name": "Timetable editor",
            "description": "Edits stops and prepares change sets",
            "actionGroups": ["browse", "edit-live", "change-sets"],
        },
        status=201,
        record="timetableEditor",
        summary="A custom role of three action groups",
    )
    assert role["key"] == "timetable-editor" and role["predefined"] is False
    s.call(
        "GET",
        "/api/v1/roles/{role_key}",
        path={"role_key": "timetable-editor"},
        status=200,
        record="timetableEditor",
        summary="The custom role, with how many grants give it",
    )
    changed = s.call(
        "PATCH",
        "/api/v1/roles/{role_key}",
        path={"role_key": "timetable-editor"},
        body={
            "expectedVersion": 1,
            "description": "Edits stops, prepares change sets and imports",
            "actionGroups": ["browse", "edit-live", "change-sets", "bulk"],
        },
        status=200,
        record="addBulk",
        summary="Add Bulk and import to the role; its holders gain it at their next request",
    )
    assert changed["version"] == 2
    s.call(
        "PATCH",
        "/api/v1/roles/{role_key}",
        path={"role_key": "reader"},
        body={"expectedVersion": 1, "description": "x"},
        status=409,
        code="ROLE_PREDEFINED",
    )
    s.call(
        "PATCH",
        "/api/v1/roles/{role_key}",
        path={"role_key": "timetable-editor"},
        body={"expectedVersion": 1, "actionGroups": ["browse", "nothing"]},
        status=409,
        code="VERSION_CONFLICT",
    )
    s.call(
        "POST",
        "/api/v1/roles",
        body={"name": "Timetable editor", "actionGroups": ["nothing"]},
        status=409,
        code="ROLE_NAME_TAKEN",
    )
    s.call(
        "POST",
        "/api/v1/roles",
        body={"name": "Another", "actionGroups": ["nothing"]},
        status=422,
        code="ACTION_GROUP_UNKNOWN",
    )
    s.call(
        "GET",
        "/api/v1/roles/{role_key}",
        path={"role_key": "nobody"},
        status=404,
        code="ROLE_NOT_FOUND",
    )
    spare = s.call(
        "POST",
        "/api/v1/roles",
        body={"name": "Spare role", "copiedFrom": "reader"},
        status=201,
    )
    assert spare["actionGroups"] == ["browse"]
    s.call(
        "DELETE",
        "/api/v1/roles/{role_key}",
        path={"role_key": spare["key"]},
        status=204,
        record="unusedRole",
        summary="Delete a custom role no grant gives",
    )

    # People.
    editor = s.call(
        "POST",
        "/api/v1/users",
        body={"name": "Reference Editor", "email": "editor@example.org"},
        status=201,
        record="referenceEditor",
        summary="A person, named by the e-mail address they sign in with",
    )
    assert editor["hasPassword"] is False and editor["active"] is True
    s.call(
        "POST",
        "/api/v1/users",
        body={"name": "Other", "email": "EDITOR@example.org"},
        status=409,
        code="EMAIL_TAKEN",
    )
    reviewer = s.call(
        "POST",
        "/api/v1/users",
        body={"name": "Reference Reviewer", "email": "reviewer@example.org"},
        status=201,
    )
    s.call(
        "POST",
        "/api/v1/users/{user_id}/password-reset",
        path={"user_id": editor["id"]},
        body={"send": True},
        status=409,
        code="MAIL_NOT_SET_UP",
    )
    s.call(
        "POST",
        "/api/v1/users/{user_id}/password-reset",
        path={"user_id": "00000000-0000-4000-8000-00000000ffff"},
        body={},
        status=404,
        code="USER_NOT_FOUND",
    )
    link = s.call(
        "POST",
        "/api/v1/users/{user_id}/password-reset",
        path={"user_id": editor["id"]},
        body={},
        status=201,
        record="link",
        summary="A one-time link that sets the person's password, shown once",
    )
    assert "token=" in link["url"] and link["sentTo"] is None
    token = parse_qs(urlsplit(link["url"]).query)["token"][0]
    done = _browser(s).post(
        "/oauth/password", data={"token": token, "password": FIRST, "repeat": FIRST}
    )
    assert done.status_code == 200, done.text[:300]
    _set_password(s, reviewer, FIRST)

    found = s.call(
        "GET",
        "/api/v1/users",
        query={"q": "reference", "pageSize": 2},
        status=200,
        record="search",
        summary="People whose name or e-mail address contains the text, in the order they were made",
    )
    assert {item["email"] for item in found["items"]} == {
        "editor@example.org",
        "reviewer@example.org",
    }
    s.call(
        "GET",
        "/api/v1/users/{user_id}",
        path={"user_id": editor["id"]},
        status=200,
        record="referenceEditor",
        summary="One person with the roles they hold and where",
    )
    editor = s.call(
        "PATCH",
        "/api/v1/users/{user_id}",
        path={"user_id": editor["id"]},
        body={"expectedVersion": editor["version"] + 1, "name": "Reference Editor (timetable)"},
        status=200,
        record="rename",
        summary="Change the person's name",
    )
    s.call(
        "PATCH",
        "/api/v1/users/{user_id}",
        path={"user_id": editor["id"]},
        body={"expectedVersion": 1, "name": "x"},
        status=409,
        code="VERSION_CONFLICT",
    )
    s.call(
        "PATCH",
        "/api/v1/users/{user_id}",
        path={"user_id": editor["id"]},
        body={"expectedVersion": editor["version"], "active": True, "email": None},
        status=422,
        code="EMAIL_REQUIRED",
    )

    # Groups and their members.
    team = s.call(
        "POST",
        "/api/v1/groups",
        body={"name": "Timetable team", "description": "People who edit the timetable"},
        status=201,
        record="timetableTeam",
        summary="A local group of people; a grant to it applies to its members",
    )
    assert team["members"] == 0 and team["source"] is None
    s.call(
        "POST",
        "/api/v1/groups",
        body={"name": "timetable TEAM"},
        status=409,
        code="GROUP_NAME_TAKEN",
    )
    s.call(
        "GET",
        "/api/v1/groups",
        query={"q": "timetable", "pageSize": 2},
        status=200,
        record="search",
        summary="Groups whose name contains the text, in the order they were made",
    )
    s.call(
        "GET",
        "/api/v1/groups/{group_id}",
        path={"group_id": team["id"]},
        status=200,
        record="timetableTeam",
        summary="One group with its member count",
    )
    team = s.call(
        "PATCH",
        "/api/v1/groups/{group_id}",
        path={"group_id": team["id"]},
        body={"expectedVersion": 1, "description": "People who edit the timetable and its stops"},
        status=200,
        record="describe",
        summary="Change the group's description",
    )
    s.call(
        "POST",
        "/api/v1/groups/{group_id}/members",
        path={"group_id": team["id"]},
        body={"userId": editor["id"]},
        status=201,
        record="addEditor",
        summary="Add one person; adding one already in the group changes nothing",
    )
    s.call(
        "POST",
        "/api/v1/groups/{group_id}/members",
        path={"group_id": team["id"]},
        body={"userId": "00000000-0000-4000-8000-00000000ffff"},
        status=404,
        code="USER_NOT_FOUND",
    )
    dry = s.call(
        "POST",
        "/api/v1/groups/{group_id}/members/batch",
        path={"group_id": team["id"]},
        body={"identifiers": ["Reviewer@Example.org"], "dryRun": True},
        status=200,
    )
    assert dry["items"][0]["outcome"] == "toAdd" and dry["changed"] == 0
    batch = s.call(
        "POST",
        "/api/v1/groups/{group_id}/members/batch",
        path={"group_id": team["id"]},
        body={
            "userIds": [editor["id"]],
            "identifiers": ["Reviewer@Example.org", "nobody@example.org"],
        },
        status=200,
        record="threeInputs",
        summary="Add several people at once: one already in, one by e-mail address, one nobody has",
    )
    assert [item["outcome"] for item in batch["items"]] == ["alreadyMember", "added", "notFound"]
    members = s.call(
        "GET",
        "/api/v1/groups/{group_id}/members",
        path={"group_id": team["id"]},
        query={"pageSize": 2},
        status=200,
        record="firstPage",
        summary="The group's members in the order they were made",
    )
    assert len(members["items"]) == 2
    removed = s.call(
        "POST",
        "/api/v1/groups/{group_id}/members/removal",
        path={"group_id": team["id"]},
        body={"userIds": [reviewer["id"]]},
        status=200,
        record="removeReviewer",
        summary="Take several people out at once",
    )
    assert removed["items"][0]["outcome"] == "removed" and removed["changed"] == 1
    s.call(
        "POST",
        "/api/v1/groups/{group_id}/members",
        path={"group_id": team["id"]},
        body={"userId": reviewer["id"]},
        status=201,
    )
    s.call(
        "DELETE",
        "/api/v1/groups/{group_id}/members/{user_id}",
        path={"group_id": team["id"], "user_id": reviewer["id"]},
        status=204,
        record="removeReviewer",
        summary="Take one person out of the group",
    )
    s.call(
        "DELETE",
        "/api/v1/groups/{group_id}/members/{user_id}",
        path={"group_id": team["id"], "user_id": reviewer["id"]},
        status=404,
        code="GROUP_MEMBER_NOT_FOUND",
    )
    spare_group = s.call("POST", "/api/v1/groups", body={"name": "Spare group"}, status=201)
    s.call(
        "DELETE",
        "/api/v1/groups/{group_id}",
        path={"group_id": spare_group["id"]},
        status=204,
        record="spareGroup",
        summary="Delete a group with its memberships and grants",
    )
    s.call(
        "GET",
        "/api/v1/groups/{group_id}",
        path={"group_id": spare_group["id"]},
        status=404,
        code="GROUP_NOT_FOUND",
    )

    # Grants.
    options = s.call(
        "GET",
        "/api/v1/workspaces/{workspace_key}/grant-options",
        path=GRAUBUENDEN,
        status=200,
        record="graubuenden",
        summary="What a grant in the workspace can name, from the workspace's model",
    )
    assert "network" in [item["key"] for item in options["applications"]]
    assert "stop" in [item["key"] for item in options["recordTypes"]]
    grant = s.call(
        "POST",
        "/api/v1/grants",
        body={
            "principal": {"kind": "group", "id": team["id"]},
            "role": "timetable-editor",
            "scope": {
                "workspaceKey": "graubuenden",
                "applications": ["network"],
                "recordTypes": ["stop"],
            },
        },
        status=201,
        record="teamEditsStops",
        summary="Give the group the role in one workspace, writes narrowed to stops of the network",
    )
    assert grant["stale"] is False and grant["scope"]["applications"] == ["network"]
    reader = s.call(
        "POST",
        "/api/v1/grants",
        body={
            "principal": {"kind": "user", "id": editor["id"]},
            "role": "reader",
            "scope": {"workspaceKey": "graubuenden"},
        },
        status=201,
    )
    for body, status, code in (
        (
            {
                "principal": {"kind": "user", "id": editor["id"]},
                "role": "reader",
                "scope": {"workspaceKey": "graubuenden", "applications": ["nothing"]},
            },
            422,
            "GRANT_SCOPE_UNKNOWN",
        ),
        (
            {
                "principal": {"kind": "user", "id": editor["id"]},
                "role": "reader",
                "scope": {"instance": True, "workspaceKey": "graubuenden"},
            },
            422,
            "GRANT_SCOPE_INVALID",
        ),
        (
            {
                "principal": {"kind": "user", "id": editor["id"]},
                "role": "security-admin",
                "scope": {"workspaceKey": "graubuenden"},
            },
            422,
            "GRANT_SCOPE_INVALID",
        ),
        (
            {
                "principal": {"kind": "user", "id": editor["id"]},
                "consumerApi": "stops",
                "scope": {"workspaceKey": "graubuenden"},
            },
            422,
            "CONSUMER_API_CLIENTS_ONLY",
        ),
        (
            {
                "principal": {"kind": "user", "id": editor["id"]},
                "role": "nobody",
                "scope": {"instance": True},
            },
            404,
            "ROLE_NOT_FOUND",
        ),
        (
            {
                "principal": {"kind": "client", "id": "00000000-0000-4000-8000-00000000ffff"},
                "role": "reader",
                "scope": {"instance": True},
            },
            404,
            "CLIENT_NOT_FOUND",
        ),
        (
            {
                "principal": {"kind": "user", "id": editor["id"]},
                "role": "reader",
                "scope": {"workspaceKey": "nowhere"},
            },
            404,
            "WORKSPACE_NOT_FOUND",
        ),
    ):
        s.call("POST", "/api/v1/grants", body=body, status=status, code=code)
    s.call(
        "DELETE",
        "/api/v1/roles/{role_key}",
        path={"role_key": "timetable-editor"},
        status=409,
        code="ROLE_IN_USE",
    )
    s.call(
        "GET",
        "/api/v1/grants",
        query={"workspaceKey": "graubuenden", "pageSize": 3},
        status=200,
        record="inTheWorkspace",
        summary="The grants made in one workspace, in the order they were made",
    )
    s.call(
        "GET",
        "/api/v1/users/{user_id}/grants",
        path={"user_id": editor["id"]},
        status=200,
        record="referenceEditor",
        summary="The person's grants: their own and their group's, which names the group",
    )
    s.call(
        "GET",
        "/api/v1/workspaces/{workspace_key}/access",
        path=GRAUBUENDEN,
        query={"pageSize": 3},
        status=200,
        record="graubuenden",
        summary="Every grant that applies in the workspace, made there or at the instance",
    )
    s.call(
        "DELETE",
        "/api/v1/grants/{grant_id}",
        path={"grant_id": reader["id"]},
        status=204,
        record="directReader",
        summary="Remove a grant; it stops applying on the person's next request",
    )
    s.call(
        "DELETE",
        "/api/v1/grants/{grant_id}",
        path={"grant_id": reader["id"]},
        status=404,
        code="GRANT_NOT_FOUND",
    )

    # The caller's own view.
    e = _person_calls(s, "editor@example.org", FIRST)
    me = e.call(
        "GET",
        "/api/v1/me",
        status=200,
        record="editor",
        summary="Who the token belongs to, and how they signed in",
    )
    assert me["kind"] == "user" and me["signedInWith"] == "password"
    permissions = e.call(
        "GET",
        "/api/v1/me/permissions",
        query={"workspaceKey": "graubuenden"},
        status=200,
        record="graubuenden",
        summary="What the person may do in the workspace, and the grants it comes from",
    )
    held = {item["key"]: item for item in permissions["actionGroups"]}
    assert held["edit-live"]["applications"] == ["network"]
    assert held["edit-live"]["sources"][0]["group"]["name"] == "Timetable team"
    e.call(
        "GET",
        "/api/v1/me/action-groups",
        status=200,
        record="heldAnywhere",
        summary="Every action group the person holds anywhere, for what the interface shows them",
    )
    e.call(
        "GET",
        "/api/v1/me/grants",
        query={"pageSize": 3},
        status=200,
        record="firstPage",
        summary="The person's grants; a group's grant names the group",
    )
    assert e.call("GET", "/api/v1/users", status=403, code="FORBIDDEN")


def test_a_person_looks_after_their_own_sign_in(security):
    """Sessions, password, authenticator app and passkeys of the signed-in person."""
    s = security
    e = _person_calls(s, "editor@example.org", FIRST)
    other = _person_calls(s, "editor@example.org", FIRST)
    listed = e.call(
        "GET",
        "/api/v1/me/sessions",
        query={"pageSize": 3},
        status=200,
        record="openSessions",
        summary="The open sessions of the person; `current` marks this one",
    )
    assert len(listed["items"]) >= 2
    here = e.call("GET", "/api/v1/me", status=200)["sessionId"]
    other_id = next(item["id"] for item in listed["items"] if item["id"] != here)
    e.call(
        "DELETE",
        "/api/v1/me/sessions/{session_id}",
        path={"session_id": other_id},
        status=204,
        record="otherSession",
        summary="Sign out another session of the person",
    )
    e.call(
        "DELETE",
        "/api/v1/me/sessions/{session_id}",
        path={"session_id": other_id},
        status=404,
        code="SESSION_NOT_FOUND",
    )
    assert other.api.token

    e.call(
        "POST",
        "/api/v1/me/password",
        body={"currentPassword": "not the password", "newPassword": SECOND},
        status=422,
        code="PASSWORD_INCORRECT",
    )
    e.call(
        "POST",
        "/api/v1/me/password",
        body={"currentPassword": FIRST, "newPassword": "short"},
        status=422,
        code="PASSWORD_REJECTED",
    )
    e.call(
        "POST",
        "/api/v1/me/password",
        body={"currentPassword": FIRST, "newPassword": SECOND},
        status=204,
        record="changePassword",
        summary="Change the password; every other session ends",
    )

    # An authenticator app, then the recovery codes.
    off = e.call(
        "GET",
        "/api/v1/me/second-factor",
        status=200,
        record="notSetUp",
        summary="No authenticator app yet",
    )
    assert off["enabled"] is False and off["required"] is False
    e.call(
        "POST",
        "/api/v1/me/second-factor/confirmation",
        body={"code": "123456"},
        status=404,
        code="SECOND_FACTOR_NOT_FOUND",
    )
    codes = _enrol(e, record=True)
    assert len(codes) == 10
    e.call(
        "POST",
        "/api/v1/me/second-factor",
        status=409,
        code="SECOND_FACTOR_EXISTS",
    )
    on = e.call(
        "GET",
        "/api/v1/me/second-factor",
        status=200,
        record="setUp",
        summary="The app is set up and ten recovery codes are left",
    )
    assert on["enabled"] is True and on["recoveryCodesLeft"] == 10
    e.call(
        "POST",
        "/api/v1/me/second-factor/recovery-codes",
        body={"code": "000000"},
        status=422,
        code="CODE_INCORRECT",
    )
    fresh = e.call(
        "POST",
        "/api/v1/me/second-factor/recovery-codes",
        body={"code": codes[0]},
        status=200,
        record="newCodes",
        summary="Ten new recovery codes, answered once; a recovery code proves it is the person",
        mask={
            "code": "abcd-efgh-0001",
            "recoveryCodes": [f"jklm-npqr-{n:04d}" for n in range(1, 11)],
        },
    )
    assert len(fresh["recoveryCodes"]) == 10
    e.call(
        "DELETE",
        "/api/v1/me/second-factor",
        body={"code": fresh["recoveryCodes"][0]},
        status=204,
        record="removeApp",
        summary="Remove the app with a recovery code",
        mask={"code": "jklm-npqr-0001"},
    )
    e.call(
        "DELETE",
        "/api/v1/me/second-factor",
        body={"code": "000000"},
        status=404,
        code="SECOND_FACTOR_NOT_FOUND",
    )

    # Passkeys: added on the engine's own page, listed, renamed and removed here.
    issuer = urlsplit(s.client.get("/.well-known/oauth-authorization-server").json()["issuer"])
    laptop = SoftwareAuthenticator(f"{issuer.scheme}://{issuer.netloc}")
    phone = SoftwareAuthenticator(f"{issuer.scheme}://{issuer.netloc}")
    browser = _signed_in_browser(s, "editor@example.org", SECOND)
    first = _add_passkey(browser, SECOND, laptop, "Laptop")
    second = _add_passkey(browser, SECOND, phone, "Phone")
    mine = e.call(
        "GET",
        "/api/v1/me/passkeys",
        query={"pageSize": 3},
        status=200,
        record="twoPasskeys",
        summary="The person's passkeys by the name they gave them; never the credential",
    )
    assert [item["name"] for item in mine["items"]] == ["Laptop", "Phone"]
    e.call(
        "PATCH",
        "/api/v1/me/passkeys/{passkey_id}",
        path={"passkey_id": first},
        body={"name": "Work laptop"},
        status=200,
        record="rename",
        summary="Rename a passkey",
    )
    e.call(
        "PATCH",
        "/api/v1/me/passkeys/{passkey_id}",
        path={"passkey_id": "00000000-0000-4000-8000-00000000ffff"},
        body={"name": "x"},
        status=404,
        code="PASSKEY_NOT_FOUND",
    )
    s.call(
        "GET",
        "/api/v1/users/{user_id}/passkeys",
        path={"user_id": e.call("GET", "/api/v1/me", status=200)["id"]},
        status=200,
        record="referenceEditor",
        summary="A person's passkeys, as an administrator reads them",
    )
    s.call(
        "DELETE",
        "/api/v1/users/{user_id}/passkeys/{passkey_id}",
        path={"user_id": e.call("GET", "/api/v1/me", status=200)["id"], "passkey_id": second},
        status=204,
        record="lostPhone",
        summary="An administrator removes a passkey for someone who lost the device",
    )
    e.call(
        "DELETE",
        "/api/v1/me/passkeys/{passkey_id}",
        path={"passkey_id": first},
        body={"proof": "wrong"},
        status=422,
        code="CODE_INCORRECT",
    )
    e.call(
        "DELETE",
        "/api/v1/me/passkeys/{passkey_id}",
        path={"passkey_id": first},
        body={"proof": SECOND},
        status=204,
        record="removeLaptop",
        summary="Remove the person's own passkey; the proof is their password or a code",
        mask={"proof": "example-password"},
    )

    # A second factor again, for an administrator to remove.
    _enrol(e)
    s.call(
        "DELETE",
        "/api/v1/users/{user_id}/second-factor",
        path={"user_id": e.call("GET", "/api/v1/me", status=200)["id"]},
        status=204,
        record="lostPhone",
        summary="An administrator removes the second factor of someone who lost the phone",
    )
    s.call(
        "DELETE",
        "/api/v1/users/{user_id}/second-factor",
        path={"user_id": e.call("GET", "/api/v1/me", status=200)["id"]},
        status=404,
        code="SECOND_FACTOR_NOT_FOUND",
    )
    # A person with sign-in managed by an administrator changes none of it.
    s.call(
        "GET",
        "/api/v1/security-events",
        query={"aggregateType": ["user"], "pageSize": 3},
        status=200,
        record="userEvents",
        summary="Changes to people and their sign-ins, newest first, each naming who made it",
    )
    s.call(
        "GET",
        "/api/v1/security-events",
        query={"aggregateType": ["no-such-kind"]},
        status=422,
        code="REQUEST_VALIDATION_ERROR",
    )
    # Sign the reviewer out everywhere, then the editor. First an administrator takes the reviewer's
    # sign-in into their own hands: they then change none of their credentials or other sessions.
    r = _person_calls(s, "reviewer@example.org", FIRST)
    reviewer = s.call("GET", "/api/v1/users", query={"q": "reviewer@"}, status=200)["items"][0]
    managed = s.call(
        "PATCH",
        "/api/v1/users/{user_id}",
        path={"user_id": reviewer["id"]},
        body={"expectedVersion": reviewer["version"], "signInManaged": True},
        status=200,
    )
    assert managed["signInManaged"] is True
    r.call(
        "POST",
        "/api/v1/me/password",
        body={"currentPassword": FIRST, "newPassword": SECOND},
        status=403,
        code="SIGN_IN_MANAGED",
    )
    r.call("POST", "/api/v1/me/second-factor", status=403, code="SIGN_IN_MANAGED")
    r.call(
        "DELETE",
        "/api/v1/me/sessions/{session_id}",
        path={"session_id": "00000000-0000-4000-8000-00000000ffff"},
        status=403,
        code="SIGN_IN_MANAGED",
    )
    r.call("DELETE", "/api/v1/me/sessions", status=403, code="SIGN_IN_MANAGED")
    assert len(r.call("GET", "/api/v1/me/sessions", status=200)["items"]) == 1
    s.call(
        "PATCH",
        "/api/v1/users/{user_id}",
        path={"user_id": reviewer["id"]},
        body={"expectedVersion": managed["version"], "signInManaged": False},
        status=200,
    )
    r.call(
        "DELETE",
        "/api/v1/me/sessions",
        status=204,
        record="signOutEverywhere",
        summary="Sign out everywhere, this session included",
    )
    s.call(
        "DELETE",
        "/api/v1/users/{user_id}/sessions",
        path={"user_id": e.call("GET", "/api/v1/me", status=200)["id"]},
        status=204,
        record="editorEverywhere",
        summary="An administrator signs a person out everywhere",
    )


def test_a_client_signs_in_and_its_secret_is_rotated(security):
    """Clients, their secrets, the token endpoint and the signing keys."""
    s = security
    client = s.call(
        "POST",
        "/api/v1/clients",
        body={"name": "Timetable export", "kind": "api"},
        status=201,
        record="timetableExport",
        summary="A client and its first secret, shown once",
        mask=SECRET_PLACEHOLDER,
    )
    assert client["secret"] and client["active"] is True and len(client["secrets"]) == 1
    s.call(
        "POST",
        "/api/v1/clients",
        body={"name": "x", "kind": "session"},
        status=422,
        code="REQUEST_VALIDATION_ERROR",
    )
    s.call(
        "GET",
        "/api/v1/clients",
        query={"q": "export", "kind": "api", "pageSize": 2},
        status=200,
        record="search",
        summary="API clients whose name contains the text",
    )
    s.call(
        "GET",
        "/api/v1/clients/{client_id}",
        path={"client_id": client["id"]},
        status=200,
        record="timetableExport",
        summary="One client with its valid secrets, never their values",
    )
    s.call(
        "GET",
        "/api/v1/clients/{client_id}",
        path={"client_id": "00000000-0000-4000-8000-00000000ffff"},
        status=404,
        code="CLIENT_NOT_FOUND",
    )
    renamed = s.call(
        "PATCH",
        "/api/v1/clients/{client_id}",
        path={"client_id": client["id"]},
        body={"expectedVersion": client["version"], "name": "Timetable export job"},
        status=200,
        record="rename",
        summary="Rename a client",
    )
    s.call(
        "PATCH",
        "/api/v1/clients/{client_id}",
        path={"client_id": client["id"]},
        body={"expectedVersion": client["version"], "name": "x"},
        status=409,
        code="VERSION_CONFLICT",
    )
    rotated = s.call(
        "POST",
        "/api/v1/clients/{client_id}/secrets",
        path={"client_id": client["id"]},
        body={"expectedVersion": renamed["version"], "overlapHours": 24},
        status=201,
        record="rotation",
        summary="A new secret; the old one stays valid for the overlap",
        mask=SECRET_PLACEHOLDER,
    )
    assert len(rotated["secrets"]) == 2 and rotated["secret"]
    token = s.call(
        "POST",
        "/oauth/token",
        form={"grant_type": "client_credentials", "scope": "management"},
        headers=_basic(client["id"], rotated["secret"]),
        status=200,
        signed_in=False,
        record="clientCredentials",
        summary="A client signs in with its ID and secret and gets an access token",
        notes=[
            (
                "The request is a form, `grant_type=client_credentials&scope=management`, with "
                "the client's ID and secret as HTTP Basic credentials."
            )
        ],
        mask={"access_token": "example-access-token"},
    )
    assert token["token_type"] == "Bearer" and token["expires_in"] > 0
    me = s.client.get("/api/v1/me", headers=_bearer(token["access_token"]))
    assert me.status_code == 200 and me.json()["kind"] == "client"
    nope = s.client.get("/api/v1/me/sessions", headers=_bearer(token["access_token"]))
    assert nope.status_code == 403 and nope.json()["error"]["code"] == "NOT_A_PERSON"
    s.call(
        "POST",
        "/api/v1/grants",
        body={
            "principal": {"kind": "client", "id": client["id"]},
            "consumerApi": "stops",
            "scope": {"workspaceKey": "graubuenden"},
        },
        status=201,
    )
    removed = s.call(
        "DELETE",
        "/api/v1/clients/{client_id}/secrets/{secret_id}",
        path={"client_id": client["id"], "secret_id": client["secretId"]},
        status=200,
        record="stopTheOldSecret",
        summary="Stop the first secret at once, before its overlap ends",
    )
    assert len(removed["secrets"]) == 1
    s.call(
        "DELETE",
        "/api/v1/clients/{client_id}/secrets/{secret_id}",
        path={"client_id": client["id"], "secret_id": client["secretId"]},
        status=404,
        code="CLIENT_SECRET_NOT_FOUND",
    )
    wrong = s.client.post(
        "/oauth/token",
        data={"grant_type": "client_credentials"},
        headers=_basic(client["id"], client["secret"]),
    )
    assert wrong.status_code == 401 and wrong.json()["error"] == "invalid_client"

    keys = s.call(
        "GET",
        "/api/v1/token-signing-keys",
        query={"pageSize": 3},
        status=200,
        record="firstPage",
        summary="The keys that sign access tokens, newest first; never a private key",
    )
    assert keys["items"][0]["state"] == "current"
    rotation = s.call(
        "POST",
        "/api/v1/token-signing-keys/rotation",
        body={"immediate": False},
        status=201,
        record="rotate",
        summary="A new signing key; the previous one accepts the tokens it signed until they expire",
    )
    assert rotation["state"] == "current"
    s.call(
        "GET",
        "/api/v1/security-events",
        query={"aggregateType": ["client"], "pageSize": 3},
        status=200,
        record="clientEvents",
        summary="Changes to clients and their secrets, newest first",
    )
    s.call(
        "GET",
        "/oauth/jwks",
        status=200,
        signed_in=False,
        record="published",
        summary="The public keys that verify access tokens now",
        mask={
            "x": "example-public-value",
            "y": "example-public-value",
            "n": "example-public-value",
        },
    )
    metadata = s.call(
        "GET",
        "/.well-known/oauth-authorization-server",
        status=200,
        signed_in=False,
        record="metadata",
        summary="The authorization server's endpoints and what it supports",
    )
    assert metadata["token_endpoint"].endswith("/oauth/token")
    # Revoking a refresh token signs the session out.
    browser = _signed_in_browser(s, "reviewer@example.org", FIRST)
    revoked = browser.post("/oauth/revoke")
    assert revoked.status_code == 200
    s._record(
        "POST",
        "/oauth/revoke",
        "signOut",
        "A browser signs its session out with the refresh cookie it holds",
        {},
        {},
        None,
        200,
        None,
        [
            (
                "The request is a form with an optional `token` (a refresh token); without it "
                "the browser's cookie is used. An unknown token answers the same."
            )
        ],
    )


def test_the_organisations_sign_in_provider_is_connected(security):
    """Sign-in providers, local sign-in and linking a provider identity to a person."""
    s = security
    with OidcProvider(client_id="reference-engine", client_secret="example-client-secret") as idp:
        provider = s.call(
            "POST",
            "/api/v1/sign-in-providers",
            body={
                "key": "company-sso",
                "name": "Company SSO",
                "issuer": idp.issuer,
                "clientId": idp.client_id,
                "clientSecret": idp.client_secret,
                "groupsClaim": "groups",
                "enabled": True,
            },
            status=201,
            record="companySso",
            summary="Connect an OpenID Connect provider; it is read first, and its secret is never answered",
        )
        assert provider["clientSecretSet"] is True and "clientSecret" not in provider
        s.call(
            "POST",
            "/api/v1/sign-in-providers",
            body={
                "key": "company-sso",
                "name": "Again",
                "issuer": idp.issuer,
                "clientId": "x",
                "clientSecret": "x",
            },
            status=409,
            code="SIGN_IN_PROVIDER_KEY_TAKEN",
        )
        s.call(
            "POST",
            "/api/v1/sign-in-providers",
            body={
                "key": "nowhere-sso",
                "name": "Nowhere",
                "issuer": "http://127.0.0.1:9",
                "clientId": "x",
                "clientSecret": "x",
            },
            status=422,
            code="SIGN_IN_PROVIDER_UNREACHABLE",
        )
        s.call(
            "GET",
            "/api/v1/sign-in-providers",
            query={"pageSize": 2},
            status=200,
            record="firstPage",
            summary="The providers as created, never a secret",
        )
        s.call(
            "GET",
            "/api/v1/sign-in-providers/{key}",
            path={"key": "company-sso"},
            status=200,
            record="companySso",
            summary="One provider with the address to register with it",
        )
        s.call(
            "GET",
            "/api/v1/sign-in-providers/{key}",
            path={"key": "nobody"},
            status=404,
            code="SIGN_IN_PROVIDER_NOT_FOUND",
        )
        s.call(
            "PATCH",
            "/api/v1/sign-in-providers/{key}",
            path={"key": "company-sso"},
            body={"expectedVersion": provider["version"], "name": "Company single sign-on"},
            status=200,
            record="rename",
            summary="Change the button's name; the saved secret stays",
        )
        s.call(
            "PATCH",
            "/api/v1/sign-in-providers/{key}",
            path={"key": "company-sso"},
            body={"expectedVersion": provider["version"], "issuer": "https://other.example.org"},
            status=422,
            code="SIGN_IN_PROVIDER_SECRET_REQUIRED",
        )
        spare = s.call(
            "POST",
            "/api/v1/sign-in-providers",
            body={
                "key": "spare-sso",
                "name": "Spare",
                "issuer": "https://spare.example.org",
                "clientId": "spare",
                "clientSecret": "example-client-secret",
                "enabled": False,
            },
            status=201,
        )
        s.call(
            "DELETE",
            "/api/v1/sign-in-providers/{key}",
            path={"key": spare["key"]},
            status=204,
            record="unusedProvider",
            summary="Delete a provider nobody has signed in with",
        )

        s.call(
            "PATCH",
            "/api/v1/sign-in-providers/local",
            body={"expectedVersion": 1, "enabled": False},
            status=409,
            code="NO_WORKING_PROVIDER",
        )
        # Someone signs in through the provider, and is then linked to the person who had an account.
        staff = s.call(
            "POST",
            "/api/v1/groups",
            body={"name": "Staff", "source": {"provider": "company-sso", "claimValue": "staff"}},
            status=201,
        )
        assert staff["source"]["provider"]["key"] == "company-sso"
        s.call(
            "POST",
            "/api/v1/groups",
            body={
                "name": "Staff again",
                "source": {"provider": "company-sso", "claimValue": "staff"},
            },
            status=409,
            code="GROUP_CLAIM_TAKEN",
        )
        s.call(
            "POST",
            "/api/v1/groups/{group_id}/members",
            path={"group_id": staff["id"]},
            body={"userId": s.call("GET", "/api/v1/me", status=200)["id"]},
            status=409,
            code="GROUP_FROM_PROVIDER",
        )
        _through_provider(
            s,
            idp,
            "company-sso",
            sub="sso-1",
            name="Reference Editor",
            email="editor.sso@example.org",
            preferred_username="editor.sso",
            groups=["staff"],
        )
        made = s.call("GET", "/api/v1/users", query={"q": "editor.sso"}, status=200)["items"][0]
        assert made["identities"][0]["provider"]["key"] == "company-sso"
        editor = s.call("GET", "/api/v1/users", query={"q": "editor@example.org"}, status=200)[
            "items"
        ][0]
        linked = s.call(
            "POST",
            "/api/v1/users/{user_id}/identities",
            path={"user_id": editor["id"]},
            body={"expectedVersion": editor["version"], "fromUserId": made["id"]},
            status=200,
            record="linkSso",
            summary="Move the identity a provider sign-in made onto the person who had an account",
        )
        assert [i["subject"] for i in linked["identities"]] == ["sso-1"]
        s.call(
            "POST",
            "/api/v1/users/{user_id}/identities",
            path={"user_id": editor["id"]},
            body={"expectedVersion": linked["version"], "fromUserId": editor["id"]},
            status=422,
            code="LINK_SAME_PERSON",
        )
        s.call(
            "POST",
            "/api/v1/users/{user_id}/identities",
            path={"user_id": editor["id"]},
            body={"expectedVersion": linked["version"], "fromUserId": made["id"]},
            status=409,
            code="NO_IDENTITY_TO_LINK",
        )
        s.call(
            "POST",
            "/api/v1/users/{user_id}/identities",
            path={"user_id": made["id"]},
            body={"expectedVersion": 1, "fromUserId": editor["id"]},
            status=409,
            code="LINK_TARGET_DEACTIVATED",
        )
        s.call(
            "DELETE",
            "/api/v1/sign-in-providers/{key}",
            path={"key": "company-sso"},
            status=409,
            code="SIGN_IN_PROVIDER_IN_USE",
        )
        s.call(
            "DELETE",
            "/api/v1/users/{user_id}/identities/{provider}",
            path={"user_id": editor["id"], "provider": "company-sso"},
            status=204,
            record="unlinkSso",
            summary="Undo a link: the next sign-in with the provider makes a new person",
        )
        s.call(
            "DELETE",
            "/api/v1/users/{user_id}/identities/{provider}",
            path={"user_id": editor["id"], "provider": "company-sso"},
            status=404,
            code="IDENTITY_NOT_FOUND",
        )

    local = s.call(
        "GET",
        "/api/v1/sign-in-providers/local",
        status=200,
        record="passwordOn",
        summary="Whether people sign in with a password, and whether it needs a second factor",
    )
    assert local["enabled"] is True and local["secondFactorRequired"] is False
    required = s.call(
        "PATCH",
        "/api/v1/sign-in-providers/local",
        body={"expectedVersion": local["version"], "secondFactorRequired": True},
        status=200,
        record="requireSecondFactor",
        summary="Require a second factor with a password",
    )
    assert required["secondFactorRequired"] is True
    s.call(
        "PATCH",
        "/api/v1/sign-in-providers/local",
        body={"expectedVersion": local["version"], "secondFactorRequired": False},
        status=409,
        code="VERSION_CONFLICT",
    )
    s.call(
        "PATCH",
        "/api/v1/sign-in-providers/local",
        body={"expectedVersion": required["version"], "secondFactorRequired": False},
        status=200,
    )


def test_an_assistant_reaches_the_engine_through_agent_access(security):
    """Agent clients, registered assistants, the calls through ``/mcp`` and the discovery endpoints."""
    s = security
    status = s.call(
        "GET",
        "/api/v1/agent-access",
        status=200,
        record="enabled",
        summary="Whether assistants can reach the instance, where and under which limits",
    )
    assert status["enabled"] is True and status["url"].endswith("/mcp")
    agent = s.call(
        "POST",
        "/api/v1/clients",
        body={"name": "Reporting assistant", "kind": "agent"},
        status=201,
        mask=SECRET_PLACEHOLDER,
    )
    s.call(
        "POST",
        "/api/v1/grants",
        body={
            "principal": {"kind": "client", "id": agent["id"]},
            "role": "agent",
            "scope": {"workspaceKey": "graubuenden"},
        },
        status=201,
    )
    token = s.call(
        "POST",
        "/oauth/token",
        form={"grant_type": "client_credentials", "scope": "agent"},
        headers=_basic(agent["id"], agent["secret"]),
        status=200,
        signed_in=False,
    )
    assert token["scope"] == "agent"
    used = _call_tool(s, token["access_token"], "list_workspaces")
    assert not used.isError
    s.call(
        "GET",
        "/api/v1/agent-access/clients",
        query={"pageSize": 2},
        status=200,
        record="firstPage",
        summary="The agent clients with their calls of the last 30 days",
    )
    calls = s.call(
        "GET",
        "/api/v1/agent-access/calls",
        query={"pageSize": 2},
        status=200,
        record="firstPage",
        summary="Each tool call through /mcp, newest first; the names of its arguments, never their values",
    )
    assert calls["items"][0]["principalKind"] == "client"
    every = s.call("GET", "/api/v1/agent-access/calls", query={"pageSize": 10}, status=200)
    assert "list_workspaces" in {item["tool"] for item in every["items"]}

    s.call(
        "GET",
        "/.well-known/oauth-protected-resource",
        status=200,
        signed_in=False,
        record="resource",
        summary="The MCP endpoint as a protected resource, and the server that signs assistants in",
    )
    s.call(
        "GET",
        "/.well-known/oauth-protected-resource/mcp",
        status=200,
        signed_in=False,
        record="resource",
        summary="The same document at the address derived from /mcp",
    )
    registered = s.call(
        "POST",
        "/oauth/register",
        body={"client_name": "Claude Code", "redirect_uris": [ASSISTANT_CALLBACK]},
        status=201,
        signed_in=False,
        record="localAssistant",
        summary="An assistant registers itself as a public client that returns to this computer",
        mask={"client_id_issued_at": 1793610000},
    )
    assert registered["token_endpoint_auth_method"] == "none"
    refused = s.client.post(
        "/oauth/register", json={"client_name": "x", "redirect_uris": ["https://example.org/x"]}
    )
    assert refused.status_code == 400 and refused.json()["error"] == "invalid_redirect_uri"
    made = s.call(
        "POST",
        "/api/v1/agent-access/applications",
        body={
            "name": "Planning assistant",
            "redirectUris": ["https://assistant.example.org/callback"],
        },
        status=201,
        record="planningAssistant",
        summary="Register an assistant that may return to an exact HTTPS address",
    )
    assert made["source"] == "administrator" and made["blocked"] is False
    s.call(
        "POST",
        "/api/v1/agent-access/applications",
        body={"name": "Plain http", "redirectUris": ["http://example.org/callback"]},
        status=422,
        code="AGENT_APPLICATION_INVALID",
    )
    s.call(
        "GET",
        "/api/v1/agent-access/applications",
        query={"pageSize": 2},
        status=200,
        record="firstPage",
        summary="The assistants people sign in with, in the order they were registered",
    )
    blocked = s.call(
        "POST",
        "/api/v1/agent-access/applications/{application_id}/block",
        path={"application_id": made["id"]},
        status=200,
        record="planningAssistant",
        summary="Block an assistant: no one signs in with it and its sessions end",
    )
    assert blocked["blocked"] is True
    restored = s.call(
        "POST",
        "/api/v1/agent-access/applications/{application_id}/restore",
        path={"application_id": made["id"]},
        status=200,
        record="planningAssistant",
        summary="People may sign in with it again",
    )
    assert restored["blocked"] is False
    s.call(
        "POST",
        "/api/v1/agent-access/applications/{application_id}/block",
        path={"application_id": "00000000-0000-4000-8000-00000000ffff"},
        status=404,
        code="AGENT_APPLICATION_NOT_FOUND",
    )
