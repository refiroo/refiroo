from datetime import UTC, datetime

from sqlalchemy import delete, select, update
from sqlalchemy.orm import Session

from ..models.database import RelationSetVersion


def increment_set_versions(
    session: Session,
    *,
    workspace_key: str,
    workspace_draft_id: str | None,
    relation_type_key: str,
    from_object_type_key: str,
    to_object_type_key: str,
    from_object_id: str,
    to_object_id: str,
) -> None:
    """Atomically increment the outgoing and incoming set versions for one relation mutation.

    Called on every relation create, update or delete so the mapping-replacement endpoint can
    detect concurrent modifications to the same binding set.
    """
    for anchor_id, direction in (
        (from_object_id, "outgoing"),
        (to_object_id, "incoming"),
    ):
        _increment_one(
            session,
            workspace_key=workspace_key,
            workspace_draft_id=workspace_draft_id,
            relation_type_key=relation_type_key,
            from_object_type_key=from_object_type_key,
            to_object_type_key=to_object_type_key,
            anchor_object_id=anchor_id,
            direction=direction,
        )


def _increment_one(
    session: Session,
    *,
    workspace_key: str,
    workspace_draft_id: str | None,
    relation_type_key: str,
    from_object_type_key: str,
    to_object_type_key: str,
    anchor_object_id: str,
    direction: str,
) -> None:
    """Increment a single set-version row, creating it on first touch (lazy, version 0 → 1)."""
    draft_filter = (
        RelationSetVersion.workspace_draft_id == workspace_draft_id
        if workspace_draft_id is not None
        else RelationSetVersion.workspace_draft_id.is_(None)
    )
    now = datetime.now(UTC)
    result = session.execute(
        update(RelationSetVersion)
        .where(
            RelationSetVersion.workspace_key == workspace_key,
            draft_filter,
            RelationSetVersion.relation_type_key == relation_type_key,
            RelationSetVersion.from_object_type_key == from_object_type_key,
            RelationSetVersion.to_object_type_key == to_object_type_key,
            RelationSetVersion.anchor_object_id == anchor_object_id,
            RelationSetVersion.direction == direction,
        )
        .values(version=RelationSetVersion.version + 1, updated_at=now)
        .execution_options(synchronize_session=False)
    )
    if result.rowcount == 0:
        session.add(
            RelationSetVersion(
                workspace_key=workspace_key,
                workspace_draft_id=workspace_draft_id,
                relation_type_key=relation_type_key,
                from_object_type_key=from_object_type_key,
                to_object_type_key=to_object_type_key,
                anchor_object_id=anchor_object_id,
                direction=direction,
                version=1,
                created_at=now,
                updated_at=now,
            )
        )
        session.flush()


def delete_draft_set_versions(session: Session, draft_id: str) -> None:
    """Remove all set-version rows scoped to a discarded or activated draft."""
    session.execute(
        delete(RelationSetVersion).where(RelationSetVersion.workspace_draft_id == draft_id)
    )


def merge_draft_set_versions_to_live(
    session: Session,
    draft_id: str,
    workspace_key: str,
) -> None:
    """Carry draft set-version increments into the live context during activation.

    For each binding+anchor+direction the draft touched, increment the corresponding live
    set-version row by the draft's version (the number of mutations the draft made to that set).
    Then delete the draft rows.
    """
    draft_rows = list(
        session.scalars(
            select(RelationSetVersion).where(
                RelationSetVersion.workspace_draft_id == draft_id
            )
        )
    )
    now = datetime.now(UTC)
    for row in draft_rows:
        live_result = session.execute(
            update(RelationSetVersion)
            .where(
                RelationSetVersion.workspace_key == workspace_key,
                RelationSetVersion.workspace_draft_id.is_(None),
                RelationSetVersion.relation_type_key == row.relation_type_key,
                RelationSetVersion.from_object_type_key == row.from_object_type_key,
                RelationSetVersion.to_object_type_key == row.to_object_type_key,
                RelationSetVersion.anchor_object_id == row.anchor_object_id,
                RelationSetVersion.direction == row.direction,
            )
            .values(
                version=RelationSetVersion.version + row.version,
                updated_at=now,
            )
            .execution_options(synchronize_session=False)
        )
        if live_result.rowcount == 0:
            session.add(
                RelationSetVersion(
                    workspace_key=workspace_key,
                    workspace_draft_id=None,
                    relation_type_key=row.relation_type_key,
                    from_object_type_key=row.from_object_type_key,
                    to_object_type_key=row.to_object_type_key,
                    anchor_object_id=row.anchor_object_id,
                    direction=row.direction,
                    version=row.version,
                    created_at=now,
                    updated_at=now,
                )
            )
    session.flush()
    delete_draft_set_versions(session, draft_id)
