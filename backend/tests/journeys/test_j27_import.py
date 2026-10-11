"""J27 — Exchange a supplier file: the import (USER_JOURNEYS.md, 0.9 J2, J3).

Each test writes in a workspace of its own. The journey application runs no worker thread; a test
runs the engine's job worker itself (``_run``). Files are built as a supplier would send them:
workbooks with openpyxl, CSV and JSON Lines as text.
"""

import csv
import io
import json
from datetime import date, datetime, timedelta
from uuid import UUID, uuid4, uuid5

import pytest
from openpyxl import Workbook
from scenario import ok, refused
from sqlalchemy import text

from app.db import SessionLocal
from app.engine.jobs.worker import JobWorker, WorkerSettings

XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
TYPES = {
    "xlsx": XLSX,
    "csv": "text/csv",
    "jsonl": "application/x-ndjson",
    "xls": "application/vnd.ms-excel",
}


def _workspace(world):
    key = f"import-{uuid4().hex[:8]}"
    ok(world.api.post("/workspaces", {"key": key, "label": "Import site"}), 201)
    return key


def _xlsx(sheets):
    book = Workbook()
    book.remove(book.active)
    for title, rows in sheets.items():
        sheet = book.create_sheet(title)
        for row in rows:
            sheet.append(list(row))
    buffer = io.BytesIO()
    book.save(buffer)
    return buffer.getvalue()


def _csv(rows):
    buffer = io.StringIO()
    csv.writer(buffer).writerows(rows)
    return buffer.getvalue().encode()


def _request(workspace, **extra):
    return {
        "workspaceKey": workspace,
        "policy": "independent",
        "onExisting": "overwrite",
        "stage": "execute",
        **extra,
    }


def _send(world, name, content, request, headers=None):
    file_type = TYPES[name.rsplit(".", 1)[1]]
    return world.api.upload(
        "/imports", {"file": (name, content, file_type)}, {"request": json.dumps(request)}, headers
    )


def _run(world):
    return world.api.client.app.state.job_worker.run_until_idle()


def _imported(world, name, content, request, headers=None):
    job = ok(_send(world, name, content, request, headers), 202)
    assert job["kind"] == "import" and job["state"] == "queued", job["error"]
    _run(world)
    return ok(world.api.get(f"/jobs/{job['id']}"))


def _outcomes(world, job):
    items, cursor = [], None
    while True:
        page = ok(world.api.get(f"/jobs/{job['id']}/items", pageSize=500, cursor=cursor))
        items += page["items"]
        cursor = page.get("nextCursor")
        if not cursor:
            return items


def _by_ref(items):
    rows = {}
    for item in items:
        rows.setdefault(item["ref"], []).append(item)
    return rows


def _code(item):
    return item.get("error", {}).get("code")


def _named(world, structure, workspace, **context):
    page = ok(
        world.api.get(
            f"/objects/{world.key(structure)}", workspaceKey=workspace, pageSize=100, **context
        )
    )
    return {item["name"]: item for item in page["items"]}


def _related(world, object_id, structure, workspace):
    page = ok(
        world.api.get(
            "/relations",
            objectId=object_id,
            relationTypeKey=world.key(structure),
            workspaceKey=workspace,
            pageSize=100,
        )
    )
    return {item["object"]["id"] for item in page["items"]}


def _ledger_profile(world, key=None):
    """R records from a sheet, keyed by R.u, with typed values and a value map."""
    return {
        "key": key or f"ledgers-{uuid4().hex[:8]}",
        "name": "Ledgers",
        "sources": [
            {
                "sheet": "Ledgers",
                "applicationKey": world.app("R"),
                "objectTypeKey": world.key("R"),
                "key": {"attributeTypeKey": world.key("R.u")},
                "columns": [
                    {"column": "Number", "attributeTypeKey": world.key("R.u")},
                    {"column": "Name", "field": "name"},
                    {"column": "Owner", "attributeTypeKey": world.key("R.q")},
                    {"column": "Summary", "attributeTypeKey": world.key("R.x1")},
                    {"column": "Score", "attributeTypeKey": world.key("R.n"), "valueMap": "blanks"},
                    {"column": "Flagged", "attributeTypeKey": world.key("R.b")},
                    {"column": "Opened", "attributeTypeKey": world.key("R.dt")},
                ],
            }
        ],
        "valueMaps": {"blanks": {"N/A": None}},
    }


LEDGER_HEADER = ("Number", "Name", "Owner", "Summary", "Score", "Flagged", "Opened")


@pytest.mark.journey("J27.7")
@pytest.mark.structures("R", "R.u", "R.n", "R.b", "R.dt", "R.q", "R.x1", "H", "K", "K.code", "Bnn")
def test_profiles_are_kept_under_a_version_and_refused_with_every_problem(world):
    """Given a valid profile. When it is created, read, listed, changed at its version, changed
    again at the old version, created twice and deleted. Then it is version 1, then 2; the stale
    change is a version conflict naming the current version; the second create is refused. A
    profile naming an unknown attribute, a relationship the two types do not allow and two sources
    that reference each other is refused with three problems at their pointers. After a release
    removes an attribute a stored profile binds, the profile reads as no longer valid with that
    path, and an import naming it is refused with the same problem."""
    profile = _ledger_profile(world)
    created = ok(world.api.post("/import-profiles", profile), 201)
    assert created["version"] == 1 and created["valid"] is True and created["problems"] == []
    active = ok(world.api.get("/model-runtime-state"))["activeReleaseId"]
    assert created["checkedAgainst"] == active
    read = ok(world.api.get(f"/import-profiles/{profile['key']}"))
    assert read["sources"] == created["sources"] and read["name"] == "Ledgers"
    assert profile["key"] in {p["key"] for p in ok(world.api.get("/import-profiles"))["items"]}

    body = {k: v for k, v in profile.items() if k != "key"}
    changed = ok(
        world.api.put(
            f"/import-profiles/{profile['key']}", {**body, "name": "Renamed", "expectedVersion": 1}
        )
    )
    assert changed["version"] == 2 and changed["name"] == "Renamed"
    error = refused(
        world.api.put(f"/import-profiles/{profile['key']}", {**body, "expectedVersion": 1}),
        409,
        "IMPORT_PROFILE_VERSION_CONFLICT",
    )
    assert error["details"]["currentVersion"] == 2
    refused(world.api.post("/import-profiles", profile), 409, "IMPORT_PROFILE_EXISTS")

    bad = _ledger_profile(world)
    bad["sources"][0]["columns"].append(
        {"column": "Ghost", "attributeTypeKey": "no-such-attribute"}
    )
    bad["sources"][0]["columns"].append(
        {
            "column": "Tokens",
            "relation": {
                "relationTypeKey": world.key("Bnn"),
                "objectTypeKey": world.key("K"),
                "matchBy": {"field": "name"},
            },
        }
    )
    bnn = {"relationTypeKey": world.key("Bnn"), "matchBy": {"field": "name"}}
    bad["sources"] += [
        {
            "sheet": "Branches",
            "applicationKey": world.app("H"),
            "objectTypeKey": world.key("H"),
            "columns": [
                {"column": "Name", "field": "name"},
                {"column": "Token", "relation": {**bnn, "objectTypeKey": world.key("K")}},
            ],
        },
        {
            "sheet": "Tokens",
            "applicationKey": world.app("K"),
            "objectTypeKey": world.key("K"),
            "columns": [
                {"column": "Name", "field": "name"},
                {
                    "column": "Branch",
                    "relation": {**bnn, "direction": "incoming", "objectTypeKey": world.key("H")},
                },
            ],
        },
    ]
    error = refused(world.api.post("/import-profiles", bad), 422, "INVALID_IMPORT_PROFILE")
    problems = {(p["path"], p["code"]) for p in error["details"]["problems"]}
    assert problems == {
        ("/sources/0/columns/7/attributeTypeKey", "UNKNOWN_ATTRIBUTE"),
        ("/sources/0/columns/8/relation", "RELATION_NOT_ALLOWED"),
        ("/sources", "SOURCE_CYCLE"),
    }, problems

    model, added = world.candidate("compatible")
    ok(world.activate(world.install(model)["id"]))
    bound = _ledger_profile(world)
    bound["sources"][0]["columns"].append({"column": "Added", "attributeTypeKey": added})
    ok(world.api.post("/import-profiles", bound), 201)
    again = dict(
        world.configuration.model,
        release={**world.configuration.model["release"], "version": "again"},
    )
    ok(world.activate(world.install(again)["id"]))
    stale = ok(world.api.get(f"/import-profiles/{bound['key']}"))
    assert stale["valid"] is False
    assert {(p["path"], p["code"]) for p in stale["problems"]} == {
        ("/sources/0/columns/7/attributeTypeKey", "UNKNOWN_ATTRIBUTE")
    }
    ws = _workspace(world)
    content = _xlsx({"Ledgers": [LEDGER_HEADER + ("Added",)]})
    error = refused(
        _send(world, "ledgers.xlsx", content, _request(ws, profileKey=bound["key"])),
        422,
        "INVALID_IMPORT_PROFILE",
    )
    assert [p["path"] for p in error["details"]["problems"]] == [
        "/sources/0/columns/7/attributeTypeKey"
    ]

    ok(world.api.delete(f"/import-profiles/{profile['key']}", expectedVersion=2), 204)
    refused(world.api.get(f"/import-profiles/{profile['key']}"), 404, "IMPORT_PROFILE_NOT_FOUND")


def _workbook_profile(world, parent_structure, parent_name):
    """Every binding kind: P and C by a parent name, K, H with a split relation column and flags,
    and R keyed by R.u with a related D under a fixed parent."""
    k = world.key
    by_name = {"field": "name"}
    return {
        "key": f"supplier-{uuid4().hex[:8]}",
        "name": "Supplier workbook",
        "sources": [
            {
                "sheet": "Rooms",
                "applicationKey": world.app("C"),
                "objectTypeKey": k("C"),
                "columns": [
                    {"column": "Name", "field": "name"},
                    {"column": "Estate", "parent": {"objectTypeKey": k("P"), "matchBy": by_name}},
                ],
            },
            {
                "sheet": "Estates",
                "applicationKey": world.app("P"),
                "objectTypeKey": k("P"),
                "columns": [
                    {"column": "Name", "field": "name"},
                    {"column": "Code", "attributeTypeKey": k("H.code")},
                ],
            },
            {
                "sheet": "Branches",
                "applicationKey": world.app("H"),
                "objectTypeKey": k("H"),
                "columns": [
                    {"column": "Code", "attributeTypeKey": k("H.code")},
                    {"column": "Name", "field": "name"},
                    {
                        "column": "Tokens",
                        "valueMap": "none",
                        "relation": {
                            "relationTypeKey": k("Bnn"),
                            "objectTypeKey": k("K"),
                            "matchBy": {"attributeTypeKey": k("K.code")},
                            "split": ";",
                        },
                    },
                    {
                        "columns": ["Web", "Phone"],
                        "relationFlags": {
                            "relationTypeKey": k("Bnn"),
                            "objectTypeKey": k("K"),
                            "matchBy": by_name,
                            "targets": {"Web": "Token three", "Phone": "Token one"},
                        },
                    },
                ],
            },
            {
                "sheet": "Tokens",
                "applicationKey": world.app("K"),
                "objectTypeKey": k("K"),
                "columns": [
                    {"column": "Code", "attributeTypeKey": k("K.code")},
                    {"column": "Name", "field": "name"},
                ],
            },
            {
                "sheet": "Ledgers",
                "applicationKey": world.app("R"),
                "objectTypeKey": k("R"),
                "key": {"attributeTypeKey": k("R.u")},
                "columns": [
                    {"column": "Number", "attributeTypeKey": k("R.u")},
                    {"column": "Name", "field": "name"},
                    {"column": "Owner", "attributeTypeKey": k("R.q")},
                    {"column": "Summary", "attributeTypeKey": k("R.x1")},
                    {"column": "Score", "attributeTypeKey": k("R.n"), "valueMap": "none"},
                    {"column": "Flagged", "attributeTypeKey": k("R.b")},
                    {"column": "Opened", "attributeTypeKey": k("R.dt")},
                    {
                        "column": "Permit",
                        "relatedRecord": {
                            "relationTypeKey": k("Bown"),
                            "applicationKey": world.app("D"),
                            "objectTypeKey": k("D"),
                            "parent": {
                                "objectTypeKey": k(parent_structure),
                                "matchBy": by_name,
                                "value": parent_name,
                            },
                            "attributeTypeKey": k("K.code"),
                        },
                    },
                ],
            },
        ],
        "valueMaps": {"none": {"N/A": None, "-": None}},
    }


def _workbook():
    return {
        "Rooms": [("Name", "Estate"), ("Room in new", "New estate"), ("Room in old", "Old estate")],
        "Estates": [("Name", "Code"), ("New estate", "NE")],
        "Branches": [
            ("Code", "Name", "Tokens", "Web", "Phone"),
            ("BR1", "Branch one", "TK1;TK2", "x", None),
            ("BR2", "Branch two", "-", None, "yes"),
        ],
        "Tokens": [
            ("Code", "Name"),
            ("TK1", "Token one"),
            ("TK2", "Token two"),
            ("TK3", "Token three"),
        ],
        "Ledgers": [
            LEDGER_HEADER + ("Permit",),
            ("L-NEW", "New ledger", "Ann", "Summary", 42, True, date(2026, 3, 4), "PC1"),
            ("L-OLD", "Old ledger renamed", "Bob", "Summary", "N/A", False, "2026-05-06", None),
        ],
    }


def _parent_of_d(world, workspace):
    """The record a D stands under: G itself, or an M container below it (``deep-scope``)."""
    ground = world.made("G", "Ground", workspace=workspace)
    parent_id = world.dependant_parent(ground["id"], workspace=workspace)
    structure = "M" if parent_id != ground["id"] else "G"
    name = (
        "Ground"
        if structure == "G"
        else world.record("M", parent_id, workspaceKey=workspace)["name"]
    )
    return structure, name, parent_id


def _check_workbook_loaded(world, ws, existing, permit_parent, **context):
    estates = _named(world, "P", ws, **context)
    rooms = _named(world, "C", ws, **context)
    assert rooms["Room in new"]["parentObjectId"] == estates["New estate"]["id"]
    assert rooms["Room in old"]["parentObjectId"] == existing["estate"]["id"]
    new_estate = world.record("P", estates["New estate"]["id"], workspaceKey=ws, **context)
    assert world.value(new_estate, "H.code") == "NE"

    tokens = _named(world, "K", ws, **context)
    branches = _named(world, "H", ws, **context)
    ledgers = _named(world, "R", ws, **context)
    new = world.record("R", ledgers["New ledger"]["id"], workspaceKey=ws, **context)
    assert world.value(new, "R.u") == "L-NEW"
    assert world.value(new, "R.n") == 42
    assert world.value(new, "R.b") is True
    assert world.value(new, "R.dt") == "2026-03-04"
    old = world.record("R", existing["ledger"]["id"], workspaceKey=ws, **context)
    assert old["name"] == "Old ledger renamed"
    assert world.value(old, "R.b") is False and world.value(old, "R.dt") == "2026-05-06"
    assert world.value(old, "R.n") == 7
    return tokens, branches, new


@pytest.mark.journey("J27.8")
@pytest.mark.structures(
    "R",
    "R.u",
    "R.n",
    "R.b",
    "R.dt",
    "R.q",
    "R.x1",
    "P",
    "C",
    "H",
    "H.code",
    "K",
    "K.code",
    "Bnn",
    "G",
    "D",
    "Bown",
)
def test_a_workbook_loads_every_binding_kind_through_a_profile(world):
    """Given an existing P "Old estate" and an existing R numbered L-OLD, and a workbook whose
    sheets load C records under a P named in the row (one created by the same file, one existing),
    P records, K tokens, H branches with a split relation column through a value map and two flag
    columns, and R ledgers keyed by R.u with an integer, a date cell, a date as text, a boolean, a
    value mapped to nothing and a related D under a fixed parent. When it is imported live under
    independent with overwrite. Then the job completes, every row applied; each record, value,
    parent, relationship and related record reads back as the file says; the existing ledger is
    updated in place; every item names its sheet and row; the feed names the job as the cause."""
    ws = _workspace(world)
    existing = {
        "estate": world.made("P", "Old estate", workspace=ws),
        "ledger": world.made(
            "R", "Old ledger", workspace=ws, values={"R.u": "L-OLD", "R.n": 7, "R.b": True}
        ),
    }
    parent_structure, parent_name, permit_parent = _parent_of_d(world, ws)
    profile = ok(
        world.api.post("/import-profiles", _workbook_profile(world, parent_structure, parent_name)),
        201,
    )

    job = _imported(
        world, "supplier.xlsx", _xlsx(_workbook()), _request(ws, profileKey=profile["key"])
    )
    assert job["state"] == "completed" and job["result"] == "applied", job["error"]
    assert job["parameters"]["file"]["name"] == "supplier.xlsx"
    assert job["parameters"]["profile"]["key"] == profile["key"]
    outcomes = _outcomes(world, job)
    rows = _by_ref(outcomes)
    assert {"Rooms!2", "Rooms!3", "Estates!2", "Branches!2", "Tokens!4", "Ledgers!3"} <= set(rows)
    assert {item["status"] for item in outcomes} == {"applied"}

    tokens, branches, new = _check_workbook_loaded(world, ws, existing, permit_parent)
    assert _related(world, branches["Branch one"]["id"], "Bnn", ws) == {
        tokens["Token one"]["id"],
        tokens["Token two"]["id"],
        tokens["Token three"]["id"],
    }
    assert _related(world, branches["Branch two"]["id"], "Bnn", ws) == {tokens["Token one"]["id"]}
    permits = _related(world, new["id"], "Bown", ws)
    assert len(permits) == 1
    permit = world.record("D", permits.pop(), workspaceKey=ws)
    assert permit["parentObjectId"] == permit_parent and world.value(permit, "K.code") == "PC1"

    entries = ok(world.api.get(f"/workspaces/{ws}/feed", pageSize=200))["items"]
    from_job = [e for e in entries if e["cause"].get("id") == job["id"]]
    assert from_job and all(e["cause"]["kind"] == "job" for e in from_job)

    # The ledgers again: each finds its record by R.u and its related D through Bown and its parent.
    ledgers_only = _workbook_profile(world, parent_structure, parent_name)
    ledgers_only["sources"] = ledgers_only["sources"][-1:]
    ledgers_only = ok(world.api.post("/import-profiles", ledgers_only), 201)
    again = _imported(
        world,
        "ledgers.xlsx",
        _xlsx({"Ledgers": _workbook()["Ledgers"]}),
        _request(ws, profileKey=ledgers_only["key"]),
    )
    assert {(i["status"], i.get("action")) for i in _outcomes(world, again)} == {
        ("applied", "unchanged")
    }
    assert _related(world, new["id"], "Bown", ws) == {permit["id"]}


@pytest.mark.journey("J27.8")
@pytest.mark.structures("R", "R.u", "R.n", "R.b", "R.dt", "R.q", "R.x1")
def test_the_same_content_as_csv_loads_the_same_and_into_a_change_set_only_there(world):
    """Given the ledger rows as a workbook and as CSV. When each is imported into a workspace of its
    own, and the CSV again into a change set of a third. Then both give the same records with the
    same values and the same outcome counts; the change set holds the records and live data does
    not."""
    rows = [
        LEDGER_HEADER,
        ("L-1", "First ledger", "Ann", "Summary", 12, True, "2026-01-02"),
        ("L-2", "Second ledger", "Bob", "Summary", "N/A", False, "2026-02-03"),
    ]
    profile = ok(world.api.post("/import-profiles", _ledger_profile(world)), 201)

    def loaded(ws, **context):
        records = _named(world, "R", ws, **context)
        return {
            name: (
                world.value(world.record("R", item["id"], workspaceKey=ws, **context), "R.u"),
                world.value(world.record("R", item["id"], workspaceKey=ws, **context), "R.n"),
                world.value(world.record("R", item["id"], workspaceKey=ws, **context), "R.b"),
                world.value(world.record("R", item["id"], workspaceKey=ws, **context), "R.dt"),
            )
            for name, item in records.items()
        }

    first, second = _workspace(world), _workspace(world)
    from_xlsx = _imported(
        world, "l.xlsx", _xlsx({"Ledgers": rows}), _request(first, profileKey=profile["key"])
    )
    from_csv = _imported(world, "l.csv", _csv(rows), _request(second, profileKey=profile["key"]))
    assert from_xlsx["counts"] == from_csv["counts"] and from_csv["counts"]["created"] == 2
    assert (
        loaded(first)
        == loaded(second)
        == {
            "First ledger": ("L-1", 12, True, "2026-01-02"),
            "Second ledger": ("L-2", None, False, "2026-02-03"),
        }
    )
    assert {item["ref"] for item in _outcomes(world, from_csv)} == {"csv!2", "csv!3"}

    third = _workspace(world)
    cs = world.change_set(workspace=third)
    request = {
        "changeSetId": cs["id"],
        "expectedChangeSetVersion": cs["version"],
        "policy": "independent",
        "onExisting": "overwrite",
        "stage": "execute",
        "profileKey": profile["key"],
    }
    staged = _imported(world, "l.csv", _csv(rows), request)
    assert staged["state"] == "completed" and staged["counts"]["created"] == 2, staged["error"]
    assert set(loaded(third, changeSetId=cs["id"])) == {"First ledger", "Second ledger"}
    assert _named(world, "R", third) == {}


def _export(world, ws, types, fmt, relations="withinScope", where=None):
    request = {
        "workspaceKey": ws,
        "scope": {
            "types": [
                {"objectTypeKey": world.key(t), **({"where": where[t]} if where and t in where else {})}
                for t in types
            ]
        },
        "include": {"relations": relations},
        "format": fmt,
    }
    job = ok(world.api.post("/exports", request), 202)
    world.api.client.app.state.export_worker.run_until_idle()
    response = world.api.get(f"/jobs/{job['id']}/output")
    assert response.status_code == 200, response.text
    return response.content


@pytest.mark.journey("J27.9", "J27.3")
@pytest.mark.structures("H", "H.code", "K", "K.code", "Bnn", "Bnn.weight")
def test_an_export_sent_back_without_a_profile_changes_nothing_and_an_edited_one_applies(world):
    """Given H and K records with Bnn relationships. When they are exported as CSV and as XLSX and
    each file is sent back without a profile. Then every item is applied unchanged. When the CSV is
    sent with one name edited, one row added without an ID, and one record renamed in the
    workspace since the export and in the file. Then the edited record is updated, the added row
    created, the changed one refused as a version conflict and the rest unchanged. A JSON Lines
    export sent as a file is applied unchanged too."""
    ws = _workspace(world)
    top = world.made("H", "Top", workspace=ws, values={"H.code": "T"})
    leaf = world.made("H", "Leaf", parent=top["id"], workspace=ws, values={"H.code": "L"})
    token = world.made("K", "Token", workspace=ws, values={"K.code": "K1"})
    ok(world.relate("Bnn", leaf["id"], token["id"], {"Bnn.weight": 2}), 201)
    types = ("H", "K")

    for fmt in ("csv", "xlsx", "jsonl"):
        content = _export(world, ws, types, fmt)
        job = _imported(world, f"back.{fmt}", content, _request(ws, onExisting="reject"))
        assert job["state"] == "completed", job["error"]
        assert {(i["status"], i.get("action")) for i in _outcomes(world, job)} == {
            ("applied", "unchanged")
        }, fmt

    content = _export(world, ws, types, "csv").decode("utf-8-sig")
    ok(
        world.update(
            "H",
            leaf["id"],
            world.record("H", leaf["id"], workspaceKey=ws)["version"],
            name="Leaf meanwhile",
        )
    )
    rows = list(csv.reader(io.StringIO(content)))
    header = rows[0]
    column = {name: header.index(name) for name in header}
    edited = [header]
    for row in rows[1:]:
        if row[column["id"]] == top["id"]:
            row[column["name"]] = "Top edited"
        if row[column["id"]] == leaf["id"]:
            row[column["name"]] = "Leaf edited"
        edited.append(row)
    added = [""] * len(header)
    added[column["objectTypeKey"]] = world.key("H")
    added[column["applicationKey"]] = world.app("H")
    added[column["name"]] = "Added in the file"
    added[column[f"#{world.key('H.code')}"]] = "ADD"
    edited.insert(2, added)
    job = _imported(world, "edited.csv", _csv(edited), _request(ws, onExisting="reject"))
    by_row = {item["ref"]: item for item in _outcomes(world, job)}
    assert by_row["csv!2"]["action"] in ("updated", "unchanged")
    outcome = {(item["status"], item.get("action") or _code(item)) for ref, item in by_row.items()}
    assert ("applied", "updated") in outcome and ("applied", "created") in outcome
    assert ("rejected", "VERSION_CONFLICT") in outcome
    assert world.record("H", top["id"], workspaceKey=ws)["name"] == "Top edited"
    assert world.record("H", leaf["id"], workspaceKey=ws)["name"] == "Leaf meanwhile"
    added_record = _named(world, "H", ws)["Added in the file"]
    assert world.value(world.record("H", added_record["id"], workspaceKey=ws), "H.code") == "ADD"


@pytest.mark.journey("J27.10", "J27.11")
@pytest.mark.structures("H", "H.code")
def test_an_export_previewed_into_another_workspace_says_whose_records_they_are(world):
    """Given a parent and a child exported from one workspace. When the file is previewed into a
    second workspace of the instance. Then the job says before anything runs that its rows name
    records of the first workspace; the parent's row is refused as an ID taken there and the
    child's because its parent is there, each naming that workspace (0.9 J4a; D49's limit, said)."""
    source, target = _workspace(world), _workspace(world)
    top = world.made("H", "Top", workspace=source, values={"H.code": "T"})
    world.made("H", "Leaf", parent=top["id"], workspace=source, values={"H.code": "L"})
    content = _export(world, source, ("H",), "csv")

    job = _imported(world, "from-elsewhere.csv", content, _request(target, stage="preview"))
    assert job["state"] == "awaiting_confirmation", job["error"]
    assert job["notices"] == [
        {
            "code": "RECORD_IDS_OF_ANOTHER_WORKSPACE",
            "message": job["notices"][0]["message"],
            "details": {"workspaceKey": source, "rows": 2},
        }
    ]
    assert f"'{source}'" in job["notices"][0]["message"]

    refusals = {_code(item): item["error"] for item in _outcomes(world, job)}
    taken, parent = refusals["OBJECT_ALREADY_EXISTS"], refusals["REFERENCE_NOT_FOUND"]
    assert taken["details"]["workspaceKey"] == source and f"'{source}'" in taken["message"]
    assert parent["details"]["workspaceKey"] == source and f"'{source}'" in parent["message"]
    assert "parent" in parent["message"]


# The counterpart derivation API.md documents (0.9 J5, D97): a record of another workspace loads into
# workspace W as the record whose ID is uuid5(namespace, "W/{its ID}") marked as version 4.
COUNTERPARTS = UUID("2218e355-f627-4a22-a009-bebe5423891c")


def _counterpart(workspace, object_id):
    return str(UUID(bytes=uuid5(COUNTERPARTS, f"{workspace}/{object_id}").bytes, version=4))


def _source(world):
    """Workspace A: H records Top and Leaf (below Top), a K record and a Bnn from Leaf to it."""
    a = _workspace(world)
    top = world.made("H", "Top", workspace=a, values={"H.code": "T"})
    leaf = world.made("H", "Leaf", parent=top["id"], workspace=a, values={"H.code": "L"})
    token = world.made("K", "Token", workspace=a, values={"K.code": "K1"})
    ok(world.relate("Bnn", leaf["id"], token["id"], {"Bnn.weight": 2}), 201)
    return a, top, leaf, token


def _joined(world, source_id, workspace, **context):
    page = ok(
        world.api.get(
            "/relations",
            objectId=source_id,
            relationTypeKey=world.key("Bnn"),
            workspaceKey=workspace,
            pageSize=100,
            **context,
        )
    )
    return {item["object"]["id"] for item in page["items"]}


@pytest.mark.journey("J27.14")
@pytest.mark.structures("H", "H.code", "K", "K.code", "Bnn", "Bnn.weight")
def test_another_workspaces_export_loads_whole_as_this_workspaces_own_records(world):
    """Given Top, Leaf below it, Token and a relationship in workspace A. When A's export is
    imported into B with counterparts. Then each record is created in B with its counterpart ID and
    names its source ID; Leaf stands below Top's counterpart and the relationship joins the
    counterparts; A is unchanged; the job says the rows load as B's own records (0.9 J5)."""
    a, top, leaf, token = _source(world)
    b = _workspace(world)
    content = _export(world, a, ("H", "K"), "csv")

    job = _imported(world, "from-a.csv", content, _request(b, otherWorkspaceIds="counterparts"))
    assert job["state"] == "completed" and job["result"] == "applied", job["error"]
    assert job["notices"] == [
        {
            "code": "RECORD_IDS_AS_COUNTERPARTS",
            "message": job["notices"][0]["message"],
            "details": {"workspaceKey": a, "rows": 3},
        }
    ]
    created = {
        item["sourceId"]: item
        for item in _outcomes(world, job)
        if item.get("action") == "created" and "sourceId" in item
    }
    for record in (top, leaf, token):
        assert created[record["id"]]["id"] == _counterpart(b, record["id"])
    assert world.record("H", _counterpart(b, leaf["id"]), workspaceKey=b)["parentObjectId"] == (
        _counterpart(b, top["id"])
    )
    assert _joined(world, _counterpart(b, leaf["id"]), b) == {_counterpart(b, token["id"])}
    assert world.record("H", leaf["id"], workspaceKey=a)["parentObjectId"] == top["id"]
    assert set(_named(world, "H", a)) == {"Top", "Leaf"}


@pytest.mark.journey("J27.14")
@pytest.mark.structures("H", "H.code", "K", "K.code", "Bnn", "Bnn.weight")
def test_another_workspaces_export_sent_again_changes_nothing_and_an_edit_overwrites(world):
    """Given A's export loaded into B with counterparts. When the same file is sent again. Then
    every item is unchanged and B holds no further record. When Top is renamed in the file and it
    is sent with onExisting overwrite. Then only Top's counterpart is updated (D98: the file's
    versions are A's and are not claimed)."""
    a, top, _leaf, _token = _source(world)
    b = _workspace(world)
    content = _export(world, a, ("H", "K"), "csv")
    first = _imported(world, "a.csv", content, _request(b, otherWorkspaceIds="counterparts"))
    assert first["result"] == "applied", first["error"]

    again = _imported(
        world, "a.csv", content, _request(b, otherWorkspaceIds="counterparts", onExisting="reject")
    )
    assert {(i["status"], i.get("action")) for i in _outcomes(world, again)} == {
        ("applied", "unchanged")
    }
    assert set(_named(world, "H", b)) == {"Top", "Leaf"}

    rows = list(csv.reader(io.StringIO(content.decode("utf-8-sig"))))
    column = {name: rows[0].index(name) for name in rows[0]}
    for row in rows[1:]:
        if row[column["id"]] == top["id"]:
            row[column["name"]] = "Top renamed"
    edited = _imported(
        world, "edited.csv", _csv(rows), _request(b, otherWorkspaceIds="counterparts")
    )
    actions = {(i.get("sourceId"), i.get("action")) for i in _outcomes(world, edited)}
    assert (top["id"], "updated") in actions
    assert {action for source, action in actions if source != top["id"]} == {"unchanged"}
    assert world.record("H", _counterpart(b, top["id"]), workspaceKey=b)["name"] == "Top renamed"


@pytest.mark.journey("J27.14", "J11")
@pytest.mark.structures("H", "H.code", "K", "K.code", "Bnn", "Bnn.weight")
def test_another_workspaces_records_load_file_by_file(world):
    """Given A's H and K records exported without relationships and loaded into B with
    counterparts. When A's relationships, from a JSON Lines export, are sent to B as a batch with
    counterparts. Then they join B's counterparts. When a supplier file read through a profile
    names a new record's parent by A's ID. Then it stands below that parent's counterpart (D100)."""
    a, top, leaf, token = _source(world)
    b = _workspace(world)
    records = _export(world, a, ("H", "K"), "csv", relations="none")
    loaded = _imported(world, "records.csv", records, _request(b, otherWorkspaceIds="counterparts"))
    assert loaded["result"] == "applied", loaded["error"]
    assert _joined(world, _counterpart(b, leaf["id"]), b) == set()

    lines = _export(world, a, ("H", "K"), "jsonl").decode().splitlines()
    relations = [item for item in map(json.loads, lines) if item["op"] == "ensureRelation"]
    batch = ok(
        world.api.post(
            "/batches",
            {
                "workspaceKey": b,
                "policy": "atomic",
                "run": "inline",
                "otherWorkspaceIds": "counterparts",
                "items": relations,
            },
        )
    )
    assert batch["job"]["result"] == "applied", batch["items"]
    assert _joined(world, _counterpart(b, leaf["id"]), b) == {_counterpart(b, token["id"])}

    profile = {
        "key": f"children-{uuid4().hex[:8]}",
        "name": "Children",
        "sources": [
            {
                "applicationKey": world.app("H"),
                "objectTypeKey": world.key("H"),
                "columns": [
                    {"column": "Code", "attributeTypeKey": world.key("H.code")},
                    {"column": "Name", "field": "name"},
                    {
                        "column": "Parent",
                        "parent": {"objectTypeKey": world.key("H"), "matchBy": {"field": "id"}},
                    },
                ],
            }
        ],
    }
    ok(world.api.post("/import-profiles", profile), 201)
    supplier = _csv([("Code", "Name", "Parent"), ("C2", "Second child", top["id"])])
    job = _imported(
        world,
        "children.csv",
        supplier,
        _request(b, profileKey=profile["key"], otherWorkspaceIds="counterparts"),
    )
    assert job["result"] == "applied", _outcomes(world, job)
    child = _named(world, "H", b)["Second child"]
    assert child["parentObjectId"] == _counterpart(b, top["id"])


@pytest.mark.journey("J27.14", "J27.3")
@pytest.mark.structures("H", "H.code", "K", "K.code", "Bnn", "Bnn.weight")
def test_a_workspaces_own_export_with_counterparts_stays_exact(world):
    """Given records made in B. When B's export is sent back to B with counterparts. Then every
    item is unchanged under B's own IDs, with no source ID: only another workspace's IDs are
    translated."""
    b, top, leaf, token = _source(world)
    content = _export(world, b, ("H", "K"), "csv")
    job = _imported(world, "own.csv", content, _request(b, otherWorkspaceIds="counterparts"))
    outcomes = _outcomes(world, job)
    assert {(i["status"], i.get("action")) for i in outcomes} == {("applied", "unchanged")}
    assert {i["id"] for i in outcomes if "id" in i} == {top["id"], leaf["id"], token["id"]}
    assert not any("sourceId" in i for i in outcomes)
    assert job["notices"] == []


@pytest.mark.journey("J27.14", "J27.10")
@pytest.mark.structures("H", "H.code")
def test_a_counterpart_not_loaded_yet_is_refused_saying_what_to_load_first(world):
    """Given A's export holding only Leaf. When it is imported into C with counterparts. Then Leaf's
    row is refused: its parent is a record of A whose counterpart is not in C, and the refusal says
    to load the file holding it first."""
    a = _workspace(world)
    top = world.made("H", "Top", workspace=a, values={"H.code": "T"})
    world.made("H", "Leaf", parent=top["id"], workspace=a, values={"H.code": "L"})
    c = _workspace(world)
    only_leaf = {"H": [{"field": "name", "op": "eq", "value": "Leaf"}]}
    content = _export(world, a, ("H",), "csv", where=only_leaf)

    job = _imported(world, "leaf.csv", content, _request(c, otherWorkspaceIds="counterparts"))
    [refused] = [i for i in _outcomes(world, job) if i["status"] == "rejected"]
    assert refused["error"]["code"] == "REFERENCE_NOT_FOUND"
    assert refused["error"]["details"]["workspaceKey"] == a
    assert f"'{a}'" in refused["error"]["message"]
    assert "load the file holding it first" in refused["error"]["message"]


@pytest.mark.journey("J27.14")
@pytest.mark.structures("H", "H.code", "K", "K.code", "Bnn", "Bnn.weight")
def test_another_workspaces_export_into_a_change_set_takes_the_live_counterparts(world):
    """Given A's export. When it is imported into a change set of B with counterparts. Then the
    records carry the counterpart IDs a live load would give; after publishing, live B reads them."""
    a, top, leaf, _token = _source(world)
    b = _workspace(world)
    cs = world.change_set(workspace=b)
    content = _export(world, a, ("H", "K"), "csv")
    request = {
        "changeSetId": cs["id"],
        "expectedChangeSetVersion": cs["version"],
        "policy": "independent",
        "onExisting": "overwrite",
        "stage": "execute",
        "otherWorkspaceIds": "counterparts",
    }
    job = _imported(world, "a.csv", content, request)
    assert job["result"] == "applied", job["error"]
    in_set = world.record("H", _counterpart(b, leaf["id"]), workspaceKey=b, changeSetId=cs["id"])
    assert in_set["parentObjectId"] == _counterpart(b, top["id"])
    world.publish(cs, workspace=b)
    assert world.record("H", _counterpart(b, top["id"]), workspaceKey=b)["name"] == "Top"


def _sc10_rows():
    return [
        LEDGER_HEADER,
        ("S-NEW", "New value", "Ann", "Summary", 10, True, "2026-01-01"),
        ("S-OLD", "Existing value renamed", "Bob", "Summary", 20, False, "2026-01-01"),
        ("S-BAD", "Invalid number", "Cid", "Summary", "twelve", False, "2026-01-01"),
        ("S-DUP", "Duplicate one", "Dee", "Summary", 30, False, "2026-01-01"),
        ("S-DUP", "Duplicate two", "Dee", "Summary", 30, False, "2026-01-01"),
    ]


@pytest.mark.journey("J27.10", "J27.8")
@pytest.mark.structures("R", "R.u", "R.n", "R.b", "R.dt", "R.q", "R.x1", "H", "K", "K.code", "Bnn")
def test_rows_that_cannot_load_are_rejected_by_row_and_the_rest_load(world):
    """Given an existing ledger S-OLD, two K tokens sharing one code and the SC-10 file: a new
    value, an existing value, an invalid number, two rows with one key and different names, and
    branches naming the shared token code, an unknown code, and a known one. When it is imported
    under independent with overwrite. Then the new one is created, the existing one updated, the
    number refused with its column, both duplicates refused naming each other, the ambiguous match
    refused with its count and the unknown one as not found. Under atomic nothing is written and
    the other items are unprocessed. Sent again with the same Idempotency-Key the job is replayed;
    sent again without one, every applied row is unchanged."""
    ws = _workspace(world)
    old = world.made("R", "Existing value", workspace=ws, values={"R.u": "S-OLD"})
    for n in (1, 2):
        world.made("K", f"Shared {n}", workspace=ws, values={"K.code": "SHARED"})
    world.made("K", "Known", workspace=ws, values={"K.code": "KNOWN"})
    world.made("K", "Other", workspace=ws, values={"K.code": "OTHER"})
    profile = _ledger_profile(world)
    profile["sources"].append(
        {
            "sheet": "Branches",
            "applicationKey": world.app("H"),
            "objectTypeKey": world.key("H"),
            "columns": [
                {"column": "Name", "field": "name"},
                {"column": "Code", "attributeTypeKey": world.key("H.code")},
                {
                    "column": "Token",
                    "relation": {
                        "relationTypeKey": world.key("Bnn"),
                        "objectTypeKey": world.key("K"),
                        "matchBy": {"attributeTypeKey": world.key("K.code")},
                    },
                },
            ],
        }
    )
    profile = ok(world.api.post("/import-profiles", profile), 201)
    workbook = {
        "Ledgers": _sc10_rows(),
        "Branches": [
            ("Name", "Code", "Token"),
            ("Ambiguous branch", "B1", "SHARED"),
            ("Lost branch", "B2", "NOWHERE"),
            ("Good branch", "B3", "KNOWN"),
        ],
    }
    content = _xlsx(workbook)

    atomic = _imported(
        world, "sc10.xlsx", content, _request(ws, profileKey=profile["key"], policy="atomic")
    )
    statuses = {item["status"] for item in _outcomes(world, atomic)}
    assert statuses == {"rejected", "unprocessed"}, statuses
    assert "S-NEW" not in {
        world.value(world.record("R", r["id"], workspaceKey=ws), "R.u")
        for r in _named(world, "R", ws).values()
    }

    headers = {"Idempotency-Key": f"sc10-{uuid4().hex}"}
    job = _imported(world, "sc10.xlsx", content, _request(ws, profileKey=profile["key"]), headers)
    assert job["state"] == "completed" and job["result"] == "partial", job["error"]
    rows = _by_ref(_outcomes(world, job))
    assert [i["action"] for i in rows["Ledgers!2"]] == ["created"]
    assert [i["action"] for i in rows["Ledgers!3"]] == ["updated"]
    bad = rows["Ledgers!4"][0]
    assert _code(bad) == "INVALID_ATTRIBUTE_VALUE" and bad["error"]["details"]["column"] == "Score"
    for ref, other in (("Ledgers!5", 6), ("Ledgers!6", 5)):
        error = rows[ref][0]["error"]
        assert error["code"] == "DUPLICATE_KEY_IN_FILE" and other in error["details"]["rows"]
    ambiguous = rows["Branches!2"][0]["error"]
    assert ambiguous["code"] == "REFERENCE_AMBIGUOUS"
    assert ambiguous["details"]["count"] == 2 and ambiguous["details"]["column"] == "Token"
    assert _code(rows["Branches!3"][0]) == "REFERENCE_NOT_FOUND"
    assert {i["status"] for i in rows["Branches!4"]} == {"applied"}
    assert world.record("R", old["id"], workspaceKey=ws)["name"] == "Existing value renamed"

    replay = _send(world, "sc10.xlsx", content, _request(ws, profileKey=profile["key"]), headers)
    assert ok(replay, 202)["id"] == job["id"] and replay.headers["idempotent-replayed"] == "true"

    again = _imported(world, "sc10.xlsx", content, _request(ws, profileKey=profile["key"]))
    applied = [
        i
        for i in _outcomes(world, again)
        if i["status"] == "applied" and i["ref"].startswith("Ledgers!")
    ]
    assert applied and {i["action"] for i in applied} == {"unchanged"}


@pytest.mark.journey("J27.10")
@pytest.mark.structures("R", "R.u", "R.q", "R.x1", "K", "K.code", "B1n")
def test_rows_repeating_a_key_with_equal_values_load_as_one_record_with_every_relationship(world):
    """Given two K tokens. When a file holds two rows for one ledger number with equal values and
    a different token each in its relation column. Then the ledger is created once and holds both
    relationships."""
    ws = _workspace(world)
    first = world.made("K", "First", workspace=ws, values={"K.code": "T1"})
    second = world.made("K", "Second", workspace=ws, values={"K.code": "T2"})
    profile = _ledger_profile(world)
    profile["sources"][0]["columns"] = profile["sources"][0]["columns"][:4] + [
        {
            "column": "Token",
            "relation": {
                "relationTypeKey": world.key("B1n"),
                "objectTypeKey": world.key("K"),
                "matchBy": {"attributeTypeKey": world.key("K.code")},
            },
        }
    ]
    profile = ok(world.api.post("/import-profiles", profile), 201)
    rows = [
        ("Number", "Name", "Owner", "Summary", "Token"),
        ("L-1", "Ledger", "Ann", "Summary", "T1"),
        ("L-1", "Ledger", "Ann", "Summary", "T2"),
    ]
    job = _imported(world, "rows.csv", _csv(rows), _request(ws, profileKey=profile["key"]))
    assert job["state"] == "completed" and job["result"] == "applied", job["error"]
    ledgers = _named(world, "R", ws)
    assert list(ledgers) == ["Ledger"]
    assert _related(world, ledgers["Ledger"]["id"], "B1n", ws) == {first["id"], second["id"]}


@pytest.mark.journey("J27.10", "J27.8")
@pytest.mark.structures("H", "H.code", "Hparent")
def test_a_hierarchy_in_one_sheet_loads_parents_first_and_a_ring_is_refused(world):
    """Given a sheet of H rows whose parent column names rows further down, and three rows naming
    each other in a ring. When it is imported. Then every parent is created before its children
    whatever the row order; the three ring rows are refused as a cycle and the rest load."""
    ws = _workspace(world)
    profile = {
        "key": f"tree-{uuid4().hex[:6]}",
        "name": "Tree",
        "sources": [
            {
                "applicationKey": world.app("H"),
                "objectTypeKey": world.key("H"),
                "columns": [
                    {"column": "Name", "field": "name"},
                    {"column": "Code", "attributeTypeKey": world.key("H.code")},
                    {
                        "column": "Parent",
                        "parent": {"objectTypeKey": world.key("H"), "matchBy": {"field": "name"}},
                    },
                ],
            }
        ],
    }
    profile = ok(world.api.post("/import-profiles", profile), 201)
    rows = [
        ("Name", "Code", "Parent"),
        ("Leaf", "C3", "Middle"),
        ("Middle", "C2", "Root"),
        ("Root", "C1", None),
        ("Ring A", "RA", "Ring C"),
        ("Ring B", "RB", "Ring A"),
        ("Ring C", "RC", "Ring B"),
    ]
    job = _imported(world, "tree.csv", _csv(rows), _request(ws, profileKey=profile["key"]))
    rows_out = _by_ref(_outcomes(world, job))
    assert {_code(rows_out[f"csv!{n}"][0]) for n in (5, 6, 7)} == {"REFERENCE_CYCLE"}
    records = _named(world, "H", ws)
    assert set(records) == {"Leaf", "Middle", "Root"}
    assert records["Leaf"]["parentObjectId"] == records["Middle"]["id"]
    assert records["Middle"]["parentObjectId"] == records["Root"]["id"]
    assert records["Root"]["parentObjectId"] is None


@pytest.mark.journey("J27.10")
@pytest.mark.structures("R", "R.u", "R.n", "R.b", "R.dt", "R.q", "R.x1")
def test_a_file_that_does_not_fit_fails_before_anything_is_written(world):
    """Given a profile reading a Ledgers sheet. When a workbook lacks the sheet, one lacks a column,
    a file is not a workbook, an .xls file is sent, and a file is over the limit. Then the first two
    jobs fail with the mismatch naming each problem and write nothing; the third fails as
    unreadable; the .xls and the oversized file are refused before a job is stored."""
    ws = _workspace(world)
    profile = ok(world.api.post("/import-profiles", _ledger_profile(world)), 201)
    request = _request(ws, profileKey=profile["key"])

    job = _imported(world, "a.xlsx", _xlsx({"Other": [("x",)]}), request)
    assert job["state"] == "failed" and job["error"]["code"] == "IMPORT_FILE_MISMATCH", job["error"]
    assert job["error"]["details"]["problems"][0]["path"] == "/sources/0/sheet"
    header = tuple(name for name in LEDGER_HEADER if name != "Score")
    job = _imported(
        world,
        "b.xlsx",
        _xlsx({"Ledgers": [header, ("L-9", "Nine", "A", "S", True, "2026-01-01")]}),
        request,
    )
    assert job["state"] == "failed" and job["error"]["code"] == "IMPORT_FILE_MISMATCH", job["error"]
    assert [p["path"] for p in job["error"]["details"]["problems"]] == [
        "/sources/0/columns/4/column"
    ]
    job = _imported(world, "c.xlsx", b"not a workbook", request)
    assert job["state"] == "failed" and job["error"]["code"] == "IMPORT_FILE_UNREADABLE", job[
        "error"
    ]
    assert _named(world, "R", ws) == {}

    jobs = len(ok(world.api.get("/jobs", workspaceKey=ws))["items"])
    refused(_send(world, "old.xls", b"\xd0\xcf\x11\xe0", request), 422, "UNSUPPORTED_FILE_FORMAT")
    assert len(ok(world.api.get("/jobs", workspaceKey=ws))["items"]) == jobs


@pytest.mark.journey("J27.10")
@pytest.mark.structures("R", "R.u", "R.q", "R.x1")
@pytest.mark.settings(IMPORT_MAX_BYTES="100")
def test_a_file_over_the_limit_is_refused_naming_the_setting(world):
    """Given the service started with a 100-byte import limit. When a larger file is sent. Then it is
    refused naming the setting, its maximum and the file's size, and no job is stored."""
    ws = _workspace(world)
    profile = ok(world.api.post("/import-profiles", _ledger_profile(world)), 201)
    content = _csv(
        [LEDGER_HEADER] + [(f"L-{n}", "Name", "A", "S", 1, True, "2026-01-01") for n in range(20)]
    )
    error = refused(
        _send(world, "big.csv", content, _request(ws, profileKey=profile["key"])),
        413,
        "IMPORT_TOO_LARGE",
    )
    assert error["details"] == {
        "setting": "IMPORT_MAX_BYTES",
        "maximum": 100,
        "bytes": len(content),
    }
    assert ok(world.api.get("/jobs", workspaceKey=ws))["items"] == []


@pytest.mark.journey("J27.10")
@pytest.mark.structures("R")
@pytest.mark.settings(INTEGRATION_JOBS_ENABLED="false")
def test_with_job_creation_off_the_import_writes_are_absent_and_profiles_read(world):
    """Given the service started with job creation turned off. When an import is sent and a profile
    created. Then neither route is there, and profile reads still answer."""
    response = _send(world, "x.csv", b"a\n", _request("main"))
    assert response.status_code in (404, 405), response.text
    response = world.api.post("/import-profiles", {"key": "x", "name": "x", "sources": []})
    assert response.status_code in (404, 405), response.text
    ok(world.api.get("/import-profiles"))


# --- J3: preview, confirmation and outcomes by row -----------------------------------------------


def _previewed(world, name, content, request, headers=None):
    """A preview sent and run until it waits for confirmation."""
    job = _imported(world, name, content, {**request, "stage": "preview"}, headers)
    assert job["state"] == "awaiting_confirmation", (job["state"], job["error"])
    return job


def _rows(world, job, **params):
    rows, cursor = [], None
    while True:
        page = ok(world.api.get(f"/jobs/{job['id']}/rows", pageSize=2, cursor=cursor, **params))
        rows += page["items"]
        cursor = page.get("nextCursor")
        if not cursor:
            return rows


def _confirm(world, job):
    return world.api.post(f"/jobs/{job['id']}/confirm", None)


def _feed_head(world, ws):
    return ok(world.api.get(f"/workspaces/{ws}/feed", pageSize=1))["headPosition"]


def _sc10_profile(world):
    profile = _ledger_profile(world)
    profile["sources"].append(
        {
            "sheet": "Branches",
            "applicationKey": world.app("H"),
            "objectTypeKey": world.key("H"),
            "columns": [
                {"column": "Name", "field": "name"},
                {"column": "Code", "attributeTypeKey": world.key("H.code")},
                {
                    "column": "Token",
                    "relation": {
                        "relationTypeKey": world.key("Bnn"),
                        "objectTypeKey": world.key("K"),
                        "matchBy": {"attributeTypeKey": world.key("K.code")},
                    },
                },
            ],
        }
    )
    return ok(world.api.post("/import-profiles", profile), 201)


def _sc10_file():
    """A new value, an existing value, an invalid number, two rows with one key and different
    names, an ambiguous and a missing match."""
    return _xlsx(
        {
            "Ledgers": _sc10_rows(),
            "Branches": [
                ("Name", "Code", "Token"),
                ("Ambiguous branch", "B1", "SHARED"),
                ("Lost branch", "B2", "NOWHERE"),
            ],
        }
    )


def _sc10_world(world, ws):
    old = world.made("R", "Existing value", workspace=ws, values={"R.u": "S-OLD"})
    for n in (1, 2):
        world.made("K", f"Shared {n}", workspace=ws, values={"K.code": "SHARED"})
    return old


REFUSED_ROWS = {"Ledgers!4", "Ledgers!5", "Ledgers!6", "Branches!2", "Branches!3"}


def _codes_by_row(world, job):
    return {
        row["ref"]: tuple(o["error"]["code"] for o in row["outcomes"] if o["status"] == "rejected")
        for row in _rows(world, job, status="rejected")
    }


@pytest.mark.journey("J27.11", "J27.10")
@pytest.mark.structures("R", "R.u", "R.n", "R.b", "R.dt", "R.q", "R.x1", "H", "K", "K.code", "Bnn")
def test_a_preview_changes_nothing_and_confirming_it_executes_with_the_same_outcomes(world):
    """Given an existing ledger S-OLD, two K tokens sharing one code and the SC-10 file. When it is
    previewed under independent. Then the job waits with a complete preview: one record created,
    one updated, the refused rows listed by row with their columns, the result partial; records,
    the feed head and the existing record's history are unchanged. When confirmed, the job
    completes with the same codes on the same rows, and a second confirm answers with the same
    job. Under atomic the preview says the result would be rejected and lists the same rows."""
    ws = _workspace(world)
    old = _sc10_world(world, ws)
    profile = _sc10_profile(world)
    names = set(_named(world, "R", ws))
    head = _feed_head(world, ws)
    history = ok(world.api.get(f"/objects/{world.key('R')}/{old['id']}/history"))["items"]

    job = _previewed(world, "sc10.xlsx", _sc10_file(), _request(ws, profileKey=profile["key"]))
    preview = job["preview"]
    assert preview["coverage"] == "complete"
    assert preview["counts"]["created"] == 1 and preview["counts"]["updated"] == 1
    assert preview["counts"]["rejected"] == len(REFUSED_ROWS)
    assert preview["result"] == "partial" and preview["previewedAt"]
    assert preview["rows"] == {"total": 7, "previewed": 7, "rejected": len(REFUSED_ROWS)}
    assert job["bindingReport"] is not None and job["finishedAt"] is None
    previewed_codes = _codes_by_row(world, job)
    assert set(previewed_codes) == REFUSED_ROWS
    score = next(r for r in _rows(world, job, status="rejected") if r["ref"] == "Ledgers!4")
    assert score["sheet"] == "Ledgers" and score["row"] == 4 and score["status"] == "rejected"
    assert score["outcomes"][0]["error"]["details"]["column"] == "Score"
    applied = {r["ref"]: r["actions"] for r in _rows(world, job, status="applied")}
    assert applied["Ledgers!2"]["created"] == 1 and applied["Ledgers!3"]["updated"] == 1
    one_row = ok(world.api.get(f"/jobs/{job['id']}/items", ref="Ledgers!3"))["items"]
    assert [i["ref"] for i in one_row] == ["Ledgers!3"]

    assert set(_named(world, "R", ws)) == names
    assert world.record("R", old["id"], workspaceKey=ws)["name"] == "Existing value"
    assert _feed_head(world, ws) == head
    after = ok(world.api.get(f"/objects/{world.key('R')}/{old['id']}/history"))["items"]
    assert after == history

    confirmed = ok(_confirm(world, job), 202)
    assert confirmed["state"] == "queued" and confirmed["confirmedAt"]
    assert confirmed["preview"] == preview
    _run(world)
    done = ok(world.api.get(f"/jobs/{job['id']}"))
    assert done["state"] == "completed" and done["result"] == "partial", done["error"]
    assert _codes_by_row(world, done) == previewed_codes
    assert world.record("R", old["id"], workspaceKey=ws)["name"] == "Existing value renamed"
    again = ok(_confirm(world, job), 202)
    assert again["id"] == job["id"] and again["state"] == "completed"
    assert again["confirmedAt"] == confirmed["confirmedAt"]

    atomic_ws = _workspace(world)
    _sc10_world(world, atomic_ws)
    atomic = _previewed(
        world,
        "sc10.xlsx",
        _sc10_file(),
        _request(atomic_ws, profileKey=profile["key"], policy="atomic"),
    )
    assert atomic["preview"]["result"] == "rejected"
    assert _codes_by_row(world, atomic) == previewed_codes


@pytest.mark.journey("J27.10", "J27.11")
@pytest.mark.structures("V", "V.code", "V.rank", "V.on")
def test_every_failing_cell_of_a_row_is_named_and_the_binding_report_counts_each_column(world):
    """Given two V records named "Twin" and one named "Root". When a file's rows hold a row with an
    invalid integer and an invalid date, a row under a parent no record is named, a row under the
    ambiguous "Twin", and two good rows, and it is previewed. Then the first row's error names both
    cells; the binding report counts one refusal in each of the two columns, and in the parent
    column one resolved by the file's own rows or the data, one not found and one ambiguous."""
    ws = _workspace(world)
    root = world.made("V", "Root", workspace=ws, values={"V.code": "ROOT"})
    for n in (1, 2):
        world.made("V", "Twin", workspace=ws, values={"V.code": f"TWIN{n}"})
    k = world.key
    profile = {
        "key": f"articles-{uuid4().hex[:6]}",
        "name": "Articles",
        "sources": [
            {
                "applicationKey": world.app("V"),
                "objectTypeKey": k("V"),
                "key": {"attributeTypeKey": k("V.code")},
                "columns": [
                    {"column": "Code", "attributeTypeKey": k("V.code")},
                    {"column": "Name", "field": "name"},
                    {"column": "Rank", "attributeTypeKey": k("V.rank")},
                    {"column": "On", "attributeTypeKey": k("V.on")},
                    {
                        "column": "Under",
                        "parent": {"objectTypeKey": k("V"), "matchBy": {"field": "name"}},
                    },
                ],
            }
        ],
    }
    profile = ok(world.api.post("/import-profiles", profile), 201)
    rows = [
        ("Code", "Name", "Rank", "On", "Under"),
        ("A1", "Two bad cells", "many", "yesterday", "Root"),
        ("A2", "Lost", 2, "2026-01-02", "Nobody"),
        ("A3", "Twin child", 3, "2026-01-03", "Twin"),
        ("A4", "Good", 4, "2026-01-04", "Root"),
        ("A5", "Top", 5, None, None),
    ]
    job = _previewed(world, "articles.csv", _csv(rows), _request(ws, profileKey=profile["key"]))
    first = ok(world.api.get(f"/jobs/{job['id']}/items", ref="csv!2"))["items"][0]["error"]
    assert first["code"] == "INVALID_ATTRIBUTE_VALUE" and first["details"]["column"] == "Rank"
    assert [(c["column"], c["code"]) for c in first["details"]["cells"]] == [
        ("Rank", "INVALID_ATTRIBUTE_VALUE"),
        ("On", "INVALID_ATTRIBUTE_VALUE"),
    ]
    [source] = job["bindingReport"]
    assert source["objectTypeKey"] == k("V") and source["rows"] == 5
    assert source["rejectedRows"] == 3
    columns = {c["column"]: c for c in source["columns"]}
    assert columns["Rank"]["binding"] == "attributeTypeKey"
    assert columns["Rank"]["target"] == k("V.rank")
    assert (columns["Rank"]["cells"], columns["Rank"]["refused"]) == (5, 1)
    assert (columns["On"]["empty"], columns["On"]["refused"], columns["On"]["converted"]) == (
        1,
        1,
        3,
    )
    under = columns["Under"]
    assert under["binding"] == "parent" and under["target"] == k("V")
    assert (under["cells"], under["empty"]) == (5, 1)
    assert (under["resolved"], under["notFound"], under["ambiguous"]) == (2, 1, 1)
    assert root["id"]


@pytest.mark.journey("J27.11")
@pytest.mark.structures("R", "R.u", "R.n", "R.b", "R.dt", "R.q", "R.x1", "H", "K", "K.code", "Bnn")
def test_execution_binds_again_so_data_changed_since_the_preview_counts(world):
    """Given the SC-10 file previewed. When the existing value is deleted and the token the missing
    match names is created through the API before confirming. Then the execution creates the value
    the preview reported updated, and loads the row the preview refused as not found."""
    ws = _workspace(world)
    old = _sc10_world(world, ws)
    profile = _sc10_profile(world)
    job = _previewed(world, "sc10.xlsx", _sc10_file(), _request(ws, profileKey=profile["key"]))
    assert _codes_by_row(world, job)["Branches!3"] == ("REFERENCE_NOT_FOUND",)

    current = world.record("R", old["id"], workspaceKey=ws)
    ok(
        world.api.delete(
            f"/objects/{world.key('R')}/{old['id']}", expectedVersion=current["version"]
        ),
        204,
    )
    world.made("K", "Found later", workspace=ws, values={"K.code": "NOWHERE"})
    ok(_confirm(world, job), 202)
    _run(world)
    done = ok(world.api.get(f"/jobs/{job['id']}"))
    assert done["state"] == "completed", done["error"]
    rows = {row["ref"]: row for row in _rows(world, done)}
    assert rows["Ledgers!3"]["actions"]["created"] == 1
    assert rows["Branches!3"]["status"] == "applied"
    assert "Branches!3" not in _codes_by_row(world, done)


@pytest.mark.journey("J27.11")
@pytest.mark.structures("R", "R.u", "R.n", "R.b", "R.dt", "R.q", "R.x1")
def test_a_preview_in_a_change_set_leaves_it_and_a_stale_claim_refuses_the_confirm(world):
    """Given a change set. When ledger rows are previewed into it. Then its version and contents are
    unchanged. When the change set is written meanwhile, confirm is refused as a version conflict
    and the job still waits."""
    ws = _workspace(world)
    cs = world.change_set(workspace=ws)
    profile = ok(world.api.post("/import-profiles", _ledger_profile(world)), 201)
    rows = [LEDGER_HEADER, ("L-1", "First", "Ann", "Summary", 1, True, "2026-01-02")]
    request = {
        "changeSetId": cs["id"],
        "expectedChangeSetVersion": cs["version"],
        "policy": "independent",
        "onExisting": "overwrite",
        "profileKey": profile["key"],
    }
    job = _previewed(world, "l.csv", _csv(rows), request)
    assert job["preview"]["counts"]["created"] == 1
    read = ok(world.api.get(f"/change-sets/{cs['id']}"))
    assert read["version"] == cs["version"]
    assert _named(world, "R", ws, changeSetId=cs["id"]) == {}

    world.made("R", "Meanwhile", workspace=ws, change_set=read)
    refused(_confirm(world, job), 409, "CHANGE_SET_VERSION_CONFLICT")
    assert ok(world.api.get(f"/jobs/{job['id']}"))["state"] == "awaiting_confirmation"


@pytest.mark.journey("J27.12")
@pytest.mark.structures("R", "R.u", "R.n", "R.b", "R.dt", "R.q", "R.x1")
@pytest.mark.settings(JOB_PREVIEW_MAX_ITEMS="5")
def test_a_large_file_is_previewed_in_part_and_every_binding_refusal_is_still_reported(world):
    """Given the preview limit at 5 items. When a 12-row file with two rows that cannot be bound is
    previewed. Then 5 items ran, the preview says sample with the rows it covers fully, and both
    binding refusals are reported; the capabilities name the limit."""
    limits = ok(world.api.get("/capabilities"))["integrationJobs"]["limits"]
    assert limits["previewMaxItems"] == 5
    ws = _workspace(world)
    profile = ok(world.api.post("/import-profiles", _ledger_profile(world)), 201)
    rows = [LEDGER_HEADER] + [
        (f"L-{n:02d}", f"Ledger {n}", "Ann", "Summary", n, True, "2026-01-02") for n in range(10)
    ]
    rows += [("L-X1", "Bad one", "Ann", "Summary", "x", True, "2026-01-02")]
    rows += [("L-X2", "Bad two", "Ann", "Summary", 1, True, "never")]
    job = _previewed(world, "big.csv", _csv(rows), _request(ws, profileKey=profile["key"]))
    preview = job["preview"]
    assert preview["coverage"] == "sample"
    assert preview["items"] == {"total": 12, "previewed": 7}
    assert preview["rows"] == {"total": 12, "previewed": 7, "rejected": 2}
    assert preview["counts"]["created"] == 5 and preview["counts"]["rejected"] == 2
    assert set(_codes_by_row(world, job)) == {"csv!12", "csv!13"}
    assert _named(world, "R", ws) == {}


@pytest.mark.journey("J27.11")
@pytest.mark.structures("R", "R.u", "R.n", "R.b", "R.dt", "R.q", "R.x1")
def test_a_waiting_preview_ends_by_cancel_or_retention_and_only_a_preview_confirms(world):
    """Given a waiting preview. When it is cancelled. Then it is cancelled at once, its file is gone
    and its outcomes still read. Given another, past its retention after the sweep, it is expired
    and confirm is refused as expired, as it is past its retention before the sweep. Confirming an executed import or a batch is refused as not
    awaiting confirmation, naming its state."""
    ws = _workspace(world)
    profile = ok(world.api.post("/import-profiles", _ledger_profile(world)), 201)
    rows = [LEDGER_HEADER, ("L-1", "First", "Ann", "Summary", 1, True, "2026-01-02")]
    request = _request(ws, profileKey=profile["key"])
    files = world.api.client.app.state.job_files

    job = _previewed(world, "l.csv", _csv(rows), request)
    assert files.source(job["id"]).is_file()
    cancelled = ok(world.api.post(f"/jobs/{job['id']}/cancel", None), 202)
    assert cancelled["state"] == "cancelled" and cancelled["finishedAt"]
    assert not files.source(job["id"]).is_file()
    assert [r["ref"] for r in _rows(world, job)] == ["csv!2"]
    refused(_confirm(world, job), 409, "JOB_NOT_AWAITING_CONFIRMATION")

    # Past its retention before the hourly sweep has run, it is expired all the same (0.9 R-F9).
    late = _previewed(world, "l.csv", _csv(rows), request)
    with SessionLocal() as session:
        session.execute(
            text("UPDATE jobs SET expires_at = now() - interval '1 second' WHERE id = :id"),
            {"id": late["id"]},
        )
        session.commit()
    refused(_confirm(world, late), 410, "JOB_EXPIRED")

    waiting = _previewed(world, "l.csv", _csv(rows), request)
    expires = datetime.fromisoformat(waiting["expiresAt"])
    world.api.client.app.state.job_worker.sweep(expires + timedelta(seconds=1))
    assert ok(world.api.get(f"/jobs/{waiting['id']}"))["state"] == "expired"
    refused(_confirm(world, waiting), 410, "JOB_EXPIRED")

    executed = _imported(world, "l.csv", _csv(rows), request)
    error = refused(_confirm(world, executed), 409, "JOB_NOT_AWAITING_CONFIRMATION")
    assert error["details"]["state"] == "completed"
    batch = ok(
        world.api.post(
            "/batches",
            {
                "workspaceKey": ws,
                "policy": "independent",
                "run": "inline",
                "items": [{"op": "delete", "target": {"id": str(uuid4())}, "expectedVersion": 1}],
            },
        )
    )
    refused(_confirm(world, batch["job"]), 409, "JOB_NOT_AWAITING_CONFIRMATION")
    refused(world.api.get(f"/jobs/{batch['job']['id']}/rows"), 404, "JOB_HAS_NO_ROWS")


@pytest.mark.journey("J27.10", "J24")
@pytest.mark.structures("R", "R.u", "R.n", "R.b", "R.dt", "R.q", "R.x1")
@pytest.mark.settings(JOB_CHUNK_ITEMS="3")
def test_an_interrupted_import_resumes_and_a_retry_with_its_key_creates_nothing_twice(world):
    """Given a 10-row file sent with an Idempotency-Key and three items a chunk. When the worker
    binds it, runs one chunk and stops, and another worker takes the job over. Then the job
    completes with every row created once; sent again with the key it is answered with the same
    job and nothing more is created."""
    ws = _workspace(world)
    profile = ok(world.api.post("/import-profiles", _ledger_profile(world)), 201)
    rows = [LEDGER_HEADER] + [
        (f"L-{n:02d}", f"Ledger {n}", "Ann", "Summary", n, True, "2026-01-02") for n in range(10)
    ]
    content = _csv(rows)
    headers = {"Idempotency-Key": f"resume-{uuid4().hex}"}
    request = _request(ws, profileKey=profile["key"])
    job = ok(_send(world, "l.csv", content, request, headers), 202)

    state = world.api.client.app.state
    first = JobWorker(SessionLocal, WorkerSettings(3, 120, 7), owner="first", files=state.job_files)
    assert first.run_once() and first.run_once()
    midway = ok(world.api.get(f"/jobs/{job['id']}"))
    assert midway["state"] == "running" and midway["progress"]["processed"] == 3
    first.stop()
    second = JobWorker(
        SessionLocal, WorkerSettings(3, 120, 7), owner="second", files=state.job_files
    )
    second.run_until_idle()
    done = ok(world.api.get(f"/jobs/{job['id']}"))
    assert done["state"] == "completed" and done["counts"]["created"] == 10, done["error"]
    assert len(_named(world, "R", ws)) == 10

    replay = _send(world, "l.csv", content, request, headers)
    assert ok(replay, 202)["id"] == job["id"] and replay.headers["idempotent-replayed"] == "true"
    _run(world)
    assert len(_named(world, "R", ws)) == 10


@pytest.mark.journey("J13.9")
@pytest.mark.structures("H", "H.code", "K", "K.code", "Bcand")
def test_an_import_row_relating_a_record_that_is_no_candidate_is_refused(world):
    """Given K records coded "OK…" and "NO…" and a relationship whose K end takes only codes
    starting "OK". When a file of H records relates one row to each through that relationship, run
    independent. Then the row naming the "NO" K is refused with RELATION_CANDIDATE_REFUSED and the
    other is loaded with its relationship (0.9 K7, D174)."""
    ws = _workspace(world)
    tag = uuid4().hex[:6]
    good = world.made("K", f"{tag} good", values={"K.code": f"OK-{tag}"}, workspace=ws)
    world.made("K", f"{tag} bad", values={"K.code": f"NO-{tag}"}, workspace=ws)
    profile = {
        "key": f"picks-{tag}",
        "name": "Picks",
        "sources": [
            {
                "applicationKey": world.app("H"),
                "objectTypeKey": world.key("H"),
                "columns": [
                    {"column": "Code", "attributeTypeKey": world.key("H.code")},
                    {"column": "Name", "field": "name"},
                    {
                        "column": "Token",
                        "relation": {
                            "relationTypeKey": world.key("Bcand"),
                            "objectTypeKey": world.key("K"),
                            "matchBy": {"field": "name"},
                        },
                    },
                ],
            }
        ],
    }
    ok(world.api.post("/import-profiles", profile), 201)
    content = _csv(
        [
            ("Code", "Name", "Token"),
            ("G1", f"{tag} takes good", f"{tag} good"),
            ("B1", f"{tag} takes bad", f"{tag} bad"),
        ]
    )
    job = _imported(world, "picks.csv", content, _request(ws, profileKey=profile["key"]))
    codes = sorted(filter(None, (_code(item) for item in _outcomes(world, job))))
    assert codes == ["RELATION_CANDIDATE_REFUSED"], _outcomes(world, job)
    loaded = _named(world, "H", ws)
    assert _related(world, loaded[f"{tag} takes good"]["id"], "Bcand", ws) == {good["id"]}
