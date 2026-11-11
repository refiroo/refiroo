"""The ``consumer subscriptions`` area (webhooks) of the management API's reference, recorded from a run
on the guide's reference data (see ``test_reference_recording.py``, whose seed, scenario and normaliser
this file uses).

An integrator subscribes a receiver to the changes of the Graubünden stops in one municipality. The
receiver is a small HTTP server this test starts on the same machine and stops again; it answers 503 to
the first attempt, so the example shows a request being retried. A change set adds two stops and renames
one, and is published; the engine's event deriver and dispatcher run in the test's own thread (the
recording application starts neither), with a clock the test moves forward instead of waiting. The test
checks what the receiver got: one request carrying the three events, the same delivery ID on both
attempts, and a signature that verifies with the key the create answered. Then the integrator reads the
deliveries and one request, rotates the key, resends an event (which is signed with both keys), edits,
suspends, resumes and deletes the subscription. Each step records the main successful use of the
operation it calls; the refusals the area's text names are asserted without being recorded.

The signing key is replaced by a placeholder in the recorded files (``SECRET_MASKS``), and the receiver's
local address by an invented host (a call's ``mask``). No request leaves the machine.

    cd backend && RDM_RECORD_EXAMPLES=1 .venv/bin/python -m pytest tests/test_reference_webhooks.py -q
"""

import hashlib
import hmac
import json
import threading
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Self

import pytest
import seeds
from test_reference_change_sets import CHANGE_SETS, GRAUBUENDEN, _new_stop, _publish_body, _version
from test_reference_change_sets import ONE as CHANGE_SET
from test_reference_recording import (
    RECORDING,
    SEED,
    Scenario,
    _application,
    _register_seed,
)
from test_reference_records import _one

SUBSCRIPTIONS = "/api/v1/consumer-subscriptions"
ONE = SUBSCRIPTIONS + "/{subscription_id}"
DELIVERIES = ONE + "/deliveries"
DELIVERY = DELIVERIES + "/{delivery_id}"
CAPABILITY = {
    "CONSUMER_SUBSCRIPTIONS_ENABLED": "true",
    "WEBHOOK_PRIVATE_ADDRESSES_ALLOWED": "true",  # the receiver listens on localhost
}
# The address the examples show: the recorded calls went to the receiver on this machine.
SHOWN = {"url": "https://hooks.example.org/rdm/stops"}


class Receiver:
    """A webhook receiver on ``localhost``: answers each request with the next scripted answer (then 200)
    and records it."""

    def __init__(self) -> None:
        self.requests: list[dict[str, Any]] = []
        self.script: list[tuple[int, bytes]] = []
        self._lock = threading.Lock()
        receiver = self

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self) -> None:
                body = self.rfile.read(int(self.headers["Content-Length"]))
                with receiver._lock:
                    status, answer = receiver.script.pop(0) if receiver.script else (200, b"ok")
                    receiver.requests.append(
                        {
                            "headers": {k.lower(): v for k, v in self.headers.items()},
                            "raw": body,
                            "body": json.loads(body),
                            "status": status,
                        }
                    )
                self.send_response(status)
                self.send_header("Content-Length", str(len(answer)))
                self.end_headers()
                self.wfile.write(answer)

            def log_message(self, *_args: Any) -> None:
                pass

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.url = f"http://localhost:{self.server.server_address[1]}/rdm/stops"
        self._thread = threading.Thread(target=self.server.serve_forever, daemon=True)

    def then(self, status: int, body: bytes = b"") -> None:
        self.script.append((status, body))

    def __enter__(self) -> Self:
        self._thread.start()
        return self

    def __exit__(self, *_exc: object) -> None:
        self.server.shutdown()
        self.server.server_close()
        self._thread.join(5)


def signatures(secret: str, request: dict[str, Any]) -> list[str]:
    """The signatures ``secret`` makes of the request, as the header lists them."""
    stamp = request["headers"]["rdm-timestamp"].encode()
    return [
        f"sha256={hmac.new(secret.encode(), stamp + b'.' + request['raw'], hashlib.sha256).hexdigest()}"
    ]


def verifies(secret: str, request: dict[str, Any]) -> bool:
    return signatures(secret, request)[0] in request["headers"]["rdm-signature"].split(",")


@pytest.fixture(scope="module")
def hooks() -> Iterator[tuple[Scenario, Receiver]]:
    _register_seed()
    seeds.ensure(SEED)
    url = seeds.clone(SEED)
    try:
        with Receiver() as receiver, _application(url, CAPABILITY) as client:
            scenario = Scenario(client)
            yield scenario, receiver
            if RECORDING:
                scenario.write_examples()
    finally:
        seeds.drop(url.database)


def _version_of(s: Scenario, subscription_id: str) -> int:
    return s.call("GET", ONE, path={"subscription_id": subscription_id}, status=200)["version"]


def test_an_integrator_receives_the_changes_of_a_municipality_by_webhook(hooks):
    s, receiver = hooks
    state = s.client.app.state
    zuoz = _one(s, "municipality", "Zuoz")
    train = _one(s, "mode", "Train")
    wanted = {
        "name": "Stops of Zuoz",
        "consumerApi": "stops",
        "workspaceKey": "graubuenden",
        "events": ["stops-changed"],
        "filters": {"municipality": ["Zuoz"]},
        "url": receiver.url,
        "maxEventsPerBatch": 10,
    }

    # What is refused before anything is stored.
    s.call(
        "POST",
        SUBSCRIPTIONS,
        body={**wanted, "url": "http://hooks.example.org/rdm"},
        status=400,
        code="INVALID_WEBHOOK_URL",
    )
    s.call(
        "POST",
        SUBSCRIPTIONS,
        body={**wanted, "events": ["no-such-event"]},
        status=400,
        code="UNKNOWN_EVENT",
    )
    s.call(
        "POST",
        SUBSCRIPTIONS,
        body={**wanted, "filters": {"municipality": ["Nowhere"]}},
        status=400,
        code="FILTER_MATCHES_NOTHING",
    )
    s.call(
        "POST",
        SUBSCRIPTIONS,
        body={**wanted, "consumerApi": "nothing"},
        status=400,
        code="CONSUMER_API_NOT_FOUND",
    )

    created = s.call(
        "POST",
        SUBSCRIPTIONS,
        body=wanted,
        status=201,
        record="create",
        summary="Subscribe a receiver to the changes of the stops of Zuoz, up to ten events per request",
        mask=SHOWN,
        notes=[
            (
                "The answer is the only one that holds `signingSecret`; no read returns it again. The "
                "recorded call went to a receiver on the same machine; the address shown is invented."
            )
        ],
    )
    secret, sub = created["signingSecret"], created["id"]
    assert secret.startswith("rdmwh_") and created["status"] == "active" and created["version"] == 1
    assert created["owner"]["kind"] == "user" and created["acknowledgedThrough"] >= 0
    where = {"subscription_id": sub}
    s.call(
        "GET",
        SUBSCRIPTIONS,
        query={"consumerApi": "stops", "pageSize": 5},
        status=200,
        record="ofTheStopsApi",
        summary="The subscriptions of the stops API, newest first; no list answers the signing key",
        mask=SHOWN,
    )
    assert "signingSecret" not in s.call("GET", ONE, path=where, status=200)
    s.call(
        "GET",
        ONE,
        path={"subscription_id": "00000000-0000-4000-8000-00000000ffff"},
        status=404,
        code="SUBSCRIPTION_NOT_FOUND",
    )

    # A change set adds two stops in Zuoz and renames one; publishing it makes three events.
    started = s.call(
        "POST",
        CHANGE_SETS,
        path=GRAUBUENDEN,
        body={"name": "Zuoz: new stops", "source": "currentLive"},
        status=201,
    )
    cs = started["id"]
    _new_stop(s, cs, zuoz["id"], "Zuoz, Sportplatz", train["id"])
    _new_stop(s, cs, zuoz["id"], "Zuoz, Post", train["id"])
    stop = s.call(
        "GET",
        "/api/v1/objects/{object_type_key}",
        path={"object_type_key": "stop"},
        query={"parentObjectId": zuoz["id"], "sort": "name", "pageSize": 1},
        status=200,
    )["items"][0]
    s.call(
        "PATCH",
        "/api/v1/objects/{object_type_key}/{object_id}",
        path={"object_type_key": "stop", "object_id": stop["id"]},
        body={
            "name": stop["name"] + " (Bahnhof)",
            "expectedVersion": stop["version"],
            "changeSetId": cs,
            "expectedChangeSetVersion": _version(s, cs),
        },
        status=200,
    )
    s.call(
        "POST",
        CHANGE_SET + "/publication",
        path={"change_set_id": cs},
        body=_publish_body(s, cs),
        status=200,
    )
    assert state.event_deriver.run_until_idle() >= 1

    # The receiver is unavailable at first: the request is retried with the same delivery ID.
    receiver.then(503, b"Service Unavailable")
    now = datetime.now(UTC)
    state.consumer_dispatcher.run_until_idle(now)
    (failed,) = receiver.requests
    assert failed["status"] == 503 and verifies(secret, failed)
    retried = s.call(
        "GET",
        ONE,
        path=where,
        status=200,
        record="whileARequestIsRetried",
        summary="A subscription whose last request failed: the request being retried and when it is due",
        mask=SHOWN,
        notes=[
            (
                "The times in the examples are placeholders in the order things happened, not the real "
                "gaps: the first retry follows the first failure after about 10 seconds."
            )
        ],
    )
    pending = retried["delivery"]["pending"]
    assert pending["attempts"] == 1 and pending["lastError"]["kind"] == "status"
    assert retried["acknowledgedThrough"] == created["acknowledgedThrough"]
    state.consumer_dispatcher.run_until_idle(now + timedelta(minutes=1))
    assert len(receiver.requests) == 2
    second = receiver.requests[1]
    assert second["status"] == 200 and verifies(secret, second)
    assert second["headers"]["rdm-delivery-id"] == failed["headers"]["rdm-delivery-id"]
    assert second["headers"]["rdm-delivery-id"] == pending["deliveryId"]
    sent = second["body"]["events"]
    assert len(sent) == 3 and {item["change"] for item in sent} == {"created", "updated"}

    rows = s.call(
        "GET",
        DELIVERIES,
        path=where,
        query={"pageSize": 3},
        status=200,
        record="newestFirst",
        summary="What was delivered, one row per event; the three events of one request share its status and attempts",
    )
    assert {row["deliveryId"] for row in rows["items"]} == {pending["deliveryId"]}
    assert {(row["status"], row["attempts"], row["responseStatus"]) for row in rows["items"]} == {
        ("succeeded", 2, 200)
    }
    s.call("GET", DELIVERIES, path=where, query={"status": "failed"}, status=200)
    delivery = s.call(
        "GET",
        DELIVERY,
        path={**where, "delivery_id": pending["deliveryId"]},
        status=200,
        record="aRequestWithItsAttempts",
        summary="One request: its events, the body the receiver got and both attempts, the first answered 503",
    )
    assert [a["responseStatus"] for a in delivery["attempts"]] == [503, 200]
    assert delivery["requestBytes"] == len(second["raw"])
    s.call(
        "GET",
        DELIVERY,
        path={**where, "delivery_id": "00000000-0000-4000-8000-00000000ffff"},
        status=404,
        code="DELIVERY_NOT_FOUND",
    )

    # A new signing key: for 24 hours every request is signed with both keys.
    rotated = s.call(
        "POST",
        ONE + "/rotate-secret",
        path=where,
        body={"expectedVersion": _version_of(s, sub), "overlapHours": 24},
        status=200,
        record="rotate",
        summary="Make a new signing key; the previous one keeps signing beside it for 24 hours",
        mask=SHOWN,
    )
    assert rotated["signingSecret"] != secret and rotated["previousSigningKeyExpiresAt"] is not None

    event = delivery["events"][0]
    s.call(
        "POST",
        DELIVERY + "/resend",
        path={**where, "delivery_id": pending["deliveryId"]},
        body={"eventId": "00000000-0000-4000-8000-00000000ffff"},
        status=404,
        code="EVENT_NOT_IN_DELIVERY",
    )
    resent = s.call(
        "POST",
        DELIVERY + "/resend",
        path={**where, "delivery_id": pending["deliveryId"]},
        body={"eventId": event["eventId"]},
        status=201,
        record="resend",
        summary="Send one event of a delivered request again, alone, as it was sent",
    )
    assert resent["resendOf"] == pending["deliveryId"] and resent["status"] == "succeeded"
    again = receiver.requests[-1]
    assert again["headers"]["rdm-redelivery"] == "manual"
    assert again["body"]["events"] == [
        next(item for item in sent if item["eventId"] == event["eventId"])
    ]
    assert verifies(rotated["signingSecret"], again) and verifies(secret, again)
    assert len(again["headers"]["rdm-signature"].split(",")) == 2

    # Edit: one event per request from now on. Stale versions are refused.
    s.call(
        "PATCH",
        ONE,
        path=where,
        body={"maxEventsPerBatch": 1, "expectedVersion": 1},
        status=409,
        code="VERSION_CONFLICT",
    )
    edited = s.call(
        "PATCH",
        ONE,
        path=where,
        body={"maxEventsPerBatch": 1, "expectedVersion": _version_of(s, sub)},
        status=200,
        record="update",
        summary="Send one event per request from now on",
        mask=SHOWN,
    )
    assert edited["maxEventsPerBatch"] == 1 and edited["version"] == rotated["version"] + 1

    suspended = s.call(
        "POST",
        ONE + "/suspend",
        path=where,
        body={"expectedVersion": edited["version"]},
        status=200,
        record="suspend",
        summary="Stop delivery until the subscription is resumed",
        mask=SHOWN,
    )
    assert (
        suspended["status"] == "suspended"
        and suspended["suspension"]["reason"] == "SUSPENDED_BY_USER"
    )
    s.call(
        "POST",
        ONE + "/suspend",
        path=where,
        body={"expectedVersion": suspended["version"]},
        status=409,
        code="SUBSCRIPTION_ALREADY_SUSPENDED",
    )
    resumed = s.call(
        "POST",
        ONE + "/resume",
        path=where,
        body={"expectedVersion": suspended["version"]},
        status=200,
        record="resume",
        summary="Continue from the first event not acknowledged",
        mask=SHOWN,
    )
    assert resumed["status"] == "active" and resumed["suspension"] is None
    s.call(
        "POST",
        ONE + "/resume",
        path=where,
        body={"expectedVersion": resumed["version"]},
        status=409,
        code="SUBSCRIPTION_NOT_SUSPENDED",
    )

    s.call(
        "DELETE",
        ONE,
        path=where,
        query={"expectedVersion": 1},
        status=409,
        code="VERSION_CONFLICT",
    )
    s.call(
        "DELETE",
        ONE,
        path=where,
        query={"expectedVersion": resumed["version"]},
        status=204,
        record="delete",
        summary="Delete the subscription; its delivery log goes with it",
    )
    s.call("GET", ONE, path=where, status=404, code="SUBSCRIPTION_NOT_FOUND")
    s.call("GET", DELIVERIES, path=where, status=404, code="SUBSCRIPTION_NOT_FOUND")
