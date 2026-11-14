"""Resending a delivered webhook event by hand (Base 0.9 U5a revision, C-D129–C-D131).

The event is taken from the stored body of the request it was sent in, exactly as it was sent,
and sent alone in a new request: a new delivery ID, the same event ID, a fresh signature and
``RDM-Redelivery: manual``. The request keeps the format it was sent in, even when the
subscription's format was edited since (C17): an RDM JSON envelope with the one event, a structured
CloudEvent, or a CloudEvents batch of one. The request is sent during the call, one attempt and no
retry, on any subscription, suspended ones included, and is logged as a request of its own that
names the one it repeats. The subscription's position and any batch being retried are left alone.
"""

import json
import time
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from ...errors import api_error
from ...models.database import ConsumerSubscription, ConsumerWebhookRequest
from . import delivery, delivery_log
from .subscriptions import SubscriptionSettings, signing_secrets
from .webhook_client import post

REDELIVERY_HEADER = "RDM-Redelivery"


def resend_body(request: ConsumerWebhookRequest, event_id: str, delivery_id: str) -> tuple[Any, str, dict[str, Any]]:
    """The resend's body, its content type and the event as the pull feed has it. The stored body
    says its format: a JSON array is a CloudEvents batch, an object with ``specversion`` a structured
    CloudEvent, an object with ``events`` an RDM JSON envelope. Not a second copy of
    ``delivery.RequestFormat.body``: that builds a body from events; this reads one back and keeps
    the event exactly as it was sent, whatever the subscription's format is now (C-D129)."""
    if request.request_body is None:
        raise api_error(
            409,
            "DELIVERY_NOT_SENT",
            f"Delivery '{request.delivery_id}' was never sent, so there is nothing to resend",
        )
    stored = json.loads(request.request_body)
    if isinstance(stored, list):
        found = next((item for item in stored if item.get("id") == event_id), None)
        body, content_type = [found], delivery.CLOUDEVENTS_BATCH
        event = found["data"] if found else None
    elif "specversion" in stored:
        found = stored if stored.get("id") == event_id else None
        body, content_type = found, delivery.CLOUDEVENT
        event = found["data"] if found else None
    else:
        event = next((item for item in stored["events"] if item.get("eventId") == event_id), None)
        body, content_type = (
            {**stored, "deliveryId": delivery_id, "events": [event]},
            delivery.RDM_JSON,
        )
    if event is None:
        raise api_error(
            404,
            "EVENT_NOT_IN_DELIVERY",
            f"Event '{event_id}' was not sent in delivery '{request.delivery_id}'",
            {"pointer": "/eventId"},
        )
    return body, content_type, event


def resend_event(
    session: Session,
    subscription: ConsumerSubscription,
    delivery_id: str,
    event_id: str,
    settings: SubscriptionSettings,
    timeout_seconds: float = delivery.TIMEOUT_SECONDS,
) -> dict[str, Any]:
    """Send the event again and log it; the new request's detail, as
    ``delivery_log.delivery_detail`` answers it."""
    original = session.scalar(
        select(ConsumerWebhookRequest).where(
            ConsumerWebhookRequest.subscription_sequence_id == subscription.sequence_id,
            ConsumerWebhookRequest.delivery_id == delivery_id,
        )
    )
    if original is None:
        raise api_error(
            404, "DELIVERY_NOT_FOUND", f"Delivery '{delivery_id}' of subscription '{subscription.public_id}' not found"
        )
    new_id = str(uuid.uuid4())
    body, content_type, event = resend_body(original, event_id, new_id)
    data = delivery.encode(body)
    now = datetime.now(UTC)
    delivery_log.log_request(session, subscription.sequence_id, new_id, [event], now, resend_of=original.delivery_id)
    started = delivery_log.start_attempt(session, subscription.sequence_id, new_id, data, now)
    url = subscription.url
    secrets = signing_secrets(settings, subscription, now)
    # No transaction is open while the receiver answers.
    session.commit()

    headers = {
        **delivery.headers(new_id, secrets, int(now.timestamp()), data, content_type),
        REDELIVERY_HEADER: "manual",
    }
    clock = time.monotonic()
    answer = post(url, data, headers, timeout=timeout_seconds)
    elapsed = timedelta(seconds=time.monotonic() - clock)
    assert started is not None
    delivery_log.finish_attempt(
        session, started, answer, now + elapsed, int(elapsed.total_seconds() * 1000), failed="failed"
    )
    session.commit()
    return delivery_log.delivery_detail(session, subscription, new_id)
