"""The ``model``, ``model administration`` and ``model mappings`` areas of the management API's reference,
recorded from a run on the guide's reference data (see ``test_reference_recording.py``, whose seed,
scenario and normaliser this file uses).

An administrator of the Graubünden network's model reads the model the workspace runs (its
applications, types, attribute types, relation types, placements, a consumer API and the
capabilities), validates a model document and opens the workspace's draft. She applies a step of
operations, reads the draft's history, migration, outline, compiled model and consumer API documents,
undoes and redoes the step, stores a small CSV file of vehicles for the draft, follows its profile, has
the inference propose a model and applies the proposals, and dry-runs the file against the draft. The
draft is compiled and installed as a second release; the releases are read and compared, the
workspace is activated on the second release and migrated to a third, and a spare release and a spare
draft are removed. The module ``test_reference_mappings.py`` continues with a second model.
Each step records the main successful use of the operation it calls; the refusals the areas' text
names are asserted without being recorded. Every job is followed to its end.

    cd backend && RDM_RECORD_EXAMPLES=1 .venv/bin/python -m pytest tests/test_reference_model.py -q
"""

import copy
import hashlib
import json
import time
from collections.abc import Iterator

import pytest
import seeds
from openpyxl import Workbook
from sqlalchemy import create_engine, text
from sqlalchemy.pool import NullPool
from test_reference_jobs import FINAL, JOB, _upload, _wait
from test_reference_recording import (
    RECORDING,
    SEED,
    Scenario,
    _application,
    _register_seed,
)

WS = {"workspace_key": "graubuenden"}
DRAFT = "/api/v1/model-drafts/{draft_id}"
RELEASE = "/api/v1/model-releases/{release_id}"


def inventory_model(version: str = "1.0.0") -> dict:
    """A small model of another domain: the stops a cantonal inventory tracks, with its own keys."""
    return {
        "schemaVersion": "0.10",
        "release": {"key": "stop-inventory", "name": "Stop inventory", "version": version},
        "product": {
            "name": "Stop inventory",
            "description": "The stop points a cantonal inventory counts",
        },
        "attributeTypes": [
            {
                "key": "stop-number",
                "name": "Stop number",
                "valueType": "integer",
                "features": {
                    "searchable": True,
                    "unique": True,
                    "filterable": True,
                    "sortable": True,
                },
            },
            {"key": "opened", "name": "Opened on", "valueType": "date"},
            {"key": "platforms", "name": "Platforms", "valueType": "integer"},
        ],
        "objectTypes": [
            {
                "key": "stop-point",
                "name": "Stop point",
                "pluralName": "Stop points",
                "features": {"rootCreatable": True},
                "attributes": [
                    {"attributeTypeKey": "stop-number", "order": 10, "required": True},
                    {"attributeTypeKey": "opened", "order": 20},
                    {"attributeTypeKey": "platforms", "order": 30},
                ],
            }
        ],
        "relationTypes": [],
        "objectTypeRelations": [],
        "applications": [
            {
                "key": "inventory",
                "name": "Inventory",
                "objectTypeKeys": ["stop-point"],
                "defaultView": "stop-points",
                "views": [
                    {
                        "key": "stop-points",
                        "name": "Stop points",
                        "type": "table",
                        "objectTypeKey": "stop-point",
                        "config": {
                            "columns": ["name", "stop-number", "opened", "platforms"],
                            "filterFields": ["stop-number"],
                            "sortFields": ["name", "stop-number"],
                            "defaultSort": "name",
                            "pageSize": 25,
                        },
                    }
                ],
            }
        ],
    }


def _stage_old_schema(s: Scenario, release_id: str) -> None:
    """Store the release as an earlier engine left it, in schema 0.9 with its own hash: the state a
    release is in after an engine upgrade, which no request produces."""
    engine = create_engine(s.url, poolclass=NullPool)
    with engine.begin() as connection:
        row = connection.execute(
            text("SELECT model_json FROM model_releases WHERE public_id = :id"), {"id": release_id}
        ).scalar_one()
        connection.execute(
            text(
                "UPDATE model_releases SET schema_version = '0.9', model_hash = :hash,"
                " model_json = CAST(:m AS json) WHERE public_id = :id"
            ),
            {
                "m": json.dumps({**row, "schemaVersion": "0.9"}),
                "id": release_id,
                "hash": hashlib.sha256(b"the earlier engine").hexdigest(),
            },
        )
    engine.dispose()


def _without_model(body: dict) -> tuple[dict, list[str]]:
    """A draft, a page of drafts or a compilation, with each model document cut down to its release:
    the whole document is what ``GET /model`` and ``GET /model-drafts/{id}/model`` show."""
    notes = []
    if isinstance(body.get("model"), dict):
        body = {**body, "model": _release_of(body["model"])}
        notes.append(_CUT.format(where="model"))
    if isinstance(body.get("items"), list):
        body = {
            **body,
            "items": [
                {**item, "model": _release_of(item["model"])} if "model" in item else item
                for item in body["items"]
            ],
        }
        notes.append(_CUT.format(where="items[].model"))
    return body, notes


_CUT = (
    "`{where}`: the model document, which `GET /model` shows in full; only its `schemaVersion`,"
    " `release` and `product` are shown here."
)


def _release_of(document: dict) -> dict:
    return {
        key: document[key] for key in ("schemaVersion", "release", "product") if key in document
    }


def _short_openapi(body: dict) -> tuple[dict, list[str]]:
    """An OpenAPI document with its first two paths and first three schemas."""
    paths, schemas = body["paths"], body["components"]["schemas"]
    short = {
        **body,
        "paths": dict(list(paths.items())[:2]),
        "components": {**body["components"], "schemas": dict(list(schemas.items())[:3])},
    }
    return short, [
        f"`paths`: the first 2 of {len(paths)} paths are shown.",
        f"`components.schemas`: the first 3 of {len(schemas)} schemas are shown.",
    ]


class ModelScenario(Scenario):
    """A scenario whose ``call`` may shorten the body it records (``shorten``, with a note)."""

    shorten = None

    def call(self, *args, shorten=None, **kwargs):
        self.shorten = shorten
        try:
            return super().call(*args, **kwargs)
        finally:
            self.shorten = None

    def _record(self, method, route, name, summary, path, query, body, status, out, notes=None):
        if self.shorten is not None and isinstance(out, dict):
            out, more = self.shorten(out)
            notes = [*(notes or []), *more]
        super()._record(method, route, name, summary, path, query, body, status, out, notes)


@pytest.fixture(scope="module")
def model(tmp_path_factory) -> Iterator[Scenario]:
    _register_seed()
    seeds.ensure(SEED)
    url = seeds.clone(SEED)
    try:
        with _application(url) as client:
            scenario = ModelScenario(client)
            scenario.scratch = tmp_path_factory.mktemp("reference-model")
            scenario.url = url
            yield scenario
            if RECORDING:
                scenario.write_examples()
    finally:
        seeds.drop(url.database)


def _until(s: Scenario, route: str, path: dict, running: tuple[str, ...], seconds: float = 120):
    """Read a draft's job-like state (``state``) until it is no longer one of ``running``."""
    deadline = time.monotonic() + seconds
    while True:
        answer = s.call("GET", route, path=path, status=200)
        if answer["state"] not in running:
            return answer
        assert time.monotonic() < deadline, answer
        time.sleep(0.25)


def test_the_model_the_workspace_runs_is_read_and_a_document_validated(model):
    s = model
    capabilities = s.call(
        "GET",
        "/api/v1/capabilities",
        status=200,
        record="thisInstance",
        summary="What this instance offers the signed-in administrator",
    )
    assert capabilities["modelAdmin"]
    document = s.call(
        "GET",
        "/api/v1/model",
        status=200,
        record="graubuenden",
        summary="The model the default workspace runs",
    )
    assert document["release"]["version"] == "1.8.1"
    apps = s.call(
        "GET",
        "/api/v1/applications",
        query={"pageSize": 2},
        status=200,
        record="firstPage",
        summary="The first two applications of the model, in key order",
    )
    assert [a["key"] for a in apps["items"]] == ["names", "network"]
    network = s.call(
        "GET",
        "/api/v1/applications/{application_key}",
        path={"application_key": "network"},
        status=200,
        record="network",
        summary="The network application with the types it holds",
    )
    assert network["key"] == "network"
    attributes = s.call(
        "GET",
        "/api/v1/attribute-types",
        query={"pageSize": 2},
        status=200,
        record="firstPage",
        summary="The first two attribute types, in key order",
    )
    assert len(attributes["items"]) == 2
    s.call(
        "GET",
        "/api/v1/attribute-types/{attribute_type_key}",
        path={"attribute_type_key": "stop-number"},
        status=200,
        record="stopNumber",
        summary="The stop number: an integer that identifies a stop",
    )
    types = s.call(
        "GET",
        "/api/v1/object-types",
        query={"pageSize": 2},
        status=200,
        record="firstPage",
        summary="The first two object types, in key order",
    )
    assert len(types["items"]) == 2
    s.call(
        "GET",
        "/api/v1/object-types/{object_type_key}",
        path={"object_type_key": "stop"},
        status=200,
        record="stop",
        summary="The stop type: its attributes, its parent and its relationships",
    )
    relations = s.call(
        "GET",
        "/api/v1/relation-types",
        query={"pageSize": 2},
        status=200,
        record="firstPage",
        summary="The first two relation types, in key order",
    )
    assert len(relations["items"]) == 2
    s.call(
        "GET",
        "/api/v1/relation-types/{relation_type_key}",
        path={"relation_type_key": "stop-served-by-mode"},
        status=200,
        record="servedByMode",
        summary="The relationship that says which modes serve a stop",
    )
    s.call(
        "GET",
        "/api/v1/object-type-relations",
        query={"pageSize": 2},
        status=200,
        record="firstPage",
        summary="The first two rules for which types a relationship may join",
    )
    s.call(
        "GET",
        "/api/v1/model/placements",
        status=200,
        record="graubuenden",
        summary="Where records of each type may stand, per application",
    )
    s.call(
        "GET",
        "/api/v1/model/consumer-apis/{consumerApi}",
        path={"consumerApi": "stops"},
        status=200,
        record="stops",
        summary="The Stops API definition with every default written out",
    )
    s.call(
        "GET",
        "/api/v1/model/consumer-apis/{consumerApi}",
        path={"consumerApi": "nothing"},
        status=404,
        code="CONSUMER_API_NOT_FOUND",
    )
    s.call(
        "GET",
        "/api/v1/applications/{application_key}",
        path={"application_key": "nothing"},
        status=404,
    )

    valid = s.call(
        "POST",
        "/api/v1/model-validations",
        body={"model": inventory_model()},
        status=200,
        record="validDocument",
        summary="A small model document that compiles",
    )
    assert valid["valid"] is True
    broken = copy.deepcopy(inventory_model())
    broken["objectTypes"][0]["attributes"][0]["attributeTypeKey"] = "no-such-attribute"
    refused = s.call("POST", "/api/v1/model-validations", body={"model": broken}, status=200)
    assert refused["valid"] is False and refused["diagnostics"]


def test_a_draft_of_the_workspace_model_is_changed_read_and_stepped_back(model):
    s = model
    releases = s.call(
        "GET",
        "/api/v1/model-releases",
        query={"releaseKey": "guide-reference-swiss"},
        status=200,
    )
    (running,) = releases["items"]
    s.release = running
    s.call(
        "GET",
        "/api/v1/model-releases/{release_id}",
        path={"release_id": running["id"]},
        query={"includeModel": False},
        status=200,
        record="running",
        summary="The release the workspaces run, without its model document",
    )

    draft = s.call(
        "POST",
        "/api/v1/workspaces/{workspace_key}/model/draft",
        path=WS,
        status=201,
        record="graubuenden",
        summary="A draft of the model the Graubünden workspace runs",
        shorten=_without_model,
    )
    s.draft = draft
    again = s.call("POST", "/api/v1/workspaces/{workspace_key}/model/draft", path=WS, status=200)
    assert again["id"] == draft["id"]
    s.call(
        "POST",
        "/api/v1/workspaces/{workspace_key}/model/draft",
        path={"workspace_key": "nothing"},
        status=404,
        code="WORKSPACE_NOT_FOUND",
    )
    page = s.call(
        "GET",
        "/api/v1/model-drafts",
        query={"pageSize": 2},
        status=200,
        record="firstPage",
        summary="The drafts of the instance, the latest changed first",
        shorten=_without_model,
    )
    assert [item["id"] for item in page["items"]] == [draft["id"]]
    s.call(
        "GET",
        DRAFT,
        path={"draft_id": draft["id"]},
        status=200,
        record="graubuenden",
        summary="The draft with its model document, at its version",
        shorten=_without_model,
    )
    renamed = s.call(
        "PATCH",
        DRAFT,
        path={"draft_id": draft["id"]},
        body={"expectedVersion": draft["version"], "name": "Step-free access"},
        status=200,
        record="rename",
        summary="Rename the draft",
        shorten=_without_model,
    )
    assert renamed["name"] == "Step-free access" and renamed["version"] == draft["version"] + 1
    s.call(
        "PATCH",
        DRAFT,
        path={"draft_id": draft["id"]},
        body={"expectedVersion": draft["version"], "name": "Stale"},
        status=409,
        code="VERSION_CONFLICT",
    )
    s.draft = renamed

    step = s.call(
        "POST",
        DRAFT + "/operations",
        path={"draft_id": draft["id"]},
        body={
            "expectedVersion": renamed["version"],
            "operations": [
                {
                    "kind": "addAttributeType",
                    "key": "step-free",
                    "name": "Step-free access",
                    "valueType": "boolean",
                },
                {"kind": "attachAttribute", "objectType": "stop", "attributeType": "step-free"},
                {
                    "kind": "setLabel",
                    "element": {"attributeType": "step-free"},
                    "description": "Whether a passenger can board without steps",
                },
            ],
        },
        status=200,
        record="threeKinds",
        summary="A step of three operations: a new attribute type, attached to stops and described",
    )
    assert step["valid"] is True and len(step["entries"]) == 3
    s.draft = {**s.draft, "version": step["version"]}
    s.call(
        "POST",
        DRAFT + "/operations",
        path={"draft_id": draft["id"]},
        body={
            "expectedVersion": step["version"] - 1,
            "operations": [{"kind": "detachAttribute", "objectType": "stop"}],
        },
        status=409,
        code="VERSION_CONFLICT",
    )
    s.call(
        "POST",
        DRAFT + "/operations",
        path={"draft_id": draft["id"]},
        body={
            "expectedVersion": step["version"],
            "operations": [{"kind": "attachAttribute", "objectType": "stop"}],
        },
        status=422,
        code="INVALID_OPERATION",
    )
    history = s.call(
        "GET",
        DRAFT + "/operations",
        path={"draft_id": draft["id"]},
        query={"pageSize": 2},
        status=200,
        record="firstPage",
        summary="The first two operations of the draft's history, in the order they were written",
    )
    assert [e["kind"] for e in history["items"]] == ["addAttributeType", "attachAttribute"]
    s.call(
        "GET",
        DRAFT + "/migration",
        path={"draft_id": draft["id"]},
        query={"workspaceKey": "graubuenden"},
        status=200,
        record="forTheWorkspace",
        summary="What the draft's steps would do to the Graubünden workspace's records",
    )
    s.call(
        "GET",
        DRAFT + "/outline",
        path={"draft_id": draft["id"]},
        status=200,
        record="graubuenden",
        summary="The draft's structure as the editor shows it",
    )
    s.call(
        "GET",
        DRAFT + "/model",
        path={"draft_id": draft["id"]},
        status=200,
        record="graubuenden",
        summary="The draft compiled as the model, for a preview before installing",
    )
    api = DRAFT + "/consumer-apis/{consumer_api}"
    where = {"draft_id": draft["id"], "consumer_api": "stops"}
    s.call(
        "GET",
        api,
        path=where,
        status=200,
        record="stops",
        summary="The Stops API definition of the draft with every default",
    )
    s.call(
        "GET",
        api + "/schema.json",
        path=where,
        status=200,
        record="stops",
        summary="The JSON Schema of the object message the Stops API serves",
    )
    s.call(
        "GET",
        api + "/example.json",
        path=where,
        status=200,
        record="stops",
        summary="One object message valid against that schema",
    )
    s.call(
        "GET",
        api + "/openapi.json",
        path=where,
        status=200,
        record="stops",
        summary="The OpenAPI document the consumer tier serves for the Stops API",
        shorten=_short_openapi,
    )
    s.call(
        "GET",
        api,
        path={**where, "consumer_api": "nothing"},
        status=404,
    )
    release = s.call(
        "POST",
        DRAFT + "/operations",
        path={"draft_id": draft["id"]},
        body={
            "expectedVersion": step["version"],
            "operations": [{"kind": "setRelease", "version": "1.9.0"}],
        },
        status=200,
    )
    undone = s.call(
        "POST",
        DRAFT + "/undo",
        path={"draft_id": draft["id"]},
        body={"expectedVersion": release["version"]},
        status=200,
        record="latestStep",
        summary="Undo the latest step, the new release version",
    )
    assert undone["entries"][0]["origin"]["type"] == "undo"
    redone = s.call(
        "POST",
        DRAFT + "/redo",
        path={"draft_id": draft["id"]},
        body={"expectedVersion": undone["version"]},
        status=200,
        record="latestStep",
        summary="Redo it",
    )
    assert redone["entries"][0]["undone"] is False
    s.call(
        "POST",
        DRAFT + "/redo",
        path={"draft_id": draft["id"]},
        body={"expectedVersion": redone["version"]},
        status=409,
        code="NOTHING_TO_REDO",
    )
    s.draft = {**s.draft, "version": redone["version"]}


def test_a_source_file_is_read_by_the_draft_proposed_as_a_model_and_dry_run(model):
    s = model
    draft = s.draft
    workbook = s.scratch / "Fahrzeuge.xlsx"
    book = Workbook()
    sheet = book.active
    sheet.title = "Fahrzeuge"
    sheet.append(["Fahrzeugnummer", "Name", "Hersteller", "Baujahr", "Sitzplaetze"])
    for row in (
        (10021, "Bus Chur 1", "Hess", 2016, 41),
        (10022, "Bus Chur 2", "Hess", 2016, 41),
        (10130, "Bus Davos 1", "Solaris", 2019, 35),
        (10131, "Bus Davos 2", "Solaris", 2019, 35),
        (10245, "Bus Ilanz 1", "MAN", 2021, 44),
        (10246, "Bus Ilanz 2", "MAN", 2021, 44),
        (10301, "Bus Scuol 1", "Mercedes", 2022, 38),
        (10302, "Bus Scuol 2", "Mercedes", 2022, 38),
    ):
        sheet.append(row)
    book.save(workbook)
    stored = _upload(
        s,
        "/api/v1/source-files",
        {"owner": {"draftId": draft["id"]}, "format": "xlsx", "workspaceKey": "graubuenden"},
        workbook,
        status=201,
    )
    job = _wait(s, stored["profile"]["jobId"])
    assert job["state"] == "completed", job
    s.source_file = stored["id"]
    started = s.call(
        "POST",
        DRAFT + "/inference",
        path={"draft_id": draft["id"]},
        body={
            "mode": "newApplication",
            "applicationKey": "vehicles",
            "applicationName": "Vehicles",
        },
        status=202,
        record="newApplication",
        summary="Propose a new application from the vehicles file",
    )
    assert started["state"] == "checking"
    _until(s, DRAFT + "/inference", {"draft_id": draft["id"]}, ("checking",))
    inference = s.call(
        "GET",
        DRAFT + "/inference",
        path={"draft_id": draft["id"]},
        status=200,
        record="completed",
        summary="The inference finished: five proposals are open",
    )
    assert inference["state"] == "completed" and inference["counts"]["open"] == 5
    proposals = s.call(
        "GET",
        DRAFT + "/inference/proposals",
        path={"draft_id": draft["id"]},
        query={"pageSize": 2},
        status=200,
        record="firstPage",
        summary="The first two proposals, in the order they apply",
    )
    assert [p["pattern"] for p in proposals["items"]] == ["newApplication", "keyColumn"]
    applied = s.call(
        "POST",
        DRAFT + "/inference/application",
        path={"draft_id": draft["id"]},
        body={"expectedVersion": draft["version"]},
        status=200,
        record="everyOpenProposal",
        summary="Apply every open proposal, each as a step of the draft",
    )
    assert applied["dryRun"]["state"] == "checking"
    followed = _wait(s, applied["dryRun"]["jobId"])
    assert followed["state"] == "completed", followed
    s.draft = {**draft, "version": applied["version"]}
    listed = s.call(
        "POST",
        DRAFT + "/inference/list",
        path={"draft_id": draft["id"]},
        body={
            "sheet": "Fahrzeuge",
            "headerRow": 1,
            "block": {"firstColumn": "C", "lastColumn": "C", "lastRow": 9},
        },
        status=200,
        record="manufacturers",
        summary="Read the manufacturer column as a list",
    )
    assert listed["pattern"] == "listBlock" and listed["operations"]
    profile = s.call(
        "GET",
        DRAFT + "/profile",
        path={"draft_id": draft["id"]},
        status=200,
        record="withTheVehiclesFile",
        summary="The import profile the draft holds for the vehicles file",
    )
    assert profile["sourceFile"]["id"] == stored["id"] and profile["valid"] is True
    run = s.call(
        "POST",
        DRAFT + "/dry-run",
        path={"draft_id": draft["id"]},
        body={"sourceFileId": stored["id"], "workspaceKey": "graubuenden"},
        status=202,
        record="vehiclesFile",
        summary="Check the vehicles file against the draft's model; nothing is written",
    )
    assert run["state"] == "checking"
    done = _until(s, DRAFT + "/dry-run", {"draft_id": draft["id"]}, ("checking",))
    assert done["state"] == "completed", done
    s.call(
        "GET",
        DRAFT + "/dry-run",
        path={"draft_id": draft["id"]},
        status=200,
        record="vehiclesFile",
        summary="The dry run's summary: the eight vehicles would be created",
    )
    rows = s.call(
        "GET",
        DRAFT + "/dry-run/rows",
        path={"draft_id": draft["id"]},
        query={"pageSize": 2},
        status=200,
        record="firstPage",
        summary="The first two rows the dry run checked",
    )
    assert len(rows["items"]) == 2


def test_the_draft_is_installed_compared_activated_and_the_workspace_migrated(model):
    s = model
    draft, first = s.draft, s.release
    compiled = s.call(
        "POST",
        DRAFT + "/compile",
        path={"draft_id": draft["id"]},
        body={"expectedVersion": draft["version"]},
        status=200,
        record="graubuenden",
        summary="The draft compiles: what changes against the release it started from",
        shorten=_without_model,
    )
    assert compiled["valid"] is True and compiled["againstReleaseId"] == first["id"]
    s.call(
        "POST",
        DRAFT + "/installation",
        path={"draft_id": draft["id"]},
        body={"expectedVersion": draft["version"] - 1},
        status=409,
        code="VERSION_CONFLICT",
    )
    installed = s.call(
        "POST",
        DRAFT + "/installation",
        path={"draft_id": draft["id"]},
        body={"expectedVersion": draft["version"]},
        status=201,
        record="secondRelease",
        summary="Install the draft as a second release of the guide model",
    )
    assert installed["importProfile"] == {"key": "fahrzeuge", "version": 1}
    second = installed
    s.second = second
    listed = s.call(
        "GET",
        "/api/v1/model-releases",
        query={"releaseKey": "guide-reference-swiss", "status": "active"},
        status=200,
        record="ofTheGuideModel",
        summary="The releases of the guide model, with the workspaces that run each",
    )
    assert [item["version"] for item in listed["items"]] == ["1.8.1", "1.9.0"]
    diff = s.call(
        "GET",
        RELEASE + "/diff",
        path={"release_id": second["id"]},
        query={"againstReleaseId": first["id"], "workspaceKey": "graubuenden"},
        status=200,
        record="againstTheRunningRelease",
        summary="What the second release changes, and whether the Graubünden workspace can take it",
    )
    assert diff["compatibility"]["classification"] == "compatible" and diff["changes"]
    runtime = s.call("GET", "/api/v1/workspaces/{workspace_key}/model", path=WS, status=200)
    s.call(
        "POST",
        "/api/v1/workspaces/{workspace_key}/model/activation",
        path=WS,
        body={
            "releaseId": second["id"],
            "expectedVersion": runtime["version"] + 1,
            "expectedReleaseId": first["id"],
        },
        status=409,
        code="ACTIVATION_CONFLICT",
    )
    activated = s.call(
        "POST",
        "/api/v1/workspaces/{workspace_key}/model/activation",
        path=WS,
        body={
            "releaseId": second["id"],
            "expectedVersion": runtime["version"],
            "expectedReleaseId": first["id"],
        },
        status=200,
        record="secondRelease",
        summary="Activate the second release in the Graubünden workspace",
    )
    assert activated["releaseId"] == second["id"] and activated["version"] == runtime["version"] + 1
    s.runtime = activated
    history = s.call(
        "GET",
        RELEASE + "/activations",
        path={"release_id": second["id"]},
        status=200,
        record="secondRelease",
        summary="Where the second release was selected as a workspace's model",
    )
    assert [(i["workspaceKey"], i["previousReleaseId"]) for i in history["items"]] == [
        ("graubuenden", first["id"])
    ]


def test_the_workspace_is_migrated_to_a_third_release_and_spares_are_removed(model):
    s = model
    second, runtime = s.second, s.runtime
    document = s.call("GET", "/api/v1/model", query={"workspaceKey": "graubuenden"}, status=200)
    later = copy.deepcopy(document)
    later["release"]["version"] = "1.9.1"
    third_draft = s.call(
        "POST",
        "/api/v1/model-drafts",
        body={"name": "Version 1.9.1", "model": later, "baseReleaseId": second["id"]},
        status=201,
    )
    third = s.call(
        "POST",
        DRAFT + "/installation",
        path={"draft_id": third_draft["id"]},
        body={"expectedVersion": third_draft["version"]},
        status=201,
    )
    job = s.call(
        "POST",
        "/api/v1/workspaces/{workspace_key}/model/migrations",
        path=WS,
        body={"targetReleaseId": third["id"], "expectedVersion": runtime["version"]},
        status=202,
        record="toTheThirdRelease",
        summary="Queue the preview of a migration of the workspace's records to the third release",
    )
    assert job["kind"] == "migration"
    waiting = _wait(s, job["id"], "awaiting_confirmation", *FINAL)
    assert waiting["state"] == "awaiting_confirmation", waiting
    summary = waiting["migration"]
    assert summary["counts"] == {"conversion": 0, "reclassified": 0, "loss": 0, "refused": 0}
    s.call(
        "POST",
        JOB + "/confirm",
        path={"job_id": job["id"]},
        body={
            "expectedVersion": summary["expectedVersion"],
            "expectedFeedPosition": summary["feedPosition"],
        },
        status=202,
    )
    done = _wait(s, job["id"])
    assert done["state"] == "completed", done
    now = s.call("GET", "/api/v1/workspaces/{workspace_key}/model", path=WS, status=200)
    assert now["releaseId"] == third["id"]
    s.call(
        "POST",
        "/api/v1/workspaces/{workspace_key}/model/migrations",
        path=WS,
        body={"targetReleaseId": third["id"], "expectedVersion": now["version"]},
        status=422,
        code="MIGRATION_TARGET_IS_CURRENT",
    )

    # A spare release: a model of another domain, installed, brought up to the present schema,
    # retired and deleted; and a spare draft, deleted.
    spare_draft = s.call(
        "POST",
        "/api/v1/model-drafts",
        body={"name": "Spare", "model": inventory_model()},
        status=201,
    )
    spare = s.call(
        "POST",
        DRAFT + "/installation",
        path={"draft_id": spare_draft["id"]},
        body={"expectedVersion": spare_draft["version"]},
        status=201,
    )
    _stage_old_schema(s, spare["id"])
    preview = s.call(
        "POST",
        RELEASE + "/raising",
        path={"release_id": spare["id"]},
        body={"confirm": False},
        status=200,
    )
    assert preview["applied"] is False and preview["schemaFrom"] == "0.9"
    raised = s.call(
        "POST",
        RELEASE + "/raising",
        path={"release_id": spare["id"]},
        body={"confirm": True, "expectedModelHash": preview["modelHash"]},
        status=200,
        record="aReleaseOfAnEarlierSchema",
        summary="Bring a release stored in an earlier schema up to the present one",
    )
    assert raised["applied"] is True and raised["schemaTo"] == "0.10"
    s.call(
        "POST",
        RELEASE + "/raising",
        path={"release_id": spare["id"]},
        body={"confirm": False},
        status=422,
        code="RELEASE_NOT_RAISABLE",
    )
    retired = s.call(
        "PATCH",
        RELEASE,
        path={"release_id": spare["id"]},
        body={"status": "retired", "expectedStatusVersion": spare["statusVersion"]},
        status=200,
        record="retire",
        summary="Retire the spare release: it can no longer be chosen",
    )
    assert retired["status"] == "retired" and retired["statusVersion"] == 2
    s.call(
        "DELETE",
        RELEASE,
        path={"release_id": third["id"]},
        query={"expectedStatusVersion": third["statusVersion"]},
        status=409,
        code="MODEL_RELEASE_IN_USE",
    )
    s.call(
        "DELETE",
        RELEASE,
        path={"release_id": spare["id"]},
        query={"expectedStatusVersion": retired["statusVersion"]},
        status=204,
        record="spare",
        summary="Delete the spare release; nothing referred to it",
    )
    s.call(
        "GET", RELEASE, path={"release_id": spare["id"]}, status=404, code="MODEL_RELEASE_NOT_FOUND"
    )
    scratch = s.call(
        "POST",
        "/api/v1/model-drafts",
        body={"name": "Scratch", "model": inventory_model("2.0.0")},
        status=201,
    )
    s.call(
        "DELETE",
        DRAFT,
        path={"draft_id": scratch["id"]},
        query={"expectedVersion": scratch["version"] + 1},
        status=409,
        code="VERSION_CONFLICT",
    )
    s.call(
        "DELETE",
        DRAFT,
        path={"draft_id": scratch["id"]},
        query={"expectedVersion": scratch["version"]},
        status=204,
        record="scratch",
        summary="Delete a draft nobody needs",
    )
    s.call("GET", DRAFT, path={"draft_id": scratch["id"]}, status=404)
