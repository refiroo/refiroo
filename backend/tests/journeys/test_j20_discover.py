"""J20 — Discover the model and the API (USER_JOURNEYS.md)."""

import copy
import json
import re

import pytest
from openapi_schema_validator import OAS31Validator
from openapi_spec_validator import validate as validate_openapi
from scenario import (
    W1,
    consumer_list,
    consumer_object,
    consumer_publications,
    consumer_resolve,
    consumer_xref,
    ok,
    refused,
)

UUID4 = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$")


def _walk(world, path, **params):
    items, cursor = [], None
    while True:
        page = ok(world.api.get(path, pageSize=1, cursor=cursor, **params))
        items += page["items"]
        cursor = page.get("nextCursor")
        if not cursor:
            return items


def _identifiers(value, found):
    """Every value under an ``id`` or ``…Id`` key, anywhere in a response."""
    if isinstance(value, dict):
        for key, item in value.items():
            if (key == "id" or key.endswith("Id")) and not isinstance(item, (dict, list)):
                found.append(item)
            _identifiers(item, found)
    elif isinstance(value, list):
        for item in value:
            _identifiers(item, found)
    return found


@pytest.mark.journey("J20")
@pytest.mark.structures("R", "H", "K", "Bnn")
def test_read_capabilities_model_placements_and_metadata(world):
    """When the integrator reads the capabilities, the model, the placements and every metadata
    collection one item a page, a type, a relationship type's pairs, an attribute type, the reference
    page and the OpenAPI document. Then the capabilities name the four gated groups with their flags,
    limits and settings, the change feed's retention and the consumer batch resolve maximum; the model names its release; the placements give each application's
    top-level types and per type its children and possible types; each collection walks every item
    once; the relationship type lists its pairs with cardinality and whether required; every
    identifier is a UUID and none is a number."""
    capabilities = ok(world.api.get("/capabilities"))
    gated = {"modelAdmin", "workspaceAdmin", "integrationJobs", "consumerSubscriptions"}
    assert set(capabilities) == gated | {"changeFeed", "consumerApi"}
    assert all("setting" in capabilities[group] for group in gated)
    assert capabilities["changeFeed"]["retentionDays"] >= 1
    assert capabilities["consumerApi"]["resolveMaxItems"] >= 1
    assert {"batchMaxItems", "batchMaxBytes"} <= set(capabilities["integrationJobs"]["limits"])

    model = world.api.get("/model")
    assert (
        model.status_code == 200 and model.headers["ETag"] and model.headers["X-Model-Release-Id"]
    )
    placements = ok(world.api.get("/model/placements"))
    applications = (
        {
            a["applicationKey"] if "applicationKey" in a else a.get("key"): a
            for a in placements.get("applications", placements.get("items", []))
        }
        if isinstance(placements, dict)
        else {}
    )
    assert applications, placements
    first = applications[world.app("H")]
    assert world.key("H") in first["topLevelObjectTypeKeys"]
    parents = {p["objectTypeKey"]: p for p in first["parents"]}
    assert world.key("H") in parents[world.key("H")]["childObjectTypeKeys"]
    assert "possibleObjectTypeKeys" in parents[world.key("H")]

    declared = world.configuration.model
    for path, collection, key in (
        ("/applications", "applications", "key"),
        ("/object-types", "objectTypes", "key"),
        ("/relation-types", "relationTypes", "key"),
        ("/attribute-types", "attributeTypes", "key"),
    ):
        walked = [item[key] for item in _walk(world, path)]
        assert sorted(walked) == sorted(item["key"] for item in declared[collection])
    assert ok(world.api.get(f"/object-types/{world.key('H')}"))["key"] == world.key("H")
    assert ok(world.api.get(f"/attribute-types/{world.key('H.code')}"))["key"] == world.key(
        "H.code"
    )
    relation_type = ok(world.api.get(f"/relation-types/{world.key('Bnn')}"))
    pairs = relation_type["allowedPairs"]
    assert pairs and all({"cardinality", "required"} <= set(pair) for pair in pairs)
    from_h = ok(
        world.api.get("/object-type-relations", fromObjectType=world.key("H"), pageSize=100)
    )
    assert world.key("Bnn") in {item["relationTypeKey"] for item in from_h["items"]}

    record = world.made("R", "Identified")
    samples = [
        record,
        world.workspace_model(),
        ok(world.api.get("/model-releases")),
        ok(world.api.get(f"/workspaces/{W1}/change-sets")),
    ]
    found = [value for value in _identifiers(samples, []) if value is not None]
    assert found and all(isinstance(value, str) and UUID4.match(value) for value in found), found

    docs = world.api.get("/docs/api")
    assert docs.status_code == 200 and "text/html" in docs.headers["content-type"]
    assert "openapi" in ok(world.api.get("/openapi.json"))


@pytest.mark.journey("J20.1")
@pytest.mark.structures("R")
def test_discover_the_model_of_a_change_set_on_another_release(world):
    """Given change set C2 pinned to candidate M2, which adds a type. When the model, the types and
    the placements are read in C2, and a live metadata cursor reused there. Then they answer M2's
    model with the added type; the reused cursor, two contexts at once and an unknown change set are
    refused."""
    model, _key = world.candidate("compatible")
    release = world.install(model)["id"]
    c2 = world.change_set(modelReleaseId=release)
    added = f"{world.key('R')}-added-type"

    read = world.api.get("/model", changeSetId=c2["id"])
    assert read.headers["X-Model-Release-Id"] == release
    assert added in {t["key"] for t in ok(read)["objectTypes"]}
    types = ok(world.api.get("/object-types", changeSetId=c2["id"], pageSize=100))["items"]
    assert added in {t["key"] for t in types}
    placements = ok(world.api.get("/model/placements", changeSetId=c2["id"]))
    assert added in str(placements)
    assert added not in {
        t["key"] for t in ok(world.api.get("/object-types", pageSize=100))["items"]
    }

    live = ok(world.api.get("/object-types", pageSize=1))
    refused(
        world.api.get("/object-types", pageSize=1, cursor=live["nextCursor"], changeSetId=c2["id"]),
        422,
        "INVALID_CURSOR",
    )
    p1 = world.publish(world.change_set())
    refused(
        world.api.get("/model", changeSetId=c2["id"], publicationId=p1["id"]),
        422,
        "MUTUALLY_EXCLUSIVE_CONTEXT",
    )
    refused(
        world.api.get("/model", changeSetId="00000000-0000-4000-8000-000000000000"),
        404,
        "CHANGE_SET_NOT_FOUND",
    )


@pytest.mark.journey("J20.2")
@pytest.mark.structures("R")
def test_read_the_releases(world):
    """When the releases are listed, the active one, a release's detail and the runtime state read.
    Then the list pages the installed releases, the active filter returns only M1, the detail omits
    its model unless asked, and the runtime state names M1 and its version."""
    state = world.workspace_model()
    model, _key = world.candidate("compatible")
    candidate = world.install(model)["id"]
    installed = [r["id"] for r in _walk(world, "/model-releases")]
    assert sorted(installed) == sorted([state["releaseId"], candidate])
    active = ok(world.api.get("/model-releases", assigned=True))["items"]
    assert [r["id"] for r in active] == [state["releaseId"]]
    assert "model" not in ok(world.api.get(f"/model-releases/{candidate}"))
    assert ok(world.api.get(f"/model-releases/{candidate}", includeModel=True))["model"]
    assert state["version"] >= 1 and UUID4.match(state["releaseId"])


# --- the consumer APIs' documents (C6b) ----------------------------------------------------------

CAPI = (
    "Capi",
    "R",
    "R2",
    "R.u",
    "R2.u",
    "R.b",
    "R.n",
    "R.dt",
    "K",
    "K.code",
    "B11",
    "Bown",
    "Bscope",
    "G",
    "M",
    "D",
    "B1n",
)


def _index(world, **params):
    return world.api.get("/api/consumer", **params)


def _activate(world, model, suffix):
    model["release"]["version"] += f"-{suffix}"
    ok(world.activate(world.install(model)["id"]))


def _every_entry(world):
    entries, cursor = [], None
    while True:
        page = ok(_index(world, pageSize=1, cursor=cursor))
        entries += page["items"]
        cursor = page["nextCursor"]
        if not cursor:
            return entries


@pytest.mark.journey("J20.3")
@pytest.mark.structures(*CAPI)
def test_the_consumer_api_index(world):
    """The index lists the configuration's definition with its consumerApi, name, contractVersion and
    an openapi URL that answers 200. A release adding a second definition lists both, in key order,
    paging with pageSize=1; a release removing it lists one again. A page size of 0 is 400
    INVALID_PAGE_SIZE. A matching If-None-Match is 304."""
    capi = world.key("Capi")
    response = _index(world)
    (entry,) = ok(response)["items"]
    assert entry == {
        "consumerApi": capi,
        "name": "Capi",
        "contractVersion": 1,
        "openapi": f"/api/consumer/{capi}/v1/openapi.json",
    }
    assert ok(world.api.get(entry["openapi"]))["info"]["version"] == "1"
    unchanged = world.api.client.get(
        "/api/consumer", headers={"If-None-Match": response.headers["ETag"]}
    )
    assert unchanged.status_code == 304

    _activate(world, world.with_consumer_api(copy.deepcopy(world.configuration.model)), "second")
    entries = _every_entry(world)
    assert [item["consumerApi"] for item in entries] == sorted([capi, "journey-api"])
    second = next(item for item in entries if item["consumerApi"] == "journey-api")
    assert second["name"] == "Journey API"
    assert ok(world.api.get(second["openapi"]))["info"]["title"] == "Journey API"
    assert ok(_index(world, includeTotal="true"))["totalCount"] == 2

    _activate(world, copy.deepcopy(world.configuration.model), "without")
    assert [item["consumerApi"] for item in _every_entry(world)] == [capi]
    refused(_index(world, pageSize=0), 400, "INVALID_PAGE_SIZE")


def _conforms(document, path, method, answer):
    """``answer`` validates against the document's ``200`` schema of the operation."""
    schema = document["paths"][path][method]["responses"]["200"]["content"]["application/json"][
        "schema"
    ]
    OAS31Validator({**schema, "components": document["components"]}).validate(answer)


@pytest.mark.journey("J20.4")
@pytest.mark.structures(*CAPI)
def test_a_consumer_apis_document(world):
    """info.version is the contract version and info.title the name. Every path is literal, one per
    list, none holding {consumerApi} or {contractVersion}, and the document is valid OpenAPI 3.1. A
    real answer of get by ID, a list page, XREF (any, and one with to.), batch resolve and the
    publications list each validates against its documented 200 schema. A definition parameter
    appears on the routes that apply it, with style form; the targetable one's to. name appears; the
    contains and 10,000-match limits appear in XREF's description. After a release raising the
    version to 2, v2's document has info.version "2" and v2 in every path, and v1's is 404
    CONTRACT_VERSION_NOT_FOUND."""
    capi = world.key("Capi")
    base = f"/api/consumer/{capi}/v1"
    document = ok(world.api.get(f"{base}/openapi.json"))
    validate_openapi(document)
    assert document["openapi"].startswith("3.1")
    assert (document["info"]["title"], document["info"]["version"]) == ("Capi", "1")
    lists = [world.key(f"Capi.{name}") for name in ("all", "entries", "permits", "rates", "fees")]
    assert set(document["paths"]) == {
        f"{base}/xref",
        f"{base}/objects/{{id}}",
        f"{base}/resolve",
        f"{base}/publications",
        *(f"{base}/lists/{key}" for key in lists),
    }
    assert not any(
        "{consumerApi}" in path or "{contractVersion}" in path for path in document["paths"]
    )

    xref = document["paths"][f"{base}/xref"]["get"]
    parameters = {item["name"]: item for item in xref["parameters"]}
    token, watch = world.key("Capi.token"), world.key("Capi.watch")
    assert parameters[token]["style"] == "form"
    assert f"to.{watch}" in parameters
    assert {"query", "expect", "workspace", "publication"} <= set(parameters)
    assert "3 characters" in xref["description"] and "10,000" in xref["description"]
    entries = document["paths"][f"{base}/lists/{lists[1]}"]["get"]
    assert world.key("Capi.entries.parent") in {item["name"] for item in entries["parameters"]}
    by_id = document["paths"][f"{base}/objects/{{id}}"]["get"]
    assert token in {item["name"] for item in by_id["parameters"]}
    assert "pageSize" not in {item["name"] for item in by_id["parameters"]}

    north = world.made("G", "Region north", values={"K.code": "GN"})
    ledger = world.made(
        "R", "Documented ledger", values={"R.u": "DOC-1", "R.n": 7, "R.dt": "2026-01-02"}
    )
    other = world.made("R", "Desk owner", values={"R.u": "OWN-1"})
    desk = world.made(
        "D",
        "North desk",
        parent=world.dependant_parent(north["id"]),
        relations=[world.owner("Bown", other["id"])],
    )
    ok(world.relate("Bscope", ledger["id"], desk["id"]), 201)
    token_record = world.made("K", "Documented token", values={"K.code": "TK-D"})
    ok(world.relate("B11", ledger["id"], token_record["id"]), 201)
    world.made("R2", "Documented entry", parent=ledger["id"], values={"R2.u": "DOC-E"})
    world.publish(world.change_set())

    to = f"to.{watch}"
    _conforms(document, f"{base}/objects/{{id}}", "get", ok(consumer_object(world, ledger["id"])))
    _conforms(
        document,
        f"{base}/objects/{{id}}",
        "get",
        ok(consumer_object(world, ledger["id"], **{to: "Region north"})),
    )
    _conforms(
        document,
        f"{base}/lists/{lists[0]}",
        "get",
        ok(consumer_list(world, lists[0], includeTotal="true")),
    )
    _conforms(
        document,
        f"{base}/lists/{lists[1]}",
        "get",
        ok(consumer_list(world, lists[1], **{to: "Region north"})),
    )
    _conforms(document, f"{base}/xref", "get", ok(consumer_xref(world, query="Documented")))
    _conforms(
        document,
        f"{base}/xref",
        "get",
        ok(consumer_xref(world, query="DOC-1", expect="one", **{to: "Region north"})),
    )
    answer = ok(
        consumer_resolve(
            world, {"items": [{"query": "DOC-1"}, {"query": "nothing-like-it"}, {"id": "x"}]}
        )
    )
    _conforms(document, f"{base}/resolve", "post", answer)
    _conforms(document, f"{base}/publications", "get", ok(consumer_publications(world)))

    model = copy.deepcopy(world.configuration.model)
    (definition,) = [item for item in model["consumerApis"] if item["key"] == capi]
    definition["contractVersion"] = 2
    _activate(world, model, "v2")
    raised = ok(world.api.get(f"/api/consumer/{capi}/v2/openapi.json"))
    validate_openapi(raised)
    assert raised["info"]["version"] == "2"
    assert all(path.startswith(f"/api/consumer/{capi}/v2/") for path in raised["paths"])
    error = refused(world.api.get(f"{base}/openapi.json"), 404, "CONTRACT_VERSION_NOT_FOUND")
    assert error["details"]["contractVersion"] == 2


def _reference_sources(world, **params):
    """The sources the API reference page at ``/docs/api`` gives Scalar."""
    page = world.api.get("/docs/api", **params)
    assert page.status_code == 200, page.text
    match = re.search(r'Scalar\.createApiReference\("#rdm-api-reference", (\{.*\})\);', page.text)
    assert match, page.text
    return json.loads(match.group(1))["sources"]


@pytest.mark.journey("J20.5")
@pytest.mark.structures(*CAPI)
def test_the_api_reference_lists_the_consumer_apis(world):
    """The reference page's sources are the management API, then one per consumer API of the active
    release, in consumerApi order, labelled "{name} · v{contractVersion}", each at the URL the API
    index names, which answers 200. A link to a source (Scalar's ?api={slug}) opens the page. A release adding a definition adds its source; one removing it
    removes it; one raising Capi to version 2 shows v2 in the label, in every path and in
    info.version, and the v1 document answers 404."""
    capi = world.key("Capi")
    management, consumer = _reference_sources(world)
    assert management == {
        "title": "Management API",
        "slug": "management",
        "url": "/openapi.json",
        "default": True,
    }
    assert consumer == {
        "title": "Capi · v1",
        "slug": f"consumer-{capi}-v1",
        "url": f"/api/consumer/{capi}/v1/openapi.json",
    }
    assert [consumer["url"]] == [entry["openapi"] for entry in ok(_index(world))["items"]]
    assert ok(world.api.get(consumer["url"]))["info"]["title"] == "Capi"
    assert _reference_sources(world, api=consumer["slug"]) == [management, consumer]

    _activate(world, world.with_consumer_api(copy.deepcopy(world.configuration.model)), "second")
    sources = _reference_sources(world)[1:]
    assert [source["url"] for source in sources] == [
        entry["openapi"] for entry in _every_entry(world)
    ]
    assert {source["title"] for source in sources} == {"Capi · v1", "Journey API · v1"}
    for source in sources:
        ok(world.api.get(source["url"]))

    model = copy.deepcopy(world.configuration.model)
    (definition,) = [item for item in model["consumerApis"] if item["key"] == capi]
    definition["contractVersion"] = 2
    _activate(world, model, "v2")
    (_, raised) = _reference_sources(world)
    assert raised["title"] == "Capi · v2"
    assert raised["url"] == f"/api/consumer/{capi}/v2/openapi.json"
    document = ok(world.api.get(raised["url"]))
    assert document["info"]["version"] == "2"
    assert all(path.startswith(f"/api/consumer/{capi}/v2/") for path in document["paths"])
    refused(
        world.api.get(f"/api/consumer/{capi}/v1/openapi.json"), 404, "CONTRACT_VERSION_NOT_FOUND"
    )


@pytest.mark.journey("J20.6")
@pytest.mark.structures("Capi")
def test_a_consumer_api_definition_expanded(world):
    """Given Capi written with its defaults left out and an event per exposed type. When an integrator
    reads it expanded. Then every exposed type has its public name, the operations are listed, the
    events perType makes are written out as events of their own, every filter that matches has its
    matchOn and every list within a filter its types; the read carries the model's ETag. An unknown
    definition is 404 CONSUMER_API_NOT_FOUND."""
    capi = world.key("Capi")
    model = copy.deepcopy(world.configuration.model)
    model["release"]["version"] += "-expanded"
    (definition,) = [item for item in model["consumerApis"] if item["key"] == capi]
    container = world.key("Capi.container")
    del definition["filters"][container]["matchOn"]
    definition["operations"]["events"] = {"perType": True}
    # The event keys perType makes are the type keys, which must then be URL keys too.
    url_keys = all(re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", key) for key in definition["exposes"])
    if not url_keys:
        draft = ok(world.api.post("/model-drafts", {"name": "Expanded", "model": model}), 201)
        compiled = ok(
            world.api.post(
                f"/model-drafts/{draft['id']}/compile", {"expectedVersion": draft["version"]}
            )
        )
        assert [d["path"] for d in compiled["diagnostics"]] == [
            f"/consumerApis/{capi}/operations/events/perType"
        ]
        definition["operations"]["events"] = {
            "custom": [
                {"key": "every", "objectTypes": definition["exposes"], "changes": ["created"]}
            ]
        }
    ok(world.activate(world.install(model)["id"]))

    response = world.api.get(f"/model/consumer-apis/{capi}")
    expanded = ok(response)
    assert response.headers["ETag"] == world.api.get("/model").headers["ETag"]
    assert expanded["exposes"] == definition["exposes"]
    assert expanded["publicNames"] == definition["publicNames"]
    assert set(expanded["operations"]) == {"objects", "xref", "resolve", "lists", "events"}
    events = expanded["operations"]["events"]
    assert events["perType"] is False
    if url_keys:
        assert events["custom"] == [
            {
                "key": f"{key}-changed",
                "objectTypes": [key],
                "changes": ["created", "updated", "deleted"],
            }
            for key in definition["exposes"]
        ]
    filters = expanded["filters"]
    assert filters[container] == {"under": [world.key("M")], "matchOn": ["id", "name"]}
    assert all("matchOn" in item for item in filters.values() if "byType" not in item)
    assert all(
        "types" in item["within"]
        for item in expanded["operations"]["lists"].values()
        if "within" in item
    )
    assert expanded["object"]["fields"][world.key("Capi.id")] == {"role": "id", "from": ["id"]}
    refused(world.api.get("/model/consumer-apis/no-such-api"), 404, "CONSUMER_API_NOT_FOUND")
