"""``engine/moves/mapping_inference.py``: how the inference scores candidates (0.11 X1, D108).

Generated A proposed onto generated B, changed by hand where a rule needs it: a type with nothing
like it in the target is not proposed; two source attributes like one target attribute do not
both take it; a pair of value types no value crosses is never proposed; and what the stored
records share outweighs what the attributes share.
"""

import copy

from configurations import all_configurations

from app.engine.model.compiler import parse_model
from app.engine.moves.mapping_inference import Inference
from app.engine.moves.sides import Side

A, B = all_configurations()["generated-a"], all_configurations()["generated-b"]


def _side(model, release="r"):
    return Side(parse_model(model), release)


def _types(proposals):
    return {p.source_type: p for p in proposals if p.kind == "type"}


def test_a_type_like_nothing_is_not_proposed():
    model = copy.deepcopy(A.model)
    model["attributeTypes"].append({"key": "qq-zz", "name": "Qzq", "valueType": "boolean"})
    model["objectTypes"].append(
        {
            "key": "qq-lonely",
            "name": "Qzq lonely",
            "pluralName": "Qzq lonelies",
            "displayAttributeTypeKey": "qq-zz",
            "attributes": [{"attributeTypeKey": "qq-zz", "order": 10}],
            "features": {"rootCreatable": True},
        }
    )
    model["applications"][0]["objectTypeKeys"].append("qq-lonely")
    types = _types(Inference(_side(model), _side(B.model)).proposals())
    assert "qq-lonely" not in types
    assert types[A.key("R")].target == B.key("R")


def test_two_attributes_like_one_target_take_it_once():
    model = copy.deepcopy(A.model)
    for item in model["attributeTypes"]:
        if item["key"] == A.key("R.x2"):
            item["name"] = "R.x1"
    proposal = _types(Inference(_side(model), _side(B.model)).proposals())[A.key("R")]
    targets = [o["target"] for o in proposal.operations if o["kind"] == "mapAttribute"]
    assert len(targets) == len(set(targets))
    attributes = {
        o["attribute"]: o["target"] for o in proposal.operations if o["kind"] == "mapAttribute"
    }
    assert attributes[A.key("R.x1")] == B.key("R.x1")


def test_value_types_no_value_crosses_are_never_proposed():
    model = copy.deepcopy(B.model)
    for item in model["attributeTypes"]:
        if item["key"] == B.key("H.rank"):
            item["valueType"] = "boolean"
    proposal = _types(Inference(_side(A.model), _side(model)).proposals())[A.key("H")]
    assert A.key("H.rank") not in {
        o["attribute"] for o in proposal.operations if o["kind"] == "mapAttribute"
    }


def test_stored_records_outweigh_shared_attributes():
    model = copy.deepcopy(B.model)
    for item in model["objectTypes"]:
        if item["key"] == B.key("R"):
            item["name"] = "Something else"
        if item["key"] == B.key("K"):
            item["name"] = "R"
    source, target = _side(A.model), _side(model)
    without = _types(Inference(source, target).proposals())[A.key("R")]
    assert without.target == B.key("R")
    stored = {(A.key("R"), B.key("K")): 10}
    proposal = _types(Inference(source, target, stored, {A.key("R"): 10}).proposals())[A.key("R")]
    assert proposal.target == B.key("K")
    assert {"kind": "storedRecords", "matched": 10, "of": 10} in proposal.evidence
    assert B.key("R") in {a["target"] for a in proposal.alternatives}


def test_shared_records_propose_a_match_by_a_unique_attribute():
    source, target = _side(A.model), _side(B.model)
    plain = _types(Inference(source, target).proposals())[A.key("R")]
    assert "setMatch" not in {o["kind"] for o in plain.operations}
    shared = {(A.key("R"), B.key("R")): 4}
    proposal = _types(Inference(source, target, shared, {A.key("R"): 8}).proposals())[A.key("R")]
    [match] = [o for o in proposal.operations if o["kind"] == "setMatch"]
    assert match["match"] == {"attributeTypeKey": B.key("R.u")}
    assert proposal.expected["match"] == match["match"]
