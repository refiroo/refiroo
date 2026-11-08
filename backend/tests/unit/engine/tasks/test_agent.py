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
    return {
        "key": key,
        "name": key.title(),
        "attributes": [{"attributeTypeKey": a} for a in attributes],
    }


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
        ("Grown", "Changed type (adds b), 2 attributes"),
        ("Loaded", "1 attribute, 1 record"),
        ("Fresh", "New type, 3 attributes, 1,200 records"),
    ]


def test_a_type_that_differs_only_in_form_is_not_changed_and_a_real_difference_is_named():
    base = {
        "attributeTypes": [{"key": "a", "name": "Alpha"}, {"key": "b", "name": "Beta"}],
        "objectTypes": [
            {
                "key": "same",
                "name": "Same",
                "attributes": [
                    {"attributeTypeKey": "a", "required": True, "order": 10, "ui": {}},
                    {"attributeTypeKey": "b", "order": 20},
                ],
            },
            {
                "key": "loosened",
                "name": "Loosened",
                "attributes": [{"attributeTypeKey": "a", "required": True}],
            },
        ],
    }
    model = {
        "attributeTypes": base["attributeTypes"],
        "objectTypes": [
            {
                "key": "same",
                "name": "Same",
                # Listed the other way round, defaults spelled out, another order number.
                "attributes": [
                    {
                        "attributeTypeKey": "b",
                        "required": False,
                        "readOnly": False,
                        "order": 5,
                        "ui": None,
                    },
                    {
                        "attributeTypeKey": "a",
                        "required": True,
                        "readOnly": False,
                        "order": 6,
                        "ui": {},
                    },
                ],
            },
            {
                "key": "loosened",
                "name": "Loosened",
                "attributes": [{"attributeTypeKey": "a", "required": False}],
            },
        ],
    }
    assert [(i["name"], i["text"]) for i in _shape(model, base, {})] == [
        ("Loosened", "Changed type (changes how Alpha is filled in), 1 attribute")
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
    # The session writes for the person, in their terms; the closing lines stay allowed.
    voice = command[command.index("--append-system-prompt") + 1]
    assert "proposal.json" in voice and "CHANGE_SET:" in voice


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
    # Its scratch folder is inside its own folder, the only place every turn may read (task 95).
    assert _session_environment("tok-1", tmp_path)["TMPDIR"] == str(tmp_path / "tmp")
    assert (tmp_path / "tmp").is_dir()
    from app.engine.tasks.agent import _folder_rule

    assert f"$TMPDIR is {tmp_path / 'tmp'}" in _folder_rule(tmp_path)
    monkeypatch.setenv("AI_AGENT_SANDBOX", "")
    assert _command(tmp_path, "Words", "s-1", False)[0] == "claude"


def test_the_session_is_verified_by_tls_unless_the_api_is_on_this_machine():
    from app.engine.tasks.agent import _connection, _loopback

    assert _loopback("https://localhost:8000") and _loopback("http://127.0.0.1:8000")
    assert not _loopback("https://192.168.0.36:8000") and not _loopback("https://rdm.example.org")
    assert "curl -k" in _connection("w", "https://localhost:8000")
    assert "curl -k" not in _connection("w", "https://rdm.example.org")


def test_the_session_runs_restricted_outside_a_container_and_unprompted_inside_one(
    monkeypatch, tmp_path
):
    """Container: no --restricted, permission prompts off, no setting sources; host: unchanged."""
    from app.engine.tasks.agent import _safeguards

    monkeypatch.setenv("AI_AGENT_SANDBOX", "container")
    inside = _safeguards("http://127.0.0.1:8000", tmp_path)
    assert "--restricted" not in inside and "dontAsk" not in inside
    assert inside[inside.index("--permission-mode") + 1] == "bypassPermissions"
    assert inside[inside.index("--setting-sources") + 1] == ""
    assert "--strict-mcp-config" in inside and "--disallowedTools" in inside
    # The read block refuses `$REFIROO_TOKEN` in compound commands; the assistant user is the boundary.
    assert "permissions" not in json.loads(inside[inside.index("--settings") + 1])

    monkeypatch.delenv("AI_AGENT_SANDBOX", raising=False)
    outside = _safeguards("http://127.0.0.1:8000", tmp_path)
    assert "--restricted" in outside and "bypassPermissions" not in outside
    assert outside[outside.index("--permission-mode") + 1] == "dontAsk"
    assert "--setting-sources" not in outside
    host = json.loads(outside[outside.index("--settings") + 1])
    assert host["permissions"] == {"blockReadsOutsideWorkingDirectories": True}


def _landing(monkeypatch, tmp_path, proposal, *, workbook):
    """``_proposal_landed`` for a task whose session wrote ``proposal`` (``workbook``: the task has a file)."""
    from unittest.mock import MagicMock

    from app.engine.tasks import agent

    task = SimpleNamespace(
        id=1, state="reading", notes=[], design={"stage": "model"}, draft_id=None, check="old"
    )
    monkeypatch.setattr(agent, "load_task", lambda *args, **kwargs: task)
    monkeypatch.setattr(agent, "touch", lambda *args, **kwargs: None, raising=False)
    monkeypatch.setattr("app.engine.tasks.store.touch", lambda *args, **kwargs: None)
    (tmp_path / agent.PROPOSAL).write_text(json.dumps(proposal))
    session = MagicMock()
    session.scalar.return_value = 7 if workbook else None
    progress = SimpleNamespace(result={"result": "Done."})
    agent._proposal_landed(session, None, "t", tmp_path, progress, None, None)
    return task


def test_a_words_proposal_without_a_draft_is_a_proposal_with_no_model_change(monkeypatch, tmp_path):
    task = _landing(
        monkeypatch,
        tmp_path,
        {"draftId": None, "summary": "Set the abbreviation.", "questions": [{"text": "Sure?"}]},
        workbook=False,
    )
    assert task.state == "checked" and task.draft_id is None and task.check is None
    assert task.design["modelUnchanged"] is True and task.design["stage"] == "model"
    assert task.design["summary"] == "Set the abbreviation."
    assert task.design["questions"][0]["text"] == "Sure?"
    assert task.design["moves"] == [] and task.design["outline"] == []


def test_a_workbook_proposal_without_a_draft_still_fails(monkeypatch, tmp_path):
    task = _landing(monkeypatch, tmp_path, {"draftId": None, "summary": "A plan."}, workbook=True)
    assert task.state == "failed" and "modelUnchanged" not in task.design


def test_a_words_proposal_without_a_summary_or_with_moves_or_a_missing_draft_still_fails(
    monkeypatch, tmp_path
):
    for proposal in (
        {"draftId": None, "summary": " "},
        {"draftId": None, "summary": "Merge.", "moves": [{"from": "a", "to": "b"}]},
    ):
        assert _landing(monkeypatch, tmp_path, proposal, workbook=False).state == "failed"


def test_accepting_a_proposal_without_a_draft_asks_for_the_change_set_on_the_live_release():
    from app.engine.tasks import agent

    assert "install no release" in agent._ACCEPTED_UNCHANGED
    assert "source currentLive" in agent._ACCEPTED_UNCHANGED and agent.LAST_LINE in (
        agent._ACCEPTED_UNCHANGED
    )
    assert "Install" in agent._ACCEPTED
