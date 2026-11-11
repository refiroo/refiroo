"""The place the candidate criteria fix, and the fields that identify a type's records (0.17 PP-D24,
PP-D25; ``engine/model/candidate_places.py``), judged on the example model."""

import json
from pathlib import Path

from app.engine.model.candidate_places import derive_place, identifying_fields, propose_place
from app.engine.model.compiler import parse_model
from app.models.schema import CandidateCriterion

STARTER = Path(__file__).resolve().parents[5] / "model" / "rdm-starter.json"
MODEL = parse_model(json.loads(STARTER.read_text()))


def _place(*criteria: CandidateCriterion):
    return derive_place(MODEL, "system", "system-value", criteria)


def _criterion(field: str, op: str = "eq", value: object = "Group A") -> CandidateCriterion:
    return CandidateCriterion(field=field, op=op, value=value)


def test_equalities_on_one_ancestor_type_fix_the_place():
    place = _place(
        _criterion("ancestor:system-group.name"),
        _criterion("ancestor:system-group.group-code", value="GA"),
    )
    assert place is not None
    assert (place.object_type_key, place.name, place.attributes) == (
        "system-group",
        "Group A",
        {"group-code": "GA"},
    )


def test_a_place_without_a_value_its_type_requires_is_not_derived():
    # A group needs its code: a record created without it would be refused, so none is offered.
    assert _place(_criterion("ancestor:system-group.name")) is None


def test_criteria_that_fix_no_one_place_derive_none():
    assert _place() is None
    assert _place(_criterion("ancestor:system-group.name", "contains")) is None
    assert _place(_criterion("name")) is None
    # The same field twice is a choice of two values, not one place.
    assert (
        _place(
            _criterion("ancestor:system-group.name"),
            _criterion("ancestor:system-group.name", value="B"),
            _criterion("ancestor:system-group.group-code", value="GA"),
        )
        is None
    )
    # The column's own type is no place under the column.
    assert _place(_criterion("ancestor:system.name")) is None


def test_the_identifying_fields_start_with_the_name():
    fields = identifying_fields(MODEL, "system-value")
    assert fields[0] == "name" and len(set(fields)) == len(fields)
    assert identifying_fields(MODEL, "no-such-type") == []


def test_every_text_field_of_the_type_is_offered_not_only_the_unique_ones():
    # PP-D27: the choice of what a cell lists is every text attribute the type binds.
    fields = identifying_fields(MODEL, "system-value")
    text = [
        item.attributeTypeKey
        for item in MODEL.object_type("system-value").attributes
        if MODEL.attribute_type(item.attributeTypeKey).valueType in {"text", "longText"}
    ]
    assert set(text) <= set(fields)
    assert not any(
        MODEL.attribute_type(key).valueType == "boolean" for key in fields if key != "name"
    )


def _lenient_model():
    """The starter with the translation-group-like type asking for no code, so a new one can be proposed."""
    raw = json.loads(STARTER.read_text())
    group = next(item for item in raw["objectTypes"] if item["key"] == "system-group")
    for binding in group["attributes"]:
        binding.pop("required", None)
    return parse_model(raw)


def _propose(model, used, *criteria, chain=()):
    return propose_place(model, "system", "system-value", criteria, used, chain)


def test_a_proposed_container_takes_the_type_and_the_most_common_name_of_the_ones_in_use():
    model = _lenient_model()
    used = [("system-group", "B"), ("system-group", "A"), ("system-group", "B")]
    place = _propose(model, used)
    assert place is not None and place.proposed
    assert (place.object_type_key, place.name, place.attributes) == ("system-group", "B", {})
    # A tie goes to the first name in order.
    assert _propose(model, [("system-group", "Y"), ("system-group", "X")]).name == "X"


def test_nothing_is_proposed_without_evidence_or_where_a_container_would_be_refused():
    model = _lenient_model()
    assert _propose(model, []) is None
    # A type the other columns use that cannot sit under the column and hold the cell.
    assert _propose(model, [("system", "S")]) is None
    # A group that asks for a code cannot be proposed: the dialog could not fill it.
    assert _propose(MODEL, [("system-group", "A")]) is None
    # A new group so named would not meet the relationship's ancestor criteria.
    criteria = _criterion("ancestor:system-group.name", value="Booked")
    assert _propose(model, [("system-group", "Other")], criteria) is None
    assert _propose(model, [("system-group", "Booked")], criteria).name == "Booked"
