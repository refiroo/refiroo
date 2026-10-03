"""0.9.0-alpha.1 PG3b: batch items decided in memory and written in bulk, beside other writers.

A bulk write that fails on a row the rules could not see is redone item by item (PG-D15); that case
is the unit test ``tests/unit/engine/jobs/test_batches.py`` (H4d-1). A chunk holds the workspace lock from its first
read to its commit (PG-D14), so a unique value raced by a single write and a chunk item is given
once. A record's version is compared in memory now, not claimed by a conditional ``UPDATE``, so
two updates racing on one version are shown to be refused as before. And a chunk checks its release before it writes any matrix state, so an activation that
drops a matrix shape beside a chunk ends neither in a deadlock: the chunk fails
``model_release_changed``.
"""

import threading
from concurrent.futures import ThreadPoolExecutor
from typing import Any

import pytest
from sqlalchemy import func, select
from test_pg3_concurrency import (  # noqa: F401 - fixtures
    HOLD_TIMEOUT,
    WORKSPACE_LOCK,
    at_commit,
    at_lock,
    client,
    codelist,
    created,
    domain,
    job,
    post_object,
    race,
    refused,
    waiting_on,
    workspace,
)
from test_w5_activation_write_race import _activate, _candidate
from wp8_support import unique_key

from app.db import SessionLocal
from app.engine.jobs.worker import JobWorker, WorkerSettings
from app.engine.model import registry
from app.models.database import RdmObject


def domain_item(code: str, **extra: Any) -> dict:
    return {
        "op": "create",
        "applicationKey": "rdm-master",
        "objectTypeKey": "domain",
        "name": f"Batch domain {code}",
        "attributes": [{"attributeTypeKey": "domain-code", "value": code}],
        **extra,
    }


def queue(api, workspace_key: str, items: list[dict]) -> str:
    response = api.post(
        "/api/v1/batches",
        json={"policy": "independent", "run": "background", "workspaceKey": workspace_key, "items": items},
    )
    assert response.status_code == 202, response.text
    return response.json()["id"]


def worker() -> JobWorker:
    return JobWorker(SessionLocal, WorkerSettings(50, 120, 7), owner=unique_key("worker"))


def item_outcomes(api, job_id: str) -> list[tuple]:
    response = api.get(f"/api/v1/jobs/{job_id}/items")
    assert response.status_code == 200, response.text
    return [
        (item["status"], item.get("action") or (item.get("error") or {}).get("code"))
        for item in response.json()["items"]
    ]


def domains_named(workspace_key: str, prefix: str) -> int:
    with SessionLocal() as session:
        return session.scalar(
            select(func.count())
            .select_from(RdmObject)
            .where(RdmObject.workspace_key == workspace_key, RdmObject.name.like(f"{prefix}%"))
        )


@pytest.mark.parametrize("first", ["chunk", "single write"])
def test_a_unique_value_raced_by_a_chunk_and_a_single_write_is_given_once(
    client, workspace, request, first  # noqa: F811
):
    """The chunk takes the workspace lock before it reads; whichever writer holds it first gives
    the value, and the other is refused with its single write's code."""
    # One hold per test: the chunk at its lock, or the single write at its commit.
    hold = request.getfixturevalue("at_lock" if first == "chunk" else "at_commit")
    code = unique_key("raced")
    tag = unique_key("race")
    job_id = queue(client, workspace, [domain_item(f"{tag}-a"), domain_item(code), domain_item(f"{tag}-b")])
    runner = worker()
    with ThreadPoolExecutor(max_workers=2) as pool:
        hold.arm()
        if first == "chunk":
            held = pool.submit(runner.run_once)
            assert hold.reached.wait(HOLD_TIMEOUT), "the chunk never reached its lock"
            other = pool.submit(post_object, client, workspace, "domain", domain_code=code)
        else:
            held = pool.submit(post_object, client, workspace, "domain", domain_code=code)
            assert hold.reached.wait(HOLD_TIMEOUT), "the single write never reached its commit"
            other = pool.submit(runner.run_once)
        try:
            assert waiting_on(WORKSPACE_LOCK), "the second writer did not wait for the lock"
            assert not other.done()
        finally:
            hold.release()
        single = (other if first == "chunk" else held).result(HOLD_TIMEOUT)
        (held if first == "chunk" else other).result(HOLD_TIMEOUT)
    runner.run_until_idle()
    assert job(client, job_id)["state"] == "completed"
    if first == "chunk":
        refused(single, 409, "duplicate_attribute_value")
        assert item_outcomes(client, job_id) == [("applied", "created")] * 3
    else:
        created(single)
        assert item_outcomes(client, job_id) == [
            ("applied", "created"),
            ("rejected", "duplicate_attribute_value"),
            ("applied", "created"),
        ]


def rename(api, record: dict, name: str):
    return api.patch(
        f"/api/v1/objects/{record['objectTypeKey']}/{record['id']}",
        json={"expectedVersion": record["version"], "name": name},
    )


def test_two_updates_racing_on_one_version(client, workspace, at_commit):  # noqa: F811
    """The second update read the record before the first committed; it reads it again under the
    lock, sees the new version and is refused."""
    record = domain(client, workspace)
    first, second = race(
        at_commit, lambda: rename(client, record, "First"), lambda: rename(client, record, "Second")
    )
    assert first.status_code == 200, first.text
    refused(second, 409, "version_conflict")
    current = client.get(
        f"/api/v1/objects/domain/{record['id']}", params={"workspaceKey": workspace}
    ).json()
    assert (current["name"], current["version"]) == ("First", record["version"] + 1)


def test_a_batch_update_racing_a_single_update_on_one_version(client, workspace, at_commit):  # noqa: F811
    record = domain(client, workspace)
    update = {"op": "update", "target": {"id": record["id"]}, "expectedVersion": record["version"],
              "name": "From the batch"}
    job_id = queue(client, workspace, [update])
    runner = worker()
    with ThreadPoolExecutor(max_workers=2) as pool:
        at_commit.arm()
        held = pool.submit(rename, client, record, "Single")
        assert at_commit.reached.wait(HOLD_TIMEOUT), "the single update never reached its commit"
        chunk = pool.submit(runner.run_once)
        try:
            assert waiting_on(WORKSPACE_LOCK), "the chunk did not wait for the lock"
        finally:
            at_commit.release()
        assert held.result(HOLD_TIMEOUT).status_code == 200
        chunk.result(HOLD_TIMEOUT)
    assert item_outcomes(client, job_id) == [("rejected", "version_conflict")]
    current = client.get(
        f"/api/v1/objects/domain/{record['id']}", params={"workspaceKey": workspace}
    ).json()
    assert current["name"] == "Single"


def _without_matrices(source: dict) -> None:
    for application in source["applications"]:
        application["views"] = [
            view for view in application.get("views", []) if view["type"] != "relationMatrix"
        ]


def test_an_activation_dropping_a_matrix_shape_beside_a_chunk_does_not_deadlock(
    client, workspace, monkeypatch  # noqa: F811
):
    """The chunk's translations change a stored cell of the codelist translation matrix. Held at
    its release check, before it rewrites that cell's state row, the chunk holds nothing the
    activation needs: the activation drops the shape and commits, and the chunk then fails
    ``model_release_changed``, with nothing written. Were the state row rewritten first, the
    activation would wait for it while the chunk waits for the activation."""
    owner = codelist(client, workspace)
    language = created(post_object(client, workspace, "language", language_code=unique_key("l")))
    group = created(
        post_object(client, workspace, "translation-group", parent=language["id"], group_code="g")
    )
    translation = {
        "relationTypeKey": "object-has-translation",
        "direction": "incoming",
        "otherObjectId": owner["id"],
    }
    # The cell (the codelist, the language) holds a translation: its state row is stored.
    created(
        post_object(
            client,
            workspace,
            "translation",
            parent=group["id"],
            initial=[translation],
            translated_name="Stored",
            active=False,
        )
    )
    items = [
        {
            "op": "create",
            "applicationKey": "rdm-translations",
            "objectTypeKey": "translation",
            "name": f"Batch translation {number}",
            "parent": {"id": group["id"]},
            "attributes": [
                {"attributeTypeKey": "translated-name", "value": f"Text {number}"},
                {"attributeTypeKey": "active", "value": False},
            ],
            "initialRelations": [
                {
                    "relationTypeKey": "object-has-translation",
                    "direction": "incoming",
                    "object": {"id": owner["id"]},
                }
            ],
        }
        for number in range(3)
    ]
    job_id = queue(client, workspace, items)
    release = _candidate(client, _without_matrices)
    in_chunk = threading.local()
    reached, released = threading.Event(), threading.Event()
    original = registry.require_resolved_release

    def held(session) -> None:
        # The first check inside the chunk's items (its claim commits before them).
        if getattr(in_chunk, "running", False) and session.in_nested_transaction() and not reached.is_set():
            reached.set()
            assert released.wait(HOLD_TIMEOUT), "the chunk was never released"
        original(session)

    monkeypatch.setattr(registry, "require_resolved_release", held)
    runner = worker()

    def run_chunk() -> bool:
        in_chunk.running = True
        return runner.run_once()

    with ThreadPoolExecutor(max_workers=2) as pool:
        running = pool.submit(run_chunk)
        try:
            assert reached.wait(HOLD_TIMEOUT), "the chunk never reached its release check"
            activation = pool.submit(_activate, client, release).result(HOLD_TIMEOUT)
        finally:
            released.set()
        assert running.result(HOLD_TIMEOUT) is True
    assert activation.status_code == 200, activation.text
    finished = job(client, job_id)
    assert finished["state"] == "failed", finished
    assert finished["error"]["code"] == "model_release_changed", finished
    assert item_outcomes(client, job_id) == [("unprocessed", None)] * 3
    with SessionLocal() as session:
        assert (
            session.scalar(
                select(func.count())
                .select_from(RdmObject)
                .where(RdmObject.workspace_key == workspace, RdmObject.name.like("Batch translation%"))
            )
            == 0
        )
