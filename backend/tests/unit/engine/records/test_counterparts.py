"""A counterpart's ID (0.9 J5, D97): derived from the record's ID and the workspace alone; in
PostgreSQL, ``rdm_counterpart`` derives the same (0.11 X2, D120)."""

from random import Random
from uuid import UUID, uuid4

from sqlalchemy import text

from app.db import SessionLocal
from app.engine.records.counterparts import counterpart

WORKSPACES = ("default", "second-site", "ö-site/east", "x~1", "a" * 160)


def test_a_counterpart_is_the_same_for_one_record_and_workspace_and_differs_otherwise():
    record, other = str(uuid4()), str(uuid4())
    assert counterpart("west", record) == counterpart("west", record)
    assert counterpart("west", record) != counterpart("east", record)
    assert counterpart("west", record) != counterpart("west", other)
    assert counterpart("west", record) != record


def test_a_counterpart_is_a_version_4_uuid_the_api_accepts_back():
    derived = UUID(counterpart("west", str(uuid4())))
    assert derived.version == 4
    assert derived.variant == "specified in RFC 4122"


def test_the_database_derives_the_same_counterpart_as_python(seeded):
    """Generated workspace keys and record IDs, those with characters outside ASCII and a JSON
    pointer's separators included."""
    random = Random(20261021)
    pairs = [
        (workspace, str(UUID(int=random.getrandbits(128), version=4)))
        for workspace in WORKSPACES
        for _ in range(40)
    ]
    with SessionLocal() as session:
        found = session.execute(
            text(
                "SELECT rdm_counterpart(w, o) FROM unnest(CAST(:w AS text[]), CAST(:o AS text[]))"
                " AS p(w, o)"
            ),
            {"w": [w for w, _ in pairs], "o": [o for _, o in pairs]},
        ).scalars()
        assert list(found) == [counterpart(w, o) for w, o in pairs]
