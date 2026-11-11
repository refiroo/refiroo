"""The Claude Code provider (``engine/proposals/claude_code.py``): one headless ``claude -p`` call
per request with nothing a project could add, the answer and its cost read from the CLI's JSON,
every failure named."""

import json
import subprocess
from types import SimpleNamespace

import pytest
from pydantic import BaseModel

from app.engine.proposals import claude_code
from app.engine.proposals.claude_code import ClaudeCodeProvider
from app.engine.proposals.provider import ProposalRequest, ProviderError


class Answer(BaseModel):
    ready: bool


REQUEST = ProposalRequest("connectionTest", "Say ready", "t/1", {"test": True}, Answer)
USAGE = {"input_tokens": 3, "cache_creation_input_tokens": 10, "cache_read_input_tokens": 100}


def _run(monkeypatch, stdout="", returncode=0, stderr="", raises=None):
    seen = {}

    def run(command, **kwargs):
        seen["command"], seen["kwargs"] = command, kwargs
        if raises:
            raise raises
        return SimpleNamespace(stdout=stdout, returncode=returncode, stderr=stderr)

    monkeypatch.setattr(claude_code.subprocess, "run", run)
    return seen


def _reply(**extra):
    return json.dumps(
        {"structured_output": {"ready": True}, "usage": {**USAGE, "output_tokens": 5}, **extra}
    )


def test_one_call_with_no_tools_settings_or_session_returns_the_answer_tokens_and_cost(monkeypatch):
    seen = _run(monkeypatch, _reply(total_cost_usd=0.0123, duration_ms=900))
    answer = ClaudeCodeProvider("sonnet", 77).propose(REQUEST)
    assert (answer.data, answer.model, answer.tokens_in, answer.tokens_out, answer.cost_usd) == (
        {"ready": True},
        "sonnet",
        113,
        5,
        0.0123,
    )
    command = seen["command"]
    assert command[1] == "-p" and json.dumps({"test": True}) not in command
    assert seen["kwargs"]["input"] == json.dumps({"test": True})
    assert command[command.index("--system-prompt") + 1] == "Say ready"
    assert command[command.index("--tools") + 1] == ""
    assert command[command.index("--setting-sources") + 1] == ""
    assert command[command.index("--model") + 1] == "sonnet"
    assert {"--strict-mcp-config", "--no-session-persistence", "--json-schema"} <= set(command)
    assert seen["kwargs"]["timeout"] == 77 and seen["kwargs"]["cwd"].startswith("/")


def test_no_model_leaves_claude_codes_default_and_no_cost_is_none(monkeypatch):
    seen = _run(monkeypatch, _reply())
    answer = ClaudeCodeProvider("", 60).propose(REQUEST)
    assert "--model" not in seen["command"]
    assert (answer.model, answer.cost_usd) == ("claude-code", None)


def test_an_answer_in_result_text_is_read_when_there_is_no_structured_output(monkeypatch):
    _run(monkeypatch, json.dumps({"result": '{"ready": false}', "usage": {}}))
    assert ClaudeCodeProvider("", 60).propose(REQUEST).data == {"ready": False}


@pytest.mark.parametrize(
    ("kwargs", "kind", "text"),
    [
        ({"raises": subprocess.TimeoutExpired("claude", 1)}, "unreachable", "in time"),
        ({"raises": FileNotFoundError()}, "unreachable", "could not be run"),
        ({"stdout": "not json", "returncode": 1}, "failed", "no JSON"),
        ({"stdout": _reply(), "returncode": 1}, "failed", "Claude Code failed"),
        ({"stdout": json.dumps({"is_error": True, "result": "limit"})}, "failed", "limit"),
        ({"stdout": json.dumps({"result": "words", "usage": {}})}, "malformed", "not JSON"),
    ],
)
def test_every_failure_is_named(monkeypatch, kwargs, kind, text):
    _run(monkeypatch, **kwargs)
    with pytest.raises(ProviderError, match=text) as raised:
        ClaudeCodeProvider("", 60).propose(REQUEST)
    assert raised.value.kind == kind


def test_a_large_context_goes_on_stdin_and_argv_stays_small(monkeypatch):
    seen = _run(monkeypatch, _reply())
    big = ProposalRequest("p", "Say ready", "t/1", {"rows": ["x" * 100] * 5000}, Answer)
    ClaudeCodeProvider("", 60).propose(big)
    assert len(seen["kwargs"]["input"]) > 500_000
    assert sum(len(part) for part in seen["command"]) < 10_000


def test_the_child_gets_only_what_claude_code_needs(monkeypatch):
    for name, value in {
        "DATABASE_URL": "postgresql://secret",
        "SECRETS_ENCRYPTION_KEY": "k",
        "ANTHROPIC_API_KEY": "a",
        "CLAUDE_CODE_OAUTH_TOKEN": "c",
        "LC_ALL": "C",
        "PATH": "/usr/bin",
    }.items():
        monkeypatch.setenv(name, value)
    seen = _run(monkeypatch, _reply())
    ClaudeCodeProvider("", 60).propose(REQUEST)
    env = seen["kwargs"]["env"]
    assert "DATABASE_URL" not in env and "SECRETS_ENCRYPTION_KEY" not in env
    assert env["ANTHROPIC_API_KEY"] == "a" and env["CLAUDE_CODE_OAUTH_TOKEN"] == "c"
    assert env["LC_ALL"] == "C" and env["PATH"] == "/usr/bin"


def test_a_failed_reply_carries_the_tokens_and_cost_it_was_charged(monkeypatch):
    _run(
        monkeypatch,
        json.dumps(
            {
                "is_error": True,
                "result": "limit",
                "usage": {**USAGE, "output_tokens": 5},
                "total_cost_usd": 0.5,
            }
        ),
    )
    with pytest.raises(ProviderError) as raised:
        ClaudeCodeProvider("", 60).propose(REQUEST)
    assert (raised.value.tokens_in, raised.value.tokens_out, raised.value.cost_usd) == (113, 5, 0.5)
