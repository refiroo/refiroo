"""One retry for both HTTP adapters (FX1, D3): a passing failure is sent again after a wait (the
provider's ``retry-after``, else a delay that doubles); a request that timed out is never resent."""

import httpx
import pytest
from pydantic import BaseModel

from app.engine.proposals import retry
from app.engine.proposals.claude import ClaudeProvider
from app.engine.proposals.openai_compatible import OpenAICompatibleProvider
from app.engine.proposals.provider import ProposalRequest, ProviderError


class Answer(BaseModel):
    ready: bool


REQUEST = ProposalRequest("connectionTest", "Say ready", "t/1", {}, Answer)
CLAUDE_OK = httpx.Response(
    200,
    json={"stop_reason": "end_turn", "content": [{"type": "text", "text": '{"ready": true}'}]},
)
OPENAI_OK = httpx.Response(200, json={"choices": [{"message": {"content": '{"ready": true}'}}]})


@pytest.fixture
def waits(monkeypatch):
    waited: list[float] = []
    monkeypatch.setattr(retry, "_sleep", waited.append)
    return waited


def _client(*replies, seen):
    queue = list(replies)

    def handle(request):
        seen.append(request)
        reply = queue.pop(0)
        if isinstance(reply, BaseException):
            raise reply
        return reply

    return httpx.Client(transport=httpx.MockTransport(handle))


def _providers(*replies, seen):
    """Each adapter on its own copy of the same replies, the Claude one first."""
    return [
        ClaudeProvider("k", http_client=_client(*replies, seen=seen)),
        OpenAICompatibleProvider("http://local/v1", "m", http_client=_client(*replies, seen=seen)),
    ]


@pytest.mark.parametrize("adapter", [0, 1])
def test_a_passing_failure_waits_a_growing_delay_before_each_resend(adapter, waits):
    seen = []
    ok = (CLAUDE_OK, OPENAI_OK)[adapter]
    provider = _providers(httpx.Response(503), httpx.Response(529), ok, seen=seen)[adapter]
    assert provider.propose(REQUEST).data == {"ready": True}
    assert len(seen) == 3 and waits == [1.0, 2.0]


@pytest.mark.parametrize("adapter", [0, 1])
def test_a_retry_after_is_waited_for(adapter, waits):
    seen = []
    ok = (CLAUDE_OK, OPENAI_OK)[adapter]
    limited = httpx.Response(429, headers={"retry-after": "7"})
    provider = _providers(limited, ok, seen=seen)[adapter]
    provider.propose(REQUEST)
    assert len(seen) == 2 and waits == [7.0]


@pytest.mark.parametrize("adapter", [0, 1])
def test_a_wait_beyond_the_bound_is_not_waited_for_and_the_call_fails_as_rate_limited(
    adapter, waits
):
    seen = []
    limited = httpx.Response(429, headers={"retry-after": "3600"})
    provider = _providers(limited, seen=seen)[adapter]
    with pytest.raises(ProviderError) as raised:
        provider.propose(REQUEST)
    assert raised.value.kind == "rateLimited" and len(seen) == 1 and waits == []


@pytest.mark.parametrize("adapter", [0, 1])
def test_a_timed_out_request_is_never_sent_again(adapter, waits):
    seen = []
    provider = _providers(httpx.ReadTimeout("slow"), seen=seen)[adapter]
    with pytest.raises(ProviderError) as raised:
        provider.propose(REQUEST)
    assert raised.value.kind == "unreachable" and "in time" in raised.value.message
    assert len(seen) == 1 and waits == []


@pytest.mark.parametrize("adapter", [0, 1])
def test_a_connection_that_never_opened_is_sent_again_and_then_named(adapter, waits):
    seen = []
    errors = [httpx.ConnectError("refused")] * 3
    provider = _providers(*errors, seen=seen)[adapter]
    with pytest.raises(ProviderError) as raised:
        provider.propose(REQUEST)
    assert raised.value.kind == "unreachable" and len(seen) == 3 and waits == [1.0, 2.0]
    assert raised.value.message.endswith("(AI_BASE_URL)") == (adapter == 1)


def test_the_wait_reads_seconds_a_date_or_nothing():
    assert retry.wait_seconds("2.5", 0) == 2.5
    assert retry.wait_seconds(None, 2) == 4.0
    assert retry.wait_seconds("soon", 1) == 2.0
    assert retry.wait_seconds("Wed, 21 Oct 2015 07:28:00 GMT", 0) == 0.0
