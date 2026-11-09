"""``engine/model/authoring/draft_migration.py``: where the records of a moved type go (0.13 MG)."""

from app.engine.model.authoring.draft_migration import application_target


def test_a_type_that_left_one_application_for_another_sends_its_records_there():
    # Listed in four applications, one of which it left for a fifth: a released type moved out of the
    # application its records stand in while others still list it.
    assert (
        application_target(
            {"a", "b", "c", "d"},
            {"e", "b", "c", "d"},
        )
        == "e"
    )
    assert application_target({"a"}, {"b"}) == "b"


def test_a_type_that_left_no_application_or_only_left_names_no_destination():
    assert application_target({"a", "b"}, {"a", "b"}) is None
    assert application_target({"a", "b"}, {"a"}) is None
    assert application_target({"a"}, {"a", "b"}) is None
    assert application_target(set(), {"a"}) is None
