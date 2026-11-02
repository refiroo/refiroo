"""J57 — Notification digests and following a workspace (USER_JOURNEYS.md § Digests, 0.16 AO3).

A person who is mailed for their inbox may choose, per kind of notice, to be mailed at once, in a
digest or not at all, and a digest comes daily or weekly at 07:00 in their time zone. A digest says
kinds and counts and links to the notices, and no name (D432). A person may follow a workspace they
may browse and then has a notice when a change set is published there. The sender is driven by
``run_once(now)`` with the clock the test names; every case runs on two configurations through the
public API.
"""

import json
from collections import Counter
from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

import pytest
from scenario import W1, W2, ok, refused, send_mail
from sqlalchemy import text
from test_j24_background_job import _items, _worker
from test_j39_sign_in import _browser, _reset_link, _set_password, _sign_in
from test_j40_authorization import _as, _client, _grant
from test_j42_approvals import _decide, _proposal, _publish, _submit
from test_j46_inbox_mail import (
    APPLICATION,
    SWITCH,
    _database,
    _submit_one,
    _submitter,
)
from test_j46_mail import _person, _save, smtp  # noqa: F401 - a fixture

ZONE = "Europe/Budapest"
FOLLOWED = "/me/followed-workspaces"
SECRET_NAME = "Quarterly pricing rework"
SECRET_COMMENT = "Please look at the Berlin numbers"
SECRET_FILE = "operators-Q3-final.xlsx"
DIGEST = {"every": "daily", "timeZone": ZONE}


def _write(world, statement: str, **parameters) -> None:
    with world.api.client.app.state.session_factory() as session:
        session.execute(text(statement), parameters)
        session.commit()


def _member(world, username: str, email: str | None = None, role: str = "owner", workspace=W1):
    """A person with a password holding ``role`` in a workspace, their grant, and the world as they
    see it."""
    person = _person(world, username, email or f"{username}@example.org")
    response = _set_password(_browser(world), _reset_link(world, person))
    assert response.status_code == 200, response.text
    grant = _grant(world, "user", person["id"], role, workspaceKey=workspace)
    return person, grant, _as(world, _sign_in(_browser(world), username))


def _steward(world, smtp, username="olga", kinds=None, digest=DIGEST, **extra):  # noqa: F811
    """A person mailed for their inbox with the given choices; mail is set up once."""
    if not ok(world.api.get("/mail-settings"))["configured"]:
        _save(world, smtp, applicationUrl=APPLICATION)
    _, _, person = _member(world, username)
    body = {"enabled": True, "kinds": kinds or {}, "digest": digest, **extra}
    found = ok(person.api.put(SWITCH, {key: value for key, value in body.items() if value}))
    return person, found


def _when(found: dict) -> datetime:
    return datetime.fromisoformat(found["digest"]["nextAt"])


def _local(moment: datetime) -> datetime:
    return moment.astimezone(ZoneInfo(ZONE))


def _inbox(person, **params) -> list[dict]:
    return ok(person.api.get("/me/notifications", **params))["items"]


def _failed_import(world, person, applied: int = 1286, rejected: int = 14) -> str:
    """A background job of the person that finished and then failed with rejected rows: the jobs
    trigger makes its notice."""
    job = ok(
        person.api.post(
            "/batches",
            {
                "workspaceKey": W1,
                "policy": "independent",
                "run": "background",
                "items": _items(person, 2, "F"),
            },
        ),
        202,
    )
    _worker("digest").run_until_idle()
    counts = json.dumps({"applied": applied, "rejected": rejected})
    _write(
        world,
        "UPDATE jobs SET kind = 'import', state = 'failed', counts = CAST(:counts AS json), "
        "parameters = CAST(:parameters AS json) WHERE id = :id",
        counts=counts,
        parameters=json.dumps({"fileName": SECRET_FILE}),
        id=job["id"],
    )
    return job["id"]


def _delivery(found: dict) -> dict[str, str]:
    return {item["kind"]: item["delivery"] for item in found["kinds"]}


def _text(mail) -> str:
    return mail.get_content()


@pytest.mark.journey("J57.1")
def test_a_digest_says_what_waits_in_one_message_at_seven(world, smtp):  # noqa: F811
    """Given a steward who chose approvals and failed jobs in a daily digest in their time zone.
    When three change sets are submitted and an import fails with rejected rows, then before 07:00
    there nothing is mailed, and at 07:00 one message says the counts of the notices made, the job's
    line carries its counts, every notice has its link, and no per-notice mail went."""
    kinds = {"change-set.submitted": "digest", "job.failed": "digest", "job.completed": "off"}
    olga, found = _steward(world, smtp, kinds=kinds)
    assert found["digest"]["every"] == "daily" and found["digest"]["timeZone"] == ZONE
    due = _when(found)
    local = due.astimezone(ZoneInfo(ZONE))
    assert (local.hour, local.minute) == (7, 0) and due > datetime.now(UTC)
    assert _delivery(found)["change-set.submitted"] == "digest"
    assert _delivery(found)["change-set.approved"] == "now"

    submitter = _submitter(world)
    for number in range(3):
        _submit_one(world, submitter, f"Plan {number}", f"Comment {number}")
    _failed_import(world, olga)

    assert send_mail(world, due - timedelta(minutes=1)) == 0 and smtp.messages == []
    assert send_mail(world, due) == 1
    [mail] = smtp.messages
    body = _text(mail)
    assert mail["To"] == "olga@example.org"
    assert mail["Subject"].endswith(": 4 notices in your inbox")
    assert body.startswith("3 change sets wait for your approval; 1 job you started failed.")
    assert "An import, 1,286 rows applied, 14 rows rejected" in body
    made = Counter(item["kind"] for item in _inbox(olga))
    assert made["change-set.submitted"] == 3 and made["job.failed"] == 1
    for item in _inbox(olga):
        if item["kind"] in ("change-set.submitted", "job.failed"):
            assert f"{APPLICATION}/notifications?notice={item['id']}" in body
    assert body.count("?notice=") == 4 and "Settings > Notifications" in body
    assert len(smtp.messages) == 1
    again = ok(olga.api.get(SWITCH))
    assert _when(again) > due and _when(again).astimezone(ZoneInfo(ZONE)).hour == 7


@pytest.mark.journey("J57.2")
def test_a_digest_carries_no_name(world, smtp):  # noqa: F811
    """Given a change set with a name and a comment, a workspace, a person, a submitting client and
    a job with a file name, all planted. When the digest is mailed, then none of them is in its
    subject or text."""
    kinds = {"change-set.submitted": "digest", "job.failed": "digest", "job.completed": "off"}
    olga, found = _steward(world, smtp, kinds=kinds)
    label = ok(world.api.get(f"/workspaces/{W1}"))["label"]
    _submit_one(world, _submitter(world), SECRET_NAME, SECRET_COMMENT)
    _failed_import(world, olga)
    assert send_mail(world, _when(found)) == 1
    [mail] = smtp.messages
    for private in (
        SECRET_NAME,
        SECRET_COMMENT,
        SECRET_FILE,
        label,
        W1,
        "olga",
        "Olga",
        "contributor",
    ):
        assert private not in _text(mail) and private not in mail["Subject"]
    assert "waiting for your approval" in _text(mail)


@pytest.mark.journey("J57.3")
def test_nothing_new_or_everything_read_gives_no_mail_and_the_time_moves_on(world, smtp):  # noqa: F811
    """Given a daily digest. When nothing was made by 07:00, then no mail and the next time is the
    next morning; when two notices were made and one read before the next 07:00, then the digest
    holds the other only."""
    olga, found = _steward(world, smtp, kinds={"change-set.submitted": "digest"})
    first = _when(found)
    assert send_mail(world, first) == 0 and smtp.messages == []
    second = _when(ok(olga.api.get(SWITCH)))
    assert _local(second).date() - _local(first).date() == timedelta(days=1)
    assert (_local(second).hour, _local(second).minute) == (7, 0)

    submitter = _submitter(world)
    _submit_one(world, submitter, "Read before")
    ok(olga.api.post("/me/notifications/read", {"all": True}))
    _submit_one(world, submitter, "Still waiting")
    assert send_mail(world, second) == 1
    [mail] = smtp.messages
    assert mail["Subject"].endswith(": 1 notice in your inbox")
    assert _text(mail).count("?notice=") == 1

    ok(olga.api.post("/me/notifications/read", {"all": True}))
    third = _when(ok(olga.api.get(SWITCH)))
    assert send_mail(world, third) == 0 and len(smtp.messages) == 1


@pytest.mark.journey("J57.4")
def test_two_senders_in_one_round_send_one_digest(world, smtp, monkeypatch):  # noqa: F811
    """Given a digest due. When a second sender runs while the first is queueing it, then one
    message is made; the notices in it are never mailed again by either sender."""
    from app.engine.mail import outbox
    from app.engine.mail.sender import MailSender

    _, found = _steward(world, smtp, kinds={"change-set.submitted": "digest"})
    _submit_one(world, _submitter(world))
    due = _when(found)
    app = world.api.client.app
    second = MailSender(app.state.session_factory, app.state.identity_settings, owner="second")
    seen: list[int] = []
    enqueue = outbox.enqueue

    def enqueue_while_the_other_runs(*args, **kwargs):
        seen.append(second.run_once(due))
        return enqueue(*args, **kwargs)

    monkeypatch.setattr(outbox, "enqueue", enqueue_while_the_other_runs)
    assert send_mail(world, due) == 1
    monkeypatch.setattr(outbox, "enqueue", enqueue)
    assert seen == [0] and len(smtp.messages) == 1
    assert second.run_until_idle(due + timedelta(days=2)) == 0
    assert send_mail(world, due + timedelta(days=2)) == 0 and len(smtp.messages) == 1
    mailed = _database(world, "SELECT count(*) FROM notifications WHERE mailed_at IS NOT NULL")
    assert mailed == [(1,)]
    assert ok(world.api.get("/mail-settings"))["outbox"] == {"pending": 0, "sent": 1, "failed": 0}


@pytest.mark.journey("J57.5")
def test_kinds_are_mailed_at_once_in_the_digest_or_not_and_the_inbox_keeps_all(world, smtp):  # noqa: F811
    """Given a person who chose approvals for the digest, approved for at once and sent back for no
    mail. When a change set is waiting for them, one of theirs is approved and one sent back, then
    the approval is mailed as today, the digest holds only the waiting one, and the inbox holds
    all three."""
    kinds = {"change-set.submitted": "digest", "change-set.sent-back": "off"}
    pavel, found = _steward(world, smtp, "pavel", kinds=kinds)
    olga = _member(world, "olga")[2]
    assert _delivery(found)["change-set.approved"] == "now"
    own, other = _proposal(world, pavel, "Pavel one"), _proposal(world, pavel, "Pavel two")
    ok(_submit(pavel, own), 201)
    ok(_submit(pavel, other), 201)
    ok(_decide(world, olga, pavel.current(own), "approve"))
    ok(_decide(world, olga, pavel.current(other), "sendBack", "Name it properly"))
    _submit_one(world, _submitter(world))

    assert send_mail(world) == 1
    [now] = smtp.messages
    assert "was approved" in _text(now) and "?notice=" not in _text(now)
    kinds_in_inbox = {item["kind"] for item in _inbox(pavel)}
    assert {"change-set.submitted", "change-set.approved", "change-set.sent-back"} <= kinds_in_inbox

    assert send_mail(world, _when(found)) == 1
    digest = smtp.messages[1]
    assert digest["Subject"].endswith(": 1 notice in your inbox")
    assert "waiting for your approval" in _text(digest) and "sent back" not in _text(digest)
    unmailed = _database(
        world,
        "SELECT kind FROM notifications n JOIN users u ON u.id = n.user_id "
        "WHERE u.username = 'pavel' AND n.mailed_at IS NULL",
    )
    assert unmailed == [("change-set.sent-back",)]


@pytest.mark.journey("J57.6")
def test_a_weekly_digest_comes_on_monday_and_a_removed_job_loses_its_counts(world, smtp):  # noqa: F811
    """Given a weekly digest. When notices arrive over the week and the retention removes the job of
    one, then on Monday at 07:00 one message holds them all, the removed job's line has no counts,
    and the next one is a week later."""
    kinds = {"change-set.submitted": "digest", "job.failed": "digest", "job.completed": "off"}
    olga, found = _steward(world, smtp, kinds=kinds, digest={"every": "weekly", "timeZone": ZONE})
    due = _when(found)
    local = due.astimezone(ZoneInfo(ZONE))
    assert local.weekday() == 0 and (local.hour, local.minute) == (7, 0)
    submitter = _submitter(world)
    for number in range(2):
        _submit_one(world, submitter, f"Plan {number}")
    job = _failed_import(world, olga)
    _write(world, "DELETE FROM jobs WHERE id = :id", id=job)

    assert send_mail(world, due - timedelta(minutes=1)) == 0
    assert send_mail(world, due) == 1
    [mail] = smtp.messages
    body = _text(mail)
    assert mail["Subject"].endswith(": 3 notices in your inbox")
    assert "weekly digest" in body and "2 change sets wait for your approval" in body
    assert "An import" in body and "rows" not in body
    assert _local(_when(ok(olga.api.get(SWITCH)))).date() - local.date() == timedelta(days=7)


@pytest.mark.journey("J57.7")
def test_choices_are_refused_whole_and_a_digest_needs_mail_that_can_work(world, smtp):  # noqa: F811
    """Given a person with a digest. When they name an unknown time zone, an unknown kind or a
    digest without its frequency, then it is 422 and nothing changes, and a kind in the digest with
    no digest set is refused. When mail is off, not set up, the person has no address or is
    inactive, then no digest is made, and the time does not move where mail is not set up."""
    _save(world, smtp, applicationUrl=APPLICATION)
    _, _, nora = _member(world, "nora")
    before = ok(nora.api.get(SWITCH))
    assert before["digest"] is None
    error = refused(
        nora.api.put(SWITCH, {"kinds": {"job.failed": "digest"}}), 422, "DIGEST_NOT_SET"
    )
    assert error["details"] == {"kinds": ["job.failed"]}
    refused(
        nora.api.put(
            SWITCH, {"enabled": True, "digest": {"every": "daily", "timeZone": "Mars/Base"}}
        ),
        422,
        "UNKNOWN_TIME_ZONE",
    )
    refused(
        nora.api.put(SWITCH, {"enabled": True, "digest": {"timeZone": ZONE}}),
        422,
        "REQUEST_VALIDATION_ERROR",
    )
    refused(
        nora.api.put(SWITCH, {"digest": {"every": "hourly", "timeZone": ZONE}}),
        422,
        "REQUEST_VALIDATION_ERROR",
    )
    refused(
        nora.api.put(SWITCH, {"enabled": True, "digest": DIGEST, "kinds": {"nonsense": "digest"}}),
        422,
        "UNKNOWN_NOTICE_KIND",
    )
    refused(
        nora.api.put(SWITCH, {"kinds": {"job.failed": "weekly"}}), 422, "REQUEST_VALIDATION_ERROR"
    )
    assert ok(nora.api.get(SWITCH)) == before
    refused(_submitter(world).api.put(SWITCH, {"digest": DIGEST}), 403, "NOT_A_PERSON")

    # A digest is made for none of these.
    kinds = {"change-set.submitted": "digest"}
    switched_off, _ = _steward(world, smtp, "quinn", kinds=kinds)
    _steward(world, smtp, "rhea", kinds=kinds)
    _steward(world, smtp, "sam", kinds=kinds)
    _, found = _steward(world, smtp, "tess", kinds=kinds)
    _submit_one(world, _submitter(world))
    ok(switched_off.api.put(SWITCH, {"enabled": False}))
    _write(world, "UPDATE users SET email = NULL WHERE username = 'rhea'")
    _write(world, "UPDATE users SET active = false WHERE username = 'sam'")
    later = _when(found) + timedelta(days=2)
    ok(world.api.delete("/mail-settings"), 204)
    due_before = _database(world, "SELECT username, notice_digest_due_at FROM users ORDER BY id")
    assert send_mail(world, later) == 0 and smtp.messages == []
    assert (
        _database(world, "SELECT username, notice_digest_due_at FROM users ORDER BY id")
        == due_before
    )

    _save(world, smtp, applicationUrl=APPLICATION)
    assert send_mail(world, later) == 1
    [mail] = smtp.messages
    assert mail["To"] == "tess@example.org"
    unmailed = _database(
        world, "SELECT count(*) FROM notifications WHERE mailed_at IS NULL AND user_id IS NOT NULL"
    )
    assert unmailed[0][0] >= 3


@pytest.mark.journey("J57.8")
def test_a_publication_reaches_those_who_follow_the_workspace(world, smtp):  # noqa: F811
    """Given two people who follow a workspace and a third who does not, and a fourth who follows it
    and then loses Browse there. When a change set is published by a request and another directly,
    then each follower has one notice per publication, the publisher and the others none; following
    a workspace one may not browse is 404, unfollowing stops the notices, and a digest line names
    no change set or workspace."""
    kinds = {"change-set.published": "digest"}
    _save(world, smtp, applicationUrl=APPLICATION)
    olga, _ = _steward(world, smtp, "olga", kinds=kinds)
    _, _, pavel = _member(world, "pavel")
    _, _, quinn = _member(world, "quinn")
    _, lost, rhea = _member(world, "rhea")
    _, _, outsider = _member(world, "ola", workspace=W2)
    assert [item["following"] for item in ok(olga.api.get("/me/workspaces"))["items"]] == [False]

    for follower in (olga, pavel, rhea):
        assert ok(follower.api.put(f"{FOLLOWED}/{W1}", None))["workspaceKey"] == W1
    ok(olga.api.put(f"{FOLLOWED}/{W1}", None))
    refused(outsider.api.put(f"{FOLLOWED}/{W1}", None), 404, "NOT_FOUND")
    refused(olga.api.put(f"{FOLLOWED}/no-such-site", None), 404, "NOT_FOUND")
    refused(_submitter(world).api.put(f"{FOLLOWED}/{W1}", None), 403, "NOT_A_PERSON")
    assert [item["workspaceKey"] for item in ok(olga.api.get(FOLLOWED))["items"]] == [W1]
    assert ok(quinn.api.get(FOLLOWED))["items"] == []
    assert [item["following"] for item in ok(olga.api.get("/me/workspaces"))["items"]] == [True]
    ok(world.api.delete(f"/grants/{lost['id']}"), 204)

    def published(person) -> list[dict]:
        return [item for item in _inbox(person) if item["kind"] == "change-set.published"]

    submitter = _submitter(world)
    requested = _submit_one(world, submitter, SECRET_NAME, SECRET_COMMENT)
    ok(_decide(world, pavel, submitter.current(requested), "approve"))
    assert len(published(olga)) == 1 and len(published(pavel)) == 0
    assert published(quinn) == [] and published(submitter) == []
    # Rhea follows the workspace but lost Browse there: she is told nothing of it.
    assert published(rhea) == []
    notice = published(olga)[0]
    assert notice["workspaceKey"] == W1 and notice["subject"]["kind"] == "change-set"
    # Opening it leads to the publication: the notice names it, and it is the workspace's active one.
    first = notice["details"]["publicationId"]
    assert ok(olga.api.get(f"/publications/{first}"))["status"] == "active"
    assert ok(olga.api.get(f"/publications/{first}"))["workspaceKey"] == W1

    direct = _proposal(world, submitter, "Direct one")
    owner = _client(world, "publisher", ("owner", {"workspaceKey": W1}))[1]
    ok(_publish(world, owner, direct))
    assert len(published(olga)) == 2 and len(published(pavel)) == 1
    assert published(quinn) == [] and published(owner) == [] and published(rhea) == []
    # The first publication was superseded: its notice leads nowhere any more.
    assert ok(olga.api.get(f"/publications/{first}"))["status"] == "withdrawn"

    ok(olga.api.delete(f"{FOLLOWED}/{W1}"), 204)
    ok(olga.api.delete(f"{FOLLOWED}/{W1}"), 204)
    third = _proposal(world, submitter, "Third one")
    ok(_publish(world, owner, third))
    assert len(published(olga)) == 2 and len(published(pavel)) == 2

    ok(pavel.api.put(SWITCH, {"enabled": True, "digest": DIGEST, "kinds": kinds}))
    fourth = _proposal(world, submitter, "Fourth one")
    ok(_publish(world, owner, fourth))
    assert len(published(pavel)) == 3
    # Olga's digest, of the two she was told of, is due as well.
    assert send_mail(world, _when(ok(pavel.api.get(SWITCH))) + timedelta(days=1)) == 2
    [mail] = [m for m in smtp.messages if m["To"] == "pavel@example.org"]
    label = ok(world.api.get(f"/workspaces/{W1}"))["label"]
    for private in (SECRET_NAME, SECRET_COMMENT, label, W1, "Fourth one", "Direct one"):
        assert private not in _text(mail) and private not in mail["Subject"]
    assert "published in a workspace you follow" in _text(mail)
