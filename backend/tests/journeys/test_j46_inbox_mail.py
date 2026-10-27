"""J46.10 — inbox notices by mail (0.12 M2).

A person may be mailed one plain-text message per inbox notice. It is off until the person switches
it on (``/me/notification-mail``), names the kind of event only and links to the application. The
approver is a person who signs in as the browser does (a client has an inbox but no mail); the
submitter is a client, as in J42.5. Notices arrive through the API (a submission); no state is
written from outside it. The harness server (``tests/smtp_server.py``) receives what the sender
sends; a test runs the sender itself (``send_mail``), as in J46.
"""

import pytest
from scenario import W1, ok, refused, send_mail
from test_j39_sign_in import _browser, _reset_link, _set_password, _sign_in
from test_j40_authorization import _as, _client, _grant
from test_j42_approvals import _decide, _proposal, _submit
from test_j46_mail import _person, _save, smtp  # noqa: F401 - a fixture

SWITCH = "/me/notification-mail"
APPLICATION = "https://refiroo.example.org"
SECRET_NAME = "Quarterly pricing rework"
SECRET_COMMENT = "Please look at the Berlin numbers"


def _approver(world, username: str = "olga", email: str | None = "olga@example.org"):
    """A person with a password who may approve in the workspace, and the world as they see it."""
    person = _person(world, username, email)
    response = _set_password(_browser(world), _reset_link(world, person))
    assert response.status_code == 200, response.text
    _grant(world, "user", person["id"], "owner", workspaceKey=W1)
    return person, _as(world, _sign_in(_browser(world), username))


def _submitter(world):
    return _client(world, "contributor", ("contributor", {"workspaceKey": W1}))[1]


def _submit_one(world, submitter, name: str = SECRET_NAME, comment: str = SECRET_COMMENT) -> dict:
    change_set = _proposal(world, submitter, name)
    ok(_submit(submitter, change_set, comment), 201)
    return change_set


def _database(world, statement: str):
    from sqlalchemy import text

    with world.api.client.app.state.session_factory() as session:
        return session.execute(text(statement)).all()


@pytest.mark.journey("J46.10")
def test_notice_mail_is_off_until_a_person_switches_it_on(world, smtp):  # noqa: F811
    """Given mail is set up and an approver who has not switched notice mail on. When a change set
    is submitted for approval, then the approver has the notice and the sender mails no one."""
    _save(world, smtp, applicationUrl=APPLICATION)
    _, approver = _approver(world)
    assert ok(approver.api.get(SWITCH)) == {
        "enabled": False,
        "available": True,
        "reason": None,
        "email": "olga@example.org",
    }
    _submit_one(world, _submitter(world))
    assert ok(approver.api.get("/me/notifications"))["unreadCount"] == 1
    assert send_mail(world) == 0
    assert smtp.messages == []


@pytest.mark.journey("J46.10")
def test_a_notice_is_mailed_naming_its_kind_and_nothing_of_the_change(world, smtp):  # noqa: F811
    """Given an approver who switched notice mail on. When a change set is submitted, then one
    message reaches their address from the saved sender, says a change set waits for approval and
    links to the application, and holds neither the change set's name nor the submitter's comment
    nor the submitter's name."""
    _save(world, smtp, applicationUrl=APPLICATION)
    _, approver = _approver(world)
    assert ok(approver.api.put(SWITCH, {"enabled": True}))["enabled"] is True
    _submit_one(world, _submitter(world))

    assert send_mail(world) == 1
    [mail] = smtp.messages
    text = mail.get_content()
    assert mail["To"] == "olga@example.org" and mail["From"] == "refiroo@example.org"
    assert "something is waiting in your inbox" in mail["Subject"]
    assert "waiting for your approval" in text and APPLICATION in text
    assert "Account" in text
    for private in (SECRET_NAME, SECRET_COMMENT, "contributor", W1, "olga"):
        assert private not in text and private not in mail["Subject"]
    assert ok(world.api.get("/mail-settings"))["outbox"] == {"pending": 0, "sent": 1, "failed": 0}


@pytest.mark.journey("J46.10")
def test_old_read_and_client_notices_are_not_mailed(world, smtp):  # noqa: F811
    """Given an approver with a notice from before switching on, then another after switching on
    that they read, and a submitter (a client) who gets the decision. When the sender runs, then
    nothing is mailed: not the earlier notice, not the read one, not the client's."""
    _save(world, smtp, applicationUrl=APPLICATION)
    _, approver = _approver(world)
    submitter = _submitter(world)
    _submit_one(world, submitter, "Before switching on")
    ok(approver.api.put(SWITCH, {"enabled": True}))

    _submit_one(world, submitter, "Read at once")
    ok(approver.api.post("/me/notifications/read", {"all": True}))

    waiting = ok(approver.api.get("/me/notifications"))["items"]
    assert len(waiting) == 2
    # The decision on the submitter's change set reaches the client's inbox.
    oldest = waiting[-1]
    change_set = submitter.current({"id": oldest["subject"]["id"]})
    ok(_decide(world, approver, change_set, "approve"))
    assert ok(submitter.api.get("/me/notifications"))["unreadCount"] == 1

    assert send_mail(world) == 0
    assert smtp.messages == []
    assert ok(world.api.get("/mail-settings"))["outbox"] == {"pending": 0, "sent": 0, "failed": 0}


@pytest.mark.journey("J46.10")
def test_switching_on_is_refused_where_it_cannot_work_and_off_always_works(world, smtp):  # noqa: F811
    """Given mail is not set up. When a person with an address switches on, then it is refused as
    not set up; with mail set up a person with no address is refused for the address; a client is
    refused as not a person and is told it is unavailable. A person who switched on can switch off
    twice, even after mail is removed, and switching on again keeps the first time."""
    _, approver = _approver(world)
    assert ok(approver.api.get(SWITCH))["reason"] == "mail-not-set-up"
    assert ok(approver.api.get(SWITCH))["available"] is False
    refused(approver.api.put(SWITCH, {"enabled": True}), 409, "MAIL_NOT_SET_UP")

    _save(world, smtp, applicationUrl=APPLICATION)
    _, nobody = _approver(world, "nora", None)
    state = ok(nobody.api.get(SWITCH))
    assert (state["reason"], state["available"], state["email"]) == ("no-email", False, None)
    refused(nobody.api.put(SWITCH, {"enabled": True}), 409, "NO_EMAIL")

    client = _submitter(world)
    assert ok(client.api.get(SWITCH)) == {
        "enabled": False,
        "available": False,
        "reason": "not-a-person",
        "email": None,
    }
    refused(client.api.put(SWITCH, {"enabled": True}), 403, "NOT_A_PERSON")

    assert ok(approver.api.put(SWITCH, {"enabled": True}))["enabled"] is True
    since = _database(world, "SELECT notice_mail_since FROM users WHERE username = 'olga'")
    assert since[0][0] is not None
    ok(approver.api.put(SWITCH, {"enabled": True}))
    assert _database(world, "SELECT notice_mail_since FROM users WHERE username = 'olga'") == since

    ok(world.api.delete("/mail-settings"), 204)
    assert ok(approver.api.put(SWITCH, {"enabled": False}))["enabled"] is False
    assert ok(approver.api.put(SWITCH, {"enabled": False}))["enabled"] is False
    assert _database(world, "SELECT notice_mail_since FROM users WHERE username = 'olga'") == [
        (None,)
    ]


@pytest.mark.journey("J46.10")
def test_a_notice_waits_while_mail_is_not_set_up_and_is_mailed_once_it_is(world, smtp):  # noqa: F811
    """Given an approver who switched on while mail was set up, and mail then removed. When a
    change set is submitted and the sender runs, then nothing is sent and the notice is unmarked;
    when mail is saved again the notice is mailed."""
    _save(world, smtp, applicationUrl=APPLICATION)
    _, approver = _approver(world)
    ok(approver.api.put(SWITCH, {"enabled": True}))
    ok(world.api.delete("/mail-settings"), 204)
    _submit_one(world, _submitter(world))

    assert send_mail(world) == 0 and smtp.messages == []
    assert (
        _database(
            world,
            "SELECT count(*) FROM notifications n JOIN users u ON u.id = n.user_id "
            "WHERE u.username = 'olga' AND n.mailed_at IS NULL",
        )[0][0]
        == 1
    )

    _save(world, smtp, applicationUrl=APPLICATION)
    assert send_mail(world) == 1
    [mail] = smtp.messages
    assert mail["To"] == "olga@example.org" and "waiting for your approval" in mail.get_content()


@pytest.mark.journey("J46.10")
def test_a_notice_is_mailed_once_however_often_the_sender_runs(world, smtp):  # noqa: F811
    """Given an approver who switched on and one notice. When the sender runs twice, then one
    message was sent; a second notice later gives a second message."""
    _save(world, smtp, applicationUrl=APPLICATION)
    _, approver = _approver(world)
    ok(approver.api.put(SWITCH, {"enabled": True}))
    submitter = _submitter(world)
    _submit_one(world, submitter)

    assert send_mail(world) == 1
    assert send_mail(world) == 0
    assert len(smtp.messages) == 1

    _submit_one(world, submitter, "Another one", "Another comment")
    assert send_mail(world) == 1
    assert len(smtp.messages) == 2
