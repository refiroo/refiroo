"""Whether a request may ask the AI provider (Product 0.16 AP1, AP-D3, AP-D7).

A feature's route calls ``ai_requested`` with what the caller sent: omitted, the provider is asked
whenever a provider is set, the send level allows the feature and the caller holds Use AI
proposals; ``false`` never; ``true`` is refused when it cannot be, so a client is never told it was
asked when it was not.
"""

from fastapi import Request

from ..config import SendLevel
from ..engine.authorization.catalogue import FEATURE_GROUPS
from ..engine.proposals.context import FEATURE_LEVELS, Policy
from ..engine.proposals.provider import Purpose
from ..engine.proposals.registry import AiConfiguration
from ..errors import api_error

GROUP = FEATURE_GROUPS[0]


def _chosen_level_serves(ai: AiConfiguration, purpose: Purpose, send_level: SendLevel | None) -> bool:
    """Whether the level a request chose (the ceiling when it chose none) gives the feature what it
    needs."""
    return send_level is None or Policy(send_level, ai.policy.samples).offers(purpose)


def configuration(request: Request) -> AiConfiguration:
    return request.app.state.ai


def ai_requested(
    request: Request,
    purpose: Purpose,
    asked: bool | None,
    *,
    workspace_key: str | None,
    send_level: SendLevel | None = None,
) -> bool:
    """``send_level`` is the level the caller chose for this request (AP-D3): never above the
    operator's ceiling (``AI_SEND_LEVEL``), and the level that applies must still satisfy what the
    feature needs; either is ``409 AI_SEND_LEVEL_TOO_LOW``."""
    if asked is False:
        return False
    ai = configuration(request)
    permitted = request.state.permissions.allows(GROUP, workspace_key)
    if asked is None:
        return ai.offers(purpose) and permitted and _chosen_level_serves(ai, purpose, send_level)
    if not ai.configured:
        raise api_error(
            409, "AI_NOT_CONFIGURED", "No AI provider is set up on this instance (AI_PROVIDER)"
        )
    if send_level is not None and not ai.policy.allows(send_level):
        raise api_error(
            409,
            "AI_SEND_LEVEL_TOO_LOW",
            f"sendLevel '{send_level}' is above this instance's ceiling AI_SEND_LEVEL "
            f"'{ai.policy.level}'; a request may choose a lower level, never a higher one",
            {"sendLevel": send_level, "ceiling": ai.policy.level},
        )
    if not ai.offers(purpose) or not _chosen_level_serves(ai, purpose, send_level):
        level = send_level or ai.policy.level
        raise api_error(
            409,
            "AI_SEND_LEVEL_TOO_LOW",
            f"Send level '{level}' does not allow what this feature needs to send "
            f"({FEATURE_LEVELS[purpose]})",
            {"sendLevel": level, "ceiling": ai.policy.level, "needs": FEATURE_LEVELS[purpose]},
        )
    if not permitted:
        where = f" in workspace '{workspace_key}'" if workspace_key else " at the instance"
        raise api_error(
            403,
            "FORBIDDEN",
            f"Asking the AI provider{where} needs Use AI proposals",
            {"action": "ai-proposals", "groups": [GROUP], "workspaceKey": workspace_key},
        )
    return True
