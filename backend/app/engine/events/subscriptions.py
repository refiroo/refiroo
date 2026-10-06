"""Webhook subscriptions: create, edit, suspend, resume, delete and list (Base 0.9 C11).

A subscription names a consumer API, a workspace, some of the API's events, filters in the
definition's own parameters, a URL, a delivery mode and a payload (CONSUMER_API "Subscriptions").
Create, edit and resume run the same checks, against the active release, the deployment's host
allowlist and the workspace: the definition serves what it names (``subscription_rules``), each
filter value matches a record now (C-D100), the URL passes the allowlist (C-D101) and the workspace
is active. A subscription records the contract version it was accepted under (C-D99).

A new subscription starts after the workspace's feed head, or after an earlier position still kept
(C-D97). Its signing key is 32 random bytes, answered once and stored sealed with the deployment key
(C-D96, C-D12). A subscription is ``active`` or ``suspended`` with a reason (C-D98); a resume checks
again and, after events it had not acknowledged expired, is refused unless it resets to the feed's
head (C-D93 revised, C-D110). Every change claims the version read. The dispatcher (C12) delivers;
an edit drops the batch it is retrying and a resume clears its failures, so the next attempt is at
once, from the first unacknowledged event (C-D108, C-D111).
"""

import base64
import secrets
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from ...common.pagination import Page, PageRequest, integer_key, paginate_statement
from ...common.sealing import seal
from ...errors import ApiError, api_error
from ...models.commands import (
    ConsumerSubscriptionCreate,
    ConsumerSubscriptionUpdate,
)
from ...models.database import ConsumerSubscription, Workspace
from ...models.schema import EngineModel
from ..model.registry import resolve_model_snapshot
from ..reads.consumer_events import AFTER_POSITION, EventWindow, check_after, event_window
from ..reads.consumer_parameters import unmatched_values
from ..reads.consumer_source import ConsumerSource
from ..workspaces.catalogue import load_workspace_runtime_state
from .subscription_rules import (
    ACTIVE,
    SUSPENDED,
    SUSPENDED_BY_USER,
    Asked,
    definition_findings,
    definition_of,
    finding_body,
)
from .webhook_urls import check_webhook_url

SECRET_PREFIX = "rdmwh_"
DEFAULT_DEBOUNCE_SECONDS = 60
_KEYS = (integer_key("sequenceId", ConsumerSubscription.sequence_id, "sequence_id", descending=True),)


@dataclass(frozen=True)
class SubscriptionSettings:
    """What the deployment configures: the hosts URLs may name, the key signing keys are sealed
    with, and the events' retention, which decides what has expired."""

    allowed_hosts: tuple[str, ...]
    encryption_key: bytes
    retention_days: int


def listed(filters: Mapping[str, str | Sequence[str]]) -> dict[str, list[str]]:
    """Filters with each value as a list, as they are stored and answered."""
    return {
        name: [value] if isinstance(value, str) else list(dict.fromkeys(value))
        for name, value in filters.items()
    }


def _workspace(session: Session, key: str | None) -> Workspace | ApiError:
    effective = key if key is not None else load_workspace_runtime_state(session).default_workspace_key
    workspace = session.scalar(select(Workspace).where(Workspace.key == effective))
    if workspace is None or workspace.status != "active":
        return api_error(
            404, "WORKSPACE_NOT_FOUND", f"Workspace '{effective}' not found", {"pointer": "/workspaceKey"}
        )
    return workspace


def _findings(
    session: Session,
    model: EngineModel,
    asked: Asked,
    workspace_key: str | None,
    url: str,
    settings: SubscriptionSettings,
) -> tuple[list[ApiError], Workspace | None]:
    """Every check's refusal, in the order a create reports them, and the workspace when it is
    served."""
    findings = definition_findings(model, asked)
    resolved = _workspace(session, workspace_key)
    workspace = resolved if isinstance(resolved, Workspace) else None
    if workspace is None:
        assert isinstance(resolved, ApiError)
        findings.append(resolved)
    definition = definition_of(model, asked.consumer_api)
    named = definition is not None and not any(f.code in {"UNKNOWN_PARAMETER", "PARAMETER_NOT_SUPPORTED"} for f in findings)
    if definition is not None and workspace is not None and named:
        source = ConsumerSource(workspace.key)
        for name, values in asked.filters.items():
            refusal = unmatched_values(session, model, definition, source, name, values, f"/filters/{name}")
            if refusal is not None:
                findings.append(refusal)
    url_refusal = check_webhook_url(url, settings.allowed_hosts)
    if url_refusal is not None:
        findings.append(url_refusal)
    return findings, workspace


def secret_text(key: bytes) -> str:
    """The signing key as ``signingSecret`` shows it, and as a receiver uses it to verify."""
    return SECRET_PREFIX + base64.urlsafe_b64encode(key).decode().rstrip("=")


def _secret() -> tuple[str, bytes]:
    key = secrets.token_bytes(32)
    return secret_text(key), key


def clear_delivery(subscription: ConsumerSubscription) -> None:
    """Forget the batch being retried and its failures: the next attempt is at once, and builds a
    new batch, with a new delivery ID, after the acknowledged position."""
    subscription.pending_delivery_id = None
    subscription.pending_position = None
    subscription.pending_ordinal = None
    subscription.attempts = 0
    subscription.failing_since = None
    subscription.next_attempt_at = None
    subscription.last_error = None


def create_subscription(
    session: Session, payload: ConsumerSubscriptionCreate, settings: SubscriptionSettings
) -> tuple[ConsumerSubscription, str]:
    """The new subscription and its signing key, which no later read returns."""
    model = resolve_model_snapshot(session).model
    asked = Asked(payload.consumerApi, list(dict.fromkeys(payload.events)), listed(payload.filters))
    findings, workspace = _findings(session, model, asked, payload.workspaceKey, payload.url, settings)
    if findings:
        raise findings[0]
    assert workspace is not None
    definition = definition_of(model, asked.consumer_api)
    assert definition is not None
    window = event_window(session, workspace.key, settings.retention_days)
    start = window.feed_head
    if payload.startAfter is not None:
        check_after(window, payload.startAfter, "/startAfter")
        start = payload.startAfter
    public_id = str(uuid4())
    secret, key = _secret()
    now = datetime.now(UTC)
    subscription = ConsumerSubscription(
        public_id=public_id,
        consumer_api=definition.key,
        contract_version=definition.contractVersion,
        workspace_key=workspace.key,
        event_keys=list(asked.event_keys),
        filters=dict(asked.filters),
        url=payload.url,
        mode=payload.mode,
        debounce_seconds=(payload.debounceSeconds or DEFAULT_DEBOUNCE_SECONDS) if payload.mode == "coalesced" else None,
        payload=payload.payload,
        status=ACTIVE,
        acknowledged_position=start,
        acknowledged_ordinal=AFTER_POSITION,
        signing_key=seal(settings.encryption_key, key, public_id.encode()),
        signing_key_created_at=now,
        version=1,
        created_at=now,
        updated_at=now,
    )
    session.add(subscription)
    session.commit()
    return subscription, secret


def load_subscription(session: Session, public_id: str, *, for_update: bool = False) -> ConsumerSubscription:
    statement = select(ConsumerSubscription).where(ConsumerSubscription.public_id == public_id)
    subscription = session.scalar(statement.with_for_update() if for_update else statement)
    if subscription is None:
        raise api_error(404, "SUBSCRIPTION_NOT_FOUND", f"Subscription '{public_id}' not found")
    return subscription


def _claimed(session: Session, public_id: str, expected_version: int) -> ConsumerSubscription:
    subscription = load_subscription(session, public_id, for_update=True)
    if subscription.version != expected_version:
        raise api_error(
            409,
            "VERSION_CONFLICT",
            "Subscription version has changed",
            {"currentVersion": subscription.version},
        )
    return subscription


def _changing[T](session: Session, change: Callable[[], T]) -> T:
    """Run ``change`` and commit; a refusal rolls back, releasing the row lock and changing nothing."""
    try:
        result = change()
    except ApiError:
        session.rollback()
        raise
    session.commit()
    return result


def _touch(subscription: ConsumerSubscription) -> None:
    subscription.version += 1
    subscription.updated_at = datetime.now(UTC)


def update_subscription(
    session: Session, public_id: str, payload: ConsumerSubscriptionUpdate, settings: SubscriptionSettings
) -> ConsumerSubscription:
    """Edit what the subscription names, checked as a create; a suspended one stays suspended."""

    def change() -> ConsumerSubscription:
        subscription = _claimed(session, public_id, payload.expectedVersion)
        model = resolve_model_snapshot(session).model
        events = list(dict.fromkeys(payload.events)) if payload.events is not None else subscription.event_keys
        filters = listed(payload.filters) if payload.filters is not None else subscription.filters
        url = payload.url if payload.url is not None else subscription.url
        mode = payload.mode or subscription.mode
        if payload.debounceSeconds is not None and mode != "coalesced":
            raise api_error(
                422,
                "REQUEST_VALIDATION_ERROR",
                "Request validation failed",
                [{"loc": ["body", "debounceSeconds"], "msg": "debounceSeconds applies to mode 'coalesced' only"}],
            )
        asked = Asked(subscription.consumer_api, events, filters)
        findings, _workspace_found = _findings(
            session, model, asked, subscription.workspace_key, url, settings
        )
        # The workspace is not edited; a retired one is the suspension's business, not the edit's.
        findings = [f for f in findings if f.code != "WORKSPACE_NOT_FOUND"]
        if findings:
            raise findings[0]
        subscription.event_keys = events
        subscription.filters = filters
        subscription.url = url
        subscription.mode = mode
        if mode == "coalesced":
            subscription.debounce_seconds = (
                payload.debounceSeconds or subscription.debounce_seconds or DEFAULT_DEBOUNCE_SECONDS
            )
        else:
            subscription.debounce_seconds = None
        if payload.payload is not None:
            subscription.payload = payload.payload
        clear_delivery(subscription)
        _touch(subscription)
        return subscription

    return _changing(session, change)


def suspend_subscription(session: Session, public_id: str, expected_version: int) -> ConsumerSubscription:
    def change() -> ConsumerSubscription:
        subscription = _claimed(session, public_id, expected_version)
        if subscription.status == SUSPENDED:
            raise api_error(
                409,
                "SUBSCRIPTION_ALREADY_SUSPENDED",
                f"Subscription '{public_id}' is already suspended ({subscription.suspension_reason})",
                {"reason": subscription.suspension_reason},
            )
        subscription.status = SUSPENDED
        subscription.suspension_reason = SUSPENDED_BY_USER
        subscription.suspension_message = "Suspended through the API; resume it to continue"
        subscription.suspension_details = None
        subscription.suspended_at = datetime.now(UTC)
        _touch(subscription)
        return subscription

    return _changing(session, change)


def resume_subscription(
    session: Session,
    public_id: str,
    expected_version: int,
    reset: bool,
    settings: SubscriptionSettings,
) -> ConsumerSubscription:
    """Resume after any reason: the subscription is checked as a create (``409
    SUBSCRIPTION_NEEDS_EDIT`` listing what to fix). It continues from the first unacknowledged event,
    refused when events since then expired (C-D93); with ``reset`` it starts after the workspace's
    feed head instead, as a new subscription does (C-D110). The contract version served becomes the
    one accepted."""

    def change() -> ConsumerSubscription:
        subscription = _claimed(session, public_id, expected_version)
        if subscription.status != SUSPENDED:
            raise api_error(
                409, "SUBSCRIPTION_NOT_SUSPENDED", f"Subscription '{public_id}' is not suspended"
            )
        model = resolve_model_snapshot(session).model
        asked = Asked(subscription.consumer_api, subscription.event_keys, subscription.filters)
        findings, _workspace_found = _findings(
            session, model, asked, subscription.workspace_key, subscription.url, settings
        )
        if findings:
            raise api_error(
                409,
                "SUBSCRIPTION_NEEDS_EDIT",
                "The subscription cannot be served as it is: edit what the details list, then resume",
                {"errors": [finding_body(error) for error in findings]},
            )
        window = event_window(session, subscription.workspace_key, settings.retention_days)
        if reset:
            subscription.acknowledged_position = window.feed_head
            subscription.acknowledged_ordinal = AFTER_POSITION
        elif subscription.acknowledged_position < window.earliest - 1:
            raise api_error(
                409,
                "EVENTS_EXPIRED",
                f"Events from position {subscription.acknowledged_position + 1} to "
                f"{window.earliest - 1} expired before they were delivered. Resume with reset to "
                "start after the feed's head, and re-sync from the publication named in the details",
                expired_details(subscription.acknowledged_position, window),
            )
        definition = definition_of(model, subscription.consumer_api)
        assert definition is not None
        subscription.contract_version = definition.contractVersion
        subscription.status = ACTIVE
        subscription.suspension_reason = None
        subscription.suspension_message = None
        subscription.suspension_details = None
        subscription.suspended_at = None
        clear_delivery(subscription)
        _touch(subscription)
        return subscription

    return _changing(session, change)


def expired_details(acknowledged: int, window: EventWindow) -> dict[str, Any]:
    """The events a subscription lost, and the publication its receiver re-syncs from (C-D93)."""
    return {
        "fromPosition": acknowledged + 1,
        "toPosition": window.earliest - 1,
        "publication": window.publication,
    }


def delete_subscription(session: Session, public_id: str, expected_version: int) -> None:
    def change() -> None:
        subscription = _claimed(session, public_id, expected_version)
        session.execute(
            delete(ConsumerSubscription).where(ConsumerSubscription.sequence_id == subscription.sequence_id)
        )

    _changing(session, change)


def subscription_page(
    session: Session,
    *,
    consumer_api: str | None,
    workspace_key: str | None,
    status: str | None,
    page: PageRequest,
    page_size: int,
) -> Page[ConsumerSubscription]:
    """Subscriptions, newest first."""
    statement = select(ConsumerSubscription)
    if consumer_api is not None:
        statement = statement.where(ConsumerSubscription.consumer_api == consumer_api)
    if workspace_key is not None:
        statement = statement.where(ConsumerSubscription.workspace_key == workspace_key)
    if status is not None:
        statement = statement.where(ConsumerSubscription.status == status)
    return paginate_statement(
        session,
        statement,
        keys=_KEYS,
        scope="consumer-subscriptions",
        filters={"consumerApi": consumer_api, "workspaceKey": workspace_key, "status": status},
        page=page,
        page_size=page_size,
        message="Subscription list cursor is invalid",
    )
