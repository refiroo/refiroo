"""J30 — The events' acceptance (USER_JOURNEYS.md, CONSUMER_API "C13 event scenarios", Base 0.9 C13).

The CONSUMER_API scenarios a J30 test does not already walk, end to end: a write, the deriver, the
dispatcher and a receiver on ``localhost``, compared with the pull feed and the lists. Each test
starts the application with the subscriptions capability on, as J30.8 does, and drives the deriver
and the dispatcher itself (``derive_events``, ``dispatch``), except the last, which starts an
application whose threads run on their own, as a deployment's do. The scenarios already walked are
listed in the C13 plan with the test that walks each.
"""

import time
from itertools import pairwise
from uuid import uuid4

import pytest
from scenario import consumer_list, consumer_object, derive_events, dispatch, ok, refused
from test_j30_consumer_events import (
    EVERY,
    LEDGER,
    _activate,
    _age,
    _delete,
    _head,
    _permit,
    _workspace,
)
from test_j30_delivery import Receiver, _feed, _read, _resume, _subscribe
from test_j30_subscriptions import PATH, SUBSCRIPTIONS, _feed_head

# What an event tells, without its object or times: what the receiver and the pull feed compare.
TOLD = ("eventId", "position", "change", "id", "changed")


@pytest.fixture
def receiver():
    with Receiver() as running:
        yield running


def _received(receiver, path):
    """The requests answered on ``path``, in the order they arrived."""
    return sorted((r for r in receiver.requests if r["path"] == path), key=lambda r: r["arrived"])


def _events(receiver, path):
    return [e for r in _received(receiver, path) for e in r["body"]["events"]]


def _told(events):
    return [tuple(tuple(e[k]) if k == "changed" else e[k] for k in TOLD) for e in events]


def _staged(world, cs):
    return {"changeSetId": cs["id"], "expectedChangeSetVersion": world.current(cs)["version"]}


def _create(world, name):
    return {
        "op": "create",
        "applicationKey": world.app("R"),
        "objectTypeKey": world.key("R"),
        "name": name,
        "attributes": [
            {"attributeTypeKey": key, "value": value}
            for key, value in {**world.required_values("R"), world.key("R.u"): f"U-{uuid4().hex[:10]}"}.items()
        ],
    }


def _staged_rename(world, cs, record_id, name):
    staged = world.record("R", record_id, changeSetId=cs["id"])
    body = {"name": name, "expectedVersion": staged["version"], **_staged(world, cs)}
    return ok(world.api.patch(f"/objects/{world.key('R')}/{record_id}", body))


def _listed(world, workspace, **params):
    """Every item of the R list under ``params``, by the definition's ID output."""
    ident = world.key("Capi.id")
    read = {"workspace": workspace, "pageSize": 100, **params}
    page = ok(consumer_list(world, world.key("Capi.all"), **read))
    items = list(page["items"])
    while page["nextCursor"]:
        page = ok(consumer_list(world, world.key("Capi.all"), cursor=page["nextCursor"], **read))
        items += page["items"]
    return {item[ident]: item for item in items}


@pytest.mark.journey("J30")
@pytest.mark.settings(**SUBSCRIPTIONS)
@pytest.mark.structures(*LEDGER, "R.u")
def test_a_publish_reaches_receivers_in_batches_as_the_pull_feed_has_it(world, receiver):
    """Scenarios 4 and 13. Given a full and an identity subscription to the event over every
    change, batching up to 100. When a change set creates 150 records by one batch, renames an existing record twice and
    deletes another, and is published. Then each receiver gets requests of at most 100 events in
    position order, each sent after the previous one was answered; one event per changed object, the
    twice-renamed one once; every event caused by the publication, at or below its eventSequence.
    What each received equals the pull feed's read with its payload, and each full object equals
    get by ID."""
    _activate(world, "events")
    ws = _workspace(world)
    renamed = world.made("R", "To rename", workspace=ws)
    removed = world.made("R", "To remove", workspace=ws)
    derive_events(world)
    full = _subscribe(world, ws, receiver.url + "/full", events=[EVERY], maxEventsPerBatch=100)
    identity = _subscribe(
        world, ws, receiver.url + "/identity", events=[EVERY], payload="identity", maxEventsPerBatch=100
    )
    start = full["acknowledgedThrough"]

    cs = world.change_set(workspace=ws)
    body = {
        **_staged(world, cs),
        "policy": "atomic",
        "run": "inline",
        "items": [_create(world, f"Staged {index}") for index in range(150)],
    }
    result = ok(world.api.post("/batches", body))
    assert result["job"]["result"] == "applied", result["job"]
    _staged_rename(world, cs, renamed["id"], "Renamed once")
    _staged_rename(world, cs, renamed["id"], "Renamed twice")
    staged = world.record("R", removed["id"], changeSetId=cs["id"])
    gone = world.api.delete(
        f"/objects/{world.key('R')}/{removed['id']}", expectedVersion=staged["version"], **_staged(world, cs)
    )
    assert gone.status_code == 204, gone.text
    publication = world.publish(cs, workspace=ws)
    derive_events(world)
    dispatch(world)

    listed = ok(world.api.get(f"/api/consumer/{world.key('Capi')}/v1/publications", workspace=ws))
    sequence = next(p["eventSequence"] for p in listed["items"] if p["id"] == publication["id"])
    pulled = _feed(world, ws, start, EVERY)
    assert len(pulled) == 152
    for path, payload in (("/hook/full", "full"), ("/hook/identity", "identity")):
        requests = _received(receiver, path)
        assert [len(r["body"]["events"]) for r in requests] == [100, 52]
        assert all(later["arrived"] >= earlier["answered"] for earlier, later in pairwise(requests))
        events = _events(receiver, path)
        assert _told(events) == _told(pulled)
        assert len({e["id"] for e in events}) == len(events)
        assert {e["cause"]["kind"] for e in events} == {"publication"}
        assert {e["cause"]["id"] for e in events} == {publication["id"]}
        assert all(e["position"] <= sequence for e in events)
        assert all(("object" in e) == (payload == "full" and e["id"] != removed["id"]) for e in events)
    for event in _events(receiver, "/hook/full"):
        if event["id"] != removed["id"]:
            assert event["object"] == ok(consumer_object(world, event["id"], workspace=ws))
    changes = {e["id"]: e["change"] for e in pulled}
    assert (changes[renamed["id"]], changes[removed["id"]]) == ("updated", "deleted")
    assert _read(world, identity)["acknowledgedThrough"] == _head(world, ws)


@pytest.mark.journey("J30")
@pytest.mark.settings(**SUBSCRIPTIONS)
@pytest.mark.structures(*LEDGER, "R.u")
def test_work_that_does_not_reach_live_data_sends_nothing(world, receiver):
    """Scenarios 5 and 6. Given a full subscription. When an atomic batch whose last item is refused
    is rolled back, a write with a stale version is refused, and a change set is edited, validated
    and discarded; then a record is renamed live. Then the receiver gets one request holding only
    the rename's event, and the subscription has acknowledged through the feed's head."""
    _activate(world, "events")
    ws = _workspace(world)
    record = world.made("R", "Ledger", workspace=ws)
    stale = record["version"]
    ok(world.update("R", record["id"], stale, name="Ledger current"))
    derive_events(world)
    created = _subscribe(world, ws, receiver.url, events=[EVERY])

    rolled_back = {
        "workspaceKey": ws,
        "policy": "atomic",
        "run": "inline",
        "items": [
            _create(world, "Never kept"),
            {"op": "update", "target": {"id": record["id"]}, "expectedVersion": stale, "name": "Stale"},
        ],
    }
    assert ok(world.api.post("/batches", rolled_back))["job"]["result"] != "applied"
    refused(world.update("R", record["id"], stale, name="Refused"), 409, "VERSION_CONFLICT")
    cs = world.change_set(workspace=ws)
    _staged_rename(world, cs, record["id"], "Only in the change set")
    world.made("R", "Only staged", change_set=world.current(cs), workspace=ws)
    assert ok(world.api.post(f"/change-sets/{cs['id']}/validation"))["valid"] is True
    discarded = world.api.delete(f"/change-sets/{cs['id']}", expectedVersion=world.current(cs)["version"])
    assert discarded.status_code == 204, discarded.text
    derive_events(world)
    dispatch(world)
    assert receiver.requests == []

    version = world.record("R", record["id"], workspaceKey=ws)["version"]
    ok(world.update("R", record["id"], version, name="Ledger renamed"))
    derive_events(world)
    dispatch(world)
    (request,) = receiver.requests
    assert [(e["change"], e["id"]) for e in request["body"]["events"]] == [("updated", record["id"])]
    assert _read(world, created)["acknowledgedThrough"] == _head(world, ws)


@pytest.mark.journey("J30")
@pytest.mark.settings(**SUBSCRIPTIONS)
@pytest.mark.structures(*LEDGER, "R.u")
def test_filters_scope_deliveries_as_the_lists_do(world, receiver):
    """Scenario 7 and C-D114. Given subscriptions to the event over every change narrowed by the
    definition's type, related and projection parameters, one each. When records in and out of each
    scope are created, renamed, related and deleted. Then each receiver got the events of exactly
    those changed objects the R list returns under the same parameter, and of those deleted
    (a deletion passes every filter but the type). When the relationship that put a record in the
    related filter's scope is removed, the list no longer returns it and that subscription receives
    nothing of the change, while the one narrowed by type receives its update."""
    _activate(world, "events")
    ws = _workspace(world)
    kind, token, permit = (world.key(f"Capi.{n}") for n in ("kind", "token", "permit"))
    near, far = (world.made("K", f"Token {uuid4().hex[:6]}", workspace=ws) for _ in range(2))
    permitted = world.made("R", "Permitted", workspace=ws)
    region, _d = _permit(world, permitted["id"], ws)
    derive_events(world)
    filters = {
        "kind": {kind: world.key("Capi.R")},
        "token": {token: near["name"]},
        "permit": {permit: region["name"]},
    }
    subscriptions = {
        name: _subscribe(world, ws, receiver.url + f"/{name}", events=[EVERY], filters=value)
        for name, value in filters.items()
    }
    start = subscriptions["kind"]["acknowledgedThrough"]

    related = world.made("R", "Near ledger", workspace=ws)
    relation = ok(world.relate("B11", related["id"], near["id"]), 201)
    elsewhere = world.made("R", "Far ledger", workspace=ws)
    ok(world.relate("B11", elsewhere["id"], far["id"]), 201)
    _permit(world, elsewhere["id"], ws)
    plain = world.made("R", "Plain ledger", workspace=ws)
    world.made("R2", "Plain entry", parent=plain["id"], workspace=ws)
    ok(world.update("R", permitted["id"], permitted["version"], name="Permitted renamed"))
    near_gone = world.made("R", "Related, removed", workspace=ws)
    ok(world.relate("B11", near_gone["id"], world.made("K", f"Token {uuid4().hex[:6]}", workspace=ws)["id"]), 201)
    _delete(world, "R", near_gone["id"], ws)
    plain_gone = world.made("R", "Plain, removed", workspace=ws)
    _delete(world, "R", plain_gone["id"], ws)
    derive_events(world)
    dispatch(world)

    changed = {e["id"]: e["objectType"] for e in _feed(world, ws, start, EVERY)}
    deleted = {near_gone["id"], plain_gone["id"]}
    for name, value in filters.items():
        listed = set(_listed(world, ws, **value))
        expected = {i for i in changed if i in listed or (i in deleted and changed[i] == world.key("Capi.R"))}
        assert {e["id"] for e in _events(receiver, f"/hook/{name}")} == expected, name
    assert related["id"] in _listed(world, ws, **filters["token"])
    assert permitted["id"] in _listed(world, ws, **filters["permit"])

    sent = {name: len(_received(receiver, f"/hook/{name}")) for name in filters}
    removed = world.api.delete(f"/relations/{relation['id']}", expectedVersion=relation["version"])
    assert removed.status_code == 204, removed.text
    derive_events(world)
    dispatch(world)
    assert related["id"] not in _listed(world, ws, **filters["token"])
    assert len(_received(receiver, "/hook/token")) == sent["token"]
    assert _read(world, subscriptions["token"])["acknowledgedThrough"] == _head(world, ws)
    (update,) = _received(receiver, "/hook/kind")[sent["kind"] :]
    assert [(e["change"], e["id"]) for e in update["body"]["events"]] == [("updated", related["id"])]


@pytest.mark.journey("J30")
@pytest.mark.settings(**SUBSCRIPTIONS)
@pytest.mark.structures(*LEDGER, "R.u")
def test_a_receiver_resets_and_resyncs_after_its_events_expired(world, receiver):
    """C8 scenario 14 and C-D110's order. Given a full subscription suspended by hand while records
    are written and a change set is published, then the entries aged past retention. When it is
    resumed, the answer is 409 EVENTS_EXPIRED naming reset; resumed with reset, one more record is
    written, then the receiver reads the live list and applies what it receives for later writes
    and deletions. Then its copy equals the live list: nothing missed, and the only event repeated
    is the write between the reset and the list read, of an object the list already gave."""
    _activate(world, "events")
    ws = _workspace(world)
    created = _subscribe(world, ws, receiver.url, events=[EVERY])
    ok(world.api.post(f"{PATH}/{created['id']}/suspend", {"expectedVersion": created["version"]}))
    first = world.made("R", "First", workspace=ws)
    kept = world.made("R", "Kept", workspace=ws)
    cs = world.change_set(workspace=ws)
    staged = world.made("R", "Staged", change_set=world.current(cs), workspace=ws)
    publication = world.publish(cs, workspace=ws)
    _delete(world, "R", first["id"], ws)
    derive_events(world)
    _age(world, ws, 31, publication["feedPosition"])

    error = refused(_resume(world, created), 409, "EVENTS_EXPIRED")
    assert "reset" in error["message"]
    resumed = ok(_resume(world, created, reset=True))
    assert resumed["acknowledgedThrough"] == _feed_head(world, ws)
    between = world.made("R", "Between", workspace=ws)
    read_at = _feed_head(world, ws)
    copy = _listed(world, ws)

    later = world.made("R", "Later", workspace=ws)
    ok(world.update("R", kept["id"], world.record("R", kept["id"], workspaceKey=ws)["version"], name="Kept renamed"))
    _delete(world, "R", staged["id"], ws)
    derive_events(world)
    dispatch(world)

    received = _events(receiver, "/hook")
    for event in received:
        if event["change"] == "deleted":
            copy.pop(event["id"], None)
        else:
            copy[event["id"]] = event["object"]
    assert copy == _listed(world, ws)
    assert {kept["id"], later["id"], between["id"]} <= set(copy) and staged["id"] not in copy
    repeated = [(e["change"], e["id"]) for e in received if e["position"] <= read_at]
    assert repeated == [("created", between["id"])]


@pytest.mark.journey("J30")
@pytest.mark.settings(**SUBSCRIPTIONS)
@pytest.mark.structures(*LEDGER, "R.u")
def test_a_running_application_delivers_on_its_own(world, receiver):
    """Given an application started as a deployment runs it, its deriver's and dispatcher's
    threads on, and a subscription. When a record is created. Then the receiver gets its event
    within 10 s, with nothing driving either thread; after the application stops, both threads have
    stopped and the subscription holds no lease."""
    from harness_identity import TestClient
    from sqlalchemy import create_engine, text
    from sqlalchemy.pool import NullPool

    from app.main import create_app

    _activate(world, "events")
    ws = _workspace(world)
    created = _subscribe(world, ws, receiver.url, events=[EVERY])
    running = create_app()
    running.state.run_job_worker = False
    with TestClient(running):
        record = world.made("R", "Told on its own", workspace=ws)
        deadline = time.monotonic() + 10
        while not receiver.delivered() and time.monotonic() < deadline:
            time.sleep(0.1)
        (body,) = receiver.delivered()
        assert [(e["change"], e["id"]) for e in body["events"]] == [("created", record["id"])]
        assert body["events"][0]["object"] == ok(consumer_object(world, record["id"], workspace=ws))
    for state in (running.state.event_deriver, running.state.consumer_dispatcher):
        assert state._thread is None
    engine = create_engine(world.database, poolclass=NullPool)
    with engine.connect() as connection:
        owner = connection.scalar(
            text("SELECT lease_owner FROM consumer_subscriptions WHERE public_id = :id"), {"id": created["id"]}
        )
    engine.dispose()
    assert owner is None
    assert _read(world, created)["acknowledgedThrough"] == _head(world, ws)
