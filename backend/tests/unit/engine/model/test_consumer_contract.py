"""A consumer field's arity follows the cardinality at the exposed record's end
(``engine/model/consumer_contract.projection_shape``; 0.9 K3a, D138): ``one`` where that record
holds at most one relationship of the binding, ``many`` otherwise, in either direction."""

import json
from pathlib import Path

import pytest

from app.engine.model.compiler import compile_model, parse_model
from app.engine.model.consumer_contract import output_contract, projection_shape
from app.engine.model.consumer_definitions import consumer_api

STARTER = Path(__file__).resolve().parents[5] / "model" / "rdm-starter.json"
RELATION = "value-filed-under"


def _model(cardinality: str):
    """The starter with one more binding between two types its consumer API exposes."""
    source = json.loads(STARTER.read_text())
    source["relationTypes"].append(
        {
            "key": RELATION,
            "reverseKey": "files-value",
            "name": "Filed under",
            "reverseName": "Files",
        }
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


# --- attributes of the relationship in a related block's fields --------------------------------

CARRIED = "relation:is-primary"


def _carrying(
    *, via: str = RELATION, source: str = CARRIED, bound: bool = True, elsewhere: dict | None = None
):
    """The starter with a relation whose binding carries a boolean and a text attribute of its own, and a
    consumer API related block over ``via`` reading ``source``; ``elsewhere`` edits the definition."""
    document = json.loads(STARTER.read_text())
    document["attributeTypes"] += [
        {"key": "is-primary", "name": "Is primary", "valueType": "boolean"},
        {"key": "local-label", "name": "Local label"},
    ]
    document["relationTypes"].append(
        {
            "key": RELATION,
            "reverseKey": "files-value",
            "name": "Filed under",
            "reverseName": "Files",
        }
    )
    document["objectTypeRelations"].append(
        {
            "relationTypeKey": RELATION,
            "fromObjectTypeKey": "master-value",
            "toObjectTypeKey": "codelist",
            "cardinality": "many-to-many",
            **({"attributeTypeKeys": ["is-primary", "local-label"]} if bound else {}),
        }
    )
    api = document["consumerApis"][0]
    api["object"]["related"]["filedUnder"] = {"via": via, "fields": {"id": "id", "flag": source}}
    if elsewhere:
        elsewhere(api)
    return document


def _contract(**options):
    model = parse_model(_carrying(**options))
    return output_contract(model, consumer_api(model, "rdm"))


def _refused(**options):
    """The first error the compiler reports for the model."""
    compiled = compile_model(_carrying(**options))
    assert not compiled.valid
    return next(item for item in compiled.diagnostics if item.severity == "error")


def test_a_relation_attribute_is_typed_as_its_value_type():
    assert _contract().projections["filedUnder"]["fields"] == {"id": "text", "flag": "boolean"}
    assert (
        _contract(source="relation:local-label").projections["filedUnder"]["fields"]["flag"]
        == "text"
    )


def test_the_reverse_key_reads_the_same_binding_from_its_other_end():
    """Via the reverse key the block runs incoming, from the exposed codelists to the values."""
    contract = _contract(via="files-value")
    assert contract.projections["filedUnder"]["fields"]["flag"] == "boolean"


def test_the_reverse_route_needs_the_binding_end_to_be_exposed():
    def hide_codelist(api):
        api["exposes"] = ["master-value"]
        api["object"]["fields"]["code"] = {"role": "code", "from": ["value-code"]}
        api["object"].pop("parent", None)

    error = _refused(via="files-value", elsewhere=hide_codelist)
    assert error.code == "INVALID_REFERENCE"
    assert error.path.startswith("/consumerApis/rdm")


@pytest.mark.parametrize(
    "source", ["relation:no-such-attribute", "relation:value-code", "relation:"]
)
def test_an_attribute_the_binding_does_not_carry_is_refused_at_the_field(source):
    error = _refused(source=source)
    assert error.code == "INVALID_REFERENCE"
    assert error.path == "/consumerApis/rdm/object/related/filedUnder/fields/flag"
    assert source in error.message and RELATION in error.message


def test_a_binding_without_attributes_refuses_the_source():
    error = _refused(bound=False)
    assert error.path == "/consumerApis/rdm/object/related/filedUnder/fields/flag"
    assert "is-primary" in error.message


def test_an_object_field_cannot_read_a_relation_attribute():
    def read(api):
        api["object"]["fields"]["flagged"] = CARRIED

    error = _refused(elsewhere=read)
    assert error.code == "INVALID_REFERENCE"
    assert error.path == "/consumerApis/rdm/object/fields/flagged"


def test_a_filter_may_match_the_relationship_but_the_object_may_not():
    """``matchOn`` of an ``onRelated`` filter reads the relationship's attribute; an ``under`` filter, which
    has no relationship per record, refuses it at its pointer."""

    def filter_on_related(api):
        api["filters"]["label"] = {
            "onRelated": "filedUnder",
            "matchOn": ["relation:local-label"],
            "keepOnlyMatching": True,
        }

    model = parse_model(_carrying(elsewhere=filter_on_related))
    assert consumer_api(model, "rdm") is not None

    def filter_under(api):
        api["filters"]["label"] = {"under": ["codelist"], "matchOn": [CARRIED]}

    error = _refused(elsewhere=filter_under)
    assert error.code == "INVALID_REFERENCE"
    assert error.path == "/consumerApis/rdm/filters/label/matchOn/0"

    def unbound(api):
        api["filters"]["label"] = {
            "onRelated": "filedUnder",
            "matchOn": ["relation:no-such-attribute"],
            "keepOnlyMatching": True,
        }

    assert _refused(elsewhere=unbound).path == "/consumerApis/rdm/filters/label/matchOn/0"
