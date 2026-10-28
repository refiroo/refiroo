"""The Claude API adapter (AP-D2): the Messages API over HTTP.

The answer is constrained to the request's JSON schema by structured output
(``output_config.format``), and a request a model declines falls back on the server to another model
(``fallbacks: "default"``), so a proposal is not lost to a classifier's false positive. The key is
the operator's ``AI_API_KEY`` only.

Plain HTTP through ``httpx`` rather than the Anthropic SDK: the SDK brings ``httpx2``, which
Starlette's test client then prefers over ``httpx``, and one HTTP client serves both adapters.
"""

import json
from typing import Any

import httpx

from .provider import ProposalRequest, ProviderAnswer, ProviderError, answer_schema

DEFAULT_MODEL = "claude-opus-5-5"
DEFAULT_BASE_URL = "https://api.anthropic.com"
API_VERSION = "2023-06-01"
FALLBACK_BETA = "server-side-fallback-2026-07-01"
# Tried again by the client: overloaded, rate-limited or a passing server failure.
_RETRIED = {408, 409, 429, 500, 502, 503, 504, 529}
_ATTEMPTS = 3


class ClaudeProvider:
    name = "claude"

    def __init__(
        self,
        api_key: str,
        model: str = "",
        *,
        base_url: str = "",
        timeout: float = 60,
        http_client: httpx.Client | None = None,
    ) -> None:
        self.model = model or DEFAULT_MODEL
        self._url = f"{(base_url or DEFAULT_BASE_URL).rstrip('/')}/v1/messages"
        self._headers = {
            "x-api-key": api_key,
            "anthropic-version": API_VERSION,
            "anthropic-beta": FALLBACK_BETA,
            "content-type": "application/json",
        }
        self._client = http_client or httpx.Client(timeout=timeout)

    def propose(self, request: ProposalRequest) -> ProviderAnswer:
        body = {
            "model": self.model,
            "max_tokens": 16000,
            "system": request.instructions,
            "messages": [
                {"role": "user", "content": json.dumps(request.context, ensure_ascii=False)}
            ],
            "output_config": {
                "format": {"type": "json_schema", "schema": answer_schema(request.answer)}
            },
            "fallbacks": "default",
        }
        response = self._post(body)
        if response.status_code in (401, 403):
            raise ProviderError(
                "unauthorized",
                "The provider refused the key (AI_API_KEY)"
                if response.status_code == 401
                else "The key may not use this model",
            )
        if response.status_code == 429:
            raise ProviderError("rateLimited", "The provider limited the rate; try again later")
        if response.status_code >= 400:
            raise ProviderError(
                "failed",
                f"The provider answered {response.status_code}{_error_type(response)}",
                {"status": response.status_code},
            )
        try:
            message: dict[str, Any] = response.json()
        except ValueError as exc:
            raise ProviderError("malformed", "The provider's answer is not JSON") from exc
        stop = message.get("stop_reason")
        if stop == "refusal":
            category = (message.get("stop_details") or {}).get("category")
            raise ProviderError(
                "declined", "The provider declined the request", {"category": category}
            )
        if stop == "max_tokens":
            raise ProviderError("malformed", "The answer was cut off at its length limit")
        text = "".join(
            block.get("text", "")
            for block in message.get("content") or []
            if block.get("type") == "text"
        )
        try:
            data = json.loads(text)
        except ValueError as exc:
            raise ProviderError("malformed", "The answer is not JSON") from exc
        usage = message.get("usage") or {}
        return ProviderAnswer(
            data,
            message.get("model") or self.model,
            usage.get("input_tokens"),
            usage.get("output_tokens"),
        )

    def _post(self, body: dict[str, Any]) -> httpx.Response:
        for attempt in range(_ATTEMPTS):
            try:
                response = self._client.post(self._url, json=body, headers=self._headers)
            except httpx.TimeoutException as exc:
                if attempt + 1 < _ATTEMPTS:
                    continue
                raise ProviderError(
                    "unreachable", "The provider did not answer in time (AI_TIMEOUT_SECONDS)"
                ) from exc
            except httpx.HTTPError as exc:
                if attempt + 1 < _ATTEMPTS:
                    continue
                raise ProviderError("unreachable", "The provider could not be reached") from exc
            if response.status_code not in _RETRIED or attempt + 1 == _ATTEMPTS:
                return response
        raise AssertionError("unreachable")


def _error_type(response: httpx.Response) -> str:
    """`` (overloaded_error)`` from the API's error body, when it has one."""
    try:
        kind = (response.json().get("error") or {}).get("type")
    except ValueError, AttributeError:
        return ""
    return f" ({kind})" if kind else ""
