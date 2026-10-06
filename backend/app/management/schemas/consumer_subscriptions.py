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
    "HOST_NOT_ALLOWED",
]


class SubscriptionSuspension(BaseModel):
    """Why a subscription is suspended (C-D98). ``details`` holds a ``MODEL_CHANGED``'s ``errors``
    (each finding's code, message and body pointer), a ``CONTRACT_VERSION_CHANGED``'s accepted and
    served versions, or the retired ``workspaceKey``."""

    reason: SuspensionReason
    message: str
    details: dict[str, Any] | None
    suspendedAt: datetime


class SubscriptionResponse(BaseModel):
    """A subscription. ``contractVersion`` is the version it was accepted under; delivery continues
    after ``acknowledgedThrough``. ``signingSecret`` is in the create answer only (C-D12): keep it,
    no read returns it again."""

    id: str
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
    signingKeyCreatedAt: datetime
    version: int
    createdAt: datetime
    updatedAt: datetime
    signingSecret: str | SkipJsonSchema[None] = Field(
        default=None, exclude_if=omitted_when_none, json_schema_extra=without_default
    )


class SubscriptionPage(CollectionPage[SubscriptionResponse]):
    """Subscriptions, newest first (ADR-030)."""
