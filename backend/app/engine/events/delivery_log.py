"""The webhook delivery log (Base 0.9 U5a, C-D116–C-D119).

The dispatcher writes it as it works: when a batch is built, a request per body (one for a
per-change batch, one per notice for a coalesced one) with the events it carries; before each
send, the attempt's start and the body as sent; after it, the answer and the request's status.
An edit or resume that drops a batch marks its unfinished requests ``dropped``; a batch given up
after a day of failures, ``failed``. Entries older than the retention are deleted by one set
statement, except those of a batch still pending. Each step is a fixed number of statements
however many events a request carries.
"""

import json
from collections.abc import Sequence
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import delete, exists, insert, select, update
from sqlalchemy.orm import Session

from ...common.pagination import Page, PageRequest, integer_key, paginate_statement
from ...errors import api_error
from ...models.database import (
    ConsumerSubscription,
    ConsumerWebhookAttempt,
    ConsumerWebhookRequest,
    ConsumerWebhookRequestEvent,
)
from .webhook_client import Answer

UNFINISHED = ("queued", "sending", "retrying")


def _rows(body: dict[str, Any]) -> list[dict[str, Any]]:
    """The deliveries rows a body makes: its events, or the notice itself."""
    if "events" not in body:
        return [
            {
                "ordinal": 0,
                "event_id": None,
                "event_key": body["event"],
                "change": None,
                "object_type": None,
                "object_id": None,
                "position": body["toPosition"],
            }
        ]
    return [
        {
            "ordinal": index,
            "event_id": event["eventId"],
            "event_key": event["event"],
            "change": event.get("change"),
            "object_type": event.get("objectType"),
            "object_id": event.get("id"),
            "position": event["position"],
        }
        for index, event in enumerate(body["events"])
    ]


def open_batch(
    session: Session,
    subscription_sequence_id: int,
    batch_id: str,
    bodies: Sequence[tuple[str, dict[str, Any]]],
    now: datetime,
) -> None:
    """Log the batch's requests that are not logged yet (a retried batch's are), queued, with the
    events each carries."""
    request = ConsumerWebhookRequest
    known = set(
        session.scalars(
            select(request.delivery_id).where(
                request.subscription_sequence_id == subscription_sequence_id, request.batch_id == batch_id
            )
        )
    )
    missing = [(delivery_id, body) for delivery_id, body in bodies if delivery_id not in known]
    if not missing:
        return
    created = session.execute(
        insert(request)
        .values(
            [
                {
                    "subscription_sequence_id": subscription_sequence_id,
                    "delivery_id": delivery_id,
                    "batch_id": batch_id,
                    "kind": "events" if "events" in body else "notice",
                    "status": "queued",
                    "attempts": 0,
                    "created_at": now,
                }
                for delivery_id, body in missing
            ]
        )
        .returning(request.sequence_id, request.delivery_id)
    ).all()
    sequence_of = {row.delivery_id: row.sequence_id for row in created}
    events = [
        {"request_sequence_id": sequence_of[delivery_id], **row}
        for delivery_id, body in missing
        for row in _rows(body)
    ]
    session.execute(insert(ConsumerWebhookRequestEvent), events)


def start_attempt(
    session: Session, subscription_sequence_id: int, delivery_id: str, data: bytes, at: datetime
) -> tuple[int, int] | None:
    """Mark the request as being sent with ``data`` and log the attempt's start; the request's
    sequence ID and the attempt's number, or ``None`` when the request is not logged."""
    request = ConsumerWebhookRequest
    row = session.execute(
        update(request)
        .where(request.subscription_sequence_id == subscription_sequence_id, request.delivery_id == delivery_id)
        .values(
            status="sending",
            attempts=request.attempts + 1,
            request_body=data.decode("utf-8"),
            request_bytes=len(data),
            sent_at=at,
        )
        .returning(request.sequence_id, request.attempts)
        .execution_options(synchronize_session=False)
    ).one_or_none()
    if row is None:
        return None
    session.execute(
        insert(ConsumerWebhookAttempt).values(request_sequence_id=row.sequence_id, number=row.attempts, started_at=at)
    )
    return row.sequence_id, row.attempts


def finish_attempt(session: Session, started: tuple[int, int], answer: Answer, completed: datetime, duration_ms: int) -> None:
    """Log the attempt's answer, and the request's status: ``succeeded``, or ``retrying`` unless an
    edit dropped it meanwhile. A request the receiver acknowledged is ``succeeded`` even then."""
    sequence_id, number = started
    error = answer.error
    session.execute(
        update(ConsumerWebhookAttempt)
        .where(ConsumerWebhookAttempt.request_sequence_id == sequence_id, ConsumerWebhookAttempt.number == number)
        .values(
            completed_at=completed,
            duration_ms=duration_ms,
            response_status=answer.status,
            error_kind=error["kind"] if error else None,
            error_message=error["message"] if error else None,
            response_body=answer.body,
        )
        .execution_options(synchronize_session=False)
    )
    request = ConsumerWebhookRequest
    statement = update(request).where(request.sequence_id == sequence_id)
    if not answer.ok:
        statement = statement.where(request.status == "sending")
    session.execute(
        statement.values(status="succeeded" if answer.ok else "retrying", last_status=answer.status).execution_options(
            synchronize_session=False
        )
    )


def settle_batch(session: Session, subscription_sequence_id: int, batch_id: str | None, status: str) -> None:
    """Mark the batch's unfinished requests ``dropped`` (an edit, a resume, events no longer taken)
    or ``failed`` (given up)."""
    if batch_id is None:
        return
    request = ConsumerWebhookRequest
    session.execute(
        update(request)
        .where(
            request.subscription_sequence_id == subscription_sequence_id,
            request.batch_id == batch_id,
            request.status.in_(UNFINISHED),
        )
        .values(status=status)
        .execution_options(synchronize_session=False)
    )


def prune(session: Session, now: datetime, retention_days: int) -> int:
    """Delete requests older than the retention, with their events and attempts (``CASCADE``),
    except those of a batch still pending; how many."""
    request, subscription = ConsumerWebhookRequest, ConsumerSubscription
    pending = exists().where(
        subscription.sequence_id == request.subscription_sequence_id,
        subscription.pending_delivery_id == request.batch_id,
    )
    result = session.execute(
        delete(request)
        .where(request.created_at < now - timedelta(days=retention_days), ~pending)
        .execution_options(synchronize_session=False)
    )
    return result.rowcount or 0


# --- reads ----------------------------------------------------------------------------------------

_ROW_KEYS = (
    integer_key("requestSequence", ConsumerWebhookRequest.sequence_id, "request_sequence", descending=True),
    integer_key("ordinal", ConsumerWebhookRequestEvent.ordinal, "ordinal", descending=True),
)


def _next_attempt(subscription: ConsumerSubscription, batch_id: str, status: str) -> datetime | None:
    if status != "retrying" or subscription.status != "active" or subscription.pending_delivery_id != batch_id:
        return None
    return subscription.next_attempt_at


def delivery_rows(
    session: Session, subscription: ConsumerSubscription, status: str | None, page: PageRequest, page_size: int
) -> tuple[Page[Any], ConsumerSubscription]:
    """The subscription's deliveries rows, newest first: its requests' events and notices."""
    request, event = ConsumerWebhookRequest, ConsumerWebhookRequestEvent
    statement = (
        select(
            request.sequence_id.label("request_sequence"),
            event.ordinal.label("ordinal"),
            request.delivery_id,
            request.batch_id,
            request.status,
            request.attempts,
            request.last_status,
            request.sent_at,
            event.event_id,
            event.event_key,
            event.change,
            event.object_type,
            event.object_id,
            event.position,
        )
        .join(event, event.request_sequence_id == request.sequence_id)
        .where(request.subscription_sequence_id == subscription.sequence_id)
    )
    if status is not None:
        statement = statement.where(request.status == status)
    found = paginate_statement(
        session,
        statement,
        keys=_ROW_KEYS,
        scope=f"consumer-deliveries:{subscription.public_id}",
        filters={"status": status},
        page=page,
        page_size=page_size,
        message="Delivery list cursor is invalid",
        rows=True,
    )
    return found, subscription


def delivery_detail(session: Session, subscription: ConsumerSubscription, delivery_id: str) -> dict[str, Any]:
    """A request with its events and attempts; ``404 DELIVERY_NOT_FOUND`` when not logged."""
    request = session.scalar(
        select(ConsumerWebhookRequest).where(
            ConsumerWebhookRequest.subscription_sequence_id == subscription.sequence_id,
            ConsumerWebhookRequest.delivery_id == delivery_id,
        )
    )
    if request is None:
        raise api_error(
            404, "DELIVERY_NOT_FOUND", f"Delivery '{delivery_id}' of subscription '{subscription.public_id}' not found"
        )
    events = session.scalars(
        select(ConsumerWebhookRequestEvent)
        .where(ConsumerWebhookRequestEvent.request_sequence_id == request.sequence_id)
        .order_by(ConsumerWebhookRequestEvent.ordinal)
    ).all()
    attempts = session.scalars(
        select(ConsumerWebhookAttempt)
        .where(ConsumerWebhookAttempt.request_sequence_id == request.sequence_id)
        .order_by(ConsumerWebhookAttempt.number)
    ).all()
    return {
        "request": request,
        "body": json.loads(request.request_body) if request.request_body is not None else None,
        "events": events,
        "attempts": attempts,
        "next_attempt_at": _next_attempt(subscription, request.batch_id, request.status),
    }


def row_next_attempt(subscription: ConsumerSubscription, row: Any) -> datetime | None:
    return _next_attempt(subscription, row.batch_id, row.status)

