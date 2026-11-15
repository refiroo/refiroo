"""A starting run drops the clones of ended runs and keeps those of live ones (TS2)."""

import subprocess
import sys

import run_ids
import seeds
from sqlalchemy import text


def _exists(name: str) -> bool:
    with seeds.admin() as server:
        return bool(
            server.scalar(text("SELECT 1 FROM pg_database WHERE datname = :n"), {"n": name})
        )


def test_a_starting_run_drops_only_the_clones_of_runs_that_ended():
    child = subprocess.Popen([sys.executable, "-c", "pass"])
    ended = run_ids.of_process(child.pid)
    child.wait()
    mine, other_live, gone, gone_runner = (
        run_ids.name(),
        run_ids.name(run=run_ids.of_process(1)),  # process 1 is alive for as long as the machine is
        run_ids.name(run=ended),
        run_ids.name("r", ended),
    )
    with seeds.admin() as server:
        for database in (mine, other_live, gone, gone_runner):
            server.execute(text(f'CREATE DATABASE "{database}" TEMPLATE template0'))
    try:
        dropped = seeds.drop_abandoned()
        assert {gone, gone_runner} <= set(dropped)
        assert not {mine, other_live} & set(dropped)
        assert _exists(mine) and _exists(other_live)
        assert not _exists(gone) and not _exists(gone_runner)
    finally:
        for database in (mine, other_live, gone, gone_runner):
            seeds.drop(database)


def _only_these_holders(monkeypatch, *databases):
    """The volume clones the wait sees: the test's own, whatever other runs hold on the server."""
    real = run_ids.volume_holders
    monkeypatch.setattr(
        run_ids, "volume_holders", lambda names: real([n for n in names if n in databases])
    )


def test_a_volume_clone_waits_while_another_live_run_holds_one(monkeypatch):
    import pytest

    monkeypatch.setattr(seeds, "VOLUME_WAIT_SECONDS", 0.5)
    monkeypatch.setattr(seeds, "VOLUME_POLL_SECONDS", 0.1)
    assert seeds._is_volume("volume-3x4-abcdef") and not seeds._is_volume("schema")
    child = subprocess.Popen([sys.executable, "-c", "pass"])
    ended = run_ids.of_process(child.pid)
    child.wait()
    live = run_ids.name("r", run_ids.of_process(1), "v_")  # process 1 outlives the test
    dead = run_ids.name("r", ended, "v_")
    with seeds.admin() as server:
        for database in (live, dead):
            server.execute(text(f'CREATE DATABASE "{database}" TEMPLATE template0'))
    _only_these_holders(monkeypatch, live, dead)  # other runs' volume clones are not this test's
    try:
        with seeds.admin() as server, pytest.raises(TimeoutError, match="p1_"):
            seeds._wait_for_volume(server)
        assert not _exists(dead)  # an ended run's clone is dropped, never waited for
        seeds.drop(live)
        with seeds.admin() as server:
            seeds._wait_for_volume(server)  # free now; returns holding the lock
            server.execute(
                text("SELECT pg_advisory_unlock(hashtext(:n))"), {"n": seeds.VOLUME_LOCK}
            )
    finally:
        seeds.drop(live)
        seeds.drop(dead)


def test_a_browser_runners_clone_command_calls_the_seed_clone_as_it_is_defined():
    """The runners' clone command and `seeds.clone` agree on their arguments: every browser runner
    failed at its first clone when they did not (found by the TS3 lanes run)."""
    import ast
    import inspect
    from pathlib import Path

    accepted = set(inspect.signature(seeds.clone).parameters)
    source = (Path(__file__).parents[2] / "browser_seeds.py").read_text()
    calls = [
        node
        for node in ast.walk(ast.parse(source))
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "clone"
        and getattr(node.func.value, "id", "") == "seeds"
    ]
    assert calls
    for call in calls:
        assert {keyword.arg for keyword in call.keywords} <= accepted
        assert len(call.args) <= len(accepted)


def test_a_holder_of_the_same_run_is_waited_for_without_the_bound(monkeypatch):
    import threading
    import time

    monkeypatch.setattr(seeds, "VOLUME_WAIT_SECONDS", 0.3)
    monkeypatch.setattr(seeds, "VOLUME_POLL_SECONDS", 0.1)
    own = run_ids.name(
        "r", run_ids.current(), "v_"
    )  # another worker of this run: not this process's
    with seeds.admin() as server:
        server.execute(text(f'CREATE DATABASE "{own}" TEMPLATE template0'))
    _only_these_holders(monkeypatch, own)
    threading.Timer(1.0, seeds.drop, args=(own,)).start()  # its module ends, after the bound
    try:
        started = time.monotonic()
        with seeds.admin() as server:
            seeds._wait_for_volume(server)
            server.execute(
                text("SELECT pg_advisory_unlock(hashtext(:n))"), {"n": seeds.VOLUME_LOCK}
            )
        assert time.monotonic() - started > 0.5
    finally:
        seeds.drop(own)


def test_runs_whose_seed_inputs_differ_keep_a_template_each(monkeypatch):
    name = "f8-check"
    inputs = ["first"]
    monkeypatch.setitem(
        seeds.SEEDS, name, seeds.Seed(name, lambda _url: {"built": True}, lambda: list(inputs))
    )
    first = seeds.template_name(name)
    try:
        seeds.ensure(name)
        inputs[:] = ["second"]  # another run, with other inputs, uses the same seed name
        second = seeds.template_name(name)
        assert second != first
        seeds.ensure(name)
        assert _exists(first) and _exists(second)
        inputs[:] = ["first"]  # the first run's template is still current: reused, not rebuilt
        before = len(seeds.ACTIVITY)
        seeds.ensure(name)
        assert seeds.ACTIVITY[before:] == [(name, "reused", 0.0)]
        assert seeds.status(name)[0] == "current"
    finally:
        with seeds.admin() as server:
            for database in (first, second):
                seeds._drop_template(server, database)
        with seeds._catalogue() as catalogue:
            catalogue.execute(text("DELETE FROM seed_builds WHERE name = :n"), {"n": name})
