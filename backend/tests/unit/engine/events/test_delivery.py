"""What a webhook delivery is made of (Base 0.9 C12, C-D103–C-D105, C-D12)."""

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


@pytest.mark.parametrize(
    ("oldest", "newest", "due"),
    [
        (-30, -30, False),
        (-60, -59, False),
        (-60, -60, True),
        (-599, -1, False),
        (-600, -1, True),
    ],
)
def test_a_coalesced_notice_is_due_after_a_pause_or_ten_minutes(oldest, newest, due):
    assert delivery.coalesce_due(NOW + timedelta(seconds=oldest), NOW + timedelta(seconds=newest), 60, NOW) is due


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


def _event(size: int) -> dict:
    return {"eventId": "e", "object": {"text": "x" * size}}


def test_a_batch_stops_at_the_byte_limit_and_an_event_over_it_goes_alone():
    envelope = {"deliveryId": "d", "subscriptionId": "s"}
    small = [_event(10)] * 5
    assert delivery.fitting(envelope, small, limit=10_000) == 5
    one = len(delivery.encode({**envelope, "events": [_event(100)]}))
    two = len(delivery.encode({**envelope, "events": [_event(100)] * 2}))
    assert delivery.fitting(envelope, [_event(100)] * 3, limit=two) == 2
    assert delivery.fitting(envelope, [_event(100)] * 3, limit=two - 1) == 1
    assert delivery.fitting(envelope, [_event(5_000), _event(1)], limit=one) == 1
    assert len(delivery.encode({**envelope, "events": [_event(100)] * 2})) == two


def test_the_signature_is_an_hmac_of_the_timestamp_and_the_body_with_the_secret():
    body = b'{"deliveryId":"d"}'
    expected = hmac.new(b"rdmwh_secret", b"1791281643." + body, hashlib.sha256).hexdigest()
    assert delivery.sign("rdmwh_secret", 1791281643, body) == f"sha256={expected}"
    headers = delivery.headers("d", "rdmwh_secret", 1791281643, body)
    assert headers["RDM-Delivery-Id"] == "d" and headers["RDM-Timestamp"] == "1791281643"
    assert headers["RDM-Signature"] == f"sha256={expected}"
    assert delivery.sign("rdmwh_other", 1791281643, body) != headers["RDM-Signature"]
