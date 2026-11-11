"""Whose an element is and whether an operation holds (``engine/sources/inference/compare.py`` and
``run.engine_elements``, 0.10 A6, D92)."""

import copy

from app.engine.sources.inference.compare import holds, snapshot
from app.engine.sources.inference.run import ProposalStep, engine_elements

MODEL = {
    "objectTypes": [{"key": "item", "name": "Item", "attributes": [{"attributeTypeKey": "code"}]}],
    "attributeTypes": [{"key": "code", "name": "Code", "valueType": "text"}],
    "relationTypes": [],
    "objectTypeRelations": [],
    "applications": [],
}
PROFILE = {
    "sources": [
        {
            "id": "items",
            "sheet": "Items",
            "objectTypeKey": "item",
            "columns": [{"column": "Code", "attributeTypeKey": "code"}],
        }
    ],
    "valueMaps": {"blanks": {"N/A": None}},
}


def _step(number, elements, undone=False, model=MODEL, profile=PROFILE):
    origin = {
        "type": "proposal",
        "proposalId": f"p{number}",
        "snapshot": snapshot(model, profile, elements),
    }
    return ProposalStep(number, origin, undone)


def test_an_element_as_the_latest_proposal_step_left_it_is_the_engines():
    steps = [_step(1, ["objectType:item", "column:items/Code", "valueMap:blanks"])]
    assert set(engine_elements(steps, MODEL, PROFILE)) == {
        "objectType:item",
        "column:items/Code",
        "valueMap:blanks",
    }


def test_any_other_change_makes_it_the_administrators_and_putting_it_back_the_engines_again():
    steps = [_step(1, ["objectType:item", "column:items/Code"])]
    renamed = copy.deepcopy(MODEL)
    renamed["objectTypes"][0]["name"] = "Product"
    assert set(engine_elements(steps, renamed, PROFILE)) == {"column:items/Code"}
    assert set(engine_elements(steps, copy.deepcopy(MODEL), PROFILE)) == {
        "objectType:item",
        "column:items/Code",
    }


def test_an_undone_step_owns_nothing_and_a_later_step_takes_over():
    later = copy.deepcopy(MODEL)
    later["objectTypes"][0]["attributes"].append({"attributeTypeKey": "size"})
    steps = [_step(1, ["objectType:item"]), _step(2, ["objectType:item"], model=later)]
    assert set(engine_elements(steps, later, PROFILE)) == {"objectType:item"}
    assert set(engine_elements(steps, MODEL, PROFILE)) == set()
    undone = [_step(1, ["objectType:item"], undone=True)]
    assert engine_elements(undone, MODEL, PROFILE) == {}


def test_an_operation_the_draft_already_has_holds():
    assert holds({"kind": "addObjectType", "key": "item"}, MODEL, PROFILE)
    assert not holds({"kind": "addObjectType", "key": "colour"}, MODEL, PROFILE)
    assert holds(
        {"kind": "attachAttribute", "objectType": "item", "attributeType": "code"}, MODEL, PROFILE
    )
    assert holds(
        {
            "kind": "mapColumn",
            "source": "items",
            "column": "Code",
            "binding": {"attributeTypeKey": "code"},
        },
        MODEL,
        PROFILE,
    )
    assert not holds(
        {"kind": "mapColumn", "source": "items", "column": "Code", "binding": {"field": "name"}},
        MODEL,
        PROFILE,
    )
    mapped = copy.deepcopy(PROFILE)
    mapped["sources"][0]["columns"][0]["valueMap"] = "blanks"
    assert holds(
        {
            "kind": "mapColumn",
            "source": "items",
            "column": "Code",
            "binding": {"attributeTypeKey": "code"},
        },
        MODEL,
        mapped,
    ), "a value map another step added does not undo the binding"
    assert holds(
        {"kind": "setValueMap", "name": "blanks", "entries": {"N/A": None}}, MODEL, PROFILE
    )
    assert not holds(
        {"kind": "setValueMap", "name": "blanks", "entries": {"-": None}}, MODEL, PROFILE
    )
    assert holds({"kind": "unmapColumn", "source": "items", "column": "Gone"}, MODEL, PROFILE)
    assert holds(
        {"kind": "setRelease", "schemaVersion": "0.9"}, {**MODEL, "schemaVersion": "0.10"}, PROFILE
    )
    assert not holds(
        {"kind": "setRelease", "schemaVersion": "0.10"}, {**MODEL, "schemaVersion": "0.9"}, PROFILE
    )
