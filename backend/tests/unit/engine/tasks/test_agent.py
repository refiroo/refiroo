"""The assistant's session in its folder, and its checklist from what the engine recorded."""

import signal
import subprocess
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

from app.engine.tasks.agent import _steps, _stop_earlier

NOW = datetime(2026, 10, 31, 12, tzinfo=UTC)


def _job(kind, state="completed", rejected=0, applied=10, at=NOW):
    return SimpleNamespace(
        kind=kind, state=state, counts={"rejected": rejected, "applied": applied}, created_at=at
    )


def _reached(*args):
    steps, refused = _steps(*args)
    return {step["key"]: (step["done"], step["running"]) for step in steps}, refused


def test_a_turn_with_nothing_recorded_has_reached_nothing_and_lists_only_its_own_steps():
    assert _reached(False, False, {}, []) == (
        {"draft": (False, False), "operations": (False, False), "check": (False, False)},
        None,
    )
    assert _reached(True, True, {}, []) == (
        {"install": (False, False), "load": (False, False)},
        None,
    )


def test_a_check_counts_until_the_model_changes_again():
    changed = {("model_draft", "updated"): NOW}
    steps, refused = _reached(False, True, changed, [_job("dryRun", rejected=3)])
    assert steps["check"] == (True, False) and refused == 3
    later = {("model_draft", "updated"): NOW + timedelta(seconds=5)}
    steps, refused = _reached(False, True, later, [_job("dryRun", rejected=3)])
    assert steps["check"] == (False, False) and refused is None


def test_a_running_check_is_in_progress():
    steps, _ = _steps(False, True, {}, [_job("dryRun", state="running")])
    assert steps[2]["label"] == "Checking every row"
    assert (steps[2]["done"], steps[2]["running"]) == (False, True)


def test_a_load_counts_only_when_it_applied_without_a_refusal():
    refused = _job("import", rejected=3454, applied=0)
    assert _reached(True, True, {}, [refused])[0]["load"] == (False, False)
    assert _reached(True, True, {}, [refused, _job("import")])[0]["load"] == (True, False)
    assert _reached(True, True, {}, [_job("import", state="running")])[0]["load"] == (False, True)


def test_a_session_left_by_a_stopped_worker_is_ended_and_another_process_is_not():
    session = "5f1c0f7e-left-behind"
    left = subprocess.Popen(["sh", "-c", f"sleep 30; : {session}"], start_new_session=True)
    other = subprocess.Popen(["sleep", "30"], start_new_session=True)
    try:
        _stop_earlier({"pid": other.pid, "session": session})
        assert other.poll() is None
        _stop_earlier({"pid": left.pid, "session": session})
        assert left.wait(timeout=5) == -signal.SIGKILL
        _stop_earlier({"pid": left.pid, "session": session})
    finally:
        other.kill()
        other.wait()
        if left.poll() is None:
            left.kill()
