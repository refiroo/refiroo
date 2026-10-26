"""J42.5 — The inbox and the workspace's events (0.12 A2).

Each step of a publication request reaches the inbox of those concerned and the webhook events of
the workspace; a finished job reaches its requester. Written from the A2 plan and API.md §
Approvals and § Inbox before any implementation. Each case runs on two configurations through the
public API, with clients holding predefined roles (a client is a principal with an inbox like a
person). The stream is read over HTTP as J24.7's is; webhook deliveries are received on localhost
as J30.8's are.
"""

import json
import threading
import time

import httpx
import pytest
from harness_identity import token
from scenario import W1, dispatch, ok, refused
from test_j24_background_job import _items, _worker
from test_j24_job_stream import served  # noqa: F401 - a fixture
from test_j30_delivery import _now, _signed, receiver  # noqa: F401 - a fixture
from test_j42_approvals import _actors, _decide, _edit, _proposal, _submit

NOTICES = "/me/notifications"
SUBSCRIPTIONS = {"CONSUMER_SUBSCRIPTIONS_ENABLED": "true"}


def _inbox(actor, **params) -> list[dict]:
    return ok(actor.api.get(NOTICES, **params))["items"]


def _kinds(actor, **params) -> list[str]:
    """The kinds of the actor's notices, oldest first."""
    return [item["kind"] for item in reversed(_inbox(actor, **params))]


def _unread(actor) -> int:
    return ok(actor.api.get(NOTICES, pageSize=1))["unreadCount"]


@pytest.mark.journey("J42.5")
def test_a_request_reaches_the_approvers_and_its_decision_the_submitter(world):
    """Given a Contributor and a Data owner. When the Contributor submits a change set, then the
    owner has one unread "submitted" notice naming the change set and the submitter, and the
    Contributor has none. When the owner approves it, then the Contributor has an "approved"
    notice with the owner's comment, the owner's earlier notice is read, and the owner has no
    notice of their own decision."""
    actors = _actors(world, contributor="contributor", approver="owner")
    contributor, approver = actors["contributor"], actors["approver"]
    change_set = _proposal(world, contributor, "Awaiting approval")
    ok(_submit(contributor, change_set, "Please check"), 201)

    [waiting] = _inbox(approver)
    assert waiting["kind"] == "change-set.submitted" and not waiting["read"]
    assert waiting["workspaceKey"] == W1
    assert waiting["subject"] == {"kind": "change-set", "id": change_set["id"]}
    details = waiting["details"]
    assert details["changeSetName"] == change_set["name"] and details["comment"] == "Please check"
    assert details["actor"]["name"] == "contributor" and details["actor"]["kind"] == "client"
    assert _unread(approver) >= 1 and _inbox(contributor) == []

    version = contributor.current(change_set)["version"]
    ok(_decide(world, approver, {**change_set, "version": version}, "approve", "Fine"))
    [decided] = _inbox(contributor)
    assert decided["kind"] == "change-set.approved" and decided["details"]["comment"] == "Fine"
    assert decided["details"]["actor"]["name"] == "approver"
    assert decided["details"]["publicationId"]
    assert _kinds(approver) == ["change-set.submitted"]
    assert _inbox(approver)[0]["read"] is True


@pytest.mark.journey("J42.5")
def test_a_sent_back_request_reaches_the_submitter_and_a_new_one_waits_again(world):
    """Given a submitted change set. When the approver sends it back with a comment, then the
    Contributor has a "sent-back" notice with the comment and the approver's waiting notice is
    read. When the Contributor edits and submits again, then the approver has a new unread
    "submitted" notice beside the read one."""
    actors = _actors(world, contributor="contributor", approver="owner")
    contributor, approver = actors["contributor"], actors["approver"]
    change_set = _proposal(world, contributor)
    ok(_submit(contributor, change_set), 201)
    ok(_decide(world, approver, change_set, "sendBack", "Name it properly"))
    [returned] = _inbox(contributor)
    assert returned["kind"] == "change-set.sent-back"
    assert returned["details"]["comment"] == "Name it properly"
    assert [item["read"] for item in _inbox(approver)] == [True]

    ok(_edit(world, contributor, contributor.current(change_set), "Named properly"), 201)
    ok(_submit(contributor, contributor.current(change_set), "Again"), 201)
    assert [item["read"] for item in _inbox(approver)] == [False, True]
    assert _kinds(approver) == ["change-set.submitted", "change-set.submitted"]


@pytest.mark.journey("J42.5")
def test_withdrawing_a_request_closes_its_waiting_notice_and_tells_no_one(world):
    """Given a submitted change set. When the Contributor withdraws the submission, then the
    approver's waiting notice is read and nobody receives a new one."""
    actors = _actors(world, contributor="contributor", approver="owner")
    contributor, approver = actors["contributor"], actors["approver"]
    change_set = _proposal(world, contributor)
    ok(_submit(contributor, change_set), 201)
    before = _unread(approver)
    assert contributor.api.delete(f"/change-sets/{change_set['id']}/submission").status_code == 204
    assert _unread(approver) == before - 1
    assert _kinds(approver) == ["change-set.submitted"] and _inbox(approver)[0]["read"]
    assert _inbox(contributor) == []


@pytest.mark.journey("J42.5")
def test_notices_are_marked_read_by_id_or_all_and_only_the_callers_own(world):
    """Given two approvers with the same unread notices. When one marks a notice read by ID, then
    `marked` is 1 and the count falls by one; marking it again marks 0; the other approver's
    notice, named by ID, is left alone; `unread=true` lists only unread ones; `all` marks the
    rest; naming neither or both is a validation error."""
    actors = _actors(world, contributor="contributor", first="owner", second="owner")
    contributor, first, second = actors["contributor"], actors["first"], actors["second"]
    for index in range(2):
        change_set = _proposal(world, contributor, f"Proposal {index}")
        ok(_submit(contributor, change_set), 201)
    mine, theirs = _inbox(first), _inbox(second)
    assert len(mine) == len(theirs) >= 2
    start = _unread(first)

    result = ok(first.api.post(f"{NOTICES}/read", {"ids": [mine[0]["id"]]}))
    assert result == {"marked": 1, "unreadCount": start - 1}
    assert ok(first.api.post(f"{NOTICES}/read", {"ids": [mine[0]["id"]]}))["marked"] == 0
    assert ok(first.api.post(f"{NOTICES}/read", {"ids": [theirs[1]["id"]]}))["marked"] == 0
    assert _unread(second) == start
    assert [item["id"] for item in _inbox(first, unread=True)] == [
        item["id"] for item in mine if item["id"] != mine[0]["id"]
    ]
    assert ok(first.api.post(f"{NOTICES}/read", {"all": True}))["unreadCount"] == 0
    assert _inbox(first, unread=True) == []
    for body in ({}, {"ids": [mine[0]["id"]], "all": True}, {"all": False}):
        assert first.api.post(f"{NOTICES}/read", body).status_code == 422


@pytest.mark.journey("J42.5")
def test_notices_page_with_cursors_newest_first(world):
    """Given a person with three notices. When the list is read two at a time, then the pages
    continue by cursor in newest-first order with the same total unread count on each."""
    actors = _actors(world, contributor="contributor", approver="owner")
    contributor, approver = actors["contributor"], actors["approver"]
    for index in range(3):
        ok(_submit(contributor, _proposal(world, contributor, f"Page {index}")), 201)
    everything = _inbox(approver)
    assert len(everything) == 3
    first = ok(approver.api.get(NOTICES, pageSize=2))
    second = ok(approver.api.get(NOTICES, pageSize=2, cursor=first["nextCursor"]))
    assert [item["id"] for item in first["items"] + second["items"]] == [
        item["id"] for item in everything
    ]
    assert first["unreadCount"] == second["unreadCount"] == 3 and second["nextCursor"] is None


@pytest.mark.journey("J42.5")
def test_a_job_finishing_reaches_its_requester_and_an_inline_batch_does_not(world):
    """Given a Data steward. When they run a batch inline, then no notice. When they start one in
    the background and the worker finishes it, then a "job.completed" notice names the job and its
    kind, and it is the steward's alone."""
    actors = _actors(world, steward="steward", other="owner")
    steward, other = actors["steward"], actors["other"]
    inline = {
        "workspaceKey": W1,
        "policy": "independent",
        "run": "inline",
        "items": _items(steward, 2, "I"),
    }
    ok(steward.api.post("/batches", inline))
    assert _inbox(steward) == []

    background = {**inline, "run": "background", "items": _items(steward, 2, "B")}
    job = ok(steward.api.post("/batches", background), 202)
    _worker("inbox").run_until_idle()
    [notice] = _inbox(steward)
    assert notice["kind"] == "job.completed" and notice["subject"] == {
        "kind": "job",
        "id": job["id"],
    }
    assert notice["details"] == {"jobKind": "batch", "state": "completed"}
    assert all(item["subject"]["id"] != job["id"] for item in _inbox(other))


def _subscribe(world, url, **changes):
    body = {
        "name": "Approvals",
        "source": "workspace",
        "workspaceKey": W1,
        "events": [],
        "url": url,
    }
    body.update(changes)
    body["events"] = body["events"] or [
        "change-set.submitted",
        "change-set.approved",
        "change-set.sent-back",
    ]
    return world.api.post("/consumer-subscriptions", body)


@pytest.mark.journey("J42.5")
@pytest.mark.settings(**SUBSCRIPTIONS)
def test_every_step_is_a_signed_workspace_event_in_order(world, receiver):  # noqa: F811
    """Given a subscription to the workspace's change-set events. When a Contributor submits, the
    approver sends it back, it is submitted again and approved, then the receiver gets four
    signed events in order — submitted, sent-back, submitted, approved — with positions 1 to 4
    after the subscription's start, the change set, the people's names (no e-mail) and the
    comments; the subscription reads `source: workspace`, no consumer API, and has acknowledged
    through the last."""
    created = ok(_subscribe(world, receiver.url, maxEventsPerBatch=100), 201)
    assert created["source"] == "workspace" and created["consumerApi"] is None
    start = created["acknowledgedThrough"]
    actors = _actors(world, contributor="contributor", approver="owner")
    contributor, approver = actors["contributor"], actors["approver"]
    change_set = _proposal(world, contributor, "Four steps")
    ok(_submit(contributor, change_set, "First"), 201)
    ok(_decide(world, approver, change_set, "sendBack", "Needs a source"))
    ok(_edit(world, contributor, contributor.current(change_set), "Four steps, sourced"), 201)
    ok(_submit(contributor, contributor.current(change_set), "Second"), 201)
    version = contributor.current(change_set)["version"]
    ok(_decide(world, approver, {**change_set, "version": version}, "approve", "Fine"))
    dispatch(world)

    (request,) = receiver.requests
    assert _signed(created["signingSecret"], request)
    events = request["body"]["events"]
    assert request["body"]["source"] == "workspace" and request["body"]["workspaceKey"] == W1
    assert [e["event"] for e in events] == [
        "change-set.submitted",
        "change-set.sent-back",
        "change-set.submitted",
        "change-set.approved",
    ]
    assert [e["position"] for e in events] == [start + 1, start + 2, start + 3, start + 4]
    assert [e["comment"] for e in events] == ["First", "Needs a source", "Second", "Fine"]
    submitted, sent_back, _, approved = events
    assert (
        submitted["id"] == change_set["id"] and submitted["changeSet"]["name"] == change_set["name"]
    )
    assert submitted["submitter"]["name"] == "contributor" and submitted["decider"] is None
    assert (
        sent_back["decider"]["name"] == "approver"
        and sent_back["submitter"]["name"] == "contributor"
    )
    assert approved["publicationId"] and "email" not in json.dumps(events)
    current = ok(world.api.get(f"/consumer-subscriptions/{created['id']}"))
    assert current["acknowledgedThrough"] == start + 4 and current["delivery"]["pending"] is None


@pytest.mark.journey("J42.5")
@pytest.mark.settings(**SUBSCRIPTIONS)
def test_a_subscription_takes_only_the_events_it_names_and_may_be_cloudevents(world, receiver):  # noqa: F811
    """Given a CloudEvents subscription to `change-set.approved` only, one event a request. When a
    change set is submitted and approved, then only the approval arrives, as a structured
    CloudEvent of type `rdm.change-set.approved`, and the subscription has acknowledged past the
    submission too. A name that is no workspace event is `400 UNKNOWN_EVENT`; filters and a
    consumer API do not apply to this source."""
    created = ok(
        _subscribe(world, receiver.url, events=["change-set.approved"], format="cloudevents"), 201
    )
    refused(_subscribe(world, receiver.url, events=["record.created"]), 400, "UNKNOWN_EVENT")
    for extra in ({"filters": {"x": "y"}}, {"consumerApi": "any"}, {"payload": "identity"}):
        assert _subscribe(world, receiver.url, **extra).status_code == 422
    actors = _actors(world, contributor="contributor", approver="owner")
    contributor, approver = actors["contributor"], actors["approver"]
    change_set = _proposal(world, contributor)
    ok(_submit(contributor, change_set), 201)
    version = contributor.current(change_set)["version"]
    ok(_decide(world, approver, {**change_set, "version": version}, "approve"))
    dispatch(world, _now())

    (request,) = receiver.requests
    assert request["headers"]["content-type"].startswith("application/cloudevents+json")
    assert request["body"]["type"] == "rdm.change-set.approved"
    assert request["body"]["subject"] == f"change-set/{change_set['id']}"
    assert request["body"]["data"]["event"] == "change-set.approved"
    current = ok(world.api.get(f"/consumer-subscriptions/{created['id']}"))
    assert current["acknowledgedThrough"] == created["acknowledgedThrough"] + 2


@pytest.mark.journey("J42.5")
@pytest.mark.settings(**SUBSCRIPTIONS)
def test_a_workspace_events_subscription_is_edited_suspended_and_resumed_where_it_stopped(
    world,
    receiver,  # noqa: F811
):
    """Given a subscription to workspace events. When filters are put into it by an edit, then `400
    NOT_SUPPORTED_BY_SOURCE`; an edit to its events works. When it is suspended while a change set
    is submitted and resumed, then the missed event is delivered after the resume; resuming with
    `reset` instead skips what happened while suspended."""
    created = ok(_subscribe(world, receiver.url, events=["change-set.submitted"]), 201)
    path = f"/consumer-subscriptions/{created['id']}"
    current = ok(world.api.get(path))
    refused(
        world.api.patch(path, {"expectedVersion": current["version"], "filters": {"x": "y"}}),
        400,
        "NOT_SUPPORTED_BY_SOURCE",
    )
    edited = ok(world.api.patch(path, {"expectedVersion": current["version"], "name": "Renamed"}))
    suspended = ok(world.api.post(f"{path}/suspend", {"expectedVersion": edited["version"]}))
    actors = _actors(world, contributor="contributor")
    contributor = actors["contributor"]
    ok(_submit(contributor, _proposal(world, contributor, "While away")), 201)
    dispatch(world)
    assert receiver.requests == []

    resumed = ok(
        world.api.post(f"{path}/resume", {"expectedVersion": suspended["version"], "reset": False})
    )
    assert resumed["status"] == "active" and resumed["source"] == "workspace"
    dispatch(world)
    (request,) = receiver.requests
    assert [e["event"] for e in request["body"]["events"]] == ["change-set.submitted"]

    again = ok(world.api.post(f"{path}/suspend", {"expectedVersion": resumed["version"]}))
    ok(_submit(contributor, _proposal(world, contributor, "Skipped"), "Skipped"), 201)
    ok(world.api.post(f"{path}/resume", {"expectedVersion": again["version"], "reset": True}))
    dispatch(world)
    assert len(receiver.requests) == 1


class _Inbox:
    """Reads a principal's inbox stream on a thread: the events it sends, in order."""

    def __init__(self, base: str) -> None:
        self.events: list[tuple[str, dict]] = []
        self.first = threading.Event()
        self._thread = threading.Thread(target=self._read, args=(base,), daemon=True)
        self._thread.start()
        assert self.first.wait(10), "the stream sent nothing"

    def _read(self, base: str) -> None:
        bearer = token(lambda path, **kwargs: httpx.post(f"{base}{path}", **kwargs))
        headers = {"Authorization": f"Bearer {bearer}"}
        url = f"{base}/api/v1/me/notifications/events"
        try:
            with httpx.stream("GET", url, headers=headers, timeout=30) as response:
                assert response.status_code == 200, response.read()
                assert response.headers["content-type"].startswith("text/event-stream")
                name = None
                for line in response.iter_lines():
                    if line.startswith("event:"):
                        name = line.split(":", 1)[1].strip()
                    elif line.startswith("data:") and name:
                        self.events.append((name, json.loads(line.split(":", 1)[1])))
                        self.first.set()
        except httpx.RemoteProtocolError:
            pass  # the test ended and the server closed the stream

    def wait_for(self, name: str, condition=lambda body: True) -> dict:
        deadline = time.monotonic() + 10
        while True:
            for seen, body in list(self.events):
                if seen == name and condition(body):
                    return body
            assert time.monotonic() < deadline, self.events
            time.sleep(0.02)


@pytest.mark.journey("J42.5")
def test_the_inbox_stream_sends_the_count_at_once_and_each_new_notice(world, served):  # noqa: F811
    """Given the stream open. Then it sends the unread count first. When a change set is submitted,
    then it sends the notice as the list answers it and the raised count, with nothing polled."""
    stream = _Inbox(served)
    assert stream.events[0][0] == "unread"
    count = stream.events[0][1]["unreadCount"]
    actors = _actors(world, contributor="contributor")
    ok(_submit(actors["contributor"], _proposal(world, actors["contributor"], "Streamed")), 201)
    notice = stream.wait_for("notification", lambda body: body["kind"] == "change-set.submitted")
    assert notice["details"]["actor"]["name"] == "contributor" and notice["read"] is False
    assert (
        stream.wait_for("unread", lambda body: body["unreadCount"] > count)["unreadCount"] > count
    )
