"""Tracks Q, B and F composed (Base 0.9 T1): a background job writes dated records and their
relationships while a reader follows the feed (J24, J26); the model-aware query with ``asOf`` (J23.3)
and the edge list (J22.2) read the same state in live data, a change set and a publication.

Each test writes in a workspace of its own, whose feed starts empty. The journey application runs no
worker thread; a test runs the engine's job worker chunk by chunk, five items a chunk, as J24 does.
Records are created with IDs the client chose, so the job's relationship items can name them.
"""

import time
from uuid import uuid4

import pytest
from scenario import ok

from app.db import SessionLocal
from app.engine.jobs.worker import JobWorker, WorkerSettings

CHUNK = 5
DAY = "2026-06-30"
STRUCTURES = ("E", "E.from", "E.to", "K.code", "Bee")


def _worker(owner, lease=120):
    return JobWorker(SessionLocal, WorkerSettings(CHUNK, lease, 7), owner=owner)


def _workspace(world):
    key = f"t1-{uuid4().hex[:8]}"
    ok(world.api.post("/workspaces", {"key": key, "label": "Checkpoint site"}), 201)
    return key


def _period(n):
    """Every third record ends on 2026-07-01, every third starts then, the rest always apply."""
    return {1: {"E.to": "2026-07-01"}, 2: {"E.from": "2026-07-01"}}.get(n % 3, {})


def _records(world, count, prefix):
    """``create`` items for ``count`` dated records with chosen IDs, and the IDs effective on DAY."""
    items, effective = [], set()
    for n in range(count):
        values = {**world.required_values("E")}
        values.update({world.key(k): v for k, v in _period(n).items()})
        record_id = str(uuid4())
        items.append(
            {
                "op": "create",
                "id": record_id,
                "applicationKey": world.app("E"),
                "objectTypeKey": world.key("E"),
                "name": f"{prefix} {n:03d}",
                "attributes": [{"attributeTypeKey": k, "value": v} for k, v in values.items()],
            }
        )
        if n % 3 != 2:
            effective.add(record_id)
    return items, effective


def _links(world, records, count):
    """``createRelation`` items joining record i to record i + 1."""
    return [
        {
            "op": "createRelation",
            "relationTypeKey": world.key("Bee"),
            "from": {"id": records[n]["id"]},
            "to": {"id": records[n + 1]["id"]},
        }
        for n in range(count)
    ]


def _submit(world, items, *, policy="independent", **context):
    body = {**context, "policy": policy, "run": "background", "items": items}
    return ok(world.api.post("/batches", body), 202)


def _follow(world, workspace, after):
    entries = []
    while True:
        page = ok(world.api.get(f"/workspaces/{workspace}/feed", after=after, pageSize=7))
        entries += page["items"]
        after = page["nextAfter"]
        if after == page["headPosition"]:
            return entries


def _dated(world, workspace, **context):
    """The IDs the model query answers for DAY, every page followed."""
    ids, cursor = set(), None
    while True:
        body = {
            "objectTypeKey": world.key("E"),
            "asOf": DAY,
            "context": context,
            "pageSize": 10,
            **({"cursor": cursor} if cursor else {}),
        }
        page = ok(world.api.post(f"/workspaces/{workspace}/queries/objects", body))
        ids |= {item["id"] for item in page["items"]}
        cursor = page.get("nextCursor")
        if not cursor:
            return ids


def _edges(world, workspace, **context):
    """The edge list's ``Bee`` relationships as (id, from, to), every page followed."""
    edges, cursor = set(), None
    while True:
        page = ok(
            world.api.get(
                f"/workspaces/{workspace}/relations",
                relationTypeKey=world.key("Bee"),
                direction="outgoing",
                pageSize=10,
                cursor=cursor,
                **context,
            )
        )
        edges |= {(e["relationId"], e["source"]["id"], e["target"]["id"]) for e in page["items"]}
        cursor = page.get("nextCursor")
        if not cursor:
            return edges


def _named(entries):
    """What the feed's entries name: created record IDs and created relationships."""
    records = {e["id"] for e in entries if (e["kind"], e["action"]) == ("object", "created")}
    relations = {
        (e["id"], e["fromObjectId"], e["toObjectId"])
        for e in entries
        if (e["kind"], e["action"]) == ("relation", "created")
    }
    return records, relations


def _gapless(entries, after=0):
    return [e["position"] for e in entries] == list(range(after + 1, after + len(entries) + 1))


@pytest.mark.journey("J24", "J26", "J23.3", "J22.2")
@pytest.mark.structures(*STRUCTURES)
def test_a_resumed_background_job_followed_and_read_back(world):
    """Given a new workspace and a reader following its feed from position 0. When a background job
    creates 30 dated records and then 20 relationships between them, five items a chunk, the reader
    reads the feed after every chunk, and the process stops after two chunks and another takes over.
    Then the reader holds one entry per applied item, gapless, none repeated across the restart, each
    with the job as cause; the model query for a date answers exactly the records whose period covers
    it, and the edge list exactly the 20 relationships, both among what the feed named."""
    ws = _workspace(world)
    records, effective = _records(world, 30, "Rate")
    links = _links(world, records, 20)
    job = _submit(world, records + links, workspaceKey=ws)

    entries, after = [], 0
    first = _worker("process-1", lease=1)
    for _chunk in range(2):
        assert first.run_once()
        entries += _follow(world, ws, after)
        after = entries[-1]["position"]
    assert len(entries) == 10
    second = _worker("process-2")
    time.sleep(1.1)
    while second.run_once():
        entries += _follow(world, ws, after)
        after = entries[-1]["position"] if entries else after
    assert ok(world.api.get(f"/jobs/{job['id']}"))["state"] == "completed"

    assert _gapless(entries) and len(entries) == 50
    assert all(e["cause"] == {"kind": "job", "id": job["id"]} for e in entries)
    named_records, named_links = _named(entries)
    assert named_records == {r["id"] for r in records} and len(named_links) == 20

    assert _dated(world, ws) == effective and len(effective) == 20
    edges = _edges(world, ws)
    assert edges == named_links
    assert {(f, t) for _id, f, t in edges} == {(i["from"]["id"], i["to"]["id"]) for i in links}


@pytest.mark.journey("J24", "J26.2", "J23.3", "J22.2", "J11.3")
@pytest.mark.structures(*STRUCTURES)
def test_a_background_job_into_a_change_set_then_published(world):
    """Given a new workspace with a change set and a reader at the feed's head. When a background job
    writes 12 dated records and 8 relationships into the change set, and the change set is published.
    Then before the publish the feed holds nothing and the change set's dated query and edge list
    show the job's result; after it the feed holds one entry per record and relationship with the
    publication as cause, then the publication's own entry; live data and the publication answer the
    dated query and the edge list exactly as the change set did."""
    ws = _workspace(world)
    cs = world.change_set(ws)
    records, effective = _records(world, 12, "Staged rate")
    links = _links(world, records, 8)
    job = _submit(
        world,
        records + links,
        changeSetId=cs["id"],
        expectedChangeSetVersion=world.current(cs)["version"],
    )
    _worker("staging").run_until_idle()
    assert ok(world.api.get(f"/jobs/{job['id']}"))["result"] == "applied"

    assert _follow(world, ws, 0) == []
    staged_dated = _dated(world, ws, changeSetId=cs["id"])
    staged_edges = _edges(world, ws, changeSetId=cs["id"])
    assert staged_dated == effective and len(staged_edges) == 8
    assert _dated(world, ws) == set() and _edges(world, ws) == set()

    publication = world.publish(cs, workspace=ws)
    entries = _follow(world, ws, 0)
    assert _gapless(entries) and len(entries) == 21
    published = entries[-1]
    assert (published["kind"], published["action"], published["id"]) == (
        "publication",
        "published",
        publication["id"],
    )
    assert all(e["cause"] == {"kind": "publication", "id": publication["id"]} for e in entries[:-1])
    named_records, named_links = _named(entries[:-1])
    assert named_records == {r["id"] for r in records} and named_links == staged_edges

    assert _dated(world, ws) == staged_dated
    assert _dated(world, ws, publicationId=publication["id"]) == staged_dated
    assert _edges(world, ws) == staged_edges
    assert _edges(world, ws, publicationId=publication["id"]) == staged_edges


@pytest.mark.journey("J24.2", "J26.1", "J23.3", "J22.2")
@pytest.mark.structures(*STRUCTURES)
def test_cancelled_jobs_leave_the_feed_and_the_reads_consistent(world):
    """Given a new workspace. When an independent job of records and relationships is cancelled after
    its first chunk, and an atomic job of records and relationships is cancelled while it runs; then
    a record is created by hand. Then the feed holds entries for the first chunk's three records and
    two relationships only, nothing of the atomic job, and the hand-made record's entry next, with no
    gap; the dated query and the edge list show exactly what that chunk wrote."""
    ws = _workspace(world)
    worker = _worker("canceller")

    kept, kept_effective = _records(world, 12, "Kept")
    # The first chunk: three records and two relationships between them.
    items = kept[:3] + _links(world, kept, 2) + kept[3:]
    independent = _submit(world, items, workspaceKey=ws)
    assert worker.run_once()
    ok(world.api.post(f"/jobs/{independent['id']}/cancel"), 202)
    worker.run_until_idle()
    assert ok(world.api.get(f"/jobs/{independent['id']}"))["state"] == "cancelled"

    rolled, _ = _records(world, 8, "Rolled back")
    atomic = _submit(world, rolled + _links(world, rolled, 4), workspaceKey=ws, policy="atomic")
    with world.holding(ws) as held:
        chunk = held.start(worker.run_once)
        held.waiting(1)
        ok(world.api.post(f"/jobs/{atomic['id']}/cancel"), 202)
    chunk.result(timeout=20)
    worker.run_until_idle()
    assert ok(world.api.get(f"/jobs/{atomic['id']}"))["state"] == "cancelled"

    by_hand = world.made("E", "By hand", workspace=ws)
    entries = _follow(world, ws, 0)
    assert _gapless(entries) and len(entries) == 6
    assert all(e["cause"] == {"kind": "job", "id": independent["id"]} for e in entries[:5])
    assert (entries[-1]["id"], entries[-1]["cause"]) == (by_hand["id"], {"kind": "user"})
    named_records, named_links = _named(entries[:5])
    assert named_records == {r["id"] for r in kept[:3]} and len(named_links) == 2

    first_chunk = {r["id"] for r in kept[:3]}
    assert _dated(world, ws) == (kept_effective & first_chunk) | {by_hand["id"]}
    assert _edges(world, ws) == named_links
