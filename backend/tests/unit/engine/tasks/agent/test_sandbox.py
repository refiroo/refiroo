"""The assistant session's sandbox: users, gates, environment and command (``engine/tasks/agent/sandbox.py``)."""

import fcntl
import grp
import json
import os
import pwd
import subprocess
from pathlib import Path
from types import SimpleNamespace


def test_the_session_sees_only_the_named_variables(monkeypatch, tmp_path):
    from app.engine.tasks.agent import sandbox as agent_sandbox

    # The machine's own environment must not leak into what is asserted.
    machine = {"PATH": "/usr/bin", "AI_AGENT_SANDBOX": "container"}
    monkeypatch.setattr(os, "environ", machine)
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
    seen = agent_sandbox.session_environment("t", tmp_path, tmp_path / "claude")
    assert set(seen) == {
        "ANTHROPIC_API_KEY", "CLAUDE_CODE_OAUTH_TOKEN", "ANTHROPIC_BASE_URL", "ANTHROPIC_MODEL",
        "NODE_EXTRA_CA_CERTS", "LC_ALL", "LANG", "REFIROO_TOKEN", "PATH", "TMPDIR",
        "CLAUDE_CONFIG_DIR",
    }  # fmt: skip
    assert seen["CLAUDE_CONFIG_DIR"] == str(tmp_path / "claude")
    # Bedrock's names only when Bedrock is on.
    machine["CLAUDE_CODE_USE_BEDROCK"] = "1"
    bedrock = agent_sandbox.session_environment("t")
    assert bedrock["AWS_SECRET_ACCESS_KEY"] == "aws-secret" and bedrock["AWS_REGION"] == "eu-west-1"
    assert "NODE_OPTIONS" not in bedrock
    # Outside a container the same list, with the developer's own HOME, USER and SHELL.
    machine["AI_AGENT_SANDBOX"] = ""
    del machine["CLAUDE_CODE_USE_BEDROCK"]
    assert agent_sandbox.session_environment("t")["HOME"] == "/home/engine"
    assert "SECRETS_ENCRYPTION_KEY" not in agent_sandbox.session_environment("t")


def test_the_sudoers_rule_keeps_exactly_the_names_the_engine_passes():
    """The engine's list and the image's sudoers line are one list: sudo would drop a name added to
    only one of them, or keep one the engine never passes."""
    import re

    from app.engine.tasks.agent import sandbox as agent_sandbox

    dockerfile = Path(__file__).parents[5] / "Dockerfile"
    kept = re.search(r'env_keep = "([^"]*)"', dockerfile.read_text())
    assert kept is not None
    expected = {
        *agent_sandbox.PASSED_NAMES,
        *agent_sandbox.BEDROCK_NAMES,
        *(p + "*" for p in agent_sandbox.PASSED_PREFIXES),
    }
    assert set(kept.group(1).split()) == expected
    text = dockerfile.read_text()
    assert "ASSISTANTS" in text and "(assistant)" not in text
    # Two commands as a pool user, and nothing else: the session's binary and the reset between turns.
    rule = re.search(r"rdm ALL=\(ASSISTANTS\) NOPASSWD: ([^']*)'", text)
    assert rule is not None
    assert [c.strip() for c in rule.group(1).split(",")] == [
        "/usr/local/bin/claude",
        agent_sandbox.RESET_COMMAND,
    ]


def test_a_turn_holds_a_session_user_until_it_ends_and_none_free_says_what_to_raise(
    monkeypatch, tmp_path
):
    from app.engine.tasks.agent import sandbox as agent_sandbox

    monkeypatch.setattr(agent_sandbox, "_pool_users", lambda: ["assistant-1", "assistant-2"])
    slots = tmp_path / "assistant-slots"
    first, first_lock = agent_sandbox.take_session_user(slots)
    second, second_lock = agent_sandbox.take_session_user(slots)
    assert (first, second) == ("assistant-1", "assistant-2")
    assert oct(slots.stat().st_mode & 0o777) == "0o700"
    try:
        agent_sandbox.take_session_user(slots)
    except agent_sandbox.NoSessionUser as error:
        assert "ASSISTANT_USERS" in str(error) and "all 2" in str(error)
    else:
        raise AssertionError("a third turn found a user")
    # The end of a turn frees its user.
    first_lock.close()
    again, again_lock = agent_sandbox.take_session_user(slots)
    assert again == "assistant-1"
    again_lock.close()
    second_lock.close()
    monkeypatch.setattr(agent_sandbox, "_pool_users", list)
    try:
        agent_sandbox.take_session_user(slots)
    except agent_sandbox.NoSessionUser as error:
        assert "ASSISTANT_USERS" in str(error)
    else:
        raise AssertionError("no pool, yet a user")


def test_a_gate_opens_for_the_group_of_the_turns_user_and_closes_after_it(monkeypatch, tmp_path):
    from app.engine.tasks.agent import sandbox as agent_sandbox

    gate = tmp_path / "gate"
    gate.mkdir()
    gate.chmod(0o700)
    changed = []
    monkeypatch.setattr(pwd, "getpwnam", lambda name: SimpleNamespace(pw_gid=4242))
    monkeypatch.setattr(os, "fchown", lambda fd, uid, gid: changed.append((uid, gid)))
    agent_sandbox.open_gate(gate, "assistant-2")
    assert changed == [(-1, 4242)] and oct(gate.stat().st_mode & 0o777) == "0o710"
    agent_sandbox.close_gate(gate)
    assert oct(gate.stat().st_mode & 0o777) == "0o700"
    # A link in the gate's place is no gate.
    link = tmp_path / "link"
    link.symlink_to(gate)
    try:
        agent_sandbox.open_gate(link, "assistant-2")
    except OSError:
        pass
    else:
        raise AssertionError("a link was followed")


def test_a_gate_an_engine_that_died_left_open_is_closed_unless_a_turn_holds_its_user(
    monkeypatch, tmp_path
):
    from app.engine.tasks.agent import sandbox as agent_sandbox

    root = tmp_path / "assistant"
    slots = tmp_path / "assistant-slots"
    held, free = root / "held", root / "free"
    for gate in (held, free):
        gate.mkdir(parents=True)
        gate.chmod(0o710)
    names = {held.stat().st_gid: "assistant-1"}
    monkeypatch.setattr(grp, "getgrgid", lambda gid: SimpleNamespace(gr_name=names[gid]))
    # Another process is running a turn as assistant-1: its gate is open on purpose.
    slots.mkdir()
    lock = open(slots / "assistant-1", "a")  # noqa: SIM115
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    agent_sandbox.close_idle_gates(root, slots)
    assert oct(held.stat().st_mode & 0o777) == "0o710"
    lock.close()
    agent_sandbox.close_idle_gates(root, slots)
    assert (
        oct(held.stat().st_mode & 0o777) == "0o700" and oct(free.stat().st_mode & 0o777) == "0o700"
    )


def test_the_reset_command_is_a_sudo_call_as_the_session_user_with_the_folders_on_standard_input(
    monkeypatch, tmp_path
):
    from app.engine.tasks.agent import sandbox as agent_sandbox

    calls = []

    def run(command, **kwargs):
        calls.append((command, kwargs["input"]))
        return SimpleNamespace(stdout=f"{agent_sandbox.RESET_DONE}\n", stderr="", returncode=0)

    monkeypatch.setattr(subprocess, "run", run)
    agent_sandbox.reset("assistant-2")
    agent_sandbox.reset("assistant-2", tmp_path / "claude", tmp_path / "work")
    base = ["sudo", "-n", "-u", "assistant-2", "--", agent_sandbox.RESET_COMMAND]
    # The folders' paths are no argument (every process of the container reads those).
    assert calls == [
        (base, ""),
        (base, f"{tmp_path / 'claude'}\n{tmp_path / 'work'}\n"),
    ]
    # Both the marker and the exit status are the proof.
    for stdout, code, stderr in (
        ("", 1, "sudo: a password is required"),
        (f"{agent_sandbox.RESET_DONE}\n", 1, "processes remain"),
    ):
        monkeypatch.setattr(
            subprocess,
            "run",
            lambda *a, _o=(stdout, code, stderr), **k: SimpleNamespace(
                stdout=_o[0], stderr=_o[2], returncode=_o[1]
            ),
        )
        try:
            agent_sandbox.reset("assistant-2", tmp_path, tmp_path)
        except agent_sandbox.ResetFailed as error:
            assert "did not finish" in str(error)
        else:
            raise AssertionError("a reset that did not finish passed")


def test_the_reset_script_ends_processes_first_and_again_last_and_refuses_bad_paths(tmp_path):
    """It ends every process of its user, so only its refusals are run here."""

    script = Path(__file__).parents[5] / "refiroo-session-reset"
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
    from app.engine.tasks.agent import sandbox as agent_sandbox

    root = tmp_path / "assistant"
    stale, other, own = root / "stale", root / "other", root / "own"
    for gate in (stale, other, own):
        gate.mkdir(parents=True)
        gate.chmod(0o700)
    stale.chmod(0o710)
    other.chmod(0o710)
    mine = stale.stat().st_gid
    # `other` is open for another user's group: it must stay as it is.
    real_fstat = os.fstat
    inode = other.stat().st_ino

    def fstat(descriptor):
        found = real_fstat(descriptor)
        if found.st_ino == inode:
            return SimpleNamespace(st_gid=mine + 1, st_mode=found.st_mode)
        return found

    monkeypatch.setattr(os, "fstat", fstat)
    monkeypatch.setattr(pwd, "getpwnam", lambda name: SimpleNamespace(pw_gid=mine))
    monkeypatch.setattr(os, "fchown", lambda *a: None)
    agent_sandbox.close_gates_of(root, "assistant-2")
    assert oct(stale.stat().st_mode & 0o777) == "0o700"
    assert oct(other.stat().st_mode & 0o777) == "0o710"
    agent_sandbox.open_gate(own, "assistant-2")
    opened = [g.name for g in root.iterdir() if g.stat().st_mode & 0o010]
    assert sorted(opened) == ["other", "own"]


def test_an_idle_gate_is_read_again_once_its_users_lock_is_held(monkeypatch, tmp_path):
    """Review note: the gate's group was read before the lock; a turn of another process that opened the
    gate for another user in between must not find it closed."""
    from app.engine.tasks.agent import sandbox as agent_sandbox

    root = tmp_path / "assistant"
    slots = tmp_path / "assistant-slots"
    gate = root / "gate"
    gate.mkdir(parents=True)
    gate.chmod(0o710)
    real_gid = gate.stat().st_gid
    monkeypatch.setattr(grp, "getgrgid", lambda gid: SimpleNamespace(gr_name="assistant-1"))
    seen = []
    real_fstat = os.fstat

    def changing(descriptor):
        found = real_fstat(descriptor)
        seen.append(found)
        if len(seen) == 2:  # the second look: another process has opened it for another group
            return SimpleNamespace(st_gid=real_gid + 1, st_mode=found.st_mode)
        return found

    monkeypatch.setattr(os, "fstat", changing)
    agent_sandbox.close_idle_gates(root, slots)
    assert oct(gate.stat().st_mode & 0o777) == "0o710"
    # With nothing changed between the two looks, the gate is closed.
    seen.clear()
    monkeypatch.setattr(os, "fstat", real_fstat)
    agent_sandbox.close_idle_gates(root, slots)
    assert oct(gate.stat().st_mode & 0o777) == "0o700"


def test_the_session_is_verified_by_tls_unless_the_api_is_on_this_machine():
    from app.engine.tasks.agent.sandbox import loopback
    from app.engine.tasks.agent.words import _connection

    assert loopback("https://localhost:8000") and loopback("http://127.0.0.1:8000")
    assert not loopback("https://192.168.0.36:8000") and not loopback("https://rdm.example.org")
    assert "curl -k" in _connection("w", "https://localhost:8000")
    assert "curl -k" not in _connection("w", "https://rdm.example.org")


def test_the_session_runs_restricted_outside_a_container_and_unprompted_inside_one(
    monkeypatch, tmp_path
):
    """Container: no --restricted, permission prompts off, no setting sources; host: unchanged."""
    from app.engine.tasks.agent.sandbox import safeguards

    monkeypatch.setenv("AI_AGENT_SANDBOX", "container")
    inside = safeguards("http://127.0.0.1:8000", tmp_path)
    assert "--restricted" not in inside and "dontAsk" not in inside
    assert inside[inside.index("--permission-mode") + 1] == "bypassPermissions"
    assert inside[inside.index("--setting-sources") + 1] == ""
    assert "--strict-mcp-config" in inside and "--disallowedTools" in inside
    # The read block refuses `$REFIROO_TOKEN` in compound commands; the assistant user is the boundary.
    assert "permissions" not in json.loads(inside[inside.index("--settings") + 1])

    monkeypatch.delenv("AI_AGENT_SANDBOX", raising=False)
    outside = safeguards("http://127.0.0.1:8000", tmp_path)
    assert "--restricted" in outside and "bypassPermissions" not in outside
    assert outside[outside.index("--permission-mode") + 1] == "dontAsk"
    assert "--setting-sources" not in outside
    host = json.loads(outside[outside.index("--settings") + 1])
    assert host["permissions"] == {"blockReadsOutsideWorkingDirectories": True}
