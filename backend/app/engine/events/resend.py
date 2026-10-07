"""Resending a delivered webhook event by hand (Base 0.9 U5a revision, C-D129–C-D131).

The event is taken from the stored body of the request it was sent in, exactly as it was sent,
and sent alone in a new request: a new delivery ID, the same ``eventId``, a fresh signature and
``RDM-Redelivery: manual``. A notice is resent as it was. The request is sent during the call, one
attempt and no retry, on any subscription, suspended ones included, and is logged as a request of
its own that names the one it repeats. The subscription's position and any batch being retried
are left alone.
"""

import json
import time
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import insert, select
from sqlalchemy.orm import Session

from ...common.sealing import unseal
from ...errors import api_error
from ...models.database import (
    ConsumerSubscription,
    ConsumerWebhookRequest,
    ConsumerWebhookRequestEvent,
)
from . import delivery, delivery_log
from .subscriptions import SubscriptionSettings, secret_text
from .webhook_client import post

REDELIVERY_HEADER = "RDM-Redelivery"


def _body(request: ConsumerWebhookRequest, event_id: str | None, delivery_id: str) -> dict[str, Any]:
    """The resend's body: the event alone in the stored envelope, or the notice, under a new ID."""
    if request.request_body is None:
        raise api_error(
            409,
            "DELIVERY_NOT_SENT",
            f"Delivery '{request.delivery_id}' was never sent, so there is nothing to resend",
        )
    stored = json.loads(request.request_body)
    if request.kind == "notice":
        if event_id is not None:
            raise api_error(
                404, "EVENT_NOT_IN_DELIVERY", f"Delivery '{request.delivery_id}' is a notice and carries no event"
            )
        return {**stored, "deliveryId": delivery_id}
    event = next((item for item in stored["events"] if item.get("eventId") == event_id), None)
    if event is None:
        raise api_error(
            404,
            "EVENT_NOT_IN_DELIVERY",
            f"Event '{event_id}' was not sent in delivery '{request.delivery_id}'",
            {"pointer": "/eventId"},
        )
    return {**stored, "deliveryId": delivery_id, "events": [event]}


def resend_event(
    session: Session,
    subscription: ConsumerSubscription,
    delivery_id: str,
    event_id: str | None,
    settings: SubscriptionSettings,
    timeout_seconds: float = delivery.TIMEOUT_SECONDS,
) -> dict[str, Any]:
    """Send the event (or notice) again and log it; the new request's detail, as
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
    body = _body(original, event_id, new_id)
    data = delivery.encode(body)
    now = datetime.now(UTC)
    created = session.scalar(
        insert(ConsumerWebhookRequest)
        .values(
            subscription_sequence_id=subscription.sequence_id,
            delivery_id=new_id,
            batch_id=new_id,
            kind=original.kind,
            status="queued",
            attempts=0,
            created_at=now,
            resend_of=original.delivery_id,
        )
        .returning(ConsumerWebhookRequest.sequence_id)
    )
    session.execute(
        insert(ConsumerWebhookRequestEvent),
        [{"request_sequence_id": created, **row} for row in delivery_log.rows_of(body)],
    )
    started = delivery_log.start_attempt(session, subscription.sequence_id, new_id, data, now)
    url = subscription.url
    secret = secret_text(unseal(settings.encryption_key, subscription.signing_key, subscription.public_id.encode()))
    # No transaction is open while the receiver answers.
    session.commit()

    headers = {**delivery.headers(new_id, secret, int(now.timestamp()), data), REDELIVERY_HEADER: "manual"}
    clock = time.monotonic()
    answer = post(url, data, headers, timeout=timeout_seconds)
    elapsed = timedelta(seconds=time.monotonic() - clock)
    assert started is not None
    delivery_log.finish_attempt(
        session, started, answer, now + elapsed, int(elapsed.total_seconds() * 1000), failed="failed"
    )
    session.commit()
    return delivery_log.delivery_detail(session, subscription, new_id)
