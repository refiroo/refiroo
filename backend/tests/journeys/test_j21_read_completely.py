"""J21 — Read a collection completely and resume (USER_JOURNEYS.md).

The seed holds 250 V records in W1 (``scenario.ARTICLES``), with duplicate names and unset values.
"""

from uuid import uuid4

import pytest
from scenario import ARTICLES, W1, W2, ok, refused

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
        "/model-runtime-state",
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
    rank = world.key("V.rank")
    for sort, descending in ((rank, False), (f"-{rank}", True)):
        pages = _forward(world, page_size=7, sort=sort)
        items = [item for page in pages for item in page["items"]]
        ids = [item["id"] for item in items]
        assert len(ids) == ARTICLES and len(set(ids)) == ARTICLES
        values = [world.value(item, "V.rank") for item in items]
        present = [v for v in values if v is not None]
        assert 0 < len(present) < ARTICLES
        assert values[: len(present)] == present
        assert present == sorted(present, reverse=descending)

        back, cursor = [], pages[-1]["prevCursor"]
        while cursor:
            page = ok(_list(world, pageSize=7, sort=sort, cursor=cursor))
            back = [item["id"] for item in page["items"]] + back
            cursor = page.get("prevCursor")
        assert back == ids[: len(back)] and len(back) + len(pages[-1]["items"]) == ARTICLES

        for position in (len(present) - 3, len(present) + 2):
            at = ok(_list(world, pageSize=7, sort=sort, position=position, includeTotal=True))
            assert [item["id"] for item in at["items"]] == ids[position : position + 7]
            assert (at["totalCount"], at["startIndex"]) == (ARTICLES, position)
            following = ok(_list(world, pageSize=7, sort=sort, cursor=at["nextCursor"], includeTotal=True))
            assert [item["id"] for item in following["items"]] == ids[position + 7 : position + 14]
            assert following["startIndex"] == position + 7

        last = ok(_list(world, pageSize=7, sort=sort, includeTotal=True, **{"from": "end"}))
        assert [item["id"] for item in last["items"]] == ids[-7:]
        assert last["startIndex"] == ARTICLES - 7

        sought = ok(_list(world, pageSize=7, sort=sort, seek=40, includeTotal=True))
        first = next(i for i, v in enumerate(values) if v is None or (v <= 40 if descending else v >= 40))
        assert [item["id"] for item in sought["items"]] == ids[first : first + 7]
        assert sought["startIndex"] == first
