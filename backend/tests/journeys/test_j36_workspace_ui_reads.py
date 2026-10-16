"""J36 — the reads the browser's workspace models need (USER_JOURNEYS.md, Base 0.11 M5, D52, D53).

Each test runs on one configuration ``X`` in the default workspace and puts a workspace on the other
generated configuration's model ``Y`` beside it: generated A beside B, and B beside A.
"""

from uuid import uuid4

import pytest
from scenario import W1, ok, refused
from test_j36_workspace_models import BOTH, _beside, _model


@pytest.mark.journey("J36.2")
@pytest.mark.structures(*BOTH)
def test_a_release_checked_against_a_chosen_workspace(world):
    """Given the default workspace on X with records and a workspace on Y with records. When Y's
    release is diffed against X's naming X's workspace, then that workspace's records need a
    migration; naming Y's workspace, compatible against Y's own release; naming none, the default
    workspace's answer as before; an unknown workspace is refused."""
    other, y, key = _beside(world)
    x = _model(world)["releaseId"]
    world.made("R", f"x {uuid4().hex[:6]}", workspace=W1, fill=True)
    other.made("R", f"y {uuid4().hex[:6]}", workspace=key, fill=True)
    path = f"/model-releases/{y['id']}/diff"

    into_x = ok(world.api.get(path, againstReleaseId=x, workspaceKey=W1))["compatibility"]
    assert into_x["classification"] == "migration_required"
    assert into_x["activeReleaseId"] == x
    into_y = ok(world.api.get(path, againstReleaseId=x, workspaceKey=key))["compatibility"]
    assert into_y["classification"] == "compatible"
    assert into_y["activeReleaseId"] == y["id"]
    default = ok(world.api.get(path, againstReleaseId=x))["compatibility"]
    assert (default["classification"], default["activeReleaseId"]) == ("migration_required", x)
    refused(
        world.api.get(path, againstReleaseId=x, workspaceKey=f"none-{uuid4().hex[:6]}"),
        404,
        "WORKSPACE_NOT_FOUND",
    )


@pytest.mark.journey("J36.1")
@pytest.mark.structures(*BOTH)
def test_a_workspace_names_its_models_release_name(world):
    """Given a workspace on Y beside the default workspace on X. When the workspaces, a workspace,
    its model and the workspace models are read. Then each names the release it runs by
    ``releaseName``, the installed release's name."""
    _other, y, key = _beside(world)
    x_name = ok(world.api.get(f"/model-releases/{_model(world)['releaseId']}"))["name"]
    names = {W1: x_name, key: y["name"]}

    assert _model(world, key)["releaseName"] == y["name"]
    assert ok(world.api.get(f"/workspaces/{key}"))["model"]["releaseName"] == y["name"]
    listed = ok(world.api.get("/workspaces", status="all", pageSize=200))["items"]
    for item in listed:
        if item["key"] in names:
            assert item["model"]["releaseName"] == names[item["key"]]
    assigned = ok(world.api.get("/workspace-models", pageSize=200))["items"]
    for item in assigned:
        if item["workspaceKey"] in names:
            assert item["releaseName"] == names[item["workspaceKey"]]
