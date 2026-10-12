"""``engine/records/relation_set_versions.py``: sets advanced in bulk (0.10 A3a, D73).

A batch's relationships advance their relation sets in one statement per thousand sets: each set
ends at the version it had plus its count, a set not written before at its count, live and in a
change set alike, whatever the number of sets.
"""

import random

import pytest
from scenario import W1
from sqlalchemy import select

from app.db import SessionLocal
from app.engine.change_sets.lifecycle import create_change_set
from app.engine.model.registry import resolve_model_snapshot
from app.engine.records.relation_set_versions import increment_set_versions_by
from app.models.database import RelationSetVersion


def _key(index: int) -> tuple[str, str, str, str, str]:
    return ("rel", "from-type", "to-type", f"anchor-{index:05d}", ("outgoing", "incoming")[index % 2])


def _versions(session, change_set_id):
    return {
        (r.relation_type_key, r.from_object_type_key, r.to_object_type_key, r.anchor_object_id,
         r.direction): r.version
        for r in session.scalars(
            select(RelationSetVersion).where(
                RelationSetVersion.workspace_key == W1,
                RelationSetVersion.change_set_id.is_(None)
                if change_set_id is None
                else RelationSetVersion.change_set_id == change_set_id,
                RelationSetVersion.relation_type_key == "rel",
            )
        )
    }


@pytest.mark.parametrize("seed", [1, 2, 3])
@pytest.mark.parametrize("in_change_set", [False, True])
def test_many_sets_advance_by_their_counts_old_and_new(seeded, seed, in_change_set):
    rng = random.Random(seed)
    first = {_key(i): rng.randint(1, 5) for i in range(0, 2600, 2)}
    second = {_key(i): rng.randint(1, 5) for i in range(rng.randint(0, 3), 2600)}
    with SessionLocal() as session:
        release = resolve_model_snapshot(session).release_db_id
        change_set_id = (
            create_change_set(session, W1, release, source="currentLive").id
            if in_change_set
            else None
        )
        increment_set_versions_by(
            session, workspace_key=W1, change_set_id=change_set_id, counts=first
        )
        increment_set_versions_by(
            session, workspace_key=W1, change_set_id=change_set_id, counts=second
        )
        expected = {key: first.get(key, 0) + second.get(key, 0) for key in first | second}
        assert _versions(session, change_set_id) == expected
        if in_change_set:
            assert _versions(session, None) == {}
        session.rollback()
