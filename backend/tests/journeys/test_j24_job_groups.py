"""J24.9 — Related jobs grouped (0.13 JG): the jobs of an assistant task's session and of a model
draft come back as one row each, with their count and states; ``origin`` lists one group's jobs.
A task's session is a stand-in working through the API with the token the engine gave it, so which
jobs belong to the task is the engine's. Each case runs on two configurations."""

import pytest
import workbooks
from scenario import ok, refused
from test_j24_job_stream import served  # noqa: F401
from test_j34_onboard import (
    _all,
    _draft,
    _dry_run,
    _item_type,
    _materials,
    _profile,
    _profiled,
    _workspace,
)
from test_j50_ai_way_out import STRUCTURES, Way, _fresh_fake, _loaded  # noqa: F401
from test_j50_ai_workbook_load import Ledgers


def _items(world):
    return [
        {
            "op": "create",
            "applicationKey": world.app("K"),
            "objectTypeKey": world.key("K"),
            "name": "Alone",
            "attributes": [
                {"attributeTypeKey": k, "value": v} for k, v in world.required_values("K").items()
            ],
        }
    ]


def _grouped(world, **params):
    return _all(world, "/jobs", page_size=100, grouped="true", **params)


def _group(rows, kind, identifier):
    (row,) = [r for r in rows if r["group"] and r["group"]["origin"]["id"] == identifier]
    assert row["group"]["origin"]["kind"] == kind
    return row


@pytest.mark.journey("J24.9")
@pytest.mark.structures("K")
def test_a_drafts_dry_runs_are_one_group_and_a_job_without_origin_stays_alone(world):
    """Given a draft with two dry runs and a batch that belongs to neither. Then the grouped list
    has the draft as one row of two completed jobs named as the draft, newest first, and the batch
    as a row of its own; origin lists the two dry runs, each saying where it comes from; the flat
    list still holds every job, and a state that none of the group's jobs have leaves it out."""
    workspace = _workspace(world)
    book = workbooks.w1(rows=20)
    _materials(world, book, workspace)
    draft = _draft(world)
    keys = _item_type(world, draft)
    source = _profiled(world, {"draftId": draft["id"]}, "catalogue.xlsx", book.content)
    profile = _profile(world, book, keys)
    first = _dry_run(world, draft, source, workspace, profile)
    second = _dry_run(world, draft, source, workspace, profile)
    batch = ok(
        world.api.post(
            "/batches",
            {
                "workspaceKey": workspace,
                "policy": "independent",
                "run": "inline",
                "items": _items(world),
            },
        )
    )["job"]

    rows = _grouped(world, workspaceKey=workspace)
    group = _group(rows, "modelDraft", draft["id"])["group"]
    assert group["origin"]["name"] == draft["name"]
    assert group["jobs"] == 2 and group["states"]["completed"] == 2
    assert sum(group["states"].values()) == 2
    single = [r for r in rows if r["group"] is None]
    assert [r["job"]["id"] for r in single] == [batch["id"]] and single[0]["job"]["origin"] is None
    assert _group(rows, "modelDraft", draft["id"])["job"]["id"] == second["jobId"]

    listed = _all(world, "/jobs", origin=f"modelDraft:{draft['id']}")
    assert [j["id"] for j in listed] == [second["jobId"], first["jobId"]]
    assert {j["origin"]["id"] for j in listed} == {draft["id"]}
    assert _all(world, "/jobs", origin=f"modelDraft:{draft['id']}", state="failed") == []
    flat = {j["id"] for j in _all(world, "/jobs", workspaceKey=workspace)}
    assert {first["jobId"], second["jobId"], batch["id"]} <= flat
    assert ok(world.api.get(f"/jobs/{first['jobId']}"))["origin"]["name"] == draft["name"]

    page = ok(world.api.get("/jobs", grouped="true", workspaceKey=workspace, pageSize=1))
    assert len(page["items"]) == 1 and page["nextCursor"]
    refused(world.api.get("/jobs", origin="aiTask"), 422, "INVALID_ORIGIN")


@pytest.mark.journey("J24.9")
@pytest.mark.structures(*STRUCTURES)
def test_a_tasks_session_jobs_are_the_tasks_group(
    world,
    tmp_path,
    monkeypatch,
    served,  # noqa: F811
):
    """Given an assistant task whose session loaded the workbook through the API. Then the task's
    own job and the batch its session queued are one group named as the task's file, the batch says
    it comes from the task, and origin lists both."""
    monkeypatch.setenv("AI_AGENT_API_URL", served)
    ledgers = Ledgers(world)
    way = Way(world, tmp_path, monkeypatch, ledgers)
    task = _loaded(world, way, ledgers)

    group = _group(_grouped(world, workspaceKey=ledgers.workspace), "aiTask", task["id"])["group"]
    assert group["origin"]["name"] == task["fileName"] == "ledgers.xlsx"
    listed = _all(world, "/jobs", origin=f"aiTask:{task['id']}")
    assert group["jobs"] == len(listed) >= 2
    assert {"aiTask", "batch"} <= {j["kind"] for j in listed}
    assert {j["origin"]["id"] for j in listed} == {task["id"]}
    (one,) = _grouped(world, origin=f"aiTask:{task['id']}")
    assert one["group"]["jobs"] == group["jobs"]
