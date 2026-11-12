"""J36.13 — A new workspace from a workbook, in one step (USER_JOURNEYS.md, 0.17 PL4, PP-D1, PP-D44).

An administrator hands over the draft a workbook made and a name; one route installs it as a release,
creates the workspace on it and queues the workbook's load into the workspace's live data. As in
``test_j36_workspace_resources``, each test runs on one configuration with the workbook's own model
beside it; the journey application runs no worker thread, so a test runs the job worker itself.
"""

import io
from uuid import uuid4

import pytest
import workbooks
from openpyxl import load_workbook
from scenario import ok, refused
from test_j34_onboard import _application, _infer, _profiled, _run, _version
from test_j36_workspace_models import BOTH, _model
from test_j36_workspace_resources import _profile, _release_key
from test_j40_authorization import _client


def _draft(world, *, profile_key: str | None = None, content: bytes | None = None):
    """A draft started empty under a new model key with a workbook profiled and its new-model
    proposals applied (``profile_key`` names its profile, as a person may); the draft."""
    schema = ok(world.api.get("/system"))["schemaLanguages"][-1]
    name = f"Workbook {uuid4().hex[:6]}"
    empty = {
        "schemaVersion": schema,
        "release": {"key": f"workbook-{uuid4().hex[:8]}", "name": name, "version": "1.0.0"},
        "product": {"name": name},
        "attributeTypes": [],
        "objectTypes": [],
        "relationTypes": [],
        "objectTypeRelations": [],
        "applications": [],
    }
    draft = ok(world.api.post("/model-drafts", {"name": name, "model": empty}), 201)
    _profiled(
        world, {"draftId": draft["id"]}, "catalogue.xlsx", content or workbooks.w1(rows=40).content
    )
    _infer(world, draft)
    assert ok(_application(world, draft))["valid"] is True
    if profile_key is not None:
        ok(
            world.api.post(
                f"/model-drafts/{draft['id']}/operations",
                {
                    "expectedVersion": _version(world, draft),
                    "operations": [{"kind": "setProfile", "key": profile_key}],
                },
            )
        )
    return draft


def _create(world, draft, name="Catalogue", version=None, **extra):
    body = {
        "draftId": draft["id"],
        "expectedVersion": version or _version(world, draft),
        "name": name,
        **extra,
    }
    return world.api.post("/workspaces/from-workbook", body)


def _without_a_key(content: bytes) -> bytes:
    """The workbook with the item code of the fourth row of its names sheet emptied: a row the load refuses, among rows it
    accepts."""
    book = load_workbook(io.BytesIO(content))
    sheet = book[workbooks.S2]
    key = [cell.value for cell in sheet[1]].index(workbooks.S2_HEADERS["K"]) + 1
    sheet.cell(row=4, column=key).value = None
    out = io.BytesIO()
    book.save(out)
    return out.getvalue()


@pytest.mark.journey("J36.13")
@pytest.mark.structures(*BOTH)
def test_a_workbook_becomes_a_workspace_with_its_records(world):
    """Given X in the default workspace and a draft made from a workbook. When an administrator
    creates a workspace from it with a name. Then the answer is 202 with the new workspace, the release
    and the import job; the job loads every row into the new workspace; the workspace runs the
    installed release and shows its records; the default workspace still runs X at its version; and
    the draft is the new workspace's own."""
    before = _model(world)
    draft = _draft(world)

    answer = ok(_create(world, draft, "Office catalogue"), 202)
    workspace = answer["workspace"]
    assert (workspace["label"], workspace["status"]) == ("Office catalogue", "active")
    assert workspace["key"] == "office-catalogue"
    assert (answer["job"]["kind"], answer["job"]["workspaceKey"]) == ("import", workspace["key"])

    _run(world)
    done = ok(world.api.get(f"/jobs/{answer['job']['id']}"))
    assert (done["state"], done["counts"]["rejected"]) == ("completed", 0), done
    assert done["counts"]["created"] > 0
    running = ok(world.api.get(f"/workspaces/{workspace['key']}/model"))
    assert running["releaseId"] == answer["releaseId"]
    assert running["releaseKey"] == answer["releaseKey"] != _release_key(world)
    records = ok(world.api.get("/objects", workspaceKey=workspace["key"], pageSize=5))
    assert records["items"]
    assert _model(world) == before
    assert ok(world.api.get(f"/model-drafts/{draft['id']}"))["workspaceKey"] == workspace["key"]


@pytest.mark.journey("J36.13")
@pytest.mark.structures(*BOTH)
def test_a_profile_key_another_model_holds_does_not_refuse(world):
    """Given X's import profile P and a draft of a new model whose profile has P's key, which
    installing it alone refuses. When the workspace is created from the draft. Then it is created and
    the workbook loads; P is still X's, at its version."""
    taken = ok(world.api.post("/import-profiles", _profile(world)), 201)
    draft = _draft(world, profile_key=taken["key"])

    answer = ok(_create(world, draft), 202)
    _run(world)
    done = ok(world.api.get(f"/jobs/{answer['job']['id']}"))
    assert (done["state"], done["counts"]["rejected"]) == ("completed", 0), done
    after = ok(world.api.get(f"/import-profiles/{taken['key']}"))
    assert (after["version"], after["modelKey"]) == (1, _release_key(world))


@pytest.mark.journey("J36.13")
@pytest.mark.structures(*BOTH)
def test_a_refused_row_is_reported_and_the_rest_load(world):
    """Given a workbook with one translation row without its item code. When the workspace is
    created from its draft and the load ends. Then the job is completed with that row rejected, the
    other rows created, and the rejected row is listed with its code."""
    draft = _draft(world, content=_without_a_key(workbooks.w1(rows=40).content))

    answer = ok(_create(world, draft), 202)
    _run(world)
    done = ok(world.api.get(f"/jobs/{answer['job']['id']}"))
    assert done["state"] == "completed", done
    assert done["counts"]["rejected"] >= 1 and done["counts"]["created"] >= 30, done
    rows = ok(world.api.get(f"/jobs/{answer['job']['id']}/rows", status="rejected"))["items"]
    assert rows and all(row["status"] == "rejected" for row in rows)


@pytest.mark.journey("J36.13")
@pytest.mark.structures(*BOTH)
def test_a_draft_that_does_not_hold_is_refused_with_its_problems_and_nothing_is_made(world):
    """Given a draft without a workbook, and a draft with one whose model no longer compiles. When
    a workspace is created from each. Then the first is `422 DRAFT_HAS_NO_WORKBOOK`, the second `422
    INVALID_MODEL` listing the model's diagnostics; a draft read at an older version is `409
    VERSION_CONFLICT`; no workspace and no release is added."""
    workspaces = ok(world.api.get("/workspaces", pageSize=100))["items"]
    releases = ok(world.api.get("/model-releases", pageSize=100))["items"]
    release = ok(
        world.api.get(f"/model-releases/{world.workspace_model()['releaseId']}", includeModel=True)
    )
    bare = ok(
        world.api.post(
            "/model-drafts",
            {"name": "No book", "model": release["model"], "baseReleaseId": release["id"]},
        ),
        201,
    )
    refused(_create(world, bare), 422, "DRAFT_HAS_NO_WORKBOOK")

    draft = _draft(world)
    stale = {"draftId": draft["id"], "expectedVersion": _version(world, draft) - 1, "name": "Late"}
    refused(world.api.post("/workspaces/from-workbook", stale), 409, "VERSION_CONFLICT")
    model = ok(world.api.get(f"/model-drafts/{draft['id']}"))["model"]
    model["objectTypeRelations"].append(
        {
            "key": "broken",
            "relationTypeKey": "nowhere",
            "sourceObjectTypeKey": "nowhere",
            "targetObjectTypeKey": "nowhere",
        }
    )
    ok(
        world.api.patch(
            f"/model-drafts/{draft['id']}",
            {"expectedVersion": _version(world, draft), "model": model},
        )
    )
    error = refused(_create(world, draft), 422, "INVALID_MODEL")
    assert error["details"]

    assert ok(world.api.get("/workspaces", pageSize=100))["items"] == workspaces
    assert ok(world.api.get("/model-releases", pageSize=100))["items"] == releases


@pytest.mark.journey("J36.13")
@pytest.mark.structures(*BOTH)
def test_a_caller_without_the_groups_is_refused_by_code(world):
    """Given a draft made from a workbook. When callers each holding some of the groups call the route
    (Workspace administration, Install a model or Model release, Bulk and import, all at the instance).
    Then each is refused with `403 FORBIDDEN` naming the action and groups it lacks, in that order,
    and the holder of all three is answered 202."""
    draft = _draft(world)
    version = _version(world, draft)
    cases = [
        (
            [("model-admin", {"instance": True}), ("owner", {"instance": True})],
            "workspaces.create-from-workbook",
            ["workspace-admin"],
        ),
        (
            [("workspace-admin", {"instance": True}), ("owner", {"instance": True})],
            "model.install",
            ["model-release", "model-install"],
        ),
        (
            [("workspace-admin", {"instance": True}), ("model-admin", {"instance": True})],
            "bulk.write",
            ["bulk"],
        ),
    ]
    for index, (grants, action, groups) in enumerate(cases):
        _, caller = _client(world, f"From workbook {index}", *grants)
        error = refused(_create(caller, draft, version=version), 403, "FORBIDDEN")
        assert error["details"] == {"action": action, "groups": groups, "workspaceKey": None}
    _, allowed = _client(
        world,
        "From workbook allowed",
        ("workspace-admin", {"instance": True}),
        ("model-admin", {"instance": True}),
        ("owner", {"instance": True}),
    )
    ok(_create(allowed, draft, version=version), 202)
