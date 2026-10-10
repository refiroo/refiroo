"""J27 — Exchange a supplier file: a workbook for people (USER_JOURNEYS.md, 0.9 J6).

A collection exported as a workbook people work in: the columns the table shows, its relation
columns flattened, a sheet per chosen relationship, and a hidden import profile that reads it back.
Each test writes in a workspace of its own and runs the engine's workers itself. The workbook is
read and edited as a person's spreadsheet program would, with openpyxl.
"""

import io
import json
from uuid import uuid4

import pytest
from openpyxl import load_workbook
from scenario import ok, refused

XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
PROFILE_SHEET = "Import profile"
SUMMARY = "(not imported)"


def _workspace(world):
    key = f"people-{uuid4().hex[:8]}"
    ok(world.api.post("/workspaces", {"key": key, "label": "People site"}), 201)
    return key


def _people(world, ws, structure, columns, sheets, **extra):
    """``POST /exports`` of one type as a workbook for people; columns and sheets by structure."""
    return world.api.post(
        "/exports",
        {
            "workspaceKey": ws,
            "scope": {"types": [{"objectTypeKey": world.key(structure)}]},
            "format": "xlsx",
            "layout": "people",
            "people": {"columns": columns, "sheets": sheets, **extra},
        },
    )


def _workbook(world, ws, structure, columns, sheets):
    job = ok(_people(world, ws, structure, columns, sheets), 202)
    world.api.client.app.state.export_worker.run_until_idle()
    job = ok(world.api.get(f"/jobs/{job['id']}"))
    assert job["state"] == "completed", job["error"]
    response = world.api.get(f"/jobs/{job['id']}/output")
    assert response.status_code == 200, response.text
    return job, response.content


def _book(content):
    return load_workbook(io.BytesIO(content))


def _saved(book):
    buffer = io.BytesIO()
    book.save(buffer)
    return buffer.getvalue()


def _import(world, ws, content, stage="execute"):
    request = {"workspaceKey": ws, "policy": "independent", "onExisting": "reject", "stage": stage}
    job = ok(
        world.api.upload(
            "/imports",
            {"file": ("people.xlsx", content, XLSX)},
            {"request": json.dumps(request)},
        ),
        202,
    )
    world.api.client.app.state.job_worker.run_until_idle()
    return ok(world.api.get(f"/jobs/{job['id']}"))


def _outcomes(world, job):
    items, cursor = [], None
    while True:
        page = ok(world.api.get(f"/jobs/{job['id']}/items", pageSize=500, cursor=cursor))
        items += page["items"]
        cursor = page.get("nextCursor")
        if not cursor:
            return items


def _relation_name(world, structure, direction="outgoing"):
    key = world.key(structure)
    relation = next(r for r in world.configuration.model["relationTypes"] if r["key"] == key)
    return relation["name"] if direction == "outgoing" else relation["reverseName"]


def _header(sheet):
    return [cell.value for cell in sheet[1]]


def _visible(sheet):
    """The header labels of the columns a person sees, in order."""
    return [
        cell.value
        for cell in sheet[1]
        if cell.value is not None and not sheet.column_dimensions[cell.column_letter].hidden
    ]


def _rows(sheet):
    """Each data row as {header label: value}."""
    header = _header(sheet)
    return [
        dict(zip(header, (cell.value for cell in row), strict=False))
        for row in sheet.iter_rows(min_row=2)
        if any(cell.value is not None for cell in row)
    ]


def _column(sheet, label):
    return next(cell.column_letter for cell in sheet[1] if cell.value == label)


def _profile(book):
    sheet = book[PROFILE_SHEET]
    return json.loads("".join(row[0].value for row in sheet.iter_rows(min_row=2) if row[0].value))


def _tokens(world, ws, *names):
    return {
        name: world.made("K", name, workspace=ws, values={"K.code": f"C{n}"})
        for n, name in enumerate(names, start=1)
    }


def _relations(world, ws, object_id, structure):
    page = ok(
        world.api.get(
            "/relations",
            objectId=object_id,
            relationTypeKey=world.key(structure),
            workspaceKey=ws,
            pageSize=100,
        )
    )
    return {item["object"]["name"]: item for item in page["items"]}


H_STRUCTURES = ("H", "H.code", "H.rank", "K", "K.code", "Bn1", "Bnn", "Bnn.weight", "Bnn.note")


@pytest.mark.journey("J27", "J27.15")
@pytest.mark.structures(*H_STRUCTURES, "R", "R.u", "D", "D.active", "G", "Bown")
def test_a_workbook_for_people_holds_the_tables_columns_and_a_sheet_per_relationship(world):
    """Given an H related to one K through Bn1 and two through Bnn (with weights and a note), and an
    R owning two D records. When H is exported for people with a name, value, number, Bn1, Bnn and
    Bnn's K.code column and a sheet for Bnn. Then the main sheet is headed by the table's labels in
    its order, with typed cells, "; " lists and the hidden ID and version; Bnn's list (it has its own
    sheet) and its K.code column (a code that identifies nothing) are marked as summaries; the
    header is frozen and filtered, the name column filled as the header, the relation column
    otherwise; Bnn's sheet holds one row per relationship with its values. When R is exported with a
    sheet for Bown, the sheet holds the owned D records with their values, parent and owner. Each
    workbook carries a hidden import profile that is valid as a stored profile."""
    ws = _workspace(world)
    tokens = _tokens(world, ws, "Alpha token", "Beta token")
    branch = world.made("H", "First branch", workspace=ws, values={"H.code": "F", "H.rank": 3})
    world.made("H", "Second branch", workspace=ws, values={"H.code": "S"})
    ok(world.relate("Bn1", branch["id"], tokens["Alpha token"]["id"]), 201)
    ok(world.relate("Bnn", branch["id"], tokens["Alpha token"]["id"], {"Bnn.weight": 2}), 201)
    ok(
        world.relate(
            "Bnn", branch["id"], tokens["Beta token"]["id"], {"Bnn.weight": 5, "Bnn.note": "Main"}
        ),
        201,
    )
    columns = [
        "name",
        world.key("H.code"),
        world.key("H.rank"),
        f"related:{world.key('Bn1')}",
        f"related:{world.key('Bnn')}",
        f"related:{world.key('Bnn')}.{world.key('K.code')}",
    ]
    job, content = _workbook(world, ws, "H", columns, [world.key("Bnn")])
    assert job["output"]["layout"] == "people" and job["output"]["format"] == "xlsx"
    assert job["parameters"]["layout"] == "people"
    book = _book(content)
    main = book.worksheets[0]
    bn1, bnn = _relation_name(world, "Bn1"), _relation_name(world, "Bnn")
    labels = _visible(main)
    assert labels[:4] == ["Name", "H.code", "H.rank", bn1]
    assert labels[4].startswith(bnn) and SUMMARY in labels[4]
    assert "K.code" in labels[5] and SUMMARY in labels[5]
    assert all(SUMMARY not in label for label in labels[:4])
    assert main.freeze_panes == "A2" and main.auto_filter.ref

    rows = {row["Name"]: row for row in _rows(main)}
    first = rows["First branch"]
    assert first["H.code"] == "F" and first["H.rank"] == 3 and isinstance(first["H.rank"], int)
    assert first[bn1] == "Alpha token"
    assert first[labels[4]] == "Alpha token; Beta token"
    assert first[labels[5]] == "C1; C2"
    assert rows["Second branch"][bn1] is None
    hidden = [cell.value for cell in main[1] if main.column_dimensions[cell.column_letter].hidden]
    assert "Record ID" in hidden and "Record version" in hidden
    record = world.record("H", branch["id"], workspaceKey=ws)
    assert first["Record ID"] == branch["id"] and first["Record version"] == record["version"]

    name_fill = main[f"{_column(main, 'Name')}2"].fill.fgColor.rgb
    assert main["A1"].fill.fill_type == "solid" and main["A1"].fill.fgColor.rgb == name_fill
    hues = [item["key"] for item in world.configuration.model["objectTypes"]]
    if hues.index(world.key("H")) % 8 != hues.index(world.key("K")) % 8:
        assert main[f"{_column(main, bn1)}2"].fill.fgColor.rgb != name_fill

    sheet = book[book.sheetnames[1]]
    assert book.sheetnames[1].startswith(bnn[:20])
    pairs = {(row[_header(sheet)[0]], row[_header(sheet)[1]]): row for row in _rows(sheet)}
    assert set(pairs) == {("First branch", "Alpha token"), ("First branch", "Beta token")}
    beta = pairs[("First branch", "Beta token")]
    assert beta["Bnn.weight"] == 5 and beta["Bnn.note"] == "Main"
    assert book[PROFILE_SHEET].sheet_state == "hidden"
    stored = {"key": f"people-{uuid4().hex[:8]}", "name": "From the workbook", **_profile(book)}
    ok(world.api.post("/import-profiles", stored), 201)

    ledger = world.made("R", "Owning ledger", workspace=ws, values={"R.u": "OWN-1"})
    region = world.made("G", "Owning region", workspace=ws)
    place = world.dependant_parent(region["id"], ws)
    # One active D per R within a G: the second is inactive.
    for name, code, active in (("First permit", "P1", True), ("Second permit", "P2", False)):
        world.made(
            "D",
            name,
            parent=place,
            workspace=ws,
            values={"K.code": code, "D.active": active},
            relations=[world.owner("Bown", ledger["id"])],
        )
    _, content = _workbook(world, ws, "R", ["name", world.key("R.u")], [world.key("Bown")])
    book = _book(content)
    owned = book[book.sheetnames[1]]
    permits = {row["Name"]: row for row in _rows(owned)}
    assert set(permits) == {"First permit", "Second permit"}
    assert permits["First permit"]["K.code"] == "P1"
    assert "Owning ledger" in permits["First permit"].values()
    held = world.record("D", permits["First permit"]["Record ID"], workspaceKey=ws)
    assert held["parentObjectId"] == place
    stored = {"key": f"people-{uuid4().hex[:8]}", "name": "Owned", **_profile(book)}
    ok(world.api.post("/import-profiles", stored), 201)


@pytest.mark.journey("J27.16", "J27.9")
@pytest.mark.structures(*H_STRUCTURES, "Bh1n", "Bh1n.qty", "R", "R.u", "D", "G", "Bown")
def test_a_workbook_for_people_reads_back_exactly_the_changes_a_person_made(world):
    """Given H records with Bn1, Bnn and Bh1n (with a quantity) relationships. When H is exported
    for people with a sheet for Bh1n and imported untouched without a profile. Then the preview says
    every item is unchanged. When a value, a Bn1 name, Bnn's list (one name out, one in), a summary
    cell, a Bh1n quantity and a new Bh1n row are edited, a Bh1n row deleted, a record renamed in the
    app since the export is edited in the file, and a Bn1 cell names two records of one name. Then
    exactly those changes are applied, the summary is ignored, the removed name's relationship is
    gone, the deleted row's relationship remains, the renamed record is refused VERSION_CONFLICT
    and the ambiguous one REFERENCE_AMBIGUOUS. An owned record's value edited on R's Bown sheet is
    applied."""
    ws = _workspace(world)
    tokens = _tokens(
        world, ws, "Alpha token", "Beta token", "Gamma token", "Delta token", "Echo token"
    )
    _tokens(world, ws, "Twin token")
    world.made("K", "Twin token", workspace=ws, values={"K.code": "TW2"})
    first = world.made("H", "First branch", workspace=ws, values={"H.code": "F"})
    second = world.made("H", "Second branch", workspace=ws, values={"H.code": "S"})
    third = world.made("H", "Third branch", workspace=ws, values={"H.code": "T"})
    fourth = world.made("H", "Fourth branch", workspace=ws, values={"H.code": "V"})
    token = {name: item["id"] for name, item in tokens.items()}
    ok(world.relate("Bn1", first["id"], token["Alpha token"]), 201)
    ok(world.relate("Bn1", second["id"], token["Beta token"]), 201)
    ok(world.relate("Bnn", first["id"], token["Alpha token"]), 201)
    ok(world.relate("Bnn", first["id"], token["Beta token"]), 201)
    ok(world.relate("Bh1n", second["id"], token["Gamma token"], {"Bh1n.qty": 4}), 201)
    ok(world.relate("Bh1n", first["id"], token["Delta token"], {"Bh1n.qty": 2}), 201)
    columns = [
        "name",
        world.key("H.code"),
        f"related:{world.key('Bn1')}",
        f"related:{world.key('Bnn')}",
        f"related:{world.key('Bnn')}.{world.key('K.code')}",
    ]
    _, content = _workbook(world, ws, "H", columns, [world.key("Bh1n")])

    untouched = _import(world, ws, content, stage="preview")
    assert untouched["state"] == "awaiting_confirmation", untouched["error"]
    assert untouched["parameters"]["profile"]["embedded"]["objectTypeKey"] == world.key("H")
    counts = untouched["preview"]["counts"]
    assert counts["created"] == 0 and counts["updated"] == 0 and counts["rejected"] == 0
    assert {(i["status"], i.get("action")) for i in _outcomes(world, untouched)} == {
        ("applied", "unchanged")
    }

    version = world.record("H", third["id"], workspaceKey=ws)["version"]
    ok(world.update("H", third["id"], version, name="Third renamed"))
    book = _book(content)
    main = book.worksheets[0]
    labels = _visible(main)
    bn1, bnn_list, summary = labels[2], labels[3], labels[4]
    for row in range(2, main.max_row + 1):
        name = main[f"{_column(main, 'Name')}{row}"].value

        def cell(label, row=row):
            return main[f"{_column(main, label)}{row}"]

        if name == "First branch":
            cell("H.code").value = "F2"
            cell(bnn_list).value = "Alpha token; Echo token"
            cell(summary).value = "ignored"
        elif name == "Second branch":
            cell(bn1).value = "Gamma token"
        elif name == "Third branch":
            cell("H.code").value = "T2"
        elif name == "Fourth branch":
            cell(bn1).value = "Twin token"
    sheet = book[book.sheetnames[1]]
    header = _header(sheet)
    quantity = _column(sheet, "Bh1n.qty")
    pairs = {
        (sheet[f"A{row}"].value, sheet[f"B{row}"].value): row for row in range(2, sheet.max_row + 1)
    }
    sheet[f"{quantity}{pairs[('Second branch', 'Gamma token')]}"].value = 9
    sheet.delete_rows(pairs[("First branch", "Delta token")])
    added = [None] * len(header)
    added[0], added[1], added[header.index("Bh1n.qty")] = "First branch", "Alpha token", 1
    sheet.append(added)

    job = _import(world, ws, _saved(book))
    assert job["state"] == "completed", job["error"]
    outcomes = _outcomes(world, job)
    refused_codes = {
        item.get("error", {}).get("code") for item in outcomes if item["status"] == "rejected"
    }
    assert refused_codes == {"VERSION_CONFLICT", "REFERENCE_AMBIGUOUS"}
    assert world.value(world.record("H", first["id"], workspaceKey=ws), "H.code") == "F2"
    assert world.value(world.record("H", third["id"], workspaceKey=ws), "H.code") == "T"
    assert set(_relations(world, ws, second["id"], "Bn1")) == {"Gamma token"}
    assert set(_relations(world, ws, fourth["id"], "Bn1")) == set()
    assert set(_relations(world, ws, first["id"], "Bnn")) == {"Alpha token", "Echo token"}
    quantities = {
        name: item["relation"]["attributes"].get(world.key("Bh1n.qty"))
        for name, item in _relations(world, ws, second["id"], "Bh1n").items()
    }
    assert quantities == {"Gamma token": 9}
    assert set(_relations(world, ws, first["id"], "Bh1n")) == {"Delta token", "Alpha token"}
    alpha = world.record("K", token["Alpha token"], workspaceKey=ws)
    assert world.value(alpha, "K.code") == "C1"

    ledger = world.made("R", "Owning ledger", workspace=ws, values={"R.u": "OWN-2"})
    region = world.made("G", "Owning region", workspace=ws)
    permit = world.made(
        "D",
        "Owned permit",
        parent=world.dependant_parent(region["id"], ws),
        workspace=ws,
        values={"K.code": "P1"},
        relations=[world.owner("Bown", ledger["id"])],
    )
    _, content = _workbook(world, ws, "R", ["name", world.key("R.u")], [world.key("Bown")])
    book = _book(content)
    owned = book[book.sheetnames[1]]
    code = _column(owned, "K.code")
    for row in range(2, owned.max_row + 1):
        if owned[f"{_column(owned, 'Name')}{row}"].value == "Owned permit":
            owned[f"{code}{row}"].value = "P9"
    job = _import(world, ws, _saved(book))
    assert job["state"] == "completed", job["error"]
    actions = {(i["status"], i.get("action")) for i in _outcomes(world, job)}
    assert ("applied", "updated") in actions and all(status == "applied" for status, _ in actions)
    assert world.value(world.record("D", permit["id"], workspaceKey=ws), "K.code") == "P9"


@pytest.mark.journey("J27.17", "J27.5")
@pytest.mark.structures("H", "H.code", "K", "K.code", "Bnn")
def test_a_workbook_for_people_is_refused_for_what_it_cannot_hold(world):
    """Given a workspace. When a workbook for people is asked for two types, as CSV, with a column
    the type's table cannot show, or with a sheet for a relationship the type does not have. Then
    each is refused INVALID_EXPORT_LAYOUT at its pointer and no job is stored."""
    ws = _workspace(world)
    both = world.api.post(
        "/exports",
        {
            "workspaceKey": ws,
            "scope": {
                "types": [{"objectTypeKey": world.key("H")}, {"objectTypeKey": world.key("K")}]
            },
            "format": "xlsx",
            "layout": "people",
            "people": {"columns": ["name"]},
        },
    )
    assert refused(both, 422, "INVALID_EXPORT_LAYOUT")["details"]["path"] == "/scope/types"
    as_csv = world.api.post(
        "/exports",
        {
            "workspaceKey": ws,
            "scope": {"types": [{"objectTypeKey": world.key("H")}]},
            "format": "csv",
            "layout": "people",
            "people": {"columns": ["name"]},
        },
    )
    assert refused(as_csv, 422, "INVALID_EXPORT_LAYOUT")["details"]["path"] == "/format"
    unknown = _people(world, ws, "H", ["name", "no-such-field"], [])
    assert refused(unknown, 422, "INVALID_EXPORT_LAYOUT")["details"]["path"] == "/people/columns/1"
    foreign = _people(world, ws, "H", ["name"], [world.key("K.code")])
    assert refused(foreign, 422, "INVALID_EXPORT_LAYOUT")["details"]["path"] == "/people/sheets/0"
    jobs = ok(world.api.get("/jobs", workspaceKey=ws))
    assert jobs["items"] == []
