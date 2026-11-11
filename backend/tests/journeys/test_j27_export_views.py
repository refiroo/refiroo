"""J27 — Exchange a supplier file: export says what it exports (0.17 EX1, PP-D18–PP-D22).

An export that names a view gives the workbook the page shows; a type, an application or a
workspace exported for editing gives a sheet per type; every XLSX file says what it holds on an
"About this export" sheet and imports back as it is. Each test writes in a workspace of its own and
runs the engine's workers itself; the workbook is read and edited as a person's spreadsheet program
would, with openpyxl.
"""

import io
import json
from uuid import uuid4

import pytest
from openpyxl import load_workbook
from scenario import W1, ok, refused

XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
ABOUT = "About this export"
PROFILE_SHEET = "Import profile"


def _workspace(world):
    key = f"views-{uuid4().hex[:8]}"
    ok(world.api.post("/workspaces", {"key": key, "label": "Views site"}), 201)
    return key


def _export(world, ws, body):
    """``POST /exports``, run, and the completed job with its file."""
    job = ok(world.api.post("/exports", {"workspaceKey": ws, **body}), 202)
    world.api.client.app.state.export_worker.run_until_idle()
    job = ok(world.api.get(f"/jobs/{job['id']}"))
    assert job["state"] == "completed", job["error"]
    response = world.api.get(f"/jobs/{job['id']}/output")
    assert response.status_code == 200, response.text
    return job, load_workbook(io.BytesIO(response.content)), response.content


def _import(world, ws, content, stage="preview", change_set=None):
    request = {"workspaceKey": ws, "policy": "independent", "onExisting": "reject", "stage": stage}
    if change_set is not None:
        request = {
            "changeSetId": change_set["id"],
            "expectedChangeSetVersion": change_set["version"],
            "policy": "independent",
            "onExisting": "reject",
            "stage": stage,
        }
    job = ok(
        world.api.upload(
            "/imports",
            {"file": ("export.xlsx", content, XLSX)},
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


def _saved(book):
    buffer = io.BytesIO()
    book.save(buffer)
    return buffer.getvalue()


def _about(book):
    """The About sheet as {section heading: {label: value}}, in order."""
    sections, current = {}, None
    for label, value in book[ABOUT].iter_rows(min_row=4, max_col=2, values_only=True):
        if label is not None and value is None:
            current = sections.setdefault(label, {})
        elif label is not None and current is not None:
            current[label] = value
    return sections


@pytest.mark.journey("J27.23")
@pytest.mark.structures("H", "H.code", "K", "K.code", "Bnn", "Bnn.weight", "Bn1")
def test_a_type_exported_for_editing_has_a_sheet_per_type_and_imports_back_unchanged(world):
    """Given H and K records related through Bnn and Bn1. When both types are exported for editing
    and the file is imported without a profile. Then there is a sheet per type, the About sheet is
    the second sheet and says what the file holds, the hidden profile reads the file back, and
    every row comes back unchanged."""
    ws = _workspace(world)
    tokens = [
        world.made("K", name, workspace=ws, values={"K.code": f"C{n}"})
        for n, name in enumerate(("Alpha token", "Beta token", "Gamma token"), start=1)
    ]
    for n, name in enumerate(("First branch", "Second branch"), start=1):
        branch = world.made("H", name, workspace=ws, values={"H.code": f"B{n}"})
        ok(world.relate("Bnn", branch["id"], tokens[n - 1]["id"], {"Bnn.weight": n}), 201)
        ok(world.relate("Bn1", branch["id"], tokens[n]["id"]), 201)
    job, book, content = _export(
        world,
        ws,
        {
            "scope": {
                "types": [{"objectTypeKey": world.key("H")}, {"objectTypeKey": world.key("K")}]
            },
            "format": "xlsx",
            "layout": "people",
        },
    )
    assert book.sheetnames[1] == ABOUT and book.sheetnames[-1] == PROFILE_SHEET
    assert job["output"]["sheets"] == [
        item for item in book.sheetnames if item not in (ABOUT, PROFILE_SHEET)
    ]
    assert len(job["output"]["sheets"]) == 2
    about = _about(book)
    assert list(about) == ["What was exported", "What it holds", "How it loads back"]
    assert about["What was exported"]["Workspace"] == ws
    assert about["What was exported"]["Read from"] == "Live data"
    print(
        "HEADERS",
        [[c.value for c in sh[1]] for sh in book.worksheets[:1]],
        [[c.value for c in sh[1]] for sh in book.worksheets[2:3]],
    )
    preview = _import(world, ws, content)
    assert preview["state"] == "awaiting_confirmation", preview["error"]
    counts = preview["preview"]["counts"]
    rejected = [i for i in _outcomes(world, preview) if i["status"] == "rejected"]
    assert not rejected, rejected
    assert counts["created"] == 0 and counts["updated"] == 0 and counts["rejected"] == 0
    assert {(i["status"], i.get("action")) for i in _outcomes(world, preview)} == {
        ("applied", "unchanged")
    }


MATRIX = ("R", "R.u", "G", "M", "D", "D.active", "Bown", "Mown", "K.code")


def _matrix_export(world, view, state=None, **extra):
    body = {
        "view": {
            "applicationKey": world.key("A3"),
            "viewKey": world.key(view),
            "state": state or {},
        },
        "format": "xlsx",
        **extra,
    }
    return body


def _cells(book, sheet_index=0):
    """The first sheet as rows of values, headers included, by row number."""
    return [[cell.value for cell in row] for row in book.worksheets[sheet_index].iter_rows()]


def _owned_cell(world, row, parent, code, active=True):
    return world.made(
        "D",
        f"Cell {code}",
        parent=parent,
        values={"D.active": active, "K.code": code},
        relations=[world.owner("Bown", row["id"])],
    )


@pytest.mark.journey("J27.22", "J27.24")
@pytest.mark.structures(*MATRIX)
def test_a_matrix_that_creates_is_exported_and_its_cells_read_back(world):
    """Given a matrix of R rows and G columns whose cells are D records, with two columns holding
    cells and one holding none. When it is exported for editing. Then the first sheet has a group
    per column over the cell fields, hidden cell IDs and versions, the About sheet is second and says
    where new cells go; an unchanged file reads back unchanged. When a cell is edited, an empty cell
    is filled in a column holding cells and one in a column holding none, and another cell is
    cleared. Then the edit is applied under its version, the filled cell is created in the container
    that already holds the column's cells, the cleared cell changes nothing, and the column holding
    no cells refuses its cell, naming the column in plain words."""
    first, second, third = (world.made("G", f"Column {n}") for n in ("one", "two", "three"))
    in_first, in_second = world.dependant_parent(first["id"]), world.dependant_parent(second["id"])
    full = world.made("R", "Row full", values={"R.u": "RU-1"})
    half = world.made("R", "Row half", values={"R.u": "RU-2"})
    world.made("R", "Row empty", values={"R.u": "RU-3"})
    cell_one = _owned_cell(world, full, in_first, "C1")
    _owned_cell(world, full, in_second, "C2")
    _owned_cell(world, full, in_second, "C2b", active=False)
    _owned_cell(world, half, in_first, "C3")
    state = {"search": "Row ", "columnIds": [first["id"], second["id"], third["id"]]}
    _, book, content = _export(world, W1, _matrix_export(world, "Mown", state, layout="people"))
    assert book.sheetnames[1] == ABOUT and book.sheetnames[-1] == PROFILE_SHEET
    sheet = book.worksheets[0]
    group_row = [cell.value for cell in sheet[1]]
    header_row = [cell.value for cell in sheet[2]]
    assert group_row[0]  # the row type's name over its columns
    for group in ("Column one", "Column two", "Column three"):
        assert any(value and group in str(value) for value in group_row)
    assert header_row.count("K.code") == 3 and header_row.count("D.active") == 3
    hidden = [c.value for c in sheet[2] if sheet.column_dimensions[c.column_letter].hidden]
    assert "Record ID" in hidden and any("ID" in str(h) and "Column one" in str(h) for h in hidden)
    about = _about(book)
    assert any("go into" in heading for heading in about), list(about)
    place = next(rows for heading, rows in about.items() if "go into" in heading)
    assert "Place" in place
    assert "Editing in Numbers" not in about
    preview = _import(world, W1, content)
    assert preview["state"] == "awaiting_confirmation", preview["error"]
    assert {(i["status"], i.get("action")) for i in _outcomes(world, preview)} == {
        ("applied", "unchanged")
    }
    # A cell holding two records is written joined and its version says it is not loaded.
    assert any(value == "not loaded" for row in sheet.iter_rows(values_only=True) for value in row)
    assert any(
        "C2" in str(value) and ";" in str(value)
        for row in sheet.iter_rows(values_only=True)
        for value in row
    )

    def at(group, label):
        """The column of a field under a column group (the group's name is on its first cell)."""
        current = None
        for number, (heading, field) in enumerate(zip(sheet[1], sheet[2], strict=False), start=1):
            current = heading.value or current
            if current and group in str(current) and field.value == label:
                return number
        raise AssertionError((group, label))

    rows = {sheet.cell(n, 1).value: n for n in range(3, sheet.max_row + 1)}
    sheet.cell(rows["Row full"], at("Column one", "K.code")).value = "C1-edited"
    sheet.cell(rows["Row empty"], at("Column two", "K.code")).value = "N1"
    sheet.cell(rows["Row empty"], at("Column two", "D.active")).value = "Yes"
    sheet.cell(rows["Row half"], at("Column three", "K.code")).value = "N2"
    sheet.cell(rows["Row half"], at("Column one", "K.code")).value = None
    edited = _saved(book)
    preview = _import(world, W1, edited)
    assert preview["state"] == "awaiting_confirmation", preview["error"]
    outcomes = _outcomes(world, preview)
    refused = [i for i in outcomes if i["status"] == "rejected"]
    deep = "deep-scope" in world.configuration.shapes
    if deep:
        # The third column holds no cells of the view and no container: a container is proposed for it
        # (PP-D28), of the type the other columns use, and created with the cell.
        assert not refused
    else:
        # The cells stand directly under the column records: the column's own record is the only
        # container, holds none of the view's cells, and no container of another type is proposed.
        assert len(refused) == 1
        refusal = refused[0]["error"]
        assert refusal["code"] == "REFERENCE_NOT_FOUND" and "Column three" in str(refusal)
        assert "holds cells of this view" in refusal["message"]
    # Preview shows the new cell as new before anything is written.
    assert any(i.get("action") == "created" for i in outcomes)
    codes = lambda: {
        world.value(item, "K.code")
        for item in ok(world.api.get(f"/objects/{world.key('D')}", workspaceKey=W1, pageSize=100))[
            "items"
        ]
    }
    assert "N1" not in codes() and "N2" not in codes()
    ok(world.api.post(f"/jobs/{preview['id']}/confirm", {}), 202)
    world.api.client.app.state.job_worker.run_until_idle()
    assert {"C1-edited", "N1", "C2", "C2b", "C3"} <= codes() and ("N2" in codes()) == deep
    created = next(
        item
        for item in ok(world.api.get(f"/objects/{world.key('D')}", workspaceKey=W1, pageSize=100))[
            "items"
        ]
        if world.value(item, "K.code") == "N1"
    )
    assert created["parentObjectId"] == in_second
    assert cell_one


LINKS = ("R", "R.u", "G", "M", "D", "D.active", "Bown", "Bscope", "Mscope", "K.code")


def _related_ids(world, row_id, relation="Bscope"):
    page = ok(
        world.api.get(
            "/relations",
            objectId=row_id,
            relationTypeKey=world.key(relation),
            workspaceKey=W1,
            pageSize=100,
        )
    )
    return {item["object"]["id"] for item in page["items"]}


@pytest.mark.journey("J27.22", "J27.25")
@pytest.mark.structures(*LINKS)
def test_a_matrix_that_links_is_exported_and_its_cells_read_back(world):
    """Given a matrix of R rows and G columns whose cells link D records. When it is exported for
    editing. Then each column is one column listing the linked D records as name and code, the
    row's set version is hidden, a hidden sheet lists what each column may link and an unchanged
    file reads back unchanged. When a cell's list is edited (one out, one in), an empty cell is
    filled and another cell is cleared. Then only the edited and filled cells' links change, within
    their row and column, and the cleared cell's links remain."""
    g1, g2 = world.made("G", "Column one"), world.made("G", "Column two")
    in1, in2 = world.dependant_parent(g1["id"]), world.dependant_parent(g2["id"])
    owner = world.made("R", "Owner of cells", values={"R.u": "OWN"})
    first = _owned_cell(world, owner, in1, "L11")
    other = _owned_cell(world, owner, in1, "L12", active=False)
    second = _owned_cell(world, owner, in2, "L21")
    row_one = world.made("R", "Row 1", values={"R.u": "RU-1"})
    row_two = world.made("R", "Row 2", values={"R.u": "RU-2"})
    ok(world.relate("Bscope", row_one["id"], first["id"]), 201)
    ok(world.relate("Bscope", row_one["id"], second["id"]), 201)
    state = {"search": "Row ", "columnIds": [g1["id"], g2["id"]]}
    _, book, content = _export(world, W1, _matrix_export(world, "Mscope", state))
    sheet = book.worksheets[0]
    header = [cell.value for cell in sheet[2]]
    assert sum("linked" in str(value) for value in header) == 2
    assert [item for item in book.worksheets if item.sheet_state == "hidden"]
    rows = {sheet.cell(n, 1).value: n for n in range(3, sheet.max_row + 1)}
    column_one = next(n for n, v in enumerate(header, 1) if v and "Column one" in str(v))
    column_two = next(n for n, v in enumerate(header, 1) if v and "Column two" in str(v))
    cell_text = sheet.cell(rows["Row 1"], column_one).value
    assert cell_text.startswith("Cell L11")
    preview = _import(world, W1, content)
    assert preview["state"] == "awaiting_confirmation", preview["error"]
    assert {(i["status"], i.get("action")) for i in _outcomes(world, preview)} == {
        ("applied", "unchanged")
    }
    sheet.cell(rows["Row 1"], column_one).value = cell_text.replace("L11", "L12")
    sheet.cell(rows["Row 1"], column_two).value = None
    sheet.cell(rows["Row 2"], column_two).value = (
        sheet.cell(rows["Row 1"], column_two).value or "Cell L21"
    )
    preview = _import(world, W1, _saved(book))
    assert preview["state"] == "awaiting_confirmation", preview["error"]
    rejected = [i for i in _outcomes(world, preview) if i["status"] == "rejected"]
    assert not rejected, rejected
    ok(world.api.post(f"/jobs/{preview['id']}/confirm", {}), 202)
    world.api.client.app.state.job_worker.run_until_idle()
    assert _related_ids(world, row_one["id"]) == {other["id"], second["id"]}
    assert _related_ids(world, row_two["id"]) == {second["id"]}


RELATIONSHIPS = (
    "A1",
    "H",
    "H.code",
    "K",
    "K.code",
    "Bnn",
    "Bnn.weight",
    "Bnn.note",
    "Vrt",
    "Vrg",
    "Vnn",
)


def _relationship_scene(world, ws):
    tokens = {
        name: world.made("K", name, workspace=ws, values={"K.code": f"T{n}"})
        for n, name in enumerate(("Alpha token", "Beta token", "Gamma token"), start=1)
    }
    first = world.made("H", "First branch", workspace=ws, values={"H.code": "F"})
    second = world.made("H", "Second branch", workspace=ws, values={"H.code": "S"})
    ok(world.relate("Bnn", first["id"], tokens["Alpha token"]["id"], {"Bnn.weight": 2}), 201)
    ok(
        world.relate(
            "Bnn", first["id"], tokens["Beta token"]["id"], {"Bnn.weight": 5, "Bnn.note": "Main"}
        ),
        201,
    )
    ok(world.relate("Bnn", second["id"], tokens["Gamma token"]["id"], {"Bnn.weight": 1}), 201)
    return first, second, tokens


def _view(world, key, **state):
    return {
        "view": {
            "applicationKey": world.key("A1"),
            "viewKey": world.configuration.keys.get(key, key),
            "state": state,
        },
        "format": "xlsx",
    }


@pytest.mark.journey("J27.22")
@pytest.mark.structures(*RELATIONSHIPS)
def test_a_relationships_table_and_grid_are_exported_and_their_values_read_back(world):
    """Given H records related to K records with weights and notes. When the relationships table is
    exported, then it has a row per relationship with both records' columns, the values and hidden
    IDs, reads back unchanged, and an edited weight and a new row naming two records are applied.
    When the relationships grid is exported, then it has a row per H and a group per K with Linked,
    the weight and the note, reads back unchanged, a weight edited at a linked pair is applied and
    Yes on an unlinked pair links it with its values while No removes nothing."""
    ws = _workspace(world)
    first, second, _ = _relationship_scene(world, ws)
    _, book, content = _export(world, ws, _view(world, "Vrt"))
    sheet = book.worksheets[0]
    header = [cell.value for cell in sheet[1]]
    assert header[:2] == ["H", "K"] and "Bnn.weight" in header and "Bnn.note" in header
    assert sheet.max_row == 4  # a header and three relationships
    preview = _import(world, ws, content)
    assert {(i["status"], i.get("action")) for i in _outcomes(world, preview)} == {
        ("applied", "unchanged")
    }
    weight = header.index("Bnn.weight") + 1
    for row in range(2, sheet.max_row + 1):
        if sheet.cell(row, 1).value == "First branch" and sheet.cell(row, 2).value == "Alpha token":
            sheet.cell(row, weight).value = 9
    added = [None] * len(header)
    added[0], added[1], added[weight - 1] = "Second branch", "Alpha token", 4
    sheet.append(added)
    preview = _import(world, ws, _saved(book))
    rejected = [i for i in _outcomes(world, preview) if i["status"] == "rejected"]
    assert not rejected, rejected
    ok(world.api.post(f"/jobs/{preview['id']}/confirm", {}), 202)
    world.api.client.app.state.job_worker.run_until_idle()
    pairs = ok(
        world.api.get(
            "/relations",
            objectId=first["id"],
            relationTypeKey=world.key("Bnn"),
            workspaceKey=ws,
            pageSize=100,
        )
    )["items"]
    assert {item["object"]["name"]: item["relation"]["attributes"] for item in pairs} == {
        "Alpha token": {world.key("Bnn.weight"): 9},
        "Beta token": {world.key("Bnn.weight"): 5, world.key("Bnn.note"): "Main"},
    }
    assert "Alpha token" in {
        item["object"]["name"]
        for item in ok(
            world.api.get(
                "/relations",
                objectId=second["id"],
                relationTypeKey=world.key("Bnn"),
                workspaceKey=ws,
                pageSize=100,
            )
        )["items"]
    }

    _, book, content = _export(world, ws, _view(world, "Vrg"))
    grid = book.worksheets[0]
    groups = [cell.value for cell in grid[1] if cell.value]
    assert {"Alpha token", "Beta token", "Gamma token"} <= {
        value.split(" (")[0] for value in groups
    }
    labels = [cell.value for cell in grid[2]]
    assert sum(str(label).startswith("Linked") for label in labels) == 3
    preview = _import(world, ws, content)
    assert {(i["status"], i.get("action")) for i in _outcomes(world, preview)} == {
        ("applied", "unchanged")
    }
    names = {grid.cell(row, 1).value: row for row in range(3, grid.max_row + 1)}
    gamma = next(
        n for n, v in enumerate(labels, 1) if str(v).startswith("Linked") and "Gamma" in str(v)
    )
    gamma_weight = next(
        n for n, v in enumerate(labels, 1) if "Bnn.weight" in str(v) and "Gamma" in str(v)
    )
    assert grid.cell(names["First branch"], gamma).value == "No"
    grid.cell(names["First branch"], gamma).value = "Yes"
    grid.cell(names["First branch"], gamma_weight).value = 7
    preview = _import(world, ws, _saved(book))
    rejected = [i for i in _outcomes(world, preview) if i["status"] == "rejected"]
    assert not rejected, rejected
    ok(world.api.post(f"/jobs/{preview['id']}/confirm", {}), 202)
    world.api.client.app.state.job_worker.run_until_idle()
    linked = ok(
        world.api.get(
            "/relations",
            objectId=first["id"],
            relationTypeKey=world.key("Bnn"),
            workspaceKey=ws,
            pageSize=100,
        )
    )["items"]
    assert {item["object"]["name"] for item in linked} == {
        "Alpha token",
        "Beta token",
        "Gamma token",
    }


@pytest.mark.journey("J27.22")
@pytest.mark.structures(*RELATIONSHIPS)
def test_a_table_and_a_mapping_grid_export_what_the_page_shows(world):
    """Given H records related to K records. When the table view is exported with a filter, with a
    search and with its columns, and the mapping grid is exported. Then only the rows the page
    showed are written, the About sheet words the search and filters, and the mapping grid has a
    row per H with its mapped K as a column that, edited, changes the mapping."""
    ws = _workspace(world)
    _, second, _ = _relationship_scene(world, ws)
    table = f"{world.key('H')}--list"
    code = world.key("H.code")
    _, book, _ = _export(
        world,
        ws,
        _view(
            world, table, where=[{"field": code, "op": "eq", "value": "F"}], columns=["name", code]
        ),
    )
    sheet = book.worksheets[0]
    assert [cell.value for cell in sheet[1]][:2] == ["Name", "H.code"]
    assert sheet.max_row == 2 and sheet["A2"].value == "First branch"
    assert "H.code" in _about(book)["What was exported"]["Search and filters"]
    _, book, _ = _export(world, ws, _view(world, table, search="Second"))
    assert book.worksheets[0].max_row == 2 and book.worksheets[0]["A2"].value == "Second branch"
    assert "Second" in _about(book)["What was exported"]["Search and filters"]

    _, book, content = _export(world, ws, _view(world, "Vnn"))
    sheet = book.worksheets[0]
    header = [cell.value for cell in sheet[1]]
    mapped = next(n for n, label in enumerate(header, 1) if "forward" in str(label))
    assert sheet.max_row == 3
    preview = _import(world, ws, content)
    assert {(i["status"], i.get("action")) for i in _outcomes(world, preview)} == {
        ("applied", "unchanged")
    }
    rows = {sheet.cell(n, 1).value: n for n in range(2, sheet.max_row + 1)}
    sheet.cell(rows["Second branch"], mapped).value = "Alpha token; Gamma token"
    preview = _import(world, ws, _saved(book))
    rejected = [i for i in _outcomes(world, preview) if i["status"] == "rejected"]
    assert not rejected, rejected
    ok(world.api.post(f"/jobs/{preview['id']}/confirm", {}), 202)
    world.api.client.app.state.job_worker.run_until_idle()
    held = ok(
        world.api.get(
            "/relations",
            objectId=second["id"],
            relationTypeKey=world.key("Bnn"),
            workspaceKey=ws,
            pageSize=100,
        )
    )["items"]
    assert {item["object"]["name"] for item in held} == {"Alpha token", "Gamma token"}


@pytest.mark.journey("J27.23")
@pytest.mark.structures(*RELATIONSHIPS)
def test_the_technical_workbook_says_what_it_holds_and_imports_back_unchanged(world):
    """Given H and K records related through Bnn. When both types are exported as the technical
    XLSX. Then the About sheet is second and says it is ignored by an import, and the file
    imported unchanged reads every row as unchanged."""
    ws = _workspace(world)
    _relationship_scene(world, ws)
    job, book, content = _export(
        world,
        ws,
        {
            "scope": {
                "types": [{"objectTypeKey": world.key("H")}, {"objectTypeKey": world.key("K")}]
            },
            "format": "xlsx",
        },
    )
    assert job["output"]["layout"] == "technical"
    assert book.sheetnames[:3] == ["Records", ABOUT, "Relationships"]
    about = _about(book)
    assert list(about) == ["What was exported", "What it holds", "How it loads back"]
    assert about["What it holds"]["Records"].startswith("5:")
    preview = _import(world, ws, content)
    assert preview["state"] == "awaiting_confirmation", preview["error"]
    outcomes = {(i["status"], i.get("action")) for i in _outcomes(world, preview)}
    assert outcomes == {("applied", "unchanged")}, outcomes


@pytest.mark.journey("J27.26")
@pytest.mark.structures(*RELATIONSHIPS, *MATRIX[:0])
def test_an_export_of_a_view_is_refused_for_what_it_cannot_hold(world):
    """Given a workspace. When a view is exported that does not exist, or with state the view does
    not read, or as the technical tables or as CSV when it is not a table, or with a column that is
    no record, or with both a scope and a view. Then each is refused at its pointer and no job is
    stored."""
    ws = _workspace(world)
    _relationship_scene(world, ws)
    table = f"{world.key('H')}--list"

    def refused_at(body, path, code="INVALID_EXPORT_LAYOUT"):
        found = refused(world.api.post("/exports", {"workspaceKey": ws, **body}), 422, code)
        assert found["details"]["path"] == path, found

    refused_at(
        {"view": {"applicationKey": "nowhere", "viewKey": table}, "format": "xlsx"},
        "/view/applicationKey",
    )
    refused_at(
        {"view": {"applicationKey": world.key("A1"), "viewKey": "nothing"}, "format": "xlsx"},
        "/view/viewKey",
    )
    refused_at(_view(world, table, columnIds=[str(uuid4())]), "/view/state/columnIds")
    refused_at(_view(world, table, columns=["name", "no-such-field"]), "/view/state/columns/1")
    refused_at({**_view(world, "Vrt"), "layout": "technical"}, "/layout")
    refused_at({**_view(world, "Vrt"), "format": "csv"}, "/format")
    refused_at(_view(world, "Vrg", columnIds=[str(uuid4())]), "/view/state/columnIds/0")
    refused_at(
        _view(world, table, where=[{"field": "no-such-field", "op": "eq", "value": 1}]),
        "/scope/types/0/where/0/field",
        code="INVALID_QUERY",
    )
    both = refused(
        world.api.post(
            "/exports",
            {
                "workspaceKey": ws,
                **_view(world, table),
                "scope": {"types": [{"objectTypeKey": world.key("H")}]},
            },
        ),
        422,
        "REQUEST_VALIDATION_ERROR",
    )
    assert both
    assert ok(world.api.get("/jobs", workspaceKey=ws))["items"] == []


@pytest.mark.journey("J27.24")
@pytest.mark.structures(*MATRIX)
def test_a_matrix_exported_from_a_change_set_loads_back_into_it(world):
    """Given a change set over a matrix's data. When the matrix is exported from the change set,
    a cell is edited and the file is imported into the change set. Then the cell changes in the change
    set and live data is as it was, and the About sheet names the change set."""
    column = world.made("G", "Column one")
    parent = world.dependant_parent(column["id"])
    row = world.made("R", "Row full", values={"R.u": "RU-1"})
    cell = _owned_cell(world, row, parent, "S1")
    change_set = world.change_set(name="Translations to correct")
    state = {"columnIds": [column["id"]]}
    _, book, content = _export(
        world,
        W1,
        {**_matrix_export(world, "Mown", state), "context": {"changeSetId": change_set["id"]}},
    )
    assert change_set["id"] in _about(book)["What was exported"]["Read from"]
    sheet = book.worksheets[0]
    code = next(n for n, v in enumerate(sheet[2], 1) if v.value == "K.code")
    sheet.cell(3, code).value = "S1-in-set"
    current = world.current(change_set)
    job = _import(world, W1, _saved(book), stage="execute", change_set=current)
    assert job["state"] == "completed", job["error"]
    in_set = world.record("D", cell["id"], changeSetId=change_set["id"])
    assert world.value(in_set, "K.code") == "S1-in-set"
    assert world.value(world.record("D", cell["id"], workspaceKey=W1), "K.code") == "S1"
    assert content


ROOMS = ("A1", "H", "H.code", "P", "C")


@pytest.mark.journey("J27.25")
@pytest.mark.structures(*ROOMS)
def test_a_matrix_that_links_and_creates_makes_a_new_name_where_the_column_already_holds_cells(
    world,
):
    """Given a model whose matrix of H rows and P columns lets a cell link and create C records, which
    stand directly under a column, and two columns, one holding a C. When it is exported, then the
    About sheet says where new records go. When a cell names an existing record the column may link
    and a new name, and a cell of the other column names a record of the first column. Then the
    existing one is linked, the new one is created under its column and linked, and the other row is
    refused naming the record."""
    import copy

    model = copy.deepcopy(world.configuration.model)
    model["release"]["version"] = f"{model['release']['version']}-matrix"
    relation = {
        "key": "x-links-room",
        "reverseKey": "x-links-room--rev",
        "name": "Links room",
        "reverseName": "Linked by",
    }
    model["relationTypes"].append(relation)
    model["objectTypeRelations"].append(
        {
            "relationTypeKey": relation["key"],
            "fromObjectTypeKey": world.key("H"),
            "toObjectTypeKey": world.key("C"),
            "cardinality": "many-to-many",
        }
    )
    code = world.key("H.code")
    view = {
        "key": "x-rooms-by-p",
        "name": "Rooms by P",
        "type": "relationMatrix",
        "config": {
            "relationTypeKey": relation["key"],
            "direction": "outgoing",
            "rowObjectTypeKey": world.key("H"),
            "columnObjectTypeKey": world.key("P"),
            "cellObjectTypeKey": world.key("C"),
            "rowColumns": ["name", code],
            "columnLabelField": "name",
            "cellFields": [code],
            "searchFields": ["name"],
            "cellActions": ["create", "link", "unlink"],
            "pageSize": 20,
        },
    }
    next(a for a in model["applications"] if a["key"] == world.key("A1"))["views"].append(view)
    release = world.install(model)
    ok(world.activate(release["id"]))
    ws = W1
    one, two = world.made("P", "Hall one"), world.made("P", "Hall two")
    room = world.made("C", "Room 1", parent=one["id"], values={"H.code": "R1"})
    # The column already holds a cell of the view: a record of it linked to a row.
    held = world.made("H", "Row held", values={"H.code": "HELD"})
    ok(
        world.api.post(
            "/relations",
            {
                "relationTypeKey": "x-links-room",
                "fromObjectId": held["id"],
                "toObjectId": room["id"],
                "attributes": {},
            },
        ),
        201,
    )
    row_a = world.made("H", "Row a", values={"H.code": "A"})
    world.made("H", "Row b", values={"H.code": "B"})
    state = {"columnIds": [one["id"], two["id"]]}
    body = {
        "view": {
            "applicationKey": world.key("A1"),
            "viewKey": view["key"],
            "state": state,
        },
        "format": "xlsx",
    }
    _, book, content = _export(world, ws, body)
    about = _about(book)
    containers = next(rows for heading, rows in about.items() if "go into" in heading)
    assert list(containers) == ["Place"]
    numbers = about["Editing in Numbers"]
    assert "Automatic" in str(numbers["To type new names"])
    sheet = book.worksheets[0]
    header = [cell.value for cell in sheet[2]]
    first = next(n for n, v in enumerate(header, 1) if v and "Hall one" in str(v))
    second = next(n for n, v in enumerate(header, 1) if v and "Hall two" in str(v))
    rows = {sheet.cell(n, 1).value: n for n in range(3, sheet.max_row + 1)}
    sheet.cell(rows["Row a"], first).value = "Room 1; Room 2"
    # The second column holds no cells of the view, so no place of it is in use: a new name is refused.
    sheet.cell(rows["Row b"], second).value = "Room 9"
    preview = _import(world, ws, _saved(book))
    outcomes = _outcomes(world, preview)
    refusal = next(i for i in outcomes if i["status"] == "rejected")["error"]
    assert refusal["code"] == "REFERENCE_NOT_FOUND" and "Room 9" in str(refusal)
    assert any(i.get("action") == "created" for i in outcomes)
    ok(world.api.post(f"/jobs/{preview['id']}/confirm", {}), 202)
    world.api.client.app.state.job_worker.run_until_idle()
    linked = ok(
        world.api.get(
            "/relations",
            objectId=row_a["id"],
            relationTypeKey="x-links-room",
            workspaceKey=ws,
            pageSize=100,
        )
    )["items"]
    names = {item["object"]["name"]: item["object"]["parentObjectId"] for item in linked}
    assert names == {"Room 1": one["id"], "Room 2": one["id"]}
    assert room and content


@pytest.mark.journey("J27.22", "J27.23")
@pytest.mark.structures(*ROOMS)
def test_a_tree_is_a_sheet_per_type_and_a_parent_two_records_share_a_name_is_found_by_its_id(world):
    """Given a tree of P above C, with two P records of one name. When the tree is exported and the
    file imported unchanged. Then there is a sheet per type, C's parent column is for reading with
    the parent's ID hidden (a name two records share cannot find one), every row reads back
    unchanged, and a C moved by editing its hidden parent ID is moved."""
    import copy

    model = copy.deepcopy(world.configuration.model)
    model["release"]["version"] = f"{model['release']['version']}-tree"
    application = next(a for a in model["applications"] if a["key"] == world.key("A1"))
    application["views"].append(
        {
            "key": "x-tree",
            "name": "Rooms tree",
            "type": "tree",
            "config": {
                "rootObjectTypeKeys": [world.key("P")],
                "objectTypeKeys": [world.key("P"), world.key("C")],
                "labelField": "name",
                "pageSize": 20,
            },
        }
    )
    ok(world.activate(world.install(model)["id"]))
    twin_one, twin_two = world.made("P", "Twin hall"), world.made("P", "Twin hall")
    solo = world.made("P", "Solo hall")
    moving = world.made("C", "Room 1", parent=twin_one["id"], values={"H.code": "R1"})
    world.made("C", "Room 2", parent=solo["id"], values={"H.code": "R2"})
    body = {
        "view": {"applicationKey": world.key("A1"), "viewKey": "x-tree", "state": {}},
        "format": "xlsx",
    }
    job, book, content = _export(world, W1, body)
    assert len(job["output"]["sheets"]) == 2
    sheets = {sheet.title: sheet for sheet in book.worksheets}
    child_sheet = next(
        sheet
        for title, sheet in sheets.items()
        if "Room 1" in str([c.value for r in sheet.iter_rows() for c in r])
    )
    header = [cell.value for cell in child_sheet[1]]
    assert any(
        str(label).startswith("Parent") and "(not imported)" in str(label) for label in header
    )
    assert any(str(label).startswith("Parent ID") for label in header)
    preview = _import(world, W1, content)
    assert preview["state"] == "awaiting_confirmation", preview["error"]
    assert {(i["status"], i.get("action")) for i in _outcomes(world, preview)} == {
        ("applied", "unchanged")
    }
    parent_id = next(n for n, label in enumerate(header, 1) if str(label).startswith("Parent ID"))
    for row in range(2, child_sheet.max_row + 1):
        if child_sheet.cell(row, 1).value == "Room 1":
            child_sheet.cell(row, parent_id).value = twin_two["id"]
    preview = _import(world, W1, _saved(book))
    rejected = [i for i in _outcomes(world, preview) if i["status"] == "rejected"]
    assert not rejected, rejected
    ok(world.api.post(f"/jobs/{preview['id']}/confirm", {}), 202)
    world.api.client.app.state.job_worker.run_until_idle()
    assert world.record("C", moving["id"], workspaceKey=W1)["parentObjectId"] == twin_two["id"]


# --- where a new cell goes, and which field the cells list (0.17 PP-D24 to PP-D26) -----------------

PLACES = ("A1", "H", "H.code", "P", "C", "C2")


def _place_views(world, **criteria):
    """Link-and-create matrices of H rows, P columns and C2 cells, which stand under a C, one per
    named set of candidate criteria on the cell's ancestor C (``(operator, value)`` pairs on its
    name), installed and activated. Returns each view's key and relationship key by name."""
    import copy

    model = copy.deepcopy(world.configuration.model)
    model["release"]["version"] = f"{model['release']['version']}-places"
    lens = next(a for a in model["applications"] if a["key"] == world.app("C2"))
    found = {}
    for name, rules in criteria.items():
        relation = {
            "key": f"x-take-{name}",
            "reverseKey": f"x-take-{name}--rev",
            "name": f"Takes {name}",
            "reverseName": f"Taken by {name}",
        }
        model["relationTypes"].append(relation)
        model["objectTypeRelations"].append(
            {
                "relationTypeKey": relation["key"],
                "fromObjectTypeKey": world.key("H"),
                "toObjectTypeKey": world.key("C2"),
                "cardinality": "many-to-many",
                "candidates": {
                    "to": [
                        {"field": f"ancestor:{world.key('C')}.name", "op": op, "value": value}
                        for op, value in rules
                    ]
                },
            }
        )
        view = {
            "key": f"x-take-{name}-by-p",
            "name": f"Take {name}",
            "type": "relationMatrix",
            "config": {
                "relationTypeKey": relation["key"],
                "direction": "outgoing",
                "rowObjectTypeKey": world.key("H"),
                "columnObjectTypeKey": world.key("P"),
                "cellObjectTypeKey": world.key("C2"),
                "rowColumns": ["name", world.key("H.code")],
                "columnLabelField": "name",
                "cellFields": [world.key("H.code")],
                "searchFields": ["name"],
                "cellActions": ["create", "link", "unlink"],
                "pageSize": 20,
            },
        }
        lens["views"].append(view)
        found[name] = (view["key"], relation["key"])
    ok(world.activate(world.install(model)["id"]))
    return found


def _containers(world, view, column):
    return ok(
        world.api.get(
            f"/workspaces/{W1}/relation-matrix/containers",
            applicationKey=world.app("C2"),
            viewKey=view,
            columnId=column["id"],
        )
    )


def _linked(world, row_id, relation):
    page = ok(
        world.api.get(
            "/relations",
            objectId=row_id,
            relationTypeKey=relation,
            workspaceKey=W1,
            pageSize=100,
        )
    )
    return {item["object"]["id"]: item["object"]["name"] for item in page["items"]}


@pytest.mark.journey("J27.26")
@pytest.mark.structures(*PLACES)
def test_a_new_cell_goes_where_the_candidate_rules_allow_and_the_missing_place_is_created(world):
    """Given a matrix whose relationship takes only cell records under a C named "Booked group", and
    three columns: one with that C, one with another C, one with none. When the containers of each
    column are read. Then only the matching C is offered, the others are filtered out, and where none
    matches the place is derived (the C with that name) to be created. When the cell is created in
    the column without one, as the dialog does, in one atomic batch. Then the C and the record exist
    under the column, the record is linked and the containers read offers the C. A relationship whose
    criteria do not fix one place derives none, and creates nothing."""
    views = _place_views(
        world,
        exact=[("eq", "Booked group")],
        broad=[("contains", "group")],
    )
    exact, relation = views["exact"]
    broad, _ = views["broad"]
    with_group, with_other, bare = (world.made("P", f"System {n}") for n in "ABC")
    matching = world.made("C", "Booked group", parent=with_group["id"])
    other = world.made("C", "Other group", parent=with_other["id"])
    ids = lambda page: [item["id"] for item in page["items"]]
    page = _containers(world, exact, with_group)
    assert ids(page) == [matching["id"]] and page["defaultContainerId"] == matching["id"]
    assert page["derivedPlace"] == {
        "objectTypeKey": world.key("C"),
        "name": "Booked group",
        "attributes": {},
        "willBeCreated": False,
        "proposed": False,
        "applicationKey": world.app("C"),
    }
    for column in (with_other, bare):
        page = _containers(world, exact, column)
        assert ids(page) == [] and page["defaultContainerId"] is None
        assert page["derivedPlace"]["willBeCreated"] is True
        assert page["derivedPlace"]["name"] == "Booked group"
    # Criteria that do not fix one place name none; the containers that meet them are offered.
    assert ids(_containers(world, broad, with_other)) == [other["id"]]
    for column in (with_group, with_other, bare):
        assert _containers(world, broad, column)["derivedPlace"] is None
    assert ids(_containers(world, broad, bare)) == [] and (
        _containers(world, broad, bare)["defaultContainerId"] is None
    )
    # The dialog's Create in the column without the place: the place, then the record, in one batch.
    row = world.made("H", "Row one", values={"H.code": "R1"})
    place_id, cell_id = str(uuid4()), str(uuid4())
    answer = ok(
        world.api.post(
            "/batches",
            {
                "workspaceKey": W1,
                "policy": "atomic",
                "run": "inline",
                "items": [
                    {
                        "op": "create",
                        "id": place_id,
                        "applicationKey": world.app("C"),
                        "objectTypeKey": world.key("C"),
                        "name": "Booked group",
                        "parent": {"id": bare["id"]},
                        "attributes": [],
                    },
                    {
                        "op": "create",
                        "id": cell_id,
                        "applicationKey": world.app("C2"),
                        "objectTypeKey": world.key("C2"),
                        "name": "Booked",
                        "parent": {"id": place_id},
                        "attributes": [{"attributeTypeKey": world.key("H.code"), "value": "BKD"}],
                        "initialRelations": [
                            {
                                "relationTypeKey": relation,
                                "direction": "incoming",
                                "object": {"id": row["id"]},
                            }
                        ],
                    },
                ],
            },
        ),
        200,
    )
    assert answer["job"]["result"] == "applied", answer
    page = _containers(world, exact, bare)
    assert ids(page) == [place_id] and page["derivedPlace"]["willBeCreated"] is False
    assert world.record("C2", cell_id, workspaceKey=W1)["parentObjectId"] == place_id
    assert _linked(world, row["id"], relation) == {cell_id: "Booked"}


def _reading_at(job, column_text):
    """The source number and column name of the column whose name holds ``column_text``."""
    for number, source in enumerate(job["bindingReport"]):
        for column in source["columns"]:
            if column_text in column["column"] and column.get("reading"):
                return number, column["column"]
    raise AssertionError((column_text, job["bindingReport"]))


def _reading(job, column_text):
    """The preview's reading of the column whose name holds ``column_text``."""
    for source in job["bindingReport"]:
        for column in source["columns"]:
            if column_text in column["column"] and column.get("reading"):
                return column["reading"]
    raise AssertionError((column_text, job["bindingReport"]))


def _link_cell(sheet, group):
    """The column of the linked-records cell of the column record named ``group``."""
    return next(
        n
        for n, cell in enumerate(sheet[2], 1)
        if cell.value and group in str(cell.value) and "linked" in str(cell.value)
    )


@pytest.mark.journey("J27.26")
@pytest.mark.structures(*PLACES)
def test_an_import_creates_the_missing_place_with_the_new_record_and_says_so_before_writing(world):
    """Given a matrix whose relationship takes only cell records under a C named "Booked group",
    and two columns, one with that C holding a record, one without. When the matrix is exported by
    names, a cell of each column names a new record, and the file is imported as a preview. Then the
    preview reads each column by the name, says the first column's new records go into the existing C
    and the second's into a C that will be created, and writes nothing. When it is confirmed, the C
    is created under the second column with the new record in it, both records are linked, and the
    first column's record stands in its existing C."""
    exact, relation = _place_views(world, exact=[("eq", "Booked group")])["exact"]
    with_group, bare = world.made("P", "System A"), world.made("P", "System B")
    place = world.made("C", "Booked group", parent=with_group["id"])
    held = world.made("C2", "Booked", parent=place["id"], values={"H.code": "BKD"})
    row_a = world.made("H", "Row a", values={"H.code": "A"})
    row_b = world.made("H", "Row b", values={"H.code": "B"})
    ok(
        world.api.post(
            "/relations",
            {
                "relationTypeKey": relation,
                "fromObjectId": row_a["id"],
                "toObjectId": held["id"],
                "attributes": {},
            },
        ),
        201,
    )
    body = {
        "view": {
            "applicationKey": world.app("C2"),
            "viewKey": exact,
            "state": {"columnIds": [with_group["id"], bare["id"]]},
            "cellField": "name",
        },
        "format": "xlsx",
    }
    _, book, _ = _export(world, W1, body)
    sheet = book.worksheets[0]
    rows = {sheet.cell(n, 1).value: n for n in range(3, sheet.max_row + 1)}
    sheet.cell(rows["Row a"], _link_cell(sheet, "System A")).value = "Booked; Fresh"
    sheet.cell(rows["Row b"], _link_cell(sheet, "System B")).value = "Pending"
    preview = _import(world, W1, _saved(book))
    assert preview["state"] == "awaiting_confirmation", preview["error"]
    first, second = _reading(preview, "System A"), _reading(preview, "System B")
    assert first["field"] == "name" and first["recorded"] and not first["guessed"]
    assert first["newRecords"] == {
        "objectTypeKey": world.key("C"),
        "name": "Booked group",
        "willBeCreated": False,
        "reason": None,
        "message": None,
    }
    assert second["newRecords"]["willBeCreated"] is True
    assert second["newRecords"]["name"] == "Booked group"
    assert [i for i in _outcomes(world, preview) if i["status"] == "rejected"] == []
    assert _containers(world, exact, bare)["items"] == []  # nothing written by the preview
    ok(world.api.post(f"/jobs/{preview['id']}/confirm", {}), 202)
    world.api.client.app.state.job_worker.run_until_idle()
    made = _containers(world, exact, bare)
    assert [item["name"] for item in made["items"]] == ["Booked group"]
    new_place = made["items"][0]["id"]
    in_a, in_b = _linked(world, row_a["id"], relation), _linked(world, row_b["id"], relation)
    assert sorted(in_a.values()) == ["Booked", "Fresh"] and list(in_b.values()) == ["Pending"]
    parents = {
        name: world.record("C2", record_id, workspaceKey=W1)["parentObjectId"]
        for record_id, name in {**in_a, **in_b}.items()
    }
    assert parents == {"Booked": place["id"], "Fresh": place["id"], "Pending": new_place}


def _link(world, relation, row_id, cell_id):
    ok(
        world.api.post(
            "/relations",
            {
                "relationTypeKey": relation,
                "fromObjectId": row_id,
                "toObjectId": cell_id,
                "attributes": {},
            },
        ),
        201,
    )


def _links_export(world, view, columns, field=None, **extra):
    state = {"columnIds": [column["id"] for column in columns]}
    named = {"applicationKey": world.app("C2"), "viewKey": view, "state": state}
    if field is not None:
        named["cellField"] = field
    return {"view": named, "format": "xlsx", **extra}


@pytest.mark.journey("J27.26")
@pytest.mark.structures(*PLACES)
def test_the_cells_list_the_field_the_export_was_asked_for_and_the_import_reads_it_back(world):
    """Given a matrix whose cells link records that have a name and a code. When it is exported with
    the code as the cell field, then each cell lists codes, the About sheet says so, a field that does
    not identify the records is refused, and the file imports back unchanged. When a cell is edited to
    list another record by its code, a code no record has, and a code two records of the column hold.
    Then the other record is linked, the unknown code is a new record holding that code (its name is
    the code too, 0.17 PP-D27) and a code held twice is refused, naming the row."""
    view, relation = _place_views(world, exact=[("eq", "Booked group")])["exact"]
    column = world.made("P", "System A")
    place = world.made("C", "Booked group", parent=column["id"])
    booked = world.made("C2", "Booked", parent=place["id"], values={"H.code": "BKD"})
    confirmed = world.made("C2", "Confirmed", parent=place["id"], values={"H.code": "CNF"})
    row_a = world.made("H", "Row a", values={"H.code": "A"})
    row_b = world.made("H", "Row b", values={"H.code": "B"})
    _link(world, relation, row_a["id"], booked["id"])
    code = world.key("H.code")
    refused(
        world.api.post(
            "/exports",
            {"workspaceKey": W1, **_links_export(world, view, [column], "not-a-field")},
        ),
        422,
        "INVALID_EXPORT_LAYOUT",
    )
    _, book, content = _export(world, W1, _links_export(world, view, [column], code))
    sheet = book.worksheets[0]
    at = _link_cell(sheet, "System A")
    rows = {sheet.cell(n, 1).value: n for n in range(3, sheet.max_row + 1)}
    assert (
        sheet.cell(rows["Row a"], at).value == "BKD" and sheet.cell(rows["Row b"], at).value is None
    )
    said = " ".join(str(v).lower() for rows_ in _about(book).values() for v in rows_.values())
    assert "by its " + world.attribute_name("H.code").lower() in said
    unchanged = _import(world, W1, content)
    assert {(i["status"], i.get("action")) for i in _outcomes(world, unchanged)} <= {
        ("applied", "unchanged")
    }
    reading = _reading(unchanged, "System A")
    assert reading["field"] == code and reading["recorded"] and not reading["guessed"]
    labels = {option["field"]: option["label"] for option in reading["options"]}
    assert labels == {"name": "Name", code: world.attribute_name("H.code")}
    sheet.cell(rows["Row a"], at).value = "BKD; CNF"
    sheet.cell(rows["Row b"], at).value = "ZZZ"
    edited = _import(world, W1, _saved(book))
    outcomes = {i["ref"]: i for i in _outcomes(world, edited)}
    assert not [i for i in outcomes.values() if i["status"] == "rejected"]
    ok(world.api.post(f"/jobs/{edited['id']}/confirm", {}), 202)
    world.api.client.app.state.job_worker.run_until_idle()
    assert set(_linked(world, row_a["id"], relation)) == {booked["id"], confirmed["id"]}
    assert list(_linked(world, row_b["id"], relation).values()) == ["ZZZ"]
    # A second record of the column holding the code CNF: the value finds two records and is refused.
    other = world.made("C", "Other group", parent=column["id"])
    world.made("C2", "Confirmed too", parent=other["id"], values={"H.code": "CNF"})
    _, book, _ = _export(world, W1, _links_export(world, view, [column], code))
    sheet = book.worksheets[0]
    sheet.cell(rows["Row b"], at).value = "CNF"
    ambiguous = _import(world, W1, _saved(book))
    found = [i for i in _outcomes(world, ambiguous) if i["status"] == "rejected"]
    assert {i["error"]["code"] for i in found} == {"REFERENCE_AMBIGUOUS"}
    assert any(f"!{rows['Row b']}" in i["ref"] and "CNF" in i["error"]["message"] for i in found)
    named = [
        item["name"]
        for item in ok(world.api.get(f"/objects/{world.key('C2')}", workspaceKey=W1, pageSize=100))[
            "items"
        ]
    ]
    assert named.count("ZZZ") == 1 and "CNF" not in named


def _profile_of(book):
    """The import profile a workbook for people carries, as the engine reads it."""
    rows = list(book[PROFILE_SHEET].iter_rows(max_col=2, values_only=True))
    return json.loads("".join(str(row[0]) for row in rows[1:] if row[0] is not None))


@pytest.mark.journey("J27.26")
@pytest.mark.structures(*PLACES)
def test_a_file_that_records_no_reading_is_guessed_and_the_person_can_choose_another_field(world):
    """Given a file whose profile does not say which field its matrix cells list, and cells that
    list records by their codes. When it is previewed. Then the engine reads the column by the code,
    says it guessed, shows each field's matches, and every value finds its record. When the person
    chooses the name instead, a new preview of the same file runs with that field recorded, the first
    preview is cancelled, nothing was written by either, and the codes find no record."""
    view, relation = _place_views(world, exact=[("eq", "Booked group")])["exact"]
    column = world.made("P", "System A")
    place = world.made("C", "Booked group", parent=column["id"])
    booked = world.made("C2", "Booked", parent=place["id"], values={"H.code": "BKD"})
    world.made("C2", "Confirmed", parent=place["id"], values={"H.code": "CNF"})
    row = world.made("H", "Row a", values={"H.code": "A"})
    _link(world, relation, row["id"], booked["id"])
    _, book, _ = _export(world, W1, _links_export(world, view, [column], "name"))
    sheet = book.worksheets[0]
    rows = {sheet.cell(n, 1).value: n for n in range(3, sheet.max_row + 1)}
    sheet.cell(rows["Row a"], _link_cell(sheet, "System A")).value = "BKD; CNF"
    profile = _profile_of(book)
    for source in profile["sources"]:
        for binding in source["columns"]:
            within = binding.get("relation", {}).get("within")
            if within:
                within.pop("field", None)
                within.pop("labelAttributeTypeKey", None)
    request = {
        "workspaceKey": W1,
        "policy": "independent",
        "onExisting": "reject",
        "stage": "preview",
        "profile": profile,
    }
    job = ok(
        world.api.upload(
            "/imports",
            {"file": ("guess.xlsx", _saved(book), XLSX)},
            {"request": json.dumps(request)},
        ),
        202,
    )
    world.api.client.app.state.job_worker.run_until_idle()
    job = ok(world.api.get(f"/jobs/{job['id']}"))
    assert job["state"] == "awaiting_confirmation", job["error"]
    reading = _reading(job, "System A")
    code = world.key("H.code")
    assert reading["field"] == code and reading["guessed"] and not reading["recorded"]
    counts = {o["field"]: (o["matched"], o["cells"]) for o in reading["options"]}
    assert counts == {"name": (0, 2), code: (2, 2)}
    assert not [i for i in _outcomes(world, job) if i["status"] == "rejected"]
    again = ok(
        world.api.post(
            f"/jobs/{job['id']}/reread",
            {
                "readings": [
                    {
                        "source": _reading_at(job, "System A")[0],
                        "column": _reading_at(job, "System A")[1],
                        "field": "name",
                    }
                ]
            },
        ),
        202,
    )
    world.api.client.app.state.job_worker.run_until_idle()
    again = ok(world.api.get(f"/jobs/{again['id']}"))
    assert again["id"] != job["id"] and again["state"] == "awaiting_confirmation"
    assert ok(world.api.get(f"/jobs/{job['id']}"))["state"] == "cancelled"
    second = _reading(again, "System A")
    assert second["field"] == "name" and second["recorded"] and not second["guessed"]
    # Read by name, the codes name no record: each would be created, under the existing place.
    assert any(i.get("action") == "created" for i in _outcomes(world, again))
    assert second["newRecords"]["willBeCreated"] is False
    refused(
        world.api.post(
            f"/jobs/{again['id']}/reread",
            {
                "readings": [
                    {
                        "source": _reading_at(again, "System A")[0],
                        "column": "System A",
                        "field": "name",
                    }
                ]
            },
        ),
        422,
        "INVALID_IMPORT_READING",
    )
    assert _linked(world, row["id"], relation) == {booked["id"]: "Booked"}
    # 0.17 RF1-F2: a preview confirmed is no longer replaced. The re-read is refused, creates no
    # preview and leaves the confirmed import without a cancel request.
    ok(world.api.post(f"/jobs/{again['id']}/confirm", {}), 202)
    before = ok(world.api.get("/jobs", pageSize=100))["items"]
    refused(
        world.api.post(
            f"/jobs/{again['id']}/reread",
            {
                "readings": [
                    {
                        "source": _reading_at(again, "System A")[0],
                        "column": "System A",
                        "field": code,
                    }
                ]
            },
        ),
        409,
        "JOB_NOT_AWAITING_CONFIRMATION",
    )
    after = ok(world.api.get("/jobs", pageSize=100))["items"]
    assert len(after) == len(before)
    confirmed = ok(world.api.get(f"/jobs/{again['id']}"))
    assert confirmed["state"] in ("queued", "running", "completed")
    assert not confirmed.get("cancelRequestedAt")


@pytest.mark.journey("J27.26")
@pytest.mark.structures(*PLACES)
def test_where_the_rules_fix_no_place_new_cells_go_where_the_view_already_has_cells(world):
    """Given a matrix whose relationship sets no candidate rule, and three columns: one with two
    groups holding cells (two and one), one with a single group holding none, one with two groups
    holding one each (one named like a group of the first column). When the containers are read.
    Then the column's busiest group is the default; the column whose only group holds no cells and the
    tie have none, and each is given a proposed group (0.17 PP-D28) of the type the other columns
    use, named as most of their groups are (a tie going to the first name), the proposal for the tie
    leaving out its own groups. When a new name is entered in each column of an exported file and
    previewed. Then the busiest group takes its record, the other two columns' proposed groups are
    shown as to be created under their columns, and confirming creates each group and its record."""
    view, relation = _place_views(world, plain=[])["plain"]
    busy, empty, tied = (world.made("P", f"System {n}") for n in "ABC")
    big = world.made("C", "Big group", parent=busy["id"])
    small = world.made("C", "Small group", parent=busy["id"])
    unused = world.made("C", "Station", parent=empty["id"])
    left = world.made("C", "Small group", parent=tied["id"])
    right = world.made("C", "Right", parent=tied["id"])
    held = world.made("H", "Row held", values={"H.code": "HELD"})
    for group, names in ((big, "12"), (small, "3"), (left, "4"), (right, "5")):
        for number in names:
            cell = world.made("C2", f"Cell {number}", parent=group["id"], values={"H.code": number})
            _link(world, relation, held["id"], cell["id"])
    # A cell nothing is linked to is no cell of the view: its group holds none.
    world.made("C2", "Orphan", parent=unused["id"], values={"H.code": "9"})
    row_a = world.made("H", "Row a", values={"H.code": "A"})
    row_b = world.made("H", "Row b", values={"H.code": "B"})
    row_c = world.made("H", "Row c", values={"H.code": "C"})
    page = _containers(world, view, busy)
    assert page["defaultContainerId"] == big["id"] and page["derivedPlace"] is None
    assert [(i["name"], i["cellCount"]) for i in page["items"]] == [
        ("Big group", 2),
        ("Small group", 1),
    ]
    page = _containers(world, view, empty)
    assert page["defaultContainerId"] is None
    assert [(i["id"], i["cellCount"]) for i in page["items"]] == [(unused["id"], 0)]
    assert page["derivedPlace"] == {
        "objectTypeKey": world.key("C"),
        "name": "Small group",
        "attributes": {},
        "willBeCreated": True,
        "proposed": True,
        "applicationKey": world.app("C"),
    }
    page = _containers(world, view, tied)
    assert page["defaultContainerId"] is None
    assert page["derivedPlace"]["name"] == "Big group" and page["derivedPlace"]["proposed"]
    _, book, _ = _export(world, W1, _links_export(world, view, [busy, empty, tied], "name"))
    sheet = book.worksheets[0]
    rows = {sheet.cell(n, 1).value: n for n in range(3, sheet.max_row + 1)}
    for row, group, text in (
        (row_a, "System A", "New a"),
        (row_b, "System B", "New b"),
        (row_c, "System C", "New c"),
    ):
        sheet.cell(rows[row["name"]], _link_cell(sheet, group)).value = text
    preview = _import(world, W1, _saved(book))
    assert not [i for i in _outcomes(world, preview) if i["status"] == "rejected"]
    chosen = _reading(preview, "System A")["newRecords"]
    assert chosen["name"] == "Big group" and chosen["willBeCreated"] is False
    proposed = _reading(preview, "System B")["newRecords"]
    assert proposed["name"] == "Small group" and proposed["willBeCreated"] is True
    assert _reading(preview, "System C")["newRecords"]["name"] == "Big group"
    assert [i["id"] for i in _containers(world, view, empty)["items"]] == [unused["id"]]
    ok(world.api.post(f"/jobs/{preview['id']}/confirm", {}), 202)
    world.api.client.app.state.job_worker.run_until_idle()
    (made,) = _linked(world, row_a["id"], relation).keys()
    assert world.record("C2", made, workspaceKey=W1)["parentObjectId"] == big["id"]
    for row, column, group_name in ((row_b, empty, "Small group"), (row_c, tied, "Big group")):
        (made,) = _linked(world, row["id"], relation).keys()
        parent = world.record(
            "C", world.record("C2", made, workspaceKey=W1)["parentObjectId"], workspaceKey=W1
        )
        assert parent["name"] == group_name and parent["parentObjectId"] == column["id"]


# --- a value sheet per column (0.17 PP-D27) ---------------------------------------------------------


def _value_sheet(book, group):
    """A column's value sheet, its header and the column of each label."""
    sheet = book[f"Values · {group}"]
    header = [cell.value for cell in sheet[1]]
    return sheet, {str(label): number for number, label in enumerate(header, 1)}


def _value_rows(sheet, at):
    return {
        sheet.cell(n, at["Name"]).value: n
        for n in range(2, sheet.max_row + 1)
        if sheet.cell(n, at["Name"]).value
    }


def _names_of(world, type_key, **query):
    page = ok(world.api.get(f"/objects/{world.key(type_key)}", workspaceKey=W1, pageSize=100))
    return {item["name"]: item for item in page["items"]}


@pytest.mark.journey("J27.27")
@pytest.mark.structures(*PLACES)
def test_a_value_sheet_lists_each_columns_records_and_its_edits_reach_the_records(world):
    """Given a link-and-create matrix and a column holding two records in the place the rules give.
    When it is exported. Then the column has a value sheet, an Excel table of its records as full
    rows (name, code, group, hidden ID and version), the main sheet's cells list the records by the
    name and their dropdown reads the sheet's column by a defined name, and the file imports back
    unchanged. When a value-sheet row is renamed (the main cell still lists its old value), a row is added there
    and a main cell picks it (one record), a name is typed only in a main cell, a name is typed in
    both places, and a value-sheet row is picked nowhere. Then the renamed record is the same record,
    the added row is one record in the column's place and linked, the name found in neither place is
    a new record, the name typed twice is one, and the unpicked row is still created."""
    view, relation = _place_views(world, exact=[("eq", "Booked group")])["exact"]
    column = world.made("P", "System A")
    place = world.made("C", "Booked group", parent=column["id"])
    booked = world.made("C2", "Booked", parent=place["id"], values={"H.code": "BKD"})
    world.made("C2", "Confirmed", parent=place["id"], values={"H.code": "CNF"})
    row_a = world.made("H", "Row a", values={"H.code": "A"})
    row_b = world.made("H", "Row b", values={"H.code": "B"})
    row_c = world.made("H", "Row c", values={"H.code": "C"})
    _link(world, relation, row_a["id"], booked["id"])
    _, book, content = _export(world, W1, _links_export(world, view, [column], "name"))
    assert "Values · System A" in book.sheetnames
    sheet, at = _value_sheet(book, "System A")
    assert set(_value_rows(sheet, at)) == {"Booked", "Confirmed"}
    code = world.attribute_name("H.code")
    assert code in at and any("Group" in label for label in at)
    hidden = [letter for letter, dimension in sheet.column_dimensions.items() if dimension.hidden]
    assert len(hidden) == 2
    assert len(sheet.tables) == 1
    names = {name: item.attr_text for name, item in book.defined_names.items()}
    assert any(text.endswith("[Name]") for text in names.values())
    main = book.worksheets[0]
    soft = [v for v in main.data_validations.dataValidation if v.errorStyle == "warning"]
    assert soft and soft[0].formula1 in names
    unchanged = _import(world, W1, content)
    assert unchanged["state"] == "awaiting_confirmation", unchanged["error"]
    assert {(i["status"], i.get("action")) for i in _outcomes(world, unchanged)} <= {
        ("applied", "unchanged")
    }
    first = _reading(unchanged, "Name")
    assert first["valueSheet"] and first["updatedRows"] == 2 and first["newRows"] == 0
    # The edits.
    rows = {main.cell(n, 1).value: n for n in range(3, main.max_row + 1)}
    cell = _link_cell(main, "System A")
    sheet.cell(_value_rows(sheet, at)["Booked"], at["Name"]).value = "Booked, renamed"
    sheet.cell(_value_rows(sheet, at)["Confirmed"], at[code]).value = "CNF-2"
    for number, (name, value) in enumerate(
        [("Tentative", "TNT"), ("Spare", "SPR"), ("Typed twice", "TWC")], 10
    ):
        sheet.cell(number, at["Name"]).value = name
        sheet.cell(number, at[code]).value = value
    # Row a's cell still lists the record by its old value: it is found, not created again.
    main.cell(rows["Row b"], cell).value = "Tentative; Operator new; Typed twice"
    main.cell(rows["Row c"], cell).value = "Typed twice"
    preview = _import(world, W1, _saved(book))
    assert preview["state"] == "awaiting_confirmation", preview["error"]
    assert not [i for i in _outcomes(world, preview) if i["status"] == "rejected"]
    first = _reading(preview, "Name")
    assert first["updatedRows"] == 2 and first["newRows"] == 3
    linked = _reading(preview, "System A")
    assert linked["fromValueSheet"] == 3 and linked["createdValues"] == 1
    assert _names_of(world, "C2").keys() == {"Booked", "Confirmed"}
    ok(world.api.post(f"/jobs/{preview['id']}/confirm", {}), 202)
    world.api.client.app.state.job_worker.run_until_idle()
    records = _names_of(world, "C2")
    assert set(records) == {
        "Booked, renamed",
        "Confirmed",
        "Tentative",
        "Spare",
        "Typed twice",
        "Operator new",
    }
    assert records["Booked, renamed"]["id"] == booked["id"]
    assert all(
        records[name]["parentObjectId"] == place["id"]
        for name in ("Tentative", "Spare", "Typed twice", "Operator new")
    )
    assert set(_linked(world, row_a["id"], relation).values()) == {"Booked, renamed"}
    assert set(_linked(world, row_b["id"], relation).values()) == {
        "Tentative",
        "Operator new",
        "Typed twice",
    }
    assert set(_linked(world, row_c["id"], relation).values()) == {"Typed twice"}
    held = {item["attributeTypeKey"]: item["value"] for item in records["Operator new"]["attributes"]}
    assert world.key("H.code") not in held
    held = {item["attributeTypeKey"]: item["value"] for item in records["Tentative"]["attributes"]}
    assert held[world.key("H.code")] == "TNT"


@pytest.mark.journey("J27.28")
@pytest.mark.structures(*PLACES)
def test_a_proposed_container_is_created_with_the_record_by_the_dialogs_batch(world):
    """Given a matrix whose relationship sets no candidate rule, a column whose group holds cells of
    the view, a column with no group. When the containers
    of the empty column are read. Then a group named as the used one is proposed under it, of its
    type, marked as proposed and to be created; When the
    dialog creates the cell with the proposal's name edited, in one atomic batch of the group and the
    record (the same request as a derived place). Then the group has the edited name and stands under
    the column, the record stands in it and is linked, and the containers read now offers the group."""
    view, relation = _place_views(world, plain=[])["plain"]
    used, bare = world.made("P", "System A"), world.made("P", "System B")
    group = world.made("C", "Shared group", parent=used["id"])
    held = world.made("H", "Row held", values={"H.code": "HELD"})
    cell = world.made("C2", "Cell 1", parent=group["id"], values={"H.code": "1"})
    row = world.made("H", "Row new", values={"H.code": "NEW"})
    _link(world, relation, held["id"], cell["id"])
    page = _containers(world, view, bare)
    assert page["items"] == [] and page["defaultContainerId"] is None
    assert page["derivedPlace"] == {
        "objectTypeKey": world.key("C"),
        "name": "Shared group",
        "attributes": {},
        "willBeCreated": True,
        "proposed": True,
        "applicationKey": world.app("C"),
    }
    place_id, cell_id = str(uuid4()), str(uuid4())
    answer = ok(
        world.api.post(
            "/batches",
            {
                "workspaceKey": W1,
                "policy": "atomic",
                "run": "inline",
                "items": [
                    {
                        "op": "create",
                        "id": place_id,
                        "applicationKey": world.app("C"),
                        "objectTypeKey": world.key("C"),
                        "name": "Edited group",
                        "parent": {"id": bare["id"]},
                        "attributes": [],
                    },
                    {
                        "op": "create",
                        "id": cell_id,
                        "applicationKey": world.app("C2"),
                        "objectTypeKey": world.key("C2"),
                        "name": "Cell 2",
                        "parent": {"id": place_id},
                        "attributes": [{"attributeTypeKey": world.key("H.code"), "value": "2"}],
                        "initialRelations": [
                            {
                                "relationTypeKey": relation,
                                "direction": "incoming",
                                "object": {"id": row["id"]},
                            }
                        ],
                    },
                ],
            },
        ),
        200,
    )
    assert answer["job"]["result"] == "applied", answer
    page = _containers(world, view, bare)
    assert [(i["id"], i["name"], i["cellCount"]) for i in page["items"]] == [
        (place_id, "Edited group", 1)
    ]
    assert page["defaultContainerId"] == place_id and page["derivedPlace"] is None
    assert _linked(world, row["id"], relation) == {cell_id: "Cell 2"}
