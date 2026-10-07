"""J30.8–J30.9 — Receive a subscription's events, and what stops them (USER_JOURNEYS.md, Base 0.9 C12).

Each test starts the application with the subscriptions capability on, as J30.6 does, and a
receiver on ``localhost`` (the standard library's HTTP server in a thread) that answers as the test
scripts it and records each request. The journey application starts neither the deriver's nor the
dispatcher's thread: a test derives (``derive_events``) and then dispatches (``dispatch``) with a
clock it moves forward, so no test waits for a retry. Expired events (J30.9) need entries older
than the retention period; the test moves their times back in the database, as J30.5 does.
"""

import hashlib
import hmac
import json
import threading
import time
from datetime import UTC, datetime, timedelta
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from itertools import pairwise
from typing import Self
from uuid import uuid4

import pytest
from scenario import consumer_events, consumer_object, derive_events, dispatch, ok, refused
from test_j30_consumer_events import (
    EVERY,
    LEDGER,
    WATCHED,
    _activate,
    _age,
    _delete,
    _head,
    _workspace,
)
from test_j30_subscriptions import PATH, SUBSCRIPTIONS, _feed_head


class Receiver:
    """A webhook receiver on ``localhost``: answers each request with the next scripted answer
    (then the standing one: a status, a delay, headers and a body) and records it, with when it
    arrived and when it was answered."""

    def __init__(self) -> None:
        self.requests: list[dict] = []
        self.script: list[tuple[int, float, dict, bytes]] = []
        self.standing: tuple[int, float, dict, bytes] = (200, 0.0, {}, b"")
        self._lock = threading.Lock()
        receiver = self

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self) -> None:
                arrived = time.monotonic()
                body = self.rfile.read(int(self.headers["Content-Length"]))
                with receiver._lock:
                    status, delay, headers, answer = receiver.script.pop(0) if receiver.script else receiver.standing
                if delay:
                    time.sleep(delay)
                self.send_response(status)
                for name, value in headers.items():
                    self.send_header(name, value)
                self.send_header("Content-Length", str(len(answer)))
                self.end_headers()
                self.wfile.write(answer)
                with receiver._lock:
                    receiver.requests.append(
                        {
                            "path": self.path,
                            "headers": {name.lower(): value for name, value in self.headers.items()},
                            "raw": body,
                            "body": json.loads(body),
                            "status": status,
                            "arrived": arrived,
                            "answered": time.monotonic(),
                        }
                    )

            def log_message(self, *_args) -> None:
                pass

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.url = f"http://localhost:{self.server.server_address[1]}/hook"
        self._thread = threading.Thread(target=self.server.serve_forever, daemon=True)

    def answer(self, status: int, delay: float = 0.0, body: bytes = b"", **headers: str) -> None:
        self.standing = (status, delay, headers, body)

    def then(self, status: int, delay: float = 0.0, body: bytes = b"", **headers: str) -> None:
        self.script.append((status, delay, headers, body))

    def delivered(self) -> list[dict]:
        """The bodies of the requests answered ``2xx``, in the order they arrived."""
        answered = sorted(self.requests, key=lambda r: r["arrived"])
        return [r["body"] for r in answered if 200 <= r["status"] < 300]

    def __enter__(self) -> Self:
        self._thread.start()
        return self

    def __exit__(self, *_exc) -> None:
        self.server.shutdown()
        self.server.server_close()


@pytest.fixture
def receiver():
    with Receiver() as running:
        yield running


def _subscribe(world, workspace, url, **changes):
    body = {
        "name": "Ledger receiver",
        "consumerApi": world.key("Capi"),
        "workspaceKey": workspace,
        "events": [WATCHED],
        "url": url,
    }
    body.update(changes)
    return ok(world.api.post(PATH, body), 201)


def _read(world, subscription):
    return ok(world.api.get(f"{PATH}/{subscription['id']}"))


def _resume(world, subscription, **body):
    current = _read(world, subscription)
    return world.api.post(f"{PATH}/{current['id']}/resume", {"expectedVersion": current["version"], **body})


def _feed(world, workspace, after, *events):
    """The pull feed's events after ``after``, of ``events``, every page."""
    params = {"workspace": workspace, "after": after, "payload": "identity", "pageSize": 1000}
    items = []
    while True:
        page = ok(consumer_events(world, **params))
        items += [e for e in page["items"] if e["event"] in events]
        if page["caughtUp"]:
            return items
        params = {"workspace": workspace, "cursor": page["cursor"], "payload": "identity", "pageSize": 1000}


def _signed(secret, request):
    timestamp = request["headers"]["rdm-timestamp"]
    digest = hmac.new(secret.encode(), timestamp.encode() + b"." + request["raw"], hashlib.sha256)
    return request["headers"]["rdm-signature"] == f"sha256={digest.hexdigest()}"


def _ledgers(world, workspace, count, prefix):
    """``count`` exposed records created by one inline batch."""
    items = [
        {
            "op": "create",
            "applicationKey": world.app("R"),
            "objectTypeKey": world.key("R"),
            "name": f"{prefix} {index}",
            "attributes": [
                {"attributeTypeKey": key, "value": value}
                for key, value in {**world.required_values("R"), world.key("R.u"): f"{prefix}-{index}"}.items()
            ],
        }
        for index in range(count)
    ]
    body = {"workspaceKey": workspace, "policy": "atomic", "run": "inline", "items": items}
    result = ok(world.api.post("/batches", body))
    assert result["job"]["result"] == "applied", result["job"]


def _now():
    return datetime.now(UTC)


@pytest.mark.journey("J30.8")
@pytest.mark.settings(**SUBSCRIPTIONS)
@pytest.mark.structures(*LEDGER)
def test_a_subscription_receives_its_events_signed_and_in_order(world, receiver):
    """Given a subscription to the watched event with the full payload, batched. When exposed
    records are created, renamed and deleted. Then one request carries the events in position order, as the
    pull feed has them, each object as get by ID answers it, and none for the deleted record. The
    request is signed with the subscription's key over the timestamp and the body, and a body
    changed by one byte does not verify. The subscription has acknowledged through the last event
    and shows when it last delivered, with nothing pending and its version unchanged."""
    _activate(world, "events")
    ws = _workspace(world)
    created = _subscribe(world, ws, receiver.url, maxEventsPerBatch=100)
    secret, start = created["signingSecret"], created["acknowledgedThrough"]

    kept = world.made("R", "Ledger A", workspace=ws)
    ok(world.update("R", kept["id"], kept["version"], name="Ledger B"))
    gone = world.made("R", "Ledger C", workspace=ws)
    _delete(world, "R", gone["id"], ws)
    derive_events(world)
    dispatch(world)

    (request,) = receiver.requests
    body = request["body"]
    assert request["path"] == "/hook"
    assert request["headers"]["content-type"] == "application/json"
    assert request["headers"]["rdm-delivery-id"] == body["deliveryId"]
    assert abs(int(request["headers"]["rdm-timestamp"]) - time.time()) < 60
    assert _signed(secret, request)
    assert not _signed(secret, {**request, "raw": request["raw"].replace(b"Ledger", b"Ledges", 1)})
    assert (body["subscriptionId"], body["consumerApi"], body["contractVersion"], body["workspaceKey"]) == (
        created["id"],
        world.key("Capi"),
        1,
        ws,
    )
    expected = _feed(world, ws, start, WATCHED)
    assert [(e["eventId"], e["position"], e["change"], e["id"]) for e in body["events"]] == [
        (e["eventId"], e["position"], e["change"], e["id"]) for e in expected
    ]
    for event in body["events"]:
        if event["id"] == gone["id"]:
            # Composed when sent: an object deleted since has no object, code or name to send.
            assert "object" not in event and (event["code"], event["name"]) == (None, None)
        else:
            assert event["object"] == ok(consumer_object(world, event["id"], workspace=ws))
            assert event["stateAt"] >= event["position"]

    after = _read(world, created)
    assert after["acknowledgedThrough"] == body["events"][-1]["position"] == _head(world, ws)
    assert after["delivery"]["lastDeliveredAt"] and after["delivery"]["pending"] is None
    assert after["version"] == created["version"]


@pytest.mark.journey("J30.8")
@pytest.mark.settings(**SUBSCRIPTIONS)
@pytest.mark.structures(*LEDGER)
def test_many_events_arrive_in_ordered_batches_within_the_subscriptions_scope(world, receiver):
    """Given a full and an identity subscription to one event batching up to 100, and one narrowed
    to a type nothing here creates. When a batch creates 250 exposed records. Then each of the first two receives
    three requests of 100, 100 and 50 events in position order, each sent after the previous one was
    answered, only of its event; the identity requests carry no objects. The narrowed subscription
    receives nothing and has acknowledged through the feed's head."""
    _activate(world, "events")
    ws = _workspace(world)
    full = _subscribe(world, ws, receiver.url + "/full", events=[EVERY], maxEventsPerBatch=100)
    identity = _subscribe(
        world, ws, receiver.url + "/identity", events=[EVERY], payload="identity", maxEventsPerBatch=100
    )
    narrowed = _subscribe(world, ws, receiver.url + "/narrowed", filters={world.key("Capi.kind"): world.key("Capi.R2")})

    _ledgers(world, ws, 250, "Bulk")
    derive_events(world)
    dispatch(world)

    expected = [e["eventId"] for e in _feed(world, ws, full["acknowledgedThrough"], EVERY)]
    assert len(expected) == 250
    for path, payload in (("/hook/full", "full"), ("/hook/identity", "identity")):
        requests = [r for r in receiver.requests if r["path"] == path]
        assert [len(r["body"]["events"]) for r in requests] == [100, 100, 50]
        assert [e["eventId"] for r in requests for e in r["body"]["events"]] == expected
        assert all(e["event"] == EVERY for r in requests for e in r["body"]["events"])
        assert all(later["arrived"] >= earlier["answered"] for earlier, later in pairwise(requests))
        assert all(("object" in e) == (payload == "full") for r in requests for e in r["body"]["events"])
        assert all(("stateAt" in e) == (payload == "full") for r in requests for e in r["body"]["events"])
    assert not [r for r in receiver.requests if r["path"] == "/hook/narrowed"]
    assert _read(world, narrowed)["acknowledgedThrough"] == _head(world, ws)
    assert _read(world, identity)["acknowledgedThrough"] == _head(world, ws)


def _on(receiver, path):
    return [r for r in receiver.requests if r["path"] == path]


@pytest.mark.journey("J30.8")
@pytest.mark.settings(**SUBSCRIPTIONS)
@pytest.mark.structures(*LEDGER)
def test_a_subscription_sends_one_event_per_request_by_default(world, receiver):
    """Given a subscription created without a batch size. When three records are created. Then the
    receiver gets three requests in position order, each an RDM JSON envelope with one event, each
    answered before the next is sent. The subscription shows one event per request, and the
    capabilities the most a subscription may batch."""
    _activate(world, "events")
    assert ok(world.api.get("/capabilities"))["consumerSubscriptions"]["delivery"]["maxEventsPerBatch"] == 1000
    ws = _workspace(world)
    created = _subscribe(world, ws, receiver.url)
    assert (created["maxEventsPerBatch"], created["payload"], created["format"]) == (1, "full", "rdm")
    for name in ("One", "Two", "Three"):
        world.made("R", f"Ledger {name}", workspace=ws)
    derive_events(world)
    dispatch(world)

    expected = _feed(world, ws, created["acknowledgedThrough"], WATCHED)
    assert len(receiver.requests) == len(expected) == 3
    for request, event in zip(receiver.requests, expected, strict=True):
        assert request["headers"]["content-type"] == "application/json"
        assert request["body"]["subscriptionId"] == created["id"]
        assert request["headers"]["rdm-delivery-id"] == request["body"]["deliveryId"]
        assert [e["eventId"] for e in request["body"]["events"]] == [event["eventId"]]
        assert _signed(created["signingSecret"], request)
    assert len({r["body"]["deliveryId"] for r in receiver.requests}) == 3
    assert all(later["arrived"] >= earlier["answered"] for earlier, later in pairwise(receiver.requests))
    assert _read(world, created)["acknowledgedThrough"] == _head(world, ws)


@pytest.mark.journey("J30.8")
@pytest.mark.settings(**SUBSCRIPTIONS)
@pytest.mark.structures(*LEDGER)
def test_a_batched_subscription_sends_what_is_waiting_up_to_its_size_and_one_mebibyte(world, receiver):
    """Given a subscription batching up to 2 events. When five records are created, then requests
    of 2, 2 and 1 events arrive in position order. Given one batching up to 1,000 with the objects,
    when a batch creates 1,000 records whose events together exceed 1 MiB, then the first request
    stops before 1 MiB, short of 1,000 events, and every event arrives once, in order."""
    _activate(world, "events")
    ws = _workspace(world)
    pairs = _subscribe(world, ws, receiver.url + "/pairs", events=[EVERY], maxEventsPerBatch=2)
    _ledgers(world, ws, 5, "Paired")
    derive_events(world)
    dispatch(world)
    requests = _on(receiver, "/hook/pairs")
    assert [len(r["body"]["events"]) for r in requests] == [2, 2, 1]
    expected = [e["eventId"] for e in _feed(world, ws, pairs["acknowledgedThrough"], EVERY)]
    assert [e["eventId"] for r in requests for e in r["body"]["events"]] == expected

    large = _subscribe(world, ws, receiver.url + "/large", events=[EVERY], maxEventsPerBatch=1000)
    _ledgers(world, ws, 1000, "L" * 400)
    derive_events(world)
    dispatch(world)
    requests = _on(receiver, "/hook/large")
    assert sum(len(r["raw"]) for r in requests) > 1024 * 1024
    assert len(requests) >= 2 and 1 < len(requests[0]["body"]["events"]) < 1000
    assert all(len(r["raw"]) <= 1024 * 1024 for r in requests)
    expected = [e["eventId"] for e in _feed(world, ws, large["acknowledgedThrough"], EVERY)]
    assert [e["eventId"] for r in requests for e in r["body"]["events"]] == expected and len(expected) == 1000


@pytest.mark.journey("J30.8")
@pytest.mark.settings(**SUBSCRIPTIONS)
@pytest.mark.structures(*LEDGER)
@pytest.mark.parametrize("size", [1, 3])
def test_a_notification_carries_no_object_and_a_full_event_the_object_as_read(world, receiver, size):
    """Given a notification-only and a full subscription, sending one event per request or batching
    up to 3. When two records are created. Then the notification-only events carry no object and no
    ``stateAt``, and the full events the object as get by ID answers it."""
    _activate(world, "events")
    ws = _workspace(world)
    for payload in ("identity", "full"):
        _subscribe(world, ws, receiver.url + f"/{payload}", payload=payload, maxEventsPerBatch=size)
    world.made("R", "Ledger Told", workspace=ws)
    world.made("R", "Ledger Shown", workspace=ws)
    derive_events(world)
    dispatch(world)

    for payload in ("identity", "full"):
        events = [e for r in _on(receiver, f"/hook/{payload}") for e in r["body"]["events"]]
        assert len(events) == 2
        assert len(_on(receiver, f"/hook/{payload}")) == (2 if size == 1 else 1)
        for event in events:
            if payload == "identity":
                assert "object" not in event and "stateAt" not in event
            else:
                assert event["object"] == ok(consumer_object(world, event["id"], workspace=ws))


@pytest.mark.journey("J30.8")
@pytest.mark.settings(**SUBSCRIPTIONS)
@pytest.mark.structures(*LEDGER)
def test_cloudevents_are_sent_structured_one_per_request_and_as_an_array_when_batched(world, receiver):
    """Given an RDM JSON subscription, a CloudEvents one sending one event per request and a
    CloudEvents one batching up to 10, all to the watched event. When three records are created.
    Then the single ones arrive as structured CloudEvents, ``application/cloudevents+json``, and the
    batch as one array in position order, ``application/cloudevents-batch+json``. Each CloudEvent
    has spec version 1.0, the event ID as ``id``, the definition's events path in the workspace as
    ``source``, ``rdm.{event}.{change}`` as ``type``, ``{objectType}/{id}`` as ``subject``, the
    event's time, the subscription, and as ``data`` the event the RDM JSON receiver got for the same
    change. Every body verifies against its signature."""
    _activate(world, "events")
    ws = _workspace(world)
    rdm = _subscribe(world, ws, receiver.url + "/rdm", maxEventsPerBatch=10)
    single = _subscribe(world, ws, receiver.url + "/single", format="cloudevents")
    batched = _subscribe(world, ws, receiver.url + "/batched", format="cloudevents", maxEventsPerBatch=10)
    for name in ("One", "Two", "Three"):
        world.made("R", f"Ledger {name}", workspace=ws)
    derive_events(world)
    dispatch(world)

    (plain,) = _on(receiver, "/hook/rdm")
    told = {e["eventId"]: e for e in plain["body"]["events"]}
    source = f"/api/consumer/{world.key('Capi')}/v1/events?workspace={ws}"

    def check(cloudevent, subscription):
        event = told[cloudevent["id"]]
        assert cloudevent == {
            "specversion": "1.0",
            "id": event["eventId"],
            "source": source,
            "type": f"rdm.{event['event']}.{event['change']}",
            "subject": f"{event['objectType']}/{event['id']}",
            "time": event["occurredAt"],
            "datacontenttype": "application/json",
            "rdmsubscription": subscription["id"],
            "data": cloudevent["data"],
        }
        # The object is composed when sent, so only its state may differ between the receivers.
        assert {k: v for k, v in cloudevent["data"].items() if k not in {"object", "stateAt"}} == {
            k: v for k, v in event.items() if k not in {"object", "stateAt"}
        }
        assert "object" in cloudevent["data"] and "object" in event

    singles = _on(receiver, "/hook/single")
    assert [r["body"]["id"] for r in singles] == list(told)
    for request in singles:
        assert request["headers"]["content-type"] == "application/cloudevents+json; charset=utf-8"
        assert _signed(single["signingSecret"], request)
        check(request["body"], single)
    (array,) = _on(receiver, "/hook/batched")
    assert array["headers"]["content-type"] == "application/cloudevents-batch+json; charset=utf-8"
    assert _signed(batched["signingSecret"], array)
    assert [item["id"] for item in array["body"]] == list(told)
    for item in array["body"]:
        check(item, batched)
    assert _read(world, rdm)["acknowledgedThrough"] == _head(world, ws)


@pytest.mark.journey("J30.8")
@pytest.mark.settings(**SUBSCRIPTIONS)
@pytest.mark.structures(*LEDGER)
def test_an_edit_of_the_format_drops_a_retried_batch_and_sends_it_anew_in_the_new_format(world, receiver):
    """Given an RDM JSON subscription whose receiver answers 503. When a record is created and the
    attempt fails, an edit to CloudEvents drops the batch; a batch size outside 1–1,000 or the
    retired ``mode`` in an edit is a request validation error. Once the receiver answers, the event
    arrives as a CloudEvent under a new delivery ID."""
    _activate(world, "events")
    ws = _workspace(world)
    created = _subscribe(world, ws, receiver.url)
    receiver.then(503)
    world.made("R", "Ledger Reformatted", workspace=ws)
    derive_events(world)
    now = _now()
    dispatch(world, now)
    pending = _read(world, created)["delivery"]["pending"]
    assert pending["attempts"] == 1

    path = f"{PATH}/{created['id']}"
    for changes in ({"maxEventsPerBatch": 0}, {"maxEventsPerBatch": 1001}, {"mode": "perChange"}, {"format": "xml"}):
        refused(world.api.patch(path, {"expectedVersion": created["version"], **changes}), 422, "REQUEST_VALIDATION_ERROR")
    edited = ok(world.api.patch(path, {"expectedVersion": created["version"], "format": "cloudevents"}))
    assert edited["format"] == "cloudevents" and edited["delivery"]["pending"] is None
    dispatch(world, now + timedelta(seconds=1))

    failed, sent = receiver.requests
    assert sent["headers"]["rdm-delivery-id"] != failed["headers"]["rdm-delivery-id"] == pending["deliveryId"]
    assert sent["headers"]["content-type"] == "application/cloudevents+json; charset=utf-8"
    assert sent["body"]["id"] == failed["body"]["events"][0]["eventId"]
    assert _read(world, created)["acknowledgedThrough"] == _head(world, ws)


@pytest.mark.journey("J30.9")
@pytest.mark.settings(**SUBSCRIPTIONS)
@pytest.mark.structures(*LEDGER)
def test_a_failing_receiver_is_retried_with_the_same_batch_until_it_answers(world, receiver):
    """Given a subscription whose receiver answers 503. When a record is created. Then the attempt
    fails, the subscription shows the pending batch, its attempts, the last error and the next
    attempt, and a later change is not sent past it. The retry carries the same delivery ID and
    events with a new timestamp. A redirect and an answer slower than the timeout are failed
    attempts of their kind. Once the receiver answers, the batch and the one after it arrive in
    order, nothing is pending and the version is unchanged."""
    _activate(world, "events")
    ws = _workspace(world)
    created = _subscribe(world, ws, receiver.url)
    receiver.answer(503)
    world.made("R", "Ledger First", workspace=ws)
    derive_events(world)
    now = _now()
    dispatch(world, now)

    pending = _read(world, created)["delivery"]["pending"]
    assert (pending["attempts"], pending["lastError"]["kind"], pending["lastError"]["status"]) == (1, "status", 503)
    assert pending["failingSince"] and pending["lastAttemptAt"]
    assert datetime.fromisoformat(pending["nextAttemptAt"]) > now
    assert pending["throughPosition"] == _head(world, ws)

    world.made("R", "Ledger Second", workspace=ws)
    derive_events(world)
    dispatch(world, now)
    assert len(receiver.requests) == 1
    dispatch(world, now + timedelta(seconds=15))
    first, second = receiver.requests
    assert second["headers"]["rdm-delivery-id"] == first["headers"]["rdm-delivery-id"] == pending["deliveryId"]
    assert second["headers"]["rdm-timestamp"] != first["headers"]["rdm-timestamp"]
    assert [e["eventId"] for e in second["body"]["events"]] == [e["eventId"] for e in first["body"]["events"]]

    receiver.answer(302, Location="https://elsewhere.example.test/hook")
    dispatch(world, now + timedelta(seconds=60))
    error = _read(world, created)["delivery"]["pending"]["lastError"]
    assert error["kind"] == "redirect" and "elsewhere.example.test" in error["message"]

    world.api.client.app.state.consumer_dispatcher.timeout_seconds = 0.3
    receiver.answer(200, delay=1.0)
    dispatch(world, now + timedelta(minutes=5))
    pending = _read(world, created)["delivery"]["pending"]
    assert pending["lastError"]["kind"] == "timeout" and pending["attempts"] == 4

    receiver.answer(200)
    dispatch(world, now + timedelta(hours=1))
    after = _read(world, created)
    assert after["delivery"]["pending"] is None and after["version"] == created["version"]
    # The slow attempt reached the receiver after the dispatcher gave up on it: at least once.
    delivered = [e["eventId"] for body in receiver.delivered() for e in body["events"]]
    expected = [e["eventId"] for e in _feed(world, ws, created["acknowledgedThrough"], WATCHED)]
    assert list(dict.fromkeys(delivered)) == expected and len(expected) == 2
    assert after["acknowledgedThrough"] == _head(world, ws)


@pytest.mark.journey("J30.9")
@pytest.mark.settings(**SUBSCRIPTIONS)
@pytest.mark.structures(*LEDGER)
def test_a_receiver_failing_for_a_day_suspends_and_a_resume_delivers_everything(world, receiver):
    """Given a subscription whose receiver answers 500. When it fails for 24 hours of the
    dispatcher's clock. Then it is suspended DELIVERY_FAILED with the last error and the delivery,
    its version raised, and later changes are not sent. Once resumed, every event from the first
    unacknowledged one arrives, in order, none skipped."""
    _activate(world, "events")
    ws = _workspace(world)
    created = _subscribe(world, ws, receiver.url)
    receiver.answer(500)
    world.made("R", "Ledger Down", workspace=ws)
    derive_events(world)
    now = _now()
    clock = now
    dispatch(world, clock)
    while _read(world, created)["status"] == "active":
        assert clock < now + timedelta(hours=26)
        clock += timedelta(hours=2)
        dispatch(world, clock)

    suspended = _read(world, created)
    suspension = suspended["suspension"]
    assert suspension["reason"] == "DELIVERY_FAILED" and clock - now >= timedelta(hours=24)
    assert suspension["details"]["lastError"]["status"] == 500
    assert suspension["details"]["deliveryId"] == receiver.requests[0]["headers"]["rdm-delivery-id"]
    assert suspended["version"] == created["version"] + 1
    world.made("R", "Ledger While Down", workspace=ws)
    derive_events(world)
    sent = len(receiver.requests)
    dispatch(world, clock + timedelta(hours=3))
    assert len(receiver.requests) == sent

    receiver.answer(200)
    resumed = ok(_resume(world, created))
    assert resumed["status"] == "active" and resumed["delivery"]["pending"] is None
    dispatch(world)
    delivered = [e["eventId"] for body in receiver.delivered() for e in body["events"]]
    assert delivered == [e["eventId"] for e in _feed(world, ws, created["acknowledgedThrough"], WATCHED)]


@pytest.mark.journey("J30.9")
@pytest.mark.settings(**SUBSCRIPTIONS)
@pytest.mark.structures(*LEDGER)
def test_a_filter_matching_nothing_suspends(world, receiver):
    """Given a subscription narrowed to a token, when the ledger paired with it and the token are
    deleted, it is suspended FILTER_MATCHES_NOTHING naming the filter, the value and its position,
    and nothing is sent. After the filter is edited to another token and it is resumed, the deletions arrive."""
    _activate(world, "events")
    ws = _workspace(world)
    token, other = (world.made("K", f"Token {uuid4().hex[:6]}", workspace=ws) for _ in range(2))
    ledger = world.made("R", "Ledger Paired", workspace=ws)
    ok(world.relate("B11", ledger["id"], token["id"]), 201)
    derive_events(world)
    filter_name = world.key("Capi.token")
    narrowed = _subscribe(world, ws, receiver.url, events=[WATCHED, EVERY], filters={filter_name: token["name"]})
    start = narrowed["acknowledgedThrough"]
    _delete(world, "R", ledger["id"], ws)
    _delete(world, "K", token["id"], ws)
    derive_events(world)
    dispatch(world)

    assert receiver.requests == []
    suspended = _read(world, narrowed)
    suspension = suspended["suspension"]
    assert suspension["reason"] == "FILTER_MATCHES_NOTHING"
    assert suspension["details"]["parameter"] == filter_name and suspension["details"]["values"] == [token["name"]]
    assert suspension["details"]["position"] == start == suspended["acknowledgedThrough"]

    edited = ok(
        world.api.patch(f"{PATH}/{narrowed['id']}", {"expectedVersion": suspended["version"], "filters": {filter_name: other["name"]}})
    )
    ok(_resume(world, edited))
    dispatch(world)
    told = [(e["event"], e["change"]) for body in receiver.delivered() for e in body["events"] if e["id"] == ledger["id"]]
    assert (WATCHED, "deleted") in told and (EVERY, "deleted") in told


@pytest.mark.journey("J30.9")
@pytest.mark.settings(**SUBSCRIPTIONS)
@pytest.mark.structures(*LEDGER)
def test_events_expired_while_active_suspend_and_a_reset_starts_from_the_head(world, receiver):
    """Given an active subscription whose next events aged past retention (its dispatcher did not
    run). Then it is suspended EVENTS_EXPIRED with the lost range and the publication to re-sync
    from, and nothing is sent; a plain resume is refused as expired, naming reset; a resume with
    reset starts after the feed's head, and only later changes arrive. A subscription suspended by
    hand while changes are made and resumed with reset receives none of them."""
    _activate(world, "events")
    ws = _workspace(world)
    created = _subscribe(world, ws, receiver.url)
    start = created["acknowledgedThrough"]
    world.made("R", "Before", workspace=ws)
    cs = world.change_set(workspace=ws)
    world.made("R", "Added", change_set=world.current(cs), workspace=ws)
    publication = world.publish(cs, workspace=ws)
    world.made("R", "After", workspace=ws)
    derive_events(world)
    sequence = publication["feedPosition"]
    _age(world, ws, 31, sequence)
    dispatch(world)

    assert receiver.requests == []
    suspended = _read(world, created)
    assert suspended["suspension"]["reason"] == "EVENTS_EXPIRED"
    assert suspended["suspension"]["details"] == {
        "fromPosition": start + 1,
        "toPosition": sequence,
        "publication": {"id": publication["id"], "eventSequence": sequence},
    }
    error = refused(_resume(world, created), 409, "EVENTS_EXPIRED")
    assert "reset" in error["message"]
    resumed = ok(_resume(world, created, reset=True))
    assert (resumed["status"], resumed["acknowledgedThrough"]) == ("active", _feed_head(world, ws))
    fresh = world.made("R", "Fresh", workspace=ws)
    derive_events(world)
    dispatch(world)
    assert {e["id"] for body in receiver.delivered() for e in body["events"]} == {fresh["id"]}

    paused = _subscribe(world, ws, receiver.url + "/paused")
    ok(world.api.post(f"{PATH}/{paused['id']}/suspend", {"expectedVersion": paused["version"]}))
    world.made("R", "Missed", workspace=ws)
    derive_events(world)
    ok(_resume(world, paused, reset=True))
    dispatch(world)
    assert not [r for r in receiver.requests if r["path"] == "/hook/paused"]
    later = world.made("R", "Later", workspace=ws)
    derive_events(world)
    dispatch(world)
    told = {e["id"] for r in receiver.requests if r["path"] == "/hook/paused" for e in r["body"]["events"]}
    assert told == {later["id"]}


@pytest.mark.journey("J30.9")
@pytest.mark.settings(**SUBSCRIPTIONS)
@pytest.mark.structures(*LEDGER)
def test_two_dispatchers_deliver_each_batch_once_and_in_order(world, receiver):
    """Given one subscription batching up to 100 and two dispatchers on the database (two
    processes). When a batch creates 300 records and both dispatch at once. Then every event arrives exactly once, in
    position order, each batch under its own delivery ID."""
    _activate(world, "events")
    ws = _workspace(world)
    created = _subscribe(world, ws, receiver.url, events=[EVERY], payload="identity", maxEventsPerBatch=100)
    _ledgers(world, ws, 300, "Shared")
    derive_events(world)
    running = world.api.client.app.state.consumer_dispatcher
    other = type(running)(running.session_factory, running.settings)
    threads = [threading.Thread(target=d.run_until_idle) for d in (running, other)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(60)
    dispatch(world)

    delivered = [e["eventId"] for body in receiver.delivered() for e in body["events"]]
    assert delivered == [e["eventId"] for e in _feed(world, ws, created["acknowledgedThrough"], EVERY)]
    ids = [body["deliveryId"] for body in receiver.delivered()]
    assert len(ids) == len(set(ids)) == 3
