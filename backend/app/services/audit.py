from collections.abc import Iterable
from datetime import UTC, datetime
from typing import Any

from fastapi.encoders import jsonable_encoder
from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session

from ..errors import api_error
from ..models.api import AuditEventPage, AuditEventResponse
from ..models.database import AuditEvent, AuditEventSubject
from .cursors import decode_cursor, encode_cursor


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
    cursor: str | None,
    page_size: int,
) -> AuditEventPage:
    filters = {
        "objectId": object_id,
        "objectTypeKey": object_type_key,
        "workspaceKey": workspace_key,
    }
    statement = (
        select(AuditEvent)
        .join(AuditEventSubject, AuditEventSubject.audit_event_id == AuditEvent.sequence_id)
        .where(AuditEventSubject.object_id == object_id)
    )
    if cursor is not None:
        position = decode_cursor(
            cursor,
            scope="object-history",
            sort=("-occurredAt", "-sequenceId"),
            filters=filters,
            position_size=2,
            message="Audit history cursor is invalid",
        )
        try:
            occurred_at = datetime.fromisoformat(position[0])
            sequence_id = int(position[1])
        except ValueError:
            raise api_error(422, "invalid_cursor", "Audit history cursor is invalid") from None
        statement = statement.where(
            or_(
                AuditEvent.occurred_at < occurred_at,
                and_(
                    AuditEvent.occurred_at == occurred_at,
                    AuditEvent.sequence_id < sequence_id,
                ),
            )
        )
    events = list(
        session.scalars(
            statement.order_by(AuditEvent.occurred_at.desc(), AuditEvent.sequence_id.desc()).limit(
                page_size + 1
            )
        )
    )
    visible = events[:page_size]
    next_cursor = None
    if len(events) > page_size:
        last = visible[-1]
        next_cursor = encode_cursor(
            (_as_utc(last.occurred_at).isoformat(), str(last.sequence_id)),
            scope="object-history",
            sort=("-occurredAt", "-sequenceId"),
            filters=filters,
        )
    return AuditEventPage(
        items=[_audit_response(event) for event in visible], nextCursor=next_cursor
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


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)
