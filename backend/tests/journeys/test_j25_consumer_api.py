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
    broken["consumerApis"][0]["object"]["attributes"]["number"]["source"] = ["no-such-attribute"]
    broken_draft, broken_compiled = _compile(world, broken)
    assert broken_compiled["valid"] is False
    pointer = "/consumerApis/journey-api/object/attributes/number/source"
    assert any(d["path"].startswith(pointer) for d in broken_compiled["diagnostics"]), (
        broken_compiled["diagnostics"]
    )
    error = refused(_install(world, broken_draft), 422, "invalid_model")
    assert pointer in json.dumps(error["details"])

    _activate_definition(world, "api")
    state = ok(world.api.get("/model-runtime-state"))
    draft, compiled = _compile(world, _model(world, "removed", drop_flag=True))
    assert compiled["consumerContracts"]["classification"] == "version_required"
    (diagnostic,) = [
        d
        for d in compiled["consumerContracts"]["diagnostics"]
        if d["code"] == "consumer_contract_version_required"
    ]
    # A removed field has no place in the new document: the diagnostic points at its parent and
    # names it.
    assert diagnostic["path"].startswith("/consumerApis/journey-api/object")
    assert "flag" in diagnostic["path"] + diagnostic["message"], diagnostic
    release = ok(_install(world, draft), 201)
    refused(world.activate(release["id"]), 409, "consumer_contract_version_required")
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
    assert "consumer_api_removed" in _codes(without)

    _draft, lowered = _compile(world, _model(world, "lowered", version=1))
    assert "consumer_contract_version_decreased" in _codes(lowered) | {
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
    refused(world.activate(release["id"]), 409, "consumer_contract_version_required")
