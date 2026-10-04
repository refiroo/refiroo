"""J16 — See and fill relationship coverage across ancestors (USER_JOURNEYS.md).

The matrices list R records as rows and G records as columns; a cell holds the row's related D
records whose nearest G ancestor is the column (``configurations.py``: ``Mown``, ``Massoc``,
``Mrev``, ``Mscope``, ``Mone``).
"""

from uuid import uuid4

import pytest
from scenario import W1, ok, refused

MATRIX = ("R", "R.u", "G", "M", "D", "D.active", "Bown", "Mown")


def _matrix(world, view, **params):
    return world.api.get(
        f"/workspaces/{W1}/relation-matrix",
        applicationKey=world.key("A3"),
        viewKey=world.key(view),
        **params,
    )


def _read(world, view, **params):
    return ok(_matrix(world, view, **params))


def _sub(world, path, view, **params):
    return world.api.get(
        f"/workspaces/{W1}/relation-matrix/{path}",
        applicationKey=world.key("A3"),
        viewKey=world.key(view),
        **params,
    )


def _cell(page, row_id, column_id):
    row = next(item for item in page["items"] if item["row"]["id"] == row_id)
    return next(cell for cell in row["cells"] if cell["columnId"] == column_id)


def _rows(page):
    return {item["row"]["id"] for item in page["items"]}


def _owned(world, row, g, *, active=True, name=None, parent=None, **extra):
    """A D record within ``g`` owned by ``row`` (a cell of the owned view)."""
    return world.made(
        "D",
        name or f"Cell {uuid4().hex[:6]}",
        parent=parent or world.dependant_parent(g["id"]),
        values={"D.active": active},
        relations=[world.owner("Bown", row["id"])],
        **extra,
    )


def _free(world, g, owner=None, *, active=True, name=None):
    """A D record within ``g`` owned by a record of its own: a candidate for the other views."""
    owner = owner or world.made("R", f"Owner {uuid4().hex[:6]}")
    return _owned(world, owner, g, active=active, name=name)


@pytest.mark.journey("J16")
@pytest.mark.structures(*MATRIX, "Massoc")
def test_read_the_matrix_filter_by_cell_state_and_fill_an_empty_cell(world):
    """Given the owned view with rows whose cells are filled, inactive or empty. When rows with an
    empty cell in two columns are listed. Then only those are listed, the total counts them, each row
    carries its set version and cells with state, counts and records; only a record meeting the
    condition fills a cell. When a record is created in the column's default container for an empty
    row. Then its cell is filled. Every malformed read is refused with its code."""
    g1, g2 = world.made("G", "Column one"), world.made("G", "Column two")
    rows = {name: world.made("R", f"Row {name}") for name in ("full", "half", "empty", "inactive")}
    # One container per column, so each column has one default place for a new record.
    in_g1, in_g2 = world.dependant_parent(g1["id"]), world.dependant_parent(g2["id"])
    _owned(world, rows["full"], g1, parent=in_g1)
    _owned(world, rows["full"], g2, parent=in_g2)
    _owned(world, rows["half"], g1, parent=in_g1)
    _owned(world, rows["inactive"], g1, active=False, parent=in_g1)
    _owned(world, rows["inactive"], g2, parent=in_g2)
    columns = [g1["id"], g2["id"]]

    page = _read(world, "Mown", columnIds=columns, state="none", includeTotal=True, search="Row ")
    assert _rows(page) == {rows["half"]["id"], rows["empty"]["id"]} and page["totalCount"] == 2
    every = _read(world, "Mown", columnIds=columns, search="Row ")
    for item in every["items"]:
        assert isinstance(item["relationSetVersion"], int)
        for cell in item["cells"]:
            assert {"state", "recordCount", "matchingCount", "records"} <= set(cell)
            assert len(cell["records"]) <= 5
    assert _cell(every, rows["full"]["id"], g1["id"])["state"] == "one"
    inactive = _cell(every, rows["inactive"]["id"], g1["id"])
    assert inactive["state"] == "inactive" and inactive["matchingCount"] == 0

    containers = ok(_sub(world, "containers", "Mown", columnId=g1["id"]))
    default = containers["defaultContainerId"]
    assert default == in_g1
    _owned(world, rows["empty"], g1, parent=default)
    filled = _read(world, "Mown", columnIds=columns, search="Row ")
    assert _cell(filled, rows["empty"]["id"], g1["id"])["state"] == "one"
    only_g1 = _read(world, "Mown", columnIds=[g1["id"]], state="none", search="Row ")
    assert rows["empty"]["id"] not in _rows(only_g1)

    unknown = world.api.get(
        f"/workspaces/{W1}/relation-matrix", applicationKey=world.key("A3"), viewKey="no-such-view"
    )
    refused(unknown, 404, "RELATION_MATRIX_VIEW_NOT_FOUND")
    elsewhere = world.api.get(
        f"/workspaces/{W1}/relation-matrix", applicationKey="no-such-application", viewKey="any"
    )
    refused(elsewhere, 404, "UNKNOWN_APPLICATION")
    refused(_matrix(world, "Mown", state="none"), 422, "RELATION_MATRIX_STATE_REQUIRES_COLUMNS")
    refused(
        _matrix(world, "Mown", columnIds=[str(uuid4()) for _ in range(21)]), 422, "TOO_MANY_COLUMNS"
    )
    refused(_matrix(world, "Mown", columnIds=[g1["id"], g1["id"]]), 422, "DUPLICATE_COLUMN_IDS")
    refused(
        _matrix(world, "Mown", columnIds=[g1["id"]], columnCursor="anything"),
        422,
        "CONFLICTING_COLUMN_PARAMETERS",
    )
    refused(
        _matrix(world, "Mown", columnIds=[rows["full"]["id"]]),
        404,
        "RELATION_MATRIX_COLUMN_NOT_FOUND",
    )
    refused(
        _matrix(world, "Mown", parentObjectId=str(uuid4())), 404, "RELATION_MATRIX_PARENT_NOT_FOUND"
    )
    refused(
        _matrix(world, "Mown", parentObjectId=g1["id"]),
        422,
        "RELATION_MATRIX_PARENT_SCOPE_MISMATCH",
    )
    refused(
        _sub(world, "containers", "Massoc", columnId=g1["id"]),
        422,
        "RELATION_MATRIX_ACTION_NOT_ALLOWED",
    )
    refused(
        _sub(world, "link-candidates", "Massoc", columnId=g1["id"], rowId=str(uuid4())),
        404,
        "RELATION_MATRIX_ROW_NOT_FOUND",
    )


@pytest.mark.journey("J16")
@pytest.mark.structures(*MATRIX, "Bassoc", "Massoc")
def test_edit_or_remove_from_a_filled_cell(world):
    """Given a row's filled cell with record d. When d's cell fields are changed with its version,
    then the row is unlinked from it claiming the row's set. Then the cell shows the new value; after
    unlinking it is empty and the row's set version advanced; a stale set claim is refused."""
    g = world.made("G", "Column")
    row = world.made("R", "Row editable")
    d = _free(world, g, name="Editable")
    ok(world.relate("Bassoc", row["id"], d["id"]), 201)
    page = _read(world, "Massoc", columnIds=[g["id"]], search="Row editable")
    (record,) = _cell(page, row["id"], g["id"])["records"]
    version = page["items"][0]["relationSetVersion"]

    ok(world.update("D", record["id"], record["version"], values={"K.code": "EDITED"}))
    edited = _cell(
        _read(world, "Massoc", columnIds=[g["id"]], search="Row editable"), row["id"], g["id"]
    )
    assert edited["records"][0]["fields"][world.key("K.code")] == "EDITED"

    path = f"/relations/{record['relationId']}"
    stale = world.api.delete(
        path,
        expectedVersion=record["relationVersion"],
        expectedRelationSetVersion=version - 1,
        relationSetDirection="outgoing",
    )
    refused(stale, 409, "RELATION_SET_VERSION_CONFLICT")
    removed = world.api.delete(
        path,
        expectedVersion=record["relationVersion"],
        expectedRelationSetVersion=version,
        relationSetDirection="outgoing",
    )
    assert removed.status_code == 204, removed.text
    after = _read(world, "Massoc", columnIds=[g["id"]], search="Row editable")
    assert _cell(after, row["id"], g["id"])["state"] == "none"
    assert after["items"][0]["relationSetVersion"] == version + 1


@pytest.mark.journey("J16.1")
@pytest.mark.structures(
    *MATRIX, "Bassoc", "Massoc", "Brev", "Mrev", "Bscope", "Mscope", "Bone", "Mone"
)
def test_fill_a_cell_through_each_binding_shape(world):
    """Given the owned, association and reverse many-to-many views. When a cell is filled in each:
    created in the owned view, linked from the candidates in the others. Then each cell is filled; in
    the reverse view every record meets the condition and a cell with several records is no conflict;
    the candidates list ineligible records with their reason, and the totals count them."""
    g = world.made("G", "Column")
    row, other = world.made("R", "Row shaped"), world.made("R", "Row other")
    columns = [g["id"]]
    _owned(world, row, g)
    assert (
        _cell(_read(world, "Mown", columnIds=columns, search="Row shaped"), row["id"], g["id"])[
            "state"
        ]
        == "one"
    )

    candidate = _free(world, g, name="Candidate")
    version = _read(world, "Massoc", columnIds=columns, search="Row shaped")["items"][0][
        "relationSetVersion"
    ]
    listed = ok(
        _sub(
            world,
            "link-candidates",
            "Massoc",
            columnId=g["id"],
            rowId=row["id"],
            includeTotal=True,
            pageSize=100,
        )
    )
    assert candidate["id"] in {item["id"] for item in listed["items"] if item["eligible"]}
    ok(
        world.relate(
            "Bassoc",
            row["id"],
            candidate["id"],
            expectedRelationSetVersion=version,
            relationSetDirection="outgoing",
        ),
        201,
    )
    assert (
        _cell(_read(world, "Massoc", columnIds=columns, search="Row shaped"), row["id"], g["id"])[
            "state"
        ]
        == "one"
    )
    again = ok(
        _sub(
            world,
            "link-candidates",
            "Massoc",
            columnId=g["id"],
            rowId=row["id"],
            includeTotal=True,
            pageSize=100,
        )
    )
    reasons = {item["id"]: item.get("reason") for item in again["items"]}
    assert reasons[candidate["id"]] == "alreadyLinked" and again["totalCount"] == len(
        again["items"]
    )

    inactive = _free(world, g, active=False, name="Inactive candidate")
    for d in (candidate, inactive):
        ok(world.relate("Brev", d["id"], row["id"]), 201)
    reverse = _cell(
        _read(world, "Mrev", columnIds=columns, search="Row shaped"), row["id"], g["id"]
    )
    assert reverse["state"] == "several" and reverse["conflict"] is False
    assert all(record["meetsCondition"] for record in reverse["records"])

    ok(world.relate("Bscope", row["id"], candidate["id"]), 201)
    rival = _free(world, g, name="Rival")
    scoped = ok(
        _sub(world, "link-candidates", "Mscope", columnId=g["id"], rowId=row["id"], pageSize=100)
    )
    assert {item["id"]: item.get("reason") for item in scoped["items"]}[rival["id"]] == "scopeTaken"

    ok(world.relate("Bone", row["id"], candidate["id"]), 201)
    pinned = ok(
        _sub(world, "link-candidates", "Mone", columnId=g["id"], rowId=row["id"], pageSize=100)
    )
    assert {item.get("reason") for item in pinned["items"] if item["id"] != candidate["id"]} == {
        "rowCardinality"
    }
    for_other = ok(
        _sub(world, "link-candidates", "Mone", columnId=g["id"], rowId=other["id"], pageSize=100)
    )
    assert {item["id"]: item.get("reason") for item in for_other["items"]}[
        candidate["id"]
    ] == "candidateCardinality"


@pytest.mark.journey("J16.2")
@pytest.mark.structures(*MATRIX)
def test_columns_several_levels_above_the_related_record(world):
    """Given column g1 with containers M1 and M2 between it and its records. When its containers are
    listed, a record is created under M2 and the matrix read. Then the containers are listed in path
    order with no default (several); the new record fills g1's cell; a column with one container
    names it as the default."""
    g1 = world.made("G", "Deep column")
    m1 = world.made("M", "Container one", parent=g1["id"])
    m2 = world.made("M", "Container two", parent=g1["id"])
    row = world.made("R", "Row deep")

    containers = ok(_sub(world, "containers", "Mown", columnId=g1["id"]))
    listed = [item["id"] for item in containers["items"]]
    assert [i for i in listed if i in (m1["id"], m2["id"])] == [m1["id"], m2["id"]]
    assert containers["defaultContainerId"] is None
    _owned(world, row, g1, parent=m2["id"])
    assert (
        _cell(_read(world, "Mown", columnIds=[g1["id"]], search="Row deep"), row["id"], g1["id"])[
            "state"
        ]
        == "one"
    )

    g2 = world.made("G", "Single column")
    only = world.dependant_parent(g2["id"])
    assert ok(_sub(world, "containers", "Mown", columnId=g2["id"]))["defaultContainerId"] == only


@pytest.mark.journey("J16.3")
@pytest.mark.structures(*MATRIX)
def test_fill_in_a_change_set_and_publish(world):
    """Given a change set. When a cell record is created in it, the matrix read there and live, and
    the change set published. Then the cell is filled in the change set, empty live until publishing,
    then filled. A second matching record staged in the same scope shows as a conflict, validation
    reports it and publishing is refused, leaving the change set."""
    g = world.made("G", "Staged column")
    row = world.made("R", "Row staged")
    parent = world.dependant_parent(g["id"])
    cs = world.change_set()
    _owned(world, row, g, parent=parent, change_set=world.current(cs))
    staged = _read(world, "Mown", columnIds=[g["id"]], search="Row staged", changeSetId=cs["id"])
    assert _cell(staged, row["id"], g["id"])["state"] == "one"
    live = _read(world, "Mown", columnIds=[g["id"]], search="Row staged")
    assert _cell(live, row["id"], g["id"])["state"] == "none"
    world.publish(cs)
    live = _read(world, "Mown", columnIds=[g["id"]], search="Row staged")
    assert _cell(live, row["id"], g["id"])["state"] == "one"

    second = world.change_set()
    _owned(world, row, g, parent=parent, change_set=world.current(second))
    cell = _cell(
        _read(world, "Mown", columnIds=[g["id"]], search="Row staged", changeSetId=second["id"]),
        row["id"],
        g["id"],
    )
    assert cell["state"] == "several" and cell["conflict"] is True
    validation = ok(world.api.post(f"/change-sets/{second['id']}/validation"))
    assert validation["valid"] is False
    assert "DUPLICATE_RELATION_SCOPE" in {d.get("code") for d in validation["diagnostics"]}
    body = {
        "expectedChangeSetVersion": world.current(second)["version"],
        "expectedActivePublicationId": _active(world),
    }
    refused(
        world.api.post(f"/change-sets/{second['id']}/publication", body),
        422,
        "WORKSPACE_GRAPH_INVALID",
    )
    assert world.current(second)["id"] == second["id"]


def _active(world):
    items = ok(world.api.get(f"/workspaces/{W1}/publications", pageSize=1))["items"]
    return items[0]["id"] if items and items[0]["status"] == "active" else None


@pytest.mark.journey("J16.4")
@pytest.mark.structures(*MATRIX)
def test_read_the_matrix_in_a_publication(world):
    """Given a publication P0 with a filled cell, P1 after the record was removed, and a live cell
    write after P1. When the matrix is read in P1. Then it holds P1's content at set version 0
    without the live write, and the emptied cell names P0 as where the record was last held."""
    g1, g2 = world.made("G", "History column"), world.made("G", "Later column")
    row = world.made("R", "Row history")
    d = _owned(world, row, g1)
    p0 = world.publish(world.change_set())
    preview = refused(
        world.api.delete(f"/objects/{world.key('D')}/{d['id']}", expectedVersion=d["version"]),
        409,
        "OBJECT_HAS_DEPENDANTS",
    )
    gone = world.api.delete(
        f"/objects/{world.key('D')}/{d['id']}",
        expectedVersion=d["version"],
        cascade=True,
        deletionPreviewToken=preview["details"]["deletionPreviewToken"],
    )
    assert gone.status_code == 204, gone.text
    p1 = world.publish(world.change_set())
    _owned(world, row, g2)

    page = _read(
        world, "Mown", columnIds=[g1["id"], g2["id"]], search="Row history", publicationId=p1["id"]
    )
    assert page["items"][0]["relationSetVersion"] == 0
    assert _cell(page, row["id"], g2["id"])["state"] == "none"
    history = _cell(page, row["id"], g1["id"])
    assert history["state"] == "historyOnly"
    assert history["publication"] == {"id": p0["id"], "number": p0["publicationNumber"]}


@pytest.mark.journey("J16.5")
@pytest.mark.structures(*MATRIX)
def test_a_cell_filled_live_after_it_was_staged(world):
    """Given a change set that staged a matching record for row r in column g1. When live fills the
    same cell with another matching record, then the change set is published. Then publishing is
    refused, no publication is created, and the change set and the live cell stay as they are.
    (The catalogue names no code; API.md allows a changed-set conflict or an invalid merged graph.)"""
    g1 = world.made("G", "Contested column")
    row = world.made("R", "Row contested")
    parent = world.dependant_parent(g1["id"])
    cs = world.change_set()
    _owned(world, row, g1, parent=parent, change_set=world.current(cs))
    live = _owned(world, row, g1, parent=parent)
    publications = ok(world.api.get(f"/workspaces/{W1}/publications"))["items"]

    body = {
        "expectedChangeSetVersion": world.current(cs)["version"],
        "expectedActivePublicationId": _active(world),
    }
    response = world.api.post(f"/change-sets/{cs['id']}/publication", body)
    assert (response.status_code, response.json()["error"]["code"]) in {
        (409, "VERSION_CONFLICT"),
        (422, "WORKSPACE_GRAPH_INVALID"),
    }, response.text
    assert ok(world.api.get(f"/workspaces/{W1}/publications"))["items"] == publications
    cell = _cell(
        _read(world, "Mown", columnIds=[g1["id"]], search="Row contested"), row["id"], g1["id"]
    )
    assert cell["state"] == "one" and [r["id"] for r in cell["records"]] == [live["id"]]


@pytest.mark.journey("J16.6")
@pytest.mark.structures(*MATRIX, "Bassoc", "Massoc", "Bscope", "Mscope")
def test_two_relationships_racing_into_one_cell(world):
    """Given actors A and B each linking a different record to row r in column g1 without a set
    claim, both in flight at once. Then in the association view both are linked and the cell lists as
    several; in the scoped view one is linked, the other refused, and the cell lists as one."""
    g1 = world.made("G", "Raced column")
    row = world.made("R", "Row raced")
    first, second = _free(world, g1, name="First"), _free(world, g1, name="Second")

    both = world.race(
        W1, *(lambda d=d: world.relate("Bassoc", row["id"], d["id"]) for d in (first, second))
    )
    assert [r.status_code for r in both] == [201, 201]
    columns = {"columnIds": [g1["id"]], "search": "Row raced"}
    assert row["id"] in _rows(_read(world, "Massoc", state="several", **columns))
    assert row["id"] not in _rows(_read(world, "Massoc", state="one", **columns))

    one = world.race(
        W1, *(lambda d=d: world.relate("Bscope", row["id"], d["id"]) for d in (first, second))
    )
    assert sorted(r.status_code for r in one) == [201, 409]
    refused(next(r for r in one if r.status_code == 409), 409, "DUPLICATE_RELATION_SCOPE")
    assert row["id"] in _rows(_read(world, "Mscope", state="one", **columns))


@pytest.mark.journey("J16.7")
@pytest.mark.structures(*MATRIX)
def test_a_related_record_moved_to_another_column(world):
    """Given row r with record d in a container under g1 and an empty g2 cell. When d's container
    moves to g2. Then g1's cell is empty and g2's filled, and the state filter agrees; when r already
    held a matching record in g2, the move is refused naming it and nothing moves."""
    g1, g2 = world.made("G", "From column"), world.made("G", "To column")
    row = world.made("R", "Row moving")
    container = world.made("M", "Moving container", parent=g1["id"])
    _owned(world, row, g1, parent=container["id"])
    ok(world.update("M", container["id"], container["version"], parent=g2["id"]))
    columns = [g1["id"], g2["id"]]
    page = _read(world, "Mown", columnIds=columns, search="Row moving")
    assert _cell(page, row["id"], g1["id"])["state"] == "none"
    assert _cell(page, row["id"], g2["id"])["state"] == "one"
    assert row["id"] in _rows(
        _read(world, "Mown", columnIds=[g1["id"]], state="none", search="Row moving")
    )

    g3 = world.made("G", "Taken column")
    held = _owned(world, row, g3)
    moved = world.record("M", container["id"])
    error = refused(
        world.update("M", container["id"], moved["version"], parent=g3["id"]),
        409,
        "DUPLICATE_RELATION_SCOPE",
    )
    assert error["details"]["conflictingObjectId"] == held["id"]
    assert world.record("M", container["id"])["parentObjectId"] == g2["id"]
