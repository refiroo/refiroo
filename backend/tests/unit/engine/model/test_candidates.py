"""A binding's candidate criteria judged in memory, for records a batch lays before they are written
(Base 0.9 K7, ``engine/model/candidates.py``). The meaning is the list's (``object_query``): a
value held empty is ``isNull``, a value held at all is not ``isUnset`` (0.9 R-F4)."""

import json
from pathlib import Path

from app.engine.model.candidates import meets_criteria
from app.engine.model.compiler import parse_model
from app.models.schema import CandidateCriterion

STARTER = Path(__file__).resolve().parents[5] / "model" / "rdm-starter.json"
MODEL = parse_model(json.loads(STARTER.read_text()))


def _meets(op: str, value: object, values: dict) -> bool:
    criteria = (CandidateCriterion(field="domain-code", op=op, value=value),)
    return meets_criteria(MODEL, criteria, ("A record", lambda: values), [])


def test_a_record_without_the_value_has_no_value():
    assert _meets("isNull", False, {"domain-code": "HC"})
    assert not _meets("isNull", False, {})
    assert not _meets("isNull", False, {"domain-code": None})


def test_a_value_held_empty_is_null_and_set():
    assert _meets("isNull", True, {"domain-code": None})
    assert not _meets("isNull", True, {})
    assert not _meets("isUnset", True, {"domain-code": None})
    assert _meets("isUnset", True, {})
