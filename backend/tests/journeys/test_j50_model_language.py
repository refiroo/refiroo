"""J50.43 — The model language is in the API (USER_JOURNEYS.md § AI proposals, 0.16 AP11).

The OpenAPI document names the model's definitions where a model is read or written, so a client
(or an assistant) writes a model from them instead of probing the validator. Only the document
says so: at runtime the field stays an open object, so a wrong model still gets the compiler's
diagnostics with their JSON pointers.
"""

import copy

import pytest
from scenario import ok


def _resolve(schemas, node):
    """The definition a schema names, through ``$ref`` and a nullable ``anyOf``."""
    while True:
        if "$ref" in node:
            node = schemas[node["$ref"].rsplit("/", 1)[1]]
        elif "anyOf" in node:
            node = next(item for item in node["anyOf"] if item.get("type") != "null")
        else:
            return node


def _items(schemas, node):
    return _resolve(schemas, _resolve(schemas, node)["items"])


@pytest.mark.journey("J50.43")
@pytest.mark.structures("H", "K", "K.code", "Bcand")
def test_the_models_definitions_are_in_the_openapi_document_and_a_wrong_field_is_still_refused_with_its_pointer(
    world,
):
    """Given the API's OpenAPI document, when a client reads a model draft's ``model``, then it finds
    the definitions of types, relations and a binding's candidates; a model it writes from them with
    a candidate filter validates; a field no definition names in ``candidates`` is refused with its
    pointer."""
    document = ok(world.api.get("/openapi.json"))
    schemas = document["components"]["schemas"]
    path = document["paths"]["/api/v1/model-drafts"]["post"]
    body = path["requestBody"]["content"]["application/json"]["schema"]
    draft = _resolve(schemas, body)["properties"]["model"]
    model = _resolve(schemas, draft)
    assert model is schemas["EngineModel"]
    for part in ("objectTypes", "relationTypes", "objectTypeRelations"):
        assert _items(schemas, model["properties"][part])["properties"]
    binding = _items(schemas, model["properties"]["objectTypeRelations"])
    candidates = _resolve(schemas, binding["properties"]["candidates"])
    criterion = _items(schemas, candidates["properties"]["to"])
    assert {"field", "op", "value"} <= set(criterion["properties"])
    # The responses name it too.
    release = document["paths"]["/api/v1/model-releases/{release_id}"]["get"]["responses"]["200"]
    answer = _resolve(schemas, release["content"]["application/json"]["schema"])
    assert _resolve(schemas, answer["properties"]["model"]) is schemas["EngineModel"]

    bcand = world.key("Bcand")
    code = world.key("K.code")

    def with_criterion(criterion):
        found = copy.deepcopy(world.configuration.model)
        item = next(b for b in found["objectTypeRelations"] if b["relationTypeKey"] == bcand)
        item["candidates"] = {"to": [criterion]}
        found["release"]["version"] += "-language"
        return found, item

    written, _ = with_criterion({"field": code, "op": "contains", "value": "K"})
    assert ok(world.api.post("/model-validations", {"model": written}))["valid"] is True

    wrong, item = with_criterion({"field": code, "op": "contains", "value": "K", "sideways": 1})
    answer = ok(world.api.post("/model-validations", {"model": wrong}))
    assert answer["valid"] is False
    prefix = f"/objectTypeRelations/{wrong['objectTypeRelations'].index(item)}"
    assert [d["path"] for d in answer["diagnostics"]] == [f"{prefix}/candidates/to/0/sideways"]
