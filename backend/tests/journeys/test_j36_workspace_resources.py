"""J36 — What was instance-wide follows the workspace's model (USER_JOURNEYS.md, Base 0.11 M3).

Import profiles belong to a model (D9, D35, D36, D40); a draft is compared with its own model and
its compatibility reported for each workspace running it (D25, D37); the consumer API's index and
OpenAPI documents answer for a workspace (D10, D27). As in ``test_j36_workspace_models``, each test
runs on one configuration ``X`` with a workspace on the other generated configuration's model ``Y``
beside it, generated A beside B and B beside A. The journey application runs no worker thread: a
test runs the job worker and the event deriver itself.
"""

import copy
import json
from uuid import uuid4

import pytest
import workbooks
from scenario import W1, consumer_events, derive_events, ok, refused
from test_j27_import import _xlsx
from test_j30_consumer_events import LEDGER, _events
from test_j34_onboard import _application, _infer, _profiled, _run, _version
from test_j36_workspace_models import BOTH, _beside, _model, _on, _other

MISMATCH = "IMPORT_PROFILE_MODEL_MISMATCH"
XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def _release_key(world) -> str:
    return world.configuration.model["release"]["key"]


def _profile(world, key=None):
    """R records from a sheet, keyed by R.u, with its required values."""
    return {
        "key": key or f"rows-{uuid4().hex[:8]}",
        "name": "Rows",
        "sources": [
            {
                "sheet": "Rows",
                "applicationKey": world.app("R"),
                "objectTypeKey": world.key("R"),
                "key": {"attributeTypeKey": world.key("R.u")},
                "columns": [
                    {"column": "Number", "attributeTypeKey": world.key("R.u")},
                    {"column": "Name", "field": "name"},
                    {"column": "Owner", "attributeTypeKey": world.key("R.q")},
                    {"column": "Summary", "attributeTypeKey": world.key("R.x1")},
                ],
            }
        ],
    }


def _rows(prefix):
    header = ("Number", "Name", "Owner", "Summary")
    rows = [
        (f"{prefix}-{n}", name, "Owner", "Summary") for n, name in ((1, "First"), (2, "Second"))
    ]
    return _xlsx({"Rows": [header, *rows]})


def _import(world, workspace, profile_key, content):
    request = {
        "workspaceKey": workspace,
        "profileKey": profile_key,
        "policy": "independent",
        "onExisting": "overwrite",
        "stage": "execute",
    }
    return world.api.upload(
        "/imports",
        {"file": ("rows.xlsx", content, XLSX)},
        {"request": json.dumps(request)},
    )


def _imported(world, workspace, profile_key, content):
    job = ok(_import(world, workspace, profile_key, content), 202)
    _run(world)
    done = ok(world.api.get(f"/jobs/{job['id']}"))
    assert (done["state"], done["counts"]["rejected"]) == ("completed", 0), done
    return done


def _mismatch(response, model_key, workspace_model_key):
    details = refused(response, 422, MISMATCH)["details"]
    assert (details["modelKey"], details["workspaceModelKey"]) == (model_key, workspace_model_key)


def _workbook_model(world, profile_key):
    """A draft started empty under a new model key with W1 profiled, its new-model proposals
    applied and its profile named ``profile_key``: the draft and the model key."""
    schema = ok(world.api.get("/system"))["schemaLanguages"][-1]
    model_key = f"workbook-{uuid4().hex[:8]}"
    empty = {
        "schemaVersion": schema,
        "release": {"key": model_key, "name": "Workbook", "version": "1.0.0"},
        "product": {"name": "Workbook"},
        "attributeTypes": [],
        "objectTypes": [],
        "relationTypes": [],
        "objectTypeRelations": [],
        "applications": [],
    }
    draft = ok(world.api.post("/model-drafts", {"name": "Workbook", "model": empty}), 201)
    book = workbooks.w1(rows=50)
    source = _profiled(world, {"draftId": draft["id"]}, "catalogue.xlsx", book.content)
    _infer(world, draft)
    assert ok(_application(world, draft))["valid"] is True
    named = {"kind": "setProfile", "key": profile_key}
    ok(
        world.api.post(
            f"/model-drafts/{draft['id']}/operations",
            {"expectedVersion": _version(world, draft), "operations": [named]},
        )
    )
    return draft, model_key, source


def _install(world, draft):
    return world.api.post(
        f"/model-drafts/{draft['id']}/installation", {"expectedVersion": _version(world, draft)}
    )


@pytest.mark.journey("J36.4")
@pytest.mark.structures(*BOTH)
def test_a_new_model_from_a_workbook_runs_in_a_new_workspace(world):
    """Given X in the default workspace. When a draft started empty under a new model key has its
    workbook's proposals applied, is compiled, installed, and a workspace is created on its release.
    Then the compilation reports no workspace and every change as added; the default workspace still
    runs X at its version; the profile saved at installation belongs to the new model and loads the
    workbook into the new workspace; named in the default workspace it is refused."""
    before = _model(world)
    draft, model_key, source = _workbook_model(world, f"workbook-{uuid4().hex[:8]}")

    compiled = ok(
        world.api.post(
            f"/model-drafts/{draft['id']}/compile", {"expectedVersion": _version(world, draft)}
        )
    )
    assert compiled["valid"] is True
    assert compiled["compatibility"]["workspaces"] == []
    assert compiled["againstReleaseId"] is None
    assert compiled["changes"] and {c["kind"] for c in compiled["changes"]} == {"added"}

    release = ok(_install(world, draft), 201)
    key = _on(world, release["id"])
    assert _model(world) == before
    profile_key = release["importProfile"]["key"]
    profile = ok(world.api.get(f"/import-profiles/{profile_key}", workspaceKey=key))
    assert (profile["modelKey"], profile["valid"]) == (model_key, True)

    request = {
        "workspaceKey": key,
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
    assert done["counts"]["created"] > 0

    elsewhere = {**request, "workspaceKey": W1}
    _mismatch(
        world.api.upload("/imports", {}, {"request": json.dumps(elsewhere)}),
        model_key,
        _release_key(world),
    )


@pytest.mark.journey("J36.4")
@pytest.mark.structures(*BOTH)
def test_a_draft_profile_is_not_installed_over_another_models_profile(world):
    """Given X's profile P. When a draft of a new model whose profile has P's key is installed. Then
    it is refused naming P, its model and the draft's; nothing is installed and P is unchanged."""
    taken = ok(world.api.post("/import-profiles", _profile(world)), 201)
    draft, model_key, _source = _workbook_model(world, taken["key"])
    releases = ok(world.api.get("/model-releases", pageSize=100))["items"]

    details = refused(_install(world, draft), 409, MISMATCH)["details"]
    assert (details["profileKey"], details["modelKey"], details["draftModelKey"]) == (
        taken["key"],
        _release_key(world),
        model_key,
    )
    assert ok(world.api.get("/model-releases", pageSize=100))["items"] == releases
    after = ok(world.api.get(f"/import-profiles/{taken['key']}"))
    assert (after["version"], after["sources"], after["modelKey"]) == (
        1,
        taken["sources"],
        _release_key(world),
    )


@pytest.mark.journey("J36.4")
@pytest.mark.structures(*BOTH)
def test_a_draft_profile_key_taken_by_another_model_is_an_issue_with_a_free_key(world):
    """Given X's profile P and a draft of a new model whose profile has P's key. When the draft's
    profile is read, then the conflict is an error at /profile/key naming P's model and a free key;
    the installation's refusal names the same key. When the profile is given that key, the issue is
    gone and the draft installs (0.16, found by the user: the editor had no sign of it)."""
    taken = ok(world.api.post("/import-profiles", _profile(world)), 201)
    draft, model_key, _source = _workbook_model(world, taken["key"])
    issues = [
        d
        for d in ok(world.api.get(f"/model-drafts/{draft['id']}/profile"))["diagnostics"]
        if d["code"] == MISMATCH
    ]
    assert [(d["severity"], d["path"]) for d in issues] == [("error", "/profile/key")]
    assert _release_key(world) in issues[0]["message"] and model_key in issues[0]["message"]
    free = refused(_install(world, draft), 409, MISMATCH)["details"]["freeKey"]
    assert ok(world.api.get(f"/model-drafts/{draft['id']}/profile"))["freeKey"] == free
    assert free.startswith(f"{taken['key']}-") and f"'{free}'" in issues[0]["message"]
    step = ok(
        world.api.post(
            f"/model-drafts/{draft['id']}/operations",
            {
                "expectedVersion": _version(world, draft),
                "operations": [{"kind": "setProfile", "key": free}],
            },
        )
    )
    assert MISMATCH not in [d["code"] for d in step["diagnostics"]]
    assert MISMATCH not in [
        d["code"] for d in ok(world.api.get(f"/model-drafts/{draft['id']}/profile"))["diagnostics"]
    ]
    ok(_install(world, draft), 201)


@pytest.mark.journey("J36.3")
@pytest.mark.structures(*BOTH)
def test_each_model_imports_with_its_own_profile(world):
    """Given a workspace on Y beside the default workspace on X. When a profile is saved in each and
    an import runs in each with its own. Then both load. X's profile named in Y's workspace (an
    import, a file uploaded to it, a change) is refused naming both models; read in Y's workspace it
    is not valid, with that problem; the list by model holds that model's profiles only."""
    other, _y, key = _beside(world)
    x_key, y_key = _release_key(world), _release_key(other)
    mine = ok(world.api.post("/import-profiles", _profile(world)), 201)
    theirs = ok(world.api.post("/import-profiles", {**_profile(other), "workspaceKey": key}), 201)
    assert (mine["modelKey"], theirs["modelKey"]) == (x_key, y_key)
    assert theirs["valid"] is True

    _imported(world, W1, mine["key"], _rows("MINE"))
    _imported(other, key, theirs["key"], _rows("THEIRS"))

    _mismatch(_import(world, key, mine["key"], _rows("WRONG")), x_key, y_key)
    upload = world.api.upload(
        "/source-files",
        {"file": ("rows.xlsx", _rows("WRONG"), XLSX)},
        {"request": json.dumps({"owner": {"profileKey": mine["key"]}, "workspaceKey": key})},
    )
    _mismatch(upload, x_key, y_key)
    body = {k: v for k, v in _profile(world, mine["key"]).items() if k != "key"}
    _mismatch(
        world.api.put(
            f"/import-profiles/{mine['key']}", {**body, "expectedVersion": 1, "workspaceKey": key}
        ),
        x_key,
        y_key,
    )

    read = ok(world.api.get(f"/import-profiles/{mine['key']}", workspaceKey=key))
    assert read["valid"] is False
    assert [p["code"] for p in read["problems"]] == [MISMATCH]
    listed = ok(world.api.get("/import-profiles", modelKey=y_key, pageSize=100))["items"]
    assert [p["key"] for p in listed] == [theirs["key"]]


@pytest.mark.journey("J36.2")
@pytest.mark.structures(*BOTH)
def test_a_draft_is_checked_against_every_workspace_running_its_model(world):
    """Given X1 in the default workspace holding R records, a second workspace on X1 without any, a
    workspace on another model sharing X's keys holding an R, and one on Y. When a draft of X1 that
    removes R is compiled, X1 is compared with the release it installs, and a draft-only removal of R
    is sent. Then the compilation and the comparison list the two X workspaces, the one with records
    needing a migration and the other compatible, and neither other model's nor a retired one; the removal's impact
    grows with an R of the default workspace, not with one of the other model's workspace."""
    x1 = _model(world)["releaseId"]
    empty = _on(world, x1)
    twin_model = copy.deepcopy(world.configuration.model)
    twin_model["release"]["key"] = f"twin-{uuid4().hex[:8]}"
    twin = _on(world, world.install(twin_model, name="Twin")["id"])
    _other_world, _y, y_workspace = _beside(world)

    release = ok(world.api.get(f"/model-releases/{x1}", includeModel=True))
    draft = ok(
        world.api.post(
            "/model-drafts", {"name": "Without R", "model": release["model"], "baseReleaseId": x1}
        ),
        201,
    )

    def impact():
        removal = {"kind": "removeObjectType", "objectType": world.key("R")}
        return refused(
            world.api.post(
                f"/model-drafts/{draft['id']}/operations",
                {"expectedVersion": draft["version"], "operations": [removal]},
            ),
            409,
            "OPERATION_REQUIRES_MIGRATION",
        )["details"]["impact"]["records"]

    before = impact()
    world.made("R", "Twin record", workspace=twin)
    assert impact() == before
    world.made("R", "Default record", workspace=W1)
    assert impact() == before + 1

    ok(
        world.api.patch(
            f"/model-drafts/{draft['id']}",
            {"expectedVersion": draft["version"], "model": _strict(world, release["model"])},
        )
    )
    compiled = ok(
        world.api.post(
            f"/model-drafts/{draft['id']}/compile", {"expectedVersion": _version(world, draft)}
        )
    )
    assert compiled["valid"] is True, compiled["diagnostics"]

    retired = {
        w["key"] for w in ok(world.api.get("/workspaces", status="retired", pageSize=100))["items"]
    }
    installed = world.install(compiled["model"], name="Without R")
    diff = ok(world.api.get(f"/model-releases/{installed['id']}/diff", againstReleaseId=x1))
    for answer in (compiled, diff):
        by_workspace = {
            item["workspaceKey"]: item for item in answer["compatibility"]["workspaces"]
        }
        assert {W1, empty} <= set(by_workspace), by_workspace
        assert {item["releaseId"] for item in by_workspace.values()} == {x1}
        assert by_workspace[W1]["classification"] == "migration_required"
        assert by_workspace[empty]["classification"] == "compatible"
        assert twin not in by_workspace and y_workspace not in by_workspace
        assert not retired & set(by_workspace), "no activation reaches a retired workspace"


def _strict(world, base):
    """``base`` with an optional R attribute made required: R records lacking it need a migration."""
    model = copy.deepcopy(base)
    model["release"]["version"] += "-strict"
    defaults = {a["key"] for a in model["attributeTypes"] if a.get("default") is not None}
    r_type = next(t for t in model["objectTypes"] if t["key"] == world.key("R"))
    binding = next(
        b
        for b in r_type["attributes"]
        if not b.get("required") and not b.get("readOnly") and b["attributeTypeKey"] not in defaults
    )
    binding["required"] = True
    return model


@pytest.mark.journey("J36.3")
@pytest.mark.structures(*LEDGER)
def test_each_workspace_serves_its_own_consumer_apis(world):
    """Given X with Capi's events in the default workspace and Y with its own in another. When the
    API index and each definition's OpenAPI document are read for each workspace, and an R is
    created in each. Then each workspace's index lists its own model's definitions, names the
    workspace and release, and links each document with the workspace; another workspace's
    definition is not found there; each R is told as an event under its own workspace's definition."""
    other = _other(world)
    x_model = _with_events(world)
    x1 = world.install(x_model, name="X with events")["id"]
    ok(world.activate(x1))
    y1 = world.install(_with_events(other), name="Y with events")["id"]
    key = _on(world, y1)

    for here, workspace, release in ((world, W1, x1), (other, key, y1)):
        response = world.api.get("/api/consumer", workspace=workspace)
        index = ok(response)
        assert response.headers["RDM-Workspace"] == workspace
        assert response.headers["X-Model-Release-Id"] == release
        (entry,) = [item for item in index["items"] if item["consumerApi"] == here.key("Capi")]
        assert entry["openapi"].endswith(f"?workspace={workspace}")
        document = world.api.get(
            f"/api/consumer/{here.key('Capi')}/v{entry['contractVersion']}/openapi.json",
            workspace=workspace,
        )
        assert ok(document)["info"]["version"] == str(entry["contractVersion"])
        assert document.headers["X-Model-Release-Id"] == release
        listed = {item["consumerApi"] for item in index["items"]}
        assert (other if here is world else world).key("Capi") not in listed

    refused(
        world.api.get(f"/api/consumer/{other.key('Capi')}/v1/openapi.json", workspace=W1),
        404,
        "CONSUMER_API_NOT_FOUND",
    )
    refused(
        world.api.get("/api/consumer", workspace=f"none-{uuid4().hex[:6]}"),
        404,
        "WORKSPACE_NOT_FOUND",
    )

    mine = world.made("R", "Told here", workspace=W1)
    theirs = other.made("R", "Told there", workspace=key)
    derive_events(world)
    for here, workspace, record in ((world, W1, mine), (other, key, theirs)):
        events = ok(consumer_events(here, workspace=workspace, pageSize=100))["items"]
        assert record["id"] in {event["id"] for event in events}


def _with_events(world):
    model = copy.deepcopy(world.configuration.model)
    model["release"]["version"] += "-events"
    (definition,) = [d for d in model["consumerApis"] if d["key"] == world.key("Capi")]
    definition["operations"]["events"] = {"custom": _events(world)}
    return model
