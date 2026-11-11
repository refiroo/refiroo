"""J27 — Exchange a supplier file: workbooks people fill in (USER_JOURNEYS.md, 0.9 J6a).

An owned relationship laid out as columns per parent (a new parent's column filled to create its
records), dropdowns over reference sheets of the records a relationship may choose, and borders.
Each test writes in a workspace of its own and runs the engine's workers itself; the workbook is
read and edited with openpyxl, as a person's spreadsheet program would.
"""

import io
import json
from uuid import uuid4

import pytest
from openpyxl import load_workbook
from openpyxl.utils import column_index_from_string, range_boundaries
from scenario import ok, refused

XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
PROFILE_SHEET = "Import profile"


def _workspace(world):
    key = f"columns-{uuid4().hex[:8]}"
    ok(world.api.post("/workspaces", {"key": key, "label": "Columns site"}), 201)
    return key


def _people(world, ws, structure, people):
    return world.api.post(
        "/exports",
        {
            "workspaceKey": ws,
            "scope": {"types": [{"objectTypeKey": world.key(structure)}]},
            "format": "xlsx",
            "layout": "people",
            "people": people,
        },
    )


def _workbook(world, ws, structure, people):
    job = ok(_people(world, ws, structure, people), 202)
    world.api.client.app.state.export_worker.run_until_idle()
    job = ok(world.api.get(f"/jobs/{job['id']}"))
    assert job["state"] == "completed", job["error"]
    response = world.api.get(f"/jobs/{job['id']}/output")
    assert response.status_code == 200, response.text
    return job, load_workbook(io.BytesIO(response.content))


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


def _labels(sheet, hidden=False):
    return [
        cell.value
        for cell in sheet[1]
        if cell.value is not None
        and bool(sheet.column_dimensions[cell.column_letter].hidden) == hidden
    ]


def _letter(sheet, label):
    return next(cell.column_letter for cell in sheet[1] if cell.value == label)


def _rows(sheet):
    header = [cell.value for cell in sheet[1]]
    return [
        dict(zip(header, (cell.value for cell in row), strict=False))
        for row in sheet.iter_rows(min_row=2)
        if any(cell.value is not None for cell in row)
    ]


def _profile(book):
    sheet = book[PROFILE_SHEET]
    return json.loads("".join(row[0].value for row in sheet.iter_rows(min_row=2) if row[0].value))


def _choices(book, sheet, label):
    """The values the list rule of ``label``'s column offers, read from the sheet it names."""
    letter = _letter(sheet, label)
    column = column_index_from_string(letter)
    for rule in sheet.data_validations.dataValidation:
        covered = any(
            range_boundaries(str(area))[0] <= column <= range_boundaries(str(area))[2]
            for area in rule.sqref.ranges
        )
        if covered and rule.type == "list":
            source = rule.formula1
            if source.startswith('"'):
                continue  # an inline list (Yes, No), not a reference sheet
            title, _, area = source.rpartition("!")
            target = book[title.strip("'").replace("''", "'")]
            first, top, _, bottom = range_boundaries(area.replace("$", ""))
            return {target.cell(row=row, column=first).value for row in range(top, bottom + 1)} - {
                None
            }
    return None


def _scene(world, ws, ledgers=2):
    """Three regions with a place for D each (the region itself, or a container under it); the
    first ``ledgers`` R records each own an active D under the place of the region of their number."""
    regions = [world.made("G", f"Region {n}", workspace=ws) for n in (1, 2, 3)]
    places = [world.dependant_parent(region["id"], ws) for region in regions]
    holder = "M" if "deep-scope" in world.configuration.shapes else "G"
    names = [world.record(holder, place, workspaceKey=ws)["name"] for place in places]
    owners, permits = [], []
    for n in range(1, ledgers + 1):
        owner = world.made("R", f"Ledger {n}", workspace=ws, values={"R.u": f"L-{n}"})
        permit = world.made(
            "D",
            f"Permit {n}",
            parent=places[(n - 1) % 2],
            workspace=ws,
            values={"K.code": f"P{n}"},
            relations=[world.owner("Bown", owner["id"])],
        )
        owners.append(owner)
        permits.append(permit)
    return regions, places, names, owners, permits


def _columns(world, places):
    return {
        "columns": ["name", world.key("R.u")],
        "sheets": [world.key("Bown")],
        "ownedColumns": {
            world.key("Bown"): {"parents": [places[2]], "fields": ["name", world.key("K.code")]}
        },
    }


R_STRUCTURES = ("R", "R.u", "D", "D.active", "G", "M", "K.code", "Bown")


@pytest.mark.journey("J27.18")
@pytest.mark.structures(*R_STRUCTURES)
def test_an_owned_relationship_is_written_as_columns_per_parent(world):
    """Given two R records each owning a D under its own parent, and a third parent holding none.
    When R is exported for people with Bown as columns per parent, the third parent added, and the
    fields name and K.code. Then the sheet holds one row per R and a column per parent and field,
    each header naming its field and parent and, where the parent stands below the scope D is
    unique in, that G; a filled cell holds its D's value; a hidden version per parent; the profile
    is valid."""
    ws = _workspace(world)
    regions, places, names, owners, permits = _scene(world, ws)
    job, book = _workbook(world, ws, "R", _columns(world, places))
    owned = book.worksheets[2]
    assert job["output"]["sheets"][1] == owned.title
    labels = _labels(owned)
    deep = "deep-scope" in world.configuration.shapes
    for place_name, region in zip(names, regions, strict=True):
        for field in ("Name", "K.code"):
            matching = [label for label in labels if field in label and place_name in label]
            assert len(matching) == 1, (field, place_name, labels)
            if deep:
                assert region["name"] in matching[0], matching[0]
            else:
                assert matching[0] == f"{field} · {place_name}", matching[0]
    rows = {row[labels[0]]: row for row in _rows(owned)}
    assert set(rows) == {owner["name"] for owner in owners}
    first = rows["Ledger 1"]
    name_first = next(label for label in labels if "Name" in label and names[0] in label)
    code_first = next(label for label in labels if "K.code" in label and names[0] in label)
    code_third = next(label for label in labels if "K.code" in label and names[2] in label)
    assert first[name_first] == "Permit 1" and first[code_first] == "P1"
    assert first[code_third] is None and rows["Ledger 2"][code_first] is None
    hidden = _labels(owned, hidden=True)
    version = next(label for label in hidden if names[0] in label)
    record = world.record("D", permits[0]["id"], workspaceKey=ws)
    assert first[version] == record["version"]
    stored = {"key": f"columns-{uuid4().hex[:8]}", "name": "Columns", **_profile(book)}
    ok(world.api.post("/import-profiles", stored), 201)


@pytest.mark.journey("J27.19", "J27.9")
@pytest.mark.structures(*R_STRUCTURES)
def test_a_new_parents_column_filled_creates_its_records_and_edits_update_theirs(world):
    """Given three R records owning a D each, and a parent holding none. When R is exported with Bown
    as columns per parent and imported untouched. Then every item is unchanged. When the new
    parent's column is filled for two Rs, one existing cell edited, one cleared, and a D changed in
    the app since the export is edited in the file. Then two Ds are created under the new parent,
    each owned by its row's R; the edited D is updated; the cleared value stays; the changed D is
    refused VERSION_CONFLICT."""
    ws = _workspace(world)
    _, places, names, owners, permits = _scene(world, ws, ledgers=3)
    _, book = _workbook(world, ws, "R", _columns(world, places))

    untouched = _import(world, ws, _saved(book), stage="preview")
    assert untouched["state"] == "awaiting_confirmation", untouched["error"]
    counts = untouched["preview"]["counts"]
    assert counts["created"] == counts["updated"] == counts["rejected"] == 0
    assert {(i["status"], i.get("action")) for i in _outcomes(world, untouched)} == {
        ("applied", "unchanged")
    }

    third = world.record("D", permits[2]["id"], workspaceKey=ws)
    ok(world.update("D", permits[2]["id"], third["version"], name="Permit 3 meanwhile"))
    owned = book.worksheets[2]
    labels = _labels(owned)

    def label(field, place):
        return next(item for item in labels if field in item and names[place] in item)

    owner = _letter(owned, labels[0])
    for row in range(2, owned.max_row + 1):

        def cell(text, row=row):
            return owned[f"{_letter(owned, text)}{row}"]

        who = owned[f"{owner}{row}"].value
        if who in ("Ledger 1", "Ledger 2"):
            cell(label("Name", 2)).value = f"New permit {who[-1]}"
            cell(label("K.code", 2)).value = f"N{who[-1]}"
        if who == "Ledger 1":
            cell(label("K.code", 0)).value = "P1X"
        if who == "Ledger 2":
            cell(label("K.code", 1)).value = None
        if who == "Ledger 3":
            cell(label("K.code", 0)).value = "P3X"

    job = _import(world, ws, _saved(book))
    assert job["state"] == "completed", job["error"]
    refusals = {
        item["error"]["code"] for item in _outcomes(world, job) if item["status"] == "rejected"
    }
    assert refusals == {"VERSION_CONFLICT"}
    under_new = ok(
        world.api.get(
            f"/objects/{world.key('D')}", workspaceKey=ws, parentObjectId=places[2], pageSize=10
        )
    )["items"]
    assert {item["name"] for item in under_new} == {"New permit 1", "New permit 2"}
    for item in under_new:
        expected = owners[int(item["name"][-1]) - 1]["id"]
        related = ok(
            world.api.get(
                "/relations",
                objectId=item["id"],
                relationTypeKey=world.key("Bown"),
                workspaceKey=ws,
            )
        )["items"]
        assert [entry["object"]["id"] for entry in related] == [expected]
        assert world.value(world.record("D", item["id"], workspaceKey=ws), "K.code") == (
            f"N{item['name'][-1]}"
        )
    assert world.value(world.record("D", permits[0]["id"], workspaceKey=ws), "K.code") == "P1X"
    assert world.value(world.record("D", permits[1]["id"], workspaceKey=ws), "K.code") == "P2"
    assert world.value(world.record("D", permits[2]["id"], workspaceKey=ws), "K.code") == "P3"


@pytest.mark.journey("J27.20")
@pytest.mark.structures(
    "H", "K", "K.code", "Bn1", "Bcand", "R", "R.u", "D", "D.active", "G", "M", "Bown"
)
def test_pointer_cells_choose_from_reference_sheets_and_cells_have_borders(world):
    """Given K records, one whose code makes it a Bcand candidate, and an H related to it. When H is
    exported for people with Bn1 as a column and a sheet for Bcand. Then Bn1's cells offer every K,
    and the Bcand sheet's related record cells only the candidate, each from a reference sheet; every
    written cell has a border. When R is exported with Bown's rows, the parent and owner cells offer
    the parents and the Rs. A Bn1 cell holding a name outside its list is refused by row."""
    ws = _workspace(world)
    chosen = world.made("K", "Alpha token", workspace=ws, values={"K.code": "OK-1"})
    world.made("K", "Beta token", workspace=ws, values={"K.code": "NO-1"})
    branch = world.made("H", "First branch", workspace=ws)
    ok(world.relate("Bn1", branch["id"], chosen["id"]), 201)
    ok(world.relate("Bcand", branch["id"], chosen["id"]), 201)
    people = {
        "columns": ["name", f"related:{world.key('Bn1')}"],
        "sheets": [world.key("Bcand")],
    }
    job, book = _workbook(world, ws, "H", people)
    main, sheet = book.worksheets[0], book.worksheets[2]
    bn1 = _labels(main)[1]
    assert _choices(book, main, bn1) == {"Alpha token", "Beta token"}
    related = _labels(sheet)[1]
    assert _choices(book, sheet, related) == {"Alpha token"}
    assert len(job["output"]["sheets"]) == 4
    for cell in (main["A1"], main["A2"], main[f"{_letter(main, bn1)}2"], sheet["B2"]):
        assert cell.border.left.style == "thin" and cell.border.bottom.style == "thin"

    _, _, names, owners, _ = _scene(world, ws)
    _, ledgers = _workbook(
        world, ws, "R", {"columns": ["name", world.key("R.u")], "sheets": [world.key("Bown")]}
    )
    rows = ledgers.worksheets[2]
    offered = {label: _choices(ledgers, rows, label) or set() for label in _labels(rows)}
    parent = next(label for label, choices in offered.items() if names[0] in choices)
    assert set(names) <= offered[parent]
    owner_label = next(
        label for label, choices in offered.items() if choices >= {o["name"] for o in owners}
    )
    assert owner_label != parent

    for row in range(2, main.max_row + 1):
        if main[f"A{row}"].value == "First branch":
            main[f"{_letter(main, bn1)}{row}"].value = "Nobody token"
    refusal = _import(world, ws, _saved(book))
    codes = {
        item["error"]["code"] for item in _outcomes(world, refusal) if item["status"] == "rejected"
    }
    assert codes == {"REFERENCE_NOT_FOUND"}


@pytest.mark.journey("J27.21", "J27.5")
@pytest.mark.structures("H", "K", "Bnn", *R_STRUCTURES)
def test_columns_per_parent_and_lists_are_refused_for_what_they_cannot_hold(world):
    """Given a workspace with a K and an H. When columns per parent are asked for a relationship that
    owns nothing or has no sheet, with a parent D cannot stand under or not in the workspace, or a
    field D lacks, or a list for a relationship the workbook does not name. Then each is refused
    INVALID_EXPORT_LAYOUT at its pointer."""
    ws = _workspace(world)
    token = world.made("K", "Token", workspace=ws)
    bnn, bown = world.key("Bnn"), world.key("Bown")
    not_owned = _people(
        world,
        ws,
        "H",
        {"columns": ["name"], "sheets": [bnn], "ownedColumns": {bnn: {"fields": ["name"]}}},
    )
    path = refused(not_owned, 422, "INVALID_EXPORT_LAYOUT")["details"]["path"]
    assert path == f"/people/ownedColumns/{bnn}"
    no_sheet = _people(
        world, ws, "R", {"columns": ["name"], "ownedColumns": {bown: {"fields": ["name"]}}}
    )
    path = refused(no_sheet, 422, "INVALID_EXPORT_LAYOUT")["details"]["path"]
    assert path == f"/people/ownedColumns/{bown}"
    for parent in (token["id"], str(uuid4())):
        wrong = _people(
            world,
            ws,
            "R",
            {
                "columns": ["name"],
                "sheets": [bown],
                "ownedColumns": {bown: {"parents": [parent], "fields": ["name"]}},
            },
        )
        path = refused(wrong, 422, "INVALID_EXPORT_LAYOUT")["details"]["path"]
        assert path == f"/people/ownedColumns/{bown}/parents/0"
    lacking = _people(
        world,
        ws,
        "R",
        {
            "columns": ["name"],
            "sheets": [bown],
            "ownedColumns": {bown: {"fields": [world.key("R.u")]}},
        },
    )
    path = refused(lacking, 422, "INVALID_EXPORT_LAYOUT")["details"]["path"]
    assert path == f"/people/ownedColumns/{bown}/fields/0"
    unnamed = _people(world, ws, "H", {"columns": ["name"], "referenceLists": [bnn]})
    path = refused(unnamed, 422, "INVALID_EXPORT_LAYOUT")["details"]["path"]
    assert path == "/people/referenceLists/0"
