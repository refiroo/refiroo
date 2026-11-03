"""J39.11 — the API reference signs the person in (USER_JOURNEYS.md § Security, 0.12 C1, D240).

The reference page at ``/docs/api`` is open and carries no token. A person signed in at the browser
asks the engine, from that page and with the session's cookie, for an access token: it is theirs,
it reads and refuses what their roles do, and asking never renews the cookie, so the application's
own tabs keep their session. Without a session, after signing out, or from another site, there is
none. Every case runs on two configurations through the public API, as the page calls it.
"""

import pytest
from scenario import ok, refused
from test_j39_sign_in import _bearer, _browser, _me, _person, _renew, _revoked, _sign_in


def _console_token(browser, **headers):
    return browser.post("/oauth/console-token", headers=headers)


@pytest.mark.journey("J39.11")
def test_the_console_is_given_the_signed_in_persons_token(world):
    """Given a person signed in at the browser. When the reference page asks for a token, then it is
    a `management` token for that person, valid like any other, and the cookie is unchanged: the
    application's own renewal still works. The page itself is open and holds no token."""
    person = _person(world, "dora")
    browser = _browser(world)
    _sign_in(browser, "dora")
    cookie = browser.cookies.get("oauth_refresh")

    answer = ok(_console_token(browser))
    assert answer["expires_in"] > 0
    me = ok(_me(world, answer["access_token"]))
    assert me["id"] == person["id"] and me["kind"] == "user"
    assert browser.cookies.get("oauth_refresh") == cookie
    ok(_console_token(browser))
    assert ok(_renew(browser))["access_token"]

    page = browser.get("/docs/api")
    assert page.status_code == 200 and "/oauth/console-token" in page.text
    assert answer["access_token"] not in page.text and "eyJ" not in page.text


@pytest.mark.journey("J39.11")
def test_the_console_shows_what_the_person_may_do(world):
    """Given a person with no role. When the console's token reads the person's own record, then it
    is answered; when it reads or changes the workspaces' data, then it is refused with `403
    FORBIDDEN`, as the application would refuse them."""
    _person(world, "eli")
    browser = _browser(world)
    _sign_in(browser, "eli")
    token = ok(_console_token(browser))["access_token"]

    assert world.api.client.get("/api/v1/me", headers=_bearer(token)).status_code == 200
    refused(world.api.client.get("/api/v1/users", headers=_bearer(token)), 403, "FORBIDDEN")
    refused(
        world.api.client.post("/api/v1/users", json={}, headers=_bearer(token)), 403, "FORBIDDEN"
    )


@pytest.mark.journey("J39.11")
def test_there_is_no_token_without_a_session(world):
    """Given a browser with no session, one that signed out, and a token from before signing out.
    When the page asks, then `401 not_signed_in` and nothing is issued; the token from before is
    refused as revoked."""
    _person(world, "fay")
    anonymous = _browser(world)
    refusal = _console_token(anonymous)
    assert refusal.status_code == 401 and refusal.json()["error"] == "not_signed_in"
    assert "access_token" not in refusal.text

    browser = _browser(world)
    _sign_in(browser, "fay")
    token = ok(_console_token(browser))["access_token"]
    assert browser.post("/oauth/revoke").status_code == 200
    _revoked(_me(world, token))
    assert _console_token(browser).status_code == 401


@pytest.mark.journey("J39.11")
def test_another_site_cannot_ask_for_the_token(world):
    """Given a person signed in. When a page of another site posts the request, then it is refused
    `403` with no token, cookie or not; the engine's own address is accepted."""
    _person(world, "gus")
    browser = _browser(world)
    _sign_in(browser, "gus")
    refused_ = _console_token(browser, origin="https://elsewhere.example")
    assert refused_.status_code == 403 and "access_token" not in refused_.text
    assert refused_.json()["error"] == "access_denied"
    own = str(browser.base_url).rstrip("/")
    assert _console_token(browser, origin=own).status_code == 200
