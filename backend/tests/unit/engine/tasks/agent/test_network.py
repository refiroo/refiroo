"""The assistant session's network in a container (SR-D6): the proxy's allow-list and the state the
start step leaves (``refiroo_session_proxy.py``, ``engine/tasks/agent/network.py``)."""

import asyncio
import importlib.util
from pathlib import Path

import pytest

PROXY = Path(__file__).resolve().parents[5] / "refiroo_session_proxy.py"


@pytest.fixture(scope="module")
def proxy():
    spec = importlib.util.spec_from_file_location("refiroo_session_proxy", PROXY)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_the_list_is_the_providers_hosts_from_the_sessions_own_settings(proxy):
    anthropic = proxy.allowed_hosts({})
    # The API's host and the hosts a subscription's sign-in and renewal use.
    assert anthropic == ["api.anthropic.com", "claude.ai", "platform.claude.com"]
    # A gateway replaces the API's host; the sign-in hosts stay only with a subscription token.
    gateway = {"ANTHROPIC_BASE_URL": "https://llm.example.com/v1", "ANTHROPIC_API_KEY": "k"}
    assert proxy.allowed_hosts(gateway) == ["llm.example.com"]
    assert proxy.allowed_hosts({**gateway, "CLAUDE_CODE_OAUTH_TOKEN": "x"}) == [
        "claude.ai",
        "llm.example.com",
        "platform.claude.com",
    ]
    bedrock = proxy.allowed_hosts({"CLAUDE_CODE_USE_BEDROCK": "1", "AWS_REGION": "eu-west-1"})
    assert bedrock == [
        "bedrock-runtime.eu-west-1.amazonaws.com",
        "bedrock.eu-west-1.amazonaws.com",
        "sts.amazonaws.com",
        "sts.eu-west-1.amazonaws.com",
    ]
    # This machine's API is reached directly; another host is added; the one setting adds more.
    assert proxy.allowed_hosts({"AI_AGENT_API_URL": "http://127.0.0.1:8000"}) == anthropic
    more = proxy.allowed_hosts(
        {
            "AI_AGENT_API_URL": "https://engine.example.org",
            "AI_AGENT_ALLOWED_HOSTS": " A.example.net, *.corp.example ",
        }
    )
    assert {"engine.example.org", "a.example.net", "*.corp.example"} <= set(more)


def test_an_allowed_name_passes_and_everything_else_is_refused(proxy):
    allowed = ["api.anthropic.com", "*.corp.example"]
    assert proxy.permits(allowed, "api.anthropic.com")
    assert proxy.permits(allowed, "API.Anthropic.com.")
    assert proxy.permits(allowed, "a.b.corp.example")
    assert not proxy.permits(allowed, "corp.example")
    assert not proxy.permits(allowed, "example.com")
    assert not proxy.permits(allowed, "api.anthropic.com.evil.test")
    assert not proxy.permits(allowed, "evilapi.anthropic.com")
    # An address is never a name: not an IPv4 or IPv6 literal, not a number form, not an allowed name's
    # address, and not a name with anything but letters, digits and hyphens.
    for literal in (
        "160.79.104.10",
        "127.0.0.1",
        "::1",
        "[::1]",
        "0x7f000001",
        "2130706433",
        "a b.example",
    ):
        assert not proxy.permits(["160.79.104.10", "127.0.0.1", "::1"], literal)
    assert proxy.parse_connect(b"CONNECT api.anthropic.com:443 HTTP/1.1\r\nHost: x\r\n\r\n") == (
        "api.anthropic.com",
        443,
    )
    for bad in (
        b"GET http://api.anthropic.com/ HTTP/1.1\r\n\r\n",
        b"CONNECT api.anthropic.com HTTP/1.1\r\n\r\n",
    ):
        assert proxy.parse_connect(bad) is None


def test_the_proxy_answers_a_connect_to_a_refused_target_and_a_plain_request_with_a_refusal(proxy):
    async def ask(request: bytes) -> bytes:
        server = await asyncio.start_server(proxy.handler(["api.anthropic.com"]), "127.0.0.1", 0)
        port = server.sockets[0].getsockname()[1]
        try:
            reader, writer = await asyncio.open_connection("127.0.0.1", port)
            writer.write(request)
            answer = await asyncio.wait_for(reader.read(200), 5)
            writer.close()
            return answer
        finally:
            server.close()
            await server.wait_closed()

    def code(request: bytes) -> str:
        return asyncio.run(ask(request)).split(b"\r\n", 1)[0].decode()

    assert code(b"CONNECT example.com:443 HTTP/1.1\r\n\r\n") == "HTTP/1.1 403 Forbidden"
    assert code(b"CONNECT 93.184.216.34:443 HTTP/1.1\r\n\r\n") == "HTTP/1.1 403 Forbidden"
    assert code(b"CONNECT api.anthropic.com:22 HTTP/1.1\r\n\r\n") == "HTTP/1.1 403 Forbidden"
    assert (
        code(b"GET http://api.anthropic.com/ HTTP/1.1\r\n\r\n") == "HTTP/1.1 405 Method Not Allowed"
    )


def test_the_state_the_start_step_leaves_decides_what_a_turn_does(monkeypatch, tmp_path):
    from app.engine.tasks.agent import network, sandbox

    state = tmp_path / "session-network"
    monkeypatch.setenv("AI_AGENT_NETWORK_STATE", str(state))
    monkeypatch.setenv("AI_AGENT_SANDBOX", "container")
    # No file: the container was not started as root with NET_ADMIN: unrestricted, and a turn starts.
    assert network.read_state().state == network.UNRESTRICTED
    sandbox.check_network()
    assert sandbox.network_variables() == {}
    state.write_text("unrestricted the container has no NET_ADMIN capability (x)\n")
    assert network.read_state() == network.SessionNetwork(
        "unrestricted", "the container has no NET_ADMIN capability (x)"
    )
    # Restricted: the session gets the proxy and no variable of the engine's own; the proxy must run.
    state.write_text("restricted\n")
    monkeypatch.setenv("HTTPS_PROXY", "http://corporate:3128")
    monkeypatch.setattr(sandbox, "proxy_reachable", lambda: True)
    sandbox.check_network()
    environment = sandbox.session_environment("tok")
    assert environment["HTTPS_PROXY"] == "http://127.0.0.1:3128"
    assert "127.0.0.1" in environment["NO_PROXY"]
    monkeypatch.setattr(sandbox, "proxy_reachable", lambda: False)
    with pytest.raises(sandbox.NetworkNotReady, match="proxy is not running"):
        sandbox.check_network()
    # Failed: no turn starts, and the message names the cause; the engine's proxy variable is not passed.
    state.write_text("failed iptables refused the rule\n")
    with pytest.raises(sandbox.NetworkNotReady, match="iptables refused the rule"):
        sandbox.check_network()
    assert "HTTPS_PROXY" not in sandbox.session_environment("tok")
    # Outside a container none of it applies.
    monkeypatch.delenv("AI_AGENT_SANDBOX")
    sandbox.check_network()


def test_the_status_names_the_network_only_for_a_container_with_the_assistant(
    monkeypatch, tmp_path
):
    from app.engine.tasks.agent import network

    monkeypatch.setenv("AI_AGENT_NETWORK_STATE", str(tmp_path / "none"))
    assert network.report(False, True) is None
    assert network.report(True, False) is None
    assert network.report(True, True).state == network.UNRESTRICTED
