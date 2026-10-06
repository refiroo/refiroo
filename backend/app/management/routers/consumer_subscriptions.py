"""Webhook subscriptions (Base 0.9 C11, CONSUMER_API "Subscriptions").

Registered only with ``CONSUMER_SUBSCRIPTIONS_ENABLED`` (C-D10, C-D102): with the capability off
no route here is served, reads included. Nothing is delivered before C12.
"""

from typing import Literal

from fastapi import APIRouter, Query, Request

from ...engine.events.subscriptions import (
    SubscriptionSettings,
    create_subscription,
    delete_subscription,
    load_subscription,
    resume_subscription,
    subscription_page,
    suspend_subscription,
    update_subscription,
)
from ...models.commands import (
    ConsumerSubscriptionCreate,
    ConsumerSubscriptionResume,
    ConsumerSubscriptionUpdate,
    ConsumerSubscriptionVersion,
)
from ..dependencies import DbSession
from ..paging import PageQuery
from ..presenters import subscription_page as present_page
from ..presenters import subscription_response
from ..schemas.consumer_subscriptions import SubscriptionPage, SubscriptionResponse

router = APIRouter(prefix="/api/v1", tags=["consumer subscriptions"])


def _settings(request: Request) -> SubscriptionSettings:
    return request.app.state.subscription_settings


@router.post("/consumer-subscriptions", response_model=SubscriptionResponse, status_code=201)
def create(payload: ConsumerSubscriptionCreate, request: Request, session: DbSession) -> SubscriptionResponse:
    """Subscribe a URL to some of a consumer API's events in a workspace.

    The subscription is checked against the active release's definition, the deployment's host
    allowlist (``CONSUMER_WEBHOOK_ALLOWED_HOSTS``) and the workspace; each filter value must match
    a record. It starts after the workspace's feed head, or after ``startAfter``. The answer holds
    ``signingSecret``, the key every delivery is signed with: it is never returned again.
    """
    subscription, secret = create_subscription(session, payload, _settings(request))
    return subscription_response(subscription, secret)


@router.get("/consumer-subscriptions", response_model=SubscriptionPage)
def list_subscriptions(
    session: DbSession,
    paging: PageQuery,
    consumer_api: str | None = Query(default=None, alias="consumerApi"),
    workspace_key: str | None = Query(default=None, alias="workspaceKey"),
    status: Literal["active", "suspended"] | None = None,
    page_size: int = Query(default=50, ge=1, le=500, alias="pageSize"),
) -> SubscriptionPage:
    """Subscriptions, newest first."""
    return present_page(
        subscription_page(
            session,
            consumer_api=consumer_api,
            workspace_key=workspace_key,
            status=status,
            page=paging,
            page_size=page_size,
        )
    )


@router.get("/consumer-subscriptions/{subscription_id}", response_model=SubscriptionResponse)
def get_subscription(subscription_id: str, session: DbSession) -> SubscriptionResponse:
    return subscription_response(load_subscription(session, subscription_id))


@router.patch("/consumer-subscriptions/{subscription_id}", response_model=SubscriptionResponse)
def update(
    subscription_id: str, payload: ConsumerSubscriptionUpdate, request: Request, session: DbSession
) -> SubscriptionResponse:
    """Edit the events, filters, URL, mode or payload, checked as a create; a suspended
    subscription stays suspended until it is resumed."""
    return subscription_response(update_subscription(session, subscription_id, payload, _settings(request)))


@router.post("/consumer-subscriptions/{subscription_id}/suspend", response_model=SubscriptionResponse)
def suspend(subscription_id: str, payload: ConsumerSubscriptionVersion, session: DbSession) -> SubscriptionResponse:
    """Stop delivery (``SUSPENDED_BY_USER``) until the subscription is resumed."""
    return subscription_response(suspend_subscription(session, subscription_id, payload.expectedVersion))


@router.post("/consumer-subscriptions/{subscription_id}/resume", response_model=SubscriptionResponse)
def resume(
    subscription_id: str, payload: ConsumerSubscriptionResume, request: Request, session: DbSession
) -> SubscriptionResponse:
    """Continue after any suspension, from the first event not acknowledged.

    The subscription is checked as a create: ``409 SUBSCRIPTION_NEEDS_EDIT`` lists what to fix. If
    events it had not acknowledged expired meanwhile, ``409 EVENTS_EXPIRED`` names them and the
    publication to re-sync from; ``acknowledgeLoss: true`` goes on from the earliest event kept.
    Resuming accepts the contract version served.
    """
    return subscription_response(
        resume_subscription(
            session, subscription_id, payload.expectedVersion, payload.acknowledgeLoss, _settings(request)
        )
    )


@router.delete("/consumer-subscriptions/{subscription_id}", status_code=204)
def delete(
    subscription_id: str,
    session: DbSession,
    expected_version: int = Query(alias="expectedVersion", ge=1),
) -> None:
    delete_subscription(session, subscription_id, expected_version)
