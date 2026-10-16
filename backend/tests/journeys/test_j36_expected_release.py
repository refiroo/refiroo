"""J36.9 — A write built on a release the workspace no longer runs (USER_JOURNEYS.md, Base 0.11 M6a).

A client names the release it built a request on in ``X-Expected-Model-Release-Id`` (D63); a
request whose workspace, or change set, resolves another release is refused before anything is
written (D64). Each test runs on one configuration ``X`` with ``Y``, the other generated
configuration, beside it where it needs a second workspace.
"""

import pytest
from scenario import W1, ok, refused
from test_j36_workspace_models import BOTH, _beside, _model

HEADER = "X-Expected-Model-Release-Id"


def _named(release_id):
    return {HEADER: release_id}


def _renamed(world, record, name, release_id=None):
    body = {"expectedVersion": record["version"], "name": name}
    headers = _named(release_id) if release_id else None
    return world.api.patch(f"/objects/{world.key('R')}/{record['id']}", body, headers=headers)


def _second_release(world):
    """X2, compatible with X1, installed and activated into the default workspace: (X1, X2)."""
    x1 = _model(world)["releaseId"]
    model, _key = world.candidate("compatible")
    x2 = world.install(model)["id"]
    ok(world.activate(x2))
    return x1, x2


@pytest.mark.journey("J36.9")
@pytest.mark.structures(*BOTH)
def test_a_live_write_naming_a_release_its_workspace_no_longer_runs(world):
    """Given an R read under X1 in the default workspace and X2 activated there since. When the R is
    renamed naming X1, then 409 MODEL_RELEASE_CHANGED names the workspace, X1 and X2, and the R is
    unchanged. When renamed naming X2, it saves."""
    record = world.made("R", "Read under X1")
    x1, x2 = _second_release(world)

    error = refused(_renamed(world, record, "Stale", x1), 409, "MODEL_RELEASE_CHANGED")
    details = error["details"]
    assert (details["workspaceKey"], details["expectedReleaseId"], details["currentReleaseId"]) == (
        W1,
        x1,
        x2,
    )
    assert world.record("R", record["id"])["name"] == "Read under X1"

    assert ok(_renamed(world, record, "Current", x2))["name"] == "Current"


@pytest.mark.journey("J36.9")
@pytest.mark.structures(*BOTH)
def test_a_change_set_write_naming_a_release_the_change_set_left(world):
    """Given a change set pinned to X1 and moved to X2 since. When an R is created in it naming X1,
    then 409 MODEL_RELEASE_CHANGED names the workspace, the change set and both releases, and the
    change set is unchanged. Naming X2, the R is created."""
    x1 = _model(world)["releaseId"]
    change_set = world.change_set(W1)
    assert change_set["modelReleaseId"] == x1
    model, _key = world.candidate("compatible")
    x2 = world.install(model)["id"]
    moved = ok(
        world.api.patch(
            f"/change-sets/{change_set['id']}/model-release",
            {"modelReleaseId": x2, "expectedChangeSetVersion": change_set["version"]},
        )
    )
    stale = world.create("R", "In the change set", change_set=moved, headers=_named(x1))
    error = refused(stale, 409, "MODEL_RELEASE_CHANGED")
    assert error["details"]["changeSetId"] == change_set["id"]
    assert (error["details"]["expectedReleaseId"], error["details"]["currentReleaseId"]) == (x1, x2)
    assert world.current(change_set)["version"] == moved["version"]

    ok(world.create("R", "In the change set", change_set=moved, headers=_named(x2)), 201)


@pytest.mark.journey("J36.9")
@pytest.mark.structures(*BOTH)
def test_the_other_workspace_writes_by_its_own_release(world):
    """Given a workspace on Y beside the default workspace, and X2 activated into the default one.
    When an R is created in Y's workspace naming Y's release, it commits; naming X2 there, it is
    refused naming Y's workspace."""
    other, y, key = _beside(world)
    _x1, x2 = _second_release(world)

    ok(other.create("R", "Mine", workspace=key, headers=_named(y["id"])), 201)
    error = refused(
        other.create("R", "Not mine", workspace=key, headers=_named(x2)), 409, "MODEL_RELEASE_CHANGED"
    )
    assert (error["details"]["workspaceKey"], error["details"]["currentReleaseId"]) == (key, y["id"])


@pytest.mark.journey("J36.9")
@pytest.mark.structures(*BOTH)
def test_a_write_without_the_header_is_checked_against_the_current_release(world):
    """Given an R read under X1 and X2 activated since. When it is renamed naming no release, it
    saves under X2, as before M6a: the header is optional."""
    record = world.made("R", "Read under X1")
    _second_release(world)

    assert ok(_renamed(world, record, "No header"))["name"] == "No header"
