"""J30 — Follow a consumer API's changes (USER_JOURNEYS.md).

Each test activates a release whose ``Capi`` declares events, as J25.3 does, then writes in a
workspace of its own, whose feed starts empty. The journey application does not run the event
deriver's thread, so a test derives (``derive_events``) before it reads ``GET …/events``. An expired
position (J30.5) needs entries older than the retention period; the test moves their times back in
the database, as J26.6 does.
"""

import copy
import threading
from uuid import uuid4

import pytest
from scenario import W1, consumer_events, consumer_list, consumer_object, derive_events, ok, refused
from sqlalchemy import create_engine, text
from sqlalchemy.pool import NullPool

LEDGER = ("Capi", "R", "R2", "D", "K", "G", "B11", "Bown", "R.n")
WATCHED = "ledger-changed"
EVERY = "ledger-any"
CHURN = "permit-churn"


def _events(world):
    """Capi's events: R and R2 with every change, watching the code, the name, the parent and B11;
    D, creations and deletions only; R and R2 again with no watch, so every output counts."""
    return [
        {
            "key": WATCHED,
            "objectTypes": [world.key("R"), world.key("R2")],
            "changes": ["created", "updated", "deleted"],
            "watch": {
                "fields": [world.key("Capi.code"), world.key("Capi.name"), world.key("Capi.parent")],
                "related": [world.key("Capi.B11")],
            },
        },
        {"key": CHURN, "objectTypes": [world.key("D")], "changes": ["created", "deleted"]},
        {
            "key": EVERY,
            "objectTypes": [world.key("R"), world.key("R2")],
            "changes": ["created", "updated", "deleted"],
        },
    ]


def _activate(world, suffix, events=None, change=None):
    """Activate the configuration's model with ``Capi`` declaring ``events`` (by default
    :func:`_events`); ``change`` edits the definition further."""
    model = copy.deepcopy(world.configuration.model)
    model["release"]["version"] += f"-{suffix}"
    (definition,) = [d for d in model["consumerApis"] if d["key"] == world.key("Capi")]
    declared = _events(world) if events is None else events
    if declared:
        definition["operations"]["events"] = {"custom": declared}
    if change is not None:
        change(model, definition)
    release = world.install(model)
    ok(world.activate(release["id"]))
    return release


def _workspace(world):
    key = f"events-{uuid4().hex[:8]}"
    ok(world.api.post("/workspaces", {"key": key, "label": "Events site"}), 201)
    return key


def _page(world, workspace, **params):
    return ok(consumer_events(world, workspace=workspace, **params))


def _follow(world, workspace, after=0, **params):
    """Every event after ``after``, page by page by cursor until caught up."""
    page = _page(world, workspace, after=after, **params)
    events = list(page["items"])
    while not page["caughtUp"]:
        page = _page(world, workspace, cursor=page["cursor"], **params)
        events += page["items"]
    return events


def _head(world, workspace):
    return ok(world.api.get(f"/workspaces/{workspace}/feed"))["headPosition"]


def _told(events):
    """What each event tells, without its identifiers and times."""
    return [(e["event"], e["change"], e["id"], tuple(e["changed"])) for e in events]


def _sorted(world, *structures):
    return tuple(sorted(world.key(s) for s in structures))


def _version(world, structure, object_id, workspace):
    return world.record(structure, object_id, workspaceKey=workspace)["version"]


def _rename(world, structure, object_id, workspace, name):
    version = _version(world, structure, object_id, workspace)
    return ok(world.update(structure, object_id, version, name=name))


def _delete(world, structure, object_id, workspace):
    """Delete a record; one with relationships through the confirmed impact, as a client does."""
    path = f"/objects/{world.key(structure)}/{object_id}"
    version = _version(world, structure, object_id, workspace)
    response = world.api.delete(path, expectedVersion=version)
    if response.status_code == 409 and response.json()["error"]["code"] == "OBJECT_HAS_DEPENDANTS":
        impact = response.json()["error"]["details"]
        response = world.api.delete(
            path,
            expectedVersion=version,
            cascade=True,
            deletionPreviewToken=impact["deletionPreviewToken"],
        )
    assert response.status_code == 204, response.text


def _permit(world, owner, workspace, name="Permit"):
    """A D record owned by ``owner`` through Bown, under a new G (or an M under it), and the G."""
    g = world.made("G", f"Region {uuid4().hex[:6]}", workspace=workspace)
    parent = world.dependant_parent(g["id"], workspace)
    d = world.made(
        "D", name, parent=parent, workspace=workspace, relations=[world.owner("Bown", owner)]
    )
    return g, d


@pytest.mark.journey("J30.1")
@pytest.mark.structures(*LEDGER)
def test_an_objects_own_changes_are_told(world):
    """Given Capi's three events and a new workspace. When an R is created, renamed, given a value
    only the unwatched event shows, and deleted; and a D is created, renamed and deleted. Then each
    change is told under the events that take it, in position order: the watched event names the
    name but not the score, the unwatched one both; a deletion says so with no code or name. Each
    event's position is its raw feed entry's, caused by the user. The D's creation and deletion are
    told under the D event, its rename under none."""
    _activate(world, "events")
    ws = _workspace(world)
    r = world.made("R", "Ledger A", workspace=ws)
    _rename(world, "R", r["id"], ws, "Ledger B")
    version = _version(world, "R", r["id"], ws)
    ok(world.update("R", r["id"], version, values={"R.n": 7}))
    _delete(world, "R", r["id"], ws)
    derive_events(world)

    events = _follow(world, ws)
    name, score = world.key("Capi.name"), world.key("Capi.n")
    assert _told(events) == [
        (EVERY, "created", r["id"], ()),
        (WATCHED, "created", r["id"], ()),
        (EVERY, "updated", r["id"], (name,)),
        (WATCHED, "updated", r["id"], (name,)),
        (EVERY, "updated", r["id"], (score,)),
        (EVERY, "deleted", r["id"], ()),
        (WATCHED, "deleted", r["id"], ()),
    ]
    raw = [
        e["position"]
        for e in ok(world.api.get(f"/workspaces/{ws}/feed"))["items"]
        if e["id"] == r["id"]
    ]
    assert sorted({e["position"] for e in events}) == raw
    assert all(e["cause"] == {"kind": "user"} for e in events)
    assert all(e["contractVersion"] == 1 and e["objectType"] == world.key("Capi.R") for e in events)
    deleted = events[-1]
    assert (deleted["code"], deleted["name"]) == (None, None) and "object" not in deleted

    owner = world.made("R", "Owner", workspace=ws)
    head = _head(world, ws)
    _g, d = _permit(world, owner["id"], ws)
    _rename(world, "D", d["id"], ws, "Permit renamed")
    _delete(world, "D", d["id"], ws)
    derive_events(world)
    churn = _follow(world, ws, after=head, event=CHURN)
    assert _told(churn) == [(CHURN, "created", d["id"], ()), (CHURN, "deleted", d["id"], ())]
    assert all(e["objectType"] == world.key("Capi.D") for e in churn)


@pytest.mark.journey("J30.2")
@pytest.mark.structures(*LEDGER)
def test_changes_to_what_an_object_shows_are_told(world):
    """Given an R with two R2 children, a K it projects through B11 and a D it owns under a G. When
    the R is renamed, the K renamed, the G renamed and the B11 relation deleted. Then the rename
    updates the R and each child: the watched event names the children's parent, the unwatched one
    their parent, path and hierarchy. The K's rename updates the R naming the B11 projection under
    both events; the G's, the R naming its permits under the unwatched event only (the watch leaves
    them out); deleting the relation updates its former owner naming the projection."""
    _activate(world, "events")
    ws = _workspace(world)
    r = world.made("R", "Ledger", workspace=ws)
    children = [world.made("R2", f"Entry {i}", parent=r["id"], workspace=ws) for i in (1, 2)]
    k = world.made("K", "Token", workspace=ws)
    relation = ok(world.relate("B11", r["id"], k["id"]), 201)
    g, _d = _permit(world, r["id"], ws)
    derive_events(world)
    parent, path, hierarchy = (world.key(f"Capi.{n}") for n in ("parent", "path", "hierarchy"))
    projection, permits = world.key("Capi.B11"), world.key("Capi.Bown")

    head = _head(world, ws)
    _rename(world, "R", r["id"], ws, "Ledger renamed")
    derive_events(world)
    told = set(_told(_follow(world, ws, after=head)))
    shown = tuple(sorted((parent, path, hierarchy)))
    assert told == {
        (WATCHED, "updated", r["id"], (world.key("Capi.name"),)),
        (EVERY, "updated", r["id"], (world.key("Capi.name"),)),
        *((WATCHED, "updated", c["id"], (parent,)) for c in children),
        *((EVERY, "updated", c["id"], shown) for c in children),
    }

    head = _head(world, ws)
    _rename(world, "K", k["id"], ws, "Token renamed")
    derive_events(world)
    assert set(_told(_follow(world, ws, after=head))) == {
        (WATCHED, "updated", r["id"], (projection,)),
        (EVERY, "updated", r["id"], (projection,)),
    }

    head = _head(world, ws)
    _rename(world, "G", g["id"], ws, "Region renamed")
    derive_events(world)
    assert _told(_follow(world, ws, after=head)) == [(EVERY, "updated", r["id"], (permits,))]

    head = _head(world, ws)
    removed = world.api.delete(f"/relations/{relation['id']}", expectedVersion=relation["version"])
    assert removed.status_code == 204, removed.text
    derive_events(world)
    assert set(_told(_follow(world, ws, after=head))) == {
        (WATCHED, "updated", r["id"], (projection,)),
        (EVERY, "updated", r["id"], (projection,)),
    }


@pytest.mark.journey("J30.3")
@pytest.mark.structures(*LEDGER, "R.u")
def test_batches_and_publishes_are_told_with_their_cause(world):
    """Given an R in a new workspace. When an inline batch creates an R, renames the first and
    fails an update with a stale version; a write is refused; a change set renames the R and adds
    one, and is published. Then the batch's applied items are told with the job as cause and the
    failed item, the refused write and the change-set edits make none. The publish's changes are
    told with the publication as cause, at or below the position the publications list gives it."""
    _activate(world, "events")
    ws = _workspace(world)
    r = world.made("R", "Ledger", workspace=ws)
    derive_events(world)

    head = _head(world, ws)
    stale = r["version"]
    batch = {
        "workspaceKey": ws,
        "policy": "independent",
        "run": "inline",
        "items": [
            {
                "op": "create",
                "applicationKey": world.app("R"),
                "objectTypeKey": world.key("R"),
                "name": "From the batch",
                "attributes": [
                    {"attributeTypeKey": key, "value": value}
                    for key, value in world.required_values("R").items()
                ],
            },
            {"op": "update", "target": {"id": r["id"]}, "expectedVersion": stale, "name": "Renamed"},
            {"op": "update", "target": {"id": r["id"]}, "expectedVersion": stale, "name": "Stale"},
        ],
    }
    result = ok(world.api.post("/batches", batch))
    job = result["job"]["id"]
    created = next(i["id"] for i in result["items"] if i.get("action") == "created")
    refused(world.update("R", r["id"], stale, name="Refused"), 409, "VERSION_CONFLICT")
    derive_events(world)
    batched = _follow(world, ws, after=head, event=EVERY)
    assert _told(batched) == [
        (EVERY, "created", created, ()),
        (EVERY, "updated", r["id"], (world.key("Capi.name"),)),
    ]
    assert all(e["cause"] == {"kind": "job", "id": job} for e in batched)

    head = _head(world, ws)
    cs = world.change_set(workspace=ws)
    staged = world.record("R", r["id"], changeSetId=cs["id"])
    body = {
        "name": "Renamed in the change set",
        "expectedVersion": staged["version"],
        "changeSetId": cs["id"],
        "expectedChangeSetVersion": world.current(cs)["version"],
    }
    ok(world.api.patch(f"/objects/{world.key('R')}/{r['id']}", body))
    added = world.made("R", "Added in the change set", change_set=world.current(cs), workspace=ws)
    derive_events(world)
    assert _follow(world, ws, after=head) == []

    publication = world.publish(cs, workspace=ws)
    derive_events(world)
    published = _follow(world, ws, after=head, event=EVERY)
    assert set(_told(published)) == {
        (EVERY, "created", added["id"], ()),
        (EVERY, "updated", r["id"], (world.key("Capi.name"),)),
    }
    assert all(e["cause"] == {"kind": "publication", "id": publication["id"]} for e in published)
    listed = ok(world.api.get(f"/api/consumer/{world.key('Capi')}/v1/publications", workspace=ws))
    sequence = next(p["eventSequence"] for p in listed["items"] if p["id"] == publication["id"])
    assert all(e["position"] <= sequence for e in published)


@pytest.mark.journey("J30.3")
@pytest.mark.structures("Capi", "L1", "L2", "L3", "Ll1k", "L.only1", "L.extra")
def test_a_type_change_is_told_as_the_three_kinds(world):
    """Given Capi exposing L1 and L2 with an event over each and one over both, and a top-level L1
    record with an L2 child. When a change set moves the L1 under another L1, so it becomes an L2
    and its child an L3, and is published. Then, seen from the L1 event, the record is deleted; from
    the L2 event it is created and its child deleted; from the event over both it is updated with
    objectType among the changed outputs and its child, now of a type the definition does not
    expose, deleted."""

    def expose(_model, definition):
        definition["exposes"] += [world.key("L1"), world.key("L2")]
        definition["publicNames"].update({world.key("L1"): "Top", world.key("L2"): "Middle"})

    events = [
        {"key": "tops", "objectTypes": [world.key("L1")], "changes": ["created", "updated", "deleted"]},
        {"key": "middles", "objectTypes": [world.key("L2")], "changes": ["created", "updated", "deleted"]},
        {
            "key": "ladder",
            "objectTypes": [world.key("L1"), world.key("L2")],
            "changes": ["created", "updated", "deleted"],
        },
    ]
    _activate(world, "ladder", events=events, change=expose)
    top = world.made("L1", "Moving", values={"L.code": "M-1", "L.only1": "kept"})
    child = world.made("L2", "Moving 2", parent=top["id"], values={"L.code": "M-2"})
    receiving = world.made("L1", "Receiving", values={"L.code": "R-1"})
    head = _head(world, W1)

    cs = world.change_set()
    operation = {"kind": "move", "objectId": top["id"], "parentObjectId": receiving["id"]}
    inputs = [
        {
            "objectId": top["id"],
            "attributes": [{"attributeTypeKey": world.key("L.extra"), "value": "given"}],
        }
    ]
    mappings = [
        {"fromObjectTypeKey": world.key("L1"), "toObjectTypeKey": world.key("L2"), "attributes": []}
    ]
    body = {"operation": operation, "inputs": inputs, "choices": {"mappings": mappings}}
    plan = ok(world.api.post(f"/change-sets/{cs['id']}/restructurings/preview", body))
    applied = {
        **body,
        "planDigest": plan["planDigest"],
        "expectedChangeSetVersion": world.current(cs)["version"],
    }
    ok(world.api.post(f"/change-sets/{cs['id']}/restructurings", applied))
    world.publish(cs)
    derive_events(world)

    told = {(e["event"], e["change"], e["id"]): e for e in _follow(world, W1, after=head)}
    assert set(told) == {
        ("tops", "deleted", top["id"]),
        ("middles", "created", top["id"]),
        ("ladder", "updated", top["id"]),
        ("middles", "deleted", child["id"]),
        ("ladder", "deleted", child["id"]),
    }
    assert "objectType" in told[("ladder", "updated", top["id"])]["changed"]
    assert told[("tops", "deleted", top["id"])]["objectType"] == "Top"
    assert told[("middles", "created", top["id"])]["objectType"] == "Middle"
    assert told[("middles", "deleted", child["id"])]["objectType"] == "Middle"


@pytest.mark.journey("J30.4")
@pytest.mark.structures(*LEDGER)
def test_read_filter_page_and_shape_the_events(world):
    """Given a definition without events, then Capi's events, an R with five R2 children, a K it
    projects and a D under a G it owns, and the R renamed. When the events are read narrowed by
    event, by type, through a related K and by a projection parameter; five events of one position
    are read two at a time; with the full payload and with identity only; with an entity tag. Then
    each narrowing keeps what a list would, a deleted R's events pass the related filter; the position is
    read whole by cursor, and a caught-up cursor later returns the next events; each full item's
    object is what get by ID answers with the same parameters, and identity items are the same
    without it; the tag answers 304 until a live write or a new event. Every refusal names its code."""
    refused(consumer_events(world), 404, "EVENTS_NOT_DECLARED")
    _activate(world, "events")
    ws = _workspace(world)
    r = world.made("R", "Ledger", workspace=ws)
    children = [world.made("R2", f"Entry {i}", parent=r["id"], workspace=ws) for i in range(1, 6)]
    k = world.made("K", f"Token {uuid4().hex[:6]}", workspace=ws)
    ok(world.relate("B11", r["id"], k["id"]), 201)
    g, _d = _permit(world, r["id"], ws)
    gone = world.made("R", "Short-lived", workspace=ws)
    _delete(world, "R", gone["id"], ws)
    head = _head(world, ws)
    _rename(world, "R", r["id"], ws, "Ledger renamed")
    derive_events(world)

    assert {e["event"] for e in _follow(world, ws, event=CHURN)} == {CHURN}
    kind, token, permit = (world.key(f"Capi.{n}") for n in ("kind", "token", "permit"))
    entries = _follow(world, ws, **{kind: world.key("Capi.R2")})
    assert entries and {e["id"] for e in entries} == {c["id"] for c in children}
    # An event whose object no longer exists passes, its creation as well as its deletion (C-D90).
    related = _follow(world, ws, **{token: k["name"]})
    assert {e["id"] for e in related} == {r["id"], gone["id"]}
    assert {("created", gone["id"]), ("deleted", gone["id"])} <= {(e["change"], e["id"]) for e in related}

    first = _page(world, ws, after=head, event=EVERY, pageSize=2)
    pages, read = [first], list(first["items"])
    while not pages[-1]["caughtUp"]:
        pages.append(_page(world, ws, cursor=pages[-1]["cursor"], event=EVERY, pageSize=2))
        read += pages[-1]["items"]
    assert all(len(p["items"]) <= 2 for p in pages) and len(pages) >= 3
    assert {e["position"] for e in read} == {head + 1}
    assert {e["id"] for e in read} == {r["id"], *(c["id"] for c in children)}
    assert [e["eventId"] for e in read] == list(dict.fromkeys(e["eventId"] for e in read))
    later = world.made("R", "Later", workspace=ws)
    derive_events(world)
    after_caught_up = _page(world, ws, cursor=pages[-1]["cursor"], event=EVERY)
    assert [(e["change"], e["id"]) for e in after_caught_up["items"]] == [("created", later["id"])]

    region = g["name"]
    full = _follow(world, ws, **{permit: region})
    assert {e["id"] for e in full} >= {r["id"]}
    current = next(e for e in reversed(full) if e["id"] == r["id"])
    assert current["object"] == ok(consumer_object(world, r["id"], workspace=ws, **{permit: region}))
    assert current["stateAt"] >= current["position"]
    assert current["code"] == current["object"][world.key("Capi.code")]
    assert current["name"] == current["object"][world.key("Capi.name")]
    identity = _follow(world, ws, payload="identity", **{permit: region})
    stripped = [{k: v for k, v in e.items() if k not in ("object", "stateAt")} for e in full]
    assert identity == stripped
    assert ok(consumer_events(world, workspace=ws, payload="identity", pageSize=1000))["items"]

    path = f"/api/consumer/{world.key('Capi')}/v1/events?workspace={ws}"
    tagged = world.api.client.get(path)
    tag = tagged.headers["ETag"]
    assert world.api.client.get(path, headers={"If-None-Match": tag}).status_code == 304
    # A live write changes the full objects before its event is derived (0.9 R-F13, C-D65).
    _rename(world, "R", r["id"], ws, "Ledger renamed again")
    assert world.api.client.get(path, headers={"If-None-Match": tag}).status_code == 200
    tag = world.api.client.get(path).headers["ETag"]
    world.made("R", "Newest", workspace=ws)
    derive_events(world)
    assert world.api.client.get(path, headers={"If-None-Match": tag}).status_code == 200

    for params, status, code in (
        ({"event": "no-such-event"}, 400, "UNKNOWN_EVENT"),
        ({"publication": "latest"}, 400, "PARAMETER_NOT_SUPPORTED"),
        ({"asOf": "2026-01-01"}, 400, "PARAMETER_NOT_SUPPORTED"),
        ({f"to.{permit}": region}, 400, "PARAMETER_NOT_SUPPORTED"),
        ({"pageSize": 101}, 400, "INVALID_PAGE_SIZE"),
        ({"pageSize": 0, "payload": "identity"}, 400, "INVALID_PAGE_SIZE"),
        ({"pageSize": 1001, "payload": "identity"}, 400, "INVALID_PAGE_SIZE"),
        ({"payload": "everything"}, 400, "INVALID_PAYLOAD"),
        ({"after": "first"}, 400, "INVALID_POSITION"),
        ({"after": 0, "cursor": first["cursor"]}, 400, "CONFLICTING_PAGE_PARAMETERS"),
        ({"cursor": "not-a-cursor"}, 400, "INVALID_CURSOR"),
        ({"after": _head(world, ws) + 1}, 409, "EVENT_POSITION_AHEAD"),
    ):
        refused(consumer_events(world, workspace=ws, **params), status, code)
    refused(consumer_events(world, workspace="no-such-site"), 404, "WORKSPACE_NOT_FOUND")
    elsewhere = _workspace(world)
    refused(consumer_events(world, workspace=elsewhere, cursor=first["cursor"]), 400, "INVALID_CURSOR")


def _age(world, workspace, days, through):
    """Make the workspace's entries up to position ``through`` ``days`` older (J26.6)."""
    engine = create_engine(world.database, poolclass=NullPool)
    with engine.begin() as connection:
        connection.execute(
            text(
                "UPDATE audit_events SET occurred_at = occurred_at - make_interval(days => :d) "
                "WHERE workspace_key = :w AND feed_position <= :p"
            ),
            {"d": days, "w": workspace, "p": through},
        )
    engine.dispose()


def _count(world, workspace, through):
    engine = create_engine(world.database, poolclass=NullPool)
    with engine.connect() as connection:
        found = connection.scalar(
            text("SELECT count(*) FROM consumer_events WHERE workspace_key = :w AND position <= :p"),
            {"w": workspace, "p": through},
        )
    engine.dispose()
    return found


@pytest.mark.journey("J30.5")
@pytest.mark.structures(*LEDGER)
def test_an_expired_position_names_the_publication_to_resync_from(world):
    """Given a workspace with records, a publish that renames, adds and deletes, and live writes
    after it, all derived, with the entries up to the publish older than retention. When the events
    are read from the start. Then the read is refused as expired, naming the earliest and head
    positions and the active publication with its eventSequence; read from that position it is
    answered. A reader that reads the publication's list and follows the events from its
    eventSequence ends with live data. The sweep removes the expired events. A workspace without a
    publication expires nothing."""
    _activate(world, "events")
    ws = _workspace(world)
    renamed = world.made("R", "To rename", workspace=ws)
    removed = world.made("R", "To remove", workspace=ws)
    world.made("R", "Kept", workspace=ws)
    cs = world.change_set(workspace=ws)
    world.made("R", "Added", change_set=world.current(cs), workspace=ws)
    staged = world.record("R", renamed["id"], changeSetId=cs["id"])
    body = {
        "name": "Renamed",
        "expectedVersion": staged["version"],
        "changeSetId": cs["id"],
        "expectedChangeSetVersion": world.current(cs)["version"],
    }
    ok(world.api.patch(f"/objects/{world.key('R')}/{renamed['id']}", body))
    staged = world.record("R", removed["id"], changeSetId=cs["id"])
    deleted = world.api.delete(
        f"/objects/{world.key('R')}/{removed['id']}",
        expectedVersion=staged["version"],
        changeSetId=cs["id"],
        expectedChangeSetVersion=world.current(cs)["version"],
    )
    assert deleted.status_code == 204, deleted.text
    publication = world.publish(cs, workspace=ws)
    later = world.made("R", "Later", workspace=ws)
    _rename(world, "R", renamed["id"], ws, "Renamed again")
    _delete(world, "R", later["id"], ws)
    derive_events(world)
    sequence = publication["feedPosition"]
    _age(world, ws, 31, sequence)

    head = _page(world, ws, after=sequence)["headPosition"]
    for after in (0, sequence - 1):
        error = refused(consumer_events(world, workspace=ws, after=after), 410, "EVENTS_EXPIRED")
        assert error["details"] == {
            "earliestPosition": sequence + 1,
            "headPosition": head,
            "publication": {"id": publication["id"], "eventSequence": sequence},
        }

    listed = ok(
        consumer_list(world, world.key("Capi.all"), workspace=ws, publication=publication["id"], pageSize=100)
    )
    held = {item[world.key("Capi.id")] for item in listed["items"]}
    kind = world.key("Capi.kind")
    for event in _follow(world, ws, after=sequence, event=EVERY, **{kind: world.key("Capi.R")}):
        if event["change"] == "created":
            held.add(event["id"])
        elif event["change"] == "deleted":
            held.discard(event["id"])
    live = ok(consumer_list(world, world.key("Capi.all"), workspace=ws, pageSize=100))
    assert held == {item[world.key("Capi.id")] for item in live["items"]}

    assert _count(world, ws, sequence) > 0
    world.api.client.app.state.event_deriver.sweep()
    assert _count(world, ws, sequence) == 0
    assert _page(world, ws, after=sequence)["items"]

    other = _workspace(world)
    world.made("R", "Unpublished", workspace=other)
    derive_events(world)
    _age(world, other, 31, _head(world, other))
    assert _page(world, other, after=0)["items"]


def _reset(world, workspace):
    """Forget the workspace's events and start its derivation again from the first position."""
    engine = create_engine(world.database, poolclass=NullPool)
    with engine.begin() as connection:
        connection.execute(text("DELETE FROM consumer_events WHERE workspace_key = :w"), {"w": workspace})
        connection.execute(
            text("UPDATE consumer_event_checkpoints SET position = 0 WHERE workspace_key = :w"),
            {"w": workspace},
        )
    engine.dispose()


@pytest.mark.journey("J30")
@pytest.mark.structures(*LEDGER)
def test_derivation_is_repeatable_shared_and_follows_the_writes_release(world):
    """Given writes in a workspace, derived in one run. When the events are derived again from the
    same state, and again by two derivers at once. Then each time the same events with the same IDs
    result, every position derived once. (Derived as each write happened, a rename would not reach a
    child created after it: owners are read when the deriver runs, C-D89.) Given a write made under the
    release with three events, then a release adding a fourth over R's creations activated before
    it is derived. Then the write is told under the three only; an R created afterwards under all
    four."""
    _activate(world, "events")
    ws = _workspace(world)
    r = world.made("R", "Ledger", workspace=ws)
    _rename(world, "R", r["id"], ws, "Ledger renamed")
    world.made("R2", "Entry", parent=r["id"], workspace=ws)
    derive_events(world)
    derived = _follow(world, ws)
    assert len({e["position"] for e in derived}) == 3

    _reset(world, ws)
    derive_events(world)
    assert _follow(world, ws) == derived

    from app.db import SessionLocal
    from app.engine.events.worker import EventDeriver

    _reset(world, ws)
    derivers = [EventDeriver(SessionLocal) for _ in range(2)]
    threads = [threading.Thread(target=d.run_until_idle) for d in derivers]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    assert _follow(world, ws) == derived

    before = world.made("R", "Before the release", workspace=ws)
    born = {"key": "ledger-born", "objectTypes": [world.key("R")], "changes": ["created"]}
    _activate(world, "born", events=[*_events(world), born])
    derive_events(world)
    after = world.made("R", "After the release", workspace=ws)
    derive_events(world)
    told = {(e["event"], e["id"]) for e in _follow(world, ws)}
    assert ("ledger-born", before["id"]) not in told
    assert {(WATCHED, before["id"]), (EVERY, before["id"])} <= told
    assert {("ledger-born", after["id"]), (WATCHED, after["id"]), (EVERY, after["id"])} <= told
