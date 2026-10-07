"""Webhook subscriptions (Base 0.9 C11, CONSUMER_API "Subscriptions")."""

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field
from pydantic.json_schema import SkipJsonSchema

from .common import CollectionPage, omitted_when_none, without_default

SuspensionReason = Literal[
    "SUSPENDED_BY_USER",
    "MODEL_CHANGED",
    "CONTRACT_VERSION_CHANGED",
    "WORKSPACE_RETIRED",
    "DELIVERY_FAILED",
    "FILTER_MATCHES_NOTHING",
    "EVENTS_EXPIRED",
]


class SubscriptionSuspension(BaseModel):
    """Why a subscription is suspended (C-D98). ``details`` holds a ``MODEL_CHANGED``'s ``errors``
    (each finding's code, message and body pointer), a ``CONTRACT_VERSION_CHANGED``'s accepted and
    served versions, or the retired ``workspaceKey``; from the dispatcher (C12), a
    ``DELIVERY_FAILED``'s ``deliveryId``, ``attempts``, ``failingSince`` and ``lastError``, a
    ``FILTER_MATCHES_NOTHING``'s ``parameter``, ``values``, ``pointer`` and acknowledged
    ``position``, or an ``EVENTS_EXPIRED``'s lost range (``fromPosition``, ``toPosition``) and the
    ``publication`` to re-sync from."""

    reason: SuspensionReason
    message: str
    details: dict[str, Any] | None
    suspendedAt: datetime


class DeliveryError(BaseModel):
    """Why an attempt failed: the receiver's ``status``, a ``redirect`` (not followed), no answer
    within the ``timeout``, a ``connection`` or ``tls`` failure, or an ``address`` refused (C-D107).
    ``message`` holds at most 200 characters of the answer or the error."""

    kind: Literal["status", "redirect", "timeout", "connection", "tls", "address"]
    status: int | SkipJsonSchema[None] = Field(default=None, exclude_if=omitted_when_none, json_schema_extra=without_default)
    message: str


class PendingDelivery(BaseModel):
    """The batch being retried: its delivery ID (the same on every attempt), the position it ends
    at, its failed attempts since ``failingSince``, and the next attempt (C-D103, C-D111)."""

    deliveryId: str
    throughPosition: int
    attempts: int
    failingSince: datetime
    lastAttemptAt: datetime
    nextAttemptAt: datetime | None
    lastError: DeliveryError


class SubscriptionDelivery(BaseModel):
    """How delivery goes (C-D108): when a request was last acknowledged, and the batch being retried,
    ``null`` while none fails. Delivery changes neither ``version`` nor ``updatedAt``."""

    lastDeliveredAt: datetime | None
    pending: PendingDelivery | None


class SubscriptionResponse(BaseModel):
    """A subscription. ``contractVersion`` is the version it was accepted under; delivery continues
    after ``acknowledgedThrough``. ``signingSecret`` is in the create answer only (C-D12): keep it,
    no read returns it again."""

    id: str
    name: str
    consumerApi: str
    contractVersion: int
    workspaceKey: str
    events: list[str]
    filters: dict[str, list[str]]
    url: str
    mode: Literal["perChange", "coalesced"]
    debounceSeconds: int | None
    payload: Literal["full", "identity"]
    status: Literal["active", "suspended"]
    suspension: SubscriptionSuspension | None
    acknowledgedThrough: int
    delivery: SubscriptionDelivery
    signingKeyCreatedAt: datetime
    version: int
    createdAt: datetime
    updatedAt: datetime
    signingSecret: str | SkipJsonSchema[None] = Field(
        default=None, exclude_if=omitted_when_none, json_schema_extra=without_default
    )


class SubscriptionPage(CollectionPage[SubscriptionResponse]):
    """Subscriptions, newest first (ADR-030)."""


DeliveryStatus = Literal["queued", "sending", "retrying", "succeeded", "failed", "dropped"]


class DeliveryRow(BaseModel):
    """One event of a request, or one notice (U5a, C-D119). Rows of one request share its
    ``status``, ``attempts``, ``responseStatus`` and ``sentAt``: delivery is per request.
    ``nextAttemptAt`` is set while the request's batch waits for a retry."""

    deliveryId: str
    eventId: str | None
    event: str
    change: str | None
    objectType: str | None
    objectId: str | None
    position: int
    status: DeliveryStatus
    attempts: int
    responseStatus: int | None
    sentAt: datetime | None
    nextAttemptAt: datetime | None


class DeliveryPage(CollectionPage[DeliveryRow]):
    """A subscription's deliveries, newest first (ADR-030)."""


class DeliveryAttemptError(BaseModel):
    kind: Literal["status", "redirect", "timeout", "connection", "tls", "address"]
    message: str


class DeliveryAttempt(BaseModel):
    """One attempt: when it started and completed, how long it took, the receiver's status or the
    error, and up to 4 KiB of the answer (C-D116)."""

    number: int
    startedAt: datetime
    completedAt: datetime | None
    durationMs: int | None
    responseStatus: int | None
    error: DeliveryAttemptError | None
    responseBody: str | None


class DeliveryEvent(BaseModel):
    eventId: str | None
    event: str
    change: str | None
    objectType: str | None
    objectId: str | None
    position: int


class DeliveryDetail(BaseModel):
    """A request of a webhook batch: the events (or the notice) it carries, the body of its latest
    attempt as the receiver got it (C-D117), and every attempt."""

    deliveryId: str
    batchId: str
    kind: Literal["events", "notice"]
    status: DeliveryStatus
    events: list[DeliveryEvent]
    requestBody: Any | None
    requestBytes: int | None
    createdAt: datetime
    nextAttemptAt: datetime | None
    attempts: list[DeliveryAttempt]
