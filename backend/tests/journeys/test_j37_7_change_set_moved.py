"""J37.7 — A change set moved onto a release its content does not fit (USER_JOURNEYS.md, Base 0.11
V3, D87–D96).

Given in each test: a workspace on ``X1`` (J37's probe model) with records; a change set started
from its live data under ``X1``, which edits the count of "forty" (a value ``X2`` retypes, one that
converts) and creates an R record with a note (a binding ``X2`` removes); the workspace then migrated
to ``X2`` (V1), so publishing the change set is refused. A move of the change set converts its own
content to ``X2`` over the workspace's live data as it is now, in one confirmed job, and never
touches live data. Naming no configuration key.
"""

import copy
from uuid import uuid4

import pytest
from scenario import ok, refused
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


def _staged(world, change_set):
    return {
        "changeSetId": change_set["id"],
        "expectedChangeSetVersion": world.current(change_set)["version"],
    }


def _in(world, change_set, record):
    """A record as the change set reads it."""
    return ok(
        world.api.get(
            f"/objects/{record['objectTypeKey']}/{record['id']}", changeSetId=change_set["id"]
        )
    )


def _edit_in(world, change_set, record, *, name=None, values=None):
    current = _in(world, change_set, record)
    body = {"expectedVersion": current["version"], **_staged(world, change_set)}
    if name is not None:
        body["name"] = name
    if values is not None:
        body["attributes"] = [{"attributeTypeKey": k, "value": v} for k, v in values.items()]
    return ok(world.api.patch(f"/objects/{record['objectTypeKey']}/{record['id']}", body))


def _create_in(world, change_set, structure, name, values):
    body = {
        "applicationKey": world.app(structure),
        "objectTypeKey": world.key(structure),
        "name": name,
        "attributes": [
            {"attributeTypeKey": k, "value": v}
            for k, v in {**world.required_values(structure), **values}.items()
        ],
        **_staged(world, change_set),
    }
    return ok(world.api.post("/objects", body), 201)


def _left_behind(world, x2, *, mappings=(), create=None, prepare=None):
    """The given state: the workspace's key, its records, X1's ID, X2's ID, the change set and the
    record it created (by ``create(change_set)``, else an R with a note), after ``prepare(key,
    made)`` and the workspace's migration to ``x2`` (with ``mappings``)."""
    key, made, _citation = _workspace(world)
    k = _probe(world)
    x1_id = _model(world, key)["releaseId"]
    change_set = world.change_set(workspace=key)
    _edit_in(world, change_set, made["forty"], values={k.count: "41"})
    if create is None:
        new = _create_in(world, change_set, "R", "made in C", {k.note: "C note"})
    else:
        new = create(change_set)
    if prepare is not None:
        prepare(key, made)
    target = world.install(x2, name="Probe")
    job = ok(
        world.api.post(
            f"/workspaces/{key}/model/migrations",
            {
                "targetReleaseId": target["id"],
                "expectedVersion": _model(world, key)["version"],
                "typeMappings": list(mappings),
            },
        ),
        202,
    )
    _run(world)
    ok(_confirm(world, ok(world.api.get(f"/jobs/{job['id']}")), acceptLoss=True), 202)
    _run(world)
    assert _model(world, key)["releaseId"] == target["id"]
    refused(_publish(world, key, change_set), 409, "CHANGE_SET_MODEL_RELEASE_CONFLICT")
    return key, made, x1_id, target["id"], change_set, new


def _publish(world, workspace, change_set):
    active = [
        item
        for item in ok(world.api.get(f"/workspaces/{workspace}/publications", pageSize=100))[
            "items"
        ]
        if item["status"] == "active"
    ]
    body = {
        "expectedChangeSetVersion": world.current(change_set)["version"],
        "expectedActivePublicationId": active[0]["id"] if active else None,
    }
    return world.api.post(f"/change-sets/{change_set['id']}/publication", body)


def _start(world, change_set, **body):
    request = {"expectedChangeSetVersion": world.current(change_set)["version"], **body}
    return world.api.post(f"/change-sets/{change_set['id']}/model-migrations", request)


def _previewed(world, change_set, **body):
    job = ok(_start(world, change_set, **body), 202)
    _run(world)
    return ok(world.api.get(f"/jobs/{job['id']}"))


def _unchanged(world, workspace, made, change_set, records):
    """What a refused, stale, cancelled or failed move must leave: the workspace's state, the
    change set and its records as it reads them."""
    return (
        _state(world, workspace, made),
        world.current(change_set),
        [_in(world, change_set, record) for record in records],
    )


def _count_integer(world):
    return _x2(world, "count-integer", "drop-note")


@pytest.mark.journey("J37.7")
@pytest.mark.structures(*BOTH)
def test_a_preview_lists_the_change_sets_items_and_changes_nothing(world):
    """When a move of the change set is started, then the job waits for confirmation; its summary
    names the change set, its version, X1 and X2, and counts one conversion (the change set's count)
    and one loss (its note), no refusal. The change set's records, version and release and the
    workspace's records, release and feed are unchanged."""
    key, made, x1_id, x2_id, change_set, new = _left_behind(world, _count_integer(world))
    k = _probe(world)
    before = _unchanged(world, key, made, change_set, [made["forty"], new])

    job = _previewed(world, change_set)

    assert job["kind"] == "migration" and job["state"] == "awaiting_confirmation"
    summary = job["migration"]
    assert summary["changeSetId"] == change_set["id"]
    assert summary["changeSetVersion"] == before[1]["version"]
    assert summary["currentReleaseId"] == x1_id
    assert summary["targetReleaseId"] == x2_id
    assert summary["counts"] == {"conversion": 1, "reclassified": 0, "loss": 1, "refused": 0}
    (conversion,) = _rows(world, job["id"], status="conversion")
    assert (conversion["objectId"], conversion["attributeTypeKey"]) == (
        made["forty"]["id"],
        k.count,
    )
    assert (conversion["before"], conversion["after"]) == ("41", 41)
    (loss,) = _rows(world, job["id"], status="loss")
    assert (loss["objectId"], loss["attributeTypeKey"], loss["code"]) == (
        new["id"],
        k.note,
        "ATTRIBUTE_BINDING_IN_USE",
    )
    assert _unchanged(world, key, made, change_set, [made["forty"], new]) == before
    assert before[1]["modelReleaseId"] == x1_id


@pytest.mark.journey("J37.7")
@pytest.mark.structures(*BOTH)
def test_confirm_moves_the_change_set_and_it_publishes(world):
    """Given that preview and a workspace on Y beside it. Confirming without acceptLoss is 422
    MIGRATION_LOSS_NOT_ACCEPTED. With it, the change set is on X2 at its next version: its count
    reads as an integer, its note is gone, a record it did not touch reads as it is live. The
    workspace's feed has no new entry. Publishing the change set then succeeds, although the
    migration had raised the edited record's version, and its edit is live. Y is unchanged."""
    _other, _y, beside = _beside(world)
    beside_before = (_model(world, beside), _head(world, beside))
    key, made, _x1_id, x2_id, change_set, new = _left_behind(world, _count_integer(world))
    k = _probe(world)
    version = world.current(change_set)["version"]
    job = _previewed(world, change_set)
    head = _head(world, key)

    refused(_confirm(world, job), 422, "MIGRATION_LOSS_NOT_ACCEPTED")
    ok(_confirm(world, job, acceptLoss=True), 202)
    _run(world)
    done = ok(world.api.get(f"/jobs/{job['id']}"))
    assert done["state"] == "completed", done

    moved = world.current(change_set)
    assert moved["modelReleaseId"] == x2_id and moved["version"] == version + 1
    assert _value(_in(world, change_set, made["forty"]), k.count) == 41
    created = _in(world, change_set, new)
    assert created["name"] == "made in C" and _value(created, k.note) is None
    untouched, live = _in(world, change_set, made["twelve"]), _read(world, key, made["twelve"])
    assert untouched["name"] == live["name"]
    assert {a["attributeTypeKey"]: a["value"] for a in untouched["attributes"]} == {
        a["attributeTypeKey"]: a["value"] for a in live["attributes"]
    }
    assert _value(untouched, k.count) == 12
    assert _head(world, key) == head

    ok(_publish(world, key, change_set))
    assert _value(_read(world, key, made["forty"]), k.count) == 41
    assert _read(world, key, new)["name"] == "made in C"
    assert (_model(world, beside), _head(world, beside)) == beside_before


@pytest.mark.journey("J37.7")
@pytest.mark.structures(*BOTH)
def test_a_renamed_type_is_carried_by_a_type_mapping(world):
    """Given X2 renames the probe type and the change set created a probe. Previewed without
    typeMappings, the probe is a loss; with the mapping, it is reclassified, and after confirming it
    keeps its ID under the new type with its name and label."""
    k = _probe(world)
    mapping = {"fromObjectTypeKey": k.kind, "toObjectTypeKey": k.renamed}

    def create(change_set):
        body = {
            "applicationKey": world.app("R"),
            "objectTypeKey": k.kind,
            "name": "probe in C",
            "attributes": [{"attributeTypeKey": k.label, "value": "probe in C"}],
            **_staged(world, change_set),
        }
        return ok(world.api.post("/objects", body), 201)

    _key, _made, _x1_id, x2_id, change_set, new = _left_behind(
        world, _x2(world, "rename-probe"), mappings=[mapping], create=create
    )

    unmapped = _previewed(world, change_set)
    assert (new["id"], "OBJECT_TYPE_IN_USE") in {
        (row["objectId"], row["code"]) for row in _rows(world, unmapped["id"], status="loss")
    }
    ok(world.api.post(f"/jobs/{unmapped['id']}/cancel"), 202)

    mapped = _previewed(world, change_set, typeMappings=[mapping])
    (row,) = _rows(world, mapped["id"], status="reclassified")
    assert (row["objectId"], row["targetObjectTypeKey"]) == (new["id"], k.renamed)
    assert (new["id"], "OBJECT_TYPE_IN_USE") not in {
        (item["objectId"], item["code"]) for item in _rows(world, mapped["id"], status="loss")
    }
    ok(_confirm(world, mapped, acceptLoss=True), 202)
    _run(world)
    assert ok(world.api.get(f"/jobs/{mapped['id']}"))["state"] == "completed"
    assert world.current(change_set)["modelReleaseId"] == x2_id
    probe = ok(world.api.get(f"/objects/{k.renamed}/{new['id']}", changeSetId=change_set["id"]))
    assert probe["name"] == "probe in C" and _value(probe, k.label) == "probe in C"


@pytest.mark.journey("J37.7")
@pytest.mark.structures(*BOTH)
def test_a_record_changed_live_since_the_change_set_is_refused(world):
    """Given the record the change set edited is also edited live after the migration. The preview
    refuses it as CHANGE_SET_CONFLICT; confirming is 409 MIGRATION_HAS_REFUSALS; nothing changed."""
    key, made, _x1_id, _x2_id, change_set, new = _left_behind(world, _count_integer(world))
    forty = _read(world, key, made["forty"])
    ok(world.update("R", forty["id"], forty["version"], name="forty, renamed live"))
    before = _unchanged(world, key, made, change_set, [made["forty"], new])

    job = _previewed(world, change_set)
    refusals = {(row["objectId"], row["code"]) for row in _rows(world, job["id"], status="refused")}
    assert refusals == {(made["forty"]["id"], "CHANGE_SET_CONFLICT")}
    refused(_confirm(world, job, acceptLoss=True), 409, "MIGRATION_HAS_REFUSALS")
    assert _unchanged(world, key, made, change_set, [made["forty"], new]) == before


@pytest.mark.journey("J37.7")
@pytest.mark.structures(*BOTH)
def test_a_rule_the_moved_content_breaks_is_refused_until_fixed(world):
    """Given X2 makes R require the count, which every live R holds and the record the change set
    created lacks. The preview refuses that record by the change set's own validation (MISSING_REQUIRED_ATTRIBUTES). After the count
    is filled in the change set, still on X1, a new preview confirms."""
    k = _probe(world)
    x2 = _x2(world)
    r_type = next(t for t in x2["objectTypes"] if t["key"] == world.key("R"))
    next(b for b in r_type["attributes"] if b["attributeTypeKey"] == k.count)["required"] = True
    x2["release"]["version"] += "-require-count"

    def prepare(key, made):
        # Every live R holds a count before the workspace moves to X2.
        current = _read(world, key, made["empty"])
        ok(world.update("R", current["id"], current["version"], values={k.count: "7"}))

    _key, _made, _x1_id, x2_id, change_set, new = _left_behind(
        world,
        x2,
        create=lambda change_set: _create_in(world, change_set, "R", "no count", {}),
        prepare=prepare,
    )

    job = _previewed(world, change_set)
    refusals = {(row["objectId"], row["code"]) for row in _rows(world, job["id"], status="refused")}
    assert refusals == {(new["id"], "MISSING_REQUIRED_ATTRIBUTES")}
    refused(_confirm(world, job, acceptLoss=True), 409, "MIGRATION_HAS_REFUSALS")

    _edit_in(world, change_set, new, values={k.count: "3"})
    fixed = _previewed(world, change_set)
    assert fixed["migration"]["counts"]["refused"] == 0
    ok(_confirm(world, fixed, acceptLoss=True), 202)
    _run(world)
    assert world.current(change_set)["modelReleaseId"] == x2_id


@pytest.mark.journey("J37.7")
@pytest.mark.structures(*BOTH)
def test_a_stale_or_cancelled_preview_changes_nothing(world):
    """Given a waiting preview. When the change set is edited, or a record is then saved live in the
    workspace, confirming is 409 MIGRATION_REVIEW_STALE and nothing changed. A cancelled preview
    changes nothing."""
    key, made, x1_id, _x2_id, change_set, new = _left_behind(world, _count_integer(world))
    job = _previewed(world, change_set)
    _edit_in(world, change_set, new, name="edited after the preview")
    before = _unchanged(world, key, made, change_set, [made["forty"], new])
    error = refused(_confirm(world, job, acceptLoss=True), 409, "MIGRATION_REVIEW_STALE")
    assert error["details"]["currentChangeSetVersion"] == before[1]["version"]
    assert _unchanged(world, key, made, change_set, [made["forty"], new]) == before

    again = _previewed(world, change_set)
    world.made("R", "Afterwards", workspace=key)
    before = _unchanged(world, key, made, change_set, [made["forty"], new])
    refused(_confirm(world, again, acceptLoss=True), 409, "MIGRATION_REVIEW_STALE")
    assert _unchanged(world, key, made, change_set, [made["forty"], new]) == before

    third = _previewed(world, change_set)
    ok(world.api.post(f"/jobs/{third['id']}/cancel"), 202)
    refused(_confirm(world, third, acceptLoss=True), 409, "JOB_NOT_AWAITING_CONFIRMATION")
    assert _unchanged(world, key, made, change_set, [made["forty"], new]) == before
    assert world.current(change_set)["modelReleaseId"] == x1_id


@pytest.mark.journey("J37.7")
@pytest.mark.structures(*BOTH)
def test_a_move_is_refused_at_its_start(world):
    """A target other than the workspace's release is 422 MIGRATION_TARGET_NOT_WORKSPACE_RELEASE; a
    change set already on the workspace's release is 422 MIGRATION_TARGET_IS_CURRENT; a stale
    expectedChangeSetVersion is 409 CHANGE_SET_VERSION_CONFLICT."""
    key, _made, _x1_id, _x2_id, change_set, _new = _left_behind(world, _count_integer(world))
    other = copy.deepcopy(_count_integer(world))
    other["release"]["version"] += "-other"
    other_id = world.install(other, name="Probe")["id"]

    refused(
        _start(world, change_set, targetReleaseId=other_id),
        422,
        "MIGRATION_TARGET_NOT_WORKSPACE_RELEASE",
    )
    on_current = world.change_set(workspace=key)
    refused(_start(world, on_current), 422, "MIGRATION_TARGET_IS_CURRENT")
    stale = {"expectedChangeSetVersion": world.current(change_set)["version"] - 1}
    refused(
        world.api.post(f"/change-sets/{change_set['id']}/model-migrations", stale),
        409,
        "CHANGE_SET_VERSION_CONFLICT",
    )


@pytest.mark.journey("J37.7")
@pytest.mark.structures(*BOTH)
def test_a_failed_move_changes_nothing(world, monkeypatch):
    """Given a confirmed move whose execution fails at its last step, the change set's event. No
    client can make it fail, so the failure is injected at that boundary. Then the job is failed
    with MIGRATION_FAILED, and the change set's records, version and release are unchanged."""
    key, made, x1_id, _x2_id, change_set, new = _left_behind(world, _count_integer(world))
    job = _previewed(world, change_set)
    before = _unchanged(world, key, made, change_set, [made["forty"], new])

    def failing(*args, **kwargs):
        raise RuntimeError(f"injected failure {uuid4().hex[:6]}")

    from app.engine.model import change_set_migrations

    monkeypatch.setattr(change_set_migrations, "record_change_set_moved", failing)
    ok(_confirm(world, job, acceptLoss=True), 202)
    _run(world)

    failed = ok(world.api.get(f"/jobs/{job['id']}"))
    assert failed["state"] == "failed"
    assert failed["error"]["code"] == "MIGRATION_FAILED"
    assert _unchanged(world, key, made, change_set, [made["forty"], new]) == before
    assert world.current(change_set)["modelReleaseId"] == x1_id


@pytest.mark.journey("J37.7")
@pytest.mark.structures(*BOTH)
def test_moving_a_submitted_change_set_withdraws_its_submission_or_is_refused(world):
    """Given a previewed move of a change set that is submitted for publication. When it is
    confirmed without `withdrawSubmission=true`, then `409 CHANGE_SET_SUBMITTED` and the job keeps
    waiting; with it, the move runs and the request reads as withdrawn, so no approver can publish
    the moved content as submitted (0.12 R-F6)."""
    key, _made, _x1_id, x2_id, change_set, _new = _left_behind(world, _count_integer(world))
    job = _previewed(world, change_set)
    version = world.current(change_set)["version"]
    ok(
        world.api.post(
            f"/change-sets/{change_set['id']}/submission", {"expectedChangeSetVersion": version}
        ),
        201,
    )
    request = {
        "expectedVersion": job["migration"]["expectedVersion"],
        "expectedFeedPosition": job["migration"]["feedPosition"],
        "acceptLoss": True,
    }

    refused(world.api.post(f"/jobs/{job['id']}/confirm", request), 409, "CHANGE_SET_SUBMITTED")
    assert ok(world.api.get(f"/jobs/{job['id']}"))["state"] == "awaiting_confirmation"
    assert world.current(change_set)["submission"]["state"] == "submitted"

    ok(world.api.post(f"/jobs/{job['id']}/confirm", request, withdrawSubmission=True), 202)
    _run(world)
    assert ok(world.api.get(f"/jobs/{job['id']}"))["state"] == "completed"
    moved = world.current(change_set)
    assert moved["modelReleaseId"] == x2_id and moved["version"] == version + 1
    requests = ok(world.api.get(f"/workspaces/{key}/publication-requests"))["items"]
    assert [item["state"] for item in requests] == ["withdrawn"]
