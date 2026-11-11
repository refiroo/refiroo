"""J46.8 — a forgotten password, asked for on the application's sign-in screen (0.12 I6).

A person who cannot sign in asks for a new password with their e-mail address and gets
a link to the application's reset page. Whoever asks is told the same thing, so nothing shows which
accounts exist; a link goes only to an active person who has a local password and an address; asking
is slowed per name and per address, as sign-ins are; the link works once and the new password meets
the engine's rules. Every case runs on two configurations through the public API, as the browser
application calls it, with a harness SMTP server receiving what is sent.
"""

import pytest
from scenario import ok, send_mail
from test_j39_sign_in import PASSWORD, _browser, _pkce, _request
from test_j46_mail import _person, _save, _token, smtp  # noqa: F401  (smtp is a fixture)

REQUEST = "/oauth/sign-in/reset-request"
PAGE = "/oauth/sign-in/reset"
APP = {"Origin": "http://localhost:5173"}
SET_TO = "a-new-long-enough-pass-7"


def _with_password(world, name: str, email: str) -> dict:
    """A person with a password, set through an administrator's link."""
    person = _person(world, name, email)
    link = ok(world.api.post(f"/users/{person['id']}/password-reset", {}), 201)
    done = _browser(world).post(
        "/oauth/password",
        data={"token": _token(link["url"]), "password": PASSWORD, "repeat": PASSWORD},
    )
    assert done.status_code == 200, done.text
    return person


def _ask(browser, email: str, expected: int = 202):
    response = browser.post(REQUEST, json={"email": email}, headers=APP)
    assert response.status_code == expected, f"{response.status_code}: {response.text[:300]}"
    return response.json()


def _outbox(world) -> dict:
    return ok(world.api.get("/mail-settings"))["outbox"]


@pytest.mark.journey("J46.8")
def test_a_person_asks_for_a_new_password_gets_a_link_and_signs_in_with_it(world, smtp):  # noqa: F811
    """Given a person with a password and an address. When they ask by e-mail address, then they are
    answered that a link was sent if there is such an account, a message reaches their address with
    a link to the application's reset page, the link says who it is for, and setting a password
    through it ends their sessions and lets them sign in with the new one; the link works once."""
    _save(world, smtp)
    ada = _with_password(world, "ada", "ada@example.org")
    browser = _browser(world)

    answer = _ask(browser, "Ada@Example.org")
    assert answer["status"] == "requested"
    assert send_mail(world) == 1
    [mail] = smtp.messages
    assert mail["To"] == "ada@example.org" and mail["Subject"].startswith("Choose a new")
    link = next(
        line
        for line in mail.get_body(("plain",)).get_content().splitlines()
        if "reset-password?token=" in line
    )
    assert link.startswith("http://localhost:5173/reset-password?token=")
    token = _token(link)

    shown = ok(browser.get(PAGE, params={"token": token}, headers=APP))
    assert shown["email"] == "ada@example.org" and shown["minLength"] >= 8 and shown["product"]

    done = browser.post(
        "/oauth/sign-in/reset",
        json={"token": token, "password": SET_TO, "repeat": SET_TO},
        headers=APP,
    )
    assert ok(done)["status"] == "password_set"
    again = browser.post(
        "/oauth/sign-in/reset",
        json={"token": token, "password": SET_TO, "repeat": SET_TO},
        headers=APP,
    )
    assert again.status_code == 410 and again.json()["error"] == "link_gone"
    assert browser.get(PAGE, params={"token": token}, headers=APP).status_code == 410

    _, challenge = _pkce()
    signed = browser.post(
        "/oauth/sign-in/password",
        json={"request": _request(challenge), "email": "ada@example.org", "password": SET_TO},
        headers=APP,
    )
    assert ok(signed)["status"] == "signed_in"
    old = browser.post(
        "/oauth/sign-in/password",
        json={"request": _request(challenge), "email": "ada@example.org", "password": PASSWORD},
        headers=APP,
    )
    assert old.status_code == 401 and old.json()["error"] == "wrong_credentials"
    assert ada["id"]


@pytest.mark.journey("J46.8")
def test_asking_says_the_same_to_everyone_and_writes_only_to_who_can_be_written_to(world, smtp):  # noqa: F811
    """Given mail is set up and an active person with a password, one with no password yet, one
    deactivated, and no one at `nobody@example.org`. When each is asked for by e-mail address, and
    the first again in other letters, then every answer is the same, and only the first two asks
    queue a message, both to the first person."""
    _save(world, smtp)
    _with_password(world, "ada", "ada@example.org")
    _person(world, "cy", "cy@example.org")
    dan = ok(world.api.get(f"/users/{_with_password(world, 'dan', 'dan@example.org')['id']}"))
    ok(world.api.patch(f"/users/{dan['id']}", {"active": False, "expectedVersion": dan["version"]}))
    browser = _browser(world)

    answers = [
        _ask(browser, name)
        for name in (
            "ada@example.org",
            "cy@example.org",
            "dan@example.org",
            "nobody@example.org",
            "ADA@Example.org",
        )
    ]
    assert all(answer == answers[0] for answer in answers)
    assert _outbox(world)["pending"] == 2
    send_mail(world)
    assert [mail["To"] for mail in smtp.messages] == ["ada@example.org"] * 2


@pytest.mark.journey("J46.8")
def test_asking_is_slowed_whatever_the_name_matches_and_sign_in_is_not_affected(world, smtp):  # noqa: F811
    """Given mail is set up. When the same name is asked for again and again (three asks are free, then each
    waits twice as long as the last), then an ask is
    refused with the seconds to wait, for a person who exists and for one who does not alike, and
    it queued nothing; the person can still sign in meanwhile."""
    _save(world, smtp)
    _with_password(world, "ada", "ada@example.org")
    browser = _browser(world)
    slowed = {}
    for name in ("ada@example.org", "ghost@example.org"):
        taken = 0
        while True:
            response = browser.post(REQUEST, json={"email": name}, headers=APP)
            if response.status_code == 429:
                slowed[name] = response.json()
                break
            assert response.status_code == 202 and taken < 6, response.text
            taken += 1
        assert taken >= 3, f"{name}: slowed after only {taken} asks"
    assert slowed["ada@example.org"]["error"] == slowed["ghost@example.org"]["error"] == "slowed"
    assert (
        slowed["ada@example.org"]["waitSeconds"] >= 1
        and slowed["ghost@example.org"]["waitSeconds"] >= 1
    )
    queued = _outbox(world)["pending"]
    _ask(browser, "ada@example.org", 429)
    assert _outbox(world)["pending"] == queued

    _, challenge = _pkce()
    signed = browser.post(
        "/oauth/sign-in/password",
        json={"request": _request(challenge), "email": "ada@example.org", "password": PASSWORD},
        headers=APP,
    )
    assert ok(signed)["status"] == "signed_in"


def _mailed_token(outbox, index: int) -> str:
    body = outbox.messages[index].get_body(("plain",)).get_content()
    return _token(next(line for line in body.splitlines() if "reset-password?token=" in line))


@pytest.mark.journey("J46.8")
def test_an_ask_by_address_does_not_cancel_a_link_an_administrator_made(world, smtp):  # noqa: F811
    """Given an administrator's unexpired link for a person. When anyone asks for that person's
    address, then the administrator's link still opens its page and sets the password, and the
    message the ask sent carries a link of its own; when the address is asked for again, the first
    mailed link is replaced by the second, one link from the mail flow."""
    _save(world, smtp)
    ada = _with_password(world, "ada", "ada@example.org")
    theirs = _token(ok(world.api.post(f"/users/{ada['id']}/password-reset", {}), 201)["url"])
    browser = _browser(world)

    _ask(browser, "ada@example.org")
    _ask(browser, "ada@example.org")
    assert send_mail(world) == 2
    first, second = _mailed_token(smtp, 0), _mailed_token(smtp, 1)
    assert len({theirs, first, second}) == 3
    assert browser.get(PAGE, params={"token": first}, headers=APP).status_code == 410
    assert browser.get(PAGE, params={"token": second}, headers=APP).status_code == 200
    assert browser.get(PAGE, params={"token": theirs}, headers=APP).status_code == 200
    done = browser.post(
        "/oauth/sign-in/reset",
        json={"token": theirs, "password": SET_TO, "repeat": SET_TO},
        headers=APP,
    )
    assert ok(done)["status"] == "password_set"


@pytest.mark.journey("J46.8")
def test_using_one_link_ends_the_persons_other_links(world, smtp):  # noqa: F811
    """Given an administrator's link and one the person asked for. When the asked-for link sets the
    password, then the administrator's link is gone, on its page and when used, and the password is
    the one set."""
    _save(world, smtp)
    ada = _with_password(world, "ada", "ada@example.org")
    theirs = _token(ok(world.api.post(f"/users/{ada['id']}/password-reset", {}), 201)["url"])
    browser = _browser(world)
    _ask(browser, "ada@example.org")
    assert send_mail(world) == 1
    mailed = _mailed_token(smtp, 0)

    done = browser.post(
        "/oauth/sign-in/reset",
        json={"token": mailed, "password": SET_TO, "repeat": SET_TO},
        headers=APP,
    )
    assert ok(done)["status"] == "password_set"
    assert browser.get(PAGE, params={"token": theirs}, headers=APP).status_code == 410
    again = browser.post(
        "/oauth/sign-in/reset",
        json={
            "token": theirs,
            "password": "yet-another-long-pass-9",
            "repeat": "yet-another-long-pass-9",
        },
        headers=APP,
    )
    assert again.status_code == 410 and again.json()["error"] == "link_gone"


@pytest.mark.journey("J46.8")
def test_the_screen_offers_the_reset_only_where_it_can_finish(world, smtp):  # noqa: F811
    """Given no mail settings. Then the options do not offer a reset, the reset page says it is not
    available and an ask is refused `409 mail_not_set_up` without counting. When mail is set up the
    options offer it."""
    browser = _browser(world)
    _, challenge = _pkce()
    options = {"params": _request(challenge), "headers": APP}
    assert ok(browser.get("/oauth/sign-in/options", **options))["reset"] is False
    assert ok(browser.get(PAGE, headers=APP))["available"] is False
    for _ in range(5):
        assert _ask(browser, "ada@example.org", 409)["error"] == "mail_not_set_up"

    _save(world, smtp)
    assert ok(browser.get("/oauth/sign-in/options", **options))["reset"] is True
    assert ok(browser.get(PAGE, headers=APP))["available"] is True
    assert _ask(browser, "ada@example.org")["status"] == "requested"


@pytest.mark.journey("J46.8")
def test_the_new_password_meets_the_rules_and_a_replaced_link_is_gone(world, smtp):  # noqa: F811
    """Given a link. When the password is too short, or the two differ, then the answer says why and
    the link still works; when a newer link has replaced it, the old one is gone; a post from another
    site is refused; an administrator's link points to the application's page too."""
    _save(world, smtp)
    ada = _with_password(world, "ada", "ada@example.org")
    first = ok(world.api.post(f"/users/{ada['id']}/password-reset", {}), 201)
    assert first["url"].startswith("http://localhost:5173/reset-password?token=")
    old = _token(first["url"])
    second = _token(ok(world.api.post(f"/users/{ada['id']}/password-reset", {}), 201)["url"])
    browser = _browser(world)
    assert browser.get(PAGE, params={"token": old}, headers=APP).status_code == 410

    def post(password: str, repeat: str, **headers):
        return browser.post(
            "/oauth/sign-in/reset",
            json={"token": second, "password": password, "repeat": repeat},
            headers={**APP, **headers},
        )

    short = post("short", "short")
    assert short.status_code == 422 and short.json()["error"] == "password_rejected"
    differ = post(SET_TO, SET_TO + "x")
    assert differ.status_code == 422 and differ.json()["error"] == "passwords_differ"
    foreign = post(SET_TO, SET_TO, Origin="https://elsewhere.example")
    assert foreign.status_code == 403 and foreign.json()["error"] == "foreign_origin"
    assert (
        ok(browser.get(PAGE, params={"token": second}, headers=APP))["email"] == "ada@example.org"
    )
    assert ok(post(SET_TO, SET_TO))["status"] == "password_set"


@pytest.mark.journey("J46.8")
def test_a_reset_reads_the_same_whoever_asked_for_it(world, smtp):  # noqa: F811
    """Given a person with a password. When an administrator mails their link and when they ask on
    the sign-in screen, then both messages are the same message (subject and text, apart from the
    link) and name the product as the test message does (the model's name, or refiroo for a default one)."""
    _save(world, smtp)
    ada = _with_password(world, "ada", "ada@example.org")
    ok(world.api.post(f"/users/{ada['id']}/password-reset", {"send": True}), 201)
    _ask(_browser(world), "ada@example.org")
    ok(world.api.post("/mail-settings/test", {"to": "ada@example.org"}))
    send_mail(world)
    test, by_administrator, by_person = smtp.messages[-3:]  # the test message goes at once
    assert test["Subject"].endswith("test message"), [m["Subject"] for m in smtp.messages]

    def text(mail) -> str:
        return "\n".join(
            "<link>" if "token=" in line else line
            for line in mail.get_body(("plain",)).get_content().splitlines()
        )

    assert by_administrator["Subject"] == by_person["Subject"]
    assert text(by_administrator) == text(by_person)
    # The name is the model's own, or refiroo where it keeps a default name; the same in all three.
    product = test["Subject"].removesuffix(": test message")
    assert product in by_person["Subject"] and product in by_administrator["Subject"]
