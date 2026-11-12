"""The assistant's session in its folder, and its checklist from what the engine recorded."""

import fcntl
import json
import os
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
    from app.engine.tasks import agent

    def no_ps(*args, **kwargs):
        raise FileNotFoundError("ps")

    monkeypatch.setattr(agent.subprocess, "run", no_ps)
    gone = 4_000_000
    assert agent._command_of(gone) == ""
    _stop_earlier({"pid": gone, "session": "5f1c0f7e-no-ps"})
    # A process this machine can name without ps (/proc) is ended the same way.
    if agent.Path("/proc/self/cmdline").exists():
        session = "5f1c0f7e-proc"
        left = subprocess.Popen(["sh", "-c", f"sleep 30; : {session}"], start_new_session=True)
        try:
            _stop_earlier({"pid": left.pid, "session": session})
            assert left.wait(timeout=5) == -signal.SIGTERM
        finally:
            if left.poll() is None:
                left.kill()


def test_a_session_stopped_before_it_wrote_a_transcript_has_nothing_to_resume(
    monkeypatch, tmp_path
):
    """A Stop in the first seconds leaves no conversation: Go on as it was starts the session
    again instead of resuming one that does not exist (0.13 DOC11 13)."""
    from app.engine.tasks import agent

    files = SimpleNamespace(directory=tmp_path / "files")
    task = SimpleNamespace(public_id="t1", design={"agentSession": "s-1"})
    monkeypatch.delenv("CLAUDE_CONFIG_DIR", raising=False)
    assert agent.resumable(files, task) is True
    monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(tmp_path / "claude"))
    assert agent.resumable(files, task) is False
    folder = agent.folder_of(files, task)
    kept = tmp_path / "claude" / "projects" / agent._transcript_name(folder)
    kept.mkdir(parents=True)
    (kept / "s-1.jsonl").write_text("{}")
    assert agent.resumable(files, task) is True


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


def test_in_a_container_the_session_runs_as_a_pool_user_through_sudo_with_nothing_secret_on_its_command_line(
    monkeypatch, tmp_path
):
    """R-F45, 0.17 RF5: the command runs as one user of the pool; the folder's path and the person's
    words are no argument (any process of the container reads those), and the token is not either."""
    from app.engine.tasks.agent import _command, _session_environment

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
    environment = _session_environment("tok-1")
    assert "DATABASE_URL" not in environment and environment["REFIROO_TOKEN"] == "tok-1"
    assert "tok-1" not in shown
    # Its scratch folder is inside its own folder, the only place every turn may read (task 95).
    # The engine names its scratch folder and makes none: a session may have replaced what is there.
    assert _session_environment("tok-1", tmp_path)["TMPDIR"] == str(tmp_path / "tmp")
    assert not (tmp_path / "tmp").exists()
    from app.engine.tasks.agent import _folder_rule

    assert f"$TMPDIR is {tmp_path / 'tmp'}" in _folder_rule(tmp_path)
    monkeypatch.setenv("AI_AGENT_SANDBOX", "")
    assert _command(tmp_path, "Words", "s-1", False)[0] == "claude"


def test_the_words_go_to_the_sessions_standard_input_in_a_container(monkeypatch, tmp_path):
    from app.engine.tasks import agent

    monkeypatch.setenv("AI_AGENT_SANDBOX", "container")
    with subprocess.Popen(
        ["cat"], stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True
    ) as process:
        agent._feed(process, "Words\nof two lines")
        assert process.stdout.read() == "Words\nof two lines"
    # A session that has ended before it read the words is no failure of the feeding.
    with subprocess.Popen(["true"], stdin=subprocess.PIPE, text=True) as gone:
        gone.wait()
        agent._feed(gone, "x" * 200_000)


def test_the_session_sees_only_the_named_variables(monkeypatch, tmp_path):
    from app.engine.tasks import agent

    # The machine's own environment must not leak into what is asserted.
    machine = {"PATH": "/usr/bin", "AI_AGENT_SANDBOX": "container"}
    monkeypatch.setattr(agent.os, "environ", machine)
    machine.update(
        {
            "ANTHROPIC_API_KEY": "k",
            "CLAUDE_CODE_OAUTH_TOKEN": "o",
            "ANTHROPIC_BASE_URL": "https://gateway",
            "ANTHROPIC_MODEL": "m",
            "NODE_EXTRA_CA_CERTS": "/ca.pem",
            "LC_ALL": "C.UTF-8",
            "LANG": "C.UTF-8",
            # Not on the list, whatever their prefix: nothing else of Claude Code's, AWS's or Node's.
            "ANTHROPIC_FUTURE_THING": "x",
            "CLAUDE_CODE_SOMETHING": "x",
            "AWS_SECRET_ACCESS_KEY": "aws-secret",
            "AWS_REGION": "eu-west-1",
            "NODE_OPTIONS": "--require /x",
            "SECRETS_ENCRYPTION_KEY": "never",
            "HOME": "/home/engine",
        }
    )
    seen = agent._session_environment("t", tmp_path, tmp_path / "claude")
    assert set(seen) == {
        "ANTHROPIC_API_KEY", "CLAUDE_CODE_OAUTH_TOKEN", "ANTHROPIC_BASE_URL", "ANTHROPIC_MODEL",
        "NODE_EXTRA_CA_CERTS", "LC_ALL", "LANG", "REFIROO_TOKEN", "PATH", "TMPDIR",
        "CLAUDE_CONFIG_DIR",
    }  # fmt: skip
    assert seen["CLAUDE_CONFIG_DIR"] == str(tmp_path / "claude")
    # Bedrock's names only when Bedrock is on.
    machine["CLAUDE_CODE_USE_BEDROCK"] = "1"
    bedrock = agent._session_environment("t")
    assert bedrock["AWS_SECRET_ACCESS_KEY"] == "aws-secret" and bedrock["AWS_REGION"] == "eu-west-1"
    assert "NODE_OPTIONS" not in bedrock
    # Outside a container the same list, with the developer's own HOME, USER and SHELL.
    machine["AI_AGENT_SANDBOX"] = ""
    del machine["CLAUDE_CODE_USE_BEDROCK"]
    assert agent._session_environment("t")["HOME"] == "/home/engine"
    assert "SECRETS_ENCRYPTION_KEY" not in agent._session_environment("t")


def test_the_sudoers_rule_keeps_exactly_the_names_the_engine_passes():
    """The engine's list and the image's sudoers line are one list: sudo would drop a name added to
    only one of them, or keep one the engine never passes."""
    import re
    from pathlib import Path

    from app.engine.tasks import agent

    dockerfile = Path(__file__).parents[4] / "Dockerfile"
    kept = re.search(r'env_keep = "([^"]*)"', dockerfile.read_text())
    assert kept is not None
    expected = {
        *agent.PASSED_NAMES,
        *agent.BEDROCK_NAMES,
        *(p + "*" for p in agent.PASSED_PREFIXES),
    }
    assert set(kept.group(1).split()) == expected
    text = dockerfile.read_text()
    assert "ASSISTANTS" in text and "(assistant)" not in text
    # Two commands as a pool user, and nothing else: the session's binary and the reset between turns.
    rule = re.search(r"rdm ALL=\(ASSISTANTS\) NOPASSWD: ([^']*)'", text)
    assert rule is not None
    assert [c.strip() for c in rule.group(1).split(",")] == [
        "/usr/local/bin/claude",
        agent.RESET_COMMAND,
    ]


def test_a_turn_holds_a_session_user_until_it_ends_and_none_free_says_what_to_raise(
    monkeypatch, tmp_path
):
    from app.engine.tasks import agent

    monkeypatch.setattr(agent, "_pool_users", lambda: ["assistant-1", "assistant-2"])
    slots = tmp_path / "assistant-slots"
    first, first_lock = agent._take_session_user(slots)
    second, second_lock = agent._take_session_user(slots)
    assert (first, second) == ("assistant-1", "assistant-2")
    assert oct(slots.stat().st_mode & 0o777) == "0o700"
    try:
        agent._take_session_user(slots)
    except agent.NoSessionUser as error:
        assert "ASSISTANT_USERS" in str(error) and "all 2" in str(error)
    else:
        raise AssertionError("a third turn found a user")
    # The end of a turn frees its user.
    first_lock.close()
    again, again_lock = agent._take_session_user(slots)
    assert again == "assistant-1"
    again_lock.close()
    second_lock.close()
    monkeypatch.setattr(agent, "_pool_users", list)
    try:
        agent._take_session_user(slots)
    except agent.NoSessionUser as error:
        assert "ASSISTANT_USERS" in str(error)
    else:
        raise AssertionError("no pool, yet a user")


def _planted(tmp_path):
    """A working folder whose scratch folder, files and Claude Code folder a session has replaced by
    links to a folder of the engine's: ``victim`` stands for ``data/assistant`` itself."""
    victim = tmp_path / "victim"
    victim.mkdir(mode=0o750)
    victim.chmod(0o750)
    secret = victim / "secret.txt"
    secret.write_text("not for the session")
    home = tmp_path / "home"
    (home / "work").mkdir(parents=True)
    (home / "claude").mkdir()
    (home / "work" / "tmp").symlink_to(victim)
    (home / "work" / "proposal.json").symlink_to(secret)
    (home / "work" / "workbook.xlsx").symlink_to(secret)
    (home / "claude" / "sessions").symlink_to(victim)
    return victim, secret, home


def test_a_link_a_session_planted_is_never_followed_by_the_engine(monkeypatch, tmp_path):
    """Review finding: ``mkdir(exist_ok=True)`` and ``chmod`` followed a link in a folder the session
    writes in, so one turn changed the mode of the tasks' root and the next let every session in."""
    from app.engine.tasks import agent

    victim, secret, home = _planted(tmp_path)
    work = home / "work"
    monkeypatch.setenv("AI_AGENT_SANDBOX", "")
    agent._ensure_tmp(work)
    assert (work / "tmp").is_dir() and not (work / "tmp").is_symlink()
    assert oct(victim.stat().st_mode & 0o777) == "0o750" and secret.exists()
    # The engine makes no folder of a task that has them and changes nothing in them.
    monkeypatch.setenv("AI_AGENT_SANDBOX", "container")
    monkeypatch.setattr(agent, "_create_task_folders", lambda *a, **k: 1 / 0)
    agent._make_folders(work)
    assert (home / "claude" / "sessions").is_symlink()
    assert oct(victim.stat().st_mode & 0o777) == "0o750"
    # What the session wrote is read through no link, from no other kind of file, and no more than a limit.
    assert agent._read_work(work, "proposal.json") is None
    (work / "proposal.json").unlink()
    os.mkfifo(work / "proposal.json")
    assert agent._read_work(work, "proposal.json") is None
    (work / "proposal.json").unlink()
    (work / "proposal.json").write_text('{"draftId": 1}')
    assert agent._read_work(work, "proposal.json") == '{"draftId": 1}'
    assert agent._read_work(work, "proposal.json", limit=3) is None
    # What the engine hands the session replaces a link and writes nothing through it.
    agent._put(work, "workbook.xlsx", b"new")
    assert (work / "workbook.xlsx").read_bytes() == b"new" and not (
        work / "workbook.xlsx"
    ).is_symlink()
    assert secret.read_text() == "not for the session"
    (work / "proposal.json").unlink()
    (work / "proposal.json").symlink_to(secret)
    agent._drop(work, "proposal.json")
    assert not (work / "proposal.json").exists() and secret.exists()
    # Removing the task's folder removes a link and never what it points to.
    task = SimpleNamespace(public_id="t1", design={})
    monkeypatch.setenv("AI_AGENT_FOLDERS", str(tmp_path))
    monkeypatch.setattr(agent, "home_of", lambda files, t: home)
    monkeypatch.setattr(agent, "folder_of", lambda files, t: work)
    monkeypatch.setattr(agent, "_transcripts", lambda files, t: tmp_path / "none")
    agent.remove_folder(None, task)
    assert not home.exists() and secret.read_text() == "not for the session"


def test_a_gate_opens_for_the_group_of_the_turns_user_and_closes_after_it(monkeypatch, tmp_path):
    from app.engine.tasks import agent

    gate = tmp_path / "gate"
    gate.mkdir()
    gate.chmod(0o700)
    changed = []
    monkeypatch.setattr(agent.pwd, "getpwnam", lambda name: SimpleNamespace(pw_gid=4242))
    monkeypatch.setattr(agent.os, "fchown", lambda fd, uid, gid: changed.append((uid, gid)))
    agent._open_gate(gate, "assistant-2")
    assert changed == [(-1, 4242)] and oct(gate.stat().st_mode & 0o777) == "0o710"
    agent._close_gate(gate)
    assert oct(gate.stat().st_mode & 0o777) == "0o700"
    # A link in the gate's place is no gate.
    link = tmp_path / "link"
    link.symlink_to(gate)
    try:
        agent._open_gate(link, "assistant-2")
    except OSError:
        pass
    else:
        raise AssertionError("a link was followed")


def test_a_gate_an_engine_that_died_left_open_is_closed_unless_a_turn_holds_its_user(
    monkeypatch, tmp_path
):
    from app.engine.tasks import agent

    root = tmp_path / "assistant"
    slots = tmp_path / "assistant-slots"
    held, free = root / "held", root / "free"
    for gate in (held, free):
        gate.mkdir(parents=True)
        gate.chmod(0o710)
    names = {held.stat().st_gid: "assistant-1"}
    monkeypatch.setattr(agent.grp, "getgrgid", lambda gid: SimpleNamespace(gr_name=names[gid]))
    # Another process is running a turn as assistant-1: its gate is open on purpose.
    slots.mkdir()
    lock = open(slots / "assistant-1", "a")  # noqa: SIM115
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    agent._close_idle_gates(root, slots)
    assert oct(held.stat().st_mode & 0o777) == "0o710"
    lock.close()
    agent._close_idle_gates(root, slots)
    assert (
        oct(held.stat().st_mode & 0o777) == "0o700" and oct(free.stat().st_mode & 0o777) == "0o700"
    )


def test_the_reset_runs_before_and_after_a_turn_and_a_failing_one_fails_the_turn(
    monkeypatch, tmp_path
):
    from app.engine.tasks import agent

    folder = tmp_path / "gate" / "work"
    folder.mkdir(parents=True)
    events = []

    class Lock:
        def close(self):
            events.append("lock closed")

    monkeypatch.setenv("AI_AGENT_SANDBOX", "container")
    monkeypatch.setenv("AI_AGENT_FOLDERS", str(tmp_path / "assistant"))
    monkeypatch.setattr(agent, "_take_session_user", lambda slots: ("assistant-3", Lock()))
    monkeypatch.setattr(agent, "_open_gate", lambda gate, user: events.append(f"open {user}"))
    monkeypatch.setattr(agent, "_close_gates_of", lambda root, user: events.append(f"stale {user}"))
    monkeypatch.setattr(agent, "_close_gate", lambda gate: events.append("close"))
    monkeypatch.setattr(
        agent,
        "_reset",
        lambda user, config=None, work=None: events.append(
            f"reset {user}" + (" with folders" if work is not None else "")
        ),
    )
    monkeypatch.setattr(agent, "_ensure_tmp", lambda work: events.append("tmp"))
    monkeypatch.setattr(agent, "_command", lambda *a, **k: (_ for _ in ()).throw(OSError("stop")))
    monkeypatch.setattr(agent, "_end", lambda *a: None)
    monkeypatch.setattr(agent, "_record_turn", lambda *a, **k: None)
    monkeypatch.setattr(agent, "note", lambda *a: None)
    monkeypatch.setattr(agent, "finish", lambda *a: None)
    monkeypatch.setattr(agent, "_retention", lambda ctx: 1)
    monkeypatch.setattr(agent, "load_task", lambda *a, **k: SimpleNamespace(design={}))
    session = SimpleNamespace(commit=lambda: None)
    job = SimpleNamespace(id="j")
    args = (session, job, SimpleNamespace(), "t1", folder, "p", "s", "tok", 1, [])
    assert agent._turn(*args, first=True, load=False) is None
    # Before: the reset first, the gate still closed, then the gate opens. After: the reset first, the
    # gate still open for the user's files, then the gate closes, then the user is let go.
    assert events == ["reset assistant-3", "stale assistant-3", "open assistant-3", "tmp",
                      "reset assistant-3 with folders", "close", "lock closed"]  # fmt: skip
    # A reset that does not finish ends the turn before the session starts, naming what failed.
    events.clear()
    notes = []
    monkeypatch.setattr(agent, "note", lambda task, kind, text: notes.append(text))

    def failing(user, config=None, work=None):
        events.append(f"reset {user}")
        raise agent.ResetFailed("The reset of session user assistant-3 did not finish")

    monkeypatch.setattr(agent, "_reset", failing)
    assert agent._turn(*args, first=True, load=False) is None
    # A reset that fails before a turn opens no gate and starts no session; the user is let go.
    assert events == ["reset assistant-3", "lock closed"]
    assert notes == ["The reset of session user assistant-3 did not finish"]


def test_the_reset_command_is_a_sudo_call_as_the_session_user_with_the_folders_on_standard_input(
    monkeypatch, tmp_path
):
    from app.engine.tasks import agent

    calls = []

    def run(command, **kwargs):
        calls.append((command, kwargs["input"]))
        return SimpleNamespace(stdout=f"{agent.RESET_DONE}\n", stderr="", returncode=0)

    monkeypatch.setattr(agent.subprocess, "run", run)
    agent._reset("assistant-2")
    agent._reset("assistant-2", tmp_path / "claude", tmp_path / "work")
    base = ["sudo", "-n", "-u", "assistant-2", "--", agent.RESET_COMMAND]
    # The folders' paths are no argument (every process of the container reads those).
    assert calls == [
        (base, ""),
        (base, f"{tmp_path / 'claude'}\n{tmp_path / 'work'}\n"),
    ]
    # Both the marker and the exit status are the proof.
    for stdout, code, stderr in (
        ("", 1, "sudo: a password is required"),
        (f"{agent.RESET_DONE}\n", 1, "processes remain"),
    ):
        monkeypatch.setattr(
            agent.subprocess,
            "run",
            lambda *a, _o=(stdout, code, stderr), **k: SimpleNamespace(
                stdout=_o[0], stderr=_o[2], returncode=_o[1]
            ),
        )
        try:
            agent._reset("assistant-2", tmp_path, tmp_path)
        except agent.ResetFailed as error:
            assert "did not finish" in str(error)
        else:
            raise AssertionError("a reset that did not finish passed")


def test_the_reset_script_ends_processes_first_and_again_last_and_refuses_bad_paths(tmp_path):
    """It ends every process of its user, so only its refusals are run here."""
    from pathlib import Path

    script = Path(__file__).parents[4] / "refiroo-session-reset"
    text = script.read_text()
    body = text[text.index("end_processes\n\n# Makes") :]
    # Order: processes end, then the clean-up, then the chmod, then processes end again, then the marker.
    steps = [
        "end_processes",
        "make_usable",
        "rm -rf",
        "chmod g+rwX",
        "end_processes",
        'echo "refiroo-session-reset-done"',
    ]
    at = -1
    for step in steps:
        at = body.index(step, at + 1)
    assert body.rstrip().endswith('echo "refiroo-session-reset-done"') and "/dev/shm" in body
    for given in ("relative\n/abs\n", "/abs\n/a/../b\n", "/only-one\n"):
        done = subprocess.run(
            ["sh", str(script)], input=given, capture_output=True, text=True, check=False
        )
        assert done.returncode == 2 and "refiroo-session-reset-done" not in done.stdout


def test_a_gate_left_open_for_a_user_is_closed_before_its_next_turn_opens_its_own(
    monkeypatch, tmp_path
):
    """Review: an engine killed between opening a gate and closing it left the gate open to the next
    turn of the same user, for another task."""
    from app.engine.tasks import agent

    root = tmp_path / "assistant"
    stale, other, own = root / "stale", root / "other", root / "own"
    for gate in (stale, other, own):
        gate.mkdir(parents=True)
        gate.chmod(0o700)
    stale.chmod(0o710)
    other.chmod(0o710)
    mine = stale.stat().st_gid
    # `other` is open for another user's group: it must stay as it is.
    real_fstat = agent.os.fstat
    inode = other.stat().st_ino

    def fstat(descriptor):
        found = real_fstat(descriptor)
        if found.st_ino == inode:
            return SimpleNamespace(st_gid=mine + 1, st_mode=found.st_mode)
        return found

    monkeypatch.setattr(agent.os, "fstat", fstat)
    monkeypatch.setattr(agent.pwd, "getpwnam", lambda name: SimpleNamespace(pw_gid=mine))
    monkeypatch.setattr(agent.os, "fchown", lambda *a: None)
    agent._close_gates_of(root, "assistant-2")
    assert oct(stale.stat().st_mode & 0o777) == "0o700"
    assert oct(other.stat().st_mode & 0o777) == "0o710"
    agent._open_gate(own, "assistant-2")
    opened = [g.name for g in root.iterdir() if g.stat().st_mode & 0o010]
    assert sorted(opened) == ["other", "own"]


def test_a_gate_that_cannot_be_closed_fails_the_turn_and_no_gate_opens(monkeypatch, tmp_path):
    from app.engine.tasks import agent

    root = tmp_path / "assistant"
    stale = root / "stale"
    stale.mkdir(parents=True)
    stale.chmod(0o710)
    monkeypatch.setattr(
        agent.pwd, "getpwnam", lambda name: SimpleNamespace(pw_gid=stale.stat().st_gid)
    )

    def refuse(descriptor, mode):
        raise PermissionError("operation not permitted")

    monkeypatch.setattr(agent.os, "fchmod", refuse)
    try:
        agent._close_gates_of(root, "assistant-2")
    except agent.ResetFailed as error:
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
    monkeypatch.setattr(agent, "_take_session_user", lambda slots: ("assistant-2", Lock()))
    monkeypatch.setattr(agent, "_reset", lambda *a, **k: events.append("reset"))
    monkeypatch.setattr(agent, "_open_gate", lambda *a: events.append("open"))
    monkeypatch.setattr(agent, "_close_gate", lambda *a: events.append("close"))

    def stuck(root, user):
        raise agent.ResetFailed("A task's folder still open could not be closed")

    notes = []
    monkeypatch.setattr(agent, "_close_gates_of", stuck)
    for name in ("_end", "_record_turn", "finish"):
        monkeypatch.setattr(agent, name, lambda *a, **k: None)
    monkeypatch.setattr(agent, "note", lambda task, kind, text: notes.append(text))
    monkeypatch.setattr(agent, "_retention", lambda ctx: 1)
    monkeypatch.setattr(agent, "load_task", lambda *a, **k: SimpleNamespace(design={}))
    args = (SimpleNamespace(commit=lambda: None), SimpleNamespace(id="j"), SimpleNamespace(),
            "t1", folder, "p", "s", "tok", 1, [])  # fmt: skip
    assert agent._turn(*args, first=True, load=False) is None
    assert events == ["reset", "lock closed"] and "could not be closed" in notes[0]


def test_an_idle_gate_is_read_again_once_its_users_lock_is_held(monkeypatch, tmp_path):
    """Review note: the gate's group was read before the lock; a turn of another process that opened the
    gate for another user in between must not find it closed."""
    from app.engine.tasks import agent

    root = tmp_path / "assistant"
    slots = tmp_path / "assistant-slots"
    gate = root / "gate"
    gate.mkdir(parents=True)
    gate.chmod(0o710)
    real_gid = gate.stat().st_gid
    monkeypatch.setattr(agent.grp, "getgrgid", lambda gid: SimpleNamespace(gr_name="assistant-1"))
    seen = []
    real_fstat = agent.os.fstat

    def changing(descriptor):
        found = real_fstat(descriptor)
        seen.append(found)
        if len(seen) == 2:  # the second look: another process has opened it for another group
            return SimpleNamespace(st_gid=real_gid + 1, st_mode=found.st_mode)
        return found

    monkeypatch.setattr(agent.os, "fstat", changing)
    agent._close_idle_gates(root, slots)
    assert oct(gate.stat().st_mode & 0o777) == "0o710"
    # With nothing changed between the two looks, the gate is closed.
    seen.clear()
    monkeypatch.setattr(agent.os, "fstat", real_fstat)
    agent._close_idle_gates(root, slots)
    assert oct(gate.stat().st_mode & 0o777) == "0o700"


def test_in_a_container_a_tasks_folder_has_a_random_name_kept_with_the_task(monkeypatch, tmp_path):
    from app.engine.tasks import agent

    monkeypatch.setenv("AI_AGENT_SANDBOX", "container")
    monkeypatch.setenv("AI_AGENT_FOLDERS", str(tmp_path / "assistant"))
    files = SimpleNamespace(directory=tmp_path / "files")
    task = SimpleNamespace(public_id="t1", design={"agentSession": "s-1"})
    session = SimpleNamespace(commit=lambda: None)
    monkeypatch.setattr(agent, "load_task", lambda *a, **k: task)
    monkeypatch.setattr(agent, "_open_root", lambda root: root.mkdir(parents=True, exist_ok=True))
    monkeypatch.setattr(agent, "_shared_dir", lambda path: path.mkdir(exist_ok=True))
    agent.ensure_folder(session, files, "t1")
    name = task.design[agent.FOLDER_KEY]
    assert len(name) >= 32 and "t1" not in name
    assert agent.folder_of(files, task) == tmp_path / "assistant" / name / "work"
    assert agent.home_of(files, task) == tmp_path / "assistant" / name
    agent.ensure_folder(session, files, "t1")
    assert task.design[agent.FOLDER_KEY] == name
    other = SimpleNamespace(public_id="t2", design={})
    monkeypatch.setattr(agent, "load_task", lambda *a, **k: other)
    agent.ensure_folder(session, files, "t2")
    assert other.design[agent.FOLDER_KEY] != name
    assert agent._transcripts(files, task) == tmp_path / "assistant" / name / "claude" / "projects"
    # A new task's folders are made once, the gate around work and claude.
    agent._make_folders(agent.folder_of(files, task))
    home = agent.home_of(files, task)
    assert sorted(p.name for p in home.iterdir()) == ["claude", "work"]
    assert oct(home.stat().st_mode & 0o777) == "0o700" and (home / "work" / "tmp").is_dir()


def test_the_name_is_committed_before_the_folder_moves_and_a_sweep_finishes_a_move_it_finds(
    monkeypatch, tmp_path
):
    """Review finding: the folder was renamed before its name was committed, and a sweep in that
    window removed it as the folder of no task."""
    from app.engine.tasks import agent

    root = tmp_path / "assistant"
    (root / "t1").mkdir(parents=True)
    (root / "t1" / "workbook.xlsx").write_text("w")
    monkeypatch.setenv("AI_AGENT_SANDBOX", "container")
    monkeypatch.setenv("AI_AGENT_FOLDERS", str(root))
    files = SimpleNamespace(directory=tmp_path / "files")
    task = SimpleNamespace(public_id="t1", design={"agentSession": "s-1"})
    seen = []
    session = SimpleNamespace(
        commit=lambda: seen.append((task.design.get(agent.FOLDER_KEY), (root / "t1").exists()))
    )
    monkeypatch.setattr(agent, "load_task", lambda *a, **k: task)
    monkeypatch.setattr(agent, "_open_root", lambda root: None)
    monkeypatch.setattr(agent, "_shared_dir", lambda path: path.mkdir(exist_ok=True))
    assert agent.resumable(files, task) is False
    agent.ensure_folder(session, files, "t1")
    name = task.design[agent.FOLDER_KEY]
    assert seen == [(name, True)]
    assert not (root / "t1").exists()
    assert (agent.folder_of(files, task) / "workbook.xlsx").read_text() == "w"
    assert (agent.home_of(files, task) / "claude").is_dir() and agent.resumable(
        files, task
    ) is False
    # A sweep between the commit and the move finishes the move; it removes the folder of no task only
    # once it has stood for a while; and it keeps what a task names.
    (root / "t2").mkdir()
    (root / "t2" / "workbook.xlsx").write_text("w2")
    (root / "gone").mkdir()
    (root / "young").mkdir()
    old = agent.time.time() - agent.FRESH_SECONDS - 10
    os.utime(root / "gone", (old, old))
    rows = [("t1", name), ("t2", "second-name")]
    swept = SimpleNamespace(execute=lambda statement: SimpleNamespace(all=lambda: rows))
    monkeypatch.setattr(agent, "_close_idle_gates", lambda root, slots: None)
    agent.sweep(swept, files)
    assert (root / "second-name" / "work" / "workbook.xlsx").read_text() == "w2"
    assert not (root / "t2").exists() and not (root / "gone").exists()
    assert (root / "young").exists() and agent.home_of(files, task).is_dir()
    # Removing the task's folder takes its transcripts with it.
    kept = agent.home_of(files, task)
    (kept / "claude" / "projects").mkdir()
    agent.remove_folder(files, task)
    assert not kept.exists()


def test_the_progress_of_a_turn_is_read_through_the_descriptor_it_opened(tmp_path):
    """Review finding: the log was reopened by path in a folder the session writes in; a link to
    /dev/zero there would have been read until memory ran out."""
    from app.engine.tasks.agent import _Progress

    log = tmp_path / "turn.log"
    log.write_text(json.dumps({"type": "result", "result": "first"}) + "\n")
    progress = _Progress(log)
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
    planted = _Progress(tmp_path / "planted.log")
    (tmp_path / "planted.log").symlink_to(elsewhere)
    assert planted.read() is False and planted.result == {}
    os.mkfifo(tmp_path / "fifo.log")
    assert _Progress(tmp_path / "fifo.log").read() is False


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
        id=1,
        state="reading",
        notes=[],
        design={"stage": "model"},
        draft_id=None,
        check="old",
        title=None,
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


def test_a_proposal_prompt_says_a_partial_move_is_prepared_on_acceptance_not_done_by_hand():
    """The session of a split of some records of a type is told what accepting prepares, so its
    summary never hands the person manual restructuring (0.13 DOC11 14)."""
    from app.engine.tasks import agent

    prompt = agent._propose_prompt("Split the routes", "ws", "http://engine", {}, workbook=False)
    assert "partial move" in prompt and "stage nothing now" in prompt
    assert "Never tell the person to prepare a release or to restructure records by hand" in prompt


def test_the_note_of_a_type_removed_in_a_partial_move_says_its_records_move_not_that_they_are_deleted():
    """A removed type whose records the change set restructures into other types is not a deletion
    (0.13 DOC11 14); a real deletion keeps its counts."""
    from app.engine.tasks.agent import _removal_account, _requested_removals

    base = {"objectTypes": [{"key": "route", "name": "Route"}]}
    final = {
        "objectTypes": [
            {"key": "local", "name": "Local route"},
            {"key": "other", "name": "Other route"},
        ]
    }
    landing = SimpleNamespace(
        losses={"route": {"records": 4}},
        value_losses={},
        relationship_losses={("served-by", "stop", "route"): 72},
    )
    words = "remove the emptied Route type"
    asked = {"kind": "objectType", "key": "route", "words": words}
    moved = _requested_removals({"removals": [{**asked, "movedTo": ["local", "other"]}]}, words)
    _, stated = _removal_account(landing, moved, base, final)
    assert stated[0]["text"] == (
        "As you asked, Route is removed: its 4 records move to Local route and Other route."
    )
    deleted = _requested_removals({"removals": [asked]}, words)
    _, stated = _removal_account(landing, deleted, base, final)
    assert stated[0]["text"] == (
        "As you asked, Route is deleted, deleting 4 records, 72 relationships."
    )


def test_the_note_the_person_reads_drops_sentences_that_talk_about_the_proposal_file_and_its_keys():
    """The session's closing words are shown on the task: sentences about its own file, draftId,
    the moves or removals lists and movedTo are not (0.13 DOC11 15, as F4)."""
    from app.engine.tasks.agent import _said

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
    text = _said(progress)
    assert text.startswith(
        "This is a partial move: Route splits into Local route and Other route. Nothing is staged now."
    )
    for internal in ("draftId", "movedTo", "moves list", "removals list", "proposal.json"):
        assert internal not in text


_SENT = {
    "sources": [
        {
            "sheet": "Terms",
            "applicationKey": "words",
            "objectTypeKey": "term",
            "columns": [{"column": "Code", "field": "name"}],
            "key": {"field": "name"},
        }
    ],
    "valueMaps": {},
}


class _Session:
    """A session that answers the dry run's job: what the check read the workbook by."""

    def __init__(self, parameters):
        self.job = SimpleNamespace(parameters=parameters)

    def scalar(self, _statement):
        return self.job


def test_a_check_through_a_profile_the_draft_does_not_hold_fails_the_task_with_its_reason():
    """The session may send its dry run a profile inline and store none on the draft (0.17 PL3b): the
    design would have no profile to load by, so the task says so rather than offering it."""
    from app.engine.tasks.agent import _unstored_profile, profile_not_stored

    check = {"dryRunJobId": "job"}
    sent = {"profile": {"definition": _SENT}}
    for stored in (None, {}, {"key": "terms", "name": "Terms", "sources": [], "valueMaps": {}}):
        draft = SimpleNamespace(profile_json=stored)
        reason = _unstored_profile(_Session(sent), draft, check)
        assert reason is not None and "stored none on the model draft" in reason

    # Stored as the draft holds it (an id, a key and a name of its own), it is the same profile.
    held = {
        "key": "terms",
        "name": "Terms",
        "sources": [{"id": "terms", **_SENT["sources"][0]}],
        "valueMaps": {},
    }
    assert _unstored_profile(_Session(sent), SimpleNamespace(profile_json=held), check) is None
    changed = {**held, "sources": [{**held["sources"][0], "headerRow": 2}]}
    other = _unstored_profile(_Session(sent), SimpleNamespace(profile_json=changed), check)
    assert other is not None and "not the one stored" in other

    # A dry run of items reads no workbook, and a check without a job has nothing to compare.
    items = {"mode": "items"}
    assert _unstored_profile(_Session(items), SimpleNamespace(profile_json=None), check) is None
    assert profile_not_stored(None, None) is None
