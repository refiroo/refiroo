"""J58 — Shape a workbook into a model on the canvas (USER_JOURNEYS.md, 0.17 PL3b).

The canvas is a view of the model draft: every drop is one operations request on the draft, shaped
here as the canvas shapes it. A workbook is uploaded to a draft that starts empty, shaped into types
by operations, checked by the dry run and loaded by creating a workspace from the draft (PL4). As
the other draft journeys, each test starts its own draft, names the structures of its own workbook
and no key of a configuration, and runs the job worker itself.
"""

import io
import json
from typing import Any
from uuid import uuid4

import pytest
from openpyxl import Workbook
from scenario import ok, refused
from test_j34_onboard import _profiled, _run, _version, _workspace
from test_j36_workspace_models import BOTH
from test_j40_authorization import _client


def _book(**sheets: list[list[Any]]) -> bytes:
    """A workbook of the sheets given, each a list of rows; a sheet name's underscores are spaces."""
    book = Workbook()
    book.remove(book.active)
    for name, rows in sheets.items():
        sheet = book.create_sheet(name.replace("_", " "))
        for row in rows:
            sheet.append(row)
    out = io.BytesIO()
    book.save(out)
    return out.getvalue()


def _draft(world, content: bytes) -> dict[str, Any]:
    """An empty draft under a new model key with the workbook uploaded and profiled."""
    schema = ok(world.api.get("/system"))["schemaLanguages"][-1]
    name = f"Canvas {uuid4().hex[:6]}"
    empty = {
        "schemaVersion": schema,
        "release": {"key": f"canvas-{uuid4().hex[:8]}", "name": name, "version": "1.0.0"},
        "product": {"name": name},
        "attributeTypes": [],
        "objectTypes": [],
        "relationTypes": [],
        "objectTypeRelations": [],
        "applications": [],
    }
    draft = ok(world.api.post("/model-drafts", {"name": name, "model": empty}), 201)
    _profiled(world, {"draftId": draft["id"]}, "shape.xlsx", content)
    return draft


def _drop(world, draft, *operations: dict[str, Any]) -> dict[str, Any]:
    """One drop: the operations in one request, which is one step of the draft's history."""
    answer = ok(
        world.api.post(
            f"/model-drafts/{draft['id']}/operations",
            {"expectedVersion": _version(world, draft), "operations": list(operations)},
        )
    )
    assert answer["valid"] is True, answer["diagnostics"]
    return answer


def _model(world, draft) -> dict[str, Any]:
    return ok(world.api.get(f"/model-drafts/{draft['id']}"))["model"]


def _profile(world, draft) -> dict[str, Any]:
    return ok(world.api.get(f"/model-drafts/{draft['id']}/profile"))


def _check(world, draft) -> dict[str, Any]:
    """The dry run of the draft's own profile over every row, finished."""
    source = ok(world.api.get("/source-files", draftId=draft["id"]))["items"][0]
    started = ok(
        world.api.post(
            f"/model-drafts/{draft['id']}/dry-run",
            {"sourceFileId": source["id"], "workspaceKey": _workspace(world)},
        ),
        202,
    )
    _run(world)
    done = ok(world.api.get(f"/model-drafts/{draft['id']}/dry-run"))
    assert done["jobId"] == started["jobId"] and done["state"] == "completed", done
    return done


def _create(world, draft, name: str):
    return world.api.post(
        "/workspaces/from-workbook",
        {"draftId": draft["id"], "expectedVersion": _version(world, draft), "name": name},
    )


def _load(world, draft, name: str) -> tuple[dict[str, Any], dict[str, Any]]:
    """The workspace made from the draft, loaded, and the job that loaded it."""
    answer = ok(_create(world, draft, name), 202)
    _run(world)
    job = ok(world.api.get(f"/jobs/{answer['job']['id']}"))
    assert (job["state"], job["counts"]["rejected"]) == ("completed", 0), job
    return answer, job


def _names(world, workspace: str, type_key: str) -> list[str]:
    items = ok(
        world.api.get("/objects", workspaceKey=workspace, objectTypeKey=type_key, pageSize=200)
    )
    return sorted(item["name"] for item in items["items"])


PRODUCTS = [
    ["Product", "Group", "Supplier", "Price", "Colour"],
    ["Pen", "Writing", "Acme", 2, "blue"],
    ["Pencil", "Writing", "Acme", 1, "red"],
    ["Stapler", "Desk", "Binder", 9, "blue"],
    ["Tape", "Desk", "Acme", 3, "red"],
]
SUPPLIERS = [["Supplier", "City"], ["Acme", "Oslo"], ["Binder", "Bergen"]]


@pytest.mark.journey("J58.1")
@pytest.mark.structures(*BOTH)
def test_a_flat_sheet_is_shaped_into_a_hierarchy_with_its_relationship_filter_and_group(world):
    """Given a workbook of products (their group, supplier, price and colour in columns) and of
    suppliers. When the sheets are dropped as the canvas drops them, each drop one request: a sheet
    onto empty space; a parent and its child; a column onto a list's filter box with its attribute
    added; a column onto empty space as a list; the join found by the whole-set route, then the
    relationship; a group. Then each drop is one undo step, the draft is valid, every row loads
    with none refused, and the workspace holds the groups as parents of the products, the products
    related to their suppliers and the colours as a list."""
    draft = _draft(world, _book(Products=PRODUCTS, Suppliers=SUPPLIERS))

    _drop(
        world,
        draft,
        {"kind": "addApplication", "key": "shop", "name": "Shop"},
        {
            "kind": "addObjectType",
            "applicationKey": "shop",
            "key": "supplier",
            "name": "Supplier",
            "parent": None,
        },
        {
            "kind": "addSource",
            "id": "suppliers",
            "sheet": "Suppliers",
            "applicationKey": "shop",
            "objectType": "supplier",
            "key": {"field": "name"},
        },
        {
            "kind": "mapColumn",
            "source": "suppliers",
            "column": "Supplier",
            "binding": {"field": "name"},
        },
    )
    # A parent and its child, with the parent column bound, in one request.
    _drop(
        world,
        draft,
        {
            "kind": "addObjectType",
            "applicationKey": "shop",
            "key": "group",
            "name": "Group",
            "parent": None,
        },
        {
            "kind": "addObjectType",
            "applicationKey": "shop",
            "key": "product",
            "name": "Product",
            "parent": None,
        },
        {
            "kind": "setContainment",
            "objectType": "product",
            "parent": {
                "objectTypes": ["group"],
                "relationType": {"key": "in-group", "name": "Contains", "reverseName": "Part of"},
            },
        },
        {
            "kind": "addSource",
            "id": "products",
            "sheet": "Products",
            "applicationKey": "shop",
            "objectType": "product",
            "key": {"field": "name"},
        },
        {
            "kind": "mapColumn",
            "source": "products",
            "column": "Product",
            "binding": {"field": "name"},
        },
        {
            "kind": "mapColumn",
            "source": "products",
            "column": "Group",
            "binding": {
                "parent": {
                    "objectTypeKey": "group",
                    "matchBy": {"field": "name"},
                    "missing": "create",
                }
            },
        },
    )
    # The join, over every row: the supplier column of the products points at the suppliers' names.
    found = ok(
        world.api.post(
            f"/model-drafts/{draft['id']}/join-candidates",
            {
                "column": {"sheet": "Products", "column": "Supplier"},
                "against": {"sheet": "Suppliers"},
            },
        )
    )
    assert (found["best"], found["tie"], found["column"]["rows"]) == ("A", False, 4)
    assert (found["candidates"][0]["matchedRows"], found["candidates"][0]["share"]) == (4, 1.0)
    _drop(
        world,
        draft,
        {
            "kind": "addRelationType",
            "key": "supplied-by",
            "name": "Supplied by",
            "reverseName": "Supplies",
        },
        {
            "kind": "allowRelation",
            "relationType": "supplied-by",
            "from": "product",
            "to": "supplier",
        },
        {
            "kind": "mapColumn",
            "source": "products",
            "column": "Supplier",
            "binding": {
                "relation": {
                    "relationTypeKey": "supplied-by",
                    "objectTypeKey": "supplier",
                    "matchBy": {"field": "name"},
                }
            },
        },
    )
    # A column onto a list's filter box, its attribute added first, in one request.
    view = next(
        v["key"]
        for v in _model(world, draft)["applications"][0]["views"]
        if v.get("objectTypeKey") == "product"
    )
    _drop(
        world,
        draft,
        {
            "kind": "addAttributeType",
            "key": "price",
            "name": "Price",
            "valueType": "integer",
            "features": {"filterable": True},
        },
        {"kind": "attachAttribute", "objectType": "product", "attributeType": "price"},
        {
            "kind": "mapColumn",
            "source": "products",
            "column": "Price",
            "binding": {"attributeTypeKey": "price"},
        },
        {
            "kind": "setViewProperty",
            "applicationKey": "shop",
            "view": view,
            "property": "filterFields",
            "value": ["price"],
        },
    )
    # A column that is mapped to nothing, onto empty space: its distinct values as a list, linked back.
    _drop(
        world,
        draft,
        {"kind": "addAttributeType", "key": "colour", "name": "Colour"},
        {"kind": "attachAttribute", "objectType": "product", "attributeType": "colour"},
        {
            "kind": "mapColumn",
            "source": "products",
            "column": "Colour",
            "binding": {"attributeTypeKey": "colour"},
        },
        {
            "kind": "convertAttributeToListType",
            "objectType": "product",
            "attributeType": "colour",
            "key": "colour",
            "name": "Colour",
            "relationType": {"key": "has-colour", "name": "Has colour", "reverseName": "Colour of"},
        },
    )
    _drop(
        world,
        draft,
        {"kind": "addNavigationGroup", "applicationKey": "shop", "key": "stock", "label": "Stock"},
        {
            "kind": "placeCollection",
            "applicationKey": "shop",
            "collection": "product",
            "group": "stock",
        },
        {
            "kind": "placeCollection",
            "applicationKey": "shop",
            "collection": "supplier",
            "group": "stock",
        },
    )

    model = _model(world, draft)
    app = model["applications"][0]
    assert [g["key"] for g in app["navigation"]["groups"]] == ["stock"]
    assert next(v for v in app["views"] if v["key"] == view)["config"]["filterFields"][0] == "price"
    entries = ok(world.api.get(f"/model-drafts/{draft['id']}/operations", pageSize=100))["items"]
    assert len({entry["step"] for entry in entries}) == 6, "one step for each drop"
    assert [d for d in _profile(world, draft)["diagnostics"] if d["severity"] == "error"] == []

    done = _check(world, draft)
    assert done["summary"]["rows"]["total"] == len(PRODUCTS) - 1 + len(SUPPLIERS) - 1, done[
        "summary"
    ]
    answer, _ = _load(world, draft, "Shop")
    workspace = answer["workspace"]["key"]
    assert _names(world, workspace, "group") == ["Desk", "Writing"]
    assert _names(world, workspace, "product") == ["Pen", "Pencil", "Stapler", "Tape"]
    assert _names(world, workspace, "supplier") == ["Acme", "Binder"]
    assert _names(world, workspace, "colour") == ["blue", "red"]
    pen = next(
        item
        for item in ok(world.api.get("/objects", workspaceKey=workspace, objectTypeKey="product"))[
            "items"
        ]
        if item["name"] == "Pen"
    )
    assert [step["name"] for step in pen["path"]] == ["Writing", "Pen"]
    links = ok(world.api.get("/relations", workspaceKey=workspace, objectId=pen["id"]))["items"]
    related = {(link["relation"]["relationTypeKey"], link["object"]["name"]) for link in links}
    assert related == {("supplied-by", "Acme"), ("has-colour", "blue"), ("in-group", "Writing")}


XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def _reason(world, draft, *operations: dict[str, Any]) -> str:
    """The code a refused request carries for its operation, and nothing applied."""
    before = _version(world, draft)
    response = world.api.post(
        f"/model-drafts/{draft['id']}/operations",
        {"expectedVersion": before, "operations": list(operations)},
    )
    reason = refused(response, 422, "INVALID_OPERATION")["details"]["reason"]
    assert _version(world, draft) == before
    return reason


def _again(world, workspace: str, profile: str, content: bytes) -> dict[str, Any]:
    """A second file loaded by the profile the first load saved: the job, finished."""
    request = {
        "workspaceKey": workspace,
        "profileKey": profile,
        "policy": "independent",
        "onExisting": "overwrite",
        "stage": "execute",
    }
    sent = world.api.upload(
        "/imports", {"file": ("next.xlsx", content, XLSX)}, {"request": json.dumps(request)}
    )
    job = ok(sent, 202)
    _run(world)
    return ok(world.api.get(f"/jobs/{job['id']}"))


def _profile_key(world, draft) -> str:
    key = f"canvas-{uuid4().hex[:8]}"
    _drop(world, draft, {"kind": "setProfile", "key": key})
    return key


TERMS = [
    ["Code", "EN", "DE", "FR"],
    ["a1", "one", "eins", "un"],
    ["a2", "two", "zwei", None],
    ["a3", "three", None, "trois"],
]


@pytest.mark.journey("J58.2")
@pytest.mark.structures(*BOTH)
def test_a_wide_sheet_is_read_as_rows_and_repeats_from_the_saved_profile(world):
    """Given a sheet of codes with a column for each language, some cells empty. When the language
    columns are read as rows by `setUnpivot` and the two columns it adds are bound, in one request.
    Then the dry run makes a record for every filled cell, a request that unpivots a column twice, one
    column or a name the table has is refused by code and changes nothing, and the step undoes;
    the load makes a record for each filled cell and the profile saved with the model loads the
    next file the same way: the cells already loaded are found, the new ones created."""
    draft = _draft(world, _book(Terms=TERMS))
    wide = {
        "kind": "setUnpivot",
        "source": "terms",
        "columns": ["EN", "DE", "FR"],
        "nameColumn": "Language",
        "valueColumn": "Text",
    }
    _drop(
        world,
        draft,
        {"kind": "addApplication", "key": "words", "name": "Words"},
        {
            "kind": "addObjectType",
            "applicationKey": "words",
            "key": "term",
            "name": "Term",
            "parent": None,
        },
        {"kind": "addAttributeType", "key": "code", "name": "Code"},
        {"kind": "addAttributeType", "key": "language", "name": "Language"},
        {"kind": "attachAttribute", "objectType": "term", "attributeType": "code"},
        {"kind": "attachAttribute", "objectType": "term", "attributeType": "language"},
        {
            "kind": "addSource",
            "id": "terms",
            "sheet": "Terms",
            "applicationKey": "words",
            "objectType": "term",
            "key": {"field": "name"},
        },
        {
            "kind": "mapColumn",
            "source": "terms",
            "column": "Code",
            "binding": {"attributeTypeKey": "code"},
        },
    )
    before = _version(world, draft)
    assert _reason(world, draft, {**wide, "columns": ["EN"]}) == "invalidValue"
    assert _reason(world, draft, {**wide, "columns": ["EN", "EN"]}) == "invalidValue"
    assert _reason(world, draft, {**wide, "columns": ["EN", "Nowhere"]}) == "unknownElement"
    assert _reason(world, draft, {**wide, "nameColumn": "DE"}) == "keyTaken"
    assert _reason(world, draft, {**wide, "valueColumn": "Language"}) == "keyTaken"
    assert _reason(world, draft, {"kind": "clearUnpivot", "source": "terms"}) == "unknownElement"
    assert (
        _reason(world, draft, {"kind": "setFillDown", "source": "terms", "columns": ["Language"]})
        == "unknownElement"
    )

    key = _profile_key(world, draft)
    _drop(
        world,
        draft,
        wide,
        {
            "kind": "mapColumn",
            "source": "terms",
            "column": "Language",
            "binding": {"attributeTypeKey": "language"},
        },
        {"kind": "mapColumn", "source": "terms", "column": "Text", "binding": {"field": "name"}},
    )
    source = _profile(world, draft)["definition"]["sources"][0]
    assert source["unpivot"] == {
        "columns": ["EN", "DE", "FR"],
        "nameColumn": "Language",
        "valueColumn": "Text",
    }
    checked = _check(world, draft)["summary"]
    assert (checked["rows"]["total"], checked["sources"][0]["records"]["created"]) == (3, 7)

    # The reading and the bindings of its columns are one step; undone, nothing names a column that is gone.
    ok(
        world.api.post(
            f"/model-drafts/{draft['id']}/undo", {"expectedVersion": _version(world, draft)}
        )
    )
    assert "unpivot" not in _profile(world, draft)["definition"]["sources"][0]
    ok(
        world.api.post(
            f"/model-drafts/{draft['id']}/redo", {"expectedVersion": _version(world, draft)}
        )
    )
    assert _version(world, draft) > before

    answer, _ = _load(world, draft, "Words")
    workspace = answer["workspace"]["key"]
    assert _names(world, workspace, "term") == [
        "eins",
        "one",
        "three",
        "trois",
        "two",
        "un",
        "zwei",
    ]
    more = [*TERMS, ["a4", "four", "vier", None]]
    done = _again(world, workspace, key, _book(Terms=more))
    assert (done["state"], done["counts"]["rejected"], done["counts"]["created"]) == (
        "completed",
        0,
        2,
    ), done["counts"]
    assert len(_names(world, workspace, "term")) == 9


GROUPED = [
    ["Item", "Shelf", "Quantity"],
    ["Fruit", None, None],
    ["apple", "A1", 4],
    ["pear", None, 2],
    ["Veg", None, None],
    ["leek", "B2", 7],
    ["kale", None, 1],
]


@pytest.mark.journey("J58.3")
@pytest.mark.structures(*BOTH)
def test_rows_grouped_under_a_heading_and_a_column_repeated_by_blanks_repeat_from_the_saved_profile(
    world,
):
    """Given a sheet where a row holding only a heading introduces the rows beneath it (the rows hold a
    quantity, so none is mistaken for a heading) and a shelf is written once for the rows that follow. When the heading rows are read as the parent and the
    shelf is filled down. Then the dry run makes the items only (no record of a heading), the load puts each item under its
    heading with its shelf, and the saved profile loads the next file the same way."""
    draft = _draft(world, _book(Stock=GROUPED))
    key = _profile_key(world, draft)
    _drop(
        world,
        draft,
        {"kind": "addApplication", "key": "store", "name": "Store"},
        {
            "kind": "addObjectType",
            "applicationKey": "store",
            "key": "section",
            "name": "Section",
            "parent": None,
        },
        {
            "kind": "addObjectType",
            "applicationKey": "store",
            "key": "item",
            "name": "Item",
            "parent": None,
        },
        {
            "kind": "setContainment",
            "objectType": "item",
            "parent": {
                "objectTypes": ["section"],
                "relationType": {"key": "in-section", "name": "Holds", "reverseName": "Held in"},
            },
        },
        {"kind": "addAttributeType", "key": "shelf", "name": "Shelf"},
        {"kind": "attachAttribute", "objectType": "item", "attributeType": "shelf"},
        {
            "kind": "addSource",
            "id": "stock",
            "sheet": "Stock",
            "applicationKey": "store",
            "objectType": "item",
            "key": {"field": "name"},
        },
        {"kind": "mapColumn", "source": "stock", "column": "Item", "binding": {"field": "name"}},
        {
            "kind": "mapColumn",
            "source": "stock",
            "column": "Shelf",
            "binding": {"attributeTypeKey": "shelf"},
        },
        {"kind": "setHeadingRows", "source": "stock", "column": "Item", "into": "Section"},
        {"kind": "setFillDown", "source": "stock", "columns": ["Shelf"]},
        {
            "kind": "mapColumn",
            "source": "stock",
            "column": "Section",
            "binding": {
                "parent": {
                    "objectTypeKey": "section",
                    "matchBy": {"field": "name"},
                    "missing": "create",
                }
            },
        },
    )
    assert (
        _reason(
            world,
            draft,
            {"kind": "setHeadingRows", "source": "stock", "column": "Item", "into": "Shelf"},
        )
        == "keyTaken"
    )
    assert (
        _reason(world, draft, {"kind": "setFillDown", "source": "stock", "columns": ["Section"]})
        == "invalidValue"
    )
    assert _check(world, draft)["summary"]["sources"][0]["records"]["created"] == 4

    answer, _ = _load(world, draft, "Store")
    workspace = answer["workspace"]["key"]
    items = {
        item["name"]: item
        for item in ok(world.api.get("/objects", workspaceKey=workspace, objectTypeKey="item"))[
            "items"
        ]
    }
    assert {name: item["path"][0]["name"] for name, item in items.items()} == {
        "apple": "Fruit",
        "pear": "Fruit",
        "leek": "Veg",
        "kale": "Veg",
    }
    assert {name: item["attributes"][0]["value"] for name, item in items.items()} == {
        "apple": "A1",
        "pear": "A1",
        "leek": "B2",
        "kale": "B2",
    }
    more = [*GROUPED[:4], ["plum", None, 3], *GROUPED[4:]]
    done = _again(world, workspace, key, _book(Stock=more))
    assert (done["state"], done["counts"]["rejected"], done["counts"]["created"]) == (
        "completed",
        0,
        1,
    ), done["counts"]
    plum = next(
        item
        for item in ok(world.api.get("/objects", workspaceKey=workspace, objectTypeKey="item"))[
            "items"
        ]
        if item["name"] == "plum"
    )
    assert plum["path"][0]["name"] == "Fruit"
    assert plum["attributes"][0]["value"] == "A1"


def _join(world, draft, column: dict[str, Any], against: dict[str, Any]):
    return world.api.post(
        f"/model-drafts/{draft['id']}/join-candidates", {"column": column, "against": against}
    )


@pytest.mark.journey("J58.4")
@pytest.mark.structures(*BOTH)
def test_a_join_is_found_over_every_row_and_a_tie_is_asked_not_guessed(world):
    """Given a column of 1,200 different references and a lookup sheet holding them in two identical
    columns, one column of the first 1,000 and one holding only the last. When the candidates are
    asked for. Then every row is compared (the column holding only the last reference matches it),
    the two identical columns are a tie with no best and their letters, naming one of them answers
    it, and a header, a letter or a sheet the file lacks is refused by code."""
    refs = [f"R{n}" for n in range(1, 1201)]
    book = _book(
        Orders=[["Ref"], *([r] for r in refs)],
        Lookup=[
            ["Code", "Alias", "Part", "Late"],
            *(
                [r, r, r if n <= 1000 else None, r if n == 1200 else None]
                for n, r in enumerate(refs, 1)
            ),
        ],
    )
    draft = _draft(world, book)
    column = {"sheet": "Orders", "column": "Ref"}

    found = ok(_join(world, draft, column, {"sheet": "Lookup"}))
    assert found["column"] == {
        "sheet": "Orders",
        "letter": "A",
        "header": "Ref",
        "rows": 1200,
        "distinct": 1200,
    }
    by_letter = {c["letter"]: c for c in found["candidates"]}
    assert (
        by_letter["A"]["matchedValues"],
        by_letter["A"]["matchedRows"],
        by_letter["A"]["share"],
    ) == (1200, 1200, 1.0)
    assert (
        by_letter["B"]["matchedValues"],
        by_letter["C"]["matchedValues"],
        by_letter["D"]["matchedValues"],
    ) == (1200, 1000, 1)
    assert all(c["unique"] for c in found["candidates"])
    assert (found["tie"], found["best"], found["tied"]) == (True, None, ["A", "B"])
    assert [c["letter"] for c in found["candidates"]] == ["A", "B", "C", "D"]

    named = ok(_join(world, draft, column, {"sheet": "Lookup", "column": "Code"}))
    assert (named["tie"], named["best"], [c["letter"] for c in named["candidates"]]) == (
        False,
        "A",
        ["A"],
    )
    part = ok(_join(world, draft, column, {"sheet": "Lookup", "letter": "C"}))
    assert (part["best"], part["candidates"][0]["share"]) == ("C", round(1000 / 1200, 4))

    refused(
        _join(world, draft, column, {"sheet": "Lookup", "column": "Nowhere"}),
        422,
        "COLUMN_NOT_FOUND",
    )
    refused(
        _join(world, draft, {"sheet": "Orders", "letter": "Z"}, {"sheet": "Lookup"}),
        422,
        "COLUMN_NOT_FOUND",
    )
    refused(_join(world, draft, column, {"sheet": "Missing"}), 404, "SOURCE_SHEET_NOT_FOUND")
    bare = ok(
        world.api.post("/model-drafts", {"name": "No book", "model": _model(world, draft)}), 201
    )
    refused(_join(world, bare, column, {"sheet": "Lookup"}), 404, "SOURCE_FILE_NOT_FOUND")


@pytest.mark.journey("J58.5")
@pytest.mark.structures(*BOTH)
def test_card_positions_are_the_drafts_own_and_not_a_model_step(world):
    """Given a draft. When card positions are written and read, merged by key, one removed, and a
    model step is made and undone. Then the positions are as last written, the draft's version
    never moved for them (an operations request sent at the version read before still applies), the
    undo left them alone, and a position out of range, a long key or more than 500 cards is refused.
    Folded cards (merged by key, unfolded by false or null) and the chosen scope (replaced, null the
    default, an unknown one refused) are kept the same way and never move the draft's version (CE1)."""
    draft = _draft(world, _book(Sheet=[["A"], ["x"]]))
    path = f"/model-drafts/{draft['id']}/canvas"
    assert ok(world.api.get(path)) == {"positions": {}, "folded": [], "scope": None}
    version = _version(world, draft)

    placed = ok(
        world.api.patch(
            path, {"positions": {"sheet:Sheet": {"x": 10, "y": 20.5}, "type:a": {"x": -4, "y": 0}}}
        )
    )
    assert placed["positions"] == {
        "sheet:Sheet": {"x": 10.0, "y": 20.5},
        "type:a": {"x": -4.0, "y": 0.0},
    }
    moved = ok(
        world.api.patch(path, {"positions": {"type:a": {"x": 7, "y": 8}, "sheet:Sheet": None}})
    )
    assert moved["positions"] == {"type:a": {"x": 7.0, "y": 8.0}}
    assert _version(world, draft) == version

    ok(
        world.api.post(
            f"/model-drafts/{draft['id']}/operations",
            {
                "expectedVersion": version,
                "operations": [{"kind": "addApplication", "key": "one", "name": "One"}],
            },
        )
    )
    ok(
        world.api.post(
            f"/model-drafts/{draft['id']}/undo", {"expectedVersion": _version(world, draft)}
        )
    )
    assert ok(world.api.get(path)) == moved
    version = _version(world, draft)

    shut = ok(
        world.api.patch(path, {"folded": {"type:a": True, "type:b": True}, "scope": "changed"})
    )
    assert (shut["folded"], shut["scope"], shut["positions"]) == (
        ["type:a", "type:b"],
        "changed",
        moved["positions"],
    )
    opened = ok(
        world.api.patch(path, {"folded": {"type:a": None, "type:c": True, "type:b": False}})
    )
    assert (opened["folded"], opened["scope"]) == (["type:c"], "changed")
    # A part left out stays; a scope sent as null is the default again.
    assert ok(world.api.patch(path, {"positions": {"type:a": None}}))["folded"] == ["type:c"]
    assert ok(world.api.patch(path, {"scope": None}))["scope"] is None
    assert _version(world, draft) == version
    moved = ok(world.api.patch(path, {"folded": {"type:c": None}}))
    assert moved["folded"] == []

    for body in (
        {"scope": "everything"},
        {"folded": {}},
        {"folded": {"k" * 201: True}},
        {"folded": {"k": "maybe"}},
        {"positions": {"k": {"x": 2_000_000, "y": 0}}},
        {"positions": {"k" * 201: {"x": 0, "y": 0}}},
        {"positions": {}},
        {"positions": {"k": {"x": 0}}},
    ):
        refused(world.api.patch(path, body), 422, "REQUEST_VALIDATION_ERROR")
    many = {f"card:{n}": {"x": n, "y": n} for n in range(501)}
    refused(world.api.patch(path, {"positions": many}), 422, "INVALID_CANVAS")
    refused(world.api.patch(path, {"folded": {k: True for k in many}}), 422, "INVALID_CANVAS")
    assert ok(world.api.get(path)) == moved
    refused(
        world.api.get("/model-drafts/00000000-0000-4000-8000-000000000000/canvas"),
        404,
        "MODEL_DRAFT_NOT_FOUND",
    )


@pytest.mark.journey("J58.6")
@pytest.mark.structures(*BOTH)
def test_a_caller_without_model_authoring_is_refused_by_code(world):
    """Given a draft with a workbook. When a caller holding other groups but not Model authoring
    reads the join candidates, reads or writes the canvas, or sends a reading kind. Then each is
    `403 FORBIDDEN` naming the action and its group, nothing changes, and the holder of Model
    authoring is answered."""
    draft = _draft(world, _book(Sheet=[["A"], ["x"]]))
    _, caller = _client(world, "Canvas without", ("workspace-admin", {"instance": True}))
    expected = {"action": "model.author", "groups": ["model-authoring"], "workspaceKey": None}
    path = f"/model-drafts/{draft['id']}"
    version = _version(world, draft)
    reading = {
        "expectedVersion": version,
        "operations": [{"kind": "clearFillDown", "source": "none"}],
    }
    for response in (
        caller.api.post(
            f"{path}/join-candidates",
            {"column": {"sheet": "Sheet", "column": "A"}, "against": {"sheet": "Sheet"}},
        ),
        caller.api.get(f"{path}/canvas"),
        caller.api.patch(f"{path}/canvas", {"positions": {"k": {"x": 0, "y": 0}}}),
        caller.api.post(f"{path}/operations", reading),
    ):
        assert refused(response, 403, "FORBIDDEN")["details"] == expected
    assert ok(world.api.get(f"{path}/canvas")) == {"positions": {}, "folded": [], "scope": None}
    assert _version(world, draft) == version
    _, author = _client(world, "Canvas with", ("model-admin", {"instance": True}))
    ok(author.api.get(f"{path}/canvas"))
    ok(author.api.patch(f"{path}/canvas", {"positions": {"k": {"x": 1, "y": 2}}}))
    ok(
        author.api.post(
            f"{path}/join-candidates",
            {
                "column": {"sheet": "Sheet", "column": "A"},
                "against": {"sheet": "Sheet", "letter": "A"},
            },
        )
    )
    assert _reason(author, draft, {"kind": "clearFillDown", "source": "none"}) == "unknownElement"


UNTIDY = [
    ["Price list for the spring", None, None],
    ["Item", "Amount ", "Unit  price"],
    ["Pen", 2, 1.5],
    ["Pencil", 1, 0.5],
]


@pytest.mark.journey("J58.1")
@pytest.mark.structures(*BOTH)
def test_a_header_is_matched_as_the_profile_lists_it_on_any_header_row(world):
    """Given a sheet with a title row, its header on row 2, one header ending in a space and one with
    two spaces inside. When a source is added with `headerRow: 2` and each column is mapped by the
    header exactly as the profile's columns route answers it, in one request. Then the request is
    valid, the saved binding names the header as the import reads it (surrounding whitespace is not
    significant), the dry run and the load read every row, and the profile loads the next file."""
    draft = _draft(world, _book(Prices=UNTIDY))
    source = ok(world.api.get("/source-files", draftId=draft["id"]))["items"][0]
    columns = ok(world.api.get(f"/source-files/{source['id']}/profile/sheets/Prices/columns"))
    listed = [item["header"] for item in columns["items"]]
    assert "Unit  price" in listed and any(h.strip() == "Amount" for h in listed), listed
    amount = next(h for h in listed if h.strip() == "Amount")
    _drop(
        world,
        draft,
        {"kind": "addApplication", "key": "shop", "name": "Shop"},
        {
            "kind": "addObjectType",
            "applicationKey": "shop",
            "key": "item",
            "name": "Item",
            "parent": None,
        },
        {"kind": "addAttributeType", "key": "amount", "name": "Amount"},
        {"kind": "addAttributeType", "key": "unit-price", "name": "Unit price"},
        {"kind": "attachAttribute", "objectType": "item", "attributeType": "amount"},
        {"kind": "attachAttribute", "objectType": "item", "attributeType": "unit-price"},
        {
            "kind": "addSource",
            "id": "prices",
            "sheet": "Prices",
            "headerRow": 2,
            "applicationKey": "shop",
            "objectType": "item",
            "key": {"field": "name"},
        },
        {"kind": "mapColumn", "source": "prices", "column": "Item", "binding": {"field": "name"}},
        {
            "kind": "mapColumn",
            "source": "prices",
            "column": amount,
            "binding": {"attributeTypeKey": "amount"},
        },
        {
            "kind": "mapColumn",
            "source": "prices",
            "column": "Unit  price",
            "binding": {"attributeTypeKey": "unit-price"},
        },
    )
    bound = [b["column"] for b in _profile(world, draft)["definition"]["sources"][0]["columns"]]
    assert bound == ["Item", "Amount", "Unit  price"], bound
    _drop(world, draft, {"kind": "unmapColumn", "source": "prices", "column": amount})
    _drop(
        world,
        draft,
        {
            "kind": "mapColumn",
            "source": "prices",
            "column": "Amount",
            "binding": {"attributeTypeKey": "amount"},
        },
    )
    assert _check(world, draft)["state"] == "completed"
    _profile_key(world, draft)
    answer, _ = _load(world, draft, f"Prices {uuid4().hex[:6]}")
    workspace = answer["workspace"]["key"] if "workspace" in answer else None
    assert workspace is not None, answer
    assert _names(world, workspace, "item") == ["Pen", "Pencil"]
