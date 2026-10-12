"""J34 — Onboard a workbook (USER_JOURNEYS.md): source files, their profiles and the dry run
(0.10 A3).

A workbook is uploaded to a model draft and profiled; a dry run binds it through a profile against
the draft's model and says what an import would do, writing nothing. The workbooks are the
generated W1 and W3 (``tests/workbooks.py``), named by structure; the draft is the configuration's
active model with a type the test adds under a ``j34-`` key, so no test names a configuration's key.
The journey application runs no worker thread: a test runs the job worker itself (``_run``).
"""

import copy
import json
import os
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import uuid4

import pytest
import workbooks
from scenario import ok, refused

XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
TYPES = {"xlsx": XLSX, "csv": "text/csv", "xls": "application/vnd.ms-excel"}


def _run(world) -> int:
    return world.api.client.app.state.job_worker.run_until_idle()


def _workspace(world) -> str:
    key = f"onboard-{uuid4().hex[:8]}"
    ok(world.api.post("/workspaces", {"key": key, "label": "Onboarding"}), 201)
    return key


def _draft(world) -> dict[str, Any]:
    active = ok(world.api.get("/model-runtime-state"))["activeReleaseId"]
    release = ok(world.api.get(f"/model-releases/{active}", includeModel=True))
    body = {"name": "Onboarding", "model": release["model"], "baseReleaseId": release["id"]}
    return ok(world.api.post("/model-drafts", body), 201)


def _version(world, draft: dict[str, Any]) -> int:
    return ok(world.api.get(f"/model-drafts/{draft['id']}"))["version"]


def _apply(world, draft: dict[str, Any], *operations: dict[str, Any]) -> dict[str, Any]:
    answer = ok(
        world.api.post(
            f"/model-drafts/{draft['id']}/operations",
            {"expectedVersion": _version(world, draft), "operations": list(operations)},
        )
    )
    assert answer["valid"] is True, answer["diagnostics"]
    return answer


def _upload(world, owner: dict[str, str], name: str, content: bytes, **request: Any):
    return world.api.upload(
        "/source-files",
        {"file": (name, content, TYPES[name.rsplit(".", 1)[1]])},
        {"request": json.dumps({"owner": owner, **request})},
    )


def _profiled(world, owner: dict[str, str], name: str, content: bytes, **request: Any):
    source = ok(_upload(world, owner, name, content, **request), 201)
    _run(world)
    source = ok(world.api.get(f"/source-files/{source['id']}"))
    assert source["profile"]["state"] == "completed", source["profile"]
    return source


def _all(world, path: str, page_size: int = 500, **params: Any) -> list[dict[str, Any]]:
    items, cursor = [], None
    while True:
        page = ok(world.api.get(path, pageSize=page_size, cursor=cursor, **params))
        items += page["items"]
        cursor = page.get("nextCursor")
        if not cursor:
            return items


def _item_type(world, draft: dict[str, Any]) -> dict[str, str]:
    """A new type of K's application, keyed by a new unique text attribute, related to K: the
    draft's addition the W1 rows load into. The keys it created."""
    _apply(
        world,
        draft,
        {
            "kind": "addObjectType",
            "applicationKey": world.app("K"),
            "key": "j34-item",
            "name": "Item",
            "pluralName": "Items",
            "parent": None,
        },
        {
            "kind": "addAttributeType",
            "key": "j34-code",
            "name": "Item code",
            "valueType": "text",
            "features": {"unique": True, "searchable": True},
        },
        {"kind": "attachAttribute", "objectType": "j34-item", "attributeType": "j34-code"},
        {"kind": "addRelationType", "key": "j34-made-of", "name": "Made of", "reverseName": "Material of"},
        {"kind": "allowRelation", "relationType": "j34-made-of", "from": "j34-item", "to": world.key("K")},
    )
    return {"type": "j34-item", "code": "j34-code", "relation": "j34-made-of"}


def _profile(world, book: workbooks.W1, keys: dict[str, str], **extra: Any) -> dict[str, Any]:
    """W1's ``S1`` as items: ``K`` the key, ``N`` the name, ``T`` the K record of that name."""
    material = {
        "column": book.header("T"),
        "relation": {
            "relationTypeKey": keys["relation"],
            "objectTypeKey": world.key("K"),
            "matchBy": {"field": "name"},
        },
    }
    if "valueMap" in extra:
        material["valueMap"] = extra.pop("valueMap")
    return {
        "sources": [
            {
                "sheet": workbooks.S1,
                "applicationKey": world.app("K"),
                "objectTypeKey": keys["type"],
                "key": {"attributeTypeKey": keys["code"]},
                "columns": [
                    {"column": book.header("K"), "attributeTypeKey": keys["code"]},
                    {"column": book.header("N"), "field": "name"},
                    material,
                ],
            }
        ],
        **extra,
    }


def _dry_run(world, draft, source, workspace, profile) -> dict[str, Any]:
    started = ok(
        world.api.post(
            f"/model-drafts/{draft['id']}/dry-run",
            {"sourceFileId": source["id"], "workspaceKey": workspace, "profile": profile},
        ),
        202,
    )
    assert started["state"] == "checking"
    _run(world)
    done = ok(world.api.get(f"/model-drafts/{draft['id']}/dry-run"))
    assert done["jobId"] == started["jobId"]
    assert done["state"] == "completed", done["error"]
    return done


def _materials(world, book: workbooks.W1, workspace: str) -> None:
    """K records named as W1's materials, the list ``T`` looks up."""
    for name in sorted(book.distinct("T") - set(workbooks.PLACEHOLDERS)):
        ok(world.create("K", name, workspace=workspace), 201)


@pytest.mark.journey("J34.1")
@pytest.mark.structures("A1")
def test_a_workbook_uploaded_to_a_draft_is_profiled_sheet_by_sheet_and_column_by_column(world):
    """Given a draft and W1 at 200 rows. When it is uploaded. Then a profile job is queued and the
    profile reads SOURCE_FILE_PROFILE_NOT_READY until it ends; then it lists S1 and S2 with header
    row 1 and their rows, and S1's columns, paged two at a time, give the candidate keys, P's
    distinct parents, T's placeholders, Fo's delimiter and the overlaps with S2."""
    draft = _draft(world)
    book = workbooks.w1(rows=200)
    source = ok(_upload(world, {"draftId": draft["id"]}, "catalogue.xlsx", book.content), 201)
    assert source["owner"] == {"draftId": draft["id"], "profileKey": None}
    assert source["format"] == "xlsx" and source["bytes"] == len(book.content)
    assert source["profile"]["state"] == "queued"
    job = ok(world.api.get(f"/jobs/{source['profile']['jobId']}"))
    assert job["kind"] == "profile"
    refused(
        world.api.get(f"/source-files/{source['id']}/profile/sheets"),
        409,
        "SOURCE_FILE_PROFILE_NOT_READY",
    )

    _run(world)
    sheets = ok(world.api.get(f"/source-files/{source['id']}/profile/sheets"))["items"]
    assert [(s["name"], s["headerRow"], s["rows"]) for s in sheets] == [
        (workbooks.S1, 1, 201),
        (workbooks.S2, 1, 1 + 200 * len(workbooks.LANGUAGES)),
    ]
    (block,) = sheets[0]["blocks"]
    assert (block["firstColumn"], block["lastColumn"], block["headerRow"], block["rows"]) == (
        "A", book.column("X"), 1, 200,
    )

    pages, cursor, columns = 0, None, []
    while True:
        page = ok(
            world.api.get(
                f"/source-files/{source['id']}/profile/sheets/{workbooks.S1}/columns",
                pageSize=2,
                cursor=cursor,
            )
        )
        pages += 1
        columns += page["items"]
        cursor = page.get("nextCursor")
        if not cursor:
            break
    assert pages == 6
    by_header = {column["header"]: column for column in columns}
    assert list(by_header) == list(workbooks.HEADERS.values())

    def column(structure: str) -> dict[str, Any]:
        return by_header[book.header(structure)]

    # K and X (a GUID on every row) are filled on every row with no value twice.
    assert {c["header"] for c in columns if c["candidateKey"]} == {
        book.header("K"),
        book.header("X"),
    }
    assert column("P")["distinct"] == len(book.distinct("P")) == 200 // 15
    assert column("Po")["valueTypes"]["integer"] == 200
    placeholders = {item["value"]: item["count"] for item in column("T")["placeholders"]}
    assert set(placeholders) == set(workbooks.PLACEHOLDERS)
    assert placeholders == {
        value: sum(row["T"] == value for row in book.rows) for value in workbooks.PLACEHOLDERS
    }
    assert column("Fo")["delimiters"][0]["character"] == ";"
    assert column("K")["overlaps"][0] == {
        "sheet": workbooks.S2,
        "column": "A",
        "header": workbooks.S2_HEADERS["K"],
        "values": 200,
        "share": 1.0,
        "workspaceKey": None,
        "objectTypeKey": None,
        "field": None,
        "attributeTypeKey": None,
    }
    names = [o for o in column("N")["overlaps"] if o["sheet"] == workbooks.S2]
    assert names and names[0]["header"] == workbooks.S2_HEADERS["N"]
    assert column("K")["limits"] == {
        "overlapValues": 1000,
        "overlapsListed": 5,
        "placeholdersListed": 10,
    }


@pytest.mark.journey("J34.1")
@pytest.mark.structures("A1")
def test_lists_laid_side_by_side_are_reported_as_blocks_under_their_header_row(world):
    """Given W3, lists side by side under a section row and a group row. When profiled. Then each
    list is a block with its range and header row 3, separated by its empty columns, and the
    section and group rows are not taken for columns."""
    draft = _draft(world)
    book = workbooks.w3()
    source = _profiled(world, {"draftId": draft["id"]}, "lists.xlsx", book.content)
    (sheet,) = ok(world.api.get(f"/source-files/{source['id']}/profile/sheets"))["items"]
    assert sheet["name"] == book.sheet and sheet["headerRow"] == book.header_row
    assert len(sheet["blocks"]) == len(book.blocks)
    letters = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"

    def letter(number: int) -> str:
        return (letters[(number - 1) // 26 - 1] if number > 26 else "") + letters[(number - 1) % 26]

    for found, made in zip(sheet["blocks"], book.blocks, strict=True):
        assert (found["firstColumn"], found["lastColumn"]) == (letter(made["first"]), letter(made["last"]))
        assert (found["headerRow"], found["lastRow"]) == (book.header_row, made["lastRow"])
    columns = _all(world, f"/source-files/{source['id']}/profile/sheets/{book.sheet}/columns")
    firsts = [c for c in columns if c["letter"] in {letter(made["first"]) for made in book.blocks}]
    assert [c["header"] for c in firsts] == [made["title"] for made in book.blocks]


@pytest.mark.journey("J34.1")
@pytest.mark.structures("A1")
@pytest.mark.settings(IMPORT_MAX_BYTES="2000")
def test_files_are_limited_superseded_and_deleted_with_their_draft(world):
    """Given a draft. When a file over IMPORT_MAX_BYTES or an .xls file is uploaded, they are
    refused; a second file supersedes the first, which stays listed until the retention sweep;
    deleting the draft deletes its files and their staged rows."""
    draft = _draft(world)
    owner = {"draftId": draft["id"]}
    error = refused(
        _upload(world, owner, "big.csv", b"code,name\n" + b"x,y\n" * 600), 413, "IMPORT_TOO_LARGE"
    )
    assert error["details"]["setting"] == "IMPORT_MAX_BYTES"
    refused(_upload(world, owner, "old.xls", b"\xd0\xcf\x11\xe0"), 422, "UNSUPPORTED_FILE_FORMAT")

    first = _profiled(world, owner, "first.csv", b"code,name\na,Alpha\n")
    second = _profiled(world, owner, "second.csv", b"code,name\nb,Beta\n")
    listed = _all(world, "/source-files", draftId=draft["id"])
    assert [item["id"] for item in listed] == [second["id"], first["id"]]
    assert ok(world.api.get(f"/source-files/{first['id']}"))["supersededAt"] is not None
    assert second["supersededAt"] is None

    worker = world.api.client.app.state.job_worker
    files = world.api.client.app.state.job_files
    worker.sweep(datetime.now(UTC) + timedelta(days=8))
    refused(world.api.get(f"/source-files/{first['id']}"), 404, "SOURCE_FILE_NOT_FOUND")
    assert not files.upload(first["id"]).exists()
    assert files.upload(second["id"]).exists()

    ok(world.api.delete(f"/model-drafts/{draft['id']}", expectedVersion=_version(world, draft)), 204)
    refused(world.api.get(f"/source-files/{second['id']}"), 404, "SOURCE_FILE_NOT_FOUND")
    # A file without a row is kept a while, since its row may not be committed yet (files.py);
    # once older than that, the sweep removes it.
    path = files.upload(second["id"])
    worker.sweep()
    assert path.exists()
    old = (datetime.now(UTC) - timedelta(hours=1)).timestamp()
    os.utime(path, (old, old))
    worker.sweep()
    assert not path.exists()


@pytest.mark.journey("J34.3")
@pytest.mark.structures("K")
def test_the_dry_run_follows_the_editing_of_the_draft(world):
    """Given a draft with a new type and W1 mapped onto it by an inline profile, T looking up K
    records by name. When the dry run runs, then it counts records, values and relationships and
    the rows refused by code; after setKey on the mapped attribute (the profile updated) the next
    run is the same; after a value map for T's placeholders the refusals fall and the difference
    names the figures that changed; the rows behind a refusal figure are listed."""
    workspace = _workspace(world)
    book = workbooks.w1(rows=200)
    _materials(world, book, workspace)
    draft = _draft(world)
    keys = _item_type(world, draft)
    source = _profiled(world, {"draftId": draft["id"]}, "catalogue.xlsx", book.content)
    placeholder_rows = sum(row["T"] in workbooks.PLACEHOLDERS for row in book.rows)
    assert placeholder_rows >= 2

    first = _dry_run(world, draft, source, workspace, _profile(world, book, keys))
    summary = first["summary"]
    assert summary["coverage"] == "complete" and summary["difference"] is None
    assert summary["rows"] == {"total": 200, "run": 200}
    (items,) = summary["sources"]
    loaded = 200 - placeholder_rows
    assert items["objectTypeKey"] == keys["type"] and items["rows"] == 200
    assert items["records"] == {"created": loaded, "updated": 0, "unchanged": 0}
    assert items["values"] == loaded and items["relationships"] == loaded
    (rejection,) = items["rejections"]
    assert rejection == {"code": "REFERENCE_NOT_FOUND", "rows": placeholder_rows}

    _apply(world, draft, {"kind": "setKey", "element": {"attributeType": keys["code"]}, "key": "j34-sku"})
    renamed = {**keys, "code": "j34-sku"}
    second = _dry_run(world, draft, source, workspace, _profile(world, book, renamed))
    assert second["summary"]["sources"] == summary["sources"]
    assert second["summary"]["difference"] == []
    assert second["summary"]["previousJobId"] == first["jobId"]

    rows = _all(world, f"/model-drafts/{draft['id']}/dry-run/rows", code="REFERENCE_NOT_FOUND")
    assert len(rows) == placeholder_rows
    assert {row["status"] for row in rows} == {"rejected"}
    refs = {f"{workbooks.S1}!{index + 2}" for index, row in enumerate(book.rows) if row["T"] in workbooks.PLACEHOLDERS}
    assert {row["ref"] for row in rows} == refs

    mapped = _profile(
        world,
        book,
        renamed,
        valueMap="no-material",
        valueMaps={"no-material": {value: "" for value in workbooks.PLACEHOLDERS}},
    )
    third = _dry_run(world, draft, source, workspace, mapped)
    (after,) = third["summary"]["sources"]
    assert after["rejections"] == []
    assert after["records"]["created"] == 200
    (changed,) = third["summary"]["difference"]
    assert changed["figures"] == {
        "records.created": {"now": 200, "was": loaded},
        "rejections.REFERENCE_NOT_FOUND": {"now": 0, "was": placeholder_rows},
        "values": {"now": 200, "was": loaded},
    }


@pytest.mark.journey("J34.3")
@pytest.mark.structures("K")
def test_the_dry_run_checks_the_whole_file_writes_nothing_and_gives_way_to_a_newer_draft(world):
    """Given W1 above 1,000 rows. When a dry run is sent and the draft changes before it runs, it
    stops as cancelled; the next one reports every row of the new version; and the workspace's
    records and feed are unchanged."""
    workspace = _workspace(world)
    book = workbooks.w1(rows=1200)
    _materials(world, book, workspace)
    draft = _draft(world)
    keys = _item_type(world, draft)
    source = _profiled(world, {"draftId": draft["id"]}, "catalogue.xlsx", book.content)
    feed = ok(world.api.get(f"/workspaces/{workspace}/feed", pageSize=1000))["items"]
    records = ok(world.api.get(f"/objects/{world.key('K')}", workspaceKey=workspace, includeTotal=True))

    profile = _profile(world, book, keys)
    body = {"sourceFileId": source["id"], "workspaceKey": workspace, "profile": profile}
    stale = ok(world.api.post(f"/model-drafts/{draft['id']}/dry-run", body), 202)
    _apply(world, draft, {"kind": "setLabel", "element": {"objectType": keys["type"]}, "name": "Article"})
    _run(world)
    cancelled = ok(world.api.get(f"/model-drafts/{draft['id']}/dry-run"))
    assert (cancelled["jobId"], cancelled["state"]) == (stale["jobId"], "cancelled")
    assert cancelled["summary"] is None

    done = _dry_run(world, draft, source, workspace, profile)
    assert done["draftVersion"] == _version(world, draft)
    assert done["summary"]["rows"] == {"total": 1200, "run": 1200}
    (items,) = done["summary"]["sources"]
    placeholder_rows = sum(row["T"] in workbooks.PLACEHOLDERS for row in book.rows)
    assert items["records"]["created"] == 1200 - placeholder_rows

    assert ok(world.api.get(f"/workspaces/{workspace}/feed", pageSize=1000))["items"] == feed
    after = ok(world.api.get(f"/objects/{world.key('K')}", workspaceKey=workspace, includeTotal=True))
    assert after["totalCount"] == records["totalCount"]


@pytest.mark.journey("J34.3")
@pytest.mark.structures("K")
def test_a_dry_run_is_refused_for_a_draft_that_does_not_compile_or_a_profile_that_does_not_fit(world):
    """Given a draft and its profiled W1. When the dry run names an unknown file, a profile naming
    an element the draft lacks, or the draft is made invalid, it is refused SOURCE_FILE_NOT_FOUND,
    INVALID_IMPORT_PROFILE at the pointer, and INVALID_MODEL with the diagnostics."""
    workspace = _workspace(world)
    book = workbooks.w1(rows=30)
    draft = _draft(world)
    keys = _item_type(world, draft)
    pending = ok(_upload(world, {"draftId": draft["id"]}, "catalogue.xlsx", book.content), 201)

    def dry_run(source_id: str, profile: dict[str, Any]):
        body = {"sourceFileId": source_id, "workspaceKey": workspace, "profile": profile}
        return world.api.post(f"/model-drafts/{draft['id']}/dry-run", body)

    refused(dry_run(pending["id"], _profile(world, book, keys)), 409, "SOURCE_FILE_PROFILE_NOT_READY")
    _run(world)
    refused(dry_run(str(uuid4()), _profile(world, book, keys)), 404, "SOURCE_FILE_NOT_FOUND")
    other = _draft(world)
    elsewhere = _profiled(world, {"draftId": other["id"]}, "catalogue.xlsx", book.content)
    refused(dry_run(elsewhere["id"], _profile(world, book, keys)), 404, "SOURCE_FILE_NOT_FOUND")

    lacking = _profile(world, book, {**keys, "code": "j34-no-such-attribute"})
    error = refused(dry_run(pending["id"], lacking), 422, "INVALID_IMPORT_PROFILE")
    pointers = {problem["path"] for problem in error["details"]["problems"]}
    assert "/sources/0/key/attributeTypeKey" in pointers

    model = ok(world.api.get(f"/model-drafts/{draft['id']}"))["model"]
    broken = copy.deepcopy(model)
    item = next(t for t in broken["objectTypes"] if t["key"] == keys["type"])
    item["attributes"][0]["attributeTypeKey"] = "j34-missing"
    ok(world.api.patch(f"/model-drafts/{draft['id']}", {"expectedVersion": _version(world, draft), "model": broken}))
    error = refused(dry_run(pending["id"], _profile(world, book, keys)), 422, "INVALID_MODEL")
    assert error["details"], error


@pytest.mark.journey("J27.8")
@pytest.mark.structures("K")
def test_an_import_naming_a_stored_source_file_loads_as_the_file_sent_does(world):
    """Given a stored profile and a CSV file stored for it. When one import names the stored file
    and another sends the same file, each into a workspace of its own. Then both load the same
    records; naming both a file and a stored one is refused."""
    profile_key = f"j34-{uuid4().hex[:8]}"
    ok(
        world.api.post(
            "/import-profiles",
            {
                "key": profile_key,
                "name": "Materials",
                "sources": [
                    {
                        "applicationKey": world.app("K"),
                        "objectTypeKey": world.key("K"),
                        "columns": [
                            {"column": "name", "field": "name"},
                            {"column": "code", "attributeTypeKey": world.key("K.code")},
                        ],
                    }
                ],
            },
        ),
        201,
    )
    content = b"name,code\nPaper,M1\nCard,M2\nSteel,M3\n"
    stored = _profiled(world, {"profileKey": profile_key}, "materials.csv", content)
    assert stored["owner"] == {"draftId": None, "profileKey": profile_key}

    def loaded(workspace: str, **request: Any):
        body = {
            "workspaceKey": workspace,
            "profileKey": profile_key,
            "policy": "independent",
            "stage": "execute",
            **request,
        }
        return body

    by_id, sent = _workspace(world), _workspace(world)
    first = ok(
        world.api.upload("/imports", {}, {"request": json.dumps(loaded(by_id, sourceFileId=stored["id"]))}),
        202,
    )
    second = ok(
        world.api.upload(
            "/imports",
            {"file": ("materials.csv", content, "text/csv")},
            {"request": json.dumps(loaded(sent))},
        ),
        202,
    )
    _run(world)
    for job in (first, second):
        done = ok(world.api.get(f"/jobs/{job['id']}"))
        assert (done["state"], done["result"], done["counts"]["created"]) == ("completed", "applied", 3)
        assert done["parameters"]["file"]["sha256"] == stored["sha256"]
    for workspace in (by_id, sent):
        page = ok(world.api.get(f"/objects/{world.key('K')}", workspaceKey=workspace, pageSize=10))
        assert sorted(item["name"] for item in page["items"]) == ["Card", "Paper", "Steel"]

    both = world.api.upload(
        "/imports",
        {"file": ("materials.csv", content, "text/csv")},
        {"request": json.dumps(loaded(sent, sourceFileId=stored["id"]))},
    )
    refused(both, 422, "REQUEST_VALIDATION_ERROR")


# --- A5a: the draft's profile, edited by operations (D75–D80) ---


def _step(world, draft: dict[str, Any], *operations: dict[str, Any]) -> dict[str, Any]:
    """One request of operations; its answer (the draft may hold profile warnings)."""
    return ok(
        world.api.post(
            f"/model-drafts/{draft['id']}/operations",
            {"expectedVersion": _version(world, draft), "operations": list(operations)},
        )
    )


def _draft_profile(world, draft: dict[str, Any]) -> dict[str, Any]:
    return ok(world.api.get(f"/model-drafts/{draft['id']}/profile"))


def _catalogue(world, draft: dict[str, Any]) -> dict[str, str]:
    """The draft's catalogue: a category type (top level) containing items, a material and a
    colour list, item attributes for W1's key, order and supplier columns, and relations from an
    item to its material, its colour and to records of K (its features)."""
    app = world.app("K")
    _apply(
        world,
        draft,
        {"kind": "addObjectType", "applicationKey": app, "key": "j34-category", "name": "Category", "pluralName": "Categories", "parent": None},
        {
            "kind": "addObjectType",
            "applicationKey": app,
            "key": "j34-item",
            "name": "Item",
            "pluralName": "Items",
            "parent": {"objectTypes": ["j34-category"], "relationType": {"name": "Contains", "reverseName": "In", "key": "j34-contains"}},
        },
        {"kind": "addObjectType", "applicationKey": app, "key": "j34-material", "name": "Material", "pluralName": "Materials", "parent": None},
        {"kind": "addObjectType", "applicationKey": app, "key": "j34-colour", "name": "Colour", "pluralName": "Colours", "parent": None},
        {"kind": "addAttributeType", "key": "j34-code", "name": "Item code", "valueType": "text", "features": {"unique": True}},
        {"kind": "addAttributeType", "key": "j34-order", "name": "Order", "valueType": "integer", "features": {}},
        {"kind": "addAttributeType", "key": "j34-category-id", "name": "Category ID", "valueType": "text", "features": {"unique": True}},
        {"kind": "addAttributeType", "key": "j34-supplier", "name": "Supplier ID", "valueType": "text", "features": {"unique": True}},
        {"kind": "attachAttribute", "objectType": "j34-item", "attributeType": "j34-code"},
        {"kind": "attachAttribute", "objectType": "j34-item", "attributeType": "j34-order"},
        {"kind": "attachAttribute", "objectType": "j34-item", "attributeType": "j34-supplier"},
        {"kind": "attachAttribute", "objectType": "j34-category", "attributeType": "j34-category-id"},
        {"kind": "addRelationType", "key": "j34-made-of", "name": "Made of", "reverseName": "Material of"},
        {"kind": "allowRelation", "relationType": "j34-made-of", "from": "j34-item", "to": "j34-material"},
        {"kind": "addRelationType", "key": "j34-coloured", "name": "Coloured", "reverseName": "Colour of"},
        {"kind": "allowRelation", "relationType": "j34-coloured", "from": "j34-item", "to": "j34-colour"},
        {"kind": "addRelationType", "key": "j34-has-feature", "name": "Has feature", "reverseName": "Feature of"},
        {"kind": "allowRelation", "relationType": "j34-has-feature", "from": "j34-item", "to": world.key("K")},
    )
    return {"app": app}


def _features(world, workspace: str) -> None:
    """K records named as W1's feature columns and features, which its flags and ``Fo`` name."""
    for name in sorted({workbooks.HEADERS["F1"], workbooks.HEADERS["F2"], *workbooks.FEATURES}):
        ok(world.create("K", name, workspace=workspace), 201)


def _onboarding(world) -> tuple[dict[str, Any], workbooks.W1, dict[str, Any], str]:
    """A draft with the catalogue, W1 profiled for it in a workspace holding the features."""
    workspace = _workspace(world)
    _features(world, workspace)
    draft = _draft(world)
    _catalogue(world, draft)
    book = workbooks.w1(rows=200)
    source = _profiled(world, {"draftId": draft["id"]}, "catalogue.xlsx", book.content, workspaceKey=workspace)
    return draft, book, source, workspace


def _map_by_hand(world, draft: dict[str, Any], book: workbooks.W1) -> list[dict[str, Any]]:
    """W1's S1 mapped onto items, one request per step, as the editor sends them; the answers."""
    h = book.header
    lookup = {"relation": {"relationTypeKey": "j34-made-of", "objectTypeKey": "j34-material", "matchBy": {"field": "name"}, "missing": "create"}}
    steps = [
        [{"kind": "addSource", "id": "items", "sheet": workbooks.S1, "objectType": "j34-item", "key": {"attributeTypeKey": "j34-code"}}],
        [{"kind": "mapColumn", "source": "items", "column": h("K"), "binding": {"attributeTypeKey": "j34-code"}}],
        [{"kind": "mapColumn", "source": "items", "column": h("N"), "binding": {"field": "name"}}],
        [{"kind": "mapColumn", "source": "items", "column": h("P"), "binding": {"parent": {"objectTypeKey": "j34-category", "matchBy": {"field": "name"}, "missing": "create"}}}],
        [{"kind": "mapColumn", "source": "items", "column": h("T"), "binding": lookup}],
        [{"kind": "setColumnReading", "source": "items", "column": h("F1"), "reading": "relationFlag", "relationTypeKey": "j34-has-feature", "objectTypeKey": world.key("K"), "target": h("F1")}],
        [{"kind": "setColumnReading", "source": "items", "column": h("F2"), "reading": "relationFlag", "target": h("F2"), "relationTypeKey": "j34-has-feature", "objectTypeKey": world.key("K")}],
        [{"kind": "setColumnReading", "source": "items", "column": h("Fo"), "reading": "relation", "relationTypeKey": "j34-has-feature", "objectTypeKey": world.key("K")}],
        [{"kind": "splitColumn", "source": "items", "column": h("Fo"), "delimiter": ";"}],
        [{"kind": "ignoreColumn", "source": "items", "column": h("X")}],
    ]
    return [_step(world, draft, *operations) for operations in steps]


def _install(world, draft: dict[str, Any]) -> dict[str, Any]:
    """The draft installed as the next version of its release (D18)."""
    _step(world, draft, {"kind": "setRelease", "version": "1.1.0"})
    return ok(world.api.post(f"/model-drafts/{draft['id']}/installation", {"expectedVersion": _version(world, draft)}), 201)


def _summary_of(world, draft: dict[str, Any], answer: dict[str, Any]) -> dict[str, Any]:
    """The dry run a step queued, once the worker ran it."""
    assert answer["dryRun"] is not None and answer["dryRun"]["state"] == "checking", answer
    _run(world)
    done = ok(world.api.get(f"/model-drafts/{draft['id']}/dry-run"))
    assert (done["jobId"], done["state"], done["draftVersion"]) == (answer["dryRun"]["jobId"], "completed", answer["version"]), done
    return done["summary"]


@pytest.mark.journey("J34.2")
@pytest.mark.structures("K")
def test_a_workbook_is_mapped_by_hand_one_step_at_a_time_and_the_dry_run_follows(world):
    """Given a draft with a new type and W1 profiled. When a source is added on S1 and K, N, P, T,
    the flags F1/F2, Fo (split on ;) are mapped and X ignored, one request each. Then each is one
    step, the draft's profile reads them and is valid against the draft's model, and the last
    step's dry run counts S1's rows with no row refused (T's values created, D77)."""
    draft, book, _, _ = _onboarding(world)
    before = _all(world, f"/model-drafts/{draft['id']}/operations")
    answers = _map_by_hand(world, draft, book)
    after = _all(world, f"/model-drafts/{draft['id']}/operations")
    assert len({entry["step"] for entry in after}) - len({entry["step"] for entry in before}) == len(answers)

    read = _draft_profile(world, draft)
    assert read["valid"] is True, read["diagnostics"]
    (items,) = read["profile"]["sources"]
    by_column = {b.get("column") or tuple(b["columns"]): b for b in items["columns"]}
    assert by_column[book.header("K")] == {"column": book.header("K"), "attributeTypeKey": "j34-code"}
    assert by_column[(book.header("F1"), book.header("F2"))]["relationFlags"]["targets"] == {
        book.header("F1"): book.header("F1"),
        book.header("F2"): book.header("F2"),
    }
    assert by_column[book.header("Fo")]["relation"]["split"] == ";"
    assert by_column[book.header("X")] == {"column": book.header("X"), "ignore": True}
    assert "id" not in read["definition"]["sources"][0]

    summary = _summary_of(world, draft, answers[-1])
    (source,) = summary["sources"]
    assert (source["rows"], source["records"]["created"], source["rejections"]) == (200, 200, [])
    assert source["relatedRecords"] == len(book.distinct("P")) + len(book.distinct("T"))


@pytest.mark.journey("J34.2")
@pytest.mark.structures("K")
def test_a_value_map_and_values_added_to_a_list_change_the_next_dry_run(world):
    """Given W1 mapped by hand. When N/A and - are mapped to empty for T, then the colour code Lc is
    read as a lookup of a list without its values, and its values are added to the list. Then the
    first dry run's difference shows the created related records falling by the placeholders, the
    lookup refuses every row REFERENCE_NOT_FOUND, and adding the values clears the refusals."""
    draft, book, _, _ = _onboarding(world)
    first = _summary_of(world, draft, _map_by_hand(world, draft, book)[-1])["sources"][0]

    mapped = _step(
        world,
        draft,
        {"kind": "setValueMap", "name": "placeholders", "entries": dict.fromkeys(workbooks.PLACEHOLDERS), "source": "items", "column": book.header("T")},
    )
    summary = _summary_of(world, draft, mapped)
    assert summary["sources"][0]["relatedRecords"] == first["relatedRecords"] - len(workbooks.PLACEHOLDERS)
    (difference,) = summary["difference"]
    assert difference["figures"]["relatedRecords"] == {"now": first["relatedRecords"] - 2, "was": first["relatedRecords"]}

    lookup = _step(
        world,
        draft,
        {"kind": "setColumnReading", "source": "items", "column": book.header("Lc"), "reading": "lookup", "relationTypeKey": "j34-coloured", "objectTypeKey": "j34-colour"},
    )
    refusals = _summary_of(world, draft, lookup)["sources"][0]["rejections"]
    assert refusals == [{"code": "REFERENCE_NOT_FOUND", "rows": 200}]
    rows = ok(world.api.get(f"/model-drafts/{draft['id']}/dry-run/rows", code="REFERENCE_NOT_FOUND", pageSize=5))
    assert len(rows["items"]) == 5

    added = _step(world, draft, {"kind": "addValuesToList", "source": "items", "column": book.header("Lc")})
    source = _summary_of(world, draft, added)["sources"][0]
    assert source["rejections"] == []
    assert source["relatedRecords"] == first["relatedRecords"] - 2 + len(book.distinct("Lc"))


def _followed(world, draft: dict[str, Any], operation: dict[str, Any]) -> dict[str, Any]:
    """``operation`` applied; one undo puts the profile back whole, and one redo applies it again.
    The profile after it."""
    before = _draft_profile(world, draft)["profile"]
    _step(world, draft, operation)
    after = _draft_profile(world, draft)
    ok(world.api.post(f"/model-drafts/{draft['id']}/undo", {"expectedVersion": _version(world, draft)}))
    assert _draft_profile(world, draft)["profile"] == before
    ok(world.api.post(f"/model-drafts/{draft['id']}/redo", {"expectedVersion": _version(world, draft)}))
    assert _draft_profile(world, draft)["profile"] == after["profile"]
    return after


def _bindings(profile: dict[str, Any], source_id: str) -> dict[str, dict[str, Any]]:
    source = next(s for s in profile["sources"] if s["id"] == source_id)
    return {b.get("column") or ",".join(b["columns"]): b for b in source["columns"]}


@pytest.mark.journey("J34.7")
@pytest.mark.structures("K")
def test_the_draft_profile_follows_renames_moves_splits_and_merges_and_undoes_with_them(world):
    """Given W1 mapped, with a category source on S1 and Po mapped to the items' order. When the
    item type and its code are re-keyed, the order attribute moved to the category, the supplier ID
    split into a type of its own and that type merged back. Then the profile names the new keys,
    the moved column sits in the category's source, the split's columns in a source of the new
    type joined by the split's relation, the merge re-points them; the profile is valid after each;
    and one undo of each puts the profile back whole."""
    draft, book, _, _ = _onboarding(world)
    _map_by_hand(world, draft, book)
    h = book.header
    _step(
        world,
        draft,
        {"kind": "addSource", "id": "categories", "sheet": workbooks.S1, "objectType": "j34-category", "key": {"attributeTypeKey": "j34-category-id"}},
        {"kind": "mapColumn", "source": "categories", "column": h("Pi"), "binding": {"attributeTypeKey": "j34-category-id"}},
        {"kind": "mapColumn", "source": "categories", "column": h("P"), "binding": {"field": "name"}},
        {"kind": "mapColumn", "source": "items", "column": h("Po"), "binding": {"attributeTypeKey": "j34-order"}},
        {"kind": "mapColumn", "source": "items", "column": h("X"), "binding": {"attributeTypeKey": "j34-supplier"}},
    )

    renamed = _followed(world, draft, {"kind": "setKey", "element": {"objectType": "j34-item"}, "key": "j34-article"})
    assert renamed["valid"] is True, renamed["diagnostics"]
    items = next(s for s in renamed["profile"]["sources"] if s["id"] == "items")
    assert items["objectTypeKey"] == "j34-article"

    rekeyed = _followed(world, draft, {"kind": "setKey", "element": {"attributeType": "j34-code"}, "key": "j34-article-code"})
    assert rekeyed["valid"] is True, rekeyed["diagnostics"]
    items = next(s for s in rekeyed["profile"]["sources"] if s["id"] == "items")
    assert items["key"] == {"attributeTypeKey": "j34-article-code"}
    assert _bindings(rekeyed["profile"], "items")[h("K")]["attributeTypeKey"] == "j34-article-code"

    moved = _followed(world, draft, {"kind": "moveAttribute", "attributeType": "j34-order", "from": "j34-article", "to": "j34-category"})
    assert moved["valid"] is True, moved["diagnostics"]
    assert h("Po") not in _bindings(moved["profile"], "items")
    assert _bindings(moved["profile"], "categories")[h("Po")] == {"column": h("Po"), "attributeTypeKey": "j34-order"}

    split = _followed(
        world,
        draft,
        {"kind": "splitObjectType", "objectType": "j34-article", "key": "j34-supply", "name": "Supply", "attributes": ["j34-supplier"], "relationType": {"name": "Supplied as", "reverseName": "Supply of", "key": "j34-supplied"}},
    )
    assert split["valid"] is True, split["diagnostics"]
    supply = next(s for s in split["profile"]["sources"] if s["objectTypeKey"] == "j34-supply")
    assert (supply["sheet"], supply["key"]) == (workbooks.S1, {"attributeTypeKey": "j34-supplier"})
    assert _bindings(split["profile"], supply["id"])[h("X")] == {"column": h("X"), "attributeTypeKey": "j34-supplier"}
    assert _bindings(split["profile"], "items")[h("X")]["relation"] == {
        "relationTypeKey": "j34-supplied",
        "objectTypeKey": "j34-supply",
        "matchBy": {"attributeTypeKey": "j34-supplier"},
    }

    merged = _followed(world, draft, {"kind": "mergeObjectTypes", "into": "j34-article", "from": "j34-supply"})
    assert merged["valid"] is True, merged["diagnostics"]
    assert {s["objectTypeKey"] for s in merged["profile"]["sources"]} == {"j34-article", "j34-category"}
    assert _bindings(merged["profile"], "items")[h("X")]["relation"]["objectTypeKey"] == "j34-article"


@pytest.mark.journey("J34.7")
@pytest.mark.structures("K")
def test_a_removed_attribute_leaves_its_column_unmapped_until_undone(world):
    """Given Po mapped to the items' order. When the order attribute is detached. Then its column is
    no longer bound, the profile keeps it as unmapped and the step warns COLUMN_UNMAPPED at it;
    after undo the column is mapped again and the warning is gone."""
    draft, book, _, _ = _onboarding(world)
    _map_by_hand(world, draft, book)
    _step(world, draft, {"kind": "mapColumn", "source": "items", "column": book.header("Po"), "binding": {"attributeTypeKey": "j34-order"}})

    answer = _step(world, draft, {"kind": "detachAttribute", "objectType": "j34-item", "attributeType": "j34-order"})
    unmapped = [d for d in answer["diagnostics"] if d["code"] == "COLUMN_UNMAPPED"]
    assert [d["path"] for d in unmapped] == ["/profile/unmapped/0"], answer["diagnostics"]
    profile = _draft_profile(world, draft)["profile"]
    assert book.header("Po") not in _bindings(profile, "items")
    (entry,) = profile["unmapped"]
    assert (entry["column"], entry["because"]) == (book.header("Po"), {"kind": "detachAttribute"})

    undone = ok(world.api.post(f"/model-drafts/{draft['id']}/undo", {"expectedVersion": _version(world, draft)}))
    assert not [d for d in undone["diagnostics"] if d["code"] == "COLUMN_UNMAPPED"]
    assert _bindings(_draft_profile(world, draft)["profile"], "items")[book.header("Po")]["attributeTypeKey"] == "j34-order"


@pytest.mark.journey("J34.3")
@pytest.mark.structures("K")
def test_a_step_that_can_change_the_load_queues_the_dry_run_and_a_label_does_not(world):
    """Given W1 mapped. When a step maps a column. Then its answer says the dry run is checking and
    the draft's latest dry run is of that version. When a step only changes a label. Then no dry
    run is queued (D79)."""
    draft, book, _, _ = _onboarding(world)
    _map_by_hand(world, draft, book)
    _run(world)
    answer = _step(world, draft, {"kind": "ignoreColumn", "source": "items", "column": book.header("Ln")})
    _summary_of(world, draft, answer)

    label = _step(world, draft, {"kind": "setLabel", "element": {"objectType": "j34-item"}, "name": "Article"})
    assert label["dryRun"] is None
    assert ok(world.api.get(f"/model-drafts/{draft['id']}/dry-run"))["draftVersion"] == answer["version"]


@pytest.mark.journey("J34.8")
@pytest.mark.structures("K")
def test_installing_saves_the_draft_profile_and_an_import_naming_it_loads_what_the_dry_run_counted(world):
    """Given W1 mapped and its dry run. When the draft is installed and activated. Then the
    installation saved an instance profile of the draft profile's key, checked against the new
    release; an import naming it and the draft's stored file into a change set creates the records
    the dry run counted."""
    draft, book, source, workspace = _onboarding(world)
    summary = _summary_of(world, draft, _map_by_hand(world, draft, book)[-1])
    figures = summary["sources"][0]
    profile_key = _draft_profile(world, draft)["profile"]["key"]

    release = _install(world, draft)
    assert release["importProfile"] == {"key": profile_key, "version": 1}
    stored = ok(world.api.get(f"/import-profiles/{profile_key}"))
    assert stored["checkedAgainst"] == release["id"]
    ok(world.activate(release["id"]))
    assert ok(world.api.get(f"/import-profiles/{profile_key}"))["valid"] is True

    change_set = world.change_set(workspace)
    request = {
        "changeSetId": change_set["id"],
        "expectedChangeSetVersion": change_set["version"],
        "profileKey": profile_key,
        "sourceFileId": source["id"],
        "policy": "independent",
        "onExisting": "overwrite",
        "stage": "execute",
    }
    job = ok(world.api.upload("/imports", {}, {"request": json.dumps(request)}), 202)
    _run(world)
    done = ok(world.api.get(f"/jobs/{job['id']}"))
    assert (done["state"], done["counts"]["rejected"]) == ("completed", 0), done
    assert done["counts"]["created"] == (
        figures["records"]["created"] + figures["relatedRecords"] + figures["relationships"]
    )


@pytest.mark.journey("J34.8")
@pytest.mark.structures("K")
def test_the_editor_loads_the_workbook_into_a_new_change_set_whose_review_lists_it_and_publishing_makes_it_live(world):
    """Given W1 mapped by hand and its dry run. When the editor's load runs its three calls (D81):
    the draft installed and activated, a change set named after the file, and the import of the
    stored file through the saved profile into it. Then the change set lists the records the dry
    run counted as added, nothing is live before publishing, and after publishing the records are
    the workspace's."""
    draft, book, source, workspace = _onboarding(world)
    figures = _summary_of(world, draft, _map_by_hand(world, draft, book)[-1])["sources"][0]

    release = _install(world, draft)
    ok(world.activate(release["id"]))
    change_set = world.change_set(workspace, name="Load catalogue.xlsx (2026-10-12)")
    request = {
        "changeSetId": change_set["id"],
        "expectedChangeSetVersion": change_set["version"],
        "profileKey": release["importProfile"]["key"],
        "sourceFileId": source["id"],
        "policy": "independent",
        "onExisting": "overwrite",
        "stage": "execute",
    }
    job = ok(world.api.upload("/imports", {}, {"request": json.dumps(request)}), 202)
    _run(world)
    assert ok(world.api.get(f"/jobs/{job['id']}"))["state"] == "completed"

    review = _all(world, f"/change-sets/{change_set['id']}/object-changes", objectTypeKey="j34-item")
    assert len(review) == figures["records"]["created"] == len(book.rows)
    assert {item["kind"] for item in review} == {"added"}
    live = ok(world.api.get("/objects/j34-item", workspaceKey=workspace, includeTotal=True))
    assert live["totalCount"] == 0

    world.publish(change_set, workspace)
    live = ok(world.api.get("/objects/j34-item", workspaceKey=workspace, includeTotal=True))
    assert live["totalCount"] == len(book.rows)


@pytest.mark.journey("J34.2")
@pytest.mark.structures("K")
def test_mapping_kinds_refuse_what_the_file_or_the_draft_lacks(world):
    """A mapping kind naming a column or a sheet the file lacks is INVALID_OPERATION
    (unknownElement), as is addSource on a draft without a source file; a stale version is
    VERSION_CONFLICT."""
    draft, book, _, _ = _onboarding(world)
    _map_by_hand(world, draft, book)

    def operation(*operations: dict[str, Any], version: int | None = None):
        body = {"expectedVersion": version or _version(world, draft), "operations": list(operations)}
        return world.api.post(f"/model-drafts/{draft['id']}/operations", body)

    column = refused(operation({"kind": "ignoreColumn", "source": "items", "column": "No such column"}), 422, "INVALID_OPERATION")
    assert (column["details"]["reason"], column["details"]["pointer"]) == ("unknownElement", "/operations/0/column")
    sheet = refused(operation({"kind": "addSource", "sheet": "No such sheet", "objectType": "j34-item"}), 422, "INVALID_OPERATION")
    assert sheet["details"]["reason"] == "unknownElement"
    refused(operation({"kind": "ignoreColumn", "source": "items", "column": book.header("X")}, version=1), 409, "VERSION_CONFLICT")

    empty = _draft(world)
    _catalogue(world, empty)
    bare = world.api.post(
        f"/model-drafts/{empty['id']}/operations",
        {"expectedVersion": _version(world, empty), "operations": [{"kind": "addSource", "sheet": workbooks.S1, "objectType": "j34-item"}]},
    )
    assert refused(bare, 422, "INVALID_OPERATION")["details"]["reason"] == "unknownElement"


@pytest.mark.journey("J27.8")
@pytest.mark.structures("K")
def test_an_import_creates_the_list_values_a_lookup_names_once_whatever_the_rows(world):
    """Given an inline profile whose relation column creates the list records it does not find
    (D77). When a file names one absent value on three rows and an existing one on another. Then
    the absent value is created once and every row relates to it; a column creating by an
    attribute match is refused CREATE_NEEDS_NAME_MATCH."""
    workspace = _workspace(world)
    draft = _draft(world)
    _catalogue(world, draft)
    _apply(world, draft, {"kind": "allowRelation", "relationType": "j34-made-of", "from": "j34-category", "to": "j34-material"})
    release = _install(world, draft)
    ok(world.activate(release["id"]))
    paper = {"workspaceKey": workspace, "applicationKey": world.app("K"), "objectTypeKey": "j34-material", "name": "Paper", "attributes": []}
    ok(world.api.post("/objects", paper), 201)

    def profile(match: dict[str, Any]) -> dict[str, Any]:
        return {
            "sources": [
                {
                    "applicationKey": world.app("K"),
                    "objectTypeKey": "j34-category",
                    "columns": [
                        {"column": "name", "field": "name"},
                        {"column": "material", "relation": {"relationTypeKey": "j34-made-of", "objectTypeKey": "j34-material", "matchBy": match, "missing": "create"}},
                    ],
                },
            ]
        }

    content = b"name,material\nA,Glossy\nB,Glossy\nC,Glossy\nD,Paper\n"
    request = {"workspaceKey": workspace, "policy": "independent", "stage": "execute", "profile": profile({"field": "name"})}
    job = ok(world.api.upload("/imports", {"file": ("lists.csv", content, "text/csv")}, {"request": json.dumps(request)}), 202)
    _run(world)
    done = ok(world.api.get(f"/jobs/{job['id']}"))
    rows = ok(world.api.get(f"/jobs/{job['id']}/rows", pageSize=10))["items"]
    assert (done["state"], done["counts"]["rejected"]) == ("completed", 0), rows
    names = [item["name"] for item in _all(world, "/objects/j34-material", workspaceKey=workspace)]
    assert sorted(names) == ["Glossy", "Paper"]
    assert done["counts"]["created"] == 4 + 1 + 4

    bad = {**request, "profile": profile({"attributeTypeKey": "j34-code"})}
    error = refused(world.api.upload("/imports", {"file": ("lists.csv", content, "text/csv")}, {"request": json.dumps(bad)}), 422, "INVALID_IMPORT_PROFILE")
    assert any(p["code"] == "CREATE_NEEDS_NAME_MATCH" for p in error["details"]["problems"]), error
