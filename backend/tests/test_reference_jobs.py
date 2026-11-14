"""The ``jobs``, ``imports`` and ``source files`` areas of the management API's reference, recorded from a
run on the guide's reference data (see ``test_reference_recording.py``, whose seed, scenario and
normaliser this file uses).

An integrator who keeps the Graubünden stop list adds stops in a batch, previews and confirms one, and
cancels another; exports the stops to read them back; and loads the fictional bus company's stop list
(``guide/samples/Haltestellen_Busbetrieb_Nord.xlsx``) through an import profile: the profile is saved, the
workbook is stored and profiled, the import is previewed, its rejected rows read and the import
confirmed. The next version of the workbook, a copy changed here, is stored and checked against the data
the first one loaded. A second import, of a small CSV file made here, is read again with another field.
Each step records the main successful use of the operation it calls; the refusals the areas' text names
are asserted without being recorded. Every job is followed to its end.

    cd backend && RDM_RECORD_EXAMPLES=1 .venv/bin/python -m pytest tests/test_reference_jobs.py -q
"""

import json
import time
from collections.abc import Iterator
from pathlib import Path
from uuid import uuid4

import pytest
import seeds
from test_reference_recording import (
    BASE,
    RECORDING,
    SAMPLES,
    SEED,
    Scenario,
    _application,
    _register_seed,
)

WORKBOOK = SAMPLES / "Haltestellen_Busbetrieb_Nord.xlsx"
XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
JOB = "/api/v1/jobs/{job_id}"
PROFILE = "/api/v1/import-profiles/{profile_key}"
SOURCE = "/api/v1/source-files/{source_file_id}"
WS = {"workspaceKey": "graubuenden"}
WS_PATH = {"workspace_key": "graubuenden"}
FINAL = ("completed", "failed", "cancelled", "expired")
# The workbook's date column as text, and the words for "no value" in it, mapped to what the model holds.
DATES = {
    "?": None,
    "n/a": None,
    "01.04.2021": "2021-04-01",
    "12.05.2021": "2021-05-12",
    "09.03.2022": "2022-03-09",
    "11.12.2022": "2022-12-11",
    "10.12.2023": "2023-12-10",
    "15.12.2024": "2024-12-15",
    "09.08.2025": "2025-08-09",
    "03.06.2026": "2026-06-03",
    "01.08.2026": "2026-08-01",
}

BUS_STOPS = {
    "key": "bus-stops-north",
    "name": "Bus stops, Busbetrieb Nord",
    "workspaceKey": "graubuenden",
    "sources": [
        {
            "sheet": "Haltestellen",
            "headerRow": 3,
            "applicationKey": "network",
            "objectTypeKey": "stop",
            "key": {"attributeTypeKey": "stop-number"},
            "columns": [
                {"column": "Haltestelle", "field": "name"},
                {"column": "Haltestelle", "attributeTypeKey": "designation"},
                {"column": "UIC-Nr", "attributeTypeKey": "stop-number"},
                {"column": "gültig ab", "attributeTypeKey": "valid-from", "valueMap": "dates"},
                {
                    "column": "Gemeinde",
                    "valueMap": "municipalities",
                    "parent": {"objectTypeKey": "municipality", "matchBy": {"field": "name"}},
                },
            ],
        }
    ],
    "valueMaps": {"dates": DATES, "municipalities": {"Coira": "Chur", "Cuira": "Chur"}},
}


@pytest.fixture(scope="module")
def jobs(tmp_path_factory) -> Iterator[Scenario]:
    _register_seed()
    seeds.ensure(SEED)
    url = seeds.clone(SEED)
    try:
        with _application(url) as client:
            scenario = Scenario(client)
            scenario.scratch = tmp_path_factory.mktemp("reference-jobs")
            yield scenario
            if RECORDING:
                scenario.write_examples()
    finally:
        seeds.drop(url.database)


def _wait(s: Scenario, job_id: str, *states: str, seconds: float = 180) -> dict:
    """Follow a job until it is in one of ``states`` (a final one by default)."""
    wanted = states or FINAL
    deadline = time.monotonic() + seconds
    while True:
        job = s.call("GET", JOB, path={"job_id": job_id}, status=200)
        if job["state"] in wanted:
            return job
        assert time.monotonic() < deadline, job
        time.sleep(0.25)


def _upload(
    s: Scenario,
    route: str,
    request: dict,
    file: Path,
    *,
    status: int,
    record: str | None = None,
    summary: str = "",
    query: dict | None = None,
    headers: dict | None = None,
    notes: list[str] | None = None,
    content_type: str = XLSX,
    code: str | None = None,
) -> dict:
    """A multipart request: the file and its ``request`` part. The example records the response and
    names the parts in its notes, since the document shows a JSON body only."""
    url = route
    if query:
        url += "?" + "&".join(f"{key}={value}" for key, value in query.items())
    with file.open("rb") as handle:
        response = s.client.post(
            url,
            data={"request": json.dumps(request)},
            files={"file": (file.name, handle, content_type)},
            headers={"Origin": BASE, "Authorization": "Bearer " + s.api.token, **(headers or {})},
        )
    out = response.json() if response.content else None
    assert response.status_code == status, (
        f"POST {url}: {response.status_code} {response.text[:600]}"
    )
    if code is not None:
        assert out["error"]["code"] == code, out
    if record:
        shown = [
            f"The request part: `{json.dumps(request)}`.",
            f"The file part: `{file.name}`.",
            *(notes or []),
        ]
        s._record("POST", route, record, summary, {}, query or {}, None, status, out, shown)
        if RECORDING:
            time.sleep(1.1)
    return out


def _stop(ref: str, name: str, number: int, **more) -> dict:
    """A create or upsert item for a stop of Chur."""
    return {
        "ref": ref,
        "applicationKey": "network",
        "objectTypeKey": "stop",
        "name": name,
        "parent": {
            "objectTypeKey": "municipality",
            "key": {"attributeTypeKey": "fso-number", "value": 3901},
        },
        "attributes": [
            {"attributeTypeKey": "designation", "value": name},
            {"attributeTypeKey": "stop-number", "value": number},
        ],
        **more,
    }


def _stop_version(s: Scenario, stop_id: str) -> int:
    return s.call(
        "GET",
        "/api/v1/objects/{object_type_key}/{object_id}",
        path={"object_type_key": "stop", "object_id": stop_id},
        status=200,
    )["version"]


def test_stops_are_added_in_a_batch_exported_changed_and_a_preview_discarded(jobs):
    s = jobs
    first = str(uuid4())
    key = {"Idempotency-Key": "chur-stops-2027-01"}
    request = {
        "workspaceKey": "graubuenden",
        "policy": "independent",
        "run": "inline",
        "onExisting": "reject",
        "items": [
            _stop("stop-1", "Chur, Stadtbibliothek", 8599001, op="create", id=first),
            _stop(
                "stop-2",
                "Chur, Kantonsschule",
                8599002,
                op="upsert",
                key={"attributeTypeKey": "stop-number"},
            ),
            {
                "ref": "stop-1-bus",
                "op": "ensureRelation",
                "relationTypeKey": "stop-served-by-mode",
                "from": {"id": first},
                "to": {
                    "objectTypeKey": "mode",
                    "key": {"attributeTypeKey": "mode-code", "value": "BUS"},
                },
            },
        ],
    }
    batch = s.call(
        "POST",
        "/api/v1/batches",
        body=request,
        status=200,
        headers=key,
        record="threeKinds",
        summary="Two new stops, one by ID and one by key, and the first served by the bus",
        notes=["Sent with the header `Idempotency-Key: chur-stops-2027-01`."],
    )
    assert batch["job"]["result"] == "applied" and batch["job"]["counts"]["created"] == 3
    assert [item["status"] for item in batch["items"]] == ["applied"] * 3
    stop_1, stop_2 = batch["items"][0], batch["items"][1]
    # The same key and request answer the first job again; another request under it is refused.
    again = s.client.post(
        "/api/v1/batches",
        json=request,
        headers={"Origin": BASE, "Authorization": "Bearer " + s.api.token, **key},
    )
    assert again.status_code == 200 and again.headers["Idempotent-Replayed"] == "true"
    assert again.json()["job"]["id"] == batch["job"]["id"]
    s.call(
        "POST",
        "/api/v1/batches",
        body={**request, "policy": "atomic"},
        status=422,
        code="IDEMPOTENCY_KEY_REUSED",
        headers=key,
    )
    s.call(
        "POST",
        "/api/v1/batches",
        body={**request, "stage": "preview"},
        status=422,
        code="REQUEST_VALIDATION_ERROR",
    )

    # Export what the batch added, and follow and read the export.
    export = s.call(
        "POST",
        "/api/v1/exports",
        body={
            "workspaceKey": "graubuenden",
            "scope": {
                "types": [
                    {
                        "objectTypeKey": "stop",
                        "where": [{"field": "stop-number", "op": "gte", "value": 8599000}],
                    }
                ]
            },
            "include": {"relations": "withinScope"},
            "format": "jsonl",
        },
        status=202,
        record="newStops",
        summary="The stops numbered from 8599000, as JSON Lines",
    )
    assert export["kind"] == "export" and export["state"] in ("queued", "running", "completed")
    done = _wait(s, export["id"])
    assert done["state"] == "completed" and done["output"]["counts"]["records"] == {"stop": 2}
    s.call(
        "GET",
        JOB + "/events",
        path={"job_id": export["id"]},
        status=200,
        record="finishedExport",
        summary="A finished export: one event, then the stream ends",
    )
    file = s.call(
        "GET",
        JOB + "/output",
        path={"job_id": export["id"]},
        status=200,
        record="newStopsFile",
        summary="The export's file: a batch item per line",
    )
    assert "upsert" in file["raw"]
    s.call(
        "GET",
        JOB + "/output",
        path={"job_id": batch["job"]["id"]},
        status=404,
        code="JOB_HAS_NO_OUTPUT",
    )
    s.call(
        "GET",
        JOB + "/rows",
        path={"job_id": batch["job"]["id"]},
        status=404,
        code="JOB_HAS_NO_ROWS",
    )
    s.call(
        "POST",
        JOB + "/cancel",
        path={"job_id": batch["job"]["id"]},
        status=409,
        code="JOB_FINISHED",
    )

    # A background batch changes one stop and removes the other.
    queued = s.call(
        "POST",
        "/api/v1/batches",
        body={
            "workspaceKey": "graubuenden",
            "policy": "atomic",
            "run": "background",
            "items": [
                {
                    "ref": "rename",
                    "op": "update",
                    "target": {"id": first},
                    "expectedVersion": stop_1["version"],
                    "name": "Chur, Stadtbibliothek (Süd)",
                },
                {
                    "ref": "remove",
                    "op": "delete",
                    "target": {"id": stop_2["id"]},
                    "expectedVersion": stop_2["version"],
                },
            ],
        },
        status=202,
    )
    assert queued["kind"] == "batch" and queued["state"] == "queued"
    finished = _wait(s, queued["id"])
    assert finished["state"] == "completed" and finished["result"] == "applied"
    s.call(
        "GET",
        JOB,
        path={"job_id": queued["id"]},
        status=200,
        record="backgroundBatch",
        summary="A background batch that ran to its end",
    )
    items = s.call(
        "GET",
        JOB + "/items",
        path={"job_id": queued["id"]},
        query={"pageSize": 2},
        status=200,
        record="outcomes",
        summary="What happened to each item, in item order",
    )
    assert [item["action"] for item in items["items"]] == ["updated", "deleted"]
    refused = s.call(
        "GET",
        JOB + "/items",
        path={"job_id": batch["job"]["id"]},
        query={"status": "rejected"},
        status=200,
    )
    assert refused["items"] == []

    # A preview shows what a batch would do and waits; it is discarded without writing anything.
    preview = s.call(
        "POST",
        "/api/v1/batches",
        body={
            "workspaceKey": "graubuenden",
            "policy": "independent",
            "run": "background",
            "stage": "preview",
            "items": [
                {
                    "ref": "rename-library",
                    "op": "update",
                    "target": {"id": first},
                    "expectedVersion": _stop_version(s, first),
                    "name": "Chur, Stadtbibliothek (Nord)",
                }
            ],
        },
        status=202,
    )
    waiting = _wait(s, preview["id"], "awaiting_confirmation", *FINAL)
    assert waiting["state"] == "awaiting_confirmation" and waiting["preview"]["result"] == "applied"
    cancelled = s.call(
        "POST",
        JOB + "/cancel",
        path={"job_id": preview["id"]},
        status=202,
        record="waitingPreview",
        summary="A preview that waits for confirmation is cancelled at once",
    )
    assert cancelled["state"] == "cancelled"
    assert _stop_version(s, first) == 2


def export_id(s: Scenario) -> str:
    """The first export job of the scenario."""
    return s.call("GET", "/api/v1/jobs", query={"kind": "export"}, status=200)["items"][-1]["id"]


def _next_version(scratch: Path) -> Path:
    """The workbook as its next version: a column renamed, a stop renamed and a stop left out."""
    import openpyxl

    book = openpyxl.load_workbook(WORKBOOK)
    sheet = book["Haltestellen"]
    sheet["E3"] = "gültig seit"
    for row in sheet.iter_rows(min_row=4):
        if row[3].value is not None and str(row[3].value).strip() == "8510601":
            row[0].value = "Domat/Ems, Ardisla Nord"
        if row[3].value is not None and str(row[3].value).strip() == "8512788":
            sheet.delete_rows(row[0].row)
            break
    target = scratch / "Haltestellen_Busbetrieb_Nord_Winter.xlsx"
    book.save(target)
    return target


def test_a_workbook_is_loaded_through_a_profile_and_the_next_one_is_checked(jobs):
    s = jobs
    s.call("POST", "/api/v1/import-profiles", body={**BUS_STOPS, "key": "dup"}, status=201)
    s.call(
        "POST",
        "/api/v1/import-profiles",
        body={**BUS_STOPS, "key": "dup"},
        status=409,
        code="IMPORT_PROFILE_EXISTS",
    )
    s.call(
        "DELETE",
        PROFILE,
        path={"profile_key": "dup"},
        query={"expectedVersion": 2},
        status=409,
        code="VERSION_CONFLICT",
    )
    s.call(
        "DELETE",
        PROFILE,
        path={"profile_key": "dup"},
        query={"expectedVersion": 1},
        status=204,
        record="unused",
        summary="Delete a profile at the version read",
    )
    made = s.call(
        "POST",
        "/api/v1/import-profiles",
        body=BUS_STOPS,
        status=201,
        record="busStops",
        summary="A profile for the bus company's stop list, saved against the Graubünden workspace's release",
    )
    assert made["valid"] is True and made["version"] == 1 and made["lastLoad"] is None
    listed = s.call(
        "GET",
        "/api/v1/import-profiles",
        query={"pageSize": 5, "workspaceKey": "graubuenden"},
        status=200,
        record="inKeyOrder",
        summary="The instance's profiles in key order",
    )
    assert [item["key"] for item in listed["items"]] == ["bus-stops-north"]
    s.call(
        "GET",
        PROFILE,
        path={"profile_key": "bus-stops-north"},
        query={"workspaceKey": "graubuenden"},
        status=200,
        record="busStops",
        summary="The profile as it reads under the workspace's release",
    )
    s.call(
        "GET", PROFILE, path={"profile_key": "nothing"}, status=404, code="IMPORT_PROFILE_NOT_FOUND"
    )

    # Store the workbook for the profile and read what its profile says.
    stored = _upload(
        s,
        "/api/v1/source-files",
        {"owner": {"profileKey": "bus-stops-north"}, "workspaceKey": "graubuenden"},
        WORKBOOK,
        status=201,
        record="busStopsWorkbook",
        summary="The bus company's workbook, stored for the profile and queued for profiling",
    )
    assert stored["version"] == 1 and stored["profile"]["state"] in (
        "queued",
        "running",
        "completed",
    )
    _wait(s, stored["profile"]["jobId"])
    s.call(
        "GET",
        "/api/v1/source-files",
        query={"profileKey": "bus-stops-north", "pageSize": 5},
        status=200,
        record="ofTheProfile",
        summary="The profile's files, newest first",
    )
    s.call(
        "GET",
        SOURCE,
        path={"source_file_id": stored["id"]},
        status=200,
        record="busStopsWorkbook",
        summary="The stored file once its profile is complete",
    )
    sheets = s.call(
        "GET",
        SOURCE + "/profile/sheets",
        path={"source_file_id": stored["id"]},
        query={"pageSize": 3},
        status=200,
        record="workbookSheets",
        summary="The workbook's sheets with their blocks",
    )
    assert [sheet["name"] for sheet in sheets["items"]] == ["Haltestellen", "Namen", "Lokale Codes"]
    s.call(
        "GET",
        SOURCE + "/profile/sheets/{sheet}/columns",
        path={"source_file_id": stored["id"], "sheet": "Haltestellen"},
        query={"pageSize": 3},
        status=200,
        record="stopColumns",
        summary="The first columns of the Haltestellen sheet with their statistics",
    )
    s.call(
        "GET",
        SOURCE + "/profile/sheets/{sheet}/cells",
        path={"source_file_id": stored["id"], "sheet": "Haltestellen"},
        query={"range": "A3:D6", "pageSize": 4},
        status=200,
        record="headerAndFirstRows",
        summary="The header and the first rows of the sheet as an import reads them",
    )
    s.call(
        "GET",
        SOURCE + "/profile/sheets/{sheet}/columns",
        path={"source_file_id": stored["id"], "sheet": "Nope"},
        status=404,
        code="SOURCE_SHEET_NOT_FOUND",
    )
    s.call(
        "GET", SOURCE, path={"source_file_id": "missing"}, status=404, code="SOURCE_FILE_NOT_FOUND"
    )

    # Preview the import: the rows of one municipality that does not exist are refused.
    preview = _upload(
        s,
        "/api/v1/imports",
        {
            "workspaceKey": "graubuenden",
            "profileKey": "bus-stops-north",
            "policy": "independent",
            "onExisting": "reject",
            "stage": "preview",
        },
        WORKBOOK,
        status=202,
        record="previewTheWorkbook",
        summary="The workbook sent through the profile, as a preview that writes nothing",
    )
    assert preview["kind"] == "import" and preview["stage"] in (None, "binding", "previewing")
    waiting = _wait(s, preview["id"], "awaiting_confirmation", *FINAL)
    assert waiting["state"] == "awaiting_confirmation"
    assert waiting["preview"]["rows"] == {"total": 51, "previewed": 51, "rejected": 6}
    assert waiting["preview"]["counts"]["created"] >= 45
    rejected = s.call(
        "GET",
        JOB + "/rows",
        path={"job_id": preview["id"]},
        query={"status": "rejected", "pageSize": 2},
        status=200,
        record="rejectedRows",
        summary="The rows the preview refused, in file order",
    )
    assert {row["outcomes"][0]["error"]["code"] for row in rejected["items"]} == {
        "REFERENCE_NOT_FOUND"
    }
    s.call(
        "GET",
        JOB + "/rows",
        path={"job_id": preview["id"]},
        query={"status": "loss"},
        status=422,
        code="INVALID_PAGE_PARAMETER",
    )
    one_row = s.call(
        "GET",
        JOB + "/items",
        path={"job_id": preview["id"]},
        query={"ref": "Haltestellen!4"},
        status=200,
    )
    assert one_row["items"] and one_row["items"][0]["ref"] == "Haltestellen!4"
    s.call(
        "POST",
        JOB + "/confirm",
        path={"job_id": preview["id"]},
        status=202,
        record="importPreview",
        summary="Confirm the preview: the import runs from the stored file",
    )
    done = _wait(s, preview["id"])
    assert done["state"] == "completed" and done["result"] == "partial", done
    assert done["counts"]["created"] == 45 and done["counts"]["rejected"] == 6, done["counts"]
    # Confirming again answers with the job as it is; a job that waits for nothing is refused.
    again = s.call("POST", JOB + "/confirm", path={"job_id": preview["id"]}, status=202)
    assert again["confirmedAt"] == done["confirmedAt"]
    s.call(
        "POST",
        JOB + "/confirm",
        path={"job_id": export_id(s)},
        status=409,
        code="JOB_NOT_AWAITING_CONFIRMATION",
    )
    s.call(
        "GET",
        "/api/v1/jobs",
        query={"workspaceKey": "graubuenden", "state": "completed", "pageSize": 2},
        status=200,
        record="newestFinished",
        summary="The workspace's finished jobs, the newest first",
    )
    s.call(
        "GET",
        "/api/v1/jobs",
        query={"workspaceKey": "graubuenden", "kind": "import"},
        status=200,
    )
    profile_after = s.call("GET", PROFILE, path={"profile_key": "bus-stops-north"}, status=200)
    assert profile_after["lastLoad"]["counts"] == {
        "created": 45,
        "updated": 0,
        "deleted": 0,
        "rejected": 6,
    }

    # The next version of the workbook is stored and checked against what the first one loaded.
    winter = _next_version(s.scratch)
    second = _upload(
        s,
        "/api/v1/source-files",
        {"owner": {"profileKey": "bus-stops-north"}, "workspaceKey": "graubuenden"},
        winter,
        status=201,
    )
    _wait(s, second["profile"]["jobId"])
    check = s.call(
        "POST",
        PROFILE + "/check",
        path={"profile_key": "bus-stops-north"},
        query={"workspaceKey": "graubuenden"},
        status=202,
        record="winterWorkbook",
        summary="Check the stored file of the profile again",
    )
    assert check["state"] == "checking"
    _wait(s, check["jobId"])
    report = s.call(
        "GET",
        PROFILE + "/check",
        path={"profile_key": "bus-stops-north"},
        query={"workspaceKey": "graubuenden"},
        status=200,
        record="winterWorkbook",
        summary="What the next workbook changes: a renamed column and what the load would do",
    )
    assert report["sources"][0]["columns"]["renamed"][0]["to"] == "gültig seit"
    for tail in ("new-values", "drift", "missing-records"):
        found = s.call(
            "GET",
            PROFILE + "/check/" + tail,
            path={"profile_key": "bus-stops-north"},
            query={"workspaceKey": "graubuenden", "pageSize": 2},
            status=200,
            record="winterWorkbook",
            summary="The check's findings",
        )
        assert found["items"], tail
    s.call(
        "GET",
        PROFILE + "/check/rows",
        path={"profile_key": "bus-stops-north"},
        query={"workspaceKey": "graubuenden", "status": "rejected", "pageSize": 2},
        status=200,
        record="winterWorkbook",
        summary="The rows behind the check's figures",
    )

    # The profile follows the renamed column; the first file is deleted once the second is current.
    renamed = json.loads(json.dumps(BUS_STOPS).replace("gültig ab", "gültig seit"))
    updated = s.call(
        "PUT",
        PROFILE,
        path={"profile_key": "bus-stops-north"},
        body={
            "name": "Bus stops, Busbetrieb Nord (winter)",
            "expectedVersion": 1,
            "workspaceKey": "graubuenden",
            "sources": renamed["sources"],
            "valueMaps": renamed["valueMaps"],
        },
        status=200,
        record="busStops",
        summary="Replace the profile: its date column now has the new header",
    )
    assert updated["version"] == 2 and updated["valid"] is True
    s.call(
        "PUT",
        PROFILE,
        path={"profile_key": "bus-stops-north"},
        body={"name": "Late", "expectedVersion": 1, "sources": renamed["sources"]},
        status=409,
        code="VERSION_CONFLICT",
    )
    s.call(
        "DELETE",
        SOURCE,
        path={"source_file_id": stored_first_id(s)},
        query={"expectedVersion": 1},
        status=204,
        record="superseded",
        summary="Delete the first workbook, which the second superseded",
    )
    s.call(
        "GET",
        SOURCE,
        path={"source_file_id": stored_first_id(s, missing=True)},
        status=404,
        code="SOURCE_FILE_NOT_FOUND",
    )


def stored_first_id(s: Scenario, missing: bool = False) -> str:
    """The profile's first stored file (the oldest), or its ID after it was deleted."""
    if missing:
        return s.first_file
    found = s.call(
        "GET", "/api/v1/source-files", query={"profileKey": "bus-stops-north"}, status=200
    )["items"][-1]
    s.first_file = found["id"]
    return found["id"]


def test_a_preview_is_read_again_with_another_field(jobs):
    s = jobs
    csv = s.scratch / "Verkehrsmittel.csv"
    csv.write_text(
        "UIC-Nr,Verkehrsmittel\n8571924,BUS\n8595591,BUS\n8571710,TRAM\n", encoding="utf-8"
    )
    request = {
        "workspaceKey": "graubuenden",
        "profile": {
            "sources": [
                {
                    "applicationKey": "network",
                    "objectTypeKey": "stop",
                    "record": "existing",
                    "key": {"attributeTypeKey": "stop-number"},
                    "columns": [
                        {"column": "UIC-Nr", "attributeTypeKey": "stop-number"},
                        {
                            "column": "Verkehrsmittel",
                            "relation": {
                                "relationTypeKey": "stop-served-by-mode",
                                "objectTypeKey": "mode",
                                "matchBy": {"field": "name"},
                            },
                        },
                    ],
                }
            ]
        },
        "format": "csv",
        "policy": "independent",
        "stage": "preview",
    }
    first = _upload(s, "/api/v1/imports", request, csv, status=202, content_type="text/csv")
    waiting = _wait(s, first["id"], "awaiting_confirmation", *FINAL)
    assert waiting["state"] == "awaiting_confirmation"
    report = waiting["bindingReport"][0]["columns"][1]
    assert report["notFound"] == 3, report
    again = s.call(
        "POST",
        JOB + "/reread",
        path={"job_id": first["id"]},
        body={"readings": [{"source": 0, "column": "Verkehrsmittel", "field": "mode-code"}]},
        status=202,
        record="readByModeCode",
        summary="Read the file again with the modes found by their code instead of their name",
    )
    assert again["id"] != first["id"] and again["stage"] in (None, "binding", "previewing")
    assert _wait(s, first["id"])["state"] == "cancelled"
    ready = _wait(s, again["id"], "awaiting_confirmation", *FINAL)
    assert ready["state"] == "awaiting_confirmation"
    assert ready["bindingReport"][0]["columns"][1]["resolved"] == 3
    s.call(
        "POST",
        JOB + "/reread",
        path={"job_id": first["id"]},
        body={"readings": [{"source": 0, "column": "Verkehrsmittel", "field": "name"}]},
        status=409,
        code="JOB_NOT_AWAITING_CONFIRMATION",
    )
    s.call("POST", JOB + "/cancel", path={"job_id": again["id"]}, status=202)
    assert _wait(s, again["id"])["state"] == "cancelled"
    waiting_now = s.call(
        "GET", "/api/v1/jobs", query={"state": "awaiting_confirmation"}, status=200
    )
    assert waiting_now["items"] == []
    running = [
        job
        for state in ("queued", "running")
        for job in s.call("GET", "/api/v1/jobs", query={"state": state}, status=200)["items"]
    ]
    assert running == []


def test_the_refusals_the_text_names(jobs):
    s = jobs
    batch = "/api/v1/batches"
    item = {
        "op": "ensureNoRelation",
        "relationTypeKey": "stop-served-by-mode",
        "from": {"id": str(uuid4())},
        "to": {"id": str(uuid4())},
    }
    base = {"policy": "independent", "run": "inline", "items": [item]}
    s.call("POST", batch, body=base, status=422, code="INVALID_BATCH_CONTEXT")
    cs = s.call(
        "POST",
        "/api/v1/workspaces/{workspace_key}/change-sets",
        path=WS_PATH,
        body={"name": "Refusals", "source": "currentLive"},
        status=201,
    )
    s.call(
        "POST",
        batch,
        body={**base, "changeSetId": cs["id"]},
        status=409,
        code="CHANGE_SET_REQUIRED",
    )
    s.call(
        "POST",
        batch,
        body={**base, "changeSetId": cs["id"], "expectedChangeSetVersion": 9},
        status=409,
        code="CHANGE_SET_VERSION_CONFLICT",
    )
    s.call(
        "POST",
        batch,
        body={**base, "changeSetId": cs["id"], "expectedChangeSetVersion": 9, "run": "background"},
        status=409,
        code="CHANGE_SET_VERSION_CONFLICT",
    )
    s.call(
        "POST",
        batch,
        body={
            **base,
            "workspaceKey": "graubuenden",
            "changeSetId": cs["id"],
            "expectedChangeSetVersion": 1,
        },
        status=422,
        code="INVALID_BATCH_CONTEXT",
    )
    s.call(
        "DELETE",
        "/api/v1/change-sets/{change_set_id}",
        path={"change_set_id": cs["id"]},
        query={"expectedVersion": cs["version"]},
        status=204,
    )
    s.call(
        "POST",
        batch,
        body={**base, "changeSetId": str(uuid4()), "expectedChangeSetVersion": 1},
        status=404,
        code="CHANGE_SET_NOT_FOUND",
    )
    s.call(
        "POST",
        batch,
        body={**base, "workspaceKey": "nowhere"},
        status=404,
        code="WORKSPACE_NOT_FOUND",
    )
    s.call(
        "POST",
        "/api/v1/jobs/{job_id}/cancel",
        path={"job_id": str(uuid4())},
        status=404,
        code="JOB_NOT_FOUND",
    )
    s.call("GET", "/api/v1/jobs", query={"origin": "other"}, status=422, code="INVALID_ORIGIN")

    export = {
        "workspaceKey": "graubuenden",
        "scope": {"types": [{"objectTypeKey": "stop"}]},
        "format": "jsonl",
    }
    s.call(
        "POST",
        "/api/v1/exports",
        body={**export, "workspaceKey": "nowhere"},
        status=404,
        code="WORKSPACE_NOT_FOUND",
    )
    s.call(
        "POST",
        "/api/v1/exports",
        body={**export, "scope": {"types": [{"objectTypeKey": "nothing"}]}},
        status=422,
        code="INVALID_QUERY",
    )
    s.call(
        "POST",
        "/api/v1/exports",
        body={
            **export,
            "scope": {"types": [{"objectTypeKey": "stop"}], "parentObjectId": str(uuid4())},
        },
        status=404,
        code="PARENT_NOT_FOUND",
    )
    s.call(
        "POST",
        "/api/v1/exports",
        body={**export, "context": {"changeSetId": str(uuid4())}},
        status=404,
        code="CHANGE_SET_NOT_FOUND",
    )
    s.call(
        "POST",
        "/api/v1/exports",
        body={**export, "context": {"publicationId": str(uuid4())}},
        status=404,
        code="PUBLICATION_NOT_FOUND",
    )
    s.call(
        "POST",
        "/api/v1/exports",
        body={**export, "format": "csv", "layout": "people", "people": {"columns": ["nothing"]}},
        status=422,
        code="INVALID_EXPORT_LAYOUT",
    )

    check = PROFILE + "/check"
    s.call(
        "POST",
        check,
        path={"profile_key": "bus-stops-north"},
        query={"workspaceKey": "nowhere"},
        status=404,
        code="SOURCE_FILE_NOT_FOUND",
    )
    s.call(
        "GET",
        check,
        path={"profile_key": "bus-stops-north"},
        query={"workspaceKey": "nowhere"},
        status=404,
        code="PROFILE_CHECK_NOT_FOUND",
    )
    s.call(
        "GET",
        check,
        path={"profile_key": "nothing"},
        query={"workspaceKey": "graubuenden"},
        status=404,
        code="IMPORT_PROFILE_NOT_FOUND",
    )
    s.call(
        "GET",
        "/api/v1/import-profiles",
        query={"workspaceKey": "nowhere"},
        status=404,
        code="WORKSPACE_NOT_FOUND",
    )
    s.call(
        "GET",
        PROFILE,
        path={"profile_key": "bus-stops-north"},
        query={"workspaceKey": "nowhere"},
        status=404,
        code="WORKSPACE_NOT_FOUND",
    )
    s.call(
        "POST",
        "/api/v1/import-profiles",
        body={**BUS_STOPS, "key": "elsewhere", "workspaceKey": "nowhere"},
        status=404,
        code="WORKSPACE_NOT_FOUND",
    )
    bad = json.loads(json.dumps(BUS_STOPS))
    bad["key"] = "broken"
    bad["sources"][0]["objectTypeKey"] = "nothing"
    refused = s.call(
        "POST", "/api/v1/import-profiles", body=bad, status=422, code="INVALID_IMPORT_PROFILE"
    )
    assert refused["error"]["details"]["problems"]

    # The file part and a stored file are alternatives; unknown things are 404.
    sources = "/api/v1/source-files"
    request = {"owner": {"profileKey": "bus-stops-north"}, "workspaceKey": "graubuenden"}
    _upload(
        s,
        sources,
        {"owner": {"draftId": "nothing"}},
        WORKBOOK,
        status=404,
        code="MODEL_DRAFT_NOT_FOUND",
    )
    _upload(
        s,
        sources,
        {"owner": {"profileKey": "nothing"}},
        WORKBOOK,
        status=404,
        code="IMPORT_PROFILE_NOT_FOUND",
    )
    _upload(
        s,
        sources,
        {**request, "workspaceKey": "nowhere"},
        WORKBOOK,
        status=404,
        code="WORKSPACE_NOT_FOUND",
    )
    _upload(
        s,
        sources,
        {"owner": {"draftId": "a", "profileKey": "b"}},
        WORKBOOK,
        status=422,
        code="REQUEST_VALIDATION_ERROR",
    )
    _upload(
        s, sources, request, s.scratch / "Verkehrsmittel.csv", status=201, content_type="text/csv"
    )
    odd = s.scratch / "notes.txt"
    odd.write_text("x")
    _upload(
        s,
        sources,
        request,
        odd,
        status=422,
        content_type="text/plain",
        code="UNSUPPORTED_FILE_FORMAT",
    )
    imports = "/api/v1/imports"
    run = {"workspaceKey": "graubuenden", "policy": "independent", "stage": "preview"}
    _upload(
        s,
        imports,
        {**run, "profileKey": "nothing"},
        WORKBOOK,
        status=404,
        code="IMPORT_PROFILE_NOT_FOUND",
    )
    _upload(
        s,
        imports,
        {**run, "profileKey": "bus-stops-north", "sourceFileId": "nothing"},
        WORKBOOK,
        status=422,
        code="REQUEST_VALIDATION_ERROR",
    )
    _upload(
        s,
        imports,
        {**run, "workspaceKey": "nowhere", "profileKey": "bus-stops-north"},
        WORKBOOK,
        status=404,
        code="WORKSPACE_NOT_FOUND",
    )
    _upload(
        s, imports, run, odd, status=422, content_type="text/plain", code="UNSUPPORTED_FILE_FORMAT"
    )
    page = s.call("GET", sources, query={"profileKey": "bus-stops-north"}, status=200)
    stale = page["items"][0]
    s.call(
        "DELETE",
        SOURCE,
        path={"source_file_id": stale["id"]},
        query={"expectedVersion": 9},
        status=409,
        code="VERSION_CONFLICT",
    )
    s.call(
        "DELETE",
        SOURCE,
        path={"source_file_id": stale["id"]},
        query={"expectedVersion": stale["version"]},
        status=204,
    )
