"""J20 — Discover the model and the API (USER_JOURNEYS.md)."""

import re

import pytest
from scenario import W1, ok, refused

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
    page and the OpenAPI document. Then the capabilities name the three groups with their flags,
    limits and settings; the model names its release; the placements give each application's
    top-level types and per type its children and possible types; each collection walks every item
    once; the relationship type lists its pairs with cardinality and whether required; every
    identifier is a UUID and none is a number."""
    capabilities = ok(world.api.get("/capabilities"))
    assert set(capabilities) == {"modelAdmin", "workspaceAdmin", "integrationJobs"}
    assert all("setting" in group for group in capabilities.values())
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
        ok(world.api.get("/model-runtime-state")),
        ok(world.api.get("/model-releases")),
        ok(world.api.get(f"/workspaces/{W1}/change-sets")),
    ]
    found = [value for value in _identifiers(samples, []) if value is not None]
    assert found and all(isinstance(value, str) and UUID4.match(value) for value in found), found

    docs = world.api.get("/docs")
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
        "invalid_cursor",
    )
    p1 = world.publish(world.change_set())
    refused(
        world.api.get("/model", changeSetId=c2["id"], publicationId=p1["id"]),
        422,
        "mutually_exclusive_context",
    )
    refused(
        world.api.get("/model", changeSetId="00000000-0000-4000-8000-000000000000"),
        404,
        "change_set_not_found",
    )


@pytest.mark.journey("J20.2")
@pytest.mark.structures("R")
def test_read_the_releases(world):
    """When the releases are listed, the active one, a release's detail and the runtime state read.
    Then the list pages the installed releases, the active filter returns only M1, the detail omits
    its model unless asked, and the runtime state names M1 and its version."""
    state = ok(world.api.get("/model-runtime-state"))
    model, _key = world.candidate("compatible")
    candidate = world.install(model)["id"]
    installed = [r["id"] for r in _walk(world, "/model-releases")]
    assert sorted(installed) == sorted([state["activeReleaseId"], candidate])
    active = ok(world.api.get("/model-releases", active=True))["items"]
    assert [r["id"] for r in active] == [state["activeReleaseId"]]
    assert "model" not in ok(world.api.get(f"/model-releases/{candidate}"))
    assert ok(world.api.get(f"/model-releases/{candidate}", includeModel=True))["model"]
    assert state["version"] >= 1 and UUID4.match(state["activeReleaseId"])
