"""Unit tests for the snapshot reads (``app.engine.reads.snapshot_reads``)."""

from uuid import uuid4

from scenario import W1
from sqlalchemy import select

from app.db import SessionLocal
from app.engine.change_sets.lifecycle import create_change_set
from app.engine.model.registry import resolve_model_snapshot
from app.engine.reads.snapshot_reads import change_set_context, find_objects
from app.models.database import RdmObject


def test_find_objects_reads_more_records_than_a_statement_may_bind(seeded):
    """0.9 R (R-F24): deleting about 100,000 records in a change set failed in a read of their
    types, `number of parameters must be between 0 and 65535`: the change set's projection binds
    each ID twice. Any number of IDs is read, a statement at a time."""
    with SessionLocal() as session:
        release = resolve_model_snapshot(session).release_db_id
        staged = create_change_set(session, W1, release, source="currentLive")
        session.commit()
        context = change_set_context(session, staged.id)
        stored = session.scalars(select(RdmObject.id).where(RdmObject.workspace_key == W1)).all()
        missing = [str(uuid4()) for _ in range(40_000)]

        found = find_objects(session, context, [*missing[:20_000], *stored, *missing[20_000:]])

    assert stored and set(found) == set(stored)
