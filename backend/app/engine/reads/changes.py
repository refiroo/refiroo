"""Data and model changes across workspaces, newest first (Product 0.12 Z6, D340–D344, D347).

One read of the audit for "what did this person or client change", "what changed in the workspaces
I read since Monday" and "what did I change": filtered by who made a change, its workspace, its
kind and its time, and always by what the caller may see (D342, as every list, D249). Security
events stay at ``/security-events`` (D319); a relation set's ``transition`` summaries are left out,
since each relationship it changed is its own entry.
"""

from collections.abc import Sequence
from datetime import datetime
from typing import Any, Literal

from sqlalchemy import and_, cast, false, func, or_, select
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Session

from ...common.pagination import Page, PageRequest, datetime_key, integer_key, paginate_statement
from ...models.database import AuditEvent, OAuthClient, User
from ..authorization.permissions import Permissions

ChangeKind = Literal["record", "relationship", "change-set", "publication", "model"]

# The audit aggregates of each kind; a withdrawal is aggregated on the workspace.
KIND_AGGREGATES: dict[str, tuple[str, ...]] = {
    "record": ("object", "change-set-object"),
    "relationship": ("relation",),
    "change-set": ("change-set",),
    "publication": ("publication", "workspace"),
    "model": ("model_draft", "model_release", "model_runtime_state", "workspace_model"),
}
KIND_OF = {aggregate: kind for kind, items in KIND_AGGREGATES.items() for aggregate in items}
# Model administration outside every workspace: drafts, installs, activations from before 0.11.
OUTSIDE_WORKSPACES = ("model_draft", "model_release", "model_runtime_state")

_KEYS = (
    datetime_key("occurredAt", AuditEvent.occurred_at, "occurred_at", descending=True),
    integer_key("sequenceId", AuditEvent.sequence_id, "sequence_id", descending=True),
)


def visible(permissions: Permissions) -> Any:
    """The entries the caller may see (D342): in a workspace with Browse there; model
    administration outside workspaces with Model authoring at the instance; an entry of a deleted
    workspace, or one never placed, only with Browse at the instance."""
    browsed = permissions.workspaces(frozenset({"browse"}))
    data = ~AuditEvent.aggregate_type.in_(OUTSIDE_WORKSPACES)
    if browsed is None:
        conditions = [data]
    elif browsed:
        conditions = [and_(data, AuditEvent.workspace_key.in_(sorted(browsed)))]
    else:
        conditions = []
    if permissions.allows("model-authoring", None):
        conditions.append(AuditEvent.aggregate_type.in_(OUTSIDE_WORKSPACES))
    return or_(*conditions) if conditions else false()


def _made_by(session: Session, actor_id: str) -> Any:
    """Entries the person or client ``actor_id`` made, on the actor's own index; none for an ID
    no principal has."""
    user = session.scalar(select(User.id).where(User.public_id == actor_id))
    if user is not None:
        return AuditEvent.actor_user_id == user
    client = session.scalar(select(OAuthClient.id).where(OAuthClient.public_id == actor_id))
    return AuditEvent.actor_client_id == client if client is not None else false()


def narrowing(
    *,
    object_type_key: str | None = None,
    relation_type_key: str | None = None,
    cause_id: str | None = None,
    action: str | None = None,
    attribute_key: str | None = None,
    live: bool = False,
) -> list[Any]:
    """The conditions an account of history links to (0.16 AO2, AO-D27): the changes a fact counted,
    read in the database from the entry's ``subject`` and ``changes`` as the account reads them.
    ``live`` keeps entries that changed live data (those with a feed position); staged entries of a
    published change set stand beside them in the audit and are left out."""
    changes = cast(AuditEvent.changes, JSONB)
    conditions: list[Any] = []
    if object_type_key is not None:
        conditions.append(
            func.coalesce(
                AuditEvent.subject["objectTypeKey"].as_string(),
                AuditEvent.changes["objectTypeKey"].as_string(),
            )
            == object_type_key
        )
    if relation_type_key is not None:
        conditions.append(
            func.coalesce(
                AuditEvent.subject["relationTypeKey"].as_string(),
                AuditEvent.changes["relationTypeKey"].as_string(),
            )
            == relation_type_key
        )
    if cause_id is not None:
        conditions.append(AuditEvent.cause_id == cause_id)
    if action == "moved":
        conditions.append(
            and_(
                AuditEvent.action != "created",
                or_(
                    changes.has_key("parentObjectId"),
                    changes["changedFields"].has_key("parentObjectId"),
                ),
            )
        )
    elif action is not None:
        conditions.append(AuditEvent.action == action)
    if attribute_key is not None:
        conditions.append(
            or_(
                changes["attributeTypeKeys"].has_key(attribute_key),
                changes["attributes"].has_key(attribute_key),
            )
        )
    if live:
        conditions.append(AuditEvent.feed_position.is_not(None))
    return conditions


def change_page(
    session: Session,
    permissions: Permissions,
    *,
    actor_id: str | None,
    workspace_key: str | None,
    kinds: Sequence[str],
    since: datetime | None,
    until: datetime | None,
    page: PageRequest,
    page_size: int,
    object_type_key: str | None = None,
    relation_type_key: str | None = None,
    cause_id: str | None = None,
    action: str | None = None,
    attribute_key: str | None = None,
    live: bool = False,
) -> Page[AuditEvent]:
    """The caller's page of changes, newest first: ``since`` included, ``until`` not."""
    aggregates = [item for kind in (kinds or KIND_AGGREGATES) for item in KIND_AGGREGATES[kind]]
    statement = select(AuditEvent).where(
        AuditEvent.aggregate_type.in_(aggregates),
        # A withdrawal is the only entry the workspace aggregate holds today; others stay out.
        or_(AuditEvent.aggregate_type != "workspace", AuditEvent.action == "publication-withdrawn"),
        visible(permissions),
    )
    if actor_id is not None:
        statement = statement.where(_made_by(session, actor_id))
    if workspace_key is not None:
        statement = statement.where(AuditEvent.workspace_key == workspace_key)
    if since is not None:
        statement = statement.where(AuditEvent.occurred_at >= since)
    if until is not None:
        statement = statement.where(AuditEvent.occurred_at < until)
    statement = statement.where(
        *narrowing(
            object_type_key=object_type_key,
            relation_type_key=relation_type_key,
            cause_id=cause_id,
            action=action,
            attribute_key=attribute_key,
            live=live,
        )
    )
    return paginate_statement(
        session,
        statement,
        keys=_KEYS,
        scope="changes",
        filters={
            "actorId": actor_id,
            "workspaceKey": workspace_key,
            "kind": sorted(kinds),
            "since": since.isoformat() if since else None,
            "until": until.isoformat() if until else None,
            "objectTypeKey": object_type_key,
            "relationTypeKey": relation_type_key,
            "causeId": cause_id,
            "action": action,
            "attributeKey": attribute_key,
            "live": live,
        },
        page=page,
        page_size=page_size,
        message="Changes cursor is invalid",
    )
