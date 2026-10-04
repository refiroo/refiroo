"""J14 — Build and change a hierarchy (USER_JOURNEYS.md)."""

import pytest
from scenario import W1, ok, refused


def _candidates(world, structure, object_id, **params):
    path = f"/objects/{world.key(structure)}/{object_id}/parent-candidates"
    return ok(world.api.get(path, pageSize=100, includeTotal=True, **params))


def _move(world, structure, object_id, parent, **context):
    record = world.record(
        structure, object_id, **{k: v for k, v in context.items() if k == "changeSetId"}
    )
    body = {"parentObjectId": parent, "expectedVersion": record["version"], **context}
    return world.api.patch(f"/objects/{world.key(structure)}/{object_id}", body)


def _ids(path):
    return [part["id"] for part in path]


@pytest.mark.journey("J14")
@pytest.mark.structures("H", "K", "Bnn")
def test_find_a_nested_record_add_a_child_and_move_it(world):
    """Given the H hierarchy. When the integrator pages from the top level down to h4, adds child x
    under it, reads x's parent candidates and moves x into the other branch. Then x's path ends with
    its new parent, its relationship and child come with it, the other records keep their versions;
    a search finds h4 with its path without paging the levels."""
    h4, j2 = world.ids["h4"], world.ids["j2"]
    h_type = world.key("H")
    tops = ok(world.api.get(f"/objects/{h_type}", topLevel=True))["items"]
    assert {item["id"] for item in tops} == {world.ids["h1"], world.ids["j1"]}
    parent = world.ids["h1"]
    for level in range(2, 5):
        children = ok(world.api.get(f"/objects/{h_type}", parentObjectId=parent))["items"]
        parent = next(item["id"] for item in children if item["id"] == world.ids[f"h{level}"])
    assert parent == h4

    x = world.made("H", "Moving child", parent=h4)
    x_child = world.made("H", "Moving grandchild", parent=x["id"])
    relation = ok(world.relate("Bnn", x["id"], world.ids["k05"], {"Bnn.weight": 1}), 201)
    others = {
        key: world.record("H", world.ids[key])["version"]
        for key in ("h1", "h2", "h3", "h4", "h5", "j1", "j2", "j3")
    }
    candidates = _candidates(world, "H", x["id"])["items"]
    assert any(item["id"] == j2 and item["eligible"] for item in candidates)

    moved = ok(_move(world, "H", x["id"], j2))
    assert _ids(moved["path"])[-2:] == [j2, x["id"]]
    assert _ids(world.record("H", x_child["id"])["path"])[-3:] == [j2, x["id"], x_child["id"]]
    links = ok(world.api.get("/relations", objectId=x["id"], relationTypeKey=world.key("Bnn")))
    assert [item["relation"]["id"] for item in links["items"]] == [relation["id"]]
    assert {key: world.record("H", world.ids[key])["version"] for key in others} == others

    found = ok(world.api.get(f"/objects/{h_type}", search="Level 4 north"))["items"]
    assert [item["id"] for item in found] == [h4] and len(found[0]["path"]) == 4


@pytest.mark.journey("J14.1")
@pytest.mark.structures("H")
def test_a_self_hierarchy_moves_at_any_depth(world):
    """Given branch one six levels deep and branch two. When h3, with its descendants, moves under
    branch two's top record. Then every descendant's path starts at branch two's top and is one
    shorter; the top level still holds only the two tops."""
    before = {level: world.record("H", world.ids[f"h{level}"])["path"] for level in range(3, 7)}
    ok(_move(world, "H", world.ids["h3"], world.ids["j1"]))
    for level, path in before.items():
        now = world.record("H", world.ids[f"h{level}"])["path"]
        assert now[0]["id"] == world.ids["j1"] and len(now) == len(path) - 1
    tops = ok(world.api.get(f"/objects/{world.key('H')}", topLevel=True))["items"]
    assert {item["id"] for item in tops} == {world.ids["h1"], world.ids["j1"]}


@pytest.mark.journey("J14.2")
@pytest.mark.structures("P", "Q", "C", "C2", "H")
def test_a_hierarchy_of_mixed_types(world):
    """Given C record c, with a child, under P record p, and Q record q. When c's parent candidates
    are listed, then narrowed to Q; c moves under q; then under a record of a type C cannot stand
    under. Then the candidates hold P and Q records, the narrowed list only Q; the move brings the
    child along; the last move is refused."""
    p, q = world.made("P", "Estate"), world.made("Q", "Venue")
    c = world.made("C", "Room", parent=p["id"])
    child = world.made("C2", "Shelf", parent=c["id"])

    types = {item["objectTypeKey"] for item in _candidates(world, "C", c["id"])["items"]}
    assert {world.key("P"), world.key("Q")} <= types
    narrowed = _candidates(world, "C", c["id"], parentObjectTypeKey=world.key("Q"))["items"]
    assert {item["objectTypeKey"] for item in narrowed} == {world.key("Q")}

    ok(_move(world, "C", c["id"], q["id"]))
    assert _ids(world.record("C2", child["id"])["path"]) == [q["id"], c["id"], child["id"]]
    # A record of a type C cannot stand under, in C's application (see J03.2).
    refused(_move(world, "C", c["id"], world.ids["h1"]), 422, "INVALID_PARENT_TYPE")


@pytest.mark.journey("J14.3")
@pytest.mark.structures("H", "P", "C")
def test_to_the_top_level(world):
    """When H record h3 moves to the top level, and C record c does the same. Then h3 is listed at the
    top with a one-element path; c is refused."""
    moved = ok(_move(world, "H", world.ids["h3"], None))
    assert _ids(moved["path"]) == [world.ids["h3"]]
    tops = ok(world.api.get(f"/objects/{world.key('H')}", topLevel=True))["items"]
    assert world.ids["h3"] in {item["id"] for item in tops}
    c = world.made("C", "Room", parent=world.made("P", "Estate")["id"])
    refused(_move(world, "C", c["id"], None), 422, "PARENT_REQUIRED")


@pytest.mark.journey("J14.4")
@pytest.mark.structures("H")
def test_a_record_cannot_move_into_its_own_subtree(world):
    """Given H record h2 with descendants. When its parent candidates are listed, then it is moved
    under its level-4 descendant. Then the candidates mark the descendant, itself and its current
    parent ineligible with the reason, and the total counts them; the move is refused and nothing
    changes."""
    h2 = world.ids["h2"]
    page = _candidates(world, "H", h2)
    reasons = {item["id"]: (item["eligible"], item["reason"]) for item in page["items"]}
    assert reasons[world.ids["h4"]] == (False, "descendant")
    assert reasons[h2] == (False, "self")
    assert reasons[world.ids["h1"]] == (False, "currentParent")
    assert page["totalCount"] == len(page["items"])

    before = world.record("H", h2)
    refused(_move(world, "H", h2, world.ids["h4"]), 422, "PARENT_CYCLE")
    assert world.record("H", h2) == before


@pytest.mark.journey("J14.5")
@pytest.mark.structures("R", "G", "D", "D.active", "Bown")
def test_a_move_that_changes_a_scope_ancestor(world):
    """Given D records d1 within G g1 and d2 within G g2, both active and both owned by r through the
    scoped relationship. When d2 moves into g1. Then it is refused naming g1 and d1, and d2 stays."""
    r = world.made("R", "Owner")
    g1, g2 = world.made("G", "Scope one"), world.made("G", "Scope two")
    d1, d2 = (
        world.made(
            "D",
            name,
            parent=world.dependant_parent(g["id"]),
            values={"D.active": True},
            relations=[world.owner("Bown", r["id"])],
        )
        for name, g in (("First", g1), ("Second", g2))
    )

    error = refused(
        _move(world, "D", d2["id"], d1["parentObjectId"]), 409, "DUPLICATE_RELATION_SCOPE"
    )
    assert error["details"]["ancestorObjectId"] == g1["id"]
    assert error["details"]["conflictingObjectId"] == d1["id"]
    assert world.record("D", d2["id"])["parentObjectId"] == d2["parentObjectId"]


@pytest.mark.journey("J14.6")
@pytest.mark.structures("H", "K", "Bnn")
def test_a_move_keeps_relationships_across_applications(world):
    """Given subtree h3 whose records relate to K records (h4 to k1, and k records related to h5).
    When h3 moves to the other branch. Then k1 still lists h4 with the same relationship and version,
    and h4's new path."""
    k1 = world.made("K", "Linked token")
    relation = ok(world.relate("Bnn", world.ids["h4"], k1["id"], {"Bnn.weight": 1}), 201)
    ok(_move(world, "H", world.ids["h3"], world.ids["j1"]))

    items = ok(world.api.get("/relations", objectId=k1["id"]))["items"]
    (item,) = [i for i in items if i["relation"]["id"] == relation["id"]]
    assert item["relation"]["version"] == relation["version"]
    assert (
        item["object"]["id"] == world.ids["h4"]
        and item["object"]["path"][0]["id"] == world.ids["j1"]
    )


@pytest.mark.journey("J14.7")
@pytest.mark.structures("H")
def test_move_in_a_change_set(world):
    """Given change set CS1. When h3 moves under j2 in CS1 and j2's parent candidates are read there.
    Then in CS1 the moved records follow; h3 and its descendants are j2's descendants and its former
    ancestors are not; live is unchanged; CS1's changes list h3 as changed with its parent and its
    former path."""
    h3, j2 = world.ids["h3"], world.ids["j2"]
    cs1 = world.change_set()
    ok(
        _move(
            world,
            "H",
            h3,
            j2,
            changeSetId=cs1["id"],
            expectedChangeSetVersion=world.current(cs1)["version"],
        )
    )

    staged = world.record("H", world.ids["h6"], changeSetId=cs1["id"])
    assert _ids(staged["path"])[:3] == [world.ids["j1"], j2, h3]
    reasons = {
        item["id"]: item["reason"]
        for item in _candidates(world, "H", j2, changeSetId=cs1["id"])["items"]
    }
    assert reasons[h3] == "descendant" and reasons[world.ids["h6"]] == "descendant"
    assert reasons[world.ids["h1"]] != "descendant" and reasons[world.ids["h2"]] != "descendant"
    assert world.record("H", h3)["parentObjectId"] == world.ids["h2"]

    changes = ok(world.api.get(f"/change-sets/{cs1['id']}/object-changes", pageSize=100))["items"]
    (entry,) = [item for item in changes if item["objectId"] == h3]
    assert entry["kind"] == "changed" and "parent" in entry["changedFields"]
    assert _ids(entry["beforePath"]) == [world.ids["h1"], world.ids["h2"], h3]


@pytest.mark.journey("J14.8")
@pytest.mark.structures("H")
def test_two_moves_racing_into_a_cycle(world):
    """Given sibling H records a and b; actor A moves a under b while actor B moves b under a, both
    in flight at once. Then one move succeeds and the other is refused; both paths end at a top."""
    a, b = (world.made("H", name, parent=world.ids["h1"]) for name in ("Sibling A", "Sibling B"))
    versions = {a["id"]: a["version"], b["id"]: b["version"]}

    def move(child, parent):
        body = {"parentObjectId": parent, "expectedVersion": versions[child]}
        return world.api.patch(f"/objects/{world.key('H')}/{child}", body)

    responses = world.race(W1, lambda: move(a["id"], b["id"]), lambda: move(b["id"], a["id"]))
    assert sorted(response.status_code for response in responses) == [200, 422]
    refused(next(r for r in responses if r.status_code == 422), 422, "PARENT_CYCLE")
    for record in (a, b):
        path = world.record("H", record["id"])["path"]
        assert path[0]["id"] == world.ids["h1"] and len(path) <= 3
