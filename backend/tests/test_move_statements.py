"""Base 0.11 X2 (D123, I28): what a move's dry run costs, counted at two selection sizes.

A move binds its selection in set statements and previews its items through the batch path, so
its statements are a constant: for 50 and for 500 selected records, each with a relationship whose
other end stays behind, they stay within a few of each other, never one per record. Counted on
generated A moved onto generated B, the binding and the preview together, as the worker runs them.
The full-volume time is X5's measurement.
"""

import sys
from uuid import uuid4

import layout
import pytest

sys.path.insert(0, str(layout.JOURNEYS))

from configurations import all_configurations
from scenario import W1, ok, world_for
from volume_fixture import measure

from app.db import get_engine

SIZES = (50, 500)
# Statements per dry run (binding, preview and record), measured 2026-10-18 at 124 for both sizes
# (X2): the two walks of the hierarchy ran once each, the tokens standing at its top.
BUDGET = 130
# How far apart the two counts may be: an IN list for every 500 values the items name.
ALLOWANCE = 6


def _tokens(world, count):
    """``count`` new token records, each related to a branch that stays behind; their IDs."""
    h5, prefix = world.ids["h5"], uuid4().hex[:6]
    relation = {
        "relationTypeKey": world.key("Bnn"),
        "direction": "incoming",
        "object": {"id": h5},
        "attributes": {world.key("Bnn.weight"): 1},
    }
    items = [
        {
            "op": "create",
            "applicationKey": world.app("K"),
            "objectTypeKey": world.key("K"),
            "name": f"Moved token {prefix} {index}",
            "attributes": [{"attributeTypeKey": world.key("K.code"), "value": f"M{prefix}{index}"}],
            "initialRelations": [relation],
        }
        for index in range(count)
    ]
    body = {"workspaceKey": W1, "policy": "atomic", "run": "inline", "items": items}
    batch = ok(world.api.post("/batches", body))
    return [item["id"] for item in batch["items"]]


def _mapping(world):
    """Generated B beside A, a mapping between them proposed and applied: the workspace and the
    mapping's key and version."""
    other = all_configurations()["generated-b"]
    release = world.install(other.model, name="Other model")
    target = f"site-{uuid4().hex[:8]}"
    body = {"key": target, "label": target, "modelReleaseId": release["id"]}
    ok(world.api.post("/workspaces", body), 201)
    key = f"map-{uuid4().hex[:8]}"
    body = {"key": key, "name": "Move", "sourceWorkspaceKey": W1, "targetWorkspaceKey": target}
    ok(world.api.post("/model-mappings", body), 201)
    inference = {"sourceWorkspaceKey": W1, "targetWorkspaceKey": target}
    ok(world.api.post(f"/model-mappings/{key}/inference", inference), 202)
    world.api.client.app.state.job_worker.run_until_idle()
    version = ok(world.api.get(f"/model-mappings/{key}"))["version"]
    applied = ok(
        world.api.post(f"/model-mappings/{key}/inference/application", {"expectedVersion": version})
    )
    return target, key, applied["version"]


@pytest.fixture(scope="module")
def measured():
    configuration = all_configurations()["generated-a"]
    found = {}
    with world_for(configuration) as world:
        target, key, version = _mapping(world)
        worker = world.api.client.app.state.job_worker
        for size in SIZES:
            ids = _tokens(world, size)
            body = {
                "sourceWorkspaceKey": W1,
                "targetWorkspaceKey": target,
                "mapping": {"key": key, "expectedVersion": version},
                "selection": {"objectIds": ids},
            }
            job = ok(world.api.post("/moves", body), 202)
            with measure(get_engine()) as cost:
                worker.run_until_idle()
            found[size] = (cost.statements, ok(world.api.get(f"/jobs/{job['id']}")))
    return found


def test_a_dry_run_costs_a_constant_number_of_statements(measured):
    counted = {size: statements for size, (statements, _job) in measured.items()}
    # Ten times the records: a few statements apart, not one per record.
    assert max(counted.values()) - min(counted.values()) <= ALLOWANCE, counted
    assert max(counted.values()) <= BUDGET, counted


def test_every_record_and_relationship_has_its_row(measured):
    for size, (_statements, job) in measured.items():
        assert job["state"] == "completed", job
        summary = job["move"]
        assert summary["rows"] == 2 * size, summary
        assert summary["counts"]["create"] == size, summary
        assert {r["code"]: r["count"] for r in summary["reasons"]} == {
            "RELATION_TARGET_LEFT_BEHIND": size
        }, summary
