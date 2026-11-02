"""A deterministic provider for tests and browser runners (AP-D11): ``AI_PROVIDER=
app.engine.proposals.fake:provider``.

It answers from a table keyed by purpose, by default with a fixed answer derived from the context,
and records every request it was sent, so a test can prove what left the instance. A test replaces
an answer with ``script`` (a value, a function of the context, or an exception to raise) and clears
the table and the record with ``reset``. Nothing leaves the process.
"""

from collections import Counter
from collections.abc import Callable
from typing import Any

from .provider import ProposalRequest, ProviderAnswer, ProviderError, Purpose

MODEL = "fake-1"


def _common(first: str, second: str) -> int:
    """How many characters two names share, counted by letter (case ignored)."""
    left, right = Counter(first.lower()), Counter(second.lower())
    return sum((left & right).values())


def _targets(context: dict[str, Any]) -> dict[str, Any]:
    """Each source's candidate with the most characters in common with its name, else the first."""
    shared = {item["ref"]: item for item in context.get("candidates", [])}
    answers = []
    for source in context.get("sources", []):
        pool = [shared[ref] for ref in source.get("candidates", shared)] if shared else []
        if not pool:
            answers.append({"source": source["ref"], "target": None, "reason": "", "confidence": 0})
            continue
        best = max(pool, key=lambda item: _common(source["name"], item["name"]))
        answers.append(
            {
                "source": source["ref"],
                "target": best["ref"],
                "reason": "Closest name",
                "confidence": 0.8,
            }
        )
    return {"answers": answers}


def _translation(context: dict[str, Any]) -> dict[str, Any]:
    """A question the list cannot filter by is searched for as it stands."""
    return {"filters": [], "search": context.get("question", ""), "notExpressed": []}


def _summary(context: dict[str, Any]) -> dict[str, Any]:
    """One statement for each of the first three facts, citing it."""
    return {
        "statements": [
            {"text": fact["text"], "factIds": [fact["id"]]} for fact in context.get("facts", [])[:3]
        ]
    }


DEFAULTS: dict[Purpose, Callable[[dict[str, Any]], Any]] = {
    "connectionTest": lambda context: {"ready": True},
    "mappingTarget": _targets,
    "queryTranslation": _translation,
    "impactSummary": _summary,
    "historyAccount": _summary,
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
