"""Shared renderers from service dataclasses to API response models.

These live beside the routers rather than inside one of them so no router has to import another
router's internals.
"""

from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..common.pagination import Page
from ..common.time import as_utc
from ..engine.events import delivery_log
from ..engine.imports.profiles import StoredProfile
from ..engine.jobs.store import release_public_ids
from ..engine.model.compiler import ModelDiagnostic
from ..engine.model.consumer_contract import contract_diagnostics
from ..engine.model.diff import SemanticChange
from ..engine.reads.feed import FeedPage as FeedRead
from ..engine.reads.object_query import live_object_paths
from ..engine.records.attributes import load_attribute_values
from ..engine.records.feed import changed_names
from ..engine.records.values import row_value
from ..engine.workspaces.catalogue import delete_blocker, load_workspace_runtime_state
from ..models.database import (
    AttributeValue,
    AuditEvent,
    ConsumerSubscription,
    Job,
    JobItem,
    ModelRelease,
    ObjectRelation,
    RdmObject,
    Workspace,
    WorkspaceRuntimeState,
)
from ..models.schema import EngineModel
from .schemas.consumer_subscriptions import (
    DeliveryAttempt,
    DeliveryAttemptError,
    DeliveryDetail,
    DeliveryError,
    DeliveryEvent,
    DeliveryPage,
    DeliveryRow,
    PendingDelivery,
    SubscriptionDelivery,
    SubscriptionPage,
    SubscriptionResponse,
    SubscriptionSuspension,
)
from .schemas.imports import ImportProfilePage, ImportProfileProblem, ImportProfileResponse
from .schemas.jobs import (
    BatchResponse,
    JobCounts,
    JobItemPage,
    JobItemResponse,
    JobPage,
    JobProgress,
    JobResponse,
)
from .schemas.model import (
    ModelChangeResponse,
    ModelConsumerContractsResponse,
    ModelDiagnosticResponse,
)
from .schemas.records import (
    AttributeOutput,
    AttributeValueResponse,
    AuditCause,
    AuditEventPage,
    AuditEventResponse,
    FeedCause,
    FeedEntry,
    FeedPage,
    ObjectResponse,
    RelationResponse,
)
from .schemas.workspaces import (
    WorkspaceDetailResponse,
    WorkspaceResponse,
    WorkspaceRuntimeStateResponse,
)


def snapshot_attributes(
    model: EngineModel, object_id: str, attributes: dict[str, Any] | None
) -> list[AttributeOutput]:
    """A change set or publication row's JSON values in the object read's attribute shape."""
    outputs = []
    for key, value in (attributes or {}).items():
        definition = model.attribute_type(key)
        outputs.append(
            AttributeOutput(
                id=f"{object_id}:{key}",
                attributeTypeKey=key,
                name=definition.name if definition else key,
                valueType=definition.valueType if definition else "text",
                value=value,
            )
        )
    return outputs


def diagnostic_response(item: ModelDiagnostic) -> ModelDiagnosticResponse:
    values: dict[str, Any] = {
        "severity": item.severity,
        "code": item.code,
        "path": item.path,
        "message": item.message,
    }
    if item.count is not None:
        values["count"] = item.count
    return ModelDiagnosticResponse(**values)


def consumer_contracts_response(
    active: EngineModel, candidate: EngineModel, active_release_id: str
) -> ModelConsumerContractsResponse:
    """The candidate's consumer API definitions checked against the active release's (C-D17)."""
    diagnostics = contract_diagnostics(active, candidate)
    breaking = any(item.severity == "error" for item in diagnostics)
    return ModelConsumerContractsResponse(
        classification="version_required" if breaking else "compatible",
        activeReleaseId=active_release_id,
        diagnostics=[diagnostic_response(item) for item in diagnostics],
    )


def diagnostic_details(diagnostics: Any) -> list[dict[str, Any]]:
    """Render diagnostics for the ``details`` payload of a structured API error."""
    return [diagnostic_response(item).model_dump(exclude_none=True) for item in diagnostics]


def change_response(item: SemanticChange) -> ModelChangeResponse:
    values: dict[str, Any] = {"kind": item.kind, "path": item.path}
    if item.kind != "added":
        values["before"] = item.before
    if item.kind != "removed":
        values["after"] = item.after
    return ModelChangeResponse(**values)


def build_attribute_value_response(
    model: EngineModel, row: AttributeValue, object_version: int
) -> AttributeValueResponse:
    key = row.attribute_type_key
    definition = model.attribute_type(key)
    return AttributeValueResponse(
        id=row.id,
        attributeTypeKey=key,
        name=definition.name if definition else key,
        valueType=definition.valueType if definition else "text",
        value=row_value(row),
        objectVersion=object_version,
    )


def build_object_responses(
    session: Session, model: EngineModel, objects: list[RdmObject]
) -> list[ObjectResponse]:
    values = load_attribute_values(session, [item.id for item in objects])
    paths = live_object_paths(session, objects)
    return [
        ObjectResponse(
            id=item.id,
            workspaceKey=item.workspace_key,
            applicationKey=item.application_key,
            objectTypeKey=item.object_type_key,
            parentObjectId=item.parent_object_id,
            name=item.name,
            path=paths[item.id],
            attributes=_build_attribute_outputs(model, values[item.id]),
            version=item.version,
            createdAt=item.created_at,
            updatedAt=item.updated_at,
        )
        for item in objects
    ]


def _build_attribute_outputs(model: EngineModel, values: dict) -> list[AttributeOutput]:
    result = []
    for key, (value_id, value) in values.items():
        definition = model.attribute_type(key)
        result.append(
            AttributeOutput(
                id=value_id,
                attributeTypeKey=key,
                name=definition.name if definition else key,
                valueType=definition.valueType if definition else "text",
                value=value,
            )
        )
    return result


def build_relation_response(relation: ObjectRelation) -> RelationResponse:
    return RelationResponse(
        id=relation.id,
        relationTypeKey=relation.relation_type_key,
        fromObjectId=relation.from_object_id,
        toObjectId=relation.to_object_id,
        attributes=relation.attributes,
        version=relation.version,
        createdAt=relation.created_at,
        updatedAt=relation.updated_at,
    )


def workspace_response(item: Workspace) -> WorkspaceResponse:
    return WorkspaceResponse(
        key=item.key,
        label=item.label,
        status=item.status,
        version=item.version,
        createdAt=as_utc(item.created_at),
        updatedAt=as_utc(item.updated_at),
    )


def workspace_detail_response(session: Session, item: Workspace) -> WorkspaceDetailResponse:
    blocker, _ = delete_blocker(
        session, item.key, load_workspace_runtime_state(session).default_workspace_key
    )
    return WorkspaceDetailResponse(
        **workspace_response(item).model_dump(), deletable=blocker is None, deleteBlockedBy=blocker
    )


def runtime_state_response(item: WorkspaceRuntimeState) -> WorkspaceRuntimeStateResponse:
    return WorkspaceRuntimeStateResponse(
        defaultWorkspaceKey=item.default_workspace_key,
        version=item.version,
        updatedAt=as_utc(item.updated_at),
    )


def _audit_response(event: AuditEvent) -> AuditEventResponse:
    changed_fields, attribute_type_keys = changed_names(event)
    return AuditEventResponse(
        id=event.event_id,
        aggregateType=event.aggregate_type,
        aggregateId=event.aggregate_id,
        action=event.action,
        version=event.version,
        changedFields=changed_fields,
        attributeTypeKeys=attribute_type_keys,
        occurredAt=event.occurred_at,
        cause=(
            AuditCause(kind=event.cause_kind, id=event.cause_id) if event.cause_kind else None
        ),
    )


def audit_event_page(events: Page[AuditEvent]) -> AuditEventPage:
    return AuditEventPage(items=[_audit_response(event) for event in events.items], **events.links())


_FEED_KINDS = {"object": "object", "relation": "relation", "publication": "publication"}
_FEED_ACTIONS = {"publication-withdrawn": "withdrawn"}


def _feed_entry(event: AuditEvent, releases: dict[int, str]) -> FeedEntry:
    subject = event.feed_subject or {}
    changes = event.changes if isinstance(event.changes, dict) else {}
    if event.aggregate_type in ("publication", "workspace"):
        kind, changed_fields, attribute_type_keys = "publication", [], []
        # A withdrawal is aggregated on the workspace and names the publication it withdrew.
        entry_id = changes.get("withdrawnPublicationId", event.aggregate_id)
    else:
        kind, entry_id = event.aggregate_type, event.aggregate_id
        changed_fields, attribute_type_keys = changed_names(event)
    return FeedEntry(
        position=event.feed_position,
        eventId=event.event_id,
        occurredAt=event.occurred_at,
        kind=kind,
        action=_FEED_ACTIONS.get(event.action, event.action),
        id=entry_id,
        version=event.version,
        objectTypeKey=subject.get("objectTypeKey"),
        applicationKey=subject.get("applicationKey"),
        previousObjectTypeKey=subject.get("previousObjectTypeKey"),
        relationTypeKey=subject.get("relationTypeKey"),
        fromObjectId=subject.get("fromObjectId"),
        toObjectId=subject.get("toObjectId"),
        changedFields=changed_fields,
        attributeTypeKeys=attribute_type_keys,
        cause=FeedCause(kind=event.cause_kind or "user", id=event.cause_id),
        modelReleaseId=releases.get(event.model_release_id),
    )


def feed_page(session: Session, page: FeedRead) -> FeedPage:
    ids = {event.model_release_id for event in page.entries if event.model_release_id is not None}
    releases = (
        dict(
            session.execute(
                select(ModelRelease.id, ModelRelease.public_id).where(ModelRelease.id.in_(ids))
            )
            .tuples()
            .all()
        )
        if ids
        else {}
    )
    return FeedPage(
        items=[_feed_entry(event, releases) for event in page.entries],
        nextAfter=page.next_after,
        headPosition=page.head_position,
        earliestPosition=page.earliest_position,
    )


def change_set_object_response(item, change_set_id: str, model, *, path=None) -> ObjectResponse:
    attrs = snapshot_attributes(model, item.object_id, item.attributes)
    return ObjectResponse(
        id=item.object_id,
        workspaceKey=(getattr(item, "workspace_key", None) or ""),
        applicationKey=item.application_key,
        objectTypeKey=item.object_type_key,
        parentObjectId=item.parent_object_id,
        name=item.name,
        path=path or [],
        attributes=attrs,
        version=item.version,
        # Not recorded for change set and history rows (WP-10K); never substitute the current time.
        createdAt=None,
        updatedAt=None,
    )


def job_responses(session: Session, jobs: list[Job]) -> list[JobResponse]:
    releases = release_public_ids(session, jobs)
    return [
        JobResponse(
            id=job.id,
            kind=job.kind,
            workspaceKey=job.workspace_key,
            changeSetId=job.change_set_id,
            changeSetVersion=job.change_set_version,
            policy=job.parameters.get("policy"),
            parameters={key: value for key, value in job.parameters.items() if key != "policy"},
            modelReleaseId=releases[job.model_release_id],
            state=job.state,
            stage=job.stage,
            progress=JobProgress(total=job.total, processed=job.processed),
            counts=JobCounts(**job.counts),
            result=job.result,
            error=job.error,
            createdAt=as_utc(job.created_at),
            startedAt=as_utc(job.started_at) if job.started_at else None,
            finishedAt=as_utc(job.finished_at) if job.finished_at else None,
            expiresAt=as_utc(job.expires_at),
            cancelRequestedAt=_optional_utc(job.cancel_requested_at),
            leaseOwner=job.lease_owner,
            leaseExpiresAt=_optional_utc(job.lease_expires_at),
            output=job.output,
        )
        for job in jobs
    ]


def _optional_utc(value: datetime | None) -> datetime | None:
    return as_utc(value) if value is not None else None


def job_page(session: Session, jobs: Page[Job]) -> JobPage:
    return JobPage(items=job_responses(session, jobs.items), **jobs.links())


def job_item_response(item: JobItem) -> JobItemResponse:
    return JobItemResponse(index=item.item_index, ref=item.ref, status=item.status, **item.outcome)


def job_item_page(items: Page[JobItem]) -> JobItemPage:
    return JobItemPage(items=[job_item_response(item) for item in items.items], **items.links())


def batch_response(session: Session, job: Job, items: Page[JobItem]) -> BatchResponse:
    return BatchResponse(
        job=job_responses(session, [job])[0],
        items=[job_item_response(item) for item in items.items],
        **items.links(),
    )


def subscription_response(item: ConsumerSubscription, secret: str | None = None) -> SubscriptionResponse:
    return SubscriptionResponse(
        id=item.public_id,
        name=item.name,
        consumerApi=item.consumer_api,
        contractVersion=item.contract_version,
        workspaceKey=item.workspace_key,
        events=list(item.event_keys),
        filters={name: list(values) for name, values in item.filters.items()},
        url=item.url,
        maxEventsPerBatch=item.max_events_per_batch,
        payload=item.payload,
        format=item.format,
        status=item.status,
        suspension=None
        if item.suspension_reason is None or item.suspended_at is None
        else SubscriptionSuspension(
            reason=item.suspension_reason,
            message=item.suspension_message or "",
            details=item.suspension_details,
            suspendedAt=as_utc(item.suspended_at),
        ),
        acknowledgedThrough=item.acknowledged_position,
        delivery=_delivery(item),
        signingKeyCreatedAt=as_utc(item.signing_key_created_at),
        version=item.version,
        createdAt=as_utc(item.created_at),
        updatedAt=as_utc(item.updated_at),
        signingSecret=secret,
    )


def _delivery(item: ConsumerSubscription) -> SubscriptionDelivery:
    failing = (
        item.pending_position is not None
        and item.failing_since is not None
        and item.last_attempt_at is not None
        and item.last_error is not None
    )
    return SubscriptionDelivery(
        lastDeliveredAt=as_utc(item.last_delivered_at) if item.last_delivered_at else None,
        pending=PendingDelivery(
            deliveryId=item.pending_delivery_id or "",
            throughPosition=item.pending_position or 0,
            attempts=item.attempts,
            failingSince=as_utc(item.failing_since),
            lastAttemptAt=as_utc(item.last_attempt_at),
            nextAttemptAt=as_utc(item.next_attempt_at) if item.next_attempt_at else None,
            lastError=DeliveryError(**(item.last_error or {})),
        )
        if failing
        else None,
    )


def subscription_page(page: Page[ConsumerSubscription]) -> SubscriptionPage:
    return SubscriptionPage(items=[subscription_response(item) for item in page.items], **page.links())


def delivery_page(page: Page[Any], subscription: ConsumerSubscription) -> DeliveryPage:
    """A subscription's deliveries rows (U5a, C-D119)."""
    return DeliveryPage(
        items=[
            DeliveryRow(
                deliveryId=row.delivery_id,
                eventId=row.event_id,
                event=row.event_key,
                change=row.change,
                objectType=row.object_type,
                objectId=row.object_id,
                position=row.position,
                status=row.status,
                attempts=row.attempts,
                responseStatus=row.last_status,
                sentAt=as_utc(row.sent_at) if row.sent_at else None,
                nextAttemptAt=_utc_or_none(delivery_log.row_next_attempt(subscription, row)),
                resendOf=row.resend_of,
            )
            for row in page.items
        ],
        **page.links(),
    )


def delivery_detail_response(found: dict[str, Any]) -> DeliveryDetail:
    """A request of a webhook batch with its events and attempts (U5a, C-D116, C-D117)."""
    request = found["request"]
    return DeliveryDetail(
        deliveryId=request.delivery_id,
        batchId=request.batch_id,
        status=request.status,
        events=[
            DeliveryEvent(
                eventId=event.event_id,
                event=event.event_key,
                change=event.change,
                objectType=event.object_type,
                objectId=event.object_id,
                position=event.position,
            )
            for event in found["events"]
        ],
        requestBody=found["body"],
        requestBytes=request.request_bytes,
        createdAt=as_utc(request.created_at),
        nextAttemptAt=_utc_or_none(found["next_attempt_at"]),
        resendOf=request.resend_of,
        attempts=[
            DeliveryAttempt(
                number=attempt.number,
                startedAt=as_utc(attempt.started_at),
                completedAt=_utc_or_none(attempt.completed_at),
                durationMs=attempt.duration_ms,
                responseStatus=attempt.response_status,
                error=DeliveryAttemptError(kind=attempt.error_kind, message=attempt.error_message or "")
                if attempt.error_kind
                else None,
                responseBody=attempt.response_body,
            )
            for attempt in found["attempts"]
        ],
    )


def _utc_or_none(value: datetime | None) -> datetime | None:
    return as_utc(value) if value is not None else None


def import_profile_response(found: StoredProfile) -> ImportProfileResponse:
    profile = found.profile
    return ImportProfileResponse(
        key=profile.key,
        name=profile.name,
        version=profile.version,
        checkedAgainst=found.checked_against,
        valid=not found.problems,
        problems=[ImportProfileProblem(**problem.body()) for problem in found.problems],
        createdAt=as_utc(profile.created_at),
        updatedAt=as_utc(profile.updated_at),
        **profile.definition,
    )


def import_profile_page(found: list[StoredProfile], page: Page[Any]) -> ImportProfilePage:
    return ImportProfilePage(items=[import_profile_response(item) for item in found], **page.links())
