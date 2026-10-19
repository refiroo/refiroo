"""J12.10, J36.2 and J37 across processes — the engine run as several processes on one database
(USER_JOURNEYS.md, Base 0.11 N1).

Each process is a server started as an operator starts it (``processes.run``) and reached over HTTP:
two processes on one database stand for two nodes, and one process with ``--workers 2`` for
``WEB_CONCURRENCY=2``. A process learns of another's release switch by the read every request makes
at resolution (D165); installations and startups take database locks (D167, D168). The read guard
for a read whose workspace switched while it ran (D166) is tested at the engine boundary, in
``test_j36_read_guard.py``.
"""

import threading
import time
from collections.abc import Iterator
from contextlib import ExitStack, contextmanager

import pytest
import seeds
from alembic.script import ScriptDirectory
from processes import run
from scenario import W1, W2, ok, refused, scenario_seed
from service import scalar
from test_j36_expected_release import HEADER
from test_j36_workspace_models import BOTH, _model
from test_j37_workspace_migration import _confirm, _probe, _value, _workspace, _x2

from app.db import migration_config

HEAD = ScriptDirectory.from_config(migration_config()).get_current_head()
FINAL = {"completed", "failed", "cancelled", "expired"}


@contextmanager
def _two(configuration) -> Iterator[tuple]:
    """Processes A and B on one clone of the configuration's seed."""
    name = scenario_seed(configuration)
    ids = seeds.ensure(name)["ids"]
    url = seeds.clone(name)
    try:
        with ExitStack() as stack:
            a = stack.enter_context(run(configuration, url, ids))
            b = stack.enter_context(run(configuration, url, ids))
            yield a.world, b.world
    finally:
        seeds.drop(url.database)


def _together(*calls):
    """``calls`` sent at once, each on a thread of its own; their answers in order."""
    start = threading.Barrier(len(calls))
    answers = [None] * len(calls)

    def send(index, call):
        start.wait()
        answers[index] = call()

    threads = [threading.Thread(target=send, args=item) for item in enumerate(calls)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(120)
    return answers


def _job(world, job_id, states):
    deadline = time.monotonic() + 120
    while time.monotonic() < deadline:
        job = ok(world.api.get(f"/jobs/{job_id}"))
        if job["state"] in states:
            return job
        time.sleep(0.2)
    raise AssertionError(f"job {job_id} stayed {job['state']}")


@pytest.mark.journey("J12.10")
def test_several_processes_start_together(configuration):
    """Given an empty database. When the service starts with two workers (``WEB_CONCURRENCY=2``)
    and model administration on. Then both workers start and serve, /health is ready, the database
    is at the latest revision and runs one bootstrap release, and the log holds no error."""
    url = seeds.create_empty()
    try:
        with run(configuration, url, workers=2) as process:
            for _ in range(6):
                assert process.world.api.get("/health").status_code == 200
            output = process.output()
            assert output.count("Application startup complete") == 2, output
            assert "ERROR" not in output and "Traceback" not in output, output
        assert scalar(url, "SELECT version_num FROM alembic_version") == HEAD
        assert scalar(url, "SELECT count(*) FROM model_releases") == 1
        assert scalar(url, "SELECT count(*) FROM workspace_models") == scalar(
            url, "SELECT count(*) FROM workspaces"
        )
    finally:
        seeds.drop(url.database)


@pytest.mark.journey("J36.2", "J36.5")
@pytest.mark.structures(*BOTH)
def test_a_switch_in_one_process_is_served_by_the_other(configuration):
    """Given processes A and B, B having served the default workspace on X1. When X2 (with a new
    type) is installed and activated into the default workspace through A. Then B's next reads of
    it serve X2 and list the new type, the second workspace still runs X1 on B, and a write sent to
    B built on X1 is refused naming both releases, nothing saved."""
    with _two(configuration) as (a, b):
        x1 = _model(b)["releaseId"]
        record = b.made("R", "Before the switch")
        model, _key = a.candidate("compatible")
        known = {t["key"] for t in configuration.model["objectTypes"]}
        (new_type,) = {t["key"] for t in model["objectTypes"]} - known
        x2 = a.install(model)["id"]
        ok(a.activate(x2))

        assert _model(b)["releaseId"] == x2
        served = b.api.get("/model", workspaceKey=W1)
        assert ok(served)["release"]["version"] == model["release"]["version"]
        assert served.headers["X-Model-Release-Id"] == x2
        assert new_type in {t["key"] for t in ok(served)["objectTypes"]}
        assert _model(b, W2)["releaseId"] == x1

        body = {"expectedVersion": record["version"], "name": "Built on X1"}
        stale = b.api.patch(f"/objects/{b.key('R')}/{record['id']}", body, headers={HEADER: x1})
        error = refused(stale, 409, "MODEL_RELEASE_CHANGED")
        assert error["details"]["currentReleaseId"] == x2
        assert a.record("R", record["id"])["name"] == "Before the switch"


@pytest.mark.journey("J36.2")
@pytest.mark.structures(*BOTH)
def test_install_and_activate_from_two_processes_at_once(configuration):
    """Given processes A and B and two drafts holding one model. When each draft is installed, one
    through A and one through B at once. Then one answers 201 and the other 200 with the same
    release, and one release is installed. When that release is activated into the default
    workspace through A and B at once, claiming one version. Then one answers 200 and the other
    409 ACTIVATION_CONFLICT; the workspace runs the release at the next version."""
    with _two(configuration) as (a, b):
        model, _key = a.candidate("compatible")
        drafts = [
            ok(world.api.post("/model-drafts", {"name": f"Draft {n}", "model": model}), 201)
            for n, world in enumerate((a, b))
        ]
        installed = _together(
            *(
                lambda world=world, draft=draft: world.api.post(
                    f"/model-drafts/{draft['id']}/installation",
                    {"expectedVersion": draft["version"]},
                )
                for world, draft in zip((a, b), drafts, strict=True)
            )
        )
        assert sorted(answer.status_code for answer in installed) == [200, 201], [
            answer.text for answer in installed
        ]
        (release_id,) = {answer.json()["id"] for answer in installed}
        version = model["release"]["version"]
        assert (
            scalar(
                a.database,
                f"SELECT count(*) FROM model_releases WHERE release_version = '{version}'",
            )
            == 1
        )

        before = _model(a)
        body = {
            "releaseId": release_id,
            "expectedVersion": before["version"],
            "expectedReleaseId": before["releaseId"],
        }
        activated = _together(
            *(
                lambda world=world: world.api.post(f"/workspaces/{W1}/model/activation", body)
                for world in (a, b)
            )
        )
        codes = sorted(answer.status_code for answer in activated)
        assert codes == [200, 409], [answer.text for answer in activated]
        (conflict,) = [answer for answer in activated if answer.status_code == 409]
        refused(conflict, 409, "ACTIVATION_CONFLICT")
        assert (_model(b)["releaseId"], _model(b)["version"]) == (release_id, before["version"] + 1)


@pytest.mark.journey("J37.2")
@pytest.mark.structures(*BOTH)
def test_a_migration_confirmed_in_one_process_is_served_by_the_other(configuration):
    """Given processes A and B and a workspace on X1 with R records holding counts. When a
    migration to X2, which makes the count an integer, is previewed and confirmed through A. Then
    B's next reads of the workspace serve X2 and the counts as integers."""
    with _two(configuration) as (a, b):
        key, made, _citation = _workspace(a)
        k = _probe(a)
        assert _value(b.record("R", made["twelve"]["id"], workspaceKey=key), k.count) == "12"
        x2 = a.install(_x2(a, "count-integer"), name="Probe")["id"]
        current = _model(a, key)
        started = a.api.post(
            f"/workspaces/{key}/model/migrations",
            {"targetReleaseId": x2, "expectedVersion": current["version"]},
        )
        job = _job(a, ok(started, 202)["id"], {"awaiting_confirmation", *FINAL})
        assert job["state"] == "awaiting_confirmation", job
        accept = {"acceptLoss": True} if job["migration"]["counts"]["loss"] else {}
        ok(_confirm(a, job, **accept), 202)
        assert _job(a, job["id"], FINAL)["state"] == "completed"

        assert _model(b, key)["releaseId"] == x2
        assert _value(b.record("R", made["twelve"]["id"], workspaceKey=key), k.count) == 12
