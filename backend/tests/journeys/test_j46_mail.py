"""J46 — send mail (USER_JOURNEYS.md § Security, 0.12 M1).

A Security administrator saves the SMTP connection, proves it with a test message, and the engine
sends what other journeys queue (a new person's link, a reset) in the background. The harness server
(``tests/smtp_server.py``) is a real SMTP server on ``127.0.0.1`` with a certificate made for the
run, which the engine verifies as it would any server's; ``SSL_CERT_FILE`` makes it trusted. The
journey application does not start the sender's thread: a test runs it with a clock it moves forward.
No route queues mail yet, so a test queues it as the engine's own code will (``queue_mail``).
"""

import json
import socket
from datetime import UTC, datetime, timedelta

import pytest
from scenario import ok, queue_mail, refused, send_mail
from smtp_server import FakeSmtp
from sqlalchemy import text
from test_j40_authorization import _client

from app.engine.identity.resealing import reseal
from app.engine.mail import templates

PASSWORD = "smtp-secret-9"
LOGIN = ("mailer", PASSWORD)
LINK = "https://refiroo.example.org/reset?token=one-time-token"


@pytest.fixture
def smtp(monkeypatch):
    """A server with a login, secured by STARTTLS, whose certificate the engine trusts."""
    with FakeSmtp(login=LOGIN) as server:
        monkeypatch.setenv("SSL_CERT_FILE", str(server.certificate_file))
        yield server


def _settings(server: FakeSmtp, **changes) -> dict:
    return {
        "host": "127.0.0.1",
        "port": server.port,
        "security": "starttls",
        "username": LOGIN[0],
        "password": PASSWORD,
        "fromAddress": "refiroo@example.org",
        **changes,
    }


def _save(world, server: FakeSmtp, **changes) -> dict:
    return ok(world.api.put("/mail-settings", _settings(server, **changes)))


def _reset_mail(name: str = "Ada") -> templates.Rendered:
    return templates.password_reset("refiroo", name, LINK, 24)


def _database(world, statement: str):
    from sqlalchemy import text

    with world.api.client.app.state.session_factory() as session:
        return session.execute(text(statement)).all()


@pytest.mark.journey("J46.1")
def test_mail_is_set_up_and_proved_with_a_test_message(world, smtp):
    """Given an instance with no mail settings, when the administrator saves a server with a login
    and sends a test message, then the settings are answered without the password, the message
    reaches the server from the saved address with the link the application is reached at, and
    the change is a security event that never holds the password."""
    before = ok(world.api.get("/mail-settings"))
    assert before["configured"] is False and before["host"] is None and before["version"] is None
    assert before["applicationUrlIsDefault"] is True and before["applicationUrl"]
    assert before["outbox"] == {"pending": 0, "sent": 0, "failed": 0}

    saved = _save(world, smtp, applicationUrl="https://refiroo.example.org/")
    assert saved["configured"] is True and saved["version"] == 1
    assert saved["host"] == "127.0.0.1" and saved["security"] == "starttls"
    assert saved["username"] == LOGIN[0] and saved["passwordSet"] is True
    assert saved["applicationUrl"] == "https://refiroo.example.org"
    assert saved["applicationUrlIsDefault"] is False
    assert PASSWORD not in json.dumps(ok(world.api.get("/mail-settings")))

    sent = ok(world.api.post("/mail-settings/test", {"to": "ada@example.org"}))
    assert sent == {"sentTo": "ada@example.org"}
    [message] = smtp.messages
    assert message["To"] == "ada@example.org" and message["From"] == "refiroo@example.org"
    assert "test message" in message["Subject"]
    assert "https://refiroo.example.org\n" in message.get_content().replace("\r\n", "\n")

    events = ok(world.api.get("/security-events", aggregateType="mail-settings"))["items"]
    assert [(e["action"], e["aggregateId"]) for e in events] == [("created", "mail")]
    assert "password" in events[0]["details"]["changedFields"]
    assert PASSWORD not in json.dumps(events)


@pytest.mark.journey("J46.1")
def test_saving_again_replaces_the_settings_and_keeps_the_password(world, smtp):
    """Given saved settings, when they are saved again without a password, then the login still
    works; a stale or missing version is refused; removing the user name removes the password."""
    _save(world, smtp)
    changed = ok(
        world.api.put(
            "/mail-settings",
            {
                **_settings(smtp, fromAddress="mail@example.org"),
                "expectedVersion": 1,
                "password": None,
            },
        )
    )
    assert changed["version"] == 2 and changed["passwordSet"] is True
    ok(world.api.post("/mail-settings/test", {"to": "ada@example.org"}))
    assert smtp.messages[0]["From"] == "mail@example.org"

    same = ok(
        world.api.put(
            "/mail-settings",
            {
                **_settings(smtp, fromAddress="mail@example.org"),
                "expectedVersion": 2,
                "password": None,
            },
        )
    )
    assert same["version"] == 2

    stale = refused(
        world.api.put("/mail-settings", {**_settings(smtp), "expectedVersion": 1}),
        409,
        "VERSION_CONFLICT",
    )
    assert stale["details"] == {"currentVersion": 2}
    refused(world.api.put("/mail-settings", _settings(smtp)), 409, "VERSION_CONFLICT")

    open_relay = ok(
        world.api.put(
            "/mail-settings",
            {
                "expectedVersion": 2,
                **_settings(smtp, fromAddress="mail@example.org", username=None, password=None),
            },
        )
    )
    assert open_relay["username"] is None and open_relay["passwordSet"] is False
    events = ok(world.api.get("/security-events", aggregateType="mail-settings"))["items"]
    assert [e["action"] for e in events] == ["updated", "updated", "created"]
    assert events[0]["details"]["changedFields"] == ["username", "password"]


@pytest.mark.journey("J46.2")
def test_a_test_message_names_what_failed(world, smtp, monkeypatch):
    """Given saved settings, when the test message cannot be sent, then the refusal says what failed
    and names it in `details.kind`: the connection, TLS, the login, the recipient."""
    refused(
        world.api.post("/mail-settings/test", {"to": "ada@example.org"}), 409, "MAIL_NOT_SET_UP"
    )

    def failed(to: str = "ada@example.org") -> dict:
        error = refused(world.api.post("/mail-settings/test", {"to": to}), 422, "MAIL_SEND_FAILED")
        assert (
            error["details"]["reason"] == error["message"] and "Traceback" not in error["message"]
        )
        assert PASSWORD not in error["message"]
        return error["details"]

    _save(world, smtp, password="not-the-password")
    assert failed()["kind"] == "login"

    def _save_again(**changes) -> dict:
        version = ok(world.api.get("/mail-settings"))["version"]
        body = {"expectedVersion": version, **_settings(smtp, **changes)}
        return ok(world.api.put("/mail-settings", body))

    _save_again(password=PASSWORD)
    smtp.refuse["gone@example.org"] = (550, "5.1.1 no such mailbox")
    assert failed("gone@example.org")["kind"] == "recipient"
    assert smtp.messages == []

    _save_again(security="tls")
    assert failed()["kind"] == "tls"

    monkeypatch.delenv("SSL_CERT_FILE")
    _save_again(security="starttls")
    assert failed()["kind"] == "tls"

    with socket.socket() as closed:
        closed.bind(("127.0.0.1", 0))
        unused = closed.getsockname()[1]
    _save_again(port=unused)
    assert failed()["kind"] == "connection"


@pytest.mark.journey("J46.1")
def test_a_new_host_or_port_needs_the_password_sent_again(world, smtp):
    """Given saved settings with a login, when the host or the port changes and no password is sent,
    then it is refused naming the password and nothing changes; with a password it is saved; with the
    host and port unchanged the saved password is kept (0.12 E1, C6)."""
    _save(world, smtp)
    for change in ({"port": smtp.port + 1}, {"host": "localhost"}):
        error = refused(
            world.api.put(
                "/mail-settings",
                {**_settings(smtp, **change), "expectedVersion": 1, "password": None},
            ),
            422,
            "MAIL_PASSWORD_REQUIRED",
        )
        assert error["details"] == {"field": "password"}
        assert "password" in error["message"]
    unchanged = ok(world.api.get("/mail-settings"))
    assert unchanged["version"] == 1 and unchanged["host"] == "127.0.0.1"
    assert unchanged["port"] == smtp.port and unchanged["passwordSet"] is True

    moved = ok(
        world.api.put("/mail-settings", {**_settings(smtp, host="localhost"), "expectedVersion": 1})
    )
    assert moved["host"] == "localhost" and moved["version"] == 2 and moved["passwordSet"] is True

    kept = ok(
        world.api.put(
            "/mail-settings",
            {
                **_settings(smtp, host="localhost", fromAddress="b@example.org"),
                "expectedVersion": 2,
                "password": None,
            },
        )
    )
    assert kept["version"] == 3 and kept["passwordSet"] is True


@pytest.mark.journey("J46.2")
def test_a_login_is_refused_over_an_unencrypted_connection(world, smtp):
    """When the administrator saves a user name with an unencrypted connection, then it is refused
    and nothing is saved; a user name needs a password the first time."""
    error = refused(
        world.api.put("/mail-settings", _settings(smtp, security="none")),
        422,
        "MAIL_INSECURE_LOGIN",
    )
    assert "TLS" in error["message"]
    refused(
        world.api.put("/mail-settings", _settings(smtp, password=None)),
        422,
        "MAIL_PASSWORD_REQUIRED",
    )
    assert ok(world.api.get("/mail-settings"))["configured"] is False
    plain = ok(
        world.api.put(
            "/mail-settings", _settings(smtp, security="none", username=None, password=None)
        )
    )
    assert plain["security"] == "none" and plain["username"] is None


@pytest.mark.journey("J46.3")
def test_queued_mail_is_sent_in_the_background_and_retried(world, smtp):
    """Given saved settings and a reset message queued, when the server is down, then the message
    waits, is tried again after 30 seconds and then 60, and no request was held; when the server is
    back it is sent, its text is gone from the database, and the outbox says so."""
    _save(world, smtp)
    start = datetime.now(UTC)
    message_id = queue_mail(world, "ada@example.org", _reset_mail(), now=start)
    assert [m["status"] for m in ok(world.api.get("/mail-outbox"))["items"]] == ["pending"]
    assert _database(world, "SELECT body IS NOT NULL FROM mail_outbox") == [(True,)]
    assert b"one-time-token" not in bytes(_database(world, "SELECT body FROM mail_outbox")[0][0])

    smtp.down = True
    assert send_mail(world, start) == 1
    [waiting] = ok(world.api.get("/mail-outbox", status="pending"))["items"]
    assert waiting["id"] == message_id and waiting["attempts"] == 1
    assert waiting["lastErrorKind"] == "connection" and waiting["lastError"]
    assert datetime.fromisoformat(waiting["nextAttemptAt"]) == start + timedelta(seconds=30)

    assert send_mail(world, start + timedelta(seconds=29)) == 0
    assert send_mail(world, start + timedelta(seconds=30)) == 1
    [waiting] = ok(world.api.get("/mail-outbox", status="pending"))["items"]
    assert waiting["attempts"] == 2
    assert datetime.fromisoformat(waiting["nextAttemptAt"]) == start + timedelta(seconds=90)

    smtp.down = False
    assert send_mail(world, start + timedelta(seconds=90)) == 1
    [sent] = ok(world.api.get("/mail-outbox", status="sent"))["items"]
    assert sent["id"] == message_id and sent["attempts"] == 3 and sent["lastError"] is None
    assert sent["nextAttemptAt"] is None and sent["finishedAt"]
    assert ok(world.api.get("/mail-settings"))["outbox"] == {"pending": 0, "sent": 1, "failed": 0}
    [mail] = smtp.messages
    assert mail["To"] == "ada@example.org" and LINK in mail.get_content()
    assert "Hello Ada" in mail.get_content()
    assert _database(world, "SELECT body FROM mail_outbox") == [(None,)]
    assert "body" not in json.dumps(ok(world.api.get("/mail-outbox")))
    assert LINK not in json.dumps(ok(world.api.get("/mail-outbox")))


@pytest.mark.journey("J46.4")
def test_mail_that_cannot_be_sent_is_given_up_with_its_reason(world, smtp):
    """Given a message for an address the server refuses for good and one that waits on a server
    that stays down, when the sender runs, then the first fails at once with the server's answer,
    the second after 24 hours, and the failed list says why; neither text stays in the database."""
    _save(world, smtp)
    start = datetime.now(UTC)
    smtp.refuse["gone@example.org"] = (550, "5.1.1 no such mailbox")
    gone = queue_mail(world, "gone@example.org", _reset_mail("Gone"), now=start)
    assert send_mail(world, start) == 1
    [failed] = ok(world.api.get("/mail-outbox", status="failed"))["items"]
    assert (
        failed["id"] == gone and failed["attempts"] == 1 and failed["lastErrorKind"] == "recipient"
    )
    assert "550" in failed["lastError"] and failed["nextAttemptAt"] is None

    smtp.down = True
    waiting = queue_mail(world, "ada@example.org", _reset_mail(), now=start)
    assert send_mail(world, start) == 1
    assert send_mail(world, start + timedelta(hours=23)) == 1
    assert [m["status"] for m in ok(world.api.get("/mail-outbox", status="pending"))["items"]] == [
        "pending"
    ]

    assert send_mail(world, start + timedelta(hours=24, minutes=1)) == 0
    given_up = {m["id"]: m for m in ok(world.api.get("/mail-outbox", status="failed"))["items"]}[
        waiting
    ]
    assert given_up["lastError"].startswith(
        "Not sent within 24 hours. Last error: Could not connect"
    )
    assert given_up["lastErrorKind"] == "connection" and given_up["finishedAt"]
    assert ok(world.api.get("/mail-settings"))["outbox"] == {"pending": 0, "sent": 0, "failed": 2}
    assert _database(world, "SELECT count(*) FROM mail_outbox WHERE body IS NOT NULL") == [(0,)]
    assert smtp.messages == []

    page = ok(world.api.get("/mail-outbox", pageSize=1))
    assert len(page["items"]) == 1 and page["nextCursor"]
    rest = ok(world.api.get("/mail-outbox", pageSize=1, cursor=page["nextCursor"]))
    assert {page["items"][0]["id"], rest["items"][0]["id"]} == {gone, waiting}


@pytest.mark.journey("J46.5")
def test_without_settings_nothing_is_sent_and_nothing_else_changes(world, smtp):
    """Given no settings, when something asks to queue mail, then it is refused as not set up; when
    the settings are removed, a message already waiting stays pending, reading why, and removing
    them again is refused."""
    from app.errors import ApiError

    with pytest.raises(ApiError) as refusal:
        queue_mail(world, "ada@example.org", _reset_mail())
    assert refusal.value.code == "MAIL_NOT_SET_UP" and refusal.value.status == 409
    assert send_mail(world) == 0
    assert ok(world.api.get("/mail-outbox"))["items"] == []

    _save(world, smtp)
    start = datetime.now(UTC)
    queue_mail(world, "ada@example.org", _reset_mail(), now=start)
    assert world.api.delete("/mail-settings").status_code == 204
    assert ok(world.api.get("/mail-settings"))["configured"] is False
    assert send_mail(world, start) == 1
    [waiting] = ok(world.api.get("/mail-outbox"))["items"]
    assert waiting["status"] == "pending" and waiting["lastErrorKind"] == "not_set_up"
    assert smtp.messages == []
    refused(world.api.delete("/mail-settings"), 409, "MAIL_NOT_SET_UP")
    events = ok(world.api.get("/security-events", aggregateType="mail-settings"))["items"]
    assert [e["action"] for e in events] == ["deleted", "created"]


@pytest.mark.journey("J46.6")
def test_only_a_security_administrator_manages_mail(world, smtp):
    """Given a Reader of everything and a Security administrator, when each calls the mail routes,
    then the Reader is refused every one and the administrator is not."""
    _, reader = _client(world, "Reads everything", ("reader", {"instance": True}))
    _, security = _client(world, "Security only", ("security-admin", {"instance": True}))
    calls = (
        ("GET", "/mail-settings", None),
        ("PUT", "/mail-settings", _settings(smtp)),
        ("POST", "/mail-settings/test", {"to": "ada@example.org"}),
        ("DELETE", "/mail-settings", None),
        ("GET", "/mail-outbox", None),
    )
    for method, path, body in calls:
        denied = reader.api.client.request(method, f"/api/v1{path}", json=body)
        assert refused(denied, 403, "FORBIDDEN")["details"]["action"] == "security.manage"
    ok(security.api.put("/mail-settings", _settings(smtp)))
    assert ok(security.api.get("/mail-settings"))["configured"] is True
    ok(security.api.post("/mail-settings/test", {"to": "ada@example.org"}))
    assert ok(security.api.get("/mail-outbox"))["items"] == []


@pytest.mark.journey("J43.5", "J46.6")
def test_the_mail_password_and_queued_mail_are_re_sealed_with_the_other_secrets(world, smtp):
    """Given a saved password and a message waiting, when the secrets are checked under the current
    key, then both are among those that open."""
    _save(world, smtp)
    queue_mail(world, "ada@example.org", _reset_mail())
    app = world.api.client.app
    with app.state.session_factory() as session:
        counts = reseal(
            session,
            app.state.identity_settings.encryption_key,
            app.state.identity_settings.encryption_key,
            check_only=True,
        )
    assert counts["mail server password"] == 1 and counts["queued mail"] == 1


def _person(world, username: str, email: str | None) -> dict:
    return ok(
        world.api.post("/users", {"username": username, "name": username.title(), "email": email}),
        201,
    )


def _link_works(world, link: str) -> bool:
    response = world.api.client.get(link.replace(world.api.client.base_url.host, "testserver"))
    return response.status_code == 200


def _token(link: str) -> str:
    from urllib.parse import parse_qs, urlsplit

    return parse_qs(urlsplit(link).query)["token"][0]


@pytest.mark.journey("J46.7")
def test_a_new_persons_link_is_mailed_and_still_shown_once(world, smtp):
    """Given mail is set up and a person with an address and no password, when the administrator
    makes their link with `send`, then the answer names the address and still holds the link, the
    mail arrives once the sender has run, welcomes the person with that same link, and the link
    sets a password; a person who has a password is told it is a new password instead."""
    _save(world, smtp, applicationUrl="https://refiroo.example.org")
    ada = _person(world, "ada", "ada@example.org")

    made = ok(world.api.post(f"/users/{ada['id']}/password-reset", {"send": True}), 201)
    assert made["sentTo"] == "ada@example.org" and made["url"] and made["expiresAt"]
    assert smtp.messages == []
    assert ok(world.api.get("/mail-settings"))["outbox"]["pending"] == 1

    assert send_mail(world) == 1
    [mail] = smtp.messages
    text = mail.get_content()
    assert mail["To"] == "ada@example.org" and "Your" in mail["Subject"]
    assert "Hello Ada" in text and made["url"] in text

    token = _token(made["url"])
    browser = world.api.client
    done = browser.post(
        "/oauth/password",
        data={"token": token, "password": "a-long-enough-pass-1", "repeat": "a-long-enough-pass-1"},
    )
    assert done.status_code == 200, done.text

    again = ok(world.api.post(f"/users/{ada['id']}/password-reset", {"send": True}), 201)
    send_mail(world)
    assert smtp.messages[-1]["Subject"].startswith("Choose a new")
    assert again["url"] in smtp.messages[-1].get_content()


@pytest.mark.journey("J46.7")
def test_without_send_nothing_is_queued(world, smtp):
    """Given mail is set up, when a link is made without `send`, then it is answered once as
    before, names no address, and no message is queued."""
    _save(world, smtp)
    ada = _person(world, "ada", "ada@example.org")
    made = ok(world.api.post(f"/users/{ada['id']}/password-reset", {}), 201)
    assert made["url"] and made["sentTo"] is None
    assert ok(world.api.get("/mail-settings"))["outbox"] == {"pending": 0, "sent": 0, "failed": 0}


@pytest.mark.journey("J46.7")
def test_a_link_cannot_be_mailed_without_mail_or_an_address_and_the_earlier_link_stays(world, smtp):
    """Given a person with a link, when the administrator asks to mail a new one without mail set
    up, or for a person with no address, then it is refused by code and the earlier link still
    works."""
    ada = _person(world, "ada", "ada@example.org")
    first = ok(world.api.post(f"/users/{ada['id']}/password-reset", {}), 201)

    refused(
        world.api.post(f"/users/{ada['id']}/password-reset", {"send": True}),
        409,
        "MAIL_NOT_SET_UP",
    )
    _save(world, smtp)
    bob = _person(world, "bob", None)
    bobs = ok(world.api.post(f"/users/{bob['id']}/password-reset", {}), 201)
    refused(world.api.post(f"/users/{bob['id']}/password-reset", {"send": True}), 409, "NO_EMAIL")

    for link in (first, bobs):
        page = world.api.client.get("/oauth/password", params={"token": _token(link["url"])})
        assert page.status_code == 200, page.text
    assert ok(world.api.get("/mail-settings"))["outbox"] == {"pending": 0, "sent": 0, "failed": 0}


@pytest.mark.journey("J46.9")
def test_an_administrator_stops_a_message_that_is_being_retried(world, smtp):
    """Given a message waiting for its next try on a server that is down, when the administrator
    stops it, then it fails at once saying so, its text is erased, and when the server is back
    nothing is sent; a message already finished cannot be stopped, nor one that does not exist."""
    _save(world, smtp)
    start = datetime.now(UTC)
    message_id = queue_mail(world, "ada@example.org", _reset_mail(), now=start)
    smtp.down = True
    assert send_mail(world, start) == 1

    stopped = ok(world.api.post(f"/mail-outbox/{message_id}/stop", {}))
    assert stopped["status"] == "failed" and stopped["lastError"] == "Stopped by an administrator"
    assert stopped["lastErrorKind"] == "stopped" and stopped["nextAttemptAt"] is None
    assert stopped["attempts"] == 1 and stopped["finishedAt"]
    assert _database(world, "SELECT body FROM mail_outbox") == [(None,)]
    assert ok(world.api.get("/mail-settings"))["outbox"] == {"pending": 0, "sent": 0, "failed": 1}

    smtp.down = False
    assert send_mail(world, start + timedelta(hours=1)) == 0
    assert smtp.messages == []
    refused(world.api.post(f"/mail-outbox/{message_id}/stop", {}), 409, "MESSAGE_NOT_WAITING")
    refused(world.api.post("/mail-outbox/no-such-message/stop", {}), 404, "NOT_FOUND")


@pytest.mark.journey("J46.9")
def test_a_message_being_sent_cannot_be_stopped_and_only_security_administration_may(world, smtp):
    """Given a message a sender holds, then stopping it is refused and the message is unchanged; a
    person without Security administration at the instance is refused."""
    _save(world, smtp)
    message_id = queue_mail(world, "ada@example.org", _reset_mail())
    with world.api.client.app.state.session_factory() as session:
        session.execute(
            text(
                "UPDATE mail_outbox SET lease_owner = 'other', "
                "lease_expires_at = now() + interval '5 minutes'"
            )
        )
        session.commit()
    refused(world.api.post(f"/mail-outbox/{message_id}/stop", {}), 409, "MESSAGE_BEING_SENT")
    assert ok(world.api.get("/mail-settings"))["outbox"]["pending"] == 1
    _, reader = _client(world, "Reads everything", ("reader", {"instance": True}))
    denied = reader.api.client.post(f"/api/v1/mail-outbox/{message_id}/stop", json={})
    assert refused(denied, 403, "FORBIDDEN")["details"]["action"] == "security.manage"
