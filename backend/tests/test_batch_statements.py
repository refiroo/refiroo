"""0.9.0-alpha.1 PG3b (PG-D17): what a batch chunk costs, counted at two seeded sizes.

A chunk's items are decided in memory and written in bulk, so its statements are a constant: at
both seeded sizes and for 100 or 500 items they stay within a few of each other, never one per item
or per stored record. What varies is an ``IN`` list for every 500 values the items name, and an
``UPDATE`` for each set of columns the items change (an item that moves, one that keeps its parent,
a value saved again unchanged), which depends on what the items find. Counted on the volume
fixture, live and in the fixture's change set, for creates whose parent is named by key and for
upserts of which half update an existing record, most of them moving it to another group.

The seconds a chunk of 500 items takes are recorded beside the counts: a live write in a background
job's workspace waits for one chunk at most (PG3), so that is the longest it waits. They are not
bounded here; PG5's full-size run confirms them.
"""

from typing import Any

import pytest
from volume_fixture import (
    APPLICATION,
    CODE,
    GROUP,
    ITEM,
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
BUDGET = {("live", "creates"): 34, ("live", "upserts"): 48, ("change set", "creates"): 46,
          ("change set", "upserts"): 52}
# How far apart the counts may be: IN lists past 500 values, UPDATE statements per set of columns.
ALLOWANCE = 4


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
                    ):
                        body = {"policy": "independent", "run": "inline", "onExisting": "overwrite",
                                "items": items, **context(label)}
                        with measure(engine) as cost:
                            response = client.post("/api/v1/batches", json=body)
                        assert response.status_code == 200, response.text
                        results[(size, label, kind, count)] = {"cost": cost, "job": response.json()["job"]}
                    first += count // 2
    print("\nPG3b statements per chunk (seconds):")
    for (size, label, kind, count), result in sorted(results.items()):
        print(f"  {size:5} {label:10} {kind:7} {count:3} items: {result['cost'].statements} "
              f"({result['cost'].seconds:.2f} s)")
    return results


@pytest.mark.parametrize("kind", ["creates", "upserts"])
@pytest.mark.parametrize("label", CONTEXTS)
def test_a_chunk_costs_a_constant_number_of_statements(measured, label, kind):
    counted = {
        (size, count): measured[(size, label, kind, count)]["cost"].statements
        for size in SIZES
        for count in COUNTS
    }
    # Four times the data and five times the items: a few statements apart, not one per item.
    assert max(counted.values()) - min(counted.values()) <= ALLOWANCE, counted
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
