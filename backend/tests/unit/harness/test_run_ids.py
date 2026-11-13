"""A database name says which run owns it, and whether that run is still alive (TS2)."""

import os
import subprocess
import sys
import time

import run_ids


def test_a_name_carries_the_owning_run():
    run = run_ids.current()
    database = run_ids.name()
    assert database.startswith(f"t_{run}_")
    assert run_ids.run_of(database) == run
    assert run_ids.run_of(run_ids.name("r", "p12_34")) == "p12_34"
    assert run_ids.run_of("postgres") is None


def test_a_run_is_live_while_its_process_runs_and_not_when_the_number_is_reused():
    pid = os.getpid()
    began = run_ids.started(pid)
    assert began is not None and abs(began - time.time()) < 365 * 86400
    assert run_ids.is_live(f"p{pid}_{began}")
    # The same process number started at another time belongs to another process.
    assert not run_ids.is_live(f"p{pid}_{began - 100}")


def test_a_run_whose_process_ended_is_not_live():
    child = subprocess.Popen([sys.executable, "-c", "pass"])
    run = run_ids.of_process(child.pid)
    child.wait()
    assert not run_ids.is_live(run)
    assert not run_ids.is_live("not-a-run")


def test_workers_belong_to_the_controllers_run():
    # A worker inherits the controller's environment and so takes its run ID, not one of its own.
    code = "import run_ids; print(run_ids.current())"
    output = subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
        text=True,
        check=True,
        cwd=os.path.dirname(run_ids.__file__),
        env={**os.environ, run_ids.ENVIRONMENT: "p7_8"},
    ).stdout.strip()
    assert output == "p7_8"
    assert run_ids.current() == os.environ[run_ids.ENVIRONMENT]


def test_only_clones_of_ended_runs_are_abandoned():
    child = subprocess.Popen([sys.executable, "-c", "pass"])
    ended = run_ids.of_process(child.pid)
    child.wait()
    assert not run_ids.abandoned(run_ids.name())
    assert run_ids.abandoned(run_ids.name(run=ended))
    assert run_ids.abandoned(run_ids.name("r", ended))
    # Databases that are not clones are never dropped, and a seed is not a clone.
    for kept in ("postgres", "rdm_harness", "seed_schema", "seed_schema__build", "template1"):
        assert not run_ids.abandoned(kept)


def test_clones_without_a_run_id_follow_the_old_rules():
    assert run_ids.abandoned("t_0123456789abcdef")
    assert run_ids.abandoned("t_session_gw1_0123abcd")
    now = time.time()
    assert run_ids.abandoned(f"r_{int(now) - 7 * 3600}_0123abcd", now)
    assert not run_ids.abandoned(f"r_{int(now) - 60}_0123abcd", now)
