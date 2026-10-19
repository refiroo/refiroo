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

    refused(world.read("H", str(uuid4()), workspaceKey=W2), 404, "OBJECT_NOT_FOUND")
    refused(world.api.get(f"/objects/unknown-type/{w2h5}"), 404, "UNKNOWN_OBJECT_TYPE")


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
    refused(both, 422, "MUTUALLY_EXCLUSIVE_CONTEXT")
    refused(world.read("R", r["id"], changeSetId=str(uuid4())), 404, "CHANGE_SET_NOT_FOUND")
    refused(world.read("R", r["id"], publicationId=str(uuid4())), 404, "PUBLICATION_NOT_FOUND")
    mismatch = world.read("R", r["id"], changeSetId=cs1["id"], workspaceKey=W2)
    refused(mismatch, 422, "WORKSPACE_CONTEXT_MISMATCH")


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

    refused(world.read("R", first["id"], workspaceKey=W2), 404, "OBJECT_NOT_FOUND")
    refused(world.api.get(f"/objects/{r_type}", workspaceKey="nowhere"), 404, "WORKSPACE_NOT_FOUND")


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
        world.api.get(f"/objects/{r_type}", **{f"filter.{b}.gt": 1}), 422, "INVALID_FILTER"
    )
    assert error["details"]["path"].endswith(f"filter.{b}.gt")
    refused(world.api.get(f"/objects/{r_type}", sort="no-such-field"), 422, "INVALID_SORT")


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
    refused(unknown, 404, "UNKNOWN_OBJECT_TYPE")


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
    refused(world.api.get(missing), 404, "ATTRIBUTE_NOT_FOUND")


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
    refused(world.api.get(other, pageSize=2, cursor=first["nextCursor"]), 422, "INVALID_CURSOR")


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


def _reverse_key(world, structure):
    """The reverse key of a relationship's type, which names it read from its ``to`` end."""
    key = world.key(structure)
    return next(r["reverseKey"] for r in world.configuration.model["relationTypes"] if r["key"] == key)


def _shown(expanded):
    return [item["object"]["fields"]["name"] for item in expanded["items"]]


def _tokens(world, tag, names):
    return {
        name: world.made("K", f"{tag} {name}", values={"K.code": f"{tag}-{name}"})["id"]
        for name in names
    }


@pytest.mark.journey("J01.8")
@pytest.mark.structures("H", "K", "Bnn", "Bn1")
def test_a_list_shows_each_rows_related_records(world):
    """Given H records related to 0, 1 and 4 K records by a many-to-many relationship, one of them
    also holding one K by a many-to-one relationship. When the H list is read with both
    relationships expanded, and the K list with the many-to-many read from its other end. Then each
    row carries, in the request's order, its first 3 related records in name order and how many
    there are; only a row with more continues, on the relationships list; without expand the items
    are as before."""
    tag = uuid4().hex[:6]
    k = _tokens(world, tag, ["Alpha", "Bravo", "Charlie", "Delta"])
    h0, h1, h4 = (world.made("H", f"{tag} H{n}")["id"] for n in (0, 1, 4))
    ok(world.relate("Bnn", h1, k["Bravo"], {"Bnn.weight": 1}), 201)
    for name in ("Delta", "Charlie", "Bravo", "Alpha"):
        ok(world.relate("Bnn", h4, k[name], {"Bnn.weight": 1}), 201)
    ok(world.relate("Bn1", h1, k["Delta"]), 201)
    bnn, bn1 = world.key("Bnn"), world.key("Bn1")

    page = ok(world.api.get(f"/objects/{world.key('H')}", search=tag, expand=[bnn, bn1]))
    rows = {item["id"]: item["expanded"] for item in page["items"]}
    assert set(rows) == {h0, h1, h4}
    for expanded in rows.values():
        assert [(e["relationTypeKey"], e["direction"]) for e in expanded] == [
            (bnn, "outgoing"),
            (bn1, "outgoing"),
        ]
    assert [(e["count"], _shown(e), e["nextCursor"]) for e in rows[h0]] == [(0, [], None)] * 2
    assert [(e["count"], _shown(e)) for e in rows[h1]] == [
        (1, [f"{tag} Bravo"]),
        (1, [f"{tag} Delta"]),
    ]
    many = rows[h4][0]
    assert many["count"] == 4
    assert _shown(many) == [f"{tag} {name}" for name in ("Alpha", "Bravo", "Charlie")]
    assert rows[h1][0]["nextCursor"] is None and many["nextCursor"]
    rest = ok(
        world.api.get(
            "/relations",
            objectId=h4,
            direction="outgoing",
            relationTypeKey=bnn,
            cursor=many["nextCursor"],
        )
    )
    assert [item["object"]["name"] for item in rest["items"]] == [f"{tag} Delta"]

    backwards = ok(
        world.api.get(
            f"/objects/{world.key('K')}", search=tag, expand=_reverse_key(world, "Bnn"), expandLimit=1
        )
    )
    bravo = next(item for item in backwards["items"] if item["id"] == k["Bravo"])
    [served] = bravo["expanded"]
    assert (served["relationTypeKey"], served["direction"], served["count"]) == (bnn, "incoming", 2)
    assert _shown(served) == [f"{tag} H1"] and served["nextCursor"]

    plain = ok(world.api.get(f"/objects/{world.key('H')}", search=tag))
    assert all("expanded" not in item for item in plain["items"])


@pytest.mark.journey("J01.8")
@pytest.mark.structures("H", "K", "Bnn")
def test_a_lists_related_records_follow_its_context(world):
    """Given H record h related to K records a and b. When a change set relates h to c and removes
    a, and live is read, the change set, and a publication taken before. Then each list shows its
    own context's related records."""
    tag = uuid4().hex[:6]
    k = _tokens(world, tag, ["Alpha", "Bravo", "Charlie"])
    h = world.made("H", f"{tag} Holder")["id"]
    first = ok(world.relate("Bnn", h, k["Alpha"], {"Bnn.weight": 1}), 201)
    ok(world.relate("Bnn", h, k["Bravo"], {"Bnn.weight": 1}), 201)
    published = world.publish(world.change_set(name=f"{tag} before"))
    cs1 = world.change_set(name=f"{tag} staged")
    ok(
        world.relate(
            "Bnn",
            h,
            k["Charlie"],
            {"Bnn.weight": 1},
            changeSetId=cs1["id"],
            expectedChangeSetVersion=world.current(cs1)["version"],
        ),
        201,
    )
    ok(
        world.api.delete(
            f"/relations/{first['id']}",
            expectedVersion=first["version"],
            changeSetId=cs1["id"],
            expectedChangeSetVersion=world.current(cs1)["version"],
        ),
        204,
    )
    bnn = world.key("Bnn")

    def shown(**context):
        page = ok(world.api.get(f"/objects/{world.key('H')}", search=tag, expand=bnn, **context))
        [item] = page["items"]
        [expanded] = item["expanded"]
        return expanded["count"], _shown(expanded)

    assert shown() == (2, [f"{tag} Alpha", f"{tag} Bravo"])
    assert shown(changeSetId=cs1["id"]) == (2, [f"{tag} Bravo", f"{tag} Charlie"])
    assert shown(publicationId=published["id"]) == (2, [f"{tag} Alpha", f"{tag} Bravo"])


@pytest.mark.journey("J01.8")
@pytest.mark.structures("H", "K", "Bn1", "Bnn")
def test_a_list_sorts_by_a_single_valued_relationship(world):
    """Given H records each holding one K by a many-to-one relationship, and H records holding none.
    When the H list is sorted by that relationship, ascending and descending, two rows a page, live
    and in a change set. Then the rows follow their K's name, those without one last in both
    directions, every row once across the pages; a many-to-many relationship is refused as a
    sort."""
    tag = uuid4().hex[:6]
    k = _tokens(world, tag, ["Alpha", "Bravo", "Charlie"])
    holders = {}
    for name, token in (("One", "Charlie"), ("Two", "Alpha"), ("Three", "Bravo"), ("Four", None)):
        holders[name] = world.made("H", f"{tag} {name}")["id"]
        if token:
            ok(world.relate("Bn1", holders[name], k[token]), 201)
    world.made("H", f"{tag} Five")
    bn1 = world.key("Bn1")
    cs1 = world.change_set(name=f"{tag} sorted")

    def read(sort, **context):
        items, cursor = [], None
        while True:
            page = ok(
                world.api.get(
                    f"/objects/{world.key('H')}",
                    search=tag,
                    sort=sort,
                    pageSize=2,
                    cursor=cursor,
                    expand=bn1,
                    **context,
                )
            )
            items += page["items"]
            cursor = page.get("nextCursor")
            if not cursor:
                return items

    for context in ({}, {"changeSetId": cs1["id"]}):
        ascending = read(f"related:{bn1}", **context)
        held = [_shown(item["expanded"][0]) for item in ascending]
        assert held[:3] == [[f"{tag} Alpha"], [f"{tag} Bravo"], [f"{tag} Charlie"]]
        assert held[3:] == [[], []] and len({item["id"] for item in ascending}) == 5
        descending = read(f"-related:{bn1}", **context)
        held = [_shown(item["expanded"][0]) for item in descending]
        assert held[:3] == [[f"{tag} Charlie"], [f"{tag} Bravo"], [f"{tag} Alpha"]]
        assert held[3:] == [[], []]

    refused(
        world.api.get(f"/objects/{world.key('H')}", sort=f"related:{world.key('Bnn')}"),
        422,
        "INVALID_SORT",
    )


@pytest.mark.journey("J01.8")
@pytest.mark.structures("H", "K", "K.code", "Bnn", "Bn1", "R", "B1n")
def test_an_expand_the_list_cannot_answer_is_refused(world):
    """When the H list names an unknown key, a relationship H has no binding of, one key twice, or
    an expandLimit past 20, each is refused, naming the parameter. When it names six columns its
    relationships have, the read answers all six: the model bounds them, not a count (D142 revised
    in K6a)."""
    h_list = f"/objects/{world.key('H')}"
    bnn, bn1, code = world.key("Bnn"), world.key("Bn1"), world.key("K.code")
    for expand in (["no-such-relation"], [world.key("B1n")], [bnn, bnn]):
        error = refused(world.api.get(h_list, expand=expand), 422, "INVALID_EXPAND")
        assert error["details"]["parameter"] == "expand"
    assert world.api.get(h_list, expand=bnn, expandLimit=21).status_code == 422
    world.made("H", f"{uuid4().hex[:6]} Six columns")
    six = [bnn, bn1, f"{bnn}.name", f"{bn1}.name", f"{bnn}.{code}", f"{bn1}.{code}"]
    page = ok(world.api.get(h_list, expand=six, pageSize=1))
    assert len(page["items"][0]["expanded"]) == 6


@pytest.mark.journey("J01.9")
@pytest.mark.structures("R", "G", "D", "D.active", "Bown", "Bscope", "K.code")
def test_a_list_shows_a_field_of_each_rows_related_records(world):
    """Given R record r related by the scoped many-to-many relationship to D records under two G
    records, one D inactive. When the R list expands that relationship with the G ancestor's name,
    with G's code attribute and with D's own active flag. Then each entry names its field and each
    record carries its name and that value, typed; the plain key answers as before. An ancestor D
    cannot sit under, an attribute D does not bind, and a sort by such a column are refused."""
    tag = uuid4().hex[:6]
    bscope, g_key, code, active = (world.key(s) for s in ("Bscope", "G", "K.code", "D.active"))
    regions = [
        world.made("G", f"{tag} G{n}", values={"K.code": f"{tag}-G{n}"}) for n in (1, 2)
    ]
    ds = [
        world.made(
            "D",
            f"{tag} D{n}",
            parent=world.dependant_parent(region["id"]),
            values={"D.active": n == 1},
            relations=[world.owner("Bown", world.made("R", f"{tag} Owner {n}")["id"])],
        )
        for n, region in ((1, regions[0]), (2, regions[1]))
    ]
    r = world.made("R", f"{tag} Watcher")
    for d in ds:
        ok(world.relate("Bscope", r["id"], d["id"]), 201)
    fields = [f"ancestor:{g_key}.name", f"ancestor:{g_key}.{code}", active]

    page = ok(
        world.api.get(
            f"/objects/{world.key('R')}",
            search=f"{tag} Watcher",
            expand=[bscope, *(f"{bscope}.{field}" for field in fields)],
        )
    )
    [item] = page["items"]
    plain, *named = item["expanded"]
    assert "field" not in plain and _shown(plain) == [f"{tag} D1", f"{tag} D2"]
    assert [entry["field"] for entry in named] == fields
    values = [[record["object"]["fields"][entry["field"]] for record in entry["items"]] for entry in named]
    assert values == [[f"{tag} G1", f"{tag} G2"], [f"{tag}-G1", f"{tag}-G2"], [True, False]]
    assert all(_shown(entry) == [f"{tag} D1", f"{tag} D2"] for entry in named)

    r_list = f"/objects/{world.key('R')}"
    for field in (f"ancestor:{world.key('K')}.name", world.key("H.code")):
        error = refused(world.api.get(r_list, expand=f"{bscope}.{field}"), 422, "INVALID_EXPAND")
        assert error["details"]["value"] == f"{bscope}.{field}"
    refused(world.api.get(r_list, sort=f"related:{bscope}.ancestor:{g_key}.name"), 422, "INVALID_SORT")


@pytest.mark.journey("J01.9")
@pytest.mark.structures("R", "G", "D", "D.active", "Bown", "Bscope", "K.code")
def test_a_lists_related_fields_read_alike_in_every_context(world):
    """0.11 X6 (D155). Given R record r related by the scoped relationship to D records under two G
    records, published as P1, then live G1's code changed and in CS1 D2 renamed and inactive. When
    the R list expands that relationship with D's name, its active flag and G's name and code, and
    the model query selects them, in CS1, in P1 and live. Then each value is what reading the D
    record and its G ancestor in that context says, in name order, with the count and no cursor."""
    tag = uuid4().hex[:6]
    bscope, g_key, code, active = (world.key(s) for s in ("Bscope", "G", "K.code", "D.active"))
    regions = [world.made("G", f"{tag} G{n}", values={"K.code": f"{tag}-G{n}"}) for n in (1, 2)]
    ds = [
        world.made(
            "D",
            f"{tag} D{n}",
            parent=world.dependant_parent(region["id"]),
            values={"D.active": True},
            relations=[world.owner("Bown", world.made("R", f"{tag} Owner {n}")["id"])],
        )
        for n, region in ((1, regions[0]), (2, regions[1]))
    ]
    r = world.made("R", f"{tag} Watcher")
    for d in ds:
        ok(world.relate("Bscope", r["id"], d["id"]), 201)
    p1 = world.publish(world.change_set(name=f"{tag} first"))
    g1 = world.record("G", regions[0]["id"])
    ok(world.update("G", g1["id"], g1["version"], values={"K.code": f"{tag}-G1 live"}))
    cs1 = world.change_set(name=f"{tag} staged")
    staged = world.record("D", ds[1]["id"], changeSetId=cs1["id"])
    body = {
        "name": f"{tag} A renamed",
        "attributes": [{"attributeTypeKey": active, "value": False}],
        "expectedVersion": staged["version"],
        "changeSetId": cs1["id"],
        "expectedChangeSetVersion": world.current(cs1)["version"],
    }
    ok(world.api.patch(f"/objects/{world.key('D')}/{ds[1]['id']}", body))
    fields = [f"ancestor:{g_key}.name", f"ancestor:{g_key}.{code}", active]

    for context in ({"changeSetId": cs1["id"]}, {"publicationId": p1["id"]}, {}):
        expected = []
        for d in ds:
            record = world.record("D", d["id"], **context)
            g = next(part for part in record["path"] if part["objectTypeKey"] == g_key)
            region = world.record("G", g["id"], **context)
            expected.append(
                (record["name"], [g["name"], world.value(region, "K.code"), world.value(record, "D.active")])
            )
        expected.sort()
        page = ok(
            world.api.get(
                f"/objects/{world.key('R')}",
                search=f"{tag} Watcher",
                expand=[f"{bscope}.{field}" for field in fields],
                **context,
            )
        )
        [item] = page["items"]
        for index, entry in enumerate(item["expanded"]):
            assert entry["count"] == 2 and entry["nextCursor"] is None
            shown = [(e["object"]["fields"]["name"], e["object"]["fields"][entry["field"]]) for e in entry["items"]]
            assert shown == [(name, values[index]) for name, values in expected], context

        query = {
            "objectTypeKey": world.key("R"),
            "where": [{"field": "name", "op": "eq", "value": f"{tag} Watcher"}],
            "select": ["name"],
            "expand": [
                {
                    "relationTypeKey": bscope,
                    "direction": "outgoing",
                    "select": ["name", f"ancestor:{g_key}", active, "parentObjectId"],
                }
            ],
            "context": context,
        }
        [queried] = ok(world.api.post(f"/workspaces/{W1}/queries/objects", query))["items"]
        items = queried["expanded"][0]["items"]
        for entry, (name, values) in zip(items, expected, strict=True):
            record = world.record("D", entry["object"]["id"], **context)
            g = next(part for part in record["path"] if part["objectTypeKey"] == g_key)
            assert entry["object"]["fields"] == {
                "name": name,
                f"ancestor:{g_key}": {"id": g["id"], "name": g["name"]},
                active: values[2],
                "parentObjectId": record["parentObjectId"],
            }
            assert entry["object"]["version"] == record["version"]


def _filtered(world, tag, **params):
    """The ids of the tagged H records the list gives with ``params``, read to the end two at a time."""
    ids, cursor, total = [], None, None
    while True:
        page = ok(
            world.api.get(
                f"/objects/{world.key('H')}",
                search=tag,
                pageSize=2,
                cursor=cursor,
                includeTotal="true" if cursor is None else None,
                **params,
            )
        )
        total = page.get("totalCount", total)
        ids += [item["id"] for item in page["items"]]
        cursor = page.get("nextCursor")
        if not cursor:
            assert total == len(ids) and len(set(ids)) == len(ids)
            return ids


def _related_holders(world):
    tag = uuid4().hex[:6]
    k = _tokens(world, tag, ["Alpha", "Bravo"])
    holders = {name: world.made("H", f"{tag} {name}", values={"H.code": f"{tag}-{name}"})["id"] for name in ("Aonly", "Bonly", "Both", "Neither")}
    for holder, tokens in (("Aonly", ["Alpha"]), ("Bonly", ["Bravo"]), ("Both", ["Alpha", "Bravo"])):
        for token in tokens:
            ok(world.relate("Bnn", holders[holder], k[token], {"Bnn.weight": 1}), 201)
    return tag, k, holders


@pytest.mark.journey("J01.10")
@pytest.mark.structures("H", "K", "Bnn", "H.code")
def test_a_list_filtered_to_records_related_to_any_of_chosen_records(world):
    """Given H records related through the many-to-many to K a, to K b, to both and to neither. When
    the H list is filtered to those related to a, then to a or b, beside a typed filter, read two at a
    time to the end with totals and by position. Then the rows are exactly those, each once."""
    tag, k, holders = _related_holders(world)
    field = f"filter__related:{world.key('Bnn')}__eq"
    assert set(_filtered(world, tag, **{field: k["Alpha"]})) == {holders["Aonly"], holders["Both"]}
    any_of = _filtered(world, tag, **{field: [k["Alpha"], k["Bravo"]]})
    assert set(any_of) == {holders["Aonly"], holders["Bonly"], holders["Both"]}
    code = f"filter__{world.key('H.code')}__eq"
    narrowed = _filtered(world, tag, **{field: [k["Alpha"], k["Bravo"]], code: f"{tag}-Bonly"})
    assert narrowed == [holders["Bonly"]]
    at = ok(
        world.api.get(
            f"/objects/{world.key('H')}", search=tag, pageSize=1, position=2, includeTotal="true",
            **{field: [k["Alpha"], k["Bravo"]]},
        )
    )
    assert at["totalCount"] == 3 and [item["id"] for item in at["items"]] == [any_of[2]]


@pytest.mark.journey("J01.10")
@pytest.mark.structures("H", "K", "Bnn", "H.code")
def test_a_list_filtered_to_records_related_to_none_or_any_in_every_context(world):
    """Given the same records. When the list is filtered to those related to none and to any, live,
    after a relationship is staged in a change set for the record related to neither, and in a
    publication taken before. Then live and the publication give the record without one; the change
    set gives none, and its record among those with any."""
    tag, k, holders = _related_holders(world)
    none, some = (f"filter__related:{world.key('Bnn')}__isNull", "true"), (f"filter__related:{world.key('Bnn')}__isNull", "false")
    published = world.publish(world.change_set(name=f"{tag} before"))
    cs1 = world.change_set(name=f"{tag} staged")
    ok(
        world.relate(
            "Bnn", holders["Neither"], k["Alpha"], {"Bnn.weight": 1},
            changeSetId=cs1["id"], expectedChangeSetVersion=world.current(cs1)["version"],
        ),
        201,
    )
    three = {holders["Aonly"], holders["Bonly"], holders["Both"]}
    assert _filtered(world, tag, **{none[0]: none[1]}) == [holders["Neither"]]
    assert set(_filtered(world, tag, **{some[0]: some[1]})) == three
    assert _filtered(world, tag, changeSetId=cs1["id"], **{none[0]: none[1]}) == []
    assert set(_filtered(world, tag, changeSetId=cs1["id"], **{some[0]: some[1]})) == three | {holders["Neither"]}
    assert _filtered(world, tag, publicationId=published["id"], **{none[0]: none[1]}) == [holders["Neither"]]


@pytest.mark.journey("J01.10")
@pytest.mark.structures("H", "K", "Bnn", "R", "B1n")
def test_a_relationship_filter_the_list_cannot_answer_is_refused(world):
    """When the H list names an unknown relationship, one H has no binding of, the contains operator
    or a field of the related records in a relationship filter. Then each is refused INVALID_FILTER."""
    h_list = f"/objects/{world.key('H')}"
    bnn = world.key("Bnn")
    for name, value in (
        ("filter.related:no-such.eq", "x"),
        (f"filter.related:{world.key('B1n')}.eq", "x"),
        (f"filter.related:{bnn}.contains", "x"),
        (f"filter.related:{bnn}.name.eq", "x"),
        (f"filter.related:{bnn}.isNull", "maybe"),
    ):
        refused(world.api.get(h_list, **{name.replace(".", "__"): value}), 422, "INVALID_FILTER")


@pytest.mark.journey("J01.3")
@pytest.mark.structures("H", "K.code")
def test_a_filter_or_sort_on_a_field_the_type_lacks_is_refused_in_upper_case(world):
    """Found in 0.9 K6: a filter or sort naming an attribute the type does not bind answered
    `invalid_filter` and `invalid_sort` in lower case, against T1b's one pattern. When the H list is
    filtered and sorted by K's code. Then each is refused INVALID_FILTER and INVALID_SORT."""
    h_list = f"/objects/{world.key('H')}"
    code = world.key("K.code")
    refused(world.api.get(h_list, **{f"filter__{code}__eq": "x"}), 422, "INVALID_FILTER")
    refused(world.api.get(h_list, sort=code), 422, "INVALID_SORT")


@pytest.mark.journey("J01.11")
@pytest.mark.structures("R", "G", "M", "D", "Bown", "K.code")
def test_a_query_keeps_the_records_under_an_ancestor_with_a_field(world):
    """Given D records under a G named "… Reserved …" coded RES and under a G named "… Open …", in B
    two levels down. When the model-aware query asks for the D records under a G whose name contains
    "reserved", whose code is RES, and both, live and in a change set that renames the open G. Then
    each answers the records under the matching G only, and the change set's rename counts there."""
    tag = uuid4().hex[:6]
    g_key, code = world.key("G"), world.key("K.code")

    def permit(region, region_code):
        g = world.made("G", f"{tag} {region}", values={"K.code": region_code})
        owner = world.made("R", f"{tag} owner in {region}")
        world.made(
            "D", f"{tag} permit in {region}", parent=world.dependant_parent(g["id"]),
            relations=[world.owner("Bown", owner["id"])],
        )
        return g

    permit("Reserved Hill", f"RES-{tag}")
    open_g = permit("Open Vale", f"OPN-{tag}")
    named = {"field": "name", "op": "contains", "value": tag}

    def query(where, **context):
        body = {"objectTypeKey": world.key("D"), "where": [named, *where]}
        if context:
            body["context"] = context
        page = ok(world.api.post(f"/workspaces/{W1}/queries/objects", body))
        return sorted(item["fields"]["name"] if "fields" in item else item["name"] for item in page["items"])

    by_name = {"field": f"ancestor:{g_key}.name", "op": "contains", "value": "reserved"}
    by_code = {"field": f"ancestor:{g_key}.{code}", "op": "eq", "value": f"RES-{tag}"}
    reserved = [f"{tag} permit in Reserved Hill"]
    assert query([by_name]) == reserved
    assert query([by_code]) == reserved
    assert query([by_name, by_code]) == reserved
    cs = world.change_set(name=f"{tag} reserve the vale")
    ok(world.api.patch(
        f"/objects/{g_key}/{open_g['id']}",
        {"name": f"{tag} Reserved Vale", "expectedVersion": open_g["version"], "changeSetId": cs["id"],
         "expectedChangeSetVersion": cs["version"]},
    ))
    assert query([by_name], changeSetId=cs["id"]) == [f"{tag} permit in Open Vale", *reserved]
    error = refused(
        world.api.post(
            f"/workspaces/{W1}/queries/objects",
            {"objectTypeKey": world.key("D"), "where": [{**by_name, "field": "ancestor:no-such.name"}]},
        ),
        422,
        "INVALID_QUERY",
    )
    assert error["details"]["path"] == "/where/0/field"
