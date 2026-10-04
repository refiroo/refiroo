"""J25 — Define a consumer API in the model (USER_JOURNEYS.md)."""

import copy
import json

import pytest
from scenario import ok, refused

API = ("R", "R.u", "R.b", "R.dt", "K", "B1n")


def _model(world, suffix, **definition):
    model = copy.deepcopy(world.configuration.model)
    model["release"]["version"] += f"-{suffix}"
    return world.with_consumer_api(model, **definition)


def _compile(world, model):
    draft = ok(world.api.post("/model-drafts", {"name": "Consumer API", "model": model}), 201)
    compiled = ok(
        world.api.post(
            f"/model-drafts/{draft['id']}/compile", {"expectedVersion": draft["version"]}
        )
    )
    return draft, compiled


def _install(world, draft):
    return world.api.post(
        f"/model-drafts/{draft['id']}/installation", {"expectedVersion": draft["version"]}
    )


def _activate_definition(world, suffix, **definition):
    draft, _compiled = _compile(world, _model(world, suffix, **definition))
    release = ok(_install(world, draft), 201)
    ok(world.activate(release["id"]))
    return release


def _codes(compiled):
    return {d["code"] for d in compiled["consumerContracts"]["diagnostics"]}


@pytest.mark.journey("J25")
@pytest.mark.structures(*API)
def test_declare_validate_compare_and_activate_a_consumer_api(world):
    """Given a model with no consumer API. When a draft declares one and is compiled; a draft whose
    field reads an undeclared attribute is compiled and installed; the valid one installed and
    activated. Then the valid draft is compatible; the broken one is invalid at the field's JSON
    pointer, and installing it is refused with that pointer; the valid one activates. When a later
    draft removes an output field at the same contract version. Then compiling asks for a version,
    activation is refused leaving the selection, and with a higher version it activates."""
    _draft, compiled = _compile(world, _model(world, "api"))
    assert compiled["valid"] is True
    assert compiled["consumerContracts"]["classification"] == "compatible"

    broken = _model(world, "broken")
    broken["consumerApis"][-1]["object"]["attributes"]["number"]["source"] = ["no-such-attribute"]
    broken_draft, broken_compiled = _compile(world, broken)
    assert broken_compiled["valid"] is False
    pointer = "/consumerApis/journey-api/object/attributes/number/source"
    assert any(d["path"].startswith(pointer) for d in broken_compiled["diagnostics"]), (
        broken_compiled["diagnostics"]
    )
    error = refused(_install(world, broken_draft), 422, "INVALID_MODEL")
    assert pointer in json.dumps(error["details"])

    _activate_definition(world, "api")
    state = ok(world.api.get("/model-runtime-state"))
    draft, compiled = _compile(world, _model(world, "removed", drop_flag=True))
    assert compiled["consumerContracts"]["classification"] == "version_required"
    (diagnostic,) = [
        d
        for d in compiled["consumerContracts"]["diagnostics"]
        if d["code"] == "CONSUMER_CONTRACT_VERSION_REQUIRED"
    ]
    # A removed field has no place in the new document: the diagnostic points at its parent and
    # names it.
    assert diagnostic["path"].startswith("/consumerApis/journey-api/object")
    assert "flag" in diagnostic["path"] + diagnostic["message"], diagnostic
    release = ok(_install(world, draft), 201)
    refused(world.activate(release["id"]), 409, "CONSUMER_CONTRACT_VERSION_REQUIRED")
    assert ok(world.api.get("/model-runtime-state")) == state
    _activate_definition(world, "removed-v2", drop_flag=True, version=2)


@pytest.mark.journey("J25.1")
@pytest.mark.structures(*API)
def test_additions_are_compatible_and_removals_and_lower_versions_are_reported(world):
    """Given an active consumer API at contract version 2. When drafts add a field and a list, omit the
    whole API, or lower its contract version to 1. Then the first is compatible, the second compatible with a removal warning,
    the third reports the decreased version."""
    _activate_definition(world, "api", version=2)
    _draft, added = _compile(world, _model(world, "added", extra=True, version=2))
    assert added["consumerContracts"]["classification"] == "compatible"

    omitted = copy.deepcopy(world.configuration.model)
    omitted["release"]["version"] += "-omitted"
    _draft, without = _compile(world, omitted)
    assert without["consumerContracts"]["classification"] == "compatible"
    assert "CONSUMER_API_REMOVED" in _codes(without)

    _draft, lowered = _compile(world, _model(world, "lowered", version=1))
    assert "CONSUMER_CONTRACT_VERSION_DECREASED" in _codes(lowered) | {
        d["code"] for d in lowered["diagnostics"]
    }


@pytest.mark.journey("J25.2")
@pytest.mark.structures(*API)
def test_a_model_change_that_changes_a_projection_needs_a_new_version(world):
    """Given an active consumer API projecting over a one-to-many relationship from its many side (one
    related record each). When a draft makes that relationship many-to-many at the same contract
    version, and is compiled, compared and
    activated. Then a new version is required, naming the projection, and activation is refused."""
    active = _activate_definition(world, "api")
    model = _model(world, "wider")
    binding = next(
        b for b in model["objectTypeRelations"] if b["relationTypeKey"] == world.key("B1n")
    )
    binding["cardinality"] = "many-to-many"
    draft, compiled = _compile(world, model)
    assert compiled["consumerContracts"]["classification"] == "version_required"
    assert any(
        "projections/ledger" in d["path"] for d in compiled["consumerContracts"]["diagnostics"]
    )
    release = ok(_install(world, draft), 201)
    diff = ok(world.api.get(f"/model-releases/{release['id']}/diff", againstReleaseId=active["id"]))
    assert diff["consumerContracts"]["classification"] == "version_required"
    refused(world.activate(release["id"]), 409, "CONSUMER_CONTRACT_VERSION_REQUIRED")


@pytest.mark.journey("J25")
@pytest.mark.structures("Capi", "R", "R.u")
def test_the_identity_reads_the_object_id(world):
    """A definition whose id source is an attribute is refused with 422 INVALID_MODEL at
    /consumerApis/<key>/object/id/source."""
    model = copy.deepcopy(world.configuration.model)
    model["release"]["version"] += "-former-id"
    (definition,) = [d for d in model["consumerApis"] if d["key"] == world.key("Capi")]
    definition["object"]["id"]["source"] = [world.key("R.u")]
    draft, _compiled = _compile(world, model)
    error = refused(_install(world, draft), 422, "INVALID_MODEL")
    pointer = f"/consumerApis/{world.key('Capi')}/object/id/source"
    assert any(d["path"] == pointer for d in error["details"]), error["details"]


def _capi(model, world):
    (definition,) = [d for d in model["consumerApis"] if d["key"] == world.key("Capi")]
    return definition


def _capi_model(world, suffix):
    model = copy.deepcopy(world.configuration.model)
    model["release"]["version"] += f"-{suffix}"
    return model, _capi(model, world)


@pytest.mark.journey("J25")
@pytest.mark.structures("Capi", "R", "R.n", "K.code")
def test_a_list_sorts_by_a_scalar_attribute_of_its_type(world):
    """An unknown attribute, a JSON attribute and an attribute the list's type does not bind are each
    refused at /consumerApis/<key>/lists/<list>/sortBy. Changing sortBy is reported as
    version_required. A parameter named from, seek or includeTotal is refused as reserved."""
    pointer = f"/consumerApis/{world.key('Capi')}/lists/{world.key('Capi.all')}/sortBy"
    json_key = "consumer-notes"
    for sort_by in ("no-such-attribute", json_key, world.key("K.code")):
        model, definition = _capi_model(world, f"sort-{sort_by}")
        model["attributeTypes"].append({"key": json_key, "name": "Notes", "valueType": "json"})
        r_type = next(t for t in model["objectTypes"] if t["key"] == world.key("R"))
        r_type["attributes"].append({"attributeTypeKey": json_key, "order": 900})
        (all_,) = [item for item in definition["lists"] if item["key"] == world.key("Capi.all")]
        all_["sortBy"] = sort_by
        _draft, compiled = _compile(world, model)
        assert compiled["valid"] is False, sort_by
        assert any(d["path"] == pointer for d in compiled["diagnostics"]), compiled["diagnostics"]

    model, definition = _capi_model(world, "sort-name")
    (all_,) = [item for item in definition["lists"] if item["key"] == world.key("Capi.all")]
    del all_["sortBy"]
    _draft, compiled = _compile(world, model)
    assert compiled["consumerContracts"]["classification"] == "version_required"
    assert any(
        d["path"].startswith(f"/consumerApis/{world.key('Capi')}/lists")
        for d in compiled["consumerContracts"]["diagnostics"]
    )

    for name in ("from", "seek", "includeTotal"):
        model, definition = _capi_model(world, f"reserved-{name}")
        definition["parameters"][name] = {"kind": "objectType"}
        _draft, compiled = _compile(world, model)
        assert compiled["valid"] is False, name
        reserved = f"/consumerApis/{world.key('Capi')}/parameters/{name}"
        assert any(d["path"] == reserved for d in compiled["diagnostics"]), compiled["diagnostics"]


@pytest.mark.journey("J25")
@pytest.mark.structures("Capi", "R", "R.u", "K.code", "B11")
def test_contains_reads_text_only(world):
    """A contains weight on id, or on an integer attribute, is refused at its /match/…/contains
    pointer: it could never match."""
    number = "consumer-serial"
    base = f"/consumerApis/{world.key('Capi')}/match"
    for where in ("own-id", "own-integer", "promoted-id"):
        model, definition = _capi_model(world, f"contains-{where}")
        model["attributeTypes"].append(
            {"key": number, "name": "Serial", "valueType": "integer", "features": {"unique": True}}
        )
        r_type = next(t for t in model["objectTypes"] if t["key"] == world.key("R"))
        r_type["attributes"].append({"attributeTypeKey": number, "order": 900})
        if where == "promoted-id":
            definition["match"]["promoted"][0]["firstMatch"].append({"field": "id", "contains": 5})
            index = len(definition["match"]["promoted"][0]["firstMatch"]) - 1
            pointer = f"{base}/promoted/0/firstMatch/{index}/contains"
        else:
            field = "id" if where == "own-id" else number
            definition["match"]["own"].append({"field": field, "exact": 5, "contains": 5})
            pointer = f"{base}/own/{len(definition['match']['own']) - 1}/contains"
        draft, compiled = _compile(world, model)
        assert compiled["valid"] is False, where
        assert any(d["path"] == pointer for d in compiled["diagnostics"]), compiled["diagnostics"]
        error = refused(_install(world, draft), 422, "INVALID_MODEL")
        assert pointer in json.dumps(error["details"])
