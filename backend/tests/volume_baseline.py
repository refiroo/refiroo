"""Track S read baseline (Base 0.8 S1) over the volume fixture.

Runs the same requests in live, draft and history contexts and records, per request, the wall time
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
    GROUP,
    GROUP_CONTAINS_ITEM,
    ITEM,
    ITEM_CITES_GROUP,
    NODE_HAS_CHILD,
    RANK,
    WORKSPACE,
    VolumeDataset,
    measure,
    scaled_shape,
    seed_volume,
    volume_model,
)

PAGE_SIZE = 20
CONTEXTS = ("live", "draft", "history")


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
    if context == "draft":
        return {"workspaceDraftId": dataset.draft_id}
    return {"workspaceRevisionId": dataset.revision_id}


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
    from app.services.cursors import encode_cursor
    from app.services.model.compiler import parse_model
    from app.services.objects import build_object_query
    from app.services.pagination import _row_position, cursor_sort
    from app.services.snapshot_reads import (
        build_snapshot_object_query,
        draft_context,
        object_scope,
        revision_context,
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
                draft_context(session, dataset.draft_id)
                if context == "draft"
                else revision_context(session, dataset.revision_id)
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
    ]


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
    """Measure every read in each context, then one live and one draft write."""
    results = []
    for context in CONTEXTS:
        for scenario, path, params in _read_scenarios(engine, context, dataset):
            status, milliseconds, statements, rows = _timed(
                engine, lambda path=path, params=params: client.get(path, params=params), repeat
            )
            results.append(
                Measurement(context, scenario, status, milliseconds, statements, rows)
            )

    path = f"/api/v1/objects/{ITEM}/{dataset.edited_item_id}"
    state: dict[str, Any] = {}

    def draft_versions() -> None:
        record = client.get(path, params={"workspaceDraftId": dataset.draft_id}).json()
        draft = client.get(f"/api/v1/workspace-drafts/{dataset.draft_id}").json()
        state.update(record=record["version"], draft=draft["version"])
        state["name"] = f"Edited {record['version']}"

    def draft_write():
        return client.patch(
            path,
            json={
                "name": state["name"],
                "expectedVersion": state["record"],
                "workspaceDraftId": dataset.draft_id,
                "expectedWorkspaceDraftVersion": state["draft"],
            },
        )

    status, milliseconds, statements, rows = _timed(engine, draft_write, repeat, draft_versions)
    results.append(Measurement("draft", "write: rename one record", status, milliseconds, statements, rows))

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
    return results


def markdown_table(results: list[Measurement]) -> str:
    """One row per scenario, one ``ms · statements · rows`` column per context."""
    scenarios = list(dict.fromkeys(item.scenario for item in results))
    by_key = {(item.scenario, item.context): item for item in results}
    lines = [
        "| Request | Live | Draft | History |",
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
        results = run_scenarios(client, engine, dataset, repeat=arguments.repeat)

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
