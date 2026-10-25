"""J39.10 — passkeys for a local account (USER_JOURNEYS.md § Security, 0.12 I4c).

A signed-in person adds a passkey on the engine's own page (the browser's prompt is a software
authenticator here, ``tests/software_authenticator.py``), names it, and then signs in with it alone
or as the second step after a password. A passkey of another site or one without the user verified
is refused; a person renames and removes theirs, an administrator removes one; the instance's
requirement is met by a passkey; the sign-in page runs the engine's one script and no other, only
where a passkey is offered. Every case runs on two configurations through the public API, with a
plain HTTP client keeping the browser's cookies.
"""

import re
from urllib.parse import parse_qs, urlsplit

import pytest
from oidc_provider import OidcProvider
from scenario import ok, refused
from software_authenticator import SoftwareAuthenticator
from test_j39_provider_sign_in import PAT, _provider, _signed_in
from test_j39_second_factor import _own, _password_step, _set_up, _step
from test_j39_sign_in import (
    PASSWORD,
    REDIRECT,
    _bearer,
    _browser,
    _exchange,
    _person,
    _pkce,
    _post_form,
    _request,
    _sign_in,
)

RETURN = "http://localhost:5173/settings/account"


@pytest.fixture
def idp():
    with OidcProvider() as provider:
        yield provider


def _origin(world) -> str:
    metadata = world.api.client.get("/.well-known/oauth-authorization-server").json()
    parts = urlsplit(metadata["issuer"])
    return f"{parts.scheme}://{parts.netloc}"


def _policy(page) -> str:
    return page.headers["content-security-policy"]


def _add(browser, authenticator: SoftwareAuthenticator, name: str = "Laptop", **changes):
    """A passkey added on the engine's page by the browser holding a session; the answer."""
    started = browser.post("/oauth/passkeys/registration/options", json={})
    assert started.status_code == 200, started.text
    body = started.json()
    credential = authenticator.register(body["options"], **changes)
    return browser.post(
        "/oauth/passkeys/registration/verify",
        json={"ceremony": body["ceremony"], "credential": credential, "name": name},
    )


def _code_of(answer) -> tuple[str, str]:
    """The browser's one-time code and the verifier's challenge's state from a ceremony's redirect."""
    assert answer.status_code == 200, answer.text
    location = urlsplit(answer.json()["redirect"])
    assert f"{location.scheme}://{location.netloc}{location.path}" == REDIRECT
    return parse_qs(location.query)["code"][0], parse_qs(location.query)["state"][0]


def _alone(browser, authenticator: SoftwareAuthenticator, **changes):
    """Sign in with a passkey alone: the ceremony's answer and the browser's PKCE verifier."""
    verifier, challenge = _pkce()
    started = browser.post("/oauth/passkeys/authentication/options", json=_request(challenge))
    assert started.status_code == 200, started.text
    body = started.json()
    credential = authenticator.assertion(body["options"], **changes)
    answer = browser.post(
        "/oauth/passkeys/authentication/verify",
        json={"ceremony": body["ceremony"], "credential": credential},
    )
    return answer, verifier


def _second(browser, step: str, authenticator: SoftwareAuthenticator, **changes):
    """The passkey as the second step of a password sign-in."""
    started = browser.post("/oauth/passkeys/authentication/options", json={"step": step})
    assert started.status_code == 200, started.text
    body = started.json()
    return browser.post(
        "/oauth/passkeys/authentication/verify",
        json={
            "ceremony": body["ceremony"],
            "credential": authenticator.assertion(body["options"], **changes),
        },
    )


def _failures(world, reason: str) -> list[dict]:
    events = ok(world.api.get("/security-events", aggregateType="sign-in"))["items"]
    return [e for e in events if e["action"] == "failed" and e["details"].get("reason") == reason]


@pytest.mark.journey("J39")
def test_a_person_adds_a_passkey_and_signs_in_with_it_alone(world):
    """Given a person with a password. When they open the engine's Add a passkey page (its policy
    allows the engine's one script and nothing inline), create one named Laptop, then Account lists
    it, unused. A browser that holds no session signs in with it alone, with no username: the
    ceremony answers the browser's one-time code, the session is signed in with a passkey, and the
    passkey reads as used. The sign-in page offers the button only once a passkey exists. A
    passkey of another site, or without the user verified, is refused and written as a failed
    sign-in. The person renames it and removes it."""
    _person(world, "mei")
    anonymous = _browser(world)
    page = anonymous.get("/oauth/authorize", params=_request(_pkce()[1]))
    assert "data-passkey" not in page.text and "script" not in _policy(page)

    browser = _browser(world)
    token = _sign_in(browser, "mei")
    assert refused_without_session(world)
    add = browser.get("/oauth/passkeys/new", params={"return": RETURN})
    assert add.status_code == 200 and 'data-passkey="register"' in add.text
    assert "/oauth/passkey.js" in add.text and "script-src 'self'" in _policy(add)
    assert "unsafe-inline'" not in _policy(add).split("style-src")[0]
    script = browser.get("/oauth/passkey.js")
    assert script.status_code == 200 and "javascript" in script.headers["content-type"]

    authenticator = SoftwareAuthenticator(_origin(world))
    assert _add(browser, authenticator, "Laptop", verified=False).status_code == 422
    assert _add(browser, authenticator, "Laptop", origin="https://evil.example").status_code == 422
    added = _add(browser, authenticator, "Laptop")
    assert added.status_code == 200, added.text
    listed = ok(_own(world, token, "GET", "/me/passkeys"))["items"]
    assert [(p["name"], p["lastUsedAt"]) for p in listed] == [("Laptop", None)]
    state = ok(_own(world, token, "GET", "/me/second-factor"))
    assert state["enabled"] is False and state["passkeys"] == 1

    page = _browser(world).get("/oauth/authorize", params=_request(_pkce()[1]))
    assert 'data-passkey="login"' in page.text and "script-src 'self'" in _policy(page)
    assert "/oauth/passkey.js" in page.text

    fresh = _browser(world)
    answer, verifier = _alone(fresh, authenticator, origin="https://evil.example")
    assert answer.status_code == 401 and "location" not in answer.headers
    answer, verifier = _alone(fresh, authenticator, verified=False)
    assert answer.status_code == 401
    assert len(_failures(world, "passkey")) == 2
    answer, verifier = _alone(fresh, authenticator)
    code, _ = _code_of(answer)
    access = ok(_exchange(fresh, code, verifier))["access_token"]
    me = ok(world.api.client.get("/api/v1/me", headers=_bearer(access)))
    assert me["signedInWith"] == "passkey" and me["username"] == "mei"
    used = ok(_own(world, access, "GET", "/me/passkeys"))["items"][0]
    assert used["lastUsedAt"]
    again = _browser(world)
    replay_options = again.post("/oauth/passkeys/authentication/options", json=_request(_pkce()[1]))
    assert replay_options.status_code == 200

    renamed = ok(
        _own(world, access, "PATCH", f"/me/passkeys/{used['id']}", {"name": "Work laptop"})
    )
    assert renamed["name"] == "Work laptop"
    # A session alone does not remove a passkey: the password is asked again.
    path = f"/me/passkeys/{used['id']}"
    refused(_own(world, access, "DELETE", path), 422, "PROOF_REQUIRED")
    refused(_own(world, access, "DELETE", path, {"proof": "not-the-password"}), 422,
            "CODE_INCORRECT")  # fmt: skip
    assert len(ok(_own(world, access, "GET", "/me/passkeys"))["items"]) == 1
    ok(_own(world, access, "DELETE", path, {"proof": PASSWORD}), 204)
    assert ok(_own(world, access, "GET", "/me/passkeys"))["items"] == []
    refused(_own(world, access, "DELETE", path, {"proof": PASSWORD}), 404, "PASSKEY_NOT_FOUND")
    gone, _ = _alone(_browser(world), authenticator)
    assert gone.status_code == 401


def refused_without_session(world) -> bool:
    """The engine's page does not serve someone with no session, and the ceremony no one."""
    page = _browser(world).get("/oauth/passkeys/new", params={"return": RETURN})
    started = _browser(world).post("/oauth/passkeys/registration/options", json={})
    return page.status_code == 401 and started.status_code == 401


@pytest.mark.journey("J39")
def test_a_passkey_is_a_second_step_after_a_password(world):
    """Given a person with a password and a passkey, and an app. When their password is right, the
    page offers the passkey beside the code; the passkey signs them in as a password session; one of
    another site or without the user verified is refused and counted; the same page with a person
    who has only a passkey offers no code field. With the instance's requirement on, a person with
    only a passkey is not asked to set up an app, and cannot remove their last passkey."""
    _person(world, "mei")
    browser = _browser(world)
    token = _sign_in(browser, "mei")
    authenticator = SoftwareAuthenticator(_origin(world))
    assert _add(browser, authenticator).status_code == 200
    _set_up(world, token)

    second = _browser(world)
    verifier, challenge = _pkce()
    page = _password_step(second, "mei", challenge)
    assert 'data-passkey="second"' in page.text and 'name="code"' in page.text
    assert "script-src 'self'" in _policy(page)
    step = _step(page)
    assert _second(second, step, authenticator, origin="https://evil.example").status_code == 401
    assert _second(second, step, authenticator, verified=False).status_code == 401
    assert len(_failures(world, "passkey")) == 2
    answer = _second(second, step, authenticator)
    code, _ = _code_of(answer)
    access = ok(_exchange(second, code, verifier))["access_token"]
    assert (
        ok(world.api.client.get("/api/v1/me", headers=_bearer(access)))["signedInWith"]
        == "password"
    )
    spent = second.post("/oauth/passkeys/authentication/options", json={"step": step})
    assert spent.status_code == 410

    # Without a passkey the page is script-free, as the code page was.
    ok(_own(world, access, "DELETE", f"/me/passkeys/{_passkey_id(world, access)}",
            {"proof": PASSWORD}), 204)  # fmt: skip
    plain = _password_step(_browser(world), "mei", _pkce()[1])
    assert "script" not in _policy(plain) and "data-passkey" not in plain.text

    # A person with only a passkey, and the requirement on.
    _person(world, "pia")
    pia = _browser(world)
    pia_token = _sign_in(pia, "pia")
    pia_key = SoftwareAuthenticator(_origin(world))
    assert _add(pia, pia_key, "Key").status_code == 200
    local = ok(world.api.get("/sign-in-providers/local"))
    ok(world.api.patch("/sign-in-providers/local", {"expectedVersion": local["version"],
                                                     "secondFactorRequired": True}))  # fmt: skip
    only = _browser(world)
    verifier, challenge = _pkce()
    ask = _password_step(only, "pia", challenge)
    assert "Set up a second factor" not in ask.text and 'data-passkey="second"' in ask.text
    assert 'name="code"' not in ask.text
    signed = _second(only, _data_step(ask), pia_key)
    assert signed.status_code == 200 and _code_of(signed)
    refused(_own(world, pia_token, "DELETE", f"/me/passkeys/{_passkey_id(world, pia_token)}",
                 {"proof": PASSWORD}), 409, "SECOND_FACTOR_REQUIRED")  # fmt: skip


def _data_step(page) -> str:
    """The step's token a passkey-only page carries on its button (it has no form to hold it)."""
    match = re.search(r'data-step="([^"]+)"', page.text)
    assert match, page.text[:400]
    return match.group(1)


def _passkey_id(world, token: str) -> str:
    return ok(_own(world, token, "GET", "/me/passkeys"))["items"][0]["id"]


@pytest.mark.journey("J39")
def test_an_administrator_removes_a_passkey_and_local_sign_in_off_refuses_one(world, idp):
    """Given a person with a passkey. When local sign-in is off, a passkey alone is refused for them,
    as a password is, since they do not keep local sign-in (D365, D393); when it is on again, a
    security administrator lists the person's passkeys and removes one, the person's count falls,
    and the removal is a security event."""
    person = _person(world, "mei")
    browser = _browser(world)
    _sign_in(browser, "mei")
    authenticator = SoftwareAuthenticator(_origin(world))
    assert _add(browser, authenticator, "Laptop").status_code == 200
    assert ok(world.api.get(f"/users/{person['id']}"))["passkeys"] == 1

    _provider(world, idp)
    _signed_in(world, idp, **PAT)
    local = ok(world.api.get("/sign-in-providers/local"))
    off = ok(world.api.patch("/sign-in-providers/local", {"expectedVersion": local["version"],
                                                          "enabled": False}))  # fmt: skip
    page = _browser(world).get("/oauth/authorize", params={**_request(_pkce()[1]), "local": "1"})
    assert 'data-passkey="login"' in page.text
    refusal, _ = _alone(_browser(world), authenticator)
    assert refusal.status_code == 401 and "location" not in refusal.headers
    assert _failures(world, "passkey")
    ok(world.api.patch("/sign-in-providers/local", {"expectedVersion": off["version"],
                                                    "enabled": True}))  # fmt: skip

    listed = ok(world.api.get(f"/users/{person['id']}/passkeys"))["items"]
    assert [p["name"] for p in listed] == ["Laptop"] and "ublic" not in str(listed)
    ok(world.api.delete(f"/users/{person['id']}/passkeys/{listed[0]['id']}"), 204)
    refused(world.api.delete(f"/users/{person['id']}/passkeys/{listed[0]['id']}"), 404,
            "PASSKEY_NOT_FOUND")  # fmt: skip
    assert ok(world.api.get(f"/users/{person['id']}"))["passkeys"] == 0
    events = ok(world.api.get("/security-events", aggregateType="user"))["items"]
    assert {"passkey-added", "passkey-removed"} <= {e["action"] for e in events}
    assert _post_form(_browser(world), "mei", PASSWORD, _pkce()[1]).status_code == 303


@pytest.mark.journey("J39")
def test_open_passkey_ceremonies_are_capped(world, monkeypatch):
    """Given an engine that already holds as many unexpired passkey sign-ins as it allows. When
    another browser asks for options, the engine answers `429` with a wait instead of storing one
    more (the endpoint is open, so it cannot grow the table without bound)."""
    from app.engine.identity import passkeys

    monkeypatch.setattr(passkeys, "MAX_OPEN_CEREMONIES", 1)
    first = _browser(world).post("/oauth/passkeys/authentication/options",
                                 json=_request(_pkce()[1]))  # fmt: skip
    assert first.status_code == 200
    second = _browser(world).post("/oauth/passkeys/authentication/options",
                                  json=_request(_pkce()[1]))  # fmt: skip
    assert second.status_code == 429 and second.headers["retry-after"] == "60"
