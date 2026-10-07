"""What a webhook delivery is made of (Base 0.9 C12, C-D103, C-D104, C-D12; C17, C-D120–C-D126)."""

import hashlib
import hmac
import json
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from app.engine.events import delivery

NOW = datetime(2026, 10, 6, 12, 0, tzinfo=UTC)


@pytest.mark.parametrize(
    ("attempts", "seconds"),
    [(1, 10), (2, 30), (3, 60), (4, 120), (5, 300), (6, 600), (7, 1800), (8, 3600), (30, 3600)],
)
def test_the_wait_after_each_failed_attempt_follows_the_schedule(attempts, seconds):
    assert delivery.retry_wait(attempts, lambda: 0.5) == timedelta(seconds=seconds)
    assert delivery.retry_wait(attempts, lambda: 0.0) == timedelta(seconds=seconds * 0.8)
    assert delivery.retry_wait(attempts, lambda: 1.0) == timedelta(seconds=seconds * 1.2)


def test_retries_give_up_24_hours_after_the_first_failure():
    assert not delivery.gives_up(NOW, NOW + timedelta(hours=24) - timedelta(seconds=1))
    assert delivery.gives_up(NOW, NOW + timedelta(hours=24))


def test_values_are_written_as_the_api_writes_them():
    body = {"at": NOW, "on": NOW.date(), "whole": Decimal(3), "part": Decimal("1.50"), "text": "ü"}
    assert json.loads(delivery.encode(body)) == {
        "at": "2026-10-06T12:00:00+00:00",
        "on": "2026-10-06",
        "whole": 3,
        "part": 1.5,
        "text": "ü",
    }
    assert b" " not in delivery.encode({"a": [1, 2]})


SOURCE = "/api/consumer/ledger/v1/events?workspace=main"


def _event(size: int = 1, number: int = 1) -> dict:
    return {
        "eventId": f"00000000-0000-0000-0000-{number:012d}",
        "position": number,
        "occurredAt": NOW,
        "event": "ledger-changed",
        "change": "updated",
        "objectType": "Ledger",
        "id": "11111111-1111-1111-1111-111111111111",
        "object": {"text": "x" * size},
    }


def _written(format: str, batched: bool) -> delivery.RequestFormat:
    envelope = {"subscriptionId": "s", "consumerApi": "ledger", "contractVersion": 1, "workspaceKey": "main"}
    return delivery.RequestFormat(format=format, batched=batched, envelope=envelope, source=SOURCE)


def test_the_events_source_is_the_definitions_events_path_in_the_workspace():
    assert delivery.events_source("ledger", 2, "main") == "/api/consumer/ledger/v2/events?workspace=main"
    assert delivery.events_source("ledger", 1, "a b&c") == "/api/consumer/ledger/v1/events?workspace=a%20b%26c"


def test_an_rdm_json_request_is_the_envelope_with_its_events_even_one():
    for batched in (False, True):
        written = _written("rdm", batched)
        assert written.content_type == "application/json"
        body = written.body("d", [_event()])
        assert body == {
            "deliveryId": "d",
            "subscriptionId": "s",
            "consumerApi": "ledger",
            "contractVersion": 1,
            "workspaceKey": "main",
            "events": [_event()],
        }


def test_a_cloudevent_carries_the_attributes_and_the_rdm_event_as_data():
    event = _event()
    single = _written("cloudevents", batched=False)
    assert single.content_type == "application/cloudevents+json; charset=utf-8"
    assert single.body("d", [event]) == {
        "specversion": "1.0",
        "id": event["eventId"],
        "source": SOURCE,
        "type": "rdm.ledger-changed.updated",
        "subject": "Ledger/11111111-1111-1111-1111-111111111111",
        "time": NOW,
        "datacontenttype": "application/json",
        "rdmsubscription": "s",
        "data": event,
    }
    batched = _written("cloudevents", batched=True)
    assert batched.content_type == "application/cloudevents-batch+json; charset=utf-8"
    # An array also for one event: the content type follows the subscription, not the traffic.
    assert batched.body("d", [event]) == [single.body("d", [event])]
    assert [item["id"] for item in batched.body("d", [_event(number=1), _event(number=2)])] == [
        _event(number=1)["eventId"],
        _event(number=2)["eventId"],
    ]
    assert json.loads(delivery.encode(single.body("d", [event])))["time"] == "2026-10-06T12:00:00+00:00"


@pytest.mark.parametrize("format", ["rdm", "cloudevents"])
def test_a_batch_stops_at_the_byte_limit_and_an_event_over_it_goes_alone(format):
    written = _written(format, batched=True)
    events = [_event(100, number) for number in range(1, 4)]

    def size(count: int) -> int:
        return len(delivery.encode(written.body("00000000-0000-0000-0000-000000000000", events[:count])))

    assert written.fitting([_event(10)] * 5, limit=10_000) == 5
    assert written.fitting(events, limit=size(2)) == 2
    assert written.fitting(events, limit=size(2) - 1) == 1
    assert written.fitting([_event(5_000), _event(1)], limit=size(1)) == 1
    assert written.fitting(events, limit=size(3)) == 3


def test_the_signature_is_an_hmac_of_the_timestamp_and_the_body_with_the_secret():
    body = b'{"deliveryId":"d"}'
    expected = hmac.new(b"rdmwh_secret", b"1791281643." + body, hashlib.sha256).hexdigest()
    assert delivery.sign("rdmwh_secret", 1791281643, body) == f"sha256={expected}"
    headers = delivery.headers("d", "rdmwh_secret", 1791281643, body)
    assert headers["RDM-Delivery-Id"] == "d" and headers["RDM-Timestamp"] == "1791281643"
    assert headers["RDM-Signature"] == f"sha256={expected}"
    assert delivery.sign("rdmwh_other", 1791281643, body) != headers["RDM-Signature"]
    assert headers["Content-Type"] == "application/json"
    assert delivery.headers("d", "k", 1, body, delivery.CLOUDEVENT)["Content-Type"] == delivery.CLOUDEVENT
