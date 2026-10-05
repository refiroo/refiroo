"""The consumer API document builder over the operators example model's definitions."""

from pathlib import Path

from openapi_spec_validator import validate as validate_openapi

from app.engine.model.consumer_openapi import consumer_openapi
from app.engine.model.loader import load_model

EXAMPLE = Path(__file__).resolve().parents[5] / "model" / "rdm-operators-timetables.json"


def test_the_operators_model_gives_one_valid_document_over_every_type():
    """The model's one consumer API exposes every object type, so its XREF looks up across the whole
    model, and its document is valid OpenAPI 3.1. A list whose parent parameter shares a definition
    parameter's name (codelists and domain) lists that name once, as the parent, which is what the
    route reads it as; the other routes keep the definition parameter."""
    model = load_model(EXAMPLE)
    (rdm,) = model.consumerApis
    assert rdm.key == "rdm"
    assert set(rdm.objectTypes) == {item.key for item in model.objectTypes}
    document = consumer_openapi(model, rdm, root_path="", resolve_max_items=1000)
    validate_openapi(document)

    codelists = document["paths"]["/api/consumer/rdm/v1/lists/codelists"]["get"]["parameters"]
    (domain,) = [item for item in codelists if item["name"] == "domain"]
    assert domain["description"].startswith("Object IDs of Domain records")
    xref = document["paths"]["/api/consumer/rdm/v1/xref"]["get"]["parameters"]
    (domain,) = [item for item in xref if item["name"] == "domain"]
    assert not domain["description"].startswith("Object IDs")
