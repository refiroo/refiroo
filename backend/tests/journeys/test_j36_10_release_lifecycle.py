"""J36.10–J36.11 — Retire a model release, and delete one nothing refers to (USER_JOURNEYS.md,
0.12 MR1).

A retired release is no longer offered or accepted where a release is chosen, while what runs on
it keeps working; a release nothing refers to may be deleted. Each test runs on generated A and B,
with the other's model installed beside it.
"""

import copy
from uuid import uuid4

import pytest
from scenario import W1, ok, refused
from service import command
from test_j36_workspace_models import BOTH, _beside, _model, _on, _other
from test_j40_authorization import _client

PRUNE = "app.cli.model_release_prune"


def _release(world, release_id):
    return ok(world.api.get(f"/model-releases/{release_id}"))


def _set_status(world, release, status):
    body = {"status": status, "expectedStatusVersion": release["statusVersion"]}
    return world.api.patch(f"/model-releases/{release['id']}", body)


def _delete(world, release):
    return world.api.delete(
        f"/model-releases/{release['id']}", expectedStatusVersion=release["statusVersion"]
    )


def _listed(world, **params):
    return {
        item["id"] for item in ok(world.api.get("/model-releases", pageSize=500, **params))["items"]
    }


@pytest.mark.journey("J36.10")
@pytest.mark.structures(*BOTH)
def test_a_retired_release_is_not_chosen_and_what_runs_on_it_keeps_working(world):
    """Given Y's release installed and a workspace on it. When Y is retired. Then it reads retired at
    the next status version; the usable list leaves it out and the retired list holds it; the
    workspace on it still reads its model, takes a record and opens a change set on its own release.
    A new workspace on Y, an activation of Y, a migration to Y and a change set elsewhere naming Y
    are each `409 MODEL_RELEASE_RETIRED`. When it is restored, a new workspace on it is created."""
    other, y, key = _beside(world)
    retired = ok(_set_status(world, _release(world, y["id"]), "retired"))
    assert (retired["status"], retired["statusVersion"]) == ("retired", 2)
    assert retired["retiredAt"] is not None
    assert y["id"] not in _listed(world, usable="true")
    assert y["id"] in _listed(world, status="retired")
    assert _model(world)["releaseId"] in _listed(world, usable="true")

    assert _model(world, key)["releaseId"] == y["id"]
    other.made("R", "Still written", workspace=key, fill=True)
    assert other.change_set(key, modelReleaseId=y["id"])["modelReleaseId"] == y["id"]

    error = refused(
        world.api.post(
            "/workspaces",
            {"key": f"w-{uuid4().hex[:8]}", "label": "On retired", "modelReleaseId": y["id"]},
        ),
        409,
        "MODEL_RELEASE_RETIRED",
    )
    assert error["details"] == {"releaseId": y["id"], "operation": "workspaceCreation"}
    error = refused(world.activate(y["id"]), 409, "MODEL_RELEASE_RETIRED")
    assert error["details"]["operation"] == "activation"
    migration = {"targetReleaseId": y["id"], "expectedVersion": _model(world)["version"]}
    error = refused(
        world.api.post(f"/workspaces/{W1}/model/migrations", migration),
        409,
        "MODEL_RELEASE_RETIRED",
    )
    assert error["details"]["operation"] == "migration"
    error = refused(
        world.api.post(
            f"/workspaces/{W1}/change-sets",
            {"name": "On Y", "source": "currentLive", "modelReleaseId": y["id"]},
        ),
        409,
        "MODEL_RELEASE_RETIRED",
    )
    assert error["details"]["operation"] == "changeSet"

    restored = ok(_set_status(world, retired, "active"))
    assert (restored["status"], restored["statusVersion"], restored.get("retiredAt")) == (
        "active",
        3,
        None,
    )
    assert _model(world, _on(world, y["id"]))["releaseId"] == y["id"]


@pytest.mark.journey("J36.10")
@pytest.mark.structures(*BOTH)
def test_retiring_is_refused_for_the_default_workspaces_release_a_stale_version_and_a_reader(world):
    """Given the default workspace's release X and Y's installed. When X is retired, then `409
    MODEL_RELEASE_IS_DEFAULT`. When Y is retired naming an earlier status version, then `409
    MODEL_RELEASE_VERSION_CONFLICT` with the current one. When a Reader retires Y, then `403`.
    Asking for the status a release has changes nothing. An unknown release is `404`."""
    x = _release(world, _model(world)["releaseId"])
    error = refused(_set_status(world, x, "retired"), 409, "MODEL_RELEASE_IS_DEFAULT")
    assert error["details"] == {"releaseId": x["id"]}

    y = _release(world, world.install(_other(world).configuration.model, name="Other model")["id"])
    assert ok(_set_status(world, y, "active"))["statusVersion"] == 1
    ok(_set_status(world, y, "retired"))
    error = refused(_set_status(world, y, "active"), 409, "MODEL_RELEASE_VERSION_CONFLICT")
    assert error["details"] == {
        "releaseId": y["id"],
        "status": "retired",
        "currentStatusVersion": 2,
    }

    _row, reader = _client(world, "Reader", ("reader", {"workspaceKey": W1}))
    refused(_set_status(reader, _release(world, y["id"]), "active"), 403, "FORBIDDEN")
    refused(
        world.api.patch(
            f"/model-releases/{uuid4()}", {"status": "retired", "expectedStatusVersion": 1}
        ),
        404,
        "MODEL_RELEASE_NOT_FOUND",
    )


@pytest.mark.journey("J36.10")
@pytest.mark.structures(*BOTH)
def test_installing_a_retired_releases_model_again_brings_it_back(world):
    """Given Y's release installed and retired. When Y's model is installed again from a new
    draft. Then the answer is the same release, `200`, active again at the next status version."""
    model = _other(world).configuration.model
    y = _release(world, world.install(model, name="Other model")["id"])
    ok(_set_status(world, y, "retired"))
    draft = ok(world.api.post("/model-drafts", {"name": "Again", "model": model}), 201)
    again = ok(
        world.api.post(
            f"/model-drafts/{draft['id']}/installation", {"expectedVersion": draft["version"]}
        )
    )
    assert (again["id"], again["status"], again["statusVersion"]) == (y["id"], "active", 3)


@pytest.mark.journey("J36.11")
@pytest.mark.structures(*BOTH)
def test_a_release_nothing_refers_to_is_deleted_and_one_in_use_is_not(world):
    """Given Y's release installed and never used, Y′ (Y at a later version) beside it with a
    workspace on Y′ holding a record, and Y″ installed. Then Y reads deletable, Y′ `running`.
    When Y is deleted, it is gone (`404`), its draft stays, and the list leaves it out. Deleting Y′
    is `409 MODEL_RELEASE_IN_USE` blocked by `running`. When the workspace moves to Y″, Y′ is
    blocked by `history` (its record was written under it) and still refused; a stale status
    version is `409 MODEL_RELEASE_VERSION_CONFLICT`."""
    other = _other(world)
    y = _release(world, world.install(other.configuration.model, name="Unused")["id"])
    assert (y["deletable"], y.get("deleteBlockedBy")) == (True, None)

    used_model = copy.deepcopy(other.configuration.model)
    used_model["release"]["version"] += "-used"
    used = world.install(used_model, name="Used")
    key = _on(world, used["id"])
    other.made("R", "Under the used release", workspace=key, fill=True)
    used = _release(world, used["id"])
    assert (used["deletable"], used["deleteBlockedBy"]) == (False, "running")

    drafts_before = ok(world.api.get("/model-drafts", pageSize=500))["items"]
    assert _delete(world, y).status_code == 204
    refused(world.api.get(f"/model-releases/{y['id']}"), 404, "MODEL_RELEASE_NOT_FOUND")
    assert y["id"] not in _listed(world)
    assert len(ok(world.api.get("/model-drafts", pageSize=500))["items"]) == len(drafts_before)

    error = refused(_delete(world, used), 409, "MODEL_RELEASE_IN_USE")
    assert error["details"] == {"releaseId": used["id"], "blockedBy": "running"}
    later_model = copy.deepcopy(used_model)
    later_model["release"]["version"] += "-later"
    ok(world.activate(world.install(later_model, name="Later")["id"], key))
    used = _release(world, used["id"])
    assert used["deleteBlockedBy"] == "history"
    refused(_delete(world, used), 409, "MODEL_RELEASE_IN_USE")
    stale = {**used, "statusVersion": used["statusVersion"] + 1}
    refused(_delete(world, stale), 409, "MODEL_RELEASE_VERSION_CONFLICT")


@pytest.mark.journey("J36.11")
@pytest.mark.structures("R")
def test_the_prune_command_deletes_retired_releases_nothing_refers_to(world):
    """Given two unused releases, one retired, and the default workspace's. When the prune command
    runs dry, nothing is deleted; when it runs, the retired one is gone and the other stays; with
    `--unused`, the other unused one goes too and the default workspace's stays. The releases come
    from the API; the command is the operator's, run against the same database."""
    other = _other(world)
    retired = _release(world, world.install(other.configuration.model, name="Retired")["id"])
    ok(_set_status(world, retired, "retired"))
    spare_model = copy.deepcopy(other.configuration.model)
    spare_model["release"]["version"] += "-spare"
    spare = world.install(spare_model, name="Spare")
    default = _model(world)["releaseId"]

    dry = command(PRUNE, world.database, "--dry-run")
    assert dry.returncode == 0 and "Nothing changed" in dry.stdout, dry.stderr
    assert {retired["id"], spare["id"]} <= _listed(world)
    assert command(PRUNE, world.database).returncode == 0
    assert retired["id"] not in _listed(world) and spare["id"] in _listed(world)
    assert command(PRUNE, world.database, "--unused").returncode == 0
    assert spare["id"] not in _listed(world) and default in _listed(world)
