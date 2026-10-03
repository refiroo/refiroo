"""Base 0.9 B1 budget (D13): batches on the Track S volume fixture cost no more than their single
writes.

An inline independent batch of 1,000 upserts (half new, half overwriting existing items) and an
atomic batch of 10,000 creates run live and in the fixture's change set. Since 0.9.0-alpha.1 PG3b
the items are decided through their single writes' rules and written in bulk, so an item costs a
small fraction of a statement (PG-D12); PG5 restated the bounds from its measurement. Re-sending
the same upserts writes nothing. The atomic batch runs through the
inline job's engine path, which B2's background run reuses, since the route caps a request at 1,000
items.

The statements per chunk are held at two seeded sizes by ``test_batch_statements`` (PG-D17), which
replaced this module's timed check that a change set item costs the same as the change set grows.
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

from app.db import SessionLocal, get_engine
from app.engine.jobs.inline import submit_inline_batch
from app.models.commands import BatchRequest

SHAPE = scaled_shape(0.005)
# Statements per item, measured at PG5 (2026-10-03): 0.06 per upsert with half of them updates and
# 0.01-0.02 per create, live and in a change set (B1, before PG3b's bulk writes: 20.5 and 34.0 per
# upsert). A chunk's statements are held exactly by ``test_batch_statements``.
ITEM_BUDGET = 0.1


def _parent(index: int) -> dict[str, Any]:
    return {"objectTypeKey": GROUP, "key": {"attributeTypeKey": CODE, "value": f"GROUP-{index % 10:06d}"}}


def upserts(count: int, prefix: str) -> list[dict[str, Any]]:
    """Every other item names one of the fixture's first 500 items (its rank changes); the rest
    are new."""
    return [
        {
            "op": "upsert",
            "applicationKey": APPLICATION,
            "objectTypeKey": ITEM,
            "key": {"attributeTypeKey": CODE},
            "name": f"Item {index}",
            "parent": _parent(index),
            "attributes": [
                {"attributeTypeKey": CODE, "value": f"ITEM-{index // 2:06d}" if index % 2 == 0 else f"{prefix}-{index:06d}"},
                {"attributeTypeKey": RANK, "value": 7},
            ],
        }
        for index in range(count)
    ]


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


@pytest.fixture(scope="module")
def measured(tmp_path_factory) -> dict[tuple[str, str], dict[str, Any]]:
    results: dict[tuple[str, str], dict[str, Any]] = {}
    directory = tmp_path_factory.mktemp("batch-volume")
    with volume_app(directory, SHAPE) as (client, dataset):
        engine = get_engine()

        def context(label: str) -> dict[str, Any]:
            if label == "live":
                return {"workspaceKey": WORKSPACE}
            version = client.get(f"/api/v1/change-sets/{dataset.change_set_id}").json()["version"]
            return {"changeSetId": dataset.change_set_id, "expectedChangeSetVersion": version}

        for label in ("live", "change set"):
            single = {
                "applicationKey": APPLICATION,
                "objectTypeKey": ITEM,
                "name": "Single",
                "parentObjectId": dataset.small_group_id,
                "attributes": [{"attributeTypeKey": CODE, "value": f"SINGLE-{label[0].upper()}"}],
                **context(label),
            }
            with measure(engine) as cost:
                response = client.post("/api/v1/objects", json=single)
            assert response.status_code == 201, response.text
            results[("single", label)] = {"cost": cost, "items": 1}
            body = {"policy": "independent", "run": "inline", "onExisting": "overwrite"}
            items = upserts(1000, f"NEW-{label[0].upper()}")
            request = {**body, "items": items, **context(label)}
            with measure(engine) as cost:
                response = client.post("/api/v1/batches", json=request)
            assert response.status_code == 200, response.text
            results[("upserts", label)] = {"cost": cost, "job": response.json()["job"], "items": 1000}
            request = {**body, "items": items, **context(label)}
            with measure(engine) as cost:
                response = client.post("/api/v1/batches", json=request)
            results[("resent", label)] = {"cost": cost, "job": response.json()["job"], "items": 1000}

            count = 10_000
            request = BatchRequest.model_validate(
                {"policy": "atomic", "run": "inline", "items": creates(count, f"A{count}{label[0]}"), **context(label)}
            )
            with SessionLocal() as session:
                with measure(engine) as cost:
                    job, _replayed = submit_inline_batch(
                        session, request, idempotency_key=None, retention_days=7
                    )
                counts = dict(job.counts)
            results[("creates", label)] = {"cost": cost, "job": {"result": job.result, "counts": counts}, "items": count}
    return results


@pytest.mark.parametrize("label", ["live", "change set"])
def test_items_cost_about_their_single_writes(measured, label):
    single = measured[("single", label)]["cost"].statements
    per_item = {}
    for kind in ("upserts", "creates"):
        result = measured[(kind, label)]
        assert result["job"]["result"] == "applied", result["job"]
        per_item[kind] = result["cost"].statements / result["items"]
        print(
            f"\nD13 {label} {kind}: {result['items']} items in {result['cost'].seconds:.1f} s, "
            f"{per_item[kind]:.2f} statements per item (single create {single})"
        )
    assert per_item["creates"] <= ITEM_BUDGET, (label, per_item, single)
    assert per_item["upserts"] <= ITEM_BUDGET, (label, per_item, single)
    counts = measured[("upserts", label)]["job"]["counts"]
    assert counts["created"] + counts["updated"] == 1000, counts
    if label == "live":
        assert counts["updated"] == 500, counts
    else:
        # The change set has deleted some of them: those upserts create the record again.
        assert 450 < counts["updated"] < 500, counts


@pytest.mark.parametrize("label", ["live", "change set"])
def test_resending_unchanged_items_writes_nothing(measured, label):
    resent = measured[("resent", label)]
    assert resent["job"]["counts"]["unchanged"] == 1000, resent["job"]
    # Reads only: fewer statements than the write (29 against 57 at PG5).
    assert resent["cost"].statements < measured[("upserts", label)]["cost"].statements
