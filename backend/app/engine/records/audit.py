from collections.abc import Iterable
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from ...common.encoding import to_jsonable
from ...common.pagination import Page, PageRequest, datetime_key, integer_key, paginate_statement
from ...models.database import AuditEvent, AuditEventSubject

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
        changes=to_jsonable(changes),
    )
    session.add(event)
    session.flush()
    for object_id in dict.fromkeys(object_ids):
        session.add(AuditEventSubject(audit_event_id=event.sequence_id, object_id=object_id))
    return event


def object_history(
    session: Session,
    *,
    object_id: str,
    object_type_key: str,
    workspace_key: str,
    page: PageRequest,
    page_size: int,
) -> Page[AuditEvent]:
    statement = (
        select(AuditEvent)
        .join(AuditEventSubject, AuditEventSubject.audit_event_id == AuditEvent.sequence_id)
        .where(AuditEventSubject.object_id == object_id)
    )
    return paginate_statement(
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
