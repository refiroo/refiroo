"""The consumer API document builder over the example model's definitions."""

import json
from pathlib import Path

from openapi_spec_validator import validate as validate_openapi

from app.engine.model.compiler import parse_model
from app.engine.model.consumer_definitions import consumer_api
from app.engine.model.consumer_openapi import consumer_openapi
from app.engine.model.loader import load_model
from app.engine.reads import consumer_lists, consumer_xref
from app.models.search_index import MIN_INDEXED_LENGTH

EXAMPLE = Path(__file__).resolve().parents[5] / "model" / "rdm-operators-timetables.json"
STARTER = EXAMPLE.with_name("rdm-starter.json")


def _base(definition) -> str:
    """The definition's routes, under the contract version it serves."""
    return f"/api/consumer/{definition.key}/v{definition.contractVersion}"


def test_the_example_model_gives_one_valid_document_over_every_type():
    """The model's ``rdm`` consumer API exposes every object type, so its XREF looks up across the
    whole model, and its document is valid OpenAPI 3.1. A list ``within`` a filter (codelists and
    domain) lists that name once, as the parent, which is what the route reads it as; the other
    routes keep the filter."""
    model = load_model(EXAMPLE)
    rdm = consumer_api(model, "rdm")
    assert rdm.key == "rdm"
    assert set(rdm.objectTypes) == {item.key for item in model.objectTypes}
    document = consumer_openapi(model, rdm, root_path="", resolve_max_items=1000, token_url="/oauth/token")
    validate_openapi(document)

    codelists = document["paths"][f"{_base(rdm)}/lists/codelists"]["get"]["parameters"]
    (domain,) = [item for item in codelists if item["name"] == "domain"]
    assert domain["description"].startswith("Object IDs of Domain records")
    xref = document["paths"][f"{_base(rdm)}/xref"]["get"]["parameters"]
    (domain,) = [item for item in xref if item["name"] == "domain"]
    assert not domain["description"].startswith("Object IDs")


def test_as_of_is_documented_where_a_read_can_return_a_dated_type():
    """``asOf`` (0.9 C16) on get by ID, XREF and batch resolve, which can return the model's dated
    types, and on the list of a dated type, not on the list of an undated one; the refusals, the
    ``RDM-As-Of-Applied`` header and an optional ``asOfApplied`` on the envelopes."""
    model = load_model(EXAMPLE)
    rdm = consumer_api(model, "rdm")
    document = consumer_openapi(model, rdm, root_path="", resolve_max_items=1000, token_url="/oauth/token")
    base = _base(rdm)

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


def test_a_definition_with_events_documents_its_pull_feed():
    """A definition that declares events gets ``GET …/events`` (0.9 C10): the reserved names, its
    parameters without ``to.`` names (the pull feed takes no crosswalk), the event and page schemas
    with the object as get by ID answers it, and ``410``; one without events has no such path."""
    document = json.loads(EXAMPLE.read_text())
    (definition,) = [item for item in document["consumerApis"] if item["key"] == "rdm"]
    del definition["operations"]["events"]
    model = parse_model(document)
    plain = consumer_openapi(model, consumer_api(model, "rdm"), root_path="", resolve_max_items=1000, token_url="/oauth/token")
    assert f"{_base(consumer_api(model, 'rdm'))}/events" not in plain["paths"]

    definition["operations"]["events"] = {
        "custom": [{"key": "reference-data-changed", "objectTypes": definition["exposes"][:2], "changes": ["created", "deleted"]}]
    }
    model = parse_model(document)
    built = consumer_openapi(model, consumer_api(model, "rdm"), root_path="", resolve_max_items=1000, token_url="/oauth/token")
    validate_openapi(built)
    events = built["paths"][f"{_base(consumer_api(model, 'rdm'))}/events"]["get"]
    names = {item["name"] for item in events["parameters"]}
    assert {"workspace", "event", "after", "cursor", "pageSize", "payload"} <= names
    assert set(definition.get("filters", {})) <= names
    assert not any(name.startswith("to.") for name in names)
    assert "410" in events["responses"] and "409" in events["responses"]
    schemas = built["components"]["schemas"]
    assert schemas["Event"]["properties"]["object"] == {"$ref": "#/components/schemas/Object"}
    assert schemas["Event"]["properties"]["event"]["enum"] == ["reference-data-changed"]


def test_the_document_states_the_limits_the_reads_apply():
    """0.9 R-F21, C-D37: the page sizes, the shortest contains term, the match limit and the term
    limit the document states are the engine's own, so a changed limit changes the document."""
    model = load_model(STARTER)
    rdm = consumer_api(model, "rdm")
    document = consumer_openapi(model, rdm, root_path="", resolve_max_items=1000, token_url="/oauth/token")
    xref = document["paths"][f"{_base(rdm)}/xref"]["get"]
    (size,) = [item for item in xref["parameters"] if item["name"] == "pageSize"]
    smallest, largest, default = consumer_lists.PAGE_SIZE
    assert size["schema"] == {"type": "integer", "minimum": smallest, "maximum": largest, "default": default}
    assert f"at least {MIN_INDEXED_LENGTH} characters" in xref["description"]
    assert f"{consumer_xref.MATCH_LIMIT:,} records" in xref["description"]
    assert f"at most {consumer_xref.MAX_TERMS} terms" in xref["description"]
