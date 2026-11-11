"""J39 — the application's own sign-in screen (USER_JOURNEYS.md § Security, 0.12 I5).

The browser application signs a person in on a screen of its own through JSON routes that answer
what the engine's pages answer: the options a request is offered, a password (right, wrong, slowed),
the second step (a code, a recovery code, the set-up), ending in the same one-time code that the
token endpoint exchanges with the PKCE verifier. The rules are the pages' (D415): a client or address
the engine does not serve, a missing challenge and a post from another site are refused here as
there, and the session that results is the same. Every case runs on two configurations through the
public API.
"""

import pytest
from scenario import ok
from test_j39_second_factor import _own, _set_up, _totp
from test_j39_sign_in import (
    PASSWORD,
    REDIRECT,
    _browser,
    _exchange,
    _person,
    _pkce,
    _request,
    _sign_in,
)

OPTIONS = "/oauth/sign-in/options"
PASSWORD_STEP = "/oauth/sign-in/password"
SECOND = "/oauth/sign-in/second-factor"
APP = {"Origin": "http://localhost:5173"}


def _signed_in(response, state: str = "where-i-was") -> str:
    """The code in the address the sign-in ends at."""
    assert response.status_code == 200, f"{response.status_code}: {response.text[:300]}"
    body = response.json()
    assert body["status"] == "signed_in", body
    assert body["redirect"].startswith(f"{REDIRECT}?code=")
    assert body["redirect"].endswith(f"&state={state}")
    return body["redirect"].split("code=")[1].split("&")[0]


@pytest.mark.journey("J39")
def test_the_screen_signs_a_person_in_with_a_password(world):
    """Given a person with a password. When the screen asks for the options of the browser's
    request, then it is offered the password form and no passkey or provider; a wrong password is
    `401 wrong_credentials` and writes the failed sign-in the page writes; the right one answers
    the address with a code and the state, which with its verifier gives a session for that person.
    A wrong verifier gets none."""
    _person(world, "ana")
    browser = _browser(world)
    verifier, challenge = _pkce()
    request = _request(challenge)
    offered = ok(browser.get(OPTIONS, params=request, headers=APP))
    assert offered["local"] is True and offered["passkey"] is False
    assert offered["providers"] == [] and offered["product"]
    # The footer's build reference, and nothing else of the system (0.13 BR).
    assert set(offered["build"]) == {"version", "commit", "tag"}

    wrong = browser.post(
        PASSWORD_STEP,
        json={"request": request, "email": "ana@example.org", "password": "nope"},
        headers=APP,
    )
    assert wrong.status_code == 401 and wrong.json()["error"] == "wrong_credentials"
    events = ok(world.api.get("/security-events", aggregateType="sign-in"))["items"]
    assert any(e["action"] == "failed" for e in events)

    right = browser.post(
        PASSWORD_STEP,
        json={"request": request, "email": "ana@example.org", "password": PASSWORD},
        headers=APP,
    )
    code = _signed_in(right)
    other = _exchange(browser, code, _pkce()[0])
    # The code is spent by a try with the wrong verifier.
    assert other.status_code == 400 and other.json()["error"] == "invalid_grant"
    again = browser.post(
        PASSWORD_STEP,
        json={"request": request, "email": "ana@example.org", "password": PASSWORD},
        headers=APP,
    )
    token = ok(_exchange(browser, _signed_in(again), verifier))["access_token"]
    me = ok(world.api.client.get("/api/v1/me", headers={"Authorization": f"Bearer {token}"}))
    assert me["email"] == "ana@example.org" and me["signedInWith"] == "password"


@pytest.mark.journey("J39")
def test_the_screen_is_refused_what_the_pages_refuse(world):
    """When the request names a client or address the engine does not serve, or has no PKCE
    challenge, the options and the password are refused `400` with the error, and nothing is
    redirected; a post from another site is `403`; failures are slowed `429` with the seconds to
    wait, as the form slows them (D271)."""
    _person(world, "ben")
    browser = _browser(world)
    _, challenge = _pkce()
    body = {"email": "ben@example.org", "password": PASSWORD}
    for changes, error in (
        ({"client_id": "other"}, "unknown_client"),
        ({"redirect_uri": "http://evil.example/signed-in"}, "unknown_client"),
        ({"response_type": "token"}, "unsupported_response_type"),
        ({"code_challenge_method": "plain"}, "invalid_request"),
    ):
        request = _request(challenge, **changes)
        asked = browser.get(OPTIONS, params=request, headers=APP)
        assert asked.status_code == 400 and asked.json()["error"] == error
        posted = browser.post(PASSWORD_STEP, json={"request": request, **body}, headers=APP)
        assert posted.status_code == 400 and posted.json()["error"] == error
    forged = browser.post(
        PASSWORD_STEP,
        json={"request": _request(challenge), **body},
        headers={"Origin": "https://evil.example"},
    )
    assert forged.status_code == 403 and forged.json()["error"] == "foreign_origin"

    request = _request(challenge)
    last = None
    for _ in range(12):
        last = browser.post(
            PASSWORD_STEP,
            json={"request": request, "email": "ben@example.org", "password": "wrong"},
            headers=APP,
        )
        if last.status_code == 429:
            break
    assert last is not None and last.status_code == 429
    assert last.json()["error"] == "slowed" and last.json()["waitSeconds"] > 0
    assert int(last.headers["retry-after"]) == last.json()["waitSeconds"]


@pytest.mark.journey("J39")
def test_the_screen_takes_the_second_step(world):
    """Given a person with an authenticator app. When the screen posts their password, then the
    answer is `second_factor` with a step token, not a code; a wrong code is `401 wrong_code`;
    a right one signs them in as a password session; a recovery code works once; a step used
    twice is `410 step_gone`."""
    _person(world, "cleo")
    token = _sign_in(_browser(world), "cleo")
    secret, codes = _set_up(world, token)

    def first(browser):
        verifier, challenge = _pkce()
        answer = browser.post(
            PASSWORD_STEP,
            json={
                "request": _request(challenge),
                "email": "cleo@example.org",
                "password": PASSWORD,
            },
            headers=APP,
        )
        assert answer.status_code == 200, answer.text
        body = answer.json()
        assert body["status"] == "second_factor" and body["stage"] == "code"
        assert body["app"] is True and "redirect" not in body
        return verifier, body["step"]

    browser = _browser(world)
    verifier, step = first(browser)
    wrong = browser.post(SECOND, json={"step": step, "code": "000000"}, headers=APP)
    assert wrong.status_code == 401 and wrong.json()["error"] == "wrong_code"
    signed = browser.post(SECOND, json={"step": step, "code": _totp(secret, ahead=1)}, headers=APP)
    access = ok(_exchange(browser, _signed_in(signed), verifier))["access_token"]
    me = ok(world.api.client.get("/api/v1/me", headers={"Authorization": f"Bearer {access}"}))
    assert me["signedInWith"] == "password" and me["email"] == "cleo@example.org"
    gone = browser.post(SECOND, json={"step": step, "code": _totp(secret, ahead=1)}, headers=APP)
    assert gone.status_code == 410 and gone.json()["error"] == "step_gone"

    other = _browser(world)
    verifier, step = first(other)
    used = other.post(SECOND, json={"step": step, "recovery": codes[0]}, headers=APP)
    _signed_in(used)
    again = _browser(world)
    _, step = first(again)
    repeat = again.post(SECOND, json={"step": step, "recovery": codes[0]}, headers=APP)
    assert repeat.status_code == 401 and repeat.json()["error"] == "wrong_code"
    assert ok(_own(world, token, "GET", "/me/second-factor"))["recoveryCodesLeft"] == 9


@pytest.mark.journey("J39")
def test_the_screen_sets_a_second_factor_up_when_it_is_required(world):
    """Given the instance requires a second factor and a person has none. When the screen posts
    their password, then it is asked to set one up (the key and the drawing); a wrong code is
    refused; a right one answers ten recovery codes, and only sending the step again without a
    code gives the address with the code."""
    _person(world, "dara")
    local = ok(world.api.get("/sign-in-providers/local"))
    ok(
        world.api.patch(
            "/sign-in-providers/local",
            {"expectedVersion": local["version"], "secondFactorRequired": True},
        )
    )
    browser = _browser(world)
    verifier, challenge = _pkce()
    answer = ok(
        browser.post(
            PASSWORD_STEP,
            json={
                "request": _request(challenge),
                "email": "dara@example.org",
                "password": PASSWORD,
            },
            headers=APP,
        )
    )
    assert answer["status"] == "second_factor" and answer["stage"] == "setup"
    assert answer["setup"]["secret"] and "<svg" in answer["setup"]["svg"]
    step = answer["step"]
    wrong = browser.post(SECOND, json={"step": step, "code": "000000"}, headers=APP)
    assert wrong.status_code == 401 and wrong.json()["error"] == "wrong_code"
    shown = ok(
        browser.post(
            SECOND, json={"step": step, "code": _totp(answer["setup"]["secret"])}, headers=APP
        )
    )
    assert shown["status"] == "recovery_codes" and len(shown["codes"]) == 10
    done = browser.post(SECOND, json={"step": step}, headers=APP)
    access = ok(_exchange(browser, _signed_in(done), verifier))["access_token"]
    assert access
