"""J24.7 — Follow a job as it changes (USER_JOURNEYS.md, 0.9 J1u).

``GET /jobs/{id}/events`` is a server-sent event stream. The test client buffers a streamed
response until it ends, so the journey application is also served over HTTP on a local port, as a
browser reaches it, and a reader thread follows the stream there while the test runs the engine's
own workers, which the journey application does not start. The stream is told of each committed
change by the database (D58), never by polling.
"""

import json
import socket
import threading
import time
from uuid import uuid4

import httpx2
import pytest
import uvicorn
from harness_identity import token
from scenario import ok, refused

FINAL = {"completed", "failed", "cancelled", "expired"}


@pytest.fixture
def served(world):
    """The journey application over HTTP on a free local port; its lifespan already runs."""
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        port = probe.getsockname()[1]
    server = uvicorn.Server(
        uvicorn.Config(
            world.api.client.app,
            host="127.0.0.1",
            port=port,
            lifespan="off",
            log_level="warning",
            timeout_graceful_shutdown=2,
        )
    )
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    deadline = time.monotonic() + 10
    while not server.started:
        assert time.monotonic() < deadline, "the local server did not start"
        time.sleep(0.02)
    try:
        yield f"http://127.0.0.1:{port}"
    finally:
        server.should_exit = True
        thread.join(10)


class Follower:
    """Reads a job's event stream on a thread: every job it sends, and whether the stream ended."""

    def __init__(self, base: str, job_id: str) -> None:
        self.jobs: list[dict] = []
        self.ended = threading.Event()
        self.first = threading.Event()
        self._thread = threading.Thread(target=self._read, args=(base, job_id), daemon=True)
        self._thread.start()
        assert self.first.wait(10), "the stream sent nothing"

    def _read(self, base, job_id):
        url = f"{base}/api/v1/jobs/{job_id}/events"
        # The harness's token (0.12 I1), obtained from the same engine.
        bearer = token(lambda path, **kwargs: httpx2.post(f"{base}{path}", **kwargs))
        headers = {"Authorization": f"Bearer {bearer}"}
        with httpx2.stream("GET", url, headers=headers, timeout=30) as response:
            assert response.status_code == 200, response.read()
            assert response.headers["content-type"].startswith("text/event-stream")
            event = None
            for line in response.iter_lines():
                if line.startswith("event:"):
                    event = line.split(":", 1)[1].strip()
                elif line.startswith("data:") and event == "job":
                    self.jobs.append(json.loads(line.split(":", 1)[1]))
                    self.first.set()
        self.ended.set()

    def wait_for(self, condition) -> None:
        """Until the stream has sent a job meeting ``condition``."""
        deadline = time.monotonic() + 10
        while not any(condition(job) for job in list(self.jobs)):
            assert time.monotonic() < deadline, [job["state"] for job in self.jobs]
            time.sleep(0.02)

    def finish(self) -> list[dict]:
        assert self.ended.wait(15), f"the stream did not end: {[job['state'] for job in self.jobs]}"
        self._thread.join(5)
        return self.jobs


def _workspace(world):
    key = f"stream-{uuid4().hex[:8]}"
    ok(world.api.post("/workspaces", {"key": key, "label": "Stream site"}), 201)
    return key


def _export(world, workspace):
    world.made("H", "Streamed", workspace=workspace, values={"H.code": f"S{uuid4().hex[:4]}"})
    body = {
        "workspaceKey": workspace,
        "scope": {"types": [{"objectTypeKey": world.key("H")}]},
        "format": "jsonl",
    }
    return ok(world.api.post("/exports", body), 202)


def _batch(world, workspace, items, policy="independent"):
    body = {"workspaceKey": workspace, "policy": policy, "run": "background", "items": items}
    return ok(world.api.post("/batches", body), 202)


def _create(world, name, **values):
    return {
        "op": "create",
        "applicationKey": world.app("R"),
        "objectTypeKey": world.key("R"),
        "name": name,
        "attributes": [
            {"attributeTypeKey": k, "value": v}
            for k, v in {**world.required_values("R"), **values}.items()
        ],
    }


@pytest.mark.journey("J24.7")
@pytest.mark.structures("H", "H.code", "R", "R.u")
def test_the_stream_follows_a_job_to_its_end(world, served):
    """Given a queued export and a queued batch. When a reader opens each one's events and the
    workers run them. Then each stream sends the job queued, then running, then completed (the
    export with its output, the batch with its counts), in that order, and ends."""
    state = world.api.client.app.state
    ws = _workspace(world)
    export = _export(world, ws)
    follower = Follower(served, export["id"])
    state.export_worker.run_until_idle()
    jobs = follower.finish()
    states = [job["state"] for job in jobs]
    assert states[0] == "queued" and states[-1] == "completed" and "running" in states, states
    assert jobs[-1]["output"]["counts"]["records"] == {world.key("H"): 1}
    assert all(job["id"] == export["id"] for job in jobs)

    batch = _batch(
        world,
        ws,
        [
            _create(world, f"Streamed {n}", **{world.key("R.u"): f"ST-{uuid4().hex[:6]}"})
            for n in range(3)
        ],
    )
    follower = Follower(served, batch["id"])
    state.job_worker.run_until_idle()
    jobs = follower.finish()
    assert jobs[0]["state"] == "queued" and jobs[-1]["state"] == "completed"
    assert jobs[-1]["counts"]["applied"] == 3


@pytest.mark.journey("J24.7")
@pytest.mark.structures("H", "H.code")
def test_a_finished_job_is_sent_once_and_an_unknown_one_is_refused(world, served):
    """Given a completed export. When a reader opens its events, and the events of an unknown job.
    Then the first sends the completed job once and ends; the second is refused as not found."""
    ws = _workspace(world)
    export = _export(world, ws)
    world.api.client.app.state.export_worker.run_until_idle()
    jobs = Follower(served, export["id"]).finish()
    assert [job["state"] for job in jobs] == ["completed"]
    refused(world.api.get(f"/jobs/{uuid4()}/events"), 404, "JOB_NOT_FOUND")


@pytest.mark.journey("J24.7", "J24.2")
@pytest.mark.structures("H", "H.code")
def test_a_cancel_request_reaches_the_stream(world, served):
    """Given a reader following a queued export. When the export is cancelled and the worker
    carries the cancel out. Then the stream sends the job with its cancel request, then cancelled,
    and ends."""
    ws = _workspace(world)
    export = _export(world, ws)
    follower = Follower(served, export["id"])
    ok(world.api.post(f"/jobs/{export['id']}/cancel"), 202)
    follower.wait_for(lambda job: job["cancelRequestedAt"] is not None)
    world.api.client.app.state.export_worker.run_until_idle()
    jobs = follower.finish()
    assert any(job["cancelRequestedAt"] and job["state"] == "queued" for job in jobs), jobs
    assert jobs[-1]["state"] == "cancelled"


@pytest.mark.journey("J24.7", "J24.2")
@pytest.mark.structures("R", "R.u")
def test_only_committed_changes_are_sent(world, served):
    """Given a reader following an atomic background batch of three creates, one of them refused.
    When the worker runs it, rolling its items back. Then the stream never sends progress the job
    did not commit: no job between none processed and all of them, and the job ends completed with
    nothing applied."""
    ws = _workspace(world)
    code = f"DUP-{uuid4().hex[:6]}"
    items = [
        _create(world, "First", **{world.key("R.u"): code}),
        _create(world, "Second", **{world.key("R.u"): f"OK-{uuid4().hex[:6]}"}),
        _create(world, "Duplicate", **{world.key("R.u"): code}),
    ]
    batch = _batch(world, ws, items, policy="atomic")
    follower = Follower(served, batch["id"])
    world.api.client.app.state.job_worker.run_until_idle()
    jobs = follower.finish()
    assert {job["progress"]["processed"] for job in jobs} <= {0, 3}
    assert jobs[-1]["state"] == "completed" and jobs[-1]["counts"]["applied"] == 0
