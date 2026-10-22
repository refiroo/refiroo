"""J21 — Read a collection completely and resume (USER_JOURNEYS.md).

The seed holds 250 V records in W1 (``scenario.ARTICLES``), with duplicate names and unset values.
"""

from uuid import uuid4

import pytest
from scenario import ARTICLES, W1, W2, ok, plan_reads, planned, refused

PAGED = ("V", "V.rank", "V.on", "V.code")


def _list(world, **params):
    return world.api.get(f"/objects/{world.key('V')}", **params)


def _forward(world, page_size=100, **params):
    pages, cursor = [], None
    while True:
        page = ok(_list(world, pageSize=page_size, cursor=cursor, **params))
        pages.append(page)
        cursor = page.get("nextCursor")
        if not cursor:
            return pages


def _ids(pages):
    return [item["id"] for page in pages for item in page["items"]]


@pytest.mark.journey("J21")
@pytest.mark.structures(*PAGED)
def test_page_to_the_end_and_back_and_resume_a_stored_cursor(world):
    """Given 250 V records. When pages of 100 are read to the end and back, and a stored cursor is
    resumed in a later request. Then 250 distinct records arrive in name order, the next cursor ends
    only at the end, walking back returns the rows in list order, and the resumed request answers
    the same page. A page size above the route's maximum is refused on every collection route."""
    pages = _forward(world)
    ids = _ids(pages)
    assert len(ids) == ARTICLES and len(set(ids)) == ARTICLES
    names = [item["name"] for page in pages for item in page["items"]]
    assert names == sorted(names, key=str.casefold)
    assert all(page["nextCursor"] for page in pages[:-1]) and pages[-1]["nextCursor"] is None

    back, cursor = [], pages[-1]["prevCursor"]
    while cursor:
        page = ok(_list(world, pageSize=100, cursor=cursor))
        back = page["items"] + back
        cursor = page.get("prevCursor")
    assert [item["id"] for item in back] == ids[: len(back)]

    stored = pages[0]["nextCursor"]
    assert ok(_list(world, pageSize=100, cursor=stored))["items"] == pages[1]["items"]

    record = world.made("H", "History owner")
    cs = world.change_set()
    publication = world.publish(world.change_set())
    one = {
        "op": "create",
        "applicationKey": world.app("V"),
        "objectTypeKey": world.key("V"),
        "name": "Batched",
        "attributes": [{"attributeTypeKey": world.key("V.code"), "value": "B1"}],
    }
    job = ok(
        world.api.post(
            "/batches",
            {"workspaceKey": W1, "policy": "independent", "run": "inline", "items": [one]},
        )
    )
    routes = [
        f"/objects/{world.key('V')}",
        "/objects",
        f"/objects/{world.key('H')}/{record['id']}/history",
        f"/workspaces/{W1}/change-sets",
        f"/workspaces/{W1}/publications",
        f"/change-sets/{cs['id']}/object-changes",
        "/workspaces",
        "/applications",
        "/object-types",
        "/model-releases",
        "/jobs",
        f"/jobs/{job['job']['id']}/items",
    ]
    for route in routes:
        refused(world.api.get(route, pageSize=100000), 422, "REQUEST_VALIDATION_ERROR")
    refused(
        world.api.get("/relations", objectId=record["id"], pageSize=100000),
        422,
        "REQUEST_VALIDATION_ERROR",
    )
    assert publication


@pytest.mark.journey("J21.1")
@pytest.mark.structures(*PAGED)
def test_jump_to_a_position(world):
    """When the list is read at position 150 with its total, at 250 and at -1. Then the page starts
    at row 150 of 250; at 250 it is empty with a cursor back to the last page; -1 is refused."""
    page = ok(_list(world, position=150, includeTotal=True, pageSize=20))
    assert (page["startIndex"], page["totalCount"]) == (150, ARTICLES)
    whole = _ids(_forward(world))
    assert [item["id"] for item in page["items"]] == whole[150:170]
    end = ok(_list(world, position=ARTICLES, includeTotal=True, pageSize=20))
    assert end["items"] == [] and end["startIndex"] == end["totalCount"] and end["prevCursor"]
    last = ok(_list(world, cursor=end["prevCursor"], pageSize=20))
    assert [item["id"] for item in last["items"]] == whole[-20:]
    refused(_list(world, position=-1), 422, "REQUEST_VALIDATION_ERROR")


@pytest.mark.journey("J21.2")
@pytest.mark.structures(*PAGED)
def test_start_from_the_end(world):
    """When the list is read from its end, 100 at a time. Then the last page, the last 100 rows (API.md:
    "the last page"; the case counted 50), comes in list order, with a cursor back and none forward."""
    page = ok(_list(world, **{"from": "end"}, pageSize=100))
    assert [item["id"] for item in page["items"]] == _ids(_forward(world))[-100:]
    assert page["nextCursor"] is None and page["prevCursor"]


@pytest.mark.journey("J21.3")
@pytest.mark.structures(*PAGED)
def test_seek_to_a_value(world):
    """When the list is sorted by an integer field and sought to 40, ascending and descending, and by
    a date field sought to something that is not a date. Then the first row is the first at or past
    40 in that direction, unset values come after the set ones; the last is refused."""
    rank = world.key("V.rank")
    up = ok(_list(world, sort=rank, seek=40, pageSize=100))["items"]
    values = [world.value(item, "V.rank") for item in up]
    assert values[0] >= 40 and all(v is None or v >= 40 for v in values)
    down = ok(_list(world, sort=f"-{rank}", seek=40, pageSize=100))["items"]
    values = [world.value(item, "V.rank") for item in down]
    assert values[0] <= 40
    present = [v for v in values if v is not None]
    assert values[: len(present)] == present and present == sorted(present, reverse=True)
    refused(_list(world, sort=world.key("V.on"), seek="not-a-date"), 422, "INVALID_SEEK")


@pytest.mark.journey("J21.4")
@pytest.mark.structures(*PAGED)
def test_totals_on_request(world):
    """When a filtered page is read with and without its total. Then with it the page carries the
    filtered count and its start; without it, neither."""
    flag = {f"filter.{world.key('V.flag')}.eq": "true"}
    counted = ok(_list(world, includeTotal=True, pageSize=10, **flag))
    every = _ids(_forward(world, **flag))
    assert (counted["totalCount"], counted["startIndex"]) == (len(every), 0)
    plain = ok(_list(world, pageSize=10, **flag))
    assert "totalCount" not in plain and "startIndex" not in plain


@pytest.mark.journey("J21.5")
@pytest.mark.structures(*PAGED)
def test_records_inserted_between_pages(world):
    """Given the first page of 100 read by name. When records sorting before and after the cursor are
    added and one is deleted elsewhere, and reading continues. Then no original row repeats or is
    skipped; rows added after the cursor appear and those before do not."""
    first = ok(_list(world, pageSize=100))
    original = _ids(_forward(world))
    before = world.made("V", "Aardvark early", values={"V.code": "EARLY"})
    after = world.made("V", "Zz late", values={"V.code": "LATE"})
    removed_id = original[150]
    victim = world.record("V", removed_id)
    deleted = world.api.delete(
        f"/objects/{world.key('V')}/{removed_id}", expectedVersion=victim["version"]
    )
    if deleted.status_code == 409:
        token = refused(deleted, 409, "OBJECT_HAS_DEPENDANTS")["details"]["deletionPreviewToken"]
        deleted = world.api.delete(
            f"/objects/{world.key('V')}/{removed_id}",
            expectedVersion=victim["version"],
            cascade=True,
            deletionPreviewToken=token,
        )
    assert deleted.status_code == 204

    rest, cursor = [], first["nextCursor"]
    while cursor:
        page = ok(_list(world, pageSize=100, cursor=cursor))
        rest += [item["id"] for item in page["items"]]
        cursor = page.get("nextCursor")
    seen = [item["id"] for item in first["items"]] + rest
    assert [i for i in seen if i in original] == [i for i in original if i != removed_id]
    assert after["id"] in rest and before["id"] not in seen


@pytest.mark.journey("J21.6")
@pytest.mark.structures(*PAGED)
def test_page_a_change_set_or_a_publication(world):
    """When the same paging runs in a change set and a publication of the same content, and each
    context's cursor is used in another. Then both return the same records in the same name order
    as live (equal names may differ: live breaks ties on an internal sequence, a change set or a
    publication on the record ID, API.md); each foreign cursor is refused."""

    def names(pages):
        return [item["name"] for page in pages for item in page["items"]]

    live_pages = _forward(world)
    publication = world.publish(world.change_set())
    cs = world.change_set()
    for context in ({"changeSetId": cs["id"]}, {"publicationId": publication["id"]}):
        pages = _forward(world, **context)
        assert names(pages) == names(live_pages)
        assert sorted(_ids(pages)) == sorted(_ids(live_pages))
    staged = ok(_list(world, pageSize=100, changeSetId=cs["id"]))["nextCursor"]
    published = ok(_list(world, pageSize=100, publicationId=publication["id"]))["nextCursor"]
    refused(_list(world, pageSize=100, cursor=staged), 422, "INVALID_CURSOR")
    refused(
        _list(world, pageSize=100, cursor=published, changeSetId=cs["id"]), 422, "INVALID_CURSOR"
    )


@pytest.mark.journey("J21.7")
@pytest.mark.structures(*PAGED)
def test_a_cursor_reused_with_another_query_is_refused(world):
    """When a list cursor is reused with another search, another workspace, a change set, or on the
    cross-type lookup, and a cursor is combined with a position. Then each is refused; the
    combination names the parameters."""
    cursor = ok(_list(world, pageSize=10))["nextCursor"]
    cs = world.change_set()
    for response in (
        _list(world, pageSize=10, cursor=cursor, search="amber"),
        _list(world, pageSize=10, cursor=cursor, workspaceKey=W2),
        _list(world, pageSize=10, cursor=cursor, changeSetId=cs["id"]),
        world.api.get("/objects", pageSize=10, cursor=cursor, workspaceKey=W1),
    ):
        refused(response, 422, "INVALID_CURSOR")
    error = refused(
        _list(world, pageSize=10, cursor=cursor, position=5), 422, "CONFLICTING_PAGE_PARAMETERS"
    )
    assert {"cursor", "position"} <= set(error["details"]["parameters"])


@pytest.mark.journey("J21.8")
@pytest.mark.structures(*PAGED)
def test_an_unknown_query_parameter_is_refused(world):
    """When a list is asked for with a misspelt parameter, and every other kind of read with an
    unknown one. Then each is refused naming the parameter (decided D-3)."""
    error = refused(_list(world, pagesize=5), 422, "UNKNOWN_PARAMETER")
    assert "pagesize" in str(error["details"])
    record = world.made("H", "Asked about")
    cs = world.change_set()
    routes = [
        "/objects",
        f"/objects/{world.key('H')}/{record['id']}",
        f"/objects/{world.key('H')}/{record['id']}/history",
        f"/objects/{world.key('H')}/{record['id']}/parent-candidates",
        "/workspaces",
        f"/workspaces/{W1}",
        f"/workspaces/{W1}/change-sets",
        f"/workspaces/{W1}/publications",
        f"/workspaces/{W1}/relations",
        f"/change-sets/{cs['id']}",
        f"/change-sets/{cs['id']}/object-changes",
        "/model",
        "/model/placements",
        "/capabilities",
        "/applications",
        "/object-types",
        "/relation-types",
        "/attribute-types",
        "/object-type-relations",
        "/model-releases",
        "/workspace-models",
        "/jobs",
        "/workspace-runtime-state",
    ]
    for route in routes:
        error = refused(
            world.api.get(route, notAParameter=uuid4().hex[:4]), 422, "UNKNOWN_PARAMETER"
        )
        assert "notAParameter" in str(error["details"]), route
    refused(
        world.api.get("/relations", objectId=record["id"], notAParameter=1),
        422,
        "UNKNOWN_PARAMETER",
    )


@pytest.mark.journey("J21.9")
@pytest.mark.structures(*PAGED)
def test_an_attribute_sort_pages_across_records_with_and_without_a_value(world):
    """Given 250 V records, some without V.rank and many sharing a value. When the list is read sorted
    by V.rank, ascending and descending, with pageSize=7, to the end through nextCursor, back through
    prevCursor, at a position in each part, with from=end, a seek and includeTotal. Then each record
    appears once, by value, the records without a value last in both directions, and totalCount and
    startIndex follow."""
    _attribute_sort_pages(world)


@pytest.mark.journey("J21.9")
@pytest.mark.structures(*PAGED)
def test_an_attribute_sort_pages_the_same_way_in_a_publication(world):
    """The same reads in a publication of those records (publicationId), which read their order
    through the publication's own value index since 0.9 C6a (C-D67), answer the same way."""
    publication = world.publish(world.change_set())
    _attribute_sort_pages(world, publicationId=publication["id"])


def _attribute_sort_pages(world, count=ARTICLES, **context):
    rank = world.key("V.rank")
    for sort, descending in ((rank, False), (f"-{rank}", True)):
        pages = _forward(world, page_size=7, sort=sort, **context)
        items = [item for page in pages for item in page["items"]]
        ids = [item["id"] for item in items]
        assert len(ids) == count and len(set(ids)) == count
        values = [world.value(item, "V.rank") for item in items]
        present = [v for v in values if v is not None]
        assert 0 < len(present) < count
        assert values[: len(present)] == present
        assert present == sorted(present, reverse=descending)

        back, cursor = [], pages[-1]["prevCursor"]
        while cursor:
            page = ok(_list(world, **context, pageSize=7, sort=sort, cursor=cursor))
            back = [item["id"] for item in page["items"]] + back
            cursor = page.get("prevCursor")
        assert back == ids[: len(back)] and len(back) + len(pages[-1]["items"]) == count

        for position in (len(present) - 3, len(present) + 2):
            at = ok(
                _list(world, **context, pageSize=7, sort=sort, position=position, includeTotal=True)
            )
            assert [item["id"] for item in at["items"]] == ids[position : position + 7]
            assert (at["totalCount"], at["startIndex"]) == (count, position)
            following = ok(
                _list(
                    world,
                    **context,
                    pageSize=7,
                    sort=sort,
                    cursor=at["nextCursor"],
                    includeTotal=True,
                )
            )
            assert [item["id"] for item in following["items"]] == ids[position + 7 : position + 14]
            assert following["startIndex"] == position + 7

        last = ok(
            _list(world, **context, pageSize=7, sort=sort, includeTotal=True, **{"from": "end"})
        )
        assert [item["id"] for item in last["items"]] == ids[-7:]
        assert last["startIndex"] == count - 7

        sought = ok(_list(world, **context, pageSize=7, sort=sort, seek=40, includeTotal=True))
        first = next(
            i for i, v in enumerate(values) if v is None or (v <= 40 if descending else v >= 40)
        )
        assert [item["id"] for item in sought["items"]] == ids[first : first + 7]
        assert sought["startIndex"] == first


def _page_reads(statement: str) -> bool:
    """A page read in an attribute's order: ordered, limited and joined to the values."""
    return "ORDER BY" in statement and "LIMIT" in statement and "attribute_values" in statement


def _counts(statement: str) -> bool:
    return "count(*)" in statement


def _node_types(plan) -> list[str]:
    return [
        plan["Node Type"],
        *(node for child in plan.get("Plans", []) for node in _node_types(child)),
    ]


def _create_v(world, name, *, parent=None, **values):
    item = {
        "op": "create",
        "applicationKey": world.app("V"),
        "objectTypeKey": world.key("V"),
        "name": name,
        "attributes": [{"attributeTypeKey": world.key(k), "value": v} for k, v in values.items()],
    }
    if parent is not None:
        item["parent"] = {"id": parent}
    return item


def _batch(world, items, **context):
    body = {
        "policy": "atomic",
        "run": "inline",
        "items": items,
        **(context or {"workspaceKey": W1}),
    }
    result = ok(world.api.post("/batches", body))
    assert result["job"]["result"] == "applied", result["job"]
    return result


@pytest.mark.journey("J21.9")
@pytest.mark.structures(*PAGED)
def test_an_attribute_sort_pages_the_same_way_in_a_change_set(world):
    """Given a change set over the 250 V records in which a value is raised past the others, a value
    given to a record without one and taken from another, records created with and without a value
    and a record deleted. When the change set's list is read sorted by V.rank in every paging mode.
    Then it lists the change set's records, by their values in the change set, those without one last
    in both directions. Its first page, under a parent too, reads the base's and the change set's
    value indexes, not each record's value, and its total reads no value (0.11 Q3, D205)."""
    rank = world.key("V.rank")
    live = [item for page in _forward(world, sort=rank) for item in page["items"]]
    held = [item for item in live if world.value(item, "V.rank") is not None]
    unset = [item for item in live if world.value(item, "V.rank") is None]
    raised, cleared, given, deleted = held[0], held[1], unset[0], held[2]

    def update(item, value):
        return {
            "op": "update",
            "target": {"id": item["id"]},
            "expectedVersion": item["version"],
            "attributes": [{"attributeTypeKey": rank, "value": value}],
        }

    cs = world.change_set()
    items = [
        update(raised, 96),
        update(cleared, None),
        update(given, 0),
        {"op": "delete", "target": {"id": deleted["id"]}, "expectedVersion": deleted["version"]},
        _create_v(world, "Staged fifty", **{"V.code": "S50", "V.rank": 50}),
        _create_v(world, "Staged zero", **{"V.code": "S00", "V.rank": 0}),
        _create_v(world, "Staged unset", **{"V.code": "SUN"}),
    ]
    _batch(world, items, changeSetId=cs["id"], expectedChangeSetVersion=cs["version"])
    context = {"changeSetId": cs["id"]}
    _attribute_sort_pages(world, count=ARTICLES + 2, **context)

    staged = {
        item["id"]: world.value(item, "V.rank")
        for page in _forward(world, sort=rank, **context)
        for item in page["items"]
    }
    assert deleted["id"] not in staged
    assert (staged[raised["id"]], staged[cleared["id"]], staged[given["id"]]) == (96, None, 0)

    with planned(_page_reads) as pages, planned(_counts) as counts:
        ok(_list(world, pageSize=7, sort=rank, includeTotal=True, **context))
        ok(_list(world, pageSize=7, sort=rank, parentObjectId=world.ids["v_top1"], **context))
    assert len(pages) == 2 and counts
    for plan in pages:
        reads = plan_reads(plan)
        assert "ix_snapshot_attribute_values_change_set_key_integer" in reads, reads
        assert "uq_snapshot_attribute_value" not in reads, reads
    for plan in counts:
        assert "snapshot_attribute_values" not in plan_reads(plan), plan_reads(plan)


@pytest.mark.journey("J21.9")
@pytest.mark.structures(*PAGED)
def test_records_sharing_a_value_follow_their_id_in_every_context(world):
    """Given 60 V records under one parent sharing one V.rank and five holding a lower one. When the
    parent's records are read sorted by V.rank, ascending and descending, live, in a change set and
    in a publication, through cursors and at a position. Then they come by value, then by record ID
    in the sort's direction, alike in the three contexts; live's first page reads them in its value
    index's order without sorting the records that share the value (0.11 Q3, D206)."""
    rank = world.key("V.rank")
    parent = _batch(world, [_create_v(world, "Tied parent", **{"V.code": "TIED"})])["items"][0][
        "id"
    ]
    children = [
        _create_v(world, f"Tied {n:02d}", parent=parent, **{"V.code": f"T{n:02d}", "V.rank": 500})
        for n in range(60)
    ]
    children += [
        _create_v(world, f"Low {n}", parent=parent, **{"V.code": f"L{n}", "V.rank": 7})
        for n in range(5)
    ]
    _batch(world, children)
    publication = world.publish(world.change_set())
    cs = world.change_set()

    for context in ({}, {"changeSetId": cs["id"]}, {"publicationId": publication["id"]}):
        for sort, descending in ((rank, False), (f"-{rank}", True)):
            read = {"sort": sort, "parentObjectId": parent, **context}
            listed = [
                item for page in _forward(world, page_size=7, **read) for item in page["items"]
            ]
            order = [(world.value(item, "V.rank"), item["id"]) for item in listed]
            assert len(order) == 65 and order == sorted(order, reverse=descending), context
            ids = [item["id"] for item in listed]
            at = ok(_list(world, pageSize=7, position=30, includeTotal=True, **read))
            assert [item["id"] for item in at["items"]] == ids[30:37]
            assert (at["totalCount"], at["startIndex"]) == (65, 30)

    with planned(_page_reads, ordered=True) as plans:
        ok(_list(world, pageSize=7, sort=rank, parentObjectId=parent))
    assert plans
    assert "ix_attribute_values_key_integer" in plan_reads(plans[0]), plan_reads(plans[0])
    assert not {"Sort", "Incremental Sort"} & set(_node_types(plans[0])), _node_types(plans[0])


@pytest.mark.journey("J21.9")
@pytest.mark.structures(*PAGED, "V.flag")
def test_a_flag_sorts_in_a_change_set_through_its_index(world):
    """When a parent's V records are read sorted by the boolean V.flag in a change set. Then false
    comes before true and the records without a value last, and the first page reads the change
    set's boolean value index (0.11 Q3, D207)."""
    flag = world.key("V.flag")
    cs = world.change_set()
    read = {"sort": flag, "parentObjectId": world.ids["v_top0"], "changeSetId": cs["id"]}
    with planned(_page_reads) as plans:
        first = ok(_list(world, pageSize=7, **read))
    listed = [item for page in _forward(world, page_size=7, **read) for item in page["items"]]
    assert [item["id"] for item in first["items"]] == [item["id"] for item in listed[:7]]
    values = [world.value(item, "V.flag") for item in listed]
    present = [value for value in values if value is not None]
    assert len(listed) == 49 and False in present and True in present
    assert values[: len(present)] == sorted(present)
    assert "ix_snapshot_attribute_values_change_set_key_boolean" in plan_reads(plans[0]), (
        plan_reads(plans[0])
    )
