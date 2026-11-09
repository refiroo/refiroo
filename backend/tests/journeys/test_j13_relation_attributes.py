"""J13.12–J13.14 — The relationship's own values in views (USER_JOURNEYS.md, 0.13 RV).

A relationship carries the attributes its binding declares. J13.12: a matrix cell reads them back,
and a link or an edit through the matrix claims the relationship's version. J13.13: a relationships
table lists a binding's relationships with both ends and the values, filtered, sorted and paged in
SQL, live, in a change set and in a publication. J13.14: one request sets values on many
relationships, all or none.
"""

from uuid import uuid4

import pytest
from scenario import W1, ok, refused

MATRIX = ("R", "G", "M", "D", "Bown", "Bassoc", "Bnn.weight", "Bnn.note", "Massoc")
TABLE = ("H", "K", "Bnn", "Bnn.weight", "Bnn.note", "Vrt")


def _cell_record(world, row_id, column_id, **params):
    page = ok(
        world.api.get(
            f"/workspaces/{W1}/relation-matrix",
            applicationKey=world.key("A3"),
            viewKey=world.key("Massoc"),
            columnIds=[column_id],
            search="Link row",
            **params,
        )
    )
    row = next(item for item in page["items"] if item["row"]["id"] == row_id)
    return row["cells"][0]["records"]


def _cell(world, column):
    """A D record in ``column``, owned by a record of its own: a cell record the matrix can link."""
    owner = world.made("R", f"Owner {uuid4().hex[:6]}")
    cell = world.made(
        "D",
        f"Cell {uuid4().hex[:6]}",
        parent=world.dependant_parent(column["id"]),
        relations=[world.owner("Bown", owner["id"])],
    )
    return cell


@pytest.mark.journey("J13.12")
@pytest.mark.structures(*MATRIX)
def test_a_matrix_cell_reads_and_changes_the_relationships_values(world):
    """Given a matrix row and a cell record in a column. When the row is linked to the record with
    values and the matrix is read. Then the cell's record carries the relationship's values and
    version. When the values are changed with that version, a second change with the old version is
    refused with its code, and the matrix then shows the new values at the new version."""
    column = world.made("G", "Matrix column")
    row = world.made("R", "Link row")
    cell = _cell(world, column)
    weight, note = world.key("Bnn.weight"), world.key("Bnn.note")

    created = ok(
        world.relate("Bassoc", row["id"], cell["id"], {"Bnn.weight": 3, "Bnn.note": "first"}), 201
    )
    (shown,) = _cell_record(world, row["id"], column["id"])
    assert shown["relationId"] == created["id"] and shown["relationVersion"] == 1
    assert shown["relationAttributes"] == {weight: 3, note: "first"}

    path = f"/relations/{created['id']}"
    changed = ok(
        world.api.patch(path, {"attributes": {weight: 5, note: "second"}, "expectedVersion": 1})
    )
    assert changed["version"] == 2
    stale = refused(
        world.api.patch(path, {"attributes": {weight: 9}, "expectedVersion": 1}),
        409,
        "VERSION_CONFLICT",
    )
    assert stale["details"]["currentVersion"] == 2
    (after,) = _cell_record(world, row["id"], column["id"])
    assert after["relationVersion"] == 2 and after["relationAttributes"] == {
        weight: 5,
        note: "second",
    }


@pytest.mark.journey("J13.12")
@pytest.mark.structures(*MATRIX)
def test_a_matrix_in_a_change_set_shows_the_values_staged_there(world):
    """Given a linked cell record and an open change set. When the values are changed in the change
    set. Then the matrix read in the change set shows them and live still shows the old ones."""
    column = world.made("G", "Staged column")
    row = world.made("R", "Link row")
    cell = _cell(world, column)
    weight = world.key("Bnn.weight")
    created = ok(world.relate("Bassoc", row["id"], cell["id"], {"Bnn.weight": 1}), 201)
    change_set = world.change_set()

    staged = ok(
        world.api.patch(
            f"/relations/{created['id']}",
            {
                "attributes": {weight: 4},
                "expectedVersion": 1,
                "changeSetId": change_set["id"],
                "expectedChangeSetVersion": world.current(change_set)["version"],
            },
        )
    )
    (in_change_set,) = _cell_record(world, row["id"], column["id"], changeSetId=change_set["id"])
    assert in_change_set["relationAttributes"] == {weight: 4}
    assert in_change_set["relationVersion"] == staged["version"]
    (live,) = _cell_record(world, row["id"], column["id"])
    assert live["relationAttributes"] == {weight: 1}


def _table(world, **params):
    return world.api.get(
        f"/workspaces/{W1}/relations",
        applicationKey=world.app("H"),
        viewKey=world.key("Vrt"),
        **params,
    )


def _weights(page, world):
    return [row["attributes"].get(world.key("Bnn.weight")) for row in page["items"]]


@pytest.mark.journey("J13.13")
@pytest.mark.structures(*TABLE)
def test_a_relationships_table_filters_sorts_and_pages_in_every_context(world):
    """Given two H records related to K records with different values, one without a weight. When the
    view's rows are read filtered by a weight, sorted by weight descending and paged. Then each row
    names both ends, its relationship's version and values, the rows stand in H groups with their
    counts, records without a weight come last, a cursor and a position reach the same rows, and a
    change set and a publication read the same rows; a field the view does not declare is refused."""
    weight = world.key("Bnn.weight")
    a, b = world.made("H", "Zrt head a"), world.made("H", "Zrt head b")
    tokens = [world.made("K", f"Zrt token {i}") for i in range(1, 5)]
    plan = [(a, 0, 3), (a, 1, 2), (a, 2, 1), (a, 3, None), (b, 0, 5), (b, 1, 2)]
    relations = []
    for head, index, value in plan:
        values = {} if value is None else {"Bnn.weight": value, "Bnn.note": f"n{value}"}
        relations.append(ok(world.relate("Bnn", head["id"], tokens[index]["id"], values), 201))

    everything = ok(
        _table(world, search="Zrt ", sort=f"-relation:{weight}", pageSize=100, includeTotal=True)
    )
    assert _weights(everything, world) == [3, 2, 1, None, 5, 2] and everything["totalCount"] == 6
    first = everything["items"][0]
    assert first["source"]["id"] == a["id"] and first["target"]["id"] == tokens[0]["id"]
    assert first["relationVersion"] == 1 and first["attributes"][weight] == 3
    assert set(first["source"]["fields"]) == {"name", world.key("H.code")}
    assert set(first["target"]["fields"]) == {"name", world.key("K.code")}
    assert everything["groupCounts"] == {a["id"]: 4, b["id"]: 2}

    pages, cursor = [], None
    while True:
        page = ok(
            _table(world, search="Zrt ", sort=f"-relation:{weight}", pageSize=2, cursor=cursor)
        )
        pages.append(_weights(page, world))
        cursor = page["nextCursor"]
        if cursor is None:
            break
    assert pages == [[3, 2], [1, None], [5, 2]]
    third = ok(_table(world, search="Zrt ", sort=f"-relation:{weight}", pageSize=2, position=4))
    assert _weights(third, world) == [5, 2]

    equal = ok(_table(world, search="Zrt ", **{"filter__relation:" + weight + "__eq": 2}))
    assert sorted(row["source"]["id"] for row in equal["items"]) == sorted([a["id"], b["id"]])
    assert equal["groupCounts"] == {a["id"]: 1, b["id"]: 1}
    only_a = ok(_table(world, fromObjectId=a["id"], sort=f"relation:{weight}", pageSize=100))
    assert _weights(only_a, world) == [1, 2, 3, None]

    refused(_table(world, **{"filter__to:name__eq": "x"}), 422, "INVALID_FILTER")
    refused(_table(world, sort="relation:" + world.key("Bnn.note") + "x"), 422, "INVALID_SORT")
    refused(_table(world, relationTypeKey=world.key("Bnn")), 422, "RELATION_TABLE_BINDING_FIXED")

    change_set = world.change_set()
    ok(
        world.api.patch(
            f"/relations/{relations[3]['id']}",
            {
                "attributes": {weight: 8},
                "expectedVersion": 1,
                "changeSetId": change_set["id"],
                "expectedChangeSetVersion": world.current(change_set)["version"],
            },
        )
    )
    staged = ok(
        _table(
            world,
            search="Zrt ",
            sort=f"-relation:{weight}",
            pageSize=100,
            changeSetId=change_set["id"],
        )
    )
    assert _weights(staged, world) == [8, 3, 2, 1, 5, 2]
    assert _weights(
        ok(_table(world, search="Zrt ", sort=f"-relation:{weight}", pageSize=100)), world
    ) == [3, 2, 1, None, 5, 2]
    publication = world.publish(change_set)
    published = ok(
        _table(
            world,
            search="Zrt ",
            sort=f"-relation:{weight}",
            pageSize=100,
            publicationId=publication["id"],
        )
    )
    assert _weights(published, world) == [8, 3, 2, 1, 5, 2]
    assert published["groupCounts"] == {a["id"]: 4, b["id"]: 2}


def _batch(world, items, **extra):
    return world.api.post("/relations/batch", {"items": items, **extra})


@pytest.mark.journey("J13.14")
@pytest.mark.structures(*TABLE)
def test_values_are_set_on_many_relationships_at_once(world):
    """Given three relationships with values. When one request sets a weight on all three, and clears
    a note on one. Then each answers at its next version with the other values kept, the request
    answers in the order of its items, and the same request in a change set stages the values there
    while live keeps them."""
    weight, note = world.key("Bnn.weight"), world.key("Bnn.note")
    head = world.made("H", "Batch head")
    made = []
    for index in range(3):
        token = world.made("K", f"Batch token {index}")
        made.append(
            ok(
                world.relate(
                    "Bnn", head["id"], token["id"], {"Bnn.weight": 1, "Bnn.note": f"n{index}"}
                ),
                201,
            )
        )

    items = [
        {"id": made[i]["id"], "expectedVersion": 1, "attributes": {weight: 6}} for i in range(3)
    ]
    items[1]["attributes"][note] = None
    done = ok(_batch(world, items))
    assert [row["id"] for row in done["items"]] == [row["id"] for row in made]
    assert [row["version"] for row in done["items"]] == [2, 2, 2]
    assert [row["attributes"] for row in done["items"]] == [
        {weight: 6, note: "n0"},
        {weight: 6},
        {weight: 6, note: "n2"},
    ]
    assert ok(world.api.get(f"/relations/{made[1]['id']}"))["attributes"] == {weight: 6}

    change_set = world.change_set()
    staged_items = [
        {"id": row["id"], "expectedVersion": 2, "attributes": {weight: 9}} for row in made
    ]
    staged = ok(
        _batch(
            world,
            staged_items,
            changeSetId=change_set["id"],
            expectedChangeSetVersion=world.current(change_set)["version"],
        )
    )
    assert {row["attributes"][weight] for row in staged["items"]} == {9}
    assert ok(world.api.get(f"/relations/{made[0]['id']}"))["attributes"][weight] == 6


@pytest.mark.journey("J13.14")
@pytest.mark.structures(*TABLE)
def test_one_stale_or_invalid_item_refuses_the_whole_batch(world):
    """Given three relationships. When a batch holds a stale version, a value below the minimum and a
    good item. Then the request is refused naming each failing item by position and code, nothing is
    written, and a batch of the good items alone then succeeds."""
    weight = world.key("Bnn.weight")
    head = world.made("H", "Refusing head")
    made = [
        ok(
            world.relate(
                "Bnn", head["id"], world.made("K", f"Refusing token {i}")["id"], {"Bnn.weight": 2}
            ),
            201,
        )
        for i in range(3)
    ]
    ok(
        world.api.patch(
            f"/relations/{made[0]['id']}", {"attributes": {weight: 3}, "expectedVersion": 1}
        )
    )

    items = [
        {"id": made[0]["id"], "expectedVersion": 1, "attributes": {weight: 7}},
        {"id": made[1]["id"], "expectedVersion": 1, "attributes": {weight: 0}},
        {"id": made[2]["id"], "expectedVersion": 1, "attributes": {weight: 7}},
    ]
    error = refused(_batch(world, items), 409, "RELATION_BATCH_REFUSED")
    failed = {item["index"]: item["code"] for item in error["details"]["items"]}
    assert failed == {0: "VERSION_CONFLICT", 1: "ATTRIBUTE_BELOW_MINIMUM"}
    assert error["details"]["items"][0]["relationId"] == made[0]["id"]
    for row, expected in zip(made, (3, 2, 2), strict=True):
        assert ok(world.api.get(f"/relations/{row['id']}"))["attributes"][weight] == expected

    only_invalid = refused(_batch(world, items[1:2]), 422, "RELATION_BATCH_REFUSED")
    assert [item["code"] for item in only_invalid["details"]["items"]] == [
        "ATTRIBUTE_BELOW_MINIMUM"
    ]
    refused(_batch(world, [items[2], items[2]]), 422, "DUPLICATE_BATCH_ITEMS")
    good = ok(_batch(world, [items[2]]))
    assert good["items"][0]["attributes"][weight] == 7
