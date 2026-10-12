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
