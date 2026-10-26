"""What a webhook delivery is made of (Base 0.9 C12, CONSUMER_API "Delivery").

The limits are constants, reported in ``GET /capabilities``: a request holds at most the
subscription's ``maxEventsPerBatch`` events (1 to ``MAX_EVENTS_PER_BATCH``) and ``MAX_BYTES`` of
body, an event alone over the limit going alone, since skipping it would break the order (C-D104,
C-D120, C-D121); a receiver answers within ``TIMEOUT_SECONDS``. A failed batch is retried after
``RETRY_WAITS`` (then hourly), each ±20 %, until ``RETRY_HOURS`` after its first failure (C-D103).

A request is written in the subscription's format (C17): RDM JSON, an envelope whose ``events``
holds the batch, even an event alone; or CloudEvents 1.0, one structured event when the subscription
sends one event per request, otherwise a batched array, also of one event (C-D125). A CloudEvent's
attributes come from the subscription and the event alone, so a retry writes the same ones, and its
``data`` is the RDM JSON event unchanged (C-D126).

A request is signed with the subscription's ``signingSecret`` as the HMAC-SHA256 key, over
``"{RDM-Timestamp}.{body}"``, and sent as ``RDM-Signature: sha256=<hex>`` (C-D12). During the overlap
after a rotation it is signed with the new key and the previous one, and the header lists both,
``sha256=<new>,sha256=<previous>``; a receiver accepts the request when any of them verifies (0.12 K1,
D238). The body is the compact JSON's UTF-8 bytes, with values written as the API writes them.
"""

import hashlib
import hmac
import json
import random
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from typing import Any
from urllib.parse import quote
from uuid import UUID

from ...models import commands

MAX_EVENTS_PER_BATCH = commands.MAX_EVENTS_PER_BATCH
MAX_BYTES = 1024 * 1024
TIMEOUT_SECONDS = 10.0
RETRY_HOURS = 24
RETRY_WAITS = (10, 30, 60, 120, 300, 600, 1800)
LATER_WAIT = 3600
JITTER = 0.2
USER_AGENT = "rdm-engine"
RDM_JSON = "application/json"
CLOUDEVENT = "application/cloudevents+json; charset=utf-8"
CLOUDEVENTS_BATCH = "application/cloudevents-batch+json; charset=utf-8"


def retry_wait(attempts: int, draw: Callable[[], float] = random.random) -> timedelta:
    """The wait after the ``attempts``-th failed attempt of a batch, with its jitter."""
    base = RETRY_WAITS[attempts - 1] if attempts <= len(RETRY_WAITS) else LATER_WAIT
    return timedelta(seconds=base * (1 + JITTER * (2 * draw() - 1)))


def gives_up(failing_since: datetime, now: datetime) -> bool:
    """Whether a batch failing since ``failing_since`` has run out of retries at ``now``."""
    return now - failing_since >= timedelta(hours=RETRY_HOURS)


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


def encode(body: Any) -> bytes:
    return json.dumps(body, default=_value, ensure_ascii=False, separators=(",", ":")).encode()


def events_source(consumer_api: str, contract_version: int, workspace_key: str) -> str:
    """A CloudEvent's ``source``: the relative path of the definition's events read in the
    workspace, a URI-reference, since the engine knows no public base URL (C-D126)."""
    return f"/api/consumer/{consumer_api}/v{contract_version}/events?workspace={quote(workspace_key, safe='')}"


def workspace_events_source(workspace_key: str) -> str:
    """A CloudEvent's ``source`` for a workspace's change-set events (A2): the relative path of the
    workspace's publication requests."""
    return f"/api/v1/workspaces/{quote(workspace_key, safe='')}/publication-requests"


def cloudevent(event: Mapping[str, Any], source: str, subscription_id: str) -> dict[str, Any]:
    """The RDM JSON ``event`` as a structured CloudEvent (C-D126). A workspace event's type is its
    key alone (``rdm.change-set.submitted``); a consumer event's adds the change."""
    return {
        "specversion": "1.0",
        "id": event["eventId"],
        "source": source,
        "type": f"rdm.{event['event']}"
        if event.get("scope") == "workspace"
        else f"rdm.{event['event']}.{event['change']}",
        "subject": f"{event['objectType']}/{event['id']}",
        "time": event["occurredAt"],
        "datacontenttype": "application/json",
        "rdmsubscription": subscription_id,
        "data": event,
    }


@dataclass(frozen=True)
class RequestFormat:
    """How a subscription's requests are written: ``rdm`` or ``cloudevents``, one event per request
    or ``batched``; ``envelope`` is the RDM JSON body's fields but the delivery ID and the events, and
    ``source`` a CloudEvent's."""

    format: str
    batched: bool
    envelope: Mapping[str, Any]
    source: str

    @property
    def content_type(self) -> str:
        if self.format == "rdm":
            return RDM_JSON
        return CLOUDEVENTS_BATCH if self.batched else CLOUDEVENT

    def _items(self, events: Sequence[Mapping[str, Any]]) -> list[Any]:
        if self.format == "rdm":
            return list(events)
        return [cloudevent(event, self.source, self.envelope["subscriptionId"]) for event in events]

    def body(self, delivery_id: str, events: Sequence[Mapping[str, Any]]) -> Any:
        """The request's body carrying ``events``: one of them unless ``batched``."""
        items = self._items(events)
        if self.format == "rdm":
            return {"deliveryId": delivery_id, **self.envelope, "events": items}
        return items if self.batched else items[0]

    def fitting(self, events: Sequence[Mapping[str, Any]], limit: int = MAX_BYTES) -> int:
        """How many of ``events``, in order, fit in one body within ``limit`` bytes: at least one."""
        # An RDM envelope's delivery ID is a UUID: its length is the same whichever.
        size = len(encode(self.body(str(UUID(int=0)), []))) if self.format == "rdm" else 2
        count = 0
        for item in self._items(events):
            size += len(encode(item)) + (1 if count else 0)
            if count and size > limit:
                break
            count += 1
        return count


def sign(secret: str, timestamp: int, body: bytes) -> str:
    digest = hmac.new(secret.encode(), str(timestamp).encode() + b"." + body, hashlib.sha256)
    return f"sha256={digest.hexdigest()}"


def headers(
    delivery_id: str, secrets: Sequence[str], timestamp: int, body: bytes, content_type: str = RDM_JSON
) -> dict[str, str]:
    """A request's headers, signed with each of ``secrets``: the current key first, then the previous
    one while it still signs."""
    return {
        "Content-Type": content_type,
        "User-Agent": USER_AGENT,
        "RDM-Delivery-Id": delivery_id,
        "RDM-Timestamp": str(timestamp),
        "RDM-Signature": ",".join(sign(secret, timestamp, body) for secret in secrets),
    }
