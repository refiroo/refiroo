"""J35 — Load the next version of a workbook (USER_JOURNEYS.md, 0.10 A5c).

A workbook mapped in a draft is installed with its profile and loaded (J34.8); the next version is
uploaded to the stored profile, which profiles it and checks it: columns new, missing and renamed,
new list values, name drift, records missing from the file, the profile against the active release
and what the load would do, writing nothing (D83). The load keeps the records missing from the file
unless the profile says to delete them, and deletes only in a change set (D82). The workbooks are
the generated W1 and W1′ (``tests/workbooks.py``); the draft is the configuration's active model
with the J34 catalogue added, so no test names a configuration's key.
"""

import copy
import json
import threading
from typing import Any

import pytest
import workbooks
from scenario import ok, refused
from sqlalchemy import text
from test_j34_onboard import (
    _all,
    _inferred,
    _install,
    _map_by_hand,
    _onboarding,
    _profiled,
    _run,
    _step,
    _upload,
    _version,
)

from app.db import SessionLocal
from app.engine.imports import binding as import_binding


def _colours(world, draft: dict[str, Any], book: workbooks.W1) -> None:
    """``Ln`` read as the item's colour by name, created when missing (the column W1′ renames)."""
    _step(
        world,
        draft,
        {
            "kind": "mapColumn",
            "source": "items",
            "column": book.header("Ln"),
            "binding": {
                "relation": {
                    "relationTypeKey": "j34-coloured",
                    "objectTypeKey": "j34-colour",
                    "matchBy": {"field": "name"},
                    "missing": "create",
                }
            },
        },
    )


def _load(world, workspace: str, profile_key: str, source_id: str, change_set: dict[str, Any] | None):
    """An import of a stored file through the stored profile, live or into a change set."""
    context = (
        {"changeSetId": change_set["id"], "expectedChangeSetVersion": change_set["version"]}
        if change_set is not None
        else {"workspaceKey": workspace}
    )
    request = {
        **context,
        "profileKey": profile_key,
        "sourceFileId": source_id,
        "policy": "independent",
        "onExisting": "overwrite",
        "stage": "execute",
    }
    return world.api.upload("/imports", {}, {"request": json.dumps(request)})


def _loaded(world) -> tuple[str, str, workbooks.W1]:
    """W1 mapped (its colours too), installed and activated with its profile, loaded into a change
    set and published: the workspace, the profile's key and the workbook."""
    draft, book, source, workspace = _onboarding(world)
    _map_by_hand(world, draft, book)
    _colours(world, draft, book)
    release = _install(world, draft)
    ok(world.activate(release["id"]))
    profile_key = release["importProfile"]["key"]
    change_set = world.change_set(workspace)
    job = ok(_load(world, workspace, profile_key, source["id"], change_set), 202)
    _run(world)
    assert ok(world.api.get(f"/jobs/{job['id']}"))["counts"]["rejected"] == 0
    world.publish(change_set, workspace)
    return workspace, profile_key, book


def _next_version(world, workspace: str, profile_key: str) -> tuple[workbooks.W1, dict[str, Any]]:
    """W1′ uploaded to the profile and checked: the workbook and the check."""
    following = workbooks.w1_next(rows=200)
    source = _profiled(
        world, {"profileKey": profile_key}, "catalogue-v2.xlsx", following.content, workspaceKey=workspace
    )
    check = ok(world.api.get(f"/import-profiles/{profile_key}/check"))
    assert (check["state"], check["sourceFileId"]) == ("completed", source["id"]), check
    return following, check


def _run_within(world, seconds: float) -> None:
    """The worker run to idle in a thread; a run still going after ``seconds`` fails the test
    rather than hanging it."""
    done = threading.Event()

    def run() -> None:
        _run(world)
        done.set()

    threading.Thread(target=run, daemon=True).start()
    assert done.wait(seconds), f"the worker did not finish within {seconds} s"


def _items(world, workspace: str) -> int:
    return ok(world.api.get("/objects/j34-item", workspaceKey=workspace, includeTotal=True))["totalCount"]


@pytest.mark.journey("J35.1")
@pytest.mark.structures("K")
def test_the_next_version_is_checked_before_anything_loads(world, monkeypatch):
    """Given W1 loaded through its profile. When W1′ is uploaded to the profile. Then the check
    reports the new column Y, Ln renamed (not one missing and one new), the new T value, the two
    records missing from the file and the five names that drifted; the load would create three
    records and update five; nothing is written.

    Regression (A5c, found measuring W1′ at 10,000 rows): the check stopped for ever at binding's
    first lease renewal, which waited for the check's own lock on its job row. The renewal comes
    every ``CHECK_ROWS`` rows, here every 50, so 200 rows reach it."""
    workspace, profile_key, book = _loaded(world)
    # The profile's last load is W1's, into a change set since published.
    last = ok(world.api.get(f"/import-profiles/{profile_key}"))["lastLoad"]
    assert (last["outcome"], last["counts"]["created"] > 0, last["publicationId"] is not None) == ("published", True, True)
    monkeypatch.setattr(import_binding, "CHECK_ROWS", 50)
    following = workbooks.w1_next(rows=200)
    ok(
        _upload(world, {"profileKey": profile_key}, "catalogue-v2.xlsx", following.content, workspaceKey=workspace),
        201,
    )
    _run_within(world, 60)
    check = ok(world.api.get(f"/import-profiles/{profile_key}/check"))
    assert check["state"] == "completed", check

    assert check["valid"] is True and check["problems"] == []
    (source,) = check["sources"]
    assert source["columns"] == {
        "new": [{"column": following.header("Y"), "letter": following.column("Y")}],
        "missing": [],
        "renamed": [
            {"from": book.header("Ln"), "to": following.header("Ln"), "letter": book.column("Ln"), "shared": 1.0}
        ],
    }
    assert (source["newValues"], source["drift"], source["missingRecords"]) == (1, 5, 2)

    path = f"/import-profiles/{profile_key}/check"
    (new_value,) = _all(world, f"{path}/new-values")
    assert (new_value["column"], new_value["value"], new_value["created"]) == (book.header("T"), "Bamboo", True)
    drift = _all(world, f"{path}/drift")
    assert {item["name"] for item in drift} == {row["N"] for row in following.rows[:5]}
    assert all(item["recordName"] == item["name"].removesuffix(" (new)") for item in drift)
    missing = _all(world, f"{path}/missing-records")
    assert sorted(item["key"] for item in missing) == [row["K"] for row in book.rows[:2]]

    (figures,) = check["dryRun"]["sources"]
    assert figures["records"] | {"unchanged": 0} == {"created": 3, "updated": 5, "unchanged": 0, "deleted": 0}
    assert (figures["missingRecords"], figures["rejections"]) == (2, [])
    rows = _all(world, f"{path}/rows", source=0, status="rejected")
    assert rows == []

    assert _items(world, workspace) == len(book.rows)
    materials = ok(world.api.get("/objects/j34-material", workspaceKey=workspace, includeTotal=True))
    # W1's load created its materials (its placeholders too, D77); the new one is not among them.
    assert materials["totalCount"] == len(book.distinct("T"))


def _accept_rename(world, profile_key: str, before: str, after: str, **source_changes: Any) -> dict[str, Any]:
    """The profile with the renamed column under its new header (what Accept does), and any other
    change to its source."""
    stored = ok(world.api.get(f"/import-profiles/{profile_key}"))
    sources = copy.deepcopy(stored["sources"])
    for binding in sources[0]["columns"]:
        if binding.get("column") == before:
            binding["column"] = after
    sources[0].update(source_changes)
    body = {"name": stored["name"], "sources": sources, "valueMaps": stored["valueMaps"], "expectedVersion": stored["version"]}
    return ok(world.api.put(f"/import-profiles/{profile_key}", body))


@pytest.mark.journey("J35.2")
@pytest.mark.structures("K")
def test_records_missing_from_the_next_version_are_kept_or_deleted_in_a_change_set(world):
    """Given W1′ checked, its rename accepted and the file checked again. When it is loaded into a change set with missing:
    report, then into another with missing: delete. Then the first keeps the two records missing
    from the file and lists none removed; the second removes exactly them; a live load with
    missing: delete is refused MISSING_DELETE_NEEDS_CHANGE_SET."""
    workspace, profile_key, book = _loaded(world)
    following, check = _next_version(world, workspace, profile_key)
    _accept_rename(world, profile_key, book.header("Ln"), following.header("Ln"))
    source_id = check["sourceFileId"]
    again = ok(world.api.post(f"/import-profiles/{profile_key}/check", {}), 202)
    assert again["state"] == "checking" and again["jobId"] != check["jobId"]
    _run(world)
    again = ok(world.api.get(f"/import-profiles/{profile_key}/check"))
    assert again["state"] == "completed" and again["sources"][0]["columns"]["renamed"] == []

    kept = world.change_set(workspace, name="Keep missing")
    job = ok(_load(world, workspace, profile_key, source_id, kept), 202)
    _run(world)
    done = ok(world.api.get(f"/jobs/{job['id']}"))
    assert (done["state"], done["counts"]["rejected"]) == ("completed", 0), done
    review = _all(world, f"/change-sets/{kept['id']}/object-changes", objectTypeKey="j34-item")
    assert {item["kind"] for item in review} == {"added", "changed"}
    assert sum(item["kind"] == "added" for item in review) == 3
    last = ok(world.api.get(f"/import-profiles/{profile_key}"))["lastLoad"]
    assert (last["outcome"], last["changeSetId"], last["sourceFileId"]) == ("inChangeSet", kept["id"], source_id)

    _accept_rename(world, profile_key, book.header("Ln"), following.header("Ln"), missing="delete")
    refused(_load(world, workspace, profile_key, source_id, None), 422, "MISSING_DELETE_NEEDS_CHANGE_SET")
    deleting = world.change_set(workspace, name="Delete missing")
    job = ok(_load(world, workspace, profile_key, source_id, deleting), 202)
    _run(world)
    assert ok(world.api.get(f"/jobs/{job['id']}"))["state"] == "completed"
    review = _all(world, f"/change-sets/{deleting['id']}/object-changes", objectTypeKey="j34-item")
    removed = [item for item in review if item["kind"] == "removed"]
    assert sorted(item["before"]["name"] for item in removed) == sorted(row["N"] for row in book.rows[:2])
    # Discarded, its load is gone: the profile says so rather than showing it as pending.
    version = ok(world.api.get(f"/change-sets/{deleting['id']}"))["version"]
    ok(world.api.delete(f"/change-sets/{deleting['id']}", expectedVersion=version), 204)
    listed = next(p for p in _all(world, "/import-profiles") if p["key"] == profile_key)
    assert listed["lastLoad"]["outcome"] == "discarded"
    assert _items(world, workspace) == len(book.rows)


def _without(node: Any, key: str) -> Any:
    """The model part without any list entry naming ``key`` (the views' generated columns)."""
    if isinstance(node, list):
        return [
            _without(item, key)
            for item in node
            if item != key and not (isinstance(item, dict) and key in item.values())
        ]
    if isinstance(node, dict):
        return {name: _without(value, key) for name, value in node.items()}
    return node


@pytest.mark.journey("J35.3")
@pytest.mark.structures("K")
def test_a_profile_a_newer_release_broke_is_listed_at_its_binding_and_refused(world):
    """Given a profile mapping X to an item attribute, saved at installation. When a newer release
    without that attribute on items is activated and a file is uploaded to the profile. Then the
    check lists ATTRIBUTE_NOT_BOUND at the binding's pointer and reads nothing, and a load through
    the profile is refused INVALID_IMPORT_PROFILE."""
    draft, book, _source, workspace = _onboarding(world)
    _map_by_hand(world, draft, book)
    _step(world, draft, {"kind": "mapColumn", "source": "items", "column": book.header("X"), "binding": {"attributeTypeKey": "j34-supplier"}})
    release = _install(world, draft)
    ok(world.activate(release["id"]))
    profile_key = release["importProfile"]["key"]

    model = copy.deepcopy(ok(world.api.get(f"/model-releases/{release['id']}", includeModel=True))["model"])
    item = next(t for t in model["objectTypes"] if t["key"] == "j34-item")
    item["attributes"] = [b for b in item["attributes"] if b["attributeTypeKey"] != "j34-supplier"]
    model["applications"] = _without(model["applications"], "j34-supplier")
    model["release"]["version"] = "1.2.0"
    ok(world.activate(world.install(model)["id"]))

    source = _profiled(world, {"profileKey": profile_key}, "catalogue.xlsx", book.content, workspaceKey=workspace)
    check = ok(world.api.get(f"/import-profiles/{profile_key}/check"))
    assert check["state"] == "completed" and check["valid"] is False
    stored = ok(world.api.get(f"/import-profiles/{profile_key}"))
    at = next(i for i, b in enumerate(stored["sources"][0]["columns"]) if b.get("attributeTypeKey") == "j34-supplier")
    assert {"path": f"/sources/0/columns/{at}/attributeTypeKey", "code": "ATTRIBUTE_NOT_BOUND"} in [
        {"path": p["path"], "code": p["code"]} for p in check["problems"]
    ]
    assert check["dryRun"] is None and check["sources"][0]["source"] is None
    refused(_load(world, workspace, profile_key, source["id"], world.change_set(workspace)), 422, "INVALID_IMPORT_PROFILE")


@pytest.mark.journey("J35.2")
@pytest.mark.structures("K")
def test_a_draft_source_says_what_a_load_does_with_records_missing_from_the_file(world):
    """Given W1 mapped in a draft. When setMissing asks a keyed source to delete, then a source
    without a key. Then the draft's profile reads missing: delete for the first, and its undo puts
    it back; the second is refused INVALID_OPERATION (invalidValue)."""
    draft, book, _source, _workspace = _onboarding(world)
    _map_by_hand(world, draft, book)
    _step(world, draft, {"kind": "setMissing", "source": "items", "missing": "delete"})
    (items,) = ok(world.api.get(f"/model-drafts/{draft['id']}/profile"))["definition"]["sources"]
    assert items["missing"] == "delete"
    # Its audit entry names the profile it changed (0.10 R-F11).
    with SessionLocal() as session:
        changed = session.scalar(
            text(
                "SELECT changes -> 'changedFields' FROM audit_events WHERE aggregate_type = 'model_draft'"
                " AND aggregate_id = :id ORDER BY sequence_id DESC LIMIT 1"
            ),
            {"id": draft["id"]},
        )
    assert "profile" in changed and "name" not in changed
    version = ok(world.api.get(f"/model-drafts/{draft['id']}"))["version"]
    ok(world.api.post(f"/model-drafts/{draft['id']}/undo", {"expectedVersion": version}))
    (items,) = ok(world.api.get(f"/model-drafts/{draft['id']}/profile"))["definition"]["sources"]
    assert "missing" not in items

    _step(world, draft, {"kind": "setSource", "source": "items", "key": None})
    version = ok(world.api.get(f"/model-drafts/{draft['id']}"))["version"]
    answer = world.api.post(
        f"/model-drafts/{draft['id']}/operations",
        {"expectedVersion": version, "operations": [{"kind": "setMissing", "source": "items", "missing": "delete"}]},
    )
    assert refused(answer, 422, "INVALID_OPERATION")["details"]["reason"] == "invalidValue"


@pytest.mark.journey("J35.1")
@pytest.mark.structures("K")
def test_the_next_version_of_an_inferred_workbook_is_checked_in_seconds(world):
    """0.10 R (found by the composed runner). Given W1 onboarded through its proposals, with its
    translation sheet's 1,400 related records loaded and published. When W1′ is uploaded to the
    saved profile. Then its check ends within 20 s: finding each row's stored translation compared
    every candidate with every relationship, 53 s of a 56 s check."""
    draft, _book, source, workspace = _inferred(world)
    ok(world.api.post(f"/model-drafts/{draft['id']}/inference/application", {"expectedVersion": _version(world, draft)}))
    _run(world)
    release = _install(world, draft)
    ok(world.activate(release["id"]))
    profile_key = release["importProfile"]["key"]
    change_set = world.change_set(workspace)
    ok(_load(world, workspace, profile_key, source["id"], change_set), 202)
    _run(world)
    world.publish(change_set, workspace)
    following = workbooks.w1_next(rows=200)
    ok(_upload(world, {"profileKey": profile_key}, "catalogue-v2.xlsx", following.content, workspaceKey=workspace), 201)
    _run_within(world, 20)
    check = ok(world.api.get(f"/import-profiles/{profile_key}/check"))
    assert check["state"] == "completed", check
