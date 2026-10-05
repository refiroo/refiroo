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


def test_as_of_is_documented_where_a_read_can_return_a_dated_type():
    """``asOf`` (0.9 C16) on get by ID, XREF and batch resolve, which can return the model's dated
    types, and on the list of a dated type, not on the list of an undated one; the refusals, the
    ``RDM-As-Of-Applied`` header and an optional ``asOfApplied`` on the envelopes."""
    model = load_model(EXAMPLE)
    (rdm,) = model.consumerApis
    document = consumer_openapi(model, rdm, root_path="", resolve_max_items=1000)
    base = "/api/consumer/rdm/v1"

    def names(path: str, method: str = "get") -> set[str]:
        return {item["name"] for item in document["paths"][f"{base}{path}"][method]["parameters"]}

    for path, method in (("/objects/{id}", "get"), ("/xref", "get"), ("/resolve", "post"), ("/lists/values", "get")):
        assert "asOf" in names(path, method), path
        operation = document["paths"][f"{base}{path}"][method]
        assert "INVALID_AS_OF, AS_OF_NOT_SUPPORTED" in operation["responses"]["400"]["description"]
        assert "RDM-As-Of-Applied" in operation["responses"]["200"]["headers"]
    assert "asOf" not in names("/lists/codelists")
    assert "asOf" not in names("/publications")
    (as_of,) = [item for item in document["paths"][f"{base}/xref"]["get"]["parameters"] if item["name"] == "asOf"]
    assert as_of["schema"] == {"type": "string", "format": "date"}
    for envelope in ("ListPage", "XrefPage", "ResolveAnswer"):
        schema = document["components"]["schemas"][envelope]
        assert "asOfApplied" in schema["properties"] and "asOfApplied" not in schema["required"]
