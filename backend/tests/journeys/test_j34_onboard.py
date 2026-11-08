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
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import uuid4

import pytest
import workbooks
from scenario import ok, refused
from sqlalchemy import text

from app.db import SessionLocal

XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
TYPES = {"xlsx": XLSX, "csv": "text/csv", "xls": "application/vnd.ms-excel"}


def _run(world) -> int:
    return world.api.client.app.state.job_worker.run_until_idle()


def _workspace(world) -> str:
    key = f"onboard-{uuid4().hex[:8]}"
    ok(world.api.post("/workspaces", {"key": key, "label": "Onboarding"}), 201)
    return key


def _draft(world) -> dict[str, Any]:
    active = world.workspace_model()["releaseId"]
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
        "block": None,
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
    list is a block with its range and header row, separated by its empty columns, and the
    section and group rows are not taken for columns. (Since 0.10 A8 W3 has a second band below the
    first, read as blocks of their own: J34.10.)"""
    draft = _draft(world)
    book = workbooks.w3()
    source = _profiled(world, {"draftId": draft["id"]}, "lists.xlsx", book.content)
    (sheet,) = ok(world.api.get(f"/source-files/{source['id']}/profile/sheets"))["items"]
    assert sheet["name"] == book.sheet and sheet["headerRow"] == book.header_row
    first_band = [b for b in book.blocks if b["headerRow"] == book.header_row]
    found = [b for b in sheet["blocks"] if b["headerRow"] == book.header_row]
    assert len(found) == len(first_band)
    for block, made in zip(found, first_band, strict=True):
        assert (block["firstColumn"], block["lastColumn"]) == (_letter(made["first"]), _letter(made["last"]))
        assert block["lastRow"] == made["lastRow"]
    columns = _all(world, f"/source-files/{source['id']}/profile/sheets/{book.sheet}/columns")
    heads = {(c["letter"], c["block"]): c["header"] for c in columns}
    indexes = {(b["firstColumn"], b["headerRow"]): i for i, b in enumerate(sheet["blocks"])}
    assert [heads[(_letter(m["first"]), indexes[(_letter(m["first"]), m["headerRow"])])] for m in first_band] == [m["title"] for m in first_band]


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
    """Given W1 above 1,000 rows. When a dry run is sent and the draft takes a step that can change
    the load before it runs, it stops as cancelled; a dry run sent before a step that cannot (a
    rename, D79) runs to its end (0.10 R); the next one reports every row of the new version; and
    the workspace's records and feed are unchanged."""
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
    kept = ok(world.api.post(f"/model-drafts/{draft['id']}/dry-run", body), 202)
    _apply(world, draft, {"kind": "setLabel", "element": {"objectType": keys["type"]}, "name": "Article"})
    _run(world)
    finished = ok(world.api.get(f"/model-drafts/{draft['id']}/dry-run"))
    assert (finished["jobId"], finished["state"]) == (kept["jobId"], "completed")

    stale = ok(world.api.post(f"/model-drafts/{draft['id']}/dry-run", body), 202)
    _apply(world, draft, {"kind": "addAttributeType", "key": "j34-later", "name": "Later", "valueType": "text"})
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
    ok(world.activate_everywhere(release["id"]))
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
    ok(world.activate_everywhere(release["id"]))
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
    ok(world.activate_everywhere(release["id"]))
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
    ok(world.activate_everywhere(release["id"]))
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
    ok(world.activate_everywhere(release["id"]))
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
    ok(world.activate_everywhere(release["id"]))
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
    ok(world.activate_everywhere(release["id"]))
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
    """Regression (reported on a real workbook, 2026-10-14): when no sheet shows a shape to
    propose from, the inference proposes nothing, says why, and applying is NOTHING_TO_APPLY; it
    used to propose the new application alone, and applying it left the draft refusing an
    application without types. (W3 served here until 0.10 A8 made its lists proposable; a sheet of
    headers with nothing under them stands in.)"""
    from openpyxl import Workbook

    book = Workbook()
    sheet = book.active
    sheet.title = "Headings"
    for column, (first, second) in enumerate((("Size", "Taille"), ("Kind", "Sorte"), ("Shape", "Forme")), start=1):
        sheet.cell(row=1, column=column * 3 - 2, value=first)
        sheet.cell(row=1, column=column * 3 - 1, value=second)
    workspace = _workspace(world)
    draft = _draft(world)
    _profiled(world, {"draftId": draft["id"]}, "headings.xlsx", workbooks._save(book), workspaceKey=workspace)
    read = _infer(world, draft)
    assert read["counts"] == {"open": 0, "applied": 0, "held": 0, "rejected": 0}
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


# --- A7: model-description sheets and matching across files (D106–D113) ------------------------


def _load(world, draft: dict[str, Any], source: dict[str, Any], workspace: str) -> dict[str, Any]:
    """The draft installed and activated, its saved profile loading the file into a change set
    that is then published; the import job."""
    release = _install(world, draft)
    ok(world.activate_everywhere(release["id"]))
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
    return done


def _described(proposals: list[dict[str, Any]]) -> dict[str, Any]:
    """W2's proposals by role: the description, its lists by sheet (the flag target's under its
    evidence's target), its fields and flag sets, and the keys their operations add."""
    found: dict[str, Any] = {"lists": {}, "fields": [], "flags": [], "types": {}}
    for proposal in proposals:
        pattern = proposal["pattern"]
        if pattern == "modelDescription":
            assert "description" not in found
            found["description"] = proposal
        elif pattern == "describedList":
            found["lists"][proposal["evidence"]["target"]] = proposal
        elif pattern == "describedField":
            found["fields"].append(proposal)
        elif pattern == "describedFlags":
            found["flags"].append(proposal)
        for operation in proposal["operations"]:
            if operation["kind"] == "addObjectType":
                found["types"][proposal["id"]] = operation["key"]
    return found


def _relations_from(proposals: list[dict[str, Any]], type_key: str) -> list[str]:
    """The types the proposals allow a relation to from ``type_key``."""
    return [
        o["to"] for p in proposals for o in p["operations"] if o["kind"] == "allowRelation" and o["from"] == type_key
    ]


def _w2_draft(world) -> tuple[dict[str, Any], workbooks.W2, dict[str, Any], str]:
    workspace = _workspace(world)
    draft = _draft(world)
    book = workbooks.w2(rows=200)
    source = _profiled(world, {"draftId": draft["id"]}, "described.xlsx", book.content, workspaceKey=workspace)
    return draft, book, source, workspace


@pytest.mark.journey("J34.9")
@pytest.mark.structures("K")
def test_a_model_description_is_read_before_the_lists_it_names(world):
    """Given W2 profiled on a draft. When the inference runs in new-application mode. Then one
    modelDescription names D's three columns with its evidence; the described type relates to two
    lists by lookups, to a flag set's list and to the list to be defined; the two list sheets are
    sources of their lists keyed by their ID; no proposal reads D or a list sheet as a row type; the
    list to be defined has no source and one warning."""
    draft, book, _, _ = _w2_draft(world)
    read = _infer(world, draft)
    proposals = _proposals(world, draft)
    described = _described(proposals)
    description = described["description"]
    assert description["sheet"] == book.description
    assert description["columns"] == [book.headers[s] for s in ("F", "Ty", "Tg")]
    evidence = description["evidence"]
    targets = {t for _, _, t in book.fields}
    assert (evidence["fields"], evidence["targets"]) == (len(book.fields), len(targets))
    assert sorted(evidence["sheets"]) == sorted([*book.lists, book.undefined])
    assert {w["value"] for w in evidence["typeWords"]} == {kind for _, kind, _ in book.fields}

    described_type = described["types"][description["id"]]
    lists = {target: described["types"][p["id"]] for target, p in described["lists"].items()}
    assert set(lists) == targets
    related = _relations_from(proposals, described_type)
    assert sorted(related) == sorted([lists[t] for t in book.lookups().values()] + [lists[book.flags]])
    for sheet in book.lists:
        (added,) = [o for o in described["lists"][sheet]["operations"] if o["kind"] == "addSource"]
        assert (added["sheet"], added["objectType"]) == (sheet, lists[sheet])
        assert "attributeTypeKey" in added["key"]
    undefined = described["lists"][book.undefined]
    assert not [o for o in undefined["operations"] if o["kind"] == "addSource"]
    assert undefined["evidence"]["toBeDefined"] is True
    assert len([w for w in read["warnings"] if book.undefined in w and "to be defined" in w]) == 1
    row_patterns = ("keyColumn", "repeatedParent", "textLookup", "codeAndName", "attribute")
    read_as_rows = [p for p in proposals if p["pattern"] in row_patterns and p["sheet"] in (book.description, *book.lists)]
    assert read_as_rows == []


def _w2_loaded(world) -> tuple[workbooks.W2, dict[str, Any], str, dict[str, Any]]:
    """W2's proposals applied, installed, loaded and published; the book, its proposals by role,
    the workspace and the dry run's summary before the load."""
    draft, book, source, workspace = _w2_draft(world)
    _infer(world, draft)
    described = _described(_proposals(world, draft))
    answer = ok(_application(world, draft))
    assert answer["valid"] is True, answer["diagnostics"]
    summary = _summary_of(world, draft, answer)
    _load(world, draft, source, workspace)
    return book, described, workspace, summary


@pytest.mark.journey("J34.9")
@pytest.mark.structures("K")
def test_the_description_and_its_lists_load_without_their_placeholders(world):
    """When W2's proposals are applied, the dry run refuses no row and skips one (the placeholder
    ID); installed, loaded into a change set and published, the lists hold the IDs W2 lists without
    the placeholder, the list to be defined holds nothing, and no record is named by a placeholder."""
    book, described, workspace, summary = _w2_loaded(world)
    assert all(s["rejections"] == [] for s in summary["sources"]), summary["sources"]
    assert sum(s["skippedRows"] for s in summary["sources"]) == 1
    lists = {target: described["types"][p["id"]] for target, p in described["lists"].items()}
    for sheet, rows in book.lists.items():
        names = sorted(item["name"] for item in _all(world, f"/objects/{lists[sheet]}", workspaceKey=workspace))
        assert names == sorted(name for _, name in rows), sheet
        assert book.placeholder[1] not in names
    assert _total(world, lists[book.undefined], workspace) == 0


@pytest.mark.journey("J34.9")
@pytest.mark.structures("K")
def test_a_flat_table_onto_the_described_model_matches_by_id_and_reports_what_differs(world):
    """Given W2 loaded and published. When W1 is uploaded to a new draft of the active model and
    the inference runs in extend mode. Then S1 maps to the described type; Lc relates to the colours
    by their ID and Ln is not mapped, with drift for each code whose names differ from the stored
    one; T relates to the materials by name, the materials W2 lacks listed as missing with their
    rows; F1 and F2 are flags of the flag set's list; no type name appears twice. Applied, the dry
    run refuses exactly the rows naming a missing material; with Create them on load, none."""
    book2, described, workspace, _ = _w2_loaded(world)
    lists = {target: described["types"][p["id"]] for target, p in described["lists"].items()}
    described_type = described["types"][described["description"]["id"]]
    draft = _draft(world)
    book = workbooks.w1(rows=200)
    _profiled(world, {"draftId": draft["id"]}, "catalogue.xlsx", book.content, workspaceKey=workspace)
    _infer(world, draft, mode="extend")
    proposals = _proposals(world, draft)
    by_pattern = {p["pattern"]: p for p in proposals if p["sheet"] == workbooks.S1}

    stored = dict(book2.lists["Colours"])
    names: dict[str, set[str]] = {}
    for row in book.rows:
        names.setdefault(row["Lc"], set()).add(row["Ln"])
    drifting = {code for code, found in names.items() if found != {stored[code]}}
    pair = by_pattern["codeAndName"]
    assert {d["code"] for d in pair["evidence"]["drift"]} == drifting
    assert "nameDrift" not in by_pattern
    materials = {name for _, name in book2.lists["Materials"]}
    missing = {}
    for row in book.rows:
        if row["T"] not in materials and row["T"] not in workbooks.PLACEHOLDERS:
            missing[row["T"]] = missing.get(row["T"], 0) + 1
    lookup = by_pattern["textLookup"]
    assert {m["value"]: m["rows"] for m in lookup["evidence"]["missing"]} == missing

    answer = ok(_application(world, draft))
    assert answer["valid"] is True, answer["diagnostics"]
    profile = _draft_profile(world, draft)["profile"]
    items = next(s for s in profile["sources"] if s["sheet"] == workbooks.S1 and s.get("key"))
    assert items["objectTypeKey"] == described_type
    bound = _bindings(profile, items["id"])
    colour = bound[book.header("Lc")]["relation"]
    assert colour["objectTypeKey"] == lists["Colours"] and "attributeTypeKey" in colour["matchBy"]
    assert not any(b.get("column") == book.header("Ln") for s in profile["sources"] for b in s["columns"])
    material = bound[book.header("T")]["relation"]
    assert (material["objectTypeKey"], material["matchBy"]) == (lists["Materials"], {"field": "name"})
    (flags,) = [b for b in items["columns"] if "relationFlags" in b]
    assert set(flags["columns"]) == {book.header("F1"), book.header("F2")}
    assert flags["relationFlags"]["objectTypeKey"] == lists[book2.flags]
    model = ok(world.api.get(f"/model-drafts/{draft['id']}/model"))["model"]
    names_of = {t["key"]: fold_name(t["name"]) for t in model["objectTypes"]}
    added = [o["key"] for p in proposals for o in p["operations"] if o["kind"] == "addObjectType"]
    list_names = [names_of[key] for key in [*lists.values(), *added]]
    assert len(list_names) == len(set(list_names)), sorted(list_names)

    summary = _summary_of(world, draft, answer)
    refusals = {s["sheet"]: s["rejections"] for s in summary["sources"] if s["rejections"]}
    naming = sum(missing.values())
    # The rows naming a missing material are refused; so are the translations of those items,
    # whose items the load does not create.
    assert refusals == {
        workbooks.S1: [{"code": "REFERENCE_NOT_FOUND", "rows": naming}],
        workbooks.S2: [{"code": "REFERENCE_NOT_FOUND", "rows": naming * len(workbooks.LANGUAGES)}],
    }, refusals

    (create,) = [
        a for a in lookup["alternatives"]
        if any(o.get("binding", {}).get("relation", {}).get("missing") == "create" for o in a["operations"])
    ]
    answer = _step(world, draft, *create["operations"])
    summary = _summary_of(world, draft, answer)
    assert all(s["rejections"] == [] for s in summary["sources"]), summary["sources"]


def fold_name(name: str) -> str:
    from app.engine.sources.inference.patterns import fold

    return fold(name)


@pytest.mark.journey("J34.9")
@pytest.mark.structures("K")
def test_a_sheet_naming_other_sheets_is_no_description_without_its_type_words(world):
    """W1 alone proposes no modelDescription; W2 with D's type column holding words outside the
    vocabulary proposes none either, and its list sheets are read by A6's rules."""
    draft, _, _, _ = _inferred(world)
    assert not [p for p in _proposals(world, draft) if p["pattern"].startswith(("modelDescription", "described"))]

    import io

    from openpyxl import load_workbook

    book = workbooks.w2(rows=200)
    changed = load_workbook(io.BytesIO(book.content))
    sheet = changed[book.description]
    for row in range(2, len(book.fields) + 2):
        sheet.cell(row=row, column=2, value=f"Kind {row}")
    content = io.BytesIO()
    changed.save(content)
    workspace = _workspace(world)
    other = _draft(world)
    _profiled(world, {"draftId": other["id"]}, "described.xlsx", content.getvalue(), workspaceKey=workspace)
    _infer(world, other)
    proposals = _proposals(world, other)
    assert not [p for p in proposals if p["pattern"].startswith(("modelDescription", "described"))]
    assert {p["sheet"] for p in proposals if p["pattern"] == "keyColumn"} >= set(book.lists)


@pytest.mark.journey("J27.8")
@pytest.mark.structures("K")
def test_an_import_skips_rows_without_a_key_when_its_source_says_so(world):
    """Given an inline profile keyed by a unique attribute and a file with an empty key on one row.
    With rowsWithoutKey skip the other rows load and the row is counted skipped; left out, it is
    refused MISSING_RECORD_KEY; skip on a source without a key is refused INVALID_IMPORT_PROFILE."""
    workspace = _workspace(world)
    draft = _draft(world)
    _catalogue(world, draft)
    release = _install(world, draft)
    ok(world.activate_everywhere(release["id"]))
    content = b"id,name\nA1,Alpha\n,Beta\nC3,Gamma\n"

    def importing(source: dict[str, Any]):
        profile = {
            "sources": [
                {
                    "applicationKey": world.app("K"),
                    "objectTypeKey": "j34-category",
                    "columns": [{"column": "id", "attributeTypeKey": "j34-category-id"}, {"column": "name", "field": "name"}],
                    **source,
                }
            ]
        }
        request = {"workspaceKey": workspace, "policy": "independent", "stage": "execute", "profile": profile}
        return world.api.upload("/imports", {"file": ("keys.csv", content, "text/csv")}, {"request": json.dumps(request)})

    keyed = {"key": {"attributeTypeKey": "j34-category-id"}}
    job = ok(importing({**keyed, "rowsWithoutKey": "skip"}), 202)
    _run(world)
    done = ok(world.api.get(f"/jobs/{job['id']}"))
    assert (done["state"], done["counts"]["rejected"], done["counts"]["created"]) == ("completed", 0, 2), done
    assert done["bindingReport"][0]["skippedRows"] == 1
    assert sorted(o["name"] for o in _all(world, "/objects/j34-category", workspaceKey=workspace)) == ["Alpha", "Gamma"]

    job = ok(importing(keyed), 202)
    _run(world)
    done = ok(world.api.get(f"/jobs/{job['id']}"))
    rows = ok(world.api.get(f"/jobs/{job['id']}/rows", pageSize=10))["items"]
    assert done["counts"]["rejected"] == 1
    assert [o["error"]["code"] for r in rows for o in r["outcomes"] if o.get("error")] == ["MISSING_RECORD_KEY"], rows

    error = refused(importing({"rowsWithoutKey": "skip"}), 422, "INVALID_IMPORT_PROFILE")
    assert [p["path"] for p in error["details"]["problems"]] == ["/sources/0/rowsWithoutKey"], error


@pytest.mark.journey("J34.5")
@pytest.mark.structures("K")
def test_a_workbook_uploaded_without_a_workspace_is_compared_with_the_default_workspaces_records(world):
    """Regression (found by the A7 browser runner, 2026-10-14): the editor uploads a workbook without
    naming a workspace, and its columns were compared with no records, so extend mode matched
    nothing by value. Given records of K named as T's values in the default workspace, when W1 is
    uploaded to a draft without a workspace, then T's overlaps name K by name."""
    book = workbooks.w1(rows=60)
    for name in sorted(book.distinct("T") - set(workbooks.PLACEHOLDERS)):
        ok(world.create("K", name), 201)
    draft = _draft(world)
    source = _profiled(world, {"draftId": draft["id"]}, "catalogue.xlsx", book.content)
    columns = ok(world.api.get(f"/source-files/{source['id']}/profile/sheets/{workbooks.S1}/columns", pageSize=50))["items"]
    material = next(c for c in columns if c["header"] == book.header("T"))
    named = [o for o in material["overlaps"] if o.get("objectTypeKey") == world.key("K") and o.get("field") == "name"]
    assert named and named[0]["workspaceKey"] == ok(world.api.get("/workspace-runtime-state"))["defaultWorkspaceKey"], material["overlaps"]


# --- J34.10 a sheet of lists laid out for reading (0.10 A8a, D114–D121) ------------------------


def _letter(number: int) -> str:
    letters = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    return (letters[(number - 1) // 26 - 1] if number > 26 else "") + letters[(number - 1) % 26]


def _w3_draft(world) -> tuple[dict[str, Any], workbooks.W3, dict[str, Any], str]:
    workspace = _workspace(world)
    draft = _draft(world)
    book = workbooks.w3()
    source = _profiled(world, {"draftId": draft["id"]}, "lists.xlsx", book.content, workspaceKey=workspace)
    return draft, book, source, workspace


def _place(block: dict[str, Any]) -> tuple[str, str, int]:
    """A W3 block's columns and header row as the profile and a source name them."""
    return _letter(block["first"]), _letter(block["last"]), block["headerRow"]


def _list_blocks(proposals: list[dict[str, Any]]) -> dict[tuple[str, str, int], dict[str, Any]]:
    """The listBlock proposals by their block's columns and header row."""
    found = {}
    for proposal in proposals:
        if proposal["pattern"] == "listBlock":
            block = proposal["evidence"]["block"]
            at = (block["firstColumn"], block["lastColumn"], block["headerRow"])
            assert at not in found, at
            found[at] = proposal
    return found


def _operations(proposal: dict[str, Any], kind: str) -> list[dict[str, Any]]:
    return [o for o in proposal["operations"] if o["kind"] == kind]


def _list_type(proposal: dict[str, Any]) -> dict[str, Any]:
    """The addObjectType of a listBlock's own list (the first translated list adds the language and
    translation types too)."""
    (added,) = _operations(proposal, "addSource")
    (made,) = [o for o in _operations(proposal, "addObjectType") if o["key"] == added["objectType"]]
    return made


@pytest.mark.journey("J34.10")
@pytest.mark.structures("K")
def test_a_sheet_laid_out_for_reading_is_profiled_list_by_list_with_the_titles_above_each(world):
    """Given W3 profiled. Then its profile lists every block of both bands with its range, header
    row and titles; a block under another in the same columns is a block of its own; and no
    block's column holds a title, a note or the sentence under a list among its values."""
    _, book, source, _ = _w3_draft(world)
    (sheet,) = ok(world.api.get(f"/source-files/{source['id']}/profile/sheets"))["items"]
    found = {(b["firstColumn"], b["lastColumn"], b["headerRow"]): b for b in sheet["blocks"]}
    made = {_place(b): b for b in book.blocks}
    assert set(found) == set(made)
    for at, block in made.items():
        assert found[at]["lastRow"] == block["lastRow"], at
        assert found[at]["titles"] == block["titles"], at
    stacked = [b for b in book.blocks if b["headerRow"] != book.header_row]
    assert stacked and all(any(o["first"] == b["first"] and o["headerRow"] < b["headerRow"] for o in book.blocks) for b in stacked)

    columns = _all(world, f"/source-files/{source['id']}/profile/sheets/{book.sheet}/columns")
    noise = {t for b in book.blocks for t in b["titles"]} | {b["note"] for b in book.blocks if b["note"]} | {workbooks.PROSE}
    held = {v["value"] for c in columns for v in c["values"]}
    assert not held & noise, held & noise
    heads = {(c["letter"], c["block"]): c["header"] for c in columns}
    for index, block in enumerate(sheet["blocks"]):
        assert heads[(block["firstColumn"], index)] == made[(block["firstColumn"], block["lastColumn"], block["headerRow"])]["title"]


@pytest.mark.journey("J34.10")
@pytest.mark.structures("K")
def test_each_list_of_a_sheet_laid_out_for_reading_is_proposed_with_its_translations_flags_notes_and_group(world):
    """When the inference runs on W3 in new-application mode. Then one listBlock per block that is a
    list, none for the note alone (a warning names it); each list's source names its block; the
    language blocks' columns are translations in the language their header names, else Language 1;
    the column holding only its header is unbound and reported; the Y/N column is a yes/no
    attribute; a note's list carries the note in its evidence and description; one navigation group
    per innermost title, holding its lists."""
    draft, book, _, _ = _w3_draft(world)
    read = _infer(world, draft)
    proposals = _proposals(world, draft)
    blocks = _list_blocks(proposals)
    lists = {_place(b): b for b in book.lists()}
    assert set(blocks) == set(lists)
    (free,) = [b for b in book.blocks if not b["values"]]
    assert any(free["title"] in w and "not a list" in w for w in read["warnings"]), read["warnings"]

    names = {}
    for at, block in lists.items():
        proposal = blocks[at]
        (added,) = _operations(proposal, "addSource")
        assert added["sheet"] == book.sheet and added["headerRow"] == block["headerRow"]
        assert (added["block"]["firstColumn"], added["block"]["lastColumn"], added["block"]["lastRow"]) == (at[0], at[1], block["lastRow"])
        assert added["key"] == {"field": "name"}
        made = _list_type(proposal)
        names[at] = made["key"]
        mapped = {o["column"]: o["binding"] for o in _operations(proposal, "mapColumn")}
        assert mapped[block["title"]] == {"field": "name"}
        for header, values in block["translations"].items():
            if values is None:
                assert header not in mapped
                assert header in [e["column"] for e in proposal["evidence"]["empty"]]
                continue
            language = header.rsplit("(", 1)[1].rstrip(")") if "(" in header else "Language 1"
            assert mapped[header]["relatedRecord"]["parent"]["value"] == language, header
        if block["shape"] == "flags":
            (flag,) = [h for h in mapped if h != block["title"]]
            attribute = mapped[flag]["attributeTypeKey"]
            types = {o["key"]: o["valueType"] for p in proposals for o in _operations(p, "addAttributeType")}
            assert types[attribute] == "boolean"
        if block["note"]:
            assert proposal["evidence"]["note"]["meaning"] == block["meaning"]
            assert made.get("description") or block["meaning"] == "heading"
        else:
            assert proposal["evidence"].get("note") is None

    groups = [p for p in proposals if p["pattern"] == "navigationGroup"]
    collections = {}
    for proposal in groups:
        (added,) = _operations(proposal, "addNavigationGroup")
        collections[added["label"]] = sorted(added["collections"])
    expected = {
        title: sorted(names[_place(b)] for b in book.lists() if b["title"] in headers)
        for title, headers in book.groups().items()
        if len(headers) >= 2
    }
    assert collections == expected


def _w3_loaded(world) -> tuple[workbooks.W3, list[dict[str, Any]], str, dict[str, Any]]:
    draft, book, source, workspace = _w3_draft(world)
    _infer(world, draft)
    proposals = _proposals(world, draft)
    answer = ok(_application(world, draft))
    assert answer["valid"] is True, answer["diagnostics"]
    summary = _summary_of(world, draft, answer)
    _load(world, draft, source, workspace)
    return book, proposals, workspace, summary


@pytest.mark.journey("J34.10")
@pytest.mark.structures("K")
def test_the_lists_of_a_sheet_laid_out_for_reading_load_by_name_with_their_translations(world):
    """When W3's proposals are applied, the dry run refuses no row and counts each note row
    skipped; installed, loaded into a change set and published, each list holds its values by
    name, with their translations, and no record is named by a note, a title or a header."""
    book, proposals, workspace, summary = _w3_loaded(world)
    assert all(s["rejections"] == [] for s in summary["sources"]), summary["sources"]
    noted = [b for b in book.lists() if b["note"]]
    assert sum(s["skippedRows"] for s in summary["sources"]) == len(noted)
    blocks = _list_blocks(proposals)
    noise = {t for b in book.blocks for t in b["titles"]} | {b["note"] for b in book.blocks if b["note"]} | {b["title"] for b in book.blocks}
    translation_type = None
    for block in book.lists():
        made = _list_type(blocks[_place(block)])
        names = sorted(o["name"] for o in _all(world, f"/objects/{made['key']}", workspaceKey=workspace))
        assert names == sorted(block["values"]), block["title"]
        assert not set(names) & noise
        if block["shape"] == "languages":
            mapped = {o["column"]: o["binding"] for o in _operations(blocks[_place(block)], "mapColumn")}
            translation_type = next(b["relatedRecord"]["objectTypeKey"] for b in mapped.values() if "relatedRecord" in b)
    translated = {o["name"] for o in _all(world, f"/objects/{translation_type}", workspaceKey=workspace)}
    expected = {v for b in book.lists() for values in b["translations"].values() if values for v in values}
    assert translated == expected


@pytest.mark.journey("J34.10")
@pytest.mark.structures("K")
def test_a_block_narrowed_by_its_source_loads_the_rows_left_in_it(world):
    """When a block's source is narrowed by setSource to end two rows earlier, the dry run counts
    two rows fewer for it, and the other sources count as before."""
    draft, book, _, _ = _w3_draft(world)
    _infer(world, draft)
    proposals = _proposals(world, draft)
    answer = ok(_application(world, draft))
    before = _summary_of(world, draft, answer)
    block = next(b for b in book.lists() if b["shape"] == "plain" and len(b["values"]) >= 4)
    proposal = _list_blocks(proposals)[_place(block)]
    made = _list_type(proposal)
    (added,) = _operations(proposal, "addSource")
    narrowed = {**added["block"], "lastRow": block["lastRow"] - 2}
    after = _summary_of(world, draft, _step(world, draft, {"kind": "setSource", "source": added["id"], "block": narrowed}))
    rows = {s["objectTypeKey"]: s["rows"] for s in before["sources"]}
    now = {s["objectTypeKey"]: s["rows"] for s in after["sources"]}
    assert now[made["key"]] == rows[made["key"]] - 2
    assert {k: v for k, v in now.items() if k != made["key"]} == {k: v for k, v in rows.items() if k != made["key"]}


# --- J34.10 the editor's lists (0.10 A8b, D122–D130) --------------------------------------------


def _range(first: str, top: int, last: str, bottom: int) -> str:
    return f"{first}{top}:{last}{bottom}"


def _w3_applied(world) -> tuple[dict[str, Any], workbooks.W3, dict[str, Any], dict[str, Any], dict[str, Any]]:
    """W3's proposals applied: the draft, the book, its file, the listBlocks by place and the dry
    run the application queued."""
    draft, book, source, _ = _w3_draft(world)
    _infer(world, draft)
    blocks = _list_blocks(_proposals(world, draft))
    answer = ok(_application(world, draft))
    return draft, book, source, blocks, _summary_of(world, draft, answer)


def _groups(world, draft: dict[str, Any]) -> dict[str, list[str]]:
    model = ok(world.api.get(f"/model-drafts/{draft['id']}/model"))["model"]
    return {
        group["label"]: list(group["collections"])
        for application in model["applications"]
        for group in (application.get("navigation") or {}).get("groups", [])
    }


def _rows_by_type(summary: dict[str, Any]) -> dict[str, int]:
    return {s["objectTypeKey"]: s["rows"] for s in summary["sources"]}


@pytest.mark.journey("J34.10")
@pytest.mark.structures("K")
def test_a_lists_cells_are_read_row_by_row_by_their_range(world):
    """Given W3 profiled. When a list's range is read. Then its rows come in order, the header row
    first, each cell by its letter with its value type, paged with cursors; a range that is empty or
    outside the sheet is refused INVALID_RANGE."""
    _, book, source, _ = _w3_draft(world)
    block = next(b for b in book.lists() if b["shape"] == "languages")
    first, last, header = _place(block)
    path = f"/source-files/{source['id']}/profile/sheets/{book.sheet}/cells"
    rows = _all(world, path, page_size=3, range=_range(first, header, last, block["lastRow"]))
    assert [r["row"] for r in rows] == list(range(header, block["lastRow"] + 1))
    letters = [_letter(n) for n in range(block["first"], block["last"] + 1)]
    assert all(sorted(r["cells"]) == letters for r in rows), rows
    assert rows[0]["cells"][first] == {"text": block["title"], "kind": "text"}
    assert [r["cells"][first]["text"] for r in rows[1:]] == block["values"]
    for wrong in ("B5:A2", "A9000:B9010", "nonsense"):
        refused(world.api.get(path, range=wrong), 422, "INVALID_RANGE")


@pytest.mark.journey("J34.10")
@pytest.mark.structures("K")
def test_a_lists_header_row_moved_keeps_each_column_on_its_letter(world):
    """Given W3's proposals applied. When a list's source moves its headerRow one row down, each
    bound column keeps its binding under the header its letter has on the new row and the dry run
    counts one row fewer for it; a column whose new header cell is empty becomes unmapped."""
    draft, book, _, blocks, before = _w3_applied(world)
    block = next(b for b in book.lists() if b["shape"] == "languages")
    proposal = blocks[_place(block)]
    made = _list_type(proposal)
    (added,) = _operations(proposal, "addSource")
    bound = {o["column"]: o["binding"] for o in _operations(proposal, "mapColumn")}
    after = _summary_of(world, draft, _step(world, draft, {"kind": "setSource", "source": added["id"], "headerRow": block["headerRow"] + 1}))
    assert _rows_by_type(after)[made["key"]] == _rows_by_type(before)[made["key"]] - 1
    moved = next(s for s in _draft_profile(world, draft)["profile"]["sources"] if s["id"] == added["id"])
    assert moved["headerRow"] == block["headerRow"] + 1
    now = {c["column"]: {k: v for k, v in c.items() if k != "column"} for c in moved["columns"]}
    below = {block["title"]: block["values"][0]}
    for header, values in block["translations"].items():
        below[header] = values[0]
    assert now == {below[header]: binding for header, binding in bound.items()}

    gapped = next(b for b in book.blocks if b["shape"] == "gapped")
    (gap_source,) = _operations(blocks[_place(gapped)], "addSource")
    _step(world, draft, {"kind": "setSource", "source": gap_source["id"], "headerRow": gapped["headerRow"] + 1})
    profile = _draft_profile(world, draft)["profile"]
    assert [(u["source"], u["column"]) for u in profile["unmapped"]] == [(gap_source["id"], gapped["title"])]


@pytest.mark.journey("J34.10")
@pytest.mark.structures("K")
def test_a_list_not_loaded_leaves_the_load_and_its_group_until_undone(world):
    """Given W3's proposals applied. When a list's source and list type are removed in one step,
    the dry run has no source for it, its navigation group no longer lists it, and proposing again
    proposes nothing for it; undoing the step restores the source, the type and the group entry."""
    draft, book, _, blocks, _ = _w3_applied(world)
    block = next(b for b in book.lists() if b["shape"] == "plain" and len(book.groups()[b["titles"][-1]]) >= 2)
    proposal = blocks[_place(block)]
    made = _list_type(proposal)
    (added,) = _operations(proposal, "addSource")
    group = block["titles"][-1]
    assert made["key"] in _groups(world, draft)[group]

    answer = _step(world, draft, {"kind": "removeSource", "source": added["id"]}, {"kind": "removeObjectType", "objectType": made["key"]})
    assert answer["valid"] is True, answer["diagnostics"]
    assert made["key"] not in _rows_by_type(_summary_of(world, draft, answer))
    assert made["key"] not in _groups(world, draft)[group]

    _infer(world, draft)
    again = _list_blocks(_proposals(world, draft)).get(_place(block))
    assert again is None or again["status"] != "open", again

    ok(world.api.post(f"/model-drafts/{draft['id']}/undo", {"expectedVersion": _version(world, draft)}))
    assert added["id"] in [s["id"] for s in _draft_profile(world, draft)["profile"]["sources"]]
    assert made["key"] in _groups(world, draft)[group]


@pytest.mark.journey("J34.10")
@pytest.mark.structures("K")
def test_a_rectangle_is_read_as_a_list_on_request(world):
    """Given W3's proposals applied and a list with a note not loaded (its source and type removed).
    When its rectangle is sent to the list route, the answer is a list proposal with a list type, a
    source on that rectangle keyed by name and its note row skipped; its operations applied, the
    dry run loads its values, and the list is the administrator's, not proposed. The free field's
    rectangle, with nothing under its header but its note, is refused INVALID_RANGE. (Case 10 as
    the user decided on 2026-10-15: W3's free field holds no values to load.)"""
    draft, book, _, blocks, _ = _w3_applied(world)
    block = next(b for b in book.lists() if b["note"] and b["headerRow"] == book.header_row)
    proposal = blocks[_place(block)]
    made = _list_type(proposal)
    (added,) = _operations(proposal, "addSource")
    _step(world, draft, {"kind": "removeSource", "source": added["id"]}, {"kind": "removeObjectType", "objectType": made["key"]})

    first, last, header = _place(block)
    path = f"/model-drafts/{draft['id']}/inference/list"
    body = {"sheet": book.sheet, "headerRow": header, "block": {"firstColumn": first, "lastColumn": last, "lastRow": block["lastRow"]}}
    read = ok(world.api.post(path, body))
    assert read["pattern"] == "listBlock"
    (source,) = _operations(read, "addSource")
    assert (source["headerRow"], source["block"]["firstColumn"], source["block"]["lastColumn"], source["block"]["lastRow"]) == (header, first, last, block["lastRow"])
    assert source["key"] == {"field": "name"}
    assert {"kind": "setSource", "source": source["id"], "rowsWithoutKey": "skip"} in read["operations"]
    answer = _step(world, draft, *read["operations"])
    assert answer["valid"] is True, answer["diagnostics"]
    summary = _summary_of(world, draft, answer)
    (loaded,) = [s for s in summary["sources"] if s["objectTypeKey"] == source["objectType"]]
    assert (loaded["records"]["created"], loaded["skippedRows"], loaded["rejections"]) == (len(block["values"]), 1, [])
    proposed = {e["element"] for e in ok(world.api.get(f"/model-drafts/{draft['id']}/inference"))["proposed"]}
    assert f"objectType:{source['objectType']}" not in proposed

    free = next(b for b in book.blocks if b["shape"] == "free")
    first, last, header = _place(free)
    body = {"sheet": book.sheet, "headerRow": header, "block": {"firstColumn": first, "lastColumn": last, "lastRow": free["lastRow"]}}
    refused(world.api.post(path, body), 422, "INVALID_RANGE")


@pytest.mark.journey("J34.10")
@pytest.mark.structures("K")
def test_a_table_is_not_read_as_lists_even_with_an_empty_row_in_it(world):
    """W1 (one table) and a table with an empty row in it propose no listBlock, and each is one
    block, as before A8."""
    from openpyxl import Workbook

    book = Workbook()
    sheet = book.active
    sheet.title = "Table"
    sheet.append(["Code", "Name", "Size", "Price"])
    for index in range(1, 21):
        sheet.append([f"C{index:03d}", f"Thing {index}", index % 4, index * 1.5])
        if index == 10:
            sheet.append([])
    gapped = workbooks._save(book)
    for name, content in (("catalogue.xlsx", workbooks.w1(rows=60).content), ("gapped.xlsx", gapped)):
        workspace = _workspace(world)
        draft = _draft(world)
        source = _profiled(world, {"draftId": draft["id"]}, name, content, workspaceKey=workspace)
        sheets = ok(world.api.get(f"/source-files/{source['id']}/profile/sheets"))["items"]
        assert all(len(s["blocks"]) == 1 for s in sheets), [(s["name"], s["blocks"]) for s in sheets]
        _infer(world, draft)
        assert not [p for p in _proposals(world, draft) if p["pattern"] == "listBlock"]


# --- J34.10 lists of one shape as one list (0.10 A8c, D140–D146) -----------------------------------


def _one_list(proposal: dict[str, Any]) -> list[dict[str, Any]]:
    """A listBlock's alternatives reading its run as one list under the headers (D143)."""
    return [
        a for a in proposal["alternatives"]
        if any(o["kind"] == "addSource" and o.get("parent") for o in a["operations"])
    ]


def _model_types(world, draft: dict[str, Any]) -> dict[str, dict[str, Any]]:
    model = ok(world.api.get(f"/model-drafts/{draft['id']}/model"))["model"]
    return {t["key"]: t for t in model["objectTypes"]}


def _contains(world, draft: dict[str, Any], parent: str, child: str) -> bool:
    model = ok(world.api.get(f"/model-drafts/{draft['id']}/model"))["model"]
    containing = {r["key"] for r in model["relationTypes"] if (r.get("features") or {}).get("parentOf")}
    return any(
        (r["fromObjectTypeKey"], r["toObjectTypeKey"]) == (parent, child) and r["relationTypeKey"] in containing
        for r in model["objectTypeRelations"]
    )


@pytest.mark.journey("J34.10")
@pytest.mark.structures("K")
def test_lists_of_one_shape_carry_the_alternative_of_one_list_under_their_headers(world):
    """Case 11. Given W3 profiled and the inference run. Then each list of the third band's run
    carries the alternative of one list naming the run's three lists, each source fixed to its
    list's header; no list of the first two bands carries it."""
    draft, book, _, _ = _w3_draft(world)
    _infer(world, draft)
    blocks = _list_blocks(_proposals(world, draft))
    run = book.run()
    assert len(run) == 3
    for block in run:
        (alternative,) = _one_list(blocks[_place(block)])
        sources = _operations(alternative, "addSource")
        assert sorted(o["parent"]["value"] for o in sources) == sorted(b["title"] for b in run)
        assert {(o["headerRow"], o["block"]["firstColumn"]) for o in sources} == {(b["headerRow"], _letter(b["first"])) for b in run}
    others = [p for at, p in blocks.items() if at not in {_place(b) for b in run}]
    assert others and not [p for p in others if _one_list(p)]


@pytest.mark.journey("J34.10")
@pytest.mark.structures("K")
def test_lists_of_one_shape_load_as_one_list_under_their_headers(world):
    """Case 12. When W3's proposals are applied and the alternative's operations sent as one step,
    the draft has a parent list and one list contained in it, the run's three list types are gone,
    and the dry run refuses no row and skips each second header row; undoing the step restores the
    three lists. Sent again, installed, loaded into a change set and published, the parent list
    holds the three headers, each value stands under its header, the name under two headers is two
    records, and a second load of the same file changes nothing."""
    draft, book, source, workspace = _w3_draft(world)
    _infer(world, draft)
    blocks = _list_blocks(_proposals(world, draft))
    ok(_application(world, draft))
    run = book.run()
    old = [_list_type(blocks[_place(b)])["key"] for b in run]
    (alternative,) = _one_list(blocks[_place(run[0])])
    sources = _operations(alternative, "addSource")
    (one,) = {o["objectType"] for o in sources}
    (parent,) = {o["parent"]["objectTypeKey"] for o in sources}

    answer = _step(world, draft, *alternative["operations"])
    assert answer["valid"] is True, answer["diagnostics"]
    types = _model_types(world, draft)
    assert not set(old) & set(types)
    assert parent in types and _contains(world, draft, parent, one)
    summary = _summary_of(world, draft, answer)
    assert all(s["rejections"] == [] for s in summary["sources"]), summary["sources"]
    mine = [s for s in summary["sources"] if s["objectTypeKey"] == one]
    assert len(mine) == 3 and all(s["skippedRows"] == 1 for s in mine), mine

    ok(world.api.post(f"/model-drafts/{draft['id']}/undo", {"expectedVersion": _version(world, draft)}))
    types = _model_types(world, draft)
    assert set(old) <= set(types) and one not in types
    assert _step(world, draft, *alternative["operations"])["valid"] is True

    release = _install(world, draft)
    ok(world.activate_everywhere(release["id"]))

    def loading() -> dict[str, Any]:
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
        return done

    loading()
    parents = {o["id"]: o["name"] for o in _all(world, f"/objects/{parent}", workspaceKey=workspace)}
    assert sorted(parents.values()) == sorted(b["title"] for b in run)
    under: dict[str, list[str]] = {}
    for record in _all(world, f"/objects/{one}", workspaceKey=workspace):
        under.setdefault(parents[record["parentObjectId"]], []).append(record["name"])
    assert {k: sorted(v) for k, v in under.items()} == {b["title"]: sorted(b["values"]) for b in run}
    assert sum(1 for b in run if "Shared value" in b["values"]) == 2
    again = loading()
    assert (again["counts"]["created"], again["counts"]["updated"]) == (0, 0), again["counts"]


@pytest.mark.journey("J34.10")
@pytest.mark.structures("K")
def test_a_second_header_row_is_a_note_and_names_no_record(world):
    """Case 13. Given W3 profiled, each run list's note is its second header row (meaning
    heading); loaded, no record is named by it."""
    _, book, source, _ = _w3_draft(world)
    (sheet,) = ok(world.api.get(f"/source-files/{source['id']}/profile/sheets"))["items"]
    found = {(b["firstColumn"], b["lastColumn"], b["headerRow"]): b for b in sheet["blocks"]}
    for block in book.run():
        assert found[_place(block)]["note"] == {"row": block["headerRow"] + 1, "text": block["note"], "meaning": "heading"}
    book, proposals, workspace, _ = _w3_loaded(world)
    blocks = _list_blocks(proposals)
    for block in book.run():
        names = {o["name"] for o in _all(world, f"/objects/{_list_type(blocks[_place(block)])['key']}", workspaceKey=workspace)}
        assert block["note"] not in names and names == set(block["values"])


def _fixed_import(world, workspace: str, sources: list[dict[str, Any]], sheets: dict[str, list[tuple[Any, ...]]]):
    """An import of an xlsx file of ``sheets`` by an inline profile of ``sources``: the job and its
    final state."""
    from openpyxl import Workbook

    book = Workbook()
    book.remove(book.active)
    for name, rows in sheets.items():
        sheet = book.create_sheet(name)
        for row in rows:
            sheet.append(list(row))
    profile = {"sources": sources}
    request = {"workspaceKey": workspace, "policy": "independent", "stage": "execute", "onExisting": "overwrite", "profile": profile}
    files = {"file": ("fixed.xlsx", workbooks._save(book), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}
    answer = world.api.upload("/imports", files, {"request": json.dumps(request)})
    if answer.status_code != 202:
        return answer, None
    job = answer.json()
    _run(world)
    return job, ok(world.api.get(f"/jobs/{job['id']}"))


def _item_source(world, sheet: str, parent: str, **more: Any) -> dict[str, Any]:
    return {
        "sheet": sheet,
        "applicationKey": world.app("K"),
        "objectTypeKey": "j34-item",
        "key": {"field": "name"},
        "parent": {"objectTypeKey": "j34-category", "matchBy": {"field": "name"}, "value": parent, **more},
        "columns": [{"column": "name", "field": "name"}],
    }


def _catalogue_installed(world) -> str:
    workspace = _workspace(world)
    draft = _draft(world)
    _catalogue(world, draft)
    ok(world.activate_everywhere(_install(world, draft)["id"]))
    return workspace


@pytest.mark.journey("J27.8")
@pytest.mark.structures("K")
def test_an_import_sets_a_fixed_parent_on_every_row(world):
    """Case 14, J27 variant (0.10 A8c, D141). An import whose source sets parent to a value with
    missing: create creates the parent and places every row under it; with the default refuse and
    no such record, every row is refused REFERENCE_NOT_FOUND; a source with a fixed parent and a
    parent column is refused INVALID_IMPORT_PROFILE at its parent."""
    workspace = _catalogue_installed(world)
    rows = [("name",), ("Hammer",), ("Saw",), ("Drill",)]
    _, done = _fixed_import(world, workspace, [_item_source(world, "Items", "Tools", missing="create")], {"Items": rows})
    assert (done["state"], done["counts"]["rejected"]) == ("completed", 0), done
    (tools,) = [o for o in _all(world, "/objects/j34-category", workspaceKey=workspace) if o["name"] == "Tools"]
    items = _all(world, "/objects/j34-item", workspaceKey=workspace)
    assert sorted(o["name"] for o in items) == ["Drill", "Hammer", "Saw"]
    assert {o["parentObjectId"] for o in items} == {tools["id"]}

    job, done = _fixed_import(world, workspace, [_item_source(world, "Items", "Garden")], {"Items": [("name",), ("Rake",), ("Hoe",)]})
    found = ok(world.api.get(f"/jobs/{job['id']}/rows", pageSize=10))["items"]
    codes = [o["error"]["code"] for r in found for o in r["outcomes"] if o.get("error")]
    assert codes == ["REFERENCE_NOT_FOUND", "REFERENCE_NOT_FOUND"], found

    both = _item_source(world, "Items", "Tools", missing="create")
    both["columns"].append({"column": "category", "parent": {"objectTypeKey": "j34-category", "matchBy": {"field": "name"}}})
    answer, _ = _fixed_import(world, workspace, [both], {"Items": [("name", "category"), ("Axe", "Tools")]})
    error = refused(answer, 422, "INVALID_IMPORT_PROFILE")
    assert "/sources/0/parent" in [p["path"] for p in error["details"]["problems"]]


@pytest.mark.journey("J27.8")
@pytest.mark.structures("K")
def test_an_import_keyed_by_name_finds_records_under_their_parent(world):
    """Case 15, J27 variant (0.10 A8c, D142). Two sources keyed by name, fixed to two parents, each
    holding one name: the first load creates two records, the second changes none; two rows of one
    name under one parent with different values are refused DUPLICATE_KEY_IN_FILE."""
    workspace = _catalogue_installed(world)
    sources = [
        _item_source(world, "Tools", "Tools", missing="create"),
        _item_source(world, "Toys", "Toys", missing="create"),
    ]
    sheets = {"Tools": [("name",), ("Set",)], "Toys": [("name",), ("Set",)]}
    _, done = _fixed_import(world, workspace, sources, sheets)
    assert (done["state"], done["counts"]["rejected"]) == ("completed", 0), done
    items = _all(world, "/objects/j34-item", workspaceKey=workspace)
    assert [o["name"] for o in items] == ["Set", "Set"] and len({o["parentObjectId"] for o in items}) == 2
    _, done = _fixed_import(world, workspace, sources, sheets)
    assert (done["counts"]["created"], done["counts"]["updated"], done["counts"]["rejected"]) == (0, 0, 0), done

    ordered = _item_source(world, "Tools", "Tools", missing="create")
    ordered["columns"].append({"column": "order", "attributeTypeKey": "j34-order"})
    job, _ = _fixed_import(world, workspace, [ordered], {"Tools": [("name", "order"), ("Set", 1), ("Set", 2)]})
    found = ok(world.api.get(f"/jobs/{job['id']}/rows", pageSize=10))["items"]
    codes = [o["error"]["code"] for r in found for o in r["outcomes"] if o.get("error")]
    assert codes == ["DUPLICATE_KEY_IN_FILE", "DUPLICATE_KEY_IN_FILE"], found


@pytest.mark.journey("J27.8")
@pytest.mark.structures("K")
def test_an_import_keyed_by_name_finds_its_records_by_name(world):
    """J27 variant (0.10 A8a, D117): an import keyed by {"field": "name"} creates the list's
    records; the same file again changes none; a file naming a record by a name two records of the
    type share is refused AMBIGUOUS_NAME_KEY."""
    workspace = _workspace(world)
    draft = _draft(world)
    _catalogue(world, draft)
    release = _install(world, draft)
    ok(world.activate_everywhere(release["id"]))

    def importing(content: bytes):
        profile = {
            "sources": [
                {
                    "applicationKey": world.app("K"),
                    "objectTypeKey": "j34-material",
                    "key": {"field": "name"},
                    "columns": [{"column": "name", "field": "name"}],
                }
            ]
        }
        request = {"workspaceKey": workspace, "policy": "independent", "stage": "execute", "onExisting": "overwrite", "profile": profile}
        job = ok(world.api.upload("/imports", {"file": ("names.csv", content, "text/csv")}, {"request": json.dumps(request)}), 202)
        _run(world)
        return job, ok(world.api.get(f"/jobs/{job['id']}"))

    _, done = importing(b"name\nPaper\nCard\nSteel\n")
    assert (done["state"], done["counts"]["created"], done["counts"]["rejected"]) == ("completed", 3, 0), done
    _, done = importing(b"name\nPaper\nCard\nSteel\n")
    assert (done["counts"]["created"], done["counts"]["updated"], done["counts"]["rejected"]) == (0, 0, 0), done
    assert sorted(o["name"] for o in _all(world, "/objects/j34-material", workspaceKey=workspace)) == ["Card", "Paper", "Steel"]

    body = {"applicationKey": world.app("K"), "objectTypeKey": "j34-material", "name": "Paper", "workspaceKey": workspace}
    ok(world.api.post("/objects", body), 201)
    job, done = importing(b"name\nPaper\n")
    rows = ok(world.api.get(f"/jobs/{job['id']}/rows", pageSize=10))["items"]
    assert [o["error"]["code"] for r in rows for o in r["outcomes"] if o.get("error")] == ["AMBIGUOUS_NAME_KEY"], rows


@pytest.mark.journey("J34.2")
@pytest.mark.structures("K")
def test_a_header_ending_in_a_space_is_mapped_by_its_trimmed_name(world):
    """Regression (found on the user's reading-layout workbook by A8a's real-file smoke): the import
    reads a header without its surrounding spaces, but the draft's sheets kept them, so mapping the
    column by the name the import reads was refused unknownElement. Given a file whose header ends
    in a space, a source maps the column by its trimmed name and the dry run reads it."""
    workspace = _workspace(world)
    draft = _draft(world)
    _catalogue(world, draft)
    _profiled(world, {"draftId": draft["id"]}, "spaced.csv", b"Colour ,Code\nRed,R\nBlue,B\n", workspaceKey=workspace)
    _step(world, draft, {"kind": "addSource", "id": "colours", "sheet": "csv", "objectType": "j34-colour", "key": {"field": "name"}})
    summary = _summary_of(world, draft, _step(world, draft, {"kind": "mapColumn", "source": "colours", "column": "Colour", "binding": {"field": "name"}}))
    (colours,) = summary["sources"]
    assert (colours["rows"], colours["rejections"]) == (2, [])


# --- 0.10 R: a source file's jobs and the requests meeting them (R-F5–R-F9) ---------------------


class _PausedProfile:
    """The worker, in a thread of its own, running a file's profile and stopped once its cells are
    staged: the profile's transaction holds what it holds for the rest of its run."""

    def __init__(self, world, monkeypatch) -> None:
        from app.engine.sources import profiling

        self.reached, self.released = threading.Event(), threading.Event()
        staged = profiling._stage

        def pausing(*args: Any, **kwargs: Any) -> list[str]:
            names = staged(*args, **kwargs)
            self.reached.set()
            self.released.wait(30)
            return names

        monkeypatch.setattr(profiling, "_stage", pausing)
        self.pool = ThreadPoolExecutor(max_workers=2)
        self.worker = self.pool.submit(world.api.client.app.state.job_worker.run_until_idle)
        assert self.reached.wait(30), "the profile did not start"

    def finish(self) -> None:
        self.released.set()
        self.worker.result(timeout=60)
        self.pool.shutdown()


@pytest.mark.journey("J34.1")
@pytest.mark.structures("A1")
def test_a_running_profile_leaves_the_next_upload_and_the_drafts_steps_free(world, monkeypatch):
    """0.10 R-F5. Given a draft's file whose profile is running. When the corrected file is
    uploaded and a step is applied to the draft meanwhile. Then both answer at once, without waiting
    for the profile; the first file is superseded once the profile ends."""
    draft = _draft(world)
    owner = {"draftId": draft["id"]}
    first = ok(_upload(world, owner, "first.csv", b"code,name\na,Alpha\n"), 201)
    paused = _PausedProfile(world, monkeypatch)
    try:
        second = paused.pool.submit(_upload, world, owner, "second.csv", b"code,name\nb,Beta\n")
        ok(second.result(timeout=10), 201)
        step = {"kind": "addAttributeType", "key": "j34-free", "name": "Free", "valueType": "text"}
        paused.pool.submit(_apply, world, draft, step).result(timeout=10)
    finally:
        paused.finish()
    assert ok(world.api.get(f"/source-files/{first['id']}"))["supersededAt"] is not None


@pytest.mark.journey("J34.1")
@pytest.mark.structures("A1")
def test_deleting_a_file_stops_its_running_profile_and_then_deletes(world, monkeypatch):
    """0.10 R-F5, R-F7. Given a draft's file whose profile is running. When the file is deleted.
    Then the delete asks the profile to stop before it waits for it; the profile stops at its next
    check, among its statistics, as cancelled, and the delete then answers 204."""
    draft = _draft(world)
    first = ok(_upload(world, {"draftId": draft["id"]}, "first.csv", b"code,name\na,Alpha\n"), 201)
    job_id = first["profile"]["jobId"]
    paused = _PausedProfile(world, monkeypatch)
    try:
        deleting = paused.pool.submit(
            world.api.delete, f"/source-files/{first['id']}", expectedVersion=first["version"]
        )
        deadline = time.monotonic() + 10
        while ok(world.api.get(f"/jobs/{job_id}"))["cancelRequestedAt"] is None:
            assert time.monotonic() < deadline, "the delete did not ask the profile to stop"
            time.sleep(0.05)
    finally:
        paused.finish()
    ok(deleting.result(timeout=30), 204)
    assert ok(world.api.get(f"/jobs/{job_id}"))["state"] == "cancelled"
    refused(world.api.get(f"/source-files/{first['id']}"), 404, "SOURCE_FILE_NOT_FOUND")


@pytest.mark.journey("J34.3")
@pytest.mark.structures("K")
def test_a_dry_run_whose_file_is_deleted_while_it_runs_fails_and_says_so(world, monkeypatch):
    """0.10 R-F8. Given a dry run of a draft's file. When the file is deleted while the dry run
    previews its rows. Then the dry run fails SOURCE_FILE_NOT_FOUND instead of completing with
    what it read."""
    from app.engine.jobs import worker as worker_module

    draft, book, source, _workspace_key = _onboarding(world)
    _map_by_hand(world, draft, book)
    previewed = worker_module.preview_items

    def deleting(*args: Any, **kwargs: Any):
        found = previewed(*args, **kwargs)
        with SessionLocal() as session:
            session.execute(text("DELETE FROM source_files WHERE public_id = :id"), {"id": source["id"]})
            session.commit()
        return found

    monkeypatch.setattr(worker_module, "preview_items", deleting)
    # The last mapping step queued the dry run.
    _run(world)
    job = ok(world.api.get(f"/jobs/{ok(world.api.get(f'/model-drafts/{draft['id']}/dry-run'))['jobId']}"))
    assert job["state"] == "failed" and "SOURCE_FILE_NOT_FOUND" in json.dumps(job["error"]), job


@pytest.mark.journey("J34.1")
@pytest.mark.structures("A1")
def test_two_uploads_committed_together_are_sorted_out_by_the_sweep(world):
    """0.10 R-F9. Given two files of one draft, neither superseded, as two uploads committed
    together leave them. When the retention sweep runs. Then the older is superseded as of the
    newer's upload, and deleted by a sweep past the retention period."""
    draft = _draft(world)
    owner = {"draftId": draft["id"]}
    first = _profiled(world, owner, "first.csv", b"code,name\na,Alpha\n")
    second = _profiled(world, owner, "second.csv", b"code,name\nb,Beta\n")
    with SessionLocal() as session:
        session.execute(text("UPDATE source_files SET superseded_at = NULL WHERE public_id = :id"), {"id": first["id"]})
        session.commit()
    worker = world.api.client.app.state.job_worker
    worker.sweep()
    assert ok(world.api.get(f"/source-files/{first['id']}"))["supersededAt"] == second["uploadedAt"]
    worker.sweep(datetime.now(UTC) + timedelta(days=8))
    refused(world.api.get(f"/source-files/{first['id']}"), 404, "SOURCE_FILE_NOT_FOUND")


@pytest.mark.journey("J34.4")
@pytest.mark.structures("A1")
def test_an_inference_asked_to_stop_while_it_runs_stops(world, monkeypatch):
    """0.10 R-F6. Given a draft's inference running. When it is asked to stop while it reads the
    workbook, as a newer inference of the draft asks. Then it stops as cancelled at its next check
    and stores no proposals."""
    from app.engine.sources.inference import run as inference_run

    workspace = _workspace(world)
    draft = _draft(world)
    book = workbooks.w1(rows=50)
    _profiled(world, {"draftId": draft["id"]}, "catalogue.xlsx", book.content, workspaceKey=workspace)
    started = ok(world.api.post(f"/model-drafts/{draft['id']}/inference", {"mode": "newApplication"}), 202)
    found = inference_run.find

    def asked_to_stop(*args: Any, **kwargs: Any):
        with SessionLocal() as session:
            session.execute(text("UPDATE jobs SET cancel_requested_at = now() WHERE id = :id"), {"id": started["jobId"]})
            session.commit()
        return found(*args, **kwargs)

    monkeypatch.setattr(inference_run, "find", asked_to_stop)
    _run(world)
    assert ok(world.api.get(f"/jobs/{started['jobId']}"))["state"] == "cancelled"
    refused(world.api.get(f"/model-drafts/{draft['id']}/inference/proposals"), 409, "INFERENCE_NOT_READY")


# --- AQ: a column named by its letter (0.13) ------------------------------------------------------


def _tagged_book() -> bytes:
    """A block with an empty header cell (C) and a header three times (D, E, F)."""
    from openpyxl import Workbook

    book = Workbook()
    sheet = book.active
    sheet.title = "Tags"
    sheet.append(["Code", "Name", None, "Tag", "Tag", "Tag"])
    for number in range(1, 6):
        # Numbers in the rows keep them from reading as a header of their own.
        sheet.append([number, f"Item {number}", f"order {number}", number * 10, number * 20, number * 30])
    import io

    buffer = io.BytesIO()
    book.save(buffer)
    return buffer.getvalue()


@pytest.mark.journey("J34.11")
@pytest.mark.structures("K")
def test_a_column_with_an_empty_header_and_equal_headers_load_by_letter_and_by_the_readers_names(world):
    """Given a block whose header row has an empty cell and three equal headers. When the draft's
    columns are bound by letter (the empty one, the third equal one) and by Tag and Tag #2, then
    the draft's dry run reads every column, a letter outside the sheet is refused, and the
    installed profile loads every value into the records."""
    workspace = _workspace(world)
    draft = _draft(world)
    app = world.app("K")
    attributes = ["j34-order", "j34-t1", "j34-t2", "j34-t3"]  # the empty-header column, then the Tags
    _apply(
        world,
        draft,
        {"kind": "addObjectType", "applicationKey": app, "key": "j34-tagged", "name": "Tagged", "pluralName": "Tagged", "parent": None},
        {"kind": "addAttributeType", "key": "j34-code", "name": "Tag code", "valueType": "text", "features": {"unique": True}},
        *[{"kind": "addAttributeType", "key": key, "name": key, "valueType": "text", "features": {}} for key in attributes],
        *[{"kind": "attachAttribute", "objectType": "j34-tagged", "attributeType": key} for key in ["j34-code", *attributes]],
    )
    source = _profiled(world, {"draftId": draft["id"]}, "tags.xlsx", _tagged_book(), workspaceKey=workspace)
    _step(world, draft, {"kind": "addSource", "id": "tags", "sheet": "Tags", "objectType": "j34-tagged", "key": {"attributeTypeKey": "j34-code"}})
    answer = _step(
        world,
        draft,
        {"kind": "mapColumn", "source": "tags", "column": "Code", "binding": {"attributeTypeKey": "j34-code"}},
        {"kind": "mapColumn", "source": "tags", "column": "Name", "binding": {"field": "name"}},
        {"kind": "mapColumn", "source": "tags", "letter": "C", "binding": {"attributeTypeKey": "j34-order"}},
        {"kind": "mapColumn", "source": "tags", "column": "Tag", "binding": {"attributeTypeKey": "j34-t1"}},
        {"kind": "mapColumn", "source": "tags", "column": "Tag #2", "binding": {"attributeTypeKey": "j34-t2"}},
        {"kind": "mapColumn", "source": "tags", "letter": "F", "binding": {"attributeTypeKey": "j34-t3"}},
    )
    read = _draft_profile(world, draft)
    assert read["valid"] is True, read["diagnostics"]
    bound = {b.get("column") or "letter " + b["letter"]: b for b in read["profile"]["sources"][0]["columns"]}
    assert bound["letter C"] == {"letter": "C", "attributeTypeKey": "j34-order"}
    assert bound["Tag #2"]["attributeTypeKey"] == "j34-t2" and bound["letter F"]["attributeTypeKey"] == "j34-t3"
    summary = _summary_of(world, draft, answer)["sources"][0]
    assert (summary["rows"], summary["records"]["created"], summary["rejections"]) == (5, 5, [])

    def refusal(**column):
        body = {
            "expectedVersion": _version(world, draft),
            "operations": [{"kind": "ignoreColumn", "source": "tags", **column}],
        }
        return refused(world.api.post(f"/model-drafts/{draft['id']}/operations", body), 422, "INVALID_OPERATION")

    assert refusal(letter="ZZ")["details"]["reason"] == "unknownElement"
    assert refusal(letter="C", column="Tag")["details"]["reason"] == "invalidValue"
    assert refusal(letter="3")["details"]["reason"] == "invalidValue"

    # The same bindings in an inline dry run and in an import, read back from the records.
    assert _dry_run(world, draft, source, workspace, read["definition"])["summary"]["sources"][0]["rejections"] == []
    _load(world, draft, source, workspace)
    records = ok(world.api.get("/objects/j34-tagged", workspaceKey=workspace, pageSize=50))["items"]
    first = next(r for r in records if r["name"] == "Item 1")
    values = {a["attributeTypeKey"]: a["value"] for a in first["attributes"]}
    assert (values["j34-order"], values["j34-t1"], values["j34-t2"], values["j34-t3"]) == ("order 1", "10", "20", "30")


@pytest.mark.journey("J33.18")
@pytest.mark.structures("K")
def test_a_whole_profile_is_set_in_one_step_and_a_value_map_is_undone_alone(world):
    """Given W1 mapped by hand and its dry run. When the source is removed and the profile the
    draft's profile read gave in definition is set whole, then the dry run gives the original's
    figures and one undo takes the whole profile back; and when three value maps are set and the
    first is undone, the other two stay."""
    draft, book, _, _ = _onboarding(world)
    original = _summary_of(world, draft, _map_by_hand(world, draft, book)[-1])
    definition = _draft_profile(world, draft)["definition"]
    removed = _step(world, draft, {"kind": "removeSource", "source": "items"})
    assert _draft_profile(world, draft)["definition"] is None and removed["valid"] is True

    whole = _step(world, draft, {"kind": "setProfile", **definition})
    assert _draft_profile(world, draft)["definition"] == definition
    assert _summary_of(world, draft, whole)["sources"] == original["sources"]
    assert len(whole["entries"]) == 1 and whole["entries"][0]["inverse"]["kind"] == "restoreElements"

    ok(world.api.post(f"/model-drafts/{draft['id']}/undo", {"expectedVersion": _version(world, draft)}))
    assert _draft_profile(world, draft)["definition"] is None

    steps = {}
    for name in ("first", "second", "third"):
        answer = _step(world, draft, {"kind": "setValueMap", "name": name, "entries": {name: None}})
        steps[name] = answer["entries"][0]["step"]
    ok(world.api.post(f"/model-drafts/{draft['id']}/undo", {"expectedVersion": _version(world, draft), "step": steps["first"]}))
    maps = _draft_profile(world, draft)["profile"]["valueMaps"]
    assert sorted(maps) == ["second", "third"] and maps["third"] == {"third": None}

    unknown = world.api.post(
        f"/model-drafts/{draft['id']}/operations",
        {"expectedVersion": _version(world, draft), "operations": [{"kind": "setProfile", "sources": [{**definition["sources"][0], "sheet": "No such sheet"}]}]},
    )
    assert refused(unknown, 422, "INVALID_OPERATION")["details"]["reason"] == "unknownElement"
