"""J38.2, J38.3, J38.6, J38.8 — The move into a reviewed change set (USER_JOURNEYS.md, Base 0.11 X3,
D128–D137).

A move's dry run waits for confirmation; confirming it loads what was previewed into a new change
set of the target workspace, which is reviewed and published as any other. A moved record keeps
where it came from, so a second move finds it again and a move back finds its original. With
``mode: move`` a second change set, in the source workspace, deletes what was loaded, and it
publishes only after the copy. Each test runs on one configuration ``X`` in the default workspace
with a workspace on ``Y``, the other generated configuration, beside it, the mapping proposed and
applied as in J38.1: generated A to B, and B to A. Naming no configuration key.
"""

import copy
from uuid import uuid4

import pytest
from scenario import W1, consumer_events, derive_events, ok, refused
from test_j36_workspace_models import BOTH, _other
from test_j38_1_model_mapping import _apply, _beside, _create, _infer, _operate, _read, _run
from test_j38_2_move_dry_run import _count, _counterpart, _head, _records, _rows, _start


def _mapped(world, source=W1, target=None, model=None):
    """Y beside X (``model`` for Y's when given) and the mapping from ``source`` to the target
    proposed and applied: Y's world, the target workspace and the mapping's key."""
    other = _other(world)
    if target is None:
        other, _release, target = _beside(world, model)
    key = _create(world, source, target)["key"]
    _infer(world, key, source, target)
    _apply(world, key)
    return other, target, key


def _reverse(world, source, target):
    """The mapping from ``source`` back to ``target``, proposed and applied."""
    key = _create(world, source, target)["key"]
    _infer(world, key, source, target)
    _apply(world, key)
    return key


def _preview(world, key, target, selection=None, **extra):
    """A move's dry run, run until it waits for confirmation: the job and every row."""
    job = ok(_start(world, key, target, selection, **extra), 202)
    _run(world)
    job = ok(world.api.get(f"/jobs/{job['id']}"))
    assert job["state"] == "awaiting_confirmation", job
    return job, _rows(world, job["id"])


def _confirm(world, job):
    """The move confirmed and loaded: the job, every row and the target's change set."""
    ok(world.api.post(f"/jobs/{job['id']}/confirm"), 202)
    _run(world)
    job = ok(world.api.get(f"/jobs/{job['id']}"))
    assert job["state"] == "completed", job
    return job, _rows(world, job["id"])


def _publish(world, change_set_id, workspace):
    """``POST /change-sets/{id}/publication``, answered as it comes."""
    active = ok(world.api.get(f"/workspaces/{workspace}/publications", pageSize=1))["items"]
    current = [item for item in active if item.get("status") == "active"]
    body = {
        "expectedChangeSetVersion": ok(world.api.get(f"/change-sets/{change_set_id}"))["version"],
        "expectedActivePublicationId": current[0]["id"] if current else None,
    }
    return world.api.post(f"/change-sets/{change_set_id}/publication", body)


def _record(world, row, workspace=None, **params):
    """The target record of ``row``: in a change set, or live in ``workspace``."""
    if workspace is not None:
        params["workspaceKey"] = workspace
    return world.api.get(f"/objects/{row['targetType']}/{row['targetId']}", **params)


def _change_sets(world, workspace):
    return ok(world.api.get(f"/workspaces/{workspace}/change-sets"))["items"]


def _ledgers(world):
    return {"types": [{"objectTypeKey": world.key("R")}]}


def _ledger(world, name):
    return world.made("R", f"{name} {uuid4().hex[:6]}", values={"R.u": f"U-{uuid4().hex[:8]}"})


def _with_events(other):
    """Y's model with its consumer API telling every change of its ledgers."""
    model = copy.deepcopy(other.configuration.model)
    (definition,) = [d for d in model["consumerApis"] if d["key"] == other.key("Capi")]
    definition["operations"]["events"] = {
        "custom": [
            {
                "key": "ledger-any",
                "objectTypes": [other.key("R")],
                "changes": ["created", "updated", "deleted"],
            }
        ]
    }
    return model


def _events(other, workspace):
    derive_events(other)
    page = ok(consumer_events(other, workspace=workspace, payload="identity", pageSize=1000))
    return page["items"]


@pytest.mark.journey("J38.8")
@pytest.mark.structures(*BOTH)
def test_a_copy_confirmed_reviewed_and_published(world):
    """Given a dry run of the whole workspace waiting for confirmation. When it is confirmed, the
    job completes naming a new change set of the target that holds every created and updated row's
    record under its target ID, while the target's live records, feed and consumer events are
    unchanged and the source is untouched. When the change set is published, the records are live
    in the target and its consumer API tells each ledger's creation; a moved record's history names
    the move's job as its cause with its origin in the source."""
    other, target, key = _mapped(world, model=_with_events(_other(world)))
    ledger = _ledger(world, "Ledger")
    world.made("R2", "Entry", parent=ledger["id"])
    held = _count(world, "R", W1)
    head, source_head = _head(world, target), _head(world, W1)

    job, preview = _preview(world, key, target)
    assert job["changeSetId"] is None
    job, rows = _confirm(world, job)

    change_set = ok(world.api.get(f"/change-sets/{job['changeSetId']}"))
    assert change_set["workspaceKey"] == target
    moving = [r for r in rows if r["kind"] == "record" and r["outcome"] in ("create", "update")]
    previewed = [
        r for r in preview if r["kind"] == "record" and r["outcome"] in ("create", "update")
    ]
    assert moving and len(moving) == len(previewed)
    for row in moving:
        ok(_record(world, row, changeSetId=change_set["id"]))
        refused(_record(world, row, target), 404, "OBJECT_NOT_FOUND")
    assert _head(world, target) == head
    assert _events(other, target) == []
    assert _head(world, W1) == source_head and _count(world, "R", W1) == held

    publication = ok(_publish(world, change_set["id"], target))
    assert publication["workspaceKey"] == target
    for row in moving:
        ok(_record(world, row, target))
    ledgers = {r["targetId"] for r in moving if r["targetType"] == other.key("R")}
    told = {e["id"] for e in _events(other, target) if e["change"] == "created"}
    assert ledgers and ledgers <= told

    [row] = [r for r in moving if r["sourceId"] == ledger["id"]]
    history = ok(world.api.get(f"/objects/{row['targetType']}/{row['targetId']}/history"))
    [moved] = [e for e in history["items"] if (e.get("cause") or {}).get("id") == job["id"]]
    assert moved["cause"]["kind"] == "job"
    assert moved["cause"]["origin"] == {"workspaceKey": W1, "objectId": ledger["id"]}


@pytest.mark.journey("J38.6")
@pytest.mark.structures(*BOTH)
def test_a_second_move_found_again(world):
    """Given ledgers copied into the target and published, and one renamed in the source since.
    When the same move runs again, its rows update the records found by their counterparts; once
    confirmed and published, the target holds as many ledgers as before, the renamed one renamed."""
    other, target, key = _mapped(world)
    ledger = _ledger(world, "Ledger")
    job, _seen = _confirm(world, _preview(world, key, target, _ledgers(world))[0])
    ok(_publish(world, job["changeSetId"], target))
    copied = _count(other, "R", target)

    version = world.record("R", ledger["id"])["version"]
    ok(world.update("R", ledger["id"], version, name="Renamed ledger"))
    job, rows = _preview(world, key, target, _ledgers(world))
    found = _records(rows)
    assert {row["outcome"] for row in found.values()} == {"update"}
    assert {row["foundBy"] for row in found.values()} == {"counterpart"}
    job, rows = _confirm(world, job)
    ok(_publish(world, job["changeSetId"], target))

    assert _count(other, "R", target) == copied
    moved = _records(rows)[ledger["id"]]
    assert moved["targetId"] == _counterpart(target, ledger["id"])
    assert ok(_record(world, moved, target))["name"] == "Renamed ledger"


@pytest.mark.journey("J38.6")
@pytest.mark.structures(*BOTH)
def test_a_record_moved_back_finds_its_original(world):
    """Given ledgers copied into the target and published, and a ledger created in the target
    itself. When ledgers move back through the reverse mapping, the ones that came from the source
    update their originals, naming the original IDs, and the target's own ledger is created."""
    other, target, key = _mapped(world)
    ledger = _ledger(world, "Ledger")
    job, _seen = _confirm(world, _preview(world, key, target, _ledgers(world))[0])
    ok(_publish(world, job["changeSetId"], target))
    native = other.made("R", "Native ledger", workspace=target, values={"R.u": "N-1"})

    back = _reverse(world, target, W1)
    _job, rows = _preview(world, back, W1, _ledgers(other), source=target)
    found = _records(rows)
    copy_of = _counterpart(target, ledger["id"])
    assert found[copy_of]["outcome"] == "updateOriginal", found[copy_of]
    assert found[copy_of]["foundBy"] == "origin"
    assert found[copy_of]["targetId"] == ledger["id"]
    assert found[native["id"]]["outcome"] == "create"
    assert found[native["id"]]["targetId"] == _counterpart(W1, native["id"])


@pytest.mark.journey("J38.3")
@pytest.mark.structures(*BOTH)
def test_a_subtree_moved(world):
    """Given ledgers with entries. When a ledger's subtree moves with entries unmapped, the ledger is
    copied and kept in the source, since its entries stay. When another ledger's subtree moves, one
    entry changed in the source after the dry run, the target's change set holds the copy and a new
    change set of the source deletes the entry that did not change; the changed one is copied as
    previewed and kept, and so is its ledger. The source's change set publishes only after the
    target's; then the deleted entry is gone from the source. Moved back, it is created again under
    its original ID, under its ledger."""
    _other_world, target, key = _mapped(world)
    first = _ledger(world, "First")
    world.made("R2", "Unmoved entry", parent=first["id"])
    second = _ledger(world, "Second")
    gone = world.made("R2", "Moved entry", parent=second["id"])
    changed = world.made("R2", "Changed entry", parent=second["id"])

    ok(_operate(world, key, {"kind": "unmapType", "sourceType": world.key("R2")}))
    job, _seen = _preview(world, key, target, {"parentObjectId": first["id"]}, mode="move")
    job, rows = _confirm(world, job)
    kept = _records(rows)[first["id"]]
    assert kept["outcome"] == "create"
    assert kept["source"]["outcome"] == "kept"
    assert {r["code"] for r in kept["source"]["reasons"]} == {"OBJECT_HAS_DEPENDANTS"}
    ok(
        world.api.post(
            f"/model-mappings/{key}/undo", {"expectedVersion": _read(world, key)["version"]}
        )
    )

    job, _seen = _preview(world, key, target, {"parentObjectId": second["id"]}, mode="move")
    version = world.record("R2", changed["id"])["version"]
    ok(world.update("R2", changed["id"], version, name="Changed since"))
    job, rows = _confirm(world, job)
    found = _records(rows)
    assert found[gone["id"]]["source"]["outcome"] == "deleted"
    assert found[changed["id"]]["source"]["outcome"] == "kept"
    assert {r["code"] for r in found[changed["id"]]["source"]["reasons"]} == {"SOURCE_CHANGED"}
    assert found[second["id"]]["source"]["outcome"] == "kept"
    copied = ok(_record(world, found[changed["id"]], changeSetId=job["changeSetId"]))
    assert copied["name"] == "Changed entry"

    deletion = job["move"]["sourceChangeSetId"]
    assert ok(world.api.get(f"/change-sets/{deletion}"))["workspaceKey"] == W1
    early = refused(_publish(world, deletion, W1), 409, "MOVE_COPY_NOT_PUBLISHED")
    assert early["details"]["changeSetId"] == job["changeSetId"]
    world.record("R2", gone["id"])
    ok(_publish(world, job["changeSetId"], target))
    ok(_publish(world, deletion, W1))
    refused(world.read("R2", gone["id"]), 404, "OBJECT_NOT_FOUND")
    world.record("R2", changed["id"])

    back = _reverse(world, target, W1)
    copy_of = _counterpart(target, gone["id"])
    job, rows = _preview(world, back, W1, {"objectIds": [copy_of]}, source=target)
    row = _records(rows)[copy_of]
    assert row["outcome"] == "create" and row["foundBy"] == "origin", row
    assert row["targetId"] == gone["id"]
    assert row["targetParentId"] == second["id"]


@pytest.mark.journey("J38.3")
@pytest.mark.structures(*BOTH)
def test_a_whole_subtree_moved_leaves_the_source(world):
    """0.11 X5 (found by the checkpoint's browser walk): a ledger whose entries all move. When its
    subtree moves, the source's change set deletes the ledger and every entry, the ledger not kept
    for dependants that the same move deletes. Once both change sets are published, the subtree is
    in the target and gone from the source."""
    _other_world, target, key = _mapped(world)
    ledger = _ledger(world, "Whole")
    entries = [world.made("R2", f"Entry {n}", parent=ledger["id"]) for n in (1, 2)]

    job, _seen = _preview(world, key, target, {"parentObjectId": ledger["id"]}, mode="move")
    job, rows = _confirm(world, job)
    found = _records(rows)
    for record in (ledger, *entries):
        assert found[record["id"]]["source"] == {"outcome": "deleted", "reasons": []}, found
    ok(_publish(world, job["changeSetId"], target))
    ok(_publish(world, job["move"]["sourceChangeSetId"], W1))
    refused(world.read("R", ledger["id"]), 404, "OBJECT_NOT_FOUND")
    for entry in entries:
        refused(world.read("R2", entry["id"]), 404, "OBJECT_NOT_FOUND")
    assert ok(_record(world, found[ledger["id"]], target))["name"] == ledger["name"]


@pytest.mark.journey("J38.2")
@pytest.mark.structures(*BOTH)
def test_a_move_executed_without_waiting(world):
    """Given the mapping applied. When a move is sent with ``stage: execute``, it completes without
    waiting, naming its change set, with the rows a confirmed dry run of it has."""
    _other_world, target, key = _mapped(world)
    _ledger(world, "Ledger")
    _job, previewed = _preview(world, key, target, _ledgers(world))

    job = ok(_start(world, key, target, _ledgers(world), stage="execute"), 202)
    _run(world)
    job = ok(world.api.get(f"/jobs/{job['id']}"))
    assert job["state"] == "completed" and job["changeSetId"], job
    rows = _rows(world, job["id"])
    assert {i: r["outcome"] for i, r in _records(rows).items()} == {
        i: r["outcome"] for i, r in _records(previewed).items()
    }


@pytest.mark.journey("J38.2")
@pytest.mark.structures(*BOTH)
def test_a_load_whose_lease_was_taken_commits_nothing(world, monkeypatch):
    """Given a move sent with ``stage: execute`` (0.11 R, R-F9). When another process takes the
    job's lease while this one opens the target's change set, then this one commits nothing; the
    load, run again, completes with one "Move from" change set in the target, the job's own."""
    from app.engine.moves import move_load

    _other_world, target, key = _mapped(world)
    _ledger(world, "Ledger")
    opening = move_load._start

    taken = []

    def start(session, job):
        opening(session, job)
        if not taken:
            # Another process holds the job now, as its lease's takeover writes it; the rollback
            # gives it back, and the next run opens the change set again.
            taken.append(job.change_set_id)
            job.lease_owner = "another-process"
            session.flush()

    monkeypatch.setattr(move_load, "_start", start)
    job = ok(_start(world, key, target, _ledgers(world), stage="execute"), 202)
    _run(world)
    done = ok(world.api.get(f"/jobs/{job['id']}"))
    assert taken and done["state"] == "completed", done
    opened = [c["id"] for c in _change_sets(world, target) if c["name"].startswith("Move from")]
    assert opened == [done["changeSetId"]] and taken[0] not in opened


@pytest.mark.journey("J38")
@pytest.mark.structures(*BOTH)
def test_a_confirmation_refused(world):
    """Given dry runs waiting for confirmation. When the mapping changed after one, when one has
    nothing to create or update, and when the target runs another release than the dry run's, each
    confirmation is refused with its code, the job still waits and no change set is created."""
    other, target, key = _mapped(world)
    _ledger(world, "Ledger")
    before = len(_change_sets(world, target))

    def refuse(job, status, code):
        refused(world.api.post(f"/jobs/{job['id']}/confirm"), status, code)
        assert ok(world.api.get(f"/jobs/{job['id']}"))["state"] == "awaiting_confirmation"
        assert len(_change_sets(world, target)) == before

    job, _seen = _preview(world, key, target, _ledgers(world))
    match = {"kind": "setMatch", "sourceType": world.key("R"), "match": {"field": "name"}}
    ok(_operate(world, key, match))
    refuse(job, 409, "MOVE_MAPPING_CHANGED")

    ok(_operate(world, key, {"kind": "unmapType", "sourceType": world.key("R")}))
    job, _seen = _preview(world, key, target, _ledgers(world))
    refuse(job, 422, "MOVE_NOTHING_TO_MOVE")
    ok(
        world.api.post(
            f"/model-mappings/{key}/undo", {"expectedVersion": _read(world, key)["version"]}
        )
    )

    job, _seen = _preview(world, key, target, _ledgers(world))
    model = copy.deepcopy(other.configuration.model)
    model["release"]["version"] += "-next"
    ok(world.activate(world.install(model, name="Next")["id"], target))
    refuse(job, 409, "MODEL_RELEASE_CHANGED")
