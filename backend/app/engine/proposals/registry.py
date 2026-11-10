"""``AI_PROVIDER`` resolved once at startup (AP-D2) into the configuration every feature reads.

A setting that cannot work (a provider without its key or address, a factory that does not import)
refuses the start with the setting named, rather than failing at a steward's first proposal.
"""

import importlib
from dataclasses import dataclass
from typing import Any

from ...config import Settings
from .claude import ClaudeProvider
from .claude_code import ClaudeCodeProvider
from .context import Policy
from .openai_compatible import OpenAICompatibleProvider
from .provider import ProposalProvider, Purpose


@dataclass(frozen=True)
class AiConfiguration:
    provider: ProposalProvider | None
    policy: Policy
    min_confidence: float
    log_content: bool
    log_content_days: int
    # AI_CONTEXT_TOKENS: the model's window, when a feature must size its calls to it.
    context_tokens: int | None = None
    # AI_MAX_STEPS and AI_TASK_RETENTION_DAYS (0.16 AP6a): an assistant task's provider calls per
    # job, and the days it is kept.
    task_retention_days: int = 90

    @property
    def configured(self) -> bool:
        return self.provider is not None

    def offers(self, purpose: Purpose) -> bool:
        """Whether a feature of ``purpose`` is offered: a provider is set and the send level
        allows what it needs (hidden otherwise, AP-D3)."""
        return self.provider is not None and self.policy.offers(purpose)


def load_provider(settings: Settings) -> ProposalProvider | None:
    setting = settings.ai_provider.strip()
    if not setting:
        return None
    timeout = settings.ai_timeout_seconds
    if setting == "claude":
        if not settings.ai_api_key:
            raise RuntimeError(
                "AI_PROVIDER=claude needs AI_API_KEY, the key of the organisation's Claude account"
            )
        return ClaudeProvider(
            settings.ai_api_key, settings.ai_model, base_url=settings.ai_base_url, timeout=timeout
        )
    if setting == "claude-code":
        return ClaudeCodeProvider(settings.ai_model, timeout)
    if setting == "openai-compatible":
        missing = [
            name
            for name, value in (
                ("AI_BASE_URL", settings.ai_base_url),
                ("AI_MODEL", settings.ai_model),
            )
            if not value
        ]
        if missing:
            raise RuntimeError(
                f"AI_PROVIDER=openai-compatible needs {' and '.join(missing)}: the endpoint and the model it serves"
            )
        return OpenAICompatibleProvider(
            settings.ai_base_url,
            settings.ai_model,
            settings.ai_api_key,
            reasoning_effort=settings.ai_reasoning_effort,
            timeout=timeout,
        )
    module_name, separator, attribute = setting.partition(":")
    if not separator or not module_name or not attribute:
        raise RuntimeError(
            f"AI_PROVIDER must be claude, claude-code, openai-compatible or a factory written module:function, not {setting!r}"
        )
    try:
        factory: Any = getattr(importlib.import_module(module_name), attribute)
        provider = factory()
    except Exception as exc:
        raise RuntimeError(
            f"AI_PROVIDER {setting!r} could not be loaded ({type(exc).__name__}: {exc})"
        ) from exc
    if not callable(getattr(provider, "propose", None)):
        # A refused start is a RuntimeError, as every other setting's.
        raise RuntimeError(f"AI_PROVIDER {setting!r} returned an object without propose(request)")  # noqa: TRY004
    return provider


def configure(settings: Settings) -> AiConfiguration:
    return AiConfiguration(
        provider=load_provider(settings),
        policy=Policy(settings.ai_send_level, settings.ai_sample_values),
        min_confidence=settings.ai_min_confidence,
        log_content=settings.ai_log_content,
        log_content_days=settings.ai_log_content_days,
        context_tokens=settings.ai_context_tokens,
        task_retention_days=settings.ai_task_retention_days,
    )


def provider_label(provider: ProposalProvider) -> str:
    return getattr(provider, "name", "") or type(provider).__name__


def model_label(provider: ProposalProvider) -> str:
    return getattr(provider, "model", "") or ""
