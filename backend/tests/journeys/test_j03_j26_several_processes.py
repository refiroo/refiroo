"""The concurrency and uniqueness invariants with several processes on one database (Base 0.11 N3,
the roadmap's first 0.11 exit item, D176): J03.8, J02.2, J14.8, J13.8 and J26.5 raced across two
server processes, a background job on one node racing a live write on the other (J24), and a
frozen node's locks released by the server (J24.3, D182).

Each race sends one call to process A and one to process B while the test holds the workspace's
row (``World.race``), so both are in flight before either commits, as clients of two nodes arriving
together. The engine decides them through PostgreSQL's locks, which no process can bypass: the
races pass on the code before N3 too and are the exit item's evidence. Only the frozen node's case
is new behaviour.
"""

import time
from collections.abc import Callable, Iterator
from concurrent.futures import ThreadPoolExecutor
from contextlib import ExitStack

import pytest
from scenario import W1, ok, refused
from test_j24_background_job import _items, _submit
from test_j24_several_processes import (
    FINAL,
    _freeze,
    _held_by,
    _holding,
    _job,
    _nodes,
    _resume,
    _waiting,
)
from test_j26_follow_changes import _follow, _workspace

# How long the frozen node's case lets a transaction sit idle before the server ends it (D182).
IDLE_SECONDS = "2"


@pytest.fixture(scope="module")
def pairs() -> Iterator[Callable]:
    """Processes A and B on one clone per configuration, started on first use and shared by the
    races, which freeze nothing."""
    started: dict[str, tuple] = {}
    with ExitStack() as stack:

        def pair(configuration):
            if configuration.name not in started:
                started[configuration.name] = stack.enter_context(_nodes(configuration))
            return started[configuration.name]

        yield pair


@pytest.mark.journey("J03.8")
@pytest.mark.structures("R", "R.u")
def test_two_processes_creating_one_unique_value(configuration, pairs):
    """Given processes A and B. When an R record with one unique value is created through each at
    once. Then one is created and the other refused; one record carries the value."""
    a, b, _ = pairs(configuration)
    responses = a.world.race(
        W1,
        lambda: a.world.create("R", "Across A", values={"R.u": "ACROSS"}),
        lambda: b.world.create("R", "Across B", values={"R.u": "ACROSS"}),
    )
    assert sorted(r.status_code for r in responses) == [201, 409]
    refused(next(r for r in responses if r.status_code == 409), 409, "DUPLICATE_ATTRIBUTE_VALUE")
    u = a.world.key("R.u")
    for process in (a, b):
        page = ok(
            process.world.api.get(f"/objects/{a.world.key('R')}", **{f"filter.{u}.eq": "ACROSS"})
        )
        assert len(page["items"]) == 1


@pytest.mark.journey("J02.2")
@pytest.mark.structures("R")
def test_two_processes_saving_one_version(configuration, pairs):
    """Given an R record. When it is renamed through A and through B with the same expected
    version at once. Then one rename is saved and the other refused; the name is the winner's."""
    a, b, _ = pairs(configuration)
    record = a.world.made("R", "Shared across")
    responses = a.world.race(
        W1,
        *(
            lambda process=process, name=name: process.world.update(
                "R", record["id"], record["version"], name=name
            )
            for process, name in ((a, "Writer A"), (b, "Writer B"))
        ),
    )
    assert sorted(r.status_code for r in responses) == [200, 409]
    refused(next(r for r in responses if r.status_code == 409), 409, "VERSION_CONFLICT")
    winner = next(r for r in responses if r.status_code == 200).json()["name"]
    assert b.world.record("R", record["id"])["name"] == winner
    assert b.world.record("R", record["id"])["version"] == record["version"] + 1


@pytest.mark.journey("J14.8")
@pytest.mark.structures("H")
def test_two_processes_moving_into_a_cycle(configuration, pairs):
    """Given sibling H records x and y. When x is moved under y through A and y under x through B at
    once. Then one move succeeds and the other is refused; both paths end at a top."""
    a, b, _ = pairs(configuration)
    x, y = (a.world.made("H", name, parent=a.world.ids["h1"]) for name in ("Across X", "Across Y"))

    def move(process, child, parent):
        body = {"parentObjectId": parent["id"], "expectedVersion": child["version"]}
        return lambda: process.world.api.patch(f"/objects/{a.world.key('H')}/{child['id']}", body)

    responses = a.world.race(W1, move(a, x, y), move(b, y, x))
    assert sorted(r.status_code for r in responses) == [200, 422]
    refused(next(r for r in responses if r.status_code == 422), 422, "PARENT_CYCLE")
    for record in (x, y):
        path = b.world.record("H", record["id"])["path"]
        assert path[0]["id"] == a.world.ids["h1"] and len(path) <= 3


@pytest.mark.journey("J13.8")
@pytest.mark.structures("R", "K", "B11")
def test_two_processes_relating_into_one_cardinality_limit(configuration, pairs):
    """Given R records r1 and r2 and a K record k. When r1 is related to k through A and r2 through
    B at once, k taking one such relationship. Then one is created and the other refused."""
    a, b, _ = pairs(configuration)
    r1, r2 = (a.world.made("R", f"Across racer {n}")["id"] for n in (1, 2))
    k = a.world.made("K", "Across contested")["id"]
    responses = a.world.race(
        W1, lambda: a.world.relate("B11", r1, k), lambda: b.world.relate("B11", r2, k)
    )
    assert sorted(r.status_code for r in responses) == [201, 409]
    refused(next(r for r in responses if r.status_code == 409), 409, "CARDINALITY_VIOLATION")
    incoming = ok(
        b.world.api.get(
            "/relations",
            objectId=k,
            direction="incoming",
            relationTypeKey=a.world.key("B11"),
            pageSize=100,
        )
    )["items"]
    assert len(incoming) == 1


@pytest.mark.journey("J26.5")
@pytest.mark.structures("R")
def test_two_processes_writing_get_gapless_feed_positions(configuration, pairs):
    """Given a new workspace with three records. When one is renamed through A, two through B and a
    record is created through A, all at once. Then the feed holds every change once, positions
    1..7 with no gap, each record's entries rising with its version, read the same through A and
    B."""
    a, b, _ = pairs(configuration)
    ws = _workspace(a.world)
    records = [a.world.made("R", f"Feed {n}", workspace=ws) for n in range(3)]

    def rename(process, record):
        return lambda: process.world.update("R", record["id"], record["version"], name="At once")

    calls = [rename(a if n % 2 else b, record) for n, record in enumerate(records)]
    calls.append(lambda: a.world.create("R", "Feed created", workspace=ws))
    responses = a.world.race(ws, *calls)
    assert sorted(r.status_code for r in responses) == [200] * 3 + [201]
    entries = _follow(a.world, ws)
    assert [e["position"] for e in entries] == list(range(1, 8))
    assert _follow(b.world, ws) == entries
    for record in records:
        versions = [e["version"] for e in entries if e["id"] == record["id"]]
        assert versions == sorted(versions) and len(versions) == 2


@pytest.mark.journey("J24.8", "J03.8")
@pytest.mark.structures("R", "R.u")
def test_a_job_on_one_node_and_a_live_write_on_another_for_one_unique_value(configuration):
    """Given processes A and B. When B's worker applies a background batch item creating an R
    record with a unique value while a live create through A sends the same value, both in flight
    at once. Then one record carries the value, and the other write is refused with
    DUPLICATE_ATTRIBUTE_VALUE: the live create's answer, or the job item's outcome."""
    with _nodes(configuration) as (a, b, url), ThreadPoolExecutor(1) as pool:
        _freeze(a, url)
        with _holding(url, "SELECT 1 FROM workspaces WHERE key = :k FOR UPDATE", k=W1):
            job = _submit(b.world, _items(b.world, 1, "Dup"))
            _held_by(url, job["id"], b)
            _waiting(url, 1)
            _resume(a)
            created = pool.submit(a.world.create, "R", "Dup live", values={"R.u": "Dup-000"})
            _waiting(url, 2)
        response = created.result(timeout=30)
        done = _job(b.world, job["id"], FINAL)
        assert done["state"] == "completed", done
        item = ok(b.world.api.get(f"/jobs/{job['id']}/items", pageSize=10))["items"][0]
        if response.status_code == 201:
            assert item["status"] != "applied" and "DUPLICATE_ATTRIBUTE_VALUE" in str(item), item
        else:
            refused(response, 409, "DUPLICATE_ATTRIBUTE_VALUE")
            assert item["status"] == "applied", item
        u = a.world.key("R.u")
        page = ok(b.world.api.get(f"/objects/{a.world.key('R')}", **{f"filter.{u}.eq": "Dup-000"}))
        assert len(page["items"]) == 1


@pytest.mark.journey("J24.3")
@pytest.mark.structures("R", "R.u")
def test_a_frozen_nodes_locks_are_released_by_the_server(configuration):
    """Given processes A and B with DATABASE_IDLE_TRANSACTION_TIMEOUT of 2 s. When A's worker holds
    W1's lock in a chunk of a background batch and A is frozen. Then a write to W1 through B answers
    within 10 s and B completes the job while A stays frozen. A, resumed, finds its transaction
    ended: its worker says so in one line, without a traceback and without failing the job; A
    serves again.

    What the line says depends on what A reads first. The server's notice (SQLSTATE 25P03) names
    DATABASE_IDLE_TRANSACTION_TIMEOUT; when A's next statement meets the closed socket first, the
    reset discards the unread notice and A sees a lost connection (seen in N3).
    """
    settings = {"JOB_CHUNK_ITEMS": "10", "DATABASE_IDLE_TRANSACTION_TIMEOUT": IDLE_SECONDS}
    with _nodes(configuration, **settings) as (a, b, url):
        _freeze(b, url)
        with _holding(url, "SELECT 1 FROM workspaces WHERE key = :k FOR UPDATE", k=W1):
            job = _submit(a.world, _items(a.world, 40, "Frozen"))
            _held_by(url, job["id"], a)
            _waiting(url, 1)
            _freeze(a)
            _resume(b)
            _held_by(url, job["id"], b)
        # A's chunk was granted W1's lock when the test let it go, and holds it, frozen.
        sent = time.monotonic()
        beside = b.world.create("R", "Beside the stalled node", values={"R.u": "BESIDE"})
        assert beside.status_code == 201, beside.text
        assert time.monotonic() - sent < 10
        done = _job(b.world, job["id"], FINAL)
        assert (done["state"], done["counts"]["applied"]) == ("completed", 40), done

        _resume(a)
        deadline = time.monotonic() + 20
        notice = ("DATABASE_IDLE_TRANSACTION_TIMEOUT", "cannot reach the database")
        while not any(text in a.output() for text in notice):
            assert time.monotonic() < deadline, a.output()[-4000:]
            time.sleep(0.2)
        time.sleep(3)  # The worker's next round, which finds the database again.
        noticed = [line for line in a.output().splitlines() if any(text in line for text in notice)]
        assert len(noticed) == 1, noticed
        assert "Traceback" not in a.output()
        assert ok(a.world.api.get("/health")) is not None
        page = ok(a.world.api.get(f"/objects/{a.world.key('R')}", search="Frozen ", pageSize=100))
        assert sorted(a.world.names(page)) == [f"Frozen {n:03d}" for n in range(40)]
        assert _job(a.world, job["id"], FINAL)["state"] == "completed"
