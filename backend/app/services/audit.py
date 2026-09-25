from collections.abc import Iterable
from typing import Any

from fastapi.encoders import jsonable_encoder
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models.api import AuditEventPage, AuditEventResponse
from ..models.database import AuditEvent, AuditEventSubject
from .pagination import PageRequest, datetime_key, integer_key, paginate_statement

_HISTORY_KEYS = (
    datetime_key("occurredAt", AuditEvent.occurred_at, "occurred_at", descending=True),
    integer_key("sequenceId", AuditEvent.sequence_id, "sequence_id", descending=True),
)


def record_audit_event(
    session: Session,
    *,
    aggregate_type: str,
    aggregate_id: str,
    action: str,
    version: int,
    changes: dict[str, Any],
    object_ids: Iterable[str],
) -> AuditEvent:
    event = AuditEvent(
        aggregate_type=aggregate_type,
        aggregate_id=aggregate_id,
        action=action,
        version=version,
        changes=jsonable_encoder(changes),
    )
    session.add(event)
    session.flush()
    for object_id in dict.fromkeys(object_ids):
        session.add(AuditEventSubject(audit_event_id=event.sequence_id, object_id=object_id))
    return event


def list_object_history(
    session: Session,
    *,
    object_id: str,
    object_type_key: str,
    workspace_key: str,
    page: PageRequest,
    page_size: int,
) -> AuditEventPage:
    statement = (
        select(AuditEvent)
        .join(AuditEventSubject, AuditEventSubject.audit_event_id == AuditEvent.sequence_id)
        .where(AuditEventSubject.object_id == object_id)
    )
    events = paginate_statement(
        session,
        statement,
        keys=_HISTORY_KEYS,
        scope="object-history",
        filters={
            "objectId": object_id,
            "objectTypeKey": object_type_key,
            "workspaceKey": workspace_key,
        },
        page=page,
        page_size=page_size,
        message="Audit history cursor is invalid",
    )
    return AuditEventPage(
        items=[_audit_response(event) for event in events.items], **events.links()
    )


def _audit_response(event: AuditEvent) -> AuditEventResponse:
    changes = event.changes if isinstance(event.changes, dict) else {}
    attributes = changes.get("attributes")
    return AuditEventResponse(
        id=event.event_id,
        aggregateType=event.aggregate_type,
        aggregateId=event.aggregate_id,
        action=event.action,
        version=event.version,
        changedFields=sorted(str(key) for key in changes),
        attributeTypeKeys=_attribute_type_keys(event, attributes),
        occurredAt=event.occurred_at,
    )


def _attribute_type_keys(event: AuditEvent, attributes: Any) -> list[str]:
    if not isinstance(attributes, dict):
        return []
    if event.aggregate_type == "relation" and event.action == "updated":
        return sorted(
            {
                str(key)
                for position in ("from", "to")
                for key in (
                    attributes.get(position)
                    if isinstance(attributes.get(position), dict)
                    else {}
                )
            }
        )
    return sorted(str(key) for key in attributes)
