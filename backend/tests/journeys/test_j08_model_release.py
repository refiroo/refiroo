"""J08 — Create and activate an application-model release (USER_JOURNEYS.md).

J08.9 (a draft's history) is planned (D-5).
"""

import copy

import pytest
from scenario import W1, ok, refused

DISABLED = {"MODEL_ADMIN_MUTATIONS_ENABLED": "false"}


def _active(world):
    return ok(world.api.get("/model-runtime-state"))


def _model_release(world):
    return world.api.get("/model").headers["X-Model-Release-Id"]


def _draft(world, model, name="Draft", base=None):
    body = {"name": name, "model": model, **({"baseReleaseId": base} if base else {})}
    return ok(world.api.post("/model-drafts", body), 201)


def _compile(world, draft):
    return ok(
        world.api.post(
            f"/model-drafts/{draft['id']}/compile", {"expectedVersion": draft["version"]}
        )
    )


def _install(world, draft):
    return world.api.post(
        f"/model-drafts/{draft['id']}/installation", {"expectedVersion": draft["version"]}
    )


def _broken(world):
    """The configuration's model with an application naming a type the model lacks."""
    model = copy.deepcopy(world.configuration.model)
    model["applications"][0]["objectTypeKeys"].append("no-such-type")
    model["release"]["version"] += "-broken"
    return model


@pytest.mark.journey("J08")
@pytest.mark.structures("R")
def test_draft_compile_install_and_activate_a_release(world):
    """Given M1 active. When a draft with a compatible addition is saved, changed, compiled, installed
    (twice) and activated against the runtime state. Then the draft is versioned and the releases are
    unchanged by saving; compiling is valid with its changes and compatible; installing answers the
    new inactive release, then the same release again, and the model still reads M1; activating
    answers the next runtime state and the model reads the new release. A stale draft, an unknown
    draft, an invalid model and a reused release identity are refused."""
    m1 = _active(world)
    releases = ok(world.api.get("/model-releases", active=True))["items"]
    assert [r["id"] for r in releases] == [m1["activeReleaseId"]]
    model, added = world.candidate("compatible")
    draft = _draft(world, world.configuration.model, base=m1["activeReleaseId"])
    patched = ok(
        world.api.patch(
            f"/model-drafts/{draft['id']}", {"expectedVersion": draft["version"], "model": model}
        )
    )
    assert patched["version"] == draft["version"] + 1
    assert (
        ok(world.api.get("/model-releases"))["items"]
        == ok(world.api.get("/model-releases"))["items"]
    )
    assert len(ok(world.api.get("/model-releases"))["items"]) == 1

    compiled = _compile(world, patched)
    assert compiled["valid"] is True and compiled["compatibility"]["classification"] == "compatible"
    assert any(c["kind"] == "added" and added in c["path"] for c in compiled["changes"])
    assert all({"kind", "path"} <= set(c) for c in compiled["changes"])
    release = ok(_install(world, patched), 201)
    assert release["active"] is False and _model_release(world) == m1["activeReleaseId"]
    again = ok(_install(world, patched), 200)
    assert again["id"] == release["id"]

    activated = ok(world.activate(release["id"]))
    assert (
        activated["activeReleaseId"] == release["id"] and activated["version"] == m1["version"] + 1
    )
    assert _model_release(world) == release["id"]

    refused(
        world.api.patch(
            f"/model-drafts/{draft['id']}", {"expectedVersion": draft["version"], "name": "Stale"}
        ),
        409,
        "VERSION_CONFLICT",
    )
    refused(
        world.api.get("/model-drafts/00000000-0000-4000-8000-000000000000"),
        404,
        "MODEL_DRAFT_NOT_FOUND",
    )
    error = refused(_install(world, _draft(world, _broken(world))), 422, "INVALID_MODEL")
    assert any(d["path"].startswith("/applications") for d in error["details"])
    reused = copy.deepcopy(model)
    reused["product"]["name"] = "Same identity, other content"
    refused(_install(world, _draft(world, reused)), 409, "RELEASE_IDENTITY_CONFLICT")


def _validate_without_saving(world):
    drafts = (
        ok(world.api.get("/model-drafts"))
        if world.api.get("/model-drafts").status_code == 200
        else None
    )
    releases = ok(world.api.get("/model-releases"))["items"]
    answer = ok(world.api.post("/model-validations", {"model": _broken(world)}))
    assert answer["valid"] is False
    (diagnostic,) = [
        d
        for d in answer["diagnostics"]
        if "no-such-type" in d["message"] or d["path"].startswith("/applications")
    ][:1]
    assert {"severity", "code", "path", "message"} <= set(diagnostic)
    assert diagnostic["path"].startswith("/applications/")
    assert ok(world.api.get("/model-releases"))["items"] == releases
    if drafts is not None:
        assert ok(world.api.get("/model-drafts"))["items"] == drafts["items"]


@pytest.mark.journey("J08.1")
@pytest.mark.structures("R")
def test_validate_a_model_without_saving_it(world):
    """When a model with a reference to a missing type is validated. Then it is invalid with a
    diagnostic naming its severity, code, JSON pointer and message, and nothing is saved."""
    _validate_without_saving(world)


@pytest.mark.journey("J08.1", "J08.7")
@pytest.mark.structures("R")
@pytest.mark.settings(**DISABLED)
def test_with_model_administration_disabled(world):
    """Given model administration disabled. When a model is validated and a release read. Then both
    answer as on any instance; every draft, install and activation route is absent, and the
    capabilities say so with the setting's name."""
    _validate_without_saving(world)
    release = _active(world)["activeReleaseId"]
    assert "model" not in ok(world.api.get(f"/model-releases/{release}"))
    assert ok(world.api.get(f"/model-releases/{release}", includeModel=True))["model"]
    capabilities = ok(world.api.get("/capabilities"))["modelAdmin"]
    assert (capabilities["manageDrafts"], capabilities["install"], capabilities["activate"]) == (
        False,
        False,
        False,
    )
    assert capabilities["setting"] == "MODEL_ADMIN_MUTATIONS_ENABLED"
    body = {"expectedRuntimeVersion": 1, "expectedActiveReleaseId": release}
    for response in (
        world.api.get("/model-drafts"),
        world.api.post("/model-drafts", {"name": "x", "model": {}}),
        world.api.post(
            "/model-drafts/00000000-0000-4000-8000-000000000000/installation",
            {"expectedVersion": 1},
        ),
        world.api.post(f"/model-releases/{release}/activation", body),
    ):
        assert response.status_code == 404, response.text


@pytest.mark.journey("J08.2")
@pytest.mark.structures("R", "R.u", "R.b", "K", "B1n")
def test_compare_two_installed_releases(world):
    """Given M1 (with a consumer API) active and M2 installed, which adds an attribute, renames a view
    and removes a consumer field. When M2 is compared with M1. Then the changes list the added path
    and the changed name with both sides; compatibility names the active release; the consumer
    contracts report the removal. An unknown release to compare with is refused."""
    base = world.with_consumer_api(copy.deepcopy(world.configuration.model))
    base["release"]["version"] += "-api"
    m1 = world.install(base)["id"]
    ok(world.activate(m1))
    model, added = world.candidate("compatible")
    model = world.with_consumer_api(model, drop_flag=True)
    m2 = world.install(model)["id"]

    diff = ok(world.api.get(f"/model-releases/{m2}/diff", againstReleaseId=m1))
    additions = [c for c in diff["changes"] if c["kind"] == "added" and added in c["path"]]
    assert additions and all(c.get("before") is None for c in additions)
    renamed = [
        c
        for c in diff["changes"]
        if c["kind"] == "changed" and c["path"].endswith("/name") and c["after"] == "Renamed view"
    ]
    assert renamed and renamed[0]["before"]
    assert diff["compatibility"]["activeReleaseId"] == m1
    assert diff["consumerContracts"]["classification"] == "version_required"
    refused(
        world.api.get(
            f"/model-releases/{m2}/diff", againstReleaseId="00000000-0000-4000-8000-000000000000"
        ),
        404,
        "MODEL_RELEASE_NOT_FOUND",
    )


@pytest.mark.journey("J08.3", "J08.8")
@pytest.mark.structures("R")
def test_reactivate_an_older_release_and_read_the_activation_history(world):
    """Given M1 selected at bootstrap and M2 activated. When M1 is activated again. Then the model
    reads M1; M1's history lists only that activation, coming from M2, and M2's its own, coming from
    M1, oldest first; an unknown release's history is refused."""
    m1 = _active(world)["activeReleaseId"]
    model, _key = world.candidate("compatible")
    m2 = world.install(model)["id"]
    ok(world.activate(m2))
    ok(world.activate(m1))
    assert _model_release(world) == m1

    first = ok(world.api.get(f"/model-releases/{m1}/activations"))["items"]
    assert [(i["kind"], i["previousReleaseId"]) for i in first] == [("activated", m2)]
    second = ok(world.api.get(f"/model-releases/{m2}/activations"))["items"]
    assert [(i["kind"], i["previousReleaseId"]) for i in second] == [("activated", m1)]
    refused(
        world.api.get("/model-releases/00000000-0000-4000-8000-000000000000/activations"),
        404,
        "MODEL_RELEASE_NOT_FOUND",
    )


@pytest.mark.journey("J08.4")
@pytest.mark.structures("R")
def test_data_the_candidate_does_not_fit_blocks_activation(world):
    """Given a release that makes an attribute required, and N records lacking it. When it is
    compiled, compared and activated. Then compiling and comparing need a migration, with a
    diagnostic at the type's path counting N; activation is refused naming the data, and the runtime
    state and model are unchanged."""
    for name in ("Lacking one", "Lacking two"):
        world.made("R", name)
    model, key = world.candidate("incompatible")
    lacking = 0
    for workspace in (W1, "second-site", "closed-site"):
        page = ok(
            world.api.get(
                f"/objects/{world.key('R')}",
                workspaceKey=workspace,
                pageSize=1,
                includeTotal=True,
                **{f"filter.{key}.isUnset": "true"},
            )
        )
        lacking += page["totalCount"]
    state = _active(world)

    compiled = _compile(world, _draft(world, model))
    release = world.install(model)["id"]
    diff = ok(
        world.api.get(f"/model-releases/{release}/diff", againstReleaseId=state["activeReleaseId"])
    )
    for answer in (compiled, diff):
        assert answer["compatibility"]["classification"] == "migration_required"
        (diagnostic,) = [
            d for d in answer["compatibility"]["diagnostics"] if world.key("R") in d["path"]
        ]
        assert diagnostic["count"] == lacking
    refused(world.activate(release), 409, "MODEL_MIGRATION_REQUIRED")
    assert _active(world) == state and _model_release(world) == state["activeReleaseId"]


@pytest.mark.journey("J08.5")
@pytest.mark.structures("R")
def test_two_activations_from_the_same_runtime_state(world):
    """Given administrators A and B who read the runtime state at version v, and two compatible
    releases installed. When A activates one with v, then B the other with v. Then B is refused and
    A's release stays active at v+1."""
    state = _active(world)
    model, _key = world.candidate("compatible")
    m2 = world.install(model)["id"]
    model["release"]["version"] += "-other"
    m3 = world.install(model)["id"]
    body = {
        "expectedRuntimeVersion": state["version"],
        "expectedActiveReleaseId": state["activeReleaseId"],
    }
    ok(world.api.post(f"/model-releases/{m2}/activation", body))
    refused(world.api.post(f"/model-releases/{m3}/activation", body), 409, "ACTIVATION_CONFLICT")
    now = _active(world)
    assert (now["activeReleaseId"], now["version"]) == (m2, state["version"] + 1)


@pytest.mark.journey("J08.6")
@pytest.mark.structures("R")
def test_activation_beside_a_live_write(world):
    """Given actor A's live write resolved under M1 and waiting for its workspace, and actor B
    activating M2. Then B's activation completes while A still waits; A is then refused because the
    release changed, naming both releases, and nothing of A is saved."""
    m1 = _active(world)["activeReleaseId"]
    model, _key = world.candidate("compatible")
    m2 = world.install(model)["id"]
    record = world.made("R", "Before activation")

    with world.holding(W1) as held:
        write = held.start(lambda: world.update("R", record["id"], record["version"], name="Late"))
        held.waiting(1)
        ok(world.activate(m2))
        assert not write.done()
    error = refused(write.result(timeout=30), 409, "MODEL_RELEASE_CHANGED")
    assert (error["details"]["resolvedReleaseId"], error["details"]["activeReleaseId"]) == (m1, m2)
    assert world.record("R", record["id"])["name"] == "Before activation"


@pytest.mark.journey("J08.7")
@pytest.mark.structures("R")
def test_export_a_release_and_reuse_it(world):
    """When a release is read with and without its model, and the exported model saved as a draft and
    compiled. Then the model is present only when asked for, and the draft compiles valid with the
    release's model hash."""
    model, _key = world.candidate("compatible")
    release = world.install(model)
    plain = ok(world.api.get(f"/model-releases/{release['id']}"))
    assert "model" not in plain
    exported = ok(world.api.get(f"/model-releases/{release['id']}", includeModel=True))["model"]
    compiled = _compile(world, _draft(world, exported))
    assert compiled["valid"] is True and compiled["modelHash"] == release["modelHash"]
