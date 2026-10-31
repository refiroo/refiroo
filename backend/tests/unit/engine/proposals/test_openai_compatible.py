"""The OpenAI-compatible adapter (``engine/proposals/openai_compatible.py``, AP-D2): the schema asked
for, every refusal named, a reply out of place malformed."""

import json

import httpx
import pytest
from pydantic import BaseModel

from app.engine.proposals.openai_compatible import OpenAICompatibleProvider
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


def _openai(
    *responses: httpx.Response, seen: list[httpx.Request], key: str = ""
) -> OpenAICompatibleProvider:
    return OpenAICompatibleProvider(
        "http://local:8080/v1/", "llama", key, http_client=_client(*responses, seen=seen)
    )


def test_openai_compatible_asks_for_the_schema_and_reads_the_choice():
    seen: list[httpx.Request] = []
    reply = {
        "model": "llama-3",
        "choices": [{"message": {"content": '{"items": []}'}, "finish_reason": "stop"}],
        "usage": {"prompt_tokens": 9, "completion_tokens": 2},
    }
    answer = _openai(httpx.Response(200, json=reply), seen=seen, key="s").propose(REQUEST)
    sent = json.loads(seen[0].content)
    assert seen[0].url == "http://local:8080/v1/chat/completions"
    assert seen[0].headers["authorization"] == "Bearer s"
    assert sent["response_format"]["json_schema"]["schema"] == answer_schema(Answer)
    assert (answer.data, answer.model, answer.tokens_in) == ({"items": []}, "llama-3", 9)


def test_openai_compatible_without_a_key_sends_no_authorization():
    seen: list[httpx.Request] = []
    reply = {"choices": [{"message": {"content": "{}"}}]}
    _openai(httpx.Response(200, json=reply), seen=seen).propose(REQUEST)
    assert "authorization" not in seen[0].headers


@pytest.mark.parametrize(
    ("response", "kind"),
    [
        (httpx.Response(401), "unauthorized"),
        (httpx.Response(429), "rateLimited"),
        (httpx.Response(500), "failed"),
        (httpx.Response(200, json={"choices": []}), "malformed"),
        (
            httpx.Response(
                200, json={"choices": [{"message": {"content": "{"}, "finish_reason": "length"}]}
            ),
            "malformed",
        ),
        (httpx.Response(200, json={"choices": [{"message": {"content": "prose"}}]}), "malformed"),
    ],
)
def test_openai_compatible_names_each_refusal(response, kind):
    with pytest.raises(ProviderError) as raised:
        _openai(response, seen=[]).propose(REQUEST)
    assert raised.value.kind == kind


def test_a_reasoning_effort_is_sent_only_when_set():
    reply = {"choices": [{"message": {"content": "{}"}}]}
    seen: list[httpx.Request] = []
    OpenAICompatibleProvider(
        "http://local/v1",
        "qwen",
        reasoning_effort="none",
        http_client=_client(httpx.Response(200, json=reply), seen=seen),
    ).propose(REQUEST)
    assert json.loads(seen[0].content)["reasoning_effort"] == "none"
    _openai(httpx.Response(200, json=reply), seen=seen).propose(REQUEST)
    assert "reasoning_effort" not in json.loads(seen[1].content)


def test_the_instructions_show_the_answer_as_an_example_to_fill_in():
    """An endpoint that does not enforce response_format still gets told the shape (a small local
    model copied a raw schema back, and filled in an example: found 2026-10-28)."""
    seen: list[httpx.Request] = []
    reply = {"choices": [{"message": {"content": '{"items": []}'}}]}
    _openai(httpx.Response(200, json=reply), seen=seen).propose(REQUEST)
    system = json.loads(seen[0].content)["messages"][0]["content"]
    assert (
        system.startswith("Name them")
        and '{"items": [{"name": "<name>", "confidence": 0}]}' in system
    )
