"""The optional assistant (Product 0.10 A6, A-D5, D95): an interface, with no provider bundled.

``INFERENCE_ASSISTANT`` names a factory (``package.module:function``) returning an object with
``suggest(request)``; empty, the default, means no assistant and nothing is sent anywhere. The
request holds each sheet's headers and at most ``INFERENCE_ASSISTANT_ROWS`` of its rows, and the
types the inference's proposals add. The assistant answers labels for those types; each becomes a
proposal of pattern ``assistant`` (a ``setLabel`` requiring the proposal it renames). It never
applies anything, and a failing assistant is a warning: the deterministic proposals stand.
"""

import importlib
import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any, Protocol

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class AssistantSheet:
    name: str
    headers: list[str]
    rows: list[list[str | None]]


@dataclass(frozen=True)
class AssistantType:
    """A type a proposal adds: the proposal, the type's key and the name the rules gave it."""

    proposal: str
    key: str
    name: str


@dataclass(frozen=True)
class AssistantRequest:
    sheets: list[AssistantSheet]
    types: list[AssistantType] = field(default_factory=list)


@dataclass(frozen=True)
class AssistantSuggestion:
    """A better name for a type a proposal adds, and why."""

    proposal: str
    key: str
    name: str
    reason: str = ""


class Assistant(Protocol):
    def suggest(self, request: AssistantRequest) -> list[AssistantSuggestion]: ...


def load_assistant(setting: str) -> Assistant | None:
    """The assistant ``setting`` names, or ``None`` when it is empty."""
    if not setting.strip():
        return None
    module_name, _, attribute = setting.strip().partition(":")
    factory: Callable[[], Assistant] = getattr(importlib.import_module(module_name), attribute or "assistant")
    return factory()


def suggestions(assistant: Assistant, request: AssistantRequest) -> tuple[list[AssistantSuggestion], str | None]:
    """The assistant's suggestions for types the request names; a failure as a warning."""
    known = {(t.proposal, t.key) for t in request.types}
    try:
        answered = assistant.suggest(request)
    except Exception as exc:  # noqa: BLE001 - any failure of an operator's plug-in is a warning
        logger.warning("The inference assistant failed: %s", exc)
        return [], f"The assistant failed ({type(exc).__name__}); the proposals of the rules stand"
    found = [s for s in answered if (s.proposal, s.key) in known and isinstance(s.name, str) and s.name.strip()]
    return found, None


def proposal_body(suggestion: AssistantSuggestion, current: str) -> dict[str, Any]:
    return {
        "summary": f"The assistant suggests naming {current} \"{suggestion.name}\""
        + (f": {suggestion.reason}" if suggestion.reason else "."),
        "operations": [{"kind": "setLabel", "element": {"objectType": suggestion.key}, "name": suggestion.name}],
        "evidence": {"assistant": True, "reason": suggestion.reason},
    }
