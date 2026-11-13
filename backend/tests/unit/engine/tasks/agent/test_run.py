"""One turn of the assistant session, its progress and its checklist (``engine/tasks/agent/run.py``)."""

import json
import os
import pwd
import signal
import subprocess
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace

from app.engine.tasks.agent.run import _steps, _stop_earlier

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
        assert left.wait(timeout=5) == -signal.SIGTERM
        _stop_earlier({"pid": left.pid, "session": session})
    finally:
        other.kill()
        other.wait()
        if left.poll() is None:
            left.kill()


def test_stopping_a_session_in_an_image_without_ps_ends_it_and_never_raises(monkeypatch):
    """The reference engine's image has no ``ps``: a person's Stop must still reach the task as
    their stop, not as an internal error (0.13 DOC11 F6)."""
    from app.engine.tasks.agent import run as agent_run

    def no_ps(*args, **kwargs):
        raise FileNotFoundError("ps")

    monkeypatch.setattr(subprocess, "run", no_ps)
    gone = 4_000_000
    assert agent_run._command_of(gone) == ""
    _stop_earlier({"pid": gone, "session": "5f1c0f7e-no-ps"})
    # A process this machine can name without ps (/proc) is ended the same way.
    if Path("/proc/self/cmdline").exists():
        session = "5f1c0f7e-proc"
        left = subprocess.Popen(["sh", "-c", f"sleep 30; : {session}"], start_new_session=True)
        try:
            _stop_earlier({"pid": left.pid, "session": session})
            assert left.wait(timeout=5) == -signal.SIGTERM
        finally:
            if left.poll() is None:
                left.kill()


def test_the_persons_words_are_the_last_argument_after_the_end_of_the_options(
    monkeypatch, tmp_path
):
    """Words that look like options (R-F9) are the prompt, not a flag of the command."""
    from app.engine.tasks.agent.run import _command

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


def test_in_a_container_the_session_runs_as_a_pool_user_through_sudo_with_nothing_secret_on_its_command_line(
    monkeypatch, tmp_path
):
    """R-F45, 0.17 RF5: the command runs as one user of the pool; the folder's path and the person's
    words are no argument (any process of the container reads those), and the token is not either."""
    from app.engine.tasks.agent.run import _command
    from app.engine.tasks.agent.sandbox import session_environment

    monkeypatch.setenv("AI_AGENT_COMMAND", "claude --model sonnet")
    monkeypatch.setenv("AI_AGENT_SANDBOX", "container")
    monkeypatch.setenv("DATABASE_URL", "postgresql://secret")
    folder = tmp_path / "random-name" / "work"
    command = _command(folder, "Words that are private", "s-1", False, "assistant-3")
    assert command[:6] == ["sudo", "-n", "-u", "assistant-3", "--", "claude"]
    assert "--resume" in command and command[command.index("--resume") + 1] == "s-1"
    shown = " ".join(command)
    assert "random-name" not in shown and str(tmp_path) not in shown
    assert "Words that are private" not in shown and "--" not in command[6:]
    # The sandbox of the operating system is off in a container, and the token is no argument.
    settings = json.loads(command[command.index("--settings") + 1])
    assert settings["sandbox"]["enabled"] is False
    assert "filesystem" not in settings["sandbox"] and "network" not in settings["sandbox"]
    environment = session_environment("tok-1")
    assert "DATABASE_URL" not in environment and environment["REFIROO_TOKEN"] == "tok-1"
    assert "tok-1" not in shown
    # Its scratch folder is inside its own folder, the only place every turn may read (task 95).
    # The engine names its scratch folder and makes none: a session may have replaced what is there.
    assert session_environment("tok-1", tmp_path)["TMPDIR"] == str(tmp_path / "tmp")
    assert not (tmp_path / "tmp").exists()
    from app.engine.tasks.agent.run import _folder_rule

    assert f"$TMPDIR is {tmp_path / 'tmp'}" in _folder_rule(tmp_path)
    monkeypatch.setenv("AI_AGENT_SANDBOX", "")
    assert _command(tmp_path, "Words", "s-1", False)[0] == "claude"


def test_the_words_go_to_the_sessions_standard_input_in_a_container(monkeypatch, tmp_path):
    from app.engine.tasks.agent import run as agent_run

    monkeypatch.setenv("AI_AGENT_SANDBOX", "container")
    with subprocess.Popen(
        ["cat"], stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True
    ) as process:
        agent_run._feed(process, "Words\nof two lines")
        assert process.stdout.read() == "Words\nof two lines"
    # A session that has ended before it read the words is no failure of the feeding.
    with subprocess.Popen(["true"], stdin=subprocess.PIPE, text=True) as gone:
        gone.wait()
        agent_run._feed(gone, "x" * 200_000)


def test_the_reset_runs_before_and_after_a_turn_and_a_failing_one_fails_the_turn(
    monkeypatch, tmp_path
):
    from app.engine.tasks.agent import run as agent_run
    from app.engine.tasks.agent import sandbox as agent_sandbox

    folder = tmp_path / "gate" / "work"
    folder.mkdir(parents=True)
    events = []

    class Lock:
        def close(self):
            events.append("lock closed")

    monkeypatch.setenv("AI_AGENT_SANDBOX", "container")
    monkeypatch.setenv("AI_AGENT_FOLDERS", str(tmp_path / "assistant"))
    monkeypatch.setattr(agent_run, "take_session_user", lambda slots: ("assistant-3", Lock()))
    monkeypatch.setattr(agent_run, "open_gate", lambda gate, user: events.append(f"open {user}"))
    monkeypatch.setattr(
        agent_run, "close_gates_of", lambda root, user: events.append(f"stale {user}")
    )
    monkeypatch.setattr(agent_run, "close_gate", lambda gate: events.append("close"))
    monkeypatch.setattr(
        agent_run,
        "reset",
        lambda user, config=None, work=None: events.append(
            f"reset {user}" + (" with folders" if work is not None else "")
        ),
    )
    monkeypatch.setattr(agent_run, "ensure_tmp", lambda work: events.append("tmp"))
    monkeypatch.setattr(
        agent_run, "_command", lambda *a, **k: (_ for _ in ()).throw(OSError("stop"))
    )
    monkeypatch.setattr(agent_run, "_end", lambda *a: None)
    monkeypatch.setattr(agent_run, "_record_turn", lambda *a, **k: None)
    monkeypatch.setattr(agent_run, "note", lambda *a: None)
    monkeypatch.setattr(agent_run, "finish", lambda *a: None)
    monkeypatch.setattr(agent_run, "retention", lambda ctx: 1)
    monkeypatch.setattr(agent_run, "load_task", lambda *a, **k: SimpleNamespace(design={}))
    session = SimpleNamespace(commit=lambda: None)
    job = SimpleNamespace(id="j")
    args = (session, job, SimpleNamespace(), "t1", folder, "p", "s", "tok", 1, [])
    assert agent_run._turn(*args, first=True, load=False) is None
    # Before: the reset first, the gate still closed, then the gate opens. After: the reset first, the
    # gate still open for the user's files, then the gate closes, then the user is let go.
    assert events == ["reset assistant-3", "stale assistant-3", "open assistant-3", "tmp",
                      "reset assistant-3 with folders", "close", "lock closed"]  # fmt: skip
    # A reset that does not finish ends the turn before the session starts, naming what failed.
    events.clear()
    notes = []
    monkeypatch.setattr(agent_run, "note", lambda task, kind, text: notes.append(text))

    def failing(user, config=None, work=None):
        events.append(f"reset {user}")
        raise agent_sandbox.ResetFailed("The reset of session user assistant-3 did not finish")

    monkeypatch.setattr(agent_run, "reset", failing)
    assert agent_run._turn(*args, first=True, load=False) is None
    # A reset that fails before a turn opens no gate and starts no session; the user is let go.
    assert events == ["reset assistant-3", "lock closed"]
    assert notes == ["The reset of session user assistant-3 did not finish"]


def test_a_gate_that_cannot_be_closed_fails_the_turn_and_no_gate_opens(monkeypatch, tmp_path):
    from app.engine.tasks.agent import run as agent_run
    from app.engine.tasks.agent import sandbox as agent_sandbox

    root = tmp_path / "assistant"
    stale = root / "stale"
    stale.mkdir(parents=True)
    stale.chmod(0o710)
    monkeypatch.setattr(pwd, "getpwnam", lambda name: SimpleNamespace(pw_gid=stale.stat().st_gid))

    def refuse(descriptor, mode):
        raise PermissionError("operation not permitted")

    monkeypatch.setattr(os, "fchmod", refuse)
    try:
        agent_sandbox.close_gates_of(root, "assistant-2")
    except agent_sandbox.ResetFailed as error:
        assert "could not be closed" in str(error) and "assistant-2" in str(error)
    else:
        raise AssertionError("a gate that stayed open let the turn go on")
    monkeypatch.undo()
    # In a turn it is the same failure as a failed reset: no gate opens, no session starts.
    events = []
    folder = tmp_path / "gate" / "work"
    folder.mkdir(parents=True)

    class Lock:
        def close(self):
            events.append("lock closed")

    monkeypatch.setenv("AI_AGENT_SANDBOX", "container")
    monkeypatch.setenv("AI_AGENT_FOLDERS", str(root))
    monkeypatch.setattr(agent_run, "take_session_user", lambda slots: ("assistant-2", Lock()))
    monkeypatch.setattr(agent_run, "reset", lambda *a, **k: events.append("reset"))
    monkeypatch.setattr(agent_run, "open_gate", lambda *a: events.append("open"))
    monkeypatch.setattr(agent_run, "close_gate", lambda *a: events.append("close"))

    def stuck(root, user):
        raise agent_sandbox.ResetFailed("A task's folder still open could not be closed")

    notes = []
    monkeypatch.setattr(agent_run, "close_gates_of", stuck)
    for name in ("_end", "_record_turn", "finish"):
        monkeypatch.setattr(agent_run, name, lambda *a, **k: None)
    monkeypatch.setattr(agent_run, "note", lambda task, kind, text: notes.append(text))
    monkeypatch.setattr(agent_run, "retention", lambda ctx: 1)
    monkeypatch.setattr(agent_run, "load_task", lambda *a, **k: SimpleNamespace(design={}))
    args = (SimpleNamespace(commit=lambda: None), SimpleNamespace(id="j"), SimpleNamespace(),
            "t1", folder, "p", "s", "tok", 1, [])  # fmt: skip
    assert agent_run._turn(*args, first=True, load=False) is None
    assert events == ["reset", "lock closed"] and "could not be closed" in notes[0]


def test_the_progress_of_a_turn_is_read_through_the_descriptor_it_opened(tmp_path):
    """Review finding: the log was reopened by path in a folder the session writes in; a link to
    /dev/zero there would have been read until memory ran out."""
    from app.engine.tasks.agent.run import Progress

    log = tmp_path / "turn.log"
    log.write_text(json.dumps({"type": "result", "result": "first"}) + "\n")
    progress = Progress(log)
    progress.read()
    assert progress.result["result"] == "first"
    elsewhere = tmp_path / "elsewhere.log"
    elsewhere.write_text(json.dumps({"type": "result", "result": "elsewhere"}) + "\n")
    held = log.with_name("held.log")
    log.rename(held)
    log.symlink_to(elsewhere)
    with held.open("a") as more:
        more.write(json.dumps({"type": "result", "result": "second"}) + "\n")
    progress.read()
    progress.close()
    assert progress.result["result"] == "second"
    # A link in its place from the start is not a log, and nor is anything but a regular file.
    planted = Progress(tmp_path / "planted.log")
    (tmp_path / "planted.log").symlink_to(elsewhere)
    assert planted.read() is False and planted.result == {}
    os.mkfifo(tmp_path / "fifo.log")
    assert Progress(tmp_path / "fifo.log").read() is False


def test_the_note_the_person_reads_drops_sentences_that_talk_about_the_proposal_file_and_its_keys():
    """The session's closing words are shown on the task: sentences about its own file, draftId,
    the moves or removals lists and movedTo are not (0.13 DOC11 15, as F4)."""
    from app.engine.tasks.agent.run import closing_words

    said = (
        "This is a partial move: Route splits into Local route and Other route. "
        "Its draftId is the draft's ID and its moves list is empty, because Route splits into two types. "
        "Its removals list has one entry, Route, with movedTo set to the two new types. "
        "The proposal is in proposal.json in this folder. "
        "Nothing is staged now."
    )
    progress = SimpleNamespace(
        result={"result": said, "duration_ms": 43000, "total_cost_usd": 0.16}
    )
    text = closing_words(progress)
    assert text.startswith(
        "This is a partial move: Route splits into Local route and Other route. Nothing is staged now."
    )
    for internal in ("draftId", "movedTo", "moves list", "removals list", "proposal.json"):
        assert internal not in text
