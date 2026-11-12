"""The ``objects`` and ``attributes`` areas of the management API's reference, recorded from a run on the
guide's reference data (see ``test_reference_recording.py``, whose seed, scenario and normaliser this
file uses).

An integrator who maintains the Graubünden timetable data looks a place up, adds a stop to a
municipality, completes and corrects it, moves it, reads what happened to it and removes it again. Each
step records the main successful use of the operation it calls; the refusals the area's text names are
asserted without being recorded.

    cd backend && RDM_RECORD_EXAMPLES=1 .venv/bin/python -m pytest tests/test_reference_records.py -q
"""

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

OBJECTS = "/api/v1/objects"
ONE = "/api/v1/objects/{object_type_key}/{object_id}"
TYPED = "/api/v1/objects/{object_type_key}"
ATTRIBUTE = "/api/v1/objects/{object_type_key}/{object_id}/attributes/{attribute_type_key}"
QUERY = "/api/v1/workspaces/{workspace_key}/queries/objects"


@pytest.fixture(scope="module")
def records() -> Iterator[Scenario]:
    _register_seed()
    seeds.ensure(SEED)
    url = seeds.clone(SEED)
    try:
        with _application(url) as client:
            scenario = Scenario(client)
            yield scenario
            if RECORDING:
                scenario.write_examples()
    finally:
        seeds.drop(url.database)


def _one(s: Scenario, type_key: str, name: str) -> dict:
    page = s.call(
        "GET", TYPED, path={"object_type_key": type_key}, query={"search": name}, status=200
    )
    (found,) = [item for item in page["items"] if item["name"] == name]
    return found


def test_an_integrator_adds_corrects_moves_and_removes_a_stop(records):
    s = records
    zuoz = _one(s, "municipality", "Zuoz")
    davos = _one(s, "municipality", "Davos")
    pontresina = _one(s, "municipality", "Pontresina")
    train = _one(s, "mode", "Train")

    # Find a place when its type is not known, then list the stops of one municipality.
    found = s.call(
        "GET",
        OBJECTS,
        query={"filter.name.startsWith": "Zuoz", "sort": "objectType", "pageSize": 3},
        status=200,
        record="byName",
        summary="Records of any type whose name starts with Zuoz, by type",
    )
    assert len({item["objectTypeKey"] for item in found["items"]}) > 1
    assert all("modelReleaseId" in item for item in found["items"])
    listed = s.call(
        "GET",
        TYPED,
        path={"object_type_key": "stop"},
        query={
            "parentObjectId": davos["id"],
            "sort": "-stop-number",
            "pageSize": 3,
            "includeTotal": True,
        },
        status=200,
        record="inDavos",
        summary="The stops of Davos, the highest stop number first",
    )
    assert listed["totalCount"] > 3 and listed["nextCursor"]

    # Add a stop under Zuoz, served by the train mode.
    created = s.call(
        "POST",
        OBJECTS,
        body={
            "workspaceKey": "graubuenden",
            "applicationKey": "network",
            "objectTypeKey": "stop",
            "parentObjectId": zuoz["id"],
            "name": "Zuoz, Sportplatz",
            "attributes": [
                {"attributeTypeKey": "designation", "value": "Sportplatz"},
                {"attributeTypeKey": "stop-number", "value": 8599001},
            ],
            "initialRelations": [
                {
                    "relationTypeKey": "stop-served-by-mode",
                    "direction": "outgoing",
                    "otherObjectId": train["id"],
                }
            ],
        },
        status=201,
        record="underZuoz",
        summary="A stop under Zuoz, served by the train mode",
    )
    stop = created["id"]
    assert created["version"] == 1 and created["path"][-2]["id"] == zuoz["id"]
    where = {"object_type_key": "stop", "object_id": stop}
    s.call(
        "GET",
        ONE,
        path=where,
        status=200,
        record="theNewStop",
        summary="The stop as it was created",
    )

    # Complete it value by value.
    done = s.call(
        "POST",
        ATTRIBUTE,
        path={**where, "attribute_type_key": "height"},
        body={"value": 1716.5, "expectedVersion": 1},
        status=201,
        record="setHeight",
        summary="Set the height, which the stop does not hold yet",
    )
    assert done["version"] == 2
    s.call(
        "POST",
        ATTRIBUTE,
        path={**where, "attribute_type_key": "height"},
        body={"value": 1716.5, "expectedVersion": 2},
        status=409,
        code="ATTRIBUTE_ALREADY_EXISTS",
    )
    s.call(
        "GET",
        ATTRIBUTE,
        path={**where, "attribute_type_key": "height"},
        status=200,
        record="readHeight",
        summary="The height and the version of the stop that holds it",
    )
    fixed = s.call(
        "PATCH",
        ATTRIBUTE,
        path={**where, "attribute_type_key": "height"},
        body={"value": 1716.8, "expectedVersion": 2},
        status=200,
        record="correctHeight",
        summary="Correct the height",
    )
    assert fixed["version"] == 3
    s.call(
        "PATCH",
        ATTRIBUTE,
        path={**where, "attribute_type_key": "abbreviation"},
        body={"value": "ZSPL", "expectedVersion": 3},
        status=404,
        code="ATTRIBUTE_NOT_FOUND",
    )
    s.call(
        "DELETE",
        ATTRIBUTE,
        path={**where, "attribute_type_key": "height"},
        query={"expectedVersion": 3},
        status=204,
        record="clearHeight",
        summary="Remove the height again",
    )
    s.call(
        "DELETE",
        ATTRIBUTE,
        path={**where, "attribute_type_key": "stop-number"},
        query={"expectedVersion": 4},
        status=422,
        code="CANNOT_DELETE_REQUIRED_ATTRIBUTE",
    )

    # Change the record as a whole.
    s.call(
        "PATCH",
        ONE,
        path=where,
        body={"name": "Zuoz, Sportplatz 2", "expectedVersion": 3},
        status=409,
        code="VERSION_CONFLICT",
    )
    s.call(
        "PATCH",
        ONE,
        path=where,
        body={
            "expectedVersion": 4,
            "attributes": [
                {"attributeTypeKey": "valid-from", "value": "2026-12-13"},
                {"attributeTypeKey": "valid-to", "value": "2026-12-01"},
            ],
        },
        status=422,
        code="INVALID_EFFECTIVE_PERIOD",
    )
    renamed = s.call(
        "PATCH",
        ONE,
        path=where,
        body={
            "name": "Zuoz, Sportplatz Mitte",
            "expectedVersion": 4,
            "attributes": [{"attributeTypeKey": "valid-from", "value": "2026-12-13"}],
        },
        status=200,
        record="renameAndDate",
        summary="Rename the stop and give it a first day of validity",
    )
    assert renamed["version"] == 5 and renamed["name"] == "Zuoz, Sportplatz Mitte"
    s.call(
        "PATCH",
        ONE,
        path=where,
        body={"parentObjectId": None, "expectedVersion": 5},
        status=422,
        code="PARENT_REQUIRED",
    )

    # Move it to another municipality.
    candidates = s.call(
        "GET",
        "/api/v1/objects/{object_type_key}/{object_id}/parent-candidates",
        path=where,
        query={"search": "Pontresina", "pageSize": 3},
        status=200,
        record="municipalityPontresina",
        summary="The municipalities named Pontresina the stop could move under",
    )
    (candidate,) = candidates["items"]
    assert candidate["id"] == pontresina["id"] and candidate["eligible"] is True
    moved = s.call(
        "PATCH",
        ONE,
        path=where,
        body={"parentObjectId": pontresina["id"], "expectedVersion": 5},
        status=200,
    )
    assert moved["version"] == 6 and moved["path"][-2]["id"] == pontresina["id"]
    s.call(
        "PATCH",
        ONE,
        path=where,
        body={"parentObjectId": stop, "expectedVersion": 6},
        status=422,
        code="INVALID_PARENT_TYPE",
    )

    history = s.call(
        "GET",
        "/api/v1/objects/{object_type_key}/{object_id}/history",
        path=where,
        query={"pageSize": 3},
        status=200,
        record="newestFirst",
        summary="The three newest entries of the stop's history",
    )
    assert history["items"][0]["version"] == 6 and history["nextCursor"]
    assert history["items"][0]["kind"] == "structure"

    # Ask for it again by criteria.
    queried = s.call(
        "POST",
        QUERY,
        path={"workspace_key": "graubuenden"},
        body={
            "objectTypeKey": "stop",
            "asOf": "2027-01-01",
            "where": [
                {"field": "ancestor:municipality", "op": "eq", "value": pontresina["id"]},
                {
                    "related": {
                        "relationTypeKey": "stop-served-by-mode",
                        "direction": "outgoing",
                        "where": [{"field": "name", "op": "eq", "value": "Train"}],
                    }
                },
            ],
            "sort": "-stop-number",
            "select": ["name", "stop-number", "ancestor:municipality"],
            "expand": [
                {
                    "relationTypeKey": "stop-served-by-mode",
                    "direction": "outgoing",
                    "select": ["name"],
                    "limit": 3,
                }
            ],
            "pageSize": 2,
            "includeTotal": True,
        },
        status=200,
        record="trainStopsInPontresina",
        summary="The stops of Pontresina that the train serves, with their modes",
    )
    assert queried["items"][0]["id"] == stop
    s.call(
        "POST",
        QUERY,
        path={"workspace_key": "graubuenden"},
        body={"objectTypeKey": "stop", "where": [{"field": "colour", "op": "eq", "value": 1}]},
        status=422,
        code="INVALID_QUERY",
    )

    # The refusals the area's text names.
    s.call(
        "POST",
        OBJECTS,
        body={
            "workspaceKey": "graubuenden",
            "applicationKey": "network",
            "objectTypeKey": "stop",
            "parentObjectId": zuoz["id"],
            "name": "Zuoz, Sportplatz",
            "attributes": [
                {"attributeTypeKey": "designation", "value": "Sportplatz"},
                {"attributeTypeKey": "stop-number", "value": 8599001},
            ],
        },
        status=409,
        code="DUPLICATE_ATTRIBUTE_VALUE",
    )
    s.call(
        "POST",
        OBJECTS,
        body={
            "workspaceKey": "graubuenden",
            "applicationKey": "network",
            "objectTypeKey": "stop",
            "parentObjectId": zuoz["id"],
            "name": "Zuoz, ohne Nummer",
            "attributes": [{"attributeTypeKey": "designation", "value": "ohne Nummer"}],
        },
        status=422,
        code="MISSING_REQUIRED_ATTRIBUTES",
    )
    s.call(
        "POST",
        OBJECTS,
        body={
            "applicationKey": "network",
            "objectTypeKey": "stop",
            "name": "Zuoz, ohne Arbeitsbereich",
        },
        status=422,
        code="WORKSPACE_KEY_REQUIRED",
    )
    s.call(
        "GET",
        OBJECTS,
        query={"asOf": "2027-01-01"},
        status=422,
        code="AS_OF_NOT_SUPPORTED",
    )
    s.call(
        "GET",
        TYPED,
        path={"object_type_key": "municipality"},
        query={"asOf": "2027-01-01"},
        status=422,
        code="AS_OF_NOT_SUPPORTED",
    )
    s.call(
        "GET",
        ONE,
        path={"object_type_key": "municipality", "object_id": stop},
        status=409,
        code="OBJECT_TYPE_CHANGED",
    )
    s.call(
        "DELETE",
        ONE,
        path={"object_type_key": "municipality", "object_id": zuoz["id"]},
        query={"expectedVersion": zuoz["version"]},
        status=409,
        code="OBJECT_HAS_DEPENDANTS",
    )
    s.call(
        "DELETE",
        ONE,
        path={"object_type_key": "municipality", "object_id": zuoz["id"]},
        query={"expectedVersion": zuoz["version"], "cascade": True},
        status=409,
        code="DELETION_PREVIEW_REQUIRED",
    )

    # Remove a record nothing depends on, then one that has relationships, which takes the preview.
    spare = s.call(
        "POST",
        OBJECTS,
        body={
            "workspaceKey": "graubuenden",
            "applicationKey": "network",
            "objectTypeKey": "stop",
            "parentObjectId": zuoz["id"],
            "name": "Zuoz, Provisorium",
            "attributes": [
                {"attributeTypeKey": "designation", "value": "Provisorium"},
                {"attributeTypeKey": "stop-number", "value": 8599002},
            ],
        },
        status=201,
    )
    s.call(
        "DELETE",
        ONE,
        path={"object_type_key": "stop", "object_id": spare["id"]},
        query={"expectedVersion": 1},
        status=204,
        record="removeAStop",
        summary="Delete a stop that nothing depends on",
    )
    preview = s.call(
        "DELETE",
        ONE,
        path=where,
        query={"expectedVersion": 6},
        status=409,
        code="OBJECT_HAS_DEPENDANTS",
    )
    details = preview["error"]["details"]
    assert details["objectCount"] == 1 and details["relationshipCount"] == 2
    impact = s.call(
        "GET",
        "/api/v1/objects/{object_type_key}/{object_id}/deletion-impact",
        path=where,
        status=200,
        record="deletionImpact",
        summary="Read what deleting a stop with relationships would take, deleting nothing",
    )
    assert impact["deletionPreviewToken"] == details["deletionPreviewToken"]
    assert impact["relationshipCount"] == 2 and impact["requiresCascade"] is True
    s.call(
        "DELETE",
        ONE,
        path=where,
        query={
            "expectedVersion": 6,
            "cascade": True,
            "deletionPreviewToken": details["deletionPreviewToken"],
        },
        status=204,
    )
    s.call("GET", ONE, path=where, status=404, code="OBJECT_NOT_FOUND")
