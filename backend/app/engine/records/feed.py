"""Feed positions (Base 0.9 F1, INTEGRATION_API §F3, D5).

Every change to a workspace's live data takes the next position of the workspace's feed: a counter
on the workspace row, incremented under the row lock every live write already holds from
``LiveWrites._begin`` until it commits (PG-D5). A transaction's entries get consecutive positions;
one that rolls back rolls its counter back too, so positions are gapless and a reader never sees a
position commit before a lower one. Change-set work changes no live data and takes none.

An entry keeps what the feed names about it (``subject``): the object type and application of a
record, the relation type and ends of a relation; a later delete leaves nothing to look them up by.
"""

from typing import Any

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from ...models.database import ModelRuntimeState, Workspace


def take_positions(session: Session, workspace_key: str, count: int) -> tuple[int, int | None]:
    """Take ``count`` positions of the workspace's feed: the first one, and the model release the
    write runs under (the active one, which the commit check holds it to).

    The caller holds the workspace row lock (``LiveWrites._begin``, or publishing's and
    withdrawal's own); the update needs no other. ``updated_at`` is kept: the workspace itself
    did not change.
    """
    active = (
        select(ModelRuntimeState.active_model_release_id)
        .where(ModelRuntimeState.id == 1)
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


def object_subject(item: Any, previous_object_type_key: str | None = None) -> dict[str, Any]:
    """What a record's entry names: a live row, a decided record or a published one."""
    subject = {"objectTypeKey": item.object_type_key, "applicationKey": item.application_key}
    if previous_object_type_key is not None:
        subject["previousObjectTypeKey"] = previous_object_type_key
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
