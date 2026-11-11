"""Base 0.9 B2 budget: a 100,000-item background batch on the Track S volume fixture (§B7).

The batch is sent through the route and run by the application's worker thread, live and in the
fixture's change set, while single live writes are made beside it. Recorded per run: the
submission time (the job and its 100,000 inputs in one transaction), the worker's throughput, the
statements per item against the single write's, and the latency of the writes made meanwhile.

The latency is recorded, not bounded here: a live write in the job's workspace waits for one
chunk at most (0.9.0-alpha.1 PG3), and the time of one chunk is held at two seeded sizes beside its
statement counts (``test_batch_statements``, PG3b, PG-D17). PG5's run (2026-10-03) confirmed both
at full size: 100,000 items in 52 s live and 64 s in the change set, writes beside the job served
in 0.35 s at most. PG3b replaced this module's timed check that an item costs the same at the end
of the job as at its start; the rates by quarter are still recorded.
"""

import statistics
import time
from datetime import datetime
from typing import Any

import pytest
from test_batch_volume import SHAPE, creates
from volume_fixture import APPLICATION, CODE, ITEM, WORKSPACE, measure, volume_app

from app.db import get_engine

ITEMS = 100_000


@pytest.fixture(scope="module")
def measured(tmp_path_factory) -> dict[str, dict[str, Any]]:
    results: dict[str, dict[str, Any]] = {}
    directory = tmp_path_factory.mktemp("background-volume")
    with volume_app(directory, SHAPE) as (client, dataset):
        engine = get_engine()

        def context(label: str) -> dict[str, Any]:
            if label == "live":
                return {"workspaceKey": WORKSPACE}
            version = client.get(f"/api/v1/change-sets/{dataset.change_set_id}").json()["version"]
            return {"changeSetId": dataset.change_set_id, "expectedChangeSetVersion": version}

        single = {
            "applicationKey": APPLICATION,
            "objectTypeKey": ITEM,
            "name": "Single",
            "parentObjectId": dataset.small_group_id,
        }
        for label in ("live", "change set"):
            costs = {}
            for where in dict.fromkeys(("live", label)):
                write = {
                    **single,
                    **context(where),
                    "attributes": [
                        {"attributeTypeKey": CODE, "value": f"SINGLE-B2-{label[0]}-{where[0]}"}
                    ],
                }
                with measure(engine) as costs[where]:
                    assert client.post("/api/v1/objects", json=write).status_code == 201
            live_cost, single_cost = costs["live"], costs[label]
            body = {
                "policy": "independent",
                "run": "background",
                "items": creates(ITEMS, f"BG{label[0]}"),
                **context(label),
            }
            with measure(engine) as cost:
                started = time.perf_counter()
                response = client.post("/api/v1/batches", json=body)
                submitted = time.perf_counter() - started
                assert response.status_code == 202, response.text
                job_id = response.json()["id"]
                latencies: list[float] = []
                progress: list[tuple[float, int]] = []
                while (job := client.get(f"/api/v1/jobs/{job_id}").json())["state"] in {
                    "queued",
                    "running",
                }:
                    progress.append((time.perf_counter(), job["progress"]["processed"]))
                    number = len(latencies)
                    write = {
                        **single,
                        "name": f"Beside {number}",
                        "workspaceKey": WORKSPACE,
                        "attributes": [
                            {"attributeTypeKey": CODE, "value": f"BESIDE-{label[0]}-{number}"}
                        ],
                    }
                    began = time.perf_counter()
                    assert client.post("/api/v1/objects", json=write).status_code == 201
                    latencies.append(time.perf_counter() - began)
                    time.sleep(0.5)
            progress.append((time.perf_counter(), job["progress"]["processed"]))
            ran = (
                datetime.fromisoformat(job["finishedAt"]) - datetime.fromisoformat(job["startedAt"])
            ).total_seconds()
            results[label] = {
                "job": job,
                "submitted": submitted,
                "ran": ran,
                "per_item_statements": (cost.statements - live_cost.statements * len(latencies))
                / ITEMS,
                "single_statements": single_cost.statements,
                "latencies": latencies,
                "rates": _rates(progress),
            }
            print(
                f"\nB2 {label}: submit {submitted:.1f} s, run {ran:.0f} s "
                f"({ITEMS / max(ran, 1):.0f} items/s), "
                f"{results[label]['per_item_statements']:.1f} statements per item "
                f"(single create {single_cost.statements}); writes beside it: {len(latencies)} served"
                + (
                    f" (median {statistics.median(latencies):.2f} s, max {max(latencies):.2f} s)"
                    if latencies
                    else ""
                )
                + f"; ms per item by quarter {', '.join(f'{rate:.2f}' for rate in results[label]['rates'])}"
            )
    return results


def _rates(progress: list[tuple[float, int]]) -> list[float]:
    """Milliseconds per item over each quarter of the job, between the progress samples that
    bracket it (the polls are sparse while a write beside the job waits for the lock)."""
    rates = []
    for quarter in range(4):
        low, high = ITEMS * quarter // 4, ITEMS * (quarter + 1) // 4
        start, begun = max((sample for sample in progress if sample[1] <= low), default=progress[0])
        end, reached = min(
            (sample for sample in progress if sample[1] >= high), default=progress[-1]
        )
        rates.append((end - start) * 1000 / max(reached - begun, 1))
    return rates


@pytest.mark.parametrize("label", ["live", "change set"])
def test_a_background_batch_of_100000_items_runs_within_its_budget(measured, label):
    result = measured[label]
    job = result["job"]
    assert (job["state"], job["result"], job["counts"]["created"]) == (
        "completed",
        "applied",
        ITEMS,
    ), job
    # Each item costs no more than its single write; chunks add their outcomes and checkpoint.
    assert result["per_item_statements"] <= result["single_statements"], result
    # The writes beside it are recorded (see the module docstring), not bounded here.
    assert result["latencies"], result
