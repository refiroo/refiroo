"""The ``model mappings`` and ``moves`` areas of the management API's reference, recorded from a run on the
guide's reference data (see ``test_reference_recording.py``, whose seed, scenario and normaliser this
file uses, and ``test_reference_model.py``, whose second model it installs).

The administrator of the Graubünden network's model also keeps the stop inventory of a canton, a second
model of its own. She saves its document as a draft, installs it, makes a workspace that runs it and
maps what a Graubünden stop becomes there: types and attributes by operations that she undoes and redoes,
and a second mapping that the inference proposes and she applies. Then she starts a move of some stops
into the inventory workspace and follows its job. The second mapping is deleted. Each step records the
main successful use of the operation it calls; the refusals the areas' text names are asserted without
being recorded. Every job is followed to its end.

    cd backend && RDM_RECORD_EXAMPLES=1 .venv/bin/python -m pytest tests/test_reference_mappings.py -q
"""

from collections.abc import Iterator

import pytest
import seeds
from test_reference_jobs import FINAL, JOB, _wait
from test_reference_model import DRAFT, ModelScenario, _until, _without_model, inventory_model
from test_reference_recording import RECORDING, SEED, _application, _register_seed

MAPPINGS = "/api/v1/model-mappings"
MAPPING = MAPPINGS + "/{key}"
KEY = {"key": "stops-to-inventory"}


@pytest.fixture(scope="module")
def mappings() -> Iterator[ModelScenario]:
    _register_seed()
    seeds.ensure(SEED)
    url = seeds.clone(SEED)
    try:
        with _application(url) as client:
            scenario = ModelScenario(client)
            yield scenario
            if RECORDING:
                scenario.write_examples()
    finally:
        seeds.drop(url.database)


def test_a_second_model_is_installed_and_run_by_a_workspace_of_its_own(mappings):
    s = mappings
    draft = s.call(
        "POST",
        "/api/v1/model-drafts",
        body={"name": "Stop inventory", "model": inventory_model()},
        status=201,
        record="fromADocument",
        summary="Save a model document of another model as a draft",
        shorten=_without_model,
    )
    assert draft["baseReleaseId"] is None
    release = s.call(
        "POST",
        DRAFT + "/installation",
        path={"draft_id": draft["id"]},
        body={"expectedVersion": draft["version"]},
        status=201,
    )
    workspace = s.call(
        "POST",
        "/api/v1/workspaces",
        body={"key": "inventory", "label": "Stop inventory", "modelReleaseId": release["id"]},
        status=201,
    )
    assert workspace["model"]["releaseKey"] == "stop-inventory"
    s.inventory_release = release

    # The mapping between the two models: created from the two workspaces, which name their releases.
    created = s.call(
        "POST",
        MAPPINGS,
        body={
            "key": "stops-to-inventory",
            "name": "Stops of Graubünden into the stop inventory",
            "sourceWorkspaceKey": "graubuenden",
            "targetWorkspaceKey": "inventory",
        },
        status=201,
        record="betweenTwoWorkspaces",
        summary="A mapping from the releases two workspaces run, with no type mapped yet",
    )
    assert created["version"] == 1 and created["types"] == []
    s.call(
        "POST",
        MAPPINGS,
        body={
            "key": "stops-to-inventory",
            "name": "Again",
            "sourceWorkspaceKey": "graubuenden",
            "targetWorkspaceKey": "inventory",
        },
        status=409,
        code="MODEL_MAPPING_EXISTS",
    )
    s.call(
        "POST",
        MAPPINGS,
        body={
            "key": "one-model",
            "name": "Both",
            "sourceWorkspaceKey": "graubuenden",
            "sourceReleaseId": release["id"],
            "targetWorkspaceKey": "inventory",
        },
        status=422,
        code="INVALID_MODEL_MAPPING",
    )
    s.mapping = created

    first = s.call(
        "POST",
        MAPPING + "/operations",
        path=KEY,
        body={
            "expectedVersion": created["version"],
            "operations": [
                {"kind": "mapType", "sourceType": "stop", "targetType": "stop-point"},
                {
                    "kind": "mapAttribute",
                    "sourceType": "stop",
                    "attribute": "stop-number",
                    "target": "stop-number",
                },
                {"kind": "setValueMap", "name": "dates", "values": {"?": None, "n/a": None}},
                {
                    "kind": "mapAttribute",
                    "sourceType": "stop",
                    "attribute": "valid-from",
                    "target": "opened",
                    "valueMap": "dates",
                },
            ],
        },
        status=200,
        record="aStopBecomesAStation",
        summary="Map the stop type to the stop point type, with its number and its first date",
    )
    assert first["problems"] == [] and len(first["entries"]) == 4
    s.call(
        "POST",
        MAPPING + "/operations",
        path=KEY,
        body={
            "expectedVersion": created["version"],
            "operations": [{"kind": "mapType", "sourceType": "stop", "targetType": "nothing"}],
        },
        status=409,
        code="VERSION_CONFLICT",
    )
    s.call(
        "POST",
        MAPPING + "/operations",
        path=KEY,
        body={
            "expectedVersion": first["version"],
            "operations": [{"kind": "mapType", "sourceType": "stop", "targetType": "nothing"}],
        },
        status=422,
        code="INVALID_OPERATION",
    )
    second = s.call(
        "POST",
        MAPPING + "/operations",
        path=KEY,
        body={
            "expectedVersion": first["version"],
            "operations": [
                {
                    "kind": "setMatch",
                    "sourceType": "stop",
                    "match": {"attributeTypeKey": "stop-number"},
                },
                {"kind": "setDefault", "sourceType": "stop", "attribute": "platforms", "value": 1},
            ],
        },
        status=200,
    )
    s.call(
        "POST",
        MAPPING + "/undo",
        path=KEY,
        body={"expectedVersion": second["version"], "step": 1},
        status=409,
        code="OPERATION_HAS_DEPENDANTS",
    )
    undone = s.call(
        "POST",
        MAPPING + "/undo",
        path=KEY,
        body={"expectedVersion": second["version"]},
        status=200,
        record="latestStep",
        summary="Undo the latest step: the default and the match go",
    )
    assert {e["origin"]["type"] for e in undone["entries"]} == {"undo"}
    redone = s.call(
        "POST",
        MAPPING + "/redo",
        path=KEY,
        body={"expectedVersion": undone["version"]},
        status=200,
        record="latestStep",
        summary="Redo it",
    )
    s.call(
        "POST",
        MAPPING + "/redo",
        path=KEY,
        body={"expectedVersion": redone["version"]},
        status=409,
        code="NOTHING_TO_REDO",
    )
    s.version = redone["version"]
    page = s.call(
        "GET",
        MAPPINGS,
        query={"sourceModelKey": "guide-reference-swiss", "pageSize": 2},
        status=200,
        record="ofTheGuideModel",
        summary="The mappings out of the guide model, in key order",
    )
    assert [item["key"] for item in page["items"]] == ["stops-to-inventory"]
    read = s.call(
        "GET",
        MAPPING,
        path=KEY,
        query={"sourceWorkspaceKey": "graubuenden", "targetWorkspaceKey": "inventory"},
        status=200,
        record="againstTheWorkspaces",
        summary="The mapping with its problems and what it leaves unmapped, as the workspaces run",
    )
    assert read["problems"] == [] and read["types"][0]["target"] == "stop-point"
    assert read["types"][0]["match"] == {"attributeTypeKey": "stop-number"}
    s.call("GET", MAPPING, path={"key": "nothing"}, status=404, code="MODEL_MAPPING_NOT_FOUND")
    history = s.call(
        "GET",
        MAPPING + "/operations",
        path=KEY,
        query={"pageSize": 2},
        status=200,
        record="firstPage",
        summary="The first two operations of the mapping's history, in the order they were written",
    )
    assert [e["kind"] for e in history["items"]] == ["mapType", "mapAttribute"]
    s.mapping = read


def test_a_mapping_is_proposed_by_an_inference_and_a_move_is_started_and_followed(mappings):
    s = mappings
    spare = {"key": "stops-proposed"}
    s.call(
        "POST",
        MAPPINGS,
        body={
            "key": "stops-proposed",
            "name": "Stops, proposed",
            "sourceWorkspaceKey": "graubuenden",
            "targetWorkspaceKey": "inventory",
        },
        status=201,
    )
    started = s.call(
        "POST",
        MAPPING + "/inference",
        path=spare,
        body={"sourceWorkspaceKey": "graubuenden", "targetWorkspaceKey": "inventory"},
        status=202,
        record="betweenTwoWorkspaces",
        summary="Propose the mapping from the two releases and the two workspaces' records",
    )
    assert started["state"] == "checking"
    finished = _until(s, MAPPING + "/inference", spare, ("checking",))
    assert finished["state"] == "completed", finished
    s.call("GET", MAPPING + "/inference", path=KEY, status=404, code="INFERENCE_NOT_FOUND")
    inference = s.call(
        "GET",
        MAPPING + "/inference",
        path=spare,
        status=200,
        record="completed",
        summary="The inference finished: its proposals by status",
    )
    assert inference["counts"]["open"] == 4
    proposals = s.call(
        "GET",
        MAPPING + "/inference/proposals",
        path=spare,
        query={"sourceType": "stop", "pageSize": 2},
        status=200,
        record="ofTheStopType",
        summary="The proposals for the stop type: the target type, then what depends on it",
    )
    (proposal,) = proposals["items"]
    assert proposal["kind"] == "type" and proposal["target"] == "stop-point"
    applied = s.call(
        "POST",
        MAPPING + "/inference/application",
        path=spare,
        body={"expectedVersion": 1, "proposals": [proposal["id"]]},
        status=200,
        record="theStopProposal",
        summary="Apply the proposal for the stop type as a step of the mapping",
    )
    assert applied["entries"][0]["origin"]["type"] == "proposal"
    s.call(
        "DELETE",
        MAPPING,
        path=spare,
        query={"expectedVersion": applied["version"] - 1},
        status=409,
        code="VERSION_CONFLICT",
    )
    s.call(
        "DELETE",
        MAPPING,
        path=spare,
        query={"expectedVersion": applied["version"]},
        status=204,
        record="spare",
        summary="Delete the spare mapping with its history and proposals",
    )
    s.call("GET", MAPPING, path=spare, status=404, code="MODEL_MAPPING_NOT_FOUND")

    mapping = s.mapping
    request = {
        "sourceWorkspaceKey": "graubuenden",
        "targetWorkspaceKey": "inventory",
        "mapping": {"key": mapping["key"], "expectedVersion": mapping["version"]},
        "selection": {
            "types": [
                {
                    "objectTypeKey": "stop",
                    "where": [{"field": "stop-number", "op": "gte", "value": 8511000}],
                }
            ]
        },
    }
    s.call(
        "POST",
        "/api/v1/moves",
        body={**request, "targetWorkspaceKey": "graubuenden"},
        status=422,
        code="MOVE_SAME_WORKSPACE",
    )
    s.call(
        "POST",
        "/api/v1/moves",
        body={**request, "mapping": {**request["mapping"], "expectedVersion": 1}},
        status=409,
        code="MOVE_MAPPING_CHANGED",
    )
    job = s.call(
        "POST",
        "/api/v1/moves",
        body=request,
        status=202,
        record="someStops",
        summary="Queue the dry run of a move of the stops numbered from 8511000 into the inventory",
    )
    assert job["kind"] == "move"
    waiting = _wait(s, job["id"], "awaiting_confirmation", *FINAL)
    assert waiting["state"] == "awaiting_confirmation", waiting
    summary = waiting["move"]
    assert summary["counts"]["create"] == 4 and summary["counts"]["refused"] == 0, summary
    s.call(
        "POST",
        JOB + "/confirm",
        path={"job_id": job["id"]},
        status=202,
    )
    done = _wait(s, job["id"])
    assert done["state"] == "completed", done
    assert done["changeSetId"]
