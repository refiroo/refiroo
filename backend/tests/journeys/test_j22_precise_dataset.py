"""J22 — Request the precise dataset an integration needs (USER_JOURNEYS.md).

The seed's 250 V records stand under five tops (``v_top0`` … ``v_top4``), 49 children each; record
``i`` has the code ``A{i:03d}`` and the date 2026-``(i % 12) + 1``-``(i % 27) + 1``. Under the first
top, ``v_many`` (record 7) cites the 30 K records ``Token 01`` … ``Token 30``, and ``v_one1`` …
``v_one3`` (records 8–10) one each, ``Token 01`` … ``Token 03``.
"""

import pytest
from scenario import W1, ok, refused

QUERIED = ("V", "V.code", "V.on", "K", "Bvk")


def _query(world, body):
    return world.api.post(f"/workspaces/{W1}/queries/objects", body)


def _ids(page):
    return [item["id"] for item in page["items"]]


@pytest.mark.journey("J22")
@pytest.mark.structures(*QUERIED)
def test_combine_criteria_select_expand_and_page(world):
    """Given V records under several tops, some citing K records, one citing 30. When the integrator
    queries one top's records with a typed criterion, an ancestor and a hop to a K record, sorted,
    with selected fields and the citations expanded five at a time, two records a page; then the same
    with the hop inverted. Then the items are exactly the matching records in sort order with the
    selected fields; each expansion counts all, shows at most five in name order and continues on
    the relationship list; the inverted hop returns the complement; the field criteria select the
    same records in the same order as list filters. An unbound field, an unknown body property and
    both contexts are refused."""
    code, on, cites = world.key("V.code"), world.key("V.on"), world.key("Bvk")
    fields = [
        {"field": code, "op": "startsWith", "value": "A00"},
        {"field": on, "op": "gte", "value": "2026-08-01"},
        {"field": f"ancestor:{world.key('V')}", "op": "eq", "value": world.ids["v_top0"]},
    ]
    hop = {
        "related": {
            "relationTypeKey": cites,
            "direction": "outgoing",
            "where": [{"field": "name", "op": "eq", "value": "Token 02"}],
        }
    }
    body = {
        "objectTypeKey": world.key("V"),
        "where": [*fields, hop],
        "sort": f"-{code}",
        "select": ["name", code, "path", f"ancestor:{world.key('V')}"],
        "expand": [
            {"relationTypeKey": cites, "direction": "outgoing", "select": ["name"], "limit": 5}
        ],
        "pageSize": 1,
    }
    first = ok(_query(world, body))
    second = ok(_query(world, {**body, "cursor": first["nextCursor"]}))
    assert second["nextCursor"] is None
    items = first["items"] + second["items"]
    # Records 9 (v_one2) and 7 (v_many) cite Token 02 and match the fields; by code descending.
    assert [item["id"] for item in items] == [world.ids["v_one2"], world.ids["v_many"]]
    one, many = items
    assert {"id", "objectTypeKey", "version", "fields"} <= set(one)
    assert one["fields"][code] == "A009"
    top = world.record("V", world.ids["v_top0"])
    assert one["fields"][f"ancestor:{world.key('V')}"] == {"id": top["id"], "name": top["name"]}

    [single] = one["expanded"]
    assert (single["count"], [i["object"]["fields"]["name"] for i in single["items"]]) == (
        1,
        ["Token 02"],
    )
    assert single["nextCursor"] is None
    [cited] = many["expanded"]
    shown = [i["object"]["fields"]["name"] for i in cited["items"]]
    assert cited["count"] == 30 and shown == [f"Token {n:02d}" for n in range(1, 6)]
    rest = ok(
        world.api.get(
            "/relations",
            objectId=many["id"],
            direction="outgoing",
            relationTypeKey=cites,
            cursor=cited["nextCursor"],
        )
    )
    assert rest["items"][0]["object"]["name"] == "Token 06"

    # Without the hop: records 1–9 under the first top whose date is from August on: 7, 8, 9.
    inverted = ok(
        _query(world, {**body, "where": [*fields, {**hop, "not": True}], "pageSize": 100})
    )
    assert _ids(inverted) == [world.ids["v_one1"]]

    plain = ok(
        _query(
            world,
            {
                "objectTypeKey": world.key("V"),
                "where": fields[:2],
                "sort": f"-{code}",
                "pageSize": 100,
            },
        )
    )
    listed = ok(
        world.api.get(
            f"/objects/{world.key('V')}",
            sort=f"-{code}",
            pageSize=100,
            **{f"filter.{code}.startsWith": "A00", f"filter.{on}.gte": "2026-08-01"},
        )
    )
    assert _ids(plain) == _ids(listed) and len(_ids(plain)) == 3

    unbound = {**body, "where": [{"field": "not-a-field", "op": "eq", "value": "x"}]}
    assert (
        refused(_query(world, unbound), 422, "invalid_query")["details"]["path"] == "/where/0/field"
    )
    refused(_query(world, {**body, "unknownProperty": 1}), 422, "request_validation_error")
    cs = world.change_set()
    publication = world.publish(world.change_set())
    both = {**body, "context": {"changeSetId": cs["id"], "publicationId": publication["id"]}}
    refused(_query(world, both), 422, "mutually_exclusive_context")


@pytest.mark.journey("J22.1")
@pytest.mark.structures("V", "K")
def test_the_cross_type_lookup(world):
    """When records of two types are looked up by a part of their name sorted by type, the children
    of one record are listed by a built-in filter, a type outside the named application is asked
    for, and a parent and the top level are asked for together. Then both types' records come
    ordered by type name, then name; exactly the children; the last two are refused."""
    for structure, name in (
        ("V", "Marker plum"),
        ("V", "Marker fig"),
        ("K", "Marker kiwi"),
        ("K", "Marker apple"),
    ):
        world.made(structure, name)
    types = {t["key"]: t["name"] for t in ok(world.api.get("/object-types", pageSize=500))["items"]}
    found = ok(
        world.api.get(
            "/objects",
            workspaceKey=W1,
            objectTypeKey=[world.key("V"), world.key("K")],
            search="marker",
            sort="objectType",
        )
    )["items"]
    order = [(types[item["objectTypeKey"]].casefold(), item["name"].casefold()) for item in found]
    assert len(found) == 4 and order == sorted(order)

    children = ok(
        world.api.get(
            "/objects",
            workspaceKey=W1,
            includeTotal=True,
            pageSize=100,
            **{"filter.parentObjectId.eq": world.ids["v_top1"]},
        )
    )
    assert children["totalCount"] == 49
    assert {item["parentObjectId"] for item in children["items"]} == {world.ids["v_top1"]}

    outside = world.api.get("/objects", applicationKey=world.app("K"), objectTypeKey=world.key("V"))
    refused(outside, 422, "invalid_object_type_for_application")
    both = world.api.get("/objects", parentObjectId=world.ids["v_top1"], topLevel=True)
    refused(both, 422, "mutually_exclusive_scope")


@pytest.mark.journey("J22.2")
@pytest.mark.structures("V", "K", "Bvk")
def test_the_edge_list(world):
    """When the workspace's edges of one relationship type are listed without a direction, outgoing
    only, and in a publication, and the removed mapping list is asked for. Then without a direction
    each edge appears twice with its ends swapped, with it once; the publication's edges carry set
    version 0; the removed list answers 405 (decided D-1)."""
    cites = world.key("Bvk")

    def edges(**params):
        return ok(
            world.api.get(
                f"/workspaces/{W1}/relations", relationTypeKey=cites, pageSize=100, **params
            )
        )["items"]

    outgoing = edges(direction="outgoing")
    assert len(outgoing) == 33 and {e["relationTypeKey"] for e in outgoing} == {cites}
    assert all(e["source"]["objectTypeKey"] == world.key("V") for e in outgoing)
    both = edges()
    pairs = {
        (e["relationId"], e["direction"]): (e["source"]["id"], e["target"]["id"]) for e in both
    }
    assert len(both) == 66
    for edge in outgoing:
        forward = pairs[(edge["relationId"], "outgoing")]
        assert pairs[(edge["relationId"], "incoming")] == forward[::-1]
    publication = world.publish(world.change_set())
    published = edges(publicationId=publication["id"])
    assert len(published) == 66 and {e["mappingVersion"] for e in published} == {0}
    assert world.api.get(f"/workspaces/{W1}/mappings").status_code == 405


@pytest.mark.journey("J22.3")
@pytest.mark.structures("H", "K", "Bnn", "Bh1n")
def test_relationships_of_one_record_searched_and_sorted(world):
    """Given a K record related to H records of two branches through two relationship types, and to
    one more H record whose name does not match. When its relationships of both types are listed,
    searched and sorted by the related records' top ancestor. Then both types' relationships with
    matching related records arrive in that ancestor's name order. A timestamp sort in a change set
    and a record the context does not hold are refused."""
    k = world.made("K", "Anchor token")["id"]
    ok(world.relate("Bnn", world.ids["h3"], k, {"Bnn.weight": 1}), 201)
    ok(world.relate("Bnn", world.ids["j2"], k, {"Bnn.weight": 1}), 201)
    ok(world.relate("Bh1n", world.ids["j3"], k), 201)
    other = world.made("H", "Elsewhere")
    ok(world.relate("Bnn", other["id"], k, {"Bnn.weight": 1}), 201)

    listed = ok(
        world.api.get(
            "/relations",
            objectId=k,
            direction="both",
            relationTypeKey=[world.key("Bnn"), world.key("Bh1n")],
            search="Level",
            sort=f"ancestor:{world.key('H')}",
        )
    )["items"]
    assert [item["object"]["id"] for item in listed] == [
        world.ids["h3"],
        world.ids["j2"],
        world.ids["j3"],
    ]
    assert {item["relation"]["relationTypeKey"] for item in listed} == {
        world.key("Bnn"),
        world.key("Bh1n"),
    }

    cs = world.change_set()
    refused(
        world.api.get("/relations", objectId=k, changeSetId=cs["id"], sort="createdAt"),
        422,
        "invalid_sort",
    )
    staged = world.made("K", "Staged only", change_set=world.current(cs))
    refused(world.api.get("/relations", objectId=staged["id"]), 404, "object_not_found")


@pytest.mark.journey("J22.4")
@pytest.mark.structures("V", "V.code")
def test_a_model_declared_field_on_the_cross_type_lookup_is_refused(world):
    """When the cross-type lookup is filtered or sorted by a model-declared field. Then each is
    refused naming the per-type route and listing the built-in fields or sorts it takes."""
    code = world.key("V.code")
    error = refused(
        world.api.get("/objects", **{f"filter.{code}.eq": "A001"}), 422, "invalid_filter"
    )
    assert error["details"]["route"].endswith("/api/v1/objects/{objectTypeKey}")
    assert (
        "name" in error["details"]["builtInFields"]
        and code not in error["details"]["builtInFields"]
    )
    error = refused(world.api.get("/objects", sort=code), 422, "invalid_sort")
    assert error["details"]["route"].endswith("/api/v1/objects/{objectTypeKey}")
    assert "name" in error["details"]["builtInSorts"]
