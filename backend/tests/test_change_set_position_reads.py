"""Base 0.8 S4R6: a change set position read resolves in its base's index and lands on the same row.

A change set lists its base rows less those its change set rows replace, plus its own rows. A position read
finds the base row at the position less the change set's own rows, then corrects for the change set rows
sorting before it (``pagination._locate``). The change sets here move rows across the order: renames to
the front, the back and the middle, new records at the front, and the fixture's tombstones. Every
landing is compared with a cursor walk of the whole list, on a publication base and a current-live
base, over a whole type and inside a parent, ascending, descending and by an attribute. The
full-volume time is recorded in the Base 0.8 plan.
"""

from typing import Any

import pytest
from volume_fixture import APPLICATION, CODE, ITEM, RANK, WORKSPACE, scaled_shape, volume_app
from wp8_support import attribute, create_change_set, create_object, update_object

from app.services import pagination

PAGE = 7


@pytest.fixture(scope="module")
def change_sets(_migrated_template, tmp_path_factory):
    """The fixture's publication-based change set and a current-live change set, both with rows moved."""
    with volume_app(
        _migrated_template, tmp_path_factory.mktemp("change-set-positions"), scaled_shape(0.01)
    ) as (client, dataset):
        current_live = create_change_set(client, WORKSPACE, source="currentLive").json()
        publication_based = client.get(f"/api/v1/change-sets/{dataset.change_set_id}").json()
        for change_set in (publication_based, current_live):
            _move_rows(client, change_set, dataset.heavy_group_id)
        yield client, dataset, {"publication": publication_based["id"], "currentLive": current_live["id"]}


def _move_rows(client, change_set: dict[str, Any], parent_id: str) -> None:
    params = {"changeSetId": change_set["id"], "sort": "name", "pageSize": 500}
    items = client.get(f"/api/v1/objects/{ITEM}", params=params).json()["items"]
    unedited = [item for item in items if "(edited)" not in item["name"]]
    renames = {
        unedited[-1]["id"]: "A moved to the front",
        unedited[-2]["id"]: "AA moved to the front",
        unedited[3]["id"]: "Zz moved to the back",
        unedited[5]["id"]: f"{unedited[len(unedited) // 2]['name']} moved to the middle",
    }
    by_id = {item["id"]: item for item in items}
    for object_id, name in renames.items():
        update_object(
            client,
            change_set,
            ITEM,
            object_id,
            payload={"name": name, "expectedVersion": by_id[object_id]["version"]},
        )
    for number in range(3):
        create_object(
            client,
            change_set,
            APPLICATION,
            ITEM,
            f"0 new at the front {number}",
            attributes=[attribute(CODE, f"NEW-{number}"), attribute(RANK, number)],
            parent_object_id=parent_id,
        )


def _get(client, params: dict[str, Any]) -> dict[str, Any]:
    response = client.get(f"/api/v1/objects/{ITEM}", params=params)
    assert response.status_code == 200, response.text
    return response.json()


def _reference(client, params: dict[str, Any]) -> list[str]:
    ids, cursor = [], None
    while True:
        body = _get(client, {**params, "pageSize": 500, **({"cursor": cursor} if cursor else {})})
        ids.extend(item["id"] for item in body["items"])
        cursor = body["nextCursor"]
        if cursor is None:
            return ids


@pytest.mark.parametrize("source", ["publication", "currentLive"])
@pytest.mark.parametrize("sort", ["name", "-name", RANK])
@pytest.mark.parametrize("scope", ["type", "parent"])
def test_change_set_position_reads_land_on_the_row_a_walk_reaches(change_sets, monkeypatch, source, sort, scope):
    client, dataset, change_set_ids = change_sets
    params = {"changeSetId": change_set_ids[source], "sort": sort}
    if scope == "parent":
        params["parentObjectId"] = dataset.heavy_group_id
    reference = _reference(client, params)
    assert len(reference) > 10 * PAGE

    located: list[tuple[int, bool]] = []
    resolve = pagination._locate

    def spy(session, overlay, position, **options):
        result = resolve(session, overlay, position, **options)
        located.append((position, result is not None))
        return result

    monkeypatch.setattr(pagination, "_locate", spy)
    size = len(reference)
    positions = sorted({0, 1, 2, 3, 4, 5, size // 2, size - PAGE, size - 1, size, size + 3, *range(0, size, 23)})
    for position in positions:
        body = _get(client, {**params, "pageSize": PAGE, "position": position, "includeTotal": True})
        landed = [item["id"] for item in body["items"]]
        assert landed == reference[position : position + PAGE], position
        assert (body["startIndex"], body["totalCount"]) == (min(position, size), size)
        if position < size:
            after = _get(client, {**params, "pageSize": PAGE, "cursor": body["nextCursor"]}) if body["nextCursor"] else None
            assert [item["id"] for item in (after or {"items": []})["items"]] == reference[position + PAGE : position + 2 * PAGE]
        if 0 < position <= size:
            before = _get(client, {**params, "pageSize": PAGE, "cursor": body["prevCursor"]})
            assert [item["id"] for item in before["items"]] == reference[max(0, position - PAGE) : position]
    # Every position read took the overlay path; beyond the change set's own rows, it resolved in the
    # base rather than falling back to an offset over the union.
    assert [position for position, _ in located] == positions
    assert all(resolved for position, resolved in located if size // 2 <= position < size)
