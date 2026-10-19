"""Base 0.11 X5: how long a move's dry run takes at the size people work with, worst case.

The move editor runs a dry run after every step (D140), so its time is what a person waits for.
Measured after X5's fixes at about 0.95 s for 2,000 records; before them the editor's first dry run
took 4.9 s (the default selection, every mapped type, re-read per record while the records were
newer than the statistics) and a repeated one up to 40 s (the dry run's own rows joined row by row
once earlier jobs' rows were in the table). The worst case is forced: generated A and generated B
installed beside the small volume seed, each in a new workspace, the source's records created just
before with automatic analysis off on the record tables, and two dry runs one after the other with
the editor's default selection; the worker runs as in the service, one chunk after another.
"""

import sys
import time
from uuid import uuid4

import layout
import pytest
from sqlalchemy import text

sys.path.insert(0, str(layout.JOURNEYS))

from configurations import all_configurations
from scenario import World
from volume_fixture import scaled_shape, volume_app

from app.db import get_engine

RECORDS = 2_000
# Seconds a dry run of RECORDS records may take on the reference laptop: about 2.5 times what it
# took when written, well under the 4.9 s and 40 s it took before (a budget, not a target).
BUDGET_SECONDS = 2.5
API = "/api/v1"


def _ok(response, status=200):
    assert response.status_code == status, response.text[:500]
    return response.json()


@pytest.fixture(scope="module")
def monkeypatch_module():
    patch = pytest.MonkeyPatch()
    yield patch
    patch.undo()


@pytest.fixture(scope="module")
def timed(tmp_path_factory, monkeypatch_module):
    monkeypatch_module.setenv("MODEL_ADMIN_MUTATIONS_ENABLED", "true")
    a, b = all_configurations()["generated-a"], all_configurations()["generated-b"]
    world = World(a, None, None)
    directory = tmp_path_factory.mktemp("move-step-time")
    with volume_app(directory, scaled_shape(0.001)) as (client, _dataset):
        worker = client.app.state.job_worker
        worker.stop()
        for key, model in (("source", a.model), ("target", b.model)):
            draft = _ok(client.post(f"{API}/model-drafts", json={"name": key, "model": model}), 201)
            body = {"expectedVersion": draft["version"]}
            installed = client.post(f"{API}/model-drafts/{draft['id']}/installation", json=body)
            release = _ok(installed, 201)
            body = {"key": key, "label": key, "modelReleaseId": release["id"]}
            _ok(client.post(f"{API}/workspaces", json=body), 201)
        with get_engine().begin() as connection:
            connection.execute(text("ANALYZE"))
            for table in ("objects", "attribute_values", "object_relations"):
                connection.execute(text(f"ALTER TABLE {table} SET (autovacuum_enabled = false)"))

        def item(structure, name, **extra):
            values = world.required_values(structure)
            return {
                "op": "create",
                "applicationKey": world.app(structure),
                "objectTypeKey": world.key(structure),
                "name": name,
                "attributes": [{"attributeTypeKey": k, "value": v} for k, v in values.items()],
                **extra,
            }

        regions = [str(uuid4()) for _ in range(RECORDS // 2)]
        for first in range(0, len(regions), 1000):
            part = regions[first : first + 1000]
            for items in (
                [item("G", f"Region {first + i}", id=region) for i, region in enumerate(part)],
                [item("M", f"Zone {first + i}", parent={"id": r}) for i, r in enumerate(part)],
            ):
                batch = {
                    "workspaceKey": "source",
                    "policy": "atomic",
                    "run": "inline",
                    "items": items,
                }
                _ok(client.post(f"{API}/batches", json=batch))
        sides = {"sourceWorkspaceKey": "source", "targetWorkspaceKey": "target"}
        _ok(client.post(f"{API}/model-mappings", json={"key": "m", "name": "M", **sides}), 201)
        _ok(client.post(f"{API}/model-mappings/m/inference", json=sides), 202)
        worker.run_until_idle()
        version = _ok(client.get(f"{API}/model-mappings/m"))["version"]
        body = {"expectedVersion": version}
        _ok(client.post(f"{API}/model-mappings/m/inference/application", json=body))
        mapping = _ok(client.get(f"{API}/model-mappings/m"))
        selection = {"types": [{"objectTypeKey": entry["source"]} for entry in mapping["types"]]}
        found = []
        for _run in range(2):
            body = {
                **sides,
                "mapping": {"key": "m", "expectedVersion": mapping["version"]},
                "selection": selection,
            }
            job = _ok(client.post(f"{API}/moves", json=body), 202)
            started = time.perf_counter()
            worker.run_until_idle()
            seconds = time.perf_counter() - started
            found.append((seconds, _ok(client.get(f"{API}/jobs/{job['id']}"))))
    return found


def test_each_dry_run_of_2000_new_records_is_within_its_budget(timed):
    for _seconds, job in timed:
        assert job["state"] == "awaiting_confirmation", job
        assert job["move"]["counts"]["create"] >= RECORDS, job["move"]["counts"]
    assert [round(seconds, 2) for seconds, _job in timed if seconds > BUDGET_SECONDS] == []
