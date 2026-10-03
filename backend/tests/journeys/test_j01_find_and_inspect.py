"""J01 — Find and inspect a record (USER_JOURNEYS.md).

UI-only part: returning to the exact list state and retrying a failed panel (runners
``wp9-navigation``, ``s5-continuous-lists``, ``wp14-contextual-browser``).
"""

from uuid import uuid4

import pytest
from scenario import W1, W2, ok, refused


@pytest.mark.journey("J01")
@pytest.mark.structures("H", "K", "Bnn")
def test_find_open_and_inspect_a_record_in_its_workspace(world):
    """Given W2 holds an H record at level 5 with relationships in both directions and a history,
    and W1 holds a record with the same name. When the integrator searches W2's list, opens the
    result and reads its relationships and history. Then every answer is W2's record: its path root
    first, both directions of relationships with the related records' paths, history newest first;
    an empty relationship section is an empty list; unknown IDs and types are refused."""
    h5, w2h5 = world.ids["h5"], world.ids["w2h5"]
    token = world.made("K", "Far token", workspace=W2, values={"K.code": "FAR"})
    ok(world.relate("Bnn", w2h5, token["id"], {"Bnn.weight": 2}), 201)
    h_type = world.key("H")

    page = ok(world.api.get(f"/objects/{h_type}", workspaceKey=W2, search="Level 5", sort="name"))
    assert [item["id"] for item in page["items"]] == [w2h5]

    record = world.record("H", w2h5, workspaceKey=W2)
    assert record["workspaceKey"] == W2
    assert [part["id"] for part in record["path"]][-1] == w2h5
    assert len(record["path"]) == 5 and record["path"][0]["id"] == world.ids["w2h1"]

    relations = ok(world.api.get("/relations", objectId=w2h5, direction="both", workspaceKey=W2))
    assert {item["direction"] for item in relations["items"]} == {"incoming", "outgoing"}
    assert all(item["object"]["path"] for item in relations["items"])
    assert h5 not in {item["object"]["id"] for item in relations["items"]}

    history = ok(world.api.get(f"/objects/{h_type}/{w2h5}/history"))["items"]
    occurred = [item["occurredAt"] for item in history]
    assert occurred == sorted(occurred, reverse=True) and len(history) >= 2

    empty = world.api.get(
        "/relations",
        objectId=w2h5,
        direction="incoming",
        relationTypeKey=world.key("Bnn"),
        workspaceKey=W2,
    )
    assert ok(empty)["items"] == []

    refused(world.read("H", str(uuid4()), workspaceKey=W2), 404, "object_not_found")
    refused(world.api.get(f"/objects/unknown-type/{w2h5}"), 404, "unknown_object_type")


@pytest.mark.journey("J01.1")
@pytest.mark.structures("R")
def test_a_record_reads_as_its_change_set_publication_or_live_content(world):
    """Given P1 holds R record r as N0, live renamed it N1 and CS1 renamed it N2. When r is read and
    listed in CS1, in P1 and live. Then the names are N2, N0 and N1; list and identity reads agree;
    the change set and publication carry no timestamps; contexts that cannot combine are refused."""
    r = world.made("R", "Name zero")
    p1 = world.publish(world.change_set(name="First"))
    r = ok(world.update("R", r["id"], r["version"], name="Name one"))
    cs1 = world.change_set(name="Staged")
    staged = world.record("R", r["id"], changeSetId=cs1["id"])
    body = {
        "name": "Name two",
        "expectedVersion": staged["version"],
        "changeSetId": cs1["id"],
        "expectedChangeSetVersion": world.current(cs1)["version"],
    }
    ok(world.api.patch(f"/objects/{world.key('R')}/{r['id']}", body))

    contexts = {
        "Name two": {"changeSetId": cs1["id"]},
        "Name zero": {"publicationId": p1["id"]},
        "Name one": {},
    }
    for name, context in contexts.items():
        record = world.record("R", r["id"], **context)
        assert record["name"] == name
        listed = ok(world.api.get(f"/objects/{world.key('R')}", search=name, **context))["items"]
        assert [item["id"] for item in listed] == [r["id"]]
        if context:
            assert record["createdAt"] is None and record["updatedAt"] is None

    both = world.read("R", r["id"], changeSetId=cs1["id"], publicationId=p1["id"])
    refused(both, 422, "mutually_exclusive_context")
    refused(world.read("R", r["id"], changeSetId=str(uuid4())), 404, "change_set_not_found")
    refused(world.read("R", r["id"], publicationId=str(uuid4())), 404, "publication_not_found")
    mismatch = world.read("R", r["id"], changeSetId=cs1["id"], workspaceKey=W2)
    refused(mismatch, 422, "workspace_context_mismatch")


@pytest.mark.journey("J01.2")
@pytest.mark.structures("R", "R.u")
def test_every_read_stays_in_the_named_workspace(world):
    """Given W1 and W2 each hold an R record named alike with the same unique value. When the
    integrator lists, searches, filters and opens it in W2. Then only W2's record is answered; W1's
    record read in W2 is not found; an unknown workspace is refused, never the default instead."""
    first = world.made("R", "Twin", values={"R.u": "TWIN-1"})
    second = world.made("R", "Twin", workspace=W2, values={"R.u": "TWIN-1"})
    r_type, u = world.key("R"), world.key("R.u")

    for params in ({}, {"search": "Twin"}, {f"filter.{u}.eq": "TWIN-1"}):
        page = ok(world.api.get(f"/objects/{r_type}", workspaceKey=W2, **params))
        assert [item["id"] for item in page["items"]] == [second["id"]]
    assert world.record("R", second["id"], workspaceKey=W2)["workspaceKey"] == W2

    refused(world.read("R", first["id"], workspaceKey=W2), 404, "object_not_found")
    refused(world.api.get(f"/objects/{r_type}", workspaceKey="nowhere"), 404, "workspace_not_found")


@pytest.mark.journey("J01.3")
@pytest.mark.structures("R", "R.n", "R.b", "R.dt", "R.u")
def test_typed_filters_keep_zero_false_and_unset_apart(world):
    """Given R records with n 0, 5 and unset, b false, true and unset, and dates. When listed with
    typed filters. Then 0 and false match as values, unset matches only unset, dates compare as
    dates and text case-insensitively; an operator the type lacks and an unknown sort are refused."""
    rows = {
        "zero": {"R.n": 0, "R.b": False, "R.dt": "2026-03-01", "R.u": "Alpha-Zero"},
        "five": {"R.n": 5, "R.b": True, "R.dt": "2026-05-01", "R.u": "beta-five"},
        "unset": {"R.u": "gamma-unset"},
    }
    ids = {
        name: world.made("R", f"Typed {name}", values=values)["id"] for name, values in rows.items()
    }
    r_type, n, b, dt, u = (world.key(s) for s in ("R", "R.n", "R.b", "R.dt", "R.u"))

    def matching(**params):
        page = ok(world.api.get(f"/objects/{r_type}", search="Typed", **params))
        return {item["id"] for item in page["items"]}

    assert matching(**{f"filter.{n}.eq": 0}) == {ids["zero"]}
    assert matching(**{f"filter.{b}.eq": "false"}) == {ids["zero"]}
    assert matching(**{f"filter.{n}.isUnset": "true"}) == {ids["unset"]}
    assert matching(**{f"filter.{dt}.gte": "2026-04-01"}) == {ids["five"]}
    assert matching(**{f"filter.{u}.contains": "ALPHA"}) == {ids["zero"]}

    error = refused(
        world.api.get(f"/objects/{r_type}", **{f"filter.{b}.gt": 1}), 422, "invalid_filter"
    )
    assert error["details"]["path"].endswith(f"filter.{b}.gt")
    refused(world.api.get(f"/objects/{r_type}", sort="no-such-field"), 422, "invalid_sort")


@pytest.mark.journey("J01.4")
@pytest.mark.structures("R", "H", "K")
def test_one_search_across_types(world):
    """Given records of R, H and K whose names share a text. When the integrator searches every type,
    then two types. Then each answer lists the matches in name order with their type and path; one
    type alone equals that type's own list; an unknown type is refused."""
    for structure, name in (("R", "Zeta ledger"), ("H", "Zeta branch"), ("K", "Zeta token")):
        world.made(structure, name)

    everything = ok(world.api.get("/objects", workspaceKey=W1, search="zeta"))["items"]
    assert [item["name"] for item in everything] == ["Zeta branch", "Zeta ledger", "Zeta token"]
    assert all(item["objectTypeKey"] and item["path"] for item in everything)

    two = world.api.get(
        "/objects", workspaceKey=W1, search="zeta", objectTypeKey=[world.key("H"), world.key("K")]
    )
    assert [item["name"] for item in ok(two)["items"]] == ["Zeta branch", "Zeta token"]

    one = ok(
        world.api.get("/objects", workspaceKey=W1, search="zeta", objectTypeKey=world.key("H"))
    )
    own = ok(world.api.get(f"/objects/{world.key('H')}", search="zeta", sort="name"))
    assert [i["id"] for i in one["items"]] == [i["id"] for i in own["items"]]

    unknown = world.api.get(
        "/objects", workspaceKey=W1, search="zeta", objectTypeKey="unknown-type"
    )
    refused(unknown, 404, "unknown_object_type")


@pytest.mark.journey("J01.5")
@pytest.mark.structures("R", "R.n", "R.dt")
def test_one_value_in_each_context(world):
    """Given R record r with n 7 in P1, 8 live and 9 in CS1. When the value is read through its own
    resource in each context. Then each answers that context's value with its type and the record's
    version; a value r does not store is not found."""
    r = world.made("R", "Valued", values={"R.n": 7})
    p1 = world.publish(world.change_set())
    r = ok(world.update("R", r["id"], r["version"], values={"R.n": 8}))
    cs1 = world.change_set()
    staged = world.record("R", r["id"], changeSetId=cs1["id"])
    body = {
        "attributes": [{"attributeTypeKey": world.key("R.n"), "value": 9}],
        "expectedVersion": staged["version"],
        "changeSetId": cs1["id"],
        "expectedChangeSetVersion": world.current(cs1)["version"],
    }
    ok(world.api.patch(f"/objects/{world.key('R')}/{r['id']}", body))

    path = f"/objects/{world.key('R')}/{r['id']}/attributes/{world.key('R.n')}"
    for value, context in (
        (7, {"publicationId": p1["id"]}),
        (8, {}),
        (9, {"changeSetId": cs1["id"]}),
    ):
        answer = ok(world.api.get(path, **context))
        assert answer["value"] == value and answer["valueType"] == "integer"
        assert answer["objectVersion"] >= 1

    missing = f"/objects/{world.key('R')}/{r['id']}/attributes/{world.key('R.dt')}"
    refused(world.api.get(missing), 404, "attribute_not_found")


@pytest.mark.journey("J01.6")
@pytest.mark.structures("H", "K", "Bnn")
def test_history_newest_first_with_its_relationships(world):
    """Given a record created, updated twice, related to a K record whose relationship attribute then
    changes. When its history is paged two at a time. Then the events are newest first, with what
    changed and no values; a cursor from another record's history is refused."""
    h = world.made("H", "Storied", values={"H.code": "ST"})
    h = ok(world.update("H", h["id"], h["version"], name="Storied once"))
    h = ok(world.update("H", h["id"], h["version"], values={"H.rank": 3}))
    relation = ok(world.relate("Bnn", h["id"], world.ids["k01"], {"Bnn.weight": 1}), 201)
    ok(
        world.api.patch(
            f"/relations/{relation['id']}",
            {"attributes": {world.key("Bnn.weight"): 2}, "expectedVersion": 1},
        )
    )

    events, cursor = [], None
    path = f"/objects/{world.key('H')}/{h['id']}/history"
    while True:
        page = ok(world.api.get(path, pageSize=2, cursor=cursor))
        events += page["items"]
        cursor = page.get("nextCursor")
        if not cursor:
            break
    kinds = [(event["aggregateType"], event["action"]) for event in events]
    assert kinds == [
        ("relation", "updated"),
        ("relation", "created"),
        ("object", "updated"),
        ("object", "updated"),
        ("object", "created"),
    ]
    assert all("value" not in event and "values" not in event for event in events)
    assert world.key("H.rank") in events[2]["attributeTypeKeys"]

    first = ok(world.api.get(path, pageSize=2))
    other = f"/objects/{world.key('H')}/{world.ids['h1']}/history"
    refused(world.api.get(other, pageSize=2, cursor=first["nextCursor"]), 422, "invalid_cursor")


@pytest.mark.journey("J01.7")
@pytest.mark.structures("H", "K", "Bnn", "K.rank")
def test_related_records_of_another_application_searched_and_sorted(world):
    """Given H record h related to 30 K records of the other application. When its relationships are
    searched and sorted by a K attribute and paged. Then the items are the matching K records with
    their path, in that attribute's order with unset values last, and the pages never repeat."""
    h5, rank = world.ids["h5"], world.key("K.rank")
    seen, cursor = [], None
    while True:
        page = ok(
            world.api.get(
                "/relations",
                objectId=h5,
                relationTypeKey=world.key("Bnn"),
                search="Token",
                sort=rank,
                pageSize=7,
                cursor=cursor,
            )
        )
        seen += page["items"]
        cursor = page.get("nextCursor")
        if not cursor:
            break
    records = [item["object"] for item in seen]
    assert len(records) == 30 and len({r["id"] for r in records}) == 30
    assert all(r["applicationKey"] == world.app("K") != world.app("H") for r in records)
    assert all(r["path"] for r in records)
    ranks = [world.value(r, "K.rank") for r in records]
    present = [value for value in ranks if value is not None]
    assert present == sorted(present) and ranks[len(present) :] == [None] * (30 - len(present))
