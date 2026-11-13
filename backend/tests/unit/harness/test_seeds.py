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
