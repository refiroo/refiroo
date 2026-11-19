"""The consumer API document builder over the starter model's definitions."""

import json
from pathlib import Path

from openapi_spec_validator import validate as validate_openapi

from app.engine.model.compiler import parse_model
from app.engine.model.consumer_definitions import consumer_api
from app.engine.model.consumer_openapi import consumer_openapi
from app.engine.model.loader import load_model
from app.engine.reads import consumer_lists, consumer_xref
from app.models.search_index import MIN_INDEXED_LENGTH

STARTER = Path(__file__).resolve().parents[5] / "model" / "rdm-starter.json"


def _base(definition) -> str:
    """The definition's routes, under the contract version it serves."""
    return f"/api/consumer/{definition.key}/v{definition.contractVersion}"


def test_a_definition_over_every_type_gives_one_valid_document():
    """The starter's ``rdm`` consumer API widened to every object type, so its XREF looks up across
    the whole model, and its document is valid OpenAPI 3.1. A list ``within`` a filter (codelists and
    domain) lists that name once, as the parent, which is what the route reads it as; the other
    routes keep the filter."""
    document = json.loads(STARTER.read_text())
    (definition,) = [item for item in document["consumerApis"] if item["key"] == "rdm"]
    definition["exposes"] = [item["key"] for item in document["objectTypes"]]
    model = parse_model(document)
    rdm = consumer_api(model, "rdm")
    assert rdm.key == "rdm"
    assert set(rdm.objectTypes) == {item.key for item in model.objectTypes}
    document = consumer_openapi(
        model, rdm, root_path="", resolve_max_items=1000, token_url="/oauth/token"
    )
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
    model = load_model(STARTER)
    rdm = consumer_api(model, "rdm")
    document = consumer_openapi(
        model, rdm, root_path="", resolve_max_items=1000, token_url="/oauth/token"
    )
    base = _base(rdm)

    def names(path: str, method: str = "get") -> set[str]:
        return {item["name"] for item in document["paths"][f"{base}{path}"][method]["parameters"]}

    for path, method in (
        ("/objects/{id}", "get"),
        ("/xref", "get"),
        ("/resolve", "post"),
        ("/lists/values", "get"),
    ):
        assert "asOf" in names(path, method), path
        operation = document["paths"][f"{base}{path}"][method]
        assert "INVALID_AS_OF, AS_OF_NOT_SUPPORTED" in operation["responses"]["400"]["description"]
        assert "RDM-As-Of-Applied" in operation["responses"]["200"]["headers"]
    assert "asOf" not in names("/lists/codelists")
    assert "asOf" not in names("/publications")
    (as_of,) = [
        item
        for item in document["paths"][f"{base}/xref"]["get"]["parameters"]
        if item["name"] == "asOf"
    ]
    assert as_of["schema"] == {"type": "string", "format": "date"}
    for envelope in ("ListPage", "XrefPage", "ResolveAnswer"):
        schema = document["components"]["schemas"][envelope]
        assert "asOfApplied" in schema["properties"] and "asOfApplied" not in schema["required"]


def test_a_definition_with_events_documents_its_pull_feed():
    """A definition that declares events gets ``GET …/events`` (0.9 C10): the reserved names, its
    parameters without ``to.`` names (the pull feed takes no crosswalk), the event and page schemas
    with the object as get by ID answers it, and ``410``; one without events has no such path."""
    document = json.loads(STARTER.read_text())
    (definition,) = [item for item in document["consumerApis"] if item["key"] == "rdm"]
    del definition["operations"]["events"]
    model = parse_model(document)
    plain = consumer_openapi(
        model,
        consumer_api(model, "rdm"),
        root_path="",
        resolve_max_items=1000,
        token_url="/oauth/token",
    )
    assert f"{_base(consumer_api(model, 'rdm'))}/events" not in plain["paths"]

    definition["operations"]["events"] = {
        "custom": [
            {
                "key": "reference-data-changed",
                "objectTypes": definition["exposes"][:2],
                "changes": ["created", "deleted"],
            }
        ]
    }
    model = parse_model(document)
    built = consumer_openapi(
        model,
        consumer_api(model, "rdm"),
        root_path="",
        resolve_max_items=1000,
        token_url="/oauth/token",
    )
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
    document = consumer_openapi(
        model, rdm, root_path="", resolve_max_items=1000, token_url="/oauth/token"
    )
    xref = document["paths"][f"{_base(rdm)}/xref"]["get"]
    (size,) = [item for item in xref["parameters"] if item["name"] == "pageSize"]
    smallest, largest, default = consumer_lists.PAGE_SIZE
    assert size["schema"] == {
        "type": "integer",
        "minimum": smallest,
        "maximum": largest,
        "default": default,
    }
    assert f"at least {MIN_INDEXED_LENGTH} characters" in xref["description"]
    assert f"{consumer_xref.MATCH_LIMIT:,} records" in xref["description"]
    assert f"at most {consumer_xref.MAX_TERMS} terms" in xref["description"]


def test_each_exposed_type_has_its_own_schema_named_by_its_public_name():
    """``Object`` is a union of the types' schemas with a discriminator on ``objectType`` and no written
    mapping; a public name equal to one of the document's own schemas takes the ``Object_`` prefix and a
    mapping entry; each response holding objects names one example per type."""
    document = json.loads(STARTER.read_text())
    (definition,) = [item for item in document["consumerApis"] if item["key"] == "rdm"]
    definition["exposes"] = [item["key"] for item in document["objectTypes"]]
    definition["publicNames"] = {
        **definition.get("publicNames", {}),
        definition["exposes"][0]: "Object",
    }
    model = parse_model(document)
    rdm = consumer_api(model, "rdm")
    built = consumer_openapi(
        model, rdm, root_path="", resolve_max_items=1000, token_url="/oauth/token"
    )
    validate_openapi(built)
    schemas = built["components"]["schemas"]
    publics = {item.publicName for item in rdm.objectTypes.values()}
    assert "Object_Object" in schemas and publics - {"Object"} <= set(schemas)
    assert schemas["Object"]["discriminator"]["mapping"] == {
        "Object": "#/components/schemas/Object_Object"
    }
    for public in publics - {"Object"}:
        assert schemas[public]["properties"]["objectType"] == {"type": "string", "enum": [public]}
        assert schemas[public]["title"] == public
    base = _base(rdm)
    content = built["paths"][f"{base}/objects/{{id}}"]["get"]["responses"]["200"]["content"]
    assert set(content["application/json"]["examples"]) == publics
    for public, example in content["application/json"]["examples"].items():
        assert example["value"]["objectType"] == public
    lists = built["paths"][f"{base}/lists/codelists"]["get"]["responses"]["200"]["content"]
    assert set(lists["application/json"]["examples"]) == {"Codelist"}


def test_without_a_colliding_name_the_discriminator_has_no_mapping():
    model = load_model(STARTER)
    rdm = consumer_api(model, "rdm")
    built = consumer_openapi(
        model, rdm, root_path="", resolve_max_items=1000, token_url="/oauth/token"
    )
    assert built["components"]["schemas"]["Object"]["discriminator"] == {
        "propertyName": "objectType"
    }


def test_the_downloaded_schema_of_a_colliding_public_name_points_only_into_itself():
    """A type named like one of the document's own schemas is ``Object_<name>`` with a mapping entry; the
    standalone schema (what the editor downloads) relinks the mapping to ``$defs`` as it does every ``$ref``,
    so no pointer into ``#/components/`` is left, and an answer of that type validates against it."""
    from jsonschema import Draft202012Validator

    from app.engine.model.authoring.consumer_documents import object_schema
    from app.engine.model.consumer_examples import example_of

    document = json.loads(STARTER.read_text())
    (definition,) = [item for item in document["consumerApis"] if item["key"] == "rdm"]
    definition["exposes"] = [item["key"] for item in document["objectTypes"]]
    first = definition["exposes"][0]
    definition["publicNames"] = {**definition.get("publicNames", {}), first: "Event"}
    model = parse_model(document)
    rdm = consumer_api(model, "rdm")
    built = consumer_openapi(
        model, rdm, root_path="", resolve_max_items=1000, token_url="/oauth/token"
    )
    schema = object_schema(built, title="x")
    assert "#/components/" not in json.dumps(schema)
    mapping = schema["discriminator"]["mapping"]
    assert mapping == {"Event": "#/$defs/Object_Event"}
    assert all(target.removeprefix("#/$defs/") in schema["$defs"] for target in mapping.values())
    answer = example_of(schema, schema["$defs"], "", "Event")
    assert answer["objectType"] == "Event"
    Draft202012Validator(schema).validate(answer)


def test_an_example_of_a_type_is_chosen_by_name_through_allof_and_unions_whatever_their_order():
    """``ScoredObject`` is an ``allOf`` over the ``oneOf`` of the types: the example of a named type takes
    that type's branch there, in an ``anyOf`` beside it, and when the choices are listed the other way."""
    from app.engine.model.consumer_examples import example_of

    defs = {
        "A": {
            "type": "object",
            "properties": {"objectType": {"enum": ["A"]}, "a": {"type": "integer"}},
        },
        "B": {
            "type": "object",
            "properties": {"objectType": {"enum": ["B"]}, "b": {"type": "integer"}},
        },
        "Object": {"oneOf": [{"$ref": "#/$defs/A"}, {"$ref": "#/$defs/B"}]},
        "Scored": {
            "allOf": [
                {"$ref": "#/$defs/Object"},
                {"type": "object", "properties": {"matchScore": {"type": "integer"}}},
            ]
        },
    }
    for name in ("A", "B"):
        for schema in (
            {"$ref": "#/$defs/Scored"},
            {"anyOf": [{"$ref": "#/$defs/Scored"}, {"$ref": "#/$defs/Object"}]},
            {"anyOf": [{"$ref": "#/$defs/Object"}, {"$ref": "#/$defs/Scored"}]},
        ):
            assert example_of(schema, defs, "", name)["objectType"] == name
    defs["Object"]["oneOf"].reverse()
    assert example_of({"$ref": "#/$defs/Scored"}, defs, "", "A") == {
        "objectType": "A",
        "a": 1,
        "matchScore": 1,
    }


def test_every_schema_the_document_writes_itself_is_reserved_against_a_type_named_alike():
    """``_OWN_SCHEMAS`` is kept by hand: a schema the generator writes that is not a type's, a projection's
    or in it would let a public name overwrite it. Checked over a definition with events and one without."""
    from app.engine.model.consumer_openapi import _OWN_SCHEMAS, type_schema_names

    for with_events in (True, False):
        model = load_model(STARTER)
        rdm = consumer_api(model, "rdm")
        if not with_events:
            rdm = rdm.model_copy(update={"events": []})
        built = consumer_openapi(model, rdm, root_path="", resolve_max_items=10, token_url="/t")
        types = set(type_schema_names(rdm).values())
        own = {
            name for name in built["components"]["schemas"] if not name.startswith("Projection_")
        } - types
        assert own <= _OWN_SCHEMAS, own - _OWN_SCHEMAS
        if with_events:
            assert {"Event", "EventPage"} <= own, own


def test_the_holding_of_a_definition_is_kept_per_model_and_never_shared_between_releases():
    from app.engine.model.consumer_contract import type_holding

    first = load_model(STARTER)
    second = load_model(STARTER)
    one, other = consumer_api(first, "rdm"), consumer_api(second, "rdm")
    assert type_holding(first, one) is type_holding(first, one)
    assert type_holding(second, other) is not type_holding(first, one)
