"""J05 — Prepare and publish a coordinated design; J06 — Continue live work while a change set is
open (USER_JOURNEYS.md)."""

import pytest
from scenario import W1, W2, W3, numbered, ok, plan_reads, planned, refused
from test_j11_bulk_change import _batch
from test_j36_workspace_models import _on


def _staged(world, change_set):
    """The change set's write claim: its id and current version."""
    return {
        "changeSetId": change_set["id"],
        "expectedChangeSetVersion": world.current(change_set)["version"],
    }


def _update_in(world, change_set, structure, object_id, **changes):
    record = world.record(structure, object_id, changeSetId=change_set["id"])
    body = {"expectedVersion": record["version"], **_staged(world, change_set)}
    if "name" in changes:
        body["name"] = changes["name"]
    if "parent" in changes:
        body["parentObjectId"] = changes["parent"]
    if "values" in changes:
        body["attributes"] = [
            {"attributeTypeKey": world.key(k), "value": v} for k, v in changes["values"].items()
        ]
    return world.api.patch(f"/objects/{world.key(structure)}/{object_id}", body)


def _publish(world, change_set, active, workspace=W1):
    body = {
        "expectedChangeSetVersion": world.current(change_set)["version"],
        "expectedActivePublicationId": active,
    }
    return world.api.post(f"/change-sets/{change_set['id']}/publication", body)


def _publications(world, workspace=W1):
    return ok(world.api.get(f"/workspaces/{workspace}/publications"))["items"]


@pytest.mark.journey("J05")
@pytest.mark.structures("R", "K", "B1n")
def test_prepare_and_publish_a_coordinated_change(world):
    """Given W1 with publications P1 and P2. When a change set from current live creates, updates,
    deletes and relates records, is validated and published against P2. Then nothing staged shows
    live before publishing; validation is clean; P3 supersedes P2 with the model release; live and
    P3 hold every staged change and P2 reads unchanged, no longer current. A write without the change
    set version, a publish against a stale publication and a change set in a retired workspace are
    refused."""
    kept, gone = world.made("R", "Kept ledger"), world.made("R", "Gone ledger")
    world.publish(world.change_set())
    p2 = world.publish(world.change_set())
    token = world.made("K", "Staged token")

    cs = world.change_set(name="Coordinated")
    assert cs["source"] == "currentLive" and cs["version"] >= 1
    added = world.made("R", "Added ledger", change_set=world.current(cs))
    ok(_update_in(world, cs, "R", kept["id"], name="Kept, renamed"))
    staged_gone = world.record("R", gone["id"], changeSetId=cs["id"])
    deleted = world.api.delete(
        f"/objects/{world.key('R')}/{gone['id']}",
        expectedVersion=staged_gone["version"],
        **_staged(world, cs),
    )
    assert deleted.status_code == 204, deleted.text
    relation = ok(world.relate("B1n", kept["id"], token["id"], **_staged(world, cs)), 201)

    refused(world.read("R", added["id"]), 404, "OBJECT_NOT_FOUND")
    assert world.record("R", kept["id"])["name"] == "Kept ledger"
    assert world.record("R", gone["id"])["id"] == gone["id"]
    assert ok(world.api.post(f"/change-sets/{cs['id']}/validation"))["valid"] is True

    p3 = ok(_publish(world, cs, p2["id"]))
    assert (p3["publicationNumber"], p3["status"], p3["supersedesPublicationId"]) == (
        3,
        "active",
        p2["id"],
    )
    assert p3["modelReleaseId"]
    for context in ({}, {"publicationId": p3["id"]}):
        assert world.record("R", added["id"], **context)["name"] == "Added ledger"
        assert world.record("R", kept["id"], **context)["name"] == "Kept, renamed"
        refused(world.read("R", gone["id"], **context), 404, "OBJECT_NOT_FOUND")
        assert ok(world.api.get(f"/relations/{relation['id']}", **context))["id"] == relation["id"]
    assert ok(world.api.get(f"/publications/{p2['id']}"))["status"] == "withdrawn"
    assert world.record("R", kept["id"], publicationId=p2["id"])["name"] == "Kept ledger"

    another = world.change_set()
    refused(
        world.api.post(
            "/objects",
            {
                "applicationKey": world.app("R"),
                "objectTypeKey": world.key("R"),
                "name": "Unclaimed",
                "changeSetId": another["id"],
                "attributes": [
                    {"attributeTypeKey": k, "value": v}
                    for k, v in world.required_values("R").items()
                ],
            },
        ),
        409,
        "CHANGE_SET_REQUIRED",
    )
    refused(_publish(world, another, p2["id"]), 409, "WORKSPACE_ACTIVE_PUBLICATION_CONFLICT")
    refused(
        world.api.post(f"/workspaces/{W3}/change-sets", {"source": "currentLive"}),
        409,
        "WORKSPACE_RETIRED",
    )


@pytest.mark.journey("J05.1")
@pytest.mark.structures("R", "K", "B1n")
def test_a_change_set_from_current_live_is_frozen_when_it_starts(world):
    """Given live content changed after the last publication: a record corrected, one added, a
    relationship added and another removed. When a change set is created from current live and live
    renames a record and relates it again. Then the change set holds the content as at its creation,
    relationships included, not the later changes; a workspace that never published works the same
    way (SC-05)."""
    corrected = world.made("R", "Before correction")
    kept, dropped, later = (world.made("K", name) for name in ("Kept", "Dropped", "Later"))
    removed = ok(world.relate("B1n", corrected["id"], dropped["id"]), 201)
    world.publish(world.change_set())
    corrected = ok(world.update("R", corrected["id"], corrected["version"], name="Corrected"))
    addition = world.made("R", "Added after publishing")
    ok(world.relate("B1n", corrected["id"], kept["id"]), 201)
    gone = world.api.delete(f"/relations/{removed['id']}", expectedVersion=removed["version"])
    assert gone.status_code == 204
    cs = world.change_set()
    ok(world.update("R", corrected["id"], corrected["version"], name="Renamed again"))
    ok(world.relate("B1n", corrected["id"], later["id"]), 201)

    assert world.record("R", corrected["id"], changeSetId=cs["id"])["name"] == "Corrected"
    assert (
        world.record("R", addition["id"], changeSetId=cs["id"])["name"] == "Added after publishing"
    )
    staged = world.api.get(
        "/relations",
        objectId=corrected["id"],
        changeSetId=cs["id"],
        relationTypeKey=world.key("B1n"),
    )
    assert [item["object"]["id"] for item in ok(staged)["items"]] == [kept["id"]]

    second = world.made("R", "Never published", workspace=W2)
    unpublished = world.change_set(workspace=W2)
    assert world.record("R", second["id"], changeSetId=unpublished["id"])["id"] == second["id"]
    assert _publications(world, W2) == []


@pytest.mark.journey("J05.2")
@pytest.mark.structures("R")
def test_a_change_set_from_a_publication(world):
    """Given P1 and newer live records. When a change set is created from P1, one of P1's records
    edited and the change set published. Then it reads P1's content; the new publication derives from
    P1; newer live records it never touched are kept; P1 is unchanged. Naming the source wrongly is
    refused."""
    edited, renamed = world.made("R", "Edited in P1"), world.made("R", "Renamed in P1")
    p1 = world.publish(world.change_set())
    ok(world.update("R", renamed["id"], renamed["version"], name="Renamed live"))
    newer = world.made("R", "Newer live")

    cs = world.change_set(source="publication", derivedFromPublicationId=p1["id"])
    assert world.record("R", renamed["id"], changeSetId=cs["id"])["name"] == "Renamed in P1"
    ok(_update_in(world, cs, "R", edited["id"], name="Edited from P1"))
    publication = ok(_publish(world, cs, p1["id"]))
    assert publication["derivedFromPublicationId"] == p1["id"]
    assert world.record("R", edited["id"])["name"] == "Edited from P1"
    assert world.record("R", newer["id"])["name"] == "Newer live"
    assert world.record("R", edited["id"], publicationId=p1["id"])["name"] == "Edited in P1"

    for body in (
        {"source": "publication"},
        {"source": "currentLive", "derivedFromPublicationId": p1["id"]},
    ):
        refused(
            world.api.post(f"/workspaces/{W1}/change-sets", body), 422, "REQUEST_VALIDATION_ERROR"
        )


@pytest.mark.journey("J05.3")
@pytest.mark.structures("R")
def test_an_empty_change_set(world):
    """When a change set is created with no source. Then it is empty although live holds records, and
    a record created in it reads there only."""
    live = world.made("R", "Live only")
    cs = ok(world.api.post(f"/workspaces/{W1}/change-sets", {}), 201)
    assert cs["source"] == "empty"
    changes = ok(world.api.get(f"/objects/{world.key('R')}", changeSetId=cs["id"]))["items"]
    assert changes == []
    refused(world.read("R", live["id"], changeSetId=cs["id"]), 404, "OBJECT_NOT_FOUND")
    staged = world.made("R", "Only staged", change_set=world.current(cs))
    assert world.record("R", staged["id"], changeSetId=cs["id"])["name"] == "Only staged"
    refused(world.read("R", staged["id"]), 404, "OBJECT_NOT_FOUND")


@pytest.mark.journey("J05.4")
@pytest.mark.structures("R", "G", "M", "D", "D.active", "Bown")
def test_an_invalid_graph_is_named_and_not_published(world):
    """Given a change set where two records breach the scoped uniqueness rule (a container moved
    under another scope). When it is validated, then published. Then validation names both; publishing
    is refused; nothing is published and the change set and live are unchanged. A change set that
    validated cleanly is refused the same way when live adds a record breaching the rule with it."""
    r = world.made("R", "Owner")
    g1, g2 = world.made("G", "Scope one"), world.made("G", "Scope two")
    m1 = world.made("M", "Container one", parent=g1["id"])
    m2 = world.made("M", "Container two", parent=g2["id"])
    d1, d2 = (
        world.made(
            "D",
            name,
            parent=m["id"],
            values={"D.active": True},
            relations=[world.owner("Bown", r["id"])],
        )
        for name, m in (("First", m1), ("Second", m2))
    )
    cs = world.change_set()
    ok(_update_in(world, cs, "M", m2["id"], parent=g1["id"]))
    publications = _publications(world)

    validation = ok(world.api.post(f"/change-sets/{cs['id']}/validation"))
    assert validation["valid"] is False
    named = [d for d in validation["diagnostics"] if d.get("code") == "DUPLICATE_RELATION_SCOPE"]
    assert named
    # One record by its ID, the other by its owning relationship's.
    details = named[0]["details"]
    staged = ok(world.api.get(f"/relations/{details['relationId']}", changeSetId=cs["id"]))
    assert {details["conflictingObjectId"], staged["toObjectId"]} == {d1["id"], d2["id"]}
    refused(_publish(world, cs, None), 422, "WORKSPACE_GRAPH_INVALID")
    assert _publications(world) == publications
    assert world.record("M", m2["id"])["parentObjectId"] == g2["id"]

    g3 = world.made("G", "Scope three")
    m3 = world.made("M", "Container three", parent=g3["id"])
    clean = world.change_set()
    world.made(
        "D",
        "Staged",
        parent=m3["id"],
        values={"D.active": True},
        relations=[world.owner("Bown", r["id"])],
        change_set=world.current(clean),
    )
    assert ok(world.api.post(f"/change-sets/{clean['id']}/validation"))["valid"] is True
    world.made(
        "D",
        "Live rival",
        parent=m3["id"],
        values={"D.active": True},
        relations=[world.owner("Bown", r["id"])],
    )
    refused(_publish(world, clean, None), 422, "WORKSPACE_GRAPH_INVALID")


@pytest.mark.journey("J05.4")
@pytest.mark.structures("R", "G", "D", "D.active", "Bown")
def test_a_value_patched_in_a_change_set_is_checked_like_an_edit(world):
    """Given an active D record d1 and an inactive d2 within one G record, both owned by r, and a
    change set. When d2's active value is patched to true as a single attribute, then the change set
    holds the breach as an edit of the record does (200) and validation names it
    (DUPLICATE_RELATION_SCOPE) and publishing is refused."""
    r = world.made("R", "Owner")
    g = world.made("G", "Scope")
    owned = [world.owner("Bown", r["id"])]
    world.made(
        "D",
        "First",
        parent=world.dependant_parent(g["id"]),
        values={"D.active": True},
        relations=owned,
    )
    d2 = world.made(
        "D",
        "Second",
        parent=world.dependant_parent(g["id"]),
        values={"D.active": False},
        relations=owned,
    )
    cs = world.change_set()
    path = f"/objects/{world.key('D')}/{d2['id']}/attributes/{world.key('D.active')}"
    body = {"value": True, "expectedVersion": d2["version"], **_staged(world, cs)}
    ok(world.api.patch(path, body))
    validation = ok(world.api.post(f"/change-sets/{cs['id']}/validation"))
    assert "DUPLICATE_RELATION_SCOPE" in [d.get("code") for d in validation["diagnostics"]]
    refused(_publish(world, cs, None), 422, "WORKSPACE_GRAPH_INVALID")


@pytest.mark.journey("J05.5")
@pytest.mark.structures("R")
def test_rename_or_discard_a_change_set(world):
    """Given a change set at version v, and one pinned to a release that is not active. When it is
    renamed with v twice, then discarded with its version, and the pinned one discarded. Then the
    first rename succeeds, the second is refused, the discard removes it, and the pinned one
    discards although its release is not active; live is unchanged."""
    live = world.made("R", "Untouched")
    cs = world.change_set(name="Draft")
    renamed = ok(
        world.api.patch(
            f"/change-sets/{cs['id']}", {"name": "Renamed", "expectedVersion": cs["version"]}
        )
    )
    assert renamed["version"] == cs["version"] + 1
    refused(
        world.api.patch(
            f"/change-sets/{cs['id']}", {"name": "Again", "expectedVersion": cs["version"]}
        ),
        409,
        "CHANGE_SET_VERSION_CONFLICT",
    )
    discarded = world.api.delete(f"/change-sets/{cs['id']}", expectedVersion=renamed["version"])
    assert discarded.status_code == 204, discarded.text
    refused(world.api.get(f"/change-sets/{cs['id']}"), 404, "CHANGE_SET_NOT_FOUND")

    model, _key = world.candidate("compatible")
    release = world.install(model)
    pinned = world.change_set(modelReleaseId=release["id"])
    gone = world.api.delete(f"/change-sets/{pinned['id']}", expectedVersion=pinned["version"])
    assert gone.status_code == 204, gone.text
    assert world.record("R", live["id"])["version"] == live["version"]


@pytest.mark.journey("J05.6")
@pytest.mark.structures("R")
def test_two_writers_in_one_change_set(world):
    """Given writers A and B who read the change set at version v. When A updates record x with v,
    then B updates record y with v. Then B is refused and y is unchanged in the change set."""
    x, y = world.made("R", "Record x"), world.made("R", "Record y")
    cs = world.change_set()
    version = world.current(cs)["version"]

    def update(record, name):
        staged = world.record("R", record["id"], changeSetId=cs["id"])
        body = {
            "name": name,
            "expectedVersion": staged["version"],
            "changeSetId": cs["id"],
            "expectedChangeSetVersion": version,
        }
        return world.api.patch(f"/objects/{world.key('R')}/{record['id']}", body)

    ok(update(x, "Writer A"))
    refused(update(y, "Writer B"), 409, "CHANGE_SET_VERSION_CONFLICT")
    assert world.record("R", y["id"], changeSetId=cs["id"])["name"] == "Record y"


@pytest.mark.journey("J05.7")
@pytest.mark.structures("R")
def test_a_live_write_beside_a_capture_of_current_live(world):
    """Given actor A creating a change set from current live while actor B makes a live write, both in
    flight at once. Then B's write is saved, and A's change set either holds it or A is asked to retry
    and the retry holds it: a capture never holds part of a write. (Which of the two orders happens is
    the database's; the test cannot force the capture to have begun first without engine hooks.)"""
    record = world.made("R", "Captured")
    capture, write = world.race(
        W1,
        lambda: world.api.post(f"/workspaces/{W1}/change-sets", {"source": "currentLive"}),
        lambda: world.update("R", record["id"], record["version"], name="Written meanwhile"),
    )
    assert ok(write)["name"] == "Written meanwhile"
    if capture.status_code == 409:
        refused(capture, 409, "CHANGE_SET_SNAPSHOT_RETRY")
        capture = world.api.post(f"/workspaces/{W1}/change-sets", {"source": "currentLive"})
    cs = ok(capture, 201)
    staged = world.record("R", record["id"], changeSetId=cs["id"])["name"]
    assert staged in {"Captured", "Written meanwhile"}


@pytest.mark.journey("J06")
@pytest.mark.structures("R")
def test_live_edits_and_staged_edits_publish_together(world):
    """Given a change set editing records x and y. When a steward corrects record z live and the
    change set is published. Then live holds x's and y's staged edits and z's correction, and so does
    the new publication."""
    x, y, z = (world.made("R", f"Record {n}") for n in "xyz")
    cs = world.change_set()
    ok(_update_in(world, cs, "R", x["id"], name="Staged x"))
    ok(_update_in(world, cs, "R", y["id"], name="Staged y"))
    ok(world.update("R", z["id"], z["version"], name="Live z"))
    publication = world.publish(cs)
    for context in ({}, {"publicationId": publication["id"]}):
        names = [world.record("R", r["id"], **context)["name"] for r in (x, y, z)]
        assert names == ["Staged x", "Staged y", "Live z"]


@pytest.mark.journey("J06.1")
@pytest.mark.structures("R")
def test_a_live_addition_survives_publishing(world):
    """When a record is added live after the change set was created, then the change set is
    published. Then the addition is in live data and in the new publication."""
    cs = world.change_set()
    added = world.made("R", "Added live")
    publication = world.publish(cs)
    assert world.record("R", added["id"])["name"] == "Added live"
    assert world.record("R", added["id"], publicationId=publication["id"])["name"] == "Added live"


@pytest.mark.journey("J06.2")
@pytest.mark.structures("R")
def test_the_same_record_changed_on_both_sides(world):
    """Given a change set that changed record x and another record, and live then changing x. When
    the change set is published. Then it is refused naming x; nothing is published; the change set
    and live are unchanged, and its other staged change is not applied."""
    x, other = world.made("R", "Contested x"), world.made("R", "Other")
    cs = world.change_set()
    ok(_update_in(world, cs, "R", x["id"], name="Staged x"))
    ok(_update_in(world, cs, "R", other["id"], name="Staged other"))
    x = ok(world.update("R", x["id"], x["version"], name="Live x"))
    publications = _publications(world)

    error = refused(_publish(world, cs, None), 409, "VERSION_CONFLICT")
    named = [c for c in error["details"]["conflicts"] if c["id"] == x["id"]]
    assert named and named[0]["code"] == "VERSION_MISMATCH"
    assert _publications(world) == publications
    assert world.record("R", x["id"])["name"] == "Live x"
    assert world.record("R", other["id"])["name"] == "Other"
    assert world.record("R", x["id"], changeSetId=cs["id"])["name"] == "Staged x"


@pytest.mark.journey("J06.2")
@pytest.mark.structures("R")
def test_a_refusal_lists_at_most_twenty_conflicts_of_a_code_and_counts_the_rest(world):
    """Given a change set and live both renaming the same 23 records. When the change set is
    published. Then it is refused with 20 VERSION_MISMATCH conflicts listed and
    `details.conflictsLeftOut` counting the 3 left out; nothing is published."""
    records = [world.made("R", f"Contested {number}") for number in range(23)]
    cs = world.change_set()
    for record in records:
        ok(_update_in(world, cs, "R", record["id"], name=f"Staged {record['name']}"))
        ok(world.update("R", record["id"], record["version"], name=f"Live {record['name']}"))
    publications = _publications(world)

    error = refused(_publish(world, cs, None), 409, "VERSION_CONFLICT")
    listed = [c for c in error["details"]["conflicts"] if c["code"] == "VERSION_MISMATCH"]
    assert len(listed) == 20
    assert error["details"]["conflictsLeftOut"] == {"VERSION_MISMATCH": 3}
    assert _publications(world) == publications


@pytest.mark.journey("J06.3")
@pytest.mark.structures("R")
def test_publishing_beside_live_writes_and_other_change_sets(world):
    """Given actor A publishing a change set, actor B writing live and actor C writing in another
    change set, all in flight at once. Then all three succeed without a deadlock: the publication
    is made, B's write survives live, and C's write is in its change set. (Whether C waited for A is
    timing the test cannot see; that it is not refused or deadlocked is what it checks.)"""
    staged, live, other = (world.made("R", f"Record {n}") for n in ("staged", "live", "other"))
    cs1, cs2 = world.change_set(), world.change_set()
    ok(_update_in(world, cs1, "R", staged["id"], name="Published by A"))
    c_record = world.record("R", other["id"], changeSetId=cs2["id"])
    c_body = {"name": "Written by C", "expectedVersion": c_record["version"], **_staged(world, cs2)}
    a_body = {
        "expectedChangeSetVersion": world.current(cs1)["version"],
        "expectedActivePublicationId": None,
    }

    a, b, c = world.race(
        W1,
        lambda: world.api.post(f"/change-sets/{cs1['id']}/publication", a_body),
        lambda: world.update("R", live["id"], live["version"], name="Written by B"),
        lambda: world.api.patch(f"/objects/{world.key('R')}/{other['id']}", c_body),
    )
    ok(a), ok(b), ok(c)
    assert world.record("R", live["id"])["name"] == "Written by B"
    assert world.record("R", staged["id"])["name"] == "Published by A"
    assert world.record("R", other["id"], changeSetId=cs2["id"])["name"] == "Written by C"


@pytest.mark.journey("J05.1", "J26.2")
@pytest.mark.structures("V", "K", "Bvk")
def test_typed_values_moves_and_relationships_survive_capture_and_publish(world):
    """Current-live capture, staged values/parent/edge edits, and publication preserve typed reads
    and filters, with the publication matching live at its feed position."""
    parents = [world.made("V", name) for name in ("Old parent", "New parent")]
    values = {
        "V.code": "snapshot-copy",
        "V.rank": 7,
        "V.amount": "12.34",
        "V.flag": False,
        "V.on": "2024-02-29",
        "V.at": "2024-02-29T12:00:00+00:00",
    }
    item = world.made("V", "Typed child", parent=parents[0]["id"], values=values)
    targets = [world.made("K", name) for name in ("Original edge", "Added edge")]
    original = ok(world.relate("Bvk", item["id"], targets[0]["id"]), 201)
    cs = world.change_set()
    assert {
        k: world.value(world.record("V", item["id"], changeSetId=cs["id"]), k) for k in values
    } == {k: world.value(item, k) for k in values}
    values.update({"V.rank": 8, "V.amount": "-0.25", "V.flag": True})
    ok(_update_in(world, cs, "V", item["id"], values=values, parent=parents[1]["id"]))
    added = ok(world.relate("Bvk", item["id"], targets[1]["id"], **_staged(world, cs)), 201)
    staged = world.record("V", item["id"], changeSetId=cs["id"])

    def check(context):
        record = world.record("V", item["id"], **context)
        assert {k: world.value(record, k) for k in values} == {
            k: world.value(staged, k) for k in values
        }
        assert record["parentObjectId"] == parents[1]["id"]
        for edge in (original, added):
            assert (
                ok(world.api.get(f"/relations/{edge['id']}", **context))["toObjectId"]
                == edge["toObjectId"]
            )
        for key, value in values.items():
            found = ok(
                world.api.get(
                    f"/objects/{world.key('V')}",
                    **context,
                    **{
                        f"filter.{world.key(key)}.eq": str(value).lower()
                        if isinstance(value, bool)
                        else value
                    },
                )
            )
            assert item["id"] in {row["id"] for row in found["items"]}, key

    check({"changeSetId": cs["id"]})
    publication = world.publish(cs)
    check({})
    # Live moves past the publication's feed position; the publication keeps what live held there.
    ok(
        world.update(
            "V", item["id"], world.record("V", item["id"])["version"], values={"V.rank": 9}
        )
    )
    later = ok(world.api.get(f"/workspaces/{W1}/feed", after=publication["feedPosition"]))["items"]
    assert [(e["kind"], e["action"], e["id"]) for e in later] == [("object", "updated", item["id"])]
    assert world.value(world.record("V", item["id"]), "V.rank") == 9
    check({"publicationId": publication["id"]})


@pytest.mark.journey("J05.1", "J05")
@pytest.mark.structures("V")
def test_decimals_at_the_smallest_stored_scales_are_captured_and_published(world):
    """Reported 2026-10-04: a live decimal of 1e-16383 read back, but capturing current live and
    publishing an older change set answered 500; a 28-digit decimal near 1e-1000 lost one in its last
    digit in both copies. Given a change set opened before the values; when live records take them,
    another change set captures current live and the first is published; then both read every value
    as live does."""
    cs = world.change_set()
    amounts = ["1e-16383", "-1.000000000000000000000000001e-1000", "1e+1000"]
    items = [world.made("V", f"Amount {n}", values={"V.amount": a}) for n, a in enumerate(amounts)]
    live = [world.value(world.record("V", item["id"]), "V.amount") for item in items]
    captured = world.change_set()
    assert [
        world.value(world.record("V", item["id"], changeSetId=captured["id"]), "V.amount")
        for item in items
    ] == live
    publication = world.publish(cs)
    assert [
        world.value(world.record("V", item["id"], publicationId=publication["id"]), "V.amount")
        for item in items
    ] == live


@pytest.mark.journey("J06.4")
@pytest.mark.structures("R", "R.u")
def test_publishing_an_exchange_of_unique_values(world):
    """Given R1 holding the unique value X and R2 holding Y, and a change set that sets R1 to T, R2
    to X, then R1 to Y. When it is published. Then live reads R1 with Y and R2 with X, and a live
    create with either value is refused."""
    r1 = world.made("R", "Exchange one", values={"R.u": "SWAP-X"})
    r2 = world.made("R", "Exchange two", values={"R.u": "SWAP-Y"})
    cs = world.change_set()
    for record, value in ((r1, "SWAP-T"), (r2, "SWAP-X"), (r1, "SWAP-Y")):
        ok(_update_in(world, cs, "R", record["id"], values={"R.u": value}))
    world.publish(cs)
    assert world.value(world.record("R", r1["id"]), "R.u") == "SWAP-Y"
    assert world.value(world.record("R", r2["id"]), "R.u") == "SWAP-X"
    for value in ("SWAP-X", "SWAP-Y"):
        refused(world.create("R", "Third", values={"R.u": value}), 409, "DUPLICATE_ATTRIBUTE_VALUE")


def _typed_lookup(statement: str) -> bool:
    """A change set's unique check or key reference reading a number or a date."""
    return any(
        f"snapshot_attribute_values.{column} IN" in statement
        for column in ("integer_value", "date_value")
    )


@pytest.mark.journey("J06.5", "J11.2")
@pytest.mark.structures("R", "R.n", "R.dt")
def test_unique_numbers_and_dates_in_a_change_set(world):
    """Given a workspace whose model makes R.n (a number) and R.dt (a date) unique, and two records
    holding values. When a change set takes, frees and upserts by them. Then a create taking a held
    number or date is refused naming its holder; a number its holder gives up is taken by another
    record; a batch upsert keyed by the number finds the base record; live, a held number is still
    refused. Each of the change set's checks seeks its value on its typed index (0.11 Q2, D187).
    Live checks seek C3a's value-order indexes once the statistics hold the values (checked on the
    volume seed); on these small, fresh tables the planner may take the attribute's index."""
    site = _on(world, world.install(numbered(world.configuration), name="Numbered")["id"])
    first = world.made("R", "First", workspace=site, values={"R.n": 7, "R.dt": "2026-01-07"})
    second = world.made("R", "Second", workspace=site, values={"R.n": 8, "R.dt": "2026-01-08"})
    cs = world.change_set(site)

    def create_in(name, **values):
        return world.create("R", name, change_set=world.current(cs), values=values)

    with planned(_typed_lookup) as plans:
        taken = refused(create_in("Copy", **{"R.n": 7}), 409, "DUPLICATE_ATTRIBUTE_VALUE")
        assert taken["details"]["conflictingObjectId"] == first["id"]
        taken = refused(
            create_in("Copy", **{"R.dt": "2026-01-08"}), 409, "DUPLICATE_ATTRIBUTE_VALUE"
        )
        assert taken["details"]["conflictingObjectId"] == second["id"]

        record = world.record("R", first["id"], changeSetId=cs["id"])
        changed = {
            "expectedVersion": record["version"],
            "changeSetId": cs["id"],
            "expectedChangeSetVersion": world.current(cs)["version"],
            "attributes": [{"attributeTypeKey": world.key("R.n"), "value": 9}],
        }
        ok(world.api.patch(f"/objects/{world.key('R')}/{first['id']}", changed))
        third = ok(create_in("Third", **{"R.n": 7}), 201)

        upsert = {
            "op": "upsert",
            "applicationKey": world.app("R"),
            "objectTypeKey": world.key("R"),
            "key": {"attributeTypeKey": world.key("R.n")},
            "name": "Second, upserted",
            "attributes": [
                {"attributeTypeKey": a["attributeTypeKey"], "value": a["value"]}
                for a in second["attributes"]
                if a["attributeTypeKey"] != world.key("R.ro")
            ],
        }
        result = ok(
            _batch(
                world,
                [upsert],
                context={"changeSetId": cs["id"]},
                expectedChangeSetVersion=world.current(cs)["version"],
                onExisting="overwrite",
            )
        )
        assert [item["action"] for item in result["items"]] == ["updated"], result
        assert world.record("R", second["id"], changeSetId=cs["id"])["name"] == "Second, upserted"
        assert world.record("R", third["id"], changeSetId=cs["id"])["name"] == "Third"

    live = refused(
        world.create("R", "Live copy", workspace=site, values={"R.n": 7}),
        409,
        "DUPLICATE_ATTRIBUTE_VALUE",
    )
    assert live["details"]["conflictingObjectId"] == first["id"]
    typed = {
        "ix_snapshot_attribute_values_change_set_key_integer",
        "ix_snapshot_attribute_values_change_set_key_date",
    }
    assert plans
    for plan in plans:
        assert plan_reads(plan) & typed, plan
