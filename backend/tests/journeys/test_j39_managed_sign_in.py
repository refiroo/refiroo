"""J39.12 — a person whose sign-in an administrator manages (USER_JOURNEYS.md § Security, 0.17 SA1).

An account several people share by a known password cannot be taken from all of them by one of
them: while `signInManaged` is on, the person's own password, second factor, passkeys and other
sessions cannot be changed by them (`403 SIGN_IN_MANAGED`), a forgotten-password request for their
address sends nothing, and an administrator's reset link still sets the password. A person without
the switch is as before. Every case runs on two configurations through the public API.
"""

import pytest
from scenario import ok, refused, send_mail
from test_j39_second_factor import _own
from test_j39_sign_in import (
    PASSWORD,
    _bearer,
    _browser,
    _me,
    _person,
    _reset_link,
    _revoked,
    _set_password,
    _sign_in,
)
from test_j46_mail import _save, smtp  # noqa: F401  (smtp is a fixture)
from test_j46_reset_by_mail import REQUEST, _ask, _outbox, _with_password  # noqa: F401

NEW = "another long passphrase"


def _managed(world, name: str, on: bool = True) -> dict:
    """A person with a password whose sign-in an administrator manages (or not, when ``on`` is false)."""
    person = _person(world, name)
    if not on:
        return person
    return _switch(world, person, True)


def _version(world, person: dict) -> int:
    return ok(world.api.get(f"/users/{person['id']}"))["version"]


def _switch(world, person: dict, on: bool) -> dict:
    body = {"expectedVersion": _version(world, person), "signInManaged": on}
    return ok(world.api.patch(f"/users/{person['id']}", body))


@pytest.mark.journey("J39.12")
def test_a_managed_person_cannot_change_the_password(world):
    """Given a managed person signed in. When they change the own password with the right current
    one, then `403 SIGN_IN_MANAGED`; the old password still signs in, and `/me` shows the switch."""
    _managed(world, "kai")
    browser = _browser(world)
    token = _sign_in(browser, "kai")
    assert ok(_me(world, token))["signInManaged"] is True
    response = world.api.client.post(
        "/api/v1/me/password",
        json={"currentPassword": PASSWORD, "newPassword": NEW},
        headers=_bearer(token),
    )
    refused(response, 403, "SIGN_IN_MANAGED")
    assert ok(_me(world, _sign_in(_browser(world), "kai")))["kind"] == "user"


@pytest.mark.journey("J39.12")
def test_a_managed_person_enrols_no_second_factor_and_no_passkey(world):
    """Given a managed person signed in. When they start a second factor, ask for new recovery
    codes, or open a passkey registration, then each is `403 SIGN_IN_MANAGED` and nothing is
    enrolled."""
    _managed(world, "lia")
    browser = _browser(world)
    token = _sign_in(browser, "lia")
    refused(_own(world, token, "POST", "/me/second-factor"), 403, "SIGN_IN_MANAGED")
    refused(
        _own(world, token, "POST", "/me/second-factor/confirmation", {"code": "123456"}),
        403,
        "SIGN_IN_MANAGED",
    )
    refused(
        _own(world, token, "POST", "/me/second-factor/recovery-codes", {"code": "123456"}),
        403,
        "SIGN_IN_MANAGED",
    )
    refused(
        _own(world, token, "DELETE", "/me/second-factor", {"code": "123456"}),
        403,
        "SIGN_IN_MANAGED",
    )
    started = browser.post("/oauth/passkeys/registration/options", json={"proof": PASSWORD})
    assert started.status_code == 403 and started.json()["code"] == "SIGN_IN_MANAGED"
    page = browser.get("/oauth/passkeys/new")
    assert page.status_code == 403 and "manages the sign-in" in page.text
    state = ok(_own(world, token, "GET", "/me/second-factor"))
    assert state["enabled"] is False and state["passkeys"] == 0


@pytest.mark.journey("J39.12")
def test_a_managed_person_sees_and_ends_only_the_own_session(world):
    """Given a managed person with two sessions. When one lists sessions, then only that one is
    listed; ending the other or all is `403 SIGN_IN_MANAGED` and the other still works; signing out
    the own session works."""
    _managed(world, "mo")
    laptop, phone = _browser(world), _browser(world)
    on_laptop, on_phone = _sign_in(laptop, "mo"), _sign_in(phone, "mo")
    listed = ok(_own(world, on_laptop, "GET", "/me/sessions"))["items"]
    assert [item["current"] for item in listed] == [True]
    phone_session = ok(_me(world, on_phone))["sessionId"]
    refused(
        _own(world, on_laptop, "DELETE", f"/me/sessions/{phone_session}"), 403, "SIGN_IN_MANAGED"
    )
    refused(_own(world, on_laptop, "DELETE", "/me/sessions"), 403, "SIGN_IN_MANAGED")
    assert ok(_me(world, on_phone))["kind"] == "user"
    own_session = ok(_me(world, on_laptop))["sessionId"]
    assert _own(world, on_laptop, "DELETE", f"/me/sessions/{own_session}").status_code == 204
    _revoked(_me(world, on_laptop))
    assert ok(_me(world, on_phone))["kind"] == "user"


@pytest.mark.journey("J39.12")
def test_a_forgotten_password_request_for_a_managed_address_sends_nothing(world, smtp):  # noqa: F811
    """Given mail is set up, a managed person and an unmanaged one. When each address is asked for,
    then the public answers are the same, and only the unmanaged person's ask queues a message."""
    _save(world, smtp)
    managed = _with_password(world, "ned", "ned@example.org")
    _switch(world, managed, True)
    _with_password(world, "oda", "oda@example.org")
    browser = _browser(world)
    answers = [_ask(browser, name) for name in ("ned@example.org", "oda@example.org")]
    assert answers[0] == answers[1]
    assert _outbox(world)["pending"] == 1
    send_mail(world)
    assert [mail["To"] for mail in smtp.messages] == ["oda@example.org"]


@pytest.mark.journey("J39.12")
def test_an_administrator_sets_the_switch_and_the_password_of_a_managed_person(world):
    """Given an administrator. When they switch the switch on and off, and set a managed person's
    password through a reset link, then each is allowed and the person signs in with it; a person
    without the right to administer people cannot set the switch."""
    person = _person(world, "pia")
    assert person["signInManaged"] is False
    on = _switch(world, person, True)
    assert on["signInManaged"] is True
    assert _set_password(_browser(world), _reset_link(world, person), NEW).status_code == 200
    _sign_in(_browser(world), "pia", NEW)

    created = ok(
        world.api.post(
            "/users", {"email": "qin@example.org", "name": "Qin", "signInManaged": True}
        ),
        201,
    )
    assert created["signInManaged"] is True

    caller = _browser(world)
    token = _sign_in(caller, "pia", NEW)
    refused(
        world.api.client.patch(
            f"/api/v1/users/{person['id']}",
            json={"expectedVersion": _version(world, person), "signInManaged": False},
            headers=_bearer(token),
        ),
        403,
        "FORBIDDEN",
    )
    off = _switch(world, person, False)
    assert off["signInManaged"] is False


@pytest.mark.journey("J39.12")
def test_a_person_without_the_switch_is_as_before(world):
    """Given a person without the switch. When they change the password, list and end sessions and
    set up a second factor, then each works as before."""
    _person(world, "rue")
    here, there = _browser(world), _browser(world)
    token, other = _sign_in(here, "rue"), _sign_in(there, "rue")
    assert ok(_me(world, token))["signInManaged"] is False
    assert len(ok(_own(world, token, "GET", "/me/sessions"))["items"]) == 2
    assert _own(world, token, "POST", "/me/second-factor").status_code == 201
    change = world.api.client.post(
        "/api/v1/me/password",
        json={"currentPassword": PASSWORD, "newPassword": NEW},
        headers=_bearer(token),
    )
    assert change.status_code == 204
    _revoked(_me(world, other))
    assert _own(world, token, "DELETE", "/me/sessions").status_code == 204
