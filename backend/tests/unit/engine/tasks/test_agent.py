"""The assistant's session in its folder, and its checklist from what the engine recorded."""

import json
import signal
import subprocess
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

from app.engine.tasks.agent import _left_out, _shape, _starting_point, _steps, _stop_earlier

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


def _type(key, *attributes):
    return {"key": key, "name": key.title(), "attributes": [{"key": a} for a in attributes]}


def test_the_shape_names_what_a_proposal_adds_changes_or_loads_and_leaves_the_rest_out():
    base = {"objectTypes": [_type("kept", "a"), _type("grown", "a"), _type("loaded", "a")]}
    model = {
        "objectTypes": [
            _type("kept", "a"),
            _type("grown", "a", "b"),
            _type("loaded", "a"),
            _type("fresh", "a", "b", "c"),
        ]
    }
    shape = _shape(model, base, {"loaded": 1, "fresh": 1200})
    assert [(item["name"], item["text"]) for item in shape] == [
        ("Grown", "Changed type, 2 attributes"),
        ("Loaded", "1 attribute, 1 record"),
        ("Fresh", "New type, 3 attributes, 1,200 records"),
    ]


def test_types_holding_records_that_a_model_drops_are_flagged_and_empty_ones_are_not():
    base = {"objectTypes": [_type("held"), _type("empty")]}
    assert _left_out({"objectTypes": [_type("held")]}, base, {"held": 3}) == []
    assert _left_out({"objectTypes": []}, base, {}) == []
    found = _left_out({"objectTypes": []}, base, {"held": 3})
    assert found[0]["open"] and "Held (3)" in found[0]["text"]


def test_what_the_workspace_holds_decides_whether_the_session_adds_or_may_start_anew():
    assert "add to it" in _starting_point({"a": 2, "b": 1})
    assert "3 records" in _starting_point({"a": 2, "b": 1})
    assert "new one" in _starting_point({})


def test_the_persons_words_are_the_last_argument_after_the_end_of_the_options(
    monkeypatch, tmp_path
):
    """Words that look like options (R-F9) are the prompt, not a flag of the command."""
    from app.engine.tasks.agent import _command

    monkeypatch.setenv("AI_AGENT_COMMAND", "claude --model sonnet")
    monkeypatch.delenv("AI_AGENT_SANDBOX", raising=False)
    command = _command(tmp_path, "--dangerously-skip-permissions please", "s-1", True)
    assert command[:3] == ["claude", "--model", "sonnet"]
    assert command[-2:] == ["--", "--dangerously-skip-permissions please"]
    assert command.count("--dangerously-skip-permissions") == 0
    assert command[command.index("--session-id") + 1] == "s-1"


def test_in_a_container_the_session_runs_as_the_assistant_user_through_sudo(monkeypatch, tmp_path):
    """R-F45: the command is prefixed to run as its own user; outside a container it is not."""
    from app.engine.tasks.agent import _command, _session_environment

    monkeypatch.setenv("AI_AGENT_COMMAND", "claude --model sonnet")
    monkeypatch.setenv("AI_AGENT_SANDBOX", "container")
    monkeypatch.setenv("DATABASE_URL", "postgresql://secret")
    command = _command(tmp_path, "Words", "s-1", False)
    assert command[:6] == ["sudo", "-n", "-u", "assistant", "--", "claude"]
    assert command[-2:] == ["--", "Words"] and "--resume" in command
    # The sandbox of the operating system is off in a container, and the token is no argument.
    settings = json.loads(command[command.index("--settings") + 1])
    assert settings["sandbox"]["enabled"] is False
    environment = _session_environment("tok-1")
    assert "DATABASE_URL" not in environment and environment["REFIROO_TOKEN"] == "tok-1"
    assert "tok-1" not in " ".join(command)
    monkeypatch.setenv("AI_AGENT_SANDBOX", "")
    assert _command(tmp_path, "Words", "s-1", False)[0] == "claude"


def test_the_session_is_verified_by_tls_unless_the_api_is_on_this_machine():
    from app.engine.tasks.agent import _connection, _loopback

    assert _loopback("https://localhost:8000") and _loopback("http://127.0.0.1:8000")
    assert not _loopback("https://192.168.0.36:8000") and not _loopback("https://rdm.example.org")
    assert "curl -k" in _connection("w", "https://localhost:8000")
    assert "curl -k" not in _connection("w", "https://rdm.example.org")
