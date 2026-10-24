"""Security events: who changed access, and who signed in (Product 0.12 Z4, D317, D318).

Each change to people, groups and their members, roles, grants, clients and their secrets and token
signing keys, a one-time password link, a sign-out everywhere and each sign-in is an audit entry
outside every workspace and the feed. Its subjects are the public IDs of the principals it is
about, so a person's or client's events are those they made or are about. It records what changed,
never a password, secret, link or key. The actor is the caller, as for every audit entry
(``records/audit``); a sign-in names the person, a failed one nobody.
"""

from collections.abc import Iterable, Sequence
from typing import Any

from sqlalchemy import exists, or_, select
from sqlalchemy.orm import Session

from ...common.pagination import Page, PageRequest, datetime_key, integer_key, paginate_statement
from ...models.database import SECURITY_AGGREGATES, AuditEvent, AuditEventSubject, OAuthClient, User
from .principals import Ref, columns

_KEYS = (
    datetime_key("occurredAt", AuditEvent.occurred_at, "occurred_at", descending=True),
    integer_key("sequenceId", AuditEvent.sequence_id, "sequence_id", descending=True),
)
# What an entry names as its actor when it does not name the caller: nobody, or a principal.
CALLER = object()


def record(
    session: Session,
    aggregate_type: str,
    aggregate_id: str,
    action: str,
    *,
    about: Iterable[str] = (),
    details: dict[str, Any] | None = None,
    version: int = 1,
    by: Ref | None | object = CALLER,
) -> AuditEvent:
    """One security event in the caller's transaction; ``about`` are the public IDs of the
    principals it concerns, ``details`` what changed (never a secret)."""
    assert aggregate_type in SECURITY_AGGREGATES
    named: dict[str, Any] = {}
    if by is not CALLER:
        principal = by if isinstance(by, tuple) else None
        named = {"actor_kind": principal[0] if principal else None, **columns(principal, "actor")}
    event = AuditEvent(
        aggregate_type=aggregate_type,
        aggregate_id=aggregate_id,
        action=action,
        version=version,
        changes=details or {},
        **named,
    )
    session.add(event)
    session.flush()
    session.add_all(
        AuditEventSubject(audit_event_id=event.sequence_id, object_id=subject)
        for subject in dict.fromkeys(about)
    )
    return event


def changed(fields: Sequence[str], **values: Any) -> dict[str, Any]:
    """The details of a change: the fields that changed and their new values where shown."""
    return {"changedFields": list(fields), **{k: v for k, v in values.items() if k in fields}}


def event_page(
    session: Session,
    *,
    principal_id: str | None,
    aggregate_types: Sequence[str] | None,
    page: PageRequest,
    page_size: int,
) -> Page[AuditEvent]:
    """Security events newest first; ``principal_id`` keeps those a person or client made or that
    are about them."""
    statement = select(AuditEvent).where(
        AuditEvent.aggregate_type.in_(aggregate_types or SECURITY_AGGREGATES)
    )
    if principal_id is not None:
        made_by = or_(
            AuditEvent.actor_user_id.in_(select(User.id).where(User.public_id == principal_id)),
            AuditEvent.actor_client_id.in_(
                select(OAuthClient.id).where(OAuthClient.public_id == principal_id)
            ),
        )
        about = exists().where(
            AuditEventSubject.audit_event_id == AuditEvent.sequence_id,
            AuditEventSubject.object_id == principal_id,
        )
        statement = statement.where(or_(made_by, about))
    return paginate_statement(
        session,
        statement,
        keys=_KEYS,
        scope="security-events",
        filters={"principalId": principal_id, "aggregateType": list(aggregate_types or [])},
        page=page,
        page_size=page_size,
        message="Security event cursor is invalid",
    )
