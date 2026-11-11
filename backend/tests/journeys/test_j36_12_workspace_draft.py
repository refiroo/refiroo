"""J36.12 — Change a workspace's model from the workspace (USER_JOURNEYS.md, Base 0.16 WM1).

The draft of a workspace's model is opened with one route; applying it is the existing installation,
then activation or a migration. Each test runs on generated A and B.
"""

import copy
from datetime import UTC, datetime, timedelta

import pytest
from scenario import W1, ok, refused
from sqlalchemy import create_engine, text
from sqlalchemy.pool import NullPool
from test_j36_workspace_models import BOTH, _model, _on
from test_j37_workspace_migration import _confirm, _probe, _read, _run, _workspace, _x2
from test_j40_authorization import _client
from test_j50_ai_workbook_load import FAKE, STRUCTURES, Ledgers
from test_j50_ai_workbook_load import _read as _read_task


def _open(world, workspace):
    return world.api.post(f"/workspaces/{workspace}/model/draft")


def _draft(world, draft_id):
    return ok(world.api.get(f"/model-drafts/{draft_id}"))


def _drafts(world):
    return {item["id"] for item in ok(world.api.get("/model-drafts", pageSize=500))["items"]}


def _with_field(world, model):
    """``model`` at a new version with one more text attribute on ``R``: the changed model and the
    attribute's key."""
    changed = copy.deepcopy(model)
    key = f"{world.key('R')}-wm1-field"
    changed["attributeTypes"].append({"key": key, "name": "WM1 field"})
    r_type = next(t for t in changed["objectTypes"] if t["key"] == world.key("R"))
    r_type["attributes"].append({"attributeTypeKey": key, "order": 950})
    changed["release"]["version"] += "-wm1"
    return changed, key


def _edit(world, draft, model):
    body = {"expectedVersion": draft["version"], "model": model}
    return ok(world.api.patch(f"/model-drafts/{draft['id']}", body))


def _install(world, draft):
    body = {"expectedVersion": draft["version"]}
    return world.api.post(f"/model-drafts/{draft['id']}/installation", body)


def _released_alone(world, model):
    """``model`` installed, its draft deleted: a release no draft stands on."""
    draft = ok(world.api.post("/model-drafts", {"name": "Passing", "model": model}), 201)
    release = ok(_install(world, draft), 201)
    version = {"expectedVersion": _draft(world, draft["id"])["version"]}
    assert world.api.delete(f"/model-drafts/{draft['id']}", **version).status_code == 204
    return release


@pytest.mark.journey("J36.12")
@pytest.mark.structures(*BOTH)
def test_a_workspaces_model_is_edited_and_applied_from_the_workspace(world):
    """Given two workspaces on one release. When the first's draft is opened, a field added, and it is
    installed and activated there. Then the first runs the new release with the field, the second is
    unchanged, and opening again answers 200 with the same draft."""
    running = _model(world)
    first, second = _on(world, running["releaseId"]), _on(world, running["releaseId"])

    draft = ok(_open(world, first), 201)
    assert draft["workspaceKey"] == first
    assert draft["baseReleaseId"] == running["releaseId"]
    assert first.title() in draft["name"]

    changed, field = _with_field(world, draft["model"])
    release = ok(_install(world, _edit(world, draft, changed)), 201)
    ok(world.activate(release["id"], first))

    assert _model(world, first)["releaseId"] == release["id"]
    assert _model(world, second)["releaseId"] == running["releaseId"]
    model = ok(world.api.get(f"/model-releases/{release['id']}", includeModel=True))["model"]
    assert any(item["key"] == field for item in model["attributeTypes"])

    again = ok(_open(world, first), 200)
    assert again["id"] == draft["id"]
    assert again["baseReleaseId"] == release["id"]


def _outline(world, draft_id):
    return ok(world.api.get(f"/model-drafts/{draft_id}/outline"))


def _set_version(world, draft_id, version):
    body = {"expectedVersion": _draft(world, draft_id)["version"]}
    body["operations"] = [{"kind": "setRelease", "version": version}]
    ok(world.api.post(f"/model-drafts/{draft_id}/operations", body))


@pytest.mark.journey("J36.12")
@pytest.mark.structures(*BOTH)
def test_a_version_another_draft_took_is_not_proposed_and_the_refusal_names_a_free_one(world):
    """Given two drafts of one release, each with its own change. When the first installs the version
    the outline proposes. Then the second's outline proposes another; installing it at the taken
    version is refused with a free version, and setting that one installs it."""
    running = _model(world)
    release = ok(world.api.get(f"/model-releases/{running['releaseId']}", includeModel=True))
    base = release["model"]
    drafts = []
    for label in ("one", "two"):
        changed, field = _with_field(world, base)
        changed["release"]["version"] = base["release"]["version"]
        next(t for t in changed["attributeTypes"] if t["key"] == field)["name"] = f"Field {label}"
        body = {"name": label, "model": changed, "baseReleaseId": running["releaseId"]}
        drafts.append(ok(world.api.post("/model-drafts", body), 201))
    first, second = drafts

    taken = _outline(world, first["id"])["suggestedReleaseVersion"]
    assert taken and taken != base["release"]["version"]
    assert _outline(world, second["id"])["suggestedReleaseVersion"] == taken
    _set_version(world, first["id"], taken)
    ok(_install(world, _draft(world, first["id"])), 201)

    free = _outline(world, second["id"])["suggestedReleaseVersion"]
    assert free not in (taken, base["release"]["version"])
    _set_version(world, second["id"], taken)
    error = refused(_install(world, _draft(world, second["id"])), 409, "RELEASE_IDENTITY_CONFLICT")
    assert error["details"]["releaseVersion"] == taken
    assert error["details"]["freeVersion"] == free

    _set_version(world, second["id"], error["details"]["freeVersion"])
    ok(_install(world, _draft(world, second["id"])), 201)


@pytest.mark.journey("J36.12")
@pytest.mark.structures(*BOTH)
def test_an_existing_draft_of_the_running_release_is_reused(world):
    """Given a draft of the running release remembering no workspace and one of another release. When
    the draft is opened. Then the first is answered, now naming the workspace, and no draft is
    created."""
    running = _model(world)
    release = ok(world.api.get(f"/model-releases/{running['releaseId']}", includeModel=True))
    key = _on(world, running["releaseId"])
    body = {"name": "Begun", "model": release["model"], "baseReleaseId": running["releaseId"]}
    begun = ok(world.api.post("/model-drafts", body), 201)
    changed, _field = _with_field(world, release["model"])
    world.install(changed, name="Of another release")
    before = _drafts(world)

    answer = ok(_open(world, key), 200)
    assert answer["id"] == begun["id"]
    assert answer["workspaceKey"] == key
    assert _drafts(world) == before


@pytest.mark.journey("J36.12")
@pytest.mark.structures(*STRUCTURES)
@pytest.mark.settings(AI_PROVIDER=FAKE, AI_AGENT_COMMAND="true")
def test_a_draft_an_assistant_task_names_is_not_taken_and_a_remembered_one_outlives_its_task(world):
    """Given only the draft of a task that ended, on the running release, when the draft is opened,
    then a new draft answers 201. Given a remembered draft a task came to name, when the task's
    retention is over, then the task is gone and the draft stays. The link is written directly: a
    session sets it from outside the API."""
    running = _model(world)
    release = ok(world.api.get(f"/model-releases/{running['releaseId']}", includeModel=True))
    key = _on(world, running["releaseId"])
    body = {"name": "A session's", "model": release["model"], "baseReleaseId": running["releaseId"]}
    held = ok(world.api.post("/model-drafts", body), 201)
    task = _read_task(world, Ledgers(world))
    remembered = None

    engine = create_engine(world.database, poolclass=NullPool)
    try:

        def name(draft_id, state):
            with engine.begin() as connection:
                connection.execute(
                    text(
                        "UPDATE ai_tasks SET state = :state, draft_id = "
                        "(SELECT id FROM model_drafts WHERE public_id = :draft) "
                        "WHERE public_id = :task"
                    ),
                    {"state": state, "draft": draft_id, "task": task["id"]},
                )

        name(held["id"], "loaded")
        remembered = ok(_open(world, key), 201)
        assert remembered["id"] != held["id"]
        assert _draft(world, held["id"])["workspaceKey"] is None

        name(remembered["id"], "failed")
    finally:
        engine.dispose()
    world.api.client.app.state.job_worker.sweep(datetime.now(UTC) + timedelta(days=3650))
    refused(world.api.get(f"/ai/tasks/{task['id']}"), 404, "AI_TASK_NOT_FOUND")
    assert _draft(world, remembered["id"])["workspaceKey"] == key


@pytest.mark.journey("J36.12")
@pytest.mark.structures(*BOTH)
def test_a_draft_gives_up_its_workspace_when_the_model_changed_elsewhere(world):
    """Given a remembered draft. When another release is activated in the workspace and the draft is
    opened. Then a new draft of that release answers 201, and the old one still exists, naming no
    workspace."""
    running = _model(world)
    key = _on(world, running["releaseId"])
    old = ok(_open(world, key), 201)
    changed, _field = _with_field(world, old["model"])
    elsewhere = _released_alone(world, changed)
    ok(world.activate(elsewhere["id"], key))

    new = ok(_open(world, key), 201)
    assert new["id"] != old["id"]
    assert new["baseReleaseId"] == elsewhere["id"]
    assert new["workspaceKey"] == key
    assert _draft(world, old["id"])["workspaceKey"] is None


@pytest.mark.journey("J36.12")
@pytest.mark.structures(*BOTH)
def test_a_change_that_moves_records_is_applied_with_a_migration(world):
    """Given records holding a field the draft removes. When it is installed. Then activation answers
    `MODEL_MIGRATION_REQUIRED`; opening before the migration confirms answers the same draft; after
    the confirmation the workspace runs the release with its records, under their IDs."""
    key, made, _citation = _workspace(world)
    draft = ok(_open(world, key))
    changed = _x2(world, "drop-note")
    changed["release"]["version"] += "-wm1"
    release = ok(_install(world, _edit(world, draft, changed)), 201)

    refused(world.activate(release["id"], key), 409, "MODEL_MIGRATION_REQUIRED")
    assert ok(_open(world, key), 200)["id"] == draft["id"]

    start = {"targetReleaseId": release["id"], "expectedVersion": _model(world, key)["version"]}
    job = ok(world.api.post(f"/workspaces/{key}/model/migrations", start), 202)
    _run(world)
    job = ok(world.api.get(f"/jobs/{job['id']}"))
    ok(_confirm(world, job, acceptLoss=True), 202)
    _run(world)
    assert ok(world.api.get(f"/jobs/{job['id']}"))["state"] == "completed"

    assert _model(world, key)["releaseId"] == release["id"]
    twelve = _read(world, key, made["twelve"])
    assert twelve["id"] == made["twelve"]["id"]
    held = {item["attributeTypeKey"] for item in twelve["attributes"]}
    assert _probe(world).note not in held
    assert ok(_open(world, key), 200)["id"] == draft["id"]


@pytest.mark.journey("J36.12")
@pytest.mark.structures(*BOTH)
def test_who_may_open_and_apply_a_workspaces_draft(world):
    """No Model authoring: `FORBIDDEN` on the route. Model authoring and Model release in workspace A:
    installs A's draft; `FORBIDDEN` on B's draft and on a draft remembering none. A retired workspace:
    `WORKSPACE_RETIRED`; an unknown one: `WORKSPACE_NOT_FOUND`. Browse in A is what activating there
    reads the workspace's model with."""
    running = _model(world)
    a, b = _on(world, running["releaseId"]), _on(world, running["releaseId"])
    _row, without = _client(world, "Without", ("model-admin", {"workspaceKey": W1}))
    refused(_open(without, a), 403, "FORBIDDEN")

    authors = ok(
        world.api.post("/roles", {"name": "Authors", "actionGroups": ["model-authoring"]}), 201
    )
    releases = ok(
        world.api.post("/roles", {"name": "Releases", "actionGroups": ["model-release", "browse"]}),
        201,
    )
    _row, holder = _client(
        world,
        "Holder",
        (authors["key"], {"instance": True}),
        (releases["key"], {"workspaceKey": a}),
    )

    draft_a = ok(_open(holder, a), 201)
    changed, _field = _with_field(holder, draft_a["model"])
    release = ok(_install(holder, _edit(holder, draft_a, changed)), 201)
    ok(holder.activate(release["id"], a))

    draft_b = ok(_open(holder, b), 201)
    changed_b = copy.deepcopy(draft_b["model"])
    changed_b["release"]["version"] += "-b"
    refused(_install(holder, _edit(holder, draft_b, changed_b)), 403, "FORBIDDEN")

    body = {"name": "Of nothing", "model": changed_b}
    unattached = ok(holder.api.post("/model-drafts", body), 201)
    refused(_install(holder, unattached), 403, "FORBIDDEN")

    workspace = ok(world.api.get(f"/workspaces/{b}"))
    retire = {"expectedVersion": workspace["version"], "status": "retired"}
    ok(world.api.patch(f"/workspaces/{b}", retire))
    refused(_open(world, b), 409, "WORKSPACE_RETIRED")
    refused(_open(world, "no-such-workspace"), 404, "WORKSPACE_NOT_FOUND")
