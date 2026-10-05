"""The consumer API document builder over the operators example model's definitions."""

from pathlib import Path

from openapi_spec_validator import validate as validate_openapi

from app.engine.model.consumer_openapi import consumer_openapi
from app.engine.model.loader import load_model

EXAMPLE = Path(__file__).resolve().parents[5] / "model" / "rdm-operators-timetables.json"


def test_every_definition_of_the_operators_model_gives_a_valid_document():
    """Each of the model's consumer APIs gives valid OpenAPI 3.1. A list whose parent parameter shares
    a definition parameter's name (master-data's codelists and domain) lists that name once, as the
    parent, which is what the route reads it as; the other routes keep the definition parameter."""
    model = load_model(EXAMPLE)
    assert [item.key for item in model.consumerApis] == ["master-data", "timetables", "systems", "translations"]
    for definition in model.consumerApis:
        validate_openapi(consumer_openapi(model, definition, root_path="", resolve_max_items=1000))

    master_data = next(item for item in model.consumerApis if item.key == "master-data")
    document = consumer_openapi(model, master_data, root_path="", resolve_max_items=1000)
    codelists = document["paths"]["/api/consumer/master-data/v1/lists/codelists"]["get"]["parameters"]
    (domain,) = [item for item in codelists if item["name"] == "domain"]
    assert domain["description"].startswith("Object IDs of Domain records")
    xref = document["paths"]["/api/consumer/master-data/v1/xref"]["get"]["parameters"]
    (domain,) = [item for item in xref if item["name"] == "domain"]
    assert not domain["description"].startswith("Object IDs")
