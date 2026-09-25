"""Base 0.8 S3 and S4: the paging contract and the query additions over the S1 volume fixture.

Every read is checked against a reference list read in one large cursor walk, in live, draft and
history contexts: forward and backward cursors, the last page, anchors, totals and start indexes,
seek by value and position reads, plus top-level object lists and relation search and sort. The
volume budgets for these reads (constant statements, bounded rows) are held by
``test_volume_baseline.py``; full-volume times are recorded in the Base 0.8 plan.
"""

from typing import Any

import pytest
from volume_fixture import (
    CODE,
    GROUP,
    ITEM,
    NODE,
    RANK,
    WORKSPACE,
    scaled_shape,
    volume_app,
)

CONTEXTS = ("live", "draft", "history")
PAGE = 20


@pytest.fixture(scope="module")
def volume(_migrated_template, tmp_path_factory):
    with volume_app(_migrated_template, tmp_path_factory.mktemp("paging"), scaled_shape(0.01)) as pair:
        yield pair


def _context(context: str, dataset) -> dict[str, str]:
    if context == "live":
        return {"workspaceKey": WORKSPACE}
    if context == "draft":
        return {"workspaceDraftId": dataset.draft_id}
    return {"workspaceRevisionId": dataset.revision_id}


def _get(client, path: str, params: dict[str, Any]) -> dict[str, Any]:
    response = client.get(path, params=params)
    assert response.status_code == 200, response.text
    return response.json()


def _error(client, path: str, params: dict[str, Any]) -> dict[str, Any]:
    response = client.get(path, params=params)
    assert response.status_code == 422, response.text
    return response.json()["error"]


def _everything(client, path: str, params: dict[str, Any]) -> list[dict[str, Any]]:
    """The whole list in one cursor walk of large pages: the reference order."""
    items, cursor = [], None
    while True:
        body = _get(client, path, {**params, "pageSize": 500, **({"cursor": cursor} if cursor else {})})
        items.extend(body["items"])
        cursor = body["nextCursor"]
        if cursor is None:
            return items


def _ids(items: list[dict[str, Any]]) -> list[str]:
    return [item["id"] if "id" in item else item["relation"]["id"] for item in items]


def _walk(client, path: str, params: dict[str, Any], reference: list[str]) -> None:
    """Forward from the start and backward from the end both visit the reference exactly."""
    size = 7
    forward, cursor, first = [], None, True
    while True:
        body = _get(
            client,
            path,
            {**params, "pageSize": size, "includeTotal": True, **({"cursor": cursor} if cursor else {})},
        )
        assert body["totalCount"] == len(reference)
        assert body["startIndex"] == len(forward)
        assert (body["prevCursor"] is None) == first
        forward.extend(_ids(body["items"]))
        cursor, first = body["nextCursor"], False
        if cursor is None:
            break
    assert forward == reference

    last = _get(client, path, {**params, "pageSize": size, "from": "end", "includeTotal": True})
    assert last["nextCursor"] is None
    assert last["startIndex"] == len(reference) - len(last["items"])
    backward, body = _ids(last["items"]), last
    while body["prevCursor"] is not None:
        body = _get(client, path, {**params, "pageSize": size, "cursor": body["prevCursor"], "includeTotal": True})
        backward = _ids(body["items"]) + backward
        assert body["startIndex"] == len(reference) - len(backward)
    assert backward == reference


def _jumps(client, path: str, params: dict[str, Any], reference: list[str]) -> None:
    """Position reads land on row N; their cursors and anchor continue from there."""
    at = len(reference) // 2
    landed = _get(client, path, {**params, "pageSize": PAGE, "position": at, "includeTotal": True})
    assert _ids(landed["items"]) == reference[at : at + PAGE]
    assert (landed["startIndex"], landed["totalCount"]) == (at, len(reference))
    before = _get(client, path, {**params, "pageSize": PAGE, "cursor": landed["prevCursor"]})
    assert _ids(before["items"]) == reference[at - PAGE : at]
    after = _get(client, path, {**params, "pageSize": PAGE, "cursor": landed["nextCursor"]})
    assert _ids(after["items"]) == reference[at + PAGE : at + 2 * PAGE]
    reopened = _get(client, path, {**params, "pageSize": PAGE, "cursor": landed["anchor"]})
    assert _ids(reopened["items"]) == _ids(landed["items"])

    beyond = _get(client, path, {**params, "pageSize": PAGE, "position": len(reference) + 5, "includeTotal": True})
    assert beyond["items"] == [] and beyond["nextCursor"] is None
    assert beyond["startIndex"] == len(reference)
    tail = _get(client, path, {**params, "pageSize": PAGE, "cursor": beyond["prevCursor"]})
    assert _ids(tail["items"]) == reference[-PAGE:]


@pytest.mark.parametrize("context", CONTEXTS)
def test_object_pages_move_both_ways_and_jump_in_every_context(volume, context):
    client, dataset = volume
    path = f"/api/v1/objects/{ITEM}"
    params = {**_context(context, dataset), "parentObjectId": dataset.heavy_group_id, "sort": "name"}
    reference = _ids(_everything(client, path, params))
    assert len(reference) > 5 * PAGE
    _walk(client, path, params, reference)
    _jumps(client, path, params, reference)


@pytest.mark.parametrize("context", CONTEXTS)
@pytest.mark.parametrize("sort", ["name", "-name", RANK, f"-{RANK}"])
def test_seek_starts_at_the_first_row_at_or_after_the_value(volume, context, sort):
    client, dataset = volume
    path = f"/api/v1/objects/{ITEM}"
    params = {**_context(context, dataset), "sort": sort}
    everything = _everything(client, path, params)
    field, descending = sort.removeprefix("-"), sort.startswith("-")

    def value(item: dict[str, Any]) -> Any:
        if field == "name":
            return item["name"]
        return next((a["value"] for a in item["attributes"] if a["attributeTypeKey"] == field), None)

    target = value(everything[len(everything) // 3])
    seek = str(target)
    expected = next(
        index
        for index, item in enumerate(everything)
        if value(item) is not None and (value(item) <= target if descending else value(item) >= target)
    )
    page = _get(client, path, {**params, "seek": seek, "pageSize": PAGE, "includeTotal": True})
    assert _ids(page["items"]) == _ids(everything[expected : expected + PAGE])
    assert page["startIndex"] == expected
    back = _get(client, path, {**params, "pageSize": PAGE, "cursor": page["prevCursor"]})
    assert _ids(back["items"]) == _ids(everything[max(0, expected - PAGE) : expected])


@pytest.mark.parametrize("context", CONTEXTS)
def test_top_level_lists_only_records_without_a_parent(volume, context):
    client, dataset = volume
    scope = _context(context, dataset)

    def total(object_type: str, **extra: Any) -> int:
        body = _get(client, f"/api/v1/objects/{object_type}", {**scope, "pageSize": 1, "includeTotal": True, **extra})
        return body["totalCount"]

    assert total(GROUP, topLevel=True) == total(GROUP) == dataset.shape.groups
    assert total(NODE) > 0 and total(NODE, topLevel=True) == 0
    assert total(ITEM) > 0 and total(ITEM, topLevel=True) == 0
    roots = _get(client, f"/api/v1/objects/{GROUP}", {**scope, "topLevel": True, "sort": "name", "pageSize": 5})
    assert all(item["parentObjectId"] is None for item in roots["items"])
    refused = _error(
        client,
        f"/api/v1/objects/{ITEM}",
        {**scope, "topLevel": True, "parentObjectId": dataset.heavy_group_id},
    )
    assert refused["code"] == "mutually_exclusive_scope"


@pytest.mark.parametrize("context", CONTEXTS)
def test_relations_search_sort_seek_and_page_in_every_context(volume, context):
    client, dataset = volume
    path = "/api/v1/relations"
    params = {**_context(context, dataset), "objectId": dataset.cited_group_id}
    by_name = _everything(client, path, {**params, "sort": "name"})
    names = [row["object"]["name"] for row in by_name]
    assert len(by_name) == dataset.shape.citations and names == sorted(names)
    descending = _everything(client, path, {**params, "sort": "-name"})
    assert [row["object"]["name"] for row in descending] == names[::-1]
    _walk(client, path, {**params, "sort": "name"}, _ids(by_name))

    target = names[len(names) // 2]
    seeked = _get(client, path, {**params, "sort": "name", "seek": target, "pageSize": 3, "includeTotal": True})
    assert seeked["items"][0]["object"]["name"] == target
    assert seeked["startIndex"] == names.index(target)

    # Search covers the related record's name and its searchable fields (here the code).
    def code(row: dict[str, Any]) -> str:
        return next(a["value"] for a in row["object"]["attributes"] if a["attributeTypeKey"] == CODE)

    by_code = code(by_name[3])
    found = _everything(client, path, {**params, "search": by_code.lower(), "sort": "name"})
    assert _ids(found) == [row["relation"]["id"] for row in by_name if by_code.lower() in code(row).lower()]
    fragment = names[5][-4:]
    found = _everything(client, path, {**params, "search": fragment, "sort": "-name"})
    expected = [
        row
        for row in descending
        if fragment.casefold() in row["object"]["name"].casefold()
        or fragment.casefold() in code(row).casefold()
    ]
    assert found and _ids(found) == _ids(expected)

    created = client.get(path, params={**params, "sort": "-createdAt"})
    if context == "live":
        assert created.status_code == 200, created.text
        assert len(created.json()["items"]) == len(by_name)
    else:
        assert created.status_code == 422
        assert created.json()["error"]["code"] == "invalid_sort"
    assert _error(client, path, {**params, "sort": "size"})["code"] == "invalid_sort"
    assert _error(client, path, {**params, "seek": "Item"})["code"] == "invalid_seek"


@pytest.mark.parametrize("context", CONTEXTS)
def test_page_selection_and_cursor_binding_are_refused_explicitly(volume, context):
    client, dataset = volume
    path = f"/api/v1/objects/{ITEM}"
    params = {**_context(context, dataset), "sort": "name", "pageSize": PAGE}
    first = _get(client, path, params)
    for extra, parameters in (
        ({"cursor": first["nextCursor"], "position": 3}, ["cursor", "position"]),
        ({"cursor": first["nextCursor"], "from": "end"}, ["cursor", "from"]),
        ({"seek": "Item", "position": 3}, ["position", "seek"]),
    ):
        error = _error(client, path, {**params, **extra})
        assert error["code"] == "conflicting_page_parameters"
        assert error["details"]["parameters"] == parameters
    # Cursors stay bound to their filters, whichever direction they point.
    for cursor in (first["nextCursor"], first["anchor"]):
        error = _error(client, path, {**params, "search": "Item", "cursor": cursor})
        assert error["code"] == "invalid_cursor"
    assert _error(client, path, {**params, "position": -1})["code"] == "request_validation_error"
    if context == "live":
        # The default live order is the internal sequence, which has no public value to seek by.
        default = {key: value for key, value in params.items() if key != "sort"}
        assert _error(client, path, {**default, "seek": "Item"})["code"] == "invalid_seek"
    assert _error(client, path, {**params, "sort": RANK, "seek": "high"})["code"] == "invalid_seek"


@pytest.mark.parametrize("context", ["live", "draft"])
def test_cursor_reads_neither_repeat_nor_skip_across_a_concurrent_insert(volume, context):
    client, dataset = volume
    path = f"/api/v1/objects/{ITEM}"
    scope = _context(context, dataset)
    params = {**scope, "parentObjectId": dataset.heavy_group_id, "sort": "name", "pageSize": PAGE}
    reference = _ids(_everything(client, path, params))
    first = _get(client, path, params)
    second = _get(client, path, {**params, "cursor": first["nextCursor"]})

    created = []
    for name in ("Item 000000 inserted before", "Item 999999 inserted after"):
        body: dict[str, Any] = {
            "applicationKey": "vol-catalogue",
            "objectTypeKey": ITEM,
            "parentObjectId": dataset.heavy_group_id,
            "name": f"{name} ({context})",
            "attributes": [{"attributeTypeKey": CODE, "value": f"PAGING-{context}-{len(created)}"}],
        }
        if context == "live":
            body["workspaceKey"] = WORKSPACE
        else:
            draft = client.get(f"/api/v1/workspace-drafts/{dataset.draft_id}").json()
            body |= {"workspaceDraftId": dataset.draft_id, "expectedWorkspaceDraftVersion": draft["version"]}
        response = client.post("/api/v1/objects", json=body)
        assert response.status_code == 201, response.text
        created.append(response.json()["id"])

    seen, cursor = _ids(first["items"]) + _ids(second["items"]), second["nextCursor"]
    while cursor is not None:
        body = _get(client, path, {**params, "cursor": cursor})
        seen.extend(_ids(body["items"]))
        cursor = body["nextCursor"]
    # The row inserted behind the reader is not revisited; the one ahead is reached once.
    assert seen == reference + [created[1]]
    # Walking back from the second page reaches the insert before the first page.
    back = _get(client, path, {**params, "cursor": second["prevCursor"], "pageSize": PAGE + 1})
    assert _ids(back["items"]) == [created[0], *reference[:PAGE]]
