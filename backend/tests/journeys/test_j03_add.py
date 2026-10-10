"""J03 — Add a record where it belongs (USER_JOURNEYS.md)."""

from uuid import uuid4

import pytest
from scenario import W1, W2, W3, ok, refused


def _count(world, structure, **params):
    page = world.api.get(
        f"/objects/{world.key(structure)}", includeTotal=True, pageSize=1, **params
    )
    return ok(page)["totalCount"]


@pytest.mark.journey("J03")
@pytest.mark.structures("R", "G", "D", "Bown")
def test_add_a_dependant_with_its_parent_and_owner_in_one_request(world):
    """Given live R record r and G record g. When a D record is created under g with typed values and
    its owning relationship from r. Then it answers with its ID, values and parent; r's relationships
    list it; its path runs through g; its history holds its creation. Without a workspace, with an
    unknown one or in a retired one the same request is refused and creates nothing."""
    r = world.made("R", "Owner")
    g = world.made("G", "Scope")
    parent = world.dependant_parent(g["id"])

    d = world.made(
        "D",
        "Dependant",
        parent=parent,
        values={"D.active": True},
        relations=[world.owner("Bown", r["id"])],
    )
    assert d["parentObjectId"] == parent and world.value(d, "D.active") is True
    related = ok(world.api.get("/relations", objectId=r["id"], relationTypeKey=world.key("Bown")))
    assert [item["object"]["id"] for item in related["items"]] == [d["id"]]
    assert g["id"] in [part["id"] for part in d["path"]] and d["path"][-1]["id"] == d["id"]
    history = ok(world.api.get(f"/objects/{world.key('D')}/{d['id']}/history"))["items"]
    own = [(e["aggregateType"], e["action"]) for e in history if e["aggregateId"] == d["id"]]
    assert own == [("object", "created")]

    before = _count(world, "D")
    request = {"parent": parent, "relations": [world.owner("Bown", r["id"])]}
    refused(
        world.create("D", "No workspace", workspace=None, **request), 422, "WORKSPACE_KEY_REQUIRED"
    )
    refused(
        world.create("D", "Unknown", workspace="nowhere", **request), 404, "WORKSPACE_NOT_FOUND"
    )
    refused(world.create("D", "Retired", workspace=W3, **request), 409, "WORKSPACE_RETIRED")
    assert _count(world, "D") == before


@pytest.mark.journey("J03.1")
@pytest.mark.structures("R", "P", "C")
def test_only_a_root_type_stands_at_the_top(world):
    """Given R may stand at the top and C may not. When one of each is created with no parent. Then
    the R record is created and listed at the top level; the C record is refused and none is added."""
    r = world.made("R", "At the top")
    top = ok(world.api.get(f"/objects/{world.key('R')}", topLevel=True, search="At the top"))
    assert [item["id"] for item in top["items"]] == [r["id"]]

    before = _count(world, "C")
    refused(world.create("C", "Nowhere"), 422, "PARENT_REQUIRED")
    assert _count(world, "C") == before


@pytest.mark.journey("J03.2")
@pytest.mark.structures("H", "P", "C")
def test_a_contained_record_goes_only_where_its_type_may_stand(world):
    """Given H record h6 at level 6, P record p, W2's P record p2 and a record of a type C cannot
    stand under. When H is created under h6, C under p, C under that record and C under p2 in W1. Then the first two are created (the H record
    seven levels deep); a parent of the wrong type and one of another workspace are refused."""
    p = world.made("P", "Estate")
    p2 = world.made("P", "Other estate", workspace=W2)

    deep = world.made("H", "Level 7 north", parent=world.ids["h6"])
    assert len(deep["path"]) == 7
    assert world.made("C", "Room", parent=p["id"])["parentObjectId"] == p["id"]
    before = _count(world, "C")
    # A parent of the wrong type in the same application; one in the other application is first
    # refused for its scope (API.md, "Parent").
    refused(world.create("C", "Wrong parent", parent=world.ids["h1"]), 422, "INVALID_PARENT_TYPE")
    refused(world.create("C", "Other workspace", parent=p2["id"]), 422, "PARENT_WRONG_SCOPE")
    assert _count(world, "C") == before


@pytest.mark.journey("J03.3")
@pytest.mark.structures("R", "G", "D", "Bown")
def test_a_dependant_needs_its_owner_from_the_other_application(world):
    """Given R record r of one application and G record g of the other. When D is created under g
    without its owner, then with it. Then the first is refused and nothing exists; the second is
    created, and r's relationships show the record of the other application."""
    r = world.made("R", "Owner")
    parent = world.dependant_parent(world.made("G", "Scope")["id"])

    refused(world.create("D", "Orphan", parent=parent), 422, "MISSING_REQUIRED_RELATIONS")
    assert ok(world.api.get(f"/objects/{world.key('D')}", search="Orphan"))["items"] == []
    d = world.made("D", "Owned", parent=parent, relations=[world.owner("Bown", r["id"])])
    related = ok(world.api.get("/relations", objectId=r["id"]))["items"]
    other = [item["object"] for item in related if item["object"]["id"] == d["id"]]
    assert other and other[0]["applicationKey"] == world.app("D") != world.app("R")


@pytest.mark.journey("J03.4")
@pytest.mark.structures("H", "K", "Bnn", "Bnn.weight", "Bnn.note")
def test_relationships_given_at_creation_keep_their_typed_attributes(world):
    """Given K records k1 and k2. When an H record is created related to both, one relationship
    carrying an integer and a text. Then both relationships exist with the integer stored as a
    number; naming one relationship twice, or an integer below its minimum, is refused and creates
    nothing."""
    k1, k2 = world.ids["k03"], world.ids["k04"]
    weight, note = world.key("Bnn.weight"), world.key("Bnn.note")

    def related(target, values=None):
        return {
            "relationTypeKey": world.key("Bnn"),
            "direction": "outgoing",
            "otherObjectId": target,
            "attributes": values or {},
        }

    h = world.made("H", "Typed links", relations=[related(k1, {weight: 5, note: "t"}), related(k2)])
    items = ok(world.api.get("/relations", objectId=h["id"], relationTypeKey=world.key("Bnn")))[
        "items"
    ]
    by_target = {item["object"]["id"]: item["relation"]["attributes"] for item in items}
    assert set(by_target) == {k1, k2}
    assert by_target[k1][weight] == 5 and isinstance(by_target[k1][weight], int)
    assert by_target[k1][note] == "t"

    twice = world.create("H", "Twice", relations=[related(k1), related(k1)])
    refused(twice, 422, "DUPLICATE_INITIAL_RELATION")
    refused(
        world.create("H", "Too light", relations=[related(k1, {weight: 0})]),
        422,
        "ATTRIBUTE_BELOW_MINIMUM",
    )
    assert ok(world.api.get(f"/objects/{world.key('H')}", search="Twice"))["items"] == []
    assert ok(world.api.get(f"/objects/{world.key('H')}", search="Too light"))["items"] == []


@pytest.mark.journey("J03.5")
@pytest.mark.structures("R", "G", "D", "D.active", "Bown")
def test_scoped_uniqueness_at_creation(world):
    """Given active D record d1 within G record g, owned by r. When a second active D within g is
    created owned by r. Then it is refused naming g, d1 and d1's relationship, and nothing is
    created; once d1 is inactive the same create succeeds."""
    r = world.made("R", "Owner")
    g = world.made("G", "Scope")
    owned = [world.owner("Bown", r["id"])]
    d1 = world.made(
        "D",
        "First",
        parent=world.dependant_parent(g["id"]),
        values={"D.active": True},
        relations=owned,
    )
    first_relation = ok(
        world.api.get("/relations", objectId=d1["id"], relationTypeKey=world.key("Bown"))
    )["items"][0]["relation"]
    second_parent = world.dependant_parent(g["id"])

    error = refused(
        world.create(
            "D", "Second", parent=second_parent, values={"D.active": True}, relations=owned
        ),
        409,
        "DUPLICATE_RELATION_SCOPE",
    )
    assert error["details"]["ancestorObjectId"] == g["id"]
    assert error["details"]["conflictingObjectId"] == d1["id"]
    assert error["details"]["conflictingRelationId"] == first_relation["id"]
    assert ok(world.api.get(f"/objects/{world.key('D')}", search="Second"))["items"] == []

    ok(world.update("D", d1["id"], d1["version"], values={"D.active": False}))
    world.made("D", "Second", parent=second_parent, values={"D.active": True}, relations=owned)


@pytest.mark.journey("J03.6")
@pytest.mark.structures("R")
def test_a_record_created_with_a_supplied_id(world):
    """When an R record is created with a supplied ID, then again with the same ID. Then the first
    reads back under that ID and the second is refused."""
    supplied = str(uuid4())
    assert world.made("R", "Supplied", id=supplied)["id"] == supplied
    assert world.record("R", supplied)["name"] == "Supplied"
    refused(world.create("R", "Again", id=supplied), 409, "OBJECT_ALREADY_EXISTS")


@pytest.mark.journey("J03.7")
@pytest.mark.structures("R", "D")
def test_add_a_record_in_a_change_set(world):
    """Given change set CS1 at version v. When an R record is created in it. Then it answers the change
    set's next version, the change set holds it, live does not until CS1 is published, then under the
    same ID. A stale change set version, a type outside the application and an unknown application
    are refused."""
    cs1 = world.change_set()
    r = world.made("R", "Staged", change_set=cs1)
    assert r["changeSetVersion"] == cs1["version"] + 1
    assert world.record("R", r["id"], changeSetId=cs1["id"])["name"] == "Staged"
    refused(world.read("R", r["id"]), 404, "OBJECT_NOT_FOUND")

    stale = world.create("R", "Stale", change_set=cs1)
    refused(stale, 409, "CHANGE_SET_VERSION_CONFLICT")
    current = world.current(cs1)
    outside = {"applicationKey": world.app("R"), "objectTypeKey": world.key("D"), "name": "Outside"}
    refused(
        world.api.post(
            "/objects",
            {**outside, "changeSetId": cs1["id"], "expectedChangeSetVersion": current["version"]},
        ),
        422,
        "OBJECT_TYPE_NOT_IN_APPLICATION",
    )
    refused(
        world.api.post("/objects", {**outside, "workspaceKey": W1}),
        422,
        "INVALID_OBJECT_TYPE_FOR_APPLICATION",
    )
    unknown = {
        **outside,
        "applicationKey": "no-such-application",
        "objectTypeKey": world.key("R"),
        "workspaceKey": W1,
    }
    refused(world.api.post("/objects", unknown), 404, "UNKNOWN_APPLICATION")

    world.publish(cs1)
    assert world.record("R", r["id"])["name"] == "Staged"


@pytest.mark.journey("J03.8")
@pytest.mark.structures("R", "R.u")
def test_two_creates_racing_for_one_unique_value(world):
    """Given actors A and B each creating an R record with the same unique value, both in flight at
    once. Then exactly one is created and the other is refused; one record carries the value."""
    responses = world.race(
        W1,
        *(
            lambda name=name: world.create("R", name, values={"R.u": "RACE"})
            for name in ("Racer A", "Racer B")
        ),
    )
    statuses = sorted(response.status_code for response in responses)
    assert statuses == [201, 409]
    refused(next(r for r in responses if r.status_code == 409), 409, "DUPLICATE_ATTRIBUTE_VALUE")
    u = world.key("R.u")
    page = ok(world.api.get(f"/objects/{world.key('R')}", **{f"filter.{u}.eq": "RACE"}))
    assert len(page["items"]) == 1


@pytest.mark.journey("J03.9")
@pytest.mark.structures("H", "K", "K.code", "Bcand")
def test_an_initial_relationship_must_be_a_candidate(world):
    """Given K records coded "OK…" and "NO…", and a relationship whose K end takes only codes
    starting "OK". When an H record is created related to each. Then the one related to the "NO" K
    is refused with RELATION_CANDIDATE_REFUSED and not created; the other is."""
    tag = uuid4().hex[:6]
    good = world.made("K", f"{tag} good", values={"K.code": f"OK-{tag}"})
    bad = world.made("K", f"{tag} bad", values={"K.code": f"NO-{tag}"})

    def initial(target):
        return [{"relationTypeKey": world.key("Bcand"), "direction": "outgoing", "otherObjectId": target}]

    error = refused(
        world.create("H", f"{tag} refused", relations=initial(bad["id"])), 422, "RELATION_CANDIDATE_REFUSED"
    )
    assert error["details"]["objectId"] == bad["id"]
    page = ok(world.api.get(f"/objects/{world.key('H')}", search=f"{tag} refused"))
    assert page["items"] == []
    world.made("H", f"{tag} created", relations=initial(good["id"]))
