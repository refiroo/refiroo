"""J27 — Exchange a supplier file: the export (USER_JOURNEYS.md, 0.9 J1).

Each test writes in a workspace of its own, so its counts and its feed are its own. The journey
application runs no worker thread; a test runs the engine's export worker itself (``_run``). A file
is read back as a client reads it: JSON Lines line by line, CSV with the ``csv`` module and XLSX with
openpyxl.
"""

import base64
import csv
import hashlib
import io
import json
from uuid import uuid4

import pytest
from openpyxl import load_workbook
from scenario import ok, refused
from sqlalchemy import create_engine, text
from sqlalchemy.pool import NullPool

from app.engine.jobs import exports as exports_module

XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def _workspace(world):
    key = f"export-{uuid4().hex[:8]}"
    ok(world.api.post("/workspaces", {"key": key, "label": "Export site"}), 201)
    return key


def _export(world, workspace, types, **body):
    request = {
        "workspaceKey": workspace,
        "scope": {"types": types, **body.pop("scope", {})},
        "format": body.pop("format", "jsonl"),
        **body,
    }
    return world.api.post("/exports", request)


def _run(world):
    return world.api.client.app.state.export_worker.run_until_idle()


def _finished(world, workspace, types, **body):
    job = ok(_export(world, workspace, types, **body), 202)
    assert job["kind"] == "export" and job["state"] == "queued"
    _run(world)
    return ok(world.api.get(f"/jobs/{job['id']}"))


def _download(world, job):
    response = world.api.get(f"/jobs/{job['id']}/output")
    assert response.status_code == 200, response.text
    return response


def _lines(world, job):
    return [json.loads(line) for line in _download(world, job).content.decode().splitlines()]


def _head(world, workspace):
    return ok(world.api.get(f"/workspaces/{workspace}/feed", pageSize=1))["headPosition"]


def _type(world, structure):
    return {"objectTypeKey": world.key(structure)}


def _ids(world, structure, **context):
    page = ok(world.api.get(f"/objects/{world.key(structure)}", pageSize=100, **context))
    return {item["id"] for item in page["items"]}


def _hierarchy(world, ws):
    """Three levels of H, two K tokens and the middle H related to both through Bnn."""
    top = world.made("H", "Export top", workspace=ws, values={"H.code": "XT"})
    middle = world.made("H", "Export middle", parent=top["id"], workspace=ws, values={"H.code": "XM"})
    leaf = world.made("H", "Export leaf", parent=middle["id"], workspace=ws, values={"H.code": "XL"})
    tokens = [
        world.made("K", f"Export token {n}", workspace=ws, values={"K.code": f"XK{n}"})
        for n in (1, 2)
    ]
    for weight, token in enumerate(tokens, start=1):
        ok(world.relate("Bnn", middle["id"], token["id"], {"Bnn.weight": weight}), 201)
    return top, middle, leaf, tokens


@pytest.mark.journey("J27", "J27.1")
@pytest.mark.structures("R", "R.n", "H", "H.code", "K", "K.code", "Bnn", "Bnn.weight", "Hparent")
def test_a_live_export_holds_the_stated_scope_parents_first_with_its_manifest(world):
    """Given a workspace with R records numbered 10 and 90, an H hierarchy three levels deep and two
    K tokens the middle H relates to. When R with a criterion on R.n above 50, H and K are exported
    as JSON Lines with the relationships whose ends are both exported. Then the job completes; the
    file holds one upsert per matching record, keyed by ID with its version, every parent before its
    children, then one ensureRelation per Bnn relationship and none for containment; the manifest
    counts them, names the live context and the feed head the export read at, and its size and
    SHA-256 match the downloaded file and its Repr-Digest."""
    ws = _workspace(world)
    world.made("R", "Low", workspace=ws, values={"R.n": 10})
    high = world.made("R", "High", workspace=ws, values={"R.n": 90})
    top, middle, leaf, tokens = _hierarchy(world, ws)
    head = _head(world, ws)

    criterion = {"field": world.key("R.n"), "op": "gt", "value": 50}
    job = _finished(
        world,
        ws,
        [{**_type(world, "R"), "where": [criterion]}, _type(world, "H"), _type(world, "K")],
        include={"relations": "withinScope"},
    )
    assert job["state"] == "completed", job
    lines = _lines(world, job)
    records = [line for line in lines if line["op"] == "upsert"]
    relations = [line for line in lines if line["op"] == "ensureRelation"]
    assert len(lines) == len(records) + len(relations)
    assert lines[: len(records)] == records
    assert {r["key"]["id"] for r in records} == {
        high["id"], top["id"], middle["id"], leaf["id"], *(t["id"] for t in tokens)
    }
    seen = set()
    for record in records:
        if "parent" in record:
            assert record["parent"]["id"] in seen
        seen.add(record["key"]["id"])
    by_id = {r["key"]["id"]: r for r in records}
    assert by_id[leaf["id"]]["parent"] == {"id": middle["id"]}
    assert by_id[leaf["id"]]["expectedVersion"] == world.record("H", leaf["id"], workspaceKey=ws)["version"]
    assert by_id[high["id"]]["objectTypeKey"] == world.key("R")
    assert by_id[high["id"]]["applicationKey"] == world.app("R")
    assert {"attributeTypeKey": world.key("R.n"), "value": 90} in by_id[high["id"]]["attributes"]
    assert {(r["relationTypeKey"], r["from"]["id"], r["to"]["id"]) for r in relations} == {
        (world.key("Bnn"), middle["id"], token["id"]) for token in tokens
    }
    assert all(r["relationTypeKey"] != world.key("Hparent") for r in relations)

    output = job["output"]
    assert output["format"] == "jsonl" and output["contentType"] == "application/x-ndjson"
    assert output["counts"] == {
        "records": {world.key("R"): 1, world.key("H"): 3, world.key("K"): 2},
        "relations": {world.key("Bnn"): 2},
    }
    assert output["context"]["workspaceKey"] == ws
    assert output["context"]["changeSetId"] is None and output["context"]["publicationId"] is None
    assert output["feedPosition"] == head
    response = _download(world, job)
    digest = hashlib.sha256(response.content).digest()
    assert output["sha256"] == digest.hex() and output["bytes"] == len(response.content)
    assert response.headers["repr-digest"] == f"sha-256=:{base64.b64encode(digest).decode()}:"
    assert response.headers["content-type"].startswith("application/x-ndjson")


@pytest.mark.journey("J27.1")
@pytest.mark.structures("H", "H.code", "E", "E.from", "E.to", "F")
def test_change_sets_publications_subtrees_and_dates_each_export_what_they_hold(world):
    """Given a workspace published, then renamed live, and a change set holding a record live data
    lacks; an H hierarchy; an E rate effective from 2026-01-01 and one ended before, and an F fee.
    When the change set, the publication, the subtree below the middle H, and E and F on 2026-06-01
    are exported. Then the change set's file holds its record and names it with its version, without
    a feed position; the publication's holds the published name and its position; the subtree holds
    only the leaf; the dated export holds the effective rate and the fee, naming E as dated."""
    ws = _workspace(world)
    top, middle, leaf, _ = _hierarchy(world, ws)
    cs = world.change_set(workspace=ws)
    world.made("H", "Published extra", workspace=ws, change_set=world.current(cs))
    publication = world.publish(cs, workspace=ws)
    ok(world.update("H", top["id"], world.record("H", top["id"], workspaceKey=ws)["version"], name="Renamed live"))
    staged_cs = world.change_set(workspace=ws)
    staged = world.made("H", "Only staged", workspace=ws, change_set=world.current(staged_cs))

    job = _finished(world, ws, [_type(world, "H")], context={"changeSetId": staged_cs["id"]})
    names = {line["name"] for line in _lines(world, job)}
    assert "Only staged" in names and staged["id"] in {line["key"]["id"] for line in _lines(world, job)}
    assert job["output"]["context"]["changeSetId"] == staged_cs["id"]
    assert job["output"]["context"]["changeSetVersion"] == world.current(staged_cs)["version"]
    assert job["output"]["feedPosition"] is None

    job = _finished(world, ws, [_type(world, "H")], context={"publicationId": publication["id"]})
    names = {line["name"] for line in _lines(world, job)}
    assert "Export top" in names and "Renamed live" not in names and "Only staged" not in names
    assert job["output"]["context"]["publicationId"] == publication["id"]
    assert job["output"]["feedPosition"] == publication["feedPosition"]

    job = _finished(world, ws, [_type(world, "H")], scope={"parentObjectId": middle["id"]})
    assert [line["key"]["id"] for line in _lines(world, job)] == [leaf["id"]]

    current = world.made("E", "Current rate", workspace=ws, values={"E.from": "2026-01-01"})
    world.made("E", "Ended rate", workspace=ws, values={"E.from": "2025-01-01", "E.to": "2025-12-31"})
    fee = world.made("F", "Plain fee", workspace=ws)
    job = _finished(
        world, ws, [_type(world, "E"), _type(world, "F")], scope={"asOf": "2026-06-01"}
    )
    assert {line["key"]["id"] for line in _lines(world, job)} == {current["id"], fee["id"]}
    assert job["output"]["asOf"] == "2026-06-01"
    assert job["output"]["asOfApplied"] == [world.key("E")]


@pytest.mark.journey("J27.2")
@pytest.mark.structures("H", "H.code", "K", "K.code", "Bnn", "Bnn.weight")
def test_writes_during_an_export_are_not_in_it_and_follow_its_position(world, monkeypatch):
    """Given an export that has taken its snapshot. When a record is created and another renamed and
    both committed before the export finishes. Then the file has neither change, and both are in the
    feed after the export's position."""
    ws = _workspace(world)
    top, _, _, _ = _hierarchy(world, ws)
    written = {}
    check = exports_module.should_stop

    def write_once(*args, **kwargs):
        if not written:
            written["new"] = world.made("H", "Written meanwhile", workspace=ws)
            renamed = world.update("H", top["id"], world.record("H", top["id"], workspaceKey=ws)["version"], name="Renamed meanwhile")
            written["renamed"] = ok(renamed)
        return check(*args, **kwargs)

    monkeypatch.setattr(exports_module, "should_stop", write_once)
    job = _finished(world, ws, [_type(world, "H")])
    assert written, "the export never checked for a cancel request"
    lines = _lines(world, job)
    assert written["new"]["id"] not in {line["key"]["id"] for line in lines}
    assert {line["name"] for line in lines if line["key"]["id"] == top["id"]} == {"Export top"}

    after = job["output"]["feedPosition"]
    entries = ok(world.api.get(f"/workspaces/{ws}/feed", after=after, pageSize=100))["items"]
    assert {(e["action"], e["id"]) for e in entries} >= {
        ("created", written["new"]["id"]),
        ("updated", top["id"]),
    }


@pytest.mark.journey("J27.2", "J26.6")
@pytest.mark.structures("H", "H.code", "K", "K.code", "Bnn", "Bnn.weight")
def test_a_reader_whose_position_expired_recovers_from_an_export(world):
    """Given a published workspace whose entries up to the publish are older than the retention
    period, with live writes after it. When a reader is refused as expired, exports the live data,
    then follows the feed from the export's position, adding created records and removing deleted
    ones. Then the refusal names the export route beside the publication, and the reader holds
    exactly the records live data holds."""
    ws = _workspace(world)
    _, _, leaf, _ = _hierarchy(world, ws)
    cs = world.change_set(workspace=ws)
    world.made("H", "Published extra", workspace=ws, change_set=world.current(cs))
    publication = world.publish(cs, workspace=ws)
    world.made("H", "After publish", workspace=ws)
    _age(world, ws, 31, through=publication["feedPosition"])
    error = refused(world.api.get(f"/workspaces/{ws}/feed", after=0), 410, "FEED_POSITION_EXPIRED")
    assert error["details"]["export"] == {"href": "/api/v1/exports"}
    assert error["details"]["publication"]["id"] == publication["id"]

    job = _finished(world, ws, [_type(world, "H")])
    held = {line["key"]["id"] for line in _lines(world, job)}
    world.made("H", "After export", workspace=ws)
    gone = world.api.delete(
        f"/objects/{world.key('H')}/{leaf['id']}", expectedVersion=world.record("H", leaf["id"], workspaceKey=ws)["version"]
    )
    assert gone.status_code == 204, gone.text
    after = job["output"]["feedPosition"]
    page = ok(world.api.get(f"/workspaces/{ws}/feed", after=after, kind="object", pageSize=100))
    for entry in page["items"]:
        if entry["action"] == "created":
            held.add(entry["id"])
        elif entry["action"] == "deleted":
            held.discard(entry["id"])
    assert held == _ids(world, "H", workspaceKey=ws)


@pytest.mark.journey("J27.3")
@pytest.mark.structures("R", "R.u", "G", "D", "Bown", "H", "H.code", "K", "K.code", "Bnn", "Bnn.weight")
def test_an_export_sent_back_changes_nothing_and_an_edited_one_updates_only_unchanged_records(world):
    """Given H, K and Bnn records, and a D record that requires its Bown relationship from an R.
    When everything is exported as JSON Lines and the file is sent back as a background batch with
    the default onExisting. Then every item is applied unchanged and the feed head does not move; the
    D line carries the required relationship as an initial relation. When the same file is sent with
    one record renamed in it, and another renamed in the file and also renamed in the workspace after
    the export. Then the first is updated, the second is refused as a version conflict, and the rest
    are unchanged."""
    ws = _workspace(world)
    top, middle, leaf, _ = _hierarchy(world, ws)
    owner = world.made("R", "Owner", workspace=ws)
    g = world.made("G", "Ground", workspace=ws)
    parent = world.dependant_parent(g["id"], workspace=ws)
    dependant = world.made(
        "D", "Dependant", parent=parent, workspace=ws, relations=[world.owner("Bown", owner["id"])]
    )
    types = [_type(world, s) for s in ("R", "G", "D", "H", "K")]
    if world.holds("M"):
        types.append(_type(world, "M"))
    job = _finished(world, ws, types, include={"relations": "withinScope"})
    lines = _lines(world, job)
    line = next(item for item in lines if item.get("key", {}).get("id") == dependant["id"])
    assert {
        "relationTypeKey": world.key("Bown"), "direction": "incoming", "object": {"id": owner["id"]}
    } in [{k: v for k, v in r.items() if k != "attributes"} for r in line["initialRelations"]]

    head = _head(world, ws)
    outcomes = _batch(world, ws, lines)
    assert {(status, action) for status, action, _ in outcomes} == {("applied", "unchanged")}
    assert _head(world, ws) == head

    ok(world.update("H", leaf["id"], world.record("H", leaf["id"], workspaceKey=ws)["version"], name="Changed meanwhile"))
    edited = []
    for item in lines:
        if item.get("key", {}).get("id") == middle["id"]:
            item = {**item, "name": "Edited in the file"}
        if item.get("key", {}).get("id") == leaf["id"]:
            item = {**item, "name": "Also edited in the file"}
        edited.append(item)
    outcomes = {ref: (status, action) for status, action, ref in _batch(world, ws, edited)}
    assert outcomes[middle["id"]] == ("applied", "updated")
    assert outcomes[leaf["id"]] == ("rejected", "VERSION_CONFLICT")
    assert world.record("H", middle["id"], workspaceKey=ws)["name"] == "Edited in the file"
    assert world.record("H", leaf["id"], workspaceKey=ws)["name"] == "Changed meanwhile"
    rest = {ref: o for ref, o in outcomes.items() if ref not in (middle["id"], leaf["id"])}
    assert set(rest.values()) == {("applied", "unchanged")}
    assert top["id"] in rest


@pytest.mark.journey("J27.1", "J27.3")
@pytest.mark.structures("R", "R.u", "R.n", "R.b", "R.dt", "H", "H.code", "K", "K.code", "Bnn", "Bnn.weight")
def test_csv_and_xlsx_hold_the_same_rows_in_one_table_layout(world):
    """Given R records with a leading-zero code, a number, a boolean and a date, and H and K records
    with Bnn relationships. When they are exported as JSON Lines, CSV and XLSX. Then the CSV is one
    file whose header is the layout's keys, records then relationships, values in canonical text;
    the XLSX holds the same rows in its records and relationships tables, the code as text, the
    number as a number, the boolean as a boolean and the date as a date; all three formats hold the
    same records with the same versions."""
    ws = _workspace(world)
    coded = world.made(
        "R", "Coded", workspace=ws,
        values={"R.u": "007", "R.n": 42, "R.b": True, "R.dt": "2026-03-04"},
    )
    _, middle, _, tokens = _hierarchy(world, ws)
    types = [_type(world, "R"), _type(world, "H"), _type(world, "K")]
    jsonl = _lines(world, _finished(world, ws, types))
    versions = {line["key"]["id"]: line["expectedVersion"] for line in jsonl if line["op"] == "upsert"}

    job = _finished(world, ws, types, format="csv")
    response = _download(world, job)
    assert response.headers["content-type"].startswith("text/csv")
    assert response.content.startswith(b"\xef\xbb\xbf")
    rows = list(csv.DictReader(io.StringIO(response.content.decode("utf-8-sig"))))
    header = list(rows[0].keys())
    assert header[:9] == [
        "objectTypeKey", "applicationKey", "relationTypeKey", "id", "version", "name",
        "parentObjectId", "fromId", "toId",
    ]
    assert f"#{world.key('R.u')}" in header and "~parentPath" in header
    records = [row for row in rows if row["objectTypeKey"]]
    relations = [row for row in rows if row["relationTypeKey"]]
    assert rows == records + relations
    assert {row["id"]: int(row["version"]) for row in records} == versions
    row = next(row for row in records if row["id"] == coded["id"])
    assert row["applicationKey"] == world.app("R")
    assert row[f"#{world.key('R.u')}"] == "007"
    assert row[f"#{world.key('R.n')}"] == "42"
    assert row[f"#{world.key('R.b')}"] == "true"
    assert row[f"#{world.key('R.dt')}"] == "2026-03-04"
    assert row[f"#{world.key('H.code')}"] == ""
    assert {(r["fromId"], r["toId"]) for r in relations} == {(middle["id"], t["id"]) for t in tokens}

    job = _finished(world, ws, types, format="xlsx")
    response = _download(world, job)
    assert response.headers["content-type"].startswith(XLSX)
    book = load_workbook(io.BytesIO(response.content))
    sheet = book["Records"]
    table = sheet.tables["records"]
    cells = list(sheet[table.ref])
    keys = [cell.value for cell in cells[0]]
    assert keys[:6] == ["objectTypeKey", "applicationKey", "id", "version", "name", "parentObjectId"]
    rows = [dict(zip(keys, (cell.value for cell in row), strict=True)) for row in cells[1:]]
    assert {row["id"]: row["version"] for row in rows} == versions
    row = next(row for row in rows if row["id"] == coded["id"])
    assert row[f"#{world.key('R.u')}"] == "007"
    assert row[f"#{world.key('R.n')}"] == 42
    assert row[f"#{world.key('R.b')}"] is True
    assert row[f"#{world.key('R.dt')}"].date().isoformat() == "2026-03-04"
    relations_sheet = book["Relationships"]
    cells = list(relations_sheet[relations_sheet.tables["relationships"].ref])
    keys = [cell.value for cell in cells[0]]
    pairs = {(row[keys.index("fromId")].value, row[keys.index("toId")].value) for row in cells[1:]}
    assert pairs == {(middle["id"], t["id"]) for t in tokens}


@pytest.mark.journey("J27.4")
@pytest.mark.structures("H", "H.code", "K", "K.code", "Bnn", "Bnn.weight")
def test_a_cancelled_failed_or_expired_export_serves_no_file(world):
    """Given exports of a workspace. When one is cancelled before it runs, one runs after the active
    model release changed, one completes and then passes its retention, and a batch's output is
    asked for. Then the cancelled and failed ones answer that the job is not completed and leave no
    file; the failed one names the release change; the expired one answers expired; a batch has no
    output."""
    ws = _workspace(world)
    _hierarchy(world, ws)
    types = [_type(world, "H")]

    cancelled = ok(_export(world, ws, types), 202)
    ok(world.api.post(f"/jobs/{cancelled['id']}/cancel"), 202)
    _run(world)
    assert ok(world.api.get(f"/jobs/{cancelled['id']}"))["state"] == "cancelled"
    error = refused(world.api.get(f"/jobs/{cancelled['id']}/output"), 409, "JOB_NOT_COMPLETED")
    assert error["details"]["state"] == "cancelled"

    failed = ok(_export(world, ws, types), 202)
    model, _ = world.candidate("compatible")
    ok(world.activate(world.install(model)["id"]))
    _run(world)
    job = ok(world.api.get(f"/jobs/{failed['id']}"))
    assert job["state"] == "failed" and job["error"]["code"] == "MODEL_RELEASE_CHANGED"
    refused(world.api.get(f"/jobs/{failed['id']}/output"), 409, "JOB_NOT_COMPLETED")

    done = _finished(world, ws, types)
    assert done["state"] == "completed"
    _expire(world, done["id"])
    world.api.client.app.state.job_worker.sweep()
    assert ok(world.api.get(f"/jobs/{done['id']}"))["state"] == "expired"
    refused(world.api.get(f"/jobs/{done['id']}/output"), 410, "JOB_EXPIRED")

    directory = world.api.client.app.state.job_files.directory
    assert sorted(path.name for path in directory.iterdir()) == []

    item = {"op": "create", "applicationKey": world.app("H"), "objectTypeKey": world.key("H"), "name": "Batched"}
    batch = ok(
        world.api.post("/batches", {"workspaceKey": ws, "policy": "atomic", "run": "inline", "items": [item]})
    )
    refused(world.api.get(f"/jobs/{batch['job']['id']}/output"), 404, "JOB_HAS_NO_OUTPUT")


@pytest.mark.journey("J27.5")
@pytest.mark.structures("H", "H.code", "F")
def test_requests_the_model_or_the_workspace_cannot_answer_are_refused(world):
    """Given a workspace. When an export names an unknown type, an unknown field in a criterion, a
    date while no exported type declares a period, an unknown parent, both a change set and a
    publication, or one type twice. Then each is refused before a job is stored, a model mistake at
    its JSON pointer."""
    ws = _workspace(world)
    error = refused(_export(world, ws, [{"objectTypeKey": "no-such-type"}]), 422, "INVALID_QUERY")
    assert error["details"]["path"] == "/scope/types/0/objectTypeKey"
    bad = {"field": "no-such-field", "op": "eq", "value": "x"}
    error = refused(
        _export(world, ws, [_type(world, "F"), {**_type(world, "H"), "where": [bad]}]),
        422,
        "INVALID_QUERY",
    )
    assert error["details"]["path"] == "/scope/types/1/where/0/field"
    refused(
        _export(world, ws, [_type(world, "F")], scope={"asOf": "2026-01-01"}), 422, "AS_OF_NOT_SUPPORTED"
    )
    refused(
        _export(world, ws, [_type(world, "H")], scope={"parentObjectId": str(uuid4())}),
        404,
        "PARENT_NOT_FOUND",
    )
    both = {"changeSetId": str(uuid4()), "publicationId": str(uuid4())}
    refused(_export(world, ws, [_type(world, "H")], context=both), 422, "REQUEST_VALIDATION_ERROR")
    refused(
        _export(world, ws, [_type(world, "H"), _type(world, "H")]), 422, "REQUEST_VALIDATION_ERROR"
    )
    refused(_export(world, "no-such-workspace", [_type(world, "H")]), 404, "WORKSPACE_NOT_FOUND")
    assert ok(world.api.get("/jobs", workspaceKey=ws))["items"] == []


@pytest.mark.journey("J27.5")
@pytest.mark.structures("H")
@pytest.mark.settings(INTEGRATION_JOBS_ENABLED="false")
def test_with_job_creation_off_the_export_route_is_absent(world):
    """Given the service started with job creation turned off. When an export is requested and jobs
    are listed. Then the export route is not there, and job reads still answer."""
    response = _export(world, "main", [_type(world, "H")])
    assert response.status_code in (404, 405), response.text
    ok(world.api.get("/jobs"))


def _batch(world, workspace, items):
    """Send ``items`` as a background batch, run it, and return (status, action or code, record or
    relation ID) per item."""
    job = ok(
        world.api.post(
            "/batches",
            {"workspaceKey": workspace, "policy": "independent", "run": "background", "items": items},
        ),
        202,
    )
    world.api.client.app.state.job_worker.run_until_idle()
    outcomes, cursor = [], None
    while True:
        page = ok(world.api.get(f"/jobs/{job['id']}/items", pageSize=500, cursor=cursor))
        for item, sent in zip(page["items"], items[len(outcomes):], strict=False):
            ref = sent["key"]["id"] if "key" in sent else ("relation", sent["to"]["id"])
            outcome = item.get("action") or item.get("error", {}).get("code")
            outcomes.append((item["status"], outcome, ref))
        cursor = page.get("nextCursor")
        if not cursor:
            return outcomes


def _age(world, workspace, days, through):
    engine = create_engine(world.database, poolclass=NullPool)
    with engine.begin() as connection:
        connection.execute(
            text(
                "UPDATE audit_events SET occurred_at = occurred_at - make_interval(days => :d) "
                "WHERE workspace_key = :w AND feed_position <= :p"
            ),
            {"d": days, "w": workspace, "p": through},
        )
    engine.dispose()


def _expire(world, job_id):
    """Move the job's retention into the past, as the days passing would."""
    engine = create_engine(world.database, poolclass=NullPool)
    with engine.begin() as connection:
        connection.execute(
            text("UPDATE jobs SET expires_at = now() - interval '1 second' WHERE id = :id"),
            {"id": job_id},
        )
    engine.dispose()
