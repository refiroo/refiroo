"""Base 0.8 A2, A3b: relation matrix row state filters over the generated volume fixture.

The filter reads stored cell states (A3b; before it, D12's walk down from the selected column
records); a page's cells are resolved walking up from each related record, and are the oracle. Over every row of the generated matrices, in each
context and both directions, a filtered list must hold exactly the rows whose unfiltered cells
show the state, and a deep filtered page must be the matching slice. Budgets are held with the
other volume reads in ``test_volume_baseline.py``.
"""

import pytest
from volume_fixture import (
    CELLS_BY_COLUMN,
    MARKS_BY_COLUMN,
    MATRIX_APPLICATION,
    WORKSPACE,
    scaled_shape,
    volume_app,
)

from app.services import relation_matrix

SHAPE = scaled_shape(0.01)
PATH = f"/api/v1/workspaces/{WORKSPACE}/relation-matrix"
STATES = ("one", "several", "inactive", "historyOnly", "none")


@pytest.fixture(scope="module")
def volume(_migrated_template, tmp_path_factory):
    with volume_app(_migrated_template, tmp_path_factory.mktemp("matrix-volume"), SHAPE) as value:
        yield value


def _context(context: str, dataset) -> dict[str, str]:
    if context == "change_set":
        return {"changeSetId": dataset.change_set_id}
    if context == "publication":
        return {"publicationId": dataset.publication_id}
    return {}


def _all_rows(client, params: dict) -> list[dict]:
    rows, cursor = [], None
    while True:
        response = client.get(PATH, params={**params, "pageSize": 100, **({"cursor": cursor} if cursor else {})})
        assert response.status_code == 200, response.text
        body = response.json()
        rows += body["items"]
        cursor = body["nextCursor"]
        if cursor is None:
            return rows


@pytest.mark.parametrize("view", [CELLS_BY_COLUMN, MARKS_BY_COLUMN])
@pytest.mark.parametrize("context", ["live", "change_set", "publication"])
def test_state_filter_matches_every_rows_cells(volume, context, view, monkeypatch):
    client, dataset = volume

    def derived(*_args, **_kwargs):
        raise AssertionError("the filter derived its cells instead of reading stored states")

    monkeypatch.setattr(relation_matrix, "_current_pairs", derived)
    columns = dataset.matrix_column_ids[:10]
    params = {
        "applicationKey": MATRIX_APPLICATION,
        "viewKey": view,
        "columnIds": columns,
        **_context(context, dataset),
    }
    rows = _all_rows(client, params)
    assert len(rows) == SHAPE.groups  # every group is a row; the S1 groups have empty cells
    states = {row["row"]["name"]: {cell["state"] for cell in row["cells"]} for row in rows}
    seen = set().union(*states.values())
    for state in STATES:
        expected = [name for name, held in states.items() if state in held]
        filtered = _all_rows(client, {**params, "state": state})
        assert [row["row"]["name"] for row in filtered] == expected, state
        if len(expected) > 4:
            position = len(expected) // 2
            response = client.get(
                PATH,
                params={**params, "state": state, "position": position, "pageSize": 3, "includeTotal": True},
            )
            body = response.json()
            assert (body["totalCount"], body["startIndex"]) == (len(expected), position), state
            assert [row["row"]["name"] for row in body["items"]] == expected[position : position + 3]

    # The generated data holds the states its shape promises in each context.
    history = {"historyOnly"} if context == "live" else set()
    if view == CELLS_BY_COLUMN:
        # One active cell per row and column at most: several never occurs; a tenth is inactive.
        assert seen == {"one", "inactive", "none"} | history
    else:
        # Read incoming, no condition applies; a cell marking two groups makes several.
        assert seen == {"one", "several", "none"} | history
