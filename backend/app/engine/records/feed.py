"""Feed positions (Base 0.9 F1, INTEGRATION_API §F3, D5).

Every change to a workspace's live data takes the next position of the workspace's feed: a counter
on the workspace row, incremented under the row lock every live write already holds from
``LiveWrites._begin`` until it commits (PG-D5). A transaction's entries get consecutive positions;
one that rolls back rolls its counter back too, so positions are gapless and a reader never sees a
position commit before a lower one. Change-set work changes no live data and takes none.

An entry keeps what the feed names about it (``subject``): the object type, application and parent
of a record (and its parent before, when it moved), the relation type and ends of a relation; a later
delete leaves nothing to look them up by. The parent lets consumer events find the records a
containment projection shows (C10, C-D95).
"""

from typing import Any

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from ...models.database import AuditEvent, Workspace, WorkspaceModel


def take_positions(session: Session, workspace_key: str, count: int) -> tuple[int, int | None]:
    """Take ``count`` positions of the workspace's feed: the first one, and the model release the
    write runs under (the workspace's, which the commit check holds it to).

    The caller holds the workspace row lock (``LiveWrites._begin``, or publishing's and
    withdrawal's own); the update needs no other. ``updated_at`` is kept: the workspace itself
    did not change.
    """
    active = (
        select(WorkspaceModel.model_release_id)
        .where(WorkspaceModel.workspace_key == workspace_key)
        .scalar_subquery()
    )
    last, release_id = session.execute(
        update(Workspace)
        .where(Workspace.key == workspace_key)
        .values(feed_position=Workspace.feed_position + count, updated_at=Workspace.updated_at)
        .returning(Workspace.feed_position, active)
        .execution_options(synchronize_session=False)
    ).one()
    return last - count + 1, release_id


def object_subject(
    item: Any,
    previous_object_type_key: str | None = None,
    *,
    previous_parent_object_id: str | None = None,
    moved: bool = False,
) -> dict[str, Any]:
    """What a record's entry names: a live row, a decided record or a published one, with its
    parent; a record that ``moved`` also names the parent it had (C-D95)."""
    subject = {
        "objectTypeKey": item.object_type_key,
        "applicationKey": item.application_key,
        "parentObjectId": item.parent_object_id,
    }
    if previous_object_type_key is not None:
        subject["previousObjectTypeKey"] = previous_object_type_key
    if moved:
        subject["previousParentObjectId"] = previous_parent_object_id
    return subject


def relation_subject(
    relation_type_key: str, from_object_id: str, to_object_id: str
) -> dict[str, Any]:
    """What a relation's entry names: its type and both ends, which identify it after a delete."""
    return {
        "relationTypeKey": relation_type_key,
        "fromObjectId": from_object_id,
        "toObjectId": to_object_id,
    }


def changed_names(event: AuditEvent) -> tuple[list[str], list[str]]:
    """The field names and attribute types an entry changed, never values: what history, the feed
    and consumer events read (Base 0.9 F2, D16)."""
    changes = event.changes if isinstance(event.changes, dict) else {}
    if "changedFields" in changes:
        # A type change (ADR-034) stores its full before state, and a publish's entry (D15) only
        # names; either names what changed and the attribute types it concerned, not values.
        changed_fields = [str(key) for key in changes.get("changedFields", [])]
        attribute_type_keys = sorted(str(key) for key in changes.get("attributeTypeKeys", []))
    else:
        # A batch overwrite records the version it replaced; it is how, not what, it changed.
        changed_fields = sorted(str(key) for key in changes if key != "overwrite")
        attribute_type_keys = _attribute_type_keys(event, changes.get("attributes"))
    return changed_fields, attribute_type_keys


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
