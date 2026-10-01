from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Literal

from sqlalchemy import delete, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from ...errors import api_error
from ...models.database import RelationSetVersion


@dataclass(frozen=True)
class SetClaim:
    """A write's claim on one end's set: the version its caller read for the set anchored at that
    end, in ``direction`` (``outgoing`` anchors at the relation's from end)."""

    direction: Literal["outgoing", "incoming"]
    expected: int


def set_claim(expected: int | None, direction: str | None) -> SetClaim | None:
    """The claim a request names, or none; half a claim is refused."""
    if expected is None and direction is None:
        return None
    if expected is None or direction is None:
        raise api_error(
            422,
            "relation_set_claim_incomplete",
            "expectedRelationSetVersion and relationSetDirection are given together",
            {"parameters": ["expectedRelationSetVersion", "relationSetDirection"]},
        )
    return SetClaim(direction, expected)  # type: ignore[arg-type]


def advance_set_versions(
    session: Session,
    *,
    workspace_key: str,
    change_set_id: str | None,
    relation_type_key: str,
    from_object_type_key: str,
    to_object_type_key: str,
    from_object_id: str,
    to_object_id: str,
    claim: SetClaim | None = None,
) -> int | None:
    """Advance both ends' sets by one for a relation write; with ``claim``, the claimed end's set
    advances only from the version the caller read, otherwise the write is refused whole.

    Returns the claimed set's new version, or ``None`` without a claim.
    """
    if claim is None:
        increment_set_versions(
            session,
            workspace_key=workspace_key,
            change_set_id=change_set_id,
            relation_type_key=relation_type_key,
            from_object_type_key=from_object_type_key,
            to_object_type_key=to_object_type_key,
            from_object_id=from_object_id,
            to_object_id=to_object_id,
        )
        return None
    binding = {
        "workspace_key": workspace_key,
        "change_set_id": change_set_id,
        "relation_type_key": relation_type_key,
        "from_object_type_key": from_object_type_key,
        "to_object_type_key": to_object_type_key,
    }
    anchor, other, opposite = (
        (from_object_id, to_object_id, "incoming")
        if claim.direction == "outgoing"
        else (to_object_id, from_object_id, "outgoing")
    )
    if not claim_set_version(
        session, expected=claim.expected, **binding, anchor_object_id=anchor, direction=claim.direction
    ):
        actual = session.scalar(
            select(RelationSetVersion.version).where(
                # ``== None`` renders IS NULL for the live set.
                *(getattr(RelationSetVersion, key) == value for key, value in binding.items()),
                RelationSetVersion.anchor_object_id == anchor,
                RelationSetVersion.direction == claim.direction,
            )
        )
        raise api_error(
            409,
            "relation_set_version_conflict",
            "The relation set has changed since it was read; refresh it before retrying",
            {
                "anchorObjectId": anchor,
                "direction": claim.direction,
                "relationSetVersion": actual or 0,
            },
        )
    _increment_one(session, **binding, anchor_object_id=other, direction=opposite)
    return claim.expected + 1


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
    clauses = [getattr(RelationSetVersion, key) == value for key, value in binding.items()]
    if expected == 0:
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
