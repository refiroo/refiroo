"""A deterministic provider for tests and browser runners (AP-D11): ``AI_PROVIDER=
app.engine.proposals.fake:provider``.

It answers from a table keyed by purpose, by default with a fixed answer derived from the context,
and records every request it was sent, so a test can prove what left the instance. A test replaces
an answer with ``script`` (a value, a function of the context, or an exception to raise) and clears
the table and the record with ``reset``. Nothing leaves the process.
"""

from collections.abc import Callable
from typing import Any

from .provider import ProposalRequest, ProviderAnswer, ProviderError, Purpose

MODEL = "fake-1"


def _names(context: dict[str, Any]) -> dict[str, Any]:
    return {
        "suggestions": [
            {
                "proposal": item["proposal"],
                "key": item["key"],
                # Always a different name, so every type gets a proposal.
                "name": f"{item['name'].replace('_', ' ').title()} (suggested)",
                "reason": "Written out from the header",
                "confidence": 0.8,
            }
            for item in context.get("types", [])
        ]
    }


DEFAULTS: dict[Purpose, Callable[[dict[str, Any]], Any]] = {
    "connectionTest": lambda context: {"ready": True},
    "modelNames": _names,
}

_script: dict[str, Any] = {}
seen: list[ProposalRequest] = []


def script(purpose: Purpose, answer: Any) -> None:
    _script[purpose] = answer


def reset() -> None:
    _script.clear()
    seen.clear()


class FakeProvider:
    name = "fake"
    model = MODEL

    def propose(self, request: ProposalRequest) -> ProviderAnswer:
        seen.append(request)
        answer = _script.get(request.purpose, DEFAULTS[request.purpose])
        if isinstance(answer, BaseException):
            raise answer
        data = answer(request.context) if callable(answer) else answer
        return ProviderAnswer(data, MODEL, tokens_in=100, tokens_out=20)


def provider() -> FakeProvider:
    return FakeProvider()


__all__ = ["FakeProvider", "ProviderError", "provider", "reset", "script", "seen"]
