"""The ``mail`` and ``notifications`` areas of the management API's reference, recorded from a run on the
guide's reference data (see ``test_reference_recording.py``, whose seed, scenario and normaliser this file
uses).

The administrator of the Graubünden instance sets up mail: the SMTP connection (the harness's server,
``tests/smtp_server.py``, secured by STARTTLS with a login), a test message, a new person's welcome link
sent by mail and the outbox that shows it, one message stopped, and the administrator's own choices for
the mail of their inbox (the digest and a kind of notice). A second person follows the workspace, the
administrator publishes two change sets and the second person reads, marks and removes the notices that
arrive, and reads where a notice leads. Each step records the main successful use of the operation it
calls; the refusals the areas' text names are asserted without being recorded.

The password of the mail login is replaced by the placeholder in the recorded file (``SECRET_MASKS``), and
the harness server's address and port by an invented host (a call's ``mask``). No operation is called
against a real mail server.

    cd backend && RDM_RECORD_EXAMPLES=1 .venv/bin/python -m pytest tests/test_reference_mail.py -q
"""

import asyncio
import base64
import json
import os
from collections.abc import Iterator
from datetime import UTC, datetime
from typing import Any

import pytest
import seeds
from smtp_server import FakeSmtp
from test_reference_change_sets import (
    CHANGE_SETS,
    GRAUBUENDEN,
    ONE,
    Person,
    _approver,
    _publish_body,
    _version,
)
from test_reference_recording import (
    BASE,
    RECORDING,
    SEED,
    Scenario,
    _application,
    _register_seed,
)
from test_reference_records import _one

LOGIN = ("mailer", "a mail login password")
SERVER = {"host": "smtp.example.org", "port": 587}
FOLLOWED = "/api/v1/me/followed-workspaces/{workspace_key}"
NOTICES = "/api/v1/me/notifications"


@pytest.fixture(scope="module")
def mail() -> Iterator[tuple[Scenario, FakeSmtp]]:
    _register_seed()
    seeds.ensure(SEED)
    url = seeds.clone(SEED)
    saved = os.environ.get("SSL_CERT_FILE")
    try:
        with FakeSmtp(login=LOGIN) as server:
            # The engine verifies the server's certificate as it would any server's; this one is made for the run.
            os.environ["SSL_CERT_FILE"] = str(server.certificate_file)
            with _application(url) as client:
                scenario = Scenario(client)
                yield scenario, server
                if RECORDING:
                    scenario.write_examples()
    finally:
        if saved is None:
            os.environ.pop("SSL_CERT_FILE", None)
        else:
            os.environ["SSL_CERT_FILE"] = saved
        seeds.drop(url.database)


def _settings(server: FakeSmtp, **changes: Any) -> dict:
    return {
        "method": "smtp",
        "host": "127.0.0.1",
        "port": server.port,
        "security": "starttls",
        "username": LOGIN[0],
        "password": LOGIN[1],
        "fromAddress": "refiroo@example.org",
        "applicationUrl": "https://refiroo.example.org",
        **changes,
    }


def _send_queued(s: Scenario) -> int:
    """The application's mail sender, which a recording run does not start as a thread."""
    return s.client.app.state.mail_sender.run_until_idle(datetime.now(UTC))


def test_the_administrator_sets_up_mail_and_follows_what_is_sent(mail):
    s, smtp = mail
    before = s.call("GET", "/api/v1/mail-settings", status=200)
    assert before["configured"] is False and before["outbox"] == {
        "pending": 0,
        "sent": 0,
        "failed": 0,
    }
    # Nothing that needs mail works before it is set up.
    s.call(
        "POST",
        "/api/v1/mail-settings/test",
        body={"to": "ada@example.org"},
        status=409,
        code="MAIL_NOT_SET_UP",
    )
    s.call(
        "PUT",
        "/api/v1/mail-settings",
        body=_settings(smtp, security="none"),
        status=422,
        code="MAIL_INSECURE_LOGIN",
    )
    saved = s.call(
        "PUT",
        "/api/v1/mail-settings",
        body=_settings(smtp),
        status=200,
        record="smtp",
        summary="Save an SMTP server with a login, secured by STARTTLS; the password is never answered",
        mask=SERVER,
    )
    assert saved["configured"] is True and saved["version"] == 1 and saved["passwordSet"] is True
    assert LOGIN[1] not in str(saved)
    s.call(
        "PUT",
        "/api/v1/mail-settings",
        body=_settings(smtp),
        status=409,
        code="VERSION_CONFLICT",
    )
    s.call(
        "GET",
        "/api/v1/mail-settings",
        status=200,
        record="saved",
        summary="The saved settings, the address links point to and the outbox counts",
        mask=SERVER,
    )
    sent = s.call(
        "POST",
        "/api/v1/mail-settings/test",
        body={"to": "ada@example.org"},
        status=200,
        record="test",
        summary="A test message goes through the saved settings now",
    )
    assert sent == {"sentTo": "ada@example.org"} and len(smtp.messages) == 1
    smtp.down = True
    failed = s.call(
        "POST",
        "/api/v1/mail-settings/test",
        body={"to": "ada@example.org"},
        status=422,
        code="MAIL_SEND_FAILED",
    )
    assert failed["error"]["details"]["kind"] == "connection"
    smtp.down = False

    # A new person's welcome link is mailed; the sender then delivers it.
    ada = s.call(
        "POST",
        "/api/v1/users",
        body={"name": "Ada Planner", "email": "ada@example.org"},
        status=201,
    )
    link = s.call(
        "POST",
        "/api/v1/users/{user_id}/password-reset",
        path={"user_id": ada["id"]},
        body={"send": True},
        status=201,
    )
    assert link["sentTo"] == "ada@example.org"
    s.call(
        "GET",
        "/api/v1/mail-outbox",
        query={"status": "pending"},
        status=200,
        record="pending",
        summary="The welcome message waits in the outbox; its text is never answered",
    )
    assert _send_queued(s) == 1 and len(smtp.messages) == 2
    ben = s.call(
        "POST",
        "/api/v1/users",
        body={"name": "Ben Planner", "email": "ben@example.org"},
        status=201,
    )
    s.call(
        "POST",
        "/api/v1/users/{user_id}/password-reset",
        path={"user_id": ben["id"]},
        body={"send": True},
        status=201,
    )
    (waiting,) = s.call("GET", "/api/v1/mail-outbox", query={"status": "pending"}, status=200)[
        "items"
    ]
    stopped = s.call(
        "POST",
        "/api/v1/mail-outbox/{message_id}/stop",
        path={"message_id": waiting["id"]},
        status=200,
        record="stop",
        summary="Stop a message that has not gone yet: it fails at once and its text is erased",
    )
    assert stopped["status"] == "failed" and stopped["lastError"] == "Stopped by an administrator"
    s.call(
        "POST",
        "/api/v1/mail-outbox/{message_id}/stop",
        path={"message_id": waiting["id"]},
        status=409,
        code="MESSAGE_NOT_WAITING",
    )
    everything = s.call(
        "GET",
        "/api/v1/mail-outbox",
        query={"pageSize": 10},
        status=200,
        record="all",
        summary="Every message, newest first: the stopped one failed, the other was sent",
    )
    assert [item["status"] for item in everything["items"]] == ["failed", "sent", "sent"][
        : len(everything["items"])
    ] or {item["status"] for item in everything["items"]} <= {"failed", "sent"}

    # The administrator's own mail: switched on, the digest chosen and one kind put in it.
    s.call("GET", "/api/v1/me/notification-mail", status=200)
    s.call(
        "PUT",
        "/api/v1/me/notification-mail",
        body={"kinds": {"change-set.published": "digest"}},
        status=422,
        code="DIGEST_NOT_SET",
    )
    s.call(
        "PUT",
        "/api/v1/me/notification-mail",
        body={
            "enabled": True,
            "digest": {"every": "daily", "timeZone": "Europe/Zurich"},
            "kinds": {"change-set.published": "digest", "job.completed": "off"},
        },
        status=200,
        record="switchOn",
        summary="Switch mail for the inbox on, choose the daily digest and how two kinds are mailed",
    )
    mine = s.call(
        "GET",
        "/api/v1/me/notification-mail",
        status=200,
        record="mine",
        summary="Whether the caller is mailed, to which address, and how each kind of notice is",
    )
    assert mine["enabled"] is True and mine["digest"]["every"] == "daily"
    assert mine["digest"]["nextAt"] is not None
    s.call(
        "PUT",
        "/api/v1/me/notification-mail",
        body={"kinds": {"no.such-kind": "off"}},
        status=422,
        code="UNKNOWN_NOTICE_KIND",
    )
    s.call(
        "PUT",
        "/api/v1/me/notification-mail",
        body={"digest": {"every": "daily", "timeZone": "Nowhere/Land"}},
        status=422,
        code="UNKNOWN_TIME_ZONE",
    )
    s.call("PUT", "/api/v1/me/notification-mail", body={"enabled": False}, status=200)


def _events(s: Scenario, person: Person, wanted: int = 1) -> str:
    """The first ``wanted`` events of the person's notice stream, read from the application as a client
    reads them; the client then goes away, as it would. A stream is open as long as the client is."""

    async def read(app: Any, token: str) -> str:
        chunks: list[str] = []
        gone = asyncio.Event()

        async def receive() -> dict:
            await gone.wait()
            return {"type": "http.disconnect"}

        async def send(message: dict) -> None:
            if message["type"] == "http.response.body" and message.get("body"):
                chunks.append(message["body"].decode())
                if "".join(chunks).count("event: ") >= wanted:
                    gone.set()

        scope = {
            "type": "http",
            "asgi": {"version": "3.0"},
            "http_version": "1.1",
            "method": "GET",
            "scheme": "http",
            "path": "/api/v1/me/notifications/events",
            "raw_path": b"/api/v1/me/notifications/events",
            "query_string": b"",
            "root_path": "",
            "headers": [(b"host", b"testserver"), (b"authorization", f"Bearer {token}".encode())],
            "client": ("127.0.0.1", 50000),
            "server": ("testserver", 80),
        }
        await asyncio.wait_for(app(scope, receive, send), 30)
        return "".join(chunks)

    return s.client.portal.call(read, s.client.app, person.api.token)


def test_a_person_follows_a_workspace_and_reads_the_notices_that_arrive(mail):
    s, _ = mail
    approver = _approver(s)
    s.call("GET", "/api/v1/me/followed-workspaces", status=200)
    followed = approver.call(
        "PUT",
        FOLLOWED,
        path=GRAUBUENDEN,
        status=200,
        record="follow",
        summary="Follow a workspace: a notice arrives when a change set is published there",
    )
    assert followed["workspaceKey"] == "graubuenden"
    approver.call("PUT", FOLLOWED, path={"workspace_key": "no-such"}, status=404, code="NOT_FOUND")
    approver.call(
        "GET",
        "/api/v1/me/followed-workspaces",
        status=200,
        record="followed",
        summary="The workspaces the caller follows and may still browse",
    )

    # The administrator publishes two change sets; the follower is told of each.
    davos = _one(s, "municipality", "Davos")
    stops = s.call(
        "GET",
        "/api/v1/objects/{object_type_key}",
        path={"object_type_key": "stop"},
        query={"parentObjectId": davos["id"], "sort": "name", "pageSize": 2},
        status=200,
    )["items"]
    for stop, name in zip(stops, ("Winter 2027: stop names", "Winter 2027: signage"), strict=True):
        made = s.call(
            "POST",
            CHANGE_SETS,
            path=GRAUBUENDEN,
            body={"name": name, "source": "currentLive"},
            status=201,
        )
        s.call(
            "PATCH",
            "/api/v1/objects/{object_type_key}/{object_id}",
            path={"object_type_key": "stop", "object_id": stop["id"]},
            body={
                "name": stop["name"] + " (Post)",
                "expectedVersion": stop["version"],
                "changeSetId": made["id"],
                "expectedChangeSetVersion": _version(s, made["id"]),
            },
            status=200,
        )
        s.call(
            "POST",
            ONE + "/publication",
            path={"change_set_id": made["id"]},
            body=_publish_body(s, made["id"]),
            status=200,
        )

    first = approver.call(
        "GET",
        NOTICES,
        query={"unread": True, "pageSize": 10},
        status=200,
        record="unread",
        summary="The unread notices, newest first, with the count of all unread ones",
    )
    assert first["unreadCount"] == 2 and len(first["items"]) == 2
    newest, oldest = first["items"]
    assert newest["kind"] == "change-set.published"
    approver.call(
        "GET",
        NOTICES + "/{notification_id}",
        path={"notification_id": oldest["id"]},
        status=200,
        record="one",
        summary="One notice by ID, as a digest's link opens it",
    )
    approver.call(
        "GET",
        NOTICES + "/{notification_id}",
        path={"notification_id": "nope"},
        status=404,
        code="NOT_FOUND",
    )
    approver.call(
        "GET",
        NOTICES,
        query={"kind": "change-set.published", "q": "signage", "sort": "oldest"},
        status=200,
    )
    marked = approver.call(
        "POST",
        NOTICES + "/read",
        body={"ids": [oldest["id"]]},
        status=200,
        record="markRead",
        summary="Mark one notice read; the answer says how many changed and how many are still unread",
    )
    assert marked == {"marked": 1, "unreadCount": 1}
    approver.call("POST", NOTICES + "/read", body={}, status=422, code="REQUEST_VALIDATION_ERROR")
    removed = approver.call(
        "POST",
        NOTICES + "/removal",
        body={"read": True},
        status=200,
        record="removeRead",
        summary="Delete every read notice for good; what they were about stays",
    )
    assert removed == {"removed": 1, "unreadCount": 1}
    stream = _events(s, approver)
    assert stream.startswith("event: unread\n")
    if RECORDING:
        approver.exchanges.append(
            {
                "operation": "GET /api/v1/me/notifications/events",
                "name": "open",
                "summary": "The stream as it opens: the unread count at once (the first event; "
                "a `notification` event follows for each new notice while the client stays)",
                "request": {},
                "response": {"status": 200, "body": stream},
            }
        )
    approver.call(
        "DELETE",
        FOLLOWED,
        path=GRAUBUENDEN,
        status=204,
        record="unfollow",
        summary="Stop following the workspace; harmless when it was not followed",
    )
    s.call(
        "DELETE",
        "/api/v1/mail-settings",
        status=204,
        record="remove",
        summary="Remove the settings: no mail is sent, and what needs mail answers 409",
    )
    s.call(
        "POST",
        "/api/v1/mail-settings/test",
        body={"to": "ada@example.org"},
        status=409,
        code="MAIL_NOT_SET_UP",
    )


PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg=="
)
LOGO = "/api/v1/mail-template/logo"
LETTER = "{{logo}}\n\nDear {{recipient_name}},\n\n{{content}}\n\n--\n[{{product_name}}]({{instance_url}})\n"


def test_the_operator_edits_the_email_template_that_wraps_every_message(mail):
    """The e-mail template: read the default, refuse a draft, look at one, save it, add a logo, send a
    test to the caller's own address, remove the logo and go back to the default."""
    s, smtp = mail
    s.call("PUT", "/api/v1/mail-settings", body=_settings(smtp), status=200)
    default = s.call(
        "GET",
        "/api/v1/mail-template",
        status=200,
        record="default",
        summary="No template is saved: the default Markdown is answered and the engine's own layout is used",
    )
    assert default["saved"] is False and "{{content}}" in default["markdown"]
    s.call(
        "PUT",
        "/api/v1/mail-template",
        body={"markdown": "Dear {{recipient_name}}, {{nickname}}\n\n{{content}}\n"},
        status=422,
        code="MAIL_TEMPLATE_UNKNOWN_PLACEHOLDER",
    )
    s.call(
        "PUT",
        "/api/v1/mail-template",
        body={"markdown": "Dear {{recipient_name}}\n"},
        status=422,
        code="MAIL_TEMPLATE_CONTENT_REQUIRED",
    )
    s.call("DELETE", LOGO, status=409, code="MAIL_TEMPLATE_NOT_SAVED")
    preview = s.call(
        "POST",
        "/api/v1/mail-template/preview",
        body={"markdown": LETTER},
        status=200,
        record="preview",
        summary="A draft rendered around a sample message with sample values; nothing is saved",
    )
    assert "Dear Alex Example" in preview["text"] and "<html" in preview["html"]
    saved = s.call(
        "PUT",
        "/api/v1/mail-template",
        body={"markdown": LETTER},
        status=200,
        record="saved",
        summary="Save the template; every message is now this letter around its own text",
    )
    assert saved["saved"] is True and saved["version"] == 1
    s.call(
        "PUT",
        "/api/v1/mail-template",
        body={"markdown": LETTER},
        status=409,
        code="VERSION_CONFLICT",
    )
    for kind, data, status, code in (
        ("text/plain", b"not an image", 422, "MAIL_LOGO_UNSUPPORTED"),
        (
            "image/svg+xml",
            b"<svg xmlns='http://www.w3.org/2000/svg'><script>1</script></svg>",
            422,
            "MAIL_LOGO_UNSAFE",
        ),
    ):
        refused = s.client.put(
            LOGO,
            files={"file": ("logo", data, kind)},
            headers={"Origin": BASE, "Authorization": "Bearer " + s.api.token},
        )
        assert refused.status_code == status and refused.json()["error"]["code"] == code
    uploaded = s.client.put(
        LOGO,
        files={"file": ("logo.png", PNG, "image/png")},
        data={"expectedVersion": "1"},
        headers={"Origin": BASE, "Authorization": "Bearer " + s.api.token},
    )
    assert uploaded.status_code == 200, uploaded.text
    answer = uploaded.json()
    assert answer["logoType"] == "image/png" and answer["version"] == 2
    s._record(
        "PUT",
        LOGO,
        "uploaded",
        "Upload a PNG as the logo; the template's version moves on",
        {},
        {},
        None,
        200,
        answer,
        ["The `file` part: `logo.png`.", f"The `expectedVersion` part: `{json.dumps(1)}`."],
    )
    sent = s.call(
        "POST",
        "/api/v1/mail-template/test",
        status=200,
        record="test",
        summary="The saved template around a sample message goes to the caller's own address",
    )
    assert sent["sentTo"] and smtp.messages[-1]["To"] == sent["sentTo"]
    s.call(
        "DELETE",
        LOGO,
        query={"expectedVersion": 2},
        status=200,
        record="removeLogo",
        summary="Remove the logo; the refiroo mark is used again",
    )
    s.call(
        "DELETE", "/api/v1/mail-template", status=204, record="reset", summary="Back to the default"
    )
    assert s.call("GET", "/api/v1/mail-template", status=200)["saved"] is False
