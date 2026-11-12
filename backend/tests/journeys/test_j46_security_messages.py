"""J46.13 — a message when a person's sign-in changes (0.17 SM1).

A person is written to when their password is changed or reset, or an authenticator app or a passkey
is added or removed, so a change they did not make is noticed. The message is queued with the
change, says what changed and when and what to do if it was not them, sits in the saved e-mail
template, and carries no code or link that signs in. The tests walk each change through the API as
the person (and as a security administrator) and read what the harness's SMTP server receives.
"""

import re

import pytest
from scenario import ok, refused, send_mail
from software_authenticator import SoftwareAuthenticator
from test_j39_passkeys import _add, _origin
from test_j39_second_factor import _own, _set_up, _totp
from test_j39_sign_in import PASSWORD, _browser, _person, _reset_link, _set_password, _sign_in
from test_j46_mail import _save, smtp  # noqa: F401 - a fixture
from test_j46_mail_template import BRANDED

NEW = "a-brand-new-long-pass-9"
NOT_YOU = "contact an administrator"


def _sent(world, smtp) -> list:  # noqa: F811
    """The messages the sender delivers now."""
    before = len(smtp.messages)
    send_mail(world)
    return smtp.messages[before:]


def _text(message) -> str:
    return message.get_body(("plain",)).get_content()


def _html(message) -> str:
    return message.get_body(("html",)).get_content()


def _is_security_message(message, subject: str) -> None:
    """To the person, with the subject and the words, in both parts, and nothing that signs in."""
    assert message["To"] == "mei@example.org" and subject in message["Subject"]
    for body in (_text(message), _html(message)):
        assert "Mei" in body and NOT_YOU in body
        assert re.search(r"\b20\d\d\b.*UTC", body)
        assert "token=" not in body and "/oauth/" not in body and "/reset" not in body
        assert not re.search(r"(?<!\d)\d{6}(?!\d)", body.replace("UTC", ""))


@pytest.mark.journey("J46.13")
def test_a_changed_password_is_told_in_the_saved_template_and_a_refused_change_is_not(world, smtp):  # noqa: F811
    """Given mail is set up with a saved e-mail template and a person who has set their password
    (the first password sends nothing). When they change it with a wrong current password, nothing
    is queued; with the right one, a message says the password was changed, when, and to contact
    an administrator if it was not them, inside the template, with no link or code."""
    _save(world, smtp)
    ok(world.api.put("/mail-template", {"markdown": BRANDED}))
    _person(world, "mei")
    assert _sent(world, smtp) == []
    token = _sign_in(_browser(world), "mei")

    wrong = {"currentPassword": "not-the-password-1", "newPassword": NEW}
    refused(_own(world, token, "POST", "/me/password", wrong), 422, "PASSWORD_INCORRECT")
    refused(
        _own(
            world, token, "POST", "/me/password", {"currentPassword": PASSWORD, "newPassword": "x"}
        ),
        422,
        "PASSWORD_REJECTED",
    )
    assert _sent(world, smtp) == []

    ok(
        _own(
            world, token, "POST", "/me/password", {"currentPassword": PASSWORD, "newPassword": NEW}
        ),
        204,
    )
    [mail] = _sent(world, smtp)
    _is_security_message(mail, "your password was changed")
    assert "Dear Mei" in _text(mail) and "Dear Mei" in _html(mail)
    assert "was changed" in _text(mail) and PASSWORD not in _text(mail) and NEW not in _text(mail)
    assert ok(world.api.get("/mail-settings"))["outbox"]["pending"] == 0


@pytest.mark.journey("J46.13")
def test_a_password_reset_with_a_link_is_told_but_a_first_password_is_not(world, smtp):  # noqa: F811
    """Given mail is set up and a person with a password. When an administrator makes them a link
    (no message about it beyond the link) and they use it, then a message says the password was
    reset; a link used by a person with no password yet, to choose their first one, sends none."""
    _save(world, smtp)
    new = ok(world.api.post("/users", {"email": "ada@example.org", "name": "Ada"}), 201)
    first = _set_password(_browser(world), _reset_link(world, new))
    assert first.status_code == 200 and _sent(world, smtp) == []

    mei = _person(world, "mei")
    assert _sent(world, smtp) == []
    done = _set_password(_browser(world), _reset_link(world, mei), NEW)
    assert done.status_code == 200, done.text
    [mail] = _sent(world, smtp)
    _is_security_message(mail, "your password was reset")


@pytest.mark.journey("J46.13")
def test_an_authenticator_app_added_or_removed_is_told_whoever_removes_it(world, smtp):  # noqa: F811
    """Given mail is set up and a person with a password. When a wrong code is tried, nothing is
    queued; when they confirm an app, a message says one was added; when they remove it with a code,
    and when an administrator removes a second app they set up again, a message says it was removed
    each time."""
    _save(world, smtp)
    mei = _person(world, "mei")
    token = _sign_in(_browser(world), "mei")
    made = ok(_own(world, token, "POST", "/me/second-factor"), 201)
    refused(_own(world, token, "POST", "/me/second-factor/confirmation", {"code": "000000"}), 422,
            "CODE_INCORRECT")  # fmt: skip
    assert _sent(world, smtp) == []

    secret, _ = _set_up_again(world, token, made)
    [added] = _sent(world, smtp)
    _is_security_message(added, "an authenticator app was added")

    refused(_own(world, token, "DELETE", "/me/second-factor", {"code": "000000"}), 422,
            "CODE_INCORRECT")  # fmt: skip
    assert _sent(world, smtp) == []
    ok(_own(world, token, "DELETE", "/me/second-factor", {"code": _totp(secret, ahead=1)}), 204)
    [removed] = _sent(world, smtp)
    _is_security_message(removed, "the authenticator app was removed")

    _set_up(world, token)
    assert len(_sent(world, smtp)) == 1
    ok(world.api.delete(f"/users/{mei['id']}/second-factor"), 204)
    [by_administrator] = _sent(world, smtp)
    _is_security_message(by_administrator, "the authenticator app was removed")


def _set_up_again(world, token: str, made: dict) -> tuple[str, list[str]]:
    """Confirm the app already begun (the first wrong code was tried by the test)."""
    confirmed = ok(
        _own(
            world, token, "POST", "/me/second-factor/confirmation", {"code": _totp(made["secret"])}
        )
    )
    return made["secret"], confirmed["recoveryCodes"]


@pytest.mark.journey("J46.13")
def test_a_passkey_added_or_removed_is_told_whoever_removes_it(world, smtp):  # noqa: F811
    """Given mail is set up and a person with a password. When they add a passkey (a refused one
    first), a message says one was added; when they remove it, and when an administrator removes
    another, a message says it was removed each time; a removal refused for a wrong password sends
    none."""
    _save(world, smtp)
    mei = _person(world, "mei")
    browser = _browser(world)
    token = _sign_in(browser, "mei")
    authenticator = SoftwareAuthenticator(_origin(world))
    assert _add(browser, authenticator, "Laptop", verified=False).status_code == 422
    assert _sent(world, smtp) == []
    assert _add(browser, authenticator, "Laptop").status_code == 200
    [added] = _sent(world, smtp)
    _is_security_message(added, "a passkey was added")

    path = f"/me/passkeys/{ok(_own(world, token, 'GET', '/me/passkeys'))['items'][0]['id']}"
    refused(
        _own(world, token, "DELETE", path, {"proof": "not-the-password"}), 422, "CODE_INCORRECT"
    )
    assert _sent(world, smtp) == []
    ok(_own(world, token, "DELETE", path, {"proof": PASSWORD}), 204)
    [removed] = _sent(world, smtp)
    _is_security_message(removed, "a passkey was removed")

    assert _add(browser, SoftwareAuthenticator(_origin(world)), "Phone").status_code == 200
    assert len(_sent(world, smtp)) == 1
    [phone] = ok(world.api.get(f"/users/{mei['id']}/passkeys"))["items"]
    ok(world.api.delete(f"/users/{mei['id']}/passkeys/{phone['id']}"), 204)
    [by_administrator] = _sent(world, smtp)
    _is_security_message(by_administrator, "a passkey was removed")


@pytest.mark.journey("J46.13")
def test_without_mail_the_change_still_happens_and_nothing_is_queued_later(world, smtp):  # noqa: F811
    """Given mail is not set up. When a person changes their password, then the change is made and
    no message is waiting once mail is set up afterwards."""
    _person(world, "mei")
    token = _sign_in(_browser(world), "mei")
    ok(
        _own(
            world, token, "POST", "/me/password", {"currentPassword": PASSWORD, "newPassword": NEW}
        ),
        204,
    )
    _sign_in(_browser(world), "mei", NEW)
    _save(world, smtp)
    assert ok(world.api.get("/mail-outbox"))["items"] == []
