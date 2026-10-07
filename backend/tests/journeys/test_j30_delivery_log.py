"""J30.6 (a subscription's name) and J30.10 — Read what a subscription delivered (USER_JOURNEYS.md,
Base 0.9 U5a, C-D115–C-D119).

As in ``test_j30_delivery``: the application with the subscriptions capability on, a receiver on
``localhost`` scripted per test, and the deriver and dispatcher run by the test with a clock it
moves forward. The log is read through ``/consumer-subscriptions/{id}/deliveries``: one row per
event a request carried, newest first, and each request's detail with its body and attempts.
"""

import json
from datetime import UTC, datetime, timedelta

import pytest
from scenario import derive_events, dispatch, ok, refused
from test_j30_consumer_events import EVERY, LEDGER, WATCHED, _activate, _workspace
from test_j30_delivery import Receiver, _read, _signed, _subscribe
from test_j30_subscriptions import PATH, SUBSCRIPTIONS


@pytest.fixture
def receiver():
    with Receiver() as running:
        yield running


def _now():
    return datetime.now(UTC)


def _deliveries(world, subscription, **params):
    """Every row of the subscription's deliveries, page after page."""
    rows, cursor = [], None
    while True:
        page = ok(world.api.get(f"{PATH}/{subscription['id']}/deliveries", pageSize=2, **({"cursor": cursor} if cursor else {}), **params))
        rows += page["items"]
        cursor = page.get("nextCursor")
        if not cursor:
            return rows


def _detail(world, subscription, delivery_id):
    return ok(world.api.get(f"{PATH}/{subscription['id']}/deliveries/{delivery_id}"))


@pytest.mark.journey("J30.6")
@pytest.mark.settings(**SUBSCRIPTIONS)
@pytest.mark.structures(*LEDGER)
def test_a_subscription_has_a_name_and_renaming_keeps_a_batch_being_retried(world, receiver):
    """Given the capability on. When an operator subscribes without a name, then 422; with a name,
    every read carries it. Given a batch being retried, a rename alone changes the name and keeps
    the batch pending as it was; another edit drops it."""
    _activate(world, "events")
    ws = _workspace(world)
    nameless = {"consumerApi": world.key("Capi"), "workspaceKey": ws, "events": [WATCHED], "url": receiver.url}
    refused(world.api.post(PATH, nameless), 422, "REQUEST_VALIDATION_ERROR")
    refused(world.api.post(PATH, {**nameless, "name": ""}), 422, "REQUEST_VALIDATION_ERROR")

    created = _subscribe(world, ws, receiver.url, name="Billing feed")
    assert created["name"] == "Billing feed"
    assert _read(world, created)["name"] == "Billing feed"
    assert [item["name"] for item in ok(world.api.get(PATH, workspaceKey=ws))["items"]] == ["Billing feed"]

    receiver.answer(503)
    world.made("R", "Ledger Named", workspace=ws)
    derive_events(world)
    dispatch(world, _now())
    pending = _read(world, created)["delivery"]["pending"]
    assert pending is not None

    renamed = ok(world.api.patch(f"{PATH}/{created['id']}", {"expectedVersion": created["version"], "name": "Invoices"}))
    assert renamed["name"] == "Invoices" and renamed["delivery"]["pending"] == pending
    edited = ok(world.api.patch(f"{PATH}/{created['id']}", {"expectedVersion": renamed["version"], "url": receiver.url + "/b"}))
    assert edited["name"] == "Invoices" and edited["delivery"]["pending"] is None


@pytest.mark.journey("J30.10")
@pytest.mark.settings(**SUBSCRIPTIONS)
@pytest.mark.structures(*LEDGER)
def test_the_deliveries_list_each_event_with_what_was_sent_and_answered(world, receiver):
    """Given a receiver answering 200 with a body and a subscription batching up to 10. When two
    records are created and delivered.
    Then the deliveries list one row per event, newest first, each succeeded after one attempt with
    status 200, the event IDs, events and object IDs the receiver got. The request's detail holds
    the body as the receiver got it and one attempt, started before it completed, with the answer."""
    _activate(world, "events")
    ws = _workspace(world)
    created = _subscribe(world, ws, receiver.url, events=[EVERY], maxEventsPerBatch=10)
    receiver.answer(200, body=b'{"accepted": true}', **{"Content-Type": "application/json"})
    first = world.made("R", "Ledger One", workspace=ws)
    second = world.made("R", "Ledger Two", workspace=ws)
    derive_events(world)
    dispatch(world)

    (request,) = receiver.requests
    sent = request["body"]["events"]
    rows = _deliveries(world, created)
    assert [row["eventId"] for row in rows] == [event["eventId"] for event in reversed(sent)]
    assert [row["objectId"] for row in rows] == [second["id"], first["id"]]
    for row, event in zip(rows, reversed(sent), strict=True):
        assert (row["event"], row["change"], row["position"], row["objectType"]) == (
            event["event"],
            event["change"],
            event["position"],
            event["objectType"],
        )
        assert (row["status"], row["attempts"], row["responseStatus"]) == ("succeeded", 1, 200)
        assert row["deliveryId"] == request["headers"]["rdm-delivery-id"]
        assert row["sentAt"] and row["nextAttemptAt"] is None

    detail = _detail(world, created, rows[0]["deliveryId"])
    assert "kind" not in detail
    assert (detail["status"], detail["requestBytes"]) == ("succeeded", len(request["raw"]))
    assert detail["requestBody"] == json.loads(request["raw"])
    assert [event["eventId"] for event in detail["events"]] == [event["eventId"] for event in sent]
    (attempt,) = detail["attempts"]
    assert attempt["number"] == 1 and attempt["responseStatus"] == 200 and attempt["error"] is None
    assert datetime.fromisoformat(attempt["startedAt"]) <= datetime.fromisoformat(attempt["completedAt"])
    assert attempt["durationMs"] >= 0
    assert json.loads(attempt["responseBody"]) == {"accepted": True}


@pytest.mark.journey("J30.10")
@pytest.mark.settings(**SUBSCRIPTIONS)
@pytest.mark.structures(*LEDGER)
def test_a_retried_request_shows_each_attempt_and_when_the_next_is_due(world, receiver):
    """Given a receiver answering 503, then 200. After the first round the event's row is retrying
    after one attempt with 503, due when the subscription says the next attempt is. After the retry
    it succeeded after two attempts, and the detail lists both answers in order."""
    _activate(world, "events")
    ws = _workspace(world)
    created = _subscribe(world, ws, receiver.url)
    receiver.then(503, body=b"busy")
    world.made("R", "Ledger Retry", workspace=ws)
    derive_events(world)
    now = _now()
    dispatch(world, now)

    (row,) = _deliveries(world, created)
    pending = _read(world, created)["delivery"]["pending"]
    assert (row["status"], row["attempts"], row["responseStatus"]) == ("retrying", 1, 503)
    assert row["deliveryId"] == pending["deliveryId"]
    assert datetime.fromisoformat(row["nextAttemptAt"]) == datetime.fromisoformat(pending["nextAttemptAt"])
    assert _deliveries(world, created, status="retrying") == [row]
    assert _deliveries(world, created, status="succeeded") == []

    dispatch(world, now + timedelta(minutes=1))
    (row,) = _deliveries(world, created)
    assert (row["status"], row["attempts"], row["responseStatus"], row["nextAttemptAt"]) == ("succeeded", 2, 200, None)
    attempts = _detail(world, created, row["deliveryId"])["attempts"]
    assert [(a["number"], a["responseStatus"]) for a in attempts] == [(1, 503), (2, 200)]
    assert attempts[0]["error"]["kind"] == "status" and attempts[0]["responseBody"] == "busy"


@pytest.mark.journey("J30.10")
@pytest.mark.settings(**SUBSCRIPTIONS)
@pytest.mark.structures(*LEDGER)
def test_an_edit_drops_a_retried_request_and_a_day_of_failures_fails_it(world, receiver):
    """Given a receiver answering 500. An edit of the URL while the batch is retried leaves its rows
    dropped, and the next batch has a new delivery ID. When the receiver keeps failing for a day,
    that batch's rows are failed and the subscription is suspended DELIVERY_FAILED."""
    _activate(world, "events")
    ws = _workspace(world)
    created = _subscribe(world, ws, receiver.url)
    receiver.answer(500)
    world.made("R", "Ledger Dropped", workspace=ws)
    derive_events(world)
    now = _now()
    dispatch(world, now)
    (dropped,) = _deliveries(world, created)

    edited = ok(world.api.patch(f"{PATH}/{created['id']}", {"expectedVersion": created["version"], "url": receiver.url + "/b"}))
    assert _deliveries(world, created)[0]["status"] == "dropped"
    clock = now + timedelta(seconds=1)
    dispatch(world, clock)
    newest = _deliveries(world, created)[0]
    assert newest["status"] == "retrying" and newest["deliveryId"] != dropped["deliveryId"]

    while _read(world, edited)["status"] == "active":
        assert clock < now + timedelta(hours=26)
        clock += timedelta(hours=2)
        dispatch(world, clock)
    assert _read(world, edited)["suspension"]["reason"] == "DELIVERY_FAILED"
    statuses = {(row["deliveryId"], row["status"]) for row in _deliveries(world, created)}
    assert statuses == {(dropped["deliveryId"], "dropped"), (newest["deliveryId"], "failed")}


@pytest.mark.journey("J30.10")
@pytest.mark.settings(**SUBSCRIPTIONS, CONSUMER_WEBHOOK_LOG_RETENTION_DAYS="7")
@pytest.mark.structures(*LEDGER)
def test_deliveries_are_kept_for_the_retention_and_a_pending_batch_is_kept_longer(world, receiver):
    """Given a log retention of 7 days, reported in capabilities, a delivered subscription and one
    whose batch failed and that the operator suspended. When the dispatcher runs 8 days later, the
    delivered rows and their detail are gone, and the pending batch's rows are kept."""
    _activate(world, "events")
    capabilities = ok(world.api.get("/capabilities"))["consumerSubscriptions"]
    assert capabilities["logRetentionDays"] == 7
    ws = _workspace(world)
    delivered = _subscribe(world, ws, receiver.url + "/ok", name="Delivered")
    failing = _subscribe(world, ws, receiver.url + "/down", name="Failing")
    receiver.then(200)
    receiver.then(500)
    world.made("R", "Ledger Kept", workspace=ws)
    derive_events(world)
    now = _now()
    dispatch(world, now)
    (gone,) = _deliveries(world, delivered)
    (kept,) = _deliveries(world, failing)
    statuses = {gone["status"], kept["status"]}
    assert statuses == {"succeeded", "retrying"}
    if gone["status"] != "succeeded":
        delivered, failing, gone, kept = failing, delivered, kept, gone
    current = _read(world, failing)
    ok(world.api.post(f"{PATH}/{failing['id']}/suspend", {"expectedVersion": current["version"]}))

    dispatch(world, now + timedelta(days=8))
    assert _deliveries(world, delivered) == []
    refused(world.api.get(f"{PATH}/{delivered['id']}/deliveries/{gone['deliveryId']}"), 404, "DELIVERY_NOT_FOUND")
    assert [row["deliveryId"] for row in _deliveries(world, failing)] == [kept["deliveryId"]]


@pytest.mark.journey("J30.10")
@pytest.mark.settings(**SUBSCRIPTIONS)
@pytest.mark.structures(*LEDGER)
def test_unknown_deliveries_are_refused_and_a_deleted_subscription_takes_its_log(world, receiver):
    """An unknown delivery ID is 404 DELIVERY_NOT_FOUND, an unknown subscription 404
    SUBSCRIPTION_NOT_FOUND; once a subscription is deleted its deliveries answer 404 too."""
    _activate(world, "events")
    ws = _workspace(world)
    created = _subscribe(world, ws, receiver.url)
    world.made("R", "Ledger Logged", workspace=ws)
    derive_events(world)
    dispatch(world)
    (row,) = _deliveries(world, created)

    refused(world.api.get(f"{PATH}/{created['id']}/deliveries/no-such-delivery"), 404, "DELIVERY_NOT_FOUND")
    refused(world.api.get(f"{PATH}/no-such-subscription/deliveries"), 404, "SUBSCRIPTION_NOT_FOUND")
    refused(world.api.get(f"{PATH}/no-such-subscription/deliveries/{row['deliveryId']}"), 404, "SUBSCRIPTION_NOT_FOUND")
    current = _read(world, created)
    assert world.api.delete(f"{PATH}/{created['id']}", expectedVersion=current["version"]).status_code == 204
    refused(world.api.get(f"{PATH}/{created['id']}/deliveries"), 404, "SUBSCRIPTION_NOT_FOUND")


def _resend(world, subscription, delivery_id, event_id=None):
    body = {"eventId": event_id} if event_id else {}
    return world.api.post(f"{PATH}/{subscription['id']}/deliveries/{delivery_id}/resend", body)


def _cloudevents(request):
    """The CloudEvents a request carried: the structured event alone, or the batch."""
    return request["body"] if isinstance(request["body"], list) else [request["body"]]


@pytest.mark.journey("J30.10")
@pytest.mark.settings(**SUBSCRIPTIONS)
@pytest.mark.structures(*LEDGER)
def test_a_delivered_event_is_resent_by_hand_as_it_was_sent(world, receiver):
    """Given an event delivered among others in a batch. When the operator resends it. Then the receiver gets
    one request with a new delivery ID, that event exactly as it was sent, RDM-Redelivery: manual
    and a valid signature; the answer and a new newest row are succeeded and name the delivery
    they repeat; the subscription's position and delivery state are unchanged."""
    _activate(world, "events")
    ws = _workspace(world)
    created = _subscribe(world, ws, receiver.url, events=[EVERY], maxEventsPerBatch=10)
    world.made("R", "Ledger First", workspace=ws)
    second = world.made("R", "Ledger Second", workspace=ws)
    derive_events(world)
    dispatch(world)
    (first_request,) = receiver.requests
    sent = next(event for event in first_request["body"]["events"] if event["id"] == second["id"])
    before = _read(world, created)
    original = next(row for row in _deliveries(world, created) if row["eventId"] == sent["eventId"])

    resent = ok(_resend(world, created, original["deliveryId"], sent["eventId"]), 201)
    request = receiver.requests[-1]
    assert len(receiver.requests) == 2
    assert request["headers"]["rdm-redelivery"] == "manual"
    assert _signed(created["signingSecret"], request)
    assert request["body"]["deliveryId"] == resent["deliveryId"] != original["deliveryId"]
    assert request["body"]["events"] == [sent]
    assert (resent["status"], resent["resendOf"], len(resent["attempts"])) == ("succeeded", original["deliveryId"], 1)
    newest = _deliveries(world, created)[0]
    assert (newest["deliveryId"], newest["eventId"], newest["resendOf"], newest["status"]) == (
        resent["deliveryId"],
        sent["eventId"],
        original["deliveryId"],
        "succeeded",
    )
    after = _read(world, created)
    assert (after["acknowledgedThrough"], after["delivery"]["pending"], after["version"]) == (
        before["acknowledgedThrough"],
        before["delivery"]["pending"],
        before["version"],
    )


@pytest.mark.journey("J30.10")
@pytest.mark.settings(**SUBSCRIPTIONS)
@pytest.mark.structures(*LEDGER)
def test_a_resend_to_a_failing_receiver_fails_once_even_while_suspended(world, receiver):
    """Given a delivered event and the subscription then suspended. When the operator resends it to
    a receiver answering 500. Then the resend is failed after one attempt, and the dispatcher does
    not try it again."""
    _activate(world, "events")
    ws = _workspace(world)
    created = _subscribe(world, ws, receiver.url)
    world.made("R", "Ledger Resent", workspace=ws)
    derive_events(world)
    dispatch(world)
    (row,) = _deliveries(world, created)
    current = _read(world, created)
    ok(world.api.post(f"{PATH}/{created['id']}/suspend", {"expectedVersion": current["version"]}))

    receiver.answer(500)
    resent = ok(_resend(world, created, row["deliveryId"], row["eventId"]), 201)
    assert (resent["status"], [a["responseStatus"] for a in resent["attempts"]]) == ("failed", [500])
    sent = len(receiver.requests)
    current = _read(world, created)
    ok(world.api.post(f"{PATH}/{created['id']}/resume", {"expectedVersion": current["version"]}))
    dispatch(world, _now() + timedelta(hours=1))
    assert len(receiver.requests) == sent
    assert _detail(world, created, resent["deliveryId"])["status"] == "failed"


@pytest.mark.journey("J30.10")
@pytest.mark.settings(**SUBSCRIPTIONS)
@pytest.mark.structures(*LEDGER)
def test_what_cannot_be_resent_is_refused(world, receiver):
    """Given a delivered request. A resend naming no event is a request validation error, and an
    event ID not in the request is 404 EVENT_NOT_IN_DELIVERY; nothing is sent."""
    _activate(world, "events")
    ws = _workspace(world)
    created = _subscribe(world, ws, receiver.url)
    world.made("R", "Ledger Refused", workspace=ws)
    derive_events(world)
    dispatch(world)
    (row,) = _deliveries(world, created)

    refused(_resend(world, created, row["deliveryId"]), 422, "REQUEST_VALIDATION_ERROR")
    error = refused(_resend(world, created, row["deliveryId"], "no-such-event"), 404, "EVENT_NOT_IN_DELIVERY")
    assert error["details"]["pointer"] == "/eventId"
    assert len(receiver.requests) == 1 and len(_deliveries(world, created)) == 1


@pytest.mark.journey("J30.10")
@pytest.mark.settings(**SUBSCRIPTIONS)
@pytest.mark.structures(*LEDGER)
@pytest.mark.parametrize("size", [1, 10])
def test_a_cloudevent_is_resent_alone_in_the_content_mode_it_was_sent_in(world, receiver, size):
    """Given a CloudEvents subscription sending one event per request, or batching up to 10, and
    two delivered events. When the operator edits the subscription to RDM JSON and resends the
    second event. Then the receiver gets that CloudEvent exactly as it was sent, structured, or as
    a batch of one, in the original content type, with a new delivery ID, ``RDM-Redelivery:
    manual`` and a valid signature; its row names the event and the delivery it repeats."""
    _activate(world, "events")
    ws = _workspace(world)
    created = _subscribe(world, ws, receiver.url, events=[EVERY], format="cloudevents", maxEventsPerBatch=size)
    world.made("R", "Ledger Sent", workspace=ws)
    world.made("R", "Ledger Again", workspace=ws)
    derive_events(world)
    dispatch(world)
    original = receiver.requests[-1]
    sent = _cloudevents(original)[-1]
    content_type = original["headers"]["content-type"]
    current = _read(world, created)
    ok(world.api.patch(f"{PATH}/{created['id']}", {"expectedVersion": current["version"], "format": "rdm"}))

    delivery_id = original["headers"]["rdm-delivery-id"]
    resent = ok(_resend(world, created, delivery_id, sent["id"]), 201)
    request = receiver.requests[-1]
    assert request["headers"]["content-type"] == content_type
    assert request["body"] == (sent if size == 1 else [sent])
    assert request["headers"]["rdm-delivery-id"] == resent["deliveryId"] != delivery_id
    assert request["headers"]["rdm-redelivery"] == "manual"
    assert _signed(created["signingSecret"], request)
    assert (resent["status"], resent["resendOf"]) == ("succeeded", delivery_id)
    assert [event["eventId"] for event in resent["events"]] == [sent["id"]]
    assert resent["requestBody"] == request["body"]
