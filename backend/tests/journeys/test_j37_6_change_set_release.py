"""J37.6 — A change set started from a publication, published by moving its workspace to the
change set's release (USER_JOURNEYS.md, Base 0.11 V2, D79–D83).

Given in each test: a workspace on ``X1`` (J37's probe model) with records and a publication P1;
the workspace migrated to ``X2`` (the count an integer, and an extra attribute on ``R``) and written
under it; a change set started from P1, so pinned to ``X1``, which publishing refuses. A migration
of the workspace naming the change set moves its live data back to ``X1`` and publishes the change
set, in one confirmed job. Naming no configuration key.
"""

from uuid import uuid4

import pytest
from scenario import ok, refused
from test_j05_j06_publish import _update_in
from test_j36_workspace_models import BOTH, _beside, _model
from test_j37_workspace_migration import (
    _confirm,
    _head,
    _probe,
    _read,
    _rows,
    _run,
    _state,
    _value,
    _workspace,
    _x2,
)


def _extra(world):
    return f"{world.key('R')}-probe-extra"


def _x2_with_extra(world):
    """``X2``: the count an integer, and an extra text attribute on ``R`` that ``X1`` lacks."""
    model = _x2(world, "count-integer")
    model["attributeTypes"].append({"key": _extra(world), "name": "Probe extra"})
    r_type = next(t for t in model["objectTypes"] if t["key"] == world.key("R"))
    r_type["attributes"].append({"attributeTypeKey": _extra(world), "order": 903})
    model["release"]["version"] += "-extra"
    return model


def _migrated(world, workspace, target_id):
    job = ok(
        world.api.post(
            f"/workspaces/{workspace}/model/migrations",
            {"targetReleaseId": target_id, "expectedVersion": _model(world, workspace)["version"]},
        ),
        202,
    )
    _run(world)
    job = ok(world.api.get(f"/jobs/{job['id']}"))
    ok(_confirm(world, job, acceptLoss=True), 202)
    _run(world)
    assert ok(world.api.get(f"/jobs/{job['id']}"))["state"] == "completed"


def _historical(world):
    """The given state: the workspace's key, its records, P1, X1's and X2's IDs, and the change
    set started from P1 with the record "empty" renamed in it."""
    key, made, _citation = _workspace(world)
    x1_id = _model(world, key)["releaseId"]
    p1 = world.publish(world.change_set(workspace=key), workspace=key)
    x2 = world.install(_x2_with_extra(world), name="Probe")
    _migrated(world, key, x2["id"])
    twelve = _read(world, key, made["twelve"])
    ok(world.update("R", twelve["id"], twelve["version"], values={_extra(world): "only in X2"}))
    change_set = world.change_set(
        workspace=key, source="publication", derivedFromPublicationId=p1["id"]
    )
    ok(_update_in(world, change_set, "R", made["empty"]["id"], name="renamed from P1"))
    publication = {
        "expectedChangeSetVersion": world.current(change_set)["version"],
        "expectedActivePublicationId": p1["id"],
    }
    refused(
        world.api.post(f"/change-sets/{change_set['id']}/publication", publication),
        409,
        "CHANGE_SET_MODEL_RELEASE_CONFLICT",
    )
    return key, made, p1, x1_id, x2["id"], change_set


def _start(world, workspace, change_set, **body):
    request = {
        "changeSetId": change_set["id"],
        "expectedChangeSetVersion": world.current(change_set)["version"],
        "expectedVersion": _model(world, workspace)["version"],
        **body,
    }
    return world.api.post(f"/workspaces/{workspace}/model/migrations", request)


def _previewed(world, workspace, change_set, **body):
    job = ok(_start(world, workspace, change_set, **body), 202)
    _run(world)
    return ok(world.api.get(f"/jobs/{job['id']}"))


def _publications(world, workspace):
    return ok(world.api.get(f"/workspaces/{workspace}/publications", pageSize=100))["items"]


def _unchanged(world, workspace, made, change_set):
    """What a refused, stale or failed migration must leave: the workspace's state, its
    publications and the change set."""
    return (
        _state(world, workspace, made),
        _publications(world, workspace),
        world.current(change_set),
    )


@pytest.mark.journey("J37.6")
@pytest.mark.structures(*BOTH)
def test_a_preview_names_the_change_set_and_changes_nothing(world):
    """When a migration of the workspace naming the change set is started, then the job waits for
    confirmation; its summary names the change set, its version and X1 as the target, and counts
    two conversions (the counts back to text) and one loss (the extra value), no refusal. The
    workspace, its publications and the change set are unchanged."""
    key, made, p1, x1_id, _x2_id, change_set = _historical(world)
    k = _probe(world)
    before = _unchanged(world, key, made, change_set)

    job = _previewed(world, key, change_set)

    assert job["state"] == "awaiting_confirmation"
    summary = job["migration"]
    assert summary["targetReleaseId"] == x1_id
    assert summary["changeSetId"] == change_set["id"]
    assert summary["changeSetVersion"] == before[2]["version"]
    assert summary["activePublicationId"] == p1["id"]
    assert summary["counts"] == {"conversion": 2, "reclassified": 0, "loss": 1, "refused": 0}
    conversions = {
        (row["objectId"], row["attributeTypeKey"]): (row["before"], row["after"])
        for row in _rows(world, job["id"], status="conversion")
    }
    assert conversions == {
        (made["twelve"]["id"], k.count): (12, "12"),
        (made["forty"]["id"], k.count): (40, "40"),
    }
    (loss,) = _rows(world, job["id"], status="loss")
    assert (loss["objectId"], loss["attributeTypeKey"], loss["code"]) == (
        made["twelve"]["id"],
        _extra(world),
        "ATTRIBUTE_BINDING_IN_USE",
    )
    assert _unchanged(world, key, made, change_set) == before


@pytest.mark.journey("J37.6")
@pytest.mark.structures(*BOTH)
def test_confirm_migrates_and_publishes_together(world):
    """Given that preview and a workspace on Y beside it. When it is confirmed without acceptLoss,
    then 422 MIGRATION_LOSS_NOT_ACCEPTED. With it, the workspace runs X1; the change set is gone and
    the next publication, derived from P1 on X1, is the active one; the change set's rename is live;
    the counts read as text and the extra value is gone; the feed holds the migration's entries
    followed by the publication's. Y's workspace is unchanged."""
    _other, _y, beside = _beside(world)
    beside_before = (_model(world, beside), _head(world, beside))
    key, made, p1, x1_id, _x2_id, change_set = _historical(world)
    k = _probe(world)
    job = _previewed(world, key, change_set)
    head = job["migration"]["feedPosition"]

    refused(_confirm(world, job), 422, "MIGRATION_LOSS_NOT_ACCEPTED")
    ok(_confirm(world, job, acceptLoss=True), 202)
    _run(world)
    assert ok(world.api.get(f"/jobs/{job['id']}"))["state"] == "completed"

    assert _model(world, key)["releaseId"] == x1_id
    refused(world.api.get(f"/change-sets/{change_set['id']}"), 404, "CHANGE_SET_NOT_FOUND")
    active = [item for item in _publications(world, key) if item["status"] == "active"]
    assert len(active) == 1
    assert active[0]["derivedFromPublicationId"] == p1["id"]
    assert active[0]["modelReleaseId"] == x1_id
    assert _read(world, key, made["empty"])["name"] == "renamed from P1"
    twelve = _read(world, key, made["twelve"])
    assert _value(twelve, k.count) == "12" and _value(twelve, _extra(world)) is None
    assert _value(_read(world, key, made["forty"]), k.count) == "40"

    entries = ok(world.api.get(f"/workspaces/{key}/feed", after=head, pageSize=100))["items"]
    causes = [entry["cause"]["kind"] for entry in entries]
    assert causes and causes[0] == "job" and "publication" in causes
    assert causes == sorted(causes, key=lambda kind: kind != "job")
    assert (_model(world, beside), _head(world, beside)) == beside_before


@pytest.mark.journey("J37.6")
@pytest.mark.structures(*BOTH)
def test_a_change_set_edited_after_the_preview_makes_it_stale(world):
    """Given a waiting preview. When the change set is edited, then confirming is 409
    MIGRATION_REVIEW_STALE naming the reviewed and current change set versions, and nothing
    changed. A new preview confirms."""
    key, made, _p1, x1_id, _x2_id, change_set = _historical(world)
    job = _previewed(world, key, change_set)
    ok(_update_in(world, change_set, "R", made["empty"]["id"], name="edited after the preview"))
    before = _unchanged(world, key, made, change_set)

    error = refused(_confirm(world, job, acceptLoss=True), 409, "MIGRATION_REVIEW_STALE")
    assert error["details"]["reviewedChangeSetVersion"] == job["migration"]["changeSetVersion"]
    assert error["details"]["currentChangeSetVersion"] == before[2]["version"]
    assert _unchanged(world, key, made, change_set) == before

    again = _previewed(world, key, change_set)
    ok(_confirm(world, again, acceptLoss=True), 202)
    _run(world)
    assert ok(world.api.get(f"/jobs/{again['id']}"))["state"] == "completed"
    assert _model(world, key)["releaseId"] == x1_id


@pytest.mark.journey("J37.6")
@pytest.mark.structures(*BOTH)
def test_what_would_stop_the_publication_is_refused_in_the_preview(world):
    """Given the change set also changes the record that was changed live under X2. When previewed,
    then its refused rows name that record with CHANGE_SET_CONFLICT, and confirming is 409
    MIGRATION_HAS_REFUSALS, nothing changed."""
    key, made, _p1, _x1_id, _x2_id, change_set = _historical(world)
    ok(_update_in(world, change_set, "R", made["twelve"]["id"], name="twelve from P1"))
    before = _unchanged(world, key, made, change_set)

    job = _previewed(world, key, change_set)
    refusals = {(row["objectId"], row["code"]) for row in _rows(world, job["id"], status="refused")}
    assert (made["twelve"]["id"], "CHANGE_SET_CONFLICT") in refusals
    refused(_confirm(world, job, acceptLoss=True), 409, "MIGRATION_HAS_REFUSALS")
    assert _unchanged(world, key, made, change_set) == before


@pytest.mark.journey("J37.6")
@pytest.mark.structures(*BOTH)
def test_a_migration_naming_a_change_set_is_refused_at_its_start(world):
    """A target other than the change set's release is 422 MIGRATION_TARGET_NOT_CHANGE_SET_RELEASE;
    a change set on the workspace's own release is 422 MIGRATION_TARGET_IS_CURRENT; the change set
    named for another workspace is 404 CHANGE_SET_NOT_FOUND."""
    _other, _y, beside = _beside(world)
    key, _made, _p1, _x1_id, x2_id, change_set = _historical(world)

    refused(
        _start(world, key, change_set, targetReleaseId=x2_id),
        422,
        "MIGRATION_TARGET_NOT_CHANGE_SET_RELEASE",
    )
    on_current = world.change_set(workspace=key)
    refused(_start(world, key, on_current), 422, "MIGRATION_TARGET_IS_CURRENT")
    refused(_start(world, beside, change_set), 404, "CHANGE_SET_NOT_FOUND")


@pytest.mark.journey("J37.6")
@pytest.mark.structures(*BOTH)
def test_a_failed_publication_changes_nothing(world, monkeypatch):
    """Given a confirmed migration whose publication fails. No client can make it fail, so the
    failure is injected at the publication step of the execution. Then the job is failed with
    MIGRATION_FAILED, the workspace stays on X2 with its records and feed, and the change set is
    still open at its version."""
    key, made, _p1, _x1_id, x2_id, change_set = _historical(world)
    job = _previewed(world, key, change_set)
    before = _unchanged(world, key, made, change_set)

    def failing(*args, **kwargs):
        raise RuntimeError(f"injected failure {uuid4().hex[:6]}")

    from app.engine.model import migrations

    monkeypatch.setattr(migrations, "apply_publication", failing)
    ok(_confirm(world, job, acceptLoss=True), 202)
    _run(world)

    failed = ok(world.api.get(f"/jobs/{job['id']}"))
    assert failed["state"] == "failed"
    assert failed["error"]["code"] == "MIGRATION_FAILED"
    assert _model(world, key)["releaseId"] == x2_id
    assert _unchanged(world, key, made, change_set) == before
