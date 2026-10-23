"""J39, J40 — a person signs in from the browser (USER_JOURNEYS.md § Security, 0.12 I2).

The browser opens the engine's sign-in page with an authorization request carrying a PKCE
challenge; the form, with the right credentials, redirects back with a one-time code; the code and
its verifier answer an access token and a refresh cookie that renews the session, each refresh
token once. Sessions end when signed out, everywhere, by an administrator, on deactivation, and on a
password change or reset; failed sign-ins are slowed, never locked. A person gets a first password
from a one-time link an administrator makes. Every case runs on two configurations through the
public API, as the browser calls it.
"""

import base64
import hashlib
import secrets
import time
from urllib.parse import parse_qs, urlsplit

import pytest
from harness_identity import TestClient
from scenario import ok, refused

REDIRECT = "http://localhost:5173/signed-in"
PASSWORD = "a long passphrase for testing"


def _browser(world) -> TestClient:
    """A browser of its own, with its own cookies, that sends no harness token."""
    return TestClient(world.api.client.app, authenticated=False)


def _pkce() -> tuple[str, str]:
    verifier = secrets.token_urlsafe(48)
    digest = hashlib.sha256(verifier.encode()).digest()
    return verifier, base64.urlsafe_b64encode(digest).rstrip(b"=").decode()


def _request(challenge: str, **changes: str) -> dict[str, str]:
    return {
        "response_type": "code",
        "client_id": "browser",
        "redirect_uri": REDIRECT,
        "code_challenge": challenge,
        "code_challenge_method": "S256",
        "state": "where-i-was",
        **changes,
    }


def _post_form(browser: TestClient, username: str, password: str, challenge: str, **changes):
    return browser.post(
        "/oauth/authorize",
        data={**_request(challenge, **changes), "username": username, "password": password},
        follow_redirects=False,
    )


def _code(response) -> str:
    assert response.status_code == 303, f"{response.status_code}: {response.text[:300]}"
    location = urlsplit(response.headers["location"])
    assert f"{location.scheme}://{location.netloc}{location.path}" == REDIRECT
    query = parse_qs(location.query)
    assert query["state"] == ["where-i-was"]
    return query["code"][0]


def _exchange(browser: TestClient, code: str, verifier: str, redirect_uri: str = REDIRECT):
    return browser.post(
        "/oauth/token",
        data={
            "grant_type": "authorization_code",
            "client_id": "browser",
            "code": code,
            "code_verifier": verifier,
            "redirect_uri": redirect_uri,
        },
    )


def _sign_in(browser: TestClient, username: str, password: str = PASSWORD) -> str:
    """Sign in as the browser does; the access token, the refresh cookie kept in ``browser``."""
    verifier, challenge = _pkce()
    page = browser.get("/oauth/authorize", params=_request(challenge))
    assert page.status_code == 200 and 'name="password"' in page.text
    code = _code(_post_form(browser, username, password, challenge))
    return ok(_exchange(browser, code, verifier))["access_token"]


def _renew(browser: TestClient, refresh_token: str | None = None):
    data = {"grant_type": "refresh_token", "client_id": "browser"}
    if refresh_token is not None:
        data["refresh_token"] = refresh_token
    return browser.post("/oauth/token", data=data)


def _bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _me(world, token: str):
    return world.api.client.get("/api/v1/me", headers=_bearer(token))


def _revoked(response) -> None:
    error = refused(response, 401, "TOKEN_INVALID")
    assert error["details"] == {"reason": "revoked"}


def _invalid_grant(response) -> None:
    assert response.status_code == 400, response.text
    assert response.json()["error"] == "invalid_grant"


def _reset_link(world, person: dict) -> str:
    link = ok(world.api.post(f"/users/{person['id']}/password-reset", {}), 201)
    assert link["expiresAt"]
    return parse_qs(urlsplit(link["url"]).query)["token"][0]


def _set_password(browser: TestClient, token: str, password: str = PASSWORD):
    return browser.post(
        "/oauth/password", data={"token": token, "password": password, "repeat": password}
    )


def _person(world, username: str) -> dict:
    """A person with a password, set through the link an administrator makes."""
    person = ok(world.api.post("/users", {"username": username, "name": username.title()}), 201)
    response = _set_password(_browser(world), _reset_link(world, person))
    assert response.status_code == 200 and "Your password is set" in response.text
    return person


@pytest.mark.journey("J39")
def test_a_person_signs_in_and_works(world):
    """Given a person with a password and Data steward in the workspace (Z1). When the browser's
    authorization request opens the sign-in
    page and the form is posted with the right credentials, then it redirects to the app with a
    code and the state; the code with its verifier answers a token for an hour and sets the
    `HttpOnly`, `SameSite=Strict` cookie; `/me` names the person, signed in with a password; they
    write and read a record. A code used twice, a wrong verifier, or an address not allowed are
    refused."""
    person = _person(world, "ana")
    grant = {"principal": {"kind": "user", "id": person["id"]}, "role": "steward"}
    ok(world.api.post("/grants", {**grant, "scope": {"workspaceKey": "default"}}), 201)
    browser = _browser(world)
    verifier, challenge = _pkce()
    code = _code(_post_form(browser, "ANA", PASSWORD, challenge))
    exchanged = _exchange(browser, code, verifier)
    answer = ok(exchanged)
    assert (answer["token_type"], answer["expires_in"]) == ("Bearer", 3600)
    cookie = exchanged.headers["set-cookie"]
    assert "oauth_refresh=" in cookie and "HttpOnly" in cookie and "Path=/oauth" in cookie
    assert "samesite=strict" in cookie.lower()
    me = ok(_me(world, answer["access_token"]))
    assert (me["id"], me["kind"], me["signedInWith"]) == (person["id"], "user", "password")
    assert me["lastSignInAt"] and me["sessionId"]
    made = ok(
        world.api.client.post(
            "/api/v1/objects",
            json={
                "applicationKey": world.app("R"),
                "objectTypeKey": world.key("R"),
                "workspaceKey": "default",
                "name": "Made after signing in",
                "attributes": [
                    {"attributeTypeKey": key, "value": value}
                    for key, value in world.required_values("R").items()
                ],
            },
            headers=_bearer(answer["access_token"]),
        ),
        201,
    )
    assert ok(world.read("R", made["id"]))["name"] == "Made after signing in"

    _invalid_grant(_exchange(browser, code, verifier))
    _revoked(_me(world, answer["access_token"]))  # a code presented twice ends its session
    verifier, challenge = _pkce()
    code = _code(_post_form(browser, "ana", PASSWORD, challenge))
    _invalid_grant(_exchange(browser, code, _pkce()[0]))
    elsewhere = _post_form(
        browser, "ana", PASSWORD, challenge, redirect_uri="https://elsewhere.example/signed-in"
    )
    assert elsewhere.status_code == 400 and "location" not in elsewhere.headers
    no_pkce = browser.get(
        "/oauth/authorize",
        params=_request(challenge, code_challenge_method="plain"),
        follow_redirects=False,
    )
    assert no_pkce.status_code == 303 and "error=invalid_request" in no_pkce.headers["location"]


@pytest.mark.journey("J39.2")
def test_the_session_renews_and_a_reused_token_ends_it(world):
    """Given a session. When the cookie renews it, then a new token and a new cookie. When the old
    refresh token is presented again, then `invalid_grant` and the session ends: the new cookie no
    longer renews and the access token answers `401 TOKEN_INVALID` (`revoked`)."""
    _person(world, "ben")
    browser = _browser(world)
    _sign_in(browser, "ben")
    first = browser.cookies.get("oauth_refresh")
    renewed = ok(_renew(browser))
    second = browser.cookies.get("oauth_refresh")
    assert second and second != first
    assert ok(_me(world, renewed["access_token"]))["kind"] == "user"
    _invalid_grant(_renew(browser, first))
    _invalid_grant(_renew(browser, second))
    _revoked(_me(world, renewed["access_token"]))


@pytest.mark.journey("J39.3")
def test_signing_out_one_session_everywhere_or_by_an_administrator(world):
    """Given a person signed in in two browsers. When one session is ended from `/me/sessions`,
    then only that one is refused. When they sign out everywhere, or an administrator does, then
    every session's next request is refused and no cookie renews. `/oauth/revoke` ends the session
    it is sent with."""
    person = _person(world, "cleo")
    laptop, phone = _browser(world), _browser(world)
    on_laptop, on_phone = _sign_in(laptop, "cleo"), _sign_in(phone, "cleo")
    listed = ok(world.api.client.get("/api/v1/me/sessions", headers=_bearer(on_laptop)))["items"]
    assert len(listed) == 2 and [item["current"] for item in listed].count(True) == 1
    phone_session = ok(_me(world, on_phone))["sessionId"]
    response = world.api.client.delete(
        f"/api/v1/me/sessions/{phone_session}", headers=_bearer(on_laptop)
    )
    assert response.status_code == 204
    _revoked(_me(world, on_phone))
    _invalid_grant(_renew(phone))
    assert ok(_me(world, on_laptop))["id"] == person["id"]

    on_phone = _sign_in(phone, "cleo")
    response = world.api.client.delete("/api/v1/me/sessions", headers=_bearer(on_phone))
    assert response.status_code == 204
    for token, browser in ((on_laptop, laptop), (on_phone, phone)):
        _revoked(_me(world, token))
        _invalid_grant(_renew(browser))

    on_laptop = _sign_in(laptop, "cleo")
    assert world.api.delete(f"/users/{person['id']}/sessions").status_code == 204
    _revoked(_me(world, on_laptop))

    on_laptop = _sign_in(laptop, "cleo")
    assert laptop.post("/oauth/revoke").status_code == 200
    _revoked(_me(world, on_laptop))
    assert laptop.cookies.get("oauth_refresh") is None
    assert _renew(laptop).json()["error"] == "invalid_request"


@pytest.mark.journey("J39.4")
def test_a_deactivated_person_is_refused_at_once(world):
    """Given a signed-in person. When deactivated, then their token answers `401 TOKEN_INVALID`
    (`revoked`), the cookie renews nothing and the form does not sign them in; restored, they sign
    in again."""
    person = _person(world, "dov")
    browser = _browser(world)
    token = _sign_in(browser, "dov")
    changed = ok(world.api.patch(f"/users/{person['id']}", {"expectedVersion": 2, "active": False}))
    _revoked(_me(world, token))
    _invalid_grant(_renew(browser))
    assert _post_form(browser, "dov", PASSWORD, _pkce()[1]).status_code == 401
    ok(
        world.api.patch(
            f"/users/{person['id']}", {"expectedVersion": changed["version"], "active": True}
        )
    )
    assert ok(_me(world, _sign_in(browser, "dov")))["id"] == person["id"]


@pytest.mark.journey("J39.5")
def test_wrong_passwords_are_slowed_never_locked(world):
    """A wrong password and an unknown username give the same message. After the free failures,
    the next attempt is refused with the wait, even with the right password; after the wait the
    right password signs in."""
    _person(world, "eve")
    browser = _browser(world)
    challenge = _pkce()[1]
    wrong = _post_form(browser, "eve", "not the right passphrase", challenge)
    unknown = _post_form(browser, "nobody-here", "not the right passphrase", challenge)
    for response in (wrong, unknown):
        assert response.status_code == 401
        assert "The username or password is not right" in response.text
    for _ in range(5):
        _post_form(browser, "eve", "still not the right one", challenge)
    slowed = _post_form(browser, "eve", PASSWORD, challenge)
    assert slowed.status_code == 429 and "You can try again in" in slowed.text
    assert int(slowed.headers["retry-after"]) >= 1
    time.sleep(int(slowed.headers["retry-after"]) + 0.2)
    _sign_in(browser, "eve")


@pytest.mark.journey("J39.6")
def test_changing_ones_password(world):
    """Without the right current password `422 PASSWORD_INCORRECT`; a short or common new one
    `422 PASSWORD_REJECTED`. With both right, the other sessions end, this one goes on, and the new
    password signs in."""
    _person(world, "fay")
    here, there = _browser(world), _browser(world)
    token, other = _sign_in(here, "fay"), _sign_in(there, "fay")

    def change(current: str, new: str):
        return world.api.client.post(
            "/api/v1/me/password",
            json={"currentPassword": current, "newPassword": new},
            headers=_bearer(token),
        )

    refused(change("not my password at all", "another long passphrase"), 422, "PASSWORD_INCORRECT")
    assert refused(change(PASSWORD, "short"), 422, "PASSWORD_REJECTED")["details"] == {
        "reason": "tooShort"
    }
    refused(change(PASSWORD, "passwordpassword"), 422, "PASSWORD_REJECTED")
    assert change(PASSWORD, "another long passphrase").status_code == 204
    assert ok(_me(world, token))["kind"] == "user"
    _revoked(_me(world, other))
    assert _post_form(there, "fay", PASSWORD, _pkce()[1]).status_code == 401
    _sign_in(there, "fay", "another long passphrase")


@pytest.mark.journey("J40")
def test_a_reset_link_sets_a_password_once(world):
    """Given a person without a password. When an administrator makes a link, then its page sets a
    password under the rules and the person signs in; the link used again, or replaced by a newer
    one, is refused; using one ends the person's sessions."""
    person = ok(world.api.post("/users", {"username": "gil", "name": "Gil"}), 201)
    assert ok(world.api.get(f"/users/{person['id']}"))["hasPassword"] is False
    browser = _browser(world)
    replaced, token = _reset_link(world, person), _reset_link(world, person)
    assert browser.get("/oauth/password", params={"token": replaced}).status_code == 410
    page = browser.get("/oauth/password", params={"token": token})
    assert page.status_code == 200 and "gil" in page.text
    short = _set_password(browser, token, "short")
    assert short.status_code == 422 and "at least 15" in short.text
    assert _set_password(browser, token).status_code == 200
    assert _set_password(browser, token).status_code == 410
    assert ok(world.api.get(f"/users/{person['id']}"))["hasPassword"] is True
    signed_in = _sign_in(browser, "gil")
    assert (
        _set_password(browser, _reset_link(world, person), "a different passphrase").status_code
        == 200
    )
    _revoked(_me(world, signed_in))
    _sign_in(browser, "gil", "a different passphrase")
