"""0.9.0-alpha.1 PG3b (PG-D17): what a batch chunk costs, counted at two seeded sizes.

A chunk's items are decided in memory and written in bulk, so its statements are a constant: at
both seeded sizes and for 100 or 500 items they stay within a few of each other, never one per item
or per stored record. What varies is an ``IN`` list for every 500 values the items name, and an
``UPDATE`` for each set of columns the items change (an item that moves, one that keeps its parent,
a value saved again unchanged), which depends on what the items find. Counted on the volume
fixture, live and in the fixture's change set, for creates whose parent is named by key and for
upserts of which half update an existing record, most of them moving it to another group, and
relationship items (0.9 B3, D35): half relate a created item to a group, half replace a created
item's citations with two groups, every record named by key; and ``ensureNoRelation`` items over
them (0.9 K3, D129), half removing a relationship and half finding none.

The seconds a chunk of 500 items takes are recorded beside the counts: a live write in a background
job's workspace waits for one chunk at most (PG3), so that is the longest it waits. They are not
bounded here; PG5's full-size run confirms them.

A run of cascading delete items (0.9 K2b, D124) is counted the same way, as a preview so the seeded
data stays: two or eight groups, each run holding the heavy group with its items and seven-level
node hierarchy and groups with matrix cells, so the statements may not grow with the number of
items, the records their closures hold, or the closures' depth. The count includes the worker's
claim, the matrix states' upkeep and the preview's record.
"""

import json
from typing import Any

import pytest
from sqlalchemy import event, text
from volume_fixture import (
    APPLICATION,
    CODE,
    GROUP,
    GROUP_HAS_CELL,
    ITEM,
    ITEM_CITES_GROUP,
    RANK,
    WORKSPACE,
    measure,
    scaled_shape,
    volume_app,
)

from app.db import get_engine

SIZES = {"small": scaled_shape(0.005), "large": scaled_shape(0.02)}
COUNTS = (100, 500)
CONTEXTS = ("live", "change set")
# Statements per chunk, measured 2026-10-02 at 30-32 and 44-46 live, 43-44 and 47-49 in the change
# set (the PG3b record). Before PG3b an item cost about its single write: 20 statements live.
# Relationship items, measured 2026-10-03 at 33 and 40 live, 36 and 43 in the change set (B3).
# A previewed run of cascading deletes, measured 2026-10-09 at 47-48 live and 60-64 in the change
# set (0.9 K2b); the matrix states' upkeep reads a shape's rows only where the run touches them.
# ensureNoRelation items, measured 2026-10-09 at 32 and 36 live, 36 and 41 in the change set (K3).
# Relationship items with the citation binding's candidates on both ends, measured 2026-10-10 at 35
# and 42 live, 38 and 45 in the change set (0.9 K7): one statement per restricted end and chunk.
# Every budget gained one in 0.12 I1: the request's token lookup (its key and principal in one
# statement), whatever the chunk holds.
BUDGET = {("live", "creates"): 35, ("live", "upserts"): 49, ("change set", "creates"): 47,
          ("change set", "upserts"): 53, ("live", "relations"): 45, ("change set", "relations"): 48,
          ("live", "deletes"): 51, ("change set", "deletes"): 67, ("live", "apart"): 41,
          ("change set", "apart"): 46}
# How far apart the counts may be: IN lists past 500 values, UPDATE statements per set of columns.
# A relationship item names two or three records, so 500 of them pass 500 values more often.
ALLOWANCE = {"creates": 4, "upserts": 4, "relations": 8, "deletes": 4, "apart": 8}
DELETE_COUNTS = (2, 8)


def _parent(index: int) -> dict[str, Any]:
    return {"objectTypeKey": GROUP, "key": {"attributeTypeKey": CODE, "value": f"GROUP-{index % 10:06d}"}}


def creates(count: int, prefix: str) -> list[dict[str, Any]]:
    return [
        {
            "op": "create",
            "applicationKey": APPLICATION,
            "objectTypeKey": ITEM,
            "name": f"New {index}",
            "parent": _parent(index),
            "attributes": [{"attributeTypeKey": CODE, "value": f"{prefix}-{index:06d}"}],
        }
        for index in range(count)
    ]


def upserts(count: int, prefix: str, first: int) -> list[dict[str, Any]]:
    """Every other item names an existing item from ``first`` on (its rank changes, and it moves
    to one of the first ten groups); the rest are new."""
    return [
        {
            "op": "upsert",
            "applicationKey": APPLICATION,
            "objectTypeKey": ITEM,
            "key": {"attributeTypeKey": CODE},
            "name": f"Upserted {index}",
            "parent": _parent(index + 1),
            "attributes": [
                {
                    "attributeTypeKey": CODE,
                    "value": f"ITEM-{first + index // 2:06d}" if index % 2 == 0 else f"{prefix}-{index:06d}",
                },
                {"attributeTypeKey": RANK, "value": 11},
            ],
        }
        for index in range(count)
    ]


def relations(count: int, prefix: str) -> list[dict[str, Any]]:
    """Relationship items over the records ``creates(count, prefix)`` made."""

    def item(index: int) -> dict[str, Any]:
        return {"objectTypeKey": ITEM, "key": {"attributeTypeKey": CODE, "value": f"{prefix}-{index:06d}"}}

    return [
        {"op": "createRelation", "relationTypeKey": ITEM_CITES_GROUP, "from": item(index), "to": _parent(index + 3)}
        if index % 2 == 0
        else {
            "op": "replaceRelationSet",
            "relationTypeKey": ITEM_CITES_GROUP,
            "fromObjectTypeKey": ITEM,
            "toObjectTypeKey": GROUP,
            "direction": "outgoing",
            "anchor": item(index),
            "targets": [{"object": _parent(index + 4)}, {"object": _parent(index + 5)}],
        }
        for index in range(count)
    ]


def apart(count: int, prefix: str) -> list[dict[str, Any]]:
    """``ensureNoRelation`` items over the records ``relations(count, prefix)`` related (0.9 K3):
    half remove a relationship it made, half name a group the record is not related to."""

    def item(index: int) -> dict[str, Any]:
        return {"objectTypeKey": ITEM, "key": {"attributeTypeKey": CODE, "value": f"{prefix}-{index:06d}"}}

    return [
        {"op": "ensureNoRelation", "relationTypeKey": ITEM_CITES_GROUP, "from": item(index),
         "to": _parent(index + 3 if index % 2 == 0 else index + 9)}
        for index in range(count)
    ]


@pytest.fixture(scope="module")
def measured(tmp_path_factory) -> dict[tuple[str, str, str, int], dict[str, Any]]:
    results: dict[tuple[str, str, str, int], dict[str, Any]] = {}
    for size, shape in SIZES.items():
        directory = tmp_path_factory.mktemp(f"batch-statements-{size}")
        with volume_app(directory, shape) as (client, dataset):
            engine = get_engine()
            # The application's worker thread would add its own statements to the counts.
            client.app.state.job_worker.stop()

            def context(label: str) -> dict[str, Any]:
                if label == "live":
                    return {"workspaceKey": WORKSPACE}
                version = client.get(f"/api/v1/change-sets/{dataset.change_set_id}").json()["version"]
                return {"changeSetId": dataset.change_set_id, "expectedChangeSetVersion": version}

            for label in CONTEXTS:
                # The change set's records are publication 1's: live updates leave them as they were.
                first = 0
                for count in COUNTS:
                    tag = f"{label[0].upper()}{count}"
                    for kind, items in (
                        ("creates", creates(count, f"C{tag}")),
                        ("upserts", upserts(count, f"U{tag}", first)),
                        ("relations", relations(count, f"C{tag}")),
                        ("apart", apart(count, f"C{tag}")),
                    ):
                        body = {"policy": "independent", "run": "inline", "onExisting": "overwrite",
                                "items": items, **context(label)}
                        with measure(engine) as cost:
                            response = client.post("/api/v1/batches", json=body)
                        assert response.status_code == 200, response.text
                        results[(size, label, kind, count)] = {"cost": cost, "job": response.json()["job"]}
                    first += count // 2
            groups = _groups_to_delete(engine, dataset)
            for label in CONTEXTS:
                for count in DELETE_COUNTS:
                    chosen = [groups[0], groups[2]] if count == 2 else groups[:count]
                    items = [
                        {
                            "op": "delete",
                            "target": {"id": group_id},
                            "expectedVersion": _version(client, label, dataset, group_id),
                            "cascade": True,
                        }
                        for group_id in chosen
                    ]
                    body = {"policy": "independent", "run": "background", "stage": "preview",
                            "items": items, **context(label)}
                    queued = client.post("/api/v1/batches", json=body)
                    assert queued.status_code == 202, queued.text
                    with measure(engine) as cost:
                        client.app.state.job_worker.run_until_idle()
                    job = client.get(f"/api/v1/jobs/{queued.json()['id']}").json()
                    client.post(f"/api/v1/jobs/{job['id']}/cancel")
                    results[(size, label, "deletes", count)] = {"cost": cost, "job": job}
    print("\nPG3b statements per chunk (seconds):")
    for (size, label, kind, count), result in sorted(results.items()):
        print(f"  {size:5} {label:10} {kind:7} {count:3} items: {result['cost'].statements} "
              f"({result['cost'].seconds:.2f} s)")
    return results


def _groups_to_delete(engine: Any, dataset: Any) -> list[str]:
    """The heavy group, the small one, and six others, which hold matrix cells."""
    with engine.connect() as connection:
        others = connection.execute(
            text(
                "SELECT id FROM objects WHERE workspace_key = :workspace AND object_type_key = :type"
                " AND id NOT IN (:heavy, :cited, :small) ORDER BY id LIMIT 6"
            ),
            {"workspace": WORKSPACE, "type": GROUP, "heavy": dataset.heavy_group_id,
             "cited": dataset.cited_group_id, "small": dataset.small_group_id},
        ).scalars().all()
    return [dataset.heavy_group_id, dataset.small_group_id, *others]


def _version(client: Any, label: str, dataset: Any, group_id: str) -> int:
    params = {"workspaceKey": WORKSPACE} if label == "live" else {"changeSetId": dataset.change_set_id}
    response = client.get(f"/api/v1/objects/{GROUP}/{group_id}", params=params)
    assert response.status_code == 200, response.text
    return response.json()["version"]


@pytest.mark.parametrize("kind", ["creates", "upserts", "relations", "apart"])
@pytest.mark.parametrize("label", CONTEXTS)
def test_a_chunk_costs_a_constant_number_of_statements(measured, label, kind):
    counted = {
        (size, count): measured[(size, label, kind, count)]["cost"].statements
        for size in SIZES
        for count in COUNTS
    }
    # Four times the data and five times the items: a few statements apart, not one per item.
    assert max(counted.values()) - min(counted.values()) <= ALLOWANCE[kind], counted
    assert max(counted.values()) <= BUDGET[(label, kind)], counted


@pytest.mark.parametrize("label", CONTEXTS)
def test_every_item_is_applied(measured, label):
    for size in SIZES:
        for count in COUNTS:
            created = measured[(size, label, "creates", count)]["job"]
            assert (created["result"], created["counts"]["created"]) == ("applied", count), created
            upserted = measured[(size, label, "upserts", count)]["job"]
            assert upserted["result"] == "applied", upserted
            counts = upserted["counts"]
            assert counts["created"] + counts["updated"] == count, counts
            assert counts["updated"] > count // 3, counts
            related = measured[(size, label, "relations", count)]["job"]
            assert related["result"] == "applied", related
            assert (related["counts"]["created"], related["counts"]["updated"]) == (
                count // 2,
                count // 2,
            ), related
            kept_apart = measured[(size, label, "apart", count)]["job"]
            assert kept_apart["result"] == "applied", kept_apart
            assert (kept_apart["counts"]["deleted"], kept_apart["counts"]["unchanged"]) == (
                count // 2,
                count // 2,
            ), kept_apart


@pytest.mark.parametrize("label", CONTEXTS)
def test_a_run_of_cascading_deletes_costs_a_constant_number_of_statements(measured, label):
    """0.9 K2b (D124): the same statements for two groups or eight, at both sizes, whatever their
    closures hold."""
    counted = {
        (size, count): measured[(size, label, "deletes", count)]["cost"].statements
        for size in SIZES
        for count in DELETE_COUNTS
    }
    assert max(counted.values()) - min(counted.values()) <= ALLOWANCE["deletes"], counted
    assert max(counted.values()) <= BUDGET[(label, "deletes")], counted
    for size in SIZES:
        for count in DELETE_COUNTS:
            job = measured[(size, label, "deletes", count)]["job"]
            assert job["state"] == "awaiting_confirmation", job
            assert job["preview"]["counts"]["deleted"] == count, job["preview"]
            assert job["preview"]["deletion"]["objectCount"] > count, job["preview"]


# The closure's walk at two sizes where its owned records are many: four times the data, and in
# the change set about four times the matrix cells its groups own.
WALK_SIZES = {"small": scaled_shape(0.01), "large": scaled_shape(0.04)}


@pytest.fixture(scope="module")
def walked(tmp_path_factory) -> dict[str, tuple[int, int, int]]:
    """Per size: the buffers a change set's deletion walk of eight cell-owning groups read, the
    records it reached, and the walks of matrix cells its upkeep ran. The walk runs once more under EXPLAIN in a savepoint on the raw cursor."""
    results = {}
    for size, shape in WALK_SIZES.items():
        with volume_app(tmp_path_factory.mktemp(f"deletion-walk-{size}"), shape) as (client, dataset):
            engine = get_engine()
            client.app.state.job_worker.stop()
            with engine.connect() as connection:
                groups = connection.execute(
                    text(
                        "SELECT DISTINCT from_object_id FROM object_relations"
                        " WHERE relation_type_key = :cell ORDER BY from_object_id LIMIT 8"
                    ),
                    {"cell": GROUP_HAS_CELL},
                ).scalars().all()
            version = client.get(f"/api/v1/change-sets/{dataset.change_set_id}").json()["version"]
            items = [
                {"op": "delete", "target": {"id": group}, "cascade": True,
                 "expectedVersion": _version(client, "change set", dataset, group)}
                for group in groups
            ]
            body = {"changeSetId": dataset.change_set_id, "expectedChangeSetVersion": version,
                    "policy": "independent", "run": "background", "stage": "preview", "items": items}
            walks: list[tuple[int, int]] = []
            matrix_walks: list[str] = []

            def walk(
                connection, cursor, statement, parameters, context, executemany,
                walks=walks, matrix_walks=matrix_walks,
            ):
                if statement.lstrip().startswith("WITH RECURSIVE matrix_descendants"):
                    matrix_walks.append(statement)
                if statement.lstrip().startswith("WITH RECURSIVE reach"):
                    with cursor.connection.cursor() as probe:
                        probe.execute("SAVEPOINT walk")
                        probe.execute("EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON) " + statement, parameters)
                        plan = probe.fetchone()[0]
                        probe.execute("ROLLBACK TO SAVEPOINT walk")
                    plan = (json.loads(plan) if isinstance(plan, str) else plan)[0]["Plan"]
                    walks.append((plan["Shared Hit Blocks"] + plan["Shared Read Blocks"], plan["Plans"][0]["Actual Rows"]))

            queued = client.post("/api/v1/batches", json=body)
            assert queued.status_code == 202, queued.text
            event.listen(engine, "before_cursor_execute", walk)
            try:
                client.app.state.job_worker.run_until_idle()
            finally:
                event.remove(engine, "before_cursor_execute", walk)
            assert walks, f"{size}: the preview did not walk"
            results[size] = (*map(sum, zip(*walks, strict=True)), len(matrix_walks))
    return results


def test_the_closures_walk_reads_per_record_reached_whatever_the_data(walked):
    """0.9 R (R-F26): deleting about 100,000 records in a change set spent over 3 minutes in the
    closure's walk: for each record reached, its required owned records were found by reading every
    record of the owned type in the change set, which grows with the data. Deleting eight groups
    reads about the same buffers at four times the data (measured +4 %; before the fix +48 %)."""
    (small, _, _), (large, _, _) = walked["small"], walked["large"]
    assert large <= 1.25 * small, walked


def test_a_change_sets_deletion_walks_no_matrix_cells_under_its_tombstones(walked):
    """0.9 R (R-F27): deleting about 100,000 records in a change set spent 105 s walking the matrix
    cells under each deleted record, chunk by chunk, and found none: what a tombstone held was
    deleted with it, each a candidate itself. A deletion walks from no tombstone."""
    assert [matrix_walks for _blocks, _reached, matrix_walks in walked.values()] == [0, 0], walked
