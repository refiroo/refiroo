"""What a webhook delivery is made of (Base 0.9 C12, CONSUMER_API "Delivery").

The limits are constants, reported in ``GET /capabilities``: a per-change request holds at most
``MAX_EVENTS`` events and ``MAX_BYTES`` of body, an event alone over the limit going alone, since
skipping it would break the order (C-D104); a receiver answers within ``TIMEOUT_SECONDS``. A failed
batch is retried after ``RETRY_WAITS`` (then hourly), each ±20 %, until ``RETRY_HOURS`` after its
first failure (C-D103). A coalesced subscription is told once its newest matching event is
``debounceSeconds`` old, or its oldest ``COALESCE_MAX_SECONDS`` old (C-D105).

A request is signed with the subscription's ``signingSecret`` as the HMAC-SHA256 key, over
``"{RDM-Timestamp}.{body}"``, and sent as ``RDM-Signature: sha256=<hex>`` (C-D12). The body is the
compact JSON's UTF-8 bytes, with values written as the API writes them.
"""

import hashlib
import hmac
import json
import random
from collections.abc import Callable, Mapping, Sequence
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from typing import Any
from uuid import UUID

MAX_EVENTS = 100
MAX_BYTES = 1024 * 1024
TIMEOUT_SECONDS = 10.0
RETRY_HOURS = 24
RETRY_WAITS = (10, 30, 60, 120, 300, 600, 1800)
LATER_WAIT = 3600
JITTER = 0.2
COALESCE_MAX_SECONDS = 600
USER_AGENT = "rdm-engine"


def retry_wait(attempts: int, draw: Callable[[], float] = random.random) -> timedelta:
    """The wait after the ``attempts``-th failed attempt of a batch, with its jitter."""
    base = RETRY_WAITS[attempts - 1] if attempts <= len(RETRY_WAITS) else LATER_WAIT
    return timedelta(seconds=base * (1 + JITTER * (2 * draw() - 1)))


def gives_up(failing_since: datetime, now: datetime) -> bool:
    """Whether a batch failing since ``failing_since`` has run out of retries at ``now``."""
    return now - failing_since >= timedelta(hours=RETRY_HOURS)


def coalesce_due(oldest: datetime, newest: datetime, debounce_seconds: int, now: datetime) -> bool:
    """Whether a coalesced subscription is told at ``now`` of events from ``oldest`` to ``newest``:
    the changes paused for the debounce, or have gone on for the longest wait."""
    return now - newest >= timedelta(seconds=debounce_seconds) or now - oldest >= timedelta(
        seconds=COALESCE_MAX_SECONDS
    )


def _value(value: Any) -> Any:
    """A value JSON has no form for, written as the API writes it (FastAPI's encoders)."""
    if isinstance(value, (datetime, date, time)):
        return value.isoformat()
    if isinstance(value, Decimal):
        exponent = value.as_tuple().exponent
        return int(value) if isinstance(exponent, int) and exponent >= 0 else float(value)
    if isinstance(value, UUID):
        return str(value)
    raise TypeError(f"{type(value).__name__} is not JSON serializable")


def encode(body: Mapping[str, Any]) -> bytes:
    return json.dumps(body, default=_value, ensure_ascii=False, separators=(",", ":")).encode()


def fitting(envelope: Mapping[str, Any], events: Sequence[Mapping[str, Any]], limit: int = MAX_BYTES) -> int:
    """How many of ``events``, in order, fit in one body with ``envelope`` within ``limit`` bytes:
    at least one."""
    size = len(encode({**envelope, "events": []}))
    count = 0
    for event in events:
        size += len(encode(event)) + (1 if count else 0)
        if count and size > limit:
            break
        count += 1
    return count


def sign(secret: str, timestamp: int, body: bytes) -> str:
    digest = hmac.new(secret.encode(), str(timestamp).encode() + b"." + body, hashlib.sha256)
    return f"sha256={digest.hexdigest()}"


def headers(delivery_id: str, secret: str, timestamp: int, body: bytes) -> dict[str, str]:
    return {
        "Content-Type": "application/json",
        "User-Agent": USER_AGENT,
        "RDM-Delivery-Id": delivery_id,
        "RDM-Timestamp": str(timestamp),
        "RDM-Signature": sign(secret, timestamp, body),
    }
