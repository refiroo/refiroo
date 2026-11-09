"""J13.12–J13.16 — The relationship's own values in views (USER_JOURNEYS.md, 0.13 RV, RG).

A relationship carries the attributes its binding declares. J13.12: a matrix cell reads them back,
and a link or an edit through the matrix claims the relationship's version. J13.13: a relationships
table lists a binding's relationships with both ends and the values, filtered, sorted and paged in
SQL, live, in a change set and in a publication. J13.14: one request sets values on many
relationships, all or none. J13.15: a relationships grid reads each record once with a column group per
related record. J13.16: one value set on the relationships a grid shows, counted first, all or none.
"""

from dataclasses import replace
from uuid import uuid4

import pytest
from scenario import W1, ok, refused

MATRIX = ("R", "G", "M", "D", "Bown", "Bassoc", "Bnn.weight", "Bnn.note", "Massoc")
TABLE = ("H", "K", "Bnn", "Bnn.weight", "Bnn.note", "Vrt")
GRID = ("H", "K", "Bnn", "Bnn.weight", "Bnn.note", "Vrg")


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


def _grid(world, **params):
    return world.api.get(
        f"/workspaces/{W1}/relation-grid",
        applicationKey=world.app("H"),
        viewKey=world.key("Vrg"),
        **params,
    )


def _grid_world(world):
    """Three H records and three K records; a is related to t1 (weight 3, a note) and t2 (weight 1),
    b to t1 (weight 2), c to none."""
    heads = [world.made("H", f"Grd head {name}") for name in "abc"]
    tokens = [world.made("K", f"Grd token {i}") for i in (1, 2, 3)]
    made = {
        ("a", 1): ok(
            world.relate(
                "Bnn", heads[0]["id"], tokens[0]["id"], {"Bnn.weight": 3, "Bnn.note": "n3"}
            ),
            201,
        ),
        ("a", 2): ok(world.relate("Bnn", heads[0]["id"], tokens[1]["id"], {"Bnn.weight": 1}), 201),
        ("b", 1): ok(world.relate("Bnn", heads[1]["id"], tokens[0]["id"], {"Bnn.weight": 2}), 201),
    }
    return heads, tokens, made


def _weight(row, token, weight):
    related = row["relations"].get(token["id"])
    return related["attributes"].get(weight) if related else "unlinked"


@pytest.mark.journey("J13.15")
@pytest.mark.structures(*GRID)
def test_a_relationships_grid_shows_each_record_once_with_its_related_records(world):
    """Given three H records and three K records, two H related to some K with weights. When the grid
    is read for those K and the chosen weight. Then every H is one row, linked or not, each row
    carries its relationships by K with the chosen value only, each K is a column group counting the
    rows related to it, a relationship filter keeps the rows that hold the value at a shown K, a K
    filter narrows the column groups, a sort on a relationship value falls back to the name, rows
    page by cursor, a change set marks what it stages as proposed, a publication reads the same, and
    a field or attribute the view does not declare is refused."""
    weight, note = world.key("Bnn.weight"), world.key("Bnn.note")
    _heads, tokens, made = _grid_world(world)
    picks = {"toObjectId": [token["id"] for token in tokens], "search": "Grd head"}

    page = ok(_grid(world, attribute=[weight], includeTotal=True, **picks))
    assert [row["source"]["name"] for row in page["items"]] == [f"Grd head {n}" for n in "abc"]
    assert page["rowTotal"] == 3 and page["columnTotal"] == 3
    assert [column["name"] for column in page["columns"]] == [f"Grd token {i}" for i in (1, 2, 3)]
    assert [column["linkedCount"] for column in page["columns"]] == [2, 1, 0]
    assert set(page["columns"][0]["fields"]) == {"name", world.key("K.code")}
    first, second, third = page["items"]
    assert [_weight(first, token, weight) for token in tokens] == [3, 1, "unlinked"]
    assert first["relations"][tokens[0]["id"]]["attributes"] == {weight: 3}
    assert first["relations"][tokens[0]["id"]]["relationId"] == made[("a", 1)]["id"]
    assert first["relations"][tokens[0]["id"]]["version"] == 1
    assert [_weight(second, token, weight) for token in tokens] == [2, "unlinked", "unlinked"]
    assert third["relations"] == {} and first["mappingVersion"] >= 1
    both = ok(_grid(world, **picks))["items"][0]["relations"][tokens[0]["id"]]["attributes"]
    assert both == {weight: 3, note: "n3"}

    descending = ok(_grid(world, sort="-from:name", pageSize=2, **picks))
    assert [row["source"]["name"] for row in descending["items"]] == ["Grd head c", "Grd head b"]
    rest = ok(_grid(world, sort="-from:name", pageSize=2, cursor=descending["nextCursor"], **picks))
    assert [row["source"]["name"] for row in rest["items"]] == ["Grd head a"]
    assert rest["nextCursor"] is None
    by_value = ok(_grid(world, sort=f"-relation:{weight}", **picks))
    assert [row["source"]["name"] for row in by_value["items"]] == [f"Grd head {n}" for n in "abc"]

    holds_two = ok(_grid(world, **picks, **{"filter__relation:" + weight + "__eq": 2}))
    assert [row["source"]["name"] for row in holds_two["items"]] == ["Grd head b"]
    assert holds_two["rowTotal"] == 1
    assert [column["linkedCount"] for column in holds_two["columns"]] == [1, 0, 0]
    elsewhere = ok(
        _grid(
            world,
            search="Grd head",
            toObjectId=[tokens[1]["id"]],
            **{"filter__relation:" + weight + "__eq": 2},
        )
    )
    assert elsewhere["items"] == [] and elsewhere["rowTotal"] == 0
    named = ok(_grid(world, search="Grd head", **{"filter__to:name__eq": "Grd token 2"}))
    assert [column["id"] for column in named["columns"]] == [tokens[1]["id"]]
    assert named["columnTotal"] == 1

    # The filters of the types' main views are the grid's too, shown as columns or not.
    code, token_code = world.value(_heads[0], "H.code"), world.value(tokens[1], "K.code")
    by_code = ok(_grid(world, **picks, **{"filter__from:" + world.key("H.code") + "__eq": code}))
    assert [row["source"]["name"] for row in by_code["items"]] == ["Grd head a"]
    by_token = ok(
        _grid(
            world, search="Grd head", **{"filter__to:" + world.key("K.code") + "__eq": token_code}
        )
    )
    assert [column["id"] for column in by_token["columns"]] == [tokens[1]["id"]]
    # The object list's operators, not only equality: on a record's field and on a relationship's value.
    contains = ok(
        _grid(world, **picks, **{"filter__from:" + world.key("H.code") + "__contains": code[1:-1]})
    )
    assert "Grd head a" in [row["source"]["name"] for row in contains["items"]]
    at_least = ok(_grid(world, **picks, **{"filter__relation:" + weight + "__gte": 2}))
    assert [row["source"]["name"] for row in at_least["items"]] == ["Grd head a", "Grd head b"]
    refused(
        _grid(world, **{"filter__relation:" + weight + "__contains": "1"}), 422, "INVALID_FILTER"
    )
    refused(
        _grid(world, **{"filter__from:" + world.key("H.rank") + "__eq": "1"}), 422, "INVALID_FILTER"
    )
    refused(_grid(world, **{"filter__from:" + note + "__eq": "x"}), 422, "INVALID_FILTER")
    refused(_grid(world, attribute=[world.key("H.code")]), 422, "INVALID_ATTRIBUTE")
    refused(_grid(world, sort="to:name"), 422, "INVALID_SORT")
    refused(
        world.api.get(
            f"/workspaces/{W1}/relation-grid",
            applicationKey=world.app("H"),
            viewKey=world.key("Vnn"),
        ),
        404,
        "RELATION_TABLE_NOT_FOUND",
    )
    refused(_grid(world, cursor="not-a-cursor", **picks), 422, "INVALID_CURSOR")

    change_set = world.change_set()
    ok(
        world.api.patch(
            f"/relations/{made[('a', 2)]['id']}",
            {
                "attributes": {weight: 9},
                "expectedVersion": 1,
                "changeSetId": change_set["id"],
                "expectedChangeSetVersion": world.current(change_set)["version"],
            },
        )
    )
    staged = ok(_grid(world, changeSetId=change_set["id"], attribute=[weight], **picks))
    row = staged["items"][0]
    assert row["relations"][tokens[1]["id"]]["attributes"] == {weight: 9}
    assert [
        related["proposed"] for item in staged["items"] for related in item["relations"].values()
    ] == [False, True, False]
    live = ok(_grid(world, attribute=[weight], **picks))["items"][0]
    assert live["relations"][tokens[1]["id"]]["attributes"] == {weight: 1}
    assert not live["relations"][tokens[1]["id"]]["proposed"]
    publication = world.publish(change_set)
    published = ok(_grid(world, publicationId=publication["id"], attribute=[weight], **picks))
    assert published["items"][0]["relations"][tokens[1]["id"]]["attributes"] == {weight: 9}
    assert not any(
        related["proposed"] for item in published["items"] for related in item["relations"].values()
    )


def _change(world, rows, columns, value, **extra):
    return world.api.post(
        "/relations/grid-change",
        {
            "applicationKey": world.app("H"),
            "viewKey": world.key("Vrg"),
            "toObjectIds": [token["id"] for token in columns],
            "attributeTypeKey": world.key("Bnn.weight"),
            "value": value,
            **({"fromObjectIds": [row["id"] for row in rows]} if rows is not None else {}),
            **extra,
        },
    )


def _weights_of(world, made):
    return {
        key: ok(world.api.get(f"/relations/{relation['id']}"))["attributes"].get(
            world.key("Bnn.weight")
        )
        for key, relation in made.items()
    }


@pytest.mark.journey("J13.16")
@pytest.mark.structures(*GRID)
def test_one_value_is_set_on_the_relationships_a_grid_shows(world):
    """Given the grid's relationships and one pair not related. When the change is counted and then
    applied for two ticked rows and two column records, with and without relating the missing pair.
    Then the dry run counts what changes, what already holds the value and what is missing, and
    writes nothing; the apply changes only what differs, at the next version, relates the missing pair
    only when asked, and every row the filters select is changed with allMatching; in a change set
    the values are staged and live keeps them."""
    weight = world.key("Bnn.weight")
    heads, tokens, made = _grid_world(world)
    rows, columns = heads[:2], tokens[:2]

    counted = ok(_change(world, rows, columns, 2, dryRun=True))
    assert counted == {
        "dryRun": True,
        "change": 2,
        "same": 1,
        "missing": 1,
        "linked": 0,
        "refused": [],
        "changeSetVersion": None,
    }
    assert _weights_of(world, made) == {("a", 1): 3, ("a", 2): 1, ("b", 1): 2}
    with_link = ok(_change(world, rows, columns, 2, dryRun=True, linkMissing=True))
    assert (with_link["change"], with_link["missing"], with_link["linked"]) == (2, 1, 1)

    done = ok(_change(world, rows, columns, 2))
    assert (done["change"], done["same"], done["linked"], done["dryRun"]) == (2, 1, 0, False)
    assert _weights_of(world, made) == {("a", 1): 2, ("a", 2): 2, ("b", 1): 2}
    assert ok(world.api.get(f"/relations/{made[('a', 1)]['id']}"))["version"] == 2
    assert ok(world.api.get(f"/relations/{made[('b', 1)]['id']}"))["version"] == 1
    note = ok(world.api.get(f"/relations/{made[('a', 1)]['id']}"))["attributes"][
        world.key("Bnn.note")
    ]
    assert note == "n3"

    linked = ok(_change(world, rows, columns, 4, linkMissing=True))
    assert (linked["change"], linked["same"], linked["linked"]) == (3, 0, 1)
    grid = ok(
        _grid(
            world,
            search="Grd head",
            toObjectId=[token["id"] for token in columns],
            attribute=[weight],
        )
    )
    assert [_weight(row, token, weight) for row in grid["items"][:2] for token in columns] == [
        4,
        4,
        4,
        4,
    ]

    left_out = ok(
        _change(
            world,
            None,
            tokens[:1],
            6,
            allMatching=True,
            search="Grd head",
            exceptObjectIds=[heads[1]["id"]],
            dryRun=True,
        )
    )
    assert (left_out["change"], left_out["missing"]) == (1, 1)
    by_operator = ok(
        _change(
            world,
            None,
            tokens[:1],
            6,
            allMatching=True,
            search="Grd head",
            filters=[
                {
                    "field": "from:" + world.key("H.code"),
                    "operator": "contains",
                    "value": world.value(heads[0], "H.code"),
                }
            ],
            dryRun=True,
        )
    )
    assert (by_operator["change"], by_operator["missing"]) == (1, 0)
    every = ok(_change(world, None, tokens[:1], 6, allMatching=True, search="Grd head"))
    assert (every["change"], every["same"], every["missing"]) == (2, 0, 1)
    assert (_weights_of(world, made)[("a", 1)], _weights_of(world, made)[("b", 1)]) == (6, 6)
    only_a = ok(
        _change(
            world,
            None,
            tokens[:1],
            7,
            allMatching=True,
            search="Grd head",
            filters=[{"field": "from:name", "value": "Grd head a"}],
        )
    )
    assert (only_a["change"], only_a["missing"]) == (1, 0)

    change_set = world.change_set()
    staged = ok(
        _change(
            world,
            rows,
            columns,
            8,
            changeSetId=change_set["id"],
            expectedChangeSetVersion=world.current(change_set)["version"],
        )
    )
    assert staged["change"] == 4 and staged["changeSetVersion"] > change_set["version"]
    in_change_set = ok(
        _grid(
            world,
            changeSetId=change_set["id"],
            search="Grd head",
            toObjectId=[token["id"] for token in columns],
            attribute=[weight],
        )
    )
    assert [
        _weight(row, token, weight) for row in in_change_set["items"][:2] for token in columns
    ] == [8] * 4
    assert all(
        related["proposed"]
        for row in in_change_set["items"][:2]
        for related in row["relations"].values()
    )
    assert _weights_of(world, made)[("a", 2)] == 4


@pytest.mark.journey("J13.16")
@pytest.mark.structures(*GRID)
def test_a_grid_change_is_refused_whole_and_says_why(world):
    """Given the grid's relationships. When a value below the attribute's minimum is counted and then
    applied, an attribute the binding does not declare, records of the wrong type, a stale
    change-set version, a selection naming both ways and a change larger than the limit are sent.
    Then the dry run lists each relationship it would refuse, the apply is refused with its code and
    nothing is written, and each other request is refused with its code."""
    heads, tokens, made = _grid_world(world)
    rows, columns = heads[:2], tokens[:2]
    before = _weights_of(world, made)

    dry = ok(_change(world, rows, columns, 0, dryRun=True))
    assert dry["change"] == 3 and len(dry["refused"]) == 3
    assert {item["code"] for item in dry["refused"]} == {"ATTRIBUTE_BELOW_MINIMUM"}
    assert {item["relationId"] for item in dry["refused"]} == {made[key]["id"] for key in made}
    error = refused(_change(world, rows, columns, 0), 422, "RELATION_BATCH_REFUSED")
    assert len(error["details"]["items"]) == 3
    linking = ok(_change(world, rows, columns, 0, dryRun=True, linkMissing=True))
    assert any(item["relationId"] is None and item["toObjectId"] for item in linking["refused"])
    assert _weights_of(world, made) == before

    refused(
        world.api.post(
            "/relations/grid-change",
            {
                "applicationKey": world.app("H"),
                "viewKey": world.key("Vrg"),
                "fromObjectIds": [rows[0]["id"]],
                "toObjectIds": [columns[0]["id"]],
                "attributeTypeKey": world.key("H.code"),
                "value": "x",
            },
        ),
        422,
        "INVALID_GRID_CHANGE",
    )
    refused(_change(world, rows, [rows[0]], 2), 422, "INVALID_GRID_CHANGE")
    refused(_change(world, [columns[0]], columns, 2), 422, "INVALID_GRID_CHANGE")
    refused(_change(world, rows, columns, "heavy"), 422, "INVALID_GRID_CHANGE")
    assert _change(world, rows, columns, 2, allMatching=True).status_code == 422
    assert _change(world, None, columns, 2).status_code == 422
    change_set = world.change_set()
    refused(
        _change(world, rows, columns, 2, changeSetId=change_set["id"]),
        409,
        "CHANGE_SET_REQUIRED",
    )
    refused(
        _change(
            world,
            rows,
            columns,
            2,
            changeSetId=change_set["id"],
            expectedChangeSetVersion=change_set["version"] + 5,
        ),
        409,
        "CHANGE_SET_VERSION_CONFLICT",
    )

    state = world.api.client.app.state
    saved = state.batch_limits
    state.batch_limits = replace(saved, atomic_max_items=1)
    try:
        error = refused(_change(world, rows, columns, 2), 413, "BATCH_TOO_LARGE")
        assert error["details"] == {"setting": "ATOMIC_JOB_MAX_ITEMS", "maximum": 1, "items": 2}
        refused(_change(world, rows, columns, 2, dryRun=True), 413, "BATCH_TOO_LARGE")
    finally:
        state.batch_limits = saved
    assert _weights_of(world, made) == before
