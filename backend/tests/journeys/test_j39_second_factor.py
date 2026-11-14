"""J39.9 — a second factor for a local account (USER_JOURNEYS.md § Security, 0.12 I4b).

A person sets up an authenticator app (a TOTP secret, RFC 6238) on Account and keeps ten recovery
codes. Their password alone then leads to the sign-in page's code step, not to a session; a wrong
code is refused and counted like a wrong password, a right one signs them in once, a recovery code
works once. With the instance's requirement on, a person without a second factor sets one up on the
sign-in page before any session exists, and an administrator removes a person's factor. A person
signing in through a provider is never asked. Every case runs on two configurations through the
public API, with a plain HTTP client keeping the browser's cookies; the codes are made here from the
secret the engine answers, by RFC 4226's own arithmetic.
"""

import base64
import hashlib
import hmac
import re
import struct
import time
from html import unescape

import pytest
from oidc_provider import OidcProvider
from scenario import ok, refused
from test_j39_provider_sign_in import PAT, _provider, _signed_in
from test_j39_sign_in import (
    PASSWORD,
    _bearer,
    _browser,
    _code,
    _exchange,
    _person,
    _pkce,
    _post_form,
    _sign_in,
)

STEP = 30


@pytest.fixture
def idp():
    with OidcProvider() as provider:
        yield provider


def _totp(secret: str, ahead: int = 0) -> str:
    """The six-digit code of the current time step, or ``ahead`` steps later."""
    key = base64.b32decode(
        secret.replace(" ", "").upper() + "=" * (-len(secret.replace(" ", "")) % 8)
    )
    counter = int(time.time()) // STEP + ahead
    digest = hmac.new(key, struct.pack(">Q", counter), hashlib.sha1).digest()
    offset = digest[-1] & 0x0F
    number = struct.unpack(">I", digest[offset : offset + 4])[0] & 0x7FFFFFFF
    return f"{number % 10**6:06d}"


def _own(world, token: str, method: str, path: str, body: dict | None = None):
    return world.api.client.request(method, f"/api/v1{path}", json=body, headers=_bearer(token))


def _step(page) -> str:
    match = re.search(r'name="step" value="([^"]+)"', page.text)
    assert match, page.text[:600]
    return match.group(1)


def _second(browser, step: str, **fields):
    return browser.post(
        "/oauth/second-factor", data={"step": step, **fields}, follow_redirects=False
    )


def _password_step(browser, username: str, challenge: str):
    """The password accepted: the page that asks for more, never a redirect."""
    page = _post_form(browser, username, PASSWORD, challenge)
    assert page.status_code == 200, f"{page.status_code}: {page.text[:300]}"
    assert "location" not in page.headers
    return page


def _set_up(world, token: str) -> tuple[str, list[str]]:
    """The second factor set up on Account by the person holding ``token``; its secret and codes."""
    made = ok(_own(world, token, "POST", "/me/second-factor"), 201)
    assert made["otpauthUri"].startswith("otpauth://totp/") and "<svg" in made["qrSvg"]
    assert made["secret"] in made["otpauthUri"]
    refused(_own(world, token, "POST", "/me/second-factor/confirmation", {"code": "000000"}), 422,
            "CODE_INCORRECT")  # fmt: skip
    confirmed = ok(
        _own(
            world, token, "POST", "/me/second-factor/confirmation", {"code": _totp(made["secret"])}
        )
    )
    return made["secret"], confirmed["recoveryCodes"]


@pytest.mark.journey("J39")
def test_a_person_sets_up_an_authenticator_app_and_signs_in_with_it(world):
    """Given a person with a password. When they set up the app (a wrong code refused, the right one
    answering ten recovery codes), then Account reads it on; their password alone gives the code
    page and no code; a wrong code is refused and written as a failed sign-in; the right code signs
    them in as a password session; the same code again is refused; a recovery code signs in once and the same one is refused; new recovery codes (asking for a code)
    void the old ones; seven wrong codes in a row are slowed. Removing the factor needs a code."""
    _person(world, "mei")
    token = _sign_in(_browser(world), "mei")
    off = ok(_own(world, token, "GET", "/me/second-factor"))
    assert off == {
        "enabled": False,
        "confirmedAt": None,
        "recoveryCodesLeft": 0,
        "passkeys": 0,
        "required": False,
    }
    secret, codes = _set_up(world, token)
    assert len(codes) == len(set(codes)) == 10
    on = ok(_own(world, token, "GET", "/me/second-factor"))
    assert on["enabled"] is True and on["recoveryCodesLeft"] == 10 and on["confirmedAt"]
    refused(_own(world, token, "POST", "/me/second-factor"), 409, "SECOND_FACTOR_EXISTS")
    mei = ok(world.api.get("/users", q="mei"))["items"][0]
    assert mei["secondFactor"]["method"] == "authenticator-app" and "secret" not in str(mei)
    signed_in = ok(world.api.get("/security-events", aggregateType="sign-in"))["items"]
    assert [e["action"] for e in signed_in].count("succeeded") == 1  # the sign-in at the start

    browser = _browser(world)
    verifier, challenge = _pkce()
    page = _password_step(browser, "mei", challenge)
    assert "Enter your code" in page.text and 'name="code"' in page.text
    step = _step(page)
    wrong = _second(browser, step, code="000000")
    assert wrong.status_code == 401 and "That code is not right" in wrong.text
    assert "location" not in wrong.headers
    events = ok(world.api.get("/security-events", aggregateType="sign-in"))["items"]
    assert any(e["action"] == "failed" and e["details"].get("reason") == "code" for e in events)
    # The code that confirmed the app is spent; the next step's is the first that signs in.
    # One code for the sign-in and its replay: computed twice, a 30 s step boundary between the two
    # calls (a loaded run) makes the second a different, valid code.
    next_code = _totp(secret, ahead=1)
    signed = _second(browser, _step(wrong), code=next_code)
    access = ok(_exchange(browser, _code(signed), verifier))["access_token"]
    me = ok(world.api.client.get("/api/v1/me", headers=_bearer(access)))
    assert me["signedInWith"] == "password" and me["email"] == "mei@example.org"

    again = _browser(world)
    verifier, challenge = _pkce()
    replay = _second(again, _step(_password_step(again, "mei", challenge)), code=next_code)
    assert replay.status_code == 401 and "That code is not right" in replay.text

    third = _browser(world)
    verifier, challenge = _pkce()
    start = _password_step(third, "mei", challenge)
    recovery = _second(third, _step(start), view="recovery")
    assert "Use a recovery code" in recovery.text and 'name="recovery"' in recovery.text
    used = _second(third, _step(recovery), recovery=codes[0])
    assert used.status_code == 303
    fourth = _browser(world)
    verifier, challenge = _pkce()
    repeat = _second(fourth, _step(_password_step(fourth, "mei", challenge)), recovery=codes[0])
    assert repeat.status_code == 401 and "not right" in repeat.text
    assert ok(_own(world, token, "GET", "/me/second-factor"))["recoveryCodesLeft"] == 9

    refused(_own(world, token, "POST", "/me/second-factor/recovery-codes", {"code": "000000"}),
            422, "CODE_INCORRECT")  # fmt: skip
    fresh = ok(_own(world, token, "POST", "/me/second-factor/recovery-codes", {"code": codes[1]}))[
        "recoveryCodes"
    ]
    assert len(fresh) == 10 and not set(fresh) & set(codes)
    fifth = _browser(world)
    verifier, challenge = _pkce()
    old = _second(fifth, _step(_password_step(fifth, "mei", challenge)), recovery=codes[2])
    assert old.status_code == 401

    refused(_own(world, token, "DELETE", "/me/second-factor", {"code": "000000"}), 422,
            "CODE_INCORRECT")  # fmt: skip
    slowed = old
    for _ in range(6):
        slowed = _second(fifth, _step(slowed), code="000000")
    time.sleep(1.2)
    # A right password does not wipe the count: the next wrong code is slowed still (D271, D388).
    again_step = _step(_password_step(fifth, "mei", challenge))
    slowed = _second(fifth, again_step, code="000000")
    assert slowed.status_code == 401
    slowed = _second(fifth, _step(slowed), code="000000")
    assert slowed.status_code == 429 and "try again in" in slowed.text.lower()
    time.sleep(2.2)
    ok(_own(world, token, "DELETE", "/me/second-factor", {"code": fresh[0]}), 204)
    assert ok(_own(world, token, "GET", "/me/second-factor"))["enabled"] is False
    plain = _browser(world)
    assert _post_form(plain, "mei", PASSWORD, _pkce()[1]).status_code == 303


@pytest.mark.journey("J39")
def test_the_requirement_and_an_administrators_removal(world):
    """Given the instance requires a second factor with a password. When a person without one signs
    in with their password, the sign-in page asks them to set one up (the key and a drawn code),
    refuses a wrong code, and after a right one shows ten recovery codes; only then does Continue
    give the browser its code; Account reads it on and removing it is refused
    `409 SECOND_FACTOR_REQUIRED`. An administrator removes the factor (a security event); the
    person's next password sign-in asks for set-up again. Turning the requirement off needs no
    one's code."""
    _person(world, "nora")
    local = ok(world.api.get("/sign-in-providers/local"))
    assert local["secondFactorRequired"] is False
    on = ok(world.api.patch("/sign-in-providers/local", {"expectedVersion": local["version"],
                                                          "secondFactorRequired": True}))  # fmt: skip
    assert on["secondFactorRequired"] is True and on["enabled"] is True

    browser = _browser(world)
    verifier, challenge = _pkce()
    page = _password_step(browser, "nora", challenge)
    assert "Set up a second factor" in page.text and "<svg" in page.text
    key = unescape(re.search(r'id="key"[^>]*>([^<]+)<', page.text).group(1))
    secret = key.replace(" ", "")
    refusal = _second(browser, _step(page), code="000000")
    assert refusal.status_code == 401 and "That code is not right" in refusal.text
    assert unescape(re.search(r'id="key"[^>]*>([^<]+)<', refusal.text).group(1)) == key
    codes_page = _second(browser, _step(refusal), code=_totp(secret))
    assert codes_page.status_code == 200 and "Keep your recovery codes" in codes_page.text
    shown = re.findall(r">([a-z2-9]{4}-[a-z2-9]{4}-[a-z2-9]{4})<", codes_page.text)
    assert len(shown) == 10
    assert "location" not in codes_page.headers
    done = _second(browser, _step(codes_page), **{"continue": "1"})
    token = ok(_exchange(browser, _code(done), verifier))["access_token"]
    mine = ok(_own(world, token, "GET", "/me/second-factor"))
    assert mine["enabled"] is True and mine["required"] is True and mine["recoveryCodesLeft"] == 10
    refused(_own(world, token, "DELETE", "/me/second-factor", {"code": _totp(secret, ahead=1)}),
            409, "SECOND_FACTOR_REQUIRED")  # fmt: skip

    nora = ok(world.api.get("/users", q="nora"))["items"][0]
    ok(world.api.delete(f"/users/{nora['id']}/second-factor"), 204)
    assert ok(world.api.get(f"/users/{nora['id']}"))["secondFactor"] is None
    refused(world.api.delete(f"/users/{nora['id']}/second-factor"), 404, "SECOND_FACTOR_NOT_FOUND")
    events = ok(world.api.get("/security-events", aggregateType="user"))["items"]
    assert {"second-factor-added", "second-factor-removed"} <= {e["action"] for e in events}
    again = _password_step(_browser(world), "nora", _pkce()[1])
    assert "Set up a second factor" in again.text

    local = ok(world.api.get("/sign-in-providers/local"))
    off = ok(world.api.patch("/sign-in-providers/local", {"expectedVersion": local["version"],
                                                           "secondFactorRequired": False}))  # fmt: skip
    assert off["secondFactorRequired"] is False
    assert _post_form(_browser(world), "nora", PASSWORD, _pkce()[1]).status_code == 303


@pytest.mark.journey("J39")
def test_a_provider_sign_in_is_never_asked_for_a_second_factor(world, idp):
    """Given the instance requires a second factor with a password. When someone signs in through a
    provider, they are signed in without a code page or a set-up: the provider's own factor applies
    (D225), and they have no second factor of the engine's."""
    _provider(world, idp)
    local = ok(world.api.get("/sign-in-providers/local"))
    ok(world.api.patch("/sign-in-providers/local", {"expectedVersion": local["version"],
                                                     "secondFactorRequired": True}))  # fmt: skip
    token = _signed_in(world, idp, **PAT)
    me = ok(world.api.client.get("/api/v1/me", headers=_bearer(token)))
    assert me["signedInWith"] == "harness"
    assert ok(_own(world, token, "GET", "/me/second-factor"))["enabled"] is False


@pytest.mark.journey("J39")
def test_a_setup_page_for_a_factor_confirmed_elsewhere_answers_a_page_not_json(world):
    """Given the instance requires a second factor and a person is on the set-up step of a
    sign-in. When the same person confirms a factor elsewhere before the page is submitted (the
    requirement was off for a moment), the page they submit answers the engine's HTML page with
    the message and the step is not used, never the API's JSON error."""
    _person(world, "pia")
    local = ok(world.api.get("/sign-in-providers/local"))
    on = ok(world.api.patch("/sign-in-providers/local", {"expectedVersion": local["version"],
                                                          "secondFactorRequired": True}))  # fmt: skip
    browser = _browser(world)
    page = _password_step(browser, "pia", _pkce()[1])
    assert "Set up a second factor" in page.text

    ok(world.api.patch("/sign-in-providers/local", {"expectedVersion": on["version"],
                                                     "secondFactorRequired": False}))  # fmt: skip
    token = _sign_in(_browser(world), "pia")
    _set_up(world, token)
    local = ok(world.api.get("/sign-in-providers/local"))
    ok(world.api.patch("/sign-in-providers/local", {"expectedVersion": local["version"],
                                                     "secondFactorRequired": True}))  # fmt: skip

    answer = _second(browser, _step(page), code="000000")
    assert answer.headers["content-type"].startswith("text/html"), answer.text[:300]
    assert answer.status_code == 404 and "No second factor is being set up" in answer.text
    assert "location" not in answer.headers
