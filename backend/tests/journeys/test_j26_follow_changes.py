"""J26 — Follow changes reliably (USER_JOURNEYS.md).

Each test writes in a workspace of its own, whose feed starts empty, and reads it through
``GET /workspaces/{key}/feed``. J26 step 3 (an expired position) is F2's.
"""

from uuid import uuid4

import pytest
from scenario import ok, refused


def _workspace(world):
    key = f"feed-{uuid4().hex[:8]}"
    ok(world.api.post("/workspaces", {"key": key, "label": "Feed site"}), 201)
    return key


def _page(world, workspace, **params):
    return ok(world.api.get(f"/workspaces/{workspace}/feed", **params))


def _follow(world, workspace, after=0, **params):
    """Every entry after ``after``, page by page until the reader is caught up."""
    entries = []
    while True:
        page = _page(world, workspace, after=after, **params)
        entries += page["items"]
        assert page["nextAfter"] >= after
        after = page["nextAfter"]
        if after == page["headPosition"]:
            return entries


def _staged(world, change_set):
    return {
        "changeSetId": change_set["id"],
        "expectedChangeSetVersion": world.current(change_set)["version"],
    }


def _changed(entry):
    return (entry["kind"], entry["action"], entry["id"])


@pytest.mark.journey("J26")
@pytest.mark.structures("R", "R.n", "K", "B1n")
def test_follow_the_feed_and_resume_from_a_stored_position(world):
    """Given a new workspace with an empty feed. When an integrator creates a record, renames it,
    sets one value, relates it, removes the relationship and deletes the record, then reads the feed
    from the start two entries at a time until caught up. Then positions run 1..N with no gap in the
    order of the writes; each entry names what changed (kind, action, id, type keys, version, field
    names and attribute types, never values) with a user as its cause. Reading from a stored middle
    position returns exactly the later entries. An unknown workspace, a page size out of bounds and a
    position past the head are refused."""
    ws = _workspace(world)
    empty = _page(world, ws)
    assert (empty["items"], empty["headPosition"], empty["nextAfter"]) == ([], 0, 0)

    r = world.made("R", "Followed", workspace=ws)
    k = world.made("K", "Followed token", workspace=ws)
    renamed = ok(world.update("R", r["id"], r["version"], name="Followed, renamed"))
    value = f"/objects/{world.key('R')}/{r['id']}/attributes/{world.key('R.n')}"
    valued = ok(world.api.post(value, {"value": 7, "expectedVersion": renamed["version"]}), 201)
    relation = ok(world.relate("B1n", r["id"], k["id"]), 201)
    gone = world.api.delete(f"/relations/{relation['id']}", expectedVersion=relation["version"])
    assert gone.status_code == 204, gone.text
    current = world.record("R", r["id"], workspaceKey=ws)
    deleted = world.api.delete(
        f"/objects/{world.key('R')}/{r['id']}", expectedVersion=current["version"]
    )
    assert deleted.status_code == 204, deleted.text

    entries = _follow(world, ws, pageSize=2)
    assert [e["position"] for e in entries] == list(range(1, len(entries) + 1))
    assert [_changed(e) for e in entries] == [
        ("object", "created", r["id"]),
        ("object", "created", k["id"]),
        ("object", "updated", r["id"]),
        ("object", "updated", r["id"]),
        ("relation", "created", relation["id"]),
        ("relation", "deleted", relation["id"]),
        ("object", "deleted", r["id"]),
    ]
    assert all(e["cause"] == {"kind": "user"} for e in entries)
    assert all(e["eventId"] and e["occurredAt"] and e["modelReleaseId"] for e in entries)
    created, _, rename, set_value, related, unrelated, removed = entries
    assert (created["objectTypeKey"], created["applicationKey"]) == (
        world.key("R"),
        world.app("R"),
    )
    assert (rename["version"], rename["changedFields"]) == (renamed["version"], ["name"])
    assert set_value["version"] == valued["version"]
    assert set_value["attributeTypeKeys"] == [world.key("R.n")]
    assert "value" not in set_value and 7 not in set_value.values()
    for entry in (related, unrelated):
        assert (entry["relationTypeKey"], entry["fromObjectId"], entry["toObjectId"]) == (
            world.key("B1n"),
            r["id"],
            k["id"],
        )
        assert "objectTypeKey" not in entry
    assert removed["objectTypeKey"] == world.key("R")

    head = _page(world, ws)
    assert (head["headPosition"], head["earliestPosition"]) == (len(entries), 1)
    resumed = _follow(world, ws, after=3)
    assert resumed == entries[3:]

    refused(world.api.get("/workspaces/no-such-site/feed"), 404, "workspace_not_found")
    refused(world.api.get(f"/workspaces/{ws}/feed", pageSize=0), 422, "request_validation_error")
    refused(
        world.api.get(f"/workspaces/{ws}/feed", pageSize=1001), 422, "request_validation_error"
    )
    error = refused(
        world.api.get(f"/workspaces/{ws}/feed", after=len(entries) + 1), 409, "feed_position_ahead"
    )
    assert error["details"]["headPosition"] == len(entries)


@pytest.mark.journey("J26.1")
@pytest.mark.structures("R", "R.u")
def test_batches_carry_their_job_and_refused_writes_leave_no_gap(world):
    """Given a new workspace with one record. When an independent batch with one rejected item, an
    atomic batch that is rejected and a write with a stale version are sent, then one more record is
    created. Then only the applied items have entries, each with the job as its cause; the rejected
    work took no position, and the next write follows the last entry with no gap."""
    ws = _workspace(world)
    r = world.made("R", "Holder", workspace=ws, values={"R.u": "TAKEN"})

    def create(name, u):
        return {
            "op": "create",
            "applicationKey": world.app("R"),
            "objectTypeKey": world.key("R"),
            "name": name,
            "attributes": [
                {"attributeTypeKey": k, "value": v}
                for k, v in {**world.required_values("R"), world.key("R.u"): u}.items()
            ],
        }

    items = [create("First", "B1"), create("Clash", "TAKEN"), create("Second", "B2")]
    body = {"workspaceKey": ws, "policy": "independent", "run": "inline", "items": items}
    independent = ok(world.api.post("/batches", body))
    job = independent["job"]["id"]
    applied = [i["id"] for i in independent["items"] if i["status"] == "applied"]
    assert len(applied) == 2

    atomic = {**body, "policy": "atomic", "items": [create("Third", "B3"), create("X", "TAKEN")]}
    assert ok(world.api.post("/batches", atomic))["job"]["result"] != "applied"
    refused(world.update("R", r["id"], r["version"] + 5, name="Stale"), 409, "version_conflict")
    after = world.made("R", "After", workspace=ws)

    entries = _follow(world, ws)
    assert [e["position"] for e in entries] == [1, 2, 3, 4]
    assert [e["id"] for e in entries] == [r["id"], *applied, after["id"]]
    assert [e.get("cause") for e in entries[1:3]] == [{"kind": "job", "id": job}] * 2
    assert entries[3]["cause"] == {"kind": "user"}


@pytest.mark.journey("J26.2")
@pytest.mark.structures("R", "K", "B1n")
def test_a_publish_lists_what_it_changed_then_itself(world):
    """Given a new workspace with records and a relationship. When a change set creates, renames,
    relates and deletes, while a second change set is validated and discarded, and the first is
    published, then withdrawn. Then change-set work takes no position; the publish adds one entry
    per record and relationship it changed, records created or changed first, relationships removed,
    relationships added, records removed, each with the publication as cause, then the publication's
    own entry; untouched records have none; live data read at that position equals the publication.
    The withdrawal adds one entry."""
    ws = _workspace(world)
    kept = world.made("R", "Kept", workspace=ws)
    renamed = world.made("R", "To rename", workspace=ws)
    removed = world.made("R", "To remove", workspace=ws)
    token = world.made("K", "Token", workspace=ws)
    other_token = world.made("K", "Other token", workspace=ws)
    old = ok(world.relate("B1n", removed["id"], token["id"]), 201)
    head = _page(world, ws)["headPosition"]

    cs = world.change_set(workspace=ws)
    added = world.made("R", "Added", change_set=world.current(cs), workspace=ws)
    staged = world.record("R", renamed["id"], changeSetId=cs["id"])
    body = {"name": "Renamed", "expectedVersion": staged["version"], **_staged(world, cs)}
    ok(world.api.patch(f"/objects/{world.key('R')}/{renamed['id']}", body))
    new = ok(world.relate("B1n", added["id"], other_token["id"], **_staged(world, cs)), 201)
    relation = world.api.get(f"/relations/{old['id']}", changeSetId=cs["id"])
    gone = world.api.delete(
        f"/relations/{old['id']}", expectedVersion=ok(relation)["version"], **_staged(world, cs)
    )
    assert gone.status_code == 204, gone.text
    staged = world.record("R", removed["id"], changeSetId=cs["id"])
    deleted = world.api.delete(
        f"/objects/{world.key('R')}/{removed['id']}",
        expectedVersion=staged["version"],
        **_staged(world, cs),
    )
    assert deleted.status_code == 204, deleted.text
    other = world.change_set(workspace=ws)
    assert ok(world.api.post(f"/change-sets/{other['id']}/validation"))["valid"] is True
    discarded = world.api.delete(
        f"/change-sets/{other['id']}", expectedVersion=world.current(other)["version"]
    )
    assert discarded.status_code == 204, discarded.text
    assert _page(world, ws)["headPosition"] == head

    publication = world.publish(cs, workspace=ws)
    entries = _follow(world, ws, after=head)
    assert [e["position"] for e in entries] == list(range(head + 1, head + len(entries) + 1))
    assert {_changed(e) for e in entries[:2]} == {
        ("object", "created", added["id"]),
        ("object", "updated", renamed["id"]),
    }
    assert [_changed(e) for e in entries[2:]] == [
        ("relation", "deleted", old["id"]),
        ("relation", "created", new["id"]),
        ("object", "deleted", removed["id"]),
        ("publication", "published", publication["id"]),
    ]
    assert kept["id"] not in {e["id"] for e in entries}
    assert all(e["cause"] == {"kind": "publication", "id": publication["id"]} for e in entries[:-1])
    assert next(e for e in entries if e["id"] == renamed["id"])["changedFields"] == ["name"]

    r_type = world.key("R")
    live = ok(world.api.get(f"/objects/{r_type}", workspaceKey=ws, pageSize=100))["items"]
    held = ok(world.api.get(f"/objects/{r_type}", publicationId=publication["id"], pageSize=100))
    assert sorted((i["id"], i["name"], i["version"]) for i in live) == sorted(
        (i["id"], i["name"], i["version"]) for i in held["items"]
    )

    withdrawn = world.api.post(f"/publications/{publication['id']}/withdrawal")
    assert withdrawn.status_code == 204, withdrawn.text
    last = _follow(world, ws, after=entries[-1]["position"])
    assert [_changed(e) for e in last] == [("publication", "withdrawn", publication["id"])]


LADDER = ("L1", "L2", "L3", "K", "Ll1k", "L.only1", "L.extra")


@pytest.mark.journey("J26.3")
@pytest.mark.structures(*LADDER)
def test_a_published_type_change_reads_as_reclassified(world):
    """Given in a new workspace a top-level L1 record t related to a K record through the
    relationship only L1 has, with an L2 child, and another L1 record. When t is moved under the
    other in a change set, which makes it L2 and its child L3, and published. Then the feed has a
    reclassified entry for each, naming the previous type, plus the removal of the relationship the
    new type lacks, and no values."""
    ws = _workspace(world)
    k = world.made("K", "Ladder token", workspace=ws)
    t = world.made(
        "L1",
        "Moving",
        workspace=ws,
        values={"L.code": "M-1", "L.only1": "kept for later"},
        relations=[
            {"relationTypeKey": world.key("Ll1k"), "direction": "outgoing", "otherObjectId": k["id"]}
        ],
    )
    child = world.made("L2", "Moving 2", workspace=ws, parent=t["id"], values={"L.code": "M-2"})
    t2 = world.made("L1", "Receiving", workspace=ws, values={"L.code": "R-1"})
    head = _page(world, ws)["headPosition"]

    cs = world.change_set(workspace=ws)
    operation = {"kind": "move", "objectId": t["id"], "parentObjectId": t2["id"]}
    inputs = [
        {
            "objectId": t["id"],
            "attributes": [{"attributeTypeKey": world.key("L.extra"), "value": "given"}],
        }
    ]
    mappings = [
        {"fromObjectTypeKey": world.key("L1"), "toObjectTypeKey": world.key("L2"), "attributes": []}
    ]
    request = {"operation": operation, "inputs": inputs, "choices": {"mappings": mappings}}
    plan = ok(world.api.post(f"/change-sets/{cs['id']}/restructurings/preview", request))
    assert plan["status"] == "ready", plan
    request |= {
        "planDigest": plan["planDigest"],
        "expectedChangeSetVersion": world.current(cs)["version"],
    }
    ok(world.api.post(f"/change-sets/{cs['id']}/restructurings", request))
    assert _page(world, ws)["headPosition"] == head
    publication = world.publish(cs, workspace=ws)

    entries = _follow(world, ws, after=head)
    by_id = {e["id"]: e for e in entries}
    moved, below = by_id[t["id"]], by_id[child["id"]]
    assert (moved["action"], moved["objectTypeKey"], moved["previousObjectTypeKey"]) == (
        "reclassified",
        world.key("L2"),
        world.key("L1"),
    )
    assert (below["action"], below["objectTypeKey"], below["previousObjectTypeKey"]) == (
        "reclassified",
        world.key("L3"),
        world.key("L2"),
    )
    assert moved["changedFields"][0] == "objectType"
    assert {world.key("L.only1"), world.key("L.extra")} <= set(moved["attributeTypeKeys"])
    dropped = [e for e in entries if e["kind"] == "relation"]
    assert [(e["action"], e["relationTypeKey"], e["fromObjectId"]) for e in dropped] == [
        ("deleted", world.key("Ll1k"), t["id"])
    ]
    assert "kept for later" not in str(entries)
    assert _changed(entries[-1]) == ("publication", "published", publication["id"])


@pytest.mark.journey("J26.4")
@pytest.mark.structures("R", "K", "B1n")
def test_filters_return_matching_entries_with_a_bounded_scan(world):
    """Given a new workspace with many R records, a few K records and relationships between them.
    When the feed is read filtered by kind and by object type, a page at a time. Then the pages hold
    exactly the matching entries of the unfiltered feed, in order; a sparse filter answers pages with
    fewer entries, or none, and moves on by at most ten pages' worth of positions."""
    ws = _workspace(world)
    ledgers = [world.made("R", f"Ledger {n:02d}", workspace=ws) for n in range(24)]
    token = world.made("K", "Rare token", workspace=ws)
    relation = ok(world.relate("B1n", ledgers[-1]["id"], token["id"]), 201)
    everything = _follow(world, ws)

    relations = _follow(world, ws, kind="relation", pageSize=5)
    assert [e["id"] for e in relations] == [relation["id"]]
    tokens = _follow(world, ws, objectTypeKey=world.key("K"), pageSize=2)
    assert [e["id"] for e in tokens] == [token["id"]]
    both = _follow(world, ws, objectTypeKey=[world.key("K"), world.key("R")], pageSize=3)
    assert both == [e for e in everything if e["kind"] == "object"]

    sparse = _page(world, ws, kind="relation", pageSize=2, after=0)
    assert sparse["items"] == [] and sparse["nextAfter"] == 20
    assert sparse["headPosition"] == len(everything)


@pytest.mark.journey("J26.5")
@pytest.mark.structures("R")
def test_concurrent_writers_get_gapless_positions_in_commit_order(world):
    """Given a new workspace with three records. When three clients rename one record each and a
    fourth creates a record, all at once. Then the feed holds every change once, positions 1..N with no
    gap, each record's entries rising with its version; another workspace's feed is untouched."""
    ws, other = _workspace(world), _workspace(world)
    records = [world.made("R", f"Shared {n}", workspace=ws) for n in range(3)]

    def rename(record):
        return lambda: world.update("R", record["id"], record["version"], name="Renamed at once")

    def create(name):
        return lambda: world.create("R", name, workspace=ws)

    responses = world.race(ws, *[rename(r) for r in records], create("Racing"))
    assert sorted(r.status_code for r in responses) == [200] * 3 + [201]

    entries = _follow(world, ws)
    assert [e["position"] for e in entries] == list(range(1, 8))
    for record in records:
        versions = [e["version"] for e in entries if e["id"] == record["id"]]
        assert versions == sorted(versions) and len(versions) == 2
    assert _page(world, other)["headPosition"] == 0
