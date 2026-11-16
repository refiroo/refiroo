"""J25.10 — Keep a contract version through a breaking change (0.17.3 KV1).

A release that changes what a current contract version's readers get is activated only when it
raises ``contractVersion`` or when the request says ``keepContractVersions: true`` (KV-D1). The flag
never covers an earlier version served beside the current one (KV-D3). Activation and the migration
that activates a release take it; the activation answers and records what was kept (KV-D6).
"""

import copy

import pytest
from scenario import W1, consumer_object, ok, refused
from test_j25_earlier_versions import DEPRECATED, PARTS
from test_j30_consumer_events import LEDGER, _activate
from test_j37_workspace_migration import _confirm, _run


def _without_score(world, **more):
    """The release ``two``: ``Capi`` loses its score field and keeps its contract version."""
    score = world.key("Capi.n")

    def change(model, definition):
        del definition["object"]["fields"][score]
        definition.update(more.get("definition", {}))

    return change


def _installed(world, suffix, change):
    model = copy.deepcopy(world.configuration.model)
    model["release"]["version"] += f"-{suffix}"
    (definition,) = [d for d in model["consumerApis"] if d["key"] == world.key("Capi")]
    change(model, definition)
    return world.install(model)


def _keeping(world, release_id):
    current = world.workspace_model()
    return world.api.post(
        f"/workspaces/{W1}/model/activation",
        {
            "releaseId": release_id,
            "expectedVersion": current["version"],
            "expectedReleaseId": current["releaseId"],
            "keepContractVersions": True,
        },
    )


@pytest.mark.journey("J25.10")
@pytest.mark.structures(*LEDGER)
def test_a_breaking_release_is_activated_under_the_same_version_when_the_request_keeps_it(world):
    """Given version 1 of an API serving a score. When a release drops the score without raising the
    version, activating it is refused CONSUMER_CONTRACT_VERSION_REQUIRED; when the request says
    keepContractVersions, it is activated, the answer and the release's activation history name the
    API, version 1 and the breaking change with the actor, and version 1 now reads without the score.
    A release that changes an earlier version served beside the current one is refused with the flag
    too, naming version 1."""
    _activate(world, "one", events=[])
    record = world.made("R", "Ledger A")
    api, score = world.key("Capi"), world.key("Capi.n")
    assert score in ok(consumer_object(world, record["id"], version=1))

    release = _installed(world, "two", _without_score(world))
    state = world.workspace_model()
    refused(world.activate(release["id"]), 409, "CONSUMER_CONTRACT_VERSION_REQUIRED")
    assert world.workspace_model() == state

    answer = ok(_keeping(world, release["id"]))
    assert answer["releaseId"] == release["id"]
    (kept,) = answer["keptContractVersions"]
    assert (kept["consumerApi"], kept["contractVersion"]) == (api, 1)
    assert {d["code"] for d in kept["diagnostics"]} == {"CONSUMER_CONTRACT_VERSION_REQUIRED"}
    assert all(score in d["path"] + d["message"] for d in kept["diagnostics"])

    (event,) = ok(world.api.get(f"/model-releases/{release['id']}/activations"))["items"]
    assert event["keptContractVersions"] == answer["keptContractVersions"]
    assert event["actor"] is not None
    assert score not in ok(consumer_object(world, record["id"], version=1))

    def earlier_changed(_model, definition):
        earlier = {name: copy.deepcopy(definition[name]) for name in PARTS if name in definition}
        del earlier["object"]["fields"][world.key("Capi.name")]
        definition["earlierVersions"] = [
            {"contractVersion": 1, "deprecated": DEPRECATED, **earlier}
        ]
        definition["contractVersion"] = 2

    changed = _installed(world, "three", earlier_changed)
    state = world.workspace_model()
    error = refused(_keeping(world, changed["id"]), 409, "CONSUMER_CONTRACT_VERSION_REQUIRED")
    assert {d["code"] for d in error["details"]} == {"CONSUMER_KEPT_VERSION_CHANGED"}
    assert "version 1" in str(error["details"])
    assert world.workspace_model() == state


@pytest.mark.journey("J25.10")
@pytest.mark.structures(*LEDGER)
def test_a_migration_to_a_breaking_release_takes_the_flag_and_activates_what_it_accepted(world):
    """Given version 1 of an API serving a score. When a migration to a release that drops the score
    is requested without the flag, it is refused CONSUMER_CONTRACT_VERSION_REQUIRED and no job
    exists; with keepContractVersions, it is previewed and confirmed, the workspace runs the release
    and the release's activation history names the kept version."""
    _activate(world, "one", events=[])
    release = _installed(world, "two", _without_score(world))
    request = {
        "targetReleaseId": release["id"],
        "expectedVersion": world.workspace_model()["version"],
    }
    refused(
        world.api.post(f"/workspaces/{W1}/model/migrations", request),
        409,
        "CONSUMER_CONTRACT_VERSION_REQUIRED",
    )

    job = ok(
        world.api.post(
            f"/workspaces/{W1}/model/migrations", {**request, "keepContractVersions": True}
        ),
        202,
    )
    _run(world)
    job = ok(world.api.get(f"/jobs/{job['id']}"))
    ok(_confirm(world, job), 202)
    _run(world)
    assert ok(world.api.get(f"/jobs/{job['id']}"))["state"] == "completed"
    assert world.workspace_model()["releaseId"] == release["id"]
    (event,) = ok(world.api.get(f"/model-releases/{release['id']}/activations"))["items"]
    (kept,) = event["keptContractVersions"]
    assert (kept["consumerApi"], kept["contractVersion"]) == (world.key("Capi"), 1)
