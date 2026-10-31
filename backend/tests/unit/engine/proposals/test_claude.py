"""The Claude adapter (``engine/proposals/claude.py``, AP-D2) as the wire sees it: structured output
with fallbacks, every refusal named, a passing failure tried again."""

import json

import httpx
import pytest
from pydantic import BaseModel

from app.engine.proposals.claude import DEFAULT_MODEL, FALLBACK_BETA, ClaudeProvider
from app.engine.proposals.provider import ProposalRequest, ProviderError, answer_schema


class Inner(BaseModel):
    name: str
    confidence: float = 0.5


class Answer(BaseModel):
    items: list[Inner]


REQUEST = ProposalRequest("mappingTarget", "Name them", "m/1", {"types": ["a"]}, Answer)


def _client(*responses: httpx.Response, seen: list[httpx.Request]) -> httpx.Client:
    queue = list(responses)

    def handle(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return queue.pop(0)

    return httpx.Client(transport=httpx.MockTransport(handle))


def _claude(*responses: httpx.Response, seen: list[httpx.Request]) -> ClaudeProvider:
    return ClaudeProvider("key-1", http_client=_client(*responses, seen=seen))


def _message(text: str, stop: str = "end_turn", **extra) -> httpx.Response:
    return httpx.Response(
        200,
        json={
            "model": "claude-opus-5-5",
            "stop_reason": stop,
            "content": [{"type": "text", "text": text}],
            "usage": {"input_tokens": 11, "output_tokens": 5},
            **extra,
        },
    )


def test_claude_asks_for_structured_output_with_fallbacks_and_reads_the_answer():
    seen: list[httpx.Request] = []
    answer = _claude(_message('{"items": [{"name": "A", "confidence": 1}]}'), seen=seen).propose(
        REQUEST
    )
    sent = json.loads(seen[0].content)
    assert seen[0].url == "https://api.anthropic.com/v1/messages"
    assert (
        seen[0].headers["x-api-key"] == "key-1"
        and seen[0].headers["anthropic-beta"] == FALLBACK_BETA
    )
    assert sent["model"] == DEFAULT_MODEL and sent["system"] == "Name them"
    assert sent["output_config"]["format"] == {
        "type": "json_schema",
        "schema": answer_schema(Answer),
    }
    assert sent["fallbacks"] == "default" and json.loads(sent["messages"][0]["content"]) == {
        "types": ["a"]
    }
    assert (answer.data, answer.tokens_in, answer.tokens_out) == (
        {"items": [{"name": "A", "confidence": 1}]},
        11,
        5,
    )


@pytest.mark.parametrize(
    ("response", "kind"),
    [
        (httpx.Response(401, json={}), "unauthorized"),
        (httpx.Response(403, json={}), "unauthorized"),
        (httpx.Response(400, json={"error": {"type": "invalid_request_error"}}), "failed"),
        (_message("", stop="refusal", stop_details={"category": "cyber"}), "declined"),
        (_message('{"items": [', stop="max_tokens"), "malformed"),
        (_message("not json"), "malformed"),
    ],
)
def test_claude_names_each_refusal(response, kind):
    with pytest.raises(ProviderError) as raised:
        _claude(response, seen=[]).propose(REQUEST)
    assert raised.value.kind == kind


def test_claude_tries_a_passing_failure_again_and_then_gives_up():
    seen: list[httpx.Request] = []
    answer = _claude(httpx.Response(529, json={}), _message('{"items": []}'), seen=seen).propose(
        REQUEST
    )
    assert answer.data == {"items": []} and len(seen) == 2
    with pytest.raises(ProviderError) as raised:
        _claude(*[httpx.Response(429, json={})] * 3, seen=[]).propose(REQUEST)
    assert raised.value.kind == "rateLimited"


def test_claude_unreachable_is_named():
    def fail(request):
        raise httpx.ConnectError("refused")

    provider = ClaudeProvider("k", http_client=httpx.Client(transport=httpx.MockTransport(fail)))
    with pytest.raises(ProviderError) as raised:
        provider.propose(REQUEST)
    assert raised.value.kind == "unreachable"
