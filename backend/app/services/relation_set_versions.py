from datetime import UTC, datetime

from sqlalchemy import delete, select, update
from sqlalchemy.orm import Session

from ..models.database import RelationSetVersion


def increment_set_versions(
    session: Session,
    *,
    workspace_key: str,
    change_set_id: str | None,
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
            change_set_id=change_set_id,
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
    change_set_id: str | None,
    relation_type_key: str,
    from_object_type_key: str,
    to_object_type_key: str,
    anchor_object_id: str,
    direction: str,
) -> None:
    """Increment a single set-version row, creating it on first touch (lazy, version 0 → 1)."""
    change_set_filter = (
        RelationSetVersion.change_set_id == change_set_id
        if change_set_id is not None
        else RelationSetVersion.change_set_id.is_(None)
    )
    now = datetime.now(UTC)
    result = session.execute(
        update(RelationSetVersion)
        .where(
            RelationSetVersion.workspace_key == workspace_key,
            change_set_filter,
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
                change_set_id=change_set_id,
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


def increment_single_set_version(
    session: Session,
    *,
    workspace_key: str,
    change_set_id: str | None,
    relation_type_key: str,
    from_object_type_key: str,
    to_object_type_key: str,
    anchor_object_id: str,
    direction: str,
) -> None:
    """Increment one directional set version without touching the opposite direction.

    Used by the mapping replacement endpoint to avoid double-incrementing the source
    anchor when multiple edges change in a single atomic operation.
    """
    _increment_one(
        session,
        workspace_key=workspace_key,
        change_set_id=change_set_id,
        relation_type_key=relation_type_key,
        from_object_type_key=from_object_type_key,
        to_object_type_key=to_object_type_key,
        anchor_object_id=anchor_object_id,
        direction=direction,
    )


def claim_set_version(session: Session, *, expected: int, **binding: object) -> bool:
    """Conditionally advance an exact set, including its initially absent version-zero row."""
    from sqlalchemy.dialects.postgresql import insert as pg_insert
    from sqlalchemy.dialects.sqlite import insert as sqlite_insert

    clauses = [getattr(RelationSetVersion, key) == value for key, value in binding.items()]
    if expected == 0:
        insert = sqlite_insert if session.get_bind().dialect.name == "sqlite" else pg_insert
        session.execute(
            insert(RelationSetVersion).values(**binding, version=0).on_conflict_do_nothing()
        )
    result = session.execute(
        update(RelationSetVersion)
        .where(*clauses, RelationSetVersion.version == expected)
        .values(version=expected + 1, updated_at=datetime.now(UTC))
        .execution_options(synchronize_session=False)
    )
    return result.rowcount == 1


def delete_change_set_relation_set_versions(session: Session, change_set_id: str) -> None:
    """Remove all set-version rows scoped to a discarded or published change set."""
    session.execute(
        delete(RelationSetVersion).where(RelationSetVersion.change_set_id == change_set_id)
    )


def merge_change_set_relation_set_versions_to_live(
    session: Session,
    change_set_id: str,
    workspace_key: str,
) -> None:
    """Carry change-set relation-set version increments into the live context when it is published.

    For each binding+anchor+direction the change set touched, increment the corresponding live
    set-version row by the change set's version (the number of mutations the change set made to that set).
    Then delete the change set rows.
    """
    change_set_rows = list(
        session.scalars(
            select(RelationSetVersion).where(RelationSetVersion.change_set_id == change_set_id)
        )
    )
    now = datetime.now(UTC)
    for row in change_set_rows:
        live_result = session.execute(
            update(RelationSetVersion)
            .where(
                RelationSetVersion.workspace_key == workspace_key,
                RelationSetVersion.change_set_id.is_(None),
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
                    change_set_id=None,
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
    delete_change_set_relation_set_versions(session, change_set_id)
