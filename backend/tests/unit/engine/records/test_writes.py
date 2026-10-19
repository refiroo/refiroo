"""``engine/records/writes.py``: the write unit's removals past PostgreSQL's 65,535 parameters.

0.11 X5 found the unique-value check after a 110,000-record write listing each record as a
parameter of its own (``unique_values``). The write unit's removals listed records and
relationships the same way, so a removal of as many (a whole-workspace move's deletions,
published) would be refused by PostgreSQL. Each list is one array parameter.
"""

from uuid import uuid4

from scenario import W1

from app.db import SessionLocal
from app.engine.records.writes import LiveWrites


def test_a_removal_takes_more_relationships_than_parameters_allow(seeded):
    """Given 70,000 relationship IDs to remove. When the write unit removes them. Then its
    statements run (no relationship holds these IDs, so nothing is removed)."""
    relation_ids = {str(uuid4()) for _ in range(70_000)}
    with SessionLocal() as session:
        LiveWrites(session, W1).remove_records([], relation_ids, set())
        session.rollback()
