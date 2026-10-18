"""Base 0.11 V1 budget (D78): a workspace of 100,000 records migrated to another release, once.

The volume fixture's workspace (100,000 items under 10,000 groups, a node hierarchy, citations and
the relation matrix's records) is migrated to a release of its model that turns every item's rank
into a decimal and drops the node type with its records and relationships, raising the consumer
API's contract version as such a release must. The preview and the confirmed execution run through
the routes and the application's worker; recorded: each stage's time, the items by outcome, and that
the workspace runs the target with its values converted afterwards, and the time of a check of every
rule of the target over it (the scoped uniqueness walk included). Measured once, announced; the
time is a record, not a bound.
"""

import copy
import os
import time
from dataclasses import replace

from volume_fixture import (
    APPLICATION,
    FULL_SHAPE,
    GROUP_CONTAINS_NODE,
    NODE,
    NODE_HAS_CHILD,
    RANK,
    WORKSPACE,
    volume_app,
    volume_model,
)

# The full workspace, with a feed short enough that building the seed is about the records.
SHAPE = replace(FULL_SHAPE, feed_entries=10_000)


def _target() -> dict:
    model = copy.deepcopy(volume_model())
    model["release"]["version"] += "-v1-budget"
    next(a for a in model["attributeTypes"] if a["key"] == RANK)["valueType"] = "decimal"
    model["objectTypes"] = [t for t in model["objectTypes"] if t["key"] != NODE]
    model["relationTypes"] = [
        r for r in model["relationTypes"] if r["key"] not in {GROUP_CONTAINS_NODE, NODE_HAS_CHILD}
    ]
    model["objectTypeRelations"] = [
        p for p in model["objectTypeRelations"] if NODE not in (p["fromObjectTypeKey"], p["toObjectTypeKey"])
    ]
    application = next(a for a in model["applications"] if a["key"] == APPLICATION)
    application["objectTypeKeys"].remove(NODE)
    views = []
    for view in application["views"]:
        if view.get("objectTypeKey") == NODE:
            continue
        config = view.get("config", {})
        if NODE in config.get("objectTypeKeys", []):
            config["objectTypeKeys"].remove(NODE)
            config.get("childSort", {}).pop(NODE, None)
        views.append(view)
    application["views"] = views
    if application.get("defaultView") not in {v["key"] for v in views}:
        application["defaultView"] = views[0]["key"]
    for api in model.get("consumerApis", []):
        api["contractVersion"] += 1
    return model


def _wait(client, job_id: str, states: set[str]) -> dict:
    """The job once the application's worker thread has brought it to one of ``states``."""
    while True:
        job = client.get(f"/api/v1/jobs/{job_id}").json()
        if job["state"] in states:
            return job
        time.sleep(1)


def test_a_workspace_of_100000_records_migrates_once(tmp_path):
    os.environ["MODEL_ADMIN_MUTATIONS_ENABLED"] = "true"
    try:
        with volume_app(tmp_path, SHAPE) as (client, _dataset):
            draft = client.post("/api/v1/model-drafts", json={"name": "Budget", "model": _target()})
            assert draft.status_code == 201, draft.text
            installed = client.post(
                f"/api/v1/model-drafts/{draft.json()['id']}/installation",
                json={"expectedVersion": draft.json()["version"]},
            )
            assert installed.status_code == 201, installed.text
            current = client.get(f"/api/v1/workspaces/{WORKSPACE}/model").json()
            started = time.perf_counter()
            answer = client.post(
                f"/api/v1/workspaces/{WORKSPACE}/model/migrations",
                json={"targetReleaseId": installed.json()["id"], "expectedVersion": current["version"]},
            )
            assert answer.status_code == 202, answer.text
            job = _wait(client, answer.json()["id"], {"awaiting_confirmation", "failed"})
            preview = time.perf_counter() - started
            assert job["state"] == "awaiting_confirmation", job
            summary = job["migration"]
            assert summary["counts"]["refused"] == 0, summary
            assert summary["counts"]["conversion"] >= SHAPE.items
            assert summary["counts"]["loss"] > 0

            started = time.perf_counter()
            confirmed = client.post(
                f"/api/v1/jobs/{job['id']}/confirm",
                json={
                    "expectedVersion": summary["expectedVersion"],
                    "expectedFeedPosition": summary["feedPosition"],
                    "acceptLoss": True,
                },
            )
            assert confirmed.status_code == 202, confirmed.text
            done = _wait(client, job["id"], {"completed", "failed"})
            execution = time.perf_counter() - started
            assert done["state"] == "completed", done
            assert client.get(f"/api/v1/workspaces/{WORKSPACE}/model").json()["releaseId"] == (
                installed.json()["id"]
            )
            # Every rule of the release checked over the migrated workspace, as a migration touching
            # everything would: the scoped uniqueness walk took over 9 minutes here before V1
            # rewrote it.
            from app.db import SessionLocal
            from app.engine.model.compatibility import analyze_compatibility
            from app.engine.model.migrations import relaxed
            from app.engine.model.registry import resolve_model_snapshot

            with SessionLocal() as session:
                snapshot = resolve_model_snapshot(session, WORKSPACE)
                started = time.perf_counter()
                result = analyze_compatibility(
                    session,
                    relaxed(snapshot.model),
                    snapshot.model,
                    installed.json()["id"],
                    [WORKSPACE],
                )
                full_check = time.perf_counter() - started
                session.rollback()
            assert result.classification == "compatible", result.diagnostics
            print(
                f"\nV1 budget: preview {preview:.1f} s, execution {execution:.1f} s, "
                f"every rule checked {full_check:.1f} s, items {summary['counts']}"
            )
    finally:
        os.environ.pop("MODEL_ADMIN_MUTATIONS_ENABLED", None)
