"""Any endpoint speaking the OpenAI chat-completions protocol (AP-D2), which also covers a model run
inside the organisation for one that may not send data out.

The answer is asked for as a JSON schema (``response_format``); an endpoint whose model ignores it
answers out of shape, and the call fails as malformed rather than being guessed at.
"""

import json
from typing import Any

import httpx

from .provider import ProposalRequest, ProviderAnswer, ProviderError, answer_schema


class OpenAICompatibleProvider:
    name = "openai-compatible"

    def __init__(
        self,
        base_url: str,
        model: str,
        api_key: str = "",
        *,
        timeout: float = 60,
        http_client: httpx.Client | None = None,
    ) -> None:
        self.model = model
        self._url = f"{base_url.rstrip('/')}/chat/completions"
        self._headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
        self._client = http_client or httpx.Client(timeout=timeout)

    def propose(self, request: ProposalRequest) -> ProviderAnswer:
        body = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": request.instructions},
                {"role": "user", "content": json.dumps(request.context, ensure_ascii=False)},
            ],
            "response_format": {
                "type": "json_schema",
                "json_schema": {
                    "name": "answer",
                    "schema": answer_schema(request.answer),
                    "strict": True,
                },
            },
        }
        try:
            response = self._client.post(self._url, json=body, headers=self._headers)
        except httpx.TimeoutException as exc:
            raise ProviderError(
                "unreachable", "The provider did not answer in time (AI_TIMEOUT_SECONDS)"
            ) from exc
        except httpx.HTTPError as exc:
            raise ProviderError(
                "unreachable", f"The provider could not be reached at {self._url}"
            ) from exc
        if response.status_code in (401, 403):
            raise ProviderError("unauthorized", "The provider refused the key (AI_API_KEY)")
        if response.status_code == 429:
            raise ProviderError("rateLimited", "The provider limited the rate; try again later")
        if response.status_code >= 400:
            raise ProviderError(
                "failed",
                f"The provider answered {response.status_code}",
                {"status": response.status_code},
            )
        try:
            answer: dict[str, Any] = response.json()
            choice = answer["choices"][0]
            if choice.get("finish_reason") == "length":
                raise ProviderError("malformed", "The answer was cut off at its length limit")
            data = json.loads(choice["message"]["content"])
        except (ValueError, KeyError, IndexError, TypeError) as exc:
            raise ProviderError(
                "malformed", "The answer is not JSON in the expected place"
            ) from exc
        usage = answer.get("usage") or {}
        return ProviderAnswer(
            data,
            answer.get("model") or self.model,
            usage.get("prompt_tokens"),
            usage.get("completion_tokens"),
        )
