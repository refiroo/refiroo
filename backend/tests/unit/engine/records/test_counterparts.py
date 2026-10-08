"""A counterpart's ID (0.9 J5, D97): derived from the record's ID and the workspace alone."""

from uuid import UUID, uuid4

from app.engine.records.counterparts import counterpart


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
