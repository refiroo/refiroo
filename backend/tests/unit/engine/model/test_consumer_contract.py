"""A consumer field's arity follows the cardinality at the exposed record's end
(``engine/model/consumer_contract.projection_shape``; 0.9 K3a, D138): ``one`` where that record
holds at most one relationship of the binding, ``many`` otherwise, in either direction."""

import json
from pathlib import Path

import pytest

from app.engine.model.compiler import parse_model
from app.engine.model.consumer_contract import projection_shape
from app.engine.model.consumer_definitions import consumer_api

STARTER = Path(__file__).resolve().parents[5] / "model" / "rdm-starter.json"
RELATION = "value-filed-under"


def _model(cardinality: str):
    """The starter with one more binding between two types its consumer API exposes."""
    source = json.loads(STARTER.read_text())
    source["relationTypes"].append(
        {"key": RELATION, "reverseKey": "files-value", "name": "Filed under", "reverseName": "Files"}
    )
    source["objectTypeRelations"].append(
        {
            "relationTypeKey": RELATION,
            "fromObjectTypeKey": "master-value",
            "toObjectTypeKey": "codelist",
            "cardinality": cardinality,
        }
    )
    return parse_model(source)


@pytest.mark.parametrize(
    ("cardinality", "outgoing", "incoming"),
    [
        ("one-to-one", "one", "one"),
        ("one-to-many", "many", "one"),
        ("many-to-one", "one", "many"),
        ("many-to-many", "many", "many"),
    ],
)
def test_arity_from_the_exposed_records_end(cardinality, outgoing, incoming):
    model = _model(cardinality)
    definition = consumer_api(model, "rdm")
    assert projection_shape(model, definition, RELATION, "outgoing") == outgoing
    assert projection_shape(model, definition, RELATION, "incoming") == incoming
