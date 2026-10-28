"""Whether a request may ask the AI provider (Product 0.16 AP1, AP-D3, AP-D7).

A feature's route calls ``ai_requested`` with what the caller sent: omitted, the provider is asked
whenever a provider is set, the send level allows the feature and the caller holds Use AI
proposals; ``false`` never; ``true`` is refused when it cannot be, so a client is never told it was
asked when it was not.
"""

from fastapi import Request

from ..engine.authorization.catalogue import FEATURE_GROUPS
from ..engine.proposals.provider import Purpose
from ..engine.proposals.registry import AiConfiguration
from ..errors import api_error

GROUP = FEATURE_GROUPS[0]


def configuration(request: Request) -> AiConfiguration:
    return request.app.state.ai


def ai_requested(
    request: Request, purpose: Purpose, asked: bool | None, *, workspace_key: str | None
) -> bool:
    if asked is False:
        return False
    ai = configuration(request)
    permitted = request.state.permissions.allows(GROUP, workspace_key)
    if asked is None:
        return ai.offers(purpose) and permitted
    if not ai.configured:
        raise api_error(
            409, "AI_NOT_CONFIGURED", "No AI provider is set up on this instance (AI_PROVIDER)"
        )
    if not ai.offers(purpose):
        raise api_error(
            409,
            "AI_SEND_LEVEL_TOO_LOW",
            f"AI_SEND_LEVEL '{ai.policy.level}' does not allow what this feature needs to send",
            {"sendLevel": ai.policy.level},
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
