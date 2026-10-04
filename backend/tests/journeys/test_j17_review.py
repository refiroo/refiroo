"""J17 — Review what a change set changes (USER_JOURNEYS.md)."""

import threading

import pytest
from scenario import W1, ok, refused


def _claim(world, cs):
    return {"changeSetId": cs["id"], "expectedChangeSetVersion": world.current(cs)["version"]}


def _patch(world, cs, structure, object_id, **body):
    staged = world.record(structure, object_id, changeSetId=cs["id"])
    return ok(
        world.api.patch(
            f"/objects/{world.key(structure)}/{object_id}",
            {"expectedVersion": staged["version"], **_claim(world, cs), **body},
        )
    )


def _delete(world, cs, structure, object_id):
    """Delete in the change set, confirming the impact when the record has relationships (J04)."""
    staged = world.record(structure, object_id, changeSetId=cs["id"])
    path = f"/objects/{world.key(structure)}/{object_id}"
    response = world.api.delete(path, expectedVersion=staged["version"], **_claim(world, cs))
    if response.status_code == 409:
        token = refused(response, 409, "OBJECT_HAS_DEPENDANTS")["details"]["deletionPreviewToken"]
        response = world.api.delete(
            path,
            expectedVersion=staged["version"],
            cascade=True,
            deletionPreviewToken=token,
            **_claim(world, cs),
        )
    assert response.status_code == 204, response.text


def _all(world, path, **params):
    items, cursor = [], None
    while True:
        page = ok(world.api.get(path, cursor=cursor, **params))
        items += page["items"]
        cursor = page.get("nextCursor")
        if not cursor:
            return items


@pytest.mark.journey("J17")
@pytest.mark.structures("H", "R", "K", "B1n")
def test_list_what_a_change_set_changes_with_before_and_after(world):
    """Given a change set from current live that added, changed, removed and moved records, added and
    removed relationships, and created and deleted one record inside it. When its object and
    relationship changes are listed, filtered and paged. Then each touched record appears once with
    its kind, sides, changed fields and path; the move is a change of parent with its former path and
    one removed and one added containment edge; the record created and deleted inside is absent; after
    publishing, live matches every entry's after side. An unknown change set, an unknown type and a
    cursor reused with another filter are refused."""
    changed, removed = world.made("R", "Changed ledger"), world.made("R", "Removed ledger")
    linked = world.made("K", "Linked token")
    old_link = ok(world.relate("B1n", removed["id"], world.made("K", "Unlinked token")["id"]), 201)
    cs = world.change_set()
    added = world.made("R", "Added ledger", change_set=world.current(cs))
    _patch(world, cs, "R", changed["id"], name="Changed, staged")
    _delete(world, cs, "R", removed["id"])
    _patch(world, cs, "H", world.ids["h3"], parentObjectId=world.ids["j1"])
    ok(world.relate("B1n", changed["id"], linked["id"], **_claim(world, cs)), 201)
    passing = world.made("R", "Passing ledger", change_set=world.current(cs))
    _delete(world, cs, "R", passing["id"])

    base = f"/change-sets/{cs['id']}"
    objects = _all(world, f"{base}/object-changes", pageSize=2)
    by_id = {entry["objectId"]: entry for entry in objects}
    assert len(by_id) == len(objects) and passing["id"] not in by_id
    assert by_id[added["id"]]["kind"] == "added" and by_id[added["id"]]["before"] is None
    assert (
        by_id[changed["id"]]["kind"] == "changed"
        and "name" in by_id[changed["id"]]["changedFields"]
    )
    assert by_id[removed["id"]]["kind"] == "removed" and by_id[removed["id"]]["after"] is None
    moved = by_id[world.ids["h3"]]
    assert moved["kind"] == "changed" and "parent" in moved["changedFields"]
    assert [p["id"] for p in moved["beforePath"]][-2:] == [world.ids["h2"], world.ids["h3"]]
    assert all(entry["path"] for entry in objects if entry["kind"] != "removed")

    only_changed = _all(world, f"{base}/object-changes", kind="changed")
    assert {e["kind"] for e in only_changed} == {"changed"}
    only_h = _all(world, f"{base}/object-changes", objectTypeKey=world.key("H"))
    assert {e["objectId"] for e in only_h} == {world.ids["h3"]}
    containment = _all(world, f"{base}/relation-changes", containment="true")
    moves = [e for e in containment if world.ids["h3"] in (e["toObject"]["objectId"],)]
    assert sorted(e["kind"] for e in moves) == ["added", "removed"]
    others = _all(world, f"{base}/relation-changes", containment="false")
    assert {e["relationId"] for e in others if e["kind"] == "removed"} >= {old_link["id"]}
    assert any(
        e["kind"] == "added" and e["fromObject"]["objectId"] == changed["id"] for e in others
    )

    first = ok(world.api.get(f"{base}/object-changes", pageSize=1))
    refused(
        world.api.get(
            f"{base}/object-changes", pageSize=1, kind="added", cursor=first["nextCursor"]
        ),
        422,
        "INVALID_CURSOR",
    )
    refused(
        world.api.get(f"{base}/object-changes", objectTypeKey="no-such-type"),
        422,
        "UNKNOWN_OBJECT_TYPE",
    )
    refused(
        world.api.get("/change-sets/00000000-0000-4000-8000-000000000000/object-changes"),
        404,
        "CHANGE_SET_NOT_FOUND",
    )

    world.publish(cs)
    for entry in objects:
        structure = next(s for s in ("R", "H") if world.key(s) == entry["objectTypeKey"])
        if entry["kind"] == "removed":
            refused(world.read(structure, entry["objectId"]), 404, "OBJECT_NOT_FOUND")
            continue
        live = world.record(structure, entry["objectId"])
        assert (live["name"], live["parentObjectId"]) == (
            entry["after"]["name"],
            entry["after"]["parentObjectId"],
        )


@pytest.mark.journey("J17.1")
@pytest.mark.structures("R")
def test_a_change_set_from_a_publication_compares_with_it(world):
    """Given P1 holding x as N0, live renaming it N1, and a change set from P1 renaming it N2. When
    the object changes are read. Then x changed from N0 (P1, not live) to N2."""
    x = world.made("R", "Name zero")
    p1 = world.publish(world.change_set())
    ok(world.update("R", x["id"], x["version"], name="Name one"))
    cs = world.change_set(source="publication", derivedFromPublicationId=p1["id"])
    _patch(world, cs, "R", x["id"], name="Name two")
    (entry,) = [
        e
        for e in _all(world, f"/change-sets/{cs['id']}/object-changes")
        if e["objectId"] == x["id"]
    ]
    assert (entry["kind"], entry["before"]["name"], entry["after"]["name"]) == (
        "changed",
        "Name zero",
        "Name two",
    )


@pytest.mark.journey("J17.2")
@pytest.mark.structures("R", "K", "B1n")
def test_an_empty_root_change_set_lists_only_additions(world):
    """When records and relationships are created in an empty change set and its changes are read.
    Then every entry is an addition with no before side."""
    cs = ok(world.api.post(f"/workspaces/{W1}/change-sets", {}), 201)
    r = world.made("R", "Root ledger", change_set=world.current(cs))
    k = world.made("K", "Root token", change_set=world.current(cs))
    ok(world.relate("B1n", r["id"], k["id"], **_claim(world, cs)), 201)
    entries = _all(world, f"/change-sets/{cs['id']}/object-changes") + _all(
        world, f"/change-sets/{cs['id']}/relation-changes"
    )
    assert entries and {e["kind"] for e in entries} == {"added"}
    assert all(e["before"] is None for e in entries)


@pytest.mark.journey("J17.3")
@pytest.mark.structures("H")
def test_a_page_and_its_paths_agree_while_a_write_commits(world):
    """Given actor A reading object-change pages whose paths pass through h2 while actor B renames h2
    in the change set again and again. Then on every page every path shows one name for h2: the page
    and its paths are one snapshot. (The reads and writes overlap in time; the test cannot pin one
    read to one write without engine hooks.)"""
    cs = world.change_set()
    for level in range(3, 7):
        _patch(world, cs, "H", world.ids[f"h{level}"], name=f"Staged level {level}")
    h2 = world.ids["h2"]
    done, pages = threading.Event(), []

    def rename():
        for index in range(8):
            _patch(world, cs, "H", h2, name=f"Level 2, take {index}")
        done.set()

    writer = threading.Thread(target=rename)
    writer.start()
    while not done.is_set() or len(pages) < 3:
        pages.append(
            ok(
                world.api.get(
                    f"/change-sets/{cs['id']}/object-changes",
                    objectTypeKey=world.key("H"),
                    pageSize=10,
                )
            )
        )
    writer.join(timeout=30)
    for page in pages:
        names = {
            part["name"] for entry in page["items"] for part in entry["path"] if part["id"] == h2
        }
        assert len(names) == 1, names
