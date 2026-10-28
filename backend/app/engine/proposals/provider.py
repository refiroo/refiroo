"""The provider interface (AP-D1): one ``propose`` for every purpose.

A request names its purpose, the instructions, the context the context builder made and the shape
of the answer expected, as a Pydantic model; a provider returns the answer as parsed JSON. The
answer's shape is checked by ``calls.ask``, not by the provider, so no adapter can let a guess
through.
"""

from dataclasses import dataclass, field
from typing import Any, Literal, Protocol

from pydantic import BaseModel

# What a feature asks for. ``connectionTest`` is the operator's test of the settings (Settings › AI);
# ``modelNames`` the inference's better names for the types it adds (0.10 A6, folded in AP1).
Purpose = Literal["connectionTest", "modelNames"]

# Why a call failed, for the operator: the provider was not reached, it refused the key, it limited
# the rate, it declined the request, it answered out of shape, or it failed otherwise.
FailureKind = Literal[
    "unreachable", "unauthorized", "rateLimited", "declined", "malformed", "failed"
]


@dataclass(frozen=True)
class ProposalRequest:
    purpose: Purpose
    # What the provider is asked to do; versioned by ``prompt_version`` so a step can say which.
    instructions: str
    prompt_version: str
    # Built by ``context.py`` within the send level; JSON-serialisable.
    context: dict[str, Any]
    answer: type[BaseModel]


@dataclass(frozen=True)
class ProviderAnswer:
    data: Any
    # The model that answered, as the provider names it (it may differ from the one asked for when
    # the provider falls back).
    model: str
    tokens_in: int | None = None
    tokens_out: int | None = None


@dataclass
class ProviderError(Exception):
    kind: FailureKind
    message: str
    details: dict[str, Any] = field(default_factory=dict)

    def __str__(self) -> str:
        return self.message


class ProposalProvider(Protocol):
    # ``claude``, ``openai-compatible`` or the factory's own name.
    name: str
    model: str

    def propose(self, request: ProposalRequest) -> ProviderAnswer: ...


def answer_schema(answer: type[BaseModel]) -> dict[str, Any]:
    """The answer's JSON schema as structured output wants it: every object closed and every
    property required (a field with a default is still sent; the model fills it)."""
    schema = answer.model_json_schema()

    def close(node: Any) -> None:
        if isinstance(node, dict):
            if node.get("type") == "object" and "properties" in node:
                node["additionalProperties"] = False
                node["required"] = list(node["properties"])
            for value in node.values():
                close(value)
        elif isinstance(node, list):
            for value in node:
                close(value)

    close(schema)
    return schema
