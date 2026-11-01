"""J50 — A re-import finds its records by several columns (0.16 AP10, AP-D43).

A price file repeats one ID on two rows and tells them apart by a second column. The source's key
names both attributes; a second load updates each record and creates none. The tests use the
structure ``K`` and its two attributes, so they name no configuration's keys, and import through the
public API; the journey application runs no worker thread, a test runs the job worker itself.
"""

import json
from typing import Any
from uuid import uuid4

import pytest
from scenario import ok, refused

CSV = "text/csv"


def _workspace(world) -> str:
    key = f"combo-{uuid4().hex[:8]}"
    ok(world.api.post("/workspaces", {"key": key, "label": "Combination key"}), 201)
    return key


def _profile(world, **source: Any) -> dict[str, Any]:
    """One source of ``K`` keyed by its two attributes together; ``source`` overrides the rest."""
    return {
        "sources": [
            {
                "applicationKey": world.app("K"),
                "objectTypeKey": world.key("K"),
                "key": {"attributeTypeKeys": [world.key("K.code"), world.key("K.rank")]},
                "columns": [
                    {"column": "name", "field": "name"},
                    {"column": "code", "attributeTypeKey": world.key("K.code")},
                    {"column": "rank", "attributeTypeKey": world.key("K.rank")},
                ],
                **source,
            }
        ]
    }


def _send(world, rows: list[str], workspace: str, profile: dict[str, Any], **context: Any):
    request = {
        **({} if "changeSetId" in context else {"workspaceKey": workspace}),
        "policy": "independent",
        "onExisting": "overwrite",
        "stage": "execute",
        "profile": profile,
        **context,
    }
    content = ("name,code,rank\n" + "\n".join(rows) + "\n").encode()
    return world.api.upload(
        "/imports", {"file": ("prices.csv", content, CSV)}, {"request": json.dumps(request)}
    )


def _loaded(world, rows: list[str], workspace: str, profile: dict[str, Any], **context: Any):
    job = ok(_send(world, rows, workspace, profile, **context), 202)
    world.api.client.app.state.job_worker.run_until_idle()
    return ok(world.api.get(f"/jobs/{job['id']}"))


def _names(world, workspace: str, **context: Any) -> list[str]:
    page = ok(
        world.api.get(f"/objects/{world.key('K')}", workspaceKey=workspace, pageSize=100, **context)
    )
    return sorted(item["name"] for item in page["items"])


def _row_codes(world, job: dict[str, Any]) -> list[str | None]:
    rows = ok(world.api.get(f"/jobs/{job['id']}/rows", pageSize=50))["items"]
    return [o["error"]["code"] for r in rows for o in r["outcomes"] if o.get("error")]


FIRST = ["Alpha one,A,1", "Alpha two,A,2", "Beta one,B,1"]
AGAIN = ["Alpha 1,A,1", "Alpha 2,A,2", "Beta 1,B,1"]


@pytest.mark.journey("J50.42")
@pytest.mark.structures("K", "K.code", "K.rank")
def test_a_reimport_by_two_columns_updates_each_record_and_creates_none(world):
    """Given a file whose first column repeats (A twice) and whose two columns together identify
    every row. When it is loaded and then loaded again with other names, live and in a change set.
    Then the second load updates the three records and creates none; in the change set the live
    records stay as they were."""
    workspace = _workspace(world)
    first = _loaded(world, FIRST, workspace, _profile(world))
    assert (first["state"], first["counts"]["created"], first["counts"]["rejected"]) == (
        "completed",
        3,
        0,
    ), first
    assert _names(world, workspace) == sorted(r.split(",")[0] for r in FIRST)

    in_set = world.change_set(workspace=workspace)
    staged = _loaded(
        world,
        AGAIN,
        workspace,
        _profile(world),
        changeSetId=in_set["id"],
        expectedChangeSetVersion=in_set["version"],
    )
    assert (staged["counts"]["created"], staged["counts"]["updated"]) == (0, 3), staged
    assert _names(world, workspace, changeSetId=in_set["id"]) == sorted(
        r.split(",")[0] for r in AGAIN
    )
    assert _names(world, workspace) == sorted(r.split(",")[0] for r in FIRST)

    live = _loaded(world, AGAIN, workspace, _profile(world))
    assert (live["counts"]["created"], live["counts"]["updated"]) == (0, 3), live
    assert _names(world, workspace) == sorted(r.split(",")[0] for r in AGAIN)


@pytest.mark.journey("J50.42")
@pytest.mark.structures("K", "K.code", "K.rank")
def test_a_combination_two_stored_records_hold_refuses_its_row(world):
    """Given two stored records holding one code and rank. When a file names that combination and
    another. Then the row naming it is refused KEY_AMBIGUOUS, its message naming both columns'
    values, and the other row loads."""
    workspace = _workspace(world)
    for name in ("Twin one", "Twin two"):
        values = {"K.code": "T", "K.rank": 7}
        ok(world.create("K", name, workspace=workspace, values=values), 201)
    done = _loaded(world, ["Twin,T,7", "Single,S,1"], workspace, _profile(world))
    assert (done["counts"]["rejected"], done["counts"]["created"]) == (1, 1), done
    assert _row_codes(world, done) == ["KEY_AMBIGUOUS"]
    rows = ok(world.api.get(f"/jobs/{done['id']}/rows", pageSize=50))["items"]
    messages = [o["error"]["message"] for r in rows for o in r["outcomes"] if o.get("error")]
    assert all("code = T" in m and "rank = 7" in m for m in messages), messages
    assert "Single" in _names(world, workspace)


@pytest.mark.journey("J50.42")
@pytest.mark.structures("K", "K.code", "K.rank")
def test_an_empty_cell_in_a_key_column_follows_rows_without_key(world):
    """Given a file with one row whose rank is empty. When it is loaded by default and with
    rowsWithoutKey skip. Then by default the row is refused MISSING_RECORD_KEY; with skip it is
    counted skipped and the others load."""
    workspace = _workspace(world)
    rows = ["Alpha,A,1", "Blank,A,", "Beta,B,1"]
    refusing = _loaded(world, rows, workspace, _profile(world))
    assert refusing["counts"]["rejected"] == 1, refusing
    assert _row_codes(world, refusing) == ["MISSING_RECORD_KEY"]

    other = _workspace(world)
    skipping = _loaded(world, rows, other, _profile(world, rowsWithoutKey="skip"))
    assert (skipping["counts"]["rejected"], skipping["counts"]["created"]) == (0, 2), skipping
    assert skipping["bindingReport"][0]["skippedRows"] == 1
    assert _names(world, other) == ["Alpha", "Beta"]


@pytest.mark.journey("J50.42")
@pytest.mark.structures("K", "K.code", "K.rank")
def test_a_profile_keyed_by_a_combination_is_checked(world):
    """A combination naming an attribute no column binds, or an unknown one, is refused with the
    single key's codes at the combination's pointer."""
    workspace = _workspace(world)
    unbound = _profile(world, columns=[{"column": "name", "field": "name"}])
    error = refused(_send(world, FIRST, workspace, unbound), 422, "INVALID_IMPORT_PROFILE")
    assert {(p["path"], p["code"]) for p in error["details"]["problems"]} >= {
        ("/sources/0/key/attributeTypeKeys", "KEY_NOT_BOUND")
    }, error
    unknown = _profile(world, key={"attributeTypeKeys": [world.key("K.code"), "no-such-attribute"]})
    error = refused(_send(world, FIRST, workspace, unknown), 422, "INVALID_IMPORT_PROFILE")
    assert ("/sources/0/key/attributeTypeKeys", "UNKNOWN_ATTRIBUTE") in {
        (p["path"], p["code"]) for p in error["details"]["problems"]
    }, error
