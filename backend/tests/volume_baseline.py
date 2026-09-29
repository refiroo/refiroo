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
import sqlite3
import statistics
import sys
import tempfile
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

sys.path.insert(0, str(Path(__file__).resolve().parent))

from volume_fixture import (
    CELLS_BY_COLUMN,
    GROUP,
    GROUP_CONTAINS_ITEM,
    ITEM,
    ITEM_CITES_GROUP,
    MARKS_BY_COLUMN,
    MATRIX_APPLICATION,
    NODE,
    NODE_HAS_CHILD,
    RANK,
    SHELF,
    WORKSPACE,
    ReviewChangeSet,
    VolumeDataset,
    measure,
    scaled_shape,
    seed_review_change_set,
    seed_volume,
    volume_model,
)

PAGE_SIZE = 20
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
    engine: Engine, call: Callable[[], Any], repeat: int, before: Callable[[], None] | None = None
) -> tuple[int, float, int, int]:
    """Run ``call`` once to warm up, then ``repeat`` times; return the last run's cost.

    The time is the median of the timed runs, or the warm-up run's when ``repeat`` is 0.
    """
    timings = []
    status, statements, rows = 0, 0, 0
    for run in range(repeat + 1):
        if before is not None:
            before()
        with measure(engine) as cost:
            response = call()
        status = response.status_code
        if status >= 400:
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
        )
        for scenario, path, params in scenarios:
            status, milliseconds, statements, rows = _timed(
                engine, lambda path=path, params=params: client.get(path, params=params), repeat
            )
            results.append(
                Measurement(context, scenario, status, milliseconds, statements, rows)
            )

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
    parser.add_argument("--workdir", type=Path, default=None, help="keep the database here")
    parser.add_argument("--json", type=Path, default=None, help="also write results as JSON")
    parser.add_argument(
        "--only-restructuring",
        action="store_true",
        help="measure only the C2 restructuring planner (use --scale 0.024 for about 480 records)",
    )
    parser.add_argument(
        "--only-change-lists",
        action="store_true",
        help="measure only the P2a change lists over the review change set",
    )
    arguments = parser.parse_args()

    workdir = arguments.workdir or Path(tempfile.mkdtemp(prefix="rdm-volume-"))
    workdir.mkdir(parents=True, exist_ok=True)
    database = workdir / "volume.db"
    database.unlink(missing_ok=True)
    model_path = workdir / "volume-model.json"
    model_path.write_text(json.dumps(volume_model()))
    os.environ["DATABASE_URL"] = f"sqlite:///{database}"
    os.environ["RDM_MODEL_PATH"] = str(model_path)

    from fastapi.testclient import TestClient

    from app.db import get_engine
    from app.main import create_app

    with TestClient(create_app()) as client:
        engine = get_engine()
        started = time.perf_counter()
        dataset = seed_volume(engine, scaled_shape(arguments.scale))
        seeded = time.perf_counter() - started
        if arguments.only_restructuring:
            results, _count = restructuring_scenarios(engine, dataset, repeat=arguments.repeat)
        else:
            results = [] if arguments.only_change_lists else run_scenarios(
                client, engine, dataset, repeat=arguments.repeat
            )
            # Seeded after the other scenarios, so none of them runs beside it.
            review = seed_review_change_set(engine, dataset)
            dataset.counts.update({f"review.{key}": value for key, value in review.counts.items()})
            results += change_list_scenarios(client, engine, review, repeat=arguments.repeat)
            if not arguments.only_change_lists:
                results += known_exceptions(client, engine, dataset, repeat=arguments.repeat)

    print(
        f"Scale {arguments.scale} · {dataset.counts} · seeded in {seeded:.1f} s · "
        f"median of {arguments.repeat} runs · page size {PAGE_SIZE}"
    )
    print(
        f"Python {platform.python_version()} · SQLite {sqlite3.sqlite_version} · "
        f"{platform.platform()} · database {database}"
    )
    print()
    print(markdown_table(results))
    if arguments.json:
        arguments.json.write_text(
            json.dumps(
                {"counts": dataset.counts, "results": [item.__dict__ for item in results]},
                indent=2,
            )
        )


if __name__ == "__main__":
    main()
