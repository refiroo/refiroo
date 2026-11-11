"""The ``relations``, ``mapping`` and ``relation-matrix`` areas of the management API's reference, recorded
from a run on the guide's reference data (see ``test_reference_recording.py``, whose seed, scenario and
normaliser this file uses).

An integrator who maintains the Graubünden timetable data changes the relationships of stops (a mode
that serves one, the operator and its inspection values), maps the codes of other systems to
municipalities and reads the relationship views, the grid and the two matrices. Each step records the
main successful use of the operation it calls; the refusals the areas' text names are asserted without
being recorded. The relationship attribute values the reference set holds are not in the ``docs`` set,
so the scenario sets them through the API.

    cd backend && RDM_RECORD_EXAMPLES=1 .venv/bin/python -m pytest tests/test_reference_relations.py -q
"""

import os
from collections.abc import Iterator

import pytest
import seeds
from test_reference_recording import (
    RECORDING,
    SEED,
    Scenario,
    _application,
    _register_seed,
)
from test_reference_records import _one

RELATIONS = "/api/v1/relations"
ONE = "/api/v1/relations/{relation_id}"
WS = "/api/v1/workspaces/{workspace_key}"
GRAUBUENDEN = {"workspace_key": "graubuenden"}
NETWORK = {"applicationKey": "network"}
OPERATOR_BINDING = {
    "relationTypeKey": "stop-operated-by-operator",
    "fromObjectTypeKey": "stop",
    "toObjectTypeKey": "operator",
}
CODES_BINDING = {
    "relationTypeKey": "system-code-maps-to",
    "fromObjectTypeKey": "system-code",
    "toObjectTypeKey": "municipality",
    "direction": "outgoing",
}
CODES_TO_MUNICIPALITIES = {
    "applicationKey": "systems",
    "viewKey": "codes-to-municipalities",
    **CODES_BINDING,
}
# The deterministic fake provider the proposal job calls (``app.engine.proposals.fake``).
FAKE_PROVIDER = "app.engine.proposals.fake:provider"


@pytest.fixture(scope="module")
def relations() -> Iterator[Scenario]:
    _register_seed()
    seeds.ensure(SEED)
    url = seeds.clone(SEED)
    saved = os.environ.get("AI_PROVIDER")
    os.environ["AI_PROVIDER"] = FAKE_PROVIDER
    try:
        with _application(url) as client:
            scenario = Scenario(client)
            yield scenario
            if RECORDING:
                scenario.write_examples()
    finally:
        if saved is None:
            os.environ.pop("AI_PROVIDER", None)
        else:
            os.environ["AI_PROVIDER"] = saved
        seeds.drop(url.database)


def _relations_of(s: Scenario, object_id: str, relation_type_key: str, **record) -> dict:
    return s.call(
        "GET",
        RELATIONS,
        query={"objectId": object_id, "relationTypeKey": relation_type_key, "pageSize": 10},
        status=200,
        **record,
    )


def test_an_integrator_changes_the_relationships_of_stops(relations):
    s = relations
    davos = _one(s, "municipality", "Davos")
    bus = _one(s, "mode", "Bus")
    rhb = _one(s, "operator", "Rhätische Bahn")
    listed = s.call(
        "GET",
        "/api/v1/objects/{object_type_key}",
        path={"object_type_key": "stop"},
        query={"parentObjectId": davos["id"], "sort": "name", "pageSize": 40},
        status=200,
    )
    # Three Davos stops the Rhätische Bahn operates and no bus serves.
    chosen = []
    for stop in listed["items"]:
        found = _relations_of(s, stop["id"], "stop-operated-by-operator")["items"]
        served = _relations_of(s, stop["id"], "stop-served-by-mode")["items"]
        if (
            found
            and found[0]["object"]["id"] == rhb["id"]
            and all(item["object"]["id"] != bus["id"] for item in served)
        ):
            chosen.append((stop, found[0]["relation"]))
    assert len(chosen) >= 3
    (stop_a, operator_a), (stop_b, operator_b), (stop_c, operator_c) = chosen[:3]

    # Read what serves a stop, with the version of the set a later write can claim.
    served = s.call(
        "GET",
        RELATIONS,
        query={
            "objectId": stop_a["id"],
            "relationTypeKey": "stop-served-by-mode",
            "direction": "outgoing",
            "pageSize": 3,
        },
        status=200,
        record="modesOfAStop",
        summary="The modes that serve a stop, with the version of that set",
    )
    (set_,) = served["relationSets"]
    assert set_["relationTypeKey"] == "stop-served-by-mode" and set_["direction"] == "outgoing"
    held = s.call(
        "GET",
        RELATIONS + "/held",
        query={
            "objectTypeKey": "stop",
            "relationTypeKey": "stop-served-by-mode",
            "direction": "outgoing",
            "objectId": [stop_a["id"], stop_b["id"], stop_c["id"]],
            "pageSize": 5,
        },
        status=200,
        record="modesOfThreeStops",
        summary="The modes three stops hold, with how many of the stops hold each",
    )
    assert all(item["count"] == 1 or item["count"] == 3 for item in held["items"])

    # Add a mode, claiming the set that was read.
    added = s.call(
        "POST",
        RELATIONS,
        body={
            "relationTypeKey": "stop-served-by-mode",
            "fromObjectId": stop_a["id"],
            "toObjectId": bus["id"],
            "expectedRelationSetVersion": set_["relationSetVersion"],
            "relationSetDirection": "outgoing",
        },
        status=201,
        record="addAMode",
        summary="A bus also serves the stop; the write claims the set that was read",
    )
    assert added["version"] == 1 and added["relationSetVersion"] == set_["relationSetVersion"] + 1
    s.call(
        "POST",
        RELATIONS,
        body={
            "relationTypeKey": "stop-served-by-mode",
            "fromObjectId": stop_a["id"],
            "toObjectId": _one(s, "mode", "Tram")["id"],
            "expectedRelationSetVersion": set_["relationSetVersion"],
            "relationSetDirection": "outgoing",
        },
        status=409,
        code="RELATION_SET_VERSION_CONFLICT",
    )
    s.call(
        "POST",
        RELATIONS,
        body={
            "relationTypeKey": "stop-served-by-mode",
            "fromObjectId": stop_a["id"],
            "toObjectId": bus["id"],
        },
        status=409,
        code="DUPLICATE_RELATION",
    )
    s.call(
        "POST",
        RELATIONS,
        body={
            "relationTypeKey": "stop-served-by-mode",
            "fromObjectId": stop_a["id"],
            "toObjectId": rhb["id"],
        },
        status=422,
        code="INVALID_RELATION_PAIR",
    )
    s.call(
        "GET",
        ONE,
        path={"relation_id": added["id"]},
        status=200,
        record="theNewRelation",
        summary="The relationship that was added",
    )

    # Record when the operator last inspected the stop, and set values on two more at once.
    inspected = s.call(
        "PATCH",
        ONE,
        path={"relation_id": operator_a["id"]},
        body={
            "attributes": {"local-name": "Station office", "inspected-on": "2026-03-12"},
            "expectedVersion": operator_a["version"],
        },
        status=200,
        record="inspected",
        summary="The operator's local name for the stop and when it was inspected",
    )
    assert inspected["version"] == 2 and inspected["attributes"]["local-name"] == "Station office"
    s.call(
        "PATCH",
        ONE,
        path={"relation_id": operator_a["id"]},
        body={"attributes": {"local-name": "Station"}, "expectedVersion": 1},
        status=409,
        code="VERSION_CONFLICT",
    )
    s.call(
        "PATCH",
        ONE,
        path={"relation_id": added["id"]},
        body={"attributes": {"inspected-on": "2026-03-12"}, "expectedVersion": 1},
        status=422,
        code="UNKNOWN_RELATION_ATTRIBUTES",
    )
    batch = s.call(
        "POST",
        RELATIONS + "/batch",
        body={
            "workspaceKey": "graubuenden",
            "items": [
                {
                    "id": operator_b["id"],
                    "expectedVersion": operator_b["version"],
                    "attributes": {"local-name": "Station office", "is-primary": False},
                },
                {
                    "id": operator_c["id"],
                    "expectedVersion": operator_c["version"],
                    "attributes": {"inspected-on": "2026-05-14"},
                },
            ],
        },
        status=200,
        record="twoStops",
        summary="Values on the operator relationships of two stops, in one write",
    )
    assert [item["version"] for item in batch["items"]] == [2, 2]
    stale = s.call(
        "POST",
        RELATIONS + "/batch",
        body={
            "workspaceKey": "graubuenden",
            "items": [
                {"id": operator_b["id"], "expectedVersion": 1, "attributes": {"is-primary": True}}
            ],
        },
        status=409,
        code="RELATION_BATCH_REFUSED",
    )
    assert stale["error"]["details"]["items"][0]["code"] == "VERSION_CONFLICT"

    # Mark the Rhätische Bahn the primary operator of all three stops: count first, then apply.
    grid = {
        **NETWORK,
        "viewKey": "stop-operators",
        "fromObjectIds": [stop_a["id"], stop_b["id"], stop_c["id"]],
        "toObjectIds": [rhb["id"]],
        "attributeTypeKey": "is-primary",
        "value": True,
    }
    counted = s.call(
        "POST",
        RELATIONS + "/grid-change",
        body={**grid, "workspaceKey": "graubuenden", "dryRun": True},
        status=200,
    )
    assert counted["dryRun"] is True and counted["change"] == 3 and counted["refused"] == []
    done = s.call(
        "POST",
        RELATIONS + "/grid-change",
        body={**grid, "workspaceKey": "graubuenden"},
        status=200,
        record="markPrimary",
        summary="The Rhätische Bahn is the primary operator of three stops",
    )
    assert done["dryRun"] is False and done["change"] == 3 and done["same"] == 0
    s.call(
        "POST",
        RELATIONS + "/grid-change",
        body={**grid, "attributeTypeKey": "height", "workspaceKey": "graubuenden"},
        status=422,
        code="INVALID_GRID_CHANGE",
    )

    # Remove the bus again; a containment relationship cannot be removed on its own.
    s.call(
        "DELETE",
        ONE,
        path={"relation_id": added["id"]},
        query={"expectedVersion": 1},
        status=204,
        record="removeAMode",
        summary="The bus no longer serves the stop",
    )
    (containment,) = [
        item["relation"]
        for item in s.call(
            "GET",
            RELATIONS,
            query={"objectId": stop_a["id"], "direction": "incoming"},
            status=200,
        )["items"]
        if item["relation"]["relationTypeKey"] == "municipality-contains-stop"
    ]
    s.call(
        "DELETE",
        ONE,
        path={"relation_id": containment["id"]},
        query={"expectedVersion": containment["version"]},
        status=422,
        code="IMMUTABLE_RELATION",
    )


def test_an_integrator_maps_the_codes_of_a_system_to_municipalities(relations):
    s = relations
    first = s.call(
        "GET",
        WS + "/mapping-coverage",
        path=GRAUBUENDEN,
        query={**CODES_TO_MUNICIPALITIES, "state": "mapped", "pageSize": 2},
        status=200,
        record="mappedCodes",
        summary="The first two codes that are mapped, with their municipality",
    )
    row = first["items"][0]
    assert row["state"] == "mapped" and row["targetCount"] == 1 and first["nextCursor"]
    code = row["source"]
    mapping = {
        **CODES_BINDING,
        "sourceObjectId": code["id"],
        "expectedMappingVersion": row["mappingVersion"],
    }

    # Clear the code, find it unmapped, choose its municipality and map it again.
    cleared = s.call("PUT", WS + "/mappings", path=GRAUBUENDEN, body=mapping, status=200)
    assert cleared["state"] == "unmapped" and cleared["relationId"] is None
    unmapped = s.call(
        "GET",
        WS + "/mapping-coverage",
        path=GRAUBUENDEN,
        query={**CODES_TO_MUNICIPALITIES, "state": "unmapped", "search": code["name"][:6]},
        status=200,
    )
    assert [item["source"]["id"] for item in unmapped["items"]] == [code["id"]]
    name = row["targets"][0]["object"]["name"]
    candidates = s.call(
        "GET",
        WS + "/mapping-candidates",
        path=GRAUBUENDEN,
        query={
            "applicationKey": "systems",
            "viewKey": "codes-to-municipalities",
            "objectTypeKey": "municipality",
            "search": name[:5],
            "pageSize": 3,
        },
        status=200,
        record="municipalitiesLikeIlanz",
        summary="The municipalities whose name contains the search text",
    )
    (target,) = [item for item in candidates["items"] if item["name"] == name]
    mapped = s.call(
        "PUT",
        WS + "/mappings",
        path=GRAUBUENDEN,
        body={
            **mapping,
            "expectedMappingVersion": cleared["mappingVersion"],
            "targetObjectId": target["id"],
            "attributes": {"confirmed": True, "mapping-note": "Checked against the FSO list"},
        },
        status=200,
        record="mapACode",
        summary="The code is mapped to the municipality and the mapping is confirmed",
    )
    assert mapped["state"] == "mapped" and mapped["relationId"]
    s.call(
        "PUT",
        WS + "/mappings",
        path=GRAUBUENDEN,
        body={**mapping, "expectedMappingVersion": row["mappingVersion"]},
        status=409,
        code="MAPPING_VERSION_CONFLICT",
    )
    targets = s.call(
        "GET",
        WS + "/mapping-targets",
        path=GRAUBUENDEN,
        query={
            "applicationKey": "systems",
            "viewKey": "codes-to-municipalities",
            "relationTypeKey": "system-code-maps-to",
            "fromObjectTypeKey": "system-code",
            "toObjectTypeKey": "municipality",
            "direction": "outgoing",
            "sourceObjectId": code["id"],
            "mappingVersion": mapped["mappingVersion"],
        },
        status=200,
        record="targetsOfACode",
        summary="The municipality the code is mapped to, with the mapping's values",
    )
    assert targets["targetCount"] == 1 and targets["items"][0]["attributes"]["confirmed"] is True
    s.call(
        "GET",
        WS + "/mapping-candidates",
        path=GRAUBUENDEN,
        query={
            "applicationKey": "systems",
            "viewKey": "codes-to-municipalities",
            "objectTypeKey": "stop",
        },
        status=422,
        code="MAPPING_CANDIDATE_TYPE_MISMATCH",
    )

    # Ask the AI provider for the targets of the codes a view still lacks, into a new change set.
    proposed = s.call(
        "POST",
        WS + "/mapping-proposals",
        path=GRAUBUENDEN,
        body={
            "applicationKey": "systems",
            "viewKey": "codes-to-stops",
            "changeSetName": "Map the ticketing codes to stops",
        },
        status=202,
        record="proposeTargets",
        summary="Targets for the codes the view lacks are proposed into a new change set",
    )
    assert proposed["kind"] == "aiProposal"
    s.call(
        "POST",
        WS + "/mapping-proposals",
        path=GRAUBUENDEN,
        body={"applicationKey": "systems", "viewKey": "systems", "changeSetName": "No view"},
        status=404,
        code="MAPPING_VIEW_NOT_FOUND",
    )

    # The relationships as tables.
    listed = s.call(
        "GET",
        WS + "/relations",
        path=GRAUBUENDEN,
        query={**OPERATOR_BINDING, "direction": "outgoing", "pageSize": 3},
        status=200,
        record="operatorRelationships",
        summary="The relationships between stops and operators, three at a time",
    )
    assert all(item["relationTypeKey"] == "stop-operated-by-operator" for item in listed["items"])
    grid = s.call(
        "GET",
        WS + "/relation-grid",
        path=GRAUBUENDEN,
        query={**NETWORK, "viewKey": "stop-operators", "attribute": "is-primary", "pageSize": 2},
        status=200,
        record="stopsByOperator",
        summary="Two stops with their relationship to each operator",
    )
    assert grid["rowTotal"] > 2 and grid["columnTotal"] == len(grid["columns"])
    s.call(
        "GET",
        WS + "/relations",
        path=GRAUBUENDEN,
        query={**NETWORK, "viewKey": "stop-operators-rows", **OPERATOR_BINDING},
        status=422,
        code="RELATION_TABLE_BINDING_FIXED",
    )


def test_an_integrator_reads_the_relation_matrices(relations):
    s = relations
    zuoz = _one(s, "municipality", "Zuoz")
    german = _one(s, "language", "German")
    wikidata = _one(s, "system", "Wikidata: municipalities")
    matrix = s.call(
        "GET",
        WS + "/relation-matrix",
        path=GRAUBUENDEN,
        query={
            "applicationKey": "systems",
            "viewKey": "municipalities-by-system",
            "pageSize": 2,
            "columnPageSize": 3,
        },
        status=200,
        record="municipalitiesBySystem",
        summary="Two municipalities against the systems that name them",
    )
    assert len(matrix["items"]) == 2 and matrix["columns"]
    s.call(
        "GET",
        WS + "/relation-matrix/link-candidates",
        path=GRAUBUENDEN,
        query={
            "applicationKey": "systems",
            "viewKey": "municipalities-by-system",
            "rowId": zuoz["id"],
            "columnId": wikidata["id"],
            "pageSize": 3,
        },
        status=200,
        record="codesZuozCouldGet",
        summary="The codes of one system that a municipality could be mapped from",
    )
    s.call(
        "GET",
        WS + "/relation-matrix/containers",
        path=GRAUBUENDEN,
        query={
            "applicationKey": "names",
            "viewKey": "municipality-names",
            "columnId": german["id"],
            "pageSize": 3,
        },
        status=200,
        record="whereGermanNamesGo",
        summary="Where a new German name goes",
    )
    s.call(
        "GET",
        WS + "/relation-matrix/containers",
        path=GRAUBUENDEN,
        query={
            "applicationKey": "systems",
            "viewKey": "municipalities-by-system",
            "columnId": wikidata["id"],
        },
        status=422,
        code="RELATION_MATRIX_ACTION_NOT_ALLOWED",
    )
    s.call(
        "GET",
        WS + "/relation-matrix",
        path=GRAUBUENDEN,
        query={"applicationKey": "systems", "viewKey": "municipalities-by-system", "state": "one"},
        status=422,
        code="RELATION_MATRIX_STATE_REQUIRES_COLUMNS",
    )
