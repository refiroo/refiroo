"""J36 — Run a workspace on a model of its own (USER_JOURNEYS.md, Base 0.11 M1).

Each test runs on one configuration ``X`` and puts a workspace on the other generated
configuration's model ``Y`` beside it: generated A beside B, and B beside A. ``Y``'s records are
made through a world over ``Y``'s keys on the same application. J36.4 (New from a workbook) is M3's,
J36.7 (reads spanning workspaces) M4's.
"""

import copy
from dataclasses import replace
from uuid import uuid4

import pytest
from configurations import all_configurations
from scenario import W1, W2, World, application, ok, refused
from sqlalchemy import create_engine, text
from sqlalchemy.pool import NullPool
from test_j30_consumer_events import LEDGER, WATCHED, _events
from test_j30_subscriptions import SUBSCRIPTIONS, _read, _subscribe

# Generated A and B only: the example model holds no consumer API.
BOTH = ("Capi", "R", "R.u")


def _other(world: World) -> World:
    """A world over the other generated configuration's keys, on the same application."""
    name = "generated-b" if world.configuration.name == "generated-a" else "generated-a"
    return replace(world, configuration=all_configurations()[name], ids={})


def _model(world, workspace=W1):
    return ok(world.api.get(f"/workspaces/{workspace}/model"))


def _on(world, release_id, key=None):
    """A new workspace created on ``release_id``; its key."""
    key = key or f"site-{uuid4().hex[:8]}"
    body = {"key": key, "label": key.title(), "modelReleaseId": release_id}
    ok(world.api.post("/workspaces", body), 201)
    return key


def _beside(world):
    """``Y``'s model installed and a workspace created on it: its world, release and key."""
    other = _other(world)
    release = world.install(other.configuration.model, name="Other model")
    return other, release, _on(world, release["id"])


@pytest.mark.journey("J36.1")
@pytest.mark.structures(*BOTH)
def test_a_new_workspace_on_another_model(world):
    """Given X running in the default workspace and Y's model installed. When a workspace is created
    on Y's release, and another without naming one. Then the first runs Y's release at version 1 and
    the default workspace still X's; its model reads the same on the workspace and on its own route;
    the assigned releases list both with their workspaces; the second runs X's release; an unknown
    release is refused."""
    x = _model(world)
    _other_world, y, key = _beside(world)

    workspace = ok(world.api.get(f"/workspaces/{key}"))
    assert workspace["model"]["releaseId"] == y["id"]
    assert workspace["model"]["releaseKey"] == y["key"]
    assert workspace["model"]["version"] == 1
    assert _model(world, key) == {**workspace["model"], "workspaceKey": key}
    assert _model(world)["releaseId"] == x["releaseId"]

    assigned = ok(world.api.get("/model-releases", assigned="true"))["items"]
    workspaces = {item["id"]: item["workspaces"] for item in assigned}
    assert key in workspaces[y["id"]] and W1 in workspaces[x["releaseId"]]
    assert all(item["assigned"] for item in assigned)
    unassigned = ok(world.api.get("/model-releases", assigned="false"))["items"]
    assert y["id"] not in {item["id"] for item in unassigned}

    plain = f"plain-{uuid4().hex[:8]}"
    ok(world.api.post("/workspaces", {"key": plain, "label": "Plain"}), 201)
    assert _model(world, plain)["releaseId"] == x["releaseId"]
    missing = {"key": f"x-{uuid4().hex[:8]}", "label": "Missing", "modelReleaseId": str(uuid4())}
    refused(world.api.post("/workspaces", missing), 404, "MODEL_RELEASE_NOT_FOUND")


@pytest.mark.journey("J36.3", "J36.6")
@pytest.mark.structures(*BOTH)
def test_each_workspace_reads_and_writes_by_its_own_model(world):
    """Given a workspace on Y beside the default workspace on X. When each workspace's model is read
    and an R is created and read in each. Then each answers its own model, release and workspace;
    each record carries its model's keys; X's R is unknown in Y's workspace. Without a workspace the
    default workspace's model is read; an unknown workspace is refused."""
    other, y, key = _beside(world)
    x = _model(world)

    for workspace, release, keys in ((W1, x["releaseId"], world), (key, y["id"], other)):
        response = world.api.get("/model", workspaceKey=workspace)
        model = ok(response)
        assert response.headers["X-Model-Release-Id"] == release
        assert response.headers["RDM-Workspace"] == workspace
        assert model["release"]["key"] == keys.configuration.model["release"]["key"]

    mine = world.made("R", "Here", workspace=W1)
    theirs = other.made("R", "There", workspace=key)
    assert world.record("R", mine["id"])["objectTypeKey"] == world.key("R")
    assert other.record("R", theirs["id"], workspaceKey=key)["objectTypeKey"] == other.key("R")
    refused(world.create("R", "Wrong model", workspace=key), 404, "UNKNOWN_OBJECT_TYPE")

    plain = world.api.get("/model")
    assert plain.headers["X-Model-Release-Id"] == x["releaseId"]
    assert plain.headers["RDM-Workspace"] == W1
    refused(world.api.get("/model", workspaceKey=f"none-{uuid4().hex[:6]}"), 404, "WORKSPACE_NOT_FOUND")


@pytest.mark.journey("J36.3")
@pytest.mark.structures(*BOTH)
def test_unique_values_follow_the_workspaces_model(world):
    """Given a workspace on Y. When two R records with one R.u value are created there. Then the
    second is refused as a duplicate; the same value is accepted once in X's default workspace."""
    other, _y, key = _beside(world)
    value = f"U-{uuid4().hex[:6]}"
    other.made("R", "First", workspace=key, values={"R.u": value})
    refused(
        other.create("R", "Second", workspace=key, values={"R.u": value}),
        409,
        "DUPLICATE_ATTRIBUTE_VALUE",
    )
    world.made("R", "Elsewhere", workspace=W1, values={"R.u": value})


@pytest.mark.journey("J36.5")
@pytest.mark.structures(*BOTH)
def test_a_write_when_its_workspaces_release_changed_meanwhile(world):
    """Given X1 in the default workspace, X2 installed and a workspace on Y. When actor A's live write
    in the default workspace is resolved under X1 and waits, X2 is activated into the default
    workspace, and a live write in Y's workspace runs meanwhile. Then the write in Y's workspace
    commits and Y's workspace still runs Y; A is refused naming the workspace, X1 and X2, and
    nothing of A is saved."""
    other, y, key = _beside(world)
    x1 = _model(world)["releaseId"]
    model, _key = world.candidate("compatible")
    x2 = world.install(model)["id"]
    record = world.made("R", "Before activation")

    with world.holding(W1) as held:
        write = held.start(lambda: world.update("R", record["id"], record["version"], name="Late"))
        held.waiting(1)
        ok(world.activate(x2))
        other.made("R", "Meanwhile", workspace=key)
        assert not write.done()
    error = refused(write.result(timeout=30), 409, "MODEL_RELEASE_CHANGED")
    details = error["details"]
    assert (details["workspaceKey"], details["resolvedReleaseId"], details["currentReleaseId"]) == (
        W1,
        x1,
        x2,
    )
    assert world.record("R", record["id"])["name"] == "Before activation"
    assert _model(world, key)["releaseId"] == y["id"]


def _strict_v2(world, base):
    """``base`` with an optional R attribute made required, ``Capi`` at contract version 2 and its
    watched event dropped: incompatible with R records lacking the attribute, and a contract change."""
    model = copy.deepcopy(base)
    model["release"]["version"] += "-strict-v2"
    defaults = {a["key"] for a in model["attributeTypes"] if a.get("default") is not None}
    r_type = next(t for t in model["objectTypes"] if t["key"] == world.key("R"))
    binding = next(
        b
        for b in r_type["attributes"]
        if not b.get("required") and not b.get("readOnly") and b["attributeTypeKey"] not in defaults
    )
    binding["required"] = True
    (definition,) = [d for d in model["consumerApis"] if d["key"] == world.key("Capi")]
    definition["contractVersion"] = 2
    definition["operations"]["events"] = {
        "custom": [e for e in definition["operations"]["events"]["custom"] if e["key"] != WATCHED]
    }
    return model


@pytest.mark.journey("J36.2")
@pytest.mark.settings(**SUBSCRIPTIONS)
@pytest.mark.structures(*LEDGER)
def test_activation_into_one_workspace_leaves_the_others_alone(world):
    """Given X1 (with events) in the default workspace and a second workspace on it, the second
    holding an R that X2 cannot hold and a subscription in each, and a workspace on Y. When X2 is
    activated into the default workspace. Then it is not refused for the second's record; the
    default runs X2 at its next version, the second X1 and Y's workspace Y, each at its version;
    only the default's subscription is suspended. Activating X2 into the second is refused counting
    its record; a stale version is refused naming the workspace; the assignments of X list each
    workspace with its release."""
    base = copy.deepcopy(world.configuration.model)
    base["release"]["version"] += "-events"
    (definition,) = [d for d in base["consumerApis"] if d["key"] == world.key("Capi")]
    definition["operations"]["events"] = {"custom": _events(world)}
    x1 = world.install(base)["id"]
    ok(world.activate(x1))
    second = _on(world, x1)
    world.made("R", "Lacks the strict value", workspace=second, fill=True)
    here = _subscribe(world, W1, events=[WATCHED])
    there = _subscribe(world, second, events=[WATCHED])
    _other_world, y, third = _beside(world)
    x2 = world.install(_strict_v2(world, base))["id"]
    before = _model(world)

    activated = ok(world.activate(x2))
    assert (activated["releaseId"], activated["version"]) == (x2, before["version"] + 1)
    assert activated["changeSetsLeftBehind"] == []
    assert _model(world, second)["releaseId"] == x1 and _model(world, second)["version"] == 1
    assert _model(world, third)["releaseId"] == y["id"]
    assert _read(world, here)["status"] == "suspended"
    assert _read(world, there)["status"] == "active"

    error = refused(world.activate(x2, second), 409, "MODEL_MIGRATION_REQUIRED")
    assert sum(item.get("count", 0) for item in error["details"]) == 1
    stale = {"releaseId": x1, "expectedVersion": before["version"], "expectedReleaseId": x1}
    error = refused(world.api.post(f"/workspaces/{W1}/model/activation", stale), 409, "ACTIVATION_CONFLICT")
    assert error["details"]["workspaceKey"] == W1
    assert error["details"]["currentReleaseId"] == x2

    listed = ok(world.api.get("/workspace-models", releaseKey=world.configuration.model["release"]["key"]))
    releases = {item["workspaceKey"]: item["releaseId"] for item in listed["items"]}
    assert releases[W1] == x2 and releases[second] == x1 and releases[W2] != x2
    assert third not in releases


@pytest.mark.journey("J36.2")
@pytest.mark.structures(*BOTH)
def test_a_change_set_publishes_under_its_workspaces_release(world):
    """Given a workspace on Y. When a change set there is created, given an R and published. Then it
    is pinned to Y's release and publishes. When a change set of the default workspace is opened on
    X1 and X2 is activated there. Then the activation lists it as left behind, and publishing it is
    refused naming the workspace."""
    other, y, key = _beside(world)
    theirs = other.change_set(key)
    assert theirs["modelReleaseId"] == y["id"]
    other.made("R", "In a change set", change_set=theirs)
    other.publish(theirs, key)

    mine = world.change_set(W1)
    model, _key = world.candidate("compatible")
    x2 = world.install(model)["id"]
    activated = ok(world.activate(x2))
    assert [item["id"] for item in activated["changeSetsLeftBehind"]] == [mine["id"]]
    current = world.current(mine)
    body = {"expectedChangeSetVersion": current["version"], "expectedActivePublicationId": None}
    error = refused(
        world.api.post(f"/change-sets/{mine['id']}/publication", body),
        409,
        "CHANGE_SET_MODEL_RELEASE_CONFLICT",
    )
    assert error["details"]["workspaceKey"] == W1


@pytest.mark.journey("J36.8")
@pytest.mark.structures(*BOTH)
def test_one_workspaces_release_cannot_be_loaded(world):
    """Given a workspace on a release this version cannot read (the state arrives from outside the
    API: an older database's release, whose schema is set back in the database). When the engine
    starts. Then that workspace's reads answer unavailable naming it; the default workspace serves
    and the instance is healthy."""
    _other_world, y, key = _beside(world)
    engine = create_engine(world.database, poolclass=NullPool)
    with engine.begin() as connection:
        connection.execute(
            text("UPDATE model_releases SET schema_version = '0.4' WHERE public_id = :id"),
            {"id": y["id"]},
        )
    engine.dispose()

    with application(world.configuration, world.database) as restarted:
        error = refused(restarted.api.get("/model", workspaceKey=key), 503, "MODEL_REGISTRY_UNAVAILABLE")
        assert error["details"]["workspaceKey"] == key
        assert error["details"]["releaseId"] == y["id"]
        assert error["details"]["schemaVersion"] == "0.4"
        assert ok(restarted.api.get("/model"))["release"]["key"] == world.configuration.model["release"]["key"]
        restarted.made("R", "Still served")
        assert restarted.api.get("/health").status_code == 200
