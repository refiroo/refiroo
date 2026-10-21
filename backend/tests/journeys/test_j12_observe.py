"""J12.12–J12.15 — See the instance's state: probes, readiness per workspace and per process,
metrics and the log (USER_JOURNEYS.md, Base 0.11 O1).

Readiness and the metrics of several processes are read from real server processes on one database
(``processes.run``): a request reaches one of them, and each reports itself to the others through
the database (D192). Probes and the queued-job gauge run in-process.
"""

import copy
import json
import os
import re
import signal
import time
from contextlib import ExitStack
from uuid import uuid4

import pytest
import seeds
from processes import run
from scenario import W1, application, ok, scenario_seed
from service import execute, serve
from test_j24_background_job import _items, _submit, _unreachable
from test_j36_workspace_models import BOTH, _model, _on, _other

# Short heartbeats, so a killed process turns silent within the test.
FAST = {"PROCESS_HEARTBEAT_SECONDS": "1"}
_SAMPLE = re.compile(r"^([a-zA-Z_:][a-zA-Z0-9_:]*)(\{.*\})? (\S+)$")


def _until(read, check, seconds=20):
    deadline = time.monotonic() + seconds
    while True:
        value = read()
        if check(value):
            return value
        assert time.monotonic() < deadline, value
        time.sleep(0.2)


def _all(api, path):
    items, cursor = [], None
    while True:
        page = ok(api.get(path, pageSize=2, cursor=cursor))
        items += page["items"]
        cursor = page.get("nextCursor")
        if cursor is None:
            return items


def _samples(text):
    """The Prometheus text as (name, labels, value) samples, every line checked."""
    samples = []
    for line in text.splitlines():
        if line.startswith("#"):
            assert re.match(r"^# (HELP|TYPE) [a-zA-Z_:][a-zA-Z0-9_:]* .+$", line), line
            continue
        match = _SAMPLE.match(line)
        assert match, line
        name, labels, value = match.groups()
        parsed = dict(re.findall(r'(\w+)="((?:[^"\\]|\\.)*)"', labels or ""))
        samples.append((name, parsed, float(value)))
    return samples


@pytest.mark.journey("J12.12", "J12.8")
def test_alive_and_ready(configuration):
    """Given the service serving. When the database becomes unreachable, then returns. Then
    /health/live answers 200 throughout, while /health answers 503 during the outage and 200
    after it."""
    url = seeds.clone(scenario_seed(configuration))
    try:
        with serve(configuration, url) as service:
            client = service.client
            assert client.get("/health/live").json() == {"status": "ok"}
            assert service.health() == 200
            with _unreachable(url.database):
                assert client.get("/health/live").status_code == 200
                assert service.health() == 503
            assert client.get("/health/live").status_code == 200
            assert service.health() == 200
    finally:
        seeds.drop(url.database)


@pytest.mark.journey("J12.13", "J36")
@pytest.mark.structures(*BOTH)
def test_readiness_per_workspace_and_per_process(configuration):
    """Given processes A and B on one database: the first workspace on X, a workspace on Y's model,
    and a workspace whose release has a schema outside the window (written into the database from
    outside the API, as an older engine left it). When readiness and the processes are read from
    either process, a third process stops and B is killed. Then both name the first two workspaces
    served and the third unavailable in both processes with its schema; /health is ready; both
    processes are listed live and ready with their threads and pools; the stopped process leaves
    the list and B turns silent."""
    name = scenario_seed(configuration)
    ids = seeds.ensure(name)["ids"]
    url = seeds.clone(name)
    try:
        with ExitStack() as stack:
            a = stack.enter_context(run(configuration, url, ids, **FAST))
            b = stack.enter_context(run(configuration, url, ids, **FAST))
            world = a.world
            other = _other(world)
            on_y = _on(world, world.install(other.configuration.model, name="Y")["id"])
            older = copy.deepcopy(configuration.model)
            older["release"]["version"] += f"-older-{uuid4().hex[:6]}"
            older_release = world.install(older, name="Older")["id"]
            outside = _on(world, older_release)
            execute(
                url,
                "UPDATE model_releases SET schema_version = '0.4' WHERE public_id = :id",
                id=older_release,
            )
            x = _model(world)["releaseId"]

            for process in (a, b):
                api = process.world.api
                readiness = _until(
                    lambda api=api: {i["workspaceKey"]: i for i in _all(api, "/system/readiness")},
                    lambda items: len(items[outside]["unavailableIn"]) == 2,
                )
                assert readiness[W1]["state"] == "served" and readiness[W1]["release"]["id"] == x
                assert readiness[on_y]["state"] == "served"
                assert (
                    readiness[on_y]["release"]["key"] == other.configuration.model["release"]["key"]
                )
                held = readiness[outside]
                assert held["state"] == "unavailable" and held["release"]["schemaVersion"] == "0.4"
                assert {p["reason"] for p in held["unavailableIn"]} == {"unsupportedSchema"}
                assert {p["schemaVersion"] for p in held["unavailableIn"]} == {"0.4"}
                assert api.get("/health").status_code == 200

            processes = {p["pid"]: p for p in _all(a.world.api, "/system/processes")}
            assert {a.pid, b.pid} <= set(processes)
            for pid in (a.pid, b.pid):
                listed = processes[pid]
                assert listed["state"] == "live" and listed["ready"] is True
                assert listed["id"].split(":")[1] == str(pid)
                threads = {t["name"]: t["state"] for t in listed["threads"]}
                assert threads["jobWorker"] == "running" and threads["heartbeat"] == "running"
                assert listed["pool"]["size"] == 5 and listed["pool"]["maxOverflow"] == 10
                assert [r["reason"] for r in listed["unavailableReleases"]] == ["unsupportedSchema"]

            with run(configuration, url, ids, **FAST) as c:
                _until(
                    lambda: {p["pid"] for p in _all(a.world.api, "/system/processes")},
                    lambda pids, pid=c.pid: pid in pids,
                )
                stopped = c.pid
            assert stopped not in {p["pid"] for p in _all(a.world.api, "/system/processes")}

            os.kill(b.pid, signal.SIGKILL)
            silent = _until(
                lambda: {p["pid"]: p["state"] for p in _all(a.world.api, "/system/processes")},
                lambda states: states.get(b.pid) == "silent",
            )
            assert silent[a.pid] == "live"
            # A silent process no longer counts against a workspace.
            readiness = {i["workspaceKey"]: i for i in _all(a.world.api, "/system/readiness")}
            assert [p["processId"] for p in readiness[outside]["unavailableIn"]] == [
                processes[a.pid]["id"]
            ]
    finally:
        seeds.drop(url.database)


@pytest.mark.journey("J12.14")
@pytest.mark.structures("R")
def test_metrics_of_every_process_in_one_scrape(configuration):
    """Given processes A and B on one database. When each answers requests, one of them a 404 for a
    record that does not exist, and /metrics is read from A. Then the body is Prometheus text that
    holds both processes' requests, labelled by process and route template with no record ID, the
    404 among them, and each process's pool and readiness."""
    name = scenario_seed(configuration)
    ids = seeds.ensure(name)["ids"]
    url = seeds.clone(name)
    missing = str(uuid4())
    try:
        with ExitStack() as stack:
            a = stack.enter_context(run(configuration, url, ids, **FAST))
            b = stack.enter_context(run(configuration, url, ids, **FAST))
            type_key = configuration.key("R")
            for process in (a, b):
                api = process.world.api
                ok(api.get(f"/objects/{type_key}", workspaceKey=W1, pageSize=5))
                assert api.get(f"/objects/{type_key}/{missing}", workspaceKey=W1).status_code == 404
            pids = {a.pid: None, b.pid: None}

            def scrape():
                response = a.world.api.get("/metrics")
                assert response.status_code == 200
                assert response.headers["content-type"].startswith("text/plain; version=0.0.4")
                return _samples(response.text)

            def both_counted(samples):
                return all(
                    any(
                        n == "rdm_http_requests_total"
                        and l["process"].split(":")[1] == str(pid)
                        and l["status"] == "404"
                        for n, l, _ in samples
                    )
                    for pid in pids
                )

            samples = _until(scrape, both_counted)
            requests = [labels for n, labels, _ in samples if n == "rdm_http_requests_total"]
            assert not [labels for labels in requests if missing in labels["route"]]
            assert {"GET"} >= {labels["method"] for labels in requests if labels["status"] == "404"}
            routes = {labels["route"] for labels in requests if labels["status"] == "404"}
            assert routes == {"/api/v1/objects/{object_type_key}/{object_id}"}
            names = {n for n, _, _ in samples}
            assert {
                "rdm_http_request_duration_seconds_bucket",
                "rdm_database_pool_connections_in_use",
                "rdm_process_ready",
                "rdm_processes",
            } <= names
            ready = [v for n, _, v in samples if n == "rdm_process_ready"]
            assert len(ready) == 2 and set(ready) == {1}
    finally:
        seeds.drop(url.database)


@pytest.mark.journey("J12.14", "J24")
@pytest.mark.structures("R", "R.u")
def test_a_queued_job_is_counted(configuration):
    """Given a service whose job worker is not running. When a background batch is submitted. Then
    /metrics counts it queued under its kind."""
    url = seeds.clone(scenario_seed(configuration))
    try:
        with application(configuration, url) as world:
            _submit(world, _items(world, 2, prefix="Q"))
            samples = _samples(world.api.get("/metrics").text)
            assert ("rdm_jobs", {"kind": "batch", "state": "queued"}, 1.0) in samples
    finally:
        seeds.drop(url.database)


@pytest.mark.journey("J12.15", "J12.7")
def test_structured_logs(configuration):
    """Given a process started with LOG_FORMAT=json. When requests are sent with and without
    X-Request-Id. Then every line it writes is one JSON object; the request ID sent comes back and
    its access line carries it; one sent without gets a generated ID, also in its access line."""
    url = seeds.clone(scenario_seed(configuration))
    try:
        with run(configuration, url, LOG_FORMAT="json") as process:
            client = process.world.api.client
            sent = client.get("/api/v1/workspaces", headers={"X-Request-Id": "proxy-abc.1"})
            assert sent.headers["X-Request-Id"] == "proxy-abc.1"
            made = client.get("/api/v1/workspaces").headers["X-Request-Id"]
            assert re.fullmatch(r"[0-9a-f]{32}", made)
            spaced = client.get("/api/v1/workspaces", headers={"X-Request-Id": "not an id"})
            assert re.fullmatch(r"[0-9a-f]{32}", spaced.headers["X-Request-Id"])
            lines = _until(
                lambda: process.output().splitlines(),
                lambda lines: sum('"logger": "app.access"' in line for line in lines) >= 3,
            )
            entries = [json.loads(line) for line in lines if line.strip()]
            access = {e["requestId"]: e for e in entries if e["logger"] == "app.access"}
            for request_id in ("proxy-abc.1", made):
                line = access[request_id]
                assert line["status"] == 200 and line["route"] == "/api/v1/workspaces"
                assert line["level"] == "INFO" and line["durationMs"] >= 0
            assert any("Application startup complete" in e["message"] for e in entries)
    finally:
        seeds.drop(url.database)


@pytest.mark.journey("J12.15", "J12.7")
@pytest.mark.parametrize(
    "settings",
    [{"LOG_FORMAT": "xml"}, {"LOG_LEVEL": "loud"}, {"PROCESS_HEARTBEAT_SECONDS": "0"}],
    ids=["format", "level", "heartbeat"],
)
def test_an_invalid_log_setting_refuses_to_start(configuration, settings):
    """When the service starts with an invalid log or heartbeat setting. Then it refuses to start
    with a message naming the setting."""
    with pytest.raises(RuntimeError) as refusal, serve(configuration, None, **settings):
        pass
    assert next(iter(settings)) in str(refusal.value)
