"""``engine/moves/mapping_kinds.py``: every operation's inverse puts the mapping back exactly, and
the inverse of that inverse applies the operation again (0.11 X1, D107, ADR-041).

A mapping from generated A to generated B is built by one operation of each kind in turn; after
each, its inverse is applied to a copy and must give the definition before it, and the inverse's
own inverse the definition after it.
"""

import copy
from typing import Any

from configurations import all_configurations

from app.engine.model.authoring.document import Document
from app.engine.model.compiler import parse_model
from app.engine.moves.mapping_kinds import IDENTITIES, MappingContext, apply_operation
from app.engine.moves.sides import Side

A, B = all_configurations()["generated-a"], all_configurations()["generated-b"]
SIDES = {
    "a-release": Side(parse_model(A.model), "a-release"),
    "b-release": Side(parse_model(B.model), "b-release"),
    "b-later": Side(parse_model(B.model), "b-later"),
}
MODEL_KEYS = (A.model["release"]["key"], B.model["release"]["key"])


def _apply(
    definition: dict[str, Any], operation: dict[str, Any]
) -> tuple[dict[str, Any], dict[str, Any]]:
    document = Document(copy.deepcopy(definition), identities=IDENTITIES)
    applied = apply_operation(MappingContext(document, MODEL_KEYS, SIDES.get), operation)
    return document.data, applied.inverse


def test_every_kind_is_undone_exactly():
    a, b = A.key, B.key
    operations = [
        {"kind": "mapType", "sourceType": a("R"), "targetType": b("R")},
        {"kind": "mapType", "sourceType": a("D"), "targetType": b("D")},
        {"kind": "mapAttribute", "sourceType": a("R"), "attribute": a("R.u"), "target": b("R.u")},
        {"kind": "setValueMap", "name": "blanks", "values": {"N/A": None}},
        {
            "kind": "mapAttribute",
            "sourceType": a("R"),
            "attribute": a("R.x1"),
            "target": b("R.x1"),
            "valueMap": "blanks",
        },
        {"kind": "mapAttribute", "sourceType": a("R"), "attribute": a("R.x1"), "ignore": True},
        {"kind": "unmapAttribute", "sourceType": a("R"), "attribute": a("R.x1")},
        {"kind": "setDefault", "sourceType": a("R"), "attribute": b("R.q"), "value": "Unknown"},
        {"kind": "setDefault", "sourceType": a("R"), "attribute": b("R.q"), "value": None},
        {"kind": "setMatch", "sourceType": a("R"), "match": {"attributeTypeKey": b("R.u")}},
        {"kind": "setParent", "sourceType": a("D"), "parent": {"from": "source"}},
        {"kind": "setMissing", "sourceType": a("D"), "missing": "create"},
        {"kind": "mapRelation", "sourceType": a("R"), "relation": a("Bown"), "target": b("Bown")},
        {"kind": "setMissing", "sourceType": a("R"), "relation": a("Bown"), "missing": "refuse"},
        {"kind": "unmapRelation", "sourceType": a("R"), "relation": a("Bown")},
        {"kind": "setValueMap", "name": "blanks", "values": None},
        {"kind": "setReleases", "targetReleaseId": "b-later"},
        {"kind": "mapType", "sourceType": a("R"), "targetType": b("K")},
        {"kind": "unmapType", "sourceType": a("D")},
    ]
    definition: dict[str, Any] = {
        "sourceReleaseId": "a-release",
        "targetReleaseId": "b-release",
        "types": [],
        "valueMaps": {},
    }
    for operation in operations:
        after, inverse = _apply(definition, operation)
        assert after != definition, operation
        restored, again = _apply(after, inverse)
        assert restored == definition, operation
        redone, _ = _apply(restored, again)
        assert redone == after, operation
        definition = after
    # Mapping R onto another type forgot what named the old one.
    [entry] = definition["types"]
    assert entry == {
        "source": a("R"),
        "target": b("K"),
        "attributes": [],
        "relations": [],
        "defaults": {},
    }
