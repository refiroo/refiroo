"""The AI provider's status and call records (Product 0.16 AP1, API.md § AI proposals)."""

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

from .common import CollectionPage, PrincipalResponse

SendLevel = Literal["structure", "samples", "values"]


class AiFeature(BaseModel):
    """A feature that asks the provider: whether it is offered, and the least it needs sent."""

    purpose: Literal["modelNames"]
    name: str
    needs: SendLevel
    available: bool


class AiTotals(BaseModel):
    days: int
    calls: int
    failed: int
    tokensIn: int
    tokensOut: int
    bytesIn: int
    bytesOut: int


class AiCallResponse(BaseModel):
    """One call to the provider (AP-D4): who asked, for what, of which provider and model, how much
    went each way and how it ended. ``content`` holds the request and answer only while
    ``AI_LOG_CONTENT`` keeps them."""

    id: str
    purpose: Literal["connectionTest", "modelNames"]
    provider: str
    model: str
    sendLevel: SendLevel
    promptVersion: str
    requestedBy: PrincipalResponse | None
    jobId: str | None
    startedAt: datetime
    durationMs: int
    bytesIn: int
    bytesOut: int
    tokensIn: int | None
    tokensOut: int | None
    outcome: Literal["answered", "failed"]
    failureKind: (
        Literal["unreachable", "unauthorized", "rateLimited", "declined", "malformed", "failed"]
        | None
    )
    failure: str | None
    content: dict[str, Any] | None = Field(
        default=None, description="The request and the answer, kept only with AI_LOG_CONTENT on"
    )


class AiCallPage(CollectionPage[AiCallResponse]):
    """Calls, newest first (ADR-030)."""


class AiStatusResponse(BaseModel):
    """How the provider is set up (read from the environment at start; the key is never shown),
    which features it offers, the last call and the totals of the last ``totals.days`` days."""

    configured: bool
    provider: str | None
    model: str | None
    endpoint: str | None
    keySet: bool
    sendLevel: SendLevel
    sampleValues: int
    minConfidence: float
    logContent: bool
    logContentDays: int
    timeoutSeconds: int
    features: list[AiFeature]
    lastCall: AiCallResponse | None
    totals: AiTotals


class AiSystemInfo(BaseModel):
    """Whether a provider is set, for every signed-in caller (``GET /system``)."""

    configured: bool
    provider: str | None
    # The model asked, so a client can say what it waits for.
    model: str | None = None
    sendLevel: SendLevel
