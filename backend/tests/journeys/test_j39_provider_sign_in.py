"""J39.7, J40 — a person signs in through the organisation's provider (USER_JOURNEYS.md § Security,
0.12 I3).

The sign-in page's button starts a sign-in at the provider; the provider sends the browser back to
the engine, which checks its answer and ends as the password form does, with a one-time code for
the browser. The person is found or created by the provider and the token's subject; the provider's
groups become provider groups. Local sign-in can be turned off once a provider has worked, keeping
the administrators made on the server. Every case runs on two configurations through the public
API, with the harness provider (``tests/oidc_provider.py``) and a plain HTTP client keeping the
browser's cookies.
"""

import os
import subprocess
import sys
from urllib.parse import urlsplit

import pytest
from oidc_provider import OidcProvider
from scenario import W1, ok, refused
from service import BACKEND, render
from test_j39_sign_in import (
    PASSWORD,
    _bearer,
    _browser,
    _code,
    _exchange,
    _person,
    _pkce,
    _post_form,
    _request,
)


@pytest.fixture
def idp():
    with OidcProvider() as provider:
        yield provider


def _provider(world, idp: OidcProvider, key: str = "harness", **changes) -> dict:
    body = {
        "key": key,
        "name": "Harness ID",
        "issuer": idp.issuer,
        "clientId": idp.client_id,
        "clientSecret": idp.client_secret,
        "groupsClaim": "groups",
        "enabled": True,
        **changes,
    }
    return ok(world.api.post("/sign-in-providers", body), 201)


def _start(browser, key: str, challenge: str):
    return browser.get(
        f"/oauth/providers/{key}/start", params=_request(challenge), follow_redirects=False
    )


def _back(browser, address: str):
    """The provider's redirect, followed by the browser to the engine's callback."""
    parts = urlsplit(address)
    return browser.get(f"{parts.path}?{parts.query}", follow_redirects=False)


def _through(browser, idp: OidcProvider, key: str = "harness", **person):
    """A sign-in through the provider as ``person``; the engine's answer at the callback and the
    browser's PKCE verifier."""
    verifier, challenge = _pkce()
    started = _start(browser, key, challenge)
    assert started.status_code == 303, f"{started.status_code}: {started.text[:300]}"
    return _back(browser, idp.sign_in(started.headers["location"], **person)), verifier


def _signed_in(world, idp: OidcProvider, key: str = "harness", **person) -> str:
    """A new browser signed in through the provider; its access token."""
    browser = _browser(world)
    answer, verifier = _through(browser, idp, key, **person)
    return ok(_exchange(browser, _code(answer), verifier))["access_token"]


def _cannot(answer, text: str) -> None:
    """The engine's page saying the provider could not sign the person in, and no code."""
    assert answer.status_code in (400, 403), f"{answer.status_code}: {answer.text[:300]}"
    assert "location" not in answer.headers
    assert "could not sign you in" in answer.text and text in answer.text, answer.text


def _failures(world) -> list[dict]:
    events = ok(world.api.get("/security-events", aggregateType="sign-in"))["items"]
    return [event for event in events if event["action"] == "failed"]


def _group_by_claim(world, value: str) -> dict:
    groups = ok(world.api.get("/groups", pageSize=500))["items"]
    return next(g for g in groups if g["source"] and g["source"]["claimValue"] == value)


def _members(world, group: dict) -> list[str]:
    return [m["name"] for m in ok(world.api.get(f"/groups/{group['id']}/members"))["items"]]


def _create_admin(world, username: str):
    return subprocess.run(
        [sys.executable, "-m", "app.cli.create_admin", "--username", username, "--name",
         username.title(), "--password-stdin"],
        input=PASSWORD + "\n",
        cwd=BACKEND,
        env={**os.environ, "DATABASE_URL": render(world.database)},
        capture_output=True,
        text=True,
        timeout=60,
        check=True,
    )  # fmt: skip


PAT = {"sub": "p-1", "name": "Pat Provider", "email": "pat@example.org"}


@pytest.mark.journey("J39")
def test_a_first_and_a_second_sign_in_through_a_provider(world, idp):
    """Given a provider with the groups claim. When a person the engine has never seen signs in
    through it with groups g1 and g2, then the browser gets a code that gives a session, `/me`
    answers `signedInWith` the provider's key, the person exists with the provider's identity and
    no password, and two provider groups hold them; when they sign in again with g2 only and a new
    name, then the same person is found, renamed, and a member of g2 only."""
    provider = _provider(world, idp)
    assert "clientSecret" not in provider and provider["clientSecretSet"] is True
    assert provider["redirectUri"].endswith("/oauth/providers/harness/callback")
    page = _browser(world).get("/oauth/authorize", params=_request(_pkce()[1]))
    assert "Continue with Harness ID" in page.text and 'name="password"' in page.text

    token = _signed_in(world, idp, **PAT, preferred_username="pat", groups=["g1", "g2"])
    me = ok(world.api.client.get("/api/v1/me", headers=_bearer(token)))
    assert me["signedInWith"] == "harness"
    assert me["signInProvider"] == {"key": "harness", "name": "Harness ID"}
    person = ok(world.api.get(f"/users/{me['id']}"))
    assert (person["username"], person["name"], person["email"]) == (
        "pat", "Pat Provider", "pat@example.org")  # fmt: skip
    assert person["hasPassword"] is False and person["localKept"] is False
    assert person["identities"] == [
        {"provider": {"key": "harness", "name": "Harness ID"}, "subject": "p-1"}
    ]
    g1, g2 = _group_by_claim(world, "g1"), _group_by_claim(world, "g2")
    assert g1["source"]["provider"] == {"key": "harness", "name": "Harness ID"}
    assert _members(world, g1) == _members(world, g2) == ["Pat Provider"]
    seen = ok(world.api.get(f"/groups/{g1['id']}/members"))["items"][0]["seenAt"]
    assert seen is not None

    _signed_in(
        world, idp, **{**PAT, "name": "Pat Renamed"}, preferred_username="pat", groups=["g2"]
    )
    again = ok(world.api.get(f"/users/{me['id']}"))
    assert again["name"] == "Pat Renamed" and again["username"] == "pat"
    assert _members(world, g1) == [] and _members(world, g2) == ["Pat Renamed"]
    assert ok(world.api.get("/users", q="pat"))["items"] == [again]
    assert ok(world.api.get("/sign-in-providers/harness"))["people"] == 1


@pytest.mark.journey("J40")
@pytest.mark.structures("R")
def test_a_provider_group_granted_ahead(world, idp):
    """Given a provider group made ahead for `staff` and granted Reader in the workspace. When a
    person signs in with `staff`, then they read the workspace's records and a live write is
    refused; signed in again without `staff`, their next read is refused. Adding a member to the
    group through the API answers `409 GROUP_FROM_PROVIDER`."""
    _provider(world, idp)
    group = ok(
        world.api.post(
            "/groups", {"name": "Staff", "source": {"provider": "harness", "claimValue": "staff"}}
        ),
        201,
    )
    assert group["source"]["claimValue"] == "staff" and group["members"] == 0
    duplicate = {"name": "Other", "source": {"provider": "harness", "claimValue": "staff"}}
    refused(world.api.post("/groups", duplicate), 409, "GROUP_CLAIM_TAKEN")
    grant = {"principal": {"kind": "group", "id": group["id"]}, "role": "reader"}
    ok(world.api.post("/grants", {**grant, "scope": {"workspaceKey": W1}}), 201)

    token = _signed_in(world, idp, sub="s-1", name="Sam Staff", groups=["staff"])
    ok(world.api.client.get(f"/api/v1/objects/{world.key('R')}", params={"workspaceKey": W1},
                            headers=_bearer(token)))  # fmt: skip
    refused(world.create("R", "Not by a reader", headers=_bearer(token)), 403, "FORBIDDEN")
    member = ok(world.api.get(f"/groups/{group['id']}/members"))["items"][0]
    refused(
        world.api.post(f"/groups/{group['id']}/members", {"userId": member["id"]}),
        409,
        "GROUP_FROM_PROVIDER",
    )
    refused(world.api.delete(f"/groups/{group['id']}/members/{member['id']}"), 409,
            "GROUP_FROM_PROVIDER")  # fmt: skip

    later = _signed_in(world, idp, sub="s-1", name="Sam Staff", groups=[])
    gone = world.api.client.get(f"/api/v1/objects/{world.key('R')}", params={"workspaceKey": W1},
                                headers=_bearer(later))  # fmt: skip
    refused(gone, 403, "FORBIDDEN")


@pytest.mark.journey("J39")
def test_provider_sign_ins_that_cannot_finish(world, idp):
    """The callback with an unknown state, a used state and another browser's cookie each shows the
    engine's page without a code; the provider answering another issuer, a wrong nonce or another
    audience, or `access_denied`, is refused; a deactivated person is refused; a disabled
    provider's start is refused. Each is a `sign-in` `failed` security event with its reason."""
    provider = _provider(world, idp)
    browser = _browser(world)
    answer, _ = _through(browser, idp, **PAT)
    assert answer.status_code == 303
    callback = urlsplit(str(answer.request.url))
    used = browser.get(f"{callback.path}?{callback.query}", follow_redirects=False)
    _cannot(used, "already used")
    _cannot(browser.get("/oauth/providers/harness/callback?state=nothing&code=x"), "already used")

    challenge = _pkce()[1]
    started = _start(browser, "harness", challenge)
    back = idp.sign_in(started.headers["location"], **PAT)
    _cannot(_back(_browser(world), back), "another browser")

    for mode, text in (
        ("issuer", "could not confirm"),
        ("nonce", "could not confirm"),
        ("audience", "could not confirm"),
        ("error", "access_denied"),
    ):
        idp.misbehave = mode
        _cannot(_through(_browser(world), idp, **PAT)[0], text)
    idp.misbehave = None

    person = next(u for u in ok(world.api.get("/users", q="Pat"))["items"])
    ok(world.api.patch(f"/users/{person['id']}", {"expectedVersion": person["version"],
                                                 "active": False}))  # fmt: skip
    _cannot(_through(_browser(world), idp, **PAT)[0], "deactivated")

    ok(world.api.patch("/sign-in-providers/harness",
                       {"expectedVersion": provider["version"], "enabled": False}))  # fmt: skip
    _cannot(_start(_browser(world), "harness", _pkce()[1]), "turned off")
    reasons = [event["details"]["reason"] for event in _failures(world)]
    for reason in ("used", "unknown", "browser", "issuer", "nonce", "audience", "provider",
                   "deactivated", "disabled"):  # fmt: skip
        assert reason in reasons, (reason, reasons)
    assert all(e["details"]["provider"] == "harness" for e in _failures(world))


@pytest.mark.journey("J39")
def test_a_provider_that_names_its_issuer_on_the_way_back(world, idp):
    """Given a provider whose redirect carries `iss` and a `session_state` (as Keycloak's does).
    When a person signs in through it, then the extra parameters are ignored and a session starts;
    when the redirect's `iss` is another provider's, then the engine's page refuses it with no
    code, no person is created, and a `sign-in` `failed` event says `issuer`."""
    _provider(world, idp)
    idp.send_extra_parameters = True
    token = _signed_in(world, idp, **PAT)
    me = ok(world.api.client.get("/api/v1/me", headers=_bearer(token)))
    assert me["signedInWith"] == "harness"

    idp.misbehave = "redirect-issuer"
    _cannot(_through(_browser(world), idp, sub="p-2", name="Quinn", email="q@example.org")[0],
            "could not confirm")  # fmt: skip
    idp.misbehave = None
    assert [u["name"] for u in ok(world.api.get("/users", q="Quinn"))["items"]] == []
    assert [e["details"]["reason"] for e in _failures(world)] == ["issuer"]


@pytest.mark.journey("J39")
def test_local_sign_in_off(world, idp):
    """Turning local sign-in off with no working provider answers `409 NO_WORKING_PROVIDER`; after
    a provider sign-in it is turned off; then a local person's password is refused, a person made
    by `create_admin` signs in, a password link for the local person answers
    `409 LOCAL_SIGN_IN_OFF`, and the sign-in page lists the provider and the administrator's link;
    turned on again, the local person signs in."""
    local_person = _person(world, "lou")
    _create_admin(world, "kept")
    local = ok(world.api.get("/sign-in-providers/local"))
    assert local["enabled"] is True and local["keptPeople"] >= 1
    off = {"expectedVersion": local["version"], "enabled": False}
    refused(world.api.patch("/sign-in-providers/local", off), 409, "NO_WORKING_PROVIDER")
    _provider(world, idp)
    refused(world.api.patch("/sign-in-providers/local", off), 409, "NO_WORKING_PROVIDER")
    _signed_in(world, idp, **PAT)
    local = ok(world.api.patch("/sign-in-providers/local", off))
    assert local["enabled"] is False

    challenge = _pkce()[1]
    page = _browser(world).get("/oauth/authorize", params=_request(challenge))
    assert "Continue with Harness ID" in page.text and 'name="password"' not in page.text
    assert "Sign in with a local administrator account" in page.text
    form = _browser(world).get("/oauth/authorize", params={**_request(challenge), "local": "1"})
    assert 'name="password"' in form.text
    assert _post_form(_browser(world), "lou", PASSWORD, challenge).status_code == 401
    kept = _post_form(_browser(world), "kept", PASSWORD, challenge)
    assert kept.status_code == 303
    refused(world.api.post(f"/users/{local_person['id']}/password-reset", {}), 409,
            "LOCAL_SIGN_IN_OFF")  # fmt: skip

    on = {"expectedVersion": local["version"], "enabled": True}
    ok(world.api.patch("/sign-in-providers/local", on))
    assert _post_form(_browser(world), "lou", PASSWORD, challenge).status_code == 303


@pytest.mark.journey("J40")
def test_a_providers_settings(world, idp):
    """An enabled provider whose issuer nobody answers is refused
    `422 SIGN_IN_PROVIDER_UNREACHABLE`; a provider read never answers its secret; deleting one
    someone signed in with answers `409 SIGN_IN_PROVIDER_IN_USE`; disabling it ends that person's
    session (their next request `401`)."""
    body = {
        "key": "nowhere",
        "name": "Nowhere",
        "issuer": "http://127.0.0.1:9/",
        "clientId": "x",
        "clientSecret": "y",
        "enabled": True,
    }
    error = refused(world.api.post("/sign-in-providers", body), 422, "SIGN_IN_PROVIDER_UNREACHABLE")
    assert error["details"]["reason"]
    ok(world.api.post("/sign-in-providers", {**body, "enabled": False}), 201)
    refused(world.api.post("/sign-in-providers", {**body, "enabled": False}), 409,
            "SIGN_IN_PROVIDER_KEY_TAKEN")  # fmt: skip
    ok(world.api.delete("/sign-in-providers/nowhere"), 204)
    refused(world.api.get("/sign-in-providers/nowhere"), 404, "SIGN_IN_PROVIDER_NOT_FOUND")

    provider = _provider(world, idp)
    listed = ok(world.api.get("/sign-in-providers"))["items"]
    assert [item["key"] for item in listed] == ["harness"]
    assert all(idp.client_secret not in str(item) for item in listed)
    token = _signed_in(world, idp, **PAT)
    refused(world.api.delete("/sign-in-providers/harness"), 409, "SIGN_IN_PROVIDER_IN_USE")
    ok(world.api.client.get("/api/v1/me", headers=_bearer(token)))
    ok(world.api.patch("/sign-in-providers/harness",
                       {"expectedVersion": provider["version"], "enabled": False}))  # fmt: skip
    refused(world.api.client.get("/api/v1/me", headers=_bearer(token)), 401, "TOKEN_INVALID")
