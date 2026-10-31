"""Which type a column of translations can be read for (``engine/tasks/translations.py``): the
model must give the type exactly one relationship to a type contained in a parent."""

from app.engine.tasks.catalog import Related, TypeInfo
from app.engine.tasks.translations import language_of, structure


def _info(*related):
    return TypeInfo("branch", "Branch", "Branches", "atlas", (), (), (), True, tuple(related))


def _related(relation="guards"):
    return Related(relation, relation.title(), "room", "Room", "atlas", (("estate", "Estate", True),))


def test_exactly_one_relationship_to_a_contained_type_is_the_structure():
    found, why = structure(_info(_related()))
    assert found is not None and found.type_key == "room" and why is None


def test_none_or_several_leave_the_column_out_and_the_reason_says_which():
    none_found, why_none = structure(_info())
    assert none_found is None and "no relationship" in why_none
    several, why_several = structure(_info(_related("guards"), _related("holds")))
    assert several is None and "several" in why_several and "Holds" in why_several


def test_a_header_names_a_language_by_itself_or_by_a_word_of_it():
    assert language_of("ES") == "ES" and language_of("Spanish") == "Spanish"
    assert language_of("Name (Spanish)") == "Spanish"
    assert language_of("Price") is None
