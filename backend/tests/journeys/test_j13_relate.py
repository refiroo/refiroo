"""J13 — Relate records and maintain their relationships (USER_JOURNEYS.md).

J13.6 is walked with J04.6 (``test_j04_delete.py``): they describe the same request.
"""

from uuid import uuid4

import pytest
from scenario import W1, W2, ok, refused


def _relations(world, object_id, **params):
    return ok(world.api.get("/relations", objectId=object_id, pageSize=100, **params))["items"]


@pytest.mark.journey("J13")
@pytest.mark.structures("H", "K", "Bnn", "Bnn.weight", "Bnn.note")
def test_find_relate_change_and_remove_a_relationship(world):
    """Given H record h and K record k of the other application. When the integrator finds k by name,
    relates h to it with typed values, changes the values with the relationship's version, then
    removes it. Then each step answers the relationship at its next version, and afterwards it is
    not found; a stale version on change or removal is refused."""
    h = world.made("H", "Relating")
    k = world.made("K", "Findable token")
    found = ok(world.api.get("/objects", workspaceKey=W1, search="Findable token"))["items"]
    assert [item["id"] for item in found] == [k["id"]]

    relation = ok(
        world.relate("Bnn", h["id"], k["id"], {"Bnn.weight": 3, "Bnn.note": "first"}), 201
    )
    assert (relation["relationTypeKey"], relation["fromObjectId"], relation["toObjectId"]) == (
        world.key("Bnn"),
        h["id"],
        k["id"],
    )
    assert relation["attributes"][world.key("Bnn.weight")] == 3 and relation["version"] == 1

    path = f"/relations/{relation['id']}"
    stale_change = world.api.patch(
        path, {"attributes": {world.key("Bnn.weight"): 4}, "expectedVersion": 2}
    )
    refused(stale_change, 409, "VERSION_CONFLICT")
    changed = ok(
        world.api.patch(path, {"attributes": {world.key("Bnn.weight"): 4}, "expectedVersion": 1})
    )
    assert changed["version"] == 2 and changed["attributes"][world.key("Bnn.weight")] == 4
    refused(world.api.delete(path, expectedVersion=1), 409, "VERSION_CONFLICT")
    assert world.api.delete(path, expectedVersion=2).status_code == 204
    refused(world.api.get(path), 404, "RELATION_NOT_FOUND")


@pytest.mark.journey("J13.1")
@pytest.mark.structures("H", "K", "Bnn", "R", "B1n")
def test_both_ends_list_each_other_with_their_own_names(world):
    """Given H record h related to K record k, which an R record also relates to. When each end lists
    its relationships sorted by relationship. Then each lists the other end, labelled by the
    relationship type's name from its source and its reverse name from its target, in that order."""
    h4, k = world.ids["h4"], world.made("K", "Two-sided")
    ok(world.relate("Bnn", h4, k["id"], {"Bnn.weight": 1}), 201)
    r = world.made("R", "Also relating")
    ok(world.relate("B1n", r["id"], k["id"]), 201)
    types = {
        item["key"]: item for item in ok(world.api.get("/relation-types", pageSize=100))["items"]
    }

    def labels(items, side):
        return [types[item["relation"]["relationTypeKey"]][side] for item in items]

    outgoing = _relations(world, h4, direction="outgoing", sort="relationship")
    assert k["id"] in {item["object"]["id"] for item in outgoing}
    assert labels(outgoing, "name") == sorted(labels(outgoing, "name"), key=str.casefold)
    incoming = _relations(world, k["id"], direction="incoming", sort="relationship")
    assert {item["object"]["id"] for item in incoming} == {h4, r["id"]}
    assert labels(incoming, "reverseName") == sorted(
        labels(incoming, "reverseName"), key=str.casefold
    )
    one = ok(world.api.get(f"/relation-types/{world.key('Bnn')}"))
    assert (one["name"], one["reverseName"]) == (
        types[world.key("Bnn")]["name"],
        types[world.key("Bnn")]["reverseName"],
    )


@pytest.mark.journey("J13.2")
@pytest.mark.structures("R", "K", "B11", "B1n", "H", "Bnn")
def test_each_cardinality_holds(world):
    """Given R records r1, r2 and K records k1, k2. When one-to-one, one-to-many and many-to-many
    relationships are added between them. Then one-to-one allows one on each end, one-to-many one
    source per target, many-to-many any number."""
    r1, r2 = (world.made("R", f"Ledger {i}")["id"] for i in (1, 2))
    k1, k2 = (world.made("K", f"Paired {i}")["id"] for i in (1, 2))

    ok(world.relate("B11", r1, k1), 201)
    refused(world.relate("B11", r1, k2), 409, "CARDINALITY_VIOLATION")
    refused(world.relate("B11", r2, k1), 409, "CARDINALITY_VIOLATION")
    ok(world.relate("B1n", r1, k1), 201)
    ok(world.relate("B1n", r1, k2), 201)
    refused(world.relate("B1n", r2, k1), 409, "CARDINALITY_VIOLATION")
    h1, h2 = world.ids["j1"], world.ids["j2"]
    for source, target in ((h1, k1), (h1, k2), (h2, k1), (h2, k2)):
        ok(world.relate("Bnn", source, target, {"Bnn.weight": 1}), 201)


@pytest.mark.journey("J13.3")
@pytest.mark.structures("H", "K", "Bnn", "Bnn.weight", "R")
def test_a_relationship_must_fit_its_type(world):
    """When a relationship is created with an undeclared value, a value below its minimum, an unknown
    type, a pair its type does not allow, a missing end, an end in another workspace, or a
    containment type directly. Then each is refused with its code and none is created."""
    h = world.made("H", "Strict")
    k = world.made("K", "Strict token")
    far = world.made("K", "Far token", workspace=W2)
    r = world.made("R", "Wrong source")
    before = len(_relations(world, h["id"]))

    refused(
        world.relate("Bnn", h["id"], k["id"], {"undeclared-value": 1}),
        422,
        "UNKNOWN_RELATION_ATTRIBUTES",
    )
    refused(
        world.relate("Bnn", h["id"], k["id"], {"Bnn.weight": 0}), 422, "ATTRIBUTE_BELOW_MINIMUM"
    )
    unknown = {
        "relationTypeKey": "no-such-relation",
        "fromObjectId": h["id"],
        "toObjectId": k["id"],
    }
    refused(world.api.post("/relations", unknown), 422, "UNKNOWN_RELATION_TYPE")
    refused(world.relate("Bnn", r["id"], k["id"]), 422, "INVALID_RELATION_PAIR")
    refused(world.relate("Bnn", h["id"], str(uuid4())), 422, "RELATION_ENDPOINT_MISSING")
    refused(world.relate("Bnn", h["id"], far["id"]), 422, "RELATION_WRONG_SCOPE")
    refused(world.relate("Hparent", h["id"], world.ids["h1"]), 422, "IMMUTABLE_RELATION")
    assert len(_relations(world, h["id"])) == before


@pytest.mark.journey("J13.4")
@pytest.mark.structures("R", "G", "D", "D.active", "Bown", "Bscope")
def test_scoped_uniqueness_holds_when_the_condition_starts_to_hold(world):
    """Given D records d1 (active) and d2 (inactive) within G record g, r related to d1 by the scoped
    relationship. When r is related to d2, then d2 becomes active. Then the relationship is created
    (the condition does not hold for d2), and the update is refused naming d1; d2 stays inactive."""
    g = world.made("G", "Scope")
    d1, d2 = (
        world.made(
            "D",
            name,
            parent=world.dependant_parent(g["id"]),
            values={"D.active": active},
            relations=[world.owner("Bown", world.made("R", f"Owner of {name}")["id"])],
        )
        for name, active in (("Active one", True), ("Inactive one", False))
    )
    r = world.made("R", "Watcher")
    ok(world.relate("Bscope", r["id"], d1["id"]), 201)

    ok(world.relate("Bscope", r["id"], d2["id"]), 201)
    error = refused(
        world.update("D", d2["id"], d2["version"], values={"D.active": True}),
        409,
        "DUPLICATE_RELATION_SCOPE",
    )
    assert error["details"]["conflictingObjectId"] == d1["id"]
    assert world.value(world.record("D", d2["id"]), "D.active") is False


@pytest.mark.journey("J13.5")
@pytest.mark.structures("H", "K", "Bnn")
def test_a_claimed_write_is_refused_when_the_set_changed(world):
    """Given an integrator who read H record h's relationship set at version s. When another writer
    adds a relationship to h, then the integrator adds one claiming s. Then it is refused with h, the
    direction and the current version, and nothing is created; claiming the current version
    succeeds and advances it by one; naming only half a claim is refused."""
    h = world.made("H", "Claimed set")
    ok(world.relate("Bnn", h["id"], world.ids["k01"], {"Bnn.weight": 1}), 201)
    edges = ok(
        world.api.get(
            f"/workspaces/{W1}/relations",
            relationTypeKey=world.key("Bnn"),
            direction="outgoing",
            search="Claimed set",
        )
    )["items"]
    seen = next(item["mappingVersion"] for item in edges if item["source"]["id"] == h["id"])

    ok(world.relate("Bnn", h["id"], world.ids["k02"], {"Bnn.weight": 1}), 201)
    claim = {"expectedRelationSetVersion": seen, "relationSetDirection": "outgoing"}
    error = refused(
        world.relate("Bnn", h["id"], world.ids["k03"], {"Bnn.weight": 1}, **claim),
        409,
        "RELATION_SET_VERSION_CONFLICT",
    )
    assert error["details"]["anchorObjectId"] == h["id"]
    assert error["details"]["direction"] == "outgoing"
    current = error["details"]["relationSetVersion"]
    assert current == seen + 1
    assert len(_relations(world, h["id"], relationTypeKey=world.key("Bnn"))) == 2

    claimed = ok(
        world.relate(
            "Bnn",
            h["id"],
            world.ids["k03"],
            {"Bnn.weight": 1},
            expectedRelationSetVersion=current,
            relationSetDirection="outgoing",
        ),
        201,
    )
    assert claimed["relationSetVersion"] == current + 1
    refused(
        world.relate(
            "Bnn",
            h["id"],
            world.ids["k04"],
            {"Bnn.weight": 1},
            expectedRelationSetVersion=current + 1,
        ),
        422,
        "RELATION_SET_CLAIM_INCOMPLETE",
    )


@pytest.mark.journey("J13.3")
@pytest.mark.structures("H", "K", "Bnn", "Bnn.weight")
def test_relating_the_same_records_twice_is_refused(world):
    """Given H record h related to K record k. When the same relationship is created again, live and
    in a change set. Then each is refused as a duplicate, and h holds one such relationship in
    each. (Live, this reached the database's unique constraint and answered 500 before 0.9 B3.)"""
    h, k = world.made("H", "Related once"), world.made("K", "Related once token")
    ok(world.relate("Bnn", h["id"], k["id"], {"Bnn.weight": 1}), 201)
    refused(world.relate("Bnn", h["id"], k["id"], {"Bnn.weight": 2}), 409, "DUPLICATE_RELATION")
    cs1 = world.change_set()
    staged = world.relate(
        "Bnn",
        h["id"],
        k["id"],
        {"Bnn.weight": 2},
        changeSetId=cs1["id"],
        expectedChangeSetVersion=world.current(cs1)["version"],
    )
    refused(staged, 409, "DUPLICATE_RELATION")
    for params in ({}, {"changeSetId": cs1["id"]}):
        assert len(_relations(world, h["id"], relationTypeKey=world.key("Bnn"), **params)) == 1


def _set_versions(world, object_id, **params):
    page = ok(world.api.get("/relations", objectId=object_id, pageSize=1, **params))
    return {
        (item["relationTypeKey"], item["direction"]): item["relationSetVersion"]
        for item in page["relationSets"]
    }


@pytest.mark.journey("J13.5")
@pytest.mark.structures("H", "K", "Bnn", "Bh1n")
def test_the_record_s_relationship_list_names_each_set_s_version(world):
    """Given H record h with one relationship of one type and none of another. When the integrator
    lists h's relationships. Then each set h anchors is named with its version, the empty one at 0;
    after the only relationship is removed its set is still named, advanced; a create claiming the
    named version succeeds. In a change set the list names the change set's versions."""
    h = world.made("H", "Anchored set")
    relation = ok(world.relate("Bnn", h["id"], world.ids["k01"], {"Bnn.weight": 1}), 201)
    bnn, bh1n = (world.key("Bnn"), "outgoing"), (world.key("Bh1n"), "outgoing")
    versions = _set_versions(world, h["id"], direction="outgoing")
    assert versions[bnn] >= 1 and versions[bh1n] == 0
    only = _set_versions(world, h["id"], direction="outgoing", relationTypeKey=world.key("Bh1n"))
    assert only == {bh1n: 0}

    path = f"/relations/{relation['id']}"
    assert world.api.delete(path, expectedVersion=1).status_code == 204
    emptied = _set_versions(world, h["id"], direction="outgoing")
    assert emptied[bnn] == versions[bnn] + 1
    claimed = ok(
        world.relate(
            "Bnn",
            h["id"],
            world.ids["k02"],
            {"Bnn.weight": 1},
            expectedRelationSetVersion=emptied[bnn],
            relationSetDirection="outgoing",
        ),
        201,
    )
    assert claimed["relationSetVersion"] == emptied[bnn] + 1

    cs1 = world.change_set()
    staged = _set_versions(world, h["id"], direction="outgoing", changeSetId=cs1["id"])
    assert staged[bnn] == 0
    ok(
        world.relate(
            "Bnn",
            h["id"],
            world.ids["k03"],
            {"Bnn.weight": 1},
            changeSetId=cs1["id"],
            expectedChangeSetVersion=world.current(cs1)["version"],
        ),
        201,
    )
    assert _set_versions(world, h["id"], direction="outgoing", changeSetId=cs1["id"])[bnn] == 1


@pytest.mark.journey("J13.7")
@pytest.mark.structures("H", "K", "Bnn")
def test_relate_in_a_change_set(world):
    """Given change set CS1. When a relationship is created in it. Then CS1 lists it and live does
    not; after publishing live holds it under the same ID."""
    h, k = world.made("H", "Staged link"), world.made("K", "Staged token")
    cs1 = world.change_set()
    relation = ok(
        world.relate(
            "Bnn",
            h["id"],
            k["id"],
            {"Bnn.weight": 1},
            changeSetId=cs1["id"],
            expectedChangeSetVersion=world.current(cs1)["version"],
        ),
        201,
    )

    staged = _relations(world, h["id"], changeSetId=cs1["id"], relationTypeKey=world.key("Bnn"))
    assert [item["relation"]["id"] for item in staged] == [relation["id"]]
    assert _relations(world, h["id"], relationTypeKey=world.key("Bnn")) == []
    world.publish(cs1)
    live = _relations(world, h["id"], relationTypeKey=world.key("Bnn"))
    assert [item["relation"]["id"] for item in live] == [relation["id"]]


@pytest.mark.journey("J13.8")
@pytest.mark.structures("R", "K", "B11")
def test_two_relationships_racing_for_one_cardinality_limit(world):
    """Given actors A and B relating R records r1 and r2 one-to-one to K record k, both in flight at
    once. Then one is created and the other refused; k has one such relationship."""
    r1, r2 = (world.made("R", f"Racer {i}")["id"] for i in (1, 2))
    k = world.made("K", "Contested")["id"]
    responses = world.race(
        W1, *(lambda source=source: world.relate("B11", source, k) for source in (r1, r2))
    )
    assert sorted(response.status_code for response in responses) == [201, 409]
    refused(next(r for r in responses if r.status_code == 409), 409, "CARDINALITY_VIOLATION")
    assert len(_relations(world, k, direction="incoming", relationTypeKey=world.key("B11"))) == 1


def _held(world, ids, **params):
    query = {
        "objectTypeKey": world.key("H"),
        "relationTypeKey": world.key("Bnn"),
        "direction": "outgoing",
        "objectId": ids,
        **params,
    }
    return world.api.get("/relations/held", **query)


@pytest.mark.journey("J32.7")
@pytest.mark.structures("H", "K", "Bnn", "R", "B1n")
def test_what_a_set_of_records_holds_through_a_relationship(world):
    """Given four H records: three related to K a, one of them also to K b, one related to none. When
    the records K the four hold through the many-to-many are read. Then a with 3 and b with 1, in name
    order, paged one at a time by cursor; in a change set that relates the fourth to b, b with 2 there
    and 1 live. An unknown relationship, one H has no binding of and more than 500 records are
    refused."""
    tag = uuid4().hex[:6]
    a = world.made("K", f"{tag} Alpha", values={"K.code": f"{tag}-A"})["id"]
    b = world.made("K", f"{tag} Bravo", values={"K.code": f"{tag}-B"})["id"]
    hs = [world.made("H", f"{tag} H{n}")["id"] for n in range(4)]
    for h in hs[:3]:
        ok(world.relate("Bnn", h, a, {"Bnn.weight": 1}), 201)
    ok(world.relate("Bnn", hs[0], b, {"Bnn.weight": 1}), 201)

    page = ok(_held(world, hs))
    assert [(item["object"]["id"], item["count"]) for item in page["items"]] == [(a, 3), (b, 1)]
    assert page["items"][0]["object"]["name"] == f"{tag} Alpha"
    first = ok(_held(world, hs, pageSize=1))
    second = ok(_held(world, hs, pageSize=1, cursor=first["nextCursor"]))
    assert [item["object"]["id"] for item in first["items"] + second["items"]] == [a, b]
    assert second["nextCursor"] is None

    cs1 = world.change_set()
    ok(
        world.relate(
            "Bnn", hs[3], b, {"Bnn.weight": 1},
            changeSetId=cs1["id"], expectedChangeSetVersion=world.current(cs1)["version"],
        ),
        201,
    )
    staged = ok(_held(world, hs, changeSetId=cs1["id"]))
    assert [(item["object"]["id"], item["count"]) for item in staged["items"]] == [(a, 3), (b, 2)]
    assert [item["count"] for item in ok(_held(world, hs))["items"]] == [3, 1]

    refused(_held(world, hs, relationTypeKey="no-such-relation"), 422, "UNKNOWN_RELATION_TYPE")
    refused(_held(world, hs, relationTypeKey=world.key("B1n")), 422, "INVALID_RELATION_PAIR")
    error = refused(_held(world, [str(uuid4()) for _ in range(501)]), 422, "TOO_MANY_RECORDS")
    assert "500" in error["message"]


def _candidates(world, listed, key, anchor, search, **params):
    """The names the per-type list offers ``anchor`` records through ``key`` (0.9 K7, D173)."""
    page = ok(
        world.api.get(
            f"/objects/{world.key(listed)}",
            candidateFor=key,
            anchorTypeKey=world.key(anchor),
            search=search,
            pageSize=50,
            **params,
        )
    )
    return sorted(item["name"] for item in page["items"])


def _batch(world, items, **body):
    request = {"policy": "independent", "run": "inline", "workspaceKey": W1, "items": items, **body}
    return world.api.client.post("/api/v1/batches", json=request)


def _reserve(world, tag, region):
    """A ``D`` under a new ``G`` named ``region``, held by a new ``R`` (``Bown`` is required)."""
    g = world.made("G", f"{tag} {region}")
    owner = world.made("R", f"{tag} owner of {region}")
    return world.made(
        "D", f"{tag} permit in {region}", parent=world.dependant_parent(g["id"]),
        relations=[world.owner("Bown", owner["id"])],
    ), g


@pytest.mark.journey("J13.9")
@pytest.mark.structures("H", "K", "K.code", "Bcand", "R", "R.b", "G", "M", "D", "Bown", "Banc")
def test_a_relationship_offers_and_takes_only_its_candidates(world):
    """Given a relationship whose K end takes only codes starting "OK", and one whose R end takes only
    flagged records and whose D end only records under a G named "…reserved…". When the integrator
    reads the candidates, live and in a change set where a code changes, and relates records alone,
    in a batch and by replacing a set. Then only matching records are offered and related, the others
    refused with RELATION_CANDIDATE_REFUSED naming the end; a record already held stays when the set
    is replaced or edited in a change set, while one added must match."""
    tag = uuid4().hex[:6]
    bcand = world.key("Bcand")
    h = world.made("H", f"{tag} chooser")
    good = world.made("K", f"{tag} good", values={"K.code": f"OK-{tag}"})
    also = world.made("K", f"{tag} also good", values={"K.code": f"ok-{tag}-2"})
    bad = world.made("K", f"{tag} bad", values={"K.code": f"NO-{tag}"})
    # "startsWith" ignores case, as the list's filter does.
    assert _candidates(world, "K", bcand, "H", tag) == [f"{tag} also good", f"{tag} good"]

    cs = world.change_set(name=f"{tag} recode")
    ok(world.api.patch(
        f"/objects/{world.key('K')}/{bad['id']}",
        {"attributes": [{"attributeTypeKey": world.key("K.code"), "value": f"OK-{tag}-3"}],
         "expectedVersion": bad["version"], "changeSetId": cs["id"],
         "expectedChangeSetVersion": cs["version"]},
    ))
    assert _candidates(world, "K", bcand, "H", tag, changeSetId=cs["id"]) == [
        f"{tag} also good", f"{tag} bad", f"{tag} good"
    ]
    assert _candidates(world, "K", bcand, "H", tag) == [f"{tag} also good", f"{tag} good"]

    error = refused(world.relate("Bcand", h["id"], bad["id"]), 422, "RELATION_CANDIDATE_REFUSED")
    assert (error["details"]["end"], error["details"]["objectId"]) == ("to", bad["id"])
    assert error["details"]["criteria"].endswith("/candidates/to")
    ok(world.relate("Bcand", h["id"], good["id"]), 201)

    def item(op, target):
        return {"op": op, "relationTypeKey": bcand, "from": {"id": h["id"]}, "to": {"id": target}}

    result = ok(_batch(world, [item("ensureRelation", also["id"]), item("ensureRelation", bad["id"])]))
    assert [i["status"] for i in result["items"]] == ["applied", "rejected"]
    assert result["items"][1]["error"]["code"] == "RELATION_CANDIDATE_REFUSED"

    # Records the same batch creates are judged as the batch leaves them.
    def create_k(code):
        record_id = str(uuid4())
        return record_id, {
            "op": "create", "id": record_id, "applicationKey": world.app("K"),
            "objectTypeKey": world.key("K"), "name": f"{tag} new {code}",
            "attributes": [{"attributeTypeKey": world.key("K.code"), "value": f"{code}-{tag}"}],
        }

    new_ok, create_ok = create_k("OK")
    new_no, create_no = create_k("NO")
    result = ok(_batch(world, [create_ok, create_no, item("ensureRelation", new_ok), item("ensureRelation", new_no)]))
    assert [i["status"] for i in result["items"]] == ["applied", "applied", "applied", "rejected"]
    assert result["items"][3]["error"]["code"] == "RELATION_CANDIDATE_REFUSED"

    # good stops matching; replacing the set keeps it, and refuses bad as an addition.
    current = world.record("K", good["id"])
    ok(world.update("K", good["id"], current["version"], values={"K.code": f"NO-{tag}-4"}))
    replace = {
        "op": "replaceRelationSet", "relationTypeKey": bcand, "fromObjectTypeKey": world.key("H"),
        "toObjectTypeKey": world.key("K"), "direction": "outgoing", "anchor": {"id": h["id"]},
    }
    kept = ok(_batch(world, [{**replace, "targets": [{"object": {"id": good["id"]}}]}], onExisting="overwrite"))
    assert kept["items"][0]["status"] == "applied"
    added = ok(_batch(world, [{**replace, "targets": [{"object": {"id": bad["id"]}}]}], onExisting="overwrite"))
    assert added["items"][0]["error"]["code"] == "RELATION_CANDIDATE_REFUSED"
    # An edit of the held record keeps it, live and in a change set alike (an import's update).
    held = world.record("K", good["id"])
    edit = world.change_set(name=f"{tag} rename held")
    ok(world.api.patch(
        f"/objects/{world.key('K')}/{good['id']}",
        {"name": f"{tag} good renamed", "expectedVersion": held["version"], "changeSetId": edit["id"],
         "expectedChangeSetVersion": edit["version"]},
    ))

    # Banc: the R end must be flagged, the D end under a reserved G.
    banc = world.key("Banc")
    plain_r = world.made("R", f"{tag} unflagged", values={"R.b": False})
    flagged = world.made("R", f"{tag} flagged", values={"R.b": True})
    reserved, _g = _reserve(world, tag, "Reserved West")
    open_d, _g2 = _reserve(world, tag, "Open North")
    assert _candidates(world, "D", banc, "R", tag) == [f"{tag} permit in Reserved West"]
    error = refused(world.relate("Banc", plain_r["id"], reserved["id"]), 422, "RELATION_CANDIDATE_REFUSED")
    assert error["details"]["end"] == "from"
    error = refused(world.relate("Banc", flagged["id"], open_d["id"]), 422, "RELATION_CANDIDATE_REFUSED")
    assert error["details"]["end"] == "to"
    ok(world.relate("Banc", flagged["id"], reserved["id"]), 201)
    assert world.api.get(f"/objects/{world.key('D')}", candidateFor=banc).status_code == 422


@pytest.mark.journey("J13.10")
@pytest.mark.structures("R", "R.b", "G", "M", "D", "Bown", "Banc")
def test_a_relationship_outlives_the_criteria_it_was_chosen_by(world):
    """Given a flagged R related to a D under a G named "Reserved …". When a change set renames the G
    so it no longer matches and is published. Then the relationship is kept and the change set
    publishes; the D is no longer offered as a candidate."""
    tag = uuid4().hex[:6]
    banc = world.key("Banc")
    flagged = world.made("R", f"{tag} flagged", values={"R.b": True})
    reserved, g = _reserve(world, tag, "Reserved East")
    relation = ok(world.relate("Banc", flagged["id"], reserved["id"]), 201)
    cs = world.change_set(name=f"{tag} rename")
    ok(world.api.patch(
        f"/objects/{world.key('G')}/{g['id']}",
        {"name": f"{tag} Plain East", "expectedVersion": g["version"], "changeSetId": cs["id"],
         "expectedChangeSetVersion": cs["version"]},
    ))
    world.publish(world.current(cs))
    held = _relations(world, flagged["id"], relationTypeKey=banc, direction="outgoing")
    assert [(item["relation"]["id"], item["object"]["id"]) for item in held] == [
        (relation["id"], reserved["id"])
    ]
    assert _candidates(world, "D", banc, "R", tag) == []
