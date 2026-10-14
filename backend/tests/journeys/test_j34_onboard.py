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
        "valuesListed": 10,
    }
    # The most frequent values with their counts (0.10 A6).
    materials = {row["T"] for row in book.rows}
    frequent = column("T")["values"]
    assert len(frequent) == min(10, len(materials))
    assert frequent[0]["count"] == max(sum(row["T"] == value for row in book.rows) for value in materials)


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
    assert items["records"] == {"created": loaded, "updated": 0, "unchanged": 0, "deleted": 0}
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


# --- A6: inference over the table patterns (D86–D98) ---------------------------------------------

W1_PATTERNS = {
    "newApplication": (),
    "keyColumn": ("K", "N"),
    "repeatedParent": ("P", "Po", "Pi"),
    "textLookup": ("T",),
    "placeholders": ("T",),
    "codeAndName": ("Lc", "Ln"),
    "nameDrift": ("Lc", "Ln"),
    "flagColumns": ("F1", "F2", "Fo"),
    "externalId": ("X",),
    "translationsByRow": ("K", "Lang", "N"),
    "navigationGroup": (),
}


def _infer(world, draft: dict[str, Any], **body: Any) -> dict[str, Any]:
    """The draft's inference, run by the worker; its read once completed."""
    started = ok(world.api.post(f"/model-drafts/{draft['id']}/inference", {"mode": "newApplication", **body}), 202)
    assert started["state"] == "checking", started
    _run(world)
    done = ok(world.api.get(f"/model-drafts/{draft['id']}/inference"))
    assert (done["jobId"], done["state"]) == (started["jobId"], "completed"), done
    return done


def _proposals(world, draft: dict[str, Any]) -> list[dict[str, Any]]:
    return _all(world, f"/model-drafts/{draft['id']}/inference/proposals")


def _by_pattern(proposals: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    found: dict[str, dict[str, Any]] = {}
    for proposal in proposals:
        assert proposal["pattern"] not in found, proposal["pattern"]
        found[proposal["pattern"]] = proposal
    return found


def _application(world, draft: dict[str, Any], ids: list[str] | None = None, version: int | None = None):
    body: dict[str, Any] = {"expectedVersion": version or _version(world, draft)}
    if ids is not None:
        body["proposals"] = ids
    return world.api.post(f"/model-drafts/{draft['id']}/inference/application", body)


def _inferred(world) -> tuple[dict[str, Any], workbooks.W1, dict[str, Any], str]:
    """A draft of the active model with W1 profiled in a new workspace, and its inference run."""
    workspace = _workspace(world)
    draft = _draft(world)
    book = workbooks.w1(rows=200)
    source = _profiled(world, {"draftId": draft["id"]}, "catalogue.xlsx", book.content, workspaceKey=workspace)
    _infer(world, draft)
    return draft, book, source, workspace


def _created(entries: list[dict[str, Any]], proposals: dict[str, dict[str, Any]], pattern: str, kind: str) -> list[dict[str, Any]]:
    """The parameters of the ``kind`` operations the step of ``pattern``'s proposal applied."""
    wanted = proposals[pattern]["id"]
    return [e["parameters"] for e in entries if e["kind"] == kind and e["origin"].get("proposalId") == wanted]


def _total(world, type_key: str, workspace: str) -> int:
    return ok(world.api.get(f"/objects/{type_key}", workspaceKey=workspace, includeTotal=True, pageSize=1))["totalCount"]


@pytest.mark.journey("J34.4")
@pytest.mark.structures("K")
def test_the_inference_proposes_each_pattern_of_the_workbook_with_its_evidence_and_applies_nothing(world):
    """Given W1 profiled on a draft. When the inference runs in new-application mode. Then it lists
    the eleven proposals of W1's patterns, each with its columns and evidence; no proposal reads N
    as a key or lookup, X as a key or Po as a parent; and until applied the draft is unchanged."""
    workspace = _workspace(world)
    draft = _draft(world)
    book = workbooks.w1(rows=200)
    _profiled(world, {"draftId": draft["id"]}, "catalogue.xlsx", book.content, workspaceKey=workspace)
    version = _version(world, draft)
    history = _all(world, f"/model-drafts/{draft['id']}/operations")

    read = _infer(world, draft)
    assert read["mode"] == "newApplication" and read["draftVersion"] == version
    proposals = _by_pattern(_proposals(world, draft))
    assert set(proposals) == set(W1_PATTERNS)
    s2 = {"K": workbooks.S2_HEADERS["K"], "Lang": workbooks.S2_HEADERS["Lang"], "N": workbooks.S2_HEADERS["N"]}
    for pattern, structures in W1_PATTERNS.items():
        proposal = proposals[pattern]
        header = s2.__getitem__ if pattern == "translationsByRow" else book.header
        assert proposal["columns"] == [header(s) for s in structures], pattern
        assert proposal["status"] == "open" and proposal["operations"], pattern
        assert proposal["summary"], pattern
    assert proposals["translationsByRow"]["sheet"] == workbooks.S2
    assert proposals["keyColumn"]["sheet"] == workbooks.S1

    parent = proposals["repeatedParent"]["evidence"]
    assert parent["groups"] == len(book.distinct("P"))
    assert {d["column"]: d["constantIn"] for d in parent["dependents"]} == {
        book.header("Po"): parent["groups"],
        book.header("Pi"): parent["groups"],
    }
    pair = proposals["codeAndName"]["evidence"]
    names: dict[str, set[str]] = {}
    for row in book.rows:
        names.setdefault(row["Lc"], set()).add(row["Ln"])
    assert {d["code"] for d in pair["drift"]} == {code for code, found in names.items() if len(found) > 1}
    assert proposals["placeholders"]["evidence"]["placeholders"] and {
        p["value"] for p in proposals["placeholders"]["evidence"]["placeholders"]
    } == set(workbooks.PLACEHOLDERS)

    lookups = {c for p in proposals.values() if p["pattern"] in ("textLookup", "codeAndName", "repeatedParent") for c in p["columns"][:1]}
    assert book.header("N") not in lookups
    assert proposals["keyColumn"]["columns"][0] == book.header("K")
    assert book.header("X") not in proposals["keyColumn"]["columns"]
    assert proposals["repeatedParent"]["columns"][0] == book.header("P")
    assert _version(world, draft) == version
    assert _all(world, f"/model-drafts/{draft['id']}/operations") == history


def _empty_draft(world) -> dict[str, Any]:
    """A draft of an empty model, as the start dialog's A new model creates it."""
    schema = ok(world.api.get("/system"))["schemaLanguages"][-1]
    empty = {
        "schemaVersion": schema,
        "release": {"key": "workbook-only", "name": "Workbook only", "version": "1.0.0"},
        "product": {"name": "Workbook only"},
        "attributeTypes": [],
        "objectTypes": [],
        "relationTypes": [],
        "objectTypeRelations": [],
        "applications": [],
    }
    return ok(world.api.post("/model-drafts", {"name": "Workbook only", "model": empty}), 201)


@pytest.mark.journey("J34.4")
@pytest.mark.structures("K")
def test_a_new_application_on_an_empty_model_is_a_model_of_the_workbook_alone(world):
    """Given an empty model (the start dialog's Empty model) with W1 profiled. When the inference
    runs in new-application mode and every proposal is applied. Then the draft compiles to a model
    of the workbook's one application and its types, and nothing of the active model."""
    workspace = _workspace(world)
    draft = _empty_draft(world)
    book = workbooks.w1(rows=50)
    _profiled(world, {"draftId": draft["id"]}, "catalogue.xlsx", book.content, workspaceKey=workspace)
    _infer(world, draft)
    answer = ok(_application(world, draft))
    assert answer["valid"] is True, answer["diagnostics"]
    compiled = ok(world.api.post(f"/model-drafts/{draft['id']}/compile", {"expectedVersion": _version(world, draft)}))
    model = compiled["model"]
    assert len(model["applications"]) == 1, [a["key"] for a in model["applications"]]
    active = {t["key"] for t in world.configuration.model["objectTypes"]}
    assert model["objectTypes"] and not active & {t["key"] for t in model["objectTypes"]}
    assert _draft_profile(world, draft)["valid"] is True


@pytest.mark.journey("J34.4")
@pytest.mark.structures("K")
def test_a_workbook_of_real_shapes_gives_a_model_its_own_dry_run_takes_whole(world):
    """Given W4 (the shapes of the user's workbooks, 2026-10-14) profiled on an empty model. When
    the inference runs and every proposal is applied. Then the statuses are keyed by their GUID and
    named; the kinds have one parent, Category, optional for the rows without one, and Slot_Name is
    a list they refer to; Categoría and Kategorie translate Category by their values; North and South
    are one set; Definition is long text; the second Customer Name is left out with a warning; the
    names read as words; and the dry run refuses no row."""
    workspace = _workspace(world)
    draft = _empty_draft(world)
    book = workbooks.w4()
    _profiled(world, {"draftId": draft["id"]}, "kinds.xlsx", book.content, workspaceKey=workspace)
    read = _infer(world, draft)
    assert any("second column 'Customer Name'" in w for w in read["warnings"]), read["warnings"]
    proposals = _proposals(world, draft)
    by_sheet_pattern = {(p["sheet"], p["pattern"], tuple(p["columns"])) for p in proposals}
    assert ("Statuses", "keyColumn", ("Id", "Name")) in by_sheet_pattern
    assert ("Kinds", "translationsByColumn", ("Categoría", "Kategorie")) in by_sheet_pattern
    assert ("Kinds", "flagColumns", ("North", "South")) in by_sheet_pattern
    assert not [p for p in proposals if p["pattern"] == "repeatedParent" and p["columns"][0] == "Definition"]

    answer = ok(_application(world, draft))
    assert answer["valid"] is True, answer["diagnostics"]
    model = ok(world.api.post(f"/model-drafts/{draft['id']}/compile", {"expectedVersion": answer["version"]}))["model"]
    types = {t["name"]: t for t in model["objectTypes"]}
    assert {"Kind", "Status", "Category", "Slot Name", "Language", "Translation"} <= set(types), sorted(types)
    assert types["Kind"]["features"]["rootCreatable"] is True, "a kind without a category stands at the top"
    contained = [r for r in model["objectTypeRelations"] if r["toObjectTypeKey"] == types["Kind"]["key"]]
    assert len(contained) == 1, contained
    names = {a["name"]: a for a in model["attributeTypes"]}
    assert names["Definition"]["valueType"] == "longText"
    summary = _summary_of(world, draft, answer)
    assert all(s["rejections"] == [] for s in summary["sources"]), summary["sources"]
    kinds = next(s for s in summary["sources"] if s["objectTypeKey"] == types["Kind"]["key"])
    assert kinds["records"]["created"] == book.rows


@pytest.mark.journey("J34.4")
@pytest.mark.structures("K")
def test_the_applied_inference_loads_w1_into_a_change_set_that_publishes_every_record(world):
    """When every proposal is applied, each is one step of origin proposal, the draft and its
    profile are valid and the dry run refuses no row; installed, loaded into a change set and
    published, the workspace holds W1's parents, items, lists and translations."""
    draft, book, source, workspace = _inferred(world)
    proposals = _by_pattern(_proposals(world, draft))
    answer = ok(_application(world, draft))
    assert answer["valid"] is True, answer["diagnostics"]
    entries = answer["entries"]
    assert {e["origin"]["type"] for e in entries} == {"proposal"}
    assert len({e["step"] for e in entries}) == len(proposals)
    assert _draft_profile(world, draft)["valid"] is True
    summary = _summary_of(world, draft, answer)
    assert all(s["rejections"] == [] for s in summary["sources"]), summary["sources"]
    assert any(s["records"]["created"] == len(book.rows) for s in summary["sources"])
    assert {p["status"] for p in _proposals(world, draft)} == {"applied"}

    release = _install(world, draft)
    ok(world.activate(release["id"]))
    change_set = world.change_set(workspace)
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
    done = ok(world.api.get(f"/jobs/{job['id']}"))
    assert (done["state"], done["counts"]["rejected"]) == ("completed", 0), done
    world.publish(change_set, workspace)

    def key(pattern: str, top: bool = True) -> str:
        made = _created(entries, proposals, pattern, "addObjectType")
        return next(p["key"] for p in made if (p["parent"] is None) == top)

    majority: dict[str, dict[str, int]] = {}
    for row in book.rows:
        counts = majority.setdefault(row["Lc"], {})
        counts[row["Ln"]] = counts.get(row["Ln"], 0) + 1
    assert _total(world, key("repeatedParent"), workspace) == len(book.distinct("P"))
    assert _total(world, key("keyColumn"), workspace) == len(book.rows)
    assert _total(world, key("textLookup"), workspace) == len(book.distinct("T") - set(workbooks.PLACEHOLDERS))
    colours = ok(world.api.get(f"/objects/{key('codeAndName')}", workspaceKey=workspace, pageSize=50))["items"]
    assert sorted(c["name"] for c in colours) == sorted(max(n, key=n.get) for n in majority.values())
    features = {book.header("F1"), book.header("F2")} | {
        part.strip() for row in book.rows if row["Fo"] for part in row["Fo"].split(";")
    }
    assert _total(world, key("flagColumns"), workspace) == len(features)
    assert _total(world, key("translationsByRow"), workspace) == len(workbooks.LANGUAGES)
    assert _total(world, key("translationsByRow", top=False), workspace) == len(book.names)


@pytest.mark.journey("J34.4")
@pytest.mark.structures("K")
def test_an_applied_proposal_is_changed_by_the_editors_operations_and_becomes_the_administrators(world):
    """After applying: the text lookup's alternative maps T to a text attribute and removes its
    list; a renamed parent type keeps the profile valid; undoing the translations' step removes
    them and leaves S2 unmapped; what was changed is no longer listed as proposed."""
    draft, book, _, _ = _inferred(world)
    proposals = _by_pattern(_proposals(world, draft))
    entries = ok(_application(world, draft))["entries"]
    proposed = {item["element"] for item in ok(world.api.get(f"/model-drafts/{draft['id']}/inference"))["proposed"]}
    material = _created(entries, proposals, "textLookup", "addObjectType")[0]["key"]
    parent = _created(entries, proposals, "repeatedParent", "addObjectType")[0]["key"]
    assert {f"objectType:{material}", f"objectType:{parent}"} <= proposed

    lookup = proposals["textLookup"]
    alternative = _step(world, draft, *lookup["alternatives"][0]["operations"])
    assert alternative["valid"] is True, alternative["diagnostics"]
    model = ok(world.api.get(f"/model-drafts/{draft['id']}/model"))["model"]
    assert material not in {t["key"] for t in model["objectTypes"]}
    items = next(s for s in _draft_profile(world, draft)["profile"]["sources"] if s["sheet"] == workbooks.S1 and any(b.get("column") == book.header("K") for b in s["columns"]))
    assert "attributeTypeKey" in _bindings(_draft_profile(world, draft)["profile"], items["id"])[book.header("T")]

    renamed = _step(world, draft, {"kind": "setLabel", "element": {"objectType": parent}, "name": "Product group"})
    assert renamed["valid"] is True
    translations = next(e["step"] for e in entries if e["origin"].get("proposalId") == proposals["translationsByRow"]["id"])
    ok(world.api.post(f"/model-drafts/{draft['id']}/undo", {"expectedVersion": _version(world, draft), "step": translations}))
    profile = _draft_profile(world, draft)
    assert profile["valid"] is True, profile["diagnostics"]
    assert not any(s["sheet"] == workbooks.S2 for s in profile["profile"]["sources"])

    after = ok(world.api.get(f"/model-drafts/{draft['id']}/inference"))
    still = {item["element"] for item in after["proposed"]}
    assert f"objectType:{parent}" not in still
    assert f"objectType:{material}" not in still
    colour = _created(entries, proposals, "codeAndName", "addObjectType")[0]["key"]
    assert f"objectType:{colour}" in still
    assert next(p for p in _proposals(world, draft) if p["pattern"] == "translationsByRow")["status"] == "open"


@pytest.mark.journey("J34.4")
@pytest.mark.structures("K")
def test_proposals_are_applied_with_what_they_require_and_refused_otherwise(world):
    """A proposal without the one it requires is PROPOSAL_REQUIREMENT_MISSING; both together
    apply in order; an unknown proposal is PROPOSAL_NOT_FOUND; a stale version VERSION_CONFLICT;
    an inference on a file still profiling SOURCE_FILE_PROFILE_NOT_READY, without a file
    SOURCE_FILE_NOT_FOUND."""
    draft, _, _, _ = _inferred(world)
    proposals = _by_pattern(_proposals(world, draft))
    missing = refused(_application(world, draft, [proposals["keyColumn"]["id"]]), 422, "PROPOSAL_REQUIREMENT_MISSING")
    assert missing["details"]["requirement"] == proposals["newApplication"]["id"]
    both = ok(_application(world, draft, [proposals["keyColumn"]["id"], proposals["newApplication"]["id"]]))
    order = sorted({(e["step"], e["origin"]["proposalId"]) for e in both["entries"]})
    assert [proposal for _, proposal in order] == [proposals["newApplication"]["id"], proposals["keyColumn"]["id"]]
    refused(_application(world, draft, [str(uuid4())]), 404, "PROPOSAL_NOT_FOUND")
    refused(_application(world, draft, [proposals["externalId"]["id"]], version=1), 409, "VERSION_CONFLICT")

    waiting = _draft(world)
    ok(_upload(world, {"draftId": waiting["id"]}, "catalogue.xlsx", workbooks.w1(rows=20).content), 201)
    refused(world.api.post(f"/model-drafts/{waiting['id']}/inference", {"mode": "newApplication"}), 409, "SOURCE_FILE_PROFILE_NOT_READY")
    _run(world)
    bare = _draft(world)
    refused(world.api.post(f"/model-drafts/{bare['id']}/inference", {"mode": "newApplication"}), 404, "SOURCE_FILE_NOT_FOUND")


@pytest.mark.journey("J34.5")
@pytest.mark.structures("K")
def test_extending_the_active_model_maps_columns_onto_what_exists_and_adds_no_duplicate(world):
    """Given an active model with a type named as S1 binding a unique attribute named as K's
    header, an unbound attribute type named as X's, and a list type whose records are named as T's
    values. When the inference runs in extend mode and is applied. Then S1 loads that type, K and
    X map to those attributes, T relates to that list, and nothing is added twice."""
    workspace = _workspace(world)
    book = workbooks.w1(rows=200)
    first = _draft(world)
    app = world.app("K")
    _apply(
        world,
        first,
        {"kind": "addObjectType", "applicationKey": app, "key": "j34-item", "name": "Item", "pluralName": workbooks.S1, "parent": None},
        {"kind": "addAttributeType", "key": "j34-code", "name": book.header("K"), "valueType": "text", "features": {"unique": True}},
        {"kind": "attachAttribute", "objectType": "j34-item", "attributeType": "j34-code"},
        {"kind": "addAttributeType", "key": "j34-supplier", "name": book.header("X"), "valueType": "text", "features": {"unique": True}},
        {"kind": "addObjectType", "applicationKey": app, "key": "j34-substance", "name": "Substance", "pluralName": "Substances", "parent": None},
    )
    release = _install(world, first)
    ok(world.activate(release["id"]))
    for name in sorted(book.distinct("T") - set(workbooks.PLACEHOLDERS)):
        body = {"workspaceKey": workspace, "applicationKey": app, "objectTypeKey": "j34-substance", "name": name, "attributes": []}
        ok(world.api.post("/objects", body), 201)

    draft = _draft(world)
    _profiled(world, {"draftId": draft["id"]}, "catalogue.xlsx", book.content, workspaceKey=workspace)
    _infer(world, draft, mode="extend")
    answer = ok(_application(world, draft))
    assert answer["valid"] is True, answer["diagnostics"]
    profile = _draft_profile(world, draft)["profile"]
    items = next(s for s in profile["sources"] if s["sheet"] == workbooks.S1 and s["objectTypeKey"] == "j34-item")
    bound = _bindings(profile, items["id"])
    assert bound[book.header("K")]["attributeTypeKey"] == "j34-code"
    assert bound[book.header("X")]["attributeTypeKey"] == "j34-supplier"
    assert bound[book.header("T")]["relation"]["objectTypeKey"] == "j34-substance"
    model = ok(world.api.get(f"/model-drafts/{draft['id']}/model"))["model"]
    item = next(t for t in model["objectTypes"] if t["key"] == "j34-item")
    assert "j34-supplier" in {b["attributeTypeKey"] for b in item["attributes"]}
    headers = set(book.headers.values())
    names = [a["name"] for a in model["attributeTypes"] if a["name"] in headers]
    assert len(names) == len(set(names)), names
    assert book.header("T") not in {t["name"] for t in model["objectTypes"]}


@pytest.mark.journey("J34.5")
@pytest.mark.structures("K")
def test_extending_relates_an_id_column_to_the_records_already_holding_its_values(world):
    """D96 (added in A6a beside the approved cases, to cover the decision): given an active model
    with a type under a parent type holding a unique attribute, and records of it under one parent
    record holding W1's X values, when the inference runs in extend mode and is applied, then X
    relates each item to the record holding its value, matched by the attribute, and the dry run
    refuses no row."""
    workspace = _workspace(world)
    book = workbooks.w1(rows=60)
    app = world.app("K")
    first = _draft(world)
    _apply(
        world,
        first,
        {"kind": "addObjectType", "applicationKey": app, "key": "j34-system", "name": "System", "pluralName": "Systems", "parent": None},
        {
            "kind": "addObjectType",
            "applicationKey": app,
            "key": "j34-mapping",
            "name": "Mapping",
            "pluralName": "Mappings",
            "parent": {"objectTypes": ["j34-system"], "relationType": {"name": "Holds", "reverseName": "Held by", "key": "j34-system-holds"}},
        },
        {"kind": "addAttributeType", "key": "j34-external", "name": "External ID", "valueType": "text", "features": {"unique": True}},
        {"kind": "attachAttribute", "objectType": "j34-mapping", "attributeType": "j34-external"},
    )
    release = _install(world, first)
    ok(world.activate(release["id"]))
    system = str(uuid4())
    items = [{"op": "create", "id": system, "applicationKey": app, "objectTypeKey": "j34-system", "name": "Supplier system", "attributes": []}]
    items += [
        {
            "op": "create",
            "applicationKey": app,
            "objectTypeKey": "j34-mapping",
            "name": value,
            "parent": {"id": system},
            "attributes": [{"attributeTypeKey": "j34-external", "value": value}],
        }
        for value in sorted(book.distinct("X"))
    ]
    result = ok(world.api.post("/batches", {"workspaceKey": workspace, "policy": "atomic", "run": "inline", "items": items}))
    assert result["job"]["result"] == "applied", result["job"]

    draft = _draft(world)
    _profiled(world, {"draftId": draft["id"]}, "catalogue.xlsx", book.content, workspaceKey=workspace)
    _infer(world, draft, mode="extend")
    external = _by_pattern(_proposals(world, draft))["externalId"]
    answer = ok(_application(world, draft))
    assert answer["valid"] is True, answer["diagnostics"]
    profile = _draft_profile(world, draft)["profile"]
    items_source = next(s for s in profile["sources"] if any(b.get("column") == book.header("K") for b in s["columns"]) and s.get("key"))
    relation = _bindings(profile, items_source["id"])[book.header("X")]["relation"]
    assert (relation["objectTypeKey"], relation["matchBy"]) == ("j34-mapping", {"attributeTypeKey": "j34-external"})
    assert external["columns"] == [book.header("X")] and "Supplier system" in external["summary"]
    summary = _summary_of(world, draft, answer)
    assert all(s["rejections"] == [] for s in summary["sources"]), summary["sources"]


@pytest.mark.journey("J34.6")
@pytest.mark.structures("K")
def test_proposing_again_follows_the_engines_proposals_and_leaves_the_administrators_decisions(world):
    """After applying, taking T's alternative, renaming the parent type and undoing the
    translations, W1′ is uploaded and the inference runs and is applied again: the new column Y is
    mapped by a proposal step; the colour name binding, still the engine's, follows Ln's new
    header; T keeps its attribute with one INFERENCE_DISAGREES naming the step that decided it;
    the parent type keeps its name; the translations are not applied again."""
    draft, book, _, workspace = _inferred(world)
    proposals = _by_pattern(_proposals(world, draft))
    entries = ok(_application(world, draft))["entries"]
    decided = _step(world, draft, *proposals["textLookup"]["alternatives"][0]["operations"])["entries"][0]["step"]
    parent = _created(entries, proposals, "repeatedParent", "addObjectType")[0]["key"]
    _step(world, draft, {"kind": "setLabel", "element": {"objectType": parent}, "name": "Product group"})
    translations = next(e["step"] for e in entries if e["origin"].get("proposalId") == proposals["translationsByRow"]["id"])
    ok(world.api.post(f"/model-drafts/{draft['id']}/undo", {"expectedVersion": _version(world, draft), "step": translations}))

    newer = workbooks.w1_next(rows=200)
    _profiled(world, {"draftId": draft["id"]}, "catalogue-v2.xlsx", newer.content, workspaceKey=workspace)
    read = _infer(world, draft)
    (disagreement,) = read["disagreements"]
    assert (disagreement["column"], disagreement["step"]) == (newer.header("T"), decided)
    again = _by_pattern(_proposals(world, draft))
    assert again["translationsByRow"]["status"] == "rejected"
    answer = ok(_application(world, draft))
    assert answer["valid"] is True, answer["diagnostics"]
    assert {e["origin"]["type"] for e in answer["entries"]} == {"proposal"}

    profile = _draft_profile(world, draft)
    items = next(s for s in profile["profile"]["sources"] if any(b.get("column") == newer.header("K") for b in s["columns"]) and s.get("key"))
    assert newer.header("Y") in _bindings(profile["profile"], items["id"])
    assert "attributeTypeKey" in _bindings(profile["profile"], items["id"])[newer.header("T")]
    colour = _created(entries, proposals, "codeAndName", "addObjectType")[0]["key"]
    colours = next(s for s in profile["profile"]["sources"] if s["objectTypeKey"] == colour)
    columns = _bindings(profile["profile"], colours["id"])
    assert columns[newer.header("Ln")].get("field") == "name"
    assert book.header("Ln") not in columns
    assert not any(s["sheet"] == workbooks.S2 for s in profile["profile"]["sources"])
    model = ok(world.api.get(f"/model-drafts/{draft['id']}/model"))["model"]
    assert next(t for t in model["objectTypes"] if t["key"] == parent)["name"] == "Product group"
    warnings = {d["code"] for d in profile["diagnostics"]}
    assert "INFERENCE_DISAGREES" in warnings


@pytest.mark.journey("J27.8")
@pytest.mark.structures("K")
def test_an_import_creates_the_parents_of_related_records_and_the_records_flags_stand_for(world):
    """Given an inline profile whose translation column creates the language it names and whose
    flag columns create the records they stand for (D93). When W1 is imported. Then each language
    and each flag record is created once, with every translation and flagged relationship."""
    workspace = _workspace(world)
    book = workbooks.w1(rows=40)
    app = world.app("K")
    draft = _draft(world)
    _apply(
        world,
        draft,
        {"kind": "addObjectType", "applicationKey": app, "key": "j34-item", "name": "Item", "pluralName": "Items", "parent": None},
        {"kind": "addAttributeType", "key": "j34-code", "name": "Item code", "valueType": "text", "features": {"unique": True}},
        {"kind": "attachAttribute", "objectType": "j34-item", "attributeType": "j34-code"},
        {"kind": "addObjectType", "applicationKey": app, "key": "j34-language", "name": "Language", "pluralName": "Languages", "parent": None},
        {
            "kind": "addObjectType",
            "applicationKey": app,
            "key": "j34-translation",
            "name": "Translation",
            "pluralName": "Translations",
            "parent": {"objectTypes": ["j34-language"], "relationType": {"name": "Contains", "reverseName": "In", "key": "j34-language-contains"}},
        },
        {"kind": "addRelationType", "key": "j34-translated", "name": "Has translation", "reverseName": "Translation of"},
        {"kind": "allowRelation", "relationType": "j34-translated", "from": "j34-item", "to": "j34-translation", "cardinality": "one-to-many"},
        {"kind": "addObjectType", "applicationKey": app, "key": "j34-feature", "name": "Feature", "pluralName": "Features", "parent": None},
        {"kind": "addRelationType", "key": "j34-has-feature", "name": "Has feature", "reverseName": "Feature of"},
        {"kind": "allowRelation", "relationType": "j34-has-feature", "from": "j34-item", "to": "j34-feature"},
    )
    release = _install(world, draft)
    ok(world.activate(release["id"]))
    h = book.header
    s2 = workbooks.S2_HEADERS
    profile = {
        "sources": [
            {
                "sheet": workbooks.S1,
                "applicationKey": app,
                "objectTypeKey": "j34-item",
                "key": {"attributeTypeKey": "j34-code"},
                "columns": [
                    {"column": h("K"), "attributeTypeKey": "j34-code"},
                    {"column": h("N"), "field": "name"},
                    {
                        "columns": [h("F1"), h("F2")],
                        "relationFlags": {
                            "relationTypeKey": "j34-has-feature",
                            "objectTypeKey": "j34-feature",
                            "matchBy": {"field": "name"},
                            "targets": {h("F1"): h("F1"), h("F2"): h("F2")},
                            "missing": "create",
                        },
                    },
                ],
            },
            {
                "sheet": workbooks.S2,
                "applicationKey": app,
                "objectTypeKey": "j34-item",
                "record": "existing",
                "key": {"attributeTypeKey": "j34-code"},
                "columns": [
                    {"column": s2["K"], "attributeTypeKey": "j34-code"},
                    {
                        "column": s2["N"],
                        "relatedRecord": {
                            "relationTypeKey": "j34-translated",
                            "applicationKey": app,
                            "objectTypeKey": "j34-translation",
                            "parent": {"objectTypeKey": "j34-language", "matchBy": {"field": "name"}, "column": s2["Lang"], "missing": "create"},
                            "field": "name",
                        },
                    },
                ],
            },
        ]
    }
    request = {"workspaceKey": workspace, "profile": profile, "policy": "independent", "onExisting": "overwrite", "stage": "execute"}
    job = ok(world.api.upload("/imports", {"file": ("catalogue.xlsx", book.content, XLSX)}, {"request": json.dumps(request)}), 202)
    _run(world)
    done = ok(world.api.get(f"/jobs/{job['id']}"))
    assert (done["state"], done["counts"]["rejected"]) == ("completed", 0), done
    assert _total(world, "j34-language", workspace) == len(workbooks.LANGUAGES)
    assert _total(world, "j34-translation", workspace) == len(book.names)
    flagged = {h(f) for f in ("F1", "F2") if any(row[f] == "Y" for row in book.rows)}
    assert _total(world, "j34-feature", workspace) == len(flagged)


@pytest.mark.journey("J34.6")
@pytest.mark.structures("K")
def test_proposing_again_on_the_same_workbook_applies_nothing(world):
    """Regression (A6b's browser runner): proposing again on the unchanged workbook after an
    alternative taken left the name drift's value map in place and offered nothing; it used to
    re-apply the colour list's name binding, dropping the drift's value map, and the dry run then
    refused the rows of the drifting names."""
    draft, _, _, _ = _inferred(world)
    proposals = _by_pattern(_proposals(world, draft))
    _summary_of(world, draft, ok(_application(world, draft)))
    _step(world, draft, *proposals["textLookup"]["alternatives"][0]["operations"])
    again = _infer(world, draft)
    assert again["counts"]["open"] == 0, [p for p in _proposals(world, draft) if p["status"] == "open"]
    refused(_application(world, draft), 409, "NOTHING_TO_APPLY")


@pytest.mark.journey("J34.4")
@pytest.mark.structures("K")
def test_a_workbook_with_nothing_to_propose_leaves_the_draft_as_it_was(world):
    """Regression (reported on a real workbook, 2026-10-14): when every sheet is laid out for
    reading, the inference proposes nothing, says why, and applying is NOTHING_TO_APPLY; it used to
    propose the new application alone, and applying it left the draft refusing an application
    without types."""
    workspace = _workspace(world)
    draft = _draft(world)
    _profiled(world, {"draftId": draft["id"]}, "lists.xlsx", workbooks.w3().content, workspaceKey=workspace)
    read = _infer(world, draft)
    assert read["counts"] == {"open": 0, "applied": 0, "held": 0, "rejected": 0}
    assert any("laid out for reading" in warning for warning in read["warnings"])
    assert any("nothing is proposed" in warning for warning in read["warnings"])
    assert _proposals(world, draft) == []
    refused(_application(world, draft), 409, "NOTHING_TO_APPLY")
    assert ok(world.api.get(f"/model-drafts/{draft['id']}/outline"))["valid"] is True


@pytest.mark.journey("J34.4")
@pytest.mark.structures("K")
def test_a_table_with_a_note_beside_it_is_read_by_the_table(world):
    """Reported on a real workbook (2026-10-14): a sheet whose table has a small block beside it
    proposed nothing. Given W1 with a two-column note block right of S1's table, the inference reads
    S1 by its table, names the note block in its warnings, every source on S1 loads from the table's
    block, and the applied draft's dry run refuses no row."""
    import io

    from openpyxl import load_workbook

    book = workbooks.w1(rows=200)
    sheet_book = load_workbook(io.BytesIO(book.content))
    sheet = sheet_book[workbooks.S1]
    last = len(book.headers)
    sheet.cell(row=2, column=last + 2, value="Note")
    sheet.cell(row=2, column=last + 3, value="By")
    for row in range(3, 23):
        sheet.cell(row=row, column=last + 2, value=f"checked {row}")
        sheet.cell(row=row, column=last + 3, value="desk")
    content = io.BytesIO()
    sheet_book.save(content)

    workspace = _workspace(world)
    draft = _draft(world)
    _profiled(world, {"draftId": draft["id"]}, "catalogue.xlsx", content.getvalue(), workspaceKey=workspace)
    read = _infer(world, draft)
    assert any(f"Sheet '{workbooks.S1}' is read by its table" in warning for warning in read["warnings"])
    proposals = _by_pattern(_proposals(world, draft))
    assert proposals["keyColumn"]["columns"][0] == book.header("K")
    answer = ok(_application(world, draft))
    profile = _draft_profile(world, draft)["profile"]
    on_sheet = [s for s in profile["sources"] if s["sheet"] == workbooks.S1]
    assert on_sheet and all(s.get("block", {}).get("lastColumn") == "L" for s in on_sheet), on_sheet
    summary = _summary_of(world, draft, answer)
    assert all(s["rejections"] == [] for s in summary["sources"]), summary["sources"]
