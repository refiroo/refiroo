"""Track S read baseline (Base 0.8 S1) over the volume fixture.

Runs the same requests in live, change set and history contexts and records, per request, the wall time
inside the ASGI app, the SQL statements executed and the ORM rows materialised. The pytest module
``test_volume_baseline.py`` uses :func:`run_scenarios` at small scales to hold the budgets; run
this file directly for the full-volume figures recorded in the Base 0.8 plan::

    cd backend && .venv/bin/python tests/volume_baseline.py --scale 1 --repeat 5

Middle and last pages are reached with a cursor built by the production query and cursor code, as
a client scrolling there would hold one; S3 adds position, end, backward and seek reads beside them.
"""

import argparse
import json
import os
import platform
import statistics
import sys
import tempfile
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sqlalchemy import event, func, select, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

sys.path.insert(0, str(Path(__file__).resolve().parent))

from volume_fixture import (
    APPLICATION,
    AS_OF,
    CELLS_BY_COLUMN,
    CITING,
    CODE,
    CONSUMER_API,
    GROUP,
    GROUP_CONTAINS_ITEM,
    GROUP_HAS_CELL,
    GROUP_PARENT,
    ITEM,
    ITEM_CITES_GROUP,
    ITEMS_BY_GROUP,
    MARKS_BY_COLUMN,
    MATRIX_APPLICATION,
    NODE,
    NODE_HAS_CHILD,
    RANK,
    RANKED_ITEMS,
    SHELF,
    WITHIN_GROUP,
    WORKSPACE,
    ReviewChangeSet,
    VolumeDataset,
    feed_publication_position,
    measure,
    scaled_shape,
    seed_review_change_set,
    volume_app,
    volume_model,
)

PAGE_SIZE = 20
# The wide page a table read before 0.11 X6 (D156), measured beside the reader's page.
WIDE_PAGE = 200
CONTEXTS = ("live", "change_set", "history")


@dataclass(frozen=True)
class Measurement:
    context: str
    scenario: str
    status: int
    milliseconds: float  # median over the timed runs
    statements: int
    rows_loaded: int


def context_params(context: str, dataset: VolumeDataset) -> dict[str, str]:
    if context == "live":
        return {"workspaceKey": WORKSPACE}
    if context == "change_set":
        return {"changeSetId": dataset.change_set_id}
    return {"publicationId": dataset.publication_id}


def object_cursor(
    engine: Engine,
    context: str,
    dataset: VolumeDataset,
    *,
    parent: str | None,
    offset: int,
    direction: str = "after",
) -> tuple[str, int]:
    """A name-sorted item cursor at row ``offset`` (one-based), and the list's length.

    The cursor is the one the endpoint itself would have issued for that row in ``direction``.
    """
    from app.common.cursors import encode_cursor
    from app.common.pagination import _row_position, cursor_sort
    from app.engine.model.compiler import parse_model
    from app.engine.reads.object_query import build_object_query
    from app.engine.reads.snapshot_reads import (
        build_snapshot_object_query,
        change_set_context,
        object_scope,
        publication_context,
    )

    model = parse_model(volume_model())
    with Session(engine) as session:
        options = {
            "object_type_key": ITEM,
            "application_key": None,
            "parent_object_id": parent,
            "search": None,
            "sort": "name",
            "field_filters": [],
        }
        if context == "live":
            query = build_object_query(model, workspace_key=WORKSPACE, **options)
            scope = "objects"
        else:
            snapshot = (
                change_set_context(session, dataset.change_set_id)
                if context == "change_set"
                else publication_context(session, dataset.publication_id)
            )
            query = build_snapshot_object_query(model, snapshot, **options)
            scope = object_scope(snapshot)
        total = session.scalar(select(func.count()).select_from(query.statement.subquery()))
        ordered = query.statement.order_by(*(key.column for key in query.keys))
        row = session.execute(ordered.offset(max(offset - 1, 0)).limit(1)).one()
        record = row[0] if context == "live" else row
        position = _row_position(session, query.keys, record)
        return (
            encode_cursor(
                position,
                scope=scope,
                sort=cursor_sort(query.keys),
                filters=query.filters,
                direction=direction,
            ),
            total,
        )


def _matrix_scenarios(
    client, context: str, dataset: VolumeDataset
) -> list[tuple[str, str, dict[str, Any]]]:
    """Base 0.8 A2: relation matrix pages, whole and filtered by a cell state.

    A filtered jump lands a quarter into the filtered rows, so the page is full and not the last
    at every scale: an edge page costs a different number of statements.
    """
    path = f"/api/v1/workspaces/{WORKSPACE}/relation-matrix"
    base = {
        key: value for key, value in context_params(context, dataset).items() if key != "workspaceKey"
    }
    outgoing = {**base, "applicationKey": MATRIX_APPLICATION, "viewKey": CELLS_BY_COLUMN, "pageSize": PAGE_SIZE}
    incoming = {**outgoing, "viewKey": MARKS_BY_COLUMN}
    columns = dataset.matrix_column_ids

    def quarter(params: dict[str, Any]) -> dict[str, Any]:
        response = client.get(path, params={**params, "includeTotal": True})
        assert response.status_code == 200, response.text
        return {**params, "position": response.json()["totalCount"] // 4, "includeTotal": True}

    return [
        ("matrix: first page, 20 columns, total", path, {**outgoing, "includeTotal": True}),
        ("matrix: position ¾ deep, total", path, {**outgoing, "position": dataset.shape.groups * 3 // 4, "includeTotal": True}),
        (
            "matrix: inactive in 10 columns, jump, total",
            path,
            quarter({**outgoing, "columnIds": columns[:10], "state": "inactive"}),
        ),
        (
            "matrix: none in 3 columns, jump, total",
            path,
            quarter({**outgoing, "columnIds": columns[:3], "state": "none"}),
        ),
        (
            "matrix: history only in 20 columns",
            path,
            {**outgoing, "columnIds": columns[:20], "state": "historyOnly"},
        ),
        ("matrix incoming: first page, total", path, {**incoming, "includeTotal": True}),
        (
            "matrix incoming: one in 1 column, jump, total",
            path,
            quarter({**incoming, "columnIds": columns[:1], "state": "one"}),
        ),
    ]


def _read_scenarios(
    engine: Engine, context: str, dataset: VolumeDataset
) -> list[tuple[str, str, dict[str, Any]]]:
    base = context_params(context, dataset)
    items = f"/api/v1/objects/{ITEM}"
    page = {**base, "pageSize": PAGE_SIZE, "sort": "name"}
    _, total = object_cursor(engine, context, dataset, parent=None, offset=1)
    middle, _ = object_cursor(engine, context, dataset, parent=None, offset=total // 2)
    last, _ = object_cursor(engine, context, dataset, parent=None, offset=total - PAGE_SIZE)
    _, heavy_total = object_cursor(engine, context, dataset, parent=dataset.heavy_group_id, offset=1)
    heavy_middle, _ = object_cursor(
        engine, context, dataset, parent=dataset.heavy_group_id, offset=heavy_total // 2
    )
    heavy = {**page, "parentObjectId": dataset.heavy_group_id}
    before_middle, _ = object_cursor(
        engine, context, dataset, parent=None, offset=total // 2, direction="before"
    )
    citations = {**base, "objectId": dataset.cited_group_id, "pageSize": PAGE_SIZE}
    item_columns = [f"{ITEM_CITES_GROUP}.{CODE}", f"{GROUP_CONTAINS_ITEM}-reverse.ancestor:{GROUP}.{CODE}"]
    node_columns = [f"{NODE_HAS_CHILD}.ancestor:{GROUP}.{CODE}", f"{NODE_HAS_CHILD}-reverse.name"]
    return [
        ("objects: first page", items, page),
        ("objects: middle page", items, {**page, "cursor": middle}),
        ("objects: last page", items, {**page, "cursor": last}),
        ("children: heavy parent, first page", items, heavy),
        ("children: heavy parent, middle page", items, {**heavy, "cursor": heavy_middle}),
        (
            "children: small parent",
            items,
            {**page, "parentObjectId": dataset.small_group_id},
        ),
        (
            "relations: 1,500-relation record",
            "/api/v1/relations",
            {**base, "objectId": dataset.cited_group_id, "pageSize": PAGE_SIZE},
        ),
        (
            "relations: heavy parent",
            "/api/v1/relations",
            {**base, "objectId": dataset.heavy_group_id, "pageSize": PAGE_SIZE},
        ),
        ("record: single read", f"{items}/{dataset.live_item_id}", base),
        # S3 and S4 reads.
        ("objects: last page by from=end, total", items, {**page, "from": "end", "includeTotal": True}),
        ("objects: backward page from the middle", items, {**page, "cursor": before_middle}),
        ("objects: seek by name, total", items, {**page, "seek": "Item 0005", "includeTotal": True}),
        ("objects: position ¾ deep, total", items, {**page, "position": total * 3 // 4, "includeTotal": True}),
        (
            "children: heavy parent, position ¾ deep, total",
            items,
            {**heavy, "position": heavy_total * 3 // 4, "includeTotal": True},
        ),
        (
            "roots: top-level page, total",
            f"/api/v1/objects/{GROUP}",
            {**page, "topLevel": True, "includeTotal": True},
        ),
        (
            "relations: 1,500-relation record by name, total",
            "/api/v1/relations",
            {**citations, "sort": "name", "includeTotal": True},
        ),
        (
            "relations: 1,500-relation record, search",
            "/api/v1/relations",
            {**citations, "search": "Item 0", "sort": "-name"},
        ),
        # S4R1: the related type's attributes and ancestors.
        (
            "relations: 1,500-relation record by rank",
            "/api/v1/relations",
            {**citations, "relationTypeKey": ITEM_CITES_GROUP, "sort": RANK},
        ),
        (
            "relations: 1,500-relation record by group, total",
            "/api/v1/relations",
            {**citations, "relationTypeKey": ITEM_CITES_GROUP, "sort": "ancestor:vol-group", "includeTotal": True},
        ),
        (
            "relations: heavy parent by rank",
            "/api/v1/relations",
            {
                **base,
                "objectId": dataset.heavy_group_id,
                "relationTypeKey": GROUP_CONTAINS_ITEM,
                "sort": RANK,
                "pageSize": PAGE_SIZE,
            },
        ),
        # The same order on the object list, for comparison: an attribute sort reads every child.
        ("children: heavy parent by rank", items, {**heavy, "sort": RANK}),
        (
            "relations: heavy parent by group",
            "/api/v1/relations",
            {
                **base,
                "objectId": dataset.heavy_group_id,
                "relationTypeKey": GROUP_CONTAINS_ITEM,
                "sort": "-ancestor:vol-group",
                "pageSize": PAGE_SIZE,
            },
        ),
        (
            "relations: deep node by top node",
            "/api/v1/relations",
            {
                **base,
                "objectId": dataset.deep_node_id,
                "relationTypeKey": NODE_HAS_CHILD,
                "direction": "incoming",
                "sort": "ancestor:vol-node",
            },
        ),
        # S7: a name search over a whole type, as the sidebar tree's search sends it (the browser
        # runner saw it as the slowest tree read). A contains-match cannot use a name index.
        ("objects: search by name, total", items, {**page, "search": "Item 00432", "includeTotal": True}),
        # S8: a value-only match read through the trigram index, a phrase in every record, whose
        # value look-up falls back to each record, and a two-character search the index cannot
        # serve.
        ("objects: search by code, total", items, {**page, "search": "ITEM-0043", "includeTotal": True}),
        ("objects: common search, total", items, {**page, "search": "Item", "includeTotal": True}),
        ("objects: two-character search, total", items, {**page, "search": "m ", "includeTotal": True}),
        ("record: deep node", f"/api/v1/objects/{NODE}/{dataset.deep_node_id}", base),
        # 0.9 Q1: the cross-type lookup over every record of the workspace, and over two types.
        ("lookup: first page, every type", "/api/v1/objects", page),
        ("lookup: search by name, total", "/api/v1/objects", {**page, "search": "Item 00432", "includeTotal": True}),
        (
            "lookup: two types, first page",
            "/api/v1/objects",
            {**page, "objectTypeKey": [GROUP, ITEM]},
        ),
        # 0.9 T1: dated reads (Q4); three quarters of the items apply on the date.
        ("objects: dated, first page", items, {**page, "asOf": AS_OF}),
        ("objects: dated, total", items, {**page, "asOf": AS_OF, "includeTotal": True}),
        ("children: heavy parent, dated first page", items, {**heavy, "asOf": AS_OF}),
        # 0.11 X6 (D158): a table with relation columns, as the list sends it, at the reader's page
        # and at 200 rows. Items' related records sit under no group; nodes' children sit up to
        # seven levels under one, so their ancestor value walks the chain.
        *(
            (f"objects: relation columns, {size} rows", items, {**page, "pageSize": size, "expand": item_columns})
            for size in (PAGE_SIZE, WIDE_PAGE)
        ),
        *(
            (
                f"nodes: relation columns with an ancestor value, {size} rows",
                f"/api/v1/objects/{NODE}",
                {**page, "pageSize": size, "expand": node_columns},
            )
            for size in (PAGE_SIZE, WIDE_PAGE)
        ),
    ]


def _query_scenarios(context: str, dataset: VolumeDataset) -> list[tuple[str, dict[str, Any]]]:
    """0.9 Q3: model-aware queries, as bodies for ``POST /workspaces/{key}/queries/objects``.

    A one-hop criterion (the cited group's 1,500 citing items), its inversion (every other item),
    an ancestor criterion (the heavy group's 20,000 items), and a page with a 20-row expansion of
    the cited group's citations and of the heavy group's 20,000 items.
    """
    scope = {
        "live": {},
        "change_set": {"changeSetId": dataset.change_set_id},
        "history": {"publicationId": dataset.publication_id},
    }[context]
    base = {"context": scope, "pageSize": PAGE_SIZE}
    citing = {
        "related": {
            "relationTypeKey": ITEM_CITES_GROUP,
            "direction": "outgoing",
            "where": [{"field": "id", "op": "eq", "value": dataset.cited_group_id}],
        }
    }

    def group(group_id: str, relation: str, direction: str) -> dict[str, Any]:
        return {
            **base,
            "objectTypeKey": GROUP,
            "where": [{"field": "id", "op": "eq", "value": group_id}],
            "expand": [{"relationTypeKey": relation, "direction": direction, "select": ["name", CODE], "limit": 20}],
        }

    return [
        ("query: one-hop criterion, total", {**base, "objectTypeKey": ITEM, "where": [citing], "includeTotal": True}),
        ("query: inverted hop, first page", {**base, "objectTypeKey": ITEM, "where": [{**citing, "not": True}]}),
        (
            "query: ancestor criterion, total",
            {
                **base,
                "objectTypeKey": ITEM,
                "where": [{"field": f"ancestor:{GROUP}", "op": "eq", "value": dataset.heavy_group_id}],
                "includeTotal": True,
            },
        ),
        # 0.9 T1: dated queries (Q4).
        ("query: dated, first page", {**base, "objectTypeKey": ITEM, "asOf": AS_OF}),
        # The ancestor's items, not the cited group's: dated, those fill more than a page at every
        # scale, so both seeded sizes read the same statements.
        (
            "query: dated ancestor criterion, total",
            {
                **base,
                "objectTypeKey": ITEM,
                "asOf": AS_OF,
                "where": [{"field": f"ancestor:{GROUP}", "op": "eq", "value": dataset.heavy_group_id}],
                "includeTotal": True,
            },
        ),
        ("query: 20-row expansion of 1,500 citations", group(dataset.cited_group_id, ITEM_CITES_GROUP, "incoming")),
        ("query: 20-row expansion of 20,000 children", group(dataset.heavy_group_id, GROUP_CONTAINS_ITEM, "outgoing")),
    ]


def query_scenarios(
    client, engine: Engine, dataset: VolumeDataset, context: str, *, repeat: int
) -> list[Measurement]:
    """Measure the 0.9 Q3 query bodies in one context."""
    path = f"/api/v1/workspaces/{WORKSPACE}/queries/objects"
    results = []
    for scenario, body in _query_scenarios(context, dataset):
        status, milliseconds, statements, rows = _timed(
            engine, lambda body=body: client.post(path, json=body), repeat
        )
        results.append(Measurement(context, scenario, status, milliseconds, statements, rows))
    return results


FEED_PAGE = 500


def _feed_scenarios(context: str, dataset: VolumeDataset) -> list[tuple[str, str, dict[str, Any]]]:
    """Base 0.9 F2: a 500-entry page of the live feed at its head and at its earliest answered
    position, the middle of the feed, which the retention floor is computed for; filtered, a scan of
    ten pages for the one entry in a hundred that is a group's."""
    if context != "live":
        return []
    path = f"/api/v1/workspaces/{WORKSPACE}/feed"
    deep = feed_publication_position(dataset.shape)
    head = dataset.shape.feed_entries - FEED_PAGE
    return [
        ("feed: page at the head", path, {"after": head, "pageSize": FEED_PAGE}),
        ("feed: page at the earliest position", path, {"after": deep, "pageSize": FEED_PAGE}),
        (
            "feed: filtered page at the earliest position",
            path,
            {"after": deep, "pageSize": FEED_PAGE, "objectTypeKey": GROUP},
        ),
    ]


def _move_scenarios(context: str, dataset: VolumeDataset) -> list[tuple[str, str, dict[str, Any]]]:
    """Base 0.8 B2: move targets, in the contexts a move can write to."""
    if context == "history":
        return []
    base = {**context_params(context, dataset), "pageSize": PAGE_SIZE}
    group = f"/api/v1/objects/{GROUP}/{dataset.heavy_group_id}/parent-candidates"
    node = f"/api/v1/objects/{NODE}/{dataset.deep_node_id}/parent-candidates"
    return [
        ("parent candidates: 20,000-descendant record, total", group, {**base, "includeTotal": True}),
        ("parent candidates: search, total", group, {**base, "search": "Group 00043", "includeTotal": True}),
        ("parent candidates: deep node, two types, total", node, {**base, "includeTotal": True}),
        (
            "parent candidates: deep node, position ¾ deep",
            node,
            {**base, "position": dataset.shape.groups * 3 // 4, "includeTotal": True},
        ),
    ]


def _move(client, dataset: VolumeDataset, context: str, object_type: str, object_id: str, parents: list[str]):
    """Setup and write callables that move a record between ``parents``, one step per call."""
    path = f"/api/v1/objects/{object_type}/{object_id}"
    state: dict[str, Any] = {"step": 0}

    def before() -> None:
        params = context_params(context, dataset)
        state["body"] = {
            "parentObjectId": parents[state["step"] % len(parents)],
            "expectedVersion": client.get(path, params=params).json()["version"],
        }
        if context == "change_set":
            change_set = client.get(f"/api/v1/change-sets/{dataset.change_set_id}").json()
            state["body"].update(
                changeSetId=dataset.change_set_id, expectedChangeSetVersion=change_set["version"]
            )
        state["step"] += 1

    return before, lambda: client.patch(path, json=state["body"])


def _timed(
    engine: Engine,
    call: Callable[[], Any],
    repeat: int,
    before: Callable[[], None] | None = None,
    refused: int | None = None,
) -> tuple[int, float, int, int]:
    """Run ``call`` once to warm up, then ``repeat`` times; return the last run's cost.

    The time is the median of the timed runs, or the warm-up run's when ``repeat`` is 0. A status of
    400 or more fails the run unless it is ``refused``, the refusal the scenario measures.
    """
    timings = []
    status, statements, rows = 0, 0, 0
    for run in range(repeat + 1):
        if before is not None:
            before()
        with measure(engine) as cost:
            response = call()
        status = response.status_code
        if status >= 400 and status != refused:
            raise AssertionError(f"{response.request.url} returned {status}: {response.text}")
        statements, rows = cost.statements, cost.rows_loaded
        if run or not repeat:
            timings.append(cost.seconds * 1000)
    return status, statistics.median(timings), statements, rows


def run_scenarios(client, engine: Engine, dataset: VolumeDataset, *, repeat: int) -> list[Measurement]:
    """Measure every read in each context, then one live and one change set write."""
    results = []
    for context in CONTEXTS:
        scenarios = (
            _read_scenarios(engine, context, dataset)
            + _matrix_scenarios(client, context, dataset)
            + _move_scenarios(context, dataset)
            + _feed_scenarios(context, dataset)
        )
        for scenario, path, params in scenarios:
            status, milliseconds, statements, rows = _timed(
                engine, lambda path=path, params=params: client.get(path, params=params), repeat
            )
            results.append(
                Measurement(context, scenario, status, milliseconds, statements, rows)
            )
        results += query_scenarios(client, engine, dataset, context, repeat=repeat)

    path = f"/api/v1/objects/{ITEM}/{dataset.edited_item_id}"
    state: dict[str, Any] = {}

    def change_set_versions() -> None:
        record = client.get(path, params={"changeSetId": dataset.change_set_id}).json()
        change_set = client.get(f"/api/v1/change-sets/{dataset.change_set_id}").json()
        state.update(record=record["version"], change_set=change_set["version"])
        state["name"] = f"Edited {record['version']}"

    def change_set_write():
        return client.patch(
            path,
            json={
                "name": state["name"],
                "expectedVersion": state["record"],
                "changeSetId": dataset.change_set_id,
                "expectedChangeSetVersion": state["change_set"],
            },
        )

    status, milliseconds, statements, rows = _timed(engine, change_set_write, repeat, change_set_versions)
    results.append(Measurement("change_set", "write: rename one record", status, milliseconds, statements, rows))

    live_path = f"/api/v1/objects/{ITEM}/{dataset.live_item_id}"

    def live_version() -> None:
        record = client.get(live_path, params={"workspaceKey": WORKSPACE}).json()
        state.update(record=record["version"], name=f"Renamed {record['version']}")

    def live_write():
        return client.patch(
            live_path, json={"name": state["name"], "expectedVersion": state["record"]}
        )

    status, milliseconds, statements, rows = _timed(engine, live_write, repeat, live_version)
    results.append(Measurement("live", "write: rename one record", status, milliseconds, statements, rows))

    # B2: only the moved record's parent and edge change, whatever lies under it.
    for context in ("live", "change_set"):
        before, write = _move(
            client, dataset, context, GROUP, dataset.heavy_group_id,
            [dataset.small_group_id, dataset.cited_group_id],
        )
        status, milliseconds, statements, rows = _timed(engine, write, repeat, before)
        results.append(
            Measurement(context, "write: move a 20,000-descendant record", status, milliseconds, statements, rows)
        )
    return results


def known_exceptions(client, engine: Engine, dataset: VolumeDataset, *, repeat: int) -> list[Measurement]:
    """Requests recorded over budget (D29), measured by the script, not held by the tests.

    A first-level container of the outgoing matrix moves to the next column and back: each move
    recomputes the stored cell states of the rows of about 2,500 cells (A3b), and live it also
    re-checks their ancestor-scoped uniqueness one relation at a time.
    """
    from app.models.database import RdmObject

    with Session(engine) as session:
        first_column = dataset.matrix_column_ids[0]
        shelf = session.scalar(
            select(RdmObject.id)
            .where(RdmObject.object_type_key == SHELF, RdmObject.parent_object_id == first_column)
            .order_by(RdmObject.id)
            .limit(1)
        )
    results = []
    for context in ("live", "change_set"):
        before, write = _move(
            client, dataset, context, SHELF, shelf, [dataset.matrix_column_ids[1], first_column]
        )
        status, milliseconds, statements, rows = _timed(engine, write, repeat, before)
        results.append(
            Measurement(context, "write: move a container of ~2,500 cells", status, milliseconds, statements, rows)
        )
    return results


QUERY_PATH = f"/api/v1/workspaces/{WORKSPACE}/queries/objects"


def dated_scenarios(client, engine: Engine, dataset: VolumeDataset, *, repeat: int) -> list[Measurement]:
    """0.9 T1: only the dated reads, in every context (``--only-dated``)."""
    results = []
    for context in CONTEXTS:
        for scenario, path, params in _read_scenarios(engine, context, dataset):
            if "dated" in scenario:
                status, milliseconds, statements, rows = _timed(
                    engine, lambda path=path, params=params: client.get(path, params=params), repeat
                )
                results.append(Measurement(context, scenario, status, milliseconds, statements, rows))
        for scenario, body in _query_scenarios(context, dataset):
            if "dated" in scenario:
                status, milliseconds, statements, rows = _timed(
                    engine, lambda body=body: client.post(QUERY_PATH, json=body), repeat
                )
                results.append(Measurement(context, scenario, status, milliseconds, statements, rows))
    return results


def relation_column_scenarios(client, engine: Engine, dataset: VolumeDataset, *, repeat: int) -> list[Measurement]:
    """0.11 X6 (D159): only the lists read with relation columns, in every context
    (``--only-relation-columns``)."""
    results = []
    for context in CONTEXTS:
        for scenario, path, params in _read_scenarios(engine, context, dataset):
            if "relation columns" in scenario:
                status, milliseconds, statements, rows = _timed(
                    engine, lambda path=path, params=params: client.get(path, params=params), repeat
                )
                results.append(Measurement(context, scenario, status, milliseconds, statements, rows))
    return results


CONSUMER_LISTS = f"/api/consumer/{CONSUMER_API}/v1/lists"


def consumer_scenarios(client, engine: Engine, dataset: VolumeDataset, *, repeat: int) -> list[Measurement]:
    """0.9 C3: consumer list reads, live (``--only-consumer``); C6a: the same reads pinned to the
    seed's publication. The next page and the position jump are read through the cursor and position
    the first page and the total name. C16: the first page with a total and the position jump, dated
    by ``asOf`` (three quarters of the items apply on that day)."""
    ranked = f"{CONSUMER_LISTS}/{RANKED_ITEMS}"
    results = []
    for context, pinned in (("live", {}), ("history", {"publication": dataset.publication_id})):
        label = "consumer" if not pinned else "consumer pinned"
        base = {"workspace": WORKSPACE, "pageSize": PAGE_SIZE, **pinned}
        first = client.get(ranked, params={**base, "includeTotal": "true"}).json()
        dated = {**base, "asOf": AS_OF}
        dated_first = client.get(ranked, params={**dated, "includeTotal": "true"}).json()
        scenarios = [
            (f"{label}: first page of every item by rank", ranked, base),
            (f"{label}: next cursor page", ranked, {**base, "cursor": first["nextCursor"]}),
            (f"{label}: position jump to the middle", ranked, {**base, "position": first["totalCount"] // 2}),
            (
                f"{label}: 20,000 items under a parent",
                f"{CONSUMER_LISTS}/{ITEMS_BY_GROUP}",
                {**base, GROUP_PARENT: dataset.heavy_group_id},
            ),
            (
                f"{label}: ancestor filter with includeTotal",
                ranked,
                {**base, WITHIN_GROUP: dataset.heavy_group_id, "includeTotal": "true"},
            ),
            (f"{label}: dated, first page with includeTotal", ranked, {**dated, "includeTotal": "true"}),
            (
                f"{label}: dated, position jump to the middle",
                ranked,
                {**dated, "position": dated_first["totalCount"] // 2},
            ),
        ]
        for scenario, path, params in scenarios:
            status, milliseconds, statements, rows = _timed(
                engine, lambda path=path, params=params: client.get(path, params=params), repeat
            )
            results.append(Measurement(context, scenario, status, milliseconds, statements, rows))
    return results


CONSUMER_EVENTS = f"/api/consumer/{CONSUMER_API}/v1/events"
SUBSCRIPTIONS_PATH = "/api/v1/consumer-subscriptions"
# The subscriptions capability (0.9 C11, C12) as the delivery scenarios need it: on, and a key to
# seal signing keys with.
SUBSCRIPTION_SETTINGS = {
    "CONSUMER_SUBSCRIPTIONS_ENABLED": "true",
    "CONSUMER_WEBHOOK_KEY_ENCRYPTION_KEY": "a2tra2tra2tra2tra2tra2tra2tra2tra2tra2tra2s=",
}
CAUGHT_UP_SUBSCRIPTIONS = 100
EVENT_PAGE = 100


def activate_events(client) -> None:
    """Activate a release whose volume consumer API declares one event over groups and items, every
    change and no watch (0.9 C10); the service runs with model administration on."""
    model = volume_model()
    model["release"]["version"] += "-events"
    (definition,) = model["consumerApis"]
    definition["operations"]["events"] = {
        "custom": [
            {"key": "catalogue-changed", "objectTypes": [GROUP, ITEM], "changes": ["created", "updated", "deleted"]}
        ]
    }
    draft = client.post("/api/v1/model-drafts", json={"name": "Events", "model": model}).json()
    release = client.post(
        f"/api/v1/model-drafts/{draft['id']}/installation", json={"expectedVersion": draft["version"]}
    )
    assert release.status_code == 201, release.text
    # Into the default workspace and the volume workspace, each running its own release (0.11 M1).
    for workspace in ("default", WORKSPACE):
        state = client.get(f"/api/v1/workspaces/{workspace}/model").json()
        activated = client.post(
            f"/api/v1/workspaces/{workspace}/model/activation",
            json={
                "releaseId": release.json()["id"],
                "expectedVersion": state["version"],
                "expectedReleaseId": state["releaseId"],
            },
        )
        assert activated.status_code == 200, activated.text


def event_scenarios(
    client, engine: Engine, dataset: VolumeDataset, *, repeat: int, caught_up: int = CAUGHT_UP_SUBSCRIPTIONS
) -> tuple[list[Measurement], int]:
    """0.9 C10 (``--only-events``): deriving a page of 500 live creations, and the heavy group's rename,
    which updates every group and item below it (C-D82's fan-out); then the pull feed's first page with
    each payload and narrowed by the ``within`` ancestor parameter. Derivation runs once each (it
    consumes its entries); the reads ``repeat`` times. Also returns how many objects the rename told."""
    from app.models.database import ConsumerEvent, Workspace

    deriver = client.app.state.event_deriver
    activate_events(client)
    deriver.run_until_idle()
    results = []

    def derived(scenario: str) -> None:
        with measure(engine) as cost:
            assert deriver.derive(WORKSPACE)
        results.append(Measurement("live", scenario, 200, cost.seconds * 1000, cost.statements, cost.rows_loaded))

    items = [
        {
            "op": "create",
            "applicationKey": APPLICATION,
            "objectTypeKey": ITEM,
            "name": f"Event item {index}",
            "parent": {"id": dataset.small_group_id},
            "attributes": [{"attributeTypeKey": CODE, "value": f"EV-{index:04d}"}],
        }
        for index in range(500)
    ]
    batch = client.post(
        "/api/v1/batches", json={"workspaceKey": WORKSPACE, "policy": "atomic", "run": "inline", "items": items}
    )
    assert batch.status_code == 200, batch.text
    derived("events: derive 500 live creations")
    deriver.run_until_idle()

    path = f"/api/v1/objects/{GROUP}/{dataset.heavy_group_id}"
    heavy = client.get(path, params={"workspaceKey": WORKSPACE}).json()
    renamed = client.patch(path, json={"expectedVersion": heavy["version"], "name": f"{heavy['name']} renamed"})
    assert renamed.status_code == 200, renamed.text
    with Session(engine) as session:
        position = session.scalar(select(Workspace.feed_position).where(Workspace.key == WORKSPACE))
    derived("events: derive the heavy group's rename")
    with Session(engine) as session:
        told = session.scalar(
            select(func.count())
            .select_from(ConsumerEvent)
            .where(ConsumerEvent.workspace_key == WORKSPACE, ConsumerEvent.position == position)
        )

    base = {"workspace": WORKSPACE, "pageSize": EVENT_PAGE, "after": position - 1}
    for scenario, params in (
        ("events: first page, full", base),
        ("events: first page, identity", {**base, "payload": "identity"}),
        ("events: within the heavy group, full", {**base, WITHIN_GROUP: dataset.heavy_group_id}),
    ):
        status, milliseconds, statements, rows = _timed(
            engine, lambda params=params: client.get(CONSUMER_EVENTS, params=params), repeat
        )
        results.append(Measurement("live", scenario, status, milliseconds, statements, rows))
    results += delivery_scenarios(client, engine, position, repeat=repeat, caught_up=caught_up)
    return results, told




class _Receiver:
    """A webhook receiver on ``localhost`` that answers ``200`` at once and counts what it got."""

    def __init__(self) -> None:
        from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

        receiver = self
        self.requests = 0

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self) -> None:
                self.rfile.read(int(self.headers["Content-Length"]))
                receiver.requests += 1
                self.send_response(200)
                self.send_header("Content-Length", "0")
                self.end_headers()

            def log_message(self, *_args) -> None:
                pass

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.url = f"http://localhost:{self.server.server_address[1]}/hook"
        self._thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self._thread.start()

    def close(self) -> None:
        self.server.shutdown()
        self.server.server_close()


def delivery_scenarios(
    client, engine: Engine, position: int, *, repeat: int, caught_up: int = CAUGHT_UP_SUBSCRIPTIONS
) -> list[Measurement]:
    """0.9 C13 (``--only-events``, C-D113): webhook delivery of the heavy group's rename, the events
    at ``position``, to a receiver on ``localhost`` that answers at once. First the dispatcher's claim
    with ``caught_up`` caught-up subscriptions (one statement however many), which every process runs once a second. Then a ``full`` and an
    ``identity`` subscription starting just before the rename: one batch of 100 (the claim, the step
    and the acknowledgement, the receiver's answer included) ``repeat`` times after a warm-up, then
    the rest of the events, reported with the batches as the whole delivery. Last, one batch of 100
    ``full`` events as CloudEvents (C17). The application's dispatcher thread is off; each step runs
    here."""
    dispatcher = client.app.state.consumer_dispatcher
    assert dispatcher is not None, "the delivery scenarios need the subscriptions capability on"
    receiver = _Receiver()
    results: list[Measurement] = []

    def subscribe(**changes: Any) -> str:
        body = {
            "name": "Volume receiver",
            "consumerApi": CONSUMER_API,
            "workspaceKey": WORKSPACE,
            "events": ["catalogue-changed"],
        }
        response = client.post(SUBSCRIPTIONS_PATH, json={**body, "url": receiver.url, **changes})
        assert response.status_code == 201, response.text
        return response.json()["id"]

    def remove(subscription: str) -> None:
        version = client.get(f"{SUBSCRIPTIONS_PATH}/{subscription}").json()["version"]
        response = client.delete(f"{SUBSCRIPTIONS_PATH}/{subscription}", params={"expectedVersion": version})
        assert response.status_code == 204, response.text

    def step(now: datetime) -> tuple[list[int], Any]:
        with measure(engine) as cost:
            claimed = dispatcher.claim(now)
            for sequence_id in claimed:
                dispatcher.dispatch_one(sequence_id, now)
        return claimed, cost

    try:
        idle = [subscribe(payload="identity") for _ in range(caught_up)]
        timings = []
        for run in range(repeat + 1):
            claimed, cost = step(datetime.now(UTC))
            assert claimed == []
            if run or not repeat:
                timings.append(cost.seconds * 1000)
        results.append(
            Measurement(
                "live",
                f"delivery: claim with {caught_up} caught-up subscriptions",
                200,
                statistics.median(timings),
                cost.statements,
                cost.rows_loaded,
            )
        )
        for subscription in idle:
            remove(subscription)

        for payload in ("full", "identity"):
            subscription = subscribe(payload=payload, maxEventsPerBatch=EVENT_PAGE, startAfter=position - 1)
            sent = receiver.requests
            timings, total_ms, total_statements = [], 0.0, 0
            for run in range(repeat + 1):
                claimed, cost = step(datetime.now(UTC))
                assert len(claimed) == 1 and receiver.requests == sent + run + 1
                total_ms, total_statements = total_ms + cost.seconds * 1000, total_statements + cost.statements
                if run or not repeat:
                    timings.append(cost.seconds * 1000)
            results.append(
                Measurement(
                    "live",
                    f"delivery: a batch of {EVENT_PAGE}, {payload}",
                    200,
                    statistics.median(timings),
                    cost.statements,
                    cost.rows_loaded,
                )
            )
            with measure(engine) as rest:
                dispatcher.run_until_idle(datetime.now(UTC))
            batches = receiver.requests - sent
            results.append(
                Measurement(
                    "live",
                    f"delivery: the whole rename, {payload} ({batches} batches)",
                    200,
                    total_ms + rest.seconds * 1000,
                    total_statements + rest.statements,
                    rest.rows_loaded,
                )
            )
            remove(subscription)

        subscription = subscribe(maxEventsPerBatch=EVENT_PAGE, format="cloudevents", startAfter=position - 1)
        sent = receiver.requests
        claimed, cost = step(datetime.now(UTC))
        assert len(claimed) == 1 and receiver.requests == sent + 1
        results.append(
            Measurement(
                "live",
                f"delivery: a batch of {EVENT_PAGE}, full, CloudEvents",
                200,
                cost.seconds * 1000,
                cost.statements,
                cost.rows_loaded,
            )
        )
        remove(subscription)
    finally:
        receiver.close()
    return results


CONSUMER_XREF = f"/api/consumer/{CONSUMER_API}/v1/xref"


def consumer_xref_scenarios(client, engine: Engine, dataset: VolumeDataset, *, repeat: int) -> list[Measurement]:
    """0.9 C4: XREF lookups, live (``--only-consumer``), and since C6a pinned to the seed's
    publication: an item's code in another case, the cited
    group's code (its own match and the citing items it promotes), a 4-character contains, the
    same code with ``expect=one``, and a term in every item refused as ``QUERY_TOO_BROAD``. C5: the
    cited group's code narrowed to the heavy group (a filter over the promoted items), and with the
    ``scoresFrom`` parameter on the cited group. C16: the cited group's code dated by ``asOf``, over
    the dated items and the undated groups."""
    from app.models.database import AttributeValue

    with Session(engine) as session:
        codes = dict(
            session.execute(
                select(AttributeValue.object_id, AttributeValue.text_value).where(
                    AttributeValue.attribute_type_key == CODE,
                    AttributeValue.object_id.in_([dataset.live_item_id, dataset.cited_group_id]),
                )
            ).all()
        )
    item_code = codes[dataset.live_item_id].lower()
    results = []
    for context, pinned in (("live", {}), ("history", {"publication": dataset.publication_id})):
        label = "consumer xref" if not pinned else "consumer xref pinned"
        base = {"workspace": WORKSPACE, "pageSize": PAGE_SIZE, **pinned}
        scenarios = [
            (f"{label}: an item's code, another case", {**base, "query": item_code}, None),
            (f"{label}: a group's code promoted to its citing items", {**base, "query": codes[dataset.cited_group_id]}, None),
            (f"{label}: 4-character contains", {**base, "query": "0099"}, None),
            (f"{label}: expect=one", {"workspace": WORKSPACE, **pinned, "query": item_code, "expect": "one"}, None),
            (
                f"{label}: a group's code, within the heavy group",
                {**base, "query": codes[dataset.cited_group_id], WITHIN_GROUP: dataset.heavy_group_id},
                None,
            ),
            (
                f"{label}: a group's code, scoresFrom on the group",
                {**base, "query": codes[dataset.cited_group_id], CITING: codes[dataset.cited_group_id]},
                None,
            ),
            # Ten a page: at the smallest test shape the dated lookup holds 18 results, under one page
            # of 20, which the pager counts without a statement; every size then reads more than a page.
            (
                f"{label}: a group's code, dated",
                {**base, "pageSize": PAGE_SIZE // 2, "query": codes[dataset.cited_group_id], "asOf": AS_OF},
                None,
            ),
            (f"{label}: a term in every item, too broad", {**base, "query": "item"}, 400),
        ]
        for scenario, params, refused in scenarios:
            status, milliseconds, statements, rows = _timed(
                engine, lambda params=params: client.get(CONSUMER_XREF, params=params), repeat, refused=refused
            )
            results.append(Measurement(context, scenario, status, milliseconds, statements, rows))
    return results


CONSUMER_RESOLVE = f"/api/consumer/{CONSUMER_API}/v1/resolve"


def _resolve_bodies(engine: Engine, dataset: VolumeDataset, size: int) -> dict[str, dict[str, Any]]:
    """0.9 C14: batch resolve bodies of ``size`` items.

    Budgeted (C-D53), lookups as a flow sends them, each fitting the parameters it is sent with:

    - identifiers: item codes in another case, every tenth the code of another group, every tenth a
      miss, every twentieth an item's ID, and one contains-only term (a code without its last two
      characters), so every batch runs the contains statement for its unsettled lookups;
    - three parameter sets: no parameter, the heavy group with codes of its own items, the cited
      group's code as ``scoresFrom`` value; each set opens with a miss and a hit it keeps.

    Recorded, not budgeted:

    - cited group fan-out: as identifiers, but every tenth item is the one group code 1,500 items
      cite, so each such lookup scores 1,501 objects;
    - parameters filtering items out: the identifiers over the three sets regardless of fit, so
      most lookups lose their exact match to a parameter and read contains matches;
    - contains only: every item a code without its last character;
    - distinct parameters: every item narrowed to its own group, one parameter set per item.
    """
    from app.models.database import AttributeValue, RdmObject

    def codes_of(session: Session, *conditions: Any, limit: int) -> list[Any]:
        return list(
            session.execute(
                select(RdmObject.id, AttributeValue.text_value)
                .join(RdmObject, RdmObject.id == AttributeValue.object_id)
                .where(AttributeValue.attribute_type_key == CODE, *conditions)
                .order_by(AttributeValue.text_value)
                .limit(limit)
            ).all()
        )

    with Session(engine) as session:
        items = codes_of(session, RdmObject.object_type_key == ITEM, limit=size)
        groups = codes_of(
            session, RdmObject.object_type_key == GROUP, RdmObject.id != dataset.cited_group_id, limit=size
        )
        heavy = codes_of(session, RdmObject.parent_object_id == dataset.heavy_group_id, limit=size)
        cited = session.scalar(
            select(AttributeValue.text_value).where(
                AttributeValue.attribute_type_key == CODE, AttributeValue.object_id == dataset.cited_group_id
            )
        )

    def identifiers(group_code: Callable[[int], str]) -> list[dict[str, Any]]:
        mix = []
        for index, (object_id, code) in enumerate(items):
            if index == 0:
                mix.append({"ref": "contains", "query": code[:-2]})
            elif index % 10 == 1:
                mix.append({"query": group_code(index)})
            elif index % 10 == 2:
                mix.append({"query": f"nothing-{index}"})
            elif index % 20 == 3:
                mix.append({"id": object_id})
            else:
                mix.append({"query": code.lower()})
        return mix

    budgeted = identifiers(lambda index: groups[index // 10 % len(groups)][1])
    sets = [{}, {WITHIN_GROUP: dataset.heavy_group_id}, {CITING: cited}]
    fitting = [
        budgeted,
        [{"query": code.lower()} for _object_id, code in heavy],
        [{"query": code.lower()} for _object_id, code in items],
    ]
    per_set = (size - 6) // 3
    three_sets = [
        item
        for values, hit, own in zip(sets, (budgeted[4]["query"], heavy[0][1], cited), fitting, strict=True)
        for item in (
            [{"query": f"nothing-in-{len(values)}-{hit}", **values}, {"query": hit, **values}]
            + [{**item, **values} for item in (own * size)[:per_set]]
        )
    ]
    three_sets += [{"query": f"nothing-extra-{index}"} for index in range(size - len(three_sets))]
    return {
        "identifiers": {"items": budgeted},
        "three parameter sets": {"items": three_sets},
        "cited group fan-out": {"items": identifiers(lambda _index: cited)},
        "parameters filtering items out": {
            "items": [{**item, **sets[index % 3]} for index, item in enumerate(budgeted)]
        },
        "contains only": {"items": [{"query": code[:-1]} for _object_id, code in items]},
        "distinct parameters": {
            "items": [
                {"query": code.lower(), WITHIN_GROUP: groups[index % len(groups)][0]}
                for index, (_object_id, code) in enumerate(items)
            ]
        },
    }


def consumer_resolve_scenarios(
    client,
    engine: Engine,
    dataset: VolumeDataset,
    *,
    repeat: int,
    sizes: tuple[int, ...] = (1_000,),
    families: tuple[str, ...] = (
        "identifiers",
        "dated identifiers",
        "three parameter sets",
        "cited group fan-out",
        "parameters filtering items out",
        "contains only",
        "distinct parameters",
    ),
) -> list[Measurement]:
    """0.9 C14: batch resolve, live (``--only-consumer``): each family of :func:`_resolve_bodies` at
    each size. The scenario is named ``consumer resolve: <family>, <size> items``. ``dated
    identifiers`` (C16) sends the identifiers with ``asOf``."""
    results = []
    for size in sizes:
        bodies = _resolve_bodies(engine, dataset, size)
        for family in families:
            params = {"workspace": WORKSPACE}
            if family == "dated identifiers":
                body, params["asOf"] = bodies["identifiers"], AS_OF
            else:
                body = bodies[family]
            status, milliseconds, statements, rows = _timed(
                engine,
                lambda body=body, params=params: client.post(CONSUMER_RESOLVE, json=body, params=params),
                repeat,
            )
            scenario = f"consumer resolve: {family}, {len(body['items'])} items"
            results.append(Measurement("live", scenario, status, milliseconds, statements, rows))
    return results


def publish_scenario(client, engine: Engine, dataset: VolumeDataset) -> list[Measurement]:
    """0.9 T1: publishing a change set that renames a tenth of the items (10,000 at full volume),
    staged through inline batches, timed once: it changes the data the reads above measured."""
    from app.models.database import RdmObject

    count = dataset.shape.items // 10
    with Session(engine) as session:
        ids = session.scalars(
            select(RdmObject.id)
            .where(RdmObject.object_type_key == ITEM, RdmObject.id != dataset.live_item_id)
            .order_by(RdmObject.id)
            .limit(count)
        ).all()
    with measure(engine) as capture_cost:
        created = client.post(
            f"/api/v1/workspaces/{WORKSPACE}/change-sets",
            json={"name": "T1 publish", "source": "currentLive"},
        )
    assert created.status_code == 201, created.text
    change_set = created.json()
    for start in range(0, len(ids), 1000):
        version = client.get(f"/api/v1/change-sets/{change_set['id']}").json()["version"]
        items = [
            {
                "op": "update",
                "target": {"id": item},
                "expectedVersion": 1,
                "name": f"Published {item[:8]}",
            }
            for item in ids[start : start + 1000]
        ]
        staged = client.post(
            "/api/v1/batches",
            json={
                "changeSetId": change_set["id"],
                "expectedChangeSetVersion": version,
                "policy": "atomic",
                "run": "inline",
                "items": items,
            },
        )
        assert staged.status_code == 200 and staged.json()["job"]["result"] == "applied", (
            staged.text
        )
    version = client.get(f"/api/v1/change-sets/{change_set['id']}").json()["version"]
    body = {
        "expectedChangeSetVersion": version,
        "expectedActivePublicationId": dataset.publication_id,
    }
    with measure(engine) as cost:
        response = client.post(f"/api/v1/change-sets/{change_set['id']}/publication", json=body)
    assert response.status_code == 200, response.text
    return [
        Measurement(
            "change_set",
            "capture: current live",
            created.status_code,
            capture_cost.seconds * 1000,
            capture_cost.statements,
            capture_cost.rows_loaded,
        ),
        Measurement(
            "change_set",
            f"publish: {len(ids):,} renamed records",
            response.status_code,
            cost.seconds * 1000,
            cost.statements,
            cost.rows_loaded,
        ),
    ]


def deletion_scenarios(client, engine: Engine, dataset: VolumeDataset) -> list[Measurement]:
    """0.9 K2b, D124, run once at R (``--only-deletion``): previews of deleting about as many records
    as the items (100,000 at full volume, the groups' owned matrix cells counted) live, rolled back so the seed stays, and in the change set,
    then that deletion executed in the change set, each timed once (target under 60 s). The largest
    top-level groups are deleted with what they hold, by cascading items. The worker's own thread is
    stopped and the job is run in this thread, so its statements are counted."""
    worker = client.app.state.job_worker
    worker.stop()
    with engine.connect() as connection:
        sizes = connection.execute(
            text(
                "WITH RECURSIVE tree(root, id) AS ("
                " SELECT id, id FROM objects WHERE workspace_key = :workspace"
                "  AND object_type_key = :group AND parent_object_id IS NULL"
                " UNION ALL SELECT tree.root, child.id FROM objects child"
                "  JOIN tree ON child.parent_object_id = tree.id),"
                # The matrix cells a group owns go with it.
                " owned AS (SELECT tree.root, count(*) AS n FROM tree JOIN object_relations r"
                "  ON r.from_object_id = tree.id AND r.relation_type_key = :cell GROUP BY tree.root)"
                " SELECT tree.root, count(*) + coalesce(max(owned.n), 0) AS n FROM tree"
                "  LEFT JOIN owned ON owned.root = tree.root GROUP BY tree.root ORDER BY n DESC, tree.root"
            ),
            {"workspace": WORKSPACE, "group": GROUP, "cell": GROUP_HAS_CELL},
        ).all()
    chosen, total = [], 0
    for root, size in sizes:
        if total >= dataset.shape.items:
            break
        chosen.append(root)
        total += size

    def items(params: dict[str, str]) -> list[dict[str, Any]]:
        return [
            {
                "op": "delete",
                "target": {"id": group_id},
                "expectedVersion": client.get(f"/api/v1/objects/{GROUP}/{group_id}", params=params).json()["version"],
                "cascade": True,
            }
            for group_id in chosen
        ]

    def run(job_id: str, scenario: str, context: str) -> tuple[Measurement, dict[str, Any]]:
        with measure(engine) as cost:
            worker.run_until_idle()
        job = client.get(f"/api/v1/jobs/{job_id}").json()
        return (
            Measurement(context, scenario, 200, cost.seconds * 1000, cost.statements, cost.rows_loaded),
            job,
        )

    results = []
    live = client.post(
        "/api/v1/batches",
        json={"workspaceKey": WORKSPACE, "policy": "independent", "run": "background", "stage": "preview",
              "items": items({"workspaceKey": WORKSPACE})},
    )
    assert live.status_code == 202, live.text
    measurement, job = run(live.json()["id"], "", "live")
    deleted = job["preview"]["deletion"]["objectCount"]
    results.append(Measurement(**{**measurement.__dict__, "scenario": f"delete preview: {len(chosen)} groups, {deleted:,} records"}))
    client.post(f"/api/v1/jobs/{job['id']}/cancel")

    in_change_set = {"changeSetId": dataset.change_set_id}
    version = client.get(f"/api/v1/change-sets/{dataset.change_set_id}").json()["version"]
    staged = client.post(
        "/api/v1/batches",
        json={"changeSetId": dataset.change_set_id, "expectedChangeSetVersion": version, "policy": "independent",
              "run": "background", "stage": "preview", "items": items(in_change_set)},
    )
    assert staged.status_code == 202, staged.text
    measurement, job = run(staged.json()["id"], "", "change_set")
    deleted = job["preview"]["deletion"]["objectCount"]
    results.append(Measurement(**{**measurement.__dict__, "scenario": f"delete preview: {len(chosen)} groups, {deleted:,} records"}))
    confirmed = client.post(f"/api/v1/jobs/{job['id']}/confirm")
    assert confirmed.status_code in (200, 202), confirmed.text
    measurement, job = run(job["id"], "", "change_set")
    assert job["state"] == "completed", job
    results.append(
        Measurement(**{**measurement.__dict__, "scenario": f"delete executed: {job['counts']['deleted']:,} items applied"})
    )
    return results


MOVE_TARGET = "move-target"
MATRIX_TYPES = {"vol-column", "vol-shelf", "vol-cell"}


def move_target_model() -> dict[str, Any]:
    """0.11 X5, D151: a partly compatible model for the volume workspace's move. Every key differs
    from the volume model's and every name is kept, so the inference proposes from names, attribute
    overlap and stored values; the relation matrix application and its types are left out, so their
    records cannot move; the item type gains a required attribute nothing in the source fills."""
    model = json.loads(json.dumps(volume_model()).replace("vol-", "cat-"))
    model["release"] = {"key": "cat-model", "name": "Catalogue model", "version": "1.0.0"}
    left_out = {key.replace("vol-", "cat-") for key in MATRIX_TYPES}
    model["objectTypes"] = [item for item in model["objectTypes"] if item["key"] not in left_out]
    model["objectTypeRelations"] = [
        item
        for item in model["objectTypeRelations"]
        if not {item["fromObjectTypeKey"], item["toObjectTypeKey"]} & left_out
    ]
    used = {item["relationTypeKey"] for item in model["objectTypeRelations"]}
    model["relationTypes"] = [item for item in model["relationTypes"] if item["key"] in used]
    model["applications"] = [app for app in model["applications"] if not set(app["objectTypeKeys"]) & left_out]
    model["consumerApis"] = []
    model["attributeTypes"].append({"key": "cat-owner", "name": "Owner"})
    item = next(entry for entry in model["objectTypes"] if entry["key"] == "cat-item")
    item["attributes"].append({"attributeTypeKey": "cat-owner", "required": True, "order": 40})
    return model


def move_scenarios(client, engine: Engine, dataset: VolumeDataset) -> tuple[list[Measurement], dict[str, Any]]:
    """0.11 X5, D151–D153, run once (``--only-move``): the whole volume workspace copied into a
    workspace on :func:`move_target_model` through a proposed mapping completed by one hand step;
    the inference, the application of its proposals, the dry run (each stage), the load and the
    publication of the target's change set each timed once. The worker's chunks run in this thread,
    so their statements count. Then, with the worker on its own thread as in the service, a
    20-record move sent at once and its timeline read (D153)."""
    worker = client.app.state.job_worker
    worker.stop()
    api = "/api/v1"
    facts: dict[str, Any] = {}
    results: list[Measurement] = []
    # Every statement over 0.5 s, with its text, so one run names each slow statement.
    slow: list[tuple[float, str]] = []
    began_at: dict[int, float] = {}

    def before_statement(connection, cursor, statement, parameters, context, executemany):
        began_at[id(cursor)] = time.perf_counter()

    def after_statement(connection, cursor, statement, parameters, context, executemany):
        spent = time.perf_counter() - began_at.pop(id(cursor), time.perf_counter())
        if spent > 0.5:
            slow.append((round(spent, 1), " ".join(statement.split())[:600]))
            print(f"  slow statement {spent:.1f} s: {' '.join(statement.split())[:300]}", flush=True)

    event.listen(engine, "before_cursor_execute", before_statement)
    event.listen(engine, "after_cursor_execute", after_statement)

    def ok(response, *statuses: int) -> dict[str, Any]:
        assert response.status_code in (statuses or (200,)), response.text[:2000]
        return response.json()

    def job(job_id: str) -> dict[str, Any]:
        return ok(client.get(f"{api}/jobs/{job_id}"))

    def run(job_id: str, label: str) -> dict[str, Any]:
        """Every chunk of ``job_id`` until it waits or ends, timed per stage."""
        stages: dict[str, list[float]] = {}
        stage = job(job_id)["stage"] or "start"
        while True:
            with measure(engine) as cost:
                ran = worker.run_once()
            if not ran:
                break
            spent = stages.setdefault(stage, [0.0, 0, 0, 0])
            spent[0] += cost.seconds
            spent[1] += cost.statements
            spent[2] += cost.rows_loaded
            spent[3] += 1
            stage = job(job_id)["stage"] or stage
        for name, (seconds, statements, rows, chunks) in stages.items():
            results.append(
                Measurement("move", f"{label}: {name} ({chunks} chunks)", 200, seconds * 1000, statements, rows)
            )
            print(f"  {label}: {name} {seconds:.1f} s, {statements} statements, {chunks} chunks", flush=True)
        return job(job_id)

    def timed(label: str, call: Callable[[], Any]) -> Any:
        with measure(engine) as cost:
            answer = call()
        results.append(Measurement("move", label, 200, cost.seconds * 1000, cost.statements, cost.rows_loaded))
        print(f"  {label}: {cost.seconds:.1f} s, {cost.statements} statements", flush=True)
        return answer

    with engine.connect() as connection:
        by_type = dict(
            connection.execute(
                text("SELECT object_type_key, count(*) FROM objects WHERE workspace_key = :w GROUP BY 1"),
                {"w": WORKSPACE},
            ).all()
        )
        relationships = connection.execute(
            text("SELECT count(*) FROM object_relations r JOIN objects o ON o.id = r.from_object_id"
                 " WHERE o.workspace_key = :w"),
            {"w": WORKSPACE},
        ).scalar_one()
    facts["source records"] = by_type
    facts["source relationships"] = relationships
    print(f"  source: {sum(by_type.values()):,} records {by_type}, {relationships:,} relationships", flush=True)

    draft = ok(client.post(f"{api}/model-drafts", json={"name": "Catalogue", "model": move_target_model()}), 201)
    release = ok(
        client.post(f"{api}/model-drafts/{draft['id']}/installation", json={"expectedVersion": draft["version"]}),
        201,
    )
    ok(
        client.post(
            f"{api}/workspaces",
            json={"key": MOVE_TARGET, "label": "Move target", "modelReleaseId": release["id"]},
        ),
        201,
    )
    mapping = ok(
        client.post(
            f"{api}/model-mappings",
            json={"key": "volume-move", "name": "Volume move", "sourceWorkspaceKey": WORKSPACE,
                  "targetWorkspaceKey": MOVE_TARGET},
        ),
        201,
    )
    key = mapping["key"]
    started = ok(
        client.post(
            f"{api}/model-mappings/{key}/inference",
            json={"sourceWorkspaceKey": WORKSPACE, "targetWorkspaceKey": MOVE_TARGET},
        ),
        202,
    )
    inference = run(started["jobId"], "inference")
    assert inference["state"] == "completed", inference
    current = ok(client.get(f"{api}/model-mappings/{key}"))
    timed(
        "apply the proposals",
        lambda: ok(client.post(f"{api}/model-mappings/{key}/inference/application",
                               json={"expectedVersion": current["version"]})),
    )
    current = ok(
        client.get(f"{api}/model-mappings/{key}", params={"sourceWorkspaceKey": WORKSPACE,
                                                          "targetWorkspaceKey": MOVE_TARGET})
    )
    facts["types proposed"] = {entry["source"]: entry["target"] for entry in current["types"]}
    # The hand steps. The inference proposes the matrix types as the target's nearest type (code
    # and rank overlap); the administrator unmaps them, so their records are reported as not moved.
    for entry in current["types"]:
        if entry["source"] in MATRIX_TYPES:
            current = ok(
                client.post(
                    f"{api}/model-mappings/{key}/operations",
                    json={"expectedVersion": current["version"],
                          "operations": [{"kind": "unmapType", "sourceType": entry["source"]}]},
                )
            )
    current = ok(
        client.get(f"{api}/model-mappings/{key}", params={"sourceWorkspaceKey": WORKSPACE,
                                                          "targetWorkspaceKey": MOVE_TARGET})
    )
    # The required attribute nothing fills gets a default.
    for need in current["coverage"]["required"]:
        source_type = next(entry["source"] for entry in current["types"] if entry["target"] == need["targetType"])
        current = ok(
            client.post(
                f"{api}/model-mappings/{key}/operations",
                json={"expectedVersion": current["version"], "operations": [
                    {"kind": "setDefault", "sourceType": source_type, "attribute": need["attributeTypeKey"],
                     "value": "Unassigned"}]},
            )
        )
    current = ok(
        client.get(f"{api}/model-mappings/{key}", params={"sourceWorkspaceKey": WORKSPACE,
                                                          "targetWorkspaceKey": MOVE_TARGET})
    )
    facts["mapping problems"] = current.get("problems")
    sent = ok(
        client.post(
            f"{api}/moves",
            json={"sourceWorkspaceKey": WORKSPACE, "targetWorkspaceKey": MOVE_TARGET,
                  "mapping": {"key": key, "expectedVersion": current["version"]}, "selection": {}},
        ),
        202,
    )
    preview = run(sent["id"], "dry run")
    assert preview["state"] == "awaiting_confirmation", preview
    summary = preview["move"]
    facts["dry run"] = {"rows": summary["rows"], "counts": summary["counts"],
                        "reasons": summary["reasons"][:10]}
    print(f"  dry run: {summary['rows']:,} rows {summary['counts']}", flush=True)
    ok(client.post(f"{api}/jobs/{sent['id']}/confirm"), 202)
    loaded = run(sent["id"], "load")
    assert loaded["state"] == "completed", loaded
    change_set = loaded["move"]["targetChangeSetId"]
    version = ok(client.get(f"{api}/change-sets/{change_set}"))["version"]
    timed(
        f"publish the target's change set ({summary['rows']:,} rows)",
        lambda: ok(client.post(f"{api}/change-sets/{change_set}/publication",
                               json={"expectedChangeSetVersion": version, "expectedActivePublicationId": None})),
    )

    # D153: the service's case. The worker on its own thread, a 20-record move of items already
    # copied (so 20 updates by counterpart), sent with stage execute; its timeline polled.
    with engine.connect() as connection:
        ids = connection.execute(
            text("SELECT id FROM objects WHERE workspace_key = :w AND object_type_key = :t ORDER BY id LIMIT 20"),
            {"w": WORKSPACE, "t": ITEM},
        ).scalars().all()
    current = ok(client.get(f"{api}/model-mappings/{key}"))
    worker.start()
    timeline: list[tuple[float, str, str | None]] = []
    waits: list[Any] = []
    try:
        began = time.perf_counter()
        small = ok(
            client.post(
                f"{api}/moves",
                json={"sourceWorkspaceKey": WORKSPACE, "targetWorkspaceKey": MOVE_TARGET,
                      "mapping": {"key": key, "expectedVersion": current["version"]},
                      "selection": {"objectIds": [str(item) for item in ids]}, "mode": "move",
                      "stage": "execute"},
            ),
            202,
        )
        with engine.connect() as connection:
            queued_before = [
                tuple(row)
                for row in connection.execute(
                    text("SELECT kind, state FROM jobs WHERE state IN ('queued', 'running')"
                         " AND sequence_id < (SELECT sequence_id FROM jobs WHERE id = :id)"),
                    {"id": small["id"]},
                ).all()
            ]
        seen = None
        while time.perf_counter() - began < 300:
            state = job(small["id"])
            mark = (state["state"], state["stage"])
            if mark != seen:
                timeline.append((round(time.perf_counter() - began, 2), *mark))
                seen = mark
            if state["state"] in ("completed", "failed", "cancelled"):
                break
            with engine.connect() as connection:
                blocked = connection.execute(
                    text("SELECT a.pid, a.wait_event_type, a.wait_event, left(a.query, 160)"
                         " FROM pg_stat_activity a WHERE a.datname = current_database()"
                         " AND a.wait_event_type = 'Lock'")
                ).all()
            if blocked:
                waits.append((round(time.perf_counter() - began, 2), [tuple(row) for row in blocked]))
            time.sleep(0.1)
    finally:
        worker.stop()
    facts["small move"] = {"timeline": timeline, "lock waits": waits[:20], "queued before": queued_before,
                           "result": state["state"], "counts": state.get("counts")}
    print(f"  20-record move: {timeline}; lock waits {len(waits)}", flush=True)
    event.remove(engine, "before_cursor_execute", before_statement)
    event.remove(engine, "after_cursor_execute", after_statement)
    facts["slow statements"] = slow
    return results, facts


EXPORT_FORMATS = ("jsonl", "csv", "xlsx")


def export_scenarios(client, engine: Engine, dataset: VolumeDataset) -> list[tuple[Measurement, int]]:
    """0.9 J1: the whole live workspace exported in each format with its relationships, timed once
    each (D56), with the rows each wrote. The export runs in this thread, so its statements are
    counted; the export worker's own thread is stopped first so it cannot take the job."""
    worker = client.app.state.export_worker
    worker.stop()
    types = [item["key"] for item in volume_model()["objectTypes"]]
    results = []
    for export_format in EXPORT_FORMATS:
        body = {
            "workspaceKey": WORKSPACE,
            "scope": {"types": [{"objectTypeKey": key} for key in types]},
            "include": {"relations": "withinScope"},
            "format": export_format,
        }
        queued = client.post("/api/v1/exports", json=body)
        assert queued.status_code == 202, queued.text
        with measure(engine) as cost:
            worker.run_until_idle()
        job = client.get(f"/api/v1/jobs/{queued.json()['id']}").json()
        assert job["state"] == "completed", job
        counts = job["output"]["counts"]
        records = sum(counts["records"].values())
        relations = sum(counts["relations"].values())
        measurement = Measurement(
            "live",
            f"export {export_format}: {records:,} records, {relations:,} relationships, "
            f"{job['output']['bytes'] / 1e6:,.1f} MB",
            200,
            cost.seconds * 1000,
            cost.statements,
            cost.rows_loaded,
        )
        results.append((measurement, records + relations))
    return results


def change_list_scenarios(client, engine: Engine, review: ReviewChangeSet, *, repeat: int) -> list[Measurement]:
    """P2a: both change lists of the review change set, paged every way a reviewer reaches a row."""
    results = []
    for records, extra in (("object", {}), ("relation", {"containment": "false"})):
        path = f"/api/v1/change-sets/{review.change_set_id}/{records}-changes"
        page = {"pageSize": PAGE_SIZE}
        total = client.get(path, params={**page, "includeTotal": True}).json()["totalCount"]
        middle = client.get(path, params={**page, "position": total // 2}).json()["prevCursor"]
        scenarios = [
            ("first page", page),
            ("last page by from=end, total", {**page, "from": "end", "includeTotal": True}),
            ("backward page from the middle", {**page, "cursor": middle}),
            ("position ¾ deep, total", {**page, "position": total * 3 // 4, "includeTotal": True}),
            ("kind filter (removed), total", {**page, "kind": "removed", "includeTotal": True}),
        ]
        if extra:
            scenarios.append(("containment edges left out, total", {**page, **extra, "includeTotal": True}))
        for scenario, params in scenarios:
            status, milliseconds, statements, rows = _timed(
                engine, lambda path=path, params=params: client.get(path, params=params), repeat
            )
            results.append(
                Measurement(
                    "change_set", f"{records} changes: {scenario}", status, milliseconds, statements, rows
                )
            )
    return results


def restructuring_scenarios(
    engine: Engine, dataset: VolumeDataset, *, repeat: int
) -> tuple[list[Measurement], int]:
    """C2: the heavy group moved under the small group as a node in the change set, so it and each
    of its items change type (its nodes stay nodes). Planning alone reads level by level; the
    preview also dry-runs every record's write, which it then rolls back. Returns the
    measurements and the number of records the plan changes."""
    from app.engine.change_sets.access import change_set_model, load_change_set
    from app.engine.operations.restructuring import (
        MoveOperation,
        Restructuring,
        _Planner,
        preview_restructuring,
    )

    request = Restructuring(MoveOperation(dataset.heavy_group_id, dataset.small_group_id, NODE))

    def plan_only() -> int:
        with Session(engine) as session:
            change_set = load_change_set(session, dataset.change_set_id)
            model = change_set_model(session, change_set)
            with measure(engine) as cost:
                plan = _Planner(session, change_set, model, request).plan()
            session.rollback()
        costs.append(cost)
        return len(plan.records)

    def preview() -> int:
        with Session(engine) as session, measure(engine) as cost:
            plan = preview_restructuring(session, dataset.change_set_id, request)
        assert plan.status == "ready", plan.summary()
        costs.append(cost)
        return len(plan.records)

    results, count = [], 0
    for scenario, call in (("plan", plan_only), ("preview with dry run", preview)):
        costs: list = []
        for _ in range(repeat + 1):
            count = call()
        timed = costs[1:] or costs
        results.append(
            Measurement(
                "change_set",
                f"restructuring {scenario}: {count:,} records",
                200,
                statistics.median(item.seconds * 1000 for item in timed),
                costs[-1].statements,
                costs[-1].rows_loaded,
            )
        )
    return results, count


def markdown_table(results: list[Measurement]) -> str:
    """One row per scenario, one ``ms · statements · rows`` column per context."""
    scenarios = list(dict.fromkeys(item.scenario for item in results))
    by_key = {(item.scenario, item.context): item for item in results}
    lines = [
        "| Request | Live | Change set | History |",
        "| --- | --- | --- | --- |",
    ]
    for scenario in scenarios:
        cells = []
        for context in CONTEXTS:
            item = by_key.get((scenario, context))
            cells.append(
                "—"
                if item is None
                else f"{item.milliseconds:,.1f} ms · {item.statements} · {item.rows_loaded:,}"
            )
        lines.append(f"| {scenario} | " + " | ".join(cells) + " |")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--scale", type=float, default=1.0, help="1 is the plan's full volume")
    parser.add_argument("--repeat", type=int, default=5, help="timed runs per request")
    parser.add_argument("--json", type=Path, default=None, help="also write results as JSON")
    parser.add_argument(
        "--only-restructuring",
        action="store_true",
        help="measure only the C2 restructuring planner (use --scale 0.024 for about 480 records)",
    )
    parser.add_argument(
        "--only-queries",
        action="store_true",
        help="measure only the 0.9 Q3 model-aware queries",
    )
    parser.add_argument(
        "--only-dated",
        action="store_true",
        help="measure only the 0.9 T1 dated reads",
    )
    parser.add_argument(
        "--only-publish",
        action="store_true",
        help="measure only the 0.9 T1 publish of a tenth of the items renamed",
    )
    parser.add_argument(
        "--only-change-lists",
        action="store_true",
        help="measure only the P2a change lists over the review change set",
    )
    parser.add_argument(
        "--only-events",
        action="store_true",
        help="measure only the 0.9 C10 event derivation and pull feed (turns model administration on)",
    )
    parser.add_argument(
        "--only-exports",
        action="store_true",
        help="measure only the 0.9 J1 exports of the whole live workspace, once per format",
    )
    parser.add_argument(
        "--only-deletion",
        action="store_true",
        help="measure only the 0.9 K2b deletion of about 100,000 records (D124), once",
    )
    parser.add_argument(
        "--only-consumer",
        action="store_true",
        help="measure only the 0.9 C3 consumer list reads, C4 XREF lookups and C14 batch resolve",
    )
    parser.add_argument(
        "--only-relation-columns",
        action="store_true",
        help="measure only the 0.11 X6 lists read with relation columns, at 20 and 200 rows",
    )
    parser.add_argument(
        "--only-move",
        action="store_true",
        help="measure only the 0.11 X5 move of the whole workspace into another model, once",
    )
    arguments = parser.parse_args()

    import postgres_server
    import seeds

    from app.db import get_engine

    publish_error: Exception | None = None
    if arguments.only_events:
        os.environ["MODEL_ADMIN_MUTATIONS_ENABLED"] = "true"
        os.environ.update(SUBSCRIPTION_SETTINGS)
    if arguments.only_move:
        # Installing the target's model and the move itself are model administration (D14).
        os.environ["MODEL_ADMIN_MUTATIONS_ENABLED"] = "true"
    server_started = postgres_server.start()
    try:
        with tempfile.TemporaryDirectory() as directory:
            # Before the application is first imported (app.main builds one): export files (0.9
            # J1) stay in this run's directory, never the project's var/.
            os.environ.setdefault("JOB_FILE_DIR", str(Path(directory) / "job-files"))
            started = time.perf_counter()
            # A clone of the volume seed at this scale, built once (tests/seeds.py, H1).
            with volume_app(Path(directory), scaled_shape(arguments.scale)) as (client, dataset):
                seeded = time.perf_counter() - started
                engine = get_engine()
                server_version = engine.dialect.server_version_info
                if arguments.only_restructuring:
                    results, _count = restructuring_scenarios(engine, dataset, repeat=arguments.repeat)
                elif arguments.only_consumer:
                    results = consumer_scenarios(client, engine, dataset, repeat=arguments.repeat)
                    results += consumer_xref_scenarios(client, engine, dataset, repeat=arguments.repeat)
                    results += consumer_resolve_scenarios(client, engine, dataset, repeat=arguments.repeat)
                elif arguments.only_events:
                    results, told = event_scenarios(client, engine, dataset, repeat=arguments.repeat)
                    dataset.counts["events told by the heavy group's rename"] = told
                elif arguments.only_deletion:
                    results = deletion_scenarios(client, engine, dataset)
                elif arguments.only_move:
                    results, facts = move_scenarios(client, engine, dataset)
                    dataset.counts["move"] = facts
                elif arguments.only_exports:
                    results = [item for item, _rows in export_scenarios(client, engine, dataset)]
                elif arguments.only_relation_columns:
                    results = relation_column_scenarios(client, engine, dataset, repeat=arguments.repeat)
                elif arguments.only_dated:
                    results = dated_scenarios(client, engine, dataset, repeat=arguments.repeat)
                elif arguments.only_publish:
                    results = publish_scenario(client, engine, dataset)
                elif arguments.only_queries:
                    results = [
                        item
                        for context in CONTEXTS
                        for item in query_scenarios(
                            client, engine, dataset, context, repeat=arguments.repeat
                        )
                    ]
                else:
                    results = [] if arguments.only_change_lists else run_scenarios(
                        client, engine, dataset, repeat=arguments.repeat
                    )
                    # Seeded after the other scenarios, so none of them runs beside it.
                    review = seed_review_change_set(engine, dataset)
                    dataset.counts.update(
                        {f"review.{key}": value for key, value in review.counts.items()}
                    )
                    results += change_list_scenarios(client, engine, review, repeat=arguments.repeat)
                    if not arguments.only_change_lists:
                        results += known_exceptions(client, engine, dataset, repeat=arguments.repeat)
                        # Last: it publishes, so live data and the active publication change. A
                        # failure is reported after the table, which it must not lose.
                        try:
                            results += publish_scenario(client, engine, dataset)
                        except Exception as error:  # noqa: BLE001
                            publish_error = error
    finally:
        if server_started:
            postgres_server.stop()

    seed = "; ".join(f"{name} {outcome}" for name, outcome, _seconds in seeds.ACTIVITY)
    print(
        f"Scale {arguments.scale} · {dataset.counts} · seed ready in {seeded:.1f} s ({seed}) · "
        f"median of {arguments.repeat} runs · page size {PAGE_SIZE}"
    )
    print(
        f"Python {platform.python_version()} · PostgreSQL "
        f"{'.'.join(str(part) for part in server_version)} · {platform.platform()}"
    )
    print()
    print(markdown_table(results))
    if publish_error is not None:
        print(f"\nThe publish scenario failed: {str(publish_error)[:2000]}")
    if arguments.json:
        arguments.json.write_text(
            json.dumps(
                {"counts": dataset.counts, "results": [item.__dict__ for item in results]},
                indent=2,
            )
        )


if __name__ == "__main__":
    main()
