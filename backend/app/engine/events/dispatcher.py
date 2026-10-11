"""The webhook dispatcher (Base 0.9 C12, CONSUMER_API "Delivery").

Once a second it claims the active subscriptions that have something to deliver and are due, and
handles each: one batch, sent and recorded. Several processes share the work through a lease in the
subscription's row (C-D106): a claim sets ``lease_owner`` for 60 s on subscriptions no one else
holds, picked ``FOR UPDATE SKIP LOCKED``, least recently handled first. No row lock is held while a
request is in flight, so an operator's edit never waits for a receiver. On its thread, the claimed
subscriptions are sent by four senders, each one at a time, so a slow receiver delays only its own.

**One step** (``dispatch_one``). A subscription whose next events expired is suspended
``EVENTS_EXPIRED`` (C-D110); one with
a filter value no record matches any longer, ``FILTER_MATCHES_NOTHING``, before anything is sent
(C-D109). Otherwise it builds the batch, one request: the next events after the acknowledged
position, read as the pull feed reads them with the subscription's events, filters and payload, at
most its ``maxEventsPerBatch`` and 1 MiB, written in its format (C17). Events none of which it takes
move the acknowledged position without a request. The batch is stored as pending, its delivery ID
and the key it ends at, before it is sent, so a crash retries the same batch; each attempt reads its
range again and composes the objects anew (C-D111).

**Outcome.** A ``2xx`` moves the acknowledged position to the batch's end and clears the failures.
Anything else records the attempt, the error and the next attempt (C-D103); 24 hours after the
batch first failed, the subscription is suspended ``DELIVERY_FAILED``. Delivery progress changes
neither ``version`` nor ``updatedAt``; a suspension does (C-D108).

Tests drive it with ``run_until_idle(now)`` and a clock they move; the journey application does not
start the thread (``run_consumer_dispatcher``).
"""

import logging
import os
import socket
import threading
import time
import uuid
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import exists, or_, select, tuple_, update
from sqlalchemy.exc import OperationalError, SQLAlchemyError
from sqlalchemy.orm import Session

from ...common.outage import OutageLog
from ...common.sealing import unseal
from ...models.database import (
    ConsumerEvent,
    ConsumerEventCheckpoint,
    ConsumerSubscription,
    Workspace,
)
from ...models.schema import ConsumerApiDefinition, EngineModel
from ..model.registry import resolve_model_snapshot
from ..reads.consumer_events import EventsRequest, EventWindow, event_page, event_window
from ..reads.consumer_parameters import unmatched_values
from ..reads.consumer_source import ConsumerSource
from . import delivery, delivery_log
from .subscription_rules import (
    ACTIVE,
    DELIVERY_FAILED,
    EVENTS_EXPIRED,
    FILTER_MATCHES_NOTHING,
    SUSPENDED,
    definition_of,
)
from .subscriptions import SubscriptionSettings, clear_delivery, expired_details, secret_text
from .webhook_client import Answer, post

logger = logging.getLogger(__name__)

LEASE_SECONDS = 60
SENDERS = 4
POLL_SECONDS = 1.0
RETRY_SECONDS = 2.0
THREAD_NAME = "rdm-webhook-dispatcher"
# How often a dispatcher prunes the delivery log (C-D118).
PRUNE_EVERY = timedelta(hours=1)

Key = tuple[int, int]


@dataclass(frozen=True)
class _Batch:
    """What one step sends: one request, its delivery ID, the events it carries (as the pull feed
    has them), its body and content type, and where the batch ends."""

    delivery_id: str
    end: Key
    events: list[dict[str, Any]]
    body: Any
    content_type: str


class EventDispatcher:
    """Delivers webhook subscriptions in this process: ``run_until_idle`` once; ``start`` on a thread."""

    def __init__(
        self,
        session_factory: Callable[[], Session],
        settings: SubscriptionSettings,
        *,
        owner: str | None = None,
        senders: int = SENDERS,
        timeout_seconds: float = delivery.TIMEOUT_SECONDS,
    ) -> None:
        self.session_factory = session_factory
        self.settings = settings
        self.owner = owner or f"{socket.gethostname()}:{os.getpid()}:{uuid.uuid4().hex[:8]}"
        self.senders = senders
        self.timeout_seconds = timeout_seconds
        self._stopping = threading.Event()
        self._pruned_at: datetime | None = None
        self._thread: threading.Thread | None = None
        self._pool: ThreadPoolExecutor | None = None

    # --- claiming ---------------------------------------------------------------------------------

    def claim(self, now: datetime) -> list[int]:
        """Lease up to ``senders`` active subscriptions that are due and have a batch pending or
        events after their acknowledged position; their sequence IDs."""
        subscription, event, checkpoint = ConsumerSubscription, ConsumerEvent, ConsumerEventCheckpoint
        # Correlated to the subscription row by hand: inside UPDATE … IN (SELECT …) SQLAlchemy
        # would otherwise list the table again in the subquery's FROM.
        derived = (
            select(checkpoint.position)
            .where(checkpoint.workspace_key == subscription.workspace_key)
            .correlate(subscription)
            .scalar_subquery()
        )
        waiting = (
            exists()
            .where(
                event.workspace_key == subscription.workspace_key,
                event.consumer_api == subscription.consumer_api,
                tuple_(event.position, event.ordinal)
                > tuple_(subscription.acknowledged_position, subscription.acknowledged_ordinal),
                event.position <= derived,
            )
            .correlate(subscription)
        )
        due = (
            select(subscription.sequence_id)
            .where(
                subscription.status == ACTIVE,
                or_(subscription.next_attempt_at.is_(None), subscription.next_attempt_at <= now),
                or_(subscription.lease_owner.is_(None), subscription.lease_expires_at < now),
                or_(subscription.pending_position.is_not(None), waiting),
            )
            .order_by(subscription.lease_expires_at.asc().nulls_first(), subscription.sequence_id)
            .limit(self.senders)
            .with_for_update(skip_locked=True)
        )
        with self.session_factory() as session:
            claimed = list(
                session.scalars(
                    update(subscription)
                    .where(subscription.sequence_id.in_(due))
                    .values(lease_owner=self.owner, lease_expires_at=now + timedelta(seconds=LEASE_SECONDS))
                    .returning(subscription.sequence_id)
                    .execution_options(synchronize_session=False)
                )
            )
            session.commit()
        return sorted(claimed)

    def _release(self, sequence_id: int, now: datetime) -> None:
        with self.session_factory() as session:
            session.execute(
                update(ConsumerSubscription)
                .where(ConsumerSubscription.sequence_id == sequence_id, ConsumerSubscription.lease_owner == self.owner)
                .values(lease_owner=None, lease_expires_at=now)
                .execution_options(synchronize_session=False)
            )
            session.commit()

    # --- one subscription -------------------------------------------------------------------------

    def dispatch_one(self, sequence_id: int, now: datetime) -> bool:
        """Deliver the subscription's next batch; whether anything changed (a batch acknowledged,
        the position moved, a suspension)."""
        try:
            return self._step(sequence_id, now)
        except OperationalError as exc:
            # The subscription changed after the step's snapshot began (an edit, a suspension):
            # nothing was written, and the next round reads it as it is.
            if getattr(exc.orig, "sqlstate", None) == "40001":
                return False
            raise
        finally:
            self._release(sequence_id, now)

    def _step(self, sequence_id: int, now: datetime) -> bool:
        with self.session_factory() as session:
            # One snapshot, as the pull feed reads: an event's ``stateAt`` is the feed position its
            # object shows (CONSUMER_API "Events carry the data", 0.9 R-F8).
            session.connection(execution_options={"isolation_level": "REPEATABLE READ"})
            subscription = session.scalar(
                select(ConsumerSubscription).where(
                    ConsumerSubscription.sequence_id == sequence_id, ConsumerSubscription.lease_owner == self.owner
                )
            )
            if subscription is None or subscription.status != ACTIVE:
                return False
            model = resolve_model_snapshot(session).model
            definition = definition_of(model, subscription.consumer_api)
            # A release that no longer serves it suspended it when it was activated (C-D99).
            if definition is None or definition.contractVersion != subscription.contract_version:
                return False
            workspace = session.scalar(select(Workspace).where(Workspace.key == subscription.workspace_key))
            if workspace is None or workspace.status != "active":
                return False
            window = event_window(session, workspace.key, self.settings.retention_days)
            stopped = self._stopped_by(session, subscription, model, definition, workspace, window)
            if stopped is not None:
                reason, message, details = stopped
                return self._suspend(session, sequence_id, reason, message, details, now)
            batch = self._next_batch(session, subscription, model, definition, workspace)
            if not isinstance(batch, _Batch):
                session.commit()
                return batch
            subscription.pending_delivery_id = batch.delivery_id
            subscription.pending_position, subscription.pending_ordinal = batch.end
            delivery_log.open_batch(session, sequence_id, batch.delivery_id, batch.events, now)
            url = subscription.url
            secret = secret_text(
                unseal(self.settings.encryption_key, subscription.signing_key, subscription.public_id.encode())
            )
            session.commit()

        answer = self._send(sequence_id, url, secret, batch, now)
        return self._record(sequence_id, batch, answer, now)

    def _stopped_by(
        self,
        session: Session,
        subscription: ConsumerSubscription,
        model: EngineModel,
        definition: ConsumerApiDefinition,
        workspace: Workspace,
        window: EventWindow,
    ) -> tuple[str, str, dict[str, Any]] | None:
        """Why the subscription cannot go on, checked before anything is sent: its expired events,
        a filter value no record matches (C-D110, C-D109)."""
        if subscription.acknowledged_position < window.earliest - 1:
            details = expired_details(subscription.acknowledged_position, window)
            return (
                EVENTS_EXPIRED,
                (
                    f"Events from position {details['fromPosition']} to {details['toPosition']} expired "
                    "before they were delivered. Re-sync from the publication named in the details, "
                    "then resume with reset"
                ),
                details,
            )
        source = ConsumerSource(workspace.key)
        for name, values in subscription.filters.items():
            if name not in definition.parameters:
                continue
            found = unmatched_values(session, model, definition, source, name, values, f"/filters/{name}")
            if found is not None and found.code == FILTER_MATCHES_NOTHING:
                return (
                    FILTER_MATCHES_NOTHING,
                    (
                        f"Filter '{name}' value '{found.details['values'][0]}' no longer matches a "
                        "record: edit the filter, then resume; the events from the acknowledged "
                        "position are delivered then"
                    ),
                    {
                        "parameter": name,
                        "values": found.details["values"],
                        "pointer": f"/filters/{name}",
                        "position": subscription.acknowledged_position,
                    },
                )
        return None

    def _next_batch(
        self,
        session: Session,
        subscription: ConsumerSubscription,
        model: EngineModel,
        definition: ConsumerApiDefinition,
        workspace: Workspace,
    ) -> _Batch | bool:
        """The next batch of events, or, when none follows that the subscription takes, whether the
        acknowledged position moved past those it leaves out."""
        start = (subscription.acknowledged_position, subscription.acknowledged_ordinal)
        pending = _pending(subscription)
        request = EventsRequest(
            start=start,
            page_size=subscription.max_events_per_batch,
            payload=subscription.payload,
            event_keys=tuple(subscription.event_keys),
            parameters=subscription.filters,
        )
        page = event_page(
            session,
            model,
            definition,
            workspace,
            request,
            retention_days=self.settings.retention_days,
            through=pending,
        )
        if not page.items:
            return _acknowledge(subscription, page.last)
        delivery_id = subscription.pending_delivery_id or str(uuid.uuid4())
        written = request_format(subscription)
        count = written.fitting(page.items)
        end = page.last if count == len(page.items) else page.keys[count - 1]
        events = page.items[:count]
        return _Batch(delivery_id, end, events, written.body(delivery_id, events), written.content_type)

    # --- sending and recording --------------------------------------------------------------------

    def _send(self, sequence_id: int, url: str, secret: str, batch: _Batch, now: datetime) -> Answer:
        """Send the batch's request, renewing the lease first; the receiver's answer."""
        # A round's clock may lag behind a long round's sends; a test's runs ahead.
        at = max(now, datetime.now(UTC))
        data = delivery.encode(batch.body)
        started = self._renew(sequence_id, at, (batch.delivery_id, data))
        timestamp = int(at.timestamp())
        clock = time.monotonic()
        answer = post(
            url,
            data,
            delivery.headers(batch.delivery_id, secret, timestamp, data, batch.content_type),
            timeout=self.timeout_seconds,
        )
        elapsed = timedelta(seconds=time.monotonic() - clock)
        if started is not None:
            with self.session_factory() as session:
                delivery_log.finish_attempt(session, started, answer, at + elapsed, int(elapsed.total_seconds() * 1000))
                session.commit()
        return answer

    def _renew(
        self, sequence_id: int, now: datetime, sending: tuple[str, bytes] | None = None
    ) -> tuple[int, int] | None:
        """Renew the lease; with ``sending`` (a delivery ID and its body), log the attempt's start in
        the same transaction (U5a) and return it."""
        with self.session_factory() as session:
            session.execute(
                update(ConsumerSubscription)
                .where(ConsumerSubscription.sequence_id == sequence_id, ConsumerSubscription.lease_owner == self.owner)
                .values(lease_expires_at=now + timedelta(seconds=LEASE_SECONDS))
                .execution_options(synchronize_session=False)
            )
            started = (
                delivery_log.start_attempt(session, sequence_id, sending[0], sending[1], now) if sending else None
            )
            session.commit()
        return started

    def _record(self, sequence_id: int, batch: _Batch, answer: Answer, now: datetime) -> bool:
        """Record what the receiver answered, while this dispatcher still holds the lease."""
        with self.session_factory() as session:
            subscription = _locked(session, sequence_id)
            if subscription is None or subscription.lease_owner != self.owner:
                session.rollback()
                return False
            if answer.ok:
                # Acknowledged even if the subscription was edited or suspended meanwhile: the
                # receiver has the events. A resume with reset may have moved past them already.
                subscription.acknowledged_position, subscription.acknowledged_ordinal = max((subscription.acknowledged_position, subscription.acknowledged_ordinal), batch.end)
                if subscription.pending_delivery_id == batch.delivery_id:
                    clear_delivery(subscription)
                subscription.last_attempt_at = now
                subscription.last_delivered_at = now
                session.commit()
                return True
            if subscription.pending_delivery_id != batch.delivery_id:
                # An edit or a resume dropped the batch while it was in flight.
                session.rollback()
                return False
            assert answer.error is not None
            subscription.attempts += 1
            subscription.failing_since = subscription.failing_since or now
            subscription.last_attempt_at = now
            subscription.last_error = answer.error
            logger.info(
                "Webhook delivery %s of subscription %s failed (%s): attempt %s",
                batch.delivery_id,
                subscription.public_id,
                answer.error["kind"],
                subscription.attempts,
            )
            if subscription.status == ACTIVE and delivery.gives_up(subscription.failing_since, now):
                subscription.next_attempt_at = None
                delivery_log.settle_batch(session, sequence_id, batch.delivery_id, "failed")
                session.commit()
                return self._suspend(
                    session,
                    sequence_id,
                    DELIVERY_FAILED,
                    f"Delivery failed for {delivery.RETRY_HOURS} hours ({answer.error['message']}); resume it "
                    "once the receiver answers, and delivery continues from the first unacknowledged event",
                    {
                        "deliveryId": batch.delivery_id,
                        "attempts": subscription.attempts,
                        "failingSince": subscription.failing_since.isoformat(),
                        "lastError": answer.error,
                    },
                    now,
                )
            subscription.next_attempt_at = now + delivery.retry_wait(subscription.attempts)
            session.commit()
            return False

    def _suspend(
        self, session: Session, sequence_id: int, reason: str, message: str, details: dict[str, Any], now: datetime
    ) -> bool:
        """Suspend the subscription with ``reason`` if it is still active; a status change, so its
        version is raised (C-D98, C-D108)."""
        subscription = _locked(session, sequence_id)
        if subscription is None or subscription.status != ACTIVE:
            session.rollback()
            return False
        subscription.status = SUSPENDED
        subscription.suspension_reason = reason
        subscription.suspension_message = message
        subscription.suspension_details = details
        subscription.suspended_at = now
        subscription.version += 1
        subscription.updated_at = now
        session.commit()
        logger.warning("Webhook subscription %s is suspended: %s. %s", subscription.public_id, reason, message)
        return True

    # --- runs -------------------------------------------------------------------------------------

    def run_once(self, now: datetime | None = None) -> bool:
        """Handle every subscription claimed now; whether any changed."""
        at = now or datetime.now(UTC)
        self.prune(at)
        claimed = self.claim(at)
        if not claimed:
            return False
        if self._pool is not None and len(claimed) > 1:
            results = list(self._pool.map(lambda sequence_id: self.dispatch_one(sequence_id, at), claimed))
        else:
            results = [self.dispatch_one(sequence_id, at) for sequence_id in claimed]
        return any(results)

    def prune(self, now: datetime) -> None:
        """Delete delivery log entries past their retention, at most once per ``PRUNE_EVERY`` of
        this dispatcher's clock (C-D118)."""
        if self._pruned_at is not None and now - self._pruned_at < PRUNE_EVERY:
            return
        with self.session_factory() as session:
            removed = delivery_log.prune(session, now, self.settings.log_retention_days)
            session.commit()
        self._pruned_at = now
        if removed:
            logger.info("Pruned %s webhook delivery log entries", removed)

    def run_until_idle(self, now: datetime | None = None) -> int:
        """Handle subscriptions until none changes at ``now``; the rounds that changed one."""
        rounds = 0
        while self.run_once(now):
            rounds += 1
        return rounds

    # --- the thread -------------------------------------------------------------------------------

    def start(self) -> None:
        self._stopping.clear()
        self._pool = ThreadPoolExecutor(max_workers=self.senders, thread_name_prefix=f"{THREAD_NAME}-sender")
        self._thread = threading.Thread(target=self._loop, name=THREAD_NAME, daemon=True)
        self._thread.start()

    def stop(self, timeout: float = 30.0) -> None:
        """Stop after the running round and release this dispatcher's leases."""
        self._stopping.set()
        if self._thread is not None:
            self._thread.join(timeout)
            self._thread = None
        if self._pool is not None:
            self._pool.shutdown(wait=False, cancel_futures=True)
            self._pool = None
        try:
            with self.session_factory() as session:
                session.execute(
                    update(ConsumerSubscription)
                    .where(ConsumerSubscription.lease_owner == self.owner)
                    .values(lease_owner=None)
                    .execution_options(synchronize_session=False)
                )
                session.commit()
        except SQLAlchemyError:
            logger.warning("The webhook dispatcher could not release its leases; they expire instead")

    def _loop(self) -> None:
        outage = OutageLog(logger, "The webhook dispatcher", RETRY_SECONDS)
        while not self._stopping.is_set():
            wait = POLL_SECONDS
            try:
                while self.run_once() and not self._stopping.is_set():
                    pass
                outage.succeeded()
            except Exception as exc:  # noqa: BLE001 - every failure is logged by OutageLog
                outage.failed(exc)
                wait = RETRY_SECONDS
            self._stopping.wait(wait)


def _pending(subscription: ConsumerSubscription) -> Key | None:
    if subscription.pending_position is None or subscription.pending_ordinal is None:
        return None
    return (subscription.pending_position, subscription.pending_ordinal)


def _acknowledge(subscription: ConsumerSubscription, through: Key) -> bool:
    """Move past events the subscription leaves out, without a request; whether it moved."""
    moved = through > (subscription.acknowledged_position, subscription.acknowledged_ordinal)
    if moved:
        subscription.acknowledged_position, subscription.acknowledged_ordinal = through
    if _pending(subscription) is not None:
        clear_delivery(subscription)
        moved = True
    return moved


def request_format(subscription: ConsumerSubscription) -> delivery.RequestFormat:
    """How the subscription's requests are written (C17)."""
    return delivery.RequestFormat(
        format=subscription.format,
        batched=subscription.max_events_per_batch > 1,
        envelope={
            "subscriptionId": subscription.public_id,
            "consumerApi": subscription.consumer_api,
            "contractVersion": subscription.contract_version,
            "workspaceKey": subscription.workspace_key,
        },
        source=delivery.events_source(
            subscription.consumer_api, subscription.contract_version, subscription.workspace_key
        ),
    )


def _locked(session: Session, sequence_id: int) -> ConsumerSubscription | None:
    return session.scalar(
        select(ConsumerSubscription)
        .where(ConsumerSubscription.sequence_id == sequence_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )

